# New Wave - System Overview

> 투자 리스크 모니터링 & AI 분석 플랫폼

---

## 1. 프로젝트 개요

### 배경

PE(Private Equity) / VC(Venture Capital) 하우스에서 딜 검토 시, 대상 기업과 관련 기업에 대한 리스크를 수동으로 조사하는 것은 시간이 오래 걸리고 누락 위험이 크다. **New Wave**는 이 과정을 자동화하여, 공시(DART)와 뉴스(RSS)를 실시간으로 수집하고, AI가 분석하며, 그래프 DB로 기업 간 관계와 리스크 전이를 추적하는 시스템이다.

### 핵심 가치

| 가치 | 설명 |
|------|------|
| **실시간 모니터링** | DART 공시 + 뉴스 RSS를 주기적으로 수집, CRITICAL 이벤트 즉시 알림 |
| **AI 기반 분석** | GPT-4 Turbo로 뉴스 감성 분석, 리스크 요약, 자연어 쿼리(Text2Cypher) |
| **그래프 DB 관계 추적** | Neo4j로 기업-임원-주주-사건 간 관계를 모델링하고 리스크 전이를 계산 |
| **IM 자동 분석** | Google Gemini로 투자메모(IM) PDF를 업로드하면 자동 스코어링 |

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│             React 19 + Vite + TypeScript                     │
│                    (port 5173)                                │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐   │
│  │ Global   │  │ Analysis │  │ Risk V2                   │   │
│  │Dashboard │  │ Panel    │  │ (Command/DeepDive/XRay/   │   │
│  │          │  │          │  │  WhatIf/AICopilot)        │   │
│  └──────────┘  └──────────┘  └──────────────────────────┘   │
└─────────────┬──────────────────────────┬────────────────────┘
              │ REST API                 │ REST API
              ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   PYTHON BACKEND         │  │   NODE.JS BACKEND        │
│   FastAPI (port 8000)    │  │   Express (port 3001)    │
│                          │  │                          │
│  - 리스크 엔진 (핵심)    │  │  - PDF 업로드 & 파싱     │
│  - DART/뉴스 수집        │  │  - Gemini AI IM 분석     │
│  - AI 분석 (OpenAI)      │  │  - 스코어링 결과 저장    │
│  - 스코어링 & 시뮬레이션 │  │                          │
│  - WebSocket 실시간 알림 │  │                          │
└────────────┬─────────────┘  └────────────┬─────────────┘
             │                              │
             ▼                              ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Neo4j Aura (Cloud)     │  │   SQLite (로컬)          │
│   그래프 데이터베이스     │  │   IM 스코어링 결과       │
│                          │  │   server/database.sqlite  │
│   5-Node Hierarchy       │  │                          │
│   Deal→Company→Category  │  │   scoring_modules        │
│   →Entity→Event          │  │   scoring_items          │
│                          │  │   scoring_runs           │
│                          │  │   scoring_results        │
└──────────────────────────┘  └──────────────────────────┘
```

---

## 3. 기술 스택

### Frontend

| 기술 | 버전 | 용도 |
|------|------|------|
| React | 19.2.4 | UI 프레임워크 |
| Vite | 6.4.1 | 빌드 도구 & 개발 서버 |
| TypeScript | ~5.8.2 | 타입 안정성 |
| Tailwind CSS | CDN | 유틸리티 CSS |
| Framer Motion | 12.33.0 | 애니메이션 |
| Recharts | 3.7.0 | 차트 시각화 |
| React Force Graph 3D | 1.29.1 | 3D 네트워크 그래프 |
| Three.js | 0.182.0 | 3D 렌더링 |

### Python Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| FastAPI | >= 0.104.0 | REST API 서버 |
| uvicorn | >= 0.24.0 | ASGI 서버 |
| neo4j | >= 5.0.0 | 그래프 DB 드라이버 |
| openai | >= 1.0.0 | GPT-4 Turbo AI 분석 |
| pandas | >= 2.0.0 | 데이터 처리 |
| pydantic | >= 2.0.0 | 데이터 검증 |
| aiohttp | >= 3.9.0 | 비동기 HTTP 클라이언트 |
| loguru | >= 0.7.0 | 로깅 |

### Node.js Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| Express | 4.18.2 | HTTP 서버 |
| @google/generative-ai | 0.24.1 | Google Gemini API |
| pdf-parse | 1.1.1 | PDF 텍스트 추출 |
| multer | 1.4.5-lts.1 | 파일 업로드 처리 |
| sqlite3 | 5.1.7 | SQLite 드라이버 |

### Database

| DB | 용도 |
|----|------|
| Neo4j Aura (Cloud) | 기업 관계 그래프, 리스크 이벤트, 5-Node 계층 구조 |
| SQLite | IM 분석 스코어링 결과 저장 (Node.js 서버 전용) |

### 외부 API

| API | 용도 |
|-----|------|
| DART (전자공시) | 공시 수집, 기업 정보, 주주/임원, 재무제표 |
| OpenAI (GPT-4 Turbo) | 뉴스 분석, 리스크 요약, NL→Cypher 변환 |
| Google Gemini (2.5-flash) | IM PDF 분석, 투자 스코어링 |
| Google/Naver RSS | 뉴스 수집 |

---

## 4. 그래프 DB 스키마 (5-Node Hierarchy)

### 구조

```
Deal (투자검토)
└── TARGET → Company (메인기업)
              ├── HAS_CATEGORY → RiskCategory (10개)
              │   └── HAS_ENTITY → RiskEntity
              │       └── HAS_EVENT → RiskEvent
              └── HAS_RELATED → Company (관련기업)
                                └── (동일 구조 반복)
```

### 노드 정의

| 노드 | 설명 | 주요 속성 |
|------|------|-----------|
| **Deal** | 투자검토 건 | dealId, companyName, sector, analyst, status |
| **Company** | 기업 (메인 + 관련) | companyId, name, corpCode, totalRiskScore, riskLevel |
| **RiskCategory** | 리스크 카테고리 (10종) | id, code, name, score, weight, weighted_score |
| **RiskEntity** | 리스크 대상 엔티티 | id, name, type(PERSON/SHAREHOLDER/CASE/ISSUE) |
| **RiskEvent** | 이벤트/뉴스 | id, title, type(NEWS/DISCLOSURE/ISSUE), severity, sourceUrl |

### 관계(Relationship)

| 관계 | From → To | 설명 |
|------|-----------|------|
| `TARGET` | Deal → Company | 딜의 대상 기업 (메인 1개) |
| `HAS_CATEGORY` | Company → RiskCategory | 기업의 리스크 카테고리 |
| `HAS_RELATED` | Company → Company | 관련 기업 (자회사, 투자기업 등) |
| `HAS_ENTITY` | RiskCategory → RiskEntity | 카테고리 내 엔티티 |
| `HAS_EVENT` | RiskEntity → RiskEvent | 엔티티에 연결된 이벤트 |

### 10개 리스크 카테고리

| 코드 | 한글명 | 가중치 | 설명 |
|------|--------|--------|------|
| `SHARE` | 주주 | 0.15 | 지분 변동, 대량보유, 유상증자 |
| `EXEC` | 임원 | 0.15 | 대표이사 변경, 사임, 경영권 분쟁 |
| `CREDIT` | 신용 | 0.15 | 부도, 파산, 회생, 채무불이행 |
| `LEGAL` | 법률 | 0.12 | 소송, 제재, 과징금, 압수수색 |
| `GOV` | 지배구조 | 0.10 | 횡령, 배임, 최대주주 변경 |
| `OPS` | 운영 | 0.10 | 사업중단, 영업정지, 허가취소 |
| `AUDIT` | 감사 | 0.08 | 감사의견 부적정/한정, 분식회계 |
| `ESG` | ESG | 0.08 | 환경오염, 안전사고, 갑질, 불매운동 |
| `SUPPLY` | 공급망 | 0.05 | 공급망 리스크, 원자재, 부품 |
| `OTHER` | 기타 | 0.02 | 기타 미분류 리스크 |

> 가중치 합계 = 1.00

---

## 5. 주요 기능

### 5.1 포트폴리오 대시보드 (Global Dashboard)

전체 딜 현황을 한눈에 파악하는 메인 화면. 딜별 리스크 점수, 상태(ACTIVE/CLOSED/PENDING), 담당 애널리스트 정보를 표시한다.

### 5.2 IM(투자메모) PDF 업로드 & AI 분석

PDF 파일을 업로드하면 Google Gemini가 투자메모를 자동 분석하여 딜 조건(차입자, 스폰서, 딜 규모 등)을 추출하고 항목별 스코어링(1~5점)을 수행한다. 결과는 SQLite에 저장된다.

### 5.3 실시간 리스크 모니터링 (Command Center)

선택된 딜의 리스크 현황을 실시간으로 모니터링한다. 카테고리별 점수 게이지, 트렌드 지표, 최신 이벤트 목록을 보여준다. CRITICAL 이벤트 발생 시 즉시 알림을 표시한다.

### 5.4 카테고리별 리스크 딥다이브 (Risk Deep Dive)

10개 카테고리 중 하나를 선택하면 해당 카테고리에 속한 엔티티(인물, 주주, 사건)와 각 엔티티에 연결된 이벤트(뉴스, 공시)를 상세하게 드릴다운할 수 있다.

### 5.5 공급망 X-Ray (Supply Chain X-Ray)

대상 기업의 관련 기업(자회사, 투자기업, 공급업체) 네트워크를 시각화한다. 관련 기업에서 발생한 리스크가 대상 기업으로 전이되는 경로와 전이율을 보여준다.

### 5.6 What-If 시나리오 시뮬레이션

가상의 시나리오(예: "대표이사 횡령 적발")를 설정하면 리스크 점수 변동과 카테고리별 영향을 시뮬레이션한다. 프리셋 시나리오와 커스텀 시나리오를 모두 지원한다.

### 5.7 AI Copilot

- **자연어 쿼리**: "삼성전자 관련 소송 건은?" 같은 질문을 Cypher 쿼리로 변환하여 그래프 DB에서 조회
- **리스크 브리핑**: 경영진용 리스크 요약 보고서 자동 생성
- **인사이트**: AI가 수집된 데이터를 종합 분석하여 투자 판단에 필요한 인사이트 제공

### 5.8 CRITICAL 알림 시스템

전체 딜을 대상으로 CRITICAL 등급 이벤트를 자동 폴링하여, 부도/파산/회생 등 긴급 리스크 발생 시 즉시 화면에 알림을 표시한다.

---

## 6. API 엔드포인트 목록

### Python Backend (FastAPI, port 8000)

#### V4 API (현재 주력)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v4/deals` | 전체 딜 목록 (카테고리 포함) |
| POST | `/api/v4/deals` | 딜 생성 + 자동 데이터 수집 |
| DELETE | `/api/v4/deals/{deal_id}` | 딜 삭제 |
| POST | `/api/v4/deals/{deal_id}/collect` | 수동 데이터 수집 트리거 |
| GET | `/api/v4/deals/{deal_id}` | 딜 상세 (5-Node 드릴다운) |
| GET | `/api/v4/deals/{deal_id}/categories` | 전체 리스크 카테고리 |
| GET | `/api/v4/deals/{deal_id}/categories/{code}` | 카테고리 상세 (엔티티/이벤트) |
| GET | `/api/v4/deals/{deal_id}/categories/{code}/entities` | 카테고리 내 엔티티 목록 |
| GET | `/api/v4/deals/{deal_id}/events` | 딜의 전체 이벤트 |
| GET | `/api/v4/deals/{deal_id}/events/triaged` | 긴급도별 분류 이벤트 |
| GET | `/api/v4/events/{event_id}` | 이벤트 상세 |
| GET | `/api/v4/deals/{deal_id}/persons` | 관련 인물 목록 |
| GET | `/api/v4/persons/{person_id}` | 인물 상세 |
| GET | `/api/v4/deals/{deal_id}/evidence` | 증거 요약 (뉴스 + 공시) |
| GET | `/api/v4/deals/{deal_id}/graph` | 3D 그래프 시각화 데이터 |
| GET | `/api/v4/deals/{deal_id}/drivers` | 리스크 드라이버 랭킹 |
| GET | `/api/v4/deals/{deal_id}/briefing` | 경영진 브리핑 |
| GET | `/api/v4/alerts/critical` | 전체 딜 CRITICAL 알림 |
| GET | `/api/v4/proxy/article?url={url}` | 기사 원문 프록시 |
| GET | `/api/v4/deals/{deal_id}/cases` | 케이스 목록 |
| POST | `/api/v4/deals/{deal_id}/cases` | 케이스 생성 |
| PATCH | `/api/v4/deals/{deal_id}/cases/{case_id}` | 케이스 수정 |
| POST | `/api/v4/pipeline/run/{company_id}` | 스코어 파이프라인 실행 |

#### V3 API (스케줄러, 공급망)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v3/scheduler/status` | 스케줄러 상태 |
| POST | `/api/v3/scheduler/start` | 스케줄러 시작 |
| POST | `/api/v3/scheduler/stop` | 스케줄러 정지 |
| POST | `/api/v3/scheduler/trigger/{job_type}` | 수동 작업 트리거 |
| GET | `/api/v3/status/summary` | 시스템 헬스 요약 |
| GET | `/api/v3/companies/{id}/score` | 기업 스코어 상세 |
| GET | `/api/v3/companies/{id}/news` | 기업 뉴스 |
| GET | `/api/v3/companies/{id}/supply-chain` | 공급망 상세 |
| GET | `/api/v3/companies/list` | 전체 기업 목록 |
| GET | `/api/v3/data-quality` | 데이터 품질 지표 |
| POST | `/api/v3/refresh/{company_id}` | 데이터 강제 새로고침 |
| GET | `/api/v3/ai/insight/{company_name}` | AI 종합 인사이트 |
| POST | `/api/v3/supply-chain/discover` | 관련 기업 발견 |
| POST | `/api/v3/supply-chain/expand` | 공급망 확장 |

#### V2 API (시뮬레이션, AI)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v2/deals` | 딜 목록 (V4 폴백용) |
| POST | `/api/v2/deals` | 딜 생성 |
| DELETE | `/api/v2/deals/{deal_id}` | 딜 삭제 |
| GET | `/api/v2/deals/{deal_id}` | 딜 상세 |
| GET | `/api/v2/signals` | 실시간 리스크 시그널 |
| GET | `/api/v2/timeline/{deal_id}` | 이벤트 타임라인 |
| GET | `/api/v2/scenarios` | 시나리오 프리셋 |
| POST | `/api/v2/simulate` | 시뮬레이션 실행 |
| POST | `/api/v2/simulate/advanced` | 고급 시뮬레이션 (캐스케이드) |
| POST | `/api/v2/ai/query` | 자연어 → Cypher 쿼리 |
| POST | `/api/v2/ai/analyze-news` | 뉴스 AI 분석 |
| GET | `/api/v2/ai/summarize/{deal_id}` | AI 리스크 요약 |
| GET | `/api/v2/predict/{deal_id}` | ML 리스크 예측 |
| WS | `/ws/signals` | WebSocket 실시간 시그널 |

#### 공통

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 헬스체크 |

### Node.js Backend (Express, port 3001)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/im/upload` | IM PDF 업로드 & Gemini AI 분석 |
| GET | `/api/im/run/:id` | 분석 결과 조회 |

---

## 7. 데이터 수집 파이프라인

### 전체 흐름

```
딜 생성 (create_deal)
    │
    ├── DART 기업 코드 조회 (corpCode.xml)
    ├── 관련 기업 발견 (타법인출자현황 API)
    │   └── 최대 7개 관련 기업 자동 등록
    │
    ▼
데이터 수집 (trigger_collection)
    │
    ├── DART 공시 수집 (dart_collector_v2.py)
    │   ├── 공시 목록 (list.json)
    │   ├── 주주 현황 (hyslrSttus.json)
    │   ├── 임원 현황 (elestock.json)
    │   ├── 소송 현황 (lwstLg.json)
    │   ├── 재무제표 (fnlttSinglAcnt.json)
    │   └── 부도 이벤트 (dfOcr.json)
    │
    ├── 뉴스 수집 (news_collector_v2.py)
    │   ├── Google News RSS (신뢰도: 0.75)
    │   ├── Google+Naver RSS (신뢰도: 0.85)
    │   └── Naver Blog RSS (신뢰도: 0.40)
    │
    ▼
키워드 매칭 & 분류
    │
    ├── DART 키워드 32종 → 카테고리 매핑
    ├── NEWS 키워드 100+종 → 카테고리 매핑
    └── RiskEntity + RiskEvent 노드 생성
    │
    ▼
스코어 계산 (score_engine.py)
    │
    ├── 1. 시간감쇠: score' = raw × e^(-days/30)
    ├── 2. 신뢰도: confidence = min(0.5 + keyword_count × 0.15, 0.95)
    ├── 3. 소스 신뢰도: DART(1.0), KIND(0.95), NEWS(0.7)
    ├── 4. 최종 점수: final = decayed × confidence × source_reliability
    ├── 5. 카테고리 점수: Σ(entity scores) × category_weight
    ├── 6. 기업 점수:
    │   ├── 직접 리스크 = Σ(weighted category scores)
    │   ├── 전이 리스크 = 관련기업 × 전이율(Tier1: 0.3, Tier2: 0.1)
    │   └── CRITICAL 부스트 = +15~30 (부도/파산/회생 이벤트)
    │
    ▼
리스크 레벨 판정
    ├── PASS:     0 ~ 49
    ├── WARNING:  50 ~ 74
    └── CRITICAL: 75 ~ 100 (또는 CRITICAL 이벤트 존재 시)
```

### 수집 주기

| 유형 | 주기 | 대상 |
|------|------|------|
| 실시간 | 즉시 | 중요 공시 (부도, 파산 등) |
| 일간 | 매일 | 임원 변경, M&A, 뉴스 RSS |
| 주간 | 매주 | 주식발행, 지분변동 |
| 분기 | 분기별 | 재무제표, 감사보고서 |

### DART API 호출 제한

- **100회/분** 제한 → 수집기에 0.7초 딜레이 적용
- 뉴스 수집: 1.0초 딜레이

---

## 8. 프론트엔드 화면 구성

### 3개 메인 뷰

| 뷰 | 컴포넌트 | 설명 |
|----|----------|------|
| Global Dashboard | `GlobalDashboard.tsx` | 전체 포트폴리오 현황 |
| Analysis Panel | `AnalysisPanel.tsx` | 재무 분석 & IM 업로드 |
| Risk V2 | `RiskShell.tsx` | 고급 리스크 분석 모듈 |

### Risk V2 내 5개 화면

| 화면 | 컴포넌트 | 설명 |
|------|----------|------|
| **Command Center** | `CommandCenter.tsx` | 딜 리스크 현황 대시보드, 카테고리 게이지, 이벤트 목록 |
| **Risk Deep Dive** | `RiskDeepDive.tsx` | 카테고리 → 엔티티 → 이벤트 드릴다운 분석 |
| **Supply Chain X-Ray** | `SupplyChainXRay.tsx` | 관련 기업 네트워크 시각화, 리스크 전이 맵 |
| **What-If** | `WhatIf.tsx` | 시나리오 시뮬레이션, 리스크 민감도 분석 |
| **AI Copilot** | `AICopilotPanel.tsx` | 자연어 쿼리, AI 브리핑, 인사이트 추천 |

### 상태 관리

- `RiskV2Context.tsx`로 React Context 기반 상태 관리
- 탭 네비게이션(`NavigationBar.tsx`)으로 화면 전환
- URL 라우팅 없음 (SPA 인메모리 상태)

---

## 9. 프로젝트 디렉토리 구조

```
D:\new_wave/
├── App.tsx                       # 메인 앱 컴포넌트 (뷰 라우팅)
├── index.html                    # HTML 엔트리 (Tailwind CDN)
├── index.tsx                     # React DOM 엔트리
├── package.json                  # 프론트엔드 의존성
├── vite.config.ts                # Vite 빌드 설정 (port 3000, @/ alias)
├── tsconfig.json                 # TypeScript 설정 (ES2022, strict)
├── requirements.txt              # Python 의존성
├── .env.local                    # 환경변수 (API 키, DB 연결 정보)
│
├── components/                   # React UI 컴포넌트 (34개)
│   ├── Header.tsx                # 내비게이션 + API 상태 표시
│   ├── GlobalDashboard.tsx       # 포트폴리오 대시보드
│   ├── AnalysisPanel.tsx         # 재무 분석 패널
│   ├── PDFUploadModal.tsx        # PDF 업로드 모달
│   ├── DocumentViewer.tsx        # 문서 뷰어
│   ├── DealGraph.tsx             # 3D 딜 그래프
│   ├── MonitoringDashboard.tsx   # 모니터링 대시보드
│   └── risk-v2/                  # V2 리스크 모듈 (25개 컴포넌트)
│       ├── api-v2.ts             # API 클라이언트 (24개 함수)
│       ├── types-v2.ts           # 타입 정의 (40+)
│       ├── design-tokens.ts      # 디자인 시스템 토큰
│       ├── category-definitions.ts # 카테고리 설정
│       ├── context/
│       │   └── RiskV2Context.tsx  # 상태 관리 Context
│       ├── layout/
│       │   ├── RiskShell.tsx      # 메인 컨테이너
│       │   └── NavigationBar.tsx  # 탭 네비게이션
│       ├── screens/               # 5개 메인 화면
│       ├── shared/                # 재사용 컴포넌트 (8개)
│       └── widgets/               # 시각화 위젯 (5개)
│
├── risk_engine/                  # Python 백엔드 (핵심)
│   ├── api.py                    # FastAPI 메인 앱 (V2/V3 라우터)
│   ├── neo4j_client.py           # Neo4j 싱글톤 클라이언트
│   ├── deal_manager.py           # 딜 CRUD + CLI
│   ├── keywords.py               # 키워드 사전 (DART 32 + NEWS 100+)
│   ├── score_engine.py           # 스코어링 엔진 (시간감쇠, 신뢰도)
│   ├── dart_collector_v2.py      # DART 공시 수집기
│   ├── news_collector_v2.py      # 뉴스 RSS 수집기
│   ├── ai_service_v2.py          # OpenAI 7개 AI 함수
│   ├── simulation_engine.py      # 시나리오 시뮬레이션
│   ├── ml_predictor.py           # Prophet 시계열 예측
│   ├── scheduler.py              # APScheduler 작업 스케줄러
│   ├── monitoring_agent.py       # 24/7 자율 모니터링 에이전트
│   ├── alert_sender.py           # 알림 발송 (Email/SMS)
│   ├── validator.py              # 데이터 검증
│   └── v4/                       # V4 API
│       ├── api.py                # V4 라우터
│       ├── schemas.py            # 스키마 + 카테고리 설정
│       ├── pipelines/
│       │   └── full_pipeline.py  # 스코어 계산 파이프라인
│       └── services/
│           ├── category_service.py   # 카테고리 쿼리
│           ├── score_service.py      # 점수 계산
│           ├── event_service.py      # 이벤트 조회
│           └── person_service.py     # 인물 조회
│
├── server/                       # Node.js 백엔드
│   ├── index.js                  # Express 앱 (port 3001)
│   ├── package.json              # 서버 의존성
│   ├── schema.sql                # SQLite 스키마
│   ├── database.sqlite           # SQLite DB 파일
│   └── uploads/                  # PDF 업로드 디렉토리
│
├── scripts/                      # 유틸리티 스크립트
│   ├── init_graph_v7.py          # Neo4j 인덱스 초기화
│   ├── seed_mock_data.py         # 목 데이터 시딩
│   ├── collect_for_deal.py       # 딜별 데이터 수집
│   ├── blog_monitor.py           # 블로그 RSS 모니터
│   ├── import_excel.py           # 스코어링 항목 엑셀 임포트
│   └── screenshot_risk.cjs       # UI 스크린샷 캡처
│
├── docs/                         # 문서
│   ├── 01-plan/                  # 기능 계획서
│   ├── 02-design/                # 설계 문서
│   ├── 03-analysis/              # 분석 보고서
│   └── 04-report/                # 최종 보고서
│
└── dist/                         # Vite 빌드 산출물
```

---

## 10. 로컬 개발 환경 실행 방법

### 필수 환경변수 (.env.local)

```env
# Neo4j (필수)
NEO4J_URI=neo4j+ssc://...
NEO4J_USERNAME=
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j

# OpenAI (AI 기능 활성화 시)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4-turbo-preview

# DART (공시 수집 시)
OPENDART_API_KEY=

# Gemini (IM 분석 시)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# 앱 설정
USE_MOCK_DATA=false
VITE_API_URL=http://localhost:8000
AI_ENRICHMENT_ENABLED=true
LOG_LEVEL=INFO
```

### 실행 커맨드

```bash
# 1. Frontend (React + Vite)
npm install
npm run dev                    # → http://localhost:5173

# 2. Python Backend (FastAPI)
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn risk_engine.api:app --reload --port 8000

# 3. Node.js Backend (Express)
cd server
npm install
node index.js                  # → http://localhost:3001

# 4. (선택) Neo4j 초기화 + 목 데이터
python scripts/init_graph_v7.py --clear
python scripts/seed_mock_data.py
```

---

## 11. 주요 스크립트

| 스크립트 | 용도 | 사용법 |
|----------|------|--------|
| `init_graph_v7.py` | Neo4j 인덱스 생성. `--clear` 시 전체 데이터 삭제 후 재생성 | `python scripts/init_graph_v7.py [--clear]` |
| `seed_mock_data.py` | 7개 테스트 딜 + 관련기업 + 리스크 데이터 시딩 | `python scripts/seed_mock_data.py` |
| `collect_for_deal.py` | 실제 DART/뉴스 데이터 수집. 특정 딜 또는 전체 | `python scripts/collect_for_deal.py [--deal NAME] [--dart-only] [--news-only]` |
| `blog_monitor.py` | Naver 블로그 RSS 실시간 모니터링 (30초 간격) | `python scripts/blog_monitor.py [--deal NAME] [--interval 30]` |
| `import_excel.py` | 엑셀 파일에서 스코어링 항목 임포트 | `python scripts/import_excel.py` |
| `deal_manager.py` | 딜 CRUD CLI | `python -m risk_engine.deal_manager --list\|--add "회사명" "섹터"\|--remove "DEAL_ID"` |

---

## 12. 트러블슈팅 가이드

### Neo4j 연결 오류

**증상**: `ServiceUnavailable` 또는 SSL 인증서 관련 오류

**해결**:
- 프로토콜을 반드시 `neo4j+ssc://`로 사용 (NOT `neo4j+s://`)
- Aura 인스턴스가 자체 서명 인증서를 사용하므로 `+ssc` (SSL without cert verification) 필수
- `.env.local`의 URI 확인: `NEO4J_URI=neo4j+ssc://378d289b.databases.neo4j.io`

### DART API 호출 제한

**증상**: HTTP 429 또는 빈 응답

**해결**:
- DART API는 **분당 100회** 제한
- `dart_collector_v2.py`에 0.7초 딜레이가 설정되어 있음
- 대량 수집 시 `collect_for_deal.py --dart-only`로 DART만 별도 실행

### CORS 관련 이슈

**증상**: 프론트엔드에서 API 호출 시 CORS 에러

**해결**:
- FastAPI(`risk_engine/api.py`): `allow_origins=["*"]` 설정 확인
- Express(`server/index.js`): `app.use(cors())` 확인
- 프론트엔드에서 GET 요청 시 `Content-Type` 헤더를 생략하면 preflight 요청을 피할 수 있음 (api-v2.ts에 이미 적용됨)

### Python venv 활성화 문제

**증상**: `venv\Scripts\activate`가 PowerShell에서 실행 안 됨

**해결**:
```powershell
# PowerShell 실행 정책 변경
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 또는 cmd 사용
venv\Scripts\activate.bat
```

### 포트 충돌

| 서비스 | 기본 포트 | 확인 방법 |
|--------|-----------|-----------|
| Frontend (Vite) | 5173 | `netstat -ano \| findstr 5173` |
| Python Backend | 8000 | `netstat -ano \| findstr 8000` |
| Node.js Backend | 3001 | `netstat -ano \| findstr 3001` |

**해결**: 해당 포트를 사용 중인 프로세스를 확인하고 종료하거나, 환경변수/설정에서 포트 변경

### Mock 모드로 빠르게 테스트

Python 백엔드를 Neo4j 연결 없이 실행하려면:
```bash
# .env.local에서
USE_MOCK_DATA=true
```

---

## 부록: AI 서비스 함수 목록

### OpenAI (Python Backend)

| 함수 | 용도 | 모델 |
|------|------|------|
| `analyze_news()` | 뉴스 감성 + 리스크 점수 추론 | GPT-4 Turbo |
| `summarize_risk()` | 리스크 내러티브 생성 | GPT-4 Turbo |
| `text_to_cypher()` | 자연어 → Cypher 쿼리 변환 | GPT-4 Turbo |
| `interpret_simulation()` | 시나리오 영향 설명 | GPT-4 Turbo |
| `explain_propagation()` | 리스크 전이 경로 내러티브 | GPT-4 Turbo |
| `generate_action_guide()` | RM/OPS 대응 권고 | GPT-4 Turbo |
| `generate_comprehensive_insight()` | 종합 분석 인사이트 | GPT-4 Turbo |

### Google Gemini (Node.js Backend)

| 기능 | 모델 |
|------|------|
| IM PDF 분석 + 딜 조건 추출 + 항목별 스코어링 | Gemini 2.5-flash |
