"""
ScoreService - 기업 총 리스크 점수 계산 (5-Node 스키마)
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScoreService:
    """리스크 점수 계산 서비스 (5-Node 스키마)"""

    def __init__(self, neo4j_client):
        self.client = neo4j_client

    def calculate_company_score(self, company_id: str) -> dict:
        """기업 총 리스크 점수 계산"""
        direct_score = self._calculate_direct_score(company_id)
        propagated_score = self._calculate_propagated_score(company_id)
        critical_boost = self._calculate_critical_boost(company_id)
        total_score = min(100, direct_score + propagated_score + critical_boost)
        risk_level = self._determine_status(total_score)
        trend = self._calculate_trend(company_id, total_score)

        self._update_company_score(
            company_id, direct_score, propagated_score, total_score, risk_level, trend
        )

        if critical_boost > 0:
            logger.info(f"[{company_id}] CRITICAL 부스트 적용: +{critical_boost}점")

        return {
            "direct": direct_score,
            "propagated": propagated_score,
            "criticalBoost": critical_boost,
            "total": total_score,
            "riskLevel": risk_level,
            "trend": trend,
        }

    def _calculate_direct_score(self, company_id: str) -> int:
        """직접 리스크 계산 (카테고리 가중 합산)"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
        RETURN sum(coalesce(rc.weightedScore, 0)) AS totalWeightedScore
        """
        result = self.client.execute_read_single(query, {"companyId": company_id})
        if result and result.get("totalWeightedScore"):
            return round(result["totalWeightedScore"])
        return 0

    def _calculate_critical_boost(self, company_id: str) -> int:
        """CRITICAL 이벤트 부스터 — 부도/회생/파산 등 치명적 이벤트가 있으면 점수 직접 부스트"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
              -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
        WHERE ev.score >= 80
        RETURN count(ev) AS criticalCount, max(ev.score) AS maxScore
        """
        result = self.client.execute_read_single(query, {"companyId": company_id})
        if not result:
            return 0

        critical_count = result.get("criticalCount", 0) or 0
        max_score = result.get("maxScore", 0) or 0
        boost = 0

        if critical_count >= 3:
            boost += 30
        elif critical_count >= 1:
            boost += 15

        if max_score >= 95:
            boost += 10

        return boost

    def _calculate_propagated_score(self, company_id: str) -> int:
        """전이 리스크 계산 (관련기업 리스크 전이)"""
        query = """
        MATCH (c:Company {name: $companyId})-[r:HAS_RELATED]->(rc:Company)
        WHERE rc.totalRiskScore > 0
        WITH rc, rc.totalRiskScore AS relScore,
             CASE WHEN coalesce(r.tier, 1) = 1 THEN 0.3 ELSE 0.1 END AS rate
        RETURN sum(relScore * rate) AS propagatedScore
        """
        result = self.client.execute_read_single(query, {"companyId": company_id})
        if result and result.get("propagatedScore"):
            return min(30, round(result["propagatedScore"]))
        return 0

    def _determine_status(self, score: int) -> str:
        if score >= 60:
            return "CRITICAL"
        elif score >= 35:
            return "WARNING"
        return "PASS"

    def _calculate_trend(self, company_id: str, new_score: int) -> str:
        query = """
        MATCH (c:Company {name: $companyId})
        RETURN c.totalRiskScore AS previousScore
        """
        result = self.client.execute_read_single(query, {"companyId": company_id})
        previous_score = result.get("previousScore", 0) if result else 0

        if new_score > (previous_score or 0):
            return "UP"
        elif new_score < (previous_score or 0):
            return "DOWN"
        return "STABLE"

    def _update_company_score(
        self, company_id: str, direct: int, propagated: int,
        total: int, risk_level: str, trend: str,
    ) -> None:
        """Company 노드 점수 업데이트"""
        query = """
        MATCH (c:Company {name: $companyId})
        SET c.directScore = $direct,
            c.propagatedScore = $propagated,
            c.totalRiskScore = $total,
            c.riskLevel = $riskLevel,
            c.riskTrend = $trend,
            c.updatedAt = datetime()
        """
        self.client.execute_write(query, {
            "companyId": company_id,
            "direct": direct,
            "propagated": propagated,
            "total": total,
            "riskLevel": risk_level,
            "trend": trend,
        })
        logger.info(f"[{company_id}] 점수 업데이트: direct={direct}, propagated={propagated}, total={total}, level={risk_level}")

    def get_company_score(self, company_id: str) -> Optional[dict]:
        """기업 점수 조회"""
        query = """
        MATCH (c:Company {name: $companyId})
        RETURN c.directScore AS direct, c.propagatedScore AS propagated,
               c.totalRiskScore AS total, c.riskLevel AS riskLevel,
               c.riskTrend AS trend
        """
        return self.client.execute_read_single(query, {"companyId": company_id})

    def get_score_evidence(self, company_id: str) -> dict:
        """점수 근거 조회 (5-Node: RiskEvent 기반)"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
              -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
        WITH c,
             count(DISTINCT CASE WHEN ev.type = 'NEWS' THEN ev END) AS newsCount,
             count(DISTINCT CASE WHEN ev.type = 'DISCLOSURE' THEN ev END) AS discCount,
             collect(DISTINCT ev.title)[0..3] AS topEvents
        RETURN newsCount AS totalNews, discCount AS totalDisclosures,
               topEvents AS topFactors
        """
        result = self.client.execute_read_single(query, {"companyId": company_id})
        if result:
            return {
                "totalNews": result.get("totalNews", 0),
                "totalDisclosures": result.get("totalDisclosures", 0),
                "topFactors": result.get("topFactors", []),
            }
        return {"totalNews": 0, "totalDisclosures": 0, "topFactors": []}
