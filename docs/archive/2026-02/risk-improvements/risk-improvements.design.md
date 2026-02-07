# Risk Monitoring System - 개선 설계서

> **기능명**: risk-improvements
> **버전**: v2.2
> **작성일**: 2026-02-05
> **기반 Plan**: `/docs/01-plan/features/risk-improvements.plan.md`

---

## 1. 설계 개요

### 1.1 목적

risk v2.1의 개선 필요 영역을 구현하기 위한 상세 기술 설계서입니다. Phase 2 (실제 데이터 연동)에 집중하며, 이후 Phase에 대한 설계 방향을 제시합니다.

### 1.2 설계 범위

| Phase | 범위 | 이 문서에서 |
|-------|------|------------|
| Phase 2 | Neo4j, OpenAI, WebSocket | **상세 설계** |
| Phase 3 | ML 예측, 커스텀 시나리오 | 방향 제시 |
| Phase 4-5 | 자동화, 제품화 | 아키텍처만 |

---

## 2. Phase 2: 실제 데이터 연동 설계

### 2.1 Neo4j 데이터 연동

#### 2.1.1 환경 설정

**파일**: `.env.local`

```bash
# Neo4j 연결 설정
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=dealvalidator

# 연결 풀 설정
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=30000
```

**파일**: `risk_engine/neo4j_client.py`

```python
from neo4j import GraphDatabase
from contextlib import contextmanager
import os

class Neo4jClient:
    """Neo4j 연결 관리 클라이언트"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
        return cls._instance

    def connect(self):
        """드라이버 초기화"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI"),
                auth=(
                    os.getenv("NEO4J_USERNAME"),
                    os.getenv("NEO4J_PASSWORD")
                ),
                max_connection_pool_size=int(
                    os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", 50)
                )
            )
        return self

    def close(self):
        """연결 종료"""
        if self._driver:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self):
        """세션 컨텍스트 매니저"""
        session = self._driver.session(
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        try:
            yield session
        finally:
            session.close()

    def execute_read(self, query: str, params: dict = None):
        """읽기 쿼리 실행"""
        with self.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def execute_write(self, query: str, params: dict = None):
        """쓰기 쿼리 실행"""
        with self.session() as session:
            result = session.run(query, params or {})
            return result.consume().counters

# 싱글톤 인스턴스
neo4j_client = Neo4jClient()
```

#### 2.1.2 데이터 로드 스크립트

**파일**: `scripts/load_dart_data.py`

```python
"""DART 전자공시 데이터 → Neo4j 로드"""

import requests
from risk_engine.neo4j_client import neo4j_client

DART_API_KEY = os.getenv("OPENDART_API_KEY")
DART_BASE_URL = "https://opendart.fss.or.kr/api"

def fetch_company_list():
    """상장사 목록 조회"""
    url = f"{DART_BASE_URL}/corpCode.xml"
    params = {"crtfc_key": DART_API_KEY}
    # ... 구현

def fetch_financial_statements(corp_code: str):
    """재무제표 조회"""
    url = f"{DART_BASE_URL}/fnlttSinglAcnt.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": "2025",
        "reprt_code": "11011"  # 사업보고서
    }
    # ... 구현

def load_to_neo4j(companies: list):
    """Neo4j에 기업 데이터 로드"""
    neo4j_client.connect()

    # 기업 노드 생성
    create_query = """
    UNWIND $companies AS company
    MERGE (c:Company {corpCode: company.corp_code})
    SET c.name = company.corp_name,
        c.sector = company.sector,
        c.stockCode = company.stock_code,
        c.totalRiskScore = 50,  // 초기값
        c.updatedAt = datetime()
    """

    neo4j_client.execute_write(create_query, {"companies": companies})

if __name__ == "__main__":
    companies = fetch_company_list()
    load_to_neo4j(companies)
    print(f"✅ {len(companies)}개 기업 로드 완료")
```

**파일**: `scripts/load_news_data.py`

```python
"""뉴스 크롤링 데이터 → Neo4j 로드"""

from risk_engine.neo4j_client import neo4j_client

def load_news_articles(articles: list):
    """뉴스 기사 → Neo4j 로드"""

    create_query = """
    UNWIND $articles AS article
    MERGE (n:NewsArticle {id: article.id})
    SET n.title = article.title,
        n.content = article.content,
        n.sentiment = article.sentiment,
        n.riskScore = article.risk_score,
        n.publishedAt = datetime(article.published_at),
        n.source = article.source

    WITH n, article
    UNWIND article.mentioned_companies AS companyName
    MATCH (c:Company {name: companyName})
    MERGE (n)-[:MENTIONS]->(c)
    """

    neo4j_client.execute_write(create_query, {"articles": articles})
```

#### 2.1.3 API 연동 수정

**파일**: `risk_engine/api.py` (수정)

```python
from risk_engine.neo4j_client import neo4j_client
from risk_engine.mock_data import MOCK_DEALS  # fallback용

# 환경 변수로 Mock/실제 전환
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

@app.get("/api/v2/deals/{deal_id}/supply-chain")
async def get_supply_chain(deal_id: str):
    """공급망 그래프 조회"""

    if USE_MOCK_DATA:
        # 기존 Mock 데이터 반환
        return mock_supply_chain(deal_id)

    # Neo4j 실제 쿼리
    query = """
    MATCH (target:Company {id: $dealId})
    OPTIONAL MATCH (target)<-[r1:SUPPLIES_TO]-(supplier:Company)
    OPTIONAL MATCH (target)-[r2:SUPPLIES_TO]->(customer:Company)
    RETURN target,
           collect(DISTINCT {node: supplier, rel: r1, type: 'supplier'}) as suppliers,
           collect(DISTINCT {node: customer, rel: r2, type: 'customer'}) as customers
    """

    try:
        neo4j_client.connect()
        result = neo4j_client.execute_read(query, {"dealId": deal_id})
        return format_supply_chain_response(result)
    except Exception as e:
        logger.error(f"Neo4j 쿼리 실패: {e}")
        # Fallback to mock
        return mock_supply_chain(deal_id)
```

### 2.2 OpenAI API 연동

#### 2.2.1 환경 설정

**파일**: `.env.local` (추가)

```bash
# OpenAI 설정
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.7

# 비용 제어
OPENAI_DAILY_LIMIT_USD=50
OPENAI_CACHE_TTL_SECONDS=3600
```

#### 2.2.2 AI 서비스 구현

**파일**: `risk_engine/ai_service_v2.py`

```python
"""AI 서비스 v2 - OpenAI 실제 연동"""

from openai import OpenAI
from functools import lru_cache
import hashlib
import json
import os

class AIService:
    """6대 AI 기능 구현"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", 2000))
        self.cache = {}  # 간단한 메모리 캐시

    def _get_cache_key(self, func_name: str, params: dict) -> str:
        """캐시 키 생성"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{func_name}:{param_str}".encode()).hexdigest()

    def _call_gpt(self, system_prompt: str, user_prompt: str) -> str:
        """GPT API 호출"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=float(os.getenv("OPENAI_TEMPERATURE", 0.7))
        )
        return response.choices[0].message.content

    # ========================================
    # 1. 뉴스 자동 분석
    # ========================================
    def analyze_news(self, news_content: str) -> dict:
        """뉴스 본문 → 리스크 분석"""

        system_prompt = """당신은 금융 리스크 분석 전문가입니다.
주어진 뉴스 기사를 분석하여 JSON 형식으로 응답하세요:
{
  "severity": 1-5 (1=낮음, 5=매우높음),
  "category": "financial|legal|governance|supply_chain|market|reputation|operational|macro",
  "affected_companies": ["회사명1", "회사명2"],
  "summary": "한 줄 요약",
  "risk_factors": ["리스크1", "리스크2"]
}"""

        result = self._call_gpt(system_prompt, news_content)
        return json.loads(result)

    # ========================================
    # 2. 리스크 요약
    # ========================================
    def summarize_risk(self, deal_data: dict) -> dict:
        """딜 데이터 → 리스크 요약"""

        system_prompt = """당신은 PE/IB 심사역입니다.
주어진 딜 데이터를 분석하여 JSON 형식으로 응답하세요:
{
  "one_liner": "한 문장 요약",
  "key_risks": ["핵심 리스크1", "핵심 리스크2", "핵심 리스크3"],
  "recommendation": "권장 행동",
  "confidence": 0.0-1.0
}"""

        result = self._call_gpt(system_prompt, json.dumps(deal_data, ensure_ascii=False))
        return json.loads(result)

    # ========================================
    # 3. Text2Cypher
    # ========================================
    def text_to_cypher(self, natural_query: str) -> dict:
        """자연어 → Cypher 쿼리 변환"""

        system_prompt = """당신은 Neo4j Cypher 전문가입니다.
자연어 질문을 Cypher 쿼리로 변환하세요.

스키마:
- (:Company {name, sector, totalRiskScore, status})
- (:NewsArticle {title, sentiment, riskScore})
- (Company)-[:SUPPLIES_TO {dependency}]->(Company)
- (Company)-[:COMPETES_WITH]->(Company)
- (NewsArticle)-[:MENTIONS]->(Company)

규칙:
1. 읽기 전용 쿼리만 생성 (MATCH, RETURN만 사용)
2. DELETE, CREATE, SET 사용 금지
3. LIMIT 10 기본 적용

JSON 형식으로 응답:
{
  "cypher": "MATCH ... RETURN ...",
  "explanation": "쿼리 설명"
}"""

        result = self._call_gpt(system_prompt, natural_query)
        parsed = json.loads(result)

        # 보안: 위험한 키워드 검사
        dangerous_keywords = ["DELETE", "CREATE", "SET", "REMOVE", "DROP"]
        cypher_upper = parsed["cypher"].upper()
        for keyword in dangerous_keywords:
            if keyword in cypher_upper:
                raise ValueError(f"위험한 쿼리 감지: {keyword}")

        return parsed

    # ========================================
    # 4. 시나리오 해석
    # ========================================
    def interpret_simulation(self, simulation_result: dict) -> dict:
        """시뮬레이션 결과 → 비즈니스 해석"""

        system_prompt = """당신은 시나리오 분석 전문가입니다.
시뮬레이션 결과를 비즈니스 맥락에서 해석하세요.

JSON 형식으로 응답:
{
  "impact_summary": "영향 요약",
  "most_affected": "가장 큰 영향을 받는 영역",
  "action_items": ["조치1", "조치2", "조치3"],
  "timeline": "예상 영향 기간"
}"""

        result = self._call_gpt(system_prompt, json.dumps(simulation_result, ensure_ascii=False))
        return json.loads(result)

    # ========================================
    # 5. 전이 경로 설명
    # ========================================
    def explain_propagation(self, propagation_data: dict) -> dict:
        """리스크 전이 경로 → 비즈니스 설명"""

        system_prompt = """당신은 공급망 리스크 분석가입니다.
리스크 전이 경로를 비즈니스 맥락에서 설명하세요.

JSON 형식으로 응답:
{
  "pathway_explanation": "전이 경로 설명",
  "critical_nodes": ["핵심 노드1", "핵심 노드2"],
  "mitigation": "완화 방안"
}"""

        result = self._call_gpt(system_prompt, json.dumps(propagation_data, ensure_ascii=False))
        return json.loads(result)

    # ========================================
    # 6. 대응 전략 (RM/OPS 가이드)
    # ========================================
    def generate_action_guide(self, deal_data: dict, signal_type: str) -> dict:
        """상황별 RM/OPS 가이드 생성"""

        system_prompt = f"""당신은 PE/IB 리스크 관리 전문가입니다.
{signal_type} 상황에서의 대응 가이드를 작성하세요.

JSON 형식으로 응답:
{{
  "rm_guide": {{
    "summary": "RM 요약",
    "todo_list": ["할일1", "할일2", "할일3"],
    "talking_points": ["고객 대화 포인트1", "포인트2"]
  }},
  "ops_guide": {{
    "summary": "OPS 요약",
    "todo_list": ["할일1", "할일2", "할일3"],
    "financial_impact": "재무 영향 분석"
  }},
  "urgency": "immediate|within_24h|within_week"
}}"""

        result = self._call_gpt(system_prompt, json.dumps(deal_data, ensure_ascii=False))
        return json.loads(result)


# 싱글톤 인스턴스
ai_service = AIService()
```

#### 2.2.3 API 엔드포인트 추가

**파일**: `risk_engine/api.py` (추가)

```python
from risk_engine.ai_service_v2 import ai_service

@app.post("/api/v2/ai/analyze-news")
async def analyze_news(request: NewsAnalysisRequest):
    """뉴스 자동 분석"""
    try:
        result = ai_service.analyze_news(request.content)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/v2/ai/query")
async def text_to_cypher(request: TextQueryRequest):
    """Text2Cypher - 자연어 질의"""
    try:
        parsed = ai_service.text_to_cypher(request.query)

        # 쿼리 실행
        neo4j_client.connect()
        results = neo4j_client.execute_read(parsed["cypher"])

        return {
            "success": True,
            "data": {
                "cypher": parsed["cypher"],
                "explanation": parsed["explanation"],
                "results": results
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/v2/ai/guide/{deal_id}")
async def get_action_guide(deal_id: str, signal_type: str = "LEGAL_CRISIS"):
    """AI 대응 가이드"""
    try:
        # 딜 데이터 조회
        deal = await get_deal_detail(deal_id)

        # AI 가이드 생성
        guide = ai_service.generate_action_guide(deal, signal_type)
        return {"success": True, "data": guide}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 2.3 WebSocket 실시간 신호

#### 2.3.1 신호 발행 메커니즘

**파일**: `risk_engine/signal_publisher.py`

```python
"""실시간 신호 발행 시스템"""

import asyncio
from datetime import datetime
from typing import Set
from fastapi import WebSocket
import json

class SignalPublisher:
    """WebSocket 신호 발행자"""

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.running = False

    async def connect(self, websocket: WebSocket):
        """클라이언트 연결"""
        await websocket.accept()
        self.connections.add(websocket)
        print(f"✅ 클라이언트 연결됨. 총 {len(self.connections)}개")

    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        self.connections.discard(websocket)
        print(f"❌ 클라이언트 연결 해제. 총 {len(self.connections)}개")

    async def broadcast(self, signal: dict):
        """모든 클라이언트에 신호 브로드캐스트"""
        if not self.connections:
            return

        message = json.dumps(signal, ensure_ascii=False, default=str)

        disconnected = set()
        for websocket in self.connections:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)

        # 끊어진 연결 정리
        for ws in disconnected:
            self.disconnect(ws)

    async def start_polling(self):
        """데이터 소스 폴링 시작"""
        self.running = True

        while self.running:
            try:
                # 1. 뉴스 폴링 (10초 간격)
                news_signals = await self._poll_news()
                for signal in news_signals:
                    await self.broadcast(signal)

                # 2. DART 공시 폴링 (30초 간격)
                # ...

                await asyncio.sleep(10)
            except Exception as e:
                print(f"폴링 에러: {e}")
                await asyncio.sleep(5)

    async def _poll_news(self) -> list:
        """뉴스 소스 폴링"""
        # TODO: 실제 뉴스 API 연동
        # 현재는 예시 반환
        return []

    def stop(self):
        """폴링 중지"""
        self.running = False


# 싱글톤 인스턴스
signal_publisher = SignalPublisher()
```

#### 2.3.2 WebSocket 엔드포인트

**파일**: `risk_engine/api.py` (수정)

```python
from risk_engine.signal_publisher import signal_publisher

@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """실시간 신호 WebSocket"""
    await signal_publisher.connect(websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 대기 (heartbeat)
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")
    except Exception:
        pass
    finally:
        signal_publisher.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 폴링 시작"""
    asyncio.create_task(signal_publisher.start_polling())

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    signal_publisher.stop()
    neo4j_client.close()
```

#### 2.3.3 Frontend WebSocket 훅 수정

**파일**: `components/risk/hooks/useWebSocket.ts` (수정)

```typescript
import { useEffect, useRef, useState, useCallback } from 'react';
import { RiskSignal } from '../types';

interface UseWebSocketOptions {
  url: string;
  reconnectInterval?: number;
  maxRetries?: number;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const { url, reconnectInterval = 3000, maxRetries = 5 } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('✅ WebSocket 연결됨');
      setIsConnected(true);
      setError(null);
      retriesRef.current = 0;

      // Heartbeat 시작
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);

      ws.onclose = () => {
        clearInterval(heartbeat);
      };
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;

      try {
        const signal = JSON.parse(event.data) as RiskSignal;
        setSignals(prev => [signal, ...prev.slice(0, 99)]);
      } catch (e) {
        console.error('신호 파싱 에러:', e);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket 에러:', event);
      setError('연결 에러 발생');
    };

    ws.onclose = () => {
      console.log('❌ WebSocket 연결 종료');
      setIsConnected(false);

      // 재연결 시도
      if (retriesRef.current < maxRetries) {
        retriesRef.current++;
        setTimeout(connect, reconnectInterval);
      } else {
        setError('재연결 실패. 새로고침 필요.');
      }
    };

    wsRef.current = ws;
  }, [url, reconnectInterval, maxRetries]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { isConnected, signals, error };
}
```

---

## 3. 파일 구조

### 3.1 신규/수정 파일 목록

```
risk_engine/
├── neo4j_client.py        [신규] Neo4j 연결 클라이언트
├── ai_service_v2.py       [신규] AI 서비스 v2 (OpenAI 연동)
├── signal_publisher.py    [신규] WebSocket 신호 발행
├── api.py                 [수정] API 엔드포인트 추가
└── config.py              [신규] 환경 설정 관리

scripts/
├── load_dart_data.py      [신규] DART 데이터 로드
├── load_news_data.py      [신규] 뉴스 데이터 로드
└── setup_neo4j.py         [신규] Neo4j 스키마 초기화

components/risk/hooks/
└── useWebSocket.ts        [수정] 재연결 로직 강화

.env.local                 [신규] 환경 변수
```

### 3.2 의존성 추가

**파일**: `requirements.txt` (추가)

```
neo4j>=5.0.0
openai>=1.0.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
```

---

## 4. 구현 순서

### Phase 2 구현 체크리스트

```
Week 1: 데이터 연동
─────────────────────────────────────────
□ 1. .env.local 환경 변수 설정
□ 2. neo4j_client.py 구현
□ 3. load_dart_data.py 스크립트 작성
□ 4. load_news_data.py 스크립트 작성
□ 5. api.py Neo4j 연동 수정
□ 6. ai_service_v2.py 구현
□ 7. API 엔드포인트 AI 연동

Week 2: 실시간 기능
─────────────────────────────────────────
□ 8. signal_publisher.py 구현
□ 9. WebSocket 엔드포인트 추가
□ 10. useWebSocket.ts 재연결 로직
□ 11. 통합 테스트
□ 12. Mock/실제 전환 테스트
```

---

## 5. 테스트 계획

### 5.1 단위 테스트

| 모듈 | 테스트 항목 | 도구 |
|------|------------|------|
| neo4j_client | 연결, 쿼리, 에러 처리 | pytest |
| ai_service_v2 | 6대 기능 각각 | pytest + mocking |
| signal_publisher | 연결, 브로드캐스트 | pytest-asyncio |

### 5.2 통합 테스트

| 시나리오 | 검증 항목 |
|---------|---------|
| Neo4j → API → Frontend | 데이터 흐름 |
| OpenAI → API → Frontend | AI 응답 |
| WebSocket 연결 | 실시간 신호 |

---

## 6. 롤백 계획

### 6.1 Mock 데이터 폴백

```python
# api.py
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

if USE_MOCK_DATA:
    return mock_response()
else:
    try:
        return real_response()
    except Exception:
        return mock_response()  # 자동 폴백
```

### 6.2 환경 변수 전환

```bash
# Mock 모드로 전환 (문제 발생 시)
USE_MOCK_DATA=true

# 실제 모드로 전환
USE_MOCK_DATA=false
```

---

## 7. 검증 체크리스트

### Phase 2 완료 기준

| 항목 | 기준 | 검증 방법 |
|------|------|---------|
| Neo4j 연동 | 100개 기업 쿼리 성공 | API 테스트 |
| AI 6대 기능 | 모든 엔드포인트 응답 | 기능 테스트 |
| WebSocket | 10초 이내 신호 전달 | 지연 측정 |
| 에러 처리 | Mock 자동 폴백 | 장애 시뮬레이션 |

---

**작성**: 2026-02-05
**상태**: Design 완료
**다음 단계**: `/pdca do risk-improvements`
