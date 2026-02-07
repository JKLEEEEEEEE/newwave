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

import React, { useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

// 타입
import type { RiskCategoryV2 } from '../types-v2';

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
// 메인 컴포넌트
// ============================================
export default function CommandCenter() {
  const { state, selectDeal, selectCategory, setActiveView, currentDeal, currentCompany, currentCategories, loadDeals } = useRiskV2();
  const { selectedDealId, deals, dealsLoading, dealDetail, dealDetailLoading } = state;

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
                      {company ? (
                        <RiskBadge level={company.riskLevel} animated />
                      ) : deal.riskLevel ? (
                        <RiskBadge level={deal.riskLevel} />
                      ) : (
                        /* U6: 미선택 딜에도 status 뱃지 표시 */
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
                      <div className="text-right">
                        <p className="text-xs text-slate-500">{formatDate(deal.registeredAt)}</p>
                        <p className="text-xs text-slate-600 mt-0.5">{deal.analyst}</p>
                      </div>
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
          <span className="text-red-400">&#9679;</span>
          Recent Events
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
            recentEvents.map((event, idx) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05, duration: 0.3 }}
              >
                <GlassCard className="p-3">
                  <div className="flex items-start gap-2">
                    {/* Severity 도트 */}
                    <span
                      className="mt-1.5 w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: (SEVERITY_COLORS[event.severity] ?? SEVERITY_COLORS.MEDIUM).color }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        {/* Source icon */}
                        <span className="text-xs">
                          {event.type === 'DISCLOSURE' ? '📋' : event.type === 'NEWS' ? '📰' : '⚠️'}
                        </span>
                        <span className="text-[10px] text-slate-500 font-medium uppercase">
                          {event.type === 'DISCLOSURE' ? 'DART' : event.type === 'NEWS' ? '뉴스' : '이슈'}
                        </span>
                      </div>
                      <p className="text-sm text-white font-medium truncate">{event.title}</p>
                      <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{event.summary}</p>
                      <div className="flex items-center justify-between mt-2">
                        <span
                          className={`text-xs font-medium px-1.5 py-0.5 rounded-full`}
                          style={{
                            color: (SEVERITY_COLORS[event.severity] ?? SEVERITY_COLORS.MEDIUM).color,
                            backgroundColor: (SEVERITY_COLORS[event.severity] ?? SEVERITY_COLORS.MEDIUM).bg,
                          }}
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
            ))
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
