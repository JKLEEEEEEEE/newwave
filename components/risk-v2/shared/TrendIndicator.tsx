/**
 * TrendIndicator - 트렌드 방향 표시 (UP / DOWN / STABLE)
 * 화살표 아이콘 + 선택적 변화량 표시
 *
 * Props:
 *   - trend: 방향 (UP | DOWN | STABLE)
 *   - value: 변화량 (선택)
 *   - size: 크기 (sm | md | lg)
 */

import React from 'react';
import type { TrendV2 } from '../types-v2';

interface TrendIndicatorProps {
  trend: TrendV2;
  /** 변화량 (숫자, 선택적) */
  value?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/** 트렌드별 설정 */
const TREND_CONFIG: Record<TrendV2, {
  arrow: string;
  textClass: string;
  label: string;
}> = {
  UP: {
    arrow: '\u2191',     // ↑
    textClass: 'text-red-400',
    label: '상승',
  },
  DOWN: {
    arrow: '\u2193',     // ↓
    textClass: 'text-emerald-400',
    label: '하락',
  },
  STABLE: {
    arrow: '\u2192',     // →
    textClass: 'text-slate-400',
    label: '보합',
  },
};

/** 사이즈별 클래스 */
const SIZE_CLASSES = {
  sm: 'text-xs gap-0.5',
  md: 'text-sm gap-1',
  lg: 'text-base gap-1.5',
};

export default function TrendIndicator({
  trend,
  value,
  size = 'md',
  className = '',
}: TrendIndicatorProps) {
  const config = TREND_CONFIG[trend];

  return (
    <span
      className={`
        inline-flex items-center font-medium
        ${config.textClass}
        ${SIZE_CLASSES[size]}
        ${className}
      `}
      title={config.label}
    >
      {/* 화살표 */}
      <span className="font-bold">{config.arrow}</span>

      {/* 변화량 (있으면 표시) */}
      {value !== undefined && (
        <span>
          {value > 0 ? '+' : ''}{value}
        </span>
      )}
    </span>
  );
}
