'use client';

/**
 * EvidenceBoard - 탐정 수사판 스타일 관계도 + 시간축
 *
 * 상단 70%: 엔티티 노드 관계 그래프 (정적 격자 레이아웃)
 * 하단 30%: 이벤트 타임라인 (시간축 + severity 점)
 *
 * 엔티티 <-> 이벤트 하이라이트 연동 지원
 */

import React, { useMemo, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import type { RiskEntityV2, RiskEventV2 } from '../types-v2';
import { CATEGORY_COLORS, SEVERITY_COLORS } from '../design-tokens';
import GlassCard from '../shared/GlassCard';

// ── Props ──────────────────────────────────────────

interface EvidenceBoardProps {
  entities: RiskEntityV2[];
  events: RiskEventV2[];
  companyName?: string;
  onEntityClick?: (entityId: string) => void;
  onEventClick?: (eventId: string) => void;
  className?: string;
}

// ── Constants ──────────────────────────────────────

const ENTITY_ICONS: Record<string, string> = {
  PERSON: '\u{1F464}',
  SHAREHOLDER: '\u{1F3E2}',
  CASE: '\u2696\uFE0F',
  ISSUE: '\u26A0\uFE0F',
};

const SVG_W = 800;
const SVG_H = 500;
const GRAPH_H = SVG_H * 0.65;
const TIMELINE_Y = SVG_H * 0.72;
const TIMELINE_H = SVG_H * 0.28;
const COLS = 3;
const NODE_BASE = 36;
const NODE_MAX = 56;
const TIMELINE_LEFT = 60;
const TIMELINE_RIGHT = SVG_W - 40;

// ── Helpers ────────────────────────────────────────

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

function nodeSize(score: number): number {
  return clamp(NODE_BASE + (score / 100) * (NODE_MAX - NODE_BASE), NODE_BASE, NODE_MAX);
}

function eventDotRadius(score: number): number {
  return clamp(4 + (Math.abs(score) / 100) * 6, 4, 10);
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return '';
  }
}

// ── Main Component ─────────────────────────────────

export default function EvidenceBoard({
  entities,
  events,
  companyName,
  onEntityClick,
  onEventClick,
  className = '',
}: EvidenceBoardProps) {
  const [hoveredEntityId, setHoveredEntityId] = useState<string | null>(null);
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);
  const [tooltipEvent, setTooltipEvent] = useState<{ ev: RiskEventV2; x: number; y: number } | null>(null);

  // ── Node positions (grid layout) ─────────────────
  const nodePositions = useMemo(() => {
    const padX = 100;
    const padY = 60;
    const usableW = SVG_W - padX * 2;
    const rows = Math.ceil(entities.length / COLS);
    const cellW = usableW / COLS;
    const cellH = (GRAPH_H - padY * 2) / Math.max(rows, 1);

    return entities.map((ent, i) => {
      const col = i % COLS;
      const row = Math.floor(i / COLS);
      return {
        entity: ent,
        x: padX + cellW * col + cellW / 2,
        y: padY + cellH * row + cellH / 2,
      };
    });
  }, [entities]);

  // ── Category-based edges (same categoryCode) ─────
  const edges = useMemo(() => {
    const result: { from: typeof nodePositions[0]; to: typeof nodePositions[0] }[] = [];
    for (let i = 0; i < nodePositions.length; i++) {
      for (let j = i + 1; j < nodePositions.length; j++) {
        if (nodePositions[i].entity.categoryCode === nodePositions[j].entity.categoryCode) {
          result.push({ from: nodePositions[i], to: nodePositions[j] });
        }
      }
    }
    return result;
  }, [nodePositions]);

  // ── Timeline positions ──────────────────────────
  const timelineData = useMemo(() => {
    if (events.length === 0) return { sorted: [], minT: 0, maxT: 1, range: 1 };
    const sorted = [...events].sort(
      (a, b) => new Date(a.publishedAt).getTime() - new Date(b.publishedAt).getTime(),
    );
    const times = sorted.map((e) => new Date(e.publishedAt).getTime());
    const minT = Math.min(...times);
    const maxT = Math.max(...times);
    const range = maxT - minT || 1;
    return { sorted, minT, maxT, range };
  }, [events]);

  const eventPositions = useMemo(() => {
    const { sorted, minT, range } = timelineData;
    const axisW = TIMELINE_RIGHT - TIMELINE_LEFT;
    const baseY = TIMELINE_Y + TIMELINE_H * 0.4;
    return sorted.map((ev) => {
      const t = new Date(ev.publishedAt).getTime();
      const ratio = (t - minT) / range;
      return { event: ev, x: TIMELINE_LEFT + axisW * ratio, y: baseY };
    });
  }, [timelineData]);

  // ── Entity lookup by id ─────────────────────────
  const entityPosMap = useMemo(() => {
    const m = new Map<string, (typeof nodePositions)[0]>();
    nodePositions.forEach((np) => m.set(np.entity.id, np));
    return m;
  }, [nodePositions]);

  // ── Highlight logic ─────────────────────────────
  const highlightedEntityIds = useMemo(() => {
    if (hoveredEntityId) return new Set([hoveredEntityId]);
    if (hoveredEventId) {
      const ev = events.find((e) => e.id === hoveredEventId);
      if (ev?.entityId) return new Set([ev.entityId]);
    }
    return null;
  }, [hoveredEntityId, hoveredEventId, events]);

  const highlightedEventIds = useMemo(() => {
    if (hoveredEventId) return new Set([hoveredEventId]);
    if (hoveredEntityId) {
      return new Set(events.filter((e) => e.entityId === hoveredEntityId).map((e) => e.id));
    }
    return null;
  }, [hoveredEntityId, hoveredEventId, events]);

  // ── Callbacks ───────────────────────────────────
  const handleEntityEnter = useCallback((id: string) => setHoveredEntityId(id), []);
  const handleEntityLeave = useCallback(() => setHoveredEntityId(null), []);
  const handleEventEnter = useCallback(
    (ev: RiskEventV2, x: number, y: number) => {
      setHoveredEventId(ev.id);
      setTooltipEvent({ ev, x, y });
    },
    [],
  );
  const handleEventLeave = useCallback(() => {
    setHoveredEventId(null);
    setTooltipEvent(null);
  }, []);

  // ── Opacity helper ──────────────────────────────
  const entityOpacity = (id: string) => (!highlightedEntityIds ? 1 : highlightedEntityIds.has(id) ? 1 : 0.25);
  const eventOpacity = (id: string) => (!highlightedEventIds ? 1 : highlightedEventIds.has(id) ? 1 : 0.25);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <GlassCard gradient="purple" className={`p-5 ${className}`}>
        {/* Header */}
        <div className="mb-3 flex items-center gap-2">
          <span className="text-lg">&#x1F50D;</span>
          <h3 className="text-sm font-semibold tracking-wide text-slate-200">
            Evidence Board
            {companyName && (
              <span className="ml-2 text-xs font-normal text-slate-400">- {companyName}</span>
            )}
          </h3>
        </div>

        {/* SVG Canvas */}
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          className="w-full"
          style={{ maxHeight: 520 }}
          preserveAspectRatio="xMidYMid meet"
        >
          {/* ── Category edges (dashed) ──────────── */}
          {edges.map((edge, i) => (
            <motion.line
              key={`edge-${i}`}
              x1={edge.from.x}
              y1={edge.from.y}
              x2={edge.to.x}
              y2={edge.to.y}
              stroke={CATEGORY_COLORS[edge.from.entity.categoryCode]?.color ?? '#475569'}
              strokeWidth={1}
              strokeDasharray="6 4"
              strokeOpacity={0.35}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 + i * 0.05 }}
            />
          ))}

          {/* ── Event-to-Entity connector lines ─── */}
          {eventPositions.map((ep) => {
            const entPos = ep.event.entityId ? entityPosMap.get(ep.event.entityId) : null;
            if (!entPos) return null;
            const isHighlighted =
              highlightedEventIds?.has(ep.event.id) || highlightedEntityIds?.has(ep.event.entityId!);
            return (
              <line
                key={`conn-${ep.event.id}`}
                x1={entPos.x}
                y1={entPos.y}
                x2={ep.x}
                y2={ep.y}
                stroke={SEVERITY_COLORS[ep.event.severity]?.color ?? '#64748b'}
                strokeWidth={isHighlighted ? 1.2 : 0.6}
                strokeDasharray="3 5"
                strokeOpacity={isHighlighted ? 0.6 : 0.15}
              />
            );
          })}

          {/* ── Entity Nodes ───────────────────── */}
          {nodePositions.map((np, i) => {
            const size = nodeSize(np.entity.riskScore);
            const catColor = CATEGORY_COLORS[np.entity.categoryCode]?.color ?? '#94a3b8';
            const opacity = entityOpacity(np.entity.id);
            return (
              <motion.g
                key={np.entity.id}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity }}
                transition={{ duration: 0.4, delay: 0.1 + i * 0.06, type: 'spring', stiffness: 260, damping: 20 }}
                style={{ cursor: onEntityClick ? 'pointer' : 'default', transformOrigin: `${np.x}px ${np.y}px` }}
                onClick={() => onEntityClick?.(np.entity.id)}
                onMouseEnter={() => handleEntityEnter(np.entity.id)}
                onMouseLeave={handleEntityLeave}
              >
                {/* Node rectangle */}
                <rect
                  x={np.x - size}
                  y={np.y - size * 0.55}
                  width={size * 2}
                  height={size * 1.1}
                  rx={10}
                  ry={10}
                  fill="rgba(15,23,42,0.7)"
                  stroke={catColor}
                  strokeWidth={hoveredEntityId === np.entity.id ? 2 : 1.2}
                />
                {/* Icon */}
                <text
                  x={np.x - size + 12}
                  y={np.y + 1}
                  fontSize={14}
                  dominantBaseline="middle"
                >
                  {ENTITY_ICONS[np.entity.type] ?? '\u26A0\uFE0F'}
                </text>
                {/* Name */}
                <text
                  x={np.x - size + 28}
                  y={np.y - 4}
                  fontSize={11}
                  fontWeight={600}
                  fill="#e2e8f0"
                  dominantBaseline="middle"
                >
                  {np.entity.name.length > 12 ? np.entity.name.slice(0, 11) + '..' : np.entity.name}
                </text>
                {/* Risk score badge */}
                <text
                  x={np.x - size + 28}
                  y={np.y + 12}
                  fontSize={10}
                  fill={catColor}
                  dominantBaseline="middle"
                >
                  Risk {np.entity.riskScore}
                </text>
              </motion.g>
            );
          })}

          {/* ── Divider line ───────────────────── */}
          <line
            x1={20}
            y1={GRAPH_H + 10}
            x2={SVG_W - 20}
            y2={GRAPH_H + 10}
            stroke="rgba(148,163,184,0.15)"
            strokeWidth={1}
          />

          {/* ── Timeline axis ──────────────────── */}
          <line
            x1={TIMELINE_LEFT}
            y1={TIMELINE_Y + TIMELINE_H * 0.4}
            x2={TIMELINE_RIGHT}
            y2={TIMELINE_Y + TIMELINE_H * 0.4}
            stroke="rgba(148,163,184,0.25)"
            strokeWidth={1.5}
          />

          {/* ── Timeline tick labels ───────────── */}
          {eventPositions.map((ep, i) => (
            <text
              key={`tick-${i}`}
              x={ep.x}
              y={TIMELINE_Y + TIMELINE_H * 0.4 + 18}
              fontSize={9}
              fill="#64748b"
              textAnchor="middle"
            >
              {formatDate(ep.event.publishedAt)}
            </text>
          ))}

          {/* ── Event dots ─────────────────────── */}
          {eventPositions.map((ep, i) => {
            const r = eventDotRadius(ep.event.score);
            const sevColor = SEVERITY_COLORS[ep.event.severity]?.color ?? '#64748b';
            const opacity = eventOpacity(ep.event.id);
            return (
              <motion.circle
                key={ep.event.id}
                cx={ep.x}
                cy={ep.y}
                r={r}
                fill={sevColor}
                fillOpacity={opacity * 0.85}
                stroke={sevColor}
                strokeWidth={hoveredEventId === ep.event.id ? 2.5 : 1}
                strokeOpacity={opacity}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.35, delay: 0.4 + i * 0.06, type: 'spring', stiffness: 300, damping: 18 }}
                style={{ cursor: onEventClick ? 'pointer' : 'default', transformOrigin: `${ep.x}px ${ep.y}px` }}
                onClick={() => onEventClick?.(ep.event.id)}
                onMouseEnter={() => handleEventEnter(ep.event, ep.x, ep.y)}
                onMouseLeave={handleEventLeave}
              />
            );
          })}

          {/* ── Tooltip (SVG foreignObject) ───── */}
          {tooltipEvent && (
            <foreignObject
              x={Math.min(tooltipEvent.x + 12, SVG_W - 200)}
              y={Math.max(tooltipEvent.y - 60, 0)}
              width={190}
              height={58}
              style={{ pointerEvents: 'none' }}
            >
              <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs shadow-xl backdrop-blur-md">
                <p className="truncate font-semibold text-white">{tooltipEvent.ev.title}</p>
                <p className="mt-0.5 text-slate-400">
                  {new Date(tooltipEvent.ev.publishedAt).toLocaleDateString()}{' '}
                  <span
                    className="ml-1 font-medium"
                    style={{ color: SEVERITY_COLORS[tooltipEvent.ev.severity]?.color }}
                  >
                    {tooltipEvent.ev.severity}
                  </span>
                </p>
              </div>
            </foreignObject>
          )}

          {/* ── Empty state ────────────────────── */}
          {entities.length === 0 && events.length === 0 && (
            <text
              x={SVG_W / 2}
              y={SVG_H / 2}
              textAnchor="middle"
              fontSize={13}
              fill="#64748b"
            >
              No evidence data available
            </text>
          )}
        </svg>
      </GlassCard>
    </motion.div>
  );
}
