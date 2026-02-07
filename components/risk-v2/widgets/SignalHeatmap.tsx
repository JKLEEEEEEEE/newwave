/**
 * SignalHeatmap - GitHub-style risk signal heatmap
 * Y-axis: 10 risk categories, X-axis: recent N periods (weeks/days)
 * Cell intensity = event count / score sum per bucket
 */

import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import type { RiskEventV2, RiskCategoryV2 } from '../types-v2';
import { CATEGORY_COLORS } from '../design-tokens';
import GlassCard from '../shared/GlassCard';

interface SignalHeatmapProps {
  events: RiskEventV2[];
  categories: RiskCategoryV2[];
  granularity?: 'day' | 'week';
  periods?: number;
  onCellClick?: (categoryCode: string, periodIndex: number) => void;
  className?: string;
}

interface CellData {
  count: number;
  totalScore: number;
}

interface TooltipInfo {
  x: number;
  y: number;
  periodLabel: string;
  categoryName: string;
  count: number;
  totalScore: number;
}

const CELL_SIZE = 30;
const CELL_GAP = 3;
const LABEL_WIDTH = 110;

/** Build time period boundaries going backwards from now */
function buildPeriods(granularity: 'day' | 'week', count: number) {
  const now = new Date();
  const periods: { start: Date; end: Date; label: string }[] = [];
  const msPerDay = 86_400_000;
  const span = granularity === 'week' ? 7 * msPerDay : msPerDay;

  for (let i = count - 1; i >= 0; i--) {
    const end = new Date(now.getTime() - i * span);
    const start = new Date(end.getTime() - span);
    const label =
      granularity === 'week'
        ? `${start.getMonth() + 1}/${start.getDate()}`
        : `${end.getMonth() + 1}/${end.getDate()}`;
    periods.push({ start, end, label });
  }
  return periods;
}

/** Compute max intensity across all cells for normalization */
function normalizeOpacity(score: number, max: number): number {
  if (max === 0) return 0.05;
  return Math.min(0.15 + (score / max) * 0.85, 1);
}

export default function SignalHeatmap({
  events,
  categories,
  granularity = 'week',
  periods: periodCount = 8,
  onCellClick,
  className = '',
}: SignalHeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  const timePeriods = useMemo(() => buildPeriods(granularity, periodCount), [granularity, periodCount]);

  // Bucket events by categoryCode x period index
  const { grid, maxScore } = useMemo(() => {
    const g: Record<string, CellData[]> = {};

    for (const cat of categories) {
      g[cat.code] = Array.from({ length: periodCount }, () => ({ count: 0, totalScore: 0 }));
    }

    for (const ev of events) {
      const code = (ev as RiskEventV2 & { categoryCode?: string }).categoryCode;
      if (!code || !g[code]) continue;
      const t = new Date(ev.publishedAt).getTime();
      for (let pi = 0; pi < timePeriods.length; pi++) {
        if (t >= timePeriods[pi].start.getTime() && t < timePeriods[pi].end.getTime()) {
          g[code][pi].count += 1;
          g[code][pi].totalScore += Math.abs(ev.score);
          break;
        }
      }
    }

    let mx = 0;
    for (const code of Object.keys(g)) {
      for (const cell of g[code]) {
        if (cell.totalScore > mx) mx = cell.totalScore;
      }
    }
    return { grid: g, maxScore: mx };
  }, [events, categories, periodCount, timePeriods]);

  const svgWidth = LABEL_WIDTH + periodCount * (CELL_SIZE + CELL_GAP);
  const svgHeight = categories.length * (CELL_SIZE + CELL_GAP) + 24; // +24 for x-axis labels

  return (
    <GlassCard gradient="primary" className={`p-5 ${className}`}>
      <h3 className="text-sm font-semibold text-slate-200 mb-4 tracking-wide">
        Risk Signal Heatmap
      </h3>

      <div className="relative overflow-x-auto">
        <svg
          width={svgWidth}
          height={svgHeight}
          className="select-none"
          onMouseLeave={() => setTooltip(null)}
        >
          {/* Y-axis labels (category icon + name) */}
          {categories.map((cat, ri) => (
            <text
              key={`label-${cat.code}`}
              x={LABEL_WIDTH - 8}
              y={ri * (CELL_SIZE + CELL_GAP) + CELL_SIZE / 2 + 4}
              textAnchor="end"
              className="fill-slate-400 text-[11px]"
            >
              {cat.icon} {cat.name}
            </text>
          ))}

          {/* Grid cells */}
          {categories.map((cat, ri) =>
            timePeriods.map((period, ci) => {
              const cell = grid[cat.code]?.[ci] ?? { count: 0, totalScore: 0 };
              const color = CATEGORY_COLORS[cat.code]?.color ?? '#6b7280';
              const opacity = cell.count === 0 ? 0.05 : normalizeOpacity(cell.totalScore, maxScore);
              const cx = LABEL_WIDTH + ci * (CELL_SIZE + CELL_GAP);
              const cy = ri * (CELL_SIZE + CELL_GAP);

              return (
                <motion.rect
                  key={`${cat.code}-${ci}`}
                  x={cx}
                  y={cy}
                  width={CELL_SIZE}
                  height={CELL_SIZE}
                  rx={4}
                  fill={color}
                  fillOpacity={opacity}
                  stroke={color}
                  strokeOpacity={0.15}
                  strokeWidth={1}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: (ri * periodCount + ci) * 0.008, duration: 0.3 }}
                  className="cursor-pointer"
                  onMouseEnter={(e) => {
                    const svgEl = (e.target as SVGRectElement).ownerSVGElement;
                    const rect = svgEl?.getBoundingClientRect();
                    setTooltip({
                      x: cx + CELL_SIZE / 2 + (rect?.left ?? 0),
                      y: cy + (rect?.top ?? 0) - 8,
                      periodLabel: period.label,
                      categoryName: `${cat.icon} ${cat.name}`,
                      count: cell.count,
                      totalScore: cell.totalScore,
                    });
                  }}
                  onMouseLeave={() => setTooltip(null)}
                  onClick={() => onCellClick?.(cat.code, ci)}
                />
              );
            }),
          )}

          {/* X-axis labels (period) */}
          {timePeriods.map((period, ci) => (
            <text
              key={`x-${ci}`}
              x={LABEL_WIDTH + ci * (CELL_SIZE + CELL_GAP) + CELL_SIZE / 2}
              y={categories.length * (CELL_SIZE + CELL_GAP) + 14}
              textAnchor="middle"
              className="fill-slate-500 text-[10px]"
            >
              {period.label}
            </text>
          ))}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="fixed z-50 pointer-events-none px-3 py-2 rounded-lg
                        bg-slate-800/95 border border-white/10 backdrop-blur-sm
                        shadow-xl text-xs text-slate-200 whitespace-nowrap"
            style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, -100%)' }}
          >
            <div className="font-semibold mb-1">{tooltip.categoryName}</div>
            <div className="text-slate-400">
              {granularity === 'week' ? 'Week of' : 'Date'}: {tooltip.periodLabel}
            </div>
            <div className="mt-1 flex gap-3">
              <span>Events: <span className="text-white font-medium">{tooltip.count}</span></span>
              <span>Score: <span className="text-white font-medium">{tooltip.totalScore.toFixed(1)}</span></span>
            </div>
          </div>
        )}
      </div>
    </GlassCard>
  );
}
