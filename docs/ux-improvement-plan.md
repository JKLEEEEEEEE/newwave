# UI/UX 개선 구현 계획서

> 작성일: 2026-02-07
> 대상: `components/risk-v2/` 핵심 7개 파일
> 목적: 대회 임팩트 극대화를 위한 UX 결함 수정 및 품질 향상

---

## 0. 요약 매트릭스

| 파일 | 긴급 | 중요 | 개선 | 총 이슈 |
|------|:----:|:----:|:----:|:-------:|
| SupplyChainXRay.tsx | 2 | 2 | 2 | 6 |
| CommandCenter.tsx | 1 | 2 | 1 | 4 |
| RiskDeepDive.tsx | 1 | 3 | 1 | 5 |
| WarRoom.tsx | 0 | 2 | 2 | 4 |
| AICopilotPanel.tsx | 0 | 1 | 2 | 3 |
| RiskV2Context.tsx | 0 | 2 | 1 | 3 |
| Header.tsx | 0 | 1 | 2 | 3 |
| **합계** | **4** | **13** | **11** | **28** |

---

## 1. 공유 컴포넌트 (먼저 생성/개선)

### 1.1 SkeletonLoader.tsx -- 이미 존재, 확장 필요

**파일 위치**: `components/risk-v2/shared/SkeletonLoader.tsx`
**현재 상태**: 기본 스켈레톤(SkeletonCard, SkeletonGauge, SkeletonLine, SkeletonTableRow) 존재
**필요 추가 변형**:

```
추가할 export:
- SkeletonCategoryGrid: 5열 x 2행 카테고리 히트맵 스켈레톤 (CommandCenter, RiskDeepDive 공용)
- SkeletonDealList: 딜 리스트 카드 3개 스켈레톤 (CommandCenter, RiskDeepDive 공용)
- SkeletonEventFeed: 이벤트 피드 5줄 스켈레톤 (CommandCenter 우측 Recent Events)
- SkeletonTimeline: 타임라인 형태 스켈레톤 (RiskDeepDive Entity Level)
- SkeletonScenarioCard: 시나리오 카드 3장 스켈레톤 (WarRoom)
- SkeletonGraph3D: 3D 그래프 영역 전체 커버 스켈레톤 (SupplyChainXRay)
```

**Props 설계**:
```ts
// 기존 SkeletonLoader에 variant prop 추가하는 방식은 비권장.
// 각 프리셋을 개별 named export로 유지 (현재 패턴과 일치)
export function SkeletonCategoryGrid({ columns?: number; rows?: number }) // 기본 5x2
export function SkeletonDealList({ count?: number }) // 기본 3
export function SkeletonEventFeed({ count?: number }) // 기본 5
export function SkeletonTimeline({ count?: number }) // 기본 3
export function SkeletonScenarioCard({ count?: number }) // 기본 3
export function SkeletonGraph3D() // 중앙 로딩 + 파티클 애니메이션
```

### 1.2 ErrorState.tsx -- 신규 생성

**파일 위치**: `components/risk-v2/shared/ErrorState.tsx`

```ts
interface ErrorStateProps {
  title?: string;           // 기본: "데이터를 불러올 수 없습니다"
  message?: string;         // 에러 상세 메시지
  onRetry?: () => void;     // 재시도 콜백 (없으면 버튼 미표시)
  variant?: 'inline' | 'fullpage' | 'card';  // 배치 스타일
  icon?: React.ReactNode;   // 커스텀 아이콘 (기본: 경고 SVG)
}
```

**디자인**: GlassCard 기반, 빨간-보라 그래디언트 테두리, 재시도 버튼은 기존 보라 그래디언트 버튼 스타일

### 1.3 EmptyState.tsx -- 신규 생성

**파일 위치**: `components/risk-v2/shared/EmptyState.tsx`

```ts
interface EmptyStateProps {
  title?: string;           // 기본: "데이터가 없습니다"
  message?: string;         // 안내 메시지
  action?: { label: string; onClick: () => void };  // CTA 버튼
  icon?: React.ReactNode;   // 커스텀 아이콘
}
```

### 1.4 NodeDetailPanel.tsx -- SupplyChainXRay에서 분리 (권장)

현재 `SupplyChainXRay.tsx` Line 406~537에 인라인으로 존재하는 Node Detail Panel을 별도 컴포넌트로 분리.

```ts
interface NodeDetailPanelProps {
  node: GraphNode3D;
  graphData: { nodes: GraphNode3D[]; links: GraphLink3D[] };
  onClose: () => void;
  onNavigateDeepDive: (nodeId: string) => void;
  onNavigateCategory: (categoryCode: string) => void;
}
```

---

## 2. SupplyChainXRay.tsx (긴급 2건 + 중요 2건 + 개선 2건)

**파일**: `D:\new_wave\components\risk-v2\screens\SupplyChainXRay.tsx` (594줄)

### [긴급-1] handleNodeClick 뷰 자동전환 제거

**위치**: Line 135~151
**현재 동작**: `riskCategory` 노드 클릭 시 `selectCategory()` 호출 후 즉시 `setActiveView('deepdive')` 호출
**문제점**: 사용자가 클릭과 동시에 화면 전환되어 NodeDetailPanel 확인 불가. UX 패턴 위반 (클릭 = 선택, 더블클릭/버튼 = 이동)
**수정 계획**:

```
Line 142-146:
현재:
  case 'riskCategory':
    if (node.categoryCode) {
      selectCategory(node.categoryCode);
      setActiveView('deepdive');   // <-- 제거
    }

수정:
  case 'riskCategory':
    if (node.categoryCode) {
      selectCategory(node.categoryCode);
      // 뷰 전환은 NodeDetailPanel의 "카테고리 분석" 버튼에서 수행
    }
```

**영향 범위**: handleNodeClick 함수의 dependency array에서 `setActiveView` 제거 가능 (Line 151)

### [긴급-2] 노드 커스텀 툴팁 (마우스오버)

**위치**: Line 165~167 (`nodeLabelFn`)
**현재 동작**: ForceGraph3D 기본 tooltip으로 `"이름\n리스크: XX점"` 텍스트만 표시
**문제점**: 3D 그래프의 핵심 인터랙션인 마우스오버가 너무 단순. 노드 타입 구분 불가, 위험도 시각화 없음

**수정 계획**:
ForceGraph3D의 `nodeLabel` prop은 HTML 문자열을 지원. HTML overlay 방식으로 커스텀 툴팁 구현.

```
Line 165-167 대체:
const nodeLabelFn = useCallback((node: FGNode) => {
  const typeLabel = {
    deal: 'Deal', mainCompany: 'Main Company',
    relatedCompany: 'Related Company', riskCategory: 'Risk Category',
    riskEntity: 'Risk Entity',
  }[node.nodeType] || node.nodeType;

  const levelColor = {
    PASS: '#10b981', WARNING: '#f59e0b', FAIL: '#ef4444'
  }[node.riskLevel] || '#6b7280';

  return `
    <div style="background:rgba(15,23,42,0.95); border:1px solid rgba(148,163,184,0.2);
                border-radius:12px; padding:12px 16px; min-width:180px;
                font-family:system-ui; backdrop-filter:blur(8px);">
      <div style="font-size:13px; font-weight:700; color:white; margin-bottom:6px;">
        ${node.name}
      </div>
      <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
        <span style="font-size:10px; padding:2px 6px; border-radius:4px;
                     background:rgba(139,92,246,0.15); color:#a78bfa; font-weight:600;">
          ${typeLabel}
        </span>
        <span style="font-size:10px; color:#64748b;">Tier ${node.tier}</span>
      </div>
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <span style="font-size:11px; color:#94a3b8;">Risk Score</span>
        <span style="font-size:14px; font-weight:700; color:${levelColor};">
          ${node.riskScore}
        </span>
      </div>
      ${node.metadata?.sector ? `
        <div style="font-size:10px; color:#64748b; margin-top:4px;">
          ${String(node.metadata.sector)}
        </div>
      ` : ''}
    </div>
  `;
}, []);
```

### [중요-1] 그래프 로딩 상태 개선

**위치**: Line 96~119 (graphLoading 상태), Line 219~235 (빈 상태 UI)
**문제점**: `graphLoading` 상태가 존재하지만 JSX에서 전혀 사용하지 않음. 그래프 로딩 중에도 "딜을 선택하세요" 메시지 표시

**수정 계획**:
```
Line 196 이전에 graphLoading 체크 분기 추가:

{graphLoading ? (
  <div className="flex items-center justify-center h-full">
    <SkeletonGraph3D />   // 새 프리셋 스켈레톤
  </div>
) : selectedDealId && graphData.nodes.length > 0 ? (
  <ForceGraph3D ... />
) : (
  // 기존 빈 상태 메시지
)}
```

### [중요-2] API 에러 시 안내 없음

**위치**: Line 107~116
**문제점**: `res.success === false`일 때 빈 graphData 설정만 하고 사용자 피드백 없음

**수정 계획**:
```
Line 96 근처에 graphError 상태 추가:
const [graphError, setGraphError] = useState<string | null>(null);

Line 109-113:
if (res.success && res.data) {
  setGraphData(res.data);
  setGraphError(null);
} else {
  setGraphData({ nodes: [], links: [] });
  setGraphError(res.error ?? '그래프 데이터를 불러올 수 없습니다');
}

JSX에서 graphError 표시:
{graphError && !graphLoading && (
  <ErrorState
    title="그래프 로딩 실패"
    message={graphError}
    onRetry={() => { /* refetch */ }}
    variant="fullpage"
  />
)}
```

### [개선-1] NodeDetailPanel 분리

**위치**: Line 406~537
**내용**: 현재 인라인 130줄짜리 패널을 `shared/NodeDetailPanel.tsx`로 분리하여 재사용성 확보

### [개선-2] 좌측 패널 관련기업 클릭 피드백 부족

**위치**: Line 330~350
**문제점**: 관련기업 클릭 시 `selectCompany(rc.id)`만 호출. 어떤 기업이 현재 선택되었는지 하이라이트 없음

**수정 계획**:
```
Line 333:
className={`flex items-center justify-between p-2 rounded-lg border transition-colors cursor-pointer ${
  state.selectedCompanyId === rc.id
    ? 'bg-purple-500/10 border-purple-500/30'
    : 'bg-slate-800/30 border-white/5 hover:border-purple-500/30'
}`}
```

---

## 3. CommandCenter.tsx (긴급 1건 + 중요 2건 + 개선 1건)

**파일**: `D:\new_wave\components\risk-v2\screens\CommandCenter.tsx` (435줄)

### [긴급-1] 비선택 딜 점수 "-" 표시 문제

**위치**: Line 244~255
**현재 동작**: `company`가 null일 때(비선택 딜) 60x60 원 안에 "-" 표시
**문제점**: 딜 목록에서 선택되지 않은 딜은 항상 점수가 "-"로 보임. 딜 목록 API(`/api/v4/deals`)의 응답에 개별 딜 점수가 포함되어 있을 가능성이 있으나 현재 활용하지 않음

**수정 계획**:
1. API 확인: `fetchDealsV2` (api-v2.ts Line 108~161)에서 V4 응답의 `d.score` 필드를 `DealV2` 타입에 매핑하는지 확인 -> 현재 `DealV2` 타입에 `score` 필드 없음
2. `types-v2.ts`의 `DealV2` 인터페이스에 `score?: number` 및 `riskLevel?: RiskLevelV2` 필드 추가
3. `api-v2.ts` Line 112~120에서 V4 딜 목록 매핑 시 score 매핑 추가:
   ```
   score: d.score || 0,
   riskLevel: determineRiskLevel(d.score || 0),
   ```
4. CommandCenter.tsx Line 244~255: `deal.score`가 있으면 ScoreGauge로 표시, 없으면 기존 "-"

```
{company ? (
  <ScoreGauge score={company.totalRiskScore} size={60} ... />
) : deal.score != null && deal.score > 0 ? (
  <ScoreGauge score={deal.score} size={60} />
) : (
  <div className="w-[60px] h-[60px] rounded-full bg-slate-800/50 ...">
    <span className="text-slate-500 text-xs">-</span>
  </div>
)}
```

### [중요-1] 딜 목록 로딩 스켈레톤

**위치**: Line 226~229
**현재 동작**: `"딜 목록 로딩 중..."` 텍스트만 표시
**수정 계획**:
```
Line 226-229 대체:
{dealsLoading ? (
  <div className="flex flex-col gap-3">
    <SkeletonDealList count={3} />
  </div>
) : deals.map(...)}
```

### [중요-2] Recent Events 빈 상태 처리

**위치**: Line 324~328
**현재 동작**: 이벤트가 없을 때 `"데이터 로딩 중..."` 고정 텍스트. 실제로 로딩 완료 후에도 이벤트가 없으면 동일 메시지 표시
**문제점**: 로딩 상태와 빈 상태를 구분하지 않음

**수정 계획**:
```
{state.dealsLoading || (selectedDealId && state.dealDetailLoading) ? (
  <SkeletonEventFeed count={5} />
) : recentEvents.length > 0 ? (
  recentEvents.map(...)
) : (
  <EmptyState
    title="최근 이벤트 없음"
    message="선택된 딜에 등록된 이벤트가 없습니다"
  />
)}
```

### [개선-1] 카테고리 클릭 시 뷰 자동전환

**위치**: Line 119~122
**현재 동작**: 카테고리 클릭 시 즉시 `setActiveView('deepdive')` 호출

**수정 계획**: 이 파일에서의 카테고리 클릭 뷰전환은 의도된 UX로 보임 (CommandCenter는 대시보드 역할). 유지하되, 전환 전 간단한 확인 피드백(ripple 효과 또는 약간의 딜레이) 추가 검토. 우선순위 낮음.

---

## 4. RiskDeepDive.tsx (긴급 1건 + 중요 3건 + 개선 1건)

**파일**: `D:\new_wave\components\risk-v2\screens\RiskDeepDive.tsx` (837줄)

### [긴급-1] 관련기업 클릭 시 뷰 전환 문제

**위치**: Line 322~325 (`CompanyDetailLevel` 내부)
**현재 동작**:
```tsx
onClick={() => {
  selectCompany(rel.id);
  setActiveView('xray');  // <-- 문제
}}
```
**문제점**: Deep Dive에서 관련기업 클릭 시 X-Ray 뷰로 강제 이동. 사용자가 Deep Dive 흐름에서 관련기업의 카테고리/엔티티를 탐색하고 싶을 수 있음

**수정 계획**:
```
Line 322-325 수정:
onClick={() => {
  selectCompany(rel.id);
  // setActiveView('xray');  -- 제거
  // Deep Dive 내에서 관련기업의 카테고리 그리드를 보여주도록 유지
  // 필요시 "X-Ray에서 보기" 별도 버튼 추가
}}
```

추가로, 관련기업 카드에 두 가지 액션 버튼 추가:
```
<div className="flex gap-2 mt-2">
  <button onClick={() => selectCompany(rel.id)} className="...">
    카테고리 보기
  </button>
  <button onClick={() => { selectCompany(rel.id); setActiveView('xray'); }} className="...">
    X-Ray 보기
  </button>
</div>
```

### [중요-1] DealListLevel 로딩 스켈레톤

**위치**: Line 118~123
**현재 동작**: `"딜 목록 로딩 중..."` 텍스트만
**수정 계획**:
```
if (dealsLoading) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <SkeletonDealList count={3} />
    </div>
  );
}
```

### [중요-2] CompanyDetailLevel 로딩 스켈레톤

**위치**: Line 186~192
**현재 동작**: `"로딩 중..."` 텍스트만
**수정 계획**:
```
if (dealDetailLoading) {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-6">
        <SkeletonGauge size={120} />
        <div className="flex-1 space-y-2">
          <SkeletonLine width="40%" />
          <SkeletonLine width="60%" />
        </div>
      </div>
      <SkeletonCategoryGrid columns={5} rows={2} />
    </div>
  );
}
```

### [중요-3] CategoryDetailLevel / EntityDetailLevel 로딩 스켈레톤

**위치**: Line 398~403 (CategoryDetailLevel), Line 553~558 (EntityDetailLevel)
**현재 동작**: 각각 `"엔티티 로딩 중..."`, `"이벤트 로딩 중..."` 텍스트
**수정 계획**: `SkeletonCard` 3~4개 그리드 또는 `SkeletonTimeline` 사용

### [개선-1] Breadcrumb에 엔티티 이름 표시 개선

**위치**: Line 765~770
**현재 동작**: `selectedEntityId` (UUID 형식)가 breadcrumb에 그대로 표시
**수정 계획**: Context나 API 응답에서 entity name을 가져와 표시. 현재는 entity 선택 시 name을 state에 저장하지 않으므로, `RiskV2Context`에 `selectedEntityName` 추가 또는 `selectEntity` 호출 시 이름도 함께 전달

---

## 5. WarRoom.tsx (중요 2건 + 개선 2건)

**파일**: `D:\new_wave\components\risk-v2\screens\WarRoom.tsx` (883줄)

### [중요-1] 시나리오 로딩 스켈레톤

**위치**: Line 633~634
**현재 동작**: `"시나리오 로딩 중..."` 텍스트
**수정 계획**:
```
{scenariosLoading ? (
  <SkeletonScenarioCard count={3} />
) : (
  scenarios.map(...)
)}
```

### [중요-2] 시뮬레이션 에러 처리 UI 부재

**위치**: Line 590~591, Line 612~613
**현재 동작**: `console.error`만 호출. 사용자에게 에러 알림 없음
**수정 계획**:

```
// 상태 추가
const [simulationError, setSimulationError] = useState<string | null>(null);

// catch 블록에서:
} catch (err) {
  console.error('[WarRoom] Simulation error:', err);
  setSimulationError('시뮬레이션 실행 중 오류가 발생했습니다. 다시 시도해주세요.');
}

// JSX에서 결과 영역 직전:
{simulationError && (
  <ErrorState
    title="시뮬레이션 오류"
    message={simulationError}
    onRetry={handleRunSimulation}
    variant="card"
  />
)}
```

### [개선-1] ImpactChart 바 차트 색상 문제

**위치**: Line 285~299
**현재 동작**: `<Bar>` 안에 `<rect>` 엘리먼트를 직접 렌더링하는데, Recharts의 Bar 내부에서 rect를 children으로 넣는 것은 올바른 패턴이 아님. `<Cell>` 컴포넌트를 사용해야 함

**수정 계획**:
```
Line 285-299:
<Bar dataKey="delta" radius={[6, 6, 0, 0]}>
  {chartData.map((entry) => (
    <Cell
      key={entry.code}
      fill={entry.delta >= 0 ? '#ef4444' : '#10b981'}
    />
  ))}
</Bar>
```
(`Cell`은 이미 recharts에서 import되어 있지 않으므로 Line 15의 import에 `Cell` 추가 필요 -- 확인: 현재 import에 Cell 없음)

### [개선-2] 커스텀 시나리오 빌더 유효성 피드백

**위치**: Line 519~529
**문제점**: 영향도 슬라이더를 하나도 조작하지 않으면 버튼이 비활성화되지만, 왜 비활성인지 안내 없음
**수정 계획**: 버튼 아래에 `hasImpacts`가 false일 때 안내 텍스트 추가
```
{!hasImpacts && (
  <p className="text-xs text-slate-500 text-center mt-2">
    최소 1개 카테고리의 영향도를 설정해주세요
  </p>
)}
```

---

## 6. AICopilotPanel.tsx (중요 1건 + 개선 2건)

**파일**: `D:\new_wave\components\risk-v2\screens\AICopilotPanel.tsx` (647줄)

### [중요-1] API 에러 시 사용자 피드백 부족

**위치**: Line 473~483
**현재 동작**: catch 블록에서 `setCypherResult`에 에러 객체를 넣어 표시하긴 하지만, `success: false`인 결과를 일반 결과와 동일한 `CypherResult` 컴포넌트로 렌더링
**문제점**: 사용자가 에러인지 정상 결과인지 시각적으로 구분 어려움

**수정 계획**:
```
CypherResult 컴포넌트 (Line 279) 내부에서 result.success === false일 때:
- 빨간 테두리 + 경고 아이콘 표시
- "API 서버 연결을 확인하세요" 안내와 함께 재시도 버튼 추가

Line 279 CypherResult 수정:
function CypherResult({ result, onRetry }: { result: Text2CypherResultV2; onRetry?: () => void }) {
  if (!result.success) {
    return (
      <ErrorState
        title="쿼리 실행 실패"
        message={result.answer}
        onRetry={onRetry}
        variant="inline"
      />
    );
  }
  // ... 기존 렌더링
}
```

### [개선-1] 인사이트 로딩 상태와 에러 구분

**위치**: Line 366~391
**문제점**: `fetchAIInsight` 실패 시 `dynamicInsight`가 null로 설정되어 Mock 인사이트로 폴백됨. 사용자는 실시간 AI 데이터인지 Mock인지 구분 불가

**수정 계획**:
- API 실패 시 `insightSource: 'mock' | 'api'` 상태 추가
- InsightSection 하단의 "AI Generated Insight" 라벨에 소스 표시:
  - API: "Live AI Insight | confidence: 92%"
  - Mock: "Cached Insight (API 오프라인) | confidence: 87%"

### [개선-2] 예제 쿼리 하드코딩

**위치**: Line 145~149
**현재 동작**: 3개 고정 예제 (`EXAMPLE_QUERIES` 배열)
**수정 계획**: 현재 `activeView`와 `selectedCompany`에 따라 동적으로 변경

```
const dynamicExamples = useMemo(() => {
  const companyName = currentCompany?.name ?? 'SK하이닉스';
  switch (activeView) {
    case 'command':
      return [`${companyName} 리스크 요약`, '포트폴리오 전체 요약', '가장 위험한 딜은?'];
    case 'xray':
      return ['공급망 전이 경로', `${companyName} 관련기업`, '리스크 전이 Top 3'];
    case 'deepdive':
      return [`${companyName} 법률 위험 상세`, '카테고리별 점수 비교', '최근 이벤트 분석'];
    case 'warroom':
      return ['시뮬레이션 결과 요약', '최악의 시나리오는?', '대응 전략 추천'];
    default:
      return EXAMPLE_QUERIES;
  }
}, [activeView, currentCompany?.name]);
```

---

## 7. RiskV2Context.tsx (중요 2건 + 개선 1건)

**파일**: `D:\new_wave\components\risk-v2\context\RiskV2Context.tsx` (351줄)

### [중요-1] 에러 상태 관리 부재

**위치**: Line 30~43 (initialState), Line 236~254 (loadDeals), Line 258~272 (loadDealDetail)
**현재 동작**: API 실패 시 `console.error`만 출력. 에러 상태를 state에 저장하지 않음
**문제점**: 하위 스크린에서 에러 상태를 확인할 방법이 없어 ErrorState 컴포넌트를 사용할 수 없음

**수정 계획**:

1. `RiskV2State`에 에러 필드 추가:
```ts
// types-v2.ts의 RiskV2State에 추가
dealsError: string | null;
dealDetailError: string | null;
```

2. `initialState`에 초기값 추가:
```
Line 30-43:
dealsError: null,
dealDetailError: null,
```

3. 리듀서에 에러 액션 추가:
```
case 'SET_DEALS_ERROR':
  return { ...state, dealsError: action.payload, dealsLoading: false };
case 'SET_DEAL_DETAIL_ERROR':
  return { ...state, dealDetailError: action.payload, dealDetailLoading: false };
```

4. `loadDeals`/`loadDealDetail` catch 블록에서 에러 dispatch:
```
Line 248-249:
dispatch({ type: 'SET_DEALS_ERROR', payload: response.error ?? '딜 목록을 불러올 수 없습니다' });

Line 265-266:
dispatch({ type: 'SET_DEAL_DETAIL_ERROR', payload: response.error ?? '딜 상세 정보를 불러올 수 없습니다' });
```

### [중요-2] loadDeals의 stale closure

**위치**: Line 236~255
**문제점**: `loadDeals`가 `state.selectedDealId`를 dependency로 갖지만, `useCallback` 내에서 `state.selectedDealId`를 참조함. `useEffect(loadDeals, [])`에서 호출되므로 초기 렌더 시의 값만 캡처됨

**수정 계획**:
```
Line 244를 별도 useEffect로 분리:
// loadDeals에서 자동 선택 로직 제거
// 별도 useEffect로:
useEffect(() => {
  if (!state.selectedDealId && state.deals.length > 0) {
    dispatch({ type: 'SET_SELECTED_DEAL', payload: state.deals[0].id });
  }
}, [state.deals, state.selectedDealId]);
```

### [개선-1] Copilot 컨텍스트 자동 업데이트

**위치**: Line 227~229 (`setCopilotContext`)
**현재 동작**: `setCopilotContext`가 존재하지만 어떤 스크린에서도 호출하지 않음
**수정 계획**: `selectedDealId`, `selectedCompanyId`, `selectedCategoryCode`, `activeView` 변경 시 자동으로 copilotContext 업데이트하는 useEffect 추가

```
useEffect(() => {
  dispatch({
    type: 'SET_COPILOT_CONTEXT',
    payload: {
      view: state.activeView,
      dealId: state.selectedDealId,
      companyId: state.selectedCompanyId,
      categoryCode: state.selectedCategoryCode,
      entityId: state.selectedEntityId,
    },
  });
}, [state.activeView, state.selectedDealId, state.selectedCompanyId, state.selectedCategoryCode, state.selectedEntityId]);
```

---

## 8. Header.tsx (중요 1건 + 개선 2건)

**파일**: `D:\new_wave\components\Header.tsx` (96줄)

### [중요-1] risk-v2 뷰 활성 상태 구분 미흡

**위치**: Line 58~63
**현재 동작**: `risk-v2` 탭의 label이 "공급망 V2"이고 아이콘이 회로 모양 SVG
**문제점**: `risk`(공급망 리스크)과 `risk-v2`(공급망 V2)가 시각적으로 너무 유사. 대회 심사위원이 V2가 핵심 화면임을 인지하기 어려움

**수정 계획**:
```
Line 61-62:
label: "Risk Intelligence V2"   // 또는 "Risk V2 (AI)"
// 아이콘을 더 차별화된 것으로 교체 (뇌+회로 또는 AI 칩 아이콘)
```

추가로, `risk-v2`가 활성일 때 탭 배경에 보라색 그래디언트 효과 적용:
```
NavItem 컴포넌트(Line 85-93):
className에 risk-v2 활성 시 특별 스타일 추가
active && isV2 ? 'bg-gradient-to-r from-purple-600/20 to-indigo-600/20 border-purple-400' : ...
```

### [개선-1] 알림 버튼 기능 미구현

**위치**: Line 68~70
**현재 동작**: 알림 벨 아이콘 버튼이 있지만 클릭 핸들러 없음 (빈 `<button>`)
**수정 계획**: 대회용으로 알림 카운트 뱃지 추가 + 클릭 시 간단한 드롭다운 (최근 이벤트 3개 표시)

```
<button className="relative ...">
  <svg .../>
  {/* 알림 카운트 뱃지 */}
  <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[9px] text-white font-bold flex items-center justify-center">
    3
  </span>
</button>
```

### [개선-2] crisisAlert prop 미사용

**위치**: Line 7 (Props 인터페이스), Line 10 (구조분해 할당에서 미포함)
**현재 동작**: `crisisAlert?: boolean` prop이 정의되어 있으나 구조분해할당에서 무시됨
**수정 계획**: 사용하거나 제거. 사용한다면 헤더 상단에 빨간 위기 배너 표시

```
// crisisAlert 사용 시:
{crisisAlert && (
  <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 via-orange-500 to-red-500 animate-pulse" />
)}
```

---

## 9. 구현 우선순위 로드맵

### Phase 1: 긴급 (대회 임팩트 직결) -- 예상 2~3시간

| # | 파일 | 작업 | 예상 시간 |
|---|------|------|-----------|
| 1 | SupplyChainXRay.tsx | handleNodeClick 뷰 자동전환 제거 (Line 145) | 10분 |
| 2 | SupplyChainXRay.tsx | nodeLabel HTML 커스텀 툴팁 (Line 165-167) | 30분 |
| 3 | RiskDeepDive.tsx | 관련기업 클릭 setActiveView('xray') 제거 + 듀얼 버튼 (Line 322-325) | 30분 |
| 4 | CommandCenter.tsx | 비선택 딜 점수 표시 (types-v2 + api-v2 + 화면) | 40분 |

### Phase 2: 중요 (품질 향상) -- 예상 3~4시간

| # | 파일 | 작업 | 예상 시간 |
|---|------|------|-----------|
| 5 | shared/SkeletonLoader.tsx | 6종 프리셋 스켈레톤 추가 | 45분 |
| 6 | shared/ErrorState.tsx | 신규 컴포넌트 생성 | 30분 |
| 7 | shared/EmptyState.tsx | 신규 컴포넌트 생성 | 20분 |
| 8 | RiskV2Context.tsx | 에러 상태 관리 추가 (state + reducer + loadDeals/loadDealDetail) | 30분 |
| 9 | 전체 스크린 (4개) | 텍스트 로딩 -> 스켈레톤 교체 (총 8개소) | 40분 |
| 10 | 전체 스크린 (4개) | API 에러 시 ErrorState 표시 추가 (총 6개소) | 30분 |
| 11 | SupplyChainXRay.tsx | graphLoading 스켈레톤 + graphError 처리 | 20분 |
| 12 | AICopilotPanel.tsx | CypherResult 에러/성공 분기 UI | 20분 |
| 13 | Header.tsx | risk-v2 탭 시각 차별화 | 15분 |

### Phase 3: 개선 (완성도) -- 예상 2~3시간

| # | 파일 | 작업 | 예상 시간 |
|---|------|------|-----------|
| 14 | RiskV2Context.tsx | loadDeals stale closure 수정 | 15분 |
| 15 | RiskV2Context.tsx | copilotContext 자동 업데이트 | 15분 |
| 16 | SupplyChainXRay.tsx | NodeDetailPanel 분리 | 30분 |
| 17 | SupplyChainXRay.tsx | 관련기업 선택 하이라이트 | 10분 |
| 18 | WarRoom.tsx | ImpactChart Cell 컴포넌트 수정 | 10분 |
| 19 | WarRoom.tsx | 커스텀 시나리오 유효성 안내 | 5분 |
| 20 | AICopilotPanel.tsx | 동적 예제 쿼리 | 20분 |
| 21 | AICopilotPanel.tsx | 인사이트 소스 표시 (mock/api) | 10분 |
| 22 | Header.tsx | 알림 뱃지 + crisisAlert 활용 | 20분 |
| 23 | RiskDeepDive.tsx | Breadcrumb 엔티티 이름 표시 | 15분 |

---

## 10. 파일 변경 영향 매트릭스

```
types-v2.ts
  └── DealV2에 score/riskLevel 추가 → CommandCenter, api-v2 영향
  └── RiskV2State에 dealsError/dealDetailError 추가 → Context, 전체 스크린 영향

api-v2.ts
  └── fetchDealsV2 딜 점수 매핑 → CommandCenter, RiskDeepDive 영향

RiskV2Context.tsx
  └── 에러 상태 리듀서 추가 → 전체 스크린에서 state.dealsError 접근 가능
  └── loadDeals 자동선택 로직 분리 → 동작 변경 없음 (리팩터링)

shared/SkeletonLoader.tsx
  └── 6종 프리셋 추가 → 전체 스크린에서 import하여 사용

shared/ErrorState.tsx (신규)
  └── 전체 스크린 + AICopilotPanel에서 import

shared/EmptyState.tsx (신규)
  └── CommandCenter, RiskDeepDive에서 import
```

---

## 11. 테스트 체크리스트

- [ ] SupplyChainXRay: riskCategory 노드 클릭 시 뷰 전환 안 되는지 확인
- [ ] SupplyChainXRay: 노드 마우스오버 시 커스텀 HTML 툴팁 표시되는지 확인
- [ ] SupplyChainXRay: 그래프 로딩 중 스켈레톤 표시되는지 확인
- [ ] CommandCenter: 비선택 딜에 점수 표시되는지 확인 (API에 점수가 있는 경우)
- [ ] CommandCenter: 딜 목록 로딩 시 스켈레톤 표시되는지 확인
- [ ] RiskDeepDive: 관련기업 클릭 시 Deep Dive 내에서 드릴다운되는지 확인
- [ ] RiskDeepDive: 각 레벨 로딩 시 스켈레톤 표시되는지 확인
- [ ] WarRoom: 시나리오 로딩 시 스켈레톤 표시되는지 확인
- [ ] WarRoom: 시뮬레이션 에러 시 ErrorState 표시되는지 확인
- [ ] AICopilotPanel: Text2Cypher 실패 시 에러 UI 구분되는지 확인
- [ ] Header: risk-v2 탭이 시각적으로 차별화되는지 확인
- [ ] 전체: API 서버 꺼진 상태에서 모든 화면이 에러/Mock 상태를 적절히 표시하는지 확인
