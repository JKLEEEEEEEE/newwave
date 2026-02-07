/**
 * 커스텀 시나리오 빌더
 * 사용자 정의 What-If 시나리오 생성
 * Risk Monitoring System - Phase 3
 */

import React, { useState, useCallback } from 'react';
import { RiskCategoryId, RISK_CATEGORIES } from './types';

interface CustomScenario {
  name: string;
  description: string;
  affectedSectors: string[];
  impactFactors: Record<string, number>;
  propagationMultiplier: number;
  severity: 'low' | 'medium' | 'high';
}

interface Props {
  onScenarioCreated: (scenario: CustomScenario & { scenarioId: string }) => void;
  onClose: () => void;
  onRunSimulation?: (scenario: CustomScenario) => void;
}

const SECTORS = [
  { id: 'semiconductor', label: '반도체', icon: '💻' },
  { id: 'automotive', label: '자동차', icon: '🚗' },
  { id: 'logistics', label: '물류', icon: '🚚' },
  { id: 'finance', label: '금융', icon: '💰' },
  { id: 'construction', label: '건설', icon: '🏗️' },
  { id: 'retail', label: '유통', icon: '🛒' },
  { id: 'battery', label: '배터리', icon: '🔋' },
  { id: 'pharma', label: '제약', icon: '💊' },
];

const CATEGORIES: { id: RiskCategoryId; label: string; color: string }[] = [
  { id: 'supply_chain', label: '공급망', color: 'blue' },
  { id: 'market', label: '시장', color: 'green' },
  { id: 'legal', label: '법률', color: 'red' },
  { id: 'operational', label: '운영', color: 'yellow' },
  { id: 'financial', label: '재무', color: 'purple' },
];

const MULTIPLIERS = [1.0, 1.2, 1.5, 2.0, 2.5];

const RiskScenarioBuilder: React.FC<Props> = ({
  onScenarioCreated,
  onClose,
  onRunSimulation,
}) => {
  const [scenario, setScenario] = useState<CustomScenario>({
    name: '',
    description: '',
    affectedSectors: [],
    impactFactors: {},
    propagationMultiplier: 1.5,
    severity: 'medium',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 섹터 토글
  const toggleSector = useCallback((sectorId: string) => {
    setScenario((prev) => ({
      ...prev,
      affectedSectors: prev.affectedSectors.includes(sectorId)
        ? prev.affectedSectors.filter((s) => s !== sectorId)
        : [...prev.affectedSectors, sectorId],
    }));
  }, []);

  // 영향도 변경
  const setImpact = useCallback((category: string, value: number) => {
    setScenario((prev) => ({
      ...prev,
      impactFactors: { ...prev.impactFactors, [category]: value },
    }));
  }, []);

  // 심각도 변경
  const setSeverity = useCallback((severity: 'low' | 'medium' | 'high') => {
    setScenario((prev) => ({ ...prev, severity }));
  }, []);

  // 유효성 검사
  const validateScenario = (): boolean => {
    if (!scenario.name.trim()) {
      setError('시나리오 이름을 입력해주세요.');
      return false;
    }
    if (scenario.affectedSectors.length === 0) {
      setError('영향 섹터를 최소 1개 이상 선택해주세요.');
      return false;
    }
    const hasImpact = Object.values(scenario.impactFactors).some((v) => v > 0);
    if (!hasImpact) {
      setError('카테고리별 영향도를 설정해주세요.');
      return false;
    }
    setError(null);
    return true;
  };

  // 제출
  const handleSubmit = async () => {
    if (!validateScenario()) return;

    setIsSubmitting(true);
    try {
      const response = await fetch('/api/v2/scenarios/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: scenario.name,
          description: scenario.description,
          affectedSectors: scenario.affectedSectors,
          impactFactors: scenario.impactFactors,
          propagationMultiplier: scenario.propagationMultiplier,
          severity: scenario.severity,
        }),
      });

      const data = await response.json();
      if (data.success) {
        onScenarioCreated({
          ...scenario,
          scenarioId: data.scenarioId,
        });
      } else {
        setError(data.error || '시나리오 생성 실패');
      }
    } catch (err) {
      setError('서버 연결 실패');
      console.error('시나리오 생성 실패:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // 바로 시뮬레이션 실행
  const handleRunSimulation = () => {
    if (!validateScenario()) return;
    if (onRunSimulation) {
      onRunSimulation(scenario);
    }
  };

  // 총 영향도 계산
  const totalImpact = Object.values(scenario.impactFactors).reduce(
    (sum, v) => sum + v,
    0
  );

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <span className="text-2xl">🎯</span>
            <span>커스텀 시나리오 생성</span>
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xl"
          >
            ✕
          </button>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* 시나리오 이름 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            시나리오 이름 *
          </label>
          <input
            type="text"
            value={scenario.name}
            onChange={(e) =>
              setScenario((prev) => ({ ...prev, name: e.target.value }))
            }
            placeholder="예: 중국 희토류 수출 제한"
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg
                       text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* 시나리오 설명 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            설명 (선택)
          </label>
          <textarea
            value={scenario.description}
            onChange={(e) =>
              setScenario((prev) => ({ ...prev, description: e.target.value }))
            }
            placeholder="시나리오에 대한 상세 설명..."
            rows={2}
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg
                       text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* 심각도 선택 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            심각도
          </label>
          <div className="flex gap-2">
            {(['low', 'medium', 'high'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverity(sev)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                  scenario.severity === sev
                    ? sev === 'high'
                      ? 'bg-red-600 text-white'
                      : sev === 'medium'
                      ? 'bg-yellow-600 text-white'
                      : 'bg-green-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {sev === 'low' ? '낮음' : sev === 'medium' ? '중간' : '높음'}
              </button>
            ))}
          </div>
        </div>

        {/* 영향 섹터 선택 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            영향 섹터 선택 *
          </label>
          <div className="grid grid-cols-4 gap-2">
            {SECTORS.map((sector) => (
              <button
                key={sector.id}
                onClick={() => toggleSector(sector.id)}
                className={`p-3 rounded-lg border-2 transition-all text-center ${
                  scenario.affectedSectors.includes(sector.id)
                    ? 'border-blue-500 bg-blue-900/30'
                    : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
                }`}
              >
                <span className="text-2xl block mb-1">{sector.icon}</span>
                <div className="text-xs">{sector.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* 카테고리별 영향도 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            카테고리별 영향도 *
            <span className="text-slate-500 ml-2">
              (총 +{totalImpact}점)
            </span>
          </label>
          <div className="space-y-4">
            {CATEGORIES.map((cat) => (
              <div key={cat.id} className="flex items-center gap-4">
                <span className="w-16 text-sm text-slate-400 flex items-center gap-1">
                  {RISK_CATEGORIES[cat.id]?.icon || ''}
                  <span>{cat.label}</span>
                </span>
                <input
                  type="range"
                  min="0"
                  max="30"
                  value={scenario.impactFactors[cat.id] || 0}
                  onChange={(e) => setImpact(cat.id, parseInt(e.target.value))}
                  className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer
                             [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4
                             [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full
                             [&::-webkit-slider-thumb]:bg-blue-500"
                />
                <span className="w-16 text-right text-orange-400 font-mono">
                  +{scenario.impactFactors[cat.id] || 0}점
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 전이 배수 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            전이 배수
            <span className="text-slate-500 ml-2 font-normal">
              (공급망 전이 시 적용되는 배수)
            </span>
          </label>
          <div className="flex gap-2">
            {MULTIPLIERS.map((mult) => (
              <button
                key={mult}
                onClick={() =>
                  setScenario((prev) => ({
                    ...prev,
                    propagationMultiplier: mult,
                  }))
                }
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                  scenario.propagationMultiplier === mult
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {mult}x
              </button>
            ))}
          </div>
        </div>

        {/* 미리보기 */}
        {scenario.name && scenario.affectedSectors.length > 0 && totalImpact > 0 && (
          <div className="mb-6 p-4 bg-slate-700/30 border border-slate-600 rounded-lg">
            <div className="text-xs text-slate-400 mb-2">시나리오 미리보기</div>
            <div className="font-semibold text-slate-200">{scenario.name}</div>
            <div className="text-sm text-slate-400 mt-1">
              영향 섹터: {scenario.affectedSectors.map(s =>
                SECTORS.find(sec => sec.id === s)?.label || s
              ).join(', ')}
            </div>
            <div className="text-sm text-slate-400">
              총 영향도: +{totalImpact}점 / 전이 배수: {scenario.propagationMultiplier}x
            </div>
          </div>
        )}

        {/* 버튼 */}
        <div className="flex gap-3">
          {onRunSimulation && (
            <button
              onClick={handleRunSimulation}
              className="flex-1 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold
                         rounded-lg transition-colors"
            >
              바로 시뮬레이션
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold
                       rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? '생성 중...' : '시나리오 저장'}
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-slate-300
                       rounded-lg transition-colors"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
};

export default RiskScenarioBuilder;
