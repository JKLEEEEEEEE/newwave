# Risk UI/UX Optimization - 상세 설계서

> **기능명**: risk-ui-ux-optimization
> **작성일**: 2026-02-06
> **상태**: Design
> **Plan 참조**: [risk-ui-ux-optimization.plan.md](../../01-plan/features/risk-ui-ux-optimization.plan.md)

---

## 1. 설계 개요

### 1.1 목적

공급망 리스크 화면의 UI/UX를 통일하고 Supply Chain Graph를 인터렉티브하게 개선합니다.

### 1.2 주요 변경사항

| 영역 | Before | After |
|------|--------|-------|
| 이모지 | 컴포넌트별 개별 정의 | `EMOJI_MAP` 중앙 집중화 |
| 색상 | 하드코딩된 색상값 | `RISK_SCORE_COLORS` 상수 |
| 임계값 | 40/70 또는 50/75 혼재 | `STATUS_THRESHOLDS` (0-49/50-74/75+) |
| 그래프 | 정적 Canvas | 줌/팬/드래그 지원 |

---

## 2. 파일 구조

### 2.1 신규 생성 파일

```
components/risk/
├── constants.ts          # 공유 상수 (EMOJI_MAP, RISK_SCORE_COLORS 등)
├── utils.ts              # 유틸리티 함수 (getStatusFromScore 등)
└── ZoomControls.tsx      # 그래프 줌 컨트롤 컴포넌트
```

### 2.2 수정 대상 파일

```
components/risk/
├── types.ts              # 상수 export 추가
├── RiskGraph.tsx         # 인터렉티브 기능 추가 (핵심)
├── RiskOverview.tsx      # 이모지/색상 상수 적용
├── RiskStatusView.tsx    # 이모지 통일
├── RiskScoreBreakdownV3.tsx  # 색상 상수 적용
├── RiskSignals.tsx       # 이모지 통일
├── RiskTimeline.tsx      # 스타일 통일
├── RiskBreakdown.tsx     # 색상 상수 적용
├── RiskPropagation.tsx   # 스타일 통일
├── RiskSimulation.tsx    # 스타일 통일
├── RiskPrediction.tsx    # 스타일 통일
├── RiskScenarioBuilder.tsx   # 스타일 통일
└── RiskActionGuide.tsx   # 스타일 통일
```

---

## 3. 공유 상수 설계

### 3.1 constants.ts

```typescript
/**
 * Risk UI 공유 상수
 * - 모든 컴포넌트에서 import하여 사용
 * - 이모지, 색상, 임계값 중앙 관리
 */

// ============================================
// Status 타입
// ============================================
export type RiskStatusType = 'PASS' | 'WARNING' | 'FAIL';
export type TrendType = 'UP' | 'DOWN' | 'STABLE';
export type CategoryType = 'MARKET' | 'CREDIT' | 'OPERATIONAL' | 'LEGAL' | 'SUPPLY' | 'ESG';
export type SourceType = 'DART' | 'NEWS' | 'KIND' | 'MANUAL';

// ============================================
// 이모지 상수 (유일한 표준)
// ============================================
export const EMOJI_MAP = {
  // Status 이모지 - 다른 이모지 사용 금지
  status: {
    PASS: '🟢',
    WARNING: '🟡',
    FAIL: '🔴',
  } as const,

  // 트렌드 이모지
  trend: {
    UP: '📈',
    DOWN: '📉',
    STABLE: '➡️',
  } as const,

  // 카테고리 이모지
  category: {
    MARKET: '📊',
    CREDIT: '💳',
    OPERATIONAL: '⚙️',
    LEGAL: '⚖️',
    SUPPLY: '🔗',
    ESG: '🌱',
    GOVERNANCE: '👔',
    REPUTATION: '📢',
    MACRO: '🌍',
    FINANCIAL: '💰',
  } as const,

  // 데이터 소스 이모지
  source: {
    DART: '📋',
    NEWS: '📰',
    KIND: '📢',
    MANUAL: '✏️',
  } as const,

  // 노드 타입 이모지
  nodeType: {
    company: '🏢',
    supplier: '🏭',
    customer: '🛒',
    competitor: '⚔️',
    subsidiary: '🔗',
    person: '👤',
  } as const,
} as const;

// ============================================
// 색상 상수
// ============================================
export const RISK_SCORE_COLORS = {
  // Status 기본 색상
  PASS: '#22C55E',      // green-500
  WARNING: '#F97316',   // orange-500 (yellow 대신 orange 사용 - 가독성)
  FAIL: '#EF4444',      // red-500

  // Tailwind 클래스 매핑
  tailwind: {
    PASS: {
      text: 'text-green-400',
      bg: 'bg-green-900/30',
      border: 'border-green-700',
      progress: 'bg-green-500',
    },
    WARNING: {
      text: 'text-yellow-400',
      bg: 'bg-yellow-900/30',
      border: 'border-yellow-700',
      progress: 'bg-yellow-500',
    },
    FAIL: {
      text: 'text-red-400',
      bg: 'bg-red-900/30',
      border: 'border-red-700',
      progress: 'bg-red-500',
    },
  },

  // 그래프 노드 색상 (Canvas용)
  node: {
    PASS: '#86EFAC',    // green-300
    WARNING: '#FDE047', // yellow-300
    FAIL: '#FCA5A5',    // red-300
    selected: '#3B82F6', // blue-500
    hovered: '#FFFFFF',  // white (border)
  },

  // 그래프 엣지 색상
  edge: {
    default: '#64748B',   // slate-500
    low: '#22C55E',       // green-500 (riskTransfer < 0.4)
    medium: '#EAB308',    // yellow-500 (0.4 <= riskTransfer < 0.7)
    high: '#EF4444',      // red-500 (riskTransfer >= 0.7)
    selected: '#3B82F6',  // blue-500
  },
} as const;

// ============================================
// Status 임계값 (통일된 기준)
// ============================================
export const STATUS_THRESHOLDS = {
  PASS: { min: 0, max: 49 },
  WARNING: { min: 50, max: 74 },
  FAIL: { min: 75, max: 100 },
} as const;

// ============================================
// 그래프 줌 설정
// ============================================
export const ZOOM_CONFIG = {
  min: 0.3,              // 최소 30%
  max: 3.0,              // 최대 300%
  default: 1.0,          // 기본 100%
  step: 0.1,             // 버튼 클릭 시 10% 단위
  wheelSensitivity: 0.001, // 마우스 휠 감도
} as const;

// ============================================
// 그래프 노드 크기
// ============================================
export const NODE_SIZE = {
  center: 40,            // 중심 노드 반지름
  normal: 28,            // 일반 노드 반지름
  hoverIncrease: 4,      // 호버 시 증가량
} as const;
```

### 3.2 utils.ts

```typescript
/**
 * Risk UI 유틸리티 함수
 */

import {
  EMOJI_MAP,
  RISK_SCORE_COLORS,
  STATUS_THRESHOLDS,
  RiskStatusType,
  TrendType,
  CategoryType,
} from './constants';

// ============================================
// Status 판정 함수
// ============================================

/**
 * 점수로부터 Status 판정
 * @param score 리스크 점수 (0-100)
 * @returns 'PASS' | 'WARNING' | 'FAIL'
 */
export function getStatusFromScore(score: number): RiskStatusType {
  if (score < STATUS_THRESHOLDS.WARNING.min) return 'PASS';
  if (score < STATUS_THRESHOLDS.FAIL.min) return 'WARNING';
  return 'FAIL';
}

// ============================================
// 이모지 함수
// ============================================

/**
 * Status 이모지 반환
 */
export function getStatusEmoji(status: RiskStatusType): string {
  return EMOJI_MAP.status[status];
}

/**
 * 트렌드 이모지 반환
 */
export function getTrendEmoji(trend: TrendType): string {
  return EMOJI_MAP.trend[trend];
}

/**
 * 카테고리 이모지 반환
 */
export function getCategoryEmoji(category: string): string {
  const upperCategory = category.toUpperCase() as CategoryType;
  return EMOJI_MAP.category[upperCategory] || '📊';
}

// ============================================
// 색상 함수
// ============================================

/**
 * Status에 따른 색상 반환 (Canvas용)
 */
export function getStatusColor(status: RiskStatusType): string {
  return RISK_SCORE_COLORS[status];
}

/**
 * 점수에 따른 색상 반환 (Canvas용)
 */
export function getScoreColor(score: number): string {
  const status = getStatusFromScore(score);
  return RISK_SCORE_COLORS[status];
}

/**
 * Status에 따른 Tailwind 클래스 반환
 */
export function getStatusTailwind(status: RiskStatusType): {
  text: string;
  bg: string;
  border: string;
  progress: string;
} {
  return RISK_SCORE_COLORS.tailwind[status];
}

/**
 * 점수에 따른 Tailwind 텍스트 클래스 반환
 */
export function getScoreTextClass(score: number): string {
  const status = getStatusFromScore(score);
  return RISK_SCORE_COLORS.tailwind[status].text;
}

/**
 * 노드 색상 반환 (Canvas용)
 */
export function getNodeColor(score: number): string {
  const status = getStatusFromScore(score);
  return RISK_SCORE_COLORS.node[status];
}

/**
 * 엣지 색상 반환 (riskTransfer 기반)
 */
export function getEdgeColor(riskTransfer: number): string {
  if (riskTransfer >= 0.7) return RISK_SCORE_COLORS.edge.high;
  if (riskTransfer >= 0.4) return RISK_SCORE_COLORS.edge.medium;
  return RISK_SCORE_COLORS.edge.low;
}

// ============================================
// 그래프 변환 함수
// ============================================

/**
 * 화면 좌표를 캔버스 좌표로 변환
 */
export function screenToCanvas(
  screenX: number,
  screenY: number,
  scale: number,
  offsetX: number,
  offsetY: number
): { x: number; y: number } {
  return {
    x: (screenX - offsetX) / scale,
    y: (screenY - offsetY) / scale,
  };
}

/**
 * 캔버스 좌표를 화면 좌표로 변환
 */
export function canvasToScreen(
  canvasX: number,
  canvasY: number,
  scale: number,
  offsetX: number,
  offsetY: number
): { x: number; y: number } {
  return {
    x: canvasX * scale + offsetX,
    y: canvasY * scale + offsetY,
  };
}

/**
 * 두 점 사이의 거리 계산
 */
export function distance(x1: number, y1: number, x2: number, y2: number): number {
  return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}
```

---

## 4. RiskGraph 인터렉티브 설계 (핵심)

### 4.1 State 구조

```typescript
interface GraphState {
  // 변환 상태
  scale: number;           // 확대/축소 배율 (0.3 ~ 3.0)
  offsetX: number;         // 패닝 X 오프셋
  offsetY: number;         // 패닝 Y 오프셋

  // 드래그 상태
  isPanning: boolean;      // 화면 드래그 중
  isNodeDragging: boolean; // 노드 드래그 중
  dragStartX: number;
  dragStartY: number;
  dragNodeId: string | null;

  // 선택 상태
  selectedNodeId: string | null;
  hoveredNodeId: string | null;

  // 노드 위치 (사용자 조정 가능)
  nodePositions: Map<string, { x: number; y: number }>;
}
```

### 4.2 이벤트 핸들러 설계

```typescript
// 마우스 휠 - 줌
const handleWheel = (e: WheelEvent) => {
  e.preventDefault();

  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  // 줌 계산
  const delta = -e.deltaY * ZOOM_CONFIG.wheelSensitivity;
  const newScale = Math.min(
    ZOOM_CONFIG.max,
    Math.max(ZOOM_CONFIG.min, state.scale * (1 + delta))
  );

  // 마우스 위치 중심으로 확대 (줌 포인트 보정)
  const scaleRatio = newScale / state.scale;
  const newOffsetX = mouseX - (mouseX - state.offsetX) * scaleRatio;
  const newOffsetY = mouseY - (mouseY - state.offsetY) * scaleRatio;

  setState({
    ...state,
    scale: newScale,
    offsetX: newOffsetX,
    offsetY: newOffsetY,
  });
};

// 마우스 다운 - 드래그 시작
const handleMouseDown = (e: MouseEvent) => {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  // 캔버스 좌표로 변환
  const canvasPos = screenToCanvas(mouseX, mouseY, state.scale, state.offsetX, state.offsetY);

  // 노드 클릭 검사
  const clickedNode = findNodeAtPosition(canvasPos.x, canvasPos.y);

  if (clickedNode) {
    // 노드 드래그 시작
    setState({
      ...state,
      isNodeDragging: true,
      dragNodeId: clickedNode.id,
      dragStartX: canvasPos.x,
      dragStartY: canvasPos.y,
    });
  } else {
    // 화면 패닝 시작
    setState({
      ...state,
      isPanning: true,
      dragStartX: e.clientX - state.offsetX,
      dragStartY: e.clientY - state.offsetY,
    });
  }
};

// 마우스 이동 - 드래그 진행
const handleMouseMove = (e: MouseEvent) => {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  if (state.isPanning) {
    // 화면 패닝
    setState({
      ...state,
      offsetX: e.clientX - state.dragStartX,
      offsetY: e.clientY - state.dragStartY,
    });
  } else if (state.isNodeDragging && state.dragNodeId) {
    // 노드 드래그
    const canvasPos = screenToCanvas(mouseX, mouseY, state.scale, state.offsetX, state.offsetY);
    const newPositions = new Map(state.nodePositions);
    newPositions.set(state.dragNodeId, { x: canvasPos.x, y: canvasPos.y });

    setState({
      ...state,
      nodePositions: newPositions,
    });
  } else {
    // 호버 검사
    const canvasPos = screenToCanvas(mouseX, mouseY, state.scale, state.offsetX, state.offsetY);
    const hoveredNode = findNodeAtPosition(canvasPos.x, canvasPos.y);

    setState({
      ...state,
      hoveredNodeId: hoveredNode?.id || null,
    });
  }
};

// 마우스 업 - 드래그 종료
const handleMouseUp = () => {
  setState({
    ...state,
    isPanning: false,
    isNodeDragging: false,
    dragNodeId: null,
  });
};

// 클릭 - 노드 선택
const handleClick = (e: MouseEvent) => {
  const rect = canvas.getBoundingClientRect();
  const canvasPos = screenToCanvas(
    e.clientX - rect.left,
    e.clientY - rect.top,
    state.scale,
    state.offsetX,
    state.offsetY
  );

  const clickedNode = findNodeAtPosition(canvasPos.x, canvasPos.y);

  if (clickedNode) {
    setState({
      ...state,
      selectedNodeId: clickedNode.id === state.selectedNodeId ? null : clickedNode.id,
    });
  }
};
```

### 4.3 키보드 네비게이션

```typescript
const handleKeyDown = (e: KeyboardEvent) => {
  const PAN_STEP = 50;  // 화살표 키 이동 단위 (px)

  switch (e.key) {
    case 'ArrowUp':
      setState({ ...state, offsetY: state.offsetY + PAN_STEP });
      break;
    case 'ArrowDown':
      setState({ ...state, offsetY: state.offsetY - PAN_STEP });
      break;
    case 'ArrowLeft':
      setState({ ...state, offsetX: state.offsetX + PAN_STEP });
      break;
    case 'ArrowRight':
      setState({ ...state, offsetX: state.offsetX - PAN_STEP });
      break;
    case '+':
    case '=':
      // 줌 인
      const newScaleIn = Math.min(ZOOM_CONFIG.max, state.scale + ZOOM_CONFIG.step);
      setState({ ...state, scale: newScaleIn });
      break;
    case '-':
      // 줌 아웃
      const newScaleOut = Math.max(ZOOM_CONFIG.min, state.scale - ZOOM_CONFIG.step);
      setState({ ...state, scale: newScaleOut });
      break;
    case '0':
      // 리셋
      setState({
        ...state,
        scale: ZOOM_CONFIG.default,
        offsetX: 0,
        offsetY: 0,
      });
      break;
    case 'Escape':
      // 선택 해제
      setState({ ...state, selectedNodeId: null });
      break;
  }
};
```

### 4.4 Canvas 렌더링 수정

```typescript
const render = useCallback(() => {
  const canvas = canvasRef.current;
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // 캔버스 클리어
  ctx.setTransform(1, 0, 0, 1, 0, 0);  // 변환 리셋
  ctx.fillStyle = '#1e293b';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // 변환 적용 (줌 + 패닝)
  ctx.setTransform(
    state.scale, 0, 0, state.scale,
    state.offsetX, state.offsetY
  );

  // 엣지 렌더링
  safeData.edges.forEach(edge => {
    const fromPos = state.nodePositions.get(edge.from || edge.source);
    const toPos = state.nodePositions.get(edge.to || edge.target);
    if (!fromPos || !toPos) return;

    ctx.beginPath();
    ctx.moveTo(fromPos.x, fromPos.y);
    ctx.lineTo(toPos.x, toPos.y);
    ctx.strokeStyle = getEdgeColor(edge.riskTransfer || edge.dependency || 0.3);
    ctx.lineWidth = Math.max(1, (edge.riskTransfer || 0.3) * 4) / state.scale;  // 스케일 보정
    ctx.stroke();

    // 화살표 렌더링...
  });

  // 노드 렌더링
  safeData.nodes.forEach(node => {
    const pos = state.nodePositions.get(node.id);
    if (!pos) return;

    const isCenter = node.type === 'company';
    const isHovered = state.hoveredNodeId === node.id;
    const isSelected = state.selectedNodeId === node.id;

    const baseRadius = isCenter ? NODE_SIZE.center : NODE_SIZE.normal;
    const radius = baseRadius + (isHovered ? NODE_SIZE.hoverIncrease : 0);

    // 노드 원
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = getNodeColor(node.riskScore);
    ctx.fill();

    // 테두리
    ctx.strokeStyle = isSelected
      ? RISK_SCORE_COLORS.node.selected
      : isHovered
        ? RISK_SCORE_COLORS.node.hovered
        : getNodeTypeStyle(node.type).border;
    ctx.lineWidth = (isSelected ? 4 : isHovered ? 3 : 2) / state.scale;  // 스케일 보정
    ctx.stroke();

    // 점수 텍스트
    ctx.fillStyle = '#fff';
    ctx.font = `bold ${(isCenter ? 14 : 12) / state.scale}px sans-serif`;  // 스케일 보정
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(node.riskScore.toString(), pos.x, pos.y);

    // 레이블
    ctx.fillStyle = '#e2e8f0';
    ctx.font = `${11 / state.scale}px sans-serif`;  // 스케일 보정
    ctx.fillText(node.name || node.id, pos.x, pos.y + radius + 12 / state.scale);
  });
}, [state, safeData]);
```

### 4.5 ZoomControls 컴포넌트

```typescript
// ZoomControls.tsx
import React from 'react';
import { ZOOM_CONFIG } from './constants';

interface ZoomControlsProps {
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  disabled?: boolean;
}

export const ZoomControls: React.FC<ZoomControlsProps> = ({
  scale,
  onZoomIn,
  onZoomOut,
  onReset,
  disabled = false,
}) => {
  const percentage = Math.round(scale * 100);
  const canZoomIn = scale < ZOOM_CONFIG.max;
  const canZoomOut = scale > ZOOM_CONFIG.min;

  return (
    <div className="absolute bottom-4 right-4 flex flex-col gap-1 bg-slate-900/90 rounded-lg p-2 shadow-lg border border-slate-700">
      {/* 줌 인 */}
      <button
        onClick={onZoomIn}
        disabled={disabled || !canZoomIn}
        className={`w-8 h-8 flex items-center justify-center rounded transition-colors ${
          canZoomIn && !disabled
            ? 'bg-slate-700 hover:bg-slate-600 text-white'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
        }`}
        aria-label="확대"
        title="확대 (+)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v12M6 12h12" />
        </svg>
      </button>

      {/* 퍼센트 표시 */}
      <div className="text-center text-xs text-slate-400 py-1 select-none">
        {percentage}%
      </div>

      {/* 줌 아웃 */}
      <button
        onClick={onZoomOut}
        disabled={disabled || !canZoomOut}
        className={`w-8 h-8 flex items-center justify-center rounded transition-colors ${
          canZoomOut && !disabled
            ? 'bg-slate-700 hover:bg-slate-600 text-white'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
        }`}
        aria-label="축소"
        title="축소 (-)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 12h12" />
        </svg>
      </button>

      {/* 구분선 */}
      <div className="border-t border-slate-700 my-1" />

      {/* 리셋 */}
      <button
        onClick={onReset}
        disabled={disabled}
        className={`w-8 h-8 flex items-center justify-center rounded text-xs transition-colors ${
          !disabled
            ? 'bg-slate-700 hover:bg-slate-600 text-white'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
        }`}
        aria-label="초기화"
        title="초기화 (0)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
    </div>
  );
};

export default ZoomControls;
```

---

## 5. 컴포넌트별 수정 상세

### 5.1 RiskOverview.tsx

**변경 사항**:
- `getStatusIcon` 함수 제거 → `EMOJI_MAP.status` 사용
- `getStatusColor` 함수 → `getStatusTailwind` import
- `getScoreColor` 함수 → `getScoreTextClass` import

```typescript
// Before
const getStatusIcon = (status: RiskStatus) => {
  switch (status) {
    case 'PASS': return '🟢';
    case 'WARNING': return '🟡';
    case 'FAIL': return '🔴';
  }
};

// After
import { EMOJI_MAP, getStatusTailwind, getScoreTextClass } from './constants';
// 사용: EMOJI_MAP.status[deal.status]
```

### 5.2 RiskStatusView.tsx

**변경 사항**:
- `STATUS_CONFIG` 객체 → constants.ts로 이동 및 통일
- 이모지 하드코딩 제거

```typescript
// Before (컴포넌트 내부)
const STATUS_CONFIG = {
  PASS: { label: '정상', icon: '🟢', ... },
  ...
};

// After (constants.ts에서 import)
import { EMOJI_MAP, RISK_SCORE_COLORS } from './constants';

const STATUS_CONFIG: Record<RiskStatus, StatusConfig> = {
  PASS: {
    label: '정상',
    icon: EMOJI_MAP.status.PASS,  // '🟢'
    ...RISK_SCORE_COLORS.tailwind.PASS,
    description: '리스크 수준 양호',
  },
  // ...
};
```

### 5.3 RiskScoreBreakdownV3.tsx

**변경 사항**:
- `STATUS_COLORS` 제거 → `RISK_SCORE_COLORS.tailwind` 사용
- `CATEGORY_ICONS` 제거 → `EMOJI_MAP.category` 사용
- 점수 색상 판정 통일

```typescript
// Before
const STATUS_COLORS = {
  PASS: { bg: 'bg-green-900/30', text: 'text-green-400', border: 'border-green-600' },
  ...
};

// After
import { RISK_SCORE_COLORS, EMOJI_MAP, getStatusFromScore, getScoreTextClass } from './constants';

// STATUS_COLORS → RISK_SCORE_COLORS.tailwind 직접 사용
// 점수 색상: getScoreTextClass(score) 사용
```

### 5.4 RiskGraph.tsx

**변경 사항**:
- 줌/팬/드래그 상태 추가
- `getNodeColor` 함수 → utils.ts의 `getNodeColor` import
- `getEdgeColor` 함수 → utils.ts의 `getEdgeColor` import
- ZoomControls 컴포넌트 추가
- 키보드 이벤트 핸들러 추가

**상세 수정 내역**:
1. 상태 확장 (scale, offsetX, offsetY, isPanning, ...)
2. 이벤트 핸들러 추가 (wheel, mousedown, mousemove, mouseup, keydown)
3. Canvas 렌더링 수정 (setTransform 적용)
4. ZoomControls UI 추가

---

## 6. 구현 순서

### Phase 1: 기반 구축 (필수)

| # | 작업 | 파일 | 담당 |
|:-:|------|------|------|
| 1 | constants.ts 생성 | `constants.ts` | 공유 상수 |
| 2 | utils.ts 생성 | `utils.ts` | 유틸리티 함수 |
| 3 | types.ts에서 constants export | `types.ts` | 호환성 |

### Phase 2: 컴포넌트 수정 (필수)

| # | 작업 | 파일 |
|:-:|------|------|
| 4 | RiskOverview 이모지/색상 적용 | `RiskOverview.tsx` |
| 5 | RiskStatusView 이모지 적용 | `RiskStatusView.tsx` |
| 6 | RiskScoreBreakdownV3 색상 적용 | `RiskScoreBreakdownV3.tsx` |
| 7 | RiskSignals 이모지 적용 | `RiskSignals.tsx` |
| 8 | 기타 컴포넌트 스타일 통일 | 나머지 |

### Phase 3: RiskGraph 인터렉티브 (핵심)

| # | 작업 | 파일 |
|:-:|------|------|
| 9 | ZoomControls 컴포넌트 생성 | `ZoomControls.tsx` |
| 10 | RiskGraph 상태 확장 | `RiskGraph.tsx` |
| 11 | 휠 줌 구현 | `RiskGraph.tsx` |
| 12 | 패닝 구현 | `RiskGraph.tsx` |
| 13 | 줌 컨트롤 연결 | `RiskGraph.tsx` |
| 14 | 키보드 네비게이션 추가 | `RiskGraph.tsx` |
| 15 | 노드 드래그 구현 (P1) | `RiskGraph.tsx` |

### Phase 4: 품질 개선 (선택)

| # | 작업 | 파일 |
|:-:|------|------|
| 16 | ARIA 레이블 추가 | 전체 |
| 17 | 포커스 스타일 개선 | 전체 |
| 18 | 터치 이벤트 지원 | `RiskGraph.tsx` |

---

## 7. 테스트 계획

### 7.1 단위 테스트

```typescript
// constants.test.ts
describe('EMOJI_MAP', () => {
  it('모든 Status에 대해 이모지가 정의되어야 함', () => {
    expect(EMOJI_MAP.status.PASS).toBe('🟢');
    expect(EMOJI_MAP.status.WARNING).toBe('🟡');
    expect(EMOJI_MAP.status.FAIL).toBe('🔴');
  });
});

// utils.test.ts
describe('getStatusFromScore', () => {
  it('0-49점은 PASS', () => {
    expect(getStatusFromScore(0)).toBe('PASS');
    expect(getStatusFromScore(49)).toBe('PASS');
  });

  it('50-74점은 WARNING', () => {
    expect(getStatusFromScore(50)).toBe('WARNING');
    expect(getStatusFromScore(74)).toBe('WARNING');
  });

  it('75-100점은 FAIL', () => {
    expect(getStatusFromScore(75)).toBe('FAIL');
    expect(getStatusFromScore(100)).toBe('FAIL');
  });
});
```

### 7.2 E2E 테스트

```typescript
// RiskGraph.e2e.test.ts
describe('RiskGraph Interactive', () => {
  it('마우스 휠로 줌 가능', async () => {
    // 초기 scale 확인
    // wheel 이벤트 발생
    // scale 변경 확인
  });

  it('드래그로 패닝 가능', async () => {
    // mousedown → mousemove → mouseup
    // offset 변경 확인
  });

  it('줌 컨트롤 버튼 동작', async () => {
    // + 버튼 클릭 → scale 증가
    // - 버튼 클릭 → scale 감소
    // Reset 버튼 → scale = 1.0
  });

  it('키보드 네비게이션 동작', async () => {
    // Arrow keys → offset 변경
    // +/- keys → scale 변경
    // 0 key → reset
  });
});
```

---

## 8. 검증 체크리스트

### 8.1 이모지 통일

- [ ] 모든 컴포넌트에서 `🟢🟡🔴` 사용 (다른 이모지 사용 금지)
- [ ] `EMOJI_MAP`에서만 이모지 참조
- [ ] 하드코딩된 이모지 없음

### 8.2 색상 통일

- [ ] `RISK_SCORE_COLORS`에서만 색상 참조
- [ ] 하드코딩된 색상값 없음
- [ ] Tailwind 클래스 일관성

### 8.3 임계값 통일

- [ ] `STATUS_THRESHOLDS` 사용
- [ ] 40/70 기준 코드 제거
- [ ] 모든 판정 로직에서 50/75 기준 사용

### 8.4 그래프 인터렉티브

- [ ] 마우스 휠 줌 동작
- [ ] 드래그 패닝 동작
- [ ] 줌 컨트롤 버튼 동작
- [ ] 키보드 네비게이션 동작
- [ ] 노드 호버/선택 동작 유지

---

**작성일**: 2026-02-06
**다음 단계**: 구현 시작 (`/pdca do risk-ui-ux-optimization`)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|:----:|------|----------|
| v1.0 | 2026-02-06 | 초안 작성 |
