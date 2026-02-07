/**
 * SkeletonLoader - 로딩 스켈레톤 (pulse 애니메이션)
 * 데이터 로딩 중 placeholder UI 역할
 *
 * Props:
 *   - width: 너비 (CSS 값)
 *   - height: 높이 (CSS 값)
 *   - rounded: 모서리 둥글기 ('sm' | 'md' | 'lg' | 'full')
 */

import React from 'react';

interface SkeletonLoaderProps {
  width?: string | number;
  height?: string | number;
  rounded?: 'sm' | 'md' | 'lg' | 'full' | 'none';
  className?: string;
}

/** rounded 매핑 */
const ROUNDED_CLASSES = {
  none: '',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

export default function SkeletonLoader({
  width,
  height,
  rounded = 'md',
  className = '',
}: SkeletonLoaderProps) {
  return (
    <div
      className={`
        animate-pulse
        bg-slate-700/30
        ${ROUNDED_CLASSES[rounded]}
        ${className}
      `}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  );
}

// ============================================
// 프리셋 스켈레톤 조합 컴포넌트
// ============================================

/** 텍스트 라인 스켈레톤 */
export function SkeletonLine({ width = '100%' }: { width?: string }) {
  return <SkeletonLoader width={width} height={16} rounded="sm" />;
}

/** 카드 형태 스켈레톤 */
export function SkeletonCard() {
  return (
    <div className="p-4 space-y-3 bg-slate-900/40 border border-white/5 rounded-2xl backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <SkeletonLoader width={40} height={40} rounded="full" />
        <div className="flex-1 space-y-2">
          <SkeletonLine width="60%" />
          <SkeletonLine width="40%" />
        </div>
      </div>
      <SkeletonLine />
      <SkeletonLine width="80%" />
    </div>
  );
}

/** 게이지 형태 스켈레톤 */
export function SkeletonGauge({ size = 120 }: { size?: number }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <SkeletonLoader width={size} height={size} rounded="full" />
      <SkeletonLine width="60px" />
    </div>
  );
}

/** 테이블 행 스켈레톤 */
export function SkeletonTableRow({ columns = 4 }: { columns?: number }) {
  const widths = Array.from({ length: columns }, () => `${Math.random() * 30 + 20}%`);
  return (
    <div className="flex items-center gap-4 py-3 px-4">
      {widths.map((w, i) => (
        <div key={i} style={{ width: w }}>
          <SkeletonLoader width="100%" height={14} rounded="sm" />
        </div>
      ))}
    </div>
  );
}
