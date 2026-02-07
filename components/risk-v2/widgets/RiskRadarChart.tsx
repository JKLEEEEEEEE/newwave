'use client';

/**
 * RiskRadarChart - 10축 레이더 차트 + 업종 벤치마크 비교
 *
 * 10개 리스크 카테고리를 레이더 형태로 시각화하며,
 * 선택적으로 업종 평균 벤치마크와 비교 가능.
 */

import React, { useMemo } from 'react';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { motion } from 'framer-motion';
import type { RiskCategoryV2 } from '../types-v2';
import { CATEGORY_COLORS } from '../design-tokens';
import GlassCard from '../shared/GlassCard';

// ── Props ──────────────────────────────────────────

interface RiskRadarChartProps {
  categories: RiskCategoryV2[];
  /** 업종 평균 벤치마크 (카테고리 code -> 점수) */
  benchmark?: Partial<Record<string, number>>;
  /** 표시 모드: 원점수 or 가중점수 */
  mode?: 'score' | 'weightedScore';
  /** 축(카테고리) 클릭 콜백 */
  onCategoryClick?: (code: string) => void;
  className?: string;
}

// ── 차트 데이터 형태 ──────────────────────────────

interface RadarDatum {
  code: string;
  name: string;
  value: number;
  score: number;
  weight: number;
  weightedScore: number;
  benchmark?: number;
}

// ── 커스텀 Tooltip ─────────────────────────────────

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.[0]) return null;
  const d: RadarDatum = payload[0].payload;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/90 px-3 py-2 text-xs shadow-xl backdrop-blur-md">
      <p className="mb-1 font-semibold text-white">{d.name}</p>
      <p className="text-slate-300">
        Score: <span className="text-white">{d.score}</span>
      </p>
      <p className="text-slate-300">
        Weight: <span className="text-white">{(d.weight * 100).toFixed(0)}%</span>
      </p>
      <p className="text-slate-300">
        Weighted: <span className="text-purple-300">{d.weightedScore.toFixed(1)}</span>
      </p>
      {d.benchmark !== undefined && (
        <p className="mt-1 border-t border-white/10 pt-1 text-slate-400">
          Benchmark: <span className="text-slate-200">{d.benchmark}</span>
        </p>
      )}
    </div>
  );
}

// ── 커스텀 Tick (클릭 가능) ────────────────────────

function renderAngleTick(
  props: any,
  data: RadarDatum[],
  onCategoryClick?: (code: string) => void,
) {
  const { x, y, payload } = props;
  const datum = data[payload.index];
  if (!datum) return <g />;
  const catColor = CATEGORY_COLORS[datum.code]?.color ?? '#94a3b8';

  return (
    <g
      transform={`translate(${x},${y})`}
      onClick={() => onCategoryClick?.(datum.code)}
      style={{ cursor: onCategoryClick ? 'pointer' : 'default' }}
    >
      <text
        textAnchor="middle"
        dy={-2}
        fontSize={11}
        fill={catColor}
        fontWeight={600}
      >
        {datum.name}
      </text>
    </g>
  );
}

// ── 메인 컴포넌트 ──────────────────────────────────

export default function RiskRadarChart({
  categories,
  benchmark,
  mode = 'score',
  onCategoryClick,
  className = '',
}: RiskRadarChartProps) {
  const data = useMemo<RadarDatum[]>(() => {
    return categories.map((cat) => ({
      code: cat.code,
      name: cat.name,
      value: mode === 'weightedScore' ? (cat.weightedScore ?? cat.score * cat.weight) : cat.score,
      score: cat.score,
      weight: cat.weight,
      weightedScore: cat.weightedScore ?? cat.score * cat.weight,
      benchmark: benchmark?.[cat.code],
    }));
  }, [categories, benchmark, mode]);

  const maxValue = useMemo(() => {
    const vals = data.map((d) => d.value);
    if (benchmark) vals.push(...Object.values(benchmark).filter((v): v is number => v != null));
    return Math.max(100, ...vals);
  }, [data, benchmark]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <GlassCard gradient="purple" className={`p-5 ${className}`}>
        {/* Header */}
        <h3 className="mb-3 text-sm font-semibold tracking-wide text-slate-200">
          Risk Radar
        </h3>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={340}>
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
            <PolarGrid stroke="rgba(148,163,184,0.12)" />
            <PolarAngleAxis
              dataKey="name"
              tick={(props: any) => renderAngleTick(props, data, onCategoryClick)}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, maxValue]}
              tick={{ fill: '#64748b', fontSize: 10 }}
              axisLine={false}
            />

            {/* 벤치마크 (있으면) */}
            {benchmark && (
              <Radar
                name="Benchmark"
                dataKey="benchmark"
                stroke="#94a3b8"
                fill="transparent"
                strokeWidth={1.5}
                strokeDasharray="6 3"
                dot={false}
              />
            )}

            {/* 현재 기업 */}
            <Radar
              name="Current"
              dataKey="value"
              stroke="#a78bfa"
              fill="#8b5cf6"
              fillOpacity={0.25}
              strokeWidth={2}
              dot={{ r: 3, fill: '#a78bfa', strokeWidth: 0 }}
              activeDot={{ r: 5, fill: '#c4b5fd', strokeWidth: 0 }}
            />

            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 11, color: '#94a3b8', paddingTop: 4 }}
              iconSize={10}
            />
          </RadarChart>
        </ResponsiveContainer>
      </GlassCard>
    </motion.div>
  );
}
