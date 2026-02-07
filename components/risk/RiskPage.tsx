/**
 * Step 3. 리스크 모니터링 시스템 - 메인 페이지
 * Graph-First + AI Enhanced
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  RiskDeal,
  RiskSnapshot,
  SimulationScenario,
  SimulationResult,
  DealsResponse,
} from './types';
import { riskApi } from './api';
import RiskOverview from './RiskOverview';
import RiskSignals from './RiskSignals';
import RiskTimeline from './RiskTimeline';
import RiskGraph from './RiskGraph';
import RiskPropagation from './RiskPropagation';
import RiskBreakdown from './RiskBreakdown';
import RiskActionGuide from './RiskActionGuide';
import RiskSimulation from './RiskSimulation';
import RiskPrediction from './RiskPrediction';
import RiskScenarioBuilder from './RiskScenarioBuilder';
import AIInsightsPanel from './ai/AIInsightsPanel';

const RiskPage: React.FC = () => {
  // 상태 관리
  const [deals, setDeals] = useState<RiskDeal[]>([]);
  const [selectedDealId, setSelectedDealId] = useState<string | null>(null);
  const [dealDetail, setDealDetail] = useState<RiskSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'detail' | 'simulation' | 'prediction'>('overview');
  const [scenarios, setScenarios] = useState<SimulationScenario[]>([]);
  const [simulationResults, setSimulationResults] = useState<SimulationResult[]>([]);

  // 데이터 로드
  useEffect(() => {
    loadInitialData();
  }, []);

  // 선택된 딜 변경 시 상세 로드
  useEffect(() => {
    if (selectedDealId) {
      loadDealDetail(selectedDealId);
    }
  }, [selectedDealId]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [dealsRes, scenariosRes] = await Promise.all([
        riskApi.fetchDeals(),
        riskApi.fetchScenarios(),
      ]);

      if (dealsRes.success) {
        setDeals(dealsRes.data.deals);
        if (dealsRes.data.deals.length > 0) {
          setSelectedDealId(dealsRes.data.deals[0].id);
        }
      }

      if (scenariosRes.success) {
        setScenarios(scenariosRes.data);
      }
    } catch (error) {
      console.error('데이터 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDealDetail = async (dealId: string) => {
    try {
      const res = await riskApi.fetchDealDetail(dealId);
      if (res.success) {
        setDealDetail(res.data);
      }
    } catch (error) {
      console.error('딜 상세 로드 실패:', error);
    }
  };

  const handleDealSelect = useCallback((dealId: string) => {
    setSelectedDealId(dealId);
    setActiveTab('detail');
  }, []);

  const handleSimulation = async (scenarioId: string) => {
    try {
      const res = await riskApi.runSimulation(scenarioId);
      if (res.success) {
        setSimulationResults(res.data);
      }
    } catch (error) {
      console.error('시뮬레이션 실패:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">리스크 데이터 로딩 중...</p>
        </div>
      </div>
    );
  }

  const selectedDeal = deals.find(d => d.id === selectedDealId);

  return (
    <div className="h-full bg-slate-900 text-slate-100 overflow-hidden flex flex-col">
      {/* 헤더 */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold flex items-center gap-2">
              <span className="text-2xl">⚠️</span>
              <span>Risk Monitoring</span>
            </h1>
          </div>

          {/* 탭 네비게이션 */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'overview'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              📊 포트폴리오
            </button>
            <button
              onClick={() => setActiveTab('detail')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'detail'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              disabled={!selectedDealId}
            >
              🔍 상세 분석
            </button>
            <button
              onClick={() => setActiveTab('simulation')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'simulation'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              🎯 시뮬레이션
            </button>
            <button
              onClick={() => setActiveTab('prediction')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'prediction'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              disabled={!selectedDealId}
            >
              🔮 예측
            </button>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="flex-1 overflow-hidden p-4">
        {activeTab === 'overview' && (
          <div className="h-full grid grid-cols-12 gap-4">
            {/* 좌측: 포트폴리오 요약 */}
            <div className="col-span-5 flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-2">
              <RiskOverview
                deals={deals}
                selectedDealId={selectedDealId}
                onDealSelect={handleDealSelect}
              />
            </div>

            {/* 우측: 실시간 신호 (전체 포트폴리오) */}
            <div className="col-span-7 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
              <RiskSignals />
            </div>
          </div>
        )}

        {activeTab === 'detail' && selectedDeal && dealDetail && (
          <div className="h-full grid grid-cols-12 gap-4">
            {/* 좌측: 그래프 + 전이 분석 + 타임라인 */}
            <div className="col-span-5 flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-2">
              <RiskGraph
                data={dealDetail.data.supplyChain}
                companyName={selectedDeal.name}
              />
              <RiskPropagation data={dealDetail.data.propagation} />
              <RiskTimeline events={dealDetail.data.timeline} />
            </div>

            {/* 우측: AI 인사이트 + 카테고리 분석 */}
            <div className="col-span-7 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
              {/* AI 종합 인사이트 패널 */}
              <AIInsightsPanel
                dealId={selectedDeal.id}
                dealName={selectedDeal.name}
                showComprehensiveInsight={true}
                showSummary={true}
                showText2Cypher={true}
              />
              <RiskBreakdown scores={dealDetail.data.categoryScores} />
            </div>
          </div>
        )}

        {activeTab === 'simulation' && (
          <div className="h-full">
            <RiskSimulation
              scenarios={scenarios}
              deals={deals}
              results={simulationResults}
              onRunSimulation={handleSimulation}
            />
          </div>
        )}

        {activeTab === 'prediction' && selectedDeal && (
          <div className="h-full overflow-y-auto custom-scrollbar">
            <RiskPrediction
              dealId={selectedDeal.id}
              dealName={selectedDeal.name}
              currentScore={selectedDeal.score}
            />
          </div>
        )}
      </main>

      {/* 푸터 상태바 */}
      <footer className="bg-slate-800 border-t border-slate-700 px-6 py-2">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              Neo4j 연결됨
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              AI 서비스 활성화
            </span>
          </div>
          <div>
            마지막 업데이트: {new Date().toLocaleTimeString('ko-KR')}
          </div>
        </div>
      </footer>
    </div>
  );
};

export default RiskPage;
