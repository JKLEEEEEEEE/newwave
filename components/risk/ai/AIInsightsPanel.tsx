/**
 * Step 3. 리스크 모니터링 시스템 - AI 통합 인사이트 패널
 * GPT-4 기반 종합 분석 및 자연어 질의
 * v2.3: 종합 인사이트 탭 추가
 */

import React, { useState } from 'react';
import Text2CypherInput from './Text2CypherInput';
import RiskSummaryCard from './RiskSummaryCard';
import SimulationInterpret from './SimulationInterpret';
import ComprehensiveInsightCard from './ComprehensiveInsightCard';
import { SimulationScenario, SimulationResult } from '../types';

interface AIInsightsPanelProps {
  dealId: string | null;
  dealName?: string;
  simulationScenario?: SimulationScenario | null;
  simulationResults?: SimulationResult[];
  showText2Cypher?: boolean;
  showSummary?: boolean;
  showSimulationInterpret?: boolean;
  showComprehensiveInsight?: boolean;  // NEW
}

const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({
  dealId,
  dealName,
  simulationScenario,
  simulationResults,
  showText2Cypher = true,
  showSummary = true,
  showSimulationInterpret = false,
  showComprehensiveInsight = true,  // 기본 활성화
}) => {
  const [activeTab, setActiveTab] = useState<'insight' | 'summary' | 'query' | 'simulation'>('insight');

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          <span>AI INSIGHTS</span>
        </h3>
        <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-3 py-1 rounded text-xs font-semibold">
          Powered by GPT-4
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="flex gap-2 mb-6 border-b border-slate-700">
        {showComprehensiveInsight && (
          <button
            onClick={() => setActiveTab('insight')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'insight'
                ? 'border-purple-500 text-purple-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            🧠 종합 인사이트
          </button>
        )}
        {showSummary && (
          <button
            onClick={() => setActiveTab('summary')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'summary'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            📝 AI 요약
          </button>
        )}
        {showText2Cypher && (
          <button
            onClick={() => setActiveTab('query')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'query'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            💬 자연어 질의
          </button>
        )}
        {showSimulationInterpret && simulationScenario && simulationResults && (
          <button
            onClick={() => setActiveTab('simulation')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'simulation'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            🔮 시나리오 해석
          </button>
        )}
      </div>

      {/* 탭 콘텐츠 */}
      <div className="min-h-[300px]">
        {activeTab === 'insight' && showComprehensiveInsight && dealName && (
          <ComprehensiveInsightCard companyName={dealName} />
        )}

        {activeTab === 'summary' && showSummary && dealId && (
          <RiskSummaryCard dealId={dealId} dealName={dealName} />
        )}

        {activeTab === 'query' && showText2Cypher && (
          <Text2CypherInput />
        )}

        {activeTab === 'simulation' &&
          showSimulationInterpret &&
          simulationScenario &&
          simulationResults && (
            <SimulationInterpret
              scenario={simulationScenario}
              results={simulationResults}
            />
          )}
      </div>

      {/* AI 기능 설명 */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-400">
          {activeTab === 'insight' && (
            <div className="flex items-start gap-2">
              <span>💡</span>
              <span>
                AI가 맥락적 해석, 패턴 인식, 교차 분석을 통해 종합 인사이트와 권고사항을 제공합니다.
                리스크 점수는 알고리즘으로 계산되며, AI는 의미 해석에 집중합니다.
              </span>
            </div>
          )}
          {activeTab === 'summary' && (
            <div className="flex items-start gap-2">
              <span>💡</span>
              <span>
                AI가 리스크 현황을 분석하여 핵심 포인트와 권장 사항을 제시합니다.
              </span>
            </div>
          )}
          {activeTab === 'query' && (
            <div className="flex items-start gap-2">
              <span>💡</span>
              <span>
                자연어로 질문하면 Neo4j Cypher 쿼리로 변환하여 그래프 데이터를 조회합니다.
              </span>
            </div>
          )}
          {activeTab === 'simulation' && (
            <div className="flex items-start gap-2">
              <span>💡</span>
              <span>
                AI가 시뮬레이션 결과를 비즈니스 관점에서 해석하고 대응 방향을 제안합니다.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AIInsightsPanel;
