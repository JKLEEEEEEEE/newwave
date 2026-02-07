/**
 * Step 3. 리스크 모니터링 시스템 - API 클라이언트
 * FastAPI 서버 연동 + Mock 데이터 폴백
 */

import {
  ApiResponse,
  DealsResponse,
  SignalsResponse,
  RiskDeal,
  RiskSnapshot,
  CategoryScore,
  SupplyChainGraph,
  RiskPropagation,
  AIActionGuide,
  TimelineEvent,
  SimulationScenario,
  SimulationResult,
  Text2CypherResult,
  AINewsAnalysis,
  AIRiskSummary,
  ComprehensiveInsightResponse,
} from './types';

import {
  MOCK_DEALS,
  MOCK_SIGNALS,
  MOCK_TIMELINE,
  MOCK_CATEGORY_SCORES,
  MOCK_SUPPLY_CHAIN,
  MOCK_PROPAGATION,
  MOCK_AI_GUIDE,
  MOCK_EVIDENCE,
  MOCK_SCENARIOS,
  MOCK_SIMULATION_RESULT,
  getPortfolioSummary,
} from './mockData';

// ============================================
// 설정
// ============================================
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'; // 기본: Mock 사용

// ============================================
// 유틸리티
// ============================================
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: true,
      data,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error(`API Error (${endpoint}):`, error);
    return {
      success: false,
      data: null as any,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString(),
    };
  }
}

// 지연 시뮬레이션 (Mock 데이터용)
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ============================================
// 딜 관련 API
// ============================================

/**
 * 전체 딜 목록 조회
 */
export async function fetchDeals(): Promise<ApiResponse<DealsResponse>> {
  if (USE_MOCK) {
    await delay(300);
    return {
      success: true,
      data: {
        deals: MOCK_DEALS,
        summary: getPortfolioSummary(MOCK_DEALS),
      },
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<DealsResponse>('/api/v2/deals');
}

/**
 * 개별 딜 상세 조회
 */
export async function fetchDealDetail(dealId: string): Promise<ApiResponse<RiskSnapshot>> {
  if (USE_MOCK) {
    await delay(200);
    const deal = MOCK_DEALS.find(d => d.id === dealId) || MOCK_DEALS[0];

    return {
      success: true,
      data: {
        schemaVersion: 'monitoring.v2',
        generatedAt: new Date().toISOString(),
        data: {
          deal,
          categoryScores: MOCK_CATEGORY_SCORES,
          timeline: MOCK_TIMELINE,
          supplyChain: MOCK_SUPPLY_CHAIN,
          propagation: MOCK_PROPAGATION,
          aiGuide: MOCK_AI_GUIDE,
          evidence: MOCK_EVIDENCE,
        },
        _meta: {
          source: 'mock',
          queryTime: 150,
        },
      },
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<RiskSnapshot>(`/api/v2/deals/${dealId}`);
}

/**
 * 딜별 리스크 카테고리 분석
 */
export async function fetchRiskBreakdown(dealId: string): Promise<ApiResponse<CategoryScore[]>> {
  if (USE_MOCK) {
    await delay(150);
    return {
      success: true,
      data: MOCK_CATEGORY_SCORES,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<CategoryScore[]>(`/api/v2/deals/${dealId}/risk-breakdown`);
}

// ============================================
// 공급망 & 전이 분석 API (Neo4j 핵심)
// ============================================

/**
 * 공급망 그래프 조회
 */
export async function fetchSupplyChain(dealId: string): Promise<ApiResponse<SupplyChainGraph>> {
  if (USE_MOCK) {
    await delay(250);
    return {
      success: true,
      data: MOCK_SUPPLY_CHAIN,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<SupplyChainGraph>(`/api/v2/deals/${dealId}/supply-chain`);
}

/**
 * 리스크 전이 분석
 */
export async function fetchPropagation(dealId: string): Promise<ApiResponse<RiskPropagation>> {
  if (USE_MOCK) {
    await delay(200);
    return {
      success: true,
      data: MOCK_PROPAGATION,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<RiskPropagation>(`/api/v2/deals/${dealId}/propagation`);
}

// ============================================
// 실시간 신호 API
// ============================================

/**
 * 실시간 리스크 신호 조회
 */
export async function fetchSignals(limit: number = 10): Promise<ApiResponse<SignalsResponse>> {
  if (USE_MOCK) {
    await delay(100);
    return {
      success: true,
      data: {
        signals: MOCK_SIGNALS.slice(0, limit),
        count: MOCK_SIGNALS.length,
      },
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<SignalsResponse>(`/api/v2/signals?limit=${limit}`);
}

/**
 * 타임라인 조회
 */
export async function fetchTimeline(dealId: string): Promise<ApiResponse<TimelineEvent[]>> {
  if (USE_MOCK) {
    await delay(150);
    return {
      success: true,
      data: MOCK_TIMELINE,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<TimelineEvent[]>(`/api/v2/timeline/${dealId}`);
}

// ============================================
// 시뮬레이션 API
// ============================================

/**
 * 시뮬레이션 시나리오 목록
 */
export async function fetchScenarios(): Promise<ApiResponse<SimulationScenario[]>> {
  if (USE_MOCK) {
    await delay(100);
    return {
      success: true,
      data: MOCK_SCENARIOS,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<SimulationScenario[]>('/api/v2/scenarios');
}

/**
 * 시뮬레이션 실행
 */
export async function runSimulation(
  scenarioId: string,
  dealIds?: string[]
): Promise<ApiResponse<SimulationResult[]>> {
  if (USE_MOCK) {
    await delay(500); // 시뮬레이션은 좀 더 긴 시간
    return {
      success: true,
      data: MOCK_SIMULATION_RESULT,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<SimulationResult[]>('/api/v2/simulate', {
    method: 'POST',
    body: JSON.stringify({ scenarioId, dealIds }),
  });
}

// ============================================
// AI 기능 API
// ============================================

/**
 * AI 대응 가이드
 */
export async function fetchAIGuide(
  dealId: string,
  signalType: string = 'OPERATIONAL'
): Promise<ApiResponse<AIActionGuide>> {
  if (USE_MOCK) {
    await delay(300);
    return {
      success: true,
      data: MOCK_AI_GUIDE,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<AIActionGuide>(`/api/v2/ai-guide/${dealId}?signal_type=${signalType}`);
}

/**
 * Text2Cypher - 자연어 질의
 */
export async function queryWithNaturalLanguage(
  question: string
): Promise<ApiResponse<Text2CypherResult>> {
  if (USE_MOCK) {
    await delay(800);
    // Mock: 간단한 응답
    return {
      success: true,
      data: {
        question,
        cypher: 'MATCH (c:Company) RETURN c ORDER BY c.totalRiskScore DESC LIMIT 5',
        explanation: '리스크 점수가 높은 상위 5개 기업을 조회합니다.',
        results: MOCK_DEALS.slice(0, 5).map(d => ({ name: d.name, score: d.score })),
        answer: `리스크가 가장 높은 기업은 ${MOCK_DEALS[1].name}(${MOCK_DEALS[1].score}점)입니다.`,
        success: true,
      },
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<Text2CypherResult>('/api/v2/ai/query', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

/**
 * AI 뉴스 분석
 */
export async function analyzeNews(
  title: string,
  content: string
): Promise<ApiResponse<AINewsAnalysis>> {
  if (USE_MOCK) {
    await delay(600);
    return {
      success: true,
      data: {
        severity: 72,
        category: 'legal',
        affectedCompanies: ['SK하이닉스', '한미반도체'],
        keywords: ['특허', '소송', 'ITC'],
        summary: '특허 침해 소송으로 인한 법적 리스크 발생. 관련 기업 모니터링 필요.',
      },
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<AINewsAnalysis>('/api/v2/ai/analyze-news', {
    method: 'POST',
    body: JSON.stringify({ title, content }),
  });
}

/**
 * AI 리스크 요약
 */
export async function generateRiskSummary(dealId: string): Promise<ApiResponse<AIRiskSummary>> {
  if (USE_MOCK) {
    await delay(500);
    const deal = MOCK_DEALS.find(d => d.id === dealId) || MOCK_DEALS[0];
    return {
      success: true,
      data: {
        summary: `${deal.name}은 특허 소송(+15점)과 공급사 리스크 전이(+8점)로 인해 WARNING 상태. 공급망 다변화 검토 필요.`,
        keyPoints: [
          '특허 침해 소송으로 법률 리스크 급등',
          '한미반도체 리스크 전이 (+8점)',
          '메모리 가격 하락 추세 지속',
        ],
        recommendation: '주요 고객사 커뮤니케이션 강화 및 대체 공급사 확보 필요',
      },
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<AIRiskSummary>(`/api/v2/ai/summarize/${dealId}`);
}

/**
 * 시뮬레이션 결과 AI 해석
 */
export async function interpretSimulation(
  scenario: SimulationScenario,
  results: SimulationResult[]
): Promise<ApiResponse<string>> {
  if (USE_MOCK) {
    await delay(600);
    return {
      success: true,
      data: `${scenario.name} 시나리오 발생 시, 가장 큰 영향을 받는 기업은 ${results[0]?.dealName}(+${results[0]?.delta}점)입니다. 전체 포트폴리오 평균 리스크는 약 ${Math.round(results.reduce((sum, r) => sum + r.delta, 0) / results.length)}점 상승할 것으로 예상됩니다.`,
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<string>('/api/v2/ai/interpret-simulation', {
    method: 'POST',
    body: JSON.stringify({ scenario, results }),
  });
}

/**
 * AI 종합 인사이트 (NEW - v2.3)
 * 리스크 점수가 아닌 맥락적 해석, 패턴 인식, 교차 분석, 권고사항 제공
 */
export async function fetchComprehensiveInsight(
  companyName: string
): Promise<ApiResponse<ComprehensiveInsightResponse>> {
  if (USE_MOCK) {
    await delay(1000);
    const deal = MOCK_DEALS.find(d => d.name === companyName) || MOCK_DEALS[0];
    return {
      success: true,
      data: {
        company: deal.name,
        riskScore: deal.score,
        riskLevel: deal.status,
        insight: {
          executive_summary: `${deal.name}은 현재 ${deal.status} 등급으로, 법률 영역에서 특허 소송 관련 신호가 집중되고 있습니다. 공급망 의존도가 높은 구조로 인해 연쇄 리스크 전이에 주의가 필요합니다.`,
          context_analysis: {
            industry_context: '반도체 업황 조정기에 진입하며 메모리 가격 하락 압력 지속. 주요 고객사들의 재고 조정이 매출에 영향을 줄 수 있는 시점입니다.',
            timing_significance: '실적 발표 시즌을 앞두고 법적 리스크가 부각되어 시장 반응에 주의가 필요한 시기입니다.',
          },
          cross_signal_analysis: {
            patterns_detected: [
              '법률 카테고리 신호 2주간 3건 집중 발생',
              '공급망 리스크와 평판 리스크 동시 상승 패턴',
            ],
            correlations: '특허 소송 뉴스 발생 시점과 주가 변동이 연관되어 있으며, 관련 공급사 리스크도 동반 상승하는 경향을 보입니다.',
            anomalies: 'governance 카테고리 신호가 평소 대비 50% 증가하여 주목 필요',
          },
          stakeholder_insights: {
            executive_concerns: '최근 CFO 교체 이후 재무 전략 변화 가능성. 신임 경영진의 리스크 관리 방향 확인 필요.',
            shareholder_dynamics: '기관 투자자 지분율 안정적이나, 일부 행동주의 펀드 동향 모니터링 권장.',
          },
          key_concerns: [
            {
              issue: '미국 ITC 특허 침해 소송',
              why_it_matters: '패소 시 미국 시장 수출 제한 가능성, 매출의 약 40% 영향권',
              watch_for: '예비 판결 일정, 합의 협상 진행 여부',
            },
            {
              issue: '주요 공급사 리스크 전이',
              why_it_matters: '핵심 부품 공급사의 재무 상태 악화로 공급 안정성 우려',
              watch_for: '공급사 실적 발표, 대체 공급선 확보 현황',
            },
          ],
          recommendations: {
            immediate_actions: [
              '법무팀을 통한 소송 진행 상황 상세 파악',
              '경영진 미팅을 통한 대응 전략 확인',
            ],
            monitoring_focus: [
              'legal 카테고리 일간 모니터링 (소송 관련)',
              'supply_chain 카테고리 주간 점검',
            ],
            due_diligence_points: [
              '특허 포트폴리오 상세 분석',
              '공급사 재무제표 및 신용등급 확인',
              '유사 소송 사례 및 합의 이력 조사',
            ],
          },
          confidence: 0.75,
          analysis_limitations: 'Mock 데이터 기반 분석으로, 실제 AI 서비스 연결 시 더 정확한 인사이트 제공 가능.',
        },
        generatedAt: new Date().toISOString(),
        aiServiceAvailable: false,
      },
      timestamp: new Date().toISOString(),
    };
  }

  return fetchApi<ComprehensiveInsightResponse>(`/api/v3/ai/insight/${encodeURIComponent(companyName)}`);
}

// ============================================
// WebSocket 연결 (실시간 신호)
// ============================================

export function createSignalWebSocket(onMessage: (signal: any) => void): WebSocket | null {
  if (USE_MOCK) {
    console.log('[Mock] WebSocket not available in mock mode');
    return null;
  }

  const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws/signals';

  try {
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[WebSocket] Connected to signal stream');
    };

    ws.onmessage = (event) => {
      try {
        const signal = JSON.parse(event.data);
        onMessage(signal);
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
    };

    ws.onclose = () => {
      console.log('[WebSocket] Disconnected');
    };

    return ws;
  } catch (error) {
    console.error('[WebSocket] Failed to connect:', error);
    return null;
  }
}

// ============================================
// API 상태 확인
// ============================================

export async function checkApiHealth(): Promise<boolean> {
  if (USE_MOCK) return true;

  try {
    const response = await fetch(`${API_BASE_URL}/health`, { method: 'GET' });
    return response.ok;
  } catch {
    return false;
  }
}

// ============================================
// 내보내기
// ============================================
export const riskApi = {
  // 딜
  fetchDeals,
  fetchDealDetail,
  fetchRiskBreakdown,
  // 그래프
  fetchSupplyChain,
  fetchPropagation,
  // 신호
  fetchSignals,
  fetchTimeline,
  // 시뮬레이션
  fetchScenarios,
  runSimulation,
  // AI
  fetchAIGuide,
  queryWithNaturalLanguage,
  analyzeNews,
  generateRiskSummary,
  interpretSimulation,
  fetchComprehensiveInsight,  // NEW v2.3
  // 유틸
  createSignalWebSocket,
  checkApiHealth,
};

export default riskApi;
