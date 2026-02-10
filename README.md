# New Wave Risk Monitoring System

Graph-First + AI Enhanced 투자 리스크 모니터링 플랫폼

DART 공시, 뉴스, 블로그를 실시간 수집하고 Neo4j 그래프 DB 기반으로 리스크를 분석/시각화합니다.

---

## Quick Start

**Prerequisites:** Node.js 18+, Python 3.12+

```bash
# 1. 의존성 설치
npm install
pip install -r requirements.txt

# 2. 환경변수 설정 (.env.local)
cp .env.example .env.local  # 아래 Environment Variables 참고

# 3. 프론트엔드 (Vite dev server)
npm run dev

# 4. 백엔드 API (FastAPI, port 8000)
uvicorn risk_engine.api:app --host 0.0.0.0 --port 8000

# 5. Express 서버 (IM 분석, port 3001)
node server/index.js

# 6. (선택) 블로그 모니터 실시간 감시
python scripts/blog_monitor.py
```

---

## Architecture

### Graph DB Schema (5-Node Hierarchy)

```
Deal (투자검토)
 └── [TARGET] → Company (메인기업)
                  ├── [HAS_CATEGORY] → RiskCategory (10개 카테고리)
                  │                     └── [HAS_ENTITY] → RiskEntity
                  │                                        └── [HAS_EVENT] → RiskEvent
                  └── [HAS_RELATED] → Company (관련기업, 동일 구조)
```

| Node | Description | Types |
|------|-------------|-------|
| Deal | 투자검토 딜 | - |
| Company | 메인기업 + 관련기업 | - |
| RiskCategory | 10대 리스크 카테고리 | `SHARE` `EXEC` `CREDIT` `LEGAL` `GOV` `OPS` `AUDIT` `ESG` `SUPPLY` `OTHER` |
| RiskEntity | 리스크 주체/대상 | `PERSON` `SHAREHOLDER` `CASE` `ISSUE` |
| RiskEvent | 이벤트/뉴스 | `NEWS` `DISCLOSURE` `ISSUE` |

### Score Engine

- **Direct Score**: 메인기업 자체 이벤트 기반 점수
- **Propagated Score**: 관련기업 리스크 전이 점수
- **Critical Boost**: CRITICAL 이벤트 감지 시 +15점 부스트 + 강제 CRITICAL 판정
- **Risk Level**: PASS (0-34) / WARNING (35-59) / CRITICAL (60-100)

### Smart Triage (3축 분석)

```
Triage Score = Severity × 0.4 + Urgency × 0.3 + Confidence × 0.3
```

- **Severity**: 이벤트 심각도 (CRITICAL=100, HIGH=75, MEDIUM=50, LOW=25)
- **Urgency**: 발행일 기반 시간 감쇠 (최신=100, 7일 경과=5)
- **Confidence**: 출처 신뢰도 (DART=95%, 주요언론=85%, 블로그=40%)
- CRITICAL severity 이벤트는 triage에서도 최소 CRITICAL 보장

---

## Features

### Command Center
메인 대시보드. 전체 딜 리스크 현황, Live Feed(실시간 이벤트), Smart Triage 3축 분석

### Risk Deep Dive
딜 단위 상세 드릴다운. 카테고리별 점수, 이벤트 목록, 인물 연결, 증거 보드

### AI Copilot
자연어 질의 → Cypher 변환, AI 브리핑, 리스크 내러티브, 대응 가이드

### Supply Chain X-Ray
공급망 리스크 분석. 관련기업 리스크 전이 시각화, 3D 그래프 뷰

### IM Report Analysis
PDF 투자심의보고서 업로드 → Upstage OCR → GPT-5.2 분석 → 심사항목별 자동 평가

---

## Data Collection Pipeline

```
scripts/collect_for_deal.py
├── DART 수집 (dart_collector_v2.py)
│   ├── 공시 문서
│   ├── 주주 현황
│   ├── 임원 정보
│   ├── 대량보유 변동
│   ├── 재무지표
│   └── 리스크 이벤트
├── 뉴스 수집 (news_collector_v2.py)
│   └── Google/Naver RSS → 키워드 매칭 → 점수 산출
├── 카테고리 점수 계산 (CategoryService)
└── 총점 + 리스크 레벨 계산 (ScoreService)
```

```bash
# 전체 수집
python scripts/collect_for_deal.py

# 특정 딜만
python scripts/collect_for_deal.py --deal "퀀텀 칩 솔루션"

# 뉴스만 / DART만
python scripts/collect_for_deal.py --news-only
python scripts/collect_for_deal.py --dart-only
```

### Blog Monitor (실시간)

네이버 블로그 RSS 폴링 → 리스크 키워드 감지 → Neo4j 저장 → Telegram 알림

```bash
python scripts/blog_monitor.py                    # 전체 딜
python scripts/blog_monitor.py --deal "딜이름"     # 특정 딜
python scripts/blog_monitor.py --interval 10       # 폴링 간격(초)
```

---

## Project Structure

```
new_wave/
├── components/
│   ├── risk-v2/                  # Risk V2 UI
│   │   ├── screens/
│   │   │   ├── CommandCenter.tsx     # 메인 대시보드
│   │   │   ├── RiskDeepDive.tsx      # 딜 상세 드릴다운
│   │   │   ├── AICopilotPanel.tsx    # AI 코파일럿
│   │   │   ├── SupplyChainXRay.tsx   # 공급망 분석
│   │   │   └── WhatIf.tsx            # What-If 시나리오
│   │   ├── widgets/
│   │   │   ├── AIRiskNarrative.tsx    # AI 리스크 내러티브
│   │   │   ├── EvidenceBoard.tsx      # 증거 보드
│   │   │   ├── RiskAnatomy.tsx        # 리스크 해부
│   │   │   ├── RiskRadarChart.tsx     # 레이더 차트
│   │   │   └── SignalHeatmap.tsx      # 시그널 히트맵
│   │   ├── shared/                    # 공통 컴포넌트
│   │   ├── context/                   # React Context
│   │   ├── api-v2.ts                  # API 클라이언트
│   │   ├── types-v2.ts                # TypeScript 타입
│   │   └── utils-v2.ts               # 유틸리티
│   ├── GlobalDashboard.tsx            # 글로벌 대시보드
│   └── PDFUploadModal.tsx             # IM 보고서 업로드
│
├── risk_engine/                  # Python 백엔드
│   ├── api.py                        # FastAPI 메인 앱
│   ├── neo4j_client.py               # Neo4j 클라이언트
│   ├── dart_collector_v2.py          # DART 공시 수집
│   ├── news_collector_v2.py          # 뉴스 수집
│   ├── ai_service_v2.py              # GPT-5.2 AI 분석
│   ├── keywords.py                   # 리스크 키워드 사전
│   ├── score_engine.py               # 점수 계산 엔진
│   ├── alert_sender.py               # Telegram 알림
│   ├── simulation_engine.py          # Cascade 시뮬레이션
│   ├── deal_manager.py               # 딜 관리 CLI
│   └── v4/                           # V4 API 모듈
│       ├── api.py                        # V4 라우터
│       ├── schemas.py                    # Pydantic 스키마
│       ├── services/
│       │   ├── category_service.py       # 카테고리 점수
│       │   ├── score_service.py          # 총점 계산
│       │   ├── event_service.py          # 이벤트 관리
│       │   └── person_service.py         # 인물 연결
│       └── pipelines/
│           └── full_pipeline.py          # 전체 파이프라인
│
├── scripts/                      # 유틸리티 스크립트
│   ├── collect_for_deal.py           # 딜 단위 데이터 수집
│   ├── blog_monitor.py               # 블로그 실시간 감시
│   └── init_graph_v7.py              # 그래프 DB 초기화
│
├── server/                       # Express.js 서버
│   └── index.js                      # IM 분석 + 심사항목 API
│
└── docs/                         # 문서
```

---

## API Endpoints

### V4 API (`/api/v4`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/deals` | 전체 딜 목록 + 카테고리 요약 |
| POST | `/deals` | 딜 등록 + 자동 수집 트리거 |
| GET | `/deals/{id}` | 딜 상세 드릴다운 |
| DELETE | `/deals/{id}` | 딜 삭제 (cascade) |
| POST | `/deals/{id}/collect` | 수동 데이터 재수집 |
| GET | `/deals/{id}/categories` | 카테고리 목록 |
| GET | `/deals/{id}/categories/{code}` | 카테고리 상세 |
| GET | `/deals/{id}/events` | 이벤트 목록 |
| GET | `/deals/{id}/events/triaged` | Smart Triage 이벤트 |
| GET | `/deals/{id}/persons` | 인물 목록 |
| GET | `/deals/{id}/briefing` | AI 브리핑 |
| GET | `/deals/{id}/evidence` | 증거 목록 |
| GET | `/deals/{id}/graph` | 3D 그래프 데이터 |
| GET | `/deals/{id}/drivers` | 리스크 드라이버 |
| GET | `/alerts/critical` | CRITICAL 알림 (전체 딜) |
| GET | `/proxy/article` | 기사 본문 추출 |

### Express Server (`:3001`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/im/upload` | IM 보고서 PDF 업로드 + 분석 |
| POST | `/api/im/upload-stream` | SSE 스트리밍 분석 |
| GET | `/api/im/run/:id` | 분석 결과 조회 |
| CRUD | `/api/screening-criteria` | 심사항목 관리 |

---

## Environment Variables

`.env.local` 파일에 설정:

```env
# AI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.2

# Graph DB (Neo4j Aura Cloud)
NEO4J_URI=neo4j+ssc://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...

# Data Sources
OPENDART_API_KEY=...          # DART 공시 API

# OCR (IM 분석용)
UPSTAGE_API_KEY=...

# Telegram 알림
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## Tech Stack

**Frontend:**
- React 19 + TypeScript
- Vite
- Tailwind CSS
- Recharts + react-force-graph-3d (3D 시각화)
- Framer Motion

**Backend:**
- FastAPI + Uvicorn
- Neo4j Aura (Graph DB)
- OpenAI GPT-5.2
- Upstage (Document OCR)

**Data Sources:**
- DART OpenAPI (공시)
- Google/Naver RSS (뉴스)
- Naver Blog RSS (블로그 모니터)

**Infra:**
- Express.js (IM 서버)
- SQLite (심사항목)
- Telegram Bot API (알림)

---

## License

MIT
