"""
Graph v3 스키마 초기화 및 데이터 로더
- 책임: Status/RiskCategory 노드 생성, 인덱스/제약조건 설정
- 위치: risk_engine/load_graph_v3.py

Design Doc: docs/02-design/features/risk-graph-v3.design.md Section 4
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Literal

from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

# =============================================================================
# 상수 정의
# =============================================================================

StatusId = Literal["PASS", "WARNING", "FAIL"]

# Status 노드 정의 (시스템 고정값)
STATUS_DEFINITIONS = [
    {
        "id": "PASS",
        "name": "정상",
        "minScore": 0,
        "maxScore": 49,
        "color": "#22C55E",
        "icon": "check-circle",
        "description": "정기 모니터링",
        "priority": 3,
    },
    {
        "id": "WARNING",
        "name": "주의",
        "minScore": 50,
        "maxScore": 74,
        "color": "#F97316",
        "icon": "alert-triangle",
        "description": "집중 모니터링, 원인 분석",
        "priority": 2,
    },
    {
        "id": "FAIL",
        "name": "위험",
        "minScore": 75,
        "maxScore": 100,
        "color": "#EF4444",
        "icon": "x-circle",
        "description": "즉시 대응, 리스크 완화 조치",
        "priority": 1,
    },
]

# RiskCategory 코드 정의
RISK_CATEGORY_CODES = {
    "LEGAL": {"name": "법률위험", "weight": 0.15, "description": "소송, 규제, 제재 관련 위험"},
    "CREDIT": {"name": "신용위험", "weight": 0.20, "description": "부도, 파산, 채무불이행 관련 위험"},
    "GOVERNANCE": {"name": "지배구조위험", "weight": 0.10, "description": "경영진, 주주, 이사회 관련 위험"},
    "OPERATIONAL": {"name": "운영위험", "weight": 0.15, "description": "사업중단, 생산차질 관련 위험"},
    "AUDIT": {"name": "감사위험", "weight": 0.20, "description": "감사의견, 회계 관련 위험"},
    "ESG": {"name": "ESG위험", "weight": 0.10, "description": "환경, 사회, 지배구조 관련 위험"},
    "CAPITAL": {"name": "자본위험", "weight": 0.05, "description": "유상증자, 감자 관련 위험"},
    "OTHER": {"name": "기타위험", "weight": 0.05, "description": "기타 분류되지 않은 위험"},
}


# =============================================================================
# 스키마 초기화 클래스
# =============================================================================

class GraphSchemaV3:
    """Graph v3 스키마 관리자"""

    def __init__(self, client: Neo4jClient | None = None):
        """
        Args:
            client: Neo4jClient 인스턴스 (None이면 새로 생성)
        """
        self.client = client or Neo4jClient()

    def initialize_all(self) -> dict:
        """
        전체 스키마 초기화

        Returns:
            초기화 결과 요약
        """
        results = {
            "constraints": self.create_constraints(),
            "indexes": self.create_indexes(),
            "status_nodes": self.create_status_nodes(),
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(f"Graph v3 스키마 초기화 완료: {results}")
        return results

    def create_constraints(self) -> list[str]:
        """제약조건 생성"""
        constraints = [
            # Status
            ("status_id_unique", "CREATE CONSTRAINT status_id_unique IF NOT EXISTS FOR (s:Status) REQUIRE s.id IS UNIQUE"),

            # Company
            ("company_id_unique", "CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE"),
            ("company_corpcode_unique", "CREATE CONSTRAINT company_corpcode_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.corpCode IS UNIQUE"),

            # Deal
            ("deal_id_unique", "CREATE CONSTRAINT deal_id_unique IF NOT EXISTS FOR (d:Deal) REQUIRE d.id IS UNIQUE"),

            # News
            ("news_id_unique", "CREATE CONSTRAINT news_id_unique IF NOT EXISTS FOR (n:News) REQUIRE n.id IS UNIQUE"),
            ("news_urlhash_unique", "CREATE CONSTRAINT news_urlhash_unique IF NOT EXISTS FOR (n:News) REQUIRE n.urlHash IS UNIQUE"),

            # Disclosure
            ("disclosure_id_unique", "CREATE CONSTRAINT disclosure_id_unique IF NOT EXISTS FOR (d:Disclosure) REQUIRE d.id IS UNIQUE"),
            ("disclosure_rcept_unique", "CREATE CONSTRAINT disclosure_rcept_unique IF NOT EXISTS FOR (d:Disclosure) REQUIRE d.rceptNo IS UNIQUE"),

            # Person
            ("person_id_unique", "CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE"),

            # RiskCategory
            ("riskcategory_id_unique", "CREATE CONSTRAINT riskcategory_id_unique IF NOT EXISTS FOR (r:RiskCategory) REQUIRE r.id IS UNIQUE"),

            # RiskHistory
            ("riskhistory_id_unique", "CREATE CONSTRAINT riskhistory_id_unique IF NOT EXISTS FOR (h:RiskHistory) REQUIRE h.id IS UNIQUE"),
        ]

        created = []
        with self.client.session() as session:
            for name, query in constraints:
                try:
                    session.run(query)
                    created.append(name)
                    logger.debug(f"제약조건 생성: {name}")
                except Exception as e:
                    logger.warning(f"제약조건 생성 실패 (이미 존재할 수 있음): {name} - {e}")

        return created

    def create_indexes(self) -> list[str]:
        """인덱스 생성"""
        indexes = [
            # Company 인덱스
            ("company_name_idx", "CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.name)"),
            ("company_risklevel_idx", "CREATE INDEX company_risklevel_idx IF NOT EXISTS FOR (c:Company) ON (c.riskLevel)"),
            ("company_totalriskscore_idx", "CREATE INDEX company_totalriskscore_idx IF NOT EXISTS FOR (c:Company) ON (c.totalRiskScore)"),

            # News 인덱스
            ("news_publishedat_idx", "CREATE INDEX news_publishedat_idx IF NOT EXISTS FOR (n:News) ON (n.publishedAt)"),
            ("news_category_idx", "CREATE INDEX news_category_idx IF NOT EXISTS FOR (n:News) ON (n.category)"),
            ("news_rawscore_idx", "CREATE INDEX news_rawscore_idx IF NOT EXISTS FOR (n:News) ON (n.rawScore)"),

            # Disclosure 인덱스
            ("disclosure_filingdate_idx", "CREATE INDEX disclosure_filingdate_idx IF NOT EXISTS FOR (d:Disclosure) ON (d.filingDate)"),
            ("disclosure_category_idx", "CREATE INDEX disclosure_category_idx IF NOT EXISTS FOR (d:Disclosure) ON (d.category)"),
            ("disclosure_corpcode_idx", "CREATE INDEX disclosure_corpcode_idx IF NOT EXISTS FOR (d:Disclosure) ON (d.corpCode)"),

            # Person 인덱스
            ("person_name_idx", "CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.name)"),
            ("person_persontype_idx", "CREATE INDEX person_persontype_idx IF NOT EXISTS FOR (p:Person) ON (p.personType)"),

            # RiskCategory 인덱스
            ("riskcategory_companyid_idx", "CREATE INDEX riskcategory_companyid_idx IF NOT EXISTS FOR (r:RiskCategory) ON (r.companyId)"),
            ("riskcategory_code_idx", "CREATE INDEX riskcategory_code_idx IF NOT EXISTS FOR (r:RiskCategory) ON (r.code)"),

            # RiskHistory 인덱스
            ("riskhistory_companyid_idx", "CREATE INDEX riskhistory_companyid_idx IF NOT EXISTS FOR (h:RiskHistory) ON (h.companyId)"),
            ("riskhistory_recordedat_idx", "CREATE INDEX riskhistory_recordedat_idx IF NOT EXISTS FOR (h:RiskHistory) ON (h.recordedAt)"),
        ]

        created = []
        with self.client.session() as session:
            for name, query in indexes:
                try:
                    session.run(query)
                    created.append(name)
                    logger.debug(f"인덱스 생성: {name}")
                except Exception as e:
                    logger.warning(f"인덱스 생성 실패 (이미 존재할 수 있음): {name} - {e}")

        return created

    def create_status_nodes(self) -> list[str]:
        """Status 노드 생성 (3개 고정)"""
        query = """
        MERGE (s:Status {id: $id})
        ON CREATE SET
            s.name = $name,
            s.minScore = $minScore,
            s.maxScore = $maxScore,
            s.color = $color,
            s.icon = $icon,
            s.description = $description,
            s.priority = $priority,
            s.createdAt = datetime()
        ON MATCH SET
            s.name = $name,
            s.minScore = $minScore,
            s.maxScore = $maxScore,
            s.color = $color,
            s.icon = $icon,
            s.description = $description,
            s.priority = $priority
        RETURN s.id as id
        """

        created = []
        with self.client.session() as session:
            for status in STATUS_DEFINITIONS:
                try:
                    result = session.run(query, status)
                    record = result.single()
                    if record:
                        created.append(record["id"])
                        logger.info(f"Status 노드 생성/업데이트: {record['id']}")
                except Exception as e:
                    logger.error(f"Status 노드 생성 실패: {status['id']} - {e}")

        return created


# =============================================================================
# 데이터 로더 함수
# =============================================================================

def create_company_status_relation(
    client: Neo4jClient,
    company_id: str,
    status_id: StatusId,
    score: int,
    breakdown: dict[str, int] | None = None,
) -> bool:
    """
    Company → Status 관계 생성/업데이트

    Args:
        client: Neo4j 클라이언트
        company_id: 기업 ID
        status_id: Status ID ("PASS", "WARNING", "FAIL")
        score: 리스크 점수
        breakdown: 카테고리별 점수 (선택)

    Returns:
        성공 여부
    """
    query = """
    MATCH (c:Company {id: $companyId})
    MATCH (s:Status {id: $statusId})

    // 기존 Status 관계 삭제
    OPTIONAL MATCH (c)-[old:IN_STATUS]->(:Status)
    DELETE old

    // 새 Status 관계 생성
    CREATE (c)-[r:IN_STATUS {
        score: $score,
        breakdown: $breakdown,
        changedAt: datetime(),
        reason: $reason
    }]->(s)

    // Company 노드 업데이트
    SET c.totalRiskScore = $score,
        c.riskLevel = $statusId,
        c.updatedAt = datetime()

    RETURN c.id as companyId, s.id as statusId
    """

    reason = f"Score {score} → {status_id}"
    breakdown_str = str(breakdown) if breakdown else "{}"

    try:
        with client.session() as session:
            result = session.run(query, {
                "companyId": company_id,
                "statusId": status_id,
                "score": score,
                "breakdown": breakdown_str,
                "reason": reason,
            })
            record = result.single()
            if record:
                logger.info(f"Company-Status 관계 생성: {record['companyId']} → {record['statusId']}")
                return True
    except Exception as e:
        logger.error(f"Company-Status 관계 생성 실패: {company_id} - {e}")

    return False


def create_risk_category_for_company(
    client: Neo4jClient,
    company_id: str,
    category_code: str,
    score: int,
    factors: list[str] | None = None,
) -> str | None:
    """
    Company에 대한 RiskCategory 노드 생성

    Args:
        client: Neo4j 클라이언트
        company_id: 기업 ID
        category_code: 카테고리 코드 (LEGAL, CREDIT, 등)
        score: 카테고리 점수
        factors: 점수 근거 목록

    Returns:
        생성된 RiskCategory ID 또는 None
    """
    category_info = RISK_CATEGORY_CODES.get(category_code)
    if not category_info:
        logger.warning(f"알 수 없는 카테고리 코드: {category_code}")
        return None

    category_id = f"RC_{company_id}_{category_code}"

    query = """
    MATCH (c:Company {id: $companyId})

    MERGE (rc:RiskCategory {id: $categoryId})
    ON CREATE SET
        rc.companyId = $companyId,
        rc.code = $categoryCode,
        rc.name = $name,
        rc.description = $description,
        rc.score = $score,
        rc.weight = $weight,
        rc.weightedScore = $score * $weight,
        rc.factors = $factors,
        rc.factorCount = size($factors),
        rc.source = 'CALCULATED',
        rc.calculatedAt = datetime(),
        rc.createdAt = datetime(),
        rc.updatedAt = datetime()
    ON MATCH SET
        rc.previousScore = rc.score,
        rc.score = $score,
        rc.weightedScore = $score * $weight,
        rc.factors = $factors,
        rc.factorCount = size($factors),
        rc.changeAmount = $score - rc.previousScore,
        rc.trend = CASE
            WHEN $score > rc.previousScore THEN 'UP'
            WHEN $score < rc.previousScore THEN 'DOWN'
            ELSE 'STABLE'
        END,
        rc.calculatedAt = datetime(),
        rc.updatedAt = datetime()

    MERGE (c)-[:HAS_RISK_CATEGORY]->(rc)

    RETURN rc.id as id
    """

    try:
        with client.session() as session:
            result = session.run(query, {
                "companyId": company_id,
                "categoryId": category_id,
                "categoryCode": category_code,
                "name": category_info["name"],
                "description": category_info["description"],
                "score": score,
                "weight": category_info["weight"],
                "factors": factors or [],
            })
            record = result.single()
            if record:
                logger.debug(f"RiskCategory 생성: {record['id']}")
                return record["id"]
    except Exception as e:
        logger.error(f"RiskCategory 생성 실패: {category_id} - {e}")

    return None


def create_risk_history(
    client: Neo4jClient,
    company_id: str,
    old_status: StatusId | None,
    new_status: StatusId,
    old_score: int,
    new_score: int,
    trigger_event: str | None = None,
) -> str | None:
    """
    RiskHistory 노드 생성 (변화 추적)

    Args:
        client: Neo4j 클라이언트
        company_id: 기업 ID
        old_status: 이전 Status
        new_status: 새 Status
        old_score: 이전 점수
        new_score: 새 점수
        trigger_event: 변화 트리거 이벤트

    Returns:
        생성된 RiskHistory ID 또는 None
    """
    history_id = f"RH_{company_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    query = """
    MATCH (c:Company {id: $companyId})

    CREATE (h:RiskHistory {
        id: $historyId,
        companyId: $companyId,
        oldStatus: $oldStatus,
        newStatus: $newStatus,
        oldScore: $oldScore,
        newScore: $newScore,
        scoreDelta: $newScore - $oldScore,
        triggerEvent: $triggerEvent,
        recordedAt: datetime()
    })

    CREATE (c)-[:HAS_HISTORY]->(h)

    RETURN h.id as id
    """

    try:
        with client.session() as session:
            result = session.run(query, {
                "companyId": company_id,
                "historyId": history_id,
                "oldStatus": old_status,
                "newStatus": new_status,
                "oldScore": old_score,
                "newScore": new_score,
                "triggerEvent": trigger_event,
            })
            record = result.single()
            if record:
                logger.info(f"RiskHistory 생성: {record['id']} ({old_status}→{new_status})")
                return record["id"]
    except Exception as e:
        logger.error(f"RiskHistory 생성 실패: {history_id} - {e}")

    return None


# =============================================================================
# CLI 인터페이스
# =============================================================================

def init_graph_v3(client: Neo4jClient | None = None) -> dict:
    """
    Graph v3 스키마 초기화 (CLI용)

    Args:
        client: Neo4j 클라이언트 (None이면 새로 생성)

    Returns:
        초기화 결과
    """
    if client is None:
        client = Neo4jClient()
        client.connect()

    schema = GraphSchemaV3(client)
    return schema.initialize_all()


def get_status_summary(client: Neo4jClient) -> dict:
    """
    Status별 기업 요약 조회

    Args:
        client: Neo4j 클라이언트

    Returns:
        Status별 기업 수 및 목록
    """
    query = """
    MATCH (s:Status)
    OPTIONAL MATCH (c:Company)-[:IN_STATUS]->(s)
    WITH s, collect({
        id: c.id,
        name: c.name,
        score: c.totalRiskScore
    }) as companies
    RETURN s.id as status, s.name as name, s.color as color,
           size([c IN companies WHERE c.id IS NOT NULL]) as count,
           [c IN companies WHERE c.id IS NOT NULL] as companies
    ORDER BY s.priority
    """

    try:
        with client.session() as session:
            result = session.run(query)
            summary = {}
            for record in result:
                summary[record["status"]] = {
                    "name": record["name"],
                    "color": record["color"],
                    "count": record["count"],
                    "companies": record["companies"],
                }
            return summary
    except Exception as e:
        logger.error(f"Status 요약 조회 실패: {e}")
        return {}


if __name__ == "__main__":
    # CLI 실행
    logging.basicConfig(level=logging.INFO)
    print("Graph v3 스키마 초기화 중...")
    result = init_graph_v3()
    print(f"완료: {result}")
