/**
 * Step 3. 리스크 모니터링 시스템 - AI 리스크 요약 카드
 * GPT-4 기반 리스크 현황 한 줄 요약 및 핵심 포인트
 */

import React, { useEffect, useState } from 'react';
import { riskApi } from '../api';
import { AIRiskSummary } from '../types';

interface RiskSummaryCardProps {
  dealId: string;
  dealName?: string;
}

const RiskSummaryCard: React.FC<RiskSummaryCardProps> = ({ dealId, dealName }) => {
  const [summary, setSummary] = useState<AIRiskSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary();
  }, [dealId]);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.generateRiskSummary(dealId);
      if (response.success) {
        setSummary(response.data);
      } else {
        setError(response.error || 'AI 요약 생성 실패');
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
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <div className="text-sm text-slate-400">AI 분석 중...</div>
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

  if (!summary) {
    return (
      <div className="text-center py-8 text-slate-500">
        <div className="text-4xl mb-2">📝</div>
        <div className="text-sm">요약 정보가 없습니다</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 한 줄 요약 */}
      <div className="p-4 bg-gradient-to-r from-blue-900/30 to-purple-900/30 border border-blue-700/30 rounded-lg">
        <div className="text-xs font-semibold text-blue-300 mb-2">
          📝 AI 리스크 요약
          {dealName && (
            <span className="ml-2 text-slate-400">({dealName})</span>
          )}
        </div>
        <div className="text-slate-200 leading-relaxed">{summary.summary}</div>
      </div>

      {/* 핵심 포인트 */}
      <div>
        <div className="text-xs font-semibold text-slate-400 mb-3">
          🎯 핵심 포인트:
        </div>
        <div className="space-y-2">
          {summary.keyPoints.map((point, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg border border-slate-600"
            >
              <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-semibold">
                {idx + 1}
              </div>
              <div className="flex-1 text-sm text-slate-300">{point}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 권장 사항 */}
      <div className="p-4 bg-green-900/20 border border-green-700/30 rounded-lg">
        <div className="text-xs font-semibold text-green-300 mb-2">
          💡 권장 사항:
        </div>
        <div className="text-sm text-green-200">{summary.recommendation}</div>
      </div>

      {/* 새로고침 버튼 */}
      <button
        onClick={fetchSummary}
        className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
      >
        🔄 AI 요약 다시 생성
      </button>
    </div>
  );
};

export default RiskSummaryCard;
