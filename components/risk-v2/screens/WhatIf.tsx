/**
 * WhatIf - Digital Twin 스트레스 테스트 What-If 시뮬레이션 화면
 * What-If 시나리오를 선택하면 모든 딜의 점수가 실시간으로 변하는 시뮬레이션
 *
 * 1. 시나리오 선택 패널 (3개 프리셋)
 * 2. 시뮬레이션 실행 + 로딩
 * 3. Before/After 비교 + 차트 + AI 해석
 * 4. 커스텀 시나리오 빌더
 */

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

import type {
  CategoryCodeV2,
  SimulationScenarioV2,
  SimulationResultV2,
} from '../types-v2';
import {
  CATEGORY_COLORS,
  SEVERITY_COLORS,
  GRADIENTS,
  ANIMATION,
} from '../design-tokens';
import { CATEGORY_DEFINITIONS_V2 } from '../category-definitions';
import { riskApiV2 } from '../api-v2';
import { useRiskV2 } from '../context/RiskV2Context';
import {
  getScoreLevel,
  formatDelta,
  getSeverityLabel,
} from '../utils-v2';
import GlassCard from '../shared/GlassCard';
import ErrorState from '../shared/ErrorState';
import ScoreGauge from '../shared/ScoreGauge';
import RiskBadge from '../shared/RiskBadge';
import AnimatedNumber from '../shared/AnimatedNumber';

// ============================================
// 시나리오 아이콘 매핑
// ============================================
const SCENARIO_ICONS: Record<string, string> = {
  SIM_BUSAN_PORT: '\uD83D\uDEA2',     // 🚢
  SIM_TAIWAN_STRAIT: '\u2694\uFE0F',   // ⚔️
  SIM_MEMORY_CRASH: '\uD83D\uDCC9',    // 📉
};

// ============================================
// 심각도 → 한글 라벨
// ============================================
const SEVERITY_LABEL_MAP: Record<string, string> = {
  low: '낮음',
  medium: '보통',
  high: '높음',
};

// ============================================
// 시나리오 카드 컴포넌트
// ============================================
function ScenarioCard({
  scenario,
  isSelected,
  onSelect,
}: {
  scenario: SimulationScenarioV2;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const icon = SCENARIO_ICONS[scenario.id] ?? '\uD83D\uDD25';
  const sevLabel = SEVERITY_LABEL_MAP[scenario.severity] ?? scenario.severity;

  return (
    <GlassCard
      hover
      onClick={onSelect}
      gradient={isSelected ? 'purple' : 'none'}
      className={`p-5 transition-all ${
        isSelected
          ? 'ring-2 ring-purple-500 shadow-lg shadow-purple-500/10'
          : ''
      }`}
    >
      <div className="flex items-start gap-3 mb-3">
        <span className="text-3xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-bold text-lg">{scenario.name}</h3>
          <span
            className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium"
            style={{
              backgroundColor:
                scenario.severity === 'high'
                  ? SEVERITY_COLORS.CRITICAL.bg
                  : scenario.severity === 'medium'
                  ? SEVERITY_COLORS.MEDIUM.bg
                  : SEVERITY_COLORS.LOW.bg,
              color:
                scenario.severity === 'high'
                  ? SEVERITY_COLORS.CRITICAL.color
                  : scenario.severity === 'medium'
                  ? SEVERITY_COLORS.MEDIUM.color
                  : SEVERITY_COLORS.LOW.color,
            }}
          >
            {sevLabel}
          </span>
        </div>
      </div>

      <p className="text-slate-400 text-sm mb-3 leading-relaxed">
        {scenario.description}
      </p>

      {/* 영향 카테고리 태그 */}
      <div className="flex flex-wrap gap-1.5">
        {scenario.affectedCategories.map((catCode) => {
          const catColor = CATEGORY_COLORS[catCode] ?? {
            color: '#6b7280',
            bg: 'rgba(107, 114, 128, 0.15)',
          };
          const catDef = CATEGORY_DEFINITIONS_V2.find(
            (d) => d.code === catCode
          );
          return (
            <span
              key={catCode}
              className="px-2 py-0.5 rounded text-xs font-medium"
              style={{
                backgroundColor: catColor.bg,
                color: catColor.color,
              }}
            >
              {catDef?.icon} {catDef?.name ?? catCode}
            </span>
          );
        })}
      </div>

      {/* 전파 배수 */}
      <div className="mt-3 text-xs text-slate-500">
        전파 배수: x{scenario.propagationMultiplier.toFixed(1)}
      </div>
    </GlassCard>
  );
}

// ============================================
// Before/After 비교 카드
// ============================================
function BeforeAfterCard({ result }: { result: SimulationResultV2 }) {
  const originalLevel = getScoreLevel(result.originalScore);
  const simulatedLevel = getScoreLevel(result.simulatedScore);

  return (
    <GlassCard className="p-5">
      <h4 className="text-white font-semibold text-lg mb-4">
        {result.dealName}
      </h4>
      <div className="flex items-center justify-between gap-4">
        {/* Before */}
        <div className="flex flex-col items-center">
          <span className="text-slate-500 text-xs mb-2 font-medium">
            Before
          </span>
          <ScoreGauge score={result.originalScore} size={80} />
          <div className="mt-2">
            <RiskBadge level={originalLevel} size="sm" />
          </div>
        </div>

        {/* 화살표 + 델타 */}
        <div className="flex flex-col items-center gap-1">
          <motion.span
            className="text-slate-400 text-2xl"
            animate={{ x: [0, 10, 0] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          >
            &rarr;
          </motion.span>
          <span
            className={`text-lg font-bold ${
              result.delta > 0
                ? 'text-red-400'
                : result.delta < 0
                ? 'text-emerald-400'
                : 'text-slate-400'
            }`}
          >
            <AnimatedNumber
              value={result.delta}
              prefix={result.delta > 0 ? '+' : ''}
            />
          </span>
        </div>

        {/* After */}
        <div className="flex flex-col items-center">
          <span className="text-slate-500 text-xs mb-2 font-medium">
            After
          </span>
          <ScoreGauge score={result.simulatedScore} size={80} />
          <div className="mt-2">
            <RiskBadge level={simulatedLevel} size="sm" />
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

// ============================================
// 영향 카테고리 차트
// ============================================
function ImpactChart({
  results,
}: {
  results: SimulationResultV2[];
}) {
  // 모든 결과의 affectedCategories를 합산
  const chartData = useMemo(() => {
    const map = new Map<string, { name: string; delta: number; code: string }>();
    for (const result of results) {
      for (const cat of result.affectedCategories) {
        const existing = map.get(cat.code);
        if (existing) {
          existing.delta += cat.delta;
        } else {
          map.set(cat.code, {
            name: cat.name,
            delta: cat.delta,
            code: cat.code,
          });
        }
      }
    }
    return Array.from(map.values()).sort((a, b) => b.delta - a.delta);
  }, [results]);

  if (chartData.length === 0) return null;

  return (
    <GlassCard className="p-5">
      <h4 className="text-white font-semibold text-lg mb-4">
        카테고리별 영향도
      </h4>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(148, 163, 184, 0.1)"
            />
            <XAxis
              dataKey="name"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              axisLine={{ stroke: 'rgba(148, 163, 184, 0.1)' }}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              axisLine={{ stroke: 'rgba(148, 163, 184, 0.1)' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                border: '1px solid rgba(148, 163, 184, 0.2)',
                borderRadius: '12px',
                color: '#fff',
              }}
              formatter={(value: number) => [
                `${value > 0 ? '+' : ''}${value}`,
                '영향 점수',
              ]}
            />
            <Bar
              dataKey="delta"
              radius={[6, 6, 0, 0]}
              fill="#ef4444"
            >
              {chartData.map((entry) => {
                const catColor = CATEGORY_COLORS[entry.code]?.color ?? '#6b7280';
                return (
                  <rect
                    key={entry.code}
                    fill={entry.delta >= 0 ? '#ef4444' : '#10b981'}
                  />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

// ============================================
// AI 해석 패널
// ============================================
function AIInterpretationPanel({
  scenarioId,
  results,
  interpretation,
}: {
  scenarioId: string;
  results: SimulationResultV2[];
  interpretation: string;
}) {
  const interpretationText = interpretation || '시나리오 분석 결과를 검토 중입니다...';

  // 전이 경로 시각화 데이터
  const cascadePaths = useMemo(() => {
    return results.map((r) => ({
      dealName: r.dealName,
      companyName: r.dealName,  // Use dealName as company reference
      delta: r.delta,
      categories: r.affectedCategories.map((c) => c.name).join(', '),
    }));
  }, [results]);

  return (
    <GlassCard gradient="purple" className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-white font-semibold text-lg">
          AI What-If 분석
        </h4>
      </div>

      <p className="text-slate-300 text-sm leading-relaxed mb-6 whitespace-pre-line">
        {interpretationText}
      </p>

      {/* Cascade 전이 경로 */}
      <div className="border-t border-white/5 pt-4">
        <h5 className="text-slate-400 text-sm font-medium mb-3">
          Cascade 전이 경로
        </h5>
        <div className="space-y-2">
          {cascadePaths.map((path, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 text-sm"
            >
              <span className="text-purple-400 font-medium">
                {path.companyName}
              </span>
              <motion.span
                className="text-slate-500"
                animate={{ x: [0, 4, 0] }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  delay: idx * 0.2,
                }}
              >
                &rarr;
              </motion.span>
              <span className="text-slate-400 flex-1">{path.categories}</span>
              <span className="text-[10px] text-slate-600">📋📰</span>
              <span
                className={`ml-auto font-bold ${
                  path.delta > 0 ? 'text-red-400' : 'text-emerald-400'
                }`}
              >
                {path.delta > 0 ? '+' : ''}
                {path.delta}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Evidence sources */}
      <div className="border-t border-white/5 pt-4 mt-4">
        <h5 className="text-slate-400 text-sm font-medium mb-2">
          근거 데이터 소스
        </h5>
        <div className="flex flex-wrap gap-2">
          <span className="px-2 py-1 rounded-md text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
            <span>📋</span> DART 공시
          </span>
          <span className="px-2 py-1 rounded-md text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
            <span>📰</span> 뉴스
          </span>
          <span className="px-2 py-1 rounded-md text-[10px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center gap-1">
            <span>🤖</span> AI 분석
          </span>
        </div>
        <p className="text-[10px] text-slate-600 mt-2">
          위 분석 결과는 DART 공시, 뉴스 기사, KIND 자료를 기반으로 AI가 생성한 해석입니다.
        </p>
      </div>
    </GlassCard>
  );
}

// ============================================
// 커스텀 시나리오 빌더
// ============================================
function CustomScenarioBuilder({
  onRun,
}: {
  onRun: (scenario: SimulationScenarioV2) => void;
}) {
  const [title, setTitle] = useState('');
  const [impacts, setImpacts] = useState<Partial<Record<CategoryCodeV2, number>>>({});
  const [multiplier, setMultiplier] = useState(1.5);
  const [multiplierInput, setMultiplierInput] = useState('1.5');
  const [multiplierError, setMultiplierError] = useState<string | null>(null);

  // U18 - 전파 배수 유효성 검증
  const MULTIPLIER_MIN = 1.0;
  const MULTIPLIER_MAX = 3.0;

  const handleSliderChange = useCallback(
    (code: CategoryCodeV2, value: number) => {
      setImpacts((prev) => {
        const next = { ...prev };
        if (value === 0) {
          delete next[code];
        } else {
          next[code] = value;
        }
        return next;
      });
    },
    []
  );

  // U18 - 전파 배수 직접 입력 핸들러
  const handleMultiplierInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      setMultiplierInput(raw);

      const parsed = parseFloat(raw);
      if (isNaN(parsed) || raw.trim() === '') {
        setMultiplierError('숫자를 입력해 주세요');
        return;
      }
      if (parsed < MULTIPLIER_MIN) {
        setMultiplierError(`최솟값: ${MULTIPLIER_MIN}`);
        return;
      }
      if (parsed > MULTIPLIER_MAX) {
        setMultiplierError(`최댓값: ${MULTIPLIER_MAX}`);
        return;
      }
      setMultiplierError(null);
      setMultiplier(parsed);
    },
    []
  );

  // U18 - 슬라이더와 입력 필드 동기화
  const handleMultiplierSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseInt(e.target.value, 10) / 10;
      setMultiplier(val);
      setMultiplierInput(val.toFixed(1));
      setMultiplierError(null);
    },
    []
  );

  const handleRun = useCallback(() => {
    const affected = Object.keys(impacts) as CategoryCodeV2[];
    if (affected.length === 0) return;

    const scenario: SimulationScenarioV2 = {
      id: 'SIM_CUSTOM',
      name: title || '커스텀 시나리오',
      description: '사용자 정의 시나리오',
      affectedCategories: affected,
      severity: multiplier >= 2.0 ? 'high' : multiplier >= 1.5 ? 'medium' : 'low',
      propagationMultiplier: multiplier,
      impactFactors: impacts,
    };

    onRun(scenario);
  }, [title, impacts, multiplier, onRun]);

  const hasImpacts = Object.keys(impacts).length > 0;

  // U18 - 실행 가능 여부 종합 검증
  const isValid = hasImpacts && !multiplierError;

  return (
    <div className="border-t border-white/5 p-6">
      <h3 className="text-lg font-semibold text-white mb-4">
        커스텀 시나리오 빌더
      </h3>

      {/* 제목 입력 */}
      <div className="mb-4">
        <label className="block text-slate-400 text-sm mb-1">
          시나리오 이름
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="시나리오 이름을 입력하세요"
          className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50"
        />
      </div>

      {/* 카테고리별 슬라이더 */}
      <div className="mb-4">
        <div className="flex items-baseline justify-between mb-3">
          <label className="block text-slate-400 text-sm">
            카테고리별 영향도
          </label>
          <span className="text-slate-600 text-xs">범위: 0 ~ 50</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {CATEGORY_DEFINITIONS_V2.map((catDef) => {
            const catColor = CATEGORY_COLORS[catDef.code] ?? {
              color: '#6b7280',
              bg: 'rgba(107, 114, 128, 0.15)',
            };
            const val = impacts[catDef.code] ?? 0;

            return (
              <div key={catDef.code} className="flex items-center gap-3">
                <span className="text-sm w-6 text-center">{catDef.icon}</span>
                <span
                  className="text-sm w-16 truncate"
                  style={{ color: catColor.color }}
                >
                  {catDef.name}
                </span>
                <input
                  type="range"
                  min={0}
                  max={50}
                  value={val}
                  onChange={(e) =>
                    handleSliderChange(
                      catDef.code,
                      parseInt(e.target.value, 10)
                    )
                  }
                  className="flex-1 h-1.5 rounded-full appearance-none bg-white/10 accent-purple-500"
                />
                <span className="text-white text-sm font-mono w-8 text-right">
                  {val}
                </span>
              </div>
            );
          })}
        </div>
        {!hasImpacts && (
          <p className="text-slate-600 text-xs mt-2">
            하나 이상의 카테고리에 영향도를 설정해 주세요
          </p>
        )}
      </div>

      {/* 전파 배수 - 슬라이더 + 직접 입력 */}
      <div className="mb-6">
        <div className="flex items-baseline justify-between mb-2">
          <label className="block text-slate-400 text-sm">
            전파 배수 (Propagation Multiplier)
          </label>
          <span className="text-slate-600 text-xs">
            범위: {MULTIPLIER_MIN.toFixed(1)} ~ {MULTIPLIER_MAX.toFixed(1)}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min={10}
            max={30}
            value={Math.round(multiplier * 10)}
            onChange={handleMultiplierSliderChange}
            className="flex-1 h-1.5 rounded-full appearance-none bg-white/10 accent-purple-500"
          />
          <div className="flex flex-col items-end">
            <div className="flex items-center gap-1">
              <span className="text-slate-500 text-sm">x</span>
              <input
                type="text"
                inputMode="decimal"
                value={multiplierInput}
                onChange={handleMultiplierInputChange}
                className={`w-16 bg-white/5 border rounded-lg px-2 py-1 text-white text-sm text-center font-semibold focus:outline-none focus:ring-2 transition-colors ${
                  multiplierError
                    ? 'border-red-500/50 focus:ring-red-500/50'
                    : 'border-white/10 focus:ring-purple-500/50'
                }`}
              />
            </div>
            {multiplierError && (
              <span className="text-red-400 text-xs mt-1">{multiplierError}</span>
            )}
          </div>
        </div>
        <div className="flex justify-between text-xs text-slate-600 mt-1">
          <span>{MULTIPLIER_MIN.toFixed(1)}</span>
          <span>2.0</span>
          <span>{MULTIPLIER_MAX.toFixed(1)}</span>
        </div>
      </div>

      {/* 실행 버튼 */}
      <button
        onClick={handleRun}
        disabled={!isValid}
        className={`w-full py-3 rounded-xl font-semibold text-white transition-all ${
          isValid
            ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-lg shadow-purple-500/20'
            : 'bg-white/5 text-slate-500 cursor-not-allowed'
        }`}
      >
        커스텀 시뮬레이션 실행
      </button>
      {!isValid && hasImpacts && multiplierError && (
        <p className="text-red-400/70 text-xs text-center mt-2">
          전파 배수 값을 올바르게 입력해 주세요
        </p>
      )}
    </div>
  );
}

// ============================================
// 메인 WhatIf 컴포넌트
// ============================================
export default function WhatIf() {
  const { state } = useRiskV2();
  const { deals, dealDetail } = state;

  const [scenarios, setScenarios] = useState<SimulationScenarioV2[]>([]);
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [results, setResults] = useState<SimulationResultV2[] | null>(null);
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);
  const [aiInterpretation, setAiInterpretation] = useState<string>('');
  const [simulationError, setSimulationError] = useState<string | null>(null);

  // Load scenarios on mount
  useEffect(() => {
    riskApiV2.fetchScenarios().then(res => {
      if (res.success && res.data) {
        setScenarios(res.data);
      }
      setScenariosLoading(false);
    });
  }, []);

  const selectedScenario = useMemo(
    () => scenarios.find(s => s.id === selectedScenarioId),
    [scenarios, selectedScenarioId]
  );

  // 프리셋 시뮬레이션 실행 (API 연동)
  const handleRunSimulation = useCallback(async () => {
    if (!selectedScenario) return;

    setIsSimulating(true);
    setResults(null);
    setAiInterpretation('');
    setSimulationError(null);

    try {
      // Call real simulation API
      const dealIds = deals.map(d => d.id);
      const simRes = await riskApiV2.runSimulation(selectedScenario.id, dealIds);

      if (simRes.success && simRes.data) {
        setResults(simRes.data);
        setActiveScenarioId(selectedScenario.id);

        // Fetch AI interpretation (A7)
        const companyName = dealDetail?.mainCompany.name ?? deals[0]?.targetCompanyName ?? '';
        if (companyName) {
          const aiRes = await riskApiV2.fetchAIInsight(companyName);
          if (aiRes.success && aiRes.data) {
            setAiInterpretation(aiRes.data.summary + '\n\n' + aiRes.data.keyFindings.join('\n') + '\n\n' + aiRes.data.recommendation);
          }
        }
      } else {
        setSimulationError('시뮬레이션 결과를 가져오지 못했습니다.');
      }
    } catch (err) {
      console.error('[WhatIf] Simulation error:', err);
      setSimulationError(
        err instanceof Error
          ? err.message
          : '시뮬레이션 실행 중 알 수 없는 오류가 발생했습니다.'
      );
    } finally {
      setIsSimulating(false);
    }
  }, [selectedScenario, deals, dealDetail]);

  // 커스텀 시나리오 실행 (API 연동)
  const handleCustomRun = useCallback(async (scenario: SimulationScenarioV2) => {
    setSelectedScenarioId(null);
    setIsSimulating(true);
    setResults(null);
    setAiInterpretation('');
    setSimulationError(null);

    try {
      const dealIds = deals.map(d => d.id);
      const simRes = await riskApiV2.runSimulation(scenario.id, dealIds);

      if (simRes.success && simRes.data) {
        setResults(simRes.data);
        setActiveScenarioId('SIM_CUSTOM');
      } else {
        setSimulationError('커스텀 시뮬레이션 결과를 가져오지 못했습니다.');
      }
    } catch (err) {
      console.error('[WhatIf] Custom simulation error:', err);
      setSimulationError(
        err instanceof Error
          ? err.message
          : '커스텀 시뮬레이션 실행 중 알 수 없는 오류가 발생했습니다.'
      );
    } finally {
      setIsSimulating(false);
    }
  }, [deals]);

  return (
    <div className="flex flex-col h-full overflow-auto">
      {/* 헤더 */}
      <div className="px-6 pt-6 pb-2">
        <h2 className="text-xl font-bold text-white">
          What-If 시뮬레이션
        </h2>
        <p className="text-slate-400 text-sm mt-1">
          What-If 시나리오를 선택하고 실행하여 포트폴리오 영향을 분석합니다
        </p>
      </div>

      {/* 시나리오 선택 패널 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
        {scenariosLoading ? (
          <div className="col-span-3 text-center text-slate-400 py-8">시나리오 로딩 중...</div>
        ) : (
          scenarios.map((scenario) => (
            <div key={scenario.id}>
              <ScenarioCard
                scenario={scenario}
                isSelected={selectedScenarioId === scenario.id}
                onSelect={() => setSelectedScenarioId(scenario.id)}
              />
            </div>
          ))
        )}
      </div>

      {/* 시뮬레이션 실행 버튼 */}
      <div className="flex flex-col items-center py-4 px-6 gap-4">
        <button
          onClick={handleRunSimulation}
          disabled={!selectedScenario || isSimulating}
          className={`px-10 py-3 rounded-xl font-bold text-white text-lg transition-all ${
            selectedScenario && !isSimulating
              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-lg shadow-purple-500/20 hover:shadow-xl hover:shadow-purple-500/30'
              : 'bg-white/5 text-slate-500 cursor-not-allowed'
          }`}
        >
          {isSimulating ? (
            <span className="flex items-center gap-2">
              <motion.span
                animate={{ rotate: 360 }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  ease: 'linear',
                }}
                className="inline-block"
              >
                &#x2699;
              </motion.span>
              분석 중...
            </span>
          ) : (
            '시뮬레이션 실행'
          )}
        </button>

        {/* U29 - 시뮬레이션 로딩 상태 개선 */}
        <AnimatePresence>
          {isSimulating && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col items-center gap-3"
            >
              <div className="flex items-center gap-3">
                <motion.div
                  className="w-2 h-2 rounded-full bg-purple-500"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
                />
                <motion.div
                  className="w-2 h-2 rounded-full bg-indigo-500"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
                />
                <motion.div
                  className="w-2 h-2 rounded-full bg-purple-500"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
                />
              </div>
              <p className="text-slate-400 text-sm">
                시나리오를 적용하여 포트폴리오 영향을 분석하고 있습니다...
              </p>
              <p className="text-slate-500 text-xs">
                리스크 전파 경로를 계산하고 AI 해석을 생성 중입니다
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* U11 - 시뮬레이션 에러 상태 */}
      {simulationError && !isSimulating && (
        <div className="px-6 pb-4">
          <ErrorState
            message="시뮬레이션 실행에 실패했습니다"
            detail={simulationError}
            variant="card"
            onRetry={selectedScenario ? handleRunSimulation : undefined}
            className="max-w-lg mx-auto"
          />
        </div>
      )}

      {/* 시뮬레이션 결과 */}
      <AnimatePresence>
        {results && results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="px-6 pb-6"
          >
            <h3 className="text-lg font-semibold text-white mb-4">
              시뮬레이션 결과
            </h3>

            {/* Before/After 비교 + AI 해석 (2열 그리드) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              {/* 좌측: Before/After 카드 */}
              <div className="space-y-4">
                {results.map((result, idx) => (
                  <motion.div
                    key={result.dealId}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * ANIMATION.stagger }}
                  >
                    <BeforeAfterCard result={result} />
                  </motion.div>
                ))}
              </div>

              {/* 우측: AI 해석 패널 */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                {activeScenarioId && (
                  <AIInterpretationPanel
                    scenarioId={activeScenarioId}
                    results={results}
                    interpretation={aiInterpretation}
                  />
                )}
              </motion.div>
            </div>

            {/* 영향 카테고리 차트 */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <ImpactChart results={results} />
            </motion.div>

            {/* 리스크 맵 변화 (도넛 오버레이) */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="mt-4"
            >
              <RiskMapOverlay results={results} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 커스텀 시나리오 빌더 */}
      <CustomScenarioBuilder onRun={handleCustomRun} />
    </div>
  );
}

// ============================================
// 리스크 맵 변화 (도넛 오버레이)
// ============================================
function RiskMapOverlay({
  results,
}: {
  results: SimulationResultV2[];
}) {
  // 첫 번째 결과의 기업 기준으로 before/after 카테고리 비교
  const mapData = useMemo(() => {
    if (results.length === 0) return [];

    // 모든 카테고리에 대해 영향 합산
    const deltaMap = new Map<string, number>();
    for (const result of results) {
      for (const cat of result.affectedCategories) {
        const existing = deltaMap.get(cat.code) ?? 0;
        deltaMap.set(cat.code, existing + cat.delta);
      }
    }

    return CATEGORY_DEFINITIONS_V2.map((def) => {
      const delta = deltaMap.get(def.code) ?? 0;
      // Estimate before from delta for visual comparison
      return {
        code: def.code,
        name: def.name,
        icon: def.icon,
        before: Math.abs(delta) * 2,  // rough estimate for visual comparison
        after: Math.abs(delta) * 2 + delta,
        delta,
      };
    }).filter((d) => d.delta !== 0);
  }, [results]);

  if (mapData.length === 0) return null;

  const maxValue = Math.max(...mapData.map((d) => Math.max(d.before, d.after)), 1);

  return (
    <GlassCard className="p-5">
      <h4 className="text-white font-semibold text-lg mb-4">
        카테고리 리스크 맵 변화
      </h4>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
        {mapData.map((item) => {
          const catColor = CATEGORY_COLORS[item.code] ?? {
            color: '#6b7280',
            bg: 'rgba(107, 114, 128, 0.15)',
          };
          const beforePct = (item.before / maxValue) * 100;
          const afterPct = (item.after / maxValue) * 100;

          return (
            <div key={item.code} className="flex flex-col items-center gap-2">
              {/* 카테고리 아이콘 + 이름 */}
              <span className="text-lg">{item.icon}</span>
              <span
                className="text-xs font-medium"
                style={{ color: catColor.color }}
              >
                {item.name}
              </span>

              {/* 수직 비교 바 */}
              <div className="relative w-full h-20 flex items-end justify-center gap-2">
                {/* Before 바 */}
                <div className="flex flex-col items-center w-5">
                  <div
                    className="w-full rounded-t transition-all duration-500"
                    style={{
                      height: `${Math.max(beforePct, 4)}%`,
                      backgroundColor: catColor.color,
                      opacity: 0.3,
                    }}
                  />
                </div>
                {/* After 바 */}
                <div className="flex flex-col items-center w-5">
                  <div
                    className="w-full rounded-t transition-all duration-500"
                    style={{
                      height: `${Math.max(afterPct, 4)}%`,
                      backgroundColor: catColor.color,
                      opacity: 1,
                    }}
                  />
                </div>
              </div>

              {/* delta */}
              {item.delta !== 0 && (
                <span
                  className={`text-xs font-bold ${
                    item.delta > 0 ? 'text-red-400' : 'text-emerald-400'
                  }`}
                >
                  {item.delta > 0 ? '+' : ''}
                  {item.delta.toFixed(1)}
                </span>
              )}

              {/* 범례 */}
              <div className="flex items-center gap-2 text-[10px] text-slate-600">
                <span className="flex items-center gap-0.5">
                  <span
                    className="inline-block w-2 h-2 rounded-sm"
                    style={{
                      backgroundColor: catColor.color,
                      opacity: 0.3,
                    }}
                  />
                  B
                </span>
                <span className="flex items-center gap-0.5">
                  <span
                    className="inline-block w-2 h-2 rounded-sm"
                    style={{ backgroundColor: catColor.color }}
                  />
                  A
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}
