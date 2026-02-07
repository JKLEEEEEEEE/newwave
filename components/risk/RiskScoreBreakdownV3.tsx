/**
 * V3: 점수 상세 분해 컴포넌트
 * 직접 리스크 vs 전이 리스크 투명화
 */

import React, { useState, useEffect } from 'react';
import { RiskStatus } from './types';
import { EMOJI_MAP, RISK_SCORE_COLORS } from './constants';
import { getScoreTextClass, getStatusTailwind } from './utils';

// V3 Score Breakdown 타입
interface ScoreBreakdownData {
  companyId: string;
  companyName: string;
  totalScore: number;
  status: RiskStatus;
  breakdown: {
    directScore: number;
    propagatedScore: number;
    directWeight: number;
    propagatedWeight: number;
  };
  categories: CategoryScore[];
  recentSignals: SignalItem[];
  propagators: PropagatorItem[];
  lastUpdated: string;
}

interface CategoryScore {
  category: string;
  score: number;
  weight: number;
  signals: number;
}

interface SignalItem {
  id: string;
  type: string;
  title: string;
  score: number;
  date: string;
}

interface PropagatorItem {
  company: string;
  relation: string;
  contribution: number;
  tier: number;
}

interface RiskScoreBreakdownV3Props {
  companyId: string;
  onRefresh?: () => void;
}

// STATUS_COLORS와 CATEGORY_ICONS는 constants.ts에서 가져옴
const getStatusColors = (status: RiskStatus) => {
  const tw = getStatusTailwind(status);
  return { bg: tw.bg, text: tw.text, border: tw.border };
};

const getCategoryIcon = (category: string): string => {
  return EMOJI_MAP.category[category as keyof typeof EMOJI_MAP.category] || '📊';
};

const RiskScoreBreakdownV3: React.FC<RiskScoreBreakdownV3Props> = ({
  companyId,
  onRefresh,
}) => {
  const [data, setData] = useState<ScoreBreakdownData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'categories' | 'signals' | 'propagation'>('categories');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/v3/companies/${companyId}/score`);
        if (!response.ok) throw new Error('Failed to fetch score breakdown');
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    if (companyId) {
      fetchData();
    }
  }, [companyId]);

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
        <div className="flex items-center justify-center gap-3">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-400">점수 분석 로딩 중...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-800 rounded-xl border border-red-700 p-6">
        <div className="text-center text-red-400">
          <span className="text-xl mb-2 block">⚠️</span>
          <p>{error || '데이터 없음'}</p>
        </div>
      </div>
    );
  }

  const { breakdown, categories, recentSignals, propagators } = data;
  const statusColors = getStatusColors(data.status);

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700">
      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold flex items-center gap-2">
            <span>📊</span>
            <span>SCORE BREAKDOWN</span>
            <span className="text-xs bg-blue-600 px-2 py-0.5 rounded">V3</span>
          </h2>
          <span className="text-slate-400 text-sm">{data.companyName}</span>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded transition-colors"
          >
            🔄 새로고침
          </button>
        )}
      </div>

      {/* 총점 & 직접/전이 분해 */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center gap-6">
          {/* 총점 */}
          <div className={`flex-shrink-0 p-4 rounded-xl ${statusColors.bg} border ${statusColors.border}`}>
            <div className="text-center">
              <div className={`text-4xl font-bold ${statusColors.text}`}>
                {data.totalScore}
              </div>
              <div className={`text-sm ${statusColors.text} mt-1`}>
                {data.status}
              </div>
            </div>
          </div>

          {/* 분해 차트 */}
          <div className="flex-1">
            <div className="flex items-center gap-4 mb-3">
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-300">직접 리스크</span>
                  <span className="text-blue-400 font-medium">{breakdown.directScore}점</span>
                </div>
                <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all"
                    style={{ width: `${Math.min(breakdown.directScore, 100)}%` }}
                  />
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  비중: {(breakdown.directWeight * 100).toFixed(0)}%
                </div>
              </div>
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-300">전이 리스크</span>
                  <span className="text-purple-400 font-medium">{breakdown.propagatedScore}점</span>
                </div>
                <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 transition-all"
                    style={{ width: `${Math.min(breakdown.propagatedScore, 100)}%` }}
                  />
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  비중: {(breakdown.propagatedWeight * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* 복합 Progress Bar */}
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden flex">
              <div
                className="h-full bg-blue-500"
                style={{ width: `${breakdown.directWeight * 100}%` }}
              />
              <div
                className="h-full bg-purple-500"
                style={{ width: `${breakdown.propagatedWeight * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="flex border-b border-slate-700">
        {[
          { id: 'categories', label: '카테고리별', icon: '📋' },
          { id: 'signals', label: '최근 신호', icon: '📡' },
          { id: 'propagation', label: '전이 경로', icon: '🔗' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-slate-700 text-white border-b-2 border-blue-500'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      <div className="p-4">
        {/* 카테고리별 점수 */}
        {activeTab === 'categories' && (
          <div className="space-y-3">
            {categories.map((cat) => {
              const icon = getCategoryIcon(cat.category) || '📊';
              const scorePercent = (cat.score / 100) * 100;

              return (
                <div key={cat.category} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{icon}</span>
                      <span className="font-medium text-slate-200">{cat.category}</span>
                      {cat.signals > 0 && (
                        <span className="text-xs bg-red-600 px-1.5 py-0.5 rounded">
                          {cat.signals} 신호
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <span className={`font-bold ${
                        cat.score >= 50 ? 'text-red-400' : cat.score >= 30 ? 'text-yellow-400' : 'text-green-400'
                      }`}>
                        {cat.score}
                      </span>
                      <span className="text-slate-500 text-sm ml-1">
                        (가중치 {(cat.weight * 100).toFixed(0)}%)
                      </span>
                    </div>
                  </div>
                  <div className="h-2 bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        cat.score >= 50 ? 'bg-red-500' : cat.score >= 30 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${scorePercent}%` }}
                    />
                  </div>
                </div>
              );
            })}

            {categories.length === 0 && (
              <div className="text-center text-slate-500 py-8">
                카테고리별 점수 데이터가 없습니다
              </div>
            )}
          </div>
        )}

        {/* 최근 신호 */}
        {activeTab === 'signals' && (
          <div className="space-y-2">
            {recentSignals.map((signal) => (
              <div key={signal.id} className="bg-slate-700/50 rounded-lg p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    signal.type === 'DART' ? 'bg-blue-600' :
                    signal.type === 'NEWS' ? 'bg-purple-600' : 'bg-slate-600'
                  }`}>
                    {signal.type}
                  </span>
                  <div>
                    <div className="text-slate-200 text-sm">{signal.title}</div>
                    <div className="text-xs text-slate-500">{signal.date}</div>
                  </div>
                </div>
                <div className={`font-bold ${
                  signal.score >= 30 ? 'text-red-400' : signal.score >= 15 ? 'text-yellow-400' : 'text-slate-400'
                }`}>
                  +{signal.score}
                </div>
              </div>
            ))}

            {recentSignals.length === 0 && (
              <div className="text-center text-slate-500 py-8">
                최근 리스크 신호가 없습니다
              </div>
            )}
          </div>
        )}

        {/* 전이 경로 */}
        {activeTab === 'propagation' && (
          <div className="space-y-2">
            {propagators.map((prop, idx) => (
              <div key={idx} className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">🔗</span>
                    <div>
                      <div className="text-slate-200 font-medium">{prop.company}</div>
                      <div className="text-xs text-slate-500">
                        {prop.relation} | Tier {prop.tier}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-purple-400 font-bold">+{prop.contribution}</div>
                    <div className="text-xs text-slate-500">전이 기여</div>
                  </div>
                </div>

                {/* 전이 시각화 */}
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  <span className="px-2 py-0.5 bg-red-900/50 rounded">{prop.company}</span>
                  <span>→</span>
                  <span className="px-2 py-0.5 bg-slate-600 rounded">{data.companyName}</span>
                </div>
              </div>
            ))}

            {propagators.length === 0 && (
              <div className="text-center text-slate-500 py-8">
                <div className="text-2xl mb-2">✅</div>
                <p>전이 리스크가 없습니다</p>
                <p className="text-xs mt-1">연결된 기업으로부터의 리스크 전이가 감지되지 않았습니다</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 푸터 */}
      <div className="px-4 py-3 border-t border-slate-700 bg-slate-800/50 text-xs text-slate-500 flex justify-between">
        <span>마지막 업데이트: {new Date(data.lastUpdated).toLocaleString('ko-KR')}</span>
        <span>Company ID: {data.companyId}</span>
      </div>
    </div>
  );
};

export default RiskScoreBreakdownV3;
