"""
PersonLinkingService - 인물 조회 (5-Node 스키마)
인물은 RiskEntity(type: PERSON/SHAREHOLDER) 노드
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PersonLinkingService:
    """인물 서비스 (5-Node: RiskEntity 기반)"""

    def __init__(self, neo4j_client):
        self.client = neo4j_client

    def get_persons_by_company(self, company_id: str) -> list[dict]:
        """기업의 인물 목록 조회 (RiskEntity type=PERSON/SHAREHOLDER)"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
              -[:HAS_ENTITY]->(re:RiskEntity)
        WHERE re.type IN ['PERSON', 'SHAREHOLDER']
        OPTIONAL MATCH (re)-[:HAS_EVENT]->(ev:RiskEvent)
        WITH re, rc,
             count(DISTINCT ev) AS eventCount
        RETURN re.id AS id,
               re.name AS name,
               coalesce(re.position, '') AS position,
               re.type AS type,
               coalesce(re.riskScore, 0) AS riskScore,
               CASE
                   WHEN coalesce(re.riskScore, 0) >= 50 THEN 'FAIL'
                   WHEN coalesce(re.riskScore, 0) >= 30 THEN 'WARNING'
                   ELSE 'PASS'
               END AS riskLevel,
               0 AS relatedNewsCount,
               eventCount AS relatedEventCount
        ORDER BY re.riskScore DESC
        """
        return self.client.execute_read(query, {"companyId": company_id})

    def get_person_detail(self, person_id: str) -> Optional[dict]:
        """인물 상세 조회 (RiskEntity → RiskEvent)"""
        query = """
        MATCH (re:RiskEntity {id: $personId})
        WHERE re.type IN ['PERSON', 'SHAREHOLDER']

        // 소속 카테고리/기업
        OPTIONAL MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)-[:HAS_ENTITY]->(re)

        // 관련 이벤트
        OPTIONAL MATCH (re)-[:HAS_EVENT]->(ev:RiskEvent)

        WITH re,
             collect(DISTINCT {
                 id: c.name,
                 name: c.name,
                 relationship: rc.code
             }) AS companies,
             collect(DISTINCT {
                 id: ev.id,
                 title: ev.title,
                 category: ev.type,
                 score: coalesce(ev.score, 0)
             }) AS events

        RETURN re.id AS id,
               re.name AS name,
               coalesce(re.position, '') AS position,
               re.type AS type,
               coalesce(re.riskScore, 0) AS riskScore,
               CASE
                   WHEN coalesce(re.riskScore, 0) >= 50 THEN 'FAIL'
                   WHEN coalesce(re.riskScore, 0) >= 30 THEN 'WARNING'
                   ELSE 'PASS'
               END AS riskLevel,
               companies,
               events,
               [] AS news
        """
        return self.client.execute_read_single(query, {"personId": person_id})
