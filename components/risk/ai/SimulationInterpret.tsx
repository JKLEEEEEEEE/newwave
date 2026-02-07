/**
 * Step 3. 리스크 모니터링 시스템 - 시뮬레이션 AI 해석
 * 시뮬레이션 결과를 비즈니스 언어로 해석
 */

import React, { useEffect, useState } from 'react';
import { riskApi } from '../api';
import { SimulationScenario, SimulationResult } from '../types';

interface SimulationInterpretProps {
  scenario: SimulationScenario;
  results: SimulationResult[];
}

const SimulationInterpret: React.FC<SimulationInterpretProps> = ({
  scenario,
  results,
}) => {
  const [interpretation, setInterpretation] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInterpretation();
  }, [scenario.id, results]);

  const fetchInterpretation = async () => {
    if (results.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.interpretSimulation(scenario, results);
      if (response.success) {
        setInterpretation(response.data);
      } else {
        setError(response.error || 'AI 해석 실패');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <div className="text-sm text-slate-400">AI 해석 중...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
        <div className="text-sm text-red-300">
          <span className="font-semibold">⚠️ 오류:</span> {error}
        </div>
      </div>
    );
  }

  if (!interpretation) {
    return (
      <div className="text-center py-8 text-slate-500">
        <div className="text-4xl mb-2">🔮</div>
        <div className="text-sm">시뮬레이션을 실행하세요</div>
      </div>
    );
  }

  // 통계 계산
  const avgDelta = (
    results.reduce((sum, r) => sum + r.delta, 0) / results.length
  ).toFixed(1);
  const maxDelta = Math.max(...results.map((r) => r.delta));
  const mostAffected = results.reduce((max, r) =>
    r.delta > max.delta ? r : max
  );

  return (
    <div className="space-y-4">
      {/* 시나리오 정보 */}
      <div className="p-4 bg-purple-900/20 border border-purple-700/30 rounded-lg">
        <div className="text-xs font-semibold text-purple-300 mb-1">
          🎯 시나리오:
        </div>
        <div className="font-semibold text-purple-200">{scenario.name}</div>
        <div className="text-sm text-purple-300 mt-1">{scenario.description}</div>
      </div>

      {/* AI 해석 */}
      <div className="p-4 bg-gradient-to-r from-blue-900/30 to-purple-900/30 border border-blue-700/30 rounded-lg">
        <div className="text-xs font-semibold text-blue-300 mb-3">
          🤖 AI 비즈니스 해석:
        </div>
        <div className="text-slate-200 leading-relaxed whitespace-pre-wrap">
          {interpretation}
        </div>
      </div>

      {/* 통계 요약 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-slate-700/30 p-3 rounded-lg border border-slate-600">
          <div className="text-xs text-slate-400 mb-1">평균 영향</div>
          <div className="text-lg font-bold text-orange-400">+{avgDelta}점</div>
        </div>
        <div className="bg-slate-700/30 p-3 rounded-lg border border-slate-600">
          <div className="text-xs text-slate-400 mb-1">최대 영향</div>
          <div className="text-lg font-bold text-red-400">+{maxDelta}점</div>
        </div>
        <div className="bg-slate-700/30 p-3 rounded-lg border border-slate-600">
          <div className="text-xs text-slate-400 mb-1">최대 영향 딜</div>
          <div className="text-sm font-semibold text-slate-200 truncate">
            {mostAffected.dealName}
          </div>
        </div>
      </div>

      {/* 주요 영향 */}
      <div>
        <div className="text-xs font-semibold text-slate-400 mb-2">
          📊 상위 영향 딜:
        </div>
        <div className="space-y-2">
          {results
            .sort((a, b) => b.delta - a.delta)
            .slice(0, 3)
            .map((result, idx) => (
              <div
                key={result.dealId}
                className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg border border-slate-600"
              >
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-orange-600 text-white rounded-full flex items-center justify-center text-xs font-semibold">
                    {idx + 1}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-slate-200">
                      {result.dealName}
                    </div>
                    <div className="text-xs text-slate-500">
                      {result.originalScore}점 → {result.simulatedScore}점
                    </div>
                  </div>
                </div>
                <div className="text-lg font-bold text-orange-400">
                  +{result.delta}점
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* 새로고침 버튼 */}
      <button
        onClick={fetchInterpretation}
        className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
      >
        🔄 AI 해석 다시 생성
      </button>
    </div>
  );
};

export default SimulationInterpret;
