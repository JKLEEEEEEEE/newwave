"""
리스크 점수 계산기 v3 (Risk Graph v3)
- 책임: 직접 리스크 + 전이 리스크 통합 계산, breakdown 제공
- 위치: risk_engine/risk_calculator_v3.py

Design Doc: docs/02-design/features/risk-graph-v3.design.md Section 3.3
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from .neo4j_client import Neo4jClient
from .score_engine import determine_status, StatusType
from .load_graph_v3 import (
    create_company_status_relation,
    create_risk_category_for_company,
    create_risk_history,
    RISK_CATEGORY_CODES,
)

logger = logging.getLogger(__name__)

# =============================================================================
# 상수 정의
# =============================================================================

# 카테고리별 가중치
CATEGORY_WEIGHTS = {
    "LEGAL": 0.15,
    "CREDIT": 0.20,
    "GOVERNANCE": 0.10,
    "OPERATIONAL": 0.15,
    "AUDIT": 0.20,
    "ESG": 0.10,
    "CAPITAL": 0.05,
    "OTHER": 0.05,
}

# Tier별 전이율
TIER_PROPAGATION_RATE = {
    1: 0.70,  # Tier 1 (대표이사/회장): 70% 전이
    2: 0.50,  # Tier 2 (임원/이사): 50% 전이
    3: 0.30,  # Tier 3 (자회사/공급업체): 30% 전이
}

# 관계별 전이율
RELATION_PROPAGATION_RATE = {
    "CEO": 0.70,
    "CFO": 0.60,
    "EXECUTIVE": 0.50,
    "BOARD_MEMBER": 0.40,
    "SHAREHOLDER": 0.40,
    "SUBSIDIARY": 0.50,
    "SUPPLIER": 0.30,
    "RELATED_PARTY": 0.20,
}

# 전이 리스크 상한
MAX_PROPAGATED_RISK = 30

# Status 임계값
STATUS_THRESHOLDS = {
    "PASS": (0, 49),
    "WARNING": (50, 74),
    "FAIL": (75, 100),
}


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class CategoryScore:
    """카테고리별 점수"""
    code: str                    # LEGAL, CREDIT, etc.
    name: str                    # 법률위험, 신용위험, etc.
    score: int                   # 원점수 (0-100)
    weight: float                # 가중치 (0.0-1.0)
    weighted_score: float        # 가중 점수
    factors: list[str] = field(default_factory=list)  # 근거 목록
    source_count: int = 0        # 소스 개수 (뉴스/공시)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "weighted_score": round(self.weighted_score, 2),
            "factors": self.factors,
            "source_count": self.source_count,
        }


@dataclass
class PropagatedScore:
    """전이 리스크 점수"""
    source_name: str             # 전이 소스 (임원명, 자회사명 등)
    source_type: str             # PERSON, SUBSIDIARY, SUPPLIER
    relation: str                # CEO, EXECUTIVE, SUBSIDIARY, etc.
    tier: int                    # Tier (1, 2, 3)
    source_risk: int             # 소스의 리스크 점수
    propagation_rate: float      # 전이율
    propagated: float            # 전이된 점수

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "relation": self.relation,
            "tier": self.tier,
            "source_risk": self.source_risk,
            "propagation_rate": self.propagation_rate,
            "propagated": round(self.propagated, 2),
        }


@dataclass
class RiskBreakdown:
    """리스크 점수 상세 분석"""
    company_id: str
    company_name: str
    total_score: int
    status: StatusType
    direct_score: int
    propagated_score: int
    direct_breakdown: list[CategoryScore] = field(default_factory=list)
    propagated_breakdown: list[PropagatedScore] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "total_score": self.total_score,
            "status": self.status,
            "direct_score": self.direct_score,
            "propagated_score": self.propagated_score,
            "direct_breakdown": [c.to_dict() for c in self.direct_breakdown],
            "propagated_breakdown": [p.to_dict() for p in self.propagated_breakdown],
            "calculated_at": self.calculated_at.isoformat(),
        }


# =============================================================================
# 리스크 계산기 클래스
# =============================================================================

class RiskCalculatorV3:
    """리스크 점수 계산기 v3"""

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Args:
            neo4j_client: Neo4j 클라이언트
        """
        self.client = neo4j_client

    def calculate_total_risk(self, company_id: str) -> RiskBreakdown:
        """
        총 리스크 점수 계산

        Args:
            company_id: 기업 ID

        Returns:
            RiskBreakdown: 상세 분석 결과
        """
        # 기업 정보 조회
        company_info = self._get_company_info(company_id)
        if not company_info:
            raise ValueError(f"기업을 찾을 수 없습니다: {company_id}")

        # 직접 리스크 계산
        direct_score, direct_breakdown = self.calculate_direct_risk(company_id)

        # 전이 리스크 계산
        propagated_score, propagated_breakdown = self.calculate_propagated_risk(company_id)

        # 총점 계산 (상한 100)
        total_score = min(direct_score + propagated_score, 100)

        # Status 결정
        status = determine_status(total_score)

        breakdown = RiskBreakdown(
            company_id=company_id,
            company_name=company_info.get("name", ""),
            total_score=total_score,
            status=status,
            direct_score=direct_score,
            propagated_score=propagated_score,
            direct_breakdown=direct_breakdown,
            propagated_breakdown=propagated_breakdown,
        )

        logger.info(f"리스크 계산 완료: {company_id} - Total: {total_score} ({status})")
        return breakdown

    def calculate_direct_risk(self, company_id: str) -> tuple[int, list[CategoryScore]]:
        """
        직접 리스크 계산

        공시와 뉴스에서 직접 언급된 리스크 요소 기반

        Args:
            company_id: 기업 ID

        Returns:
            (직접 리스크 점수, 카테고리별 breakdown)
        """
        # 카테고리별 점수 조회 (Neo4j)
        query = """
        MATCH (c:Company {id: $companyId})

        // 공시 기반 리스크
        OPTIONAL MATCH (c)<-[:MENTIONS]-(d:Disclosure)
        WHERE d.rawScore > 0

        // 뉴스 기반 리스크
        OPTIONAL MATCH (c)<-[:MENTIONS]-(n:News)
        WHERE n.rawScore > 0

        WITH c,
            collect(DISTINCT {
                type: 'DISCLOSURE',
                category: d.category,
                score: d.finalScore,
                title: d.title,
                daysOld: d.daysOld
            }) as disclosures,
            collect(DISTINCT {
                type: 'NEWS',
                category: n.category,
                score: n.finalScore,
                title: n.title,
                daysOld: n.daysOld
            }) as news

        RETURN c.name as companyName, disclosures, news
        """

        category_scores: dict[str, CategoryScore] = {}

        # 카테고리 초기화
        for code, info in RISK_CATEGORY_CODES.items():
            weight = CATEGORY_WEIGHTS.get(code, 0.05)
            category_scores[code] = CategoryScore(
                code=code,
                name=info["name"],
                score=0,
                weight=weight,
                weighted_score=0,
                factors=[],
                source_count=0,
            )

        try:
            with self.client.session() as session:
                result = session.run(query, {"companyId": company_id})
                record = result.single()

                if record:
                    # 공시 처리
                    for d in record.get("disclosures", []):
                        if d and d.get("category") and d.get("score"):
                            cat = d["category"]
                            if cat in category_scores:
                                score = int(d["score"] or 0)
                                if score > category_scores[cat].score:
                                    category_scores[cat].score = score
                                category_scores[cat].factors.append(
                                    f"[공시] {d.get('title', '')[:30]}... ({score}점)"
                                )
                                category_scores[cat].source_count += 1

                    # 뉴스 처리
                    for n in record.get("news", []):
                        if n and n.get("category") and n.get("score"):
                            cat = n["category"]
                            if cat in category_scores:
                                score = int(n["score"] or 0)
                                if score > category_scores[cat].score:
                                    category_scores[cat].score = score
                                category_scores[cat].factors.append(
                                    f"[뉴스] {n.get('title', '')[:30]}... ({score}점)"
                                )
                                category_scores[cat].source_count += 1

        except Exception as e:
            logger.error(f"직접 리스크 조회 실패: {company_id} - {e}")

        # 가중 점수 계산
        for cat in category_scores.values():
            cat.weighted_score = cat.score * cat.weight

        # 직접 리스크 점수 (카테고리 최고점 기준)
        direct_score = max((c.score for c in category_scores.values()), default=0)

        # 유효한 카테고리만 반환
        breakdown = [c for c in category_scores.values() if c.score > 0 or c.source_count > 0]
        breakdown.sort(key=lambda x: x.score, reverse=True)

        return direct_score, breakdown

    def calculate_propagated_risk(self, company_id: str) -> tuple[int, list[PropagatedScore]]:
        """
        전이 리스크 계산

        임원, 자회사, 공급업체로부터 전이되는 리스크

        Args:
            company_id: 기업 ID

        Returns:
            (전이 리스크 점수, 전이 breakdown)
        """
        propagated_scores: list[PropagatedScore] = []

        # 임원/주주로부터 전이 (Person → Company)
        person_query = """
        MATCH (c:Company {id: $companyId})<-[r:WORKS_AT]-(p:Person)
        OPTIONAL MATCH (p)-[:MENTIONED_IN_NEWS]->(n:News)
        WHERE n.rawScore > 0
        WITH p, r, max(n.finalScore) as personRisk
        WHERE personRisk > 0
        RETURN p.name as personName, r.role as role, personRisk
        """

        try:
            with self.client.session() as session:
                result = session.run(person_query, {"companyId": company_id})
                for record in result:
                    role = record.get("role", "EXECUTIVE")
                    rate = RELATION_PROPAGATION_RATE.get(role, 0.3)
                    tier = self._get_tier_from_role(role)
                    source_risk = int(record.get("personRisk", 0))
                    propagated = source_risk * rate

                    propagated_scores.append(PropagatedScore(
                        source_name=record.get("personName", ""),
                        source_type="PERSON",
                        relation=role,
                        tier=tier,
                        source_risk=source_risk,
                        propagation_rate=rate,
                        propagated=propagated,
                    ))
        except Exception as e:
            logger.warning(f"임원 전이 리스크 조회 실패: {e}")

        # 자회사로부터 전이 (Subsidiary → Parent)
        subsidiary_query = """
        MATCH (c:Company {id: $companyId})<-[:SUBSIDIARY_OF]-(sub:Company)
        WHERE sub.totalRiskScore > 0
        RETURN sub.name as subName, sub.totalRiskScore as subRisk
        """

        try:
            with self.client.session() as session:
                result = session.run(subsidiary_query, {"companyId": company_id})
                for record in result:
                    rate = RELATION_PROPAGATION_RATE.get("SUBSIDIARY", 0.5)
                    source_risk = int(record.get("subRisk", 0))
                    propagated = source_risk * rate

                    propagated_scores.append(PropagatedScore(
                        source_name=record.get("subName", ""),
                        source_type="COMPANY",
                        relation="SUBSIDIARY",
                        tier=3,
                        source_risk=source_risk,
                        propagation_rate=rate,
                        propagated=propagated,
                    ))
        except Exception as e:
            logger.warning(f"자회사 전이 리스크 조회 실패: {e}")

        # 총 전이 리스크 (상한 적용)
        total_propagated = sum(p.propagated for p in propagated_scores)
        capped_propagated = min(int(total_propagated), MAX_PROPAGATED_RISK)

        propagated_scores.sort(key=lambda x: x.propagated, reverse=True)

        return capped_propagated, propagated_scores

    def _get_tier_from_role(self, role: str) -> int:
        """역할에서 Tier 결정"""
        tier1_roles = {"CEO", "CFO", "CHAIRMAN", "회장", "대표이사"}
        tier2_roles = {"EXECUTIVE", "BOARD_MEMBER", "임원", "이사"}
        tier3_roles = {"SHAREHOLDER", "주주", "관계자"}

        if role in tier1_roles:
            return 1
        elif role in tier2_roles:
            return 2
        else:
            return 3

    def _get_company_info(self, company_id: str) -> dict | None:
        """기업 정보 조회"""
        query = """
        MATCH (c:Company {id: $companyId})
        RETURN c.name as name, c.corpCode as corpCode, c.totalRiskScore as currentScore
        """
        try:
            with self.client.session() as session:
                result = session.run(query, {"companyId": company_id})
                record = result.single()
                return dict(record) if record else None
        except Exception as e:
            logger.error(f"기업 정보 조회 실패: {e}")
            return None

    def update_company_risk(self, company_id: str) -> RiskBreakdown:
        """
        기업 리스크 점수 업데이트 및 저장

        Args:
            company_id: 기업 ID

        Returns:
            RiskBreakdown: 업데이트된 리스크 정보
        """
        # 현재 점수 조회
        company_info = self._get_company_info(company_id)
        old_score = company_info.get("currentScore", 0) if company_info else 0

        # 리스크 계산
        breakdown = self.calculate_total_risk(company_id)

        # Status 관계 업데이트
        create_company_status_relation(
            client=self.client,
            company_id=company_id,
            status_id=breakdown.status,
            score=breakdown.total_score,
            breakdown={c.code: c.score for c in breakdown.direct_breakdown},
        )

        # 카테고리별 RiskCategory 노드 업데이트
        for cat_score in breakdown.direct_breakdown:
            if cat_score.score > 0:
                create_risk_category_for_company(
                    client=self.client,
                    company_id=company_id,
                    category_code=cat_score.code,
                    score=cat_score.score,
                    factors=cat_score.factors,
                )

        # 점수 변화 시 히스토리 기록
        if old_score != breakdown.total_score:
            old_status = determine_status(old_score)
            create_risk_history(
                client=self.client,
                company_id=company_id,
                old_status=old_status,
                new_status=breakdown.status,
                old_score=old_score,
                new_score=breakdown.total_score,
                trigger_event="RECALCULATION",
            )

        logger.info(f"리스크 업데이트 완료: {company_id} - {old_score} → {breakdown.total_score}")
        return breakdown


# =============================================================================
# 헬퍼 함수
# =============================================================================

def calculate_risk_for_company(client: Neo4jClient, company_id: str) -> RiskBreakdown:
    """
    특정 기업의 리스크 계산 (편의 함수)

    Args:
        client: Neo4j 클라이언트
        company_id: 기업 ID

    Returns:
        RiskBreakdown
    """
    calculator = RiskCalculatorV3(client)
    return calculator.calculate_total_risk(company_id)


def update_all_company_risks(client: Neo4jClient) -> dict[str, RiskBreakdown]:
    """
    모든 기업의 리스크 일괄 업데이트

    Args:
        client: Neo4j 클라이언트

    Returns:
        기업 ID별 RiskBreakdown
    """
    calculator = RiskCalculatorV3(client)
    results = {}

    # 모든 기업 조회
    query = "MATCH (c:Company) RETURN c.id as id"

    try:
        with client.session() as session:
            result = session.run(query)
            company_ids = [record["id"] for record in result]

        for company_id in company_ids:
            try:
                results[company_id] = calculator.update_company_risk(company_id)
            except Exception as e:
                logger.error(f"기업 리스크 업데이트 실패 ({company_id}): {e}")

    except Exception as e:
        logger.error(f"기업 목록 조회 실패: {e}")

    return results


def get_status_summary(client: Neo4jClient) -> dict:
    """
    Status별 기업 요약

    Args:
        client: Neo4j 클라이언트

    Returns:
        Status별 기업 수 및 목록
    """
    query = """
    MATCH (c:Company)
    RETURN c.riskLevel as status, count(c) as count,
           collect({id: c.id, name: c.name, score: c.totalRiskScore}) as companies
    ORDER BY
        CASE c.riskLevel
            WHEN 'FAIL' THEN 1
            WHEN 'WARNING' THEN 2
            ELSE 3
        END
    """

    summary = {"PASS": {"count": 0, "companies": []},
               "WARNING": {"count": 0, "companies": []},
               "FAIL": {"count": 0, "companies": []}}

    try:
        with client.session() as session:
            result = session.run(query)
            for record in result:
                status = record.get("status", "PASS")
                if status in summary:
                    summary[status] = {
                        "count": record.get("count", 0),
                        "companies": record.get("companies", []),
                    }
    except Exception as e:
        logger.error(f"Status 요약 조회 실패: {e}")

    return summary
