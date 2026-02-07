'use client';

import React from 'react';
import { DealDetail, RiskLevel, Trend } from './types';

interface DealSummaryCardProps {
  deal: DealDetail;
}

const RiskLevelBadge: React.FC<{ level: RiskLevel }> = ({ level }) => {
  const config: Record<RiskLevel, { label: string; bg: string; text: string }> = {
    PASS: {
      label: '정상',
      bg: 'bg-green-100 dark:bg-green-900',
      text: 'text-green-800 dark:text-green-200',
    },
    WARNING: {
      label: '주의',
      bg: 'bg-yellow-100 dark:bg-yellow-900',
      text: 'text-yellow-800 dark:text-yellow-200',
    },
    FAIL: {
      label: '위험',
      bg: 'bg-red-100 dark:bg-red-900',
      text: 'text-red-800 dark:text-red-200',
    },
  };

  const c = config[level];

  return (
    <span className={`px-3 py-1 text-sm font-semibold rounded-full ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
};

const TrendIndicator: React.FC<{ trend: Trend }> = ({ trend }) => {
  const config: Record<Trend, { icon: string; label: string; color: string }> = {
    UP: { icon: '↑', label: '상승', color: 'text-red-500' },
    DOWN: { icon: '↓', label: '하락', color: 'text-green-500' },
    STABLE: { icon: '→', label: '유지', color: 'text-gray-500' },
  };

  const c = config[trend];

  return (
    <span className={`flex items-center gap-1 text-sm ${c.color}`}>
      <span className="text-lg">{c.icon}</span>
      <span>{c.label}</span>
    </span>
  );
};

const getScoreColor = (score: number): string => {
  if (score >= 75) return 'text-red-600 dark:text-red-400';
  if (score >= 50) return 'text-orange-600 dark:text-orange-400';
  if (score >= 25) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-green-600 dark:text-green-400';
};

const ScoreGauge: React.FC<{ score: number }> = ({ score }) => {
  const getGradient = (s: number) => {
    if (s >= 75) return 'from-red-500 to-red-600';
    if (s >= 50) return 'from-orange-500 to-orange-600';
    if (s >= 25) return 'from-yellow-500 to-yellow-600';
    return 'from-green-500 to-green-600';
  };

  return (
    <div className="relative w-32 h-32">
      {/* Background circle */}
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="56"
          fill="none"
          stroke="currentColor"
          strokeWidth="12"
          className="text-gray-200 dark:text-gray-700"
        />
        <circle
          cx="64"
          cy="64"
          r="56"
          fill="none"
          stroke="url(#scoreGradient)"
          strokeWidth="12"
          strokeDasharray={`${(score / 100) * 352} 352`}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" className={`${getGradient(score).split(' ')[0].replace('from-', 'stop-')}`} />
            <stop offset="100%" className={`${getGradient(score).split(' ')[1].replace('to-', 'stop-')}`} />
          </linearGradient>
        </defs>
      </svg>
      {/* Score text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl font-bold ${getScoreColor(score)}`}>{score}</span>
        <span className="text-xs text-gray-500 dark:text-gray-400">/ 100</span>
      </div>
    </div>
  );
};

export const DealSummaryCard: React.FC<DealSummaryCardProps> = ({ deal }) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {deal.name}
          </h2>
          <p className="text-gray-500 dark:text-gray-400">{deal.sector}</p>
        </div>
        <RiskLevelBadge level={deal.riskLevel} />
      </div>

      <div className="flex items-center gap-8">
        <ScoreGauge score={deal.score} />

        <div className="flex-1 space-y-4">
          {/* Score breakdown */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-sm text-gray-500 dark:text-gray-400">직접 리스크</div>
              <div className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {deal.breakdown.direct}
              </div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-sm text-gray-500 dark:text-gray-400">전이 리스크</div>
              <div className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {deal.breakdown.propagated}
              </div>
            </div>
          </div>

          {/* Trend */}
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <span className="text-sm text-gray-500 dark:text-gray-400">트렌드</span>
            <TrendIndicator trend={deal.trend} />
          </div>
        </div>
      </div>

      {/* Evidence summary */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-6 text-sm text-gray-600 dark:text-gray-400">
          <span>관련 뉴스: {deal.evidence.totalNews}건</span>
          <span>관련 공시: {deal.evidence.totalDisclosures}건</span>
          <span>관련 이벤트: {deal.topEvents.length}건</span>
          <span>관련 인물: {deal.topPersons.length}명</span>
        </div>
      </div>
    </div>
  );
};

export default DealSummaryCard;
