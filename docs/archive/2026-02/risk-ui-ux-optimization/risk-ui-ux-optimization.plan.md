# Risk UI/UX Optimization - 공급망 리스크 화면 UI/UX 개선 계획서

> **기능명**: risk-ui-ux-optimization
> **작성일**: 2026-02-06
> **상태**: Plan

---

## 1. 배경 및 목적

### 1.1 현재 문제점

| # | 문제 | 상세 |
|:-:|------|------|
| 1 | **이모지 중복/불일치** | 같은 상태에 다른 이모지 사용 (🟢🟡🔴 vs ✅⚠️❌) |
| 2 | **Supply Chain Graph 인터렉션 부족** | 확대/축소, 패닝, 노드 드래그 불가 |
| 3 | **스타일 일관성 부재** | 컴포넌트마다 다른 색상, 간격, 폰트 스타일 |
| 4 | **점수 임계값 불일치** | 컴포넌트별로 다른 Status 분류 기준 |
| 5 | **접근성 미흡** | 키보드 네비게이션, ARIA 레이블 부재 |
| 6 | **탭 내 중복 제목/이모지** | 탭 이름과 동일한 제목이 내부에 또 표시됨 |

### 1.2 목표

```
[AS-IS]                              [TO-BE]

🟢 PASS / ✅ 정상 / 🟩 안전        →  🟢 PASS (통일)
Supply Chain: 정적 캔버스            →  확대/축소/패닝 + 노드 드래그
각 컴포넌트 개별 스타일              →  공유 스타일 상수 (RISK_COLORS)
탭마다 반복되는 "📊 Overview"        →  탭 전환으로 충분, 내부 제목 제거
```

---

## 2. 대상 컴포넌트 (13개)

| # | 컴포넌트 | 파일 | 주요 개선 |
|:-:|----------|------|----------|
| 1 | RiskPage | `RiskPage.tsx` | 탭 구조 정리, 공유 상수 import |
| 2 | RiskOverview | `RiskOverview.tsx` | 중복 이모지 제거, 카드 스타일 통일 |
| 3 | **RiskGraph** | `RiskGraph.tsx` | 인터렉티브 그래프 (핵심) |
| 4 | RiskSignals | `RiskSignals.tsx` | 이모지 통일, 테이블 스타일 |
| 5 | RiskTimeline | `RiskTimeline.tsx` | 타임라인 스타일 일관성 |
| 6 | RiskBreakdown | `RiskBreakdown.tsx` | 색상 상수 적용 |
| 7 | RiskPropagation | `RiskPropagation.tsx` | 전이 시각화 개선 |
| 8 | RiskActionGuide | `RiskActionGuide.tsx` | 액션 아이템 스타일 |
| 9 | RiskSimulation | `RiskSimulation.tsx` | 시뮬레이션 UI 개선 |
| 10 | RiskPrediction | `RiskPrediction.tsx` | 예측 차트 스타일 |
| 11 | RiskScenarioBuilder | `RiskScenarioBuilder.tsx` | 시나리오 빌더 UX |
| 12 | RiskStatusView | `RiskStatusView.tsx` | Status 뷰 통합 |
| 13 | RiskScoreBreakdownV3 | `RiskScoreBreakdownV3.tsx` | 점수 분해 UI |

---

## 3. 개선 항목

### Phase 1: 공유 스타일 시스템 구축

| # | 항목 | 파일 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 1 | 이모지 상수 정의 | `types.ts` | EMOJI_MAP 중앙 관리 | P0 |
| 2 | 색상 상수 정의 | `types.ts` | RISK_SCORE_COLORS 통일 | P0 |
| 3 | Status 임계값 통일 | `types.ts` | PASS/WARNING/FAIL 기준 통일 | P0 |
| 4 | 공유 스타일 함수 | `utils.ts` | getStatusColor, getStatusEmoji | P0 |

### Phase 2: 컴포넌트 이모지/스타일 통일

| # | 항목 | 대상 파일 | 설명 | 우선순위 |
|:-:|------|----------|------|:--------:|
| 5 | RiskOverview 이모지 통일 | `RiskOverview.tsx` | 개별 이모지 → EMOJI_MAP | P0 |
| 6 | RiskSignals 이모지 통일 | `RiskSignals.tsx` | 신호 아이콘 통일 | P0 |
| 7 | RiskStatusView 이모지 통일 | `RiskStatusView.tsx` | Status 표시 통일 | P0 |
| 8 | RiskScoreBreakdownV3 색상 통일 | `RiskScoreBreakdownV3.tsx` | 색상 상수 적용 | P0 |
| 9 | 중복 제목/이모지 제거 | 전체 | 탭 내부 중복 헤더 정리 | P1 |

### Phase 3: Supply Chain Graph 인터렉티브 개선 (핵심)

| # | 항목 | 파일 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 10 | 확대/축소 (Zoom) | `RiskGraph.tsx` | 마우스 휠 줌 | P0 |
| 11 | 패닝 (Pan) | `RiskGraph.tsx` | 드래그로 화면 이동 | P0 |
| 12 | 노드 드래그 | `RiskGraph.tsx` | 노드 위치 조정 | P1 |
| 13 | 미니맵 | `RiskGraph.tsx` | 전체 뷰 미니맵 | P2 |
| 14 | 줌 컨트롤 버튼 | `RiskGraph.tsx` | +/- 버튼, 리셋 버튼 | P0 |
| 15 | 노드 클릭 상세 | `RiskGraph.tsx` | 클릭 시 상세 패널 | P1 |
| 16 | 엣지 클릭 | `RiskGraph.tsx` | 공급관계 상세 표시 | P2 |
| 17 | 키보드 네비게이션 | `RiskGraph.tsx` | 화살표 키 이동, +/- 줌 | P1 |

### Phase 4: 접근성 및 반응형 개선

| # | 항목 | 대상 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 18 | ARIA 레이블 추가 | 전체 | 스크린리더 지원 | P1 |
| 19 | 포커스 표시 개선 | 전체 | 키보드 네비게이션 지원 | P1 |
| 20 | 반응형 레이아웃 | 전체 | 모바일/태블릿 대응 | P2 |

---

## 4. 상세 설계

### 4.1 공유 이모지 상수 (EMOJI_MAP)

```typescript
// types.ts
export const EMOJI_MAP = {
  // Status 이모지 (유일한 표준)
  status: {
    PASS: '🟢',
    WARNING: '🟡',
    FAIL: '🔴',
  },

  // 트렌드 이모지
  trend: {
    UP: '📈',
    DOWN: '📉',
    STABLE: '➡️',
  },

  // 카테고리 이모지
  category: {
    MARKET: '📊',
    CREDIT: '💳',
    OPERATIONAL: '⚙️',
    LEGAL: '⚖️',
    SUPPLY: '🔗',
    ESG: '🌱',
  },

  // 데이터 소스 이모지
  source: {
    DART: '📋',
    NEWS: '📰',
    KIND: '📢',
    MANUAL: '✏️',
  },
} as const;
```

### 4.2 색상 상수 (RISK_SCORE_COLORS)

```typescript
// types.ts
export const RISK_SCORE_COLORS = {
  // Status 색상
  PASS: '#22C55E',      // green-500
  WARNING: '#F97316',   // orange-500
  FAIL: '#EF4444',      // red-500

  // 배경 색상 (투명도 적용)
  PASS_BG: 'rgba(34, 197, 94, 0.1)',
  WARNING_BG: 'rgba(249, 115, 22, 0.1)',
  FAIL_BG: 'rgba(239, 68, 68, 0.1)',

  // 그래프 노드 색상
  node: {
    PASS: '#86EFAC',    // green-300
    WARNING: '#FDBA74', // orange-300
    FAIL: '#FCA5A5',    // red-300
    selected: '#3B82F6', // blue-500
  },

  // 그래프 엣지 색상
  edge: {
    default: '#9CA3AF',   // gray-400
    critical: '#EF4444',  // red-500
    selected: '#3B82F6',  // blue-500
  },
} as const;

// Status 임계값 (통일)
export const STATUS_THRESHOLDS = {
  PASS: { min: 0, max: 49 },
  WARNING: { min: 50, max: 74 },
  FAIL: { min: 75, max: 100 },
} as const;
```

### 4.3 유틸리티 함수

```typescript
// utils.ts
import { EMOJI_MAP, RISK_SCORE_COLORS, STATUS_THRESHOLDS } from './types';

export function getStatusFromScore(score: number): 'PASS' | 'WARNING' | 'FAIL' {
  if (score < STATUS_THRESHOLDS.WARNING.min) return 'PASS';
  if (score < STATUS_THRESHOLDS.FAIL.min) return 'WARNING';
  return 'FAIL';
}

export function getStatusColor(status: 'PASS' | 'WARNING' | 'FAIL'): string {
  return RISK_SCORE_COLORS[status];
}

export function getStatusEmoji(status: 'PASS' | 'WARNING' | 'FAIL'): string {
  return EMOJI_MAP.status[status];
}

export function getStatusBgColor(status: 'PASS' | 'WARNING' | 'FAIL'): string {
  return RISK_SCORE_COLORS[`${status}_BG`];
}
```

### 4.4 RiskGraph 인터렉티브 구현

```typescript
// RiskGraph.tsx - 핵심 변경사항

interface GraphState {
  scale: number;           // 확대/축소 배율 (0.5 ~ 3.0)
  offsetX: number;         // 패닝 X 오프셋
  offsetY: number;         // 패닝 Y 오프셋
  isDragging: boolean;     // 패닝 드래그 중
  dragStartX: number;
  dragStartY: number;
  selectedNode: string | null;
  hoveredNode: string | null;
}

// 줌 설정
const ZOOM_CONFIG = {
  min: 0.5,
  max: 3.0,
  step: 0.1,
  wheelSensitivity: 0.001,
};

// Canvas 변환 적용
function applyTransform(ctx: CanvasRenderingContext2D, state: GraphState) {
  ctx.setTransform(
    state.scale, 0, 0, state.scale,
    state.offsetX, state.offsetY
  );
}

// 마우스 휠 줌
function handleWheel(e: WheelEvent, state: GraphState): GraphState {
  e.preventDefault();
  const delta = -e.deltaY * ZOOM_CONFIG.wheelSensitivity;
  const newScale = Math.min(
    ZOOM_CONFIG.max,
    Math.max(ZOOM_CONFIG.min, state.scale + delta)
  );

  // 마우스 위치 중심으로 확대
  const mouseX = e.offsetX;
  const mouseY = e.offsetY;
  const scaleRatio = newScale / state.scale;

  return {
    ...state,
    scale: newScale,
    offsetX: mouseX - (mouseX - state.offsetX) * scaleRatio,
    offsetY: mouseY - (mouseY - state.offsetY) * scaleRatio,
  };
}

// 패닝 (드래그)
function handleMouseDown(e: MouseEvent, state: GraphState): GraphState {
  if (e.button === 0) { // 좌클릭
    return {
      ...state,
      isDragging: true,
      dragStartX: e.clientX - state.offsetX,
      dragStartY: e.clientY - state.offsetY,
    };
  }
  return state;
}

function handleMouseMove(e: MouseEvent, state: GraphState): GraphState {
  if (state.isDragging) {
    return {
      ...state,
      offsetX: e.clientX - state.dragStartX,
      offsetY: e.clientY - state.dragStartY,
    };
  }
  return state;
}

function handleMouseUp(state: GraphState): GraphState {
  return { ...state, isDragging: false };
}
```

### 4.5 줌 컨트롤 UI

```typescript
// ZoomControls.tsx
interface ZoomControlsProps {
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}

export function ZoomControls({ scale, onZoomIn, onZoomOut, onReset }: ZoomControlsProps) {
  return (
    <div className="absolute bottom-4 right-4 flex flex-col gap-2 bg-white rounded-lg shadow-lg p-2">
      <button
        onClick={onZoomIn}
        className="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded"
        aria-label="확대"
      >
        +
      </button>
      <div className="text-center text-sm text-gray-600">
        {Math.round(scale * 100)}%
      </div>
      <button
        onClick={onZoomOut}
        className="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded"
        aria-label="축소"
      >
        -
      </button>
      <button
        onClick={onReset}
        className="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded text-xs"
        aria-label="초기화"
      >
        Reset
      </button>
    </div>
  );
}
```

---

## 5. 구현 항목 요약

### 총 구현 항목: 20개

| 우선순위 | 개수 | 설명 |
|:--------:|:----:|------|
| **P0 (필수)** | 10개 | 공유 스타일, 이모지 통일, 기본 줌/팬 |
| **P1 (중요)** | 7개 | 노드 드래그, 키보드, 접근성 |
| **P2 (선택)** | 3개 | 미니맵, 엣지 클릭, 반응형 |

### Phase별 진행

```
Phase 1: 공유 스타일 시스템 (4개) ──┐
                                    │
Phase 2: 이모지/스타일 통일 (5개) ──┼── 기반 작업
                                    │
Phase 3: 인터렉티브 그래프 (8개) ───┴── 핵심 기능

Phase 4: 접근성 개선 (3개) ─────────── 품질 향상
```

---

## 6. 성공 기준

### 6.1 필수 (Must Have)

- [ ] EMOJI_MAP 상수 정의 및 전체 컴포넌트 적용
- [ ] RISK_SCORE_COLORS 상수 정의 및 전체 컴포넌트 적용
- [ ] STATUS_THRESHOLDS 통일 (PASS < 50, WARNING 50-74, FAIL 75+)
- [ ] RiskGraph 마우스 휠 확대/축소 구현
- [ ] RiskGraph 드래그 패닝 구현
- [ ] 줌 컨트롤 버튼 (+/-/Reset) 구현
- [ ] 중복 이모지/제목 제거 (탭 내부)

### 6.2 중요 (Should Have)

- [ ] 노드 드래그 기능
- [ ] 노드 클릭 시 상세 패널
- [ ] 키보드 네비게이션 (화살표, +/-)
- [ ] ARIA 레이블 추가

### 6.3 선택 (Nice to Have)

- [ ] 미니맵 표시
- [ ] 엣지 클릭 상세
- [ ] 반응형 레이아웃

---

## 7. 예상 결과물

### 7.1 개선된 Supply Chain Graph

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Supply Chain Graph                                              [+][-][⟲] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                      ┌─────────────┐                                         │
│                      │ SK하이닉스  │                                         │
│            ┌─────────│   🔴 72    │─────────┐                               │
│            │         └─────────────┘         │                               │
│            │ T1            │            T1   │                               │
│            ▼               │                 ▼                               │
│    ┌─────────────┐        │        ┌─────────────┐                          │
│    │ 한미반도체  │        │        │    ASML    │                          │
│    │   🟡 65    │        │        │   🟢 40    │                          │
│    └─────────────┘        │        └─────────────┘                          │
│                           │ T2                                               │
│                           ▼                                                  │
│                   ┌─────────────┐                                            │
│                   │SK머티리얼즈 │                                            │
│                   │   🟢 35    │                                            │
│                   └─────────────┘                                            │
│                                                                              │
│  ┌────────────────────────────────┐                          Zoom: 100%     │
│  │ 미니맵                         │                                         │
│  │ [    *     ]                  │                                         │
│  └────────────────────────────────┘                                         │
└──────────────────────────────────────────────────────────────────────────────┘

인터렉션:
- 마우스 휠: 확대/축소
- 드래그: 화면 이동
- 노드 클릭: 상세 패널
- 노드 드래그: 위치 조정
- 키보드 +/-: 확대/축소
- 화살표 키: 화면 이동
```

### 7.2 통일된 이모지 시스템

```
Before:                           After:
─────────────────────────────────────────────────────
🟢 PASS  / ✅ 정상  / 🟩 안전    →  🟢 PASS
🟡 WARNING / ⚠️ 주의 / 🟨 경고   →  🟡 WARNING
🔴 FAIL / ❌ 위험 / 🟥 고위험    →  🔴 FAIL

각 컴포넌트 개별 정의            →  EMOJI_MAP 중앙 import
```

---

## 8. 기술 참조

### 8.1 현재 RiskGraph 구조 (Canvas 기반)

```typescript
// 현재: 정적 Canvas 렌더링
// 위치: components/risk/RiskGraph.tsx

// 문제점:
// 1. 고정 scale = 1
// 2. offset 없음 (패닝 불가)
// 3. 이벤트: hover, click만 지원
// 4. 노드 위치 고정 (드래그 불가)
```

### 8.2 고려 대안: D3.js + SVG

Canvas 대신 D3.js + SVG로 전환 시:
- d3-zoom: 확대/축소/패닝 내장
- d3-drag: 노드 드래그 내장
- SVG: DOM 요소로 접근성 우수

```
권장: Canvas 유지 + 직접 구현
이유:
- 기존 코드 재사용
- 대규모 노드에서 Canvas 성능 우수
- D3 의존성 추가 불필요
```

---

## 9. 위험 요소 및 대응

| 위험 | 영향 | 확률 | 대응 방안 |
|------|:----:|:----:|----------|
| Canvas 줌 성능 | MEDIUM | LOW | 뷰포트 컬링 적용 |
| 터치 디바이스 패닝 | LOW | MEDIUM | touch 이벤트 핸들러 추가 |
| 노드 겹침 | MEDIUM | MEDIUM | Force-directed 레이아웃 고려 |
| 브라우저 호환성 | LOW | LOW | 표준 Canvas API만 사용 |

---

**작성일**: 2026-02-06
**다음 단계**: `/pdca design risk-ui-ux-optimization`

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|:----:|------|----------|
| v1.0 | 2026-02-06 | 초안 작성 |
