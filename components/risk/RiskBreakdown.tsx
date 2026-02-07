/**
 * Step 3. 리스크 모니터링 시스템 - 카테고리별 리스크 분석
 * 8대 카테고리 점수 분석 (14개 → 8개 집중화)
 */

import React from 'react';
import { CategoryScore } from './types';

interface RiskBreakdownProps {
  scores: CategoryScore[];
}

const RiskBreakdown: React.FC<RiskBreakdownProps> = ({ scores }) => {
  // 리스크 레벨별 색상
  const getScoreColor = (score: number) => {
    if (score >= 70) return 'bg-red-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getScoreTextColor = (score: number) => {
    if (score >= 70) return 'text-red-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-green-400';
  };

  // 트렌드 아이콘
  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return '📈';
    if (trend === 'down') return '📉';
    return '➡️';
  };

  const getTrendColor = (trend: string) => {
    if (trend === 'up') return 'text-red-400';
    if (trend === 'down') return 'text-green-400';
    return 'text-slate-400';
  };

  // 총 가중 점수
  const totalWeightedScore = scores.reduce((sum, s) => sum + s.weightedScore, 0);

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">📊</span>
          <span>RISK BREAKDOWN</span>
        </h3>
        <div className="text-sm">
          <span className="text-slate-400">가중 총점:</span>
          {' '}
          <span className={`font-bold ${getScoreTextColor(totalWeightedScore)}`}>
            {totalWeightedScore}점
          </span>
        </div>
      </div>

      {/* 카테고리별 점수 */}
      <div className="space-y-4">
        {scores.map((category) => (
          <div
            key={category.categoryId}
            className="bg-slate-700/30 border border-slate-600 rounded-lg p-4 hover:bg-slate-700/50 transition-colors"
          >
            {/* 카테고리 헤더 */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">{category.icon}</span>
                <div>
                  <div className="font-semibold text-slate-200">
                    {category.name}
                  </div>
                  <div className="text-xs text-slate-400">
                    가중치 {(category.weight * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* 트렌드 */}
                <div className={`text-sm ${getTrendColor(category.trend)}`}>
                  {getTrendIcon(category.trend)}
                </div>

                {/* 점수 */}
                <div className="text-right">
                  <div className={`text-2xl font-bold ${getScoreTextColor(category.score)}`}>
                    {category.score}
                  </div>
                  <div className="text-xs text-slate-500">
                    가중: {category.weightedScore}점
                  </div>
                </div>
              </div>
            </div>

            {/* 점수 바 */}
            <div className="relative h-2 bg-slate-600 rounded-full overflow-hidden mb-3">
              <div
                className={`absolute left-0 top-0 h-full ${getScoreColor(category.score)} transition-all duration-500`}
                style={{ width: `${category.score}%` }}
              />
            </div>

            {/* 주요 이벤트 */}
            {category.topEvents.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {category.topEvents.map((event, idx) => (
                  <span
                    key={idx}
                    className="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-600"
                  >
                    {event}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 범례 */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <div className="grid grid-cols-3 gap-3 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-slate-400">안전 (0-49점)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
            <span className="text-slate-400">주의 (50-69점)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span className="text-slate-400">위험 (70-100점)</span>
          </div>
        </div>
      </div>

      {/* 인사이트 */}
      <div className="mt-4 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
        <div className="text-xs text-blue-300">
          <span className="font-semibold">💡 카테고리 분석:</span>
          {' '}
          {scores.filter(s => s.score >= 70).length}개 카테고리가 위험 수준입니다.
          {' '}
          {scores.find(s => s.score === Math.max(...scores.map(sc => sc.score)))?.name}이 가장 높은 리스크를 보입니다.
        </div>
      </div>
    </div>
  );
};

export default RiskBreakdown;
