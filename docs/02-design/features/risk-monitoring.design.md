# Step 3. 리스크 모니터링 시스템 - Design Document v2.0

## 1. 설계 철학: Graph-First Approach

### 1.1 핵심 통찰
기존 시스템의 문제점:
- **14개 카테고리 중복**: 뉴스/SNS 분리, 상표/특허 분리 등 불필요한 세분화
- **Neo4j 활용 미흡**: Graph DB를 단순 저장소로만 사용, **관계 분석** 미활용
- **전이 리스크 무시**: A기업 리스크가 B기업에 미치는 영향 분석 부족

### 1.2 새로운 접근법
```
┌─────────────────────────────────────────────────────────────────┐
│                    Graph-First Risk Analysis                     │
├─────────────────────────────────────────────────────────────────┤
│  기존: 카테고리별 점수 → 합산 → 총점                              │
│  신규: 관계 분석 → 전이 경로 추적 → 영향도 기반 점수               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 리스크 카테고리 재설계 (14개 → 8개)

### 2.1 기존 vs 신규 카테고리 매핑

| 기존 카테고리 | 신규 카테고리 | 이유 |
|-------------|-------------|------|
| 공시, 신용등급 | **재무 (Financial)** | 모두 재무 건전성 관련 |
| 소송, 금감원 | **법률/규제 (Legal)** | 법적 리스크 통합 |
| 주주, 임원 | **지배구조 (Governance)** | 경영 구조 통합 |
| - (신규) | **공급망 (Supply Chain)** | Neo4j 핵심! 관계 분석 |
| 경쟁사 | **시장/경쟁 (Market)** | 산업 동향 통합 |
| 뉴스, SNS, 채용리뷰 | **평판/여론 (Reputation)** | 외부 인식 통합 |
| 특허, 상표 | **운영/IP (Operational)** | 사업 운영 통합 |
| ESG, 부동산 | **거시환경 (Macro)** | 외부 환경 요인 통합 |

### 2.2 신규 8대 리스크 카테고리

```typescript
export const RISK_CATEGORIES = {
  FINANCIAL: {
    id: 'financial',
    name: '재무',
    icon: '💰',
    weight: 0.20,  // 20%
    description: '재무제표, 신용등급, 유동성',
    neo4jQuery: 'MATCH (c:Company)-[:HAS_CREDIT_RATING]->(r) RETURN r',
    sources: ['DART', 'NICE', 'KIND'],
  },
  LEGAL: {
    id: 'legal',
    name: '법률/규제',
    icon: '⚖️',
    weight: 0.15,
    description: '소송, 제재, 규제 위반',
    neo4jQuery: 'MATCH (c:Company)-[:INVOLVED_IN]->(l:LegalCase) RETURN l',
    sources: ['대법원', '금감원', 'DART'],
  },
  GOVERNANCE: {
    id: 'governance',
    name: '지배구조',
    icon: '👔',
    weight: 0.10,
    description: '주주 구성, 경영진, 지분 변동',
    neo4jQuery: 'MATCH (c:Company)<-[:OWNS]-(s) RETURN s',
    sources: ['DART', 'KIND'],
  },
  SUPPLY_CHAIN: {
    id: 'supply_chain',
    name: '공급망',
    icon: '🔗',
    weight: 0.20,  // 높은 가중치! Neo4j 핵심
    description: '공급사/고객사 리스크 전이',
    neo4jQuery: 'MATCH path=(s:Company)-[:SUPPLIES_TO*1..3]->(c:Company) RETURN path',
    sources: ['뉴스', '공급망DB'],
  },
  MARKET: {
    id: 'market',
    name: '시장/경쟁',
    icon: '📊',
    weight: 0.10,
    description: '시장 점유율, 경쟁 동향, 산업 사이클',
    neo4jQuery: 'MATCH (c:Company)-[:COMPETES_WITH]->(comp) RETURN comp',
    sources: ['뉴스', '산업분석'],
  },
  REPUTATION: {
    id: 'reputation',
    name: '평판/여론',
    icon: '📢',
    weight: 0.10,
    description: '언론 보도, SNS 여론, 직원 평판',
    neo4jQuery: 'MATCH (c:Company)<-[:ABOUT]-(n:NewsArticle) RETURN n',
    sources: ['뉴스', 'SNS', '잡플래닛'],
  },
  OPERATIONAL: {
    id: 'operational',
    name: '운영/IP',
    icon: '⚙️',
    weight: 0.10,
    description: '특허, 생산, 인력, 기술 경쟁력',
    neo4jQuery: 'MATCH (c:Company)-[:OWNS_PATENT]->(p:Patent) RETURN p',
    sources: ['KIPRIS', '채용공고'],
  },
  MACRO: {
    id: 'macro',
    name: '거시환경',
    icon: '🌍',
    weight: 0.05,
    description: '금리, 환율, 원자재, ESG',
    neo4jQuery: 'MATCH (c:Company)-[:EXPOSED_TO]->(m:MacroFactor) RETURN m',
    sources: ['경제지표', 'ESG평가'],
  },
} as const;
```

---

## 3. Neo4j 그래프 스키마 설계

### 3.1 노드 타입 (Node Labels)

```cypher
// 핵심 엔티티
(:Company {
  id: STRING,
  name: STRING,
  sector: STRING,
  totalRiskScore: INT,
  directRiskScore: INT,
  propagatedRiskScore: INT,
  status: STRING  // PASS, WARNING, FAIL
})

(:Person {
  id: STRING,
  name: STRING,
  role: STRING,  // CEO, CFO, 대주주 등
  riskScore: INT
})

(:Sector {
  id: STRING,
  name: STRING,
  cyclePahse: STRING,  // 호황, 불황, 회복
  riskLevel: STRING
})

// 리스크 이벤트
(:RiskEvent {
  id: STRING,
  type: STRING,  // LEGAL_CRISIS, MARKET_CRISIS, OPERATIONAL
  title: STRING,
  severity: STRING,  // HIGH, MEDIUM, LOW
  date: DATETIME,
  source: STRING
})

// 뉴스/공시
(:NewsArticle {
  id: STRING,
  title: STRING,
  sentiment: STRING,
  riskScore: INT,
  date: DATETIME,
  source: STRING
})

// 거시경제 요인
(:MacroFactor {
  id: STRING,
  name: STRING,  // 금리, 환율, 유가 등
  currentLevel: FLOAT,
  trend: STRING  // UP, DOWN, STABLE
})
```

### 3.2 관계 타입 (Relationship Types)

```cypher
// 공급망 관계 (핵심!)
(supplier:Company)-[:SUPPLIES_TO {
  volume: FLOAT,
  dependency: FLOAT,  // 의존도 0~1
  criticality: STRING  // CRITICAL, MAJOR, MINOR
}]->(customer:Company)

// 지분 관계
(shareholder)-[:OWNS {
  percentage: FLOAT,
  type: STRING  // DIRECT, INDIRECT
}]->(company:Company)

// 경영 관계
(person:Person)-[:MANAGES {
  role: STRING,
  since: DATE
}]->(company:Company)

// 경쟁 관계
(company:Company)-[:COMPETES_WITH {
  marketOverlap: FLOAT
}]->(competitor:Company)

// 섹터 소속
(company:Company)-[:BELONGS_TO]->(sector:Sector)

// 리스크 노출
(company:Company)-[:EXPOSED_TO {
  sensitivity: FLOAT  // 민감도 0~1
}]->(factor:MacroFactor)

// 리스크 이벤트 발생
(company:Company)-[:HAS_EVENT]->(event:RiskEvent)

// 뉴스 관련
(article:NewsArticle)-[:ABOUT]->(company:Company)

// ⭐ 핵심: 리스크 전이 관계
(sourceCompany:Company)-[:PROPAGATES_RISK_TO {
  propagationRate: FLOAT,  // 전이율 0~1
  pathway: STRING,  // supply_chain, ownership, market
  delay: INT  // 전이 지연 일수
}]->(targetCompany:Company)
```

### 3.3 핵심 Cypher 쿼리 (경쟁 차별화 포인트)

#### 3.3.1 공급망 리스크 전이 분석
```cypher
// 특정 기업의 공급망 2단계까지 리스크 전이 경로 분석
MATCH path = (target:Company {name: $companyName})<-[:SUPPLIES_TO*1..2]-(supplier:Company)
WHERE supplier.totalRiskScore > 50
RETURN
  [n IN nodes(path) | {name: n.name, score: n.totalRiskScore}] AS riskPath,
  reduce(risk = 0, r IN relationships(path) |
    risk + (startNode(r).totalRiskScore * r.dependency)
  ) AS propagatedRisk
ORDER BY propagatedRisk DESC
```

#### 3.3.2 리스크 허브 기업 탐지
```cypher
// 많은 기업에 리스크를 전파할 수 있는 "허브" 기업 탐지
MATCH (hub:Company)-[:SUPPLIES_TO]->(customer:Company)
WITH hub, count(customer) AS customerCount,
     sum(customer.totalRiskScore) AS totalExposure
WHERE customerCount > 3
RETURN hub.name, customerCount, hub.totalRiskScore, totalExposure
ORDER BY hub.totalRiskScore * customerCount DESC
LIMIT 10
```

#### 3.3.3 시나리오 시뮬레이션 (What-If)
```cypher
// "부산항 파업" 시나리오: 물류 관련 기업 영향도 분석
MATCH (company:Company)-[:BELONGS_TO]->(sector:Sector)
WHERE sector.name IN ['물류', '해운', '제조']
MATCH (company)<-[:SUPPLIES_TO]-(supplier)
WHERE supplier.location CONTAINS '부산'
RETURN
  company.name,
  company.totalRiskScore AS currentScore,
  company.totalRiskScore + 15 AS simulatedScore,  // +15점 증가 가정
  collect(supplier.name) AS affectedSuppliers
```

---

## 4. API 설계 (FastAPI)

### 4.1 아키텍처

```
┌─────────────────┐     HTTP/WS      ┌─────────────────┐      Bolt       ┌─────────────┐
│  React Frontend │ ◄──────────────► │  FastAPI Server │ ◄──────────────► │   Neo4j DB  │
│    :3000        │                  │     :8000       │                  │    :7687    │
└─────────────────┘                  └─────────────────┘                  └─────────────┘
                                            │
                                            ▼
                                     ┌─────────────────┐
                                     │  OpenAI API     │
                                     │  (AI 가이드)     │
                                     └─────────────────┘
```

### 4.2 API 엔드포인트

```python
# risk_engine/api.py

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NewWave Risk Engine API", version="2.0")

# CORS 설정 (React 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# REST API Endpoints
# ============================================

@app.get("/api/v2/deals")
async def get_all_deals():
    """포트폴리오 전체 딜 목록 + 리스크 요약"""
    pass

@app.get("/api/v2/deals/{deal_id}")
async def get_deal_detail(deal_id: str):
    """개별 딜 상세 정보 (monitoring.v1 스키마)"""
    pass

@app.get("/api/v2/deals/{deal_id}/risk-breakdown")
async def get_risk_breakdown(deal_id: str):
    """8개 카테고리별 리스크 분석"""
    pass

@app.get("/api/v2/deals/{deal_id}/supply-chain")
async def get_supply_chain_graph(deal_id: str):
    """공급망 그래프 (Neo4j 핵심!)"""
    pass

@app.get("/api/v2/deals/{deal_id}/propagation")
async def get_risk_propagation(deal_id: str):
    """리스크 전이 경로 분석"""
    pass

@app.get("/api/v2/signals")
async def get_realtime_signals(limit: int = 10):
    """실시간 리스크 신호"""
    pass

@app.get("/api/v2/timeline/{deal_id}")
async def get_risk_timeline(deal_id: str):
    """3단계 리스크 타임라인"""
    pass

@app.post("/api/v2/simulate")
async def run_simulation(scenario: SimulationRequest):
    """시나리오 시뮬레이션 실행"""
    pass

@app.get("/api/v2/ai-guide/{deal_id}")
async def get_ai_action_guide(deal_id: str, signal_type: str = "OPERATIONAL"):
    """AI 기반 RM/OPS 대응 가이드"""
    pass

# ============================================
# WebSocket (실시간 업데이트)
# ============================================

@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """실시간 리스크 신호 스트리밍"""
    await websocket.accept()
    while True:
        # 새로운 리스크 신호 감지 시 전송
        signal = await detect_new_signal()
        await websocket.send_json(signal)
```

### 4.3 응답 스키마

```typescript
// GET /api/v2/deals/{deal_id}/supply-chain 응답
interface SupplyChainResponse {
  centerNode: {
    id: string;
    name: string;
    riskScore: number;
  };
  suppliers: {
    company: string;
    dependency: number;  // 의존도
    riskScore: number;
    tier: number;  // 1차, 2차 공급사
  }[];
  customers: {
    company: string;
    exposure: number;  // 노출도
    riskScore: number;
  }[];
  propagationPaths: {
    source: string;
    target: string;
    propagationRate: number;
    pathway: string;
  }[];
  totalPropagatedRisk: number;
}

// GET /api/v2/deals/{deal_id}/propagation 응답
interface PropagationResponse {
  directRisk: number;
  propagatedRisk: number;
  totalRisk: number;
  topPropagators: {
    company: string;
    contribution: number;
    pathway: string;
  }[];
  riskPaths: {
    path: string[];  // ["A사", "B사", "대상기업"]
    risk: number;
  }[];
}
```

---

## 5. Frontend 컴포넌트 설계

### 5.1 파일 구조

```
components/
└── risk/
    ├── index.ts                    # 배럴 파일
    ├── types.ts                    # 타입 정의
    ├── api.ts                      # API 호출 함수
    ├── hooks/
    │   ├── useRiskData.ts          # 데이터 페칭 훅
    │   └── useWebSocket.ts         # 실시간 연결 훅
    ├── RiskPage.tsx                # 메인 페이지
    ├── RiskOverview.tsx            # 포트폴리오 요약
    ├── RiskSignals.tsx             # 실시간 신호
    ├── RiskTimeline.tsx            # 3단계 타임라인
    ├── RiskGraph.tsx               # ⭐ 공급망 그래프 (Neo4j 핵심)
    ├── RiskPropagation.tsx         # ⭐ 리스크 전이 시각화
    ├── RiskBreakdown.tsx           # 8개 카테고리 분석
    ├── RiskActionGuide.tsx         # AI 대응 가이드
    └── RiskSimulation.tsx          # 시나리오 시뮬레이션
```

### 5.2 핵심 컴포넌트: RiskGraph.tsx (Neo4j 시각화)

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔗 SUPPLY CHAIN RISK GRAPH                    ● LIVE: Neo4j    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│     [2차 공급사]         [1차 공급사]         [대상기업]         │
│                                                                 │
│        🏭 A사              🏭 B사                               │
│        (45점)─────────────(62점)────────────🏢 SK하이닉스      │
│           ↓                  ↓              (68점)             │
│           └────────┬─────────┘                │                │
│                    ▼                          ▼                │
│              [전이 리스크: 12점]        [직접 리스크: 56점]      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 📊 리스크 전이 분석                                              │
│ • B사(62점) → SK하이닉스: 의존도 45%, 전이 리스크 +8점           │
│ • A사(45점) → B사 → SK하이닉스: 2단계 전이, +4점                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 핵심 컴포넌트: RiskPropagation.tsx

```
┌─────────────────────────────────────────────────────────────────┐
│ 🌊 RISK PROPAGATION ANALYSIS                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  총 리스크 점수: 68점                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │████████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░│ │
│  │       직접 리스크 (56점, 82%)      │  전이 리스크 (12점, 18%)│ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  📈 주요 리스크 전이원                                           │
│  ┌──────────────┬──────────┬────────────┬──────────┐           │
│  │ 기업         │ 기여도    │ 전이 경로   │ 리스크   │           │
│  ├──────────────┼──────────┼────────────┼──────────┤           │
│  │ 한미반도체   │ +8점     │ 공급망      │ 🔴 82점  │           │
│  │ SK그룹      │ +3점     │ 지분관계    │ 🟡 45점  │           │
│  │ 삼성전자    │ +1점     │ 경쟁관계    │ 🟢 35점  │           │
│  └──────────────┴──────────┴────────────┴──────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 시뮬레이션 시나리오 설계

### 6.1 기본 제공 시나리오

```typescript
export const SIMULATION_SCENARIOS = [
  {
    id: 'busan_port_strike',
    name: '부산항 파업',
    description: '부산항 물류 마비로 인한 공급망 차질',
    affectedSectors: ['물류', '해운', '제조', '반도체'],
    impactFactors: {
      supply_chain: +20,  // 공급망 카테고리 +20점
      operational: +10,
      market: +5,
    },
    propagationMultiplier: 1.5,  // 전이 리스크 1.5배
  },
  {
    id: 'semiconductor_demand_drop',
    name: '반도체 수요 급감',
    description: '글로벌 경기 침체로 메모리 가격 20% 하락',
    affectedSectors: ['반도체', '전자', '디스플레이'],
    impactFactors: {
      market: +25,
      financial: +15,
      reputation: +10,
    },
    propagationMultiplier: 1.3,
  },
  {
    id: 'interest_rate_hike',
    name: '금리 급등',
    description: '기준금리 100bp 인상',
    affectedSectors: ['전체'],
    impactFactors: {
      financial: +30,
      macro: +20,
    },
    propagationMultiplier: 1.2,
  },
  {
    id: 'key_supplier_bankruptcy',
    name: '핵심 공급사 부도',
    description: '1차 공급사 중 1곳 부도 발생',
    affectedSectors: ['대상 기업 공급망'],
    impactFactors: {
      supply_chain: +40,
      operational: +25,
      financial: +10,
    },
    propagationMultiplier: 2.0,  // 높은 전이 효과
  },
];
```

### 6.2 시뮬레이션 로직 (Neo4j 활용)

```python
async def run_simulation(scenario_id: str, target_company: str):
    """
    시나리오 시뮬레이션 실행
    Neo4j의 관계 기반으로 영향도 계산
    """
    scenario = get_scenario(scenario_id)

    # 1. 영향받는 기업 조회
    affected_query = """
    MATCH (target:Company {name: $company})
    MATCH (target)-[:BELONGS_TO]->(sector:Sector)
    WHERE sector.name IN $affectedSectors

    // 공급망 연결 기업도 포함
    OPTIONAL MATCH (supplier:Company)-[:SUPPLIES_TO*1..2]->(target)

    RETURN target, collect(DISTINCT supplier) AS suppliers
    """

    # 2. 시뮬레이션 점수 계산
    for company in affected_companies:
        # 직접 영향
        direct_impact = calculate_direct_impact(company, scenario.impactFactors)

        # 전이 영향 (Neo4j 그래프 기반)
        propagated_impact = calculate_propagated_impact(
            company,
            scenario.propagationMultiplier
        )

        simulated_score = company.currentScore + direct_impact + propagated_impact

    return simulation_results
```

---

## 7. 구현 우선순위 (재정렬)

### Phase 1: 기반 구축 (Day 1)
1. `types.ts` - 새로운 8개 카테고리 타입
2. `api.ts` - FastAPI 연동 함수
3. FastAPI 서버 기본 구조 (`risk_engine/api.py`)
4. Neo4j 스키마 업데이트

### Phase 2: 핵심 기능 (Day 2)
5. `RiskPage.tsx` - 메인 레이아웃
6. `RiskOverview.tsx` - 포트폴리오 요약
7. `RiskSignals.tsx` - 실시간 신호
8. REST API 구현 (`/deals`, `/signals`)

### Phase 3: Neo4j 핵심 (Day 3) ⭐
9. `RiskGraph.tsx` - **공급망 그래프 시각화**
10. `RiskPropagation.tsx` - **리스크 전이 분석**
11. API: `/supply-chain`, `/propagation`

### Phase 4: 고급 기능 (Day 4)
12. `RiskTimeline.tsx` - 3단계 타임라인
13. `RiskBreakdown.tsx` - 8개 카테고리 분석
14. `RiskActionGuide.tsx` - AI 가이드

### Phase 5: 시뮬레이션 (Day 5)
15. `RiskSimulation.tsx` - 시나리오 UI
16. API: `/simulate`
17. WebSocket 실시간 연동

---

## 8. 기존 코드 통합 전략

### 8.1 재사용할 코드

| 파일 | 재사용 부분 | 수정 필요 |
|------|-----------|----------|
| `core.py` | 스캐너 클래스들 (NewsScanner, DartAPI 등) | 카테고리 매핑 변경 |
| `ai_service.py` | AI 가이드 생성 로직 | 8개 카테고리로 수정 |
| `dashboard_adapter.py` | JSON 스냅샷 로직 | 스키마 v2 적용 |

### 8.2 새로 작성할 코드

| 파일 | 역할 |
|------|------|
| `risk_engine/api.py` | FastAPI 서버 |
| `risk_engine/graph_queries.py` | Neo4j Cypher 쿼리 모음 |
| `risk_engine/propagation.py` | 리스크 전이 계산 로직 |
| `risk_engine/simulation.py` | 시나리오 시뮬레이션 |

---

## 9. AI 기능 설계 (OpenAI GPT-4.1)

### 9.1 AI 기능 목록

| # | 기능 | 설명 | API 엔드포인트 |
|---|------|------|---------------|
| 1 | **뉴스 자동 분석** | 뉴스 본문 → 리스크 심각도/카테고리 자동 분류 | `/api/v2/ai/analyze-news` |
| 2 | **리스크 요약** | 복잡한 상황을 한 문장으로 요약 | `/api/v2/ai/summarize/{deal_id}` |
| 3 | **Text2Cypher** | 자연어 → Neo4j Cypher 쿼리 자동 생성 | `/api/v2/ai/query` |
| 4 | **시나리오 해석** | 시뮬레이션 결과를 비즈니스 언어로 설명 | `/api/v2/ai/interpret-simulation` |
| 5 | **전이 경로 설명** | 리스크 전이 경로를 비즈니스 맥락으로 해석 | `/api/v2/ai/explain-propagation` |
| 6 | **대응 전략** | 산업/상황별 맞춤 RM/OPS 가이드 | `/api/v2/ai/action-guide/{deal_id}` |

### 9.2 AI 서비스 구현 (`risk_engine/ai_service_v2.py`)

```python
# AI 기능 1: 뉴스 자동 분석
async def analyze_news_with_ai(news_title: str, news_content: str) -> dict:
    """
    뉴스 기사를 AI로 분석하여 리스크 정보 추출
    - 키워드 매칭보다 문맥 이해력이 높음
    """
    prompt = f"""다음 뉴스 기사를 분석하여 리스크 정보를 추출하세요.

[뉴스 제목]
{news_title}

[뉴스 본문]
{news_content[:1000]}

[분석 항목]
1. 리스크 심각도 (1-100점)
2. 리스크 카테고리 (재무/법률/지배구조/공급망/시장/평판/운영/거시환경)
3. 영향받는 기업 목록
4. 핵심 키워드 (3개)
5. 1줄 요약

JSON 형식으로 응답:"""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)


# AI 기능 2: 리스크 요약 생성
async def generate_risk_summary(deal_data: dict) -> str:
    """
    복잡한 리스크 데이터를 한 문장으로 요약
    - 경영진이 빠르게 상황 파악 가능
    """
    prompt = f"""다음 기업의 리스크 현황을 경영진이 빠르게 이해할 수 있도록
한 문장(50자 이내)으로 요약하세요.

기업: {deal_data['name']}
총 리스크 점수: {deal_data['score']}점
주요 리스크 요인: {', '.join(deal_data['topFactors'])}
최근 이벤트: {deal_data['lastSignal']}

요약:"""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    return response.choices[0].message.content.strip()


# AI 기능 3: Text2Cypher (자연어 → Neo4j 쿼리)
async def text2cypher(question: str) -> dict:
    """
    자연어 질문을 Neo4j Cypher 쿼리로 변환
    - "리스크가 가장 높은 기업은?" → MATCH (c:Company) RETURN c ORDER BY c.totalRiskScore DESC LIMIT 1
    """
    prompt = f"""당신은 Neo4j Cypher 쿼리 전문가입니다.

[그래프 스키마]
- (:Company {{name, sector, totalRiskScore, directRiskScore, propagatedRiskScore, status}})
- (:Person {{name, role, riskScore}})
- (:Sector {{name, riskLevel}})
- (Company)-[:SUPPLIES_TO {{dependency}}]->(Company)
- (Company)-[:COMPETES_WITH]->(Company)
- (Person)-[:MANAGES]->(Company)

[사용자 질문]
{question}

[규칙]
1. 읽기 전용 쿼리만 생성 (MATCH, RETURN, WHERE, ORDER BY, LIMIT)
2. CREATE, DELETE, SET 절대 금지
3. 결과는 LIMIT 20 이하

JSON 형식으로 응답:
{{"cypher": "쿼리문", "explanation": "설명"}}"""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)


# AI 기능 4: 시나리오 해석
async def interpret_simulation(scenario: dict, results: list) -> str:
    """
    시뮬레이션 결과를 비즈니스 언어로 해석
    - 의사결정자가 이해하기 쉬운 형태로 제공
    """
    prompt = f"""다음 리스크 시뮬레이션 결과를 비즈니스 관점에서 해석하세요.

[시나리오]
{scenario['name']}: {scenario['description']}

[영향받는 기업]
{json.dumps(results[:5], ensure_ascii=False, indent=2)}

[요청]
1. 가장 큰 영향을 받는 기업과 이유
2. 전체 포트폴리오 영향도
3. 권장 대응 방향

3-4문장으로 간결하게 작성:"""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()


# AI 기능 5: 리스크 전이 경로 설명
async def explain_propagation(propagation_data: dict) -> str:
    """
    리스크 전이 경로를 비즈니스 맥락으로 설명
    """
    prompt = f"""다음 리스크 전이 경로를 비즈니스 관점에서 설명하세요.

[대상 기업]
{propagation_data['target']}

[전이 경로]
{json.dumps(propagation_data['paths'], ensure_ascii=False, indent=2)}

[전이 리스크 기여도]
{json.dumps(propagation_data['topPropagators'], ensure_ascii=False, indent=2)}

비즈니스 담당자가 이해할 수 있도록 2-3문장으로 설명:"""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    return response.choices[0].message.content.strip()


# AI 기능 6: 산업별 맞춤 대응 가이드 (기존 ai_service.py 강화)
async def generate_action_guide_v3(
    company: str,
    industry: str,
    risk_score: int,
    signal_type: str,
    propagation_info: dict
) -> dict:
    """
    산업별 + 전이 리스크 정보를 반영한 고도화된 대응 가이드
    """
    prompt = f"""당신은 {industry} 산업 전문 금융 리스크 관리자입니다.

[현재 상황]
- 기업: {company}
- 산업: {industry}
- 리스크 점수: {risk_score}점 (직접: {propagation_info.get('direct', 0)}점, 전이: {propagation_info.get('propagated', 0)}점)
- 시그널 타입: {signal_type}
- 주요 전이원: {', '.join(propagation_info.get('topPropagators', [])[:3])}

[요청]
1. RM 영업 가이드: 선제적 대응 방향 (50자 이내)
2. RM To-Do: 즉시 실행할 3가지 액션
3. OPS 방어 가이드: 방어적 대응 방향 (50자 이내)
4. OPS To-Do: 즉시 실행할 3가지 액션
5. 전이 리스크 대응: 공급망/관계사 관련 특별 조치 1가지

JSON 형식으로 응답:"""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)
```

### 9.3 AI 기능 UI 통합

```
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 AI INSIGHTS                                    Powered by GPT │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 💬 자연어 질의 (Text2Cypher)                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ "공급망 리스크가 가장 높은 기업은?"                    [검색] │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 📝 AI 리스크 요약                                               │
│ "SK하이닉스는 특허 소송(+15점)과 공급사 한미반도체 리스크 전이   │
│  (+8점)로 인해 WARNING 상태. 공급망 다변화 검토 필요."          │
│                                                                 │
│ 🔮 시나리오 해석                                                │
│ "부산항 파업 시, SK하이닉스는 물류 의존도 45%로 가장 큰 영향.   │
│  예상 리스크 +12점 상승. 대체 물류 루트 확보 권장."             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.4 AI 컴포넌트

```
components/risk/
├── ai/
│   ├── AIInsightsPanel.tsx      # AI 통합 패널
│   ├── Text2CypherInput.tsx     # 자연어 질의 입력
│   ├── RiskSummaryCard.tsx      # AI 요약 카드
│   └── SimulationInterpret.tsx  # 시뮬레이션 해석
```

---

## 10. 성공 지표 (경진대회 차별화)

### 10.1 기술적 차별화
| 요소 | 기존 | 신규 | 차별화 포인트 |
|------|-----|------|-------------|
| 카테고리 | 14개 (산재) | 8개 (집중) | 명확한 구조 |
| Neo4j 활용 | 저장소 | **관계 분석** | 핵심 경쟁력 |
| 리스크 계산 | 합산 | **전이 기반** | 현실 반영 |
| API | 없음 | FastAPI + WS | 실시간 |
| 시뮬레이션 | 없음 | What-If | 의사결정 지원 |
| **AI** | 단순 가이드 | **6대 AI 기능** | 지능형 분석 |

### 10.2 심사 어필 포인트
1. **"Graph DB의 진정한 활용"**: 단순 저장이 아닌 관계 분석
2. **"리스크 전이 추적"**: A기업 문제가 B기업에 미치는 영향 시각화
3. **"시나리오 시뮬레이션"**: 부산항 파업 등 가상 시나리오 영향 분석
4. **"실시간 모니터링"**: WebSocket 기반 즉시 알림
5. **"AI 지능형 분석"**: Text2Cypher로 자연어 DB 조회, AI 요약/해석

---

## 11. 검증 체크리스트

### 기능 검증
- [ ] 8개 카테고리 리스크 분석
- [ ] Neo4j 공급망 그래프 조회
- [ ] 리스크 전이 경로 시각화
- [ ] 시나리오 시뮬레이션 실행
- [ ] 실시간 신호 WebSocket
- [ ] AI 대응 가이드 생성
- [ ] AI 뉴스 자동 분석
- [ ] AI 리스크 요약
- [ ] Text2Cypher 자연어 질의
- [ ] AI 시나리오 해석
- [ ] AI 전이 경로 설명

### 성능 검증
- [ ] Neo4j 쿼리 응답 < 500ms
- [ ] API 응답 < 1s
- [ ] WebSocket 연결 안정성
- [ ] AI 응답 < 3s

### 품질 검증
- [ ] 기존 컴포넌트에 영향 없음
- [ ] TypeScript 타입 오류 없음
- [ ] 스타일 일관성 유지

---

**작성일**: 2026-02-05
**버전**: v2.1 (Graph-First + AI Enhanced)
**기반 문서**: `docs/01-plan/features/risk-monitoring.plan.md`
