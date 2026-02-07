# Supply Chain Risk V2 - Total Redesign Planning Document

> **Summary**: 공급망 리스크 모니터링 시스템 전면 재설계 - 5-Node 스키마 기반 트렌디 인터렉티브 UI + Neo4j/AI 극대화
>
> **Project**: New Wave (공급망 리스크 대회)
> **Version**: 2.0
> **Author**: AI Agent
> **Date**: 2026-02-06
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

Graph DB 스키마가 5-Node 계층 구조(Deal → Company → RiskCategory → RiskEntity → RiskEvent)로 최종 확정됨에 따라, 기존 UI(포트폴리오/상세분석/시뮬레이션/예측 4탭 구조)를 전면 재설계합니다.

**핵심 목표:**
- 대회 심사위원이 "와!" 할 수준의 비주얼과 인터렉션
- Neo4j 그래프 DB 활용을 시각적으로 극대화 (3D 그래프, 실시간 탐색)
- AI(ChatGPT) 활용을 전면에 배치 (자연어 질의, 시나리오 생성, 인사이트)
- 멀티 티어 공급망 가시성 + 디지털 트윈 스트레스 테스트 아이디어 반영

### 1.2 Background

**현재 문제점:**
1. **디자인 구식**: slate-800/900 기반 다크 테마, 단조로운 카드/리스트 레이아웃
2. **스키마 불일치**: 기존 UI는 v3 스키마 기반, v5(5-Node) 스키마와 미정합
3. **Neo4j 활용 부족**: Canvas 기반 2D 그래프만 존재, 드릴다운 부족
4. **AI 활용 제한적**: 별도 탭에 격리됨, 화면 전반에 자연스럽게 녹아들지 않음
5. **인터렉션 제한**: 정적 카드 중심, 애니메이션/전환 효과 부족

**대회 핵심 평가 기준:**
- Neo4j 그래프 DB 활용도
- AI(ChatGPT) 통합 수준
- 실무 적용 가능성 + WOW 팩터

### 1.3 Design References

**디자인 트렌드 참고:**
- [Glassmorphism Dashboard Dark Mode (Dribbble)](https://dribbble.com/tags/glassmorphism-dashboard)
- [Supply Chain Dashboard (Dribbble)](https://dribbble.com/search/supply-chain-dashboard)
- [Enterprise Supply Chain Dashboard (Figma)](https://www.figma.com/community/file/1539514812839902866/enterprise-supply-chain-management-dashboard)
- [Retail & Supply Chain Analysis Dashboard (Figma)](https://www.figma.com/community/file/1294727297018831644/retail-supply-chain-analysis-dashboard)
- [Best Dashboard Design Examples 2026 (Muzli)](https://muz.li/blog/best-dashboard-design-examples-inspirations-for-2026/)
- [Neo4j Needle Design System](https://neo4j.com/blog/developer/needle-neo4j-design-system/)
- [react-force-graph (3D Force-Directed)](https://github.com/vasturiano/react-force-graph)

**벤치마크 솔루션:**
- Interos: 멀티 티어 공급망 가시성 + AI 예측
- Coupa Risk Aware: 실시간 리스크 모니터링 + ESG
- Z2Data: 트렌드 분석 + 지리적 리스크

---

## 2. Scope

### 2.1 In Scope

- [ ] **전면 UI 재설계**: Glassmorphism + Dark Theme + Gradient 기반 프리미엄 디자인
- [ ] **5-Node 스키마 완전 반영**: Deal → Company → RiskCategory → RiskEntity → RiskEvent 드릴다운
- [ ] **3D 인터렉티브 그래프**: react-force-graph-3d 기반 Neo4j 시각화 (멀티 티어)
- [ ] **AI 전면 통합**: 모든 화면에 AI 컨텍스트 패널, 자연어 질의 글로벌 검색바
- [ ] **디지털 트윈 시뮬레이션**: What-If 시나리오 + AI 기반 복구경로 추천
- [ ] **실시간 대시보드**: 리스크 시그널 라이브 피드 + 알림
- [ ] **5개 메인 화면** 재구성 (아래 3.1 참조)

### 2.2 Out of Scope

- 백엔드 API 전면 재개발 (기존 FastAPI 엔드포인트 활용, 필요시 확장)
- 모바일 반응형 (데스크톱 대시보드 집중)
- 사용자 인증/권한 관리
- 그래프 DB 스키마 구조 변경 (5-Node FROZEN)

---

## 3. Requirements

### 3.1 Functional Requirements - 5대 화면 구성

| ID | 화면 | 설명 | Priority |
|----|------|------|----------|
| FR-01 | **Command Center** (컨트롤 타워) | 전체 포트폴리오 리스크 현황 한눈에 파악. 히트맵 + 리스크 스코어보드 + 라이브 시그널 피드 + AI 요약 | **Critical** |
| FR-02 | **Supply Chain X-Ray** (공급망 투시) | 3D Force-Graph로 멀티 티어(Tier 1/2/3) 공급망 시각화. 노드 클릭 시 드릴다운. Single Point of Failure 자동 감지. Neo4j 직결 | **Critical** |
| FR-03 | **Risk Deep Dive** (리스크 심층분석) | Deal 선택 후 Company → RiskCategory → RiskEntity → RiskEvent 순 계층적 드릴다운. 각 레벨에서 점수 분해, 근거 자료, AI 해석 제공 | **Critical** |
| FR-04 | **War Room** (워게임 시뮬레이션) | 디지털 트윈 기반 What-If 시나리오. AI가 시나리오 생성 + 영향 분석 + 최적 복구경로 추천. 비용-효과 시각화 | **High** |
| FR-05 | **AI Copilot** (AI 어시스턴트) | 화면 우측 슬라이딩 패널. 자연어→Cypher 변환, 인사이트 생성, 보고서 초안, 대화형 리스크 분석. 모든 화면에서 접근 가능 | **Critical** |

### 3.2 화면별 상세 요구사항

#### FR-01: Command Center (컨트롤 타워)

```
┌──────────────────────────────────────────────────────────────┐
│  [Global Search Bar - AI Powered]          [Alerts] [Copilot]│
├──────────────┬──────────────────┬────────────────────────────┤
│              │                  │                            │
│  Portfolio   │  Risk Heatmap    │  Live Signal Feed          │
│  Scorecard   │  (10 Categories  │  (실시간 뉴스/공시/이슈)   │
│  (Deal 카드)  │   x Companies)   │                            │
│              │                  │  AI Daily Brief            │
│              │                  │  (오늘의 핵심 리스크 요약)  │
├──────────────┴──────────────────┴────────────────────────────┤
│  Trend Chart (7/30/90일)  │  Top Risk Entities  │  Actions   │
└──────────────────────────────────────────────────────────────┘
```

**핵심 요소:**
- **Portfolio Scorecard**: 각 Deal 카드 - Glassmorphism 스타일, 리스크 레벨 색상 그래디언트, 미니 스파크라인
- **Risk Heatmap**: 10개 카테고리(주주/임원/신용/법률/지배구조/운영/감사/ESG/공급망/기타) x 기업별 히트맵
- **Live Signal Feed**: 실시간 리스크 신호 타임라인 (뉴스 아이콘 + 소스 + 영향도 뱃지)
- **AI Daily Brief**: GPT가 오늘의 포트폴리오 핵심 변동사항 요약

#### FR-02: Supply Chain X-Ray (공급망 투시)

```
┌──────────────────────────────────────────────────────────────┐
│                    3D Force-Directed Graph                    │
│                                                              │
│         [Tier 3]  ←→  [Tier 2]  ←→  [Tier 1]  ←→  [TARGET] │
│                                                              │
│    노드 크기 = 리스크 점수                                     │
│    엣지 두께 = 의존도                                          │
│    색상 = 리스크 레벨 (Green/Yellow/Red)                       │
│    파티클 애니메이션 = 리스크 전이 흐름                          │
│                                                              │
├──────────────┬───────────────────────────────────────────────┤
│  Node Detail │  Propagation Analysis                         │
│  (선택 노드)  │  - 전이 경로 시각화                             │
│              │  - Single Point of Failure 경고                │
│              │  - AI 대체 공급선 추천                           │
└──────────────┴───────────────────────────────────────────────┘
```

**핵심 기술:**
- `react-force-graph-3d` (WebGL/ThreeJS) 3D 그래프
- 노드 간 파티클 애니메이션으로 리스크 전이 흐름 시각화
- 클릭 시 Neo4j에서 실시간 인접 노드 확장 (Lazy Loading)
- 카메라 자동 포커싱 + 줌 투 노드
- 필터: Tier, 리스크 레벨, 카테고리, 관계 유형

#### FR-03: Risk Deep Dive (리스크 심층분석)

```
┌──────────────────────────────────────────────────────────────┐
│  [Deal 선택] ▸ [Company 선택] ▸ [Category 선택] ▸ [Entity]   │
│  ← Breadcrumb 네비게이션                                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Company Overview ─────────────────────────────────────┐  │
│  │  Score: 67 (WARNING)  │  Direct: 45  Propagated: +22   │  │
│  │  ███████████████░░░░░░ 67/100                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ 10 Risk Categories ──────────────────────────────────┐  │
│  │  [주주 📊] [임원 👔] [신용 💳] [법률 ⚖️] [지배 🏛️]     │  │
│  │  [운영 ⚙️] [감사 📋] [ESG 🌱] [공급망 🔗] [기타 📎]   │  │
│  │                                                        │  │
│  │  → 클릭 시 해당 카테고리 하위 Entity 목록 펼침           │  │
│  │  → Entity 클릭 시 Event 목록 + 근거자료 표시             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ AI Interpretation ───────────────────────────────────┐  │
│  │  선택된 레벨의 컨텍스트에 맞는 AI 해석 자동 생성         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**핵심 인터렉션:**
- Breadcrumb 드릴다운: Deal → Company → Category → Entity → Event
- 아코디언/트리 뷰로 계층 탐색
- 각 레벨 전환 시 슬라이드 애니메이션
- 점수 분해 시각화: Donut Chart (카테고리), Waterfall Chart (Entity→Event)
- 근거 자료(뉴스/공시) 링크 + 원문 미리보기

#### FR-04: War Room (워게임 시뮬레이션)

```
┌──────────────────────────────────────────────────────────────┐
│  ┌─ Scenario Builder ──┐  ┌─ Impact Visualization ────────┐ │
│  │                     │  │                               │ │
│  │  AI 시나리오 생성기   │  │  Before / After 비교          │ │
│  │  "대만해협 봉쇄시     │  │  - 그래프 오버레이            │ │
│  │   영향은?"           │  │  - Sankey 다이어그램           │ │
│  │                     │  │  - 리스크 점수 변동 차트        │ │
│  │  [프리셋 시나리오]   │  │                               │ │
│  │  [커스텀 생성]       │  │  Time to Recover 계산         │ │
│  │  [AI 추천 시나리오]  │  │  비용-효과 매트릭스            │ │
│  │                     │  │                               │ │
│  └─────────────────────┘  └───────────────────────────────┘ │
│  ┌─ AI 대응 권고 ──────────────────────────────────────────┐ │
│  │  즉시 조치 / 모니터링 포인트 / 대체 공급선 추천          │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**핵심 기능:**
- AI가 자연어로 시나리오 입력 → 자동 파라미터 생성
- Before/After 그래프 오버레이 비교
- Cascade 분석: Tier 1 → Tier 2 → Tier 3 전파 시뮬레이션
- Dynamic Buffer Optimization: 적정 재고량 AI 추천
- 복구 경로(Time to Recover) 시각화

#### FR-05: AI Copilot (글로벌 AI 어시스턴트)

```
┌── 슬라이딩 패널 (화면 우측) ──────────┐
│                                       │
│  🤖 AI Copilot                        │
│  ─────────────────────────────────    │
│                                       │
│  [자연어 입력]                         │
│  "SK하이닉스의 법률 리스크 요약해줘"    │
│                                       │
│  → Cypher 쿼리 자동 생성 + 실행       │
│  → 결과 시각화 (차트/테이블/그래프)     │
│  → AI 해석 + 권고사항                  │
│                                       │
│  [컨텍스트 인식]                       │
│  현재 보고 있는 화면/노드/카테고리에    │
│  맞는 질문 자동 제안                   │
│                                       │
│  [빠른 액션]                          │
│  - 보고서 초안 생성                    │
│  - 유사 사례 검색                      │
│  - 리스크 비교 분석                    │
│  - 트렌드 예측                         │
└───────────────────────────────────────┘
```

### 3.3 Non-Functional Requirements

| Category | Criteria | Measurement |
|----------|----------|-------------|
| Performance | 3D 그래프 100+ 노드 60fps | Chrome DevTools FPS |
| Performance | 페이지 전환 < 300ms | Lighthouse |
| Visual | Glassmorphism + Gradient 일관성 | 디자인 리뷰 |
| Animation | 부드러운 전환 (Framer Motion) | 60fps 유지 |
| Neo4j 가시성 | 모든 데이터가 Neo4j에서 오는 것이 명확 | "Neo4j Powered" 배지 |
| AI 가시성 | AI 활용이 화면 전반에 드러남 | "GPT-4 Powered" 표시 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] 5개 메인 화면 모두 구현 완료
- [ ] 5-Node 스키마 완전 반영 (드릴다운 동작)
- [ ] 3D 그래프 인터렉션 (줌/팬/클릭/파티클)
- [ ] AI Copilot 모든 화면에서 동작
- [ ] Mock 데이터 + 실 API 모두 지원
- [ ] 애니메이션/전환 효과 적용

### 4.2 WOW Factor Checklist (대회 심사 포인트)

- [ ] 3D 그래프 멀티 티어 공급망 시각화 → "이것이 Graph DB의 힘"
- [ ] 자연어 질의 → Cypher → 시각화 실시간 시연
- [ ] What-If 시나리오 → AI 영향 분석 실시간 시연
- [ ] 리스크 전이 파티클 애니메이션 → 직관적 이해
- [ ] AI Daily Brief → "매일 아침 AI가 리스크 브리핑"
- [ ] Breadcrumb 드릴다운 → Deal부터 뉴스 원문까지 5클릭 이내

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 3D 그래프 성능 이슈 (100+ 노드) | High | Medium | react-force-graph-3d 최적화 + LOD(Level of Detail) |
| AI API 응답 지연 | Medium | Medium | Mock 폴백 + 스켈레톤 로딩 |
| 새 디펜던시 다수 추가 | Medium | Low | 최소 필수만 추가 (react-force-graph-3d, framer-motion) |
| 기존 API와 5-Node 스키마 불일치 | High | High | V5 API 엔드포인트 신규 추가 or Mock 데이터 |
| 개발 시간 부족 | High | Medium | 핵심 3화면(Command/X-Ray/DeepDive) 우선 구현 |

---

## 6. Architecture Considerations

### 6.1 Project Level

| Level | Selected |
|-------|:--------:|
| **Starter** | ☐ |
| **Dynamic** | ☑ |
| **Enterprise** | ☐ |

> React + Vite SPA 유지, 기능 기반 모듈화

### 6.2 Key Architectural Decisions

| Decision | Selected | Rationale |
|----------|----------|-----------|
| Framework | React + Vite (기존 유지) | 대회 일정상 프레임워크 변경 부적절 |
| 3D 그래프 | react-force-graph-3d | WebGL 기반 3D + 파티클 + 인터렉션 최고 |
| 애니메이션 | framer-motion | 페이지 전환, 컴포넌트 등장 효과 |
| 상태관리 | React Context + useState | 현행 유지, 복잡도 최소화 |
| 스타일 | Tailwind CSS (기존 유지) + CSS 커스텀 속성 | Glassmorphism 구현 |
| 차트 | recharts (기존) + 커스텀 SVG | Heatmap, Waterfall, Sankey |
| API | 기존 riskApi + V5 엔드포인트 확장 | Mock 폴백 유지 |

### 6.3 컴포넌트 구조 (신규)

```
components/risk-v2/
├── layout/
│   ├── RiskShell.tsx           # 전체 레이아웃 (헤더/네비/콘텐츠)
│   ├── NavigationBar.tsx       # 5화면 네비게이션
│   └── AICopilotPanel.tsx      # 우측 슬라이딩 AI 패널
├── command-center/
│   ├── CommandCenter.tsx       # FR-01 메인
│   ├── PortfolioScorecard.tsx  # Deal 카드 그리드
│   ├── RiskHeatmap.tsx         # 10카테고리 히트맵
│   ├── LiveSignalFeed.tsx      # 실시간 신호
│   └── AIDailyBrief.tsx        # AI 일일 요약
├── supply-chain-xray/
│   ├── SupplyChainXRay.tsx     # FR-02 메인
│   ├── ForceGraph3D.tsx        # 3D 그래프 wrapper
│   ├── NodeDetail.tsx          # 선택 노드 상세
│   └── PropagationFlow.tsx     # 전이 흐름 분석
├── deep-dive/
│   ├── RiskDeepDive.tsx        # FR-03 메인
│   ├── BreadcrumbNav.tsx       # 드릴다운 네비
│   ├── CompanyOverview.tsx     # Company 레벨
│   ├── CategoryGrid.tsx        # 10개 카테고리 그리드
│   ├── EntityList.tsx          # Entity 목록
│   ├── EventTimeline.tsx       # Event 타임라인
│   └── EvidenceViewer.tsx      # 근거자료 뷰어
├── war-room/
│   ├── WarRoom.tsx             # FR-04 메인
│   ├── ScenarioBuilder.tsx     # 시나리오 생성기
│   ├── ImpactVisualization.tsx # Before/After 비교
│   ├── CascadeAnalysis.tsx     # Cascade 분석
│   └── RecoveryPath.tsx        # 복구경로 추천
├── ai-copilot/
│   ├── CopilotChat.tsx         # 대화형 인터페이스
│   ├── NaturalLanguageInput.tsx # 자연어 입력
│   ├── CypherResultView.tsx    # 쿼리 결과 시각화
│   └── ContextSuggestions.tsx  # 컨텍스트 기반 추천
├── shared/
│   ├── GlassCard.tsx           # Glassmorphism 카드
│   ├── RiskBadge.tsx           # 리스크 레벨 뱃지
│   ├── ScoreGauge.tsx          # 점수 게이지
│   ├── TrendIndicator.tsx      # 트렌드 화살표
│   ├── SkeletonLoader.tsx      # 로딩 스켈레톤
│   └── PoweredByBadge.tsx      # "Neo4j/GPT-4 Powered" 뱃지
├── design-tokens.ts            # 디자인 토큰 (색상/그래디언트/글래스 효과)
├── types-v2.ts                 # V2 타입 정의
├── api-v2.ts                   # V2 API 클라이언트
└── index.ts                    # 배럴 파일
```

### 6.4 디자인 시스템

```css
/* Glassmorphism 기본 스타일 */
.glass-card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 16px;
}

/* 그래디언트 색상 팔레트 */
--gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
--gradient-danger: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
--gradient-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
--gradient-warning: linear-gradient(135deg, #f6d365 0%, #fda085 100%);

/* 리스크 레벨 색상 */
--risk-pass: #10b981 → #34d399;
--risk-warning: #f59e0b → #fbbf24;
--risk-fail: #ef4444 → #f87171;
```

---

## 7. Dependencies (추가 필요 패키지)

| Package | Purpose | Size |
|---------|---------|------|
| `react-force-graph-3d` | 3D Force-Directed 그래프 | ~2MB |
| `three` | WebGL 3D 렌더링 (peer dep) | ~1MB |
| `framer-motion` | 애니메이션/페이지 전환 | ~150KB |
| `@nivo/heatmap` (optional) | 히트맵 차트 | ~200KB |

> 최소한의 패키지만 추가하여 번들 사이즈 관리

---

## 8. Implementation Priority (구현 순서)

### Phase A: Foundation (기반)
1. 디자인 토큰 + Glassmorphism 공통 컴포넌트
2. RiskShell 레이아웃 + 네비게이션
3. types-v2.ts + api-v2.ts (5-Node 스키마 반영)

### Phase B: Core Screens (핵심 화면) - **최우선**
4. **Command Center** - 포트폴리오 대시보드
5. **Supply Chain X-Ray** - 3D 그래프
6. **Risk Deep Dive** - 계층적 드릴다운

### Phase C: Advanced (고급 기능)
7. **War Room** - 시뮬레이션
8. **AI Copilot** - 글로벌 AI 패널

### Phase D: Polish (마감)
9. 애니메이션/전환 효과 강화
10. 데모 시나리오 준비

---

## 9. Next Steps

1. [ ] Plan 문서 승인
2. [ ] Design 문서 작성 (`supply-chain-risk-v2.design.md`)
3. [ ] 패키지 설치 (react-force-graph-3d, framer-motion)
4. [ ] Phase A 구현 시작

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-06 | Initial draft | AI Agent |
