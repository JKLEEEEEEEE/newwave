/**
 * RiskDeepDive - 5-Node 계층 드릴다운 분석 화면
 * Deal -> Company -> Category -> Entity -> Event 순으로 클릭하며 파고 들어감
 *
 * 레벨 1: 딜 목록 (selectedDealId === null)
 * 레벨 2: 기업 상세 + 10개 카테고리 그리드 (selectedCategoryCode === null)
 * 레벨 3: 카테고리 상세 + 엔티티 리스트 (selectedEntityId === null)
 * 레벨 4: 엔티티 상세 + 이벤트 타임라인
 */

import React, { useMemo, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import type {
  CategoryCodeV2,
  RiskEntityV2,
  RiskEventV2,
} from '../types-v2';
import { CATEGORY_COLORS, SEVERITY_COLORS, ANIMATION } from '../design-tokens';
import { CATEGORY_DEFINITIONS_V2 } from '../category-definitions';
import { riskApiV2 } from '../api-v2';
import {
  getScoreLevel,
  getLevelClasses,
  formatDate,
  getSeverityLabel,
  getSeverityTextClass,
} from '../utils-v2';
import { useRiskV2 } from '../context/RiskV2Context';
import GlassCard from '../shared/GlassCard';
import ScoreGauge from '../shared/ScoreGauge';
import RiskBadge from '../shared/RiskBadge';
import TrendIndicator from '../shared/TrendIndicator';
import ErrorState from '../shared/ErrorState';

// ============================================
// 애니메이션 변수
// ============================================
const pageVariants = {
  initial: { opacity: 0, x: 30 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -30 },
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: ANIMATION.stagger,
    },
  },
};

const staggerItem = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
};

// ============================================
// 엔티티 타입 아이콘 매핑
// ============================================
const ENTITY_TYPE_ICONS: Record<string, string> = {
  PERSON: '\uD83D\uDC64',      // 👤
  SHAREHOLDER: '\uD83C\uDFE2', // 🏢
  CASE: '\u2696\uFE0F',        // ⚖️
  ISSUE: '\u26A0\uFE0F',       // ⚠️
};

// ============================================
// 이벤트 타입 라벨
// ============================================
const EVENT_TYPE_LABELS: Record<string, string> = {
  NEWS: '뉴스',
  DISCLOSURE: '공시',
  ISSUE: '이슈',
};

// ============================================
// Breadcrumb 컴포넌트
// ============================================
interface BreadcrumbItem {
  label: string;
  onClick: () => void;
  active: boolean;
}

function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav
      className="sticky top-0 z-10 bg-[#0a0f1e]/80 backdrop-blur px-6 py-3 border-b border-white/5"
      aria-label="브레드크럼 내비게이션"
    >
      <ol className="flex items-center gap-2 text-sm flex-wrap" role="list">
        {items.map((item, idx) => (
          <li key={idx} className="flex items-center gap-2">
            {idx > 0 && (
              <span className="text-slate-600 select-none" aria-hidden="true">&gt;</span>
            )}
            <button
              onClick={item.onClick}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  item.onClick();
                }
              }}
              tabIndex={0}
              aria-current={item.active ? 'page' : undefined}
              className={`
                px-2 py-1 rounded-md transition-colors
                hover:text-purple-300 hover:bg-purple-500/10
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 focus-visible:ring-offset-1 focus-visible:ring-offset-[#0a0f1e]
                ${
                  item.active
                    ? 'text-purple-400 font-semibold'
                    : 'text-slate-400'
                }
              `}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}

// ============================================
// 레벨 1: 딜 목록
// ============================================
function DealListLevel() {
  const { selectDeal, state } = useRiskV2();
  const { deals, dealsLoading } = state;

  if (dealsLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-40 bg-slate-700/50 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-slate-900/40 border border-white/5 rounded-2xl p-5 space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-2">
                  <div className="h-5 w-32 bg-slate-700/40 rounded animate-pulse" />
                  <div className="h-3.5 w-24 bg-slate-700/30 rounded animate-pulse" />
                  <div className="h-3 w-40 bg-slate-700/20 rounded animate-pulse mt-2" />
                </div>
                <div className="w-[60px] h-[60px] rounded-full bg-slate-800/50 animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      key="deal-list"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: ANIMATION.pageTransition }}
    >
      <h2 className="text-xl font-bold text-white mb-6">투자검토 딜 목록</h2>
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        variants={staggerContainer}
        initial="initial"
        animate="animate"
      >
        {deals.map((deal) => (
          <motion.div key={deal.id} variants={staggerItem}>
            <GlassCard
              hover
              onClick={() => selectDeal(deal.id)}
              className="p-5"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="text-white font-semibold text-lg truncate">
                    {deal.name}
                  </h3>
                  <p className="text-slate-400 text-sm mt-1">
                    {deal.targetCompanyName}
                  </p>
                  <p className="text-slate-500 text-xs mt-2">
                    담당: {deal.analyst} | {deal.status}
                  </p>
                </div>
                <div className="flex flex-col items-center gap-2 ml-4">
                  <div className="w-[60px] h-[60px] rounded-full bg-slate-800/40 flex items-center justify-center">
                    <span className="text-slate-500 text-xs">{deal.status}</span>
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
}

// ============================================
// 레벨 2: 기업 상세 + 카테고리 그리드
// ============================================
function CompanyDetailLevel({
  dealId,
}: {
  dealId: string;
}) {
  const { selectCategory, selectCompany, currentDeal, currentCompany, currentCategories, currentRelatedCompanies, state } = useRiskV2();
  const { dealDetailLoading } = state;

  if (dealDetailLoading) {
    return (
      <div className="space-y-6">
        {/* 기업 정보 스켈레톤 */}
        <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-slate-800/50 animate-pulse" />
            <div className="flex-1 space-y-2">
              <div className="h-5 w-40 bg-slate-700/40 rounded animate-pulse" />
              <div className="h-3.5 w-28 bg-slate-700/30 rounded animate-pulse" />
            </div>
          </div>
        </div>
        {/* 카테고리 그리드 스켈레톤 */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="bg-slate-900/40 border border-white/5 rounded-2xl p-4 space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-slate-700/40 animate-pulse" />
                <div className="h-3.5 w-16 bg-slate-700/30 rounded animate-pulse" />
              </div>
              <div className="h-1.5 w-full bg-slate-700/30 rounded-full animate-pulse" />
              <div className="h-3 w-12 bg-slate-700/20 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const deal = currentDeal;
  const company = currentCompany;
  const categories = currentCategories;
  const relatedCompanies = currentRelatedCompanies;

  if (!deal || !company) {
    return (
      <div className="text-slate-400 text-center py-12">
        딜 정보를 찾을 수 없습니다.
      </div>
    );
  }

  return (
    <motion.div
      key="company-detail"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: ANIMATION.pageTransition }}
    >
      {/* 상단: 기업 요약 */}
      <div className="flex items-center gap-6 mb-8">
        <ScoreGauge
          score={company.totalRiskScore}
          size={120}
          showBreakdown
          directScore={company.directScore}
          propagatedScore={company.propagatedScore}
        />
        <div>
          <h2 className="text-2xl font-bold text-white">{company.name}</h2>
          <p className="text-slate-400 mt-1">
            {company.sector} | {company.market} | {company.ticker}
          </p>
          <div className="mt-2">
            <RiskBadge level={company.riskLevel} size="lg" animated />
          </div>
        </div>
      </div>

      {/* Related company indicator */}
      {company && !company.isMain && (
        <div className="mb-4 p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
          <div className="flex items-center gap-2">
            <span className="text-yellow-400 text-sm">{'\u26A0\uFE0F'}</span>
            <p className="text-yellow-200 text-xs">
              관련기업 <span className="font-semibold">{company.name}</span>의 데이터입니다.
              {company.relationToMain && (
                <span className="text-yellow-300/70"> ({company.relationToMain.relation}, Tier {company.relationToMain.tier})</span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* 중앙: 10개 카테고리 그리드 (5열 x 2행) */}
      <h3 className="text-lg font-semibold text-white mb-4">
        리스크 카테고리 (10개)
      </h3>
      <motion.div
        className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 mb-8"
        variants={staggerContainer}
        initial="initial"
        animate="animate"
      >
        {categories.map((cat) => {
          const catColor = CATEGORY_COLORS[cat.code] ?? {
            color: '#6b7280',
            bg: 'rgba(107, 114, 128, 0.15)',
          };
          const hasData = cat.score > 0;
          const maxCatScore = Math.max(
            ...categories.map((c) => c.score),
            1
          );
          const barWidth = (cat.score / maxCatScore) * 100;

          return (
            <motion.div key={cat.id} variants={staggerItem}>
              <GlassCard
                hover={hasData}
                onClick={() => selectCategory(cat.code)}
                className={`p-4 ${!hasData ? 'opacity-30' : ''}`}
                style={{
                  borderColor: hasData ? catColor.color + '40' : undefined,
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-lg">{cat.icon}</span>
                  <TrendIndicator trend={cat.trend} size="sm" />
                </div>
                <h4
                  className="text-sm font-medium mb-1"
                  style={{ color: catColor.color }}
                >
                  {cat.name}
                </h4>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-white font-bold text-lg">
                    {cat.score}
                  </span>
                  <span className="text-slate-500 text-xs">
                    x{cat.weight}
                  </span>
                </div>
                {/* 점수 바 */}
                <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${barWidth}%`,
                      backgroundColor: catColor.color,
                    }}
                  />
                </div>
                <div className="text-slate-500 text-xs mt-2">
                  {cat.entityCount}개 엔티티 | {cat.eventCount}개 이벤트
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </motion.div>

      {/* 하단: 관련기업 패널 */}
      {relatedCompanies.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">
            관련기업
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {relatedCompanies.map((rel) => {
              const tierLabel =
                rel.relationToMain?.tier === 1 ? 'Tier 1' : 'Tier 2';
              const relation = rel.relationToMain?.relation ?? '';
              const propagationContribution = Math.round(
                rel.directScore * 0.3
              );

              return (
                <div key={rel.id}>
                <GlassCard className="p-4 cursor-pointer" hover onClick={() => {
                  selectCompany(rel.id);
                }}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-white font-medium">{rel.name}</h4>
                      <p className="text-slate-500 text-sm mt-1">
                        {relation} | {tierLabel} | {rel.sector}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-white font-bold">
                        {rel.totalRiskScore}
                      </div>
                      <RiskBadge level={rel.riskLevel} size="sm" />
                      <div className="text-slate-500 text-xs mt-1">
                        전이 기여: +{propagationContribution}
                      </div>
                    </div>
                  </div>
                </GlassCard>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ============================================
// 레벨 3: 카테고리 상세 + 엔티티 리스트
// ============================================
function CategoryDetailLevel({
  companyId,
  categoryCode,
}: {
  companyId: string;
  categoryCode: CategoryCodeV2;
}) {
  const { selectEntity, state } = useRiskV2();
  const [entities, setEntities] = useState<RiskEntityV2[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Find category from context
  const category = useMemo(
    () => state.dealDetail?.categories.find(c => c.code === categoryCode) ?? null,
    [state.dealDetail, categoryCode]
  );

  const catDef = useMemo(
    () => CATEGORY_DEFINITIONS_V2.find((d) => d.code === categoryCode),
    [categoryCode]
  );
  const catColor = CATEGORY_COLORS[categoryCode] ?? {
    color: '#6b7280',
    bg: 'rgba(107, 114, 128, 0.15)',
  };

  // Load entities from API
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    riskApiV2.fetchCategoryEntities(companyId, categoryCode).then(res => {
      if (!cancelled) {
        if (res.success && res.data) {
          setEntities(res.data);
        } else {
          setLoadError(res.error || 'API 서버에 연결할 수 없습니다.');
        }
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, [companyId, categoryCode]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-5 w-36 bg-slate-700/50 rounded animate-pulse" />
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-slate-900/40 border border-white/5 rounded-2xl p-4 space-y-2">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-slate-700/40 animate-pulse" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 w-32 bg-slate-700/40 rounded animate-pulse" />
                <div className="h-2.5 w-48 bg-slate-700/25 rounded animate-pulse" />
              </div>
              <div className="h-6 w-12 bg-slate-700/30 rounded-full animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (loadError) {
    return (
      <ErrorState
        message="엔티티 데이터를 불러올 수 없습니다"
        detail={loadError}
        onRetry={() => {
          setLoading(true);
          setLoadError(null);
          riskApiV2.fetchCategoryEntities(companyId, categoryCode).then(res => {
            if (res.success && res.data) {
              setEntities(res.data);
            } else {
              setLoadError(res.error || 'API 서버에 연결할 수 없습니다.');
            }
            setLoading(false);
          });
        }}
      />
    );
  }

  return (
    <motion.div
      key="category-detail"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: ANIMATION.pageTransition }}
    >
      {/* 상단: 카테고리 요약 */}
      <div className="flex items-center gap-4 mb-8">
        <div
          className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl"
          style={{ backgroundColor: catColor.bg }}
        >
          {catDef?.icon ?? '\uD83D\uDCCE'}
        </div>
        <div>
          <h2 className="text-xl font-bold" style={{ color: catColor.color }}>
            {category?.name ?? categoryCode}
          </h2>
          <div className="flex items-center gap-4 mt-1 text-sm text-slate-400">
            <span>
              점수: <span className="text-white font-semibold">{category?.score ?? 0}</span>
            </span>
            <span>
              가중치: <span className="text-white font-semibold">{category?.weight ?? 0}</span>
            </span>
            <span>
              가중점수:{' '}
              <span className="text-white font-semibold">
                {category?.weightedScore?.toFixed(2) ?? '0'}
              </span>
            </span>
          </div>
        </div>
      </div>

      {/* 엔티티 리스트 */}
      {entities.length === 0 ? (
        <div className="text-slate-400 text-center py-16">
          이 카테고리에 등록된 엔티티가 없습니다
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 gap-4"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {entities.map((entity) => {
            const typeIcon =
              ENTITY_TYPE_ICONS[entity.type] ?? '\u2753';
            const level = getScoreLevel(entity.riskScore);
            const levelClasses = getLevelClasses(level);

            return (
              <motion.div key={entity.id} variants={staggerItem}>
                <GlassCard
                  hover
                  onClick={() => selectEntity(entity.id)}
                  className="p-5"
                >
                  <div className="flex items-start gap-4">
                    <div className="text-2xl flex-shrink-0 mt-1">
                      {typeIcon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4 className="text-white font-semibold text-lg truncate">
                          {entity.name}
                        </h4>
                        <span
                          className={`text-xl font-bold ${levelClasses.text}`}
                        >
                          {entity.riskScore}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${levelClasses.bg} ${levelClasses.text}`}
                        >
                          {entity.type}
                        </span>
                        {entity.position && (
                          <span className="text-slate-400 text-sm">
                            {entity.position}
                          </span>
                        )}
                        {entity.subType && (
                          <span className="text-slate-500 text-xs">
                            {entity.subType}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-500 text-sm mt-2 truncate">
                        {entity.description}
                      </p>
                      <p className="text-slate-600 text-xs mt-1">
                        {entity.eventCount}개 이벤트
                      </p>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
}

// ============================================
// 레벨 4: 엔티티 상세 + 이벤트 타임라인
// ============================================
function EntityDetailLevel({
  entityId,
}: {
  entityId: string;
}) {
  const { state } = useRiskV2();
  const [events, setEvents] = useState<RiskEventV2[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [entityInfo, setEntityInfo] = useState<{ name: string; type: string; position: string; description: string; riskScore: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);

    // Fetch events
    const eventsPromise = riskApiV2.fetchEntityEvents(entityId);

    // Also try to get entity details from category
    const companyId = state.dealDetail?.mainCompany.id;
    const catCode = state.selectedCategoryCode;
    const entityPromise = companyId && catCode
      ? riskApiV2.fetchCategoryEntities(companyId, catCode)
      : Promise.resolve(null);

    Promise.all([eventsPromise, entityPromise]).then(([eventsRes, entityRes]) => {
      if (cancelled) return;

      if (eventsRes.success && eventsRes.data) {
        const sorted = [...eventsRes.data].sort((a, b) =>
          new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
        );
        setEvents(sorted);
      } else {
        setLoadError(eventsRes.error || 'API 서버에 연결할 수 없습니다.');
      }

      // Try to find entity info from category entities
      if (entityRes && entityRes.success && entityRes.data) {
        const found = entityRes.data.find(e => e.id === entityId);
        if (found) {
          setEntityInfo({
            name: found.name,
            type: found.type,
            position: found.position,
            description: found.description,
            riskScore: found.riskScore,
          });
          setLoading(false);
          return;
        }
      }

      // Fallback: derive from events
      if (eventsRes.success && eventsRes.data && eventsRes.data.length > 0) {
        const sorted = [...eventsRes.data].sort((a, b) =>
          new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
        );
        setEntityInfo({
          name: entityId,
          type: 'ISSUE',
          position: '',
          description: sorted[0].title,
          riskScore: sorted.reduce((s, e) => s + Math.max(e.score, 0), 0),
        });
      }

      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [entityId, state.dealDetail?.mainCompany.id, state.selectedCategoryCode]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-5 w-36 bg-slate-700/50 rounded animate-pulse" />
        {/* 타임라인 스켈레톤 */}
        <div className="relative pl-6 border-l-2 border-slate-700/30 space-y-4">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="relative">
              <div className="absolute -left-[calc(0.75rem+1px)] w-3 h-3 rounded-full bg-slate-700/40 animate-pulse" />
              <div className="bg-slate-900/40 border border-white/5 rounded-xl p-3 space-y-2 ml-2">
                <div className="flex items-center gap-2">
                  <div className="h-2.5 w-16 bg-slate-700/30 rounded animate-pulse" />
                  <div className="h-4 w-12 bg-slate-700/30 rounded-full animate-pulse" />
                </div>
                <div className="h-3.5 w-[70%] bg-slate-700/40 rounded animate-pulse" />
                <div className="h-2.5 w-full bg-slate-700/25 rounded animate-pulse" />
                <div className="h-2.5 w-[85%] bg-slate-700/20 rounded animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <ErrorState
        message="이벤트 데이터를 불러올 수 없습니다"
        detail={loadError}
      />
    );
  }

  // Use entityInfo or create from entityId
  const entity = entityInfo ?? {
    name: entityId,
    type: 'ISSUE' as const,
    position: '',
    description: '',
    riskScore: events.reduce((s, e) => s + Math.max(e.score, 0), 0),
  };

  const typeIcon =
    ENTITY_TYPE_ICONS[entity.type] ?? '\u2753';
  const level = getScoreLevel(entity.riskScore);

  return (
    <motion.div
      key="entity-detail"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: ANIMATION.pageTransition }}
    >
      {/* 상단: 엔티티 요약 */}
      <div className="flex items-start gap-6 mb-8">
        <ScoreGauge score={entity.riskScore} size={100} label="Risk Score" />
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{typeIcon}</span>
            <h2 className="text-2xl font-bold text-white">{entity.name}</h2>
          </div>
          <div className="flex items-center gap-3 mt-2">
            <RiskBadge level={level} />
            <span className="text-slate-400 text-sm">{entity.type}</span>
            {entity.position && (
              <span className="text-slate-400 text-sm">
                | {entity.position}
              </span>
            )}
          </div>
          <p className="text-slate-400 mt-3">{entity.description}</p>
        </div>
      </div>

      {/* 이벤트 타임라인 */}
      <h3 className="text-lg font-semibold text-white mb-6">
        이벤트 타임라인 ({events.length}건)
      </h3>

      {events.length === 0 ? (
        <div className="text-slate-400 text-center py-12">
          등록된 이벤트가 없습니다.
        </div>
      ) : (
        <motion.div
          className="relative ml-4"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {/* 세로 타임라인 선 */}
          <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-purple-500/30" />

          {events.map((event, idx) => {
            const sevColor =
              SEVERITY_COLORS[event.severity] ?? SEVERITY_COLORS.LOW;

            return (
              <motion.div
                key={event.id}
                variants={staggerItem}
                className="relative pl-8 pb-8 last:pb-0"
              >
                {/* 타임라인 노드 */}
                <div
                  className="absolute left-0 top-2 w-3 h-3 rounded-full bg-purple-500 border-2 border-[#0a0f1e]"
                  style={{
                    transform: 'translateX(-5px)',
                    boxShadow: '0 0 8px rgba(168, 85, 247, 0.4)',
                  }}
                />

                {/* 이벤트 카드 */}
                <GlassCard className="p-4">
                  {/* 날짜 + 뱃지 행 */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-500 text-sm">
                      {formatDate(event.publishedAt)}
                    </span>
                    <div className="flex items-center gap-2">
                      {/* 이벤트 타입 뱃지 */}
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center gap-1">
                        <span>{event.type === 'DISCLOSURE' ? '\uD83D\uDCCB' : event.type === 'NEWS' ? '\uD83D\uDCF0' : '\u26A0\uFE0F'}</span>
                        {EVENT_TYPE_LABELS[event.type] ?? event.type}
                      </span>
                      {/* 심각도 뱃지 */}
                      <span
                        className="px-2 py-0.5 rounded text-xs font-medium"
                        style={{
                          backgroundColor: sevColor.bg,
                          color: sevColor.color,
                          border: `1px solid ${sevColor.color}30`,
                        }}
                      >
                        {getSeverityLabel(event.severity)}
                      </span>
                    </div>
                  </div>

                  {/* 타이틀 */}
                  <h4 className="text-white font-semibold mb-1">
                    {event.title}
                  </h4>

                  {/* 요약 */}
                  <p className="text-slate-400 text-sm mb-3">
                    {event.summary}
                  </p>

                  {/* 하단: 점수 + 소스 */}
                  <div className="flex items-center justify-between text-xs">
                    <span
                      className={`font-bold ${
                        event.score > 0 ? 'text-red-400' : event.score < 0 ? 'text-emerald-400' : 'text-slate-400'
                      }`}
                    >
                      {event.score > 0 ? '+' : ''}
                      {event.score}점
                    </span>
                    <a
                      href={event.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-500 hover:text-purple-400 transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {event.sourceName}
                    </a>
                  </div>
                </GlassCard>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
}

// ============================================
// 메인 컴포넌트
// ============================================
export default function RiskDeepDive() {
  const { state, navigateBack, selectDeal, currentDeal, currentCompany, currentCategories } = useRiskV2();
  const {
    selectedDealId,
    selectedCompanyId,
    selectedCategoryCode,
    selectedEntityId,
    dealDetail,
  } = state;

  // 현재 선택된 데이터 조회 (context에서 가져옴)
  const selectedDeal = currentDeal;
  const selectedCompany = currentCompany;

  const selectedCategoryObj = useMemo(
    () =>
      selectedCategoryCode && dealDetail
        ? dealDetail.categories.find(c => c.code === selectedCategoryCode)
        : undefined,
    [selectedCategoryCode, dealDetail]
  );

  // Breadcrumb 아이템 빌드
  const breadcrumbItems = useMemo(() => {
    const items: BreadcrumbItem[] = [
      {
        label: '전체',
        onClick: () => navigateBack('deals'),
        active: !selectedDealId,
      },
    ];

    if (selectedDeal) {
      items.push({
        label: selectedDeal.name,
        onClick: () => {
          selectDeal(selectedDeal.id);
        },
        active: !!selectedDealId && !selectedCategoryCode,
      });
    }

    if (selectedCompany && selectedDealId) {
      // company level is part of deal view, included as deal breadcrumb
    }

    if (selectedCategoryObj) {
      items.push({
        label: selectedCategoryObj.name,
        onClick: () => navigateBack('company'),
        active: !!selectedCategoryCode && !selectedEntityId,
      });
    }

    if (selectedEntityId) {
      items.push({
        label: selectedEntityId,
        onClick: () => navigateBack('category'),
        active: !!selectedEntityId,
      });
    }

    return items;
  }, [
    selectedDealId,
    selectedDeal,
    selectedCompany,
    selectedCategoryCode,
    selectedCategoryObj,
    selectedEntityId,
    navigateBack,
    selectDeal,
  ]);

  // 현재 레벨 결정
  const currentLevel = useMemo(() => {
    if (!selectedDealId) return 'deals';
    if (!selectedCategoryCode) return 'company';
    if (!selectedEntityId) return 'category';
    return 'entity';
  }, [selectedDealId, selectedCategoryCode, selectedEntityId]);

  return (
    <div className="flex flex-col h-full">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* 콘텐츠 영역 */}
      <div className="flex-1 overflow-auto p-6">
        <AnimatePresence mode="wait">
          {currentLevel === 'deals' && (
            <div key="level-deals">
              <DealListLevel />
            </div>
          )}

          {currentLevel === 'company' && selectedDealId && (
            <div key={`level-company-${selectedDealId}`}>
              <CompanyDetailLevel
                dealId={selectedDealId}
              />
            </div>
          )}

          {currentLevel === 'category' &&
            selectedCategoryCode && (
              <div key={`level-category-${selectedCategoryCode}`}>
                <CategoryDetailLevel
                  companyId={dealDetail?.mainCompany.id ?? selectedDealId ?? ''}
                  categoryCode={selectedCategoryCode}
                />
              </div>
            )}

          {currentLevel === 'entity' && selectedEntityId && (
            <div key={`level-entity-${selectedEntityId}`}>
              <EntityDetailLevel
                entityId={selectedEntityId}
              />
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
