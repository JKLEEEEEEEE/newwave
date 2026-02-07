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
export type CategoryType = 'MARKET' | 'CREDIT' | 'OPERATIONAL' | 'LEGAL' | 'SUPPLY' | 'ESG' | 'GOVERNANCE' | 'REPUTATION' | 'MACRO' | 'FINANCIAL';
export type SourceType = 'DART' | 'NEWS' | 'KIND' | 'MANUAL';
export type NodeTypeKey = 'company' | 'supplier' | 'customer' | 'competitor' | 'subsidiary' | 'person';

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
    up: '📈',
    down: '📉',
    stable: '➡️',
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
    // 한글 키워드 매핑
    '법률위험': '⚖️',
    '신용위험': '💳',
    '운영위험': '⚙️',
    '시장위험': '📊',
    '공급망위험': '🔗',
    'ESG위험': '🌱',
    '재무위험': '💰',
    '평판위험': '📢',
    '지배구조': '👔',
    '거시환경': '🌍',
    // types.ts의 RiskCategoryId 매핑
    financial: '💰',
    legal: '⚖️',
    governance: '👔',
    supply_chain: '🔗',
    market: '📊',
    reputation: '📢',
    operational: '⚙️',
    macro: '🌍',
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

  // 노드 타입 테두리 색상
  nodeTypeBorder: {
    company: '#3b82f6',
    supplier: '#8b5cf6',
    customer: '#06b6d4',
    competitor: '#f97316',
    subsidiary: '#10b981',
    person: '#f59e0b',
  } as const,
} as const;

// ============================================
// 색상 상수
// ============================================
export const RISK_SCORE_COLORS = {
  // Status 기본 색상 (Canvas용 hex)
  PASS: '#22C55E',      // green-500
  WARNING: '#EAB308',   // yellow-500
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
  } as const,

  // 그래프 노드 색상 (Canvas용)
  node: {
    PASS: '#86EFAC',    // green-300
    WARNING: '#FDE047', // yellow-300
    FAIL: '#FCA5A5',    // red-300
    selected: '#3B82F6', // blue-500
    hovered: '#FFFFFF',  // white (border)
  } as const,

  // 그래프 엣지 색상
  edge: {
    default: '#64748B',   // slate-500
    low: '#22C55E',       // green-500 (riskTransfer < 0.4)
    medium: '#EAB308',    // yellow-500 (0.4 <= riskTransfer < 0.7)
    high: '#EF4444',      // red-500 (riskTransfer >= 0.7)
    selected: '#3B82F6',  // blue-500
  } as const,
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
  center: 35,            // 중심 노드 반지름
  normal: 25,            // 일반 노드 반지름
  hoverIncrease: 3,      // 호버 시 증가량
} as const;

// ============================================
// Status 설정 (UI용)
// ============================================
export const STATUS_CONFIG = {
  PASS: {
    label: '정상',
    icon: EMOJI_MAP.status.PASS,
    description: '리스크 수준 양호',
    ...RISK_SCORE_COLORS.tailwind.PASS,
  },
  WARNING: {
    label: '주의',
    icon: EMOJI_MAP.status.WARNING,
    description: '모니터링 필요',
    ...RISK_SCORE_COLORS.tailwind.WARNING,
  },
  FAIL: {
    label: '위험',
    icon: EMOJI_MAP.status.FAIL,
    description: '즉시 대응 필요',
    ...RISK_SCORE_COLORS.tailwind.FAIL,
  },
} as const;
