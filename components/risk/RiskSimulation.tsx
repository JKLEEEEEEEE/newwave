/**
 * Step 3. 리스크 모니터링 시스템 - 시나리오 시뮬레이션
 * What-If 시나리오 분석 (부산항 파업, 반도체 수요 급감 등)
 */

import React, { useState } from 'react';
import { SimulationScenario, SimulationResult, RiskDeal } from './types';
import RiskScenarioBuilder from './RiskScenarioBuilder';

interface RiskSimulationProps {
  scenarios: SimulationScenario[];
  deals: RiskDeal[];
  results: SimulationResult[];
  onRunSimulation: (scenarioId: string) => void;
}

const RiskSimulation: React.FC<RiskSimulationProps> = ({
  scenarios,
  deals,
  results,
  onRunSimulation,
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [showScenarioBuilder, setShowScenarioBuilder] = useState(false);
  const [customScenarios, setCustomScenarios] = useState<SimulationScenario[]>([]);

  // 시뮬레이션 실행
  const handleRunSimulation = async () => {
    if (!selectedScenario) return;

    setIsRunning(true);
    try {
      await onRunSimulation(selectedScenario);
    } finally {
      setTimeout(() => setIsRunning(false), 800); // 애니메이션 효과
    }
  };

  // 심각도 색상
  const getSeverityColor = (severity: string) => {
    if (severity === 'high') return 'bg-red-600';
    if (severity === 'medium') return 'bg-yellow-600';
    return 'bg-green-600';
  };

  const getSeverityLabel = (severity: string) => {
    if (severity === 'high') return '높음';
    if (severity === 'medium') return '중간';
    return '낮음';
  };

  // 점수 변화 색상
  const getDeltaColor = (delta: number) => {
    if (delta >= 15) return 'text-red-400';
    if (delta >= 10) return 'text-orange-400';
    if (delta >= 5) return 'text-yellow-400';
    return 'text-slate-400';
  };

  const allScenarios = [...scenarios, ...customScenarios];
  const selectedScenarioData = allScenarios.find(s => s.id === selectedScenario);

  // 커스텀 시나리오 생성 핸들러
  const handleScenarioCreated = (scenario: any) => {
    const newScenario: SimulationScenario = {
      id: scenario.scenarioId,
      name: scenario.name,
      description: scenario.description || '',
      affectedSectors: scenario.affectedSectors,
      impactFactors: scenario.impactFactors,
      propagationMultiplier: scenario.propagationMultiplier,
      severity: scenario.severity,
    };
    setCustomScenarios(prev => [...prev, newScenario]);
    setSelectedScenario(newScenario.id);
    setShowScenarioBuilder(false);
  };

  return (
    <>
    {/* 커스텀 시나리오 빌더 모달 */}
    {showScenarioBuilder && (
      <RiskScenarioBuilder
        onScenarioCreated={handleScenarioCreated}
        onClose={() => setShowScenarioBuilder(false)}
      />
    )}

    <div className="h-full grid grid-cols-12 gap-4">
      {/* 좌측: 시나리오 선택 */}
      <div className="col-span-4 bg-slate-800 border border-slate-700 rounded-lg p-6 overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <span className="text-2xl">🎯</span>
          <span>시나리오 선택</span>
        </h3>

        {/* 커스텀 시나리오 생성 버튼 */}
        <button
          onClick={() => setShowScenarioBuilder(true)}
          className="w-full mb-4 py-2 rounded-lg border-2 border-dashed border-slate-600
                     text-slate-400 hover:border-blue-500 hover:text-blue-400 transition-colors"
        >
          + 커스텀 시나리오 생성
        </button>

        <div className="space-y-3">
          {allScenarios.map((scenario) => (
            <div
              key={scenario.id}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                selectedScenario === scenario.id
                  ? 'border-blue-500 bg-blue-900/30'
                  : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
              }`}
              onClick={() => setSelectedScenario(scenario.id)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-slate-200">{scenario.name}</div>
                <div className={`text-xs text-white px-2 py-0.5 rounded ${getSeverityColor(scenario.severity)}`}>
                  {getSeverityLabel(scenario.severity)}
                </div>
              </div>

              <p className="text-sm text-slate-400 mb-3">{scenario.description}</p>

              <div className="space-y-1">
                <div className="text-xs text-slate-500">
                  영향 섹터: {scenario.affectedSectors.join(', ')}
                </div>
                <div className="text-xs text-slate-500">
                  전이 배수: {scenario.propagationMultiplier}x
                </div>
              </div>

              {/* 영향 요인 */}
              <div className="mt-3 flex flex-wrap gap-1">
                {Object.entries(scenario.impactFactors).map(([category, impact]) => (
                  <span
                    key={category}
                    className="text-xs bg-slate-800 text-orange-400 px-2 py-0.5 rounded border border-slate-600"
                  >
                    {category}: +{impact}점
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* 실행 버튼 */}
        <button
          onClick={handleRunSimulation}
          disabled={!selectedScenario || isRunning}
          className={`w-full mt-6 py-3 rounded-lg font-semibold transition-all ${
            selectedScenario && !isRunning
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-slate-700 text-slate-500 cursor-not-allowed'
          }`}
        >
          {isRunning ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              시뮬레이션 실행 중...
            </span>
          ) : (
            '시뮬레이션 실행'
          )}
        </button>
      </div>

      {/* 우측: 시뮬레이션 결과 */}
      <div className="col-span-8 bg-slate-800 border border-slate-700 rounded-lg p-6 overflow-y-auto">
        {results.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="text-6xl mb-4">🎯</div>
            <h3 className="text-xl font-semibold text-slate-300 mb-2">
              시나리오를 선택하고 실행하세요
            </h3>
            <p className="text-slate-500">
              선택한 시나리오가 포트폴리오에 미치는 영향을 분석합니다
            </p>
          </div>
        ) : (
          <>
            {/* 결과 헤더 */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                <span className="text-2xl">📊</span>
                <span>시뮬레이션 결과</span>
              </h3>
              {selectedScenarioData && (
                <div className="p-4 bg-blue-900/20 border border-blue-700/30 rounded-lg">
                  <div className="font-semibold text-blue-200 mb-1">
                    {selectedScenarioData.name}
                  </div>
                  <div className="text-sm text-blue-300">
                    {selectedScenarioData.description}
                  </div>
                </div>
              )}
            </div>

            {/* 전체 영향 요약 */}
            <div className="mb-6 grid grid-cols-3 gap-4">
              <div className="bg-slate-700/30 p-4 rounded-lg border border-slate-600">
                <div className="text-xs text-slate-400 mb-1">총 영향받는 딜</div>
                <div className="text-2xl font-bold text-slate-200">{results.length}개</div>
              </div>
              <div className="bg-slate-700/30 p-4 rounded-lg border border-slate-600">
                <div className="text-xs text-slate-400 mb-1">평균 점수 증가</div>
                <div className="text-2xl font-bold text-orange-400">
                  +{(results.reduce((sum, r) => sum + r.delta, 0) / results.length).toFixed(1)}점
                </div>
              </div>
              <div className="bg-slate-700/30 p-4 rounded-lg border border-slate-600">
                <div className="text-xs text-slate-400 mb-1">최대 영향 딜</div>
                <div className="text-2xl font-bold text-red-400">
                  +{Math.max(...results.map(r => r.delta))}점
                </div>
              </div>
            </div>

            {/* 딜별 영향 */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-300 mb-3">딜별 영향도</h4>
              {results
                .sort((a, b) => b.delta - a.delta)
                .map((result) => (
                  <div
                    key={result.dealId}
                    className="bg-slate-700/30 border border-slate-600 rounded-lg p-4 hover:bg-slate-700/50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="font-semibold text-slate-200">{result.dealName}</div>
                        <div className="text-xs text-slate-500 mt-1">
                          {result.originalScore}점 → {result.simulatedScore}점
                        </div>
                      </div>
                      <div className={`text-2xl font-bold ${getDeltaColor(result.delta)}`}>
                        +{result.delta}점
                      </div>
                    </div>

                    {/* 점수 변화 바 */}
                    <div className="relative h-8 bg-slate-600 rounded-lg overflow-hidden mb-3">
                      {/* 기존 점수 */}
                      <div
                        className="absolute left-0 top-0 h-full bg-blue-600 flex items-center justify-center text-xs font-medium"
                        style={{ width: `${result.originalScore}%` }}
                      >
                        {result.originalScore > 15 && <span>기존 {result.originalScore}</span>}
                      </div>
                      {/* 증가분 */}
                      <div
                        className="absolute top-0 h-full bg-red-600 flex items-center justify-center text-xs font-medium"
                        style={{
                          left: `${result.originalScore}%`,
                          width: `${result.delta}%`,
                        }}
                      >
                        {result.delta > 5 && <span>+{result.delta}</span>}
                      </div>
                    </div>

                    {/* 영향받는 카테고리 */}
                    <div className="flex flex-wrap gap-2 mb-3">
                      {result.affectedCategories.map((cat) => (
                        <span
                          key={cat.category}
                          className="text-xs bg-slate-800 text-orange-400 px-2 py-1 rounded border border-slate-600"
                        >
                          {cat.category}: +{cat.delta}점
                        </span>
                      ))}
                    </div>

                    {/* Cascade 경로 (Phase 3) */}
                    {result.cascadePath && result.cascadePath.length > 0 && (
                      <div className="mb-3 p-3 bg-slate-800/50 border border-slate-600 rounded-lg">
                        <div className="text-xs text-slate-400 mb-2 flex items-center gap-1">
                          <span>🔗</span>
                          <span className="font-semibold">Cascade 경로</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          {result.cascadePath.map((path, idx) => (
                            <span key={idx} className="flex items-center">
                              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">
                                {path}
                              </span>
                              {idx < result.cascadePath!.length - 1 && (
                                <span className="text-slate-500 mx-1">→</span>
                              )}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI 해석 */}
                    {result.interpretation && (
                      <div className="p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
                        <div className="text-xs text-blue-300">
                          <span className="font-semibold">🤖 AI 분석:</span>
                          {' '}
                          {result.interpretation}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </>
        )}
      </div>
    </div>
    </>
  );
};

export default RiskSimulation;
