/**
 * AIRiskNarrative - AI 관제 브리핑 카드
 *
 * 3대 개선:
 *   1. 1분 브리핑 카드: Headline + Status Bar (Δ delta) + What/Why/So What
 *   2. Enhanced Key Concerns: Impact/Probability + Trigger + Evidence + Owner/ETA
 *   3. Risk Timeline 스파크라인: 30일 이벤트 밀도 곡선 + severity 핀
 *
 * + Recommendations (3열 그리드)
 * + Data Sources 뱃지
 * + 새로고침 버튼 (헤더 우측)
 *
 * framer-motion stagger 애니메이션으로 각 섹션 순차 등장
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import type { BriefingResponse, RiskEventV2, RiskDriver } from '../types-v2';
import { riskApiV2 } from '../api-v2';
import { SEVERITY_COLORS, GRADIENTS } from '../design-tokens';
import GlassCard from '../shared/GlassCard';
import RiskBadge from '../shared/RiskBadge';

// ============================================
// Props
// ============================================

interface AIRiskNarrativeProps {
  dealId: string;
  companyName: string;
  riskScore?: number;
  riskLevel?: string;
  /** 최근 이벤트 (타임라인 스파크라인에 사용) */
  events?: RiskEventV2[];
  className?: string;
}

// ============================================
// Animation variants
// ============================================

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.1 },
  },
};

const sectionVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

const concernCardVariants = {
  hidden: { opacity: 0, x: -16 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
};

// ============================================
// Helpers
// ============================================

/** Impact severity 색상 결정 */
function getImpactSeverity(
  index: number,
  impact?: string,
): { key: string; color: string; bg: string } {
  const level = impact ?? ['CRITICAL', 'HIGH', 'MEDIUM'][index] ?? 'LOW';
  const sev = SEVERITY_COLORS[level as keyof typeof SEVERITY_COLORS];
  return sev ? { key: level, ...sev } : { key: 'LOW', ...SEVERITY_COLORS['LOW'] };
}

/** Probability 뱃지 색상 */
function getProbColor(prob?: string): { color: string; bg: string } {
  const m: Record<string, { color: string; bg: string }> = {
    CRITICAL: { color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
    HIGH: { color: '#f97316', bg: 'rgba(249,115,22,0.15)' },
    MEDIUM: { color: '#eab308', bg: 'rgba(234,179,8,0.15)' },
    LOW: { color: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
  };
  return m[prob ?? 'MEDIUM'] ?? m['MEDIUM'];
}

function getConfidenceColor(c: number): string {
  if (c >= 0.8) return 'text-green-400';
  if (c >= 0.5) return 'text-yellow-400';
  return 'text-red-400';
}

function toRiskLevel(level?: string): 'PASS' | 'WARNING' | 'CRITICAL' {
  if (level === 'CRITICAL' || level === 'WARNING' || level === 'PASS') return level;
  return 'PASS';
}

/** Δ delta 포맷 */
function fmtDelta(v?: number): { text: string; cls: string } | null {
  if (v == null) return null;
  if (v > 0) return { text: `+${v}`, cls: 'text-red-400' };
  if (v < 0) return { text: `${v}`, cls: 'text-green-400' };
  return { text: '0', cls: 'text-slate-500' };
}

/** 핵심 키워드 하이라이트 */
function highlightKeywords(text: string): React.ReactNode {
  if (!text) return null;
  const splitPat =
    /(위험|리스크|소송|법률|특허|규제|제재|배상|벌금|부채|적자|하락|급락|파산|부도|횡령|배임|분식|감사의견|상폐|불성실|제소|피소|손실|취약|심각|최고|가장 높|주의|경고|임계|CRITICAL|HIGH)/;
  const testPat =
    /^(위험|리스크|소송|법률|특허|규제|제재|배상|벌금|부채|적자|하락|급락|파산|부도|횡령|배임|분식|감사의견|상폐|불성실|제소|피소|손실|취약|심각|최고|가장 높|주의|경고|임계|CRITICAL|HIGH)$/;
  const parts = text.split(splitPat);
  return parts.map((p, i) => {
    if (!p) return null;
    if (testPat.test(p)) {
      return (
        <span key={i} className="text-purple-300 font-semibold">
          {p}
        </span>
      );
    }
    return <span key={i}>{p}</span>;
  });
}

// ============================================
// Risk Timeline Sparkline (Pure SVG)
// ============================================

function RiskTimelineSparkline({ events }: { events: RiskEventV2[] }) {
  const DAYS = 30;
  const W = 480;
  const H = 40;
  const PAD = 10;

  const { pins, areaPath, linePath, count } = useMemo(() => {
    const now = Date.now();
    const msDay = 86_400_000;
    const start = now - DAYS * msDay;

    const recent = events
      .filter((e) => {
        const t = new Date(e.publishedAt).getTime();
        return t >= start && t <= now;
      })
      .sort(
        (a, b) =>
          new Date(a.publishedAt).getTime() - new Date(b.publishedAt).getTime(),
      );

    if (recent.length === 0) {
      return { pins: [], areaPath: '', linePath: '', count: 0 };
    }

    // Event pins
    const p = recent.map((evt) => {
      const t = new Date(evt.publishedAt).getTime();
      const x = ((t - start) / (now - start)) * (W - PAD * 2) + PAD;
      const sevColor =
        SEVERITY_COLORS[evt.severity as keyof typeof SEVERITY_COLORS]?.color ??
        '#64748b';
      return { x, color: sevColor, score: evt.score };
    });

    // Density buckets
    const buckets = new Array(DAYS).fill(0) as number[];
    recent.forEach((evt) => {
      const t = new Date(evt.publishedAt).getTime();
      const idx = Math.min(DAYS - 1, Math.floor((t - start) / msDay));
      buckets[idx] += Math.abs(evt.score);
    });
    const maxB = Math.max(...buckets, 1);

    const pts = buckets.map((v, i) => ({
      x: (i / (DAYS - 1)) * (W - PAD * 2) + PAD,
      y: H - 6 - (v / maxB) * (H - 14),
    }));

    const area =
      `M${pts[0].x},${H - 6} ` +
      pts.map((pt) => `L${pt.x},${pt.y}`).join(' ') +
      ` L${pts[pts.length - 1].x},${H - 6} Z`;
    const line = pts
      .map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x},${pt.y}`)
      .join(' ');

    return { pins: p, areaPath: area, linePath: line, count: recent.length };
  }, [events]);

  if (count === 0) return null;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">
          Risk Timeline (30d)
        </span>
        <span className="text-[10px] text-slate-600 font-mono">{count}건</span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-10"
        preserveAspectRatio="none"
      >
        {/* Weekly grid */}
        {[7, 14, 21].map((d) => {
          const x = (d / DAYS) * (W - PAD * 2) + PAD;
          return (
            <line
              key={d}
              x1={x}
              y1={2}
              x2={x}
              y2={H - 2}
              stroke="rgba(148,163,184,0.08)"
              strokeWidth="1"
            />
          );
        })}
        {/* Baseline */}
        <line
          x1={PAD}
          y1={H - 6}
          x2={W - PAD}
          y2={H - 6}
          stroke="rgba(148,163,184,0.15)"
          strokeWidth="0.5"
        />
        {/* Density area */}
        <path d={areaPath} fill="url(#sparkGrad)" opacity="0.3" />
        {/* Density line */}
        <path
          d={linePath}
          fill="none"
          stroke="rgba(168,85,247,0.6)"
          strokeWidth="1.5"
        />
        {/* Event pins */}
        {pins.map((pin, i) => (
          <g key={i}>
            <line
              x1={pin.x}
              y1={H - 6}
              x2={pin.x}
              y2={H - 12}
              stroke={pin.color}
              strokeWidth="1"
              opacity="0.5"
            />
            <circle
              cx={pin.x}
              cy={H - 13}
              r="2.5"
              fill={pin.color}
              opacity="0.9"
            />
          </g>
        ))}
        {/* Today marker */}
        <line
          x1={W - PAD}
          y1={2}
          x2={W - PAD}
          y2={H - 2}
          stroke="rgba(239,68,68,0.4)"
          strokeWidth="1"
          strokeDasharray="2,2"
        />
        <text
          x={W - PAD - 2}
          y={8}
          textAnchor="end"
          fill="rgba(239,68,68,0.5)"
          fontSize="6"
          fontFamily="monospace"
        >
          today
        </text>
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgb(168,85,247)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="rgb(168,85,247)" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

// ============================================
// Skeleton
// ============================================

function NarrativeSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <div className="w-6 h-6 rounded bg-purple-500/20 animate-pulse" />
        <div className="h-5 w-48 rounded bg-slate-700/50 animate-pulse" />
      </div>
      {/* Briefing card skeleton */}
      <div className="rounded-xl bg-slate-800/30 p-4 space-y-3">
        <div className="h-6 w-3/4 rounded bg-slate-700/40 animate-pulse" />
        <div className="h-3 w-full rounded bg-slate-700/30 animate-pulse" />
        <div className="flex gap-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-8 w-24 rounded bg-slate-700/30 animate-pulse"
            />
          ))}
        </div>
      </div>
      {/* Concerns skeleton */}
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-28 rounded-xl bg-slate-800/40 animate-pulse"
          />
        ))}
      </div>
      {/* Timeline skeleton */}
      <div className="h-10 w-full rounded bg-slate-800/30 animate-pulse" />
      {/* Recommendations skeleton */}
      <div className="grid grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-24 rounded-xl bg-slate-800/40 animate-pulse"
          />
        ))}
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export default function AIRiskNarrative({
  dealId,
  companyName,
  riskScore,
  riskLevel,
  events = [],
  className = '',
}: AIRiskNarrativeProps) {
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [drivers, setDrivers] = useState<RiskDriver[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ---- Fetch with AbortSignal to cancel on Strict Mode re-fire ----
  const abortRef = useRef<AbortController | null>(null);

  const loadData = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const [bRes, dRes] = await Promise.all([
          riskApiV2.fetchBriefing(dealId, signal),
          riskApiV2.fetchRiskDrivers(dealId, signal).catch(() => null),
        ]);
        if (signal?.aborted) return;
        if (bRes.success && bRes.data) {
          setBriefing(bRes.data);
        } else if (bRes.error !== 'aborted') {
          setError(bRes.error || '브리핑 데이터를 불러올 수 없습니다.');
        }
        if (dRes && 'success' in dRes && dRes.success && (dRes as any).data) {
          setDrivers((dRes as any).data.topDrivers?.slice(0, 3) ?? []);
        }
      } catch (err) {
        if (signal?.aborted) return;
        setError(
          err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.',
        );
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [dealId],
  );

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    loadData(ac.signal);
    return () => ac.abort();
  }, [loadData]);

  // ---- Display values ----
  const displayLevel = toRiskLevel(briefing?.riskLevel ?? riskLevel);
  const displayScore = briefing?.riskScore ?? riskScore ?? 0;
  const displayConfidence = briefing?.confidence ?? 0;
  const confidencePct = Math.round(displayConfidence * 100);

  // ---- 1분 브리핑 데이터 ----
  const headline = useMemo(() => {
    if (briefing?.headline) return briefing.headline;
    const s = briefing?.executive_summary ?? '';
    return s.split(/[.。!]/)[0]?.trim() || `${companyName} 리스크 브리핑`;
  }, [briefing, companyName]);

  const delta24h = fmtDelta(briefing?.delta_24h);
  const delta7d = fmtDelta(briefing?.delta_7d);

  const whatLine = useMemo(() => {
    const s = briefing?.executive_summary ?? '';
    return s.split(/[.。!]/)[0]?.trim() || s;
  }, [briefing]);

  const whyLine = useMemo(() => {
    if (drivers.length > 0) {
      return drivers
        .map((d) => `${d.categoryName}(${d.contribution.toFixed(2)})`)
        .join(' \u00b7 ');
    }
    return briefing?.context_analysis?.timing_significance || '';
  }, [drivers, briefing]);

  const soWhatLine = useMemo(() => {
    return (
      briefing?.next_action ||
      briefing?.recommendations?.immediate_actions?.[0] ||
      ''
    );
  }, [briefing]);

  // ---- Error state ----
  if (!loading && error) {
    return (
      <GlassCard gradient="purple" className={`p-6 ${className}`}>
        <div className="relative pl-3">
          <div
            className="absolute left-0 top-0 bottom-0 w-1 rounded-full"
            style={{ background: GRADIENTS.purple }}
          />
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">&#10024;</span>
            <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">
              AI Risk Intelligence
            </h3>
          </div>
          <div className="text-sm text-red-400/80">{error}</div>
          <button
            onClick={() => { abortRef.current?.abort(); const ac = new AbortController(); abortRef.current = ac; loadData(ac.signal); }}
            className="mt-4 px-4 py-1.5 text-xs font-medium rounded-lg
                       bg-purple-500/10 text-purple-300 border border-purple-500/20
                       hover:bg-purple-500/20 transition-colors"
          >
            다시 시도
          </button>
        </div>
      </GlassCard>
    );
  }

  // ---- Loading state ----
  if (loading) {
    return (
      <GlassCard gradient="purple" className={className}>
        <div className="relative">
          <div
            className="absolute left-0 top-0 bottom-0 w-1 rounded-full"
            style={{ background: GRADIENTS.purple }}
          />
          <NarrativeSkeleton />
        </div>
      </GlassCard>
    );
  }

  const concerns = (briefing?.key_concerns ?? []).slice(0, 3);
  const recommendations = briefing?.recommendations;
  const dataSources = briefing?.dataSources;

  return (
    <GlassCard gradient="purple" className={`relative ${className}`}>
      {/* Left gradient stripe */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 rounded-l-2xl"
        style={{ background: GRADIENTS.purple }}
      />

      <motion.div
        className="p-6 pl-5 space-y-6"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* ===== Header + Refresh ===== */}
        <motion.div
          variants={sectionVariants}
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">&#10024;</span>
            <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">
              AI Risk Intelligence
            </h3>
          </div>
          <button
            onClick={() => { abortRef.current?.abort(); const ac = new AbortController(); abortRef.current = ac; loadData(ac.signal); }}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1 text-[10px] font-medium rounded-lg
                       bg-purple-500/10 text-purple-400 border border-purple-500/20
                       hover:bg-purple-500/20 transition-all active:scale-95"
          >
            <motion.span
              animate={loading ? { rotate: 360 } : { rotate: 0 }}
              transition={
                loading
                  ? { repeat: Infinity, duration: 1, ease: 'linear' }
                  : {}
              }
              className="inline-block text-xs"
            >
              &#8635;
            </motion.span>
            새로고침
          </button>
        </motion.div>

        {/* ===== Section 1: 1분 브리핑 카드 ===== */}
        <motion.div variants={sectionVariants}>
          <div className="rounded-xl border border-white/5 bg-slate-800/30 backdrop-blur-sm p-4 space-y-3">
            {/* Headline */}
            <h4 className="text-base font-bold text-white leading-snug">
              {highlightKeywords(headline)}
            </h4>

            {/* Status bar: LEVEL SCORE | Δ deltas | Confidence */}
            <div className="flex items-center gap-3 flex-wrap text-xs font-mono">
              <RiskBadge level={displayLevel} size="sm" animated />
              <span className="text-slate-300 font-bold">{displayScore}</span>

              {(delta24h || delta7d) && (
                <span className="text-slate-600">|</span>
              )}
              {delta24h && (
                <span className="text-slate-400">
                  &#916;24h{' '}
                  <span className={delta24h.cls}>{delta24h.text}</span>
                </span>
              )}
              {delta7d && (
                <span className="text-slate-400">
                  / 7d <span className={delta7d.cls}>{delta7d.text}</span>
                </span>
              )}

              <span className="text-slate-600">|</span>
              <span className="text-slate-400">
                Confidence{' '}
                <span className={getConfidenceColor(displayConfidence)}>
                  {confidencePct}%
                </span>
              </span>
            </div>

            {/* What / Why / So What */}
            <div className="space-y-1.5 pt-2 border-t border-white/5">
              {whatLine && (
                <div className="flex items-start gap-2">
                  <span className="text-[10px] text-purple-400 font-bold uppercase mt-0.5 w-12 flex-shrink-0">
                    What
                  </span>
                  <span className="text-sm text-slate-300 leading-relaxed">
                    {highlightKeywords(whatLine)}
                  </span>
                </div>
              )}
              {whyLine && (
                <div className="flex items-start gap-2">
                  <span className="text-[10px] text-orange-400 font-bold uppercase mt-0.5 w-12 flex-shrink-0">
                    Why
                  </span>
                  <span className="text-sm text-slate-300 leading-relaxed">
                    {whyLine}
                  </span>
                </div>
              )}
              {soWhatLine && (
                <div className="flex items-start gap-2">
                  <span className="text-[10px] text-cyan-400 font-bold uppercase mt-0.5 w-12 flex-shrink-0">
                    So What
                  </span>
                  <span className="text-sm text-slate-300 leading-relaxed">
                    {highlightKeywords(soWhatLine)}
                  </span>
                </div>
              )}
            </div>

            {/* Drivers line */}
            {drivers.length > 0 && (
              <div className="flex items-center gap-2 pt-1">
                <span className="text-[10px] text-slate-500 font-medium">
                  Drivers:
                </span>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {drivers.map((d, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                                 bg-slate-700/40 text-[10px] text-slate-300"
                    >
                      <span>{d.categoryIcon}</span>
                      <span>{d.categoryName}</span>
                      <span className="text-purple-400 font-mono font-bold">
                        {d.contribution.toFixed(2)}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>

        {/* ===== Section 2: Enhanced Key Concerns ===== */}
        {concerns.length > 0 && (
          <motion.div variants={sectionVariants} className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Key Concerns
            </h4>
            <div className="space-y-2">
              {concerns.map((concern, idx) => {
                const impactLvl =
                  concern.impact ??
                  (['CRITICAL', 'HIGH', 'MEDIUM'][idx] || 'MEDIUM');
                const probLvl =
                  concern.probability ??
                  (['HIGH', 'MEDIUM', 'MEDIUM'][idx] || 'MEDIUM');
                const sev = getImpactSeverity(idx, concern.impact);
                const prob = getProbColor(probLvl);

                return (
                  <motion.div
                    key={idx}
                    variants={concernCardVariants}
                    className="relative rounded-xl border border-white/5 bg-slate-800/30
                               backdrop-blur-sm p-4 pl-5 overflow-hidden"
                  >
                    {/* Left severity border */}
                    <div
                      className="absolute left-0 top-0 bottom-0 w-[3px]"
                      style={{ backgroundColor: sev.color }}
                    />

                    {/* Row 1: Issue + Impact/Probability badges */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-start gap-2 flex-1">
                        <span className="text-sm flex-shrink-0">
                          &#9888;&#65039;
                        </span>
                        <span className="text-sm font-semibold text-slate-200 leading-snug">
                          {concern.issue}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span
                          className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
                          style={{
                            color: sev.color,
                            backgroundColor: sev.bg,
                          }}
                        >
                          Impact {impactLvl}
                        </span>
                        <span
                          className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
                          style={{
                            color: prob.color,
                            backgroundColor: prob.bg,
                          }}
                        >
                          Prob {probLvl}
                        </span>
                      </div>
                    </div>

                    {/* Row 2: Why + Trigger */}
                    <div className="ml-6 space-y-1.5">
                      <p className="text-xs text-slate-400">
                        <span className="text-slate-500 font-medium">
                          why:
                        </span>{' '}
                        {concern.why_it_matters}
                      </p>
                      <p className="text-xs text-slate-400">
                        <span className="text-amber-500/70 font-medium">
                          trigger:
                        </span>{' '}
                        {concern.trigger || concern.watch_for}
                      </p>
                    </div>

                    {/* Row 3: Evidence + Owner/ETA */}
                    <div className="flex items-center justify-between mt-2.5 ml-6">
                      <span className="inline-flex items-center gap-1 text-[10px] text-slate-500">
                        &#128206; 근거{' '}
                        {concern.evidence_count ?? '\u2014'}건
                      </span>
                      <div className="flex items-center gap-2 text-[10px]">
                        {concern.owner || concern.eta ? (
                          <>
                            {concern.owner && (
                              <span className="text-slate-500">
                                &#128100; {concern.owner}
                              </span>
                            )}
                            {concern.eta && (
                              <span className="text-slate-500">
                                &#128197; {concern.eta}
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-slate-600 italic">
                            미지정
                          </span>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* ===== Section 3: Risk Timeline Sparkline ===== */}
        {events.length > 0 && (
          <motion.div variants={sectionVariants}>
            <RiskTimelineSparkline events={events} />
          </motion.div>
        )}

        {/* ===== Section 4: Recommendations (3-col grid) ===== */}
        {recommendations && (
          <motion.div variants={sectionVariants} className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Recommendations
            </h4>
            <div className="grid grid-cols-3 gap-3">
              <RecommendationColumn
                title="즉시 조치"
                icon="&#128680;"
                items={recommendations.immediate_actions}
                accentColor="#ef4444"
              />
              <RecommendationColumn
                title="모니터링"
                icon="&#128065;"
                items={recommendations.monitoring_focus}
                accentColor="#f59e0b"
              />
              <RecommendationColumn
                title="실사 포인트"
                icon="&#128269;"
                items={recommendations.due_diligence_points}
                accentColor="#8b5cf6"
              />
            </div>
          </motion.div>
        )}

        {/* ===== Section 5: Data Sources + Confidence ===== */}
        <motion.div variants={sectionVariants}>
          <div className="flex flex-wrap items-center gap-2">
            {dataSources ? (
              <>
                <SourceBadge
                  icon="&#128240;"
                  label="뉴스"
                  count={dataSources.newsCount}
                />
                <SourceBadge
                  icon="&#128203;"
                  label="공시"
                  count={dataSources.disclosureCount}
                />
                <SourceBadge
                  icon="&#127970;"
                  label="관련기업"
                  count={dataSources.relatedCompanyCount}
                />
                <SourceBadge
                  icon="&#128202;"
                  label="카테고리"
                  count={dataSources.categoryCount}
                />
              </>
            ) : (
              <span className="text-xs text-slate-500">소스 정보 없음</span>
            )}
            <span
              className={`ml-auto text-[10px] font-mono ${getConfidenceColor(displayConfidence)}`}
            >
              신뢰도 {confidencePct}%
            </span>
          </div>
        </motion.div>
      </motion.div>
    </GlassCard>
  );
}

// ============================================
// Sub: RecommendationColumn
// ============================================

interface RecommendationColumnProps {
  title: string;
  icon: string;
  items: string[];
  accentColor: string;
}

function RecommendationColumn({
  title,
  icon,
  items,
  accentColor,
}: RecommendationColumnProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-slate-800/20 p-3 space-y-2">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-xs">{icon}</span>
        <span
          className="text-[11px] font-bold uppercase tracking-wider"
          style={{ color: accentColor }}
        >
          {title}
        </span>
      </div>
      {items.length > 0 ? (
        <ul className="space-y-1.5">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-1.5 text-xs text-slate-300 leading-relaxed"
            >
              <span
                className="mt-1.5 w-1 h-1 rounded-full flex-shrink-0"
                style={{ backgroundColor: accentColor }}
              />
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[10px] text-slate-600 italic">항목 없음</p>
      )}
    </div>
  );
}

// ============================================
// Sub: SourceBadge
// ============================================

interface SourceBadgeProps {
  icon: string;
  label: string;
  count: number;
}

function SourceBadge({ icon, label, count }: SourceBadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
                    bg-slate-800/50 border border-white/5 text-xs text-slate-300"
    >
      <span>{icon}</span>
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-semibold text-slate-200">{count}건</span>
    </span>
  );
}
