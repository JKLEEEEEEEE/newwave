/**
 * AI 종합 인사이트 카드 (v2.3)
 * 리스크 점수가 아닌 맥락적 해석, 패턴 인식, 교차 분석, 권고사항 제공
 */

import React, { useEffect, useState } from 'react';
import { riskApi } from '../api';
import { ComprehensiveInsightResponse } from '../types';

interface ComprehensiveInsightCardProps {
  companyName: string;
}

const ComprehensiveInsightCard: React.FC<ComprehensiveInsightCardProps> = ({ companyName }) => {
  const [data, setData] = useState<ComprehensiveInsightResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['summary', 'concerns']));

  useEffect(() => {
    if (companyName) {
      fetchInsight();
    }
  }, [companyName]);

  const fetchInsight = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchComprehensiveInsight(companyName);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'AI 인사이트 생성 실패');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <div className="text-sm text-slate-400">AI 종합 분석 중...</div>
          <div className="text-xs text-slate-500 mt-1">맥락 분석, 패턴 인식, 교차 분석 수행</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
        <div className="text-sm text-red-300">
          <span className="font-semibold">오류:</span> {error}
        </div>
        <button
          onClick={fetchInsight}
          className="mt-3 px-4 py-2 bg-red-700/30 hover:bg-red-700/50 text-red-300 rounded text-sm"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-8 text-slate-500">
        <div className="text-4xl mb-2">🔍</div>
        <div className="text-sm">기업을 선택하면 AI 종합 인사이트를 제공합니다</div>
      </div>
    );
  }

  const { insight } = data;
  const confidencePercent = Math.round(insight.confidence * 100);

  return (
    <div className="space-y-4 text-sm">
      {/* 헤더: 기업명 + 신뢰도 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-white">{data.company}</span>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            data.riskLevel === 'PASS' ? 'bg-green-600/30 text-green-300' :
            data.riskLevel === 'WARNING' ? 'bg-yellow-600/30 text-yellow-300' :
            'bg-red-600/30 text-red-300'
          }`}>
            {data.riskLevel} · {data.riskScore}점
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">신뢰도</span>
          <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${confidencePercent >= 70 ? 'bg-green-500' : confidencePercent >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
          <span className="text-slate-300">{confidencePercent}%</span>
        </div>
      </div>

      {/* Executive Summary */}
      <Section
        title="Executive Summary"
        icon="📋"
        expanded={expandedSections.has('summary')}
        onToggle={() => toggleSection('summary')}
      >
        <div className="p-4 bg-gradient-to-r from-blue-900/30 to-purple-900/30 border border-blue-700/30 rounded-lg">
          <p className="text-slate-200 leading-relaxed">{insight.executive_summary}</p>
        </div>
      </Section>

      {/* Context Analysis */}
      <Section
        title="맥락 분석"
        icon="🌐"
        expanded={expandedSections.has('context')}
        onToggle={() => toggleSection('context')}
      >
        <div className="space-y-3">
          <div className="p-3 bg-slate-700/30 rounded-lg">
            <div className="text-xs text-slate-400 mb-1">업계 상황</div>
            <div className="text-slate-300">{insight.context_analysis.industry_context}</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded-lg">
            <div className="text-xs text-slate-400 mb-1">시기적 의미</div>
            <div className="text-slate-300">{insight.context_analysis.timing_significance}</div>
          </div>
        </div>
      </Section>

      {/* Cross-Signal Analysis */}
      <Section
        title="교차 신호 분석"
        icon="🔀"
        expanded={expandedSections.has('cross')}
        onToggle={() => toggleSection('cross')}
      >
        <div className="space-y-3">
          {/* Patterns */}
          <div>
            <div className="text-xs text-slate-400 mb-2">감지된 패턴</div>
            <div className="flex flex-wrap gap-2">
              {insight.cross_signal_analysis.patterns_detected.map((pattern, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-purple-600/20 border border-purple-600/30 rounded text-purple-300 text-xs"
                >
                  {pattern}
                </span>
              ))}
            </div>
          </div>
          {/* Correlations */}
          <div className="p-3 bg-slate-700/30 rounded-lg">
            <div className="text-xs text-slate-400 mb-1">상관관계</div>
            <div className="text-slate-300">{insight.cross_signal_analysis.correlations}</div>
          </div>
          {/* Anomalies */}
          {insight.cross_signal_analysis.anomalies && (
            <div className="p-3 bg-orange-900/20 border border-orange-700/30 rounded-lg">
              <div className="text-xs text-orange-400 mb-1">⚠️ 이상 징후</div>
              <div className="text-orange-300">{insight.cross_signal_analysis.anomalies}</div>
            </div>
          )}
        </div>
      </Section>

      {/* Stakeholder Insights */}
      <Section
        title="이해관계자 인사이트"
        icon="👥"
        expanded={expandedSections.has('stakeholder')}
        onToggle={() => toggleSection('stakeholder')}
      >
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-slate-700/30 rounded-lg">
            <div className="text-xs text-slate-400 mb-1">👔 임원/지배구조</div>
            <div className="text-slate-300">{insight.stakeholder_insights.executive_concerns}</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded-lg">
            <div className="text-xs text-slate-400 mb-1">📊 주주 동향</div>
            <div className="text-slate-300">{insight.stakeholder_insights.shareholder_dynamics}</div>
          </div>
        </div>
      </Section>

      {/* Key Concerns */}
      <Section
        title="핵심 우려사항"
        icon="🚨"
        expanded={expandedSections.has('concerns')}
        onToggle={() => toggleSection('concerns')}
        highlight
      >
        <div className="space-y-3">
          {insight.key_concerns.map((concern, idx) => (
            <div key={idx} className="p-4 bg-red-900/10 border border-red-700/30 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-6 h-6 bg-red-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <div className="font-medium text-red-300 mb-1">{concern.issue}</div>
                  <div className="text-slate-400 text-xs mb-2">왜 중요한가: {concern.why_it_matters}</div>
                  <div className="text-yellow-400 text-xs">👁 주시할 점: {concern.watch_for}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Recommendations */}
      <Section
        title="권고사항"
        icon="💡"
        expanded={expandedSections.has('recommendations')}
        onToggle={() => toggleSection('recommendations')}
      >
        <div className="space-y-4">
          {/* Immediate Actions */}
          <div>
            <div className="text-xs font-medium text-green-400 mb-2">🚀 즉시 조치</div>
            <div className="space-y-1">
              {insight.recommendations.immediate_actions.map((action, idx) => (
                <div key={idx} className="flex items-center gap-2 text-slate-300">
                  <span className="text-green-500">•</span>
                  {action}
                </div>
              ))}
            </div>
          </div>
          {/* Monitoring Focus */}
          <div>
            <div className="text-xs font-medium text-blue-400 mb-2">🔍 모니터링 집중</div>
            <div className="space-y-1">
              {insight.recommendations.monitoring_focus.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 text-slate-300">
                  <span className="text-blue-500">•</span>
                  {item}
                </div>
              ))}
            </div>
          </div>
          {/* Due Diligence */}
          <div>
            <div className="text-xs font-medium text-purple-400 mb-2">📋 추가 실사 필요</div>
            <div className="space-y-1">
              {insight.recommendations.due_diligence_points.map((point, idx) => (
                <div key={idx} className="flex items-center gap-2 text-slate-300">
                  <span className="text-purple-500">•</span>
                  {point}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* Limitations */}
      {insight.analysis_limitations && (
        <div className="p-3 bg-slate-800 border border-slate-600 rounded-lg text-xs text-slate-400">
          <span className="text-slate-500">⚠️ 분석 한계:</span> {insight.analysis_limitations}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-500">
          생성: {new Date(data.generatedAt).toLocaleString('ko-KR')}
          {!data.aiServiceAvailable && (
            <span className="ml-2 text-yellow-500">(Mock 데이터)</span>
          )}
        </div>
        <button
          onClick={fetchInsight}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-xs font-medium transition-colors"
        >
          🔄 다시 분석
        </button>
      </div>
    </div>
  );
};

// 접이식 섹션 컴포넌트
interface SectionProps {
  title: string;
  icon: string;
  expanded: boolean;
  onToggle: () => void;
  highlight?: boolean;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, icon, expanded, onToggle, highlight, children }) => (
  <div className={`border rounded-lg overflow-hidden ${highlight ? 'border-red-700/50' : 'border-slate-700'}`}>
    <button
      onClick={onToggle}
      className={`w-full px-4 py-3 flex items-center justify-between text-left transition-colors ${
        highlight ? 'bg-red-900/20 hover:bg-red-900/30' : 'bg-slate-800 hover:bg-slate-700'
      }`}
    >
      <div className="flex items-center gap-2 font-medium">
        <span>{icon}</span>
        <span>{title}</span>
      </div>
      <span className="text-slate-400 text-lg">{expanded ? '−' : '+'}</span>
    </button>
    {expanded && (
      <div className="p-4 bg-slate-800/50">
        {children}
      </div>
    )}
  </div>
);

export default ComprehensiveInsightCard;
