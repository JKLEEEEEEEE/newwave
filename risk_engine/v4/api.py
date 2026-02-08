"""
Risk Engine V4 API
- 드릴다운 지원
- 완전한 데이터 연결
"""

from __future__ import annotations
import logging
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .schemas import (
    DealDetailResponse, DealDetail, CategorySummary, EventSummary, PersonSummary,
    EvidenceSummary, ScoreBreakdown, CategoryDetailResponse, CategoryDetail,
    EventDetailResponse, EventDetail, PersonDetailResponse, PersonDetail,
    NewsItem, DisclosureItem, CATEGORY_CONFIG
)
from .services import EventService, CategoryService, PersonLinkingService, ScoreService
from .pipelines import run_full_pipeline
from risk_engine.ai_service_v2 import AIServiceV2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v4", tags=["Risk V4"])

# Neo4j 클라이언트 (런타임에 설정)
_neo4j_client = None


def set_neo4j_client(client):
    """Neo4j 클라이언트 설정"""
    global _neo4j_client
    _neo4j_client = client


def get_client():
    """Neo4j 클라이언트 반환"""
    if _neo4j_client is None:
        raise HTTPException(status_code=500, detail="Neo4j client not initialized")
    return _neo4j_client


# =============================================================================
# Deal APIs
# =============================================================================

@router.get("/deals")
def get_deals():
    """딜 목록 조회 (카테고리 요약 포함) - def로 스레드풀 실행"""
    client = get_client()

    query = """
    MATCH (d:Deal)-[:TARGET]->(c:Company)
    OPTIONAL MATCH (c)-[:HAS_CATEGORY]->(rc:RiskCategory)
    WITH d, c,
         collect({code: rc.code, name: rc.name, icon: rc.icon, score: rc.score}) AS categories
    RETURN c.name AS id, c.name AS name, c.sector AS sector,
           c.totalRiskScore AS score, c.riskLevel AS riskLevel,
           categories
    """
    results = client.execute_read(query, {})

    deals = []
    for r in results:
        deals.append({
            "id": r["id"],
            "name": r["name"],
            "sector": r.get("sector", ""),
            "score": r.get("score", 0) or 0,
            "riskLevel": r.get("riskLevel", "PASS") or "PASS",
            "categories": [c for c in (r.get("categories") or []) if c.get("code")],
        })

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "deals": deals,
        "summary": {
            "total": len(deals),
            "pass": sum(1 for d in deals if d["riskLevel"] == "PASS"),
            "warning": sum(1 for d in deals if d["riskLevel"] == "WARNING"),
            "critical": sum(1 for d in deals if d["riskLevel"] == "CRITICAL"),
        }
    }


class CreateDealRequest(BaseModel):
    companyName: str
    sector: str = ""
    analyst: str = ""
    ticker: str = ""
    market: str = ""


@router.post("/deals")
def create_deal(req: CreateDealRequest):
    """딜 등록 + 자동 수집 트리거"""
    client = get_client()
    from risk_engine.deal_manager import DealService
    service = DealService(client)

    # 1. 딜 생성
    result = service.create_deal(req.companyName, req.sector, req.analyst, req.ticker, req.market)

    # 2. corpCode 자동 탐색
    corp_code = service.lookup_corp_code(req.companyName)

    # 3. 관련기업 자동 탐색 (corpCode가 있을 때만)
    related = []
    if corp_code:
        related = service.discover_related_companies(req.companyName)

    # 4. 백그라운드 수집 트리거
    import threading
    def _bg_collect():
        try:
            service.trigger_collection(result["dealId"])
        except Exception as e:
            logger.error(f"Background collection failed: {e}")

    threading.Thread(target=_bg_collect, daemon=True).start()

    return {
        "dealId": result["dealId"],
        "company": result,
        "corpCode": corp_code,
        "relatedCompanies": related,
        "collectionTriggered": True,
    }


@router.delete("/deals/{deal_id}")
def delete_deal(deal_id: str):
    """딜 삭제"""
    client = get_client()
    from risk_engine.deal_manager import DealService
    service = DealService(client)
    service.delete_deal(deal_id)
    return {"deleted": deal_id}


@router.post("/deals/{deal_id}/collect")
def trigger_collection(deal_id: str):
    """수동 수집 재실행"""
    client = get_client()
    from risk_engine.deal_manager import DealService
    service = DealService(client)
    result = service.trigger_collection(deal_id)
    return result


@router.get("/deals/{deal_id}", response_model=DealDetailResponse)
def get_deal_detail(deal_id: str):
    """딜 상세 조회 (전체 드릴다운 데이터) - def로 스레드풀 실행 (이벤트루프 블로킹 방지)"""
    client = get_client()

    # 기본 정보 조회
    base_query = """
    MATCH (c:Company {name: $dealId})
    RETURN c.name AS id, c.name AS name, c.sector AS sector,
           c.totalRiskScore AS score, c.riskLevel AS riskLevel,
           c.directScore AS directScore, c.propagatedScore AS propagatedScore,
           c.riskTrend AS trend
    """
    base = client.execute_read_single(base_query, {"dealId": deal_id})
    if not base:
        raise HTTPException(status_code=404, detail=f"Deal not found: {deal_id}")

    # 카테고리 조회
    category_service = CategoryService(client)
    categories_raw = category_service.get_categories_by_company(deal_id)
    categories = [
        CategorySummary(
            code=c["code"],
            name=c["name"],
            icon=c["icon"],
            score=c.get("score", 0) or 0,
            weight=c.get("weight", 0) or 0,
            weightedScore=c.get("weightedScore", 0) or 0,
            eventCount=c.get("eventCount", 0) or 0,
            personCount=c.get("personCount", 0) or 0,
            trend=c.get("trend", "STABLE") or "STABLE",
        )
        for c in categories_raw
    ]

    # 이벤트 조회 (Top 5)
    event_service = EventService(client)
    events_raw = event_service.get_events_by_company(deal_id)[:5]
    top_events = [
        EventSummary(
            id=e["id"],
            title=e["title"],
            category=e.get("category") or "OTHER",
            score=int(e.get("score", 0) or 0),
            severity=e.get("severity") or "MEDIUM",
            type=e.get("type") or "NEWS",
            source=e.get("source") or "",
            newsCount=int(e.get("newsCount", 0) or 0),
            disclosureCount=int(e.get("disclosureCount", 0) or 0),
            firstDetectedAt=e.get("firstDetectedAt") or "",
        )
        for e in events_raw
    ]

    # 인물 조회 (Top 5)
    person_service = PersonLinkingService(client)
    persons_raw = person_service.get_persons_by_company(deal_id)[:5]
    top_persons = [
        PersonSummary(
            id=p["id"],
            name=p["name"],
            position=p.get("position") or "",
            type=p.get("type") or "EXECUTIVE",
            riskScore=int(p.get("riskScore", 0) or 0),
            relatedNewsCount=int(p.get("relatedNewsCount", 0) or 0),
            relatedEventCount=int(p.get("relatedEventCount", 0) or 0),
        )
        for p in persons_raw
    ]

    # 최근 이벤트 (최신 10개)
    recent_events_raw = event_service.get_recent_events(deal_id, limit=10)
    recent_events = [
        EventSummary(
            id=e["id"],
            title=e["title"],
            category=e.get("category") or "OTHER",
            score=int(e.get("score", 0) or 0),
            severity=e.get("severity") or "MEDIUM",
            type=e.get("type") or "NEWS",
            source=e.get("source") or "",
            newsCount=int(e.get("newsCount", 0) or 0),
            disclosureCount=int(e.get("disclosureCount", 0) or 0),
            firstDetectedAt=e.get("firstDetectedAt") or "",
        )
        for e in recent_events_raw
    ]

    # 증거 요약
    score_service = ScoreService(client)
    evidence_raw = score_service.get_score_evidence(deal_id)
    evidence = EvidenceSummary(
        totalNews=evidence_raw.get("totalNews", 0),
        totalDisclosures=evidence_raw.get("totalDisclosures", 0),
        topFactors=evidence_raw.get("topFactors", []),
    )

    return DealDetailResponse(
        schemaVersion="v4",
        generatedAt=datetime.now().isoformat(),
        deal=DealDetail(
            id=base["id"],
            name=base["name"],
            sector=base.get("sector", ""),
            score=base.get("score", 0) or 0,
            riskLevel=base.get("riskLevel", "PASS") or "PASS",
            breakdown=ScoreBreakdown(
                direct=base.get("directScore", 0) or 0,
                propagated=base.get("propagatedScore", 0) or 0,
            ),
            trend=base.get("trend", "STABLE") or "STABLE",
            categories=categories,
            topEvents=top_events,
            topPersons=top_persons,
            recentEvents=recent_events,
            evidence=evidence,
            lastUpdated=datetime.now().isoformat(),
        )
    )


# =============================================================================
# Category APIs
# =============================================================================

@router.get("/deals/{deal_id}/categories")
async def get_deal_categories(deal_id: str):
    """카테고리 목록 조회"""
    client = get_client()
    category_service = CategoryService(client)
    categories = category_service.get_categories_by_company(deal_id)

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "categories": categories,
    }


@router.get("/deals/{deal_id}/categories/{category_code}", response_model=CategoryDetailResponse)
def get_category_detail(deal_id: str, category_code: str):
    """카테고리 상세 조회"""
    client = get_client()
    category_service = CategoryService(client)

    detail = category_service.get_category_detail(deal_id, category_code)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Category not found: {category_code}")

    # 이벤트 변환
    events = [
        EventSummary(
            id=e["id"],
            title=e["title"],
            category=category_code,
            score=e.get("score", 0) or 0,
            severity=e.get("severity", "MEDIUM"),
            newsCount=e.get("newsCount", 0) or 0,
            disclosureCount=0,
            firstDetectedAt="",
        )
        for e in (detail.get("events") or []) if e.get("id")
    ]

    # 인물 변환
    persons = [
        PersonSummary(
            id=p["id"],
            name=p["name"],
            position=p.get("position") or "",
            type="EXECUTIVE",
            riskScore=p.get("riskScore", 0) or 0,
            relatedNewsCount=0,
            relatedEventCount=0,
        )
        for p in (detail.get("persons") or []) if p.get("id")
    ]

    # 뉴스 변환 (5-Node: 이벤트가 뉴스 역할)
    news = [
        NewsItem(
            id=n.get("id") or "",
            title=n.get("title") or "",
            source="",
            publishedAt="",
            rawScore=round(n.get("rawScore", 0) or 0),
            sentiment="NEUTRAL",
            url=n.get("url") or "",
        )
        for n in (detail.get("news") or []) if n.get("id")
    ]

    return CategoryDetailResponse(
        schemaVersion="v4",
        generatedAt=datetime.now().isoformat(),
        category=CategoryDetail(
            code=detail["code"],
            name=detail["name"],
            icon=detail["icon"],
            score=detail.get("score", 0) or 0,
            weight=detail.get("weight", 0) or 0,
            events=events,
            persons=persons,
            news=news,
            disclosures=[],
        )
    )


# =============================================================================
# Event APIs
# =============================================================================

@router.get("/deals/{deal_id}/events")
async def get_deal_events(deal_id: str):
    """이벤트 목록 조회"""
    client = get_client()
    event_service = EventService(client)
    events = event_service.get_events_by_company(deal_id)

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "events": events,
    }


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event_detail(event_id: str):
    """이벤트 상세 조회"""
    client = get_client()
    event_service = EventService(client)

    detail = event_service.get_event_detail(event_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")

    # 뉴스 변환
    news = [
        NewsItem(
            id=n["id"],
            title=n["title"],
            source="",
            publishedAt=n.get("publishedAt", ""),
            rawScore=n.get("rawScore", 0) or 0,
            sentiment="NEUTRAL",
            url=n.get("url", ""),
        )
        for n in (detail.get("news") or []) if n.get("id")
    ]

    # 공시 변환
    disclosures = [
        DisclosureItem(
            id=d["id"],
            title=d["title"],
            filingDate=d.get("filingDate", ""),
            rawScore=d.get("rawScore", 0) or 0,
            category="",
            url=d.get("url", ""),
        )
        for d in (detail.get("disclosures") or []) if d.get("id")
    ]

    # 인물 변환
    persons = [
        PersonSummary(
            id=p["id"],
            name=p["name"],
            position=p.get("position") or "",
            type="EXECUTIVE",
            riskScore=p.get("riskScore", 0) or 0,
            relatedNewsCount=0,
            relatedEventCount=0,
        )
        for p in (detail.get("persons") or []) if p.get("id")
    ]

    return EventDetailResponse(
        schemaVersion="v4",
        generatedAt=datetime.now().isoformat(),
        event=EventDetail(
            id=detail["id"],
            title=detail["title"],
            description=detail.get("description", ""),
            category=detail.get("category", "OTHER"),
            score=detail.get("score", 0) or 0,
            severity=detail.get("severity", "MEDIUM"),
            matchedKeywords=detail.get("matchedKeywords", []),
            involvedPersons=persons,
            news=news,
            disclosures=disclosures,
            firstDetectedAt=detail.get("firstDetectedAt", ""),
            isActive=detail.get("isActive", True),
        )
    )


# =============================================================================
# Person APIs
# =============================================================================

@router.get("/deals/{deal_id}/persons")
async def get_deal_persons(deal_id: str):
    """인물 목록 조회"""
    client = get_client()
    person_service = PersonLinkingService(client)
    persons = person_service.get_persons_by_company(deal_id)

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "persons": persons,
    }


@router.get("/persons/{person_id}", response_model=PersonDetailResponse)
async def get_person_detail(person_id: str):
    """인물 상세 조회"""
    try:
        client = get_client()
        person_service = PersonLinkingService(client)

        detail = person_service.get_person_detail(person_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"Person not found: {person_id}")

        # 뉴스 변환
        news = [
            NewsItem(
                id=n["id"],
                title=n["title"],
                source="",
                publishedAt=n.get("publishedAt") or "",
                rawScore=n.get("rawScore", 0) or 0,
                sentiment="NEUTRAL",
                url=n.get("url") or "",
            )
            for n in (detail.get("news") or []) if n.get("id")
        ]

        # 이벤트 변환
        events = [
            EventSummary(
                id=e["id"],
                title=e["title"],
                category=e.get("category") or "OTHER",
                score=e.get("score", 0) or 0,
                severity="MEDIUM",
                newsCount=0,
                disclosureCount=0,
                firstDetectedAt="",
            )
            for e in (detail.get("events") or []) if e.get("id")
        ]

        # companies에서 null 값 필터링
        companies_raw = detail.get("companies", []) or []
        companies = [c for c in companies_raw if c.get("id")]

        return PersonDetailResponse(
            schemaVersion="v4",
            generatedAt=datetime.now().isoformat(),
            person=PersonDetail(
                id=detail["id"],
                name=detail["name"],
                position=detail.get("position") or "",
                type=detail.get("type") or "EXECUTIVE",
                tier=2,
                riskScore=detail.get("riskScore", 0) or 0,
                riskLevel=detail.get("riskLevel", "PASS") or "PASS",
                riskFactors=[],
                companies=companies,
                involvedEvents=events,
                relatedNews=news,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Person detail error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Pipeline APIs
# =============================================================================

@router.post("/pipeline/run/{company_id}")
async def run_pipeline(company_id: str):
    """리스크 계산 파이프라인 실행"""
    client = get_client()
    result = run_full_pipeline(client, company_id)
    return result


@router.get("/deals/{deal_id}/evidence")
async def get_deal_evidence(deal_id: str):
    """증거 목록 조회 (5-Node: RiskEvent 기반)"""
    client = get_client()

    # 뉴스형 이벤트 조회
    news_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    WHERE ev.type = 'NEWS' AND ev.score > 0
    RETURN ev.id AS id, ev.title AS title, ev.score AS rawScore,
           '' AS url, toString(ev.createdAt) AS publishedAt
    ORDER BY ev.score DESC
    LIMIT 20
    """
    news = client.execute_read(news_query, {"dealId": deal_id})

    # 공시형 이벤트 조회
    disc_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    WHERE ev.type = 'DISCLOSURE' AND ev.score > 0
    RETURN ev.id AS id, ev.title AS title, ev.score AS rawScore,
           '' AS url, toString(ev.createdAt) AS filingDate
    ORDER BY ev.score DESC
    LIMIT 20
    """
    disclosures = client.execute_read(disc_query, {"dealId": deal_id})

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "news": news,
        "disclosures": disclosures,
    }


# =============================================================================
# Graph API
# =============================================================================

@router.get("/deals/{deal_id}/graph")
async def get_deal_graph(deal_id: str):
    """딜 기반 그래프 데이터 조회 (프론트엔드 3D 그래프용)"""
    client = get_client()

    nodes = []
    links = []

    # 1. Deal 노드
    deal_query = """
    MATCH (d:Deal)-[:TARGET]->(c:Company {name: $dealId})
    RETURN d.name AS dealName, c.name AS companyName
    """
    deal_result = client.execute_read_single(deal_query, {"dealId": deal_id})

    deal_name = deal_result["dealName"] if deal_result else f"{deal_id} 검토"

    nodes.append({
        "id": f"DEAL_{deal_id}",
        "name": deal_name,
        "nodeType": "deal",
        "riskScore": 0,
        "riskLevel": "PASS",
        "tier": 0,
        "metadata": {},
    })

    # 2. 메인 기업 노드
    company_query = """
    MATCH (c:Company {name: $dealId})
    RETURN c.name AS name, c.totalRiskScore AS score, c.riskLevel AS riskLevel,
           c.sector AS sector, c.directScore AS directScore,
           c.propagatedScore AS propagatedScore,
           c.ticker AS ticker, c.market AS market, c.corpCode AS corpCode
    """
    company = client.execute_read_single(company_query, {"dealId": deal_id})
    if not company:
        return {"nodes": nodes, "links": links}

    score = company.get("score", 0) or 0
    risk_level = company.get("riskLevel", "PASS") or "PASS"

    nodes.append({
        "id": deal_id,
        "name": company["name"],
        "nodeType": "mainCompany",
        "riskScore": score,
        "riskLevel": risk_level,
        "tier": 1,
        "selectionReason": f"투자 대상 기업 (직접점수: {company.get('directScore', 0) or 0}, 전이점수: {company.get('propagatedScore', 0) or 0})",
        "metadata": {
            "sector": company.get("sector", ""),
            "ticker": company.get("ticker", ""),
            "market": company.get("market", ""),
            "corpCode": company.get("corpCode", ""),
            "directScore": company.get("directScore", 0) or 0,
            "propagatedScore": company.get("propagatedScore", 0) or 0,
        },
    })

    links.append({
        "source": f"DEAL_{deal_id}",
        "target": deal_id,
        "relationship": "TARGET",
        "dependency": 1.0,
        "label": "투자대상",
        "riskTransfer": 0,
    })

    # 3. 카테고리 노드 (점수 있는 것만)
    cat_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)
    WHERE rc.score > 0
    RETURN rc.code AS code, rc.name AS name, rc.score AS score,
           rc.weight AS weight, rc.weightedScore AS weightedScore,
           rc.eventCount AS eventCount
    """
    categories = client.execute_read(cat_query, {"dealId": deal_id}) or []
    for cat in categories:
        cat_id = f"RC_{deal_id}_{cat['code']}"
        cat_score = cat.get("score", 0) or 0
        weighted = cat.get("weightedScore", 0) or 0
        cat_level = "CRITICAL" if weighted >= 15 else ("WARNING" if weighted >= 5 else "PASS")

        nodes.append({
            "id": cat_id,
            "name": cat["name"],
            "nodeType": "riskCategory",
            "riskScore": cat_score,
            "riskLevel": cat_level,
            "tier": 2,
            "categoryCode": cat["code"],
            "selectionReason": f"가중점수 {weighted:.1f} (원점수 {cat_score} x 가중치 {cat.get('weight', 0) or 0})",
            "metadata": {"weight": cat.get("weight", 0), "weightedScore": weighted},
        })

        links.append({
            "source": deal_id,
            "target": cat_id,
            "relationship": "HAS_CATEGORY",
            "dependency": cat.get("weight", 0) or 0,
            "label": cat["name"],
            "riskTransfer": weighted,
        })

    # 4. 메인기업 RiskEntity 노드
    entity_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)-[:HAS_ENTITY]->(re:RiskEntity)
    WHERE rc.score > 0
    RETURN re.name AS name, re.type AS type, re.riskScore AS score,
           rc.code AS catCode, rc.name AS catName,
           re.position AS position, re.description AS description
    """
    entities = client.execute_read(entity_query, {"dealId": deal_id}) or []
    entity_ids_seen = set()
    for ent in entities:
        ent_name = ent.get("name", "Unknown")
        ent_cat = ent.get("catCode", "OTHER")
        ent_id = f"RE_{deal_id}_{ent_cat}_{ent_name}"
        if ent_id in entity_ids_seen:
            continue
        entity_ids_seen.add(ent_id)
        ent_score = ent.get("score", 0) or 0
        ent_level = "CRITICAL" if ent_score >= 30 else ("WARNING" if ent_score >= 10 else "PASS")

        nodes.append({
            "id": ent_id,
            "name": ent_name,
            "nodeType": "riskEntity",
            "riskScore": ent_score,
            "riskLevel": ent_level,
            "tier": 3,
            "selectionReason": f"{ent.get('catName', ent_cat)} 카테고리 내 {ent.get('type', 'ENTITY')}",
            "metadata": {
                "type": ent.get("type", ""),
                "position": ent.get("position", ""),
                "categoryCode": ent_cat,
                "description": ent.get("description", ""),
            },
        })

        cat_id = f"RC_{deal_id}_{ent_cat}"
        links.append({
            "source": cat_id,
            "target": ent_id,
            "relationship": "HAS_ENTITY",
            "dependency": 0.5,
            "label": ent.get("type", "ENTITY"),
            "riskTransfer": ent_score,
        })

    # 5. 관련기업 노드
    related_query = """
    MATCH (c:Company {name: $dealId})-[r:HAS_RELATED]->(rc:Company)
    RETURN rc.name AS name, rc.totalRiskScore AS score, rc.riskLevel AS riskLevel,
           rc.sector AS sector, r.relation AS relation, r.tier AS tier,
           rc.ticker AS ticker, rc.market AS market,
           rc.directScore AS directScore, rc.totalRiskScore AS totalRiskScore
    """
    related = client.execute_read(related_query, {"dealId": deal_id}) or []

    # 공급망 관계도 확인
    supply_query = """
    MATCH (c1:Company {name: $dealId})-[r:SUPPLIES_TO|COMPETES_WITH]-(c2:Company)
    RETURN c2.name AS name, c2.totalRiskScore AS score, c2.riskLevel AS riskLevel,
           c2.sector AS sector, type(r) AS relation
    """
    supply_related = client.execute_read(supply_query, {"dealId": deal_id}) or []

    all_related = {}
    for r in related:
        all_related[r["name"]] = r
    for r in supply_related:
        if r["name"] not in all_related:
            r["tier"] = 2
            all_related[r["name"]] = r

    for name, rel in all_related.items():
        rel_score = rel.get("score", 0) or 0
        rel_level = rel.get("riskLevel", "PASS") or "PASS"
        rel_tier = rel.get("tier", 1) or 1
        relation_type = rel.get("relation", "관련사") or "관련사"

        nodes.append({
            "id": name,
            "name": name,
            "nodeType": "relatedCompany",
            "riskScore": rel_score,
            "riskLevel": rel_level,
            "tier": rel_tier,
            "selectionReason": f"{relation_type} 관계, 리스크 전이율 {round(rel_score * 0.3)}점",
            "metadata": {
                "relation": relation_type,
                "sector": rel.get("sector", ""),
                "ticker": rel.get("ticker", ""),
                "market": rel.get("market", ""),
                "directScore": rel.get("directScore", 0) or 0,
                "tier": rel_tier,
                "transferRate": 0.3 if rel_tier == 1 else 0.1,
            },
        })

        links.append({
            "source": deal_id,
            "target": name,
            "relationship": "HAS_RELATED",
            "dependency": 0.3 if rel_tier == 1 else 0.1,
            "label": relation_type,
            "riskTransfer": round(rel_score * 0.3) if rel_tier == 1 else round(rel_score * 0.1),
        })

    # 6. 관련기업의 카테고리 + 엔티티 노드
    for rel_name in all_related.keys():
        # 관련기업 카테고리
        rel_cat_query = """
        MATCH (c:Company {name: $companyName})-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE rc.score > 0
        RETURN rc.code AS code, rc.name AS name, rc.score AS score,
               rc.weight AS weight, rc.weightedScore AS weightedScore
        """
        rel_cats = client.execute_read(rel_cat_query, {"companyName": rel_name}) or []
        for rcat in rel_cats:
            rcat_id = f"RC_{rel_name}_{rcat['code']}"
            rcat_score = rcat.get("score", 0) or 0
            rcat_weighted = rcat.get("weightedScore", 0) or 0
            rcat_level = "CRITICAL" if rcat_weighted >= 15 else ("WARNING" if rcat_weighted >= 5 else "PASS")

            nodes.append({
                "id": rcat_id,
                "name": rcat["name"],
                "nodeType": "riskCategory",
                "riskScore": rcat_score,
                "riskLevel": rcat_level,
                "tier": 2,
                "categoryCode": rcat["code"],
                "metadata": {"weight": rcat.get("weight", 0), "weightedScore": rcat_weighted, "company": rel_name},
            })

            links.append({
                "source": rel_name,
                "target": rcat_id,
                "relationship": "HAS_CATEGORY",
                "dependency": rcat.get("weight", 0) or 0,
                "label": rcat["name"],
                "riskTransfer": rcat_weighted,
            })

        # 관련기업 엔티티
        rel_ent_query = """
        MATCH (c:Company {name: $companyName})-[:HAS_CATEGORY]->(rc:RiskCategory)-[:HAS_ENTITY]->(re:RiskEntity)
        WHERE rc.score > 0
        RETURN re.name AS name, re.type AS type, re.riskScore AS score,
               rc.code AS catCode, rc.name AS catName
        """
        rel_ents = client.execute_read(rel_ent_query, {"companyName": rel_name}) or []
        for rent in rel_ents:
            rent_name = rent.get("name", "Unknown")
            rent_cat = rent.get("catCode", "OTHER")
            rent_id = f"RE_{rel_name}_{rent_cat}_{rent_name}"
            if rent_id in entity_ids_seen:
                continue
            entity_ids_seen.add(rent_id)
            rent_score = rent.get("score", 0) or 0
            rent_level = "CRITICAL" if rent_score >= 30 else ("WARNING" if rent_score >= 10 else "PASS")

            nodes.append({
                "id": rent_id,
                "name": rent_name,
                "nodeType": "riskEntity",
                "riskScore": rent_score,
                "riskLevel": rent_level,
                "tier": 3,
                "metadata": {"type": rent.get("type", ""), "categoryCode": rent_cat, "company": rel_name},
            })

            rcat_id = f"RC_{rel_name}_{rent_cat}"
            links.append({
                "source": rcat_id,
                "target": rent_id,
                "relationship": "HAS_ENTITY",
                "dependency": 0.5,
                "label": rent.get("type", "ENTITY"),
                "riskTransfer": rent_score,
            })

    # 7. 주요 RiskEvent 노드 (score >= 20, 최대 20개)
    event_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    WHERE ev.score >= 20
    RETURN ev.id AS id, ev.title AS title, ev.score AS score,
           ev.type AS type, ev.severity AS severity,
           ev.sourceUrl AS sourceUrl, ev.sourceName AS sourceName,
           re.name AS entityName, rc.code AS catCode, rc.name AS catName
    ORDER BY ev.score DESC
    LIMIT 20
    """
    events = client.execute_read(event_query, {"dealId": deal_id}) or []
    event_ids_seen = set()
    for evt in events:
        evt_id = evt.get("id", "")
        if not evt_id or evt_id in event_ids_seen:
            continue
        event_ids_seen.add(evt_id)
        evt_score = evt.get("score", 0) or 0
        evt_level = "CRITICAL" if evt_score >= 50 else ("WARNING" if evt_score >= 20 else "PASS")

        nodes.append({
            "id": evt_id,
            "name": (evt.get("title", "")[:30] + "...") if len(evt.get("title", "")) > 30 else evt.get("title", ""),
            "nodeType": "riskEvent",
            "riskScore": evt_score,
            "riskLevel": evt_level,
            "tier": 4,
            "selectionReason": f"{evt.get('catName', '')} > {evt.get('entityName', '')}에서 발생",
            "metadata": {
                "type": evt.get("type", ""),
                "severity": evt.get("severity", ""),
                "sourceUrl": evt.get("sourceUrl", ""),
                "sourceName": evt.get("sourceName", ""),
                "entityName": evt.get("entityName", ""),
                "categoryCode": evt.get("catCode", ""),
                "fullTitle": evt.get("title", ""),
            },
        })

        # Link: Entity → Event
        ent_id = f"RE_{deal_id}_{evt.get('catCode', 'OTHER')}_{evt.get('entityName', '')}"
        if ent_id in entity_ids_seen:
            links.append({
                "source": ent_id,
                "target": evt_id,
                "relationship": "HAS_EVENT",
                "dependency": 0.3,
                "label": evt.get("type", "EVENT"),
                "riskTransfer": evt_score,
            })

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "nodes": nodes,
        "links": links,
    }


# =============================================================================
# Risk Drivers API
# =============================================================================

@router.get("/deals/{deal_id}/drivers")
def get_risk_drivers(deal_id: str):
    """리스크 기여도 Top Drivers 반환"""
    client = get_client()

    # 기업 기본 정보
    company_query = """
    MATCH (c:Company {name: $dealId})
    RETURN c.name AS name, c.totalRiskScore AS totalScore,
           c.directScore AS directScore, c.propagatedScore AS propagatedScore,
           c.riskLevel AS riskLevel
    """
    company = client.execute_read_single(company_query, {"dealId": deal_id})
    if not company:
        raise HTTPException(status_code=404, detail=f"Company not found: {deal_id}")

    # 카테고리별 점수
    category_service = CategoryService(client)
    categories = category_service.get_categories_by_company(deal_id)

    total_score = company.get("totalScore", 0) or 0
    direct_score = company.get("directScore", 0) or 0

    # 기여도 계산: weightedScore / directScore * 100
    drivers = []
    for cat in sorted(categories, key=lambda c: c.get("weightedScore", 0) or 0, reverse=True):
        weighted = cat.get("weightedScore", 0) or 0
        contribution = round(weighted / direct_score * 100, 1) if direct_score > 0 else 0
        drivers.append({
            "categoryCode": cat["code"],
            "categoryName": cat["name"],
            "categoryIcon": cat.get("icon", ""),
            "score": cat.get("score", 0) or 0,
            "weight": cat.get("weight", 0) or 0,
            "weightedScore": weighted,
            "contribution": contribution,
            "eventCount": cat.get("eventCount", 0) or 0,
            "isPropagated": False,
        })

    # 관련기업 전이 점수
    related_query = """
    MATCH (c:Company {name: $dealId})-[r:HAS_RELATED]->(rc:Company)
    RETURN rc.name AS name, rc.totalRiskScore AS score,
           coalesce(r.tier, 1) AS tier, coalesce(r.relation, '관련사') AS relation
    """
    related = client.execute_read(related_query, {"dealId": deal_id}) or []
    for rel in related:
        rel_score = rel.get("score", 0) or 0
        tier = rel.get("tier", 1) or 1
        rate = 0.3 if tier == 1 else 0.1
        transfer = round(rel_score * rate)
        if transfer > 0:
            contribution = round(transfer / total_score * 100, 1) if total_score > 0 else 0
            drivers.append({
                "categoryCode": "PROPAGATED",
                "categoryName": f"{rel['name']} 전이",
                "categoryIcon": "",
                "score": rel_score,
                "weight": rate,
                "weightedScore": transfer,
                "contribution": contribution,
                "eventCount": 0,
                "isPropagated": True,
            })

    # 기여도 기준 정렬
    drivers.sort(key=lambda d: d["weightedScore"], reverse=True)

    return {
        "companyName": company["name"],
        "totalScore": total_score,
        "directScore": direct_score,
        "propagatedScore": company.get("propagatedScore", 0) or 0,
        "riskLevel": company.get("riskLevel", "PASS") or "PASS",
        "topDrivers": drivers[:3],
        "allDrivers": drivers,
    }


@router.get("/deals/{deal_id}/briefing")
def get_deal_briefing(deal_id: str):
    """딜 대상 AI 브리핑 생성"""
    client = get_client()

    # 1. 기본 기업 정보
    company_query = """
    MATCH (c:Company {name: $dealId})
    RETURN c.name AS name, c.sector AS sector,
           c.totalRiskScore AS totalScore, c.riskLevel AS riskLevel
    """
    company = client.execute_read(company_query, {"dealId": deal_id})
    if not company:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    company = company[0]

    # 2. 카테고리 점수
    category_service = CategoryService(client)
    categories = category_service.get_categories_by_company(deal_id)
    category_scores = {cat["code"]: {"score": cat.get("score",0), "weight": cat.get("weight",0), "weightedScore": cat.get("weightedScore",0)} for cat in categories}

    # 3. 증거
    score_service = ScoreService(client)
    evidence = score_service.get_score_evidence(deal_id)

    # 4. 최근 신호 (뉴스/공시)
    signals_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    WHERE ev.type IN ['NEWS', 'DISCLOSURE']
    RETURN ev.type AS type, rc.code AS category, ev.title AS title,
           coalesce(ev.score, 0) AS score, coalesce(ev.date, '') AS date
    ORDER BY ev.date DESC LIMIT 20
    """
    signals_raw = client.execute_read(signals_query, {"dealId": deal_id}) or []
    signals = [{"type": s["type"].lower(), "category": s["category"], "title": s["title"], "score": s["score"], "date": s["date"]} for s in signals_raw]

    # 5. 임원/주주
    persons_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)
    WHERE re.type IN ['PERSON', 'SHAREHOLDER']
    RETURN DISTINCT re.name AS name, re.position AS position, re.type AS type
    LIMIT 10
    """
    persons_raw = client.execute_read(persons_query, {"dealId": deal_id}) or []
    executives = [{"name": p["name"], "position": p["position"]} for p in persons_raw if p.get("position")]
    shareholders = [{"name": p["name"], "shareRatio": 0.0} for p in persons_raw if p["type"] == "SHAREHOLDER"]

    # 6. 관련 기업
    related_query = """
    MATCH (c:Company {name: $dealId})-[r:HAS_RELATED]->(rc:Company)
    RETURN rc.name AS name, coalesce(r.relation, 'RELATED') AS relation
    LIMIT 10
    """
    related_raw = client.execute_read(related_query, {"dealId": deal_id}) or []
    related_companies = [{"name": r["name"], "relation": r["relation"]} for r in related_raw]

    # 7. deal_context 조립 + AI 호출
    deal_context = {
        "company": company["name"],
        "sector": company.get("sector", ""),
        "riskScore": company.get("totalScore", 0) or 0,
        "riskLevel": company.get("riskLevel", "PASS") or "PASS",
        "signals": signals,
        "executives": executives,
        "shareholders": shareholders,
        "relatedCompanies": related_companies,
        "categoryScores": category_scores,
    }

    ai_service = AIServiceV2()
    try:
        insight = ai_service.generate_comprehensive_insight(deal_context)
    except Exception as e:
        logger.warning(f"AI briefing 생성 실패: {e}")
        insight = {
            "executive_summary": f"{company['name']}에 대한 분석 데이터가 부족합니다.",
            "context_analysis": {"industry_context": "", "timing_significance": ""},
            "cross_signal_analysis": {"patterns_detected": [], "correlations": "", "anomalies": ""},
            "stakeholder_insights": {"executive_concerns": "", "shareholder_dynamics": ""},
            "key_concerns": [],
            "recommendations": {"immediate_actions": [], "monitoring_focus": [], "due_diligence_points": []},
            "confidence": 0.3,
            "analysis_limitations": "AI 서비스 호출 실패",
        }

    return {
        "company": company["name"],
        "riskScore": company.get("totalScore", 0) or 0,
        "riskLevel": company.get("riskLevel", "PASS") or "PASS",
        "executive_summary": insight.get("executive_summary", ""),
        "context_analysis": insight.get("context_analysis", {}),
        "cross_signal_analysis": insight.get("cross_signal_analysis", {}),
        "stakeholder_insights": insight.get("stakeholder_insights", {}),
        "key_concerns": insight.get("key_concerns", []),
        "recommendations": insight.get("recommendations", {}),
        "confidence": insight.get("confidence", 0),
        "analysis_limitations": insight.get("analysis_limitations", ""),
        "dataSources": {
            "newsCount": evidence.get("totalNews", 0),
            "disclosureCount": evidence.get("totalDisclosures", 0),
            "relatedCompanyCount": len(related_companies),
            "categoryCount": len(categories),
        },
    }


# =============================================================================
# Global Critical Alerts API
# =============================================================================

@router.get("/alerts/critical")
def get_critical_alerts(limit: int = 50):
    """전체 딜 대상 CRITICAL 이벤트 조회 (네비게이션 바 알림용)"""
    client = get_client()

    # 모든 딜의 메인기업 + 관련기업에서 고위험 이벤트 조회
    query = """
    MATCH (d:Deal)-[:TARGET]->(c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    WHERE ev.score >= 60
    RETURN ev.id AS id, ev.title AS title, ev.summary AS summary,
           ev.type AS type, ev.score AS score, ev.severity AS severity,
           ev.sourceName AS sourceName, ev.sourceUrl AS sourceUrl,
           coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS publishedAt,
           rc.code AS categoryCode, rc.name AS categoryName,
           re.name AS entityName, c.name AS companyName
    UNION
    MATCH (d:Deal)-[:TARGET]->(c:Company)-[:HAS_RELATED]->(rel:Company)
          -[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    WHERE ev.score >= 60
    RETURN ev.id AS id, ev.title AS title, ev.summary AS summary,
           ev.type AS type, ev.score AS score, ev.severity AS severity,
           ev.sourceName AS sourceName, ev.sourceUrl AS sourceUrl,
           coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS publishedAt,
           rc.code AS categoryCode, rc.name AS categoryName,
           re.name AS entityName, rel.name AS companyName
    ORDER BY score DESC
    LIMIT $limit
    """
    events_raw = client.execute_read(query, {"limit": limit}) or []

    # 트리아지 점수 계산 + CRITICAL 필터
    alerts = []
    seen_ids = set()
    for e in events_raw:
        evt_id = e.get("id", "")
        if not evt_id or evt_id in seen_ids:
            continue
        seen_ids.add(evt_id)

        severity_str = e.get("severity") or "MEDIUM"
        source_name = e.get("sourceName") or ""
        published_at = e.get("publishedAt") or ""

        severity_score = SEVERITY_SCORE_MAP.get(severity_str, 50)
        urgency = _calc_urgency(published_at)
        tier, reliability = _classify_source(source_name)
        confidence = int(reliability * 100)
        triage_score = round(severity_score * 0.4 + urgency * 0.3 + confidence * 0.3, 1)
        triage_level = _calc_triage_level(triage_score)

        # CRITICAL 레벨이거나 원점수 80 이상만
        if triage_level != "CRITICAL" and (e.get("score", 0) or 0) < 80:
            continue

        alerts.append({
            "id": evt_id,
            "entityId": e.get("entityName", ""),
            "title": e.get("title", ""),
            "summary": e.get("summary") or "",
            "type": e.get("type") or "NEWS",
            "score": e.get("score", 0) or 0,
            "severity": severity_str,
            "sourceName": source_name,
            "sourceUrl": e.get("sourceUrl") or "",
            "publishedAt": published_at,
            "urgency": urgency,
            "confidence": confidence,
            "triageScore": triage_score,
            "triageLevel": triage_level,
            "sourceTier": tier,
            "sourceReliability": reliability,
            "hasConflict": False,
            "playbook": PLAYBOOK_MAP.get(e.get("categoryCode") or "OTHER", PLAYBOOK_MAP["OTHER"]),
            "categoryCode": e.get("categoryCode") or "OTHER",
            "categoryName": e.get("categoryName") or "",
            "companyName": e.get("companyName") or "",
        })

    alerts.sort(key=lambda x: x["triageScore"], reverse=True)

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "alerts": alerts,
        "count": len(alerts),
    }


# =============================================================================
# Triaged Events API (Smart Triage + Source Transparency)
# =============================================================================

# 소스 → 등급/신뢰도 매핑
SOURCE_TIER_MAP = {
    # OFFICIAL (공공기관)
    "DART": ("OFFICIAL", 0.95),
    "금감원": ("OFFICIAL", 0.95),
    "FSS": ("OFFICIAL", 0.95),
    "한국거래소": ("OFFICIAL", 0.90),
    "공정위": ("OFFICIAL", 0.90),
    # PRESS (주요 언론)
    "연합뉴스": ("PRESS", 0.85),
    "조선일보": ("PRESS", 0.80),
    "중앙일보": ("PRESS", 0.80),
    "동아일보": ("PRESS", 0.80),
    "한겨레": ("PRESS", 0.80),
    "경향신문": ("PRESS", 0.80),
    "매일경제": ("PRESS", 0.82),
    "한국경제": ("PRESS", 0.82),
    "서울경제": ("PRESS", 0.80),
    "머니투데이": ("PRESS", 0.78),
    "이데일리": ("PRESS", 0.78),
    "아시아경제": ("PRESS", 0.78),
    "SBS": ("PRESS", 0.85),
    "KBS": ("PRESS", 0.85),
    "MBC": ("PRESS", 0.85),
    "JTBC": ("PRESS", 0.85),
    "YTN": ("PRESS", 0.82),
    "뉴스1": ("PRESS", 0.75),
    "뉴시스": ("PRESS", 0.75),
    # COMMUNITY
    "네이버": ("COMMUNITY", 0.60),
    "다음": ("COMMUNITY", 0.55),
}

SEVERITY_SCORE_MAP = {
    "CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25
}

# 카테고리별 대응 플레이북
PLAYBOOK_MAP = {
    "LEGAL": ["법률팀 검토 요청", "소송 리스크 분석 실행", "규제 영향 평가"],
    "EXEC": ["경영진 배경 조사", "내부 이해관계 확인", "거버넌스 리뷰"],
    "SHARE": ["지분 변동 모니터링", "주주총회 안건 확인", "공시 추적"],
    "CREDIT": ["재무제표 분석", "신용등급 변동 추적", "유동성 점검"],
    "GOV": ["지배구조 평가", "이사회 구성 점검", "내부통제 확인"],
    "OPS": ["운영 리스크 평가", "공급망 안정성 확인", "BCP 점검"],
    "AUDIT": ["감사보고서 검토", "내부감사 결과 확인", "회계 이슈 추적"],
    "ESG": ["ESG 등급 확인", "환경 규제 점검", "사회적 영향 평가"],
    "SUPPLY": ["공급망 의존도 분석", "대체 공급원 확인", "물류 리스크 점검"],
    "OTHER": ["종합 리스크 평가", "추가 조사 필요"],
}


def _classify_source(source_name: str) -> tuple:
    """소스명 → (tier, reliability) 분류"""
    if not source_name:
        return ("COMMUNITY", 0.50)
    for key, (tier, rel) in SOURCE_TIER_MAP.items():
        if key in source_name:
            return (tier, rel)
    # 블로그 패턴 감지
    if "blog" in source_name.lower() or "블로그" in source_name:
        return ("BLOG", 0.40)
    return ("COMMUNITY", 0.55)


def _calc_urgency(published_at: str) -> int:
    """발행일 기반 긴급도 계산 (0-100, 시간 감쇠)"""
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else None
        if not pub:
            return 30
        now = datetime.now(pub.tzinfo) if pub.tzinfo else datetime.now()
        hours_ago = max(0, (now - pub).total_seconds() / 3600)
        # 0시간=100, 6시간=85, 24시간=60, 72시간=30, 168시간(7일)=10
        if hours_ago <= 6:
            return max(80, 100 - int(hours_ago * 3))
        elif hours_ago <= 24:
            return max(55, 85 - int((hours_ago - 6) * 1.4))
        elif hours_ago <= 72:
            return max(25, 60 - int((hours_ago - 24) * 0.7))
        elif hours_ago <= 168:
            return max(5, 30 - int((hours_ago - 72) * 0.26))
        return 5
    except Exception:
        return 30


def _calc_triage_level(score: float) -> str:
    """트리아지 점수 → 레벨"""
    if score >= 75:
        return "CRITICAL"
    if score >= 55:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


@router.get("/deals/{deal_id}/events/triaged")
def get_triaged_events(deal_id: str, limit: int = 30):
    """Smart Triage 이벤트 목록 (3축 점수: Severity + Urgency + Confidence) - def로 스레드풀 실행"""
    client = get_client()

    # 메인기업 + 관련기업 이벤트 모두 가져오기
    events_query = """
    MATCH (c:Company {name: $dealId})-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    RETURN ev.id AS id, ev.title AS title, ev.summary AS summary,
           ev.type AS type, ev.score AS score, ev.severity AS severity,
           ev.sourceName AS sourceName, ev.sourceUrl AS sourceUrl,
           coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS publishedAt,
           rc.code AS categoryCode, rc.name AS categoryName,
           re.name AS entityName, c.name AS companyName
    UNION
    MATCH (c:Company {name: $dealId})-[:HAS_RELATED]->(rel:Company)
          -[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    RETURN ev.id AS id, ev.title AS title, ev.summary AS summary,
           ev.type AS type, ev.score AS score, ev.severity AS severity,
           ev.sourceName AS sourceName, ev.sourceUrl AS sourceUrl,
           coalesce(toString(ev.publishedAt), toString(ev.createdAt), '') AS publishedAt,
           rc.code AS categoryCode, rc.name AS categoryName,
           re.name AS entityName, rel.name AS companyName
    ORDER BY score DESC
    LIMIT $limit
    """
    events_raw = client.execute_read(events_query, {"dealId": deal_id, "limit": limit}) or []

    # 트리아지 점수 계산
    triaged = []
    title_set = {}  # 충돌 감지용

    for e in events_raw:
        title = e.get("title", "")
        severity_str = e.get("severity") or "MEDIUM"
        source_name = e.get("sourceName") or ""
        published_at = e.get("publishedAt") or ""
        cat_code = e.get("categoryCode") or "OTHER"

        # 3축 계산
        severity_score = SEVERITY_SCORE_MAP.get(severity_str, 50)
        urgency = _calc_urgency(published_at)
        tier, reliability = _classify_source(source_name)
        confidence = int(reliability * 100)

        # 트리아지 점수
        triage_score = round(severity_score * 0.4 + urgency * 0.3 + confidence * 0.3, 1)
        triage_level = _calc_triage_level(triage_score)

        # 충돌 감지 (동일 주제 다른 소스)
        title_key = title[:20] if title else ""
        if title_key in title_set and title_set[title_key] != source_name:
            has_conflict = True
        else:
            has_conflict = False
        title_set[title_key] = source_name

        # 플레이북
        playbook = PLAYBOOK_MAP.get(cat_code, PLAYBOOK_MAP["OTHER"])

        triaged.append({
            "id": e.get("id", ""),
            "entityId": e.get("entityName", ""),
            "title": title,
            "summary": e.get("summary") or "",
            "type": e.get("type") or "NEWS",
            "score": e.get("score", 0) or 0,
            "severity": severity_str,
            "sourceName": source_name,
            "sourceUrl": e.get("sourceUrl") or "",
            "publishedAt": published_at,
            "urgency": urgency,
            "confidence": confidence,
            "triageScore": triage_score,
            "triageLevel": triage_level,
            "sourceTier": tier,
            "sourceReliability": reliability,
            "hasConflict": has_conflict,
            "playbook": playbook,
            "categoryCode": cat_code,
            "categoryName": e.get("categoryName") or "",
            "companyName": e.get("companyName") or "",
        })

    # 트리아지 점수 기준 정렬
    triaged.sort(key=lambda x: x["triageScore"], reverse=True)

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "events": triaged,
        "summary": {
            "total": len(triaged),
            "critical": sum(1 for t in triaged if t["triageLevel"] == "CRITICAL"),
            "high": sum(1 for t in triaged if t["triageLevel"] == "HIGH"),
            "medium": sum(1 for t in triaged if t["triageLevel"] == "MEDIUM"),
            "low": sum(1 for t in triaged if t["triageLevel"] == "LOW"),
        }
    }


# =============================================================================
# Case Management API (SQLite 기반)
# =============================================================================

CASES_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cases.db")


def _init_cases_db():
    """케이스 DB 초기화"""
    os.makedirs(os.path.dirname(CASES_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(CASES_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            deal_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            event_title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            assignee TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'MEDIUM',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# 앱 시작 시 DB 초기화
_init_cases_db()


class CreateCaseRequest(BaseModel):
    event_id: str
    event_title: str
    assignee: str = ""
    notes: str = ""
    priority: str = "MEDIUM"


class UpdateCaseRequest(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None


@router.get("/deals/{deal_id}/cases")
def get_deal_cases(deal_id: str):
    """딜의 케이스 목록 조회"""
    conn = sqlite3.connect(CASES_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM cases WHERE deal_id = ? ORDER BY created_at DESC", (deal_id,)
    ).fetchall()
    conn.close()

    cases = [dict(r) for r in rows]
    return {
        "cases": cases,
        "summary": {
            "total": len(cases),
            "open": sum(1 for c in cases if c["status"] == "OPEN"),
            "inProgress": sum(1 for c in cases if c["status"] == "IN_PROGRESS"),
            "resolved": sum(1 for c in cases if c["status"] == "RESOLVED"),
        }
    }


@router.post("/deals/{deal_id}/cases")
def create_case(deal_id: str, req: CreateCaseRequest):
    """새 케이스 생성"""
    case_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()

    conn = sqlite3.connect(CASES_DB_PATH)
    conn.execute(
        """INSERT INTO cases (id, deal_id, event_id, event_title, status, assignee, notes, priority, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?)""",
        (case_id, deal_id, req.event_id, req.event_title, req.assignee, req.notes, req.priority, now, now)
    )
    conn.commit()
    conn.close()

    return {
        "id": case_id,
        "deal_id": deal_id,
        "event_id": req.event_id,
        "event_title": req.event_title,
        "status": "OPEN",
        "assignee": req.assignee,
        "notes": req.notes,
        "priority": req.priority,
        "created_at": now,
        "updated_at": now,
    }


@router.patch("/deals/{deal_id}/cases/{case_id}")
def update_case(deal_id: str, case_id: str, req: UpdateCaseRequest):
    """케이스 상태 업데이트"""
    conn = sqlite3.connect(CASES_DB_PATH)
    conn.row_factory = sqlite3.Row
    existing = conn.execute("SELECT * FROM cases WHERE id = ? AND deal_id = ?", (case_id, deal_id)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    updates = []
    params = []
    now = datetime.now().isoformat()

    if req.status is not None:
        updates.append("status = ?")
        params.append(req.status)
    if req.assignee is not None:
        updates.append("assignee = ?")
        params.append(req.assignee)
    if req.notes is not None:
        updates.append("notes = ?")
        params.append(req.notes)
    if req.priority is not None:
        updates.append("priority = ?")
        params.append(req.priority)

    updates.append("updated_at = ?")
    params.append(now)
    params.extend([case_id, deal_id])

    conn.execute(f"UPDATE cases SET {', '.join(updates)} WHERE id = ? AND deal_id = ?", params)
    conn.commit()

    updated = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    conn.close()

    return dict(updated)
