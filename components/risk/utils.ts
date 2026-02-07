/**
 * Risk UI 유틸리티 함수
 */

import {
  EMOJI_MAP,
  RISK_SCORE_COLORS,
  STATUS_THRESHOLDS,
  RiskStatusType,
  TrendType,
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
export function getTrendEmoji(trend: TrendType | string): string {
  const upperTrend = trend.toUpperCase() as TrendType;
  return EMOJI_MAP.trend[upperTrend] || EMOJI_MAP.trend[trend as keyof typeof EMOJI_MAP.trend] || '➡️';
}

/**
 * 카테고리 이모지 반환
 */
export function getCategoryEmoji(category: string): string {
  return EMOJI_MAP.category[category as keyof typeof EMOJI_MAP.category] || '📊';
}

/**
 * 노드 타입 이모지 반환
 */
export function getNodeTypeEmoji(nodeType: string): string {
  return EMOJI_MAP.nodeType[nodeType as keyof typeof EMOJI_MAP.nodeType] || '📦';
}

/**
 * 노드 타입 테두리 색상 반환
 */
export function getNodeTypeBorder(nodeType: string): string {
  return EMOJI_MAP.nodeTypeBorder[nodeType as keyof typeof EMOJI_MAP.nodeTypeBorder] || '#64748b';
}

// ============================================
// 색상 함수
// ============================================

/**
 * Status에 따른 색상 반환 (Canvas용 hex)
 */
export function getStatusColor(status: RiskStatusType): string {
  return RISK_SCORE_COLORS[status];
}

/**
 * 점수에 따른 색상 반환 (Canvas용 hex)
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
 * 점수에 따른 Tailwind 배경 클래스 반환
 */
export function getScoreBgClass(score: number): string {
  const status = getStatusFromScore(score);
  return RISK_SCORE_COLORS.tailwind[status].bg;
}

/**
 * 노드 색상 반환 (Canvas용 - 그래프 노드)
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

/**
 * 값을 범위 내로 제한
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
