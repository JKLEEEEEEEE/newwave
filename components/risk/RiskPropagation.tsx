/**
 * Step 3. 리스크 모니터링 시스템 - 리스크 전이 분석 컴포넌트
 * Neo4j 관계 기반 전이 리스크 시각화
 */

import React from 'react';
import { RiskPropagation as PropagationType } from './types';

interface RiskPropagationProps {
  data: PropagationType;
}

const RiskPropagation: React.FC<RiskPropagationProps> = ({ data }) => {
  const { directRisk, propagatedRisk, totalRisk, topPropagators, paths } = data;

  // 비율 계산
  const directPercent = Math.round((directRisk / totalRisk) * 100);
  const propagatedPercent = Math.round((propagatedRisk / totalRisk) * 100);

  // 경로별 아이콘
  const getPathwayIcon = (pathway: string) => {
    const icons: Record<string, string> = {
      supply_chain: '🔗',
      ownership: '👔',
      market: '📊',
    };
    return icons[pathway] || '🔗';
  };

  // 리스크 레벨 색상
  const getRiskColor = (score: number) => {
    if (score >= 70) return 'text-red-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-green-400';
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">🌊</span>
          <span>RISK PROPAGATION ANALYSIS</span>
        </h3>
        <div className="text-sm text-slate-400">
          Neo4j 관계 분석
        </div>
      </div>

      {/* 총 리스크 점수 */}
      <div className="mb-6">
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-2xl font-bold">{totalRisk}점</span>
          <span className="text-sm text-slate-400">총 리스크 점수</span>
        </div>

        {/* 프로그레스 바 */}
        <div className="relative h-10 bg-slate-700 rounded-lg overflow-hidden">
          {/* 직접 리스크 */}
          <div
            className="absolute left-0 top-0 h-full bg-blue-600 flex items-center justify-center text-xs font-medium transition-all"
            style={{ width: `${directPercent}%` }}
          >
            {directPercent > 15 && (
              <span>직접 리스크 ({directRisk}점, {directPercent}%)</span>
            )}
          </div>

          {/* 전이 리스크 */}
          <div
            className="absolute top-0 h-full bg-orange-600 flex items-center justify-center text-xs font-medium transition-all"
            style={{ left: `${directPercent}%`, width: `${propagatedPercent}%` }}
          >
            {propagatedPercent > 10 && (
              <span>전이 리스크 ({propagatedRisk}점, {propagatedPercent}%)</span>
            )}
          </div>

          {/* 경계선 */}
          <div
            className="absolute top-0 h-full w-0.5 bg-slate-900"
            style={{ left: `${directPercent}%` }}
          />
        </div>

        {/* 범례 */}
        <div className="flex gap-4 mt-2 text-xs text-slate-400">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-blue-600 rounded"></div>
            <span>직접 리스크: 기업 자체 이슈</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-orange-600 rounded"></div>
            <span>전이 리스크: 관계사 영향</span>
          </div>
        </div>
      </div>

      {/* 주요 리스크 전이원 */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
          <span>📈</span>
          <span>주요 리스크 전이원</span>
        </h4>

        <div className="space-y-2">
          {topPropagators.length > 0 ? (
            topPropagators.map((propagator, idx) => (
              <div
                key={idx}
                className="grid grid-cols-4 gap-3 bg-slate-700/50 p-3 rounded-lg text-sm hover:bg-slate-700 transition-colors"
              >
                <div className="font-medium text-slate-200">
                  {propagator.company}
                </div>
                <div className="text-right">
                  <span className="text-orange-400 font-semibold">+{propagator.contribution}점</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>{getPathwayIcon(propagator.pathway)}</span>
                  <span className="text-slate-400">{propagator.pathway}</span>
                </div>
                <div className={`text-right font-semibold ${getRiskColor(propagator.riskScore)}`}>
                  {propagator.riskScore}점
                </div>
              </div>
            ))
          ) : (
            <div className="text-center text-slate-500 py-4">
              전이 리스크 없음
            </div>
          )}
        </div>
      </div>

      {/* 리스크 전이 경로 */}
      {paths.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <span>🔀</span>
            <span>리스크 전이 경로</span>
          </h4>

          <div className="space-y-2">
            {paths.map((pathData, idx) => (
              <div
                key={idx}
                className="bg-slate-700/30 p-3 rounded-lg border border-slate-600"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 text-sm">
                    {pathData.path.map((node, nodeIdx) => (
                      <React.Fragment key={nodeIdx}>
                        <span className="font-medium text-slate-300">{node}</span>
                        {nodeIdx < pathData.path.length - 1 && (
                          <span className="text-slate-500">→</span>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                  <div className="text-sm font-semibold text-orange-400">
                    +{pathData.risk}점
                  </div>
                </div>
                <div className="text-xs text-slate-500">
                  {getPathwayIcon(pathData.pathway)} {pathData.pathway} 경로
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 인사이트 */}
      {propagatedRisk > 0 && (
        <div className="mt-4 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
          <div className="text-xs text-blue-300">
            <span className="font-semibold">💡 인사이트:</span>
            {' '}전이 리스크가 총 리스크의 {propagatedPercent}%를 차지합니다.
            관계사 모니터링 강화가 필요합니다.
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskPropagation;
