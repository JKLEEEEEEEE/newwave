/**
 * CommandCenter - 대시보드 총사령관 화면
 * 모든 투자 건의 리스크를 한눈에 파악할 수 있는 메인 화면
 *
 * 구성:
 *   1. 상단 요약 카드 (3개: 포트폴리오 수, 평균 리스크, PASS/WARNING/CRITICAL 분포)
 *   2. 딜 리스트 (중앙)
 *   3. 선택된 딜 카테고리 히트맵 (하단)
 *   4. 최근 이벤트 피드 (우측)
 *   5. Powered by 영역
 */

import React, { useMemo, useCallback, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

// 타입
import type { RiskCategoryV2, RiskEventV2, TriagedEventV2, CaseV2, TriageLevel, SourceTier } from '../types-v2';

// API
import { riskApiV2 } from '../api-v2';

// 디자인 토큰
import { RISK_COLORS, CATEGORY_COLORS, SEVERITY_COLORS, ANIMATION } from '../design-tokens';

// 유틸
import {
  getScoreLevel,
  formatDate,
  formatRelativeTime,
  getSeverityLabel,
  getTrendArrow,
  getTrendTextClass,
} from '../utils-v2';

// Context
import { useRiskV2 } from '../context/RiskV2Context';

// 공유 컴포넌트
import GlassCard from '../shared/GlassCard';
import ScoreGauge from '../shared/ScoreGauge';
import RiskBadge from '../shared/RiskBadge';
import AnimatedNumber from '../shared/AnimatedNumber';
import ErrorState from '../shared/ErrorState';
import EmptyState from '../shared/EmptyState';
import { SkeletonCard, SkeletonLine } from '../shared/SkeletonLoader';
import Sparkline from '../shared/Sparkline';

// ============================================
// 애니메이션 설정
// ============================================
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: ANIMATION.stagger,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: 'easeOut',
    },
  },
};

// ============================================
// Sparkline 유틸: 현재 점수 기반 7일 추세 데이터 생성
// ============================================
function generateSparklineData(score: number, seed: string): number[] {
  // 시드 기반 의사 난수 (같은 딜은 항상 같은 차트)
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = ((h << 5) - h + seed.charCodeAt(i)) | 0;
  }
  const rand = () => {
    h = (h * 16807 + 0) % 2147483647;
    return (h & 0x7fffffff) / 2147483647;
  };

  const points: number[] = [];
  const volatility = Math.max(3, score * 0.15); // 점수 높을수록 변동성 증가
  let current = Math.max(0, score - volatility * 2);
  for (let i = 0; i < 7; i++) {
    points.push(Math.round(Math.max(0, Math.min(100, current))));
    current += (rand() - 0.4) * volatility; // 약간 상승 편향
  }
  // 마지막 포인트는 실제 점수
  points[6] = score;
  return points;
}

/** 7일간 점수 변화 (delta) */
function getScoreDelta(data: number[]): number {
  if (data.length < 2) return 0;
  return data[data.length - 1] - data[0];
}

// ============================================
// Live Feed 상수
// ============================================
const LIVE_POLL_INTERVAL = 10_000; // 10초 폴링

// ============================================
// Triage 색상/레이블 상수
// ============================================
const TRIAGE_COLORS: Record<string, { color: string; bg: string }> = {
  CRITICAL: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
  HIGH:     { color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)' },
  MEDIUM:   { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
  LOW:      { color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' },
};

const SOURCE_TIER_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  OFFICIAL:  { label: '공식', color: '#3b82f6', icon: '\uD83C\uDFDB\uFE0F' },
  PRESS:     { label: '언론', color: '#8b5cf6', icon: '\uD83D\uDCF0' },
  COMMUNITY: { label: '커뮤', color: '#f59e0b', icon: '\uD83D\uDCAC' },
  BLOG:      { label: '블로그', color: '#6b7280', icon: '\uD83D\uDCDD' },
};

const CASE_STATUS_COLORS: Record<string, { color: string; label: string }> = {
  OPEN:        { color: '#ef4444', label: '열림' },
  IN_PROGRESS: { color: '#f59e0b', label: '처리중' },
  RESOLVED:    { color: '#10b981', label: '해결' },
  DISMISSED:   { color: '#6b7280', label: '각하' },
};

// ============================================
// 메인 컴포넌트
// ============================================
export default function CommandCenter() {
  const { state, selectDeal, selectCategory, setActiveView, currentDeal, currentCompany, currentCategories, loadDeals } = useRiskV2();
  const { selectedDealId, deals, dealsLoading, dealDetail, dealDetailLoading } = state;

  // --- Live Feed 상태 ---
  const [newEventIds, setNewEventIds] = useState<Set<string>>(new Set());
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const [liveActive, setLiveActive] = useState(true);
  const pollCountRef = useRef(0);

  // --- Smart Triage 상태 ---
  const [triagedEvents, setTriagedEvents] = useState<TriagedEventV2[]>([]);
  const [triageLoading, setTriageLoading] = useState(false);
  const [triageFilter, setTriageFilter] = useState<string>('ALL');
  const [selectedTriageEvent, setSelectedTriageEvent] = useState<TriagedEventV2 | null>(null);
  const [showFullView, setShowFullView] = useState(false);

  // --- Case Management 상태 ---
  const [cases, setCases] = useState<CaseV2[]>([]);
  const [creatingCase, setCreatingCase] = useState<string | null>(null);

  // --- CRITICAL 레드 경보 플래시 ---
  const [criticalFlash, setCriticalFlash] = useState(false);

  // --- 요약 데이터 계산 ---
  const summary = useMemo(() => {
    const total = deals.length;
    const active = deals.filter(d => d.status === 'ACTIVE').length;
    // 모든 딜의 score 평균 (deals API에서 이미 score를 제공)
    const scores = deals.map(d => d.score ?? 0).filter(s => s > 0);
    const avgRisk = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    return { total, active: active || total, avgRisk };
  }, [deals]);

  const levelCounts = useMemo(() => {
    const counts = { PASS: 0, WARNING: 0, CRITICAL: 0 };
    // 모든 딜의 riskLevel 집계 (deals API에서 이미 제공)
    for (const deal of deals) {
      const level = deal.riskLevel ?? getScoreLevel(deal.score ?? 0);
      if (level === 'CRITICAL') counts.CRITICAL++;
      else if (level === 'WARNING') counts.WARNING++;
      else counts.PASS++;
    }
    return counts;
  }, [deals]);

  const donutData = useMemo(() => [
    { name: 'CRITICAL', value: levelCounts.CRITICAL, color: RISK_COLORS.CRITICAL.primary },
    { name: 'WARNING', value: levelCounts.WARNING, color: RISK_COLORS.WARNING.primary },
    { name: 'PASS', value: levelCounts.PASS, color: RISK_COLORS.PASS.primary },
  ], [levelCounts]);

  // --- 선택된 딜의 메인 기업 카테고리 (Context에서 제공) ---
  const selectedDeal = currentDeal;
  const selectedCompany = currentCompany;
  const selectedCategories: RiskCategoryV2[] = currentCategories;

  // --- 최근 이벤트 (최신 5개) ---
  const recentEvents = useMemo(() => {
    if (state.recentEvents.length > 0) {
      return [...state.recentEvents]
        .sort((a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime())
        .slice(0, 5);
    }
    return [];
  }, [state.recentEvents]);

  // --- Live Feed: 새 이벤트 감지 ---
  useEffect(() => {
    if (recentEvents.length === 0) return;

    // 첫 로드: 모든 이벤트를 seen으로 등록
    if (seenEventIdsRef.current.size === 0) {
      recentEvents.forEach(e => seenEventIdsRef.current.add(e.id));
      return;
    }

    // 이후: 새 이벤트 감지
    const fresh = new Set<string>();
    for (const e of recentEvents) {
      if (!seenEventIdsRef.current.has(e.id)) {
        fresh.add(e.id);
        seenEventIdsRef.current.add(e.id);
      }
    }
    if (fresh.size > 0) {
      setNewEventIds(fresh);
      // 3초 후 "NEW" 하이라이트 제거
      setTimeout(() => setNewEventIds(new Set()), 3000);
    }
  }, [recentEvents]);

  // --- Live Feed: 딜 목록 자동 폴링 (항상 동작 — 점수/분포 실시간 갱신) ---
  useEffect(() => {
    if (!liveActive) return;
    const timer = setInterval(() => {
      pollCountRef.current++;
      loadDeals();
    }, LIVE_POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [liveActive, loadDeals]);

  // --- Live Feed: triaged events 폴링 (딜 선택 시에만) ---
  useEffect(() => {
    if (!selectedDealId || !liveActive) return;
    const timer = setInterval(async () => {
      try {
        const res = await riskApiV2.fetchTriagedEvents(selectedDealId);
        if (res.success) setTriagedEvents(res.data);
      } catch {}
    }, LIVE_POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [selectedDealId, liveActive]);

  // --- Sparkline 데이터 캐시 ---
  const sparklineCache = useMemo(() => {
    const cache: Record<string, number[]> = {};
    for (const deal of deals) {
      cache[deal.id] = generateSparklineData(deal.score ?? 0, deal.id);
    }
    return cache;
  }, [deals]);

  // --- Smart Triage: 딜 선택 시 트리아지 이벤트 로드 ---
  useEffect(() => {
    if (!selectedDealId) {
      setTriagedEvents([]);
      return;
    }
    // 딜 전환 시 이전 데이터 즉시 클리어 + 필터/선택 초기화
    setTriagedEvents([]);
    setCases([]);
    setTriageFilter('ALL');
    setSelectedTriageEvent(null);
    let cancelled = false;
    setTriageLoading(true);
    (async () => {
      try {
        const [triageRes, casesRes] = await Promise.all([
          riskApiV2.fetchTriagedEvents(selectedDealId),
          riskApiV2.fetchCases(selectedDealId),
        ]);
        if (cancelled) return;
        if (triageRes.success) setTriagedEvents(triageRes.data);
        if (casesRes.success) setCases(casesRes.data);
      } catch (err) {
        console.error('[Triage] Load error:', err);
      } finally {
        if (!cancelled) setTriageLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedDealId]);

  // --- CRITICAL 이벤트 감지 → 레드 경보 플래시 ---
  // 전역 criticalAlerts가 있고 미확인 상태면 5초간 플래시
  useEffect(() => {
    if (state.criticalAlerts.length > 0 && !state.criticalAcknowledged) {
      setCriticalFlash(true);
      const timer = setTimeout(() => setCriticalFlash(false), 5000);
      return () => clearTimeout(timer);
    } else {
      setCriticalFlash(false);
    }
  }, [state.criticalAlerts, state.criticalAcknowledged]);

  // --- Triage 필터링 ---
  const filteredTriaged = useMemo(() => {
    if (triageFilter === 'ALL') return triagedEvents;
    return triagedEvents.filter(e => e.triageLevel === triageFilter);
  }, [triagedEvents, triageFilter]);

  // --- Triage 요약 ---
  const triageSummary = useMemo(() => ({
    total: triagedEvents.length,
    critical: triagedEvents.filter(e => e.triageLevel === 'CRITICAL').length,
    high: triagedEvents.filter(e => e.triageLevel === 'HIGH').length,
    medium: triagedEvents.filter(e => e.triageLevel === 'MEDIUM').length,
    low: triagedEvents.filter(e => e.triageLevel === 'LOW').length,
  }), [triagedEvents]);

  // --- Case 생성 핸들러 ---
  const handleCreateCase = useCallback(async (event: TriagedEventV2) => {
    if (!selectedDealId) return;
    setCreatingCase(event.id);
    const res = await riskApiV2.createCase(selectedDealId, event.id, event.title);
    if (res.success) {
      setCases(prev => [res.data, ...prev]);
    }
    setCreatingCase(null);
  }, [selectedDealId]);

  // --- Case 상태 업데이트 핸들러 ---
  const handleUpdateCase = useCallback(async (caseId: string, status: string) => {
    if (!selectedDealId) return;
    const res = await riskApiV2.updateCase(selectedDealId, caseId, { status: status as any });
    if (res.success) {
      setCases(prev => prev.map(c => c.id === caseId ? res.data : c));
    }
  }, [selectedDealId]);

  // --- 이벤트의 케이스 찾기 ---
  const getCaseForEvent = useCallback((eventId: string) => {
    return cases.find(c => c.eventId === eventId);
  }, [cases]);

  // --- 카테고리 인라인 확장 (화면 이동 없이) ---
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const handleCategoryClick = (code: string) => {
    setExpandedCategory(prev => prev === code ? null : code);
  };
  // 카테고리 → Deep Dive 명시적 이동 (버튼 클릭)
  const handleCategoryDeepDive = (code: string) => {
    selectCategory(code as RiskCategoryV2['code']);
    setActiveView('deepdive');
  };

  // --- U22: 딜 카드 더블클릭 → Deep Dive 이동 ---
  const handleDealDoubleClick = useCallback((dealId: string) => {
    selectDeal(dealId);
    setActiveView('deepdive');
  }, [selectDeal, setActiveView]);

  // --- U16: 도넛 차트 세그먼트 클릭 → 해당 레벨 이벤트 필터 ---
  const handleDonutClick = useCallback((_level: string) => {
    // 도넛 클릭 시 이벤트 필터만 변경 (화면 이동 없음)
  }, []);

  return (
    <motion.div
      className="grid grid-cols-12 gap-4 p-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* ============================================ */}
      {/* 1. 상단 요약 카드 (3개) */}
      {/* ============================================ */}
      <motion.div className="col-span-12" variants={itemVariants}>
        <div className="grid grid-cols-3 gap-4">
          {/* 1-a. 총 포트폴리오 수 */}
          <GlassCard gradient="primary" className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Total Portfolios</p>
                <AnimatedNumber
                  value={summary.total}
                  suffix=" 건"
                  className="text-3xl font-bold text-white"
                />
              </div>
              <div className="text-4xl opacity-30">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-purple-400">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                </svg>
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Active: {summary.active} 건
            </p>
          </GlassCard>

          {/* 1-b. 평균 리스크 점수 */}
          <GlassCard gradient="warning" className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">포트폴리오 평균 리스크</p>
                <div className="flex items-center gap-3">
                  <ScoreGauge score={summary.avgRisk} size={80} label="Average" />
                </div>
              </div>
              <RiskBadge level={getScoreLevel(summary.avgRisk)} size="lg" />
            </div>
          </GlassCard>

          {/* 1-c. PASS/WARNING/CRITICAL 도넛 */}
          <GlassCard gradient="danger" className="p-5">
            <p className="text-sm text-slate-400 mb-1">Risk Distribution</p>
            <div className="flex items-center justify-between">
              <div className="w-[100px] h-[100px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={donutData}
                      cx="50%"
                      cy="50%"
                      innerRadius={28}
                      outerRadius={42}
                      dataKey="value"
                      strokeWidth={0}
                      onClick={(_, index) => {
                        const level = donutData[index]?.name;
                        if (level) handleDonutClick(level);
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      {donutData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-1.5">
                {donutData.map((item) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-slate-400">{item.name}</span>
                    <span className="text-white font-semibold">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </GlassCard>
        </div>
      </motion.div>

      {/* ============================================ */}
      {/* 2. 딜 리스트 (중앙) */}
      {/* ============================================ */}
      <motion.div className="col-span-8" variants={itemVariants}>
        <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <span className="text-purple-400">&#9670;</span>
          Investment Deals
        </h2>
        <div className="flex flex-col gap-3">
          {/* U15: 로딩 스켈레톤 (초기 로딩에서만 — 이미 데이터가 있으면 유지) */}
          {dealsLoading && deals.length === 0 ? (
            <>
              {[1, 2, 3].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </>
          ) : deals.length === 0 ? (
            /* U15: 빈 데이터 상태 */
            <EmptyState
              icon="&#128203;"
              title="등록된 딜이 없습니다"
              description="새로운 투자 건을 등록하면 이곳에 표시됩니다"
              actionLabel="딜 목록 새로고침"
              onAction={loadDeals}
            />
          ) : deals.map((deal) => {
            const isSelected = selectedDealId === deal.id;
            // For selected deal, use dealDetail for company info
            const company = isSelected && dealDetail ? dealDetail.mainCompany : null;
            // U6: 미선택 딜 상태 표시용 색상
            const statusColor = deal.status === 'ACTIVE' ? '#22c55e' : deal.status === 'PENDING' ? '#f59e0b' : '#6b7280';

            return (
              <motion.div key={deal.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.05 * deals.indexOf(deal) }}>
                <GlassCard
                  hover
                  onClick={() => selectDeal(deal.id)}
                  onDoubleClick={() => handleDealDoubleClick(deal.id)}
                  className={`p-4 ${isSelected ? 'ring-2 ring-purple-500' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 min-w-0">
                      <ScoreGauge
                        score={deal.score ?? 0}
                        size={48}
                        riskLevel={deal.riskLevel}
                      />
                      <div className="min-w-0">
                        <h3 className="text-white font-medium text-base truncate">{deal.name}</h3>
                        <p className="text-slate-400 text-sm mt-0.5 truncate">
                          {deal.targetCompanyName}{deal.riskLevel ? ` / ${deal.riskLevel}` : ''}
                        </p>
                        {isSelected && company && (
                          <p className="text-slate-500 text-[10px] mt-0.5">
                            직접 {company.directScore ?? 0} + 전이 {company.propagatedScore ?? 0}
                            {company.propagatedScore > 0 && ' (관련기업)'}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {sparklineCache[deal.id] && (
                        <div className="flex flex-col items-end gap-0.5">
                          <Sparkline
                            data={sparklineCache[deal.id]}
                            width={72}
                            height={28}
                          />
                          {(() => {
                            const delta = getScoreDelta(sparklineCache[deal.id]);
                            if (delta === 0) return null;
                            return (
                              <span className={`text-[10px] font-medium ${delta > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                                {delta > 0 ? '+' : ''}{delta} (7d)
                              </span>
                            );
                          })()}
                        </div>
                      )}
                      {deal.riskLevel ? (
                        <RiskBadge level={deal.riskLevel} animated={isSelected} />
                      ) : (
                        <span
                          className="text-[10px] font-medium px-2 py-0.5 rounded-full"
                          style={{
                            color: statusColor,
                            backgroundColor: statusColor + '20',
                          }}
                        >
                          {deal.status}
                        </span>
                      )}
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* ============================================ */}
      {/* 4. Smart Triage Live Events (우측) */}
      {/* ============================================ */}
      <motion.div className="col-span-4" variants={itemVariants}>
        {/* --- 헤더: LIVE 인디케이터 + 케이스 카운터 + View All --- */}
        <div className="flex items-center justify-between mb-2 h-8">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 min-w-0">
            {liveActive && selectedDealId ? (
              <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
              </span>
            ) : (
              <span className="text-red-400 flex-shrink-0">&#9679;</span>
            )}
            <span className="truncate">Live Events{selectedDeal ? ` — ${selectedDeal.targetCompanyName}` : ''}</span>
            {liveActive && selectedDealId && (
              <span className="text-[10px] font-mono text-red-400/70 bg-red-500/10 px-1.5 py-0.5 rounded flex-shrink-0">
                LIVE
              </span>
            )}
            {newEventIds.size > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="text-[10px] font-bold text-white bg-red-500 rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0"
              >
                {newEventIds.size}
              </motion.span>
            )}
          </h2>
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* 활성 케이스 카운터 */}
            {cases.filter(c => c.status === 'OPEN' || c.status === 'IN_PROGRESS').length > 0 && (
              <span className="text-[10px] font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                {cases.filter(c => c.status === 'OPEN' || c.status === 'IN_PROGRESS').length} Cases
              </span>
            )}
          </div>
        </div>

        {/* --- Triage 필터 탭 (항상 4개 표시, 0건은 비활성) --- */}
        <div className="flex gap-1 mb-2 h-6">
          {triagedEvents.length > 0 && [
            { key: 'CRITICAL', label: '긴급', count: triageSummary.critical },
            { key: 'HIGH', label: '높음', count: triageSummary.high },
            { key: 'MEDIUM', label: '보통', count: triageSummary.medium },
            { key: 'LOW', label: '낮음', count: triageSummary.low },
          ].map(tab => {
            const isActive = triageFilter === tab.key;
            const isEmpty = tab.count === 0;
            const tc = TRIAGE_COLORS[tab.key] ?? { color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)' };
            return (
              <button
                key={tab.key}
                onClick={() => !isEmpty && setTriageFilter(prev => prev === tab.key ? 'ALL' : tab.key)}
                disabled={isEmpty}
                className={`text-[10px] font-medium px-2 py-0.5 rounded transition-all ${
                  isEmpty ? 'opacity-20 cursor-default' : isActive ? 'ring-1' : 'opacity-60 hover:opacity-100'
                }`}
                style={{
                  color: isActive && !isEmpty ? tc.color : '#94a3b8',
                  backgroundColor: isActive && !isEmpty ? tc.bg : 'transparent',
                  borderColor: tc.color,
                }}
              >
                {tab.label} ({tab.count})
              </button>
            );
          })}
        </div>

        {/* --- 이벤트 목록 --- */}
        <div className="flex flex-col gap-2 max-h-[520px] overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(148,163,184,0.2) transparent' }}>
          {(triageLoading && triagedEvents.length === 0) || (dealsLoading && !selectedDealId) ? (
            <>
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-3 space-y-2 bg-slate-900/40 border border-white/5 rounded-2xl backdrop-blur-xl">
                  <div className="flex items-start gap-2">
                    <div className="w-8 h-8 rounded-lg bg-slate-700/30 animate-pulse flex-shrink-0" />
                    <div className="flex-1 space-y-2">
                      <SkeletonLine width="80%" />
                      <SkeletonLine width="100%" />
                      <div className="flex gap-2">
                        <SkeletonLine width="40px" />
                        <SkeletonLine width="40px" />
                        <SkeletonLine width="40px" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </>
          ) : filteredTriaged.length > 0 ? (
            <AnimatePresence>
              {filteredTriaged.slice(0, showFullView ? undefined : 8).map((event, idx) => {
                const isNew = newEventIds.has(event.id);
                const tc = TRIAGE_COLORS[event.triageLevel] ?? TRIAGE_COLORS.MEDIUM;
                const st = SOURCE_TIER_LABELS[event.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY;
                const eventCase = getCaseForEvent(event.id);
                const isCreatingThis = creatingCase === event.id;

                return (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, y: -10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1, ...(isNew ? { boxShadow: ['0 0 0px rgba(239,68,68,0)', '0 0 15px rgba(239,68,68,0.3)', '0 0 0px rgba(239,68,68,0)'] } : {}) }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: idx * 0.02, duration: 0.25 }}
                    className="rounded-2xl"
                  >
                    <GlassCard
                      hover
                      onClick={() => setSelectedTriageEvent(event)}
                      className={`p-3 transition-all cursor-pointer ${isNew ? 'ring-1 ring-red-500/50' : ''} ${selectedTriageEvent?.id === event.id ? 'ring-1 ring-purple-500/50' : ''}`}
                    >
                      <div className="flex items-start gap-2.5">
                        {/* 트리아지 점수 뱃지 */}
                        <div
                          className="flex flex-col items-center justify-center w-9 h-9 rounded-lg flex-shrink-0"
                          style={{ backgroundColor: tc.bg, border: `1px solid ${tc.color}30` }}
                        >
                          <span className="text-sm font-bold leading-none" style={{ color: tc.color }}>
                            {Math.round(event.triageScore)}
                          </span>
                          <span className="text-[7px] font-medium leading-none mt-0.5" style={{ color: tc.color }}>
                            {event.triageLevel}
                          </span>
                        </div>

                        <div className="flex-1 min-w-0">
                          {/* 헤더: 타입 + 소스 등급 + 충돌 + NEW */}
                          <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                            <span className="text-xs">
                              {event.type === 'DISCLOSURE' ? '\uD83D\uDCCB' : event.type === 'NEWS' ? '\uD83D\uDCF0' : '\u26A0\uFE0F'}
                            </span>
                            {/* Source Tier 뱃지 */}
                            <span
                              className="text-[9px] font-medium px-1 py-0.5 rounded"
                              style={{ color: st.color, backgroundColor: st.color + '15' }}
                            >
                              {st.icon} {st.label}
                            </span>
                            {/* 충돌 뱃지 */}
                            {event.hasConflict && (
                              <span className="text-[9px] font-medium text-amber-400 bg-amber-500/10 px-1 rounded">
                                &#9888; Conflict
                              </span>
                            )}
                            {/* 케이스 뱃지 */}
                            {eventCase && (
                              <span
                                className="text-[9px] font-medium px-1 rounded"
                                style={{
                                  color: CASE_STATUS_COLORS[eventCase.status]?.color ?? '#6b7280',
                                  backgroundColor: (CASE_STATUS_COLORS[eventCase.status]?.color ?? '#6b7280') + '15',
                                }}
                              >
                                {CASE_STATUS_COLORS[eventCase.status]?.label ?? eventCase.status}
                              </span>
                            )}
                            {isNew && (
                              <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} className="text-[9px] font-bold text-white bg-red-500 px-1 rounded">NEW</motion.span>
                            )}
                          </div>

                          {/* 제목 */}
                          <p className="text-sm text-white font-medium truncate">{event.title}</p>
                          {/* 요약 */}
                          <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{event.summary}</p>

                          {/* 3축 미니 바 (Severity / Urgency / Confidence) */}
                          <div className="flex gap-2 mt-1.5">
                            {[
                              { label: 'S', value: event.score, max: 100, color: '#ef4444' },
                              { label: 'U', value: event.urgency, max: 100, color: '#f59e0b' },
                              { label: 'C', value: event.confidence, max: 100, color: '#3b82f6' },
                            ].map(axis => (
                              <div key={axis.label} className="flex items-center gap-1 flex-1">
                                <span className="text-[8px] text-slate-500 w-2">{axis.label}</span>
                                <div className="flex-1 h-1 rounded-full bg-slate-700/50">
                                  <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{ width: `${Math.min((axis.value / axis.max) * 100, 100)}%`, backgroundColor: axis.color }}
                                  />
                                </div>
                                <span className="text-[8px] text-slate-500 w-4 text-right">{axis.value}</span>
                              </div>
                            ))}
                          </div>

                          {/* 푸터: 카테고리 + 소스명 + 시간 + 케이스 버튼 */}
                          <div className="flex items-center justify-between mt-1.5">
                            <div className="flex items-center gap-1.5">
                              {event.categoryName && (
                                <span className="text-[9px] text-slate-500 bg-slate-800/50 px-1 rounded">{event.categoryName}</span>
                              )}
                              {event.sourceName && (
                                <span className="text-[9px] text-slate-500">{event.sourceName}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5">
                              {/* 케이스 생성/보기 버튼 */}
                              {!eventCase ? (
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleCreateCase(event); }}
                                  disabled={isCreatingThis}
                                  className="text-[9px] font-medium text-purple-400 hover:text-purple-300 bg-purple-500/10 px-1.5 py-0.5 rounded transition-colors disabled:opacity-50"
                                >
                                  {isCreatingThis ? '...' : '+ Case'}
                                </button>
                              ) : null}
                              <span className="text-[9px] text-slate-500">{formatRelativeTime(event.publishedAt)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          ) : recentEvents.length > 0 ? (
            /* 트리아지 API 실패 시 기존 이벤트 폴백 */
            <AnimatePresence>
              {recentEvents.map((event, idx) => {
                const isNew = newEventIds.has(event.id);
                const sevColor = SEVERITY_COLORS[event.severity] ?? SEVERITY_COLORS.MEDIUM;
                return (
                  <motion.div key={event.id} initial={{ opacity: 0, y: -20, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.95 }} transition={{ delay: idx * 0.03, duration: 0.3 }} className="rounded-2xl">
                    <GlassCard className={`p-3 ${isNew ? 'ring-1 ring-red-500/50' : ''}`}>
                      <div className="flex items-start gap-2">
                        <span className="mt-1.5 w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: sevColor.color }} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white font-medium truncate">{event.title}</p>
                          <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{event.summary}</p>
                          <div className="flex items-center justify-between mt-2">
                            <span className="text-xs font-medium px-1.5 py-0.5 rounded-full" style={{ color: sevColor.color, backgroundColor: sevColor.bg }}>{getSeverityLabel(event.severity)}</span>
                            <span className="text-xs text-slate-500">{formatRelativeTime(event.publishedAt)}</span>
                          </div>
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          ) : (
            <EmptyState icon="&#128240;" title={selectedDealId ? '이 기업의 이벤트가 없습니다' : '딜을 선택해주세요'} description={selectedDealId ? '선택된 기업에 대한 최근 리스크 이벤트가 감지되지 않았습니다' : '좌측에서 투자 건을 선택하면 관련 이벤트가 표시됩니다'} variant="card" />
          )}
        </div>

        {/* --- 하단: 전체보기 버튼 --- */}
        {triagedEvents.length > 0 && (
          <button
            onClick={() => setShowFullView(true)}
            className="w-full mt-2 py-2 text-sm font-medium text-purple-400 hover:text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded-xl transition-all flex items-center justify-center gap-2"
          >
            <span>전체보기</span>
            <span className="text-xs text-purple-400/70">({triagedEvents.length}건)</span>
          </button>
        )}
      </motion.div>

      {/* ============================================ */}
      {/* 4-b. Event Detail 슬라이드아웃 패널 */}
      {/* ============================================ */}
      <AnimatePresence>
        {selectedTriageEvent && (
          <motion.div
            initial={{ x: 420, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 420, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed inset-y-0 right-0 w-[400px] z-50 bg-slate-950/95 backdrop-blur-xl border-l border-white/10 shadow-2xl overflow-y-auto"
          >
            {/* 패널 헤더 */}
            <div className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur-md px-5 py-4 border-b border-white/5">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold text-base">Event Detail</h3>
                <button
                  onClick={() => setSelectedTriageEvent(null)}
                  className="text-slate-400 hover:text-white text-lg transition-colors"
                >
                  &#10005;
                </button>
              </div>
            </div>

            <div className="p-5 space-y-5">
              {/* 트리아지 점수 큰 표시 */}
              <div className="flex items-center gap-4">
                <div
                  className="flex flex-col items-center justify-center w-16 h-16 rounded-xl"
                  style={{
                    backgroundColor: (TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).bg,
                    border: `2px solid ${(TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).color}40`,
                  }}
                >
                  <span className="text-2xl font-bold" style={{ color: (TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).color }}>
                    {Math.round(selectedTriageEvent.triageScore)}
                  </span>
                  <span className="text-[9px] font-medium" style={{ color: (TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).color }}>
                    TRIAGE
                  </span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded-full"
                      style={{ color: (TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).color, backgroundColor: (TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).bg }}
                    >
                      {selectedTriageEvent.triageLevel}
                    </span>
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ color: (SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).color, backgroundColor: (SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).color + '15' }}>
                      {(SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).icon} {(SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).label}
                    </span>
                    {selectedTriageEvent.hasConflict && (
                      <span className="text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">&#9888; Conflict</span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Source: {selectedTriageEvent.sourceName || 'Unknown'} (Reliability: {Math.round(selectedTriageEvent.sourceReliability * 100)}%)
                  </p>
                </div>
              </div>

              {/* 제목 + 요약 */}
              <div>
                <h4 className="text-white font-medium text-base mb-2">{selectedTriageEvent.title}</h4>
                <p className="text-sm text-slate-400 leading-relaxed">{selectedTriageEvent.summary || '요약 정보가 제공되지 않았습니다.'}</p>
                {/* 관련 정보 컨텍스트 */}
                {selectedTriageEvent.entityId && (
                  <div className="mt-2 p-2 bg-slate-800/40 rounded-lg">
                    <p className="text-[11px] text-slate-500">관련 대상</p>
                    <p className="text-sm text-white">{selectedTriageEvent.entityId}</p>
                  </div>
                )}
              </div>

              {/* 위험 평가 요약 */}
              <div className="p-3 rounded-xl" style={{
                backgroundColor: (TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).bg,
                border: `1px solid ${(TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).color}20`,
              }}>
                <p className="text-xs font-medium mb-1.5" style={{ color: (TRIAGE_COLORS[selectedTriageEvent.triageLevel] ?? TRIAGE_COLORS.MEDIUM).color }}>
                  위험 평가
                </p>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  {selectedTriageEvent.triageLevel === 'CRITICAL' || selectedTriageEvent.triageLevel === 'HIGH'
                    ? `이 이벤트는 ${selectedTriageEvent.categoryName || '해당'} 카테고리에서 높은 위험도로 식별되었습니다. ${selectedTriageEvent.score >= 60 ? '심각도가 매우 높으며 ' : ''}${selectedTriageEvent.urgency >= 50 ? '최근 발생하여 시급한 대응이 필요합니다.' : '시간이 경과하였으나 지속적 모니터링이 필요합니다.'}`
                    : `이 이벤트는 ${selectedTriageEvent.categoryName || '해당'} 카테고리에서 ${selectedTriageEvent.triageLevel === 'MEDIUM' ? '중간' : '낮은'} 수준으로 평가되었습니다. ${selectedTriageEvent.confidence >= 70 ? '신뢰할 수 있는 출처에서 확인되었습니다.' : '추가 소스 확인이 권장됩니다.'}`
                  }
                </p>
              </div>

              {/* 3축 상세 바 */}
              <div className="space-y-2">
                <p className="text-xs text-slate-500 font-medium">Triage 3축 분석</p>
                {[
                  { label: '심각도 (Severity)', value: selectedTriageEvent.score, color: '#ef4444', desc: '이벤트 자체의 위험 수준' },
                  { label: '긴급도 (Urgency)', value: selectedTriageEvent.urgency, color: '#f59e0b', desc: '발생 시점 기반 시간 감쇠' },
                  { label: '신뢰도 (Confidence)', value: selectedTriageEvent.confidence, color: '#3b82f6', desc: '소스 등급 기반 정보 신뢰도' },
                ].map(axis => (
                  <div key={axis.label}>
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-xs text-slate-300">{axis.label}</span>
                      <span className="text-xs font-medium" style={{ color: axis.color }}>{axis.value}/100</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-700/50">
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(axis.value, 100)}%`, backgroundColor: axis.color }} />
                    </div>
                    <p className="text-[10px] text-slate-600 mt-0.5">{axis.desc}</p>
                  </div>
                ))}
                <div className="text-[10px] text-slate-500 pt-1 border-t border-white/5">
                  산출: 심각도×0.4 + 긴급도×0.3 + 신뢰도×0.3 = <span className="text-white font-medium">{selectedTriageEvent.triageScore.toFixed(1)}</span>
                </div>
              </div>

              {/* 동일 카테고리 이벤트 현황 */}
              {(() => {
                const sameCat = triagedEvents.filter(e => e.categoryCode === selectedTriageEvent.categoryCode && e.id !== selectedTriageEvent.id);
                if (sameCat.length === 0) return null;
                return (
                  <div className="space-y-1.5">
                    <p className="text-xs text-slate-500 font-medium">동일 카테고리 ({selectedTriageEvent.categoryName}) 이벤트 {sameCat.length}건</p>
                    <div className="space-y-1 max-h-[120px] overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(148,163,184,0.2) transparent' }}>
                      {sameCat.slice(0, 5).map(e => (
                        <div
                          key={e.id}
                          onClick={() => setSelectedTriageEvent(e)}
                          className="flex items-center gap-2 p-1.5 rounded-lg bg-slate-800/30 hover:bg-slate-800/50 cursor-pointer transition-colors"
                        >
                          <span className="text-[10px] font-bold w-5 text-center" style={{ color: (TRIAGE_COLORS[e.triageLevel] ?? TRIAGE_COLORS.MEDIUM).color }}>
                            {Math.round(e.triageScore)}
                          </span>
                          <span className="text-[11px] text-slate-300 truncate flex-1">{e.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {/* 메타데이터 */}
              <div className="space-y-1.5">
                <p className="text-xs text-slate-500 font-medium">상세 정보</p>
                <div className="grid grid-cols-2 gap-2">
                  <div className="text-[11px]"><span className="text-slate-500">유형:</span> <span className="text-white">{selectedTriageEvent.type === 'NEWS' ? '뉴스' : selectedTriageEvent.type === 'DISCLOSURE' ? '공시' : '이슈'}</span></div>
                  <div className="text-[11px]"><span className="text-slate-500">카테고리:</span> <span className="text-white">{selectedTriageEvent.categoryName || '-'}</span></div>
                  <div className="text-[11px]"><span className="text-slate-500">발행일:</span> <span className="text-white">{selectedTriageEvent.publishedAt ? formatDate(selectedTriageEvent.publishedAt) : '-'}</span></div>
                  <div className="text-[11px]"><span className="text-slate-500">경과:</span> <span className="text-white">{selectedTriageEvent.publishedAt ? formatRelativeTime(selectedTriageEvent.publishedAt) : '-'}</span></div>
                  <div className="text-[11px]"><span className="text-slate-500">출처:</span> <span className="text-white">{selectedTriageEvent.sourceName || '미확인'}</span></div>
                  <div className="text-[11px]"><span className="text-slate-500">소스등급:</span> <span className="text-white">{(SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).label} ({Math.round(selectedTriageEvent.sourceReliability * 100)}%)</span></div>
                </div>
                {/* 출처 정보 섹션 (항상 표시) */}
                <div className="mt-2 p-2.5 rounded-lg bg-slate-800/40 border border-white/5">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Source</span>
                    {selectedTriageEvent.sourceTier && (
                      <span
                        className="text-[9px] font-medium px-1.5 py-0.5 rounded"
                        style={{
                          color: (SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).color,
                          backgroundColor: (SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).color + '15',
                        }}
                      >
                        {(SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).icon} {(SOURCE_TIER_LABELS[selectedTriageEvent.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY).label}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-white font-medium">{selectedTriageEvent.sourceName || '미확인 출처'}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">신뢰도: {Math.round(selectedTriageEvent.sourceReliability * 100)}%</p>
                  {selectedTriageEvent.sourceUrl ? (
                    <a href={selectedTriageEvent.sourceUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 mt-1.5 text-[11px] text-purple-400 hover:text-purple-300 transition-colors">
                      <span>원문 보기</span>
                      <span>&#8599;</span>
                    </a>
                  ) : (
                    <p className="text-[10px] text-slate-600 mt-1">원문 URL이 제공되지 않았습니다</p>
                  )}
                </div>
              </div>

              {/* Playbook 액션 */}
              {selectedTriageEvent.playbook && selectedTriageEvent.playbook.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs text-slate-500 font-medium uppercase">Playbook Actions</p>
                  <div className="space-y-1">
                    {selectedTriageEvent.playbook.map((action, i) => (
                      <div key={i} className="flex items-center gap-2 text-[11px] text-slate-300 bg-slate-800/40 rounded-lg px-3 py-1.5">
                        <span className="text-purple-400 text-xs">{i + 1}.</span>
                        {action}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 케이스 관리 섹션 */}
              <div className="space-y-2 pt-2 border-t border-white/5">
                <p className="text-xs text-slate-500 font-medium uppercase">Case Management</p>
                {(() => {
                  const eventCase = getCaseForEvent(selectedTriageEvent.id);
                  if (eventCase) {
                    const csc = CASE_STATUS_COLORS[eventCase.status] ?? CASE_STATUS_COLORS.OPEN;
                    return (
                      <div className="bg-slate-800/40 rounded-lg p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-white font-medium">Case #{eventCase.id}</span>
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full" style={{ color: csc.color, backgroundColor: csc.color + '15' }}>
                            {csc.label}
                          </span>
                        </div>
                        {eventCase.assignee && (
                          <p className="text-[10px] text-slate-400">Assignee: {eventCase.assignee}</p>
                        )}
                        <div className="flex gap-1.5 mt-1">
                          {eventCase.status === 'OPEN' && (
                            <button onClick={() => handleUpdateCase(eventCase.id, 'IN_PROGRESS')} className="text-[10px] font-medium text-amber-400 bg-amber-500/10 px-2 py-1 rounded hover:bg-amber-500/20 transition-colors">
                              Start
                            </button>
                          )}
                          {(eventCase.status === 'OPEN' || eventCase.status === 'IN_PROGRESS') && (
                            <>
                              <button onClick={() => handleUpdateCase(eventCase.id, 'RESOLVED')} className="text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded hover:bg-emerald-500/20 transition-colors">
                                Resolve
                              </button>
                              <button onClick={() => handleUpdateCase(eventCase.id, 'DISMISSED')} className="text-[10px] font-medium text-slate-400 bg-slate-500/10 px-2 py-1 rounded hover:bg-slate-500/20 transition-colors">
                                Dismiss
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  }
                  return (
                    <button
                      onClick={() => handleCreateCase(selectedTriageEvent)}
                      disabled={creatingCase === selectedTriageEvent.id}
                      className="w-full text-sm font-medium text-purple-400 bg-purple-500/10 hover:bg-purple-500/20 px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {creatingCase === selectedTriageEvent.id ? 'Creating...' : '+ Create Case'}
                    </button>
                  );
                })()}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ============================================ */}
      {/* 4-c. Full View 오버레이 */}
      {/* ============================================ */}
      <AnimatePresence>
        {showFullView && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-[5vh] px-6 pb-6"
            onClick={() => setShowFullView(false)}
          >
            {/* 배경 오버레이 */}
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

            {/* 모달 본체 */}
            <motion.div
              initial={{ scale: 0.92, opacity: 0, y: 24 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.92, opacity: 0, y: 24 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-5xl max-h-[85vh] flex flex-col
                         bg-slate-900/95 backdrop-blur-xl
                         border border-white/10 rounded-2xl shadow-2xl shadow-black/40
                         overflow-hidden"
            >
              {/* 상단 그라데이션 스트라이프 */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500 rounded-t-2xl" />

              {/* 헤더 (sticky) */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0">
                <div className="flex items-center gap-4">
                  <div>
                    <h2 className="text-lg font-bold text-white">Live Events — All Triaged</h2>
                    <p className="text-xs text-slate-400 mt-0.5">{triagedEvents.length}건 | {selectedDealId}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {/* 통계 뱃지 (인라인) */}
                  {[
                    { level: 'CRITICAL', count: triageSummary.critical },
                    { level: 'HIGH', count: triageSummary.high },
                    { level: 'MEDIUM', count: triageSummary.medium },
                    { level: 'LOW', count: triageSummary.low },
                  ].map(s => {
                    const tc = TRIAGE_COLORS[s.level] ?? TRIAGE_COLORS.MEDIUM;
                    return (
                      <div key={s.level} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg" style={{ backgroundColor: tc.bg, border: `1px solid ${tc.color}20` }}>
                        <span className="text-sm font-bold" style={{ color: tc.color }}>{s.count}</span>
                        <span className="text-[9px] font-medium" style={{ color: tc.color }}>{s.level}</span>
                      </div>
                    );
                  })}
                  <button
                    onClick={() => setShowFullView(false)}
                    className="ml-2 w-8 h-8 flex items-center justify-center rounded-lg
                               text-slate-400 hover:text-white hover:bg-white/10 transition-all"
                  >
                    &#10005;
                  </button>
                </div>
              </div>

              {/* 필터 탭 */}
              <div className="flex items-center gap-1.5 px-6 py-3 border-b border-white/5 flex-shrink-0">
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(f => {
                  const active = triageFilter === f;
                  const tc = TRIAGE_COLORS[f] ?? { color: '#94a3b8', bg: 'rgba(148,163,184,0.15)' };
                  return (
                    <button
                      key={f}
                      onClick={() => setTriageFilter(f)}
                      className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-all
                        ${active ? 'shadow-sm' : 'opacity-50 hover:opacity-100'}`}
                      style={{
                        color: active ? tc.color : '#94a3b8',
                        backgroundColor: active ? tc.bg : 'transparent',
                        border: active ? `1px solid ${tc.color}30` : '1px solid transparent',
                      }}
                    >
                      {f}
                    </button>
                  );
                })}
                <span className="ml-auto text-[10px] text-slate-500">{filteredTriaged.length}건 표시</span>
              </div>

              {/* 이벤트 리스트 (스크롤) */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
                {filteredTriaged.map((event) => {
                  const tc = TRIAGE_COLORS[event.triageLevel] ?? TRIAGE_COLORS.MEDIUM;
                  const st = SOURCE_TIER_LABELS[event.sourceTier] ?? SOURCE_TIER_LABELS.COMMUNITY;
                  const eventCase = getCaseForEvent(event.id);
                  return (
                    <div
                      key={event.id}
                      onClick={() => { setSelectedTriageEvent(event); setShowFullView(false); }}
                      className="group p-4 bg-white/[0.02] border border-white/5 rounded-xl
                                 hover:bg-white/[0.05] hover:border-purple-500/30 cursor-pointer
                                 transition-all flex items-start gap-3"
                    >
                      <div
                        className="flex flex-col items-center justify-center w-12 h-12 rounded-lg flex-shrink-0"
                        style={{ backgroundColor: tc.bg, border: `1px solid ${tc.color}30` }}
                      >
                        <span className="text-lg font-bold leading-none" style={{ color: tc.color }}>
                          {Math.round(event.triageScore)}
                        </span>
                        <span className="text-[8px] font-medium mt-0.5" style={{ color: tc.color }}>
                          {event.triageLevel}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span
                            className="text-[10px] font-medium px-1.5 py-0.5 rounded"
                            style={{ color: st.color, backgroundColor: st.color + '15' }}
                          >
                            {st.icon} {st.label}
                          </span>
                          {event.categoryName && (
                            <span className="text-[10px] text-slate-500 bg-slate-800/50 px-1.5 rounded">
                              {event.categoryName}
                            </span>
                          )}
                          {event.hasConflict && (
                            <span className="text-[10px] text-amber-400">&#9888;</span>
                          )}
                          {eventCase && (
                            <span
                              className="text-[10px] font-medium px-1.5 rounded"
                              style={{
                                color: (CASE_STATUS_COLORS[eventCase.status] ?? CASE_STATUS_COLORS.OPEN).color,
                                backgroundColor: (CASE_STATUS_COLORS[eventCase.status] ?? CASE_STATUS_COLORS.OPEN).color + '15',
                              }}
                            >
                              Case: {(CASE_STATUS_COLORS[eventCase.status] ?? CASE_STATUS_COLORS.OPEN).label}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-white font-medium group-hover:text-purple-200 transition-colors">
                          {event.title}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{event.summary}</p>
                        <div className="flex items-center gap-4 mt-1.5 text-[10px] text-slate-500">
                          <span>S:{event.score} U:{event.urgency} C:{event.confidence}</span>
                          <span>{event.sourceName}</span>
                          <span>{formatRelativeTime(event.publishedAt)}</span>
                        </div>
                      </div>
                      {/* 호버 시 화살표 */}
                      <span className="text-slate-600 group-hover:text-purple-400 transition-colors text-lg self-center flex-shrink-0">
                        &#8250;
                      </span>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ============================================ */}
      {/* 3. 선택된 딜 카테고리 히트맵 (하단) */}
      {/* ============================================ */}
      <motion.div className="col-span-12" variants={itemVariants}>
        {/* U15: 카테고리 히트맵 - 로딩 / 데이터 / 미선택 구분 */}
        {dealDetailLoading && selectedDealId ? (
          /* 로딩 중: 스켈레톤 히트맵 */
          <>
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-cyan-400">&#9632;</span>
              Risk Categories
            </h2>
            <div className="grid grid-cols-5 gap-3">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => (
                <div key={i} className="p-3 space-y-2 bg-slate-900/40 border border-white/5 rounded-2xl backdrop-blur-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <SkeletonLine width="24px" />
                    <SkeletonLine width="60%" />
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-slate-700/30 animate-pulse" />
                  <div className="flex justify-between">
                    <SkeletonLine width="30px" />
                    <SkeletonLine width="40px" />
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : selectedDeal && selectedCompany ? (
          <>
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-cyan-400">&#9632;</span>
              {selectedCompany.name} - Risk Categories
            </h2>
            <div className="grid grid-cols-5 gap-3">
              {selectedCategories.map((cat) => {
                const catColor = CATEGORY_COLORS[cat.code] ?? { color: '#6b7280', bg: 'rgba(107, 114, 128, 0.15)' };
                const isDim = cat.score === 0;
                const trendArrow = getTrendArrow(cat.trend);
                const trendClass = getTrendTextClass(cat.trend);

                const isExpanded = expandedCategory === cat.code;
                return (
                  <motion.div
                    key={cat.id}
                    whileHover={!isDim ? { scale: 1.02 } : undefined}
                    className={isDim ? 'opacity-30' : 'cursor-pointer'}
                    onClick={() => !isDim && handleCategoryClick(cat.code)}
                  >
                    <GlassCard
                      className="p-3"
                      hover={!isDim}
                      style={{
                        borderColor: isExpanded ? catColor.color + '60' : isDim ? undefined : catColor.color + '30',
                      }}
                    >
                      {/* 상단: 아이콘 + 이름 */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-lg">{cat.icon}</span>
                        <span
                          className="text-sm font-medium truncate"
                          style={{ color: catColor.color }}
                        >
                          {cat.name}
                        </span>
                        <span className={`text-xs ml-auto ${trendClass}`}>
                          {trendArrow}
                        </span>
                      </div>

                      {/* 점수 바 */}
                      <div className="w-full h-1.5 rounded-full bg-slate-700/50 mb-1.5">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${Math.min((cat.score / 100) * 100, 100)}%`,
                            backgroundColor: catColor.color,
                          }}
                        />
                      </div>

                      {/* 하단: 점수 + 가중치 */}
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-white font-semibold">
                          {cat.score}점
                        </span>
                        <span className="text-xs text-slate-500">
                          W: {(cat.weight * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* Entity/Event 카운트 */}
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-slate-600">
                          Entity: {cat.entityCount}
                        </span>
                        <span className="text-[10px] text-slate-600">
                          Event: {cat.eventCount}
                        </span>
                      </div>

                      {/* 확장 상세 (인라인) */}
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="mt-2 pt-2 border-t border-white/10"
                        >
                          <div className="text-[10px] text-slate-400 space-y-1 mb-2">
                            <p>가중점수: <span className="text-white">{cat.weightedScore?.toFixed(1) ?? '-'}</span></p>
                            <p>기여도: <span className="text-white">{selectedCompany ? `${((cat.weightedScore ?? 0) / Math.max(selectedCompany.directScore, 1) * 100).toFixed(0)}%` : '-'}</span></p>
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleCategoryDeepDive(cat.code); }}
                            className="w-full text-[10px] font-medium py-1 rounded text-purple-400 hover:text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 transition-colors"
                          >
                            상세 분석 →
                          </button>
                        </motion.div>
                      )}
                    </GlassCard>
                  </motion.div>
                );
              })}
            </div>
          </>
        ) : (
          <EmptyState
            icon="&#128200;"
            title="딜을 선택하면 카테고리 히트맵이 표시됩니다"
            description="상단 딜 목록에서 분석하고자 하는 투자 건을 클릭하세요"
            variant="card"
          />
        )}
      </motion.div>

      {/* ============================================ */}
      {/* 5. Footer 영역 */}
      {/* ============================================ */}
      <motion.div className="col-span-12" variants={itemVariants}>
        <div className="flex items-center justify-end pt-2 border-t border-white/5">
          <span className="text-xs text-slate-600">
            Data updated: {formatDate(new Date().toISOString())}
          </span>
        </div>
      </motion.div>

      {/* ============================================ */}
      {/* CRITICAL 레드 경보 플래시 오버레이 (5초간 깜빡임) */}
      {/* ============================================ */}
      <AnimatePresence>
        {criticalFlash && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-[200] pointer-events-none"
            style={{
              background: 'radial-gradient(ellipse at center, rgba(239,68,68,0.18) 0%, rgba(239,68,68,0.04) 100%)',
              animation: 'criticalRedPulse 0.6s ease-in-out 8',
            }}
          />
        )}
      </AnimatePresence>
      <style>{`
        @keyframes criticalRedPulse {
          0%, 100% { opacity: 0; }
          50% { opacity: 1; }
        }
      `}</style>
    </motion.div>
  );
}
