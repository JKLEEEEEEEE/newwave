# Risk Data Enrichment & Neo4j Integration Plan

> Feature: `risk-data-enrichment`
> Created: 2026-02-06
> Status: Plan Phase
> Priority: CRITICAL (Competition)

---

## 1. Background & Problem

### 현재 상태
- V2 UI 5개 화면 완성 (Command Center, Supply Chain X-Ray, Risk Deep Dive, War Room, AI Copilot)
- **모든 데이터가 Mock**: `mock-data-v2.ts`의 하드코딩 14개 이벤트, 11개 엔티티에 100% 의존
- Neo4j에 실제 데이터 존재하지만 **Frontend→Backend 연결 0%**
- UI 버그 다수: 클릭 안 됨, 깨진 기능, 하드코딩 AI 응답

### 문제 3가지 축

**축 1: 데이터 빈약 & 소스 부족**
- 이벤트 내용이 제목+1줄 수준 → 조사한 티가 안 남
- DART + 뉴스만 부분 구현 → 정보 다양성 부족
- CLI 수동 수집 명령 미완성

**축 2: Mock 100% → Neo4j 0% 연동**
- `api-v2.ts`가 `USE_MOCK=true`로 모든 API Mock 반환
- Backend에 V2/V4 API 존재하지만 Frontend가 호출 안 함
- 프론트엔드가 `/api/v3/*` 호출하는데 V3 엔드포인트 대부분 미존재

**축 3: UI 버그 15건 + UX 부족**
- Related Companies 클릭 무반응 (2곳)
- AI Copilot 3개 하드코딩 쿼리만 동작
- War Room 시뮬레이션 서버 호출 없음
- 기타 깨진 기능 다수

**축 4: Supply Chain X-Ray 노드 정보 부족**
- 노드/관계에 마우스 오버해야만 간단한 이름+점수 텍스트만 표시됨
- 노드를 클릭해도 **"왜 이 노드가 선정되었는지"** 사유 정보 없음
- 관련 이벤트, 리스크 카테고리 상세, 관계 근거가 전혀 보이지 않음
- 요구: 노드 클릭 시 **디테일 패널**에 선정 사유 + 핵심 이벤트 + 관계 정보 표시

**축 5: AI Enrichment 비용 제어 미비**
- 테스트 단계에서 OpenAI 전량 호출 시 비용 폭증 우려
- AI Enrichment 기능을 `.env.local` 환경변수로 on/off 할 수 없음
- 요구: `ENABLE_AI_ENRICHMENT=true/false`로 토글 가능하게

---

## 2. UI Bug Audit (15건 + 2건 UX 추가 = 17건 전수 점검 결과)

### CRITICAL (2건)
| # | 화면 | 파일:라인 | 증상 | 원인 | Fix |
|---|------|-----------|------|------|-----|
| 1 | RiskDeepDive | `RiskDeepDive.tsx:322-363` | 관련기업 카드 클릭 무반응 | GlassCard에 `onClick` 핸들러 없음 | onClick 추가 → selectCompany() + 해당 기업 카테고리 표시 |
| 2 | RiskDeepDive | `RiskDeepDive.tsx:189-214` | 관련기업 드릴다운 불가 | 관련기업→회사상세 네비게이션 로직 없음 | 관련기업 클릭 시 해당 기업의 카테고리 그리드 표시 |

### HIGH (5건)
| # | 화면 | 파일:라인 | 증상 | 원인 | Fix |
|---|------|-----------|------|------|-----|
| 3 | SupplyChainXRay | `SupplyChainXRay.tsx:324-343` | 관련기업 클릭 → 아무 변화 없음 | selectCompany() 호출하지만 뷰 전환 없음 | 클릭 시 deepdive로 이동 or 인라인 상세 표시 |
| 4 | AICopilot | `AICopilotPanel.tsx:82-141` | 3개 하드코딩 쿼리만 동작 | MOCK_CYPHER_RESPONSES에 3개만 존재 | → 실제 Text2Cypher API 연결 |
| 5 | WarRoom | `WarRoom.tsx:84-126` | 시뮬레이션이 Mock 계산만 | 서버 API 호출 없음, 클라이언트 계산 | → `riskApiV2.runSimulation()` 실제 호출 |
| 6 | api-v2.ts | `api-v2.ts:45` | 모든 API가 Mock 반환 | USE_MOCK=true 고정 | → Neo4j 실데이터 연결 |
| 7 | api-v2.ts | `api-v2.ts:260-325` | 시뮬레이션 API 미연결 | 서버 POST 안 함 | → POST /api/v2/simulate 호출 |

### MEDIUM (6건)
| # | 화면 | 파일:라인 | 증상 | 원인 | Fix |
|---|------|-----------|------|------|-----|
| 8 | AICopilot | `AICopilotPanel.tsx:27-76` | 인사이트가 선택 데이터 무관 | VIEW_INSIGHTS 하드코딩 | → 실제 선택 기업/카테고리 기반 AI 호출 |
| 9 | AICopilot | `AICopilotPanel.tsx:366-400` | Deep Dive 오버라이드 가짜 수치 | 65%, 78% 등 하드코딩 | → 실데이터 기반 계산 |
| 10 | WarRoom | `WarRoom.tsx:63-70` | AI 해석 항상 동일 | AI_INTERPRETATIONS 하드코딩 | → AI API 실시간 생성 |
| 11 | RiskV2Context | `RiskV2Context.tsx:52-53` | selectCompany가 뷰 전환 안 함 | 상태만 변경, 네비게이션 없음 | → selectCompany 시 activeView 자동 전환 |
| 12 | mock-data-v2.ts | 전체 | 모든 관계가 정적 | 동적 관계 불가 | → Neo4j 실시간 쿼리 |
| 13 | WarRoom | `WarRoom.tsx:766` | RiskMapOverlay 정의 순서 이상 | export 후 선언 | → 코드 정리 |

### LOW (2건)
| # | 화면 | 파일:라인 | 증상 | Fix |
|---|------|-----------|------|-----|
| 14 | SupplyChainXRay | `SupplyChainXRay.tsx:418` | "V5 (5-Node)" 하드코딩 | 제거 또는 동적 |
| 15 | RiskV2Context | `RiskV2Context.tsx:231-236` | useEffect 의존성 배열 누락 | 의존성 수정 |

### UX 개선 (2건 추가)
| # | 화면 | 파일:라인 | 증상 | 원인 | Fix |
|---|------|-----------|------|------|-----|
| 16 | SupplyChainXRay | `SupplyChainXRay.tsx:130-145` | 노드 클릭 시 선정 사유·관련 정보 없음 | `handleNodeClick`이 selectCompany만 호출, 디테일 패널 없음 | **Node Detail Panel** 추가: 클릭 시 우측 슬라이드 패널에 ① 노드 기본정보 ② 선정 사유(관계 타입·Tier) ③ 핵심 이벤트 top-3 ④ 카테고리 점수 요약 ⑤ Deep Dive 바로가기 표시 |
| 17 | Backend/CLI | `.env.local`, `enrichment_engine.py` | AI Enrichment 테스트 시 OpenAI 비용 폭증 | 비용 제어 토글 없음 | `.env.local`에 `ENABLE_AI_ENRICHMENT=true/false` 추가, Python 코드에서 False 시 AI 호출 스킵(raw 데이터만 저장), CLI `--no-enrich` 옵션 추가 |

---

## 3. API Version Strategy

### 현재 상황: 버전 불일치
```
Frontend (api-v2.ts)  →  /api/v3/*  →  대부분 미존재!
Backend (api.py)      →  /api/v2/*  →  완전 동작 (Deals, AI, Simulation)
                      →  /api/v4/*  →  드릴다운 지원 (Category, Entity, Person)
```

### 해결: V2 + V4 하이브리드 사용
| Frontend 기능 | 사용할 Backend API | 엔드포인트 |
|---------------|-------------------|-----------|
| 딜 목록/상세 | V2 | `GET /api/v2/deals`, `GET /api/v2/deals/{id}` |
| 리스크 점수 | V2 | `GET /api/v2/deals/{id}/risk-breakdown` |
| 공급망 그래프 | V2 | `GET /api/v2/deals/{id}/supply-chain` |
| 카테고리 드릴다운 | V4 | `GET /api/v4/deals/{id}/categories/{code}` |
| 엔티티/이벤트 | V4 | `GET /api/v4/events/{id}`, `GET /api/v4/persons/{id}` |
| Text2Cypher | V2 | `POST /api/v2/ai/query` |
| AI 인사이트 | V3 | `GET /api/v3/ai/insight/{company}` |
| 시뮬레이션 | V2 | `POST /api/v2/simulate` |
| 시나리오 목록 | V2 | `GET /api/v2/scenarios` |
| 전파 경로 | V2 | `GET /api/v2/deals/{id}/propagation` |

### api-v2.ts 수정 방향
```typescript
// Before (BROKEN)
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'; // always true

// After (FIXED)
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const USE_MOCK = false; // Mock 완전 제거
```

---

## 4. Data Sources (8개 소스)

### Tier 1 - 공식 소스 (신뢰도 HIGH)
| # | 소스 | API/방식 | 수집 데이터 | 매핑 카테고리 | 상태 |
|---|------|----------|------------|---------------|------|
| 1 | **DART 전자공시** | OpenDART API | 감사보고서, 임원변동, 주주현황, 재무제표, 주요사항보고서 | AUDIT, EXEC, SHARE, CREDIT | 구현됨 (dart_collector_v2.py) |
| 2 | **KIND 거래소공시** | RSS 피드 | 관리종목, 상장폐지, 불성실공시, 조회공시 | GOV, CREDIT | **신규** |
| 3 | **금융위원회/금감원** | FSS OPEN API | 제재처분, 과징금, 검사결과, 인허가 | LEGAL, GOV | **신규** |

### Tier 2 - 미디어 소스 (신뢰도 MEDIUM-HIGH)
| # | 소스 | API/방식 | 수집 데이터 | 매핑 카테고리 | 상태 |
|---|------|----------|------------|---------------|------|
| 4 | **뉴스** | Google RSS + Naver | 경제/산업/기업 뉴스 | ALL (키워드 매칭) | 구현됨 (news_collector_v2.py) |
| 5 | **KIPRIS 특허** | KIPRIS API (키 보유) | 특허분쟁, 무효심판, 소송 | LEGAL, OPS | **신규** |

### Tier 3 - 커뮤니티/평가 (신뢰도 MEDIUM)
| # | 소스 | API/방식 | 수집 데이터 | 매핑 카테고리 | 상태 |
|---|------|----------|------------|---------------|------|
| 6 | **커뮤니티** | AI 웹서치 기반 | 내부자 정보, 구조조정, 감원 | OPS, ESG | **신규** |
| 7 | **ESG 평가** | AI 웹서치 기반 | 환경/사회/지배구조 이슈 | ESG, GOV | **신규** |

### Tier 4 - 파생 분석
| # | 소스 | API/방식 | 수집 데이터 | 매핑 카테고리 | 상태 |
|---|------|----------|------------|---------------|------|
| 8 | **공급망 관계** | AI + DART 사업보고서 | 매출처, 원재료 의존도 | SUPPLY | **신규** |

---

## 5. AI Content Enrichment Pipeline

### 5.1 이벤트 AI 보강

수집된 각 이벤트에 대해 AI가 전문 애널리스트 수준의 분석 생성:

```json
{
  "summary": "공정거래위원회가 SK하이닉스의 DRAM 가격 담합 혐의에 대해 조사에 착수했다. 이번 조사는 2024년 하반기 DRAM 가격 급등기에 삼성전자, 마이크론과의 가격 조율 정황이 포착된 데 따른 것이다. 업계에서는 과징금 규모가 수천억 원에 달할 수 있다는 관측이 나온다.",
  "impact_analysis": "반도체 메모리 시장 과점 구조상 담합 혐의는 글로벌 규제당국 연쇄 조사로 이어질 가능성이 높다. EU, 미국 DOJ 추가 조사 예상. 글로벌 과징금 총액 1조원 초과 가능.",
  "key_entities": ["공정거래위원회", "DRAM", "삼성전자", "마이크론"],
  "severity": "HIGH",
  "investment_implication": "단기 주가 하방 압력 예상. 과거 2018년 EU 과징금 사례에서 6개월 내 회복 전력 있어 장기 관점 매수 기회 가능."
}
```

### 5.2 엔티티 AI 프로필 생성

```json
{
  "entity_name": "박정호 (前 부사장)",
  "profile": "SK그룹 ICT 위원장 출신. 2020~2023년 SK하이닉스 경영 전략 총괄.",
  "risk_context": "인텔 NAND 인수(약 9조원) 성과 불확실성과 맞물린 지배구조 리스크 가중 요인.",
  "timeline": "2020.03 부임 → 2021.10 인텔 NAND 인수 → 2023.06 사임 → 2024.01 검찰 조사"
}
```

---

## 6. CLI Collection Command

```bash
# 전체 파이프라인 (수집 + AI 보강 + 점수 갱신)
python -m risk_engine.monitor_control collect all --deal "SK하이닉스" --enrich

# 개별 소스
python -m risk_engine.monitor_control collect dart --deal "SK하이닉스"
python -m risk_engine.monitor_control collect news --deal "SK하이닉스"
python -m risk_engine.monitor_control collect kind --deal "SK하이닉스"
python -m risk_engine.monitor_control collect fss --deal "SK하이닉스"
python -m risk_engine.monitor_control collect patent --deal "SK하이닉스"
python -m risk_engine.monitor_control collect community --deal "SK하이닉스"
python -m risk_engine.monitor_control collect esg --deal "SK하이닉스"
python -m risk_engine.monitor_control collect supply --deal "SK하이닉스"

# AI 보강만 (기수집 데이터)
python -m risk_engine.monitor_control enrich --deal "SK하이닉스"

# 점수 갱신만
python -m risk_engine.monitor_control score update --company "SK하이닉스"
```

---

## 7. Implementation Scope (4 Phases)

### Phase A: UI Bug Fix + Neo4j 연결 (FIRST PRIORITY)

> Mock 제거, Neo4j 실데이터 연결, 15건 버그 수정

| # | Task | File(s) | Description |
|---|------|---------|-------------|
| A1 | api-v2.ts Mock 제거 | `api-v2.ts` | USE_MOCK=false, V2/V4 하이브리드 엔드포인트 연결, BASE_URL=localhost:8000 |
| A2 | RiskDeepDive 관련기업 클릭 | `RiskDeepDive.tsx` | 관련기업 GlassCard에 onClick 추가, 클릭→해당 기업 카테고리 표시 |
| A3 | SupplyChainXRay 관련기업 네비 | `SupplyChainXRay.tsx` | 관련기업 클릭→Deep Dive 뷰 전환 |
| A4 | RiskV2Context selectCompany 개선 | `RiskV2Context.tsx` | selectCompany 시 자동 뷰 전환 옵션 추가 |
| A5 | AICopilot 실 API 연결 | `AICopilotPanel.tsx` | Mock 제거 → `POST /api/v2/ai/query` 실호출 |
| A6 | WarRoom 시뮬레이션 실 API | `WarRoom.tsx` | Mock 제거 → `POST /api/v2/simulate` 실호출 |
| A7 | WarRoom AI 해석 실 생성 | `WarRoom.tsx` | 하드코딩 → `GET /api/v3/ai/insight` 실호출 |
| A8 | CommandCenter 실데이터 | `CommandCenter.tsx` | MOCK_DEALS → fetchDeals() 실호출 |
| A9 | mock-data-v2.ts 제거 | `mock-data-v2.ts`, `index.ts` | Mock 파일 완전 제거 or fallback-only로 축소 |
| A10 | X-Ray Node Detail Panel | `SupplyChainXRay.tsx` | 노드 클릭 시 우측 디테일 패널 표시 (아래 상세 참조) |

#### A10 상세: Supply Chain X-Ray Node Detail Panel

노드 클릭 시 우측에 슬라이드-인 패널 표시:

```
┌─────────────────────────────────┐
│  [노드명]              [✕ 닫기]  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                  │
│  🏷️ 노드 유형: 관련기업 (Tier 1)│
│  📊 리스크 점수: 5점 (PASS)      │
│  🔗 관계: SK하이닉스 → 계열사    │
│                                  │
│  ── 선정 사유 ──────────────── │
│  • HAS_RELATED 관계로 연결됨     │
│  • 계열사 (Tier 1) → 전이계수   │
│    0.3 적용                      │
│  • 전이 기여: +1.5점             │
│                                  │
│  ── 핵심 이벤트 (Top 3) ────── │
│  🔴 SK머티리얼즈 분식회계 의혹   │
│     CRITICAL | 70점 | 2026.02.04│
│                                  │
│  ── 카테고리 요약 ──────────── │
│  감사: 70점 (x0.08=5.6)         │
│  기타: 0점                       │
│                                  │
│  [🔍 Deep Dive에서 상세 보기]    │
└─────────────────────────────────┘
```

**구현 방식:**
- `SupplyChainXRay.tsx` 내부에 `NodeDetailPanel` 컴포넌트 추가
- `handleNodeClick` → 선택된 노드 상태(`selectedNode`) 관리
- 노드 타입별 다른 패널 내용:
  - `deal`: 딜 이름, 담당자, 상태
  - `mainCompany`: 전체 리스크 점수, 직접/전이 분해, 상위 카테고리 3개
  - `relatedCompany`: **선정 사유** (관계 타입, Tier, 전이 계수), 핵심 이벤트
  - `riskCategory`: 카테고리 점수, 가중치, 하위 엔티티 목록
  - `riskEntity`: 엔티티 점수, 관련 이벤트 타임라인
- 패널 하단에 "Deep Dive에서 상세 보기" 버튼 → `setActiveView('deepdive')` 전환
- `framer-motion` AnimatePresence로 슬라이드-인 애니메이션

### Phase B: 신규 수집기 구현 (Backend)

| # | Task | File(s) | Description |
|---|------|---------|-------------|
| B1 | KIND 수집기 | `risk_engine/kind_collector.py` | 거래소 RSS 공시 수집, 키워드 매칭, Neo4j 저장 |
| B2 | FSS 수집기 | `risk_engine/fss_collector.py` | 금감원 제재/검사 API 수집 |
| B3 | KIPRIS 수집기 | `risk_engine/patent_collector.py` | 특허 분쟁 수집 (KIPRIS API 키 보유) |
| B4 | 커뮤니티 수집기 | `risk_engine/community_collector.py` | AI 웹서치 기반 커뮤니티 이슈 수집 |
| B5 | ESG 수집기 | `risk_engine/esg_collector.py` | AI 기반 ESG 이슈 스캔 |
| B6 | 공급망 수집기 | `risk_engine/supply_collector.py` | DART 사업보고서 → 거래처 관계 추출 |

### Phase C: AI Enrichment Pipeline (비용 제어 포함)

> **핵심**: `.env.local`의 `ENABLE_AI_ENRICHMENT` 환경변수로 AI 호출 on/off 가능

| # | Task | File(s) | Description |
|---|------|---------|-------------|
| C0 | AI Enrichment 토글 | `.env.local`, `risk_engine/config.py` | `ENABLE_AI_ENRICHMENT=true/false` 환경변수 + config 모듈. False 시 AI 호출 완전 스킵, raw 데이터만 Neo4j에 저장 |
| C1 | Enrichment Engine | `risk_engine/enrichment_engine.py` | 이벤트 AI 보강: 요약/영향분석/심각도/시사점. `ENABLE_AI_ENRICHMENT=false`면 skip |
| C2 | Entity Profiler | `risk_engine/entity_profiler.py` | 인물/기관 AI 프로필 자동 생성. `ENABLE_AI_ENRICHMENT=false`면 skip |
| C3 | ai_service_v2 확장 | `risk_engine/ai_service_v2.py` | enrich_event(), profile_entity() 메서드 추가. 토글 체크 내장 |

#### C0 상세: AI Enrichment 비용 제어 설계

```python
# risk_engine/config.py
import os

ENABLE_AI_ENRICHMENT = os.getenv("ENABLE_AI_ENRICHMENT", "false").lower() == "true"

def is_enrichment_enabled() -> bool:
    """AI Enrichment 활성화 여부 (테스트 시 비용 절감용)"""
    return ENABLE_AI_ENRICHMENT
```

```bash
# .env.local 설정
ENABLE_AI_ENRICHMENT=false   # 테스트: AI 호출 안 함 (비용 0)
# ENABLE_AI_ENRICHMENT=true  # 운영/시연: AI 보강 활성화
```

**동작 분기:**
| `ENABLE_AI_ENRICHMENT` | 수집 | AI 보강 | Neo4j 저장 | 비용 |
|------------------------|------|---------|-----------|------|
| `false` (기본) | O | **X (스킵)** | raw 데이터만 | **$0** |
| `true` | O | O (GPT-4 호출) | 보강 데이터 포함 | ~$0.1/이벤트 |

**CLI 연동:**
```bash
# AI 보강 없이 수집만
python -m risk_engine.monitor_control collect all --deal "SK하이닉스"

# AI 보강 포함 (환경변수 무시, 강제 활성화)
python -m risk_engine.monitor_control collect all --deal "SK하이닉스" --enrich

# AI 보강 명시적 비활성화
python -m risk_engine.monitor_control collect all --deal "SK하이닉스" --no-enrich
```

### Phase D: CLI + Pipeline 통합

| # | Task | File(s) | Description |
|---|------|---------|-------------|
| D1 | CLI 확장 | `risk_engine/monitor_control.py` | `collect all --deal --enrich` 명령 |
| D2 | Collection Pipeline | `risk_engine/collection_pipeline.py` | 8개 소스 통합 오케스트레이터 |
| D3 | Graph Writer | `risk_engine/graph_writer.py` | 수집→Neo4j 일괄 저장 |
| D4 | Deep Dive UI 강화 | `RiskDeepDive.tsx` | 풍부한 이벤트 내용 렌더링 (AI summary, impact 등) |

---

## 8. 구현 우선순위

```
Wave 1 (즉시): Phase A 전체 (A1~A10, 10개 태스크)
  → Mock 제거 + Neo4j 연결 + 17건 버그/UX 수정
  → X-Ray Node Detail Panel 구현 (선정 사유 표시)
  → 모든 화면이 실 Graph DB 데이터로 동작

Wave 2 (수집기): Phase B + C (C0~C3 + B1~B6, 10개 태스크)
  → 6개 신규 수집기 + AI Enrichment Pipeline
  → ENABLE_AI_ENRICHMENT=false/true 토글 (비용 제어)
  → "collect all --deal --enrich" 파이프라인 동작
  → AI 활성 시 이벤트당 5~15줄 AI 분석 내용

Wave 3 (통합): Phase D (D1~D4, 4개 태스크)
  → CLI 완성 + Pipeline 오케스트레이터 + UI 강화
  → 수집→AI보강→Neo4j저장→UI반영 전체 흐름
```

---

## 9. Technical Details

### Backend 서버 실행
```bash
# venv 활성화
cd D:\new_wave
python -m venv venv  # 이미 존재
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# FastAPI 서버 시작 (port 8000)
python -m uvicorn risk_engine.api:app --host 0.0.0.0 --port 8000 --reload

# Neo4j 그래프 초기화 (필요 시)
python scripts/init_graph_v5.py
```

### 신규 Python 의존성
```
feedparser>=6.0     # KIND RSS 파싱
lxml>=5.0           # HTML/XML 파싱
```

### Environment (.env.local)
```bash
# ===== API Keys (이미 보유) =====
OPENDART_API_KEY=...     # DART 전자공시
OPENAI_API_KEY=...       # AI Enrichment (GPT-4)
KIPRIS_API_KEY=...       # 특허 (KIPRIS)

# ===== Frontend 설정 =====
VITE_USE_MOCK=false                    # Mock 비활성화 (Neo4j 실데이터 사용)
VITE_API_URL=http://localhost:8000     # FastAPI 연결

# ===== AI Enrichment 비용 제어 (★ 신규) =====
ENABLE_AI_ENRICHMENT=false   # false: AI 호출 안 함 (테스트 시 비용 $0)
                             # true:  AI 보강 활성화 (이벤트당 ~$0.1)
                             # CLI --enrich 플래그로 오버라이드 가능
```

---

## 10. Risk & Constraints

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Neo4j 서버 미실행 | UI 완전 깨짐 | Graceful fallback + 에러 메시지 |
| FastAPI 서버 미실행 | API 호출 실패 | 연결 실패 시 안내 배너 표시 |
| OpenAI 비용 (대량 enrichment) | 비용 초과 | **`ENABLE_AI_ENRICHMENT=false` 토글** + 배치+캐싱+선별 enrichment. CLI `--no-enrich` 옵션 |
| DART API 호출 제한 | 수집 실패 | 스케줄링 분산 + 재시도 |
| 커뮤니티 스크래핑 법적 | 차단/법적 | AI 웹서치 간접 수집으로 대체 |

---

## 11. Success Criteria

- [ ] Mock 데이터 **완전 제거**, 모든 화면 Neo4j 실데이터 표시
- [ ] 17건 UI 버그+UX **전수 수정** (관련기업 클릭, AI Copilot, 시뮬레이션 등)
- [ ] **Supply Chain X-Ray**: 노드 클릭 시 디테일 패널 표시 (선정 사유, 핵심 이벤트, 관계 정보)
- [ ] **AI 비용 제어**: `ENABLE_AI_ENRICHMENT=false` 설정 시 AI 호출 0건, 비용 $0
- [ ] **AI 비용 제어**: `--enrich` / `--no-enrich` CLI 플래그 정상 동작
- [ ] `python -m risk_engine.monitor_control collect all --deal "SK하이닉스" --enrich` 정상 동작
- [ ] 8개 소스 데이터 수집 (최소 5개 실동작)
- [ ] AI Enrichment: 이벤트당 5줄+ 분석, 엔티티 프로필 자동 생성 (ENABLE=true 시)
- [ ] Deep Dive에서 풍부한 이벤트 내용 확인 (요약/영향분석/시사점)
- [ ] Text2Cypher: 임의 자연어 질의 → 실제 Cypher 실행 → 결과 반환

---

## 12. Agent Team Execution Plan

> Wave 1 (Phase A) 구현을 위한 Agent Team 실행 전략

### 12.1 팀 구성 (6 Teammates)

| # | Name | Role | Agent Type | 담당 범위 |
|---|------|------|-----------|----------|
| 0 | **Leader** (현재 세션) | 팀 리더·조율자 | - | TeamCreate, 작업 분배, 진행 모니터링, 종합 |
| 1 | **Risk-Plan** | 아키텍처·태스크 설계 | `Plan` | Plan 문서 정교화, 의존성 그래프, API 매핑 테이블 확정 |
| 2 | **Risk-Understand** | 코드베이스 분석 | `Explore` | 5개 화면 Mock 의존성 맵, Backend V2/V4 응답 스키마 분석 |
| 3 | **Risk-Design** | 컴포넌트 설계 | `Plan` | api-v2.ts 재작성 설계, NodeDetailPanel 설계, 타입 매핑 |
| 4 | **Risk-Implement** | 코드 구현 | `general-purpose` | A1~A10 전체 구현 (파일 편집, 빌드 확인) |
| 5 | **Risk-Verify** | 검증·테스트 | `general-purpose` | TypeScript 빌드, 화면별 기능 검증, API 연결 테스트 |
| 6 | **Risk-Complete** | 통합·완료 | `general-purpose` | 최종 빌드, mock 파일 제거, Plan 문서 체크리스트 업데이트 |

### 12.2 파일 소유권 (충돌 방지)

> Agent Teams 핵심 원칙: **두 teammate가 동시에 같은 파일을 편집하면 안 됨**

| 파일 | 소유 Teammate | 편집 시점 |
|------|--------------|----------|
| `api-v2.ts` | Risk-Implement | Wave 3-A (최우선) |
| `RiskV2Context.tsx` | Risk-Implement | Wave 3-A |
| `CommandCenter.tsx` | Risk-Implement | Wave 3-B |
| `RiskDeepDive.tsx` | Risk-Implement | Wave 3-B |
| `SupplyChainXRay.tsx` | Risk-Implement | Wave 3-B |
| `WarRoom.tsx` | Risk-Implement | Wave 3-B |
| `AICopilotPanel.tsx` | Risk-Implement | Wave 3-B |
| `mock-data-v2.ts` | Risk-Complete | Wave 5 (마지막) |
| `types-v2.ts` (타입 추가 시) | Risk-Implement | Wave 3-A |
| `index.ts` (exports 수정) | Risk-Complete | Wave 5 |

### 12.3 실행 타임라인 (5 Waves)

```
시간 →  ══════════════════════════════════════════════════════

Wave 1 ║  Risk-Plan ████████        ← 태스크 분해 + 의존성 확정
(병렬) ║  Risk-Understand ████████  ← Mock 의존성 맵 + API 스키마 분석
       ║  (두 agent 동시 실행, 서로 다른 파일 읽기만)
       ║
Wave 2 ║         Risk-Design ██████████  ← API 매핑 + NodeDetailPanel 설계
(순차) ║         (Wave 1 결과 종합 후 설계)
       ║
Wave 3 ║  Risk-Implement ═══════════════════════════════════
(핵심) ║  ┌─ 3-A: api-v2.ts + RiskV2Context.tsx (기반) ─┐
       ║  │       ↓ (완료 후)                            │
       ║  │  3-B: 5개 화면 순차 수정                      │
       ║  │  ┌─ CommandCenter.tsx (A8)                   │
       ║  │  ├─ RiskDeepDive.tsx (A2)                    │
       ║  │  ├─ SupplyChainXRay.tsx (A3+A10)             │
       ║  │  ├─ WarRoom.tsx (A6+A7)                      │
       ║  │  └─ AICopilotPanel.tsx (A5)                  │
       ║  └──────────────────────────────────────────────┘
       ║
Wave 4 ║                Risk-Verify ████████████
(병렬) ║                (Implement 완료 후 즉시 검증 시작)
       ║                ├─ tsc --noEmit (타입 체크)
       ║                ├─ npm run build (Vite 빌드)
       ║                └─ 화면별 동작 확인
       ║
Wave 5 ║                           Risk-Complete ██████
(마무리)║                           ├─ mock-data-v2.ts 정리 (A9)
       ║                           ├─ 미사용 import 제거
       ║                           ├─ 최종 빌드 확인
       ║                           └─ Plan 체크리스트 업데이트
```

### 12.4 Wave별 상세

#### Wave 1: 분석 (Risk-Plan + Risk-Understand 병렬)

**Risk-Plan** (Plan agent, 읽기 전용):
- 현재 plan 문서 정독
- A1~A10 태스크 의존성 그래프 확정
- Backend API 엔드포인트 ↔ Frontend 함수 매핑 테이블 작성
- 출력: 정교화된 태스크 목록 + 의존성 + 매핑 테이블

**Risk-Understand** (Explore agent, 읽기 전용):
- 5개 화면 파일에서 `MOCK_*`, `mock-data-v2` import 전수 조사
- `risk_engine/api.py`에서 V2/V4 엔드포인트 응답 스키마 분석
- `types-v2.ts`와 Backend 응답 간 타입 호환성 체크
- 출력: Mock 의존성 맵 + API 응답 스키마 + 타입 갭 목록

#### Wave 2: 설계 (Risk-Design, Wave 1 의존)

**Risk-Design** (Plan agent, 읽기 전용):
- Wave 1 결과 종합
- `api-v2.ts` 재작성 상세 설계:
  - 각 함수별 호출할 Backend 엔드포인트
  - 응답 변환 로직 (Backend JSON → Frontend Type)
  - 에러 핸들링 전략
- `NodeDetailPanel` 컴포넌트 설계:
  - Props/State 정의
  - 노드 타입별 렌더링 분기
  - 데이터 조회 흐름
- 출력: 구현 가이드 (pseudo-code 수준)

#### Wave 3: 구현 (Risk-Implement, Wave 2 의존)

**Risk-Implement** (general-purpose agent, 편집 권한):

**3-A: 기반 (순차, 필수)**
1. `api-v2.ts` 완전 재작성 (A1)
   - `USE_MOCK=false` 고정, `BASE_URL=localhost:8000`
   - Mock import 전체 제거
   - V2+V4 하이브리드 엔드포인트 연결
   - 응답 변환 레이어 추가
2. `RiskV2Context.tsx` 개선 (A4)
   - `selectCompany` → 자동 뷰 전환 옵션

**3-B: 화면 수정 (순차, 3-A 의존)**
3. `CommandCenter.tsx` (A8) - Mock → Context/API 호출
4. `RiskDeepDive.tsx` (A2) - 관련기업 onClick 추가
5. `SupplyChainXRay.tsx` (A3+A10) - 관련기업 네비 + NodeDetailPanel
6. `WarRoom.tsx` (A6+A7) - 시뮬레이션 + AI 해석 실 API
7. `AICopilotPanel.tsx` (A5) - Text2Cypher 실 API

#### Wave 4: 검증 (Risk-Verify, Wave 3 의존)

**Risk-Verify** (general-purpose agent):
- `npx tsc --noEmit` 타입 체크
- `npm run build` Vite 빌드 확인
- 각 화면 Mock import 잔존 여부 확인
- API 연결 테스트 (Backend 실행 상태에서)

#### Wave 5: 완료 (Risk-Complete, Wave 4 의존)

**Risk-Complete** (general-purpose agent):
- `mock-data-v2.ts` 정리 (A9) - 완전 제거 or fallback 축소
- `index.ts` export 정리
- 미사용 import/변수 정리
- 최종 `npm run build` 확인
- Plan 문서 Success Criteria 체크

### 12.5 병렬 실행 가능 분석

| 구간 | 병렬 가능? | 설명 |
|------|-----------|------|
| Risk-Plan + Risk-Understand | **✅ 병렬** | 둘 다 읽기만, 파일 충돌 없음 |
| Risk-Design | ❌ 순차 | Wave 1 결과에 의존 |
| Risk-Implement 3-A → 3-B | ❌ 순차 | api-v2.ts가 모든 화면의 기반 |
| Risk-Implement 내 화면 수정 | ⚠️ 순차 권장 | 단일 agent가 순차 수행 (파일 충돌 방지) |
| Risk-Verify | ⚠️ 부분 병렬 | Implement 완료 즉시 검증 시작 가능 |
| Risk-Complete | ❌ 순차 | 모든 검증 통과 후 |

### 12.6 비용 최적화

| Teammate | Agent Type | Model | 예상 턴 수 | 이유 |
|----------|-----------|-------|-----------|------|
| Risk-Plan | Plan | haiku | ~5 | 읽기 전용, 빠른 분석 |
| Risk-Understand | Explore | haiku | ~8 | 파일 탐색, 스키마 확인 |
| Risk-Design | Plan | sonnet | ~6 | 설계 품질 중요 |
| Risk-Implement | general-purpose | sonnet | ~30 | 핵심 구현, 높은 품질 필요 |
| Risk-Verify | general-purpose | haiku | ~8 | 빌드 실행, 결과 확인 |
| Risk-Complete | general-purpose | haiku | ~6 | 정리 작업, 빌드 확인 |

### 12.7 실행 모드

```
teammateMode: "in-process" (Windows 호환)
```

모든 teammate가 메인 터미널 내에서 실행.
Shift+Up/Down으로 teammate 전환, Ctrl+T로 작업 목록 토글.
