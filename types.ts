
export enum HurdleStatus {
  PASS = 'PASS',
  WARNING = 'WARNING',
  FAIL = 'FAIL'
}

// Fix: Expanded DealSector type to include industry-specific categories used in App.tsx mock data
export type DealSector = 'IB' | 'PF' | 'Corporate' | '광업' | '우주항공' | '로봇' | '렌탈' | '제련' | '반도체' | '소재';

export type NodeType = 'RiskFactor' | 'Subsidiary' | 'Client' | 'Target' | 'Sponsor' | 'HoldCo' | 'OpCo' | 'Partner' | 'Investor';

export interface ScoreDetail {
  category: string;
  item: string;
  score: number; // 1 to 5
  value: string;
  weight: number;
}

export interface ScoringModule {
  id: string;
  title: string;
  description: string;
  details: ScoreDetail[];
  totalScore: number;
}

export interface AIInsight {
  title: string;
  content: string;
  impactScore: number;
  relatedCovenant: string;
  actionRequired: string;
}

export interface DealNode {
  id: string;
  name: string;
  type: NodeType;
  status: HurdleStatus;
  details: { label: string; value: string; risk?: string }[];
  position: { x: number; y: number };
  insights?: AIInsight[];
}

export interface DealEdge {
  from: string;
  to: string;
  label: string;
  relation?: string;
  isRiskPath?: boolean;
}

export interface DealSummary {
  id: string;
  name: string;
  sector: DealSector;
  sponsor: string;
  status: HurdleStatus;
  progress: '검토' | '심사' | '집행' | '관리';
  mainMetric: { label: string; value: string };
  lastSignal: string;
  lastUpdated: string;
  totalScore?: number;
  maxScore?: number;
}

export interface GlobalAlert {
  id: string;
  dealId: string;
  dealName: string;
  type: 'news' | 'legal' | 'market';
  content: string;
  time: string;
  severity: 'high' | 'medium' | 'low';
}

export interface TimelineEvent {
  id: string;
  label: string;
  date: string;
  type: string;
  active: boolean;
  description?: string;
}

export interface VerificationData {
  dealInfo: {
    sponsor: string;
    borrower: string;
    target: string;
    dealSize: string;
    equity: string;
    debt: string;
  };
  modules: ScoringModule[];
  verdict: {
    status: string;
    description: string;
    totalScore: number;
  };
  timeline: TimelineEvent[];
}


export interface MonitoringData {
  dealName: string;
  activeTrigger: string | null;
  status: HurdleStatus;
  nodes: DealNode[];
  edges: DealEdge[];
}

export interface APIScoringResult {
  run: {
    id: number;
    file_name: string;
    total_score: number;
    project_summary: {
      industry_overview_highlights: string[];
      deal_structure_financing_plan: string[];
      risk_factors_mitigation: string[];
    };
  };
  results: {
    item_key: string;
    item_name: string;
    extracted_value: string;
    score_raw: number;
    evidence_text: string;
    module_id: number;
    module_name: string;
  }[];
}
