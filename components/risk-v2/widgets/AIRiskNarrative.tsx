/**
 * AIRiskNarrative - AI 스토리텔링 리스크 카드
 * Briefing API 기반 5섹션 구조:
 *   1. Executive Summary (등급 뱃지 + 신뢰도 바)
 *   2. Key Concerns (최대 3개, severity border)
 *   3. Recommendations (3열 그리드: 즉시/모니터링/실사)
 *   4. Data Sources (미니 통계 뱃지 + 신뢰도 프로그레스 바)
 *   5. 새로고침 버튼
 *
 * framer-motion stagger 애니메이션으로 각 섹션 순차 등장
 */

import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import type { BriefingResponse } from '../types-v2';
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
  className?: string;
}

// ============================================
// Animation variants
// ============================================

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.1,
    },
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

/** Severity 색상 결정 (key_concerns 인덱스 기반 - 첫 번째가 가장 중요) */
function getConcernSeverity(index: number): { key: string; color: string; bg: string } {
  const mapping = [
    { key: 'CRITICAL', ...SEVERITY_COLORS['CRITICAL'] },
    { key: 'HIGH', ...SEVERITY_COLORS['HIGH'] },
    { key: 'MEDIUM', ...SEVERITY_COLORS['MEDIUM'] },
  ];
  return mapping[index] ?? { key: 'LOW', ...SEVERITY_COLORS['LOW'] };
}

/** 신뢰도 퍼센트 텍스트 색상 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-green-400';
  if (confidence >= 0.5) return 'text-yellow-400';
  return 'text-red-400';
}

/** RiskLevel 문자열을 RiskBadge가 받는 타입으로 변환 */
function toRiskLevel(level?: string): 'PASS' | 'WARNING' | 'FAIL' {
  if (level === 'FAIL' || level === 'WARNING' || level === 'PASS') return level;
  return 'PASS';
}

// ============================================
// Skeleton 로딩 컴포넌트
// ============================================

function NarrativeSkeleton() {
  return (
    <div className="space-y-6 p-6">
      {/* Title skeleton */}
      <div className="flex items-center gap-3">
        <div className="w-6 h-6 rounded bg-purple-500/20 animate-pulse" />
        <div className="h-5 w-48 rounded bg-slate-700/50 animate-pulse" />
      </div>

      {/* Executive summary skeleton */}
      <div className="space-y-2">
        <div className="h-4 w-full rounded bg-slate-700/40 animate-pulse" />
        <div className="h-4 w-3/4 rounded bg-slate-700/40 animate-pulse" />
        <div className="h-4 w-5/6 rounded bg-slate-700/40 animate-pulse" />
      </div>

      {/* Concerns skeleton */}
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-xl bg-slate-800/40 animate-pulse" />
        ))}
      </div>

      {/* Recommendations skeleton */}
      <div className="grid grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-xl bg-slate-800/40 animate-pulse" />
        ))}
      </div>

      {/* Data sources skeleton */}
      <div className="flex gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-8 w-24 rounded-full bg-slate-700/40 animate-pulse" />
        ))}
      </div>
    </div>
  );
}

// ============================================
// 메인 컴포넌트
// ============================================

export default function AIRiskNarrative({
  dealId,
  companyName,
  riskScore,
  riskLevel,
  className = '',
}: AIRiskNarrativeProps) {
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ---- 데이터 로드 ----
  const loadBriefing = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await riskApiV2.fetchBriefing(dealId);
      if (res.success && res.data) {
        setBriefing(res.data);
      } else {
        setError(res.error || '브리핑 데이터를 불러올 수 없습니다.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    loadBriefing();
  }, [loadBriefing]);

  // ---- 표시할 등급 / 점수 결정 (briefing 우선, fallback props) ----
  const displayLevel = toRiskLevel(briefing?.riskLevel ?? riskLevel);
  const displayScore = briefing?.riskScore ?? riskScore ?? 0;
  const displayConfidence = briefing?.confidence ?? 0;
  const confidencePct = Math.round(displayConfidence * 100);

  // ---- 에러 상태 ----
  if (!loading && error) {
    return (
      <GlassCard gradient="purple" className={`p-6 ${className}`}>
        <div className="relative pl-3">
          {/* 좌측 보라색 stripe */}
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
          <div className="text-sm text-red-400/80">
            {error}
          </div>
          <button
            onClick={loadBriefing}
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

  // ---- 로딩 상태 ----
  if (loading) {
    return (
      <GlassCard gradient="purple" className={className}>
        <div className="relative">
          {/* 좌측 보라색 stripe */}
          <div
            className="absolute left-0 top-0 bottom-0 w-1 rounded-full"
            style={{ background: GRADIENTS.purple }}
          />
          <NarrativeSkeleton />
        </div>
      </GlassCard>
    );
  }

  // ---- 데이터 준비 ----
  const concerns = (briefing?.key_concerns ?? []).slice(0, 3);
  const recommendations = briefing?.recommendations;
  const dataSources = briefing?.dataSources;

  return (
    <GlassCard gradient="purple" className={`relative ${className}`}>
      {/* 좌측 보라색 gradient stripe */}
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
        {/* ===== 헤더: AI Risk Intelligence ===== */}
        <motion.div variants={sectionVariants} className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">&#10024;</span>
            <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">
              AI Risk Intelligence
            </h3>
          </div>
          <div className="flex items-center gap-2">
            {displayScore > 0 && (
              <span className="text-xs text-slate-400 font-mono">
                Score: {displayScore}
              </span>
            )}
            <RiskBadge level={displayLevel} size="sm" animated />
          </div>
        </motion.div>

        {/* ===== 섹션 1: Executive Summary ===== */}
        <motion.div variants={sectionVariants} className="space-y-3">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Executive Summary
          </h4>
          <p className="text-sm leading-relaxed text-slate-300">
            {highlightKeywords(briefing?.executive_summary || '')}
          </p>

          {/* 등급 뱃지 + 신뢰도 미니 바 */}
          <div className="flex items-center gap-4 mt-2">
            <RiskBadge level={displayLevel} size="md" showLabel animated />
            <div className="flex items-center gap-2 flex-1 max-w-[200px]">
              <span className="text-[10px] text-slate-500 whitespace-nowrap">신뢰도</span>
              <div className="flex-1 h-1.5 rounded-full bg-slate-700/60 overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: GRADIENTS.purple }}
                  initial={{ width: 0 }}
                  animate={{ width: `${confidencePct}%` }}
                  transition={{ duration: 1, delay: 0.5, ease: 'easeOut' }}
                />
              </div>
              <span className={`text-[10px] font-mono font-medium ${getConfidenceColor(displayConfidence)}`}>
                {confidencePct}%
              </span>
            </div>
          </div>
        </motion.div>

        {/* ===== 섹션 2: Key Concerns ===== */}
        {concerns.length > 0 && (
          <motion.div variants={sectionVariants} className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Key Concerns
            </h4>
            <div className="space-y-2">
              {concerns.map((concern, idx) => {
                const sev = getConcernSeverity(idx);
                return (
                  <motion.div
                    key={idx}
                    variants={concernCardVariants}
                    className="relative rounded-xl border border-white/5 bg-slate-800/30
                               backdrop-blur-sm p-4 pl-5 overflow-hidden"
                  >
                    {/* 좌측 severity 색상 border */}
                    <div
                      className="absolute left-0 top-0 bottom-0 w-[3px]"
                      style={{ backgroundColor: sev.color }}
                    />

                    <div className="flex items-start gap-2 mb-1.5">
                      <span className="text-sm flex-shrink-0">&#9888;&#65039;</span>
                      <span className="text-sm font-semibold text-slate-200 leading-snug">
                        {concern.issue}
                      </span>
                    </div>

                    <div className="ml-6 space-y-1">
                      <p className="text-xs text-slate-400">
                        <span className="text-slate-500 font-medium">why:</span>{' '}
                        {concern.why_it_matters}
                      </p>
                      <p className="text-xs text-slate-400">
                        <span className="text-slate-500 font-medium">watch:</span>{' '}
                        {concern.watch_for}
                      </p>
                    </div>

                    {/* severity 뱃지 */}
                    <span
                      className="absolute top-3 right-3 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
                      style={{ color: sev.color, backgroundColor: sev.bg }}
                    >
                      {sev.key}
                    </span>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* ===== 섹션 3: Recommendations (3열 그리드) ===== */}
        {recommendations && (
          <motion.div variants={sectionVariants} className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Recommendations
            </h4>
            <div className="grid grid-cols-3 gap-3">
              {/* 즉시 조치 */}
              <RecommendationColumn
                title="즉시 조치"
                icon="&#128680;"
                items={recommendations.immediate_actions}
                accentColor="#ef4444"
              />
              {/* 모니터링 */}
              <RecommendationColumn
                title="모니터링"
                icon="&#128065;"
                items={recommendations.monitoring_focus}
                accentColor="#f59e0b"
              />
              {/* 실사 포인트 */}
              <RecommendationColumn
                title="실사 포인트"
                icon="&#128269;"
                items={recommendations.due_diligence_points}
                accentColor="#8b5cf6"
              />
            </div>
          </motion.div>
        )}

        {/* ===== 섹션 4: Data Sources ===== */}
        <motion.div variants={sectionVariants} className="space-y-3">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Data Sources
          </h4>
          <div className="flex flex-wrap items-center gap-2">
            {dataSources ? (
              <>
                <SourceBadge icon="&#128240;" label="뉴스" count={dataSources.newsCount} />
                <SourceBadge icon="&#128203;" label="공시" count={dataSources.disclosureCount} />
                <SourceBadge icon="&#127970;" label="관련기업" count={dataSources.relatedCompanyCount} />
                <SourceBadge icon="&#128202;" label="카테고리" count={dataSources.categoryCount} />
              </>
            ) : (
              <span className="text-xs text-slate-500">소스 정보 없음</span>
            )}
          </div>

          {/* 신뢰도 프로그레스 바 (전체 너비) */}
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-slate-500">신뢰도:</span>
            <div className="flex-1 h-2 rounded-full bg-slate-700/50 overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: GRADIENTS.purple }}
                initial={{ width: 0 }}
                animate={{ width: `${confidencePct}%` }}
                transition={{ duration: 1.2, delay: 0.8, ease: 'easeOut' }}
              />
            </div>
            <span className={`text-xs font-mono font-semibold ${getConfidenceColor(displayConfidence)}`}>
              {confidencePct}%
            </span>
          </div>
        </motion.div>

        {/* ===== 새로고침 버튼 ===== */}
        <motion.div variants={sectionVariants} className="flex justify-center pt-1">
          <button
            onClick={loadBriefing}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 text-xs font-medium rounded-xl
                       bg-purple-500/10 text-purple-300 border border-purple-500/20
                       hover:bg-purple-500/20 hover:border-purple-400/30
                       active:scale-95 transition-all disabled:opacity-50"
          >
            <motion.span
              animate={loading ? { rotate: 360 } : { rotate: 0 }}
              transition={loading ? { repeat: Infinity, duration: 1, ease: 'linear' } : {}}
              className="inline-block"
            >
              &#8635;
            </motion.span>
            새로고침
          </button>
        </motion.div>
      </motion.div>
    </GlassCard>
  );
}

// ============================================
// 하위 컴포넌트: RecommendationColumn
// ============================================

interface RecommendationColumnProps {
  title: string;
  icon: string;
  items: string[];
  accentColor: string;
}

function RecommendationColumn({ title, icon, items, accentColor }: RecommendationColumnProps) {
  return (
    <div
      className="rounded-xl border border-white/5 bg-slate-800/20 p-3 space-y-2"
    >
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
            <li key={i} className="flex items-start gap-1.5 text-xs text-slate-300 leading-relaxed">
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
// 하위 컴포넌트: SourceBadge
// ============================================

interface SourceBadgeProps {
  icon: string;
  label: string;
  count: number;
}

function SourceBadge({ icon, label, count }: SourceBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
                      bg-slate-800/50 border border-white/5 text-xs text-slate-300">
      <span>{icon}</span>
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-semibold text-slate-200">{count}건</span>
    </span>
  );
}

// ============================================
// 유틸: 핵심 키워드 하이라이트
// ============================================

/** executive_summary 내 핵심 키워드를 보라색으로 하이라이트 */
function highlightKeywords(text: string): React.ReactNode {
  if (!text) return null;

  // 리스크 관련 핵심 키워드 패턴 (split용 - 캡처그룹으로 구분자 유지)
  const splitPattern =
    /(위험|리스크|소송|법률|특허|규제|제재|배상|벌금|부채|적자|하락|급락|파산|부도|횡령|배임|분식|감사의견|상폐|불성실|제소|피소|손실|취약|심각|최고|가장 높|주의|경고|임계|FAIL|CRITICAL|HIGH)/;

  // 매칭 확인용 (g 플래그 없음)
  const testPattern =
    /^(위험|리스크|소송|법률|특허|규제|제재|배상|벌금|부채|적자|하락|급락|파산|부도|횡령|배임|분식|감사의견|상폐|불성실|제소|피소|손실|취약|심각|최고|가장 높|주의|경고|임계|FAIL|CRITICAL|HIGH)$/;

  const parts = text.split(splitPattern);

  return parts.map((part, i) => {
    if (!part) return null;
    if (testPattern.test(part)) {
      return (
        <span key={i} className="text-purple-300 font-semibold">
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}
