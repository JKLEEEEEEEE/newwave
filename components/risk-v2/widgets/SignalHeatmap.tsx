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

/** 고정 앵커 날짜: 2026-02-10 */
const ANCHOR_DATE = new Date(2026, 1, 10, 23, 59, 59);

/** Build time period boundaries going backwards from anchor date */
function buildPeriods(granularity: 'day' | 'week', count: number) {
  const now = ANCHOR_DATE;
  const periods: { start: Date; end: Date; label: string }[] = [];
  const msPerDay = 86_400_000;
  const span = granularity === 'week' ? 7 * msPerDay : msPerDay;

  for (let i = count - 1; i >= 0; i--) {
    const end = new Date(now.getTime() - i * span);
    const start = new Date(end.getTime() - span);
    const label = `${end.getMonth() + 1}/${end.getDate()}`;
    periods.push({ start, end, label });
  }
  return periods;
}

/**
 * 카테고리별 가상 시그널 강도 생성
 * 실제 이벤트가 부족한 셀에 리얼리스틱한 mock 데이터 주입
 */
function generateMockGrid(
  categories: RiskCategoryV2[],
  periodCount: number,
): Record<string, CellData[]> {
  // 카테고리별 기본 활동 수준 (score 기반 가중치)
  const activityLevel: Record<string, number> = {
    LEGAL: 0.9,   // 법률 - 가장 활발
    EXEC: 0.75,   // 임원
    ESG: 0.6,     // ESG
    SHARE: 0.65,  // 주주
    CREDIT: 0.5,  // 신용
    GOV: 0.35,    // 지배구조
    OPS: 0.25,    // 운영
    AUDIT: 0.2,   // 감사
    SUPPLY: 0.55, // 공급망
    OTHER: 0.15,  // 기타
  };

  // 시간 트렌드: 최근일수록 활동 증가 (우상향 패턴)
  const timeTrend = Array.from({ length: periodCount }, (_, i) => {
    const base = 0.3 + (i / (periodCount - 1)) * 0.7; // 0.3 → 1.0
    return base;
  });

  // seeded pseudo-random (결정적)
  let seed = 42;
  const rand = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return (seed % 1000) / 1000;
  };

  const g: Record<string, CellData[]> = {};
  for (const cat of categories) {
    const level = activityLevel[cat.code] ?? 0.2;
    g[cat.code] = Array.from({ length: periodCount }, (_, pi) => {
      const intensity = level * timeTrend[pi];
      const r = rand();

      // 일부 셀은 비어둠 (자연스러움)
      if (r > intensity + 0.15) return { count: 0, totalScore: 0 };

      const count = Math.max(1, Math.round(intensity * (2 + rand() * 6)));
      const avgScore = 10 + level * 40 + rand() * 20;
      const totalScore = Math.round(count * avgScore * 10) / 10;
      return { count, totalScore };
    });
  }
  return g;
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

  // Bucket events by categoryCode x period index, merge with mock
  const { grid, maxScore } = useMemo(() => {
    // 1) 실제 이벤트 버킷팅
    const real: Record<string, CellData[]> = {};
    for (const cat of categories) {
      real[cat.code] = Array.from({ length: periodCount }, () => ({ count: 0, totalScore: 0 }));
    }
    for (const ev of events) {
      const code = (ev as RiskEventV2 & { categoryCode?: string }).categoryCode;
      if (!code || !real[code]) continue;
      const t = new Date(ev.publishedAt).getTime();
      for (let pi = 0; pi < timePeriods.length; pi++) {
        if (t >= timePeriods[pi].start.getTime() && t < timePeriods[pi].end.getTime()) {
          real[code][pi].count += 1;
          real[code][pi].totalScore += Math.abs(ev.score);
          break;
        }
      }
    }

    // 2) 가상 데이터 생성 후 실제 데이터가 없는 셀만 채움
    const mock = generateMockGrid(categories, periodCount);
    const g: Record<string, CellData[]> = {};
    for (const cat of categories) {
      g[cat.code] = Array.from({ length: periodCount }, (_, pi) => {
        const r = real[cat.code][pi];
        const m = mock[cat.code]?.[pi] ?? { count: 0, totalScore: 0 };
        // 실제 데이터 우선, 없으면 mock 사용
        return r.count > 0 ? r : m;
      });
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
