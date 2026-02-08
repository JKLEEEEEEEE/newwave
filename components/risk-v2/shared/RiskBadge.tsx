/**
 * RiskBadge - PASS / WARNING / CRITICAL 상태 뱃지
 * 리스크 레벨에 따라 색상, 아이콘, 라벨 자동 결정
 *
 * Props:
 *   - level: 리스크 레벨 (PASS | WARNING | CRITICAL)
 *   - size: 뱃지 크기 (sm | md | lg)
 *   - showLabel: 라벨 텍스트 표시 여부
 *   - animated: CRITICAL일 때 pulse 애니메이션
 */

import React from 'react';
import type { RiskLevelV2 } from '../types-v2';
import { RISK_COLORS } from '../design-tokens';

interface RiskBadgeProps {
  level: RiskLevelV2;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  animated?: boolean;
  className?: string;
}

/** 레벨별 한글 라벨 */
const LEVEL_LABELS: Record<RiskLevelV2, string> = {
  PASS: '정상',
  WARNING: '주의',
  CRITICAL: '위험',
};

/** 사이즈별 Tailwind 클래스 */
const SIZE_CLASSES = {
  sm: {
    wrapper: 'px-2 py-0.5 text-xs gap-1',
    dot: 'w-1.5 h-1.5',
  },
  md: {
    wrapper: 'px-3 py-1 text-sm gap-1.5',
    dot: 'w-2 h-2',
  },
  lg: {
    wrapper: 'px-4 py-1.5 text-base gap-2',
    dot: 'w-2.5 h-2.5',
  },
};

export default function RiskBadge({
  level,
  size = 'md',
  showLabel = true,
  animated = false,
  className = '',
}: RiskBadgeProps) {
  const colors = RISK_COLORS[level];
  const sizeClasses = SIZE_CLASSES[size];
  const shouldAnimate = animated && level === 'CRITICAL';

  return (
    <span
      className={`
        inline-flex items-center rounded-full font-medium
        ${sizeClasses.wrapper}
        ${className}
      `}
      style={{
        backgroundColor: colors.bg,
        color: colors.primary,
        border: `1px solid ${colors.border}`,
      }}
    >
      {/* 상태 점 */}
      <span
        className={`
          rounded-full inline-block flex-shrink-0
          ${sizeClasses.dot}
          ${shouldAnimate ? 'animate-pulse' : ''}
        `}
        style={{ backgroundColor: colors.primary }}
      />

      {/* 라벨 */}
      {showLabel && (
        <span>{LEVEL_LABELS[level]}</span>
      )}
    </span>
  );
}
