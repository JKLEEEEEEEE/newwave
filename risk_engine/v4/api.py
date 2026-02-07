"""
Risk Engine V4 API
- 드릴다운 지원
- 완전한 데이터 연결
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from .schemas import (
    DealDetailResponse, DealDetail, CategorySummary, EventSummary, PersonSummary,
    EvidenceSummary, ScoreBreakdown, CategoryDetailResponse, CategoryDetail,
    EventDetailResponse, EventDetail, PersonDetailResponse, PersonDetail,
    NewsItem, DisclosureItem, CATEGORY_CONFIG
)
from .services import EventService, CategoryService, PersonLinkingService, ScoreService
from .pipelines import run_full_pipeline

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
async def get_deals():
    """딜 목록 조회 (카테고리 요약 포함)"""
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
            "fail": sum(1 for d in deals if d["riskLevel"] == "FAIL"),
        }
    }


@router.get("/deals/{deal_id}", response_model=DealDetailResponse)
async def get_deal_detail(deal_id: str):
    """딜 상세 조회 (전체 드릴다운 데이터)"""
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
async def get_category_detail(deal_id: str, category_code: str):
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
           c.propagatedScore AS propagatedScore
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
        "metadata": {"sector": company.get("sector", ""), "directScore": company.get("directScore", 0) or 0},
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
        cat_level = "FAIL" if weighted >= 15 else ("WARNING" if weighted >= 5 else "PASS")

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
    RETURN re.name AS name, re.type AS type, re.score AS score,
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
        ent_level = "FAIL" if ent_score >= 30 else ("WARNING" if ent_score >= 10 else "PASS")

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
           rc.sector AS sector, r.relation AS relation, r.tier AS tier
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
            "metadata": {"relation": relation_type, "sector": rel.get("sector", "")},
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
            rcat_level = "FAIL" if rcat_weighted >= 15 else ("WARNING" if rcat_weighted >= 5 else "PASS")

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
        RETURN re.name AS name, re.type AS type, re.score AS score,
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
            rent_level = "FAIL" if rent_score >= 30 else ("WARNING" if rent_score >= 10 else "PASS")

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

    return {
        "schemaVersion": "v4",
        "generatedAt": datetime.now().isoformat(),
        "nodes": nodes,
        "links": links,
    }
