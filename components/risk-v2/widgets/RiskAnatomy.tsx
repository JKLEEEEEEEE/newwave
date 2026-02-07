/**
 * RiskAnatomy - BowTie Diagram Widget
 *
 * 왼쪽(원인/엔티티) -> 중앙(리스크 카테고리) -> 오른쪽(결과/영향)
 * Pure SVG + framer-motion 애니메이션
 */

import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import type { RiskCategoryV2, RiskEntityV2, RiskEventV2 } from '../types-v2';
import { CATEGORY_COLORS, RISK_COLORS } from '../design-tokens';
import GlassCard from '../shared/GlassCard';

// ============================================
// 타입 & 상수
// ============================================

interface RiskAnatomyProps {
  category: RiskCategoryV2;
  entities: RiskEntityV2[];
  events?: RiskEventV2[];
  onEntityClick?: (entityId: string) => void;
  className?: string;
}

type RiskLevelKey = 'PASS' | 'WARNING' | 'FAIL';

const ENTITY_ICONS: Record<string, string> = {
  PERSON: '\uD83D\uDC64',
  SHAREHOLDER: '\uD83C\uDFE2',
  CASE: '\u2696\uFE0F',
  ISSUE: '\u26A0\uFE0F',
};

const getRiskLevel = (score: number): RiskLevelKey =>
  score >= 70 ? 'FAIL' : score >= 40 ? 'WARNING' : 'PASS';

const IMPACT_LABELS: Record<RiskLevelKey, string> = {
  PASS: 'Low Impact',
  WARNING: 'Medium Impact',
  FAIL: 'High Impact',
};

// ============================================
// SVG 레이아웃 상수
// ============================================

const SVG_W = 900;
const SVG_H_MIN = 300;
const ROW_H = 56;

const LEFT_X = 30;
const LEFT_W = 200;
const CENTER_X = SVG_W / 2;
const RIGHT_X = SVG_W - 230;
const RIGHT_W = 200;

// ============================================
// 오른쪽 윙(결과) 데이터 생성
// ============================================

interface ImpactItem {
  id: string;
  label: string;
  value: string;
  level: RiskLevelKey;
}

function buildImpacts(cat: RiskCategoryV2): ImpactItem[] {
  const ws = cat.weightedScore ?? +(cat.score * cat.weight).toFixed(1);
  const level = getRiskLevel(cat.score);

  const items: ImpactItem[] = [
    {
      id: 'ws',
      label: 'Weighted Score',
      value: `${ws.toFixed(1)}`,
      level,
    },
    {
      id: 'contrib',
      label: 'Score Contribution',
      value: `${(cat.weight * 100).toFixed(0)}% weight`,
      level,
    },
    {
      id: 'impact',
      label: 'Impact Level',
      value: IMPACT_LABELS[level],
      level,
    },
  ];

  return items;
}

// ============================================
// 베지에 곡선 path 생성
// ============================================

function bezierPath(x1: number, y1: number, x2: number, y2: number): string {
  const cx = (x1 + x2) / 2;
  return `M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`;
}

// ============================================
// 메인 컴포넌트
// ============================================

export default function RiskAnatomy({
  category,
  entities,
  events,
  onEntityClick,
  className = '',
}: RiskAnatomyProps) {
  const [hoveredEntity, setHoveredEntity] = useState<string | null>(null);

  const catColor = CATEGORY_COLORS[category.code]?.color ?? '#6b7280';
  const catBg = CATEGORY_COLORS[category.code]?.bg ?? 'rgba(107,114,128,0.15)';
  const riskLevel = getRiskLevel(category.score);
  const riskColor = RISK_COLORS[riskLevel].primary;

  // 엔티티를 riskScore 내림차순 정렬
  const sortedEntities = useMemo(
    () => [...entities].sort((a, b) => b.riskScore - a.riskScore),
    [entities],
  );

  const impacts = useMemo(() => buildImpacts(category), [category]);

  // SVG 높이 계산
  const maxRows = Math.max(sortedEntities.length, impacts.length, 3);
  const svgH = Math.max(SVG_H_MIN, maxRows * ROW_H + 80);

  // Y 위치 계산 헬퍼
  const entityY = (idx: number) => {
    const totalH = sortedEntities.length * ROW_H;
    const startY = (svgH - totalH) / 2 + ROW_H / 2;
    return startY + idx * ROW_H;
  };

  const impactY = (idx: number) => {
    const totalH = impacts.length * ROW_H;
    const startY = (svgH - totalH) / 2 + ROW_H / 2;
    return startY + idx * ROW_H;
  };

  const centerY = svgH / 2;

  // 애니메이션 variants
  const lineVariant = {
    hidden: { pathLength: 0, opacity: 0 },
    visible: (i: number) => ({
      pathLength: 1,
      opacity: 0.7,
      transition: { delay: 0.3 + i * 0.08, duration: 0.5, ease: 'easeOut' },
    }),
  };

  const nodeVariant = {
    hidden: { opacity: 0, scale: 0.8 },
    visible: (i: number) => ({
      opacity: 1,
      scale: 1,
      transition: { delay: 0.1 + i * 0.06, duration: 0.35, ease: 'easeOut' },
    }),
  };

  return (
    <GlassCard className={`p-5 ${className}`} gradient="primary">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-lg">{category.icon}</span>
        <h3 className="text-sm font-semibold text-slate-200 tracking-wide">
          Risk Anatomy
        </h3>
        <span
          className="ml-auto text-xs font-mono px-2 py-0.5 rounded-full"
          style={{ color: riskColor, background: RISK_COLORS[riskLevel].bg }}
        >
          {riskLevel} &middot; {category.score}
        </span>
      </div>

      {/* SVG Diagram */}
      <svg
        viewBox={`0 0 ${SVG_W} ${svgH}`}
        className="w-full h-auto"
        style={{ minHeight: 200 }}
      >
        {/* ── 연결선: 왼쪽 -> 중앙 ── */}
        {sortedEntities.map((ent, i) => (
          <motion.path
            key={`l-${ent.id}`}
            d={bezierPath(LEFT_X + LEFT_W, entityY(i), CENTER_X - 60, centerY)}
            fill="none"
            stroke={hoveredEntity === ent.id ? catColor : catColor}
            strokeWidth={hoveredEntity === ent.id ? 2.5 : 1.5}
            strokeOpacity={hoveredEntity === ent.id ? 1 : 0.5}
            variants={lineVariant}
            custom={i}
            initial="hidden"
            animate="visible"
          />
        ))}

        {/* ── 연결선: 중앙 -> 오른쪽 ── */}
        {impacts.map((imp, i) => (
          <motion.path
            key={`r-${imp.id}`}
            d={bezierPath(CENTER_X + 60, centerY, RIGHT_X, impactY(i))}
            fill="none"
            stroke={RISK_COLORS[imp.level].primary}
            strokeWidth={1.5}
            strokeOpacity={0.5}
            variants={lineVariant}
            custom={i + sortedEntities.length}
            initial="hidden"
            animate="visible"
          />
        ))}

        {/* ── 왼쪽 윙: 엔티티 노드 ── */}
        {sortedEntities.map((ent, i) => {
          const y = entityY(i);
          const eLevel = getRiskLevel(ent.riskScore);
          const eColor = RISK_COLORS[eLevel].primary;
          const isHovered = hoveredEntity === ent.id;

          return (
            <motion.g
              key={ent.id}
              variants={nodeVariant}
              custom={i}
              initial="hidden"
              animate="visible"
              style={{ cursor: onEntityClick ? 'pointer' : 'default' }}
              onClick={() => onEntityClick?.(ent.id)}
              onMouseEnter={() => setHoveredEntity(ent.id)}
              onMouseLeave={() => setHoveredEntity(null)}
            >
              <rect
                x={LEFT_X}
                y={y - 18}
                width={LEFT_W}
                height={36}
                rx={8}
                fill={isHovered ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.5)'}
                stroke={isHovered ? catColor : 'rgba(148,163,184,0.15)'}
                strokeWidth={isHovered ? 1.5 : 1}
              />
              {/* 아이콘 */}
              <text
                x={LEFT_X + 14}
                y={y + 5}
                fontSize={14}
                textAnchor="middle"
              >
                {ENTITY_ICONS[ent.type] ?? '\u2022'}
              </text>
              {/* 이름 (truncated) */}
              <text
                x={LEFT_X + 28}
                y={y + 4}
                fontSize={11}
                fill="#e2e8f0"
                fontWeight={500}
              >
                {ent.name.length > 14 ? ent.name.slice(0, 13) + '\u2026' : ent.name}
              </text>
              {/* 점수 뱃지 */}
              <rect
                x={LEFT_X + LEFT_W - 44}
                y={y - 10}
                width={36}
                height={20}
                rx={10}
                fill={RISK_COLORS[eLevel].bg}
              />
              <text
                x={LEFT_X + LEFT_W - 26}
                y={y + 4}
                fontSize={10}
                fill={eColor}
                textAnchor="middle"
                fontWeight={600}
                fontFamily="monospace"
              >
                {ent.riskScore}
              </text>
            </motion.g>
          );
        })}

        {/* ── 중앙 노드: 카테고리 ── */}
        <motion.g
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15, duration: 0.5, type: 'spring', stiffness: 200 }}
        >
          {/* 외곽 글로우 */}
          <circle
            cx={CENTER_X}
            cy={centerY}
            r={58}
            fill="none"
            stroke={catColor}
            strokeWidth={1}
            opacity={0.2}
          />
          {/* 메인 원 */}
          <circle
            cx={CENTER_X}
            cy={centerY}
            r={52}
            fill={catBg}
            stroke={catColor}
            strokeWidth={2}
          />
          {/* 카테고리 아이콘 */}
          <text
            x={CENTER_X}
            y={centerY - 14}
            textAnchor="middle"
            fontSize={20}
          >
            {category.icon}
          </text>
          {/* 카테고리 이름 */}
          <text
            x={CENTER_X}
            y={centerY + 6}
            textAnchor="middle"
            fontSize={11}
            fill="#e2e8f0"
            fontWeight={600}
          >
            {category.name}
          </text>
          {/* 점수 + 가중치 */}
          <text
            x={CENTER_X}
            y={centerY + 22}
            textAnchor="middle"
            fontSize={10}
            fill={catColor}
            fontFamily="monospace"
          >
            {category.score} &middot; w{(category.weight * 100).toFixed(0)}%
          </text>
        </motion.g>

        {/* ── 오른쪽 윙: 결과/영향 ── */}
        {impacts.map((imp, i) => {
          const y = impactY(i);
          const impColor = RISK_COLORS[imp.level].primary;

          return (
            <motion.g
              key={imp.id}
              variants={nodeVariant}
              custom={i + sortedEntities.length + 2}
              initial="hidden"
              animate="visible"
            >
              <rect
                x={RIGHT_X}
                y={y - 18}
                width={RIGHT_W}
                height={36}
                rx={8}
                fill="rgba(15,23,42,0.5)"
                stroke="rgba(148,163,184,0.15)"
                strokeWidth={1}
              />
              {/* 레벨 인디케이터 dot */}
              <circle
                cx={RIGHT_X + 14}
                cy={y}
                r={4}
                fill={impColor}
              />
              {/* 라벨 */}
              <text
                x={RIGHT_X + 26}
                y={y - 4}
                fontSize={9}
                fill="#94a3b8"
              >
                {imp.label}
              </text>
              {/* 값 */}
              <text
                x={RIGHT_X + 26}
                y={y + 10}
                fontSize={11}
                fill="#e2e8f0"
                fontWeight={600}
              >
                {imp.value}
              </text>
            </motion.g>
          );
        })}

        {/* ── 엔티티가 없을 경우 placeholder ── */}
        {sortedEntities.length === 0 && (
          <text
            x={LEFT_X + LEFT_W / 2}
            y={centerY}
            textAnchor="middle"
            fontSize={11}
            fill="#64748b"
          >
            No entities
          </text>
        )}
      </svg>
    </GlassCard>
  );
}
