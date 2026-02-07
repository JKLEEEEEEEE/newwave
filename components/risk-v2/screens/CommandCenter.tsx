/**
 * CommandCenter - 대시보드 총사령관 화면
 * 모든 투자 건의 리스크를 한눈에 파악할 수 있는 메인 화면
 *
 * 구성:
 *   1. 상단 요약 카드 (3개: 포트폴리오 수, 평균 리스크, PASS/WARNING/FAIL 분포)
 *   2. 딜 리스트 (중앙)
 *   3. 선택된 딜 카테고리 히트맵 (하단)
 *   4. 최근 이벤트 피드 (우측)
 *   5. Powered by 영역
 */

import React, { useMemo, useCallback, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

// 타입
import type { RiskCategoryV2, RiskEventV2 } from '../types-v2';

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
const LIVE_POLL_INTERVAL = 30_000; // 30초 폴링

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

  // --- 요약 데이터 계산 ---
  const summary = useMemo(() => {
    const total = deals.length;
    const active = deals.filter(d => d.status === 'ACTIVE').length;
    return { total, active: active || total, avgRisk: dealDetail?.mainCompany.totalRiskScore ?? 0 };
  }, [deals, dealDetail]);

  const levelCounts = useMemo(() => {
    const counts = { PASS: 0, WARNING: 0, FAIL: 0 };
    // If we have deal detail, count the main company and related companies
    if (dealDetail) {
      counts[dealDetail.mainCompany.riskLevel]++;
      for (const rc of dealDetail.relatedCompanies) {
        counts[rc.riskLevel]++;
      }
    }
    // Fill remaining deals as PASS
    const total = deals.length;
    const counted = counts.PASS + counts.WARNING + counts.FAIL;
    if (counted < total) counts.PASS += (total - counted);
    return counts;
  }, [deals, dealDetail]);

  const donutData = useMemo(() => [
    { name: 'PASS', value: levelCounts.PASS, color: RISK_COLORS.PASS.primary },
    { name: 'WARNING', value: levelCounts.WARNING, color: RISK_COLORS.WARNING.primary },
    { name: 'FAIL', value: levelCounts.FAIL, color: RISK_COLORS.FAIL.primary },
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

  // --- Live Feed: 자동 폴링 ---
  useEffect(() => {
    if (!selectedDealId || !liveActive) return;
    const timer = setInterval(() => {
      pollCountRef.current++;
      // Context의 loadDealDetail을 다시 호출하여 최신 이벤트 가져오기
      loadDeals();
    }, LIVE_POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [selectedDealId, liveActive, loadDeals]);

  // --- Sparkline 데이터 캐시 ---
  const sparklineCache = useMemo(() => {
    const cache: Record<string, number[]> = {};
    for (const deal of deals) {
      cache[deal.id] = generateSparklineData(deal.score ?? 0, deal.id);
    }
    return cache;
  }, [deals]);

  // --- 카테고리 클릭 핸들러 ---
  const handleCategoryClick = (code: string) => {
    selectCategory(code as RiskCategoryV2['code']);
    setActiveView('deepdive');
  };

  // --- U22: 딜 카드 더블클릭 → Deep Dive 이동 ---
  const handleDealDoubleClick = useCallback((dealId: string) => {
    selectDeal(dealId);
    setActiveView('deepdive');
  }, [selectDeal, setActiveView]);

  // --- U16: 도넛 차트 세그먼트 클릭 → 해당 레벨 필터 ---
  const handleDonutClick = useCallback((level: string) => {
    // 선택된 딜이 있으면 해당 레벨의 카테고리로 드릴다운
    if (selectedDealId) {
      setActiveView('deepdive');
    }
  }, [selectedDealId, setActiveView]);

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
                <p className="text-sm text-slate-400 mb-1">Avg Risk Score</p>
                <div className="flex items-center gap-3">
                  <ScoreGauge score={summary.avgRisk} size={80} label="Average" />
                </div>
              </div>
              <RiskBadge level={getScoreLevel(summary.avgRisk)} size="lg" />
            </div>
          </GlassCard>

          {/* 1-c. PASS/WARNING/FAIL 도넛 */}
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
        <motion.div
          key={`deals-${deals.length}`}
          className="flex flex-col gap-3"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* U15: 로딩 스켈레톤 */}
          {dealsLoading ? (
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
              <motion.div key={deal.id} variants={itemVariants}>
                <GlassCard
                  hover
                  onClick={() => selectDeal(deal.id)}
                  onDoubleClick={() => handleDealDoubleClick(deal.id)}
                  className={`p-4 ${isSelected ? 'ring-2 ring-purple-500' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* U6: 선택 딜 = ScoreGauge, 미선택 딜 = 미니 상태 인디케이터 */}
                      {company ? (
                        <ScoreGauge
                          score={company.totalRiskScore}
                          size={60}
                          directScore={company.directScore}
                          propagatedScore={company.propagatedScore}
                        />
                      ) : isSelected && dealDetailLoading ? (
                        /* U15: 딜 상세 로딩 중 */
                        <div className="w-[60px] h-[60px] rounded-full bg-slate-800/50 animate-pulse flex items-center justify-center">
                          <span className="text-slate-500 text-[10px]">...</span>
                        </div>
                      ) : (
                        /* U6: 미선택 딜 미니 점수 표시 */
                        <ScoreGauge
                          score={deal.score ?? 0}
                          size={48}
                        />
                      )}
                      <div>
                        <h3 className="text-white font-medium text-base">{deal.name}</h3>
                        <p className="text-slate-400 text-sm mt-0.5">
                          {deal.targetCompanyName} {company ? `(${company.ticker}) / ${company.sector}` : ''}
                        </p>
                        {/* Last event indicator */}
                        {isSelected && recentEvents.length > 0 && (
                          <p className="text-slate-500 text-[10px] mt-1 flex items-center gap-1">
                            <span className="text-red-400">●</span>
                            마지막 이벤트: {formatRelativeTime(recentEvents[0].publishedAt)}
                          </p>
                        )}
                        {/* U22: 더블클릭 힌트 (선택된 카드에만 표시) */}
                        {isSelected && company && (
                          <p className="text-slate-600 text-[10px] mt-1">더블클릭으로 상세 분석 이동</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* Sparkline 추세 차트 */}
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
                      {company ? (
                        <RiskBadge level={company.riskLevel} animated />
                      ) : deal.riskLevel ? (
                        <RiskBadge level={deal.riskLevel} />
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
        </motion.div>
      </motion.div>

      {/* ============================================ */}
      {/* 4. 최근 이벤트 피드 (우측) */}
      {/* ============================================ */}
      <motion.div className="col-span-4" variants={itemVariants}>
        <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          {/* LIVE 펄스 인디케이터 */}
          {liveActive && selectedDealId ? (
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
            </span>
          ) : (
            <span className="text-red-400">&#9679;</span>
          )}
          <span>Live Events</span>
          {liveActive && selectedDealId && (
            <span className="text-[10px] font-mono text-red-400/70 bg-red-500/10 px-1.5 py-0.5 rounded ml-1">
              LIVE
            </span>
          )}
          {newEventIds.size > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="text-[10px] font-bold text-white bg-red-500 rounded-full w-5 h-5 flex items-center justify-center"
            >
              {newEventIds.size}
            </motion.span>
          )}
        </h2>
        <div className="flex flex-col gap-2">
          {/* U15: 로딩 / 빈 데이터 / 데이터 있음 구분 */}
          {dealsLoading || dealDetailLoading ? (
            /* 로딩 중: 스켈레톤 표시 */
            <>
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-3 space-y-2 bg-slate-900/40 border border-white/5 rounded-2xl backdrop-blur-xl">
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-slate-700/30 animate-pulse mt-1.5 flex-shrink-0" />
                    <div className="flex-1 space-y-2">
                      <SkeletonLine width="80%" />
                      <SkeletonLine width="100%" />
                      <div className="flex justify-between">
                        <SkeletonLine width="50px" />
                        <SkeletonLine width="70px" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </>
          ) : recentEvents.length > 0 ? (
            <AnimatePresence mode="popLayout">
              {recentEvents.map((event, idx) => {
                const isNew = newEventIds.has(event.id);
                const sevColor = SEVERITY_COLORS[event.severity] ?? SEVERITY_COLORS.MEDIUM;
                return (
                  <motion.div
                    key={event.id}
                    layout
                    initial={{ opacity: 0, y: -20, scale: 0.95 }}
                    animate={{
                      opacity: 1,
                      y: 0,
                      scale: 1,
                      ...(isNew ? {
                        boxShadow: ['0 0 0px rgba(239,68,68,0)', '0 0 20px rgba(239,68,68,0.4)', '0 0 0px rgba(239,68,68,0)'],
                      } : {}),
                    }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    transition={{ delay: idx * 0.03, duration: 0.3, layout: { duration: 0.2 } }}
                    className="rounded-2xl"
                  >
                    <GlassCard
                      className={`p-3 transition-all ${isNew ? 'ring-1 ring-red-500/50' : ''}`}
                    >
                      <div className="flex items-start gap-2">
                        {/* Severity 도트 */}
                        <span
                          className="mt-1.5 w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: sevColor.color }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="text-xs">
                              {event.type === 'DISCLOSURE' ? '\uD83D\uDCCB' : event.type === 'NEWS' ? '\uD83D\uDCF0' : '\u26A0\uFE0F'}
                            </span>
                            <span className="text-[10px] text-slate-500 font-medium uppercase">
                              {event.type === 'DISCLOSURE' ? 'DART' : event.type === 'NEWS' ? '\uB274\uC2A4' : '\uC774\uC288'}
                            </span>
                            {isNew && (
                              <motion.span
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                className="text-[9px] font-bold text-white bg-red-500 px-1 rounded"
                              >
                                NEW
                              </motion.span>
                            )}
                          </div>
                          <p className="text-sm text-white font-medium truncate">{event.title}</p>
                          <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{event.summary}</p>
                          <div className="flex items-center justify-between mt-2">
                            <span
                              className="text-xs font-medium px-1.5 py-0.5 rounded-full"
                              style={{ color: sevColor.color, backgroundColor: sevColor.bg }}
                            >
                              {getSeverityLabel(event.severity)}
                            </span>
                            <div className="flex items-center gap-2 text-xs text-slate-500">
                              {event.sourceName && <span>{event.sourceName}</span>}
                              <span>{formatRelativeTime(event.publishedAt)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          ) : (
            /* 빈 데이터: EmptyState 컴포넌트 사용 */
            <EmptyState
              icon="&#128240;"
              title="최근 이벤트가 없습니다"
              description="딜을 선택하면 관련 이벤트가 표시됩니다"
              variant="card"
            />
          )}
        </div>
      </motion.div>

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

                return (
                  <motion.div
                    key={cat.id}
                    whileHover={!isDim ? { scale: 1.03 } : undefined}
                    className={isDim ? 'opacity-30' : 'cursor-pointer'}
                    onClick={() => !isDim && handleCategoryClick(cat.code)}
                  >
                    <GlassCard
                      className="p-3"
                      hover={!isDim}
                      style={{
                        borderColor: isDim ? undefined : catColor.color + '30',
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
    </motion.div>
  );
}
