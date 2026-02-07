/**
 * Sparkline - 인라인 미니 차트
 * Bloomberg 스타일 딜 카드 내 점수 추세 시각화
 */

import React, { useMemo } from 'react';

interface SparklineProps {
  /** 데이터 포인트 배열 (최소 2개) */
  data: number[];
  /** 너비 (px) */
  width?: number;
  /** 높이 (px) */
  height?: number;
  /** 선 색상 (auto = 추세에 따라 자동) */
  color?: string;
  /** 선 두께 */
  strokeWidth?: number;
  /** 마지막 점 표시 */
  showDot?: boolean;
  /** 그래디언트 채우기 */
  showFill?: boolean;
  className?: string;
}

export default function Sparkline({
  data,
  width = 80,
  height = 24,
  color,
  strokeWidth = 1.5,
  showDot = true,
  showFill = true,
  className = '',
}: SparklineProps) {
  const { path, fillPath, autoColor, lastX, lastY } = useMemo(() => {
    if (data.length < 2) {
      return { path: '', fillPath: '', autoColor: '#6b7280', lastX: 0, lastY: height / 2 };
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 2;
    const w = width - padding * 2;
    const h = height - padding * 2;

    const points = data.map((v, i) => ({
      x: padding + (i / (data.length - 1)) * w,
      y: padding + h - ((v - min) / range) * h,
    }));

    // SVG path
    const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

    // Fill path (area under curve)
    const fd = `${d} L${points[points.length - 1].x.toFixed(1)},${height} L${points[0].x.toFixed(1)},${height} Z`;

    // Auto color: compare first half avg vs second half avg
    const mid = Math.floor(data.length / 2);
    const firstHalf = data.slice(0, mid).reduce((a, b) => a + b, 0) / mid;
    const secondHalf = data.slice(mid).reduce((a, b) => a + b, 0) / (data.length - mid);
    const trend = secondHalf - firstHalf;
    const ac = trend > 2 ? '#ef4444' : trend < -2 ? '#10b981' : '#6b7280';

    const last = points[points.length - 1];
    return { path: d, fillPath: fd, autoColor: ac, lastX: last.x, lastY: last.y };
  }, [data, width, height]);

  const lineColor = color || autoColor;

  if (data.length < 2) return null;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      style={{ display: 'block' }}
    >
      {showFill && (
        <>
          <defs>
            <linearGradient id={`spark-fill-${lineColor.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity={0.2} />
              <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <path
            d={fillPath}
            fill={`url(#spark-fill-${lineColor.replace('#', '')})`}
          />
        </>
      )}
      <path
        d={path}
        fill="none"
        stroke={lineColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {showDot && (
        <circle
          cx={lastX}
          cy={lastY}
          r={2}
          fill={lineColor}
        />
      )}
    </svg>
  );
}
