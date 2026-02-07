"""
RiskEvent 서비스 - 5-Node 스키마 전용
경로: Company → RiskCategory → RiskEntity → RiskEvent
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EventService:
    """리스크 이벤트 서비스 (5-Node 스키마)"""

    def __init__(self, neo4j_client):
        self.client = neo4j_client

    def get_events_by_company(self, company_id: str) -> list[dict]:
        """기업의 모든 이벤트 조회 (5-Node 경로)"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
              -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
        RETURN ev.id AS id,
               ev.title AS title,
               rc.code AS category,
               ev.score AS score,
               ev.severity AS severity,
               ev.type AS type,
               ev.sourceName AS source,
               re.name AS entityName,
               re.type AS entityType,
               coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS firstDetectedAt
        ORDER BY ev.score DESC
        """
        return self.client.execute_read(query, {"companyId": company_id})

    def get_event_detail(self, event_id: str) -> Optional[dict]:
        """이벤트 상세 조회 (5-Node 경로 역추적)"""
        query = """
        MATCH (re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent {id: $eventId})
        OPTIONAL MATCH (rc:RiskCategory)-[:HAS_ENTITY]->(re)
        OPTIONAL MATCH (c:Company)-[:HAS_CATEGORY]->(rc)

        // 같은 엔티티의 다른 이벤트 (관련 뉴스/공시)
        OPTIONAL MATCH (re)-[:HAS_EVENT]->(related:RiskEvent)
        WHERE related.id <> $eventId

        WITH ev, re, rc, c,
             collect(DISTINCT {
                 id: related.id,
                 title: related.title,
                 rawScore: related.score,
                 url: '',
                 publishedAt: coalesce(toString(related.publishedAt), toString(related.createdAt), '')
             }) AS relatedEvents

        // 같은 카테고리의 PERSON 엔티티

        OPTIONAL MATCH (rc)-[:HAS_ENTITY]->(pe:RiskEntity)
        WHERE pe.type IN ['PERSON', 'SHAREHOLDER']

        WITH ev, re, rc, c, relatedEvents,
             collect(DISTINCT {
                 id: pe.id,
                 name: pe.name,
                 position: coalesce(pe.position, ''),
                 riskScore: coalesce(pe.riskScore, 0)
             }) AS persons

        RETURN ev.id AS id,
               ev.title AS title,
               coalesce(ev.summary, ev.title) AS description,
               rc.code AS category,
               ev.score AS score,
               ev.severity AS severity,
               [] AS matchedKeywords,
               persons,
               relatedEvents AS news,
               [] AS disclosures,
               coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS firstDetectedAt,
               true AS isActive
        """
        return self.client.execute_read_single(query, {"eventId": event_id})

    def get_events_by_category(self, company_id: str, category_code: str) -> list[dict]:
        """특정 카테고리의 이벤트 목록"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory {code: $code})
              -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
        RETURN ev.id AS id,
               ev.title AS title,
               rc.code AS category,
               ev.score AS score,
               ev.severity AS severity,
               ev.type AS type,
               re.name AS entityName,
               coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS firstDetectedAt
        ORDER BY ev.score DESC
        """
        return self.client.execute_read(query, {
            "companyId": company_id,
            "code": category_code,
        })

    def get_recent_events(self, company_id: str, limit: int = 10) -> list[dict]:
        """최근 이벤트 (시간순)"""
        query = """
        MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory)
              -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
        RETURN ev.id AS id,
               ev.title AS title,
               rc.code AS category,
               ev.score AS score,
               ev.severity AS severity,
               ev.type AS type,
               ev.sourceName AS source,
               re.name AS entityName,
               coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS firstDetectedAt
        ORDER BY ev.publishedAt DESC
        LIMIT $limit
        """
        return self.client.execute_read(query, {
            "companyId": company_id,
            "limit": limit,
        })
