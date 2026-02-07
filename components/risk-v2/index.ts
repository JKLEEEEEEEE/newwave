/**
 * Risk V2 - 배럴 파일 (Barrel Export)
 * 모든 타입, 컴포넌트, API, 유틸 re-export
 */

// ============================================
// 타입 (types-v2.ts)
// ============================================
export type {
  // 기본 열거형
  CategoryCodeV2,
  RiskLevelV2,
  TrendV2,
  SeverityV2,
  ViewType,
  EntityType,
  EventType,

  // 5-Node 타입
  DealV2,
  CompanyV2,
  RiskCategoryV2,
  RiskEntityV2,
  RiskEventV2,

  // 카테고리 정의
  CategoryDefinitionV2,
  CompanyRelationV2,

  // 3D 그래프
  GraphNode3D,
  GraphLink3D,
  GraphData3D,

  // 시뮬레이션
  SimulationScenarioV2,
  SimulationResultV2,

  // AI
  Text2CypherResultV2,
  CopilotContextData,
  AIInsightResponseV2,

  // API
  ApiResponseV2,
  DealsResponseV2,
  DealDetailResponseV2,
  CompanyDetailResponseV2,

  // UI
  HeatmapCell,
  RiskV2State,
  RiskV2Action,
} from './types-v2';

// ============================================
// 디자인 토큰 (design-tokens.ts)
// ============================================
export {
  GLASS,
  GRADIENTS,
  RISK_COLORS,
  CATEGORY_COLORS,
  SEVERITY_COLORS,
  NAV_ITEMS,
  ANIMATION,
  LAYOUT,
} from './design-tokens';

// ============================================
// 카테고리 정의 (category-definitions.ts)
// ============================================
export { CATEGORY_DEFINITIONS_V2 } from './category-definitions';

// ============================================
// 유틸리티 (utils-v2.ts)
// ============================================
export {
  getScoreLevel,
  getLevelClasses,
  getCategoryDef,
  getCategoryColor,
  formatDelta,
  formatDate,
  formatRelativeTime,
  getNode3DColor,
  getNode3DSize,
  getSeverityLabel,
  getSeverityTextClass,
  getTrendArrow,
  getTrendTextClass,
  clamp,
  scoreToPercent,
} from './utils-v2';

// ============================================
// API 클라이언트 (api-v2.ts)
// ============================================
export { riskApiV2, default as riskApiV2Default } from './api-v2';

// ============================================
// 컨텍스트 (context/RiskV2Context.tsx)
// ============================================
export { RiskV2Provider, useRiskV2 } from './context/RiskV2Context';

// ============================================
// 레이아웃 컴포넌트 (layout/)
// ============================================
export { default as RiskShell } from './layout/RiskShell';
export { default as NavigationBar } from './layout/NavigationBar';

// ============================================
// 공유 컴포넌트 (shared/)
// ============================================
export { default as GlassCard } from './shared/GlassCard';
export { default as RiskBadge } from './shared/RiskBadge';
export { default as ScoreGauge } from './shared/ScoreGauge';
export { default as TrendIndicator } from './shared/TrendIndicator';
export { default as SkeletonLoader, SkeletonLine, SkeletonCard, SkeletonGauge, SkeletonTableRow } from './shared/SkeletonLoader';
export { default as PoweredByBadge } from './shared/PoweredByBadge';
export { default as AnimatedNumber } from './shared/AnimatedNumber';

// ============================================
// 화면 컴포넌트 (screens/)
// ============================================
export { default as CommandCenter } from './screens/CommandCenter';
export { default as SupplyChainXRay } from './screens/SupplyChainXRay';
export { default as RiskDeepDive } from './screens/RiskDeepDive';
export { default as WarRoom } from './screens/WarRoom';
export { default as AICopilotPanel } from './screens/AICopilotPanel';
