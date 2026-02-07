/**
 * Step 3. 리스크 모니터링 시스템 - 포트폴리오 요약
 */

import React from 'react';
import { RiskDeal, RiskStatus } from './types';
import { EMOJI_MAP, STATUS_THRESHOLDS } from './constants';
import { getStatusFromScore, getScoreTextClass, getStatusTailwind } from './utils';

interface RiskOverviewProps {
  deals: RiskDeal[];
  selectedDealId: string | null;
  onDealSelect: (dealId: string) => void;
}

const RiskOverview: React.FC<RiskOverviewProps> = ({
  deals,
  selectedDealId,
  onDealSelect,
}) => {
  // 포트폴리오 요약 계산
  const summary = React.useMemo(() => {
    const total = deals.length;
    const pass = deals.filter(d => d.status === 'PASS').length;
    const warning = deals.filter(d => d.status === 'WARNING').length;
    const fail = deals.filter(d => d.status === 'FAIL').length;
    const avgScore = total > 0 ? Math.round(deals.reduce((sum, d) => sum + d.score, 0) / total) : 0;

    return { total, pass, warning, fail, avgScore };
  }, [deals]);

  // 공유 상수 사용 - 통일된 기준 (0-49: PASS, 50-74: WARNING, 75+: FAIL)
  const getStatusColor = (status: RiskStatus) => {
    const tw = getStatusTailwind(status);
    return `${tw.text} ${tw.bg}`;
  };

  const getStatusIcon = (status: RiskStatus) => {
    return EMOJI_MAP.status[status];
  };

  const getScoreColor = (score: number) => {
    return getScoreTextClass(score);
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700">
      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <span>📊</span>
          <span>RISK OVERVIEW</span>
        </h2>
        <span className="text-xs text-slate-400">
          최근 업데이트: {new Date().toLocaleTimeString('ko-KR')}
        </span>
      </div>

      {/* 요약 카드 */}
      <div className="p-4 grid grid-cols-5 gap-3">
        <div className="bg-slate-700/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-slate-100">{summary.total}</div>
          <div className="text-xs text-slate-400">전체</div>
        </div>
        <div className="bg-green-900/30 rounded-lg p-3 text-center border border-green-800/50">
          <div className="text-2xl font-bold text-green-400">{summary.pass}</div>
          <div className="text-xs text-green-400">PASS</div>
        </div>
        <div className="bg-yellow-900/30 rounded-lg p-3 text-center border border-yellow-800/50">
          <div className="text-2xl font-bold text-yellow-400">{summary.warning}</div>
          <div className="text-xs text-yellow-400">WARNING</div>
        </div>
        <div className="bg-red-900/30 rounded-lg p-3 text-center border border-red-800/50">
          <div className="text-2xl font-bold text-red-400">{summary.fail}</div>
          <div className="text-xs text-red-400">FAIL</div>
        </div>
        <div className="bg-slate-700/50 rounded-lg p-3 text-center">
          <div className={`text-2xl font-bold ${getScoreColor(summary.avgScore)}`}>
            {summary.avgScore}
          </div>
          <div className="text-xs text-slate-400">평균점수</div>
        </div>
      </div>

      {/* 딜 리스트 */}
      <div className="px-4 pb-4">
        <div className="text-xs text-slate-400 mb-2 flex items-center justify-between">
          <span>포트폴리오 딜 목록</span>
          <span>클릭하여 상세 보기</span>
        </div>
        <div className="space-y-2">
          {deals.map(deal => (
            <div
              key={deal.id}
              onClick={() => onDealSelect(deal.id)}
              className={`
                p-3 rounded-lg cursor-pointer transition-all border
                ${selectedDealId === deal.id
                  ? 'bg-blue-900/30 border-blue-600'
                  : 'bg-slate-700/50 border-slate-600 hover:bg-slate-700'
                }
              `}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{getStatusIcon(deal.status)}</span>
                  <span className="font-medium">{deal.name}</span>
                  <span className="text-xs text-slate-400 bg-slate-600 px-2 py-0.5 rounded">
                    {deal.sector}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-lg font-bold ${getScoreColor(deal.score)}`}>
                    {deal.score}점
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(deal.status)}`}>
                    {deal.status}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-3 text-slate-400">
                  <span>직접: {deal.directRisk}점</span>
                  <span className="text-orange-400">전이: +{deal.propagatedRisk}점</span>
                </div>
                <span className="text-slate-500">{deal.lastUpdated}</span>
              </div>

              {deal.topFactors.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {deal.topFactors.slice(0, 3).map((factor, idx) => (
                    <span
                      key={idx}
                      className="text-xs bg-slate-600/50 text-slate-300 px-2 py-0.5 rounded"
                    >
                      {factor}
                    </span>
                  ))}
                </div>
              )}

              {deal.lastSignal && (
                <div className="mt-2 text-xs text-slate-400 truncate">
                  📌 {deal.lastSignal}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default RiskOverview;
