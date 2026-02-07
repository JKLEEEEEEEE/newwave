/**
 * Step 3. 리스크 모니터링 시스템 - 타입 정의
 * Graph-First + AI Enhanced (v2.1)
 */

// ============================================
// 기본 상태 타입
// ============================================
export type RiskStatus = 'PASS' | 'WARNING' | 'FAIL';
export type SignalType = 'LEGAL_CRISIS' | 'MARKET_CRISIS' | 'OPERATIONAL';
export type TimelineStage = 1 | 2 | 3;
export type TrendDirection = 'up' | 'down' | 'stable';

// ============================================
// 8대 리스크 카테고리 (14개 → 8개 집중화)
// ============================================
export type RiskCategoryId =
  | 'financial'      // 재무 (공시 + 신용등급)
  | 'legal'          // 법률/규제 (소송 + 금감원)
  | 'governance'     // 지배구조 (주주 + 임원)
  | 'supply_chain'   // 공급망 (Neo4j 핵심!)
  | 'market'         // 시장/경쟁
  | 'reputation'     // 평판/여론 (뉴스 + SNS + 채용리뷰)
  | 'operational'    // 운영/IP (특허 + 상표)
  | 'macro';         // 거시환경 (ESG + 부동산 + 금리/환율)

export interface RiskCategory {
  id: RiskCategoryId;
  name: string;
  icon: string;
  weight: number;
  description: string;
  sources: string[];
}

export interface CategoryScore {
  categoryId: RiskCategoryId;
  name: string;
  icon: string;
  score: number;
  weight: number;
  weightedScore: number;
  trend: TrendDirection;
  topEvents: string[];
}

// 8대 카테고리 정의
export const RISK_CATEGORIES: Record<RiskCategoryId, RiskCategory> = {
  financial: {
    id: 'financial',
    name: '재무',
    icon: '💰',
    weight: 0.20,
    description: '재무제표, 신용등급, 유동성',
    sources: ['DART', 'NICE', 'KIND'],
  },
  legal: {
    id: 'legal',
    name: '법률/규제',
    icon: '⚖️',
    weight: 0.15,
    description: '소송, 제재, 규제 위반',
    sources: ['대법원', '금감원', 'DART'],
  },
  governance: {
    id: 'governance',
    name: '지배구조',
    icon: '👔',
    weight: 0.10,
    description: '주주 구성, 경영진, 지분 변동',
    sources: ['DART', 'KIND'],
  },
  supply_chain: {
    id: 'supply_chain',
    name: '공급망',
    icon: '🔗',
    weight: 0.20,
    description: '공급사/고객사 리스크 전이',
    sources: ['뉴스', '공급망DB'],
  },
  market: {
    id: 'market',
    name: '시장/경쟁',
    icon: '📊',
    weight: 0.10,
    description: '시장 점유율, 경쟁 동향, 산업 사이클',
    sources: ['뉴스', '산업분석'],
  },
  reputation: {
    id: 'reputation',
    name: '평판/여론',
    icon: '📢',
    weight: 0.10,
    description: '언론 보도, SNS 여론, 직원 평판',
    sources: ['뉴스', 'SNS', '잡플래닛'],
  },
  operational: {
    id: 'operational',
    name: '운영/IP',
    icon: '⚙️',
    weight: 0.10,
    description: '특허, 생산, 인력, 기술 경쟁력',
    sources: ['KIPRIS', '채용공고'],
  },
  macro: {
    id: 'macro',
    name: '거시환경',
    icon: '🌍',
    weight: 0.05,
    description: '금리, 환율, 원자재, ESG',
    sources: ['경제지표', 'ESG평가'],
  },
};

// ============================================
// 리스크 신호
// ============================================
export interface RiskSignal {
  id: string;
  signalType: SignalType;
  company: string;
  content: string;
  time: string;
  isUrgent: boolean;
  category: RiskCategoryId;
  source: string;
}

export const SIGNAL_STYLES: Record<SignalType, { bg: string; text: string; badge: string; label: string }> = {
  LEGAL_CRISIS: { bg: 'bg-red-900/30', text: 'text-red-400', badge: 'bg-red-600', label: 'LEGAL CRISIS' },
  MARKET_CRISIS: { bg: 'bg-yellow-900/30', text: 'text-yellow-400', badge: 'bg-yellow-600', label: 'MARKET CRISIS' },
  OPERATIONAL: { bg: 'bg-blue-900/30', text: 'text-blue-400', badge: 'bg-blue-600', label: 'OPERATIONAL' },
};

// ============================================
// 타임라인 이벤트 (3단계)
// ============================================
export interface TimelineEvent {
  id: string;
  stage: TimelineStage;
  stageLabel: string;
  icon: string;
  label: string;
  description: string;
  date: string;
  source: string;
}

export const TIMELINE_STAGES: Record<TimelineStage, { label: string; icon: string; color: string; description: string }> = {
  1: { label: '뉴스 보도', icon: '📰', color: 'text-blue-400', description: '선행 감지' },
  2: { label: '금융위 통지', icon: '📋', color: 'text-yellow-400', description: '규제 개입' },
  3: { label: '대주단 확인', icon: '🏦', color: 'text-red-400', description: '조치 필요' },
};

// ============================================
// 그래프 노드/엣지 (Neo4j)
// ============================================
export type NodeType = 'company' | 'person' | 'supplier' | 'customer' | 'competitor';

export interface GraphNode {
  id: string;
  type: NodeType;
  name: string;
  riskScore: number;
  role?: string;
  sector?: string;
  tier?: number;  // 1차, 2차 공급사
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: 'SUPPLIES_TO' | 'OWNS' | 'MANAGES' | 'COMPETES_WITH';
  dependency?: number;  // 의존도 0~1
  label?: string;
}

export interface SupplyChainGraph {
  centerNode: GraphNode;
  suppliers: GraphNode[];
  customers: GraphNode[];
  edges: GraphEdge[];
  totalPropagatedRisk: number;
}

// ============================================
// 리스크 전이 분석
// ============================================
export interface PropagationPath {
  path: string[];  // ["A사", "B사", "대상기업"]
  risk: number;
  pathway: 'supply_chain' | 'ownership' | 'market';
}

export interface RiskPropagation {
  directRisk: number;
  propagatedRisk: number;
  totalRisk: number;
  topPropagators: {
    company: string;
    contribution: number;
    pathway: string;
    riskScore: number;
  }[];
  paths: PropagationPath[];
}

// ============================================
// AI 액션 가이드
// ============================================
export interface ActionTodo {
  id: string;
  text: string;
  completed: boolean;
}

export interface ActionGuide {
  guide: string;
  todos: ActionTodo[];
}

export interface AIActionGuide {
  rmTitle: string;
  rmGuide: string;
  rmTodos: string[];
  opsTitle: string;
  opsGuide: string;
  opsTodos: string[];
  industry: string;
  industryInsight: string;
  propagationAction?: string;  // 전이 리스크 대응
}

// ============================================
// 딜 메트릭스
// ============================================
export interface DealMetrics {
  ltv: { current: string; prev: string; trend: TrendDirection };
  ebitda: string;
  covenant: string;
  dscr?: string;
  netDebt?: string;
}

// ============================================
// 증거 자료
// ============================================
export interface Evidence {
  id: string;
  title: string;
  source: string;
  date: string;
  sentiment: '부정' | '중립' | '긍정';
  category: RiskCategoryId;
  url?: string;
}

// ============================================
// 포트폴리오 딜 요약
// ============================================
export interface RiskDeal {
  id: string;
  name: string;
  sector: string;
  status: RiskStatus;
  score: number;
  directRisk: number;
  propagatedRisk: number;
  topFactors: string[];
  lastSignal: string;
  lastUpdated: string;
  metrics: DealMetrics;
}

// ============================================
// 메인 리스크 스냅샷 (monitoring.v2)
// ============================================
export interface RiskSnapshot {
  schemaVersion: 'monitoring.v2';
  generatedAt: string;
  data: {
    deal: RiskDeal;
    categoryScores: CategoryScore[];
    timeline: TimelineEvent[];
    supplyChain: SupplyChainGraph;
    propagation: RiskPropagation;
    aiGuide: AIActionGuide;
    evidence: Evidence[];
  };
  _meta: {
    source: string;
    queryTime: number;
  };
}

// ============================================
// 시뮬레이션 시나리오
// ============================================
export interface SimulationScenario {
  id: string;
  name: string;
  description: string;
  affectedSectors: string[];
  impactFactors: Partial<Record<RiskCategoryId, number>>;
  propagationMultiplier: number;
  severity: 'low' | 'medium' | 'high';
}

export interface SimulationResult {
  dealId: string;
  dealName: string;
  originalScore: number;
  simulatedScore: number;
  delta: number;
  affectedCategories: {
    category: RiskCategoryId;
    delta: number;
    source?: string;
    tier?: number;
    description?: string;
  }[];
  cascadePath?: string[];  // Phase 3: Cascade 경로
  interpretation?: string;  // AI 해석
}

// ============================================
// Phase 3: ML 예측 타입
// ============================================
export interface PredictionData {
  date: string;
  predicted_score: number;
  lower_bound?: number;
  upper_bound?: number;
}

export interface PredictionResult {
  company_id: string;
  periods: number;
  predictions: PredictionData[];
  trend: 'increasing' | 'decreasing' | 'stable';
  confidence: number | null;
  is_fallback: boolean;
  model_type: 'prophet' | 'random_walk' | 'simple';
}

// ============================================
// Phase 3: 커스텀 시나리오 타입
// ============================================
export interface CustomScenario {
  id?: string;
  name: string;
  description: string;
  affectedSectors: string[];
  impactFactors: Partial<Record<RiskCategoryId, number>>;
  propagationMultiplier: number;
  severity: 'low' | 'medium' | 'high';
  isCustom: boolean;
  createdAt?: string;
}

export interface AdvancedSimulationResult {
  success: boolean;
  scenario: {
    id: string;
    name: string;
    severity: string;
    affectedSectors: string[];
  };
  results: SimulationResult[];
  totalAffected: number;
  maxDelta: number;
}

// ============================================
// AI 기능 타입
// ============================================
export interface AINewsAnalysis {
  severity: number;
  category: RiskCategoryId;
  affectedCompanies: string[];
  keywords: string[];
  summary: string;
}

export interface Text2CypherResult {
  question: string;
  cypher: string;
  explanation: string;
  results: any[];
  answer: string;
  success: boolean;
}

export interface AIRiskSummary {
  summary: string;
  keyPoints: string[];
  recommendation: string;
}

// ============================================
// AI 종합 인사이트 타입 (NEW - v2.3)
// ============================================
export interface ComprehensiveInsight {
  executive_summary: string;

  context_analysis: {
    industry_context: string;
    timing_significance: string;
  };

  cross_signal_analysis: {
    patterns_detected: string[];
    correlations: string;
    anomalies: string;
  };

  stakeholder_insights: {
    executive_concerns: string;
    shareholder_dynamics: string;
  };

  key_concerns: Array<{
    issue: string;
    why_it_matters: string;
    watch_for: string;
  }>;

  recommendations: {
    immediate_actions: string[];
    monitoring_focus: string[];
    due_diligence_points: string[];
  };

  confidence: number;
  analysis_limitations: string;
}

export interface ComprehensiveInsightResponse {
  company: string;
  riskScore: number;
  riskLevel: RiskStatus;
  insight: ComprehensiveInsight;
  generatedAt: string;
  aiServiceAvailable: boolean;
}

// ============================================
// API 응답 타입
// ============================================
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  timestamp: string;
}

export interface DealsResponse {
  deals: RiskDeal[];
  summary: {
    total: number;
    pass: number;
    warning: number;
    fail: number;
    avgScore: number;
  };
}

export interface SignalsResponse {
  signals: RiskSignal[];
  count: number;
}
