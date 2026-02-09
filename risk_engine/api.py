"""
============================================================================
Step 3. 리스크 모니터링 시스템 - FastAPI 서버
============================================================================
Graph-First + AI Enhanced (v2.2)

실행 방법:
    uvicorn risk_engine.api:app --reload --port 8000

또는:
    python -m risk_engine.api
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# .env.local 로드 (프로젝트 루트에서)
import pathlib
project_root = pathlib.Path(__file__).parent.parent
load_dotenv(project_root / ".env.local")

# 로깅 설정
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# 환경 변수: Mock/실제 데이터 전환
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

# Neo4j 클라이언트 (v2.2 - 새로운 싱글톤 클라이언트)
try:
    from .neo4j_client import neo4j_client
    NEO4J_CLIENT_AVAILABLE = True
except ImportError:
    NEO4J_CLIENT_AVAILABLE = False
    neo4j_client = None
    logger.warning("⚠️ neo4j_client 로드 실패")

# Neo4j 연결 (기존 langchain 호환)
try:
    from langchain_neo4j import Neo4jGraph
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("⚠️ langchain_neo4j 미설치. pip install langchain-neo4j")

# AI 서비스 v2 (OpenAI 연동)
try:
    from .ai_service_v2 import ai_service_v2
    AI_V2_AVAILABLE = ai_service_v2.is_available
except ImportError:
    AI_V2_AVAILABLE = False
    ai_service_v2 = None
    logger.warning("⚠️ AI 서비스 v2 로드 실패")

# AI 서비스 (기존 ai_service.py - 폴백용)
try:
    from .ai_service import (
        generate_action_guide_ai_v2,
        text2cypher,
        predict_risk_trajectory,
        AI_AVAILABLE,
    )
except ImportError:
    AI_AVAILABLE = False
    logger.warning("⚠️ AI 서비스 로드 실패")

# Phase 3: 시뮬레이션 엔진
try:
    from .simulation_engine import (
        simulation_engine,
        ScenarioConfig,
        get_scenario_by_id as get_scenario_config,
        get_all_scenarios as get_preset_scenarios,
        PRESET_SCENARIOS
    )
    SIMULATION_ENGINE_AVAILABLE = True
except ImportError:
    SIMULATION_ENGINE_AVAILABLE = False
    simulation_engine = None
    logger.warning("⚠️ Simulation Engine 로드 실패")

# Phase 3: ML 예측기
try:
    from .ml_predictor import ml_predictor
    ML_PREDICTOR_AVAILABLE = ml_predictor.is_available if ml_predictor else False
except ImportError:
    ML_PREDICTOR_AVAILABLE = False
    ml_predictor = None
    logger.warning("⚠️ ML Predictor 로드 실패")

# V3: 키워드 엔진 & 점수 계산
try:
    from .keywords import match_keywords, DART_RISK_KEYWORDS, NEWS_RISK_KEYWORDS
    from .score_engine import ScoreEngine, determine_status
    KEYWORDS_AVAILABLE = True
except ImportError:
    KEYWORDS_AVAILABLE = False
    logger.warning("⚠️ Keywords/ScoreEngine 로드 실패")

# V3: 리스크 계산기
try:
    from .risk_calculator_v3 import RiskCalculatorV3
    RISK_CALCULATOR_V3_AVAILABLE = True
except ImportError:
    RISK_CALCULATOR_V3_AVAILABLE = False
    logger.warning("⚠️ RiskCalculatorV3 로드 실패")

# V3: 데이터 수집기
try:
    from .dart_collector_v2 import DartCollectorV2
    from .news_collector_v2 import NewsCollectorV2
    COLLECTORS_V2_AVAILABLE = True
except ImportError:
    COLLECTORS_V2_AVAILABLE = False
    logger.warning("⚠️ Collectors V2 로드 실패")

# 신호 발행자
try:
    from .signal_publisher import signal_publisher
    SIGNAL_PUBLISHER_AVAILABLE = True
except ImportError:
    SIGNAL_PUBLISHER_AVAILABLE = False
    signal_publisher = None
    logger.warning("⚠️ Signal Publisher 로드 실패")

# V4: 새로운 드릴다운 API
try:
    from .v4.api import router as v4_router, set_neo4j_client as v4_set_neo4j_client
    V4_AVAILABLE = True
except ImportError as e:
    V4_AVAILABLE = False
    v4_router = None
    v4_set_neo4j_client = None
    logger.warning(f"⚠️ V4 API 로드 실패: {e}")


# ============================================
# Pydantic 모델 (요청/응답 스키마)
# ============================================

class SimulationRequest(BaseModel):
    scenarioId: str
    dealIds: Optional[List[str]] = None


class Text2CypherRequest(BaseModel):
    question: str


class NewsAnalysisRequest(BaseModel):
    title: str
    content: str


class CustomScenarioRequest(BaseModel):
    """커스텀 시나리오 요청"""
    name: str
    affectedSectors: List[str]
    impactFactors: Dict[str, int]
    propagationMultiplier: float = 1.5
    severity: str = "medium"
    description: str = ""


class DealSummary(BaseModel):
    id: str
    name: str
    sector: str
    status: str
    score: int
    directRisk: int
    propagatedRisk: int
    topFactors: List[str]
    lastSignal: str
    lastUpdated: str


class DealCreateRequest(BaseModel):
    """딜 생성 요청"""
    name: str  # 기업명 (예: SK하이닉스)
    sector: str  # 섹터 (예: 반도체)
    corpCode: str = ""  # DART 기업코드 (선택)
    initialScore: int = 50  # 초기 리스크 점수


class DealUpdateRequest(BaseModel):
    """딜 수정 요청"""
    name: str = None
    sector: str = None
    corpCode: str = None
    score: int = None


# ============================================
# FastAPI 앱 설정
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    # 시작 시
    logger.info("🚀 NewWave Risk Engine API v3.0 시작")
    logger.info(f"   USE_MOCK_DATA: {USE_MOCK_DATA}")
    logger.info(f"   Neo4j Client: {'✅' if NEO4J_CLIENT_AVAILABLE else '❌'}")
    logger.info(f"   Neo4j Graph: {'✅' if NEO4J_AVAILABLE else '❌'}")
    logger.info(f"   AI v2: {'✅' if AI_V2_AVAILABLE else '❌'}")
    logger.info(f"   AI v1: {'✅' if AI_AVAILABLE else '❌'}")
    logger.info(f"   Signal Publisher: {'✅' if SIGNAL_PUBLISHER_AVAILABLE else '❌'}")
    logger.info(f"   Simulation Engine: {'✅' if SIMULATION_ENGINE_AVAILABLE else '❌'}")
    logger.info(f"   ML Predictor: {'✅' if ML_PREDICTOR_AVAILABLE else '❌'}")
    logger.info(f"   V3 Keywords: {'✅' if KEYWORDS_AVAILABLE else '❌'}")
    logger.info(f"   V3 RiskCalculator: {'✅' if RISK_CALCULATOR_V3_AVAILABLE else '❌'}")
    logger.info(f"   V3 Collectors: {'✅' if COLLECTORS_V2_AVAILABLE else '❌'}")
    logger.info(f"   V4 Drilldown API: {'✅' if V4_AVAILABLE else '❌'}")

    # Neo4j 클라이언트 연결 (v2.2)
    if NEO4J_CLIENT_AVAILABLE and not USE_MOCK_DATA:
        try:
            neo4j_client.connect()
            logger.info("   ✅ Neo4j 클라이언트 연결 성공")

            # V4 API에 Neo4j 클라이언트 설정
            if V4_AVAILABLE and v4_set_neo4j_client:
                v4_set_neo4j_client(neo4j_client)
                logger.info("   ✅ V4 API Neo4j 클라이언트 설정")
        except Exception as e:
            logger.error(f"   ❌ Neo4j 클라이언트 연결 실패: {e}")

    # Neo4j Graph 연결 (langchain 호환 - Text2Cypher용)
    if NEO4J_AVAILABLE:
        try:
            app.state.graph = Neo4jGraph(
                url=os.getenv("NEO4J_URI"),
                username=os.getenv("NEO4J_USERNAME"),
                password=os.getenv("NEO4J_PASSWORD"),
                database=os.getenv("NEO4J_DATABASE", "neo4j")
            )
            logger.info("   ✅ Neo4j Graph 연결 성공")
        except Exception as e:
            logger.error(f"   ❌ Neo4j Graph 연결 실패: {e}")
            app.state.graph = None
    else:
        app.state.graph = None

    # 신호 폴링 시작 (백그라운드)
    polling_task = None
    if SIGNAL_PUBLISHER_AVAILABLE and not USE_MOCK_DATA:
        polling_task = asyncio.create_task(signal_publisher.start_polling())
        logger.info("   ✅ 신호 폴링 시작")

    yield

    # 종료 시
    logger.info("🛑 NewWave Risk Engine API 종료")

    # 신호 폴링 중지
    if SIGNAL_PUBLISHER_AVAILABLE and signal_publisher:
        signal_publisher.stop()
        if polling_task:
            polling_task.cancel()

    # Neo4j 연결 종료
    if NEO4J_CLIENT_AVAILABLE and neo4j_client:
        neo4j_client.close()


app = FastAPI(
    title="NewWave Risk Engine API",
    description="Graph-First + AI Enhanced 리스크 모니터링 시스템 (V3: Status 중심 + 점수 투명화)",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경: 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V4 라우터 등록
if V4_AVAILABLE and v4_router:
    app.include_router(v4_router)
    logger.info("✅ V4 API 라우터 등록 완료")


# ============================================
# 헬스 체크
# ============================================

@app.get("/health")
async def health_check():
    """서버 상태 확인 (실시간 연결 체크)"""
    neo4j_ok = False
    if NEO4J_CLIENT_AVAILABLE and neo4j_client:
        try:
            neo4j_client.execute_read("RETURN 1 AS ok", {})
            neo4j_ok = True
        except Exception:
            neo4j_ok = False
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "neo4j": neo4j_ok,
        "ai": AI_AVAILABLE,
        "use_mock": USE_MOCK_DATA,
    }


# ============================================
# 딜 관련 API
# ============================================

@app.get("/api/v2/deals")
async def get_all_deals():
    """포트폴리오 전체 딜 목록 + 리스크 요약"""

    # Mock 모드 또는 Neo4j 미연결 시
    if USE_MOCK_DATA or not NEO4J_CLIENT_AVAILABLE:
        return {
            "deals": get_mock_deals(),
            "summary": {
                "total": 5,
                "pass": 2,
                "warning": 2,
                "fail": 1,
                "avgScore": 57,
            }
        }

    # Neo4j 클라이언트로 실제 데이터 조회 (v2.3 - 딜 중심)
    try:
        query = """
        MATCH (d:Deal)-[:TARGET]->(t:DealTarget)
        RETURN d.id AS dealId, d.name AS dealName, d.type AS dealType,
               t.id AS id, t.name AS name, t.sector AS sector,
               t.totalRiskScore AS score, t.riskLevel AS status
        ORDER BY t.totalRiskScore DESC
        """
        results = neo4j_client.execute_read(query)

        deals = []
        for r in results:
            score = r.get('score', 0) or 0
            status = r.get('status') or ('NORMAL' if score <= 30 else 'WATCH' if score <= 50 else 'WARNING' if score <= 70 else 'CRITICAL')

            deals.append({
                "id": r.get('id') or r['name'].replace(' ', '_').lower(),
                "name": r['name'],
                "sector": r.get('sector', '기타'),
                "status": status,
                "score": score,
                "directRisk": score,
                "propagatedRisk": 0,
                "topFactors": [],
                "lastSignal": "",
                "lastUpdated": "방금 전",
            })

        return {
            "deals": deals,
            "summary": calculate_summary(deals),
        }

    except Exception as e:
        logger.error(f"Neo4j 딜 조회 실패: {e}")
        # Fallback to mock
        return {
            "deals": get_mock_deals(),
            "summary": calculate_summary(get_mock_deals()),
        }


@app.post("/api/v2/deals")
async def create_deal(request: DealCreateRequest):
    """딜 대상 수기 등록 (시연용)"""
    if not NEO4J_CLIENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Neo4j 연결 필요")

    try:
        # 1. 먼저 Company 노드 생성/확인
        company_query = """
        MERGE (c:Company {id: $name})
        SET c.name = $name,
            c.sector = $sector,
            c.corpCode = $corpCode,
            c.totalRiskScore = $score,
            c.directScore = $score,
            c.propagatedScore = 0,
            c.riskLevel = CASE
                WHEN $score < 50 THEN 'PASS'
                WHEN $score < 75 THEN 'WARNING'
                ELSE 'FAIL'
            END,
            c.createdAt = datetime(),
            c.updatedAt = datetime()
        RETURN c.id AS id
        """
        neo4j_client.execute_write(company_query, {
            "name": request.name,
            "sector": request.sector,
            "corpCode": request.corpCode,
            "score": request.initialScore,
        })

        # 2. Deal 노드 생성
        deal_id = f"deal_{request.name.replace(' ', '_').lower()}"
        deal_query = """
        MERGE (d:Deal {id: $dealId})
        SET d.name = $dealName,
            d.type = 'EQUITY',
            d.createdAt = datetime()
        WITH d
        MATCH (c:Company {id: $companyName})
        MERGE (dt:DealTarget {id: $companyName})
        SET dt.name = c.name,
            dt.sector = c.sector,
            dt.totalRiskScore = c.totalRiskScore,
            dt.riskLevel = c.riskLevel
        MERGE (d)-[:TARGET]->(dt)
        RETURN d.id AS dealId, dt.name AS targetName
        """
        result = neo4j_client.execute_write(deal_query, {
            "dealId": deal_id,
            "dealName": f"Deal - {request.name}",
            "companyName": request.name,
        })

        logger.info(f"[Deal Created] {request.name} (sector: {request.sector}, score: {request.initialScore})")

        return {
            "success": True,
            "message": f"딜 '{request.name}' 등록 완료",
            "deal": {
                "id": deal_id,
                "name": request.name,
                "sector": request.sector,
                "score": request.initialScore,
            }
        }

    except Exception as e:
        logger.error(f"딜 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v2/deals/{deal_id}")
async def delete_deal(deal_id: str):
    """딜 대상 삭제"""
    if not NEO4J_CLIENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Neo4j 연결 필요")

    try:
        # DealTarget과 Deal 노드 삭제 (Company는 유지)
        delete_query = """
        MATCH (d:Deal)-[r:TARGET]->(dt:DealTarget)
        WHERE d.id = $dealId OR dt.id = $dealId OR dt.name = $dealId
        DELETE r
        WITH dt, d
        DELETE dt
        WITH d
        DELETE d
        RETURN count(*) AS deleted
        """
        result = neo4j_client.execute_write(delete_query, {"dealId": deal_id})

        logger.info(f"[Deal Deleted] {deal_id}")

        return {
            "success": True,
            "message": f"딜 '{deal_id}' 삭제 완료"
        }

    except Exception as e:
        logger.error(f"딜 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/deals/{deal_id}")
async def get_deal_detail(deal_id: str):
    """개별 딜 상세 정보"""
    if USE_MOCK_DATA or not NEO4J_CLIENT_AVAILABLE:
        return {
            "schemaVersion": "monitoring.v2",
            "generatedAt": datetime.now().isoformat(),
            "data": get_mock_deal_detail(deal_id),
        }

    # Neo4j에서 실제 데이터 조회 (v2.3 - 딜 중심)
    try:
        # 딜 타겟 정보 조회 (Company 노드의 점수도 함께 조회)
        company_query = """
        MATCH (d:Deal)-[:TARGET]->(t:DealTarget)
        WHERE d.id = $dealId OR t.id = $dealId
        OPTIONAL MATCH (t)-[:HAS_RISK]->(r:RiskCategory)
        OPTIONAL MATCH (c:Company {name: t.name})
        RETURN d.id AS dealId, d.name AS dealName, d.type AS dealType,
               t.id AS id, t.name AS name, t.sector AS sector,
               t.totalRiskScore AS score, t.riskLevel AS status,
               c.directScore AS directScore, c.propagatedScore AS propagatedScore,
               collect({category: r.name, score: r.score, trend: r.trend}) AS categories
        """
        result = neo4j_client.execute_read_single(company_query, {"dealId": deal_id})

        if not result:
            return {"schemaVersion": "monitoring.v2", "generatedAt": datetime.now().isoformat(), "data": get_mock_deal_detail(deal_id)}

        score = result.get('score', 0) or 0
        direct_score = result.get('directScore', 0) or 0
        propagated_score = result.get('propagatedScore', 0) or 0
        status = result.get('status') or ('NORMAL' if score <= 30 else 'WATCH' if score <= 50 else 'WARNING' if score <= 70 else 'CRITICAL')

        deal = {
            "id": result['id'],
            "name": result['name'],
            "sector": result.get('sector', '기타'),
            "status": status,
            "score": score,
            "directRisk": direct_score,
            "propagatedRisk": propagated_score,
            "topFactors": [],
            "lastSignal": "",
            "lastUpdated": "방금 전",
        }

        # 카테고리 점수 변환
        categories = result.get('categories', [])
        category_scores = []
        category_icons = {"시장위험": "📈", "신용위험": "💳", "운영위험": "⚙️", "법률위험": "⚖️", "공급망위험": "🔗", "ESG위험": "🌱"}
        for cat in categories:
            if cat.get('category'):
                category_scores.append({
                    "categoryId": cat['category'],
                    "name": cat['category'],
                    "icon": category_icons.get(cat['category'], "📊"),
                    "score": cat.get('score', 0) or 0,
                    "weight": 0.15,
                    "weightedScore": (cat.get('score', 0) or 0) * 0.15,
                    "trend": cat.get('trend', 'stable'),
                    "topEvents": [],
                })

        return {
            "schemaVersion": "monitoring.v2",
            "generatedAt": datetime.now().isoformat(),
            "data": {
                "deal": deal,
                "categoryScores": category_scores if category_scores else get_mock_category_scores(),
                "timeline": get_mock_timeline(),
                "supplyChain": get_mock_supply_chain(),
                "propagation": get_mock_propagation(),
                "aiGuide": get_mock_ai_guide(),
                "evidence": [],
            },
        }
    except Exception as e:
        logger.error(f"딜 상세 조회 실패: {e}")
        return {
            "schemaVersion": "monitoring.v2",
            "generatedAt": datetime.now().isoformat(),
            "data": get_mock_deal_detail(deal_id),
        }


@app.get("/api/v2/deals/{deal_id}/risk-breakdown")
async def get_risk_breakdown(deal_id: str):
    """8개 카테고리별 리스크 분석"""
    return get_mock_category_scores()


# ============================================
# 공급망 & 전이 분석 API (Neo4j 핵심!)
# ============================================

@app.get("/api/v2/deals/{deal_id}/supply-chain")
async def get_supply_chain(deal_id: str):
    """공급망 그래프 조회 (Neo4j 핵심 기능)"""

    # Mock 모드
    if USE_MOCK_DATA or not NEO4J_CLIENT_AVAILABLE:
        return get_mock_supply_chain()

    company_name = deal_id_to_name(deal_id)

    # v2.2: neo4j_client 사용
    try:
        result = neo4j_client.get_supply_chain(company_name)
        if result:
            return format_supply_chain_response_v2(result, company_name)
    except Exception as e:
        logger.error(f"공급망 조회 실패: {e}")

    # Fallback to mock
    return get_mock_supply_chain()


@app.get("/api/v2/deals/{deal_id}/propagation")
async def get_propagation(deal_id: str):
    """리스크 전이 경로 분석"""
    if not app.state.graph:
        return get_mock_propagation()

    company_name = deal_id_to_name(deal_id)

    # 전이 리스크 분석 쿼리
    query = """
    MATCH path = (source:Company)-[:SUPPLIES_TO*1..2]->(target:Company {name: $name})
    WHERE source.total_score > 50
    RETURN
        [n IN nodes(path) | n.name] AS pathNodes,
        [n IN nodes(path) | n.total_score] AS pathScores,
        reduce(risk = 0, r IN relationships(path) |
            risk + coalesce(r.dependency, 0.3) * startNode(r).total_score * 0.1
        ) AS propagatedRisk
    ORDER BY propagatedRisk DESC
    LIMIT 10
    """

    try:
        results = app.state.graph.query(query, {"name": company_name})
        return format_propagation_response(results, company_name)
    except Exception as e:
        print(f"전이 분석 쿼리 오류: {e}")

    return get_mock_propagation()


# ============================================
# 실시간 신호 API
# ============================================

@app.get("/api/v2/signals")
async def get_signals(limit: int = Query(default=10, le=50)):
    """실시간 리스크 신호"""
    # Mock 모드
    if USE_MOCK_DATA or not NEO4J_CLIENT_AVAILABLE:
        return {
            "signals": get_mock_signals()[:limit],
            "count": limit,
        }

    # Neo4j에서 실제 신호 조회
    try:
        query = """
        MATCH (s:Signal)
        RETURN s.id AS id, s.signalType AS signalType, s.company AS company,
               s.content AS content, s.timestamp AS time, s.isUrgent AS isUrgent,
               s.category AS category, s.source AS source
        ORDER BY s.timestamp DESC
        LIMIT $limit
        """
        results = neo4j_client.execute_read(query, {"limit": limit})

        signals = []
        for r in results:
            signals.append({
                "id": r.get("id", ""),
                "signalType": r.get("signalType", "NEWS"),
                "company": r.get("company", ""),
                "content": r.get("content", ""),
                "time": r.get("time", datetime.now().isoformat()),
                "isUrgent": r.get("isUrgent", False),
                "category": r.get("category", "operational"),
                "source": r.get("source", "system"),
            })

        return {
            "signals": signals,
            "count": len(signals),
        }

    except Exception as e:
        logger.error(f"신호 조회 실패: {e}")
        return {
            "signals": [],
            "count": 0,
        }


@app.get("/api/v2/timeline/{deal_id}")
async def get_timeline(deal_id: str):
    """3단계 리스크 타임라인"""
    return get_mock_timeline()


# ============================================
# 시뮬레이션 API
# ============================================

@app.get("/api/v2/scenarios")
async def get_scenarios():
    """시뮬레이션 시나리오 목록"""
    return get_mock_scenarios()


@app.post("/api/v2/simulate")
async def run_simulation(request: SimulationRequest):
    """시나리오 시뮬레이션 실행"""
    scenario = get_scenario_by_id(request.scenarioId)
    if not scenario:
        raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다")

    # 시뮬레이션 로직 (실제 구현 필요)
    results = calculate_simulation_impact(scenario, request.dealIds)

    return results


# ============================================
# AI 기능 API
# ============================================

@app.get("/api/v2/ai-guide/{deal_id}")
async def get_ai_guide(deal_id: str, signal_type: str = "OPERATIONAL"):
    """AI 기반 RM/OPS 대응 가이드"""
    company_name = deal_id_to_name(deal_id)

    if AI_AVAILABLE:
        try:
            guide = generate_action_guide_ai_v2(
                signal_type=signal_type,
                company=company_name,
                industry=detect_industry(company_name),
                risk_score=60,
            )
            return guide
        except Exception as e:
            print(f"AI 가이드 생성 오류: {e}")

    return get_mock_ai_guide()


@app.post("/api/v2/ai/query")
async def ai_query(request: Text2CypherRequest):
    """Text2Cypher - 자연어 질의"""

    # v2.2: AI 서비스 v2 우선 사용
    if AI_V2_AVAILABLE and ai_service_v2:
        try:
            import asyncio
            parsed = await asyncio.to_thread(ai_service_v2.text_to_cypher, request.question)

            # 쿼리 실행
            if NEO4J_CLIENT_AVAILABLE and not parsed.get("error"):
                cypher = parsed["cypher"]
                results = neo4j_client.execute_read(cypher)

                # 자연어 답변 생성
                answer = await asyncio.to_thread(
                    ai_service_v2.generate_answer,
                    request.question, cypher, results or []
                )

                return {
                    "question": request.question,
                    "cypher": cypher,
                    "explanation": parsed["explanation"],
                    "results": results,
                    "answer": answer,
                    "success": True
                }
            else:
                return {
                    "question": request.question,
                    "cypher": parsed.get("cypher"),
                    "explanation": parsed.get("explanation"),
                    "results": None,
                    "answer": parsed.get("explanation", "쿼리를 실행할 수 없습니다."),
                    "success": not parsed.get("error", False)
                }
        except Exception as e:
            logger.error(f"Text2Cypher v2 오류: {e}")

    # Fallback: 기존 AI 서비스
    if AI_AVAILABLE and app.state.graph:
        try:
            result = text2cypher(request.question, app.state.graph)
            return result
        except Exception as e:
            logger.error(f"Text2Cypher v1 오류: {e}")

    return {
        "question": request.question,
        "cypher": None,
        "results": None,
        "answer": "AI 서비스를 사용할 수 없습니다.",
        "success": False,
    }


@app.post("/api/v2/ai/analyze-news")
async def ai_analyze_news(request: NewsAnalysisRequest):
    """AI 뉴스 분석"""

    # v2.2: AI 서비스 v2 사용
    if AI_V2_AVAILABLE and ai_service_v2:
        try:
            import asyncio
            result = await asyncio.to_thread(ai_service_v2.analyze_news, request.content, request.title)
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            logger.error(f"뉴스 분석 오류: {e}")

    # Fallback: 기본 응답
    return {
        "success": False,
        "data": {
            "severity": 3,
            "category": "operational",
            "affected_companies": [],
            "summary": "AI 분석 불가 - 수동 검토 필요",
            "risk_factors": ["AI 서비스 미활성화"],
            "confidence": 0.0
        }
    }


@app.get("/api/v2/ai/summarize/{deal_id}")
async def ai_summarize(deal_id: str):
    """AI 리스크 요약"""
    company_name = deal_id_to_name(deal_id)

    return {
        "summary": f"{company_name}은 공급망 리스크와 법률 리스크가 복합 작용 중. 모니터링 강화 필요.",
        "keyPoints": [
            "특허 소송으로 법률 리스크 급등",
            "공급사 리스크 전이 발생",
        ],
        "recommendation": "선제적 대응 전략 수립 필요",
    }


@app.get("/api/v3/ai/insight/{company_name}")
async def get_comprehensive_insight(company_name: str):
    """
    종합 AI 인사이트 분석

    리스크 점수는 알고리즘으로 이미 계산되어 있으므로,
    AI는 맥락적 해석, 패턴 인식, 교차 분석, 권고사항을 제공
    """
    try:
        # Neo4j에서 데이터 수집
        deal_context = await _build_deal_context(company_name)

        if not deal_context:
            raise HTTPException(status_code=404, detail=f"Company not found: {company_name}")

        # AI 인사이트 생성 (동기 OpenAI 호출 → 스레드풀에서 실행)
        import asyncio
        from .ai_service_v2 import ai_service_v2
        insight = await asyncio.to_thread(ai_service_v2.generate_comprehensive_insight, deal_context)

        return {
            "company": company_name,
            "riskScore": deal_context.get("riskScore"),
            "riskLevel": deal_context.get("riskLevel"),
            "insight": insight,
            "generatedAt": datetime.now().isoformat(),
            "aiServiceAvailable": ai_service_v2.is_available
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종합 인사이트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _build_deal_context(company_name: str) -> Optional[Dict[str, Any]]:
    """딜 컨텍스트 데이터 구성"""
    if not NEO4J_CLIENT_AVAILABLE or not neo4j_client:
        return None

    # 1. 기업 기본 정보
    company_query = """
    MATCH (c:Company {name: $name})
    RETURN c.name AS name, c.sector AS sector,
           c.totalRiskScore AS riskScore, c.riskLevel AS riskLevel
    """
    company_result = neo4j_client.execute_read(company_query, {"name": company_name})
    if not company_result:
        return None

    company = company_result[0]

    # 2. 최근 신호 (뉴스, 공시)
    signals_query = """
    MATCH (c:Company {name: $name})
    OPTIONAL MATCH (n:News)-[:MENTIONS]->(c)
    OPTIONAL MATCH (d:Disclosure)-[:MENTIONS]->(c)
    WITH c, collect(DISTINCT {
        type: 'news',
        category: n.category,
        title: n.title,
        score: n.riskScore,
        date: toString(n.publishedAt)
    }) AS newsSignals,
    collect(DISTINCT {
        type: 'disclosure',
        category: d.category,
        title: d.title,
        score: d.riskScore,
        date: toString(d.rcept_dt)
    }) AS discSignals
    RETURN newsSignals + discSignals AS signals
    """
    signals_result = neo4j_client.execute_read(signals_query, {"name": company_name})
    signals = []
    if signals_result and signals_result[0].get('signals'):
        signals = [s for s in signals_result[0]['signals'] if s.get('title')][:20]

    # 3. 임원 정보
    executives_query = """
    MATCH (p:Person)-[r:EXECUTIVE_OF]->(c:Company {name: $name})
    RETURN p.name AS name, r.position AS position
    LIMIT 10
    """
    executives_result = neo4j_client.execute_read(executives_query, {"name": company_name})
    executives = [{"name": e["name"], "position": e.get("position", "")} for e in (executives_result or [])]

    # 4. 주주 정보
    shareholders_query = """
    MATCH (p:Person)-[r:SHAREHOLDER_OF]->(c:Company {name: $name})
    RETURN p.name AS name, r.shareRatio AS shareRatio
    ORDER BY r.shareRatio DESC
    LIMIT 10
    """
    shareholders_result = neo4j_client.execute_read(shareholders_query, {"name": company_name})
    shareholders = [{"name": s["name"], "shareRatio": s.get("shareRatio", 0)} for s in (shareholders_result or [])]

    # 5. 관계 기업
    related_query = """
    MATCH (c:Company {name: $name})-[r:SUPPLIES_TO|COMPETES_WITH|SUBSIDIARY_OF]-(related:Company)
    RETURN related.name AS name, type(r) AS relation
    LIMIT 10
    """
    related_result = neo4j_client.execute_read(related_query, {"name": company_name})
    related_companies = [{"name": r["name"], "relation": r["relation"]} for r in (related_result or [])]

    # 6. 카테고리별 점수 집계
    category_query = """
    MATCH (c:Company {name: $name})
    OPTIONAL MATCH (n:News)-[:MENTIONS]->(c)
    WITH c, n.category AS cat, avg(n.riskScore) AS avgScore
    WHERE cat IS NOT NULL
    RETURN cat AS category, avgScore AS score
    """
    category_result = neo4j_client.execute_read(category_query, {"name": company_name})
    category_scores = {}
    for r in (category_result or []):
        if r.get('category') and r.get('score'):
            category_scores[r['category']] = int(r['score'])

    return {
        "company": company.get("name", company_name),
        "sector": company.get("sector", "N/A"),
        "riskScore": company.get("riskScore", 50),
        "riskLevel": company.get("riskLevel", "WARNING"),
        "signals": signals,
        "executives": executives,
        "shareholders": shareholders,
        "relatedCompanies": related_companies,
        "categoryScores": category_scores
    }


# ============================================
# WebSocket (실시간 신호)
# ============================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """실시간 리스크 신호 WebSocket"""

    # v2.2: SignalPublisher 사용
    if SIGNAL_PUBLISHER_AVAILABLE and signal_publisher:
        await signal_publisher.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()

                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    await websocket.send_json({
                        "type": "ack",
                        "message": f"Received: {data}",
                        "timestamp": datetime.now().isoformat()
                    })
        except WebSocketDisconnect:
            signal_publisher.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket 오류: {e}")
            signal_publisher.disconnect(websocket)
    else:
        # Fallback: 기존 ConnectionManager
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_json({
                    "type": "ack",
                    "message": f"Received: {data}",
                })
        except WebSocketDisconnect:
            manager.disconnect(websocket)


# ============================================
# 헬퍼 함수
# ============================================

def deal_id_to_name(deal_id: str) -> str:
    """딜 ID를 회사명으로 변환"""
    mapping = {
        "deal1": "SK하이닉스",
        "deal2": "한미반도체",
        "deal3": "삼성전자",
        "deal4": "LG에너지솔루션",
        "deal5": "현대자동차",
        "sk_hynix": "SK하이닉스",
    }
    return mapping.get(deal_id, deal_id)


def detect_industry(company: str) -> str:
    """회사명에서 산업 분류 추정"""
    if any(kw in company for kw in ['반도체', '하이닉스', '삼성전자']):
        return '반도체'
    if any(kw in company for kw in ['배터리', '에너지']):
        return '배터리'
    if any(kw in company for kw in ['자동차', '현대', '기아']):
        return '자동차'
    return '기타'


def calculate_summary(deals: list) -> dict:
    """포트폴리오 요약 계산"""
    total = len(deals)
    if total == 0:
        return {"total": 0, "pass": 0, "warning": 0, "fail": 0, "avgScore": 0}

    pass_count = sum(1 for d in deals if d['status'] == 'PASS')
    warning_count = sum(1 for d in deals if d['status'] == 'WARNING')
    fail_count = sum(1 for d in deals if d['status'] == 'FAIL')
    avg_score = round(sum(d['score'] for d in deals) / total)

    return {
        "total": total,
        "pass": pass_count,
        "warning": warning_count,
        "fail": fail_count,
        "avgScore": avg_score,
    }


def format_supply_chain_response(result: dict) -> dict:
    """공급망 쿼리 결과 포맷팅 (기존 호환)"""
    # 실제 구현 필요
    return get_mock_supply_chain()


def format_supply_chain_response_v2(result: dict, company_name: str) -> dict:
    """공급망 쿼리 결과 포맷팅 (v2.2)"""
    if not result:
        return get_mock_supply_chain()

    target = result.get("target", {})
    suppliers_raw = result.get("suppliers", [])
    customers_raw = result.get("customers", [])
    competitors_raw = result.get("competitors", [])

    # 중앙 노드
    center_node = {
        "id": target.get("id", company_name.replace(" ", "_").lower()),
        "type": "company",
        "name": target.get("name", company_name),
        "riskScore": target.get("totalRiskScore", 50)
    }

    # 공급사 노드
    suppliers = []
    for item in suppliers_raw:
        node = item.get("node")
        if node and node.get("name"):
            suppliers.append({
                "id": node.get("id", node["name"].replace(" ", "_").lower()),
                "type": "supplier",
                "name": node["name"],
                "riskScore": node.get("totalRiskScore", 50),
                "tier": 1
            })

    # 고객사 노드
    customers = []
    for item in customers_raw:
        node = item.get("node")
        if node and node.get("name"):
            customers.append({
                "id": node.get("id", node["name"].replace(" ", "_").lower()),
                "type": "customer",
                "name": node["name"],
                "riskScore": node.get("totalRiskScore", 50)
            })

    # 엣지 생성
    edges = []
    for i, s in enumerate(suppliers):
        edges.append({
            "id": f"e_s_{i}",
            "source": s["id"],
            "target": center_node["id"],
            "relationship": "SUPPLIES_TO",
            "dependency": 0.3
        })

    for i, c in enumerate(customers):
        edges.append({
            "id": f"e_c_{i}",
            "source": center_node["id"],
            "target": c["id"],
            "relationship": "SUPPLIES_TO",
            "dependency": 0.3
        })

    # 전이 리스크 계산
    total_propagated = sum(s.get("riskScore", 0) * 0.1 for s in suppliers)

    return {
        "centerNode": center_node,
        "suppliers": suppliers,
        "customers": customers,
        "edges": edges,
        "totalPropagatedRisk": int(total_propagated)
    }


def format_propagation_response(results: list, company_name: str) -> dict:
    """전이 분석 결과 포맷팅"""
    # 실제 구현 필요
    return get_mock_propagation()


def get_scenario_by_id(scenario_id: str) -> Optional[dict]:
    """시나리오 ID로 조회"""
    scenarios = get_mock_scenarios()
    for s in scenarios:
        if s['id'] == scenario_id:
            return s
    return None


def calculate_simulation_impact(scenario: dict, deal_ids: Optional[List[str]]) -> list:
    """시뮬레이션 영향도 계산"""
    # Neo4j에서 실제 딜 대상 조회
    if not NEO4J_CLIENT_AVAILABLE:
        return []

    try:
        query = """
        MATCH (d:Deal)-[:TARGET]->(dt:DealTarget)
        RETURN dt.id AS id, dt.name AS name, dt.totalRiskScore AS score
        ORDER BY dt.totalRiskScore DESC
        """
        results = neo4j_client.execute_read(query)

        if not results:
            return []

        # 시나리오에 따른 영향도 계산
        impact_results = []
        for r in results:
            original_score = r.get('score', 50) or 50
            # 간단한 시뮬레이션: 시나리오 심각도에 따라 점수 증가
            severity_map = {"low": 5, "medium": 10, "high": 15, "critical": 20}
            delta = severity_map.get(scenario.get("severity", "medium"), 10)
            simulated_score = min(100, original_score + delta)

            impact_results.append({
                "dealId": r.get('id', ''),
                "dealName": r.get('name', ''),
                "originalScore": original_score,
                "simulatedScore": simulated_score,
                "delta": delta,
                "affectedCategories": [
                    {"category": "supply_chain", "delta": int(delta * 0.6)},
                    {"category": "operational", "delta": int(delta * 0.4)},
                ],
            })

        return impact_results

    except Exception as e:
        logger.error(f"시뮬레이션 계산 실패: {e}")
        return []


# ============================================
# Mock 데이터 함수
# ============================================

def get_mock_deals():
    """Mock 딜 목록 - 핵심 딜 대상만 (공급사/경쟁사 제외)"""
    return [
        {"id": "deal1", "name": "SK하이닉스", "sector": "반도체", "status": "WARNING", "score": 68, "directRisk": 56, "propagatedRisk": 12, "topFactors": ["특허 소송", "공급망"], "lastSignal": "ITC 조사", "lastUpdated": "30분 전"},
        {"id": "deal2", "name": "LG에너지솔루션", "sector": "배터리", "status": "PASS", "score": 42, "directRisk": 35, "propagatedRisk": 7, "topFactors": ["원자재 가격"], "lastSignal": "신규 수주", "lastUpdated": "1시간 전"},
        {"id": "deal3", "name": "현대자동차", "sector": "자동차", "status": "PASS", "score": 48, "directRisk": 38, "propagatedRisk": 10, "topFactors": ["노사 협상"], "lastSignal": "판매 호조", "lastUpdated": "3시간 전"},
    ]


def get_mock_deal_detail(deal_id: str):
    """Mock 딜 상세"""
    return {
        "deal": get_mock_deals()[0],
        "categoryScores": get_mock_category_scores(),
        "timeline": get_mock_timeline(),
        "supplyChain": get_mock_supply_chain(),
        "propagation": get_mock_propagation(),
        "aiGuide": get_mock_ai_guide(),
        "evidence": [],
    }


def get_mock_category_scores():
    """Mock 카테고리 점수"""
    return [
        {"categoryId": "financial", "name": "재무", "icon": "💰", "score": 45, "weight": 0.20, "weightedScore": 9, "trend": "stable", "topEvents": []},
        {"categoryId": "legal", "name": "법률/규제", "icon": "⚖️", "score": 78, "weight": 0.15, "weightedScore": 12, "trend": "up", "topEvents": ["ITC 조사"]},
        {"categoryId": "supply_chain", "name": "공급망", "icon": "🔗", "score": 72, "weight": 0.20, "weightedScore": 14, "trend": "up", "topEvents": ["한미반도체"]},
    ]


def get_mock_supply_chain():
    """Mock 공급망 그래프 - nodes/edges 형식"""
    return {
        "nodes": [
            {"id": "sk_hynix", "name": "SK하이닉스", "type": "company", "riskScore": 58, "sector": "반도체"},
            {"id": "hanmi_semi", "name": "한미반도체", "type": "supplier", "riskScore": 78, "sector": "반도체장비"},
            {"id": "asml", "name": "ASML", "type": "supplier", "riskScore": 25, "sector": "반도체장비"},
            {"id": "sk_materials", "name": "SK머티리얼즈", "type": "supplier", "riskScore": 45, "sector": "소재"},
            {"id": "dongwoo", "name": "동우화인켐", "type": "supplier", "riskScore": 52, "sector": "화학"},
            {"id": "apple", "name": "Apple", "type": "customer", "riskScore": 22, "sector": "IT"},
            {"id": "nvidia", "name": "NVIDIA", "type": "customer", "riskScore": 18, "sector": "반도체"},
            {"id": "amazon", "name": "Amazon", "type": "customer", "riskScore": 20, "sector": "IT"},
            {"id": "samsung_elec", "name": "삼성전자", "type": "competitor", "riskScore": 35, "sector": "전자"},
        ],
        "edges": [
            {"id": "e1", "source": "hanmi_semi", "target": "sk_hynix", "relationship": "SUPPLIES_TO", "dependency": 0.5, "riskTransfer": 0.39},
            {"id": "e2", "source": "asml", "target": "sk_hynix", "relationship": "SUPPLIES_TO", "dependency": 0.3, "riskTransfer": 0.08},
            {"id": "e3", "source": "sk_materials", "target": "sk_hynix", "relationship": "SUPPLIES_TO", "dependency": 0.45, "riskTransfer": 0.2},
            {"id": "e4", "source": "dongwoo", "target": "sk_hynix", "relationship": "SUPPLIES_TO", "dependency": 0.35, "riskTransfer": 0.18},
            {"id": "e5", "source": "sk_hynix", "target": "apple", "relationship": "SUPPLIES_TO", "dependency": 0.4, "riskTransfer": 0.23},
            {"id": "e6", "source": "sk_hynix", "target": "nvidia", "relationship": "SUPPLIES_TO", "dependency": 0.35, "riskTransfer": 0.2},
            {"id": "e7", "source": "sk_hynix", "target": "amazon", "relationship": "SUPPLIES_TO", "dependency": 0.25, "riskTransfer": 0.15},
            {"id": "e8", "source": "sk_hynix", "target": "samsung_elec", "relationship": "COMPETES_WITH", "dependency": 0, "riskTransfer": 0},
        ],
        "centerNode": {"id": "sk_hynix", "name": "SK하이닉스", "type": "company", "riskScore": 58},
        "totalPropagatedRisk": 85,
    }


def get_mock_propagation():
    """Mock 전이 분석"""
    return {
        "directRisk": 56,
        "propagatedRisk": 12,
        "totalRisk": 68,
        "topPropagators": [
            {"company": "한미반도체", "contribution": 8, "pathway": "공급망", "riskScore": 82},
        ],
        "paths": [
            {"path": ["한미반도체", "SK하이닉스"], "risk": 8, "pathway": "supply_chain"},
        ],
    }


def get_mock_signals():
    """Mock 신호"""
    return [
        {"id": "sig1", "signalType": "LEGAL_CRISIS", "company": "SK하이닉스", "content": "[긴급] 특허 침해 소송", "time": datetime.now().isoformat(), "isUrgent": True, "category": "legal", "source": "금감원"},
    ]


def get_mock_timeline():
    """Mock 타임라인"""
    return [
        {"id": "t1", "stage": 1, "stageLabel": "뉴스 보도", "icon": "🔵", "label": "특허 분쟁 보도", "description": "선행 감지", "date": "2026-02-03", "source": "뉴스"},
        {"id": "t2", "stage": 2, "stageLabel": "금융위 통지", "icon": "🟡", "label": "ITC 조사 개시", "description": "규제 개입", "date": "2026-02-04", "source": "금융위"},
    ]


def get_mock_scenarios():
    """Mock 시나리오"""
    # Phase 3: 프리셋 시나리오 사용
    if SIMULATION_ENGINE_AVAILABLE:
        return get_preset_scenarios()

    return [
        {"id": "busan_port", "name": "부산항 파업", "description": "물류 마비", "affectedSectors": ["물류", "반도체"], "impactFactors": {"supply_chain": 20}, "propagationMultiplier": 1.5, "severity": "high"},
        {"id": "memory_crash", "name": "반도체 수요 급감", "description": "메모리 가격 하락", "affectedSectors": ["반도체"], "impactFactors": {"market": 25}, "propagationMultiplier": 1.3, "severity": "high"},
    ]


def get_mock_ai_guide():
    """Mock AI 가이드"""
    return {
        "rmTitle": "💡 RM 영업 가이드 (AI)",
        "rmGuide": "특허 소송 리스크 대비 고객 커뮤니케이션 강화 필요",
        "rmTodos": ["고객 미팅", "FAQ 준비", "대안 검토"],
        "opsTitle": "🛡️ OPS 방어 가이드 (AI)",
        "opsGuide": "손해배상 시나리오별 충당금 검토",
        "opsTodos": ["재무 분석", "대체 공급사", "법무 협의"],
        "industry": "반도체",
        "industryInsight": "메모리 가격 하락 추세 지속 예상",
    }


# ============================================
# Phase 3: 고급 시뮬레이션 API
# ============================================

@app.post("/api/v2/simulate/advanced")
async def run_advanced_simulation(request: SimulationRequest):
    """
    고급 시뮬레이션 실행 (Cascade 효과)

    Phase 3 핵심 기능: 공급망 기반 동적 리스크 전이 계산
    """
    if not SIMULATION_ENGINE_AVAILABLE or not simulation_engine:
        raise HTTPException(status_code=503, detail="시뮬레이션 엔진 미활성화")

    # 시나리오 조회
    scenario_config = get_scenario_config(request.scenarioId)
    if not scenario_config:
        raise HTTPException(status_code=404, detail=f"시나리오를 찾을 수 없습니다: {request.scenarioId}")

    # 시뮬레이션 실행
    try:
        results = simulation_engine.run_simulation(
            scenario=scenario_config,
            target_deal_ids=request.dealIds
        )

        return {
            "success": True,
            "scenario": {
                "id": scenario_config.id,
                "name": scenario_config.name,
                "severity": scenario_config.severity,
                "affectedSectors": scenario_config.affected_sectors,
            },
            "results": [
                {
                    "dealId": r.deal_id,
                    "dealName": r.deal_name,
                    "originalScore": r.original_score,
                    "simulatedScore": r.simulated_score,
                    "delta": r.delta,
                    "affectedCategories": r.affected_categories,
                    "cascadePath": r.cascade_path,
                    "interpretation": r.interpretation
                }
                for r in results
            ],
            "totalAffected": len(results),
            "maxDelta": max(r.delta for r in results) if results else 0
        }

    except Exception as e:
        logger.error(f"시뮬레이션 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Phase 3: 커스텀 시나리오 API
# ============================================

@app.post("/api/v2/scenarios/custom")
async def create_custom_scenario(request: CustomScenarioRequest):
    """커스텀 시나리오 생성"""

    scenario_id = f"custom_{int(datetime.now().timestamp())}"

    # Neo4j에 저장 (선택적)
    if NEO4J_CLIENT_AVAILABLE and neo4j_client and not USE_MOCK_DATA:
        try:
            neo4j_client.connect()
            query = """
            CREATE (s:Scenario {
                id: $id,
                name: $name,
                affectedSectors: $sectors,
                impactFactors: $factors,
                propagationMultiplier: $multiplier,
                severity: $severity,
                description: $description,
                isCustom: true,
                createdAt: datetime()
            })
            RETURN s.id AS id
            """
            neo4j_client.execute_write(query, {
                "id": scenario_id,
                "name": request.name,
                "sectors": request.affectedSectors,
                "factors": json.dumps(request.impactFactors),
                "multiplier": request.propagationMultiplier,
                "severity": request.severity,
                "description": request.description
            })
            logger.info(f"커스텀 시나리오 저장: {scenario_id}")
        except Exception as e:
            logger.warning(f"Neo4j 시나리오 저장 실패 (계속 진행): {e}")

    return {
        "success": True,
        "scenarioId": scenario_id,
        "scenario": {
            "id": scenario_id,
            "name": request.name,
            "affectedSectors": request.affectedSectors,
            "impactFactors": request.impactFactors,
            "propagationMultiplier": request.propagationMultiplier,
            "severity": request.severity,
            "description": request.description,
            "isCustom": True
        },
        "message": "커스텀 시나리오가 생성되었습니다"
    }


@app.get("/api/v2/scenarios/custom")
async def get_custom_scenarios():
    """커스텀 시나리오 목록 조회"""

    if not NEO4J_CLIENT_AVAILABLE or not neo4j_client or USE_MOCK_DATA:
        return {"scenarios": [], "count": 0}

    try:
        neo4j_client.connect()
        query = """
        MATCH (s:Scenario {isCustom: true})
        RETURN s.id AS id, s.name AS name, s.affectedSectors AS affectedSectors,
               s.impactFactors AS impactFactors, s.propagationMultiplier AS propagationMultiplier,
               s.severity AS severity, s.description AS description,
               toString(s.createdAt) AS createdAt
        ORDER BY s.createdAt DESC
        """
        results = neo4j_client.execute_read(query)

        # impactFactors JSON 파싱
        scenarios = []
        for r in results:
            scenario = dict(r)
            if isinstance(scenario.get("impactFactors"), str):
                try:
                    scenario["impactFactors"] = json.loads(scenario["impactFactors"])
                except:
                    scenario["impactFactors"] = {}
            scenario["isCustom"] = True
            scenarios.append(scenario)

        return {"scenarios": scenarios, "count": len(scenarios)}

    except Exception as e:
        logger.error(f"커스텀 시나리오 조회 실패: {e}")
        return {"scenarios": [], "count": 0, "error": str(e)}


@app.post("/api/v2/scenarios/custom/{scenario_id}/simulate")
async def simulate_custom_scenario(scenario_id: str, deal_ids: Optional[List[str]] = None):
    """커스텀 시나리오로 시뮬레이션 실행"""

    if not SIMULATION_ENGINE_AVAILABLE or not simulation_engine:
        raise HTTPException(status_code=503, detail="시뮬레이션 엔진 미활성화")

    # Neo4j에서 커스텀 시나리오 조회
    scenario_data = None

    if NEO4J_CLIENT_AVAILABLE and neo4j_client and not USE_MOCK_DATA:
        try:
            neo4j_client.connect()
            query = """
            MATCH (s:Scenario {id: $id, isCustom: true})
            RETURN s.id AS id, s.name AS name, s.affectedSectors AS affectedSectors,
                   s.impactFactors AS impactFactors, s.propagationMultiplier AS propagationMultiplier,
                   s.severity AS severity, s.description AS description
            """
            scenario_data = neo4j_client.execute_read_single(query, {"id": scenario_id})
        except Exception as e:
            logger.warning(f"커스텀 시나리오 조회 실패: {e}")

    if not scenario_data:
        raise HTTPException(status_code=404, detail=f"커스텀 시나리오를 찾을 수 없습니다: {scenario_id}")

    # impactFactors 파싱
    impact_factors = scenario_data.get("impactFactors", {})
    if isinstance(impact_factors, str):
        try:
            impact_factors = json.loads(impact_factors)
        except:
            impact_factors = {}

    # ScenarioConfig 생성
    scenario_config = ScenarioConfig(
        id=scenario_data["id"],
        name=scenario_data["name"],
        affected_sectors=scenario_data.get("affectedSectors", []),
        impact_factors=impact_factors,
        propagation_multiplier=scenario_data.get("propagationMultiplier", 1.5),
        severity=scenario_data.get("severity", "medium"),
        description=scenario_data.get("description", ""),
        is_custom=True
    )

    # 시뮬레이션 실행
    results = simulation_engine.run_simulation(scenario_config, deal_ids)

    return {
        "success": True,
        "scenario": {
            "id": scenario_config.id,
            "name": scenario_config.name,
            "isCustom": True
        },
        "results": [
            {
                "dealId": r.deal_id,
                "dealName": r.deal_name,
                "originalScore": r.original_score,
                "simulatedScore": r.simulated_score,
                "delta": r.delta,
                "affectedCategories": r.affected_categories,
                "cascadePath": r.cascade_path,
                "interpretation": r.interpretation
            }
            for r in results
        ]
    }


# ============================================
# Phase 3: ML 예측 API
# ============================================

@app.get("/api/v2/predict/{deal_id}")
async def predict_risk(
    deal_id: str,
    periods: int = Query(default=30, ge=7, le=90)
):
    """
    리스크 예측

    Args:
        deal_id: 기업 ID
        periods: 예측 기간 (7-90일)
    """
    if not ml_predictor:
        raise HTTPException(status_code=503, detail="ML 예측기 미활성화")

    result = ml_predictor.predict(deal_id, periods)

    return {
        "success": True,
        "data": result
    }


@app.post("/api/v2/predict/train/{deal_id}")
async def train_prediction_model(
    deal_id: str,
    historical_days: int = Query(default=365, ge=30, le=730)
):
    """
    예측 모델 학습

    Args:
        deal_id: 기업 ID
        historical_days: 학습 데이터 기간 (30-730일)
    """
    if not ml_predictor:
        raise HTTPException(status_code=503, detail="ML 예측기 미활성화")

    if not ml_predictor.is_available:
        return {
            "success": False,
            "error": "Prophet 라이브러리 미설치. pip install prophet",
            "is_fallback": True
        }

    result = ml_predictor.train_model(deal_id, historical_days)

    return {
        "success": result.get("success", False),
        "data": result
    }


@app.get("/api/v2/predict/models")
async def list_prediction_models():
    """저장된 예측 모델 목록"""
    if not ml_predictor:
        return {"models": [], "count": 0}

    models = ml_predictor.list_models()
    return {
        "models": models,
        "count": len(models),
        "prophet_available": ml_predictor.is_available
    }


@app.delete("/api/v2/predict/models/{deal_id}")
async def delete_prediction_model(deal_id: str):
    """예측 모델 삭제"""
    if not ml_predictor:
        raise HTTPException(status_code=503, detail="ML 예측기 미활성화")

    success = ml_predictor.delete_model(deal_id)

    return {
        "success": success,
        "message": f"모델 삭제 {'성공' if success else '실패'}: {deal_id}"
    }


# ============================================
# V3 API: Status 중심 + 점수 투명화
# ============================================

# V3 Pydantic 모델
class ScoreBreakdownResponse(BaseModel):
    """점수 상세 응답"""
    companyId: str
    companyName: str
    totalScore: int
    status: str
    directScore: int
    propagatedScore: int
    categories: List[Dict]
    recentSignals: List[Dict]
    lastUpdated: str


class StatusSummaryResponse(BaseModel):
    """Status별 요약 응답"""
    pass_count: int
    warning_count: int
    fail_count: int
    companies: Dict[str, List[Dict]]


# ============================================
# 스케줄러 제어 API (v3)
# ============================================

# 전역 스케줄러 인스턴스
_scheduler_instance = None

def get_scheduler():
    """스케줄러 싱글톤 인스턴스"""
    global _scheduler_instance
    if _scheduler_instance is None:
        try:
            from .scheduler import CollectionScheduler
            _scheduler_instance = CollectionScheduler()
        except ImportError:
            pass
    return _scheduler_instance


@app.get("/api/v3/scheduler/status")
async def get_scheduler_status():
    """스케줄러 상태 조회"""
    scheduler = get_scheduler()

    if not scheduler:
        return {
            "is_available": False,
            "is_running": False,
            "message": "스케줄러 모듈 로드 실패. pip install apscheduler"
        }

    status = scheduler.get_job_status() if hasattr(scheduler, 'get_job_status') else {}

    return {
        "is_available": scheduler.is_available,
        "is_running": scheduler.is_running,
        "jobs": status.get('jobs', []),
        "recent_history": status.get('history', [])[:10]
    }


@app.post("/api/v3/scheduler/start")
async def start_scheduler():
    """스케줄러 시작"""
    scheduler = get_scheduler()

    if not scheduler:
        raise HTTPException(status_code=503, detail="스케줄러 모듈 로드 실패")

    if not scheduler.is_available:
        raise HTTPException(status_code=503, detail="APScheduler 미설치")

    if scheduler.is_running:
        return {"success": True, "message": "스케줄러가 이미 실행 중입니다"}

    if scheduler.start():
        return {"success": True, "message": "스케줄러 시작됨"}
    else:
        raise HTTPException(status_code=500, detail="스케줄러 시작 실패")


@app.post("/api/v3/scheduler/stop")
async def stop_scheduler():
    """스케줄러 중지"""
    scheduler = get_scheduler()

    if not scheduler:
        raise HTTPException(status_code=503, detail="스케줄러 없음")

    scheduler.stop()
    return {"success": True, "message": "스케줄러 중지됨"}


@app.post("/api/v3/scheduler/trigger/{job_type}")
async def trigger_scheduler_job(job_type: str):
    """특정 작업 수동 실행"""
    scheduler = get_scheduler()

    if not scheduler:
        raise HTTPException(status_code=503, detail="스케줄러 없음")

    valid_jobs = ["dart_collect", "news_collect", "score_update", "full_sync"]
    if job_type not in valid_jobs:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 작업: {job_type}. 가능: {valid_jobs}")

    if hasattr(scheduler, 'trigger_job'):
        result = scheduler.trigger_job(job_type)
        return {"success": True, "message": f"{job_type} 작업 트리거됨", "result": result}
    else:
        raise HTTPException(status_code=501, detail="trigger_job 미지원")


@app.get("/api/v3/status/summary")
async def get_status_summary():
    """
    V3: Status별 기업 요약

    Returns:
        - PASS/WARNING/FAIL별 기업 수 및 목록
    """
    if USE_MOCK_DATA or not NEO4J_CLIENT_AVAILABLE:
        # Mock 데이터 반환
        return {
            "summary": {
                "PASS": 2,
                "WARNING": 1,
                "FAIL": 1,
                "total": 4
            },
            "companies": {
                "PASS": [
                    {"id": "samsung", "name": "삼성전자", "score": 35, "sector": "전자"},
                    {"id": "hyundai", "name": "현대자동차", "score": 42, "sector": "자동차"}
                ],
                "WARNING": [
                    {"id": "sk_hynix", "name": "SK하이닉스", "score": 58, "sector": "반도체"}
                ],
                "FAIL": [
                    {"id": "hanmi", "name": "한미반도체", "score": 82, "sector": "반도체장비"}
                ]
            },
            "updatedAt": datetime.now().isoformat()
        }

    try:
        # Neo4j에서 Status별 기업 조회
        query = """
        MATCH (c:Company)-[:HAS_STATUS]->(s:Status)
        RETURN s.id AS status,
               collect({
                   id: c.id,
                   name: c.name,
                   score: c.totalRiskScore,
                   sector: c.sector
               }) AS companies,
               count(c) AS count
        ORDER BY CASE s.id WHEN 'FAIL' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END
        """
        results = neo4j_client.execute_read(query)

        summary = {"PASS": 0, "WARNING": 0, "FAIL": 0, "total": 0}
        companies = {"PASS": [], "WARNING": [], "FAIL": []}

        for r in results:
            status = r.get("status", "PASS")
            count = r.get("count", 0)
            company_list = r.get("companies", [])

            summary[status] = count
            summary["total"] += count
            companies[status] = company_list

        return {
            "summary": summary,
            "companies": companies,
            "updatedAt": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Status 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/companies/{company_id}/score")
async def get_company_score_breakdown(company_id: str):
    """
    V3: 기업 점수 상세 (breakdown 포함)

    Returns:
        - 직접 리스크 vs 전이 리스크 분해
        - 카테고리별 점수
        - 최근 신호 목록
    """
    if USE_MOCK_DATA or not NEO4J_CLIENT_AVAILABLE:
        # Mock 점수 breakdown
        return {
            "companyId": company_id,
            "companyName": deal_id_to_name(company_id),
            "totalScore": 68,
            "status": "WARNING",
            "breakdown": {
                "directScore": 56,
                "propagatedScore": 12,
                "directWeight": 0.82,
                "propagatedWeight": 0.18
            },
            "categories": [
                {"category": "법률위험", "score": 35, "weight": 0.20, "signals": 2},
                {"category": "신용위험", "score": 25, "weight": 0.25, "signals": 1},
                {"category": "운영위험", "score": 15, "weight": 0.15, "signals": 1},
                {"category": "시장위험", "score": 10, "weight": 0.15, "signals": 0},
                {"category": "공급망위험", "score": 12, "weight": 0.15, "signals": 1},
                {"category": "ESG위험", "score": 5, "weight": 0.10, "signals": 0}
            ],
            "recentSignals": [
                {"id": "sig1", "type": "DART", "title": "특허 소송 공시", "score": 25, "date": "2026-02-05"},
                {"id": "sig2", "type": "NEWS", "title": "공급망 차질 보도", "score": 15, "date": "2026-02-04"}
            ],
            "propagators": [
                {"company": "한미반도체", "relation": "SUPPLIES_TO", "contribution": 12, "tier": 1}
            ],
            "lastUpdated": datetime.now().isoformat()
        }

    try:
        # RiskCalculatorV3 사용 (복잡한 데이터 구조가 있을 때만)
        if RISK_CALCULATOR_V3_AVAILABLE:
            try:
                calculator = RiskCalculatorV3(neo4j_client)
                breakdown = calculator.calculate_total_risk(company_id)

                # RiskCalculatorV3가 유효한 점수를 반환한 경우에만 사용
                if breakdown.total_score > 0 or breakdown.direct_breakdown:
                    # direct_breakdown을 categories 형식으로 변환
                    categories = [
                        {"name": cat.category, "score": int(cat.weighted_score), "weight": cat.weight}
                        for cat in breakdown.direct_breakdown
                    ] if breakdown.direct_breakdown else []

                    # propagated_breakdown을 propagators 형식으로 변환
                    propagators = [
                        {"companyName": prop.source_name, "contribution": round(prop.propagated, 2)}
                        for prop in breakdown.propagated_breakdown
                    ] if breakdown.propagated_breakdown else []

                    return {
                        "companyId": company_id,
                        "companyName": breakdown.company_name,
                        "totalScore": breakdown.total_score,
                        "status": breakdown.status,
                        "breakdown": {
                            "directScore": breakdown.direct_score,
                            "propagatedScore": breakdown.propagated_score,
                            "directWeight": round(breakdown.direct_score / max(breakdown.total_score, 1), 2),
                            "propagatedWeight": round(breakdown.propagated_score / max(breakdown.total_score, 1), 2)
                        },
                        "categories": categories,
                        "recentSignals": [],  # RiskCalculatorV3는 signals를 반환하지 않음
                        "propagators": propagators,
                        "lastUpdated": datetime.now().isoformat()
                    }
            except Exception as calc_error:
                logger.warning(f"RiskCalculatorV3 실패, Fallback 사용: {calc_error}")
                # Fallback to simple query below

        # Fallback: 기본 Neo4j 쿼리 (categories, signals, propagators 포함)
        query = """
        MATCH (c:Company {id: $companyId})
        OPTIONAL MATCH (c)-[:HAS_STATUS]->(st:Status)
        OPTIONAL MATCH (c)<-[:DETECTED_IN]-(sig:Signal)
        OPTIONAL MATCH (c)-[:HAS_CATEGORY]->(cat:RiskCategory)
        OPTIONAL MATCH (supplier:Company)-[sr:SUPPLIES_TO]->(c)
        WITH c, st,
             collect(DISTINCT sig)[0..5] AS signals,
             collect(DISTINCT cat) AS categories,
             collect(DISTINCT {name: supplier.name, contribution: sr.riskTransfer * 100}) AS propagators
        RETURN c.id AS id, c.name AS name,
               c.totalRiskScore AS score,
               c.directRiskScore AS directScore,
               c.propagatedRiskScore AS propagatedScore,
               COALESCE(c.status, st.id, 'PASS') AS status,
               [sig IN signals WHERE sig IS NOT NULL | {
                   id: sig.id,
                   type: sig.source,
                   title: sig.title,
                   score: sig.score,
                   severity: sig.severity,
                   date: toString(sig.detectedAt)
               }] AS recentSignals,
               [cat IN categories WHERE cat IS NOT NULL | {
                   name: cat.name,
                   score: cat.score,
                   weight: cat.weight
               }] AS categories,
               [p IN propagators WHERE p.name IS NOT NULL | {
                   companyName: p.name,
                   contribution: p.contribution
               }] AS propagators
        """
        result = neo4j_client.execute_read_single(query, {"companyId": company_id})

        if not result:
            raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {company_id}")

        return {
            "companyId": result.get("id"),
            "companyName": result.get("name"),
            "totalScore": result.get("score", 0) or 0,
            "status": result.get("status", "PASS"),
            "breakdown": {
                "directScore": result.get("directScore", 0) or 0,
                "propagatedScore": result.get("propagatedScore", 0) or 0
            },
            "categories": result.get("categories", []),
            "recentSignals": result.get("recentSignals", []),
            "propagators": result.get("propagators", []),
            "lastUpdated": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"점수 breakdown 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/companies/{company_id}/news")
async def get_company_news(
    company_id: str,
    limit: int = Query(default=20, le=50)
):
    """
    V3: 기업 관련 뉴스 조회

    Returns:
        - 최근 수집된 뉴스 목록
        - 키워드 매칭 결과 포함
    """
    company_name = deal_id_to_name(company_id)

    if USE_MOCK_DATA or not COLLECTORS_V2_AVAILABLE:
        # Mock 뉴스 데이터
        return {
            "companyId": company_id,
            "companyName": company_name,
            "news": [
                {
                    "id": "news1",
                    "title": f"{company_name} 특허 분쟁 관련 소식",
                    "source": "뉴스A",
                    "url": "https://example.com/news1",
                    "publishedAt": "2026-02-05T10:00:00",
                    "keywords": ["특허", "소송"],
                    "riskScore": 25,
                    "sentiment": "negative"
                },
                {
                    "id": "news2",
                    "title": f"{company_name} 신규 투자 발표",
                    "source": "뉴스B",
                    "url": "https://example.com/news2",
                    "publishedAt": "2026-02-04T15:30:00",
                    "keywords": [],
                    "riskScore": 0,
                    "sentiment": "positive"
                }
            ],
            "total": 2,
            "lastCollected": datetime.now().isoformat()
        }

    try:
        # NewsCollectorV2로 실제 뉴스 수집
        collector = NewsCollectorV2()
        result = collector.collect_news(company_name, limit=limit)

        news_list = []
        for item in result.items:
            news_list.append({
                "id": item.id,
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "publishedAt": item.published_at.isoformat() if item.published_at else None,
                "keywords": item.matched_keywords,
                "riskScore": item.risk_score,
                "sentiment": item.sentiment
            })

        return {
            "companyId": company_id,
            "companyName": company_name,
            "news": news_list,
            "total": result.total_count,
            "riskNewsCount": result.risk_count,
            "lastCollected": result.collected_at.isoformat() if result.collected_at else datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"뉴스 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/data-quality")
async def get_data_quality():
    """
    V3: 데이터 수집 현황

    Returns:
        - 소스별 수집 통계
        - 최근 수집 시간
        - 데이터 품질 지표
    """
    if USE_MOCK_DATA or not NEO4J_CLIENT_AVAILABLE:
        return {
            "sources": {
                "DART": {
                    "totalCount": 1250,
                    "riskCount": 45,
                    "lastCollected": "2026-02-06T08:30:00",
                    "status": "healthy"
                },
                "NEWS": {
                    "totalCount": 3200,
                    "riskCount": 180,
                    "lastCollected": "2026-02-06T09:00:00",
                    "status": "healthy"
                },
                "KIND": {
                    "totalCount": 850,
                    "riskCount": 22,
                    "lastCollected": "2026-02-06T08:45:00",
                    "status": "healthy"
                }
            },
            "quality": {
                "completeness": 0.95,
                "freshness": 0.92,
                "accuracy": 0.88
            },
            "companies": {
                "total": 150,
                "withSignals": 45,
                "withoutSignals": 105
            },
            "lastFullSync": "2026-02-06T06:00:00",
            "nextScheduledSync": "2026-02-06T12:00:00"
        }

    try:
        # 소스별 통계 조회
        query = """
        MATCH (sig:Signal)
        WITH sig.source AS source, count(sig) AS total,
             sum(CASE WHEN sig.riskScore > 0 THEN 1 ELSE 0 END) AS riskCount,
             max(sig.detectedAt) AS lastDetected
        RETURN source, total, riskCount, toString(lastDetected) AS lastCollected
        """
        source_results = neo4j_client.execute_read(query)

        sources = {}
        for r in source_results:
            source = r.get("source", "UNKNOWN")
            sources[source] = {
                "totalCount": r.get("total", 0),
                "riskCount": r.get("riskCount", 0),
                "lastCollected": r.get("lastCollected"),
                "status": "healthy" if r.get("lastCollected") else "stale"
            }

        # 기업 통계
        company_query = """
        MATCH (c:Company)
        OPTIONAL MATCH (c)<-[:DETECTED_IN]-(sig:Signal)
        WITH c, count(sig) AS signalCount
        RETURN count(c) AS total,
               sum(CASE WHEN signalCount > 0 THEN 1 ELSE 0 END) AS withSignals
        """
        company_result = neo4j_client.execute_read_single(company_query)

        total_companies = company_result.get("total", 0) if company_result else 0
        with_signals = company_result.get("withSignals", 0) if company_result else 0

        return {
            "sources": sources,
            "quality": {
                "completeness": 0.95,
                "freshness": 0.92,
                "accuracy": 0.88
            },
            "companies": {
                "total": total_companies,
                "withSignals": with_signals,
                "withoutSignals": total_companies - with_signals
            },
            "lastFullSync": datetime.now().isoformat(),
            "nextScheduledSync": None
        }

    except Exception as e:
        logger.error(f"데이터 품질 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/refresh/{company_id}")
async def refresh_company_data(company_id: str):
    """
    V3: 특정 기업 데이터 갱신

    - DART 공시 재수집
    - NEWS 재수집
    - 리스크 점수 재계산
    """
    company_name = deal_id_to_name(company_id)

    if USE_MOCK_DATA:
        return {
            "success": True,
            "companyId": company_id,
            "companyName": company_name,
            "refreshed": {
                "dart": {"collected": 5, "riskSignals": 1},
                "news": {"collected": 12, "riskSignals": 3}
            },
            "newScore": 65,
            "previousScore": 68,
            "status": "WARNING",
            "refreshedAt": datetime.now().isoformat()
        }

    results = {
        "dart": {"collected": 0, "riskSignals": 0},
        "news": {"collected": 0, "riskSignals": 0}
    }

    try:
        # DART 수집
        if COLLECTORS_V2_AVAILABLE:
            dart_collector = DartCollectorV2()

            # corp_code 조회 (간소화)
            if NEO4J_CLIENT_AVAILABLE:
                query = "MATCH (c:Company {id: $id}) RETURN c.corpCode AS corpCode"
                result = neo4j_client.execute_read_single(query, {"id": company_id})
                corp_code = result.get("corpCode") if result else None

                if corp_code:
                    dart_result = dart_collector.collect_disclosures(corp_code, days=7)
                    results["dart"]["collected"] = dart_result.total_count
                    results["dart"]["riskSignals"] = dart_result.risk_count

            # NEWS 수집
            news_collector = NewsCollectorV2()
            news_result = news_collector.collect_news(company_name, limit=20)
            results["news"]["collected"] = news_result.total_count
            results["news"]["riskSignals"] = news_result.risk_count

        # 점수 재계산
        new_score = 0
        previous_score = 0
        status = "PASS"

        if RISK_CALCULATOR_V3_AVAILABLE and NEO4J_CLIENT_AVAILABLE:
            # 이전 점수 조회
            prev_query = "MATCH (c:Company {id: $id}) RETURN c.totalRiskScore AS score"
            prev_result = neo4j_client.execute_read_single(prev_query, {"id": company_id})
            previous_score = prev_result.get("score", 0) if prev_result else 0

            # 새 점수 계산
            calculator = RiskCalculatorV3(neo4j_client)
            breakdown = calculator.calculate_total_risk(company_id)
            new_score = breakdown.total_score
            status = breakdown.status

        return {
            "success": True,
            "companyId": company_id,
            "companyName": company_name,
            "refreshed": results,
            "newScore": new_score,
            "previousScore": previous_score,
            "scoreDelta": new_score - previous_score,
            "status": status,
            "refreshedAt": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"데이터 갱신 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/companies/{company_id}/supply-chain")
async def get_supply_chain_v3(company_id: str):
    """
    V3: 공급망 그래프 조회

    Returns:
        - nodes: 공급망 내 모든 기업 노드
        - edges: 공급 관계
        - centerNode: 중심 기업
        - totalPropagatedRisk: 전이 리스크 합계
    """
    # 항상 Mock 데이터 또는 load_supply_chain_data의 함수 사용
    try:
        from .load_supply_chain_data import get_supply_chain_for_company
        result = get_supply_chain_for_company(company_id)
        if result and result.get("nodes"):
            return result
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"공급망 조회 실패, Mock 사용: {e}")

    # Mock 데이터 반환
    return get_mock_supply_chain()


@app.get("/api/v3/keywords")
async def get_keyword_dictionary():
    """
    V3: 키워드 사전 조회

    Returns:
        - DART/NEWS/KIND 키워드 목록
        - 각 키워드의 가중치
    """
    if not KEYWORDS_AVAILABLE:
        return {
            "available": False,
            "message": "키워드 엔진이 로드되지 않았습니다"
        }

    return {
        "available": True,
        "dart": {k: v for k, v in DART_RISK_KEYWORDS.items()},
        "news": {k: v for k, v in NEWS_RISK_KEYWORDS.items()},
        "totalCount": len(DART_RISK_KEYWORDS) + len(NEWS_RISK_KEYWORDS)
    }


# ============================================
# Supply Chain Discovery 엔드포인트 (v3.1)
# ============================================

# Supply Chain Discovery 모듈
try:
    from .supply_chain_discovery import (
        SupplyChainDiscovery,
        run_discovery,
        MAJOR_KOREAN_COMPANIES,
        GLOBAL_PARTNERS,
    )
    DISCOVERY_AVAILABLE = True
except ImportError:
    DISCOVERY_AVAILABLE = False
    logger.warning("⚠️ Supply Chain Discovery 모듈 로드 실패")


@app.get("/api/v3/supply-chain/statistics")
async def get_supply_chain_statistics():
    """
    Supply Chain 데이터 통계

    Returns:
        기업 수, 관계 수, 산업별 분포
    """
    if not NEO4J_CLIENT_AVAILABLE:
        # Mock 통계
        return {
            "companies": {
                "korean": len(MAJOR_KOREAN_COMPANIES) if DISCOVERY_AVAILABLE else 50,
                "global": len(GLOBAL_PARTNERS) if DISCOVERY_AVAILABLE else 20,
                "total": 70
            },
            "relations": {
                "SUPPLIES_TO": 85,
                "COMPETES_WITH": 25,
                "PARTNER_OF": 15,
                "total": 125
            },
            "sectors": {
                "반도체": 12,
                "자동차": 10,
                "배터리": 8,
                "화학": 7,
                "IT": 6,
                "기타": 27
            },
            "lastUpdated": datetime.now().isoformat()
        }

    try:
        neo4j_client.connect()

        # 기업 수
        company_query = """
        MATCH (c:Company)
        RETURN count(c) AS total,
               count(CASE WHEN c.isGlobal = true THEN 1 END) AS global,
               count(CASE WHEN c.isGlobal IS NULL OR c.isGlobal = false THEN 1 END) AS korean
        """
        company_result = neo4j_client.execute_read_single(company_query)

        # 관계 수
        relation_query = """
        MATCH ()-[r]->()
        WHERE type(r) IN ['SUPPLIES_TO', 'COMPETES_WITH', 'PARTNER_OF', 'SUBSIDIARY_OF']
        RETURN type(r) AS relType, count(r) AS count
        """
        relation_results = neo4j_client.execute_read(relation_query)
        relations = {r["relType"]: r["count"] for r in relation_results}
        relations["total"] = sum(relations.values())

        # 산업별 분포
        sector_query = """
        MATCH (c:Company)
        RETURN c.sector AS sector, count(c) AS count
        ORDER BY count DESC
        """
        sector_results = neo4j_client.execute_read(sector_query)
        sectors = {r["sector"] or "기타": r["count"] for r in sector_results}

        return {
            "companies": {
                "korean": company_result["korean"] if company_result else 0,
                "global": company_result["global"] if company_result else 0,
                "total": company_result["total"] if company_result else 0
            },
            "relations": relations,
            "sectors": sectors,
            "lastUpdated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j_client.close()


@app.post("/api/v3/supply-chain/discover")
async def discover_supply_chain(
    target_companies: List[str] = None,
    save_to_db: bool = True
):
    """
    Supply Chain 자동 탐색 실행

    Args:
        target_companies: 탐색 대상 기업 목록 (None이면 전체)
        save_to_db: Neo4j에 저장 여부

    Returns:
        탐색 결과 통계
    """
    if not DISCOVERY_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Supply Chain Discovery 모듈이 설치되지 않았습니다"
        )

    try:
        # 수집기 준비
        dart_collector = None
        news_collector = None

        try:
            from .dart_collector_v2 import DartCollectorV2
            dart_collector = DartCollectorV2()
        except:
            logger.warning("DART 수집기 미사용 (API 키 없음)")

        try:
            from .news_collector_v2 import NewsCollectorV2
            news_collector = NewsCollectorV2()
        except:
            logger.warning("뉴스 수집기 미사용")

        # Discovery 실행
        discovery = SupplyChainDiscovery(
            neo4j_client=neo4j_client if NEO4J_CLIENT_AVAILABLE and save_to_db else None,
            dart_collector=dart_collector,
            news_collector=news_collector,
        )

        relations = discovery.discover_all(target_companies)

        # Neo4j에 저장
        saved_count = 0
        if save_to_db and NEO4J_CLIENT_AVAILABLE:
            neo4j_client.connect()
            saved_count = discovery.save_to_neo4j()
            neo4j_client.close()

        stats = discovery.get_statistics()
        stats["saved_to_neo4j"] = saved_count

        return {
            "success": True,
            "message": f"{stats['total_relations']}개 관계 발견, {saved_count}개 저장",
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Supply Chain Discovery 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/supply-chain/expand")
async def expand_supply_chain_data():
    """
    Supply Chain 데이터 확장 (샘플 + Discovery)

    기존 샘플 데이터를 확장하고 자동 탐색을 실행합니다.

    Returns:
        확장 결과
    """
    if not NEO4J_CLIENT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Neo4j 연결이 필요합니다"
        )

    try:
        neo4j_client.connect()
        results = {
            "steps": [],
            "total_companies": 0,
            "total_relations": 0,
        }

        # 1. 기존 샘플 데이터 로드
        try:
            from .load_supply_chain_data import load_supply_chain_data
            load_supply_chain_data()
            results["steps"].append({"step": "load_sample_data", "status": "success"})
        except Exception as e:
            results["steps"].append({"step": "load_sample_data", "status": "failed", "error": str(e)})

        # 2. Discovery 실행
        if DISCOVERY_AVAILABLE:
            try:
                discovery = SupplyChainDiscovery(neo4j_client=neo4j_client)
                relations = discovery.discover_all()
                saved = discovery.save_to_neo4j()
                results["steps"].append({
                    "step": "discovery",
                    "status": "success",
                    "discovered": len(relations),
                    "saved": saved
                })
            except Exception as e:
                results["steps"].append({"step": "discovery", "status": "failed", "error": str(e)})

        # 3. 통계 업데이트
        stats_query = """
        MATCH (c:Company)
        OPTIONAL MATCH (c)-[r]->()
        RETURN count(DISTINCT c) AS companies, count(DISTINCT r) AS relations
        """
        stats = neo4j_client.execute_read_single(stats_query)
        results["total_companies"] = stats["companies"] if stats else 0
        results["total_relations"] = stats["relations"] if stats else 0

        results["success"] = True
        results["timestamp"] = datetime.now().isoformat()

        return results

    except Exception as e:
        logger.error(f"데이터 확장 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j_client.close()


@app.get("/api/v3/companies/list")
async def get_all_companies(
    sector: str = None,
    status: str = None,
    limit: int = 100
):
    """
    전체 기업 목록 조회

    Args:
        sector: 산업 필터 (선택)
        status: 상태 필터 (PASS, WARNING, FAIL)
        limit: 최대 조회 수

    Returns:
        기업 목록
    """
    if not NEO4J_CLIENT_AVAILABLE:
        # Mock 데이터
        if DISCOVERY_AVAILABLE:
            companies = []
            for name, info in list(MAJOR_KOREAN_COMPANIES.items())[:limit]:
                companies.append({
                    "id": name,
                    "name": name,
                    "sector": info["sector"],
                    "corpCode": info.get("corpCode", ""),
                    "riskScore": 30 + hash(name) % 50,
                    "status": "WARNING" if hash(name) % 3 == 1 else "PASS"
                })
            return {"companies": companies, "total": len(companies)}
        return {"companies": [], "total": 0}

    try:
        neo4j_client.connect()

        where_clauses = []
        params = {"limit": limit}

        if sector:
            where_clauses.append("c.sector = $sector")
            params["sector"] = sector

        if status:
            where_clauses.append("c.status = $status")
            params["status"] = status

        where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
        MATCH (c:Company)
        {where_str}
        RETURN c.id AS id, c.name AS name, c.sector AS sector,
               c.corpCode AS corpCode, c.totalRiskScore AS riskScore,
               c.status AS status, c.isGlobal AS isGlobal
        ORDER BY c.totalRiskScore DESC
        LIMIT $limit
        """

        results = neo4j_client.execute_read(query, params)
        companies = [dict(r) for r in results]

        # 총 수 조회
        count_query = f"""
        MATCH (c:Company)
        {where_str}
        RETURN count(c) AS total
        """
        count_result = neo4j_client.execute_read_single(count_query, params)

        return {
            "companies": companies,
            "total": count_result["total"] if count_result else len(companies)
        }

    except Exception as e:
        logger.error(f"기업 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j_client.close()


# ============================================
# 메인 실행
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "risk_engine.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
