# Step 3. 리스크 모니터링 시스템 - Plan Document

## 1. 개요 (Overview)

### 1.1 프로젝트 배경
JB우리캐피탈 영업/리스크 통합 사전 검증 플랫폼 **newwave**의 핵심 구성 요소 중 하나인 **Step 3. 리스크** 모듈을 개발합니다.

### 1.2 목표
- 승인된 딜에 대한 **실시간 리스크 모니터링**
- Graph DB 기반 **시뮬레이션** (예: 부산항 파업, 반도체 소비재 시나리오)
- 리스크 **실시간 감지** 및 **사후 대응** 지원
- 부실 딜 **사전 차단**, 골든타임 확보

### 1.3 핵심 가치
| 항목 | 설명 |
|------|------|
| **Input** | 연동된 승인 딜 데이터 |
| **Action** | Graph DB 기반 시뮬레이션 |
| **Output** | 리스크 실시간 감지 및 사후 대응 가이드 |
| **Value** | 부실 딜 사전 차단, 골든타임 확보 |

---

## 2. 기존 시도 분석 (As-Is Analysis)

### 2.1 실패작 분석 (`risk_engine/실패작.md`)
기존 Python 기반 시스템 (v14.1)의 주요 특징:

**장점:**
- 14대 리스크 카테고리 정의 완료
- 6대 핵심 정보 채널 통합 설계
- AI 기반 가이드 생성 로직 구현 (GPT-4.1 mini)
- Text2Cypher 자연어 질의 기능
- 3단계 조기경보 타임라인 설계

**개선 필요 사항:**
- 터미널 기반 UI → 웹 UI로 전환 필요
- dashboard_adapter.py의 스냅샷 구조를 React에서 활용해야 함
- 실시간성 부족 (배치 처리 중심)
- 시뮬레이션 기능 미구현

### 2.2 핵심 재사용 요소
| 파일 | 재사용 가능 요소 |
|------|-----------------|
| `core.py` | 리스크 스코어링 로직, 카테고리 가중치 |
| `ai_service.py` | AI 가이드 생성, 산업별 컨텍스트, Text2Cypher |
| `dashboard_adapter.py` | JSON 스냅샷 스키마 (monitoring.v1) |

---

## 3. 개발 범위 (Scope)

### 3.1 독립성 원칙
- **기존 컴포넌트에 영향 없음**: Header, GlobalDashboard 등 기존 파일 수정 최소화
- **독립 라우트**: `/risk` 경로로 별도 접근
- **독립 컴포넌트 폴더**: `components/risk/` 하위에 모든 컴포넌트 배치

### 3.2 핵심 기능

#### 3.2.1 리스크 대시보드 (Risk Dashboard)
- 포트폴리오 전체 리스크 현황 한눈에 파악
- 딜별 리스크 점수 및 상태 표시 (PASS/WARNING/FAIL)
- 14개 카테고리별 리스크 분포 시각화

#### 3.2.2 실시간 리스크 신호 (Real-time Signals)
- 법적 위기 (LEGAL_CRISIS)
- 시장 위기 (MARKET_CRISIS)
- 운영 리스크 (OPERATIONAL)
- 긴급 알림 표시

#### 3.2.3 타임라인 뷰 (3-Stage Timeline)
- Stage 1: 뉴스 보도 (선행 감지)
- Stage 2: 금융위 통지 (규제 리스크)
- Stage 3: 대주단 확인 (조치 필요)

#### 3.2.4 Entity Relationship Graph
- 기업 관계도 시각화
- 공급망 연결 표시
- 리스크 전이 경로 시각화

#### 3.2.5 시뮬레이션 패널 (Simulation)
- 시나리오 선택 (부산항 파업, 반도체 수요 감소 등)
- 영향 받는 딜 목록 및 예상 리스크 점수 변화
- What-if 분석

#### 3.2.6 AI Action Guide
- RM 영업 가이드 (선제적 대응)
- OPS 방어 가이드 (방어적 대응)
- 산업별 맞춤 인사이트

---

## 4. 기술 스택 (Tech Stack)

### 4.1 Frontend
- **React 19** + **TypeScript**
- **Vite** (빌드 도구)
- **TailwindCSS** (기존 프로젝트 스타일 유지)

### 4.2 데이터 처리
- Mock 데이터로 시작 (Python 백엔드 연동 이전)
- `dashboard_adapter.py`의 스키마 (monitoring.v1) 준수

### 4.3 시각화
- SVG 기반 Graph 시각화
- CSS Grid/Flexbox 레이아웃

---

## 5. 컴포넌트 구조 (Component Structure)

```
components/
└── risk/
    ├── RiskPage.tsx              # 메인 페이지 (독립 라우트)
    ├── RiskOverview.tsx          # 포트폴리오 리스크 요약
    ├── RiskSignals.tsx           # 실시간 리스크 신호
    ├── RiskTimeline.tsx          # 3단계 타임라인
    ├── RiskGraph.tsx             # Entity Relationship Graph
    ├── RiskSimulation.tsx        # 시뮬레이션 패널
    ├── RiskActionGuide.tsx       # AI 대응 가이드
    ├── RiskBreakdown.tsx         # 14개 카테고리 분석
    ├── RiskDealCard.tsx          # 개별 딜 카드
    └── types.ts                  # 리스크 관련 타입 정의
```

---

## 6. 데이터 스키마 (Data Schema)

### 6.1 Monitoring Schema (v1)
```typescript
interface RiskSnapshot {
  schemaVersion: "monitoring.v1";
  generatedAt: string;
  data: {
    dealName: string;
    tranche: string;
    status: "PASS" | "WARNING" | "FAIL";
    metrics: {
      ltv: { current: string; prev: string; trend: "up" | "down" };
      ebitda: string;
      covenant: string;
    };
    timeline: TimelineEvent[];
    graph: { nodes: GraphNode[]; edges: GraphEdge[] };
    rmActions: ActionGuide;
    opsActions: ActionGuide;
    evidence: Evidence[];
  };
  _meta: {
    score: number;
    propagated: number;
    coverage: number;
    signal: string;
    source: string;
  };
}
```

### 6.2 리스크 카테고리 (14개)
1. 공시 (Disclosure)
2. 뉴스 (News)
3. 주주 (Shareholder)
4. 임원 (Executive)
5. 특허 (Patent) - High Weight
6. 채용/평판 (HR/Review)
7. 소송 (Legal)
8. 신용등급 (Credit Rating)
9. 금감원 (FSS)
10. ESG
11. SNS/커뮤니티
12. 부동산 (Real Estate)
13. 상표 (Trademark)
14. 경쟁사 (Competitor)

---

## 7. 구현 우선순위 (Priority)

| 우선순위 | 기능 | 중요도 | 복잡도 |
|---------|------|--------|--------|
| P0 | RiskPage (메인 레이아웃) | 높음 | 낮음 |
| P0 | RiskOverview (요약 대시보드) | 높음 | 중간 |
| P1 | RiskSignals (실시간 신호) | 높음 | 중간 |
| P1 | RiskTimeline (3단계 타임라인) | 높음 | 중간 |
| P2 | RiskGraph (관계도) | 중간 | 높음 |
| P2 | RiskActionGuide (AI 가이드) | 중간 | 중간 |
| P3 | RiskSimulation (시뮬레이션) | 중간 | 높음 |
| P3 | RiskBreakdown (카테고리 분석) | 낮음 | 낮음 |

---

## 8. 마일스톤 (Milestones)

### Phase 1: 기본 구조 (Foundation)
- [ ] 타입 정의 (`types.ts`)
- [ ] 메인 페이지 레이아웃 (`RiskPage.tsx`)
- [ ] Mock 데이터 생성
- [ ] App.tsx에 라우트 추가 (최소 수정)

### Phase 2: 핵심 기능 (Core Features)
- [ ] 리스크 요약 대시보드 (`RiskOverview.tsx`)
- [ ] 실시간 신호 패널 (`RiskSignals.tsx`)
- [ ] 3단계 타임라인 (`RiskTimeline.tsx`)

### Phase 3: 고급 기능 (Advanced Features)
- [ ] Entity Graph 시각화 (`RiskGraph.tsx`)
- [ ] AI 대응 가이드 (`RiskActionGuide.tsx`)
- [ ] 14개 카테고리 분석 (`RiskBreakdown.tsx`)

### Phase 4: 시뮬레이션 (Simulation)
- [ ] 시나리오 선택 UI (`RiskSimulation.tsx`)
- [ ] What-if 분석 기능
- [ ] 영향도 시각화

---

## 9. 성공 지표 (Success Criteria)

1. **독립성**: 기존 컴포넌트 수정 최소화 (Header.tsx 네비게이션 추가만)
2. **완성도**: P0, P1 우선순위 기능 100% 구현
3. **사용성**: 직관적인 UI/UX (기존 프로젝트 스타일 일관성)
4. **확장성**: Python 백엔드 연동 준비 완료 (스키마 호환)

---

## 10. 리스크 및 대응 방안

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| 기존 코드 충돌 | 높음 | 독립 폴더 구조, 최소 수정 원칙 |
| 데이터 스키마 불일치 | 중간 | monitoring.v1 스키마 엄격 준수 |
| 복잡한 Graph 시각화 | 중간 | SVG 기반 단순화, 외부 라이브러리 최소화 |

---

## 11. 참고 자료

- `risk_engine/실패작.md` - 기존 시스템 스펙
- `risk_engine/dashboard_adapter.py` - JSON 스냅샷 구조
- `risk_engine/ai_service.py` - AI 가이드 로직
- `risk_engine/core.py` - 리스크 스코어링 로직

---

**작성일**: 2026-02-05
**버전**: v1.0
**담당자**: Step 3 리스크 개발팀
