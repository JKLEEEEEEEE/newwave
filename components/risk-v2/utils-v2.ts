/**
 * Risk V2 - 유틸리티 함수
 * 점수 변환, 색상 매핑, 포맷 등 공통 유틸
 */

import type { RiskLevelV2, CategoryCodeV2, CategoryDefinitionV2 } from './types-v2';
import { RISK_COLORS, CATEGORY_COLORS } from './design-tokens';
import { CATEGORY_DEFINITIONS_V2 } from './category-definitions';

// ============================================
// 점수 → 리스크 레벨 변환
// ============================================

/** 점수를 리스크 레벨로 변환 (V5 기준: 50이상 FAIL, 30이상 WARNING, 나머지 PASS) */
export function getScoreLevel(score: number): RiskLevelV2 {
  if (score >= 50) return 'FAIL';
  if (score >= 30) return 'WARNING';
  return 'PASS';
}

// ============================================
// 리스크 레벨 → Tailwind 클래스
// ============================================

/** 리스크 레벨에 따른 Tailwind CSS 클래스 반환 */
export function getLevelClasses(level: RiskLevelV2): {
  text: string;
  bg: string;
  border: string;
  ring: string;
} {
  switch (level) {
    case 'PASS':
      return {
        text: 'text-emerald-400',
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/30',
        ring: 'ring-emerald-500/30',
      };
    case 'WARNING':
      return {
        text: 'text-amber-400',
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/30',
        ring: 'ring-amber-500/30',
      };
    case 'FAIL':
      return {
        text: 'text-red-400',
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        ring: 'ring-red-500/30',
      };
  }
}

// ============================================
// 카테고리 관련 유틸
// ============================================

/** 카테고리 코드 → 카테고리 정의 조회 */
export function getCategoryDef(code: CategoryCodeV2): CategoryDefinitionV2 {
  return (
    CATEGORY_DEFINITIONS_V2.find(c => c.code === code) ?? {
      code: 'OTHER',
      name: '기타',
      icon: '\uD83D\uDCCE',
      weight: 0.02,
    }
  );
}

/** 카테고리 코드 → 색상 정보 */
export function getCategoryColor(code: CategoryCodeV2): { color: string; bg: string } {
  return CATEGORY_COLORS[code] ?? { color: '#6b7280', bg: 'rgba(107, 114, 128, 0.15)' };
}

// ============================================
// 포맷 유틸
// ============================================

/** 점수 변화(delta) 포맷: +5, -3, 0 */
export function formatDelta(delta: number): string {
  if (delta > 0) return `+${delta}`;
  if (delta < 0) return `${delta}`;
  return '0';
}

/** 날짜 문자열 포맷: "2026-02-05T10:30:00Z" → "2026.02.05" */
export function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}.${m}.${day}`;
  } catch {
    return dateStr;
  }
}

/** 날짜 문자열 → 상대적 시간: "3시간 전", "2일 전" */
export function formatRelativeTime(dateStr: string): string {
  try {
    const now = Date.now();
    const target = new Date(dateStr).getTime();
    const diff = now - target;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '방금 전';
    if (minutes < 60) return `${minutes}분 전`;
    if (hours < 24) return `${hours}시간 전`;
    if (days < 30) return `${days}일 전`;
    return formatDate(dateStr);
  } catch {
    return dateStr;
  }
}

// ============================================
// 3D 그래프 유틸
// ============================================

/** 리스크 레벨 → 3D 노드 색상 (hex) */
export function getNode3DColor(level: RiskLevelV2): string {
  return RISK_COLORS[level]?.primary ?? '#6b7280';
}

/** 노드 타입과 리스크 점수 → 3D 노드 크기 */
export function getNode3DSize(nodeType: string, riskScore: number): number {
  const baseSize: Record<string, number> = {
    deal: 12,
    mainCompany: 10,
    relatedCompany: 6,
    riskCategory: 5,
    riskEntity: 4,
  };

  const base = baseSize[nodeType] ?? 4;
  // 리스크 점수가 높을수록 노드 크기 증가 (최대 2배)
  const scoreFactor = 1 + Math.min(riskScore / 100, 1);
  return base * scoreFactor;
}

// ============================================
// 심각도 유틸
// ============================================

/** 심각도 → 한글 라벨 */
export function getSeverityLabel(severity: string): string {
  const labels: Record<string, string> = {
    CRITICAL: '심각',
    HIGH: '높음',
    MEDIUM: '보통',
    LOW: '낮음',
  };
  return labels[severity] ?? severity;
}

/** 심각도 → Tailwind 텍스트 클래스 */
export function getSeverityTextClass(severity: string): string {
  const classes: Record<string, string> = {
    CRITICAL: 'text-red-400',
    HIGH: 'text-orange-400',
    MEDIUM: 'text-amber-400',
    LOW: 'text-emerald-400',
  };
  return classes[severity] ?? 'text-slate-400';
}

// ============================================
// 트렌드 유틸
// ============================================

/** 트렌드 → 화살표 문자 */
export function getTrendArrow(trend: string): string {
  switch (trend) {
    case 'UP': return '\u2191';
    case 'DOWN': return '\u2193';
    case 'STABLE': return '\u2192';
    default: return '-';
  }
}

/** 트렌드 → Tailwind 텍스트 클래스 */
export function getTrendTextClass(trend: string): string {
  switch (trend) {
    case 'UP': return 'text-red-400';
    case 'DOWN': return 'text-emerald-400';
    case 'STABLE': return 'text-slate-400';
    default: return 'text-slate-400';
  }
}

// ============================================
// 숫자 유틸
// ============================================

/** 숫자를 지정 범위로 클램프 */
export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/** 0~100 점수 → 퍼센트 문자열 */
export function scoreToPercent(score: number, max: number = 100): string {
  return `${Math.round((score / max) * 100)}%`;
}
