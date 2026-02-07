"""
CategoryService - RiskCategory 노드 관리 (5-Node 스키마)
경로: Company → HAS_CATEGORY → RiskCategory → HAS_ENTITY → RiskEntity → HAS_EVENT → RiskEvent
"""

from __future__ import annotations
import logging
from typing import Optional

from ..schemas import CATEGORY_CONFIG, CategoryCode

logger = logging.getLogger(__name__)


class CategoryService:
    """리스크 카테고리 서비스 (5-Node 스키마)"""

    def __init__(self, neo4j_client):
        self.client = neo4j_client

    def get_categories_by_company(self, company_id: str) -> list[dict]:
        """기업의 모든 카테고리 조회"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
        OPTIONAL MATCH (rc)-[:HAS_ENTITY]->(re:RiskEntity)
        OPTIONAL MATCH (re)-[:HAS_EVENT]->(ev:RiskEvent)
        WITH rc,
             count(DISTINCT re) AS entityCount,
             count(DISTINCT ev) AS eventCount,
             count(DISTINCT CASE WHEN re.type IN ['PERSON','SHAREHOLDER'] THEN re END) AS personCount
        RETURN rc.code AS code, rc.name AS name, rc.icon AS icon,
               coalesce(rc.score, 0) AS score,
               coalesce(rc.weight, 0) AS weight,
               coalesce(rc.weightedScore, 0) AS weightedScore,
               entityCount, eventCount, personCount,
               coalesce(rc.trend, 'STABLE') AS trend
        ORDER BY rc.score DESC
        """
        return self.client.execute_read(query, {"companyId": company_id})

    def get_category_detail(self, company_id: str, category_code: str) -> Optional[dict]:
        """특정 카테고리 상세 조회 (5-Node: 엔티티 + 이벤트)"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory {code: $code})

        // 엔티티 (이벤트 역할)
        OPTIONAL MATCH (rc)-[:HAS_ENTITY]->(re:RiskEntity)
        WHERE NOT re.type IN ['PERSON', 'SHAREHOLDER']
        OPTIONAL MATCH (re)-[:HAS_EVENT]->(ev:RiskEvent)
        WITH rc, re,
             collect(DISTINCT {id: ev.id, title: ev.title, rawScore: ev.score, url: ''}) AS eventNews
        WITH rc,
             collect(DISTINCT {
                 id: re.id,
                 title: re.name,
                 score: coalesce(re.riskScore, 0),
                 severity: CASE
                     WHEN coalesce(re.riskScore, 0) >= 60 THEN 'CRITICAL'
                     WHEN coalesce(re.riskScore, 0) >= 40 THEN 'HIGH'
                     WHEN coalesce(re.riskScore, 0) >= 20 THEN 'MEDIUM'
                     ELSE 'LOW'
                 END,
                 newsCount: size(eventNews)
             }) AS events,
             reduce(allNews = [], en IN collect(eventNews) | allNews + en) AS flatNews

        // 인물 엔티티
        OPTIONAL MATCH (rc)-[:HAS_ENTITY]->(pe:RiskEntity)
        WHERE pe.type IN ['PERSON', 'SHAREHOLDER']
        WITH rc, events, flatNews,
             collect(DISTINCT {
                 id: pe.id,
                 name: pe.name,
                 position: coalesce(pe.position, ''),
                 riskScore: coalesce(pe.riskScore, 0)
             }) AS persons

        RETURN rc.code AS code, rc.name AS name, rc.icon AS icon,
               coalesce(rc.score, 0) AS score,
               coalesce(rc.weight, 0) AS weight,
               events, flatNews AS news, persons
        """
        return self.client.execute_read_single(query, {
            "companyId": company_id,
            "code": category_code,
        })

    def update_category_scores(self, company_id: str) -> dict[str, int]:
        """카테고리별 점수 계산 (5-Node: RiskEntity.riskScore 합산)"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
        OPTIONAL MATCH (rc)-[:HAS_ENTITY]->(re:RiskEntity)
        WITH rc,
             count(re) AS entityCount,
             sum(coalesce(re.riskScore, 0)) AS totalScore

        SET rc.previousScore = rc.score,
            rc.score = CASE WHEN totalScore > 100 THEN 100 ELSE toInteger(totalScore) END,
            rc.weightedScore = rc.score * rc.weight,
            rc.eventCount = entityCount,
            rc.trend = CASE
                WHEN rc.score > coalesce(rc.previousScore, 0) THEN 'UP'
                WHEN rc.score < coalesce(rc.previousScore, 0) THEN 'DOWN'
                ELSE 'STABLE'
            END,
            rc.updatedAt = datetime()

        RETURN rc.code AS code, rc.score AS score, rc.weightedScore AS weightedScore
        """
        results = self.client.execute_write_with_results(query, {"companyId": company_id})

        scores = {}
        for r in results:
            scores[r["code"]] = r["score"]

        logger.info(f"[{company_id}] 카테고리 점수 업데이트: {scores}")
        return scores
