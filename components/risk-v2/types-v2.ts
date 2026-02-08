/**
 * Risk V2 - 5-Node 스키마 기반 전체 타입 정의
 * Graph DB V5 구조와 1:1 매핑
 *
 * 노드 계층: Deal → Company → RiskCategory → RiskEntity → RiskEvent
 */

// ============================================
// 기본 열거형 타입
// ============================================

/** 10개 리스크 카테고리 코드 */
export type CategoryCodeV2 =
  | 'SHARE'   // 주주
  | 'EXEC'    // 임원
  | 'CREDIT'  // 신용
  | 'LEGAL'   // 법률
  | 'GOV'     // 지배구조
  | 'OPS'     // 운영
  | 'AUDIT'   // 감사
  | 'ESG'     // ESG
  | 'SUPPLY'  // 공급망
  | 'OTHER';  // 기타

/** 리스크 레벨 (3단계) */
export type RiskLevelV2 = 'PASS' | 'WARNING' | 'FAIL';

/** 추세 방향 */
export type TrendV2 = 'UP' | 'DOWN' | 'STABLE';

/** 이벤트 심각도 (4단계) */
export type SeverityV2 = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

/** 화면 뷰 타입 */
export type ViewType = 'command' | 'xray' | 'deepdive' | 'whatif';

/** Entity 세부 타입 */
export type EntityType = 'PERSON' | 'SHAREHOLDER' | 'CASE' | 'ISSUE';

/** Event 세부 타입 */
export type EventType = 'NEWS' | 'DISCLOSURE' | 'ISSUE';

// ============================================
// 5-Node 타입 정의
// ============================================

/**
 * Node 1: Deal (투자검토)
 * - 투자 검토 건을 관리하는 최상위 노드
 * - TARGET 관계로 메인 기업과 연결
 */
export interface DealV2 {
  id: string;
  name: string;
  status: 'ACTIVE' | 'CLOSED' | 'PENDING';
  analyst: string;
  targetCompanyId: string;
  targetCompanyName: string;
  registeredAt: string;
  notes: string;
  /** 딜 목록 조회 시 포함되는 요약 점수 (미선택 딜 표시용) */
  score?: number;
  /** 딜 목록 조회 시 포함되는 리스크 레벨 (미선택 딜 표시용) */
  riskLevel?: RiskLevelV2;
}

/**
 * Node 2: Company (기업)
 * - 메인 기업 + 관련 기업 (동일 구조)
 * - isMain으로 메인/관련 구분
 * - 10개 RiskCategory를 하위에 보유
 */
export interface CompanyV2 {
  id: string;
  name: string;
  ticker: string;
  sector: string;
  market: string;
  isMain: boolean;
  /** 직접 리스크 점수 (카테고리 가중합) */
  directScore: number;
  /** 전이 리스크 점수 (관련기업으로부터) */
  propagatedScore: number;
  /** 총 리스크 점수 (직접 + 전이) */
  totalRiskScore: number;
  /** 리스크 레벨 */
  riskLevel: RiskLevelV2;
  /** 관련 기업 ID 배열 */
  relatedCompanyIds: string[];
  /** 메인 기업과의 관계 정보 (관련기업인 경우) */
  relationToMain?: {
    mainId: string;
    relation: string;
    tier: number;
  };
}

/**
 * Node 3: RiskCategory (리스크 카테고리)
 * - 10개 카테고리 중 하나
 * - Company 하위에 위치
 * - 하위 Entity의 점수를 집계
 */
export interface RiskCategoryV2 {
  id: string;
  companyId: string;
  code: CategoryCodeV2;
  name: string;
  icon: string;
  /** 가중치 (0~1, 합계 1.0) */
  weight: number;
  /** 원점수 (Entity 합산) */
  score: number;
  /** 가중 점수 (score * weight) */
  weightedScore: number;
  /** 하위 Entity 수 */
  entityCount: number;
  /** 하위 Event 수 */
  eventCount: number;
  /** 추세 */
  trend: TrendV2;
}

/**
 * Node 4: RiskEntity (리스크 엔티티)
 * - 구체적 대상: 인물, 주주, 소송, 이슈
 * - RiskCategory 하위에 위치
 * - 하위 Event의 점수를 집계
 */
export interface RiskEntityV2 {
  id: string;
  companyId: string;
  categoryCode: CategoryCodeV2;
  name: string;
  type: EntityType;
  subType: string;
  position: string;
  description: string;
  /** 리스크 점수 (하위 Event 합산, 음수는 0) */
  riskScore: number;
  /** 하위 Event 수 */
  eventCount: number;
}

/**
 * Node 5: RiskEvent (리스크 이벤트)
 * - 뉴스, 공시, 이슈 등 개별 이벤트
 * - RiskEntity 하위에 위치
 * - 점수는 음수 가능 (긍정 이벤트)
 */
export interface RiskEventV2 {
  id: string;
  entityId: string;
  title: string;
  summary: string;
  type: EventType;
  /** 점수 (음수 가능, Entity 집계 시 음수는 제외) */
  score: number;
  severity: SeverityV2;
  sourceName: string;
  sourceUrl: string;
  publishedAt: string;
  /** 활성 여부 */
  isActive?: boolean;
}

// ============================================
// 카테고리 정의 (고정 설정)
// ============================================

/** 카테고리 정의 (코드, 이름, 아이콘, 가중치) */
export interface CategoryDefinitionV2 {
  code: CategoryCodeV2;
  name: string;
  icon: string;
  weight: number;
}

// ============================================
// 관련기업 관계 타입
// ============================================

/** 관련기업 관계 정보 */
export interface CompanyRelationV2 {
  mainCompanyId: string;
  relatedCompanyId: string;
  relation: string;
  tier: number;
}

// ============================================
// 3D 그래프 시각화 타입
// ============================================

/** 3D 그래프 노드 */
export interface GraphNode3D {
  id: string;
  name: string;
  nodeType: 'deal' | 'mainCompany' | 'relatedCompany' | 'riskCategory' | 'riskEntity' | 'riskEvent';
  riskScore: number;
  riskLevel: RiskLevelV2;
  tier: number;
  categoryCode?: CategoryCodeV2;
  entityType?: EntityType;
  metadata: Record<string, unknown>;
}

/** 3D 그래프 링크 */
export interface GraphLink3D {
  source: string;
  target: string;
  relationship: 'TARGET' | 'HAS_CATEGORY' | 'HAS_RELATED' | 'HAS_ENTITY' | 'HAS_EVENT';
  dependency: number;
  label: string;
  riskTransfer: number;
}

/** 3D 그래프 전체 데이터 */
export interface GraphData3D {
  nodes: GraphNode3D[];
  links: GraphLink3D[];
}

// ============================================
// 시뮬레이션 타입
// ============================================

/** 시뮬레이션 시나리오 */
export interface SimulationScenarioV2 {
  id: string;
  name: string;
  description: string;
  affectedCategories: CategoryCodeV2[];
  severity: 'low' | 'medium' | 'high';
  propagationMultiplier: number;
  impactFactors: Partial<Record<CategoryCodeV2, number>>;
}

/** 시뮬레이션 결과 */
export interface SimulationResultV2 {
  dealId: string;
  dealName: string;
  companyId: string;
  originalScore: number;
  simulatedScore: number;
  delta: number;
  affectedCategories: {
    code: CategoryCodeV2;
    name: string;
    delta: number;
  }[];
  cascadePath?: string[];
  aiInterpretation?: string;
}

// ============================================
// AI 기능 타입
// ============================================

/** Text2Cypher 결과 */
export interface Text2CypherResultV2 {
  question: string;
  cypher: string;
  explanation: string;
  results: unknown[];
  answer: string;
  visualizationType: 'table' | 'chart' | 'graph';
  success: boolean;
}

/** Copilot 컨텍스트 데이터 */
export interface CopilotContextData {
  view: ViewType;
  nodeId: string | null;
  nodeType: 'deal' | 'company' | 'category' | 'entity' | 'event' | null;
  additionalData: Record<string, unknown>;
}

/** AI 인사이트 응답 */
export interface AIInsightResponseV2 {
  summary: string;
  keyFindings: string[];
  recommendation: string;
  confidence: number;
  generatedAt: string;
}

// ============================================
// API 응답 타입
// ============================================

/** 범용 API 응답 래퍼 */
export interface ApiResponseV2<T> {
  success: boolean;
  data: T;
  error?: string;
  timestamp: string;
}

/** 딜 목록 응답 */
export interface DealsResponseV2 {
  deals: DealV2[];
  summary: {
    total: number;
    active: number;
    avgRisk: number;
  };
}

/** 딜 상세 응답 (메인 기업 + 카테고리 + 관련기업) */
export interface DealDetailResponseV2 {
  deal: DealV2;
  mainCompany: CompanyV2;
  categories: RiskCategoryV2[];
  relatedCompanies: CompanyV2[];
  /** 최근 이벤트 (서버에서 제공, 최대 10개) */
  recentEvents?: RiskEventV2[];
}

/** 기업 상세 응답 */
export interface CompanyDetailResponseV2 {
  company: CompanyV2;
  categories: RiskCategoryV2[];
  entities: RiskEntityV2[];
  relatedCompanies: CompanyV2[];
}

// ============================================
// 히트맵 타입
// ============================================

/** 히트맵 셀 (기업 x 카테고리 매트릭스) */
export interface HeatmapCell {
  companyId: string;
  companyName: string;
  categoryCode: CategoryCodeV2;
  score: number;
}

// ============================================
// 상태 관리 타입
// ============================================

/** RiskV2 글로벌 상태 */
export interface RiskV2State {
  selectedDealId: string | null;
  selectedCompanyId: string | null;
  selectedCategoryCode: CategoryCodeV2 | null;
  selectedEntityId: string | null;
  activeView: ViewType;
  copilotOpen: boolean;
  copilotContext: CopilotContextData | null;
  deals: DealV2[];
  dealsLoading: boolean;
  /** 선택된 딜의 상세 데이터 */
  dealDetail: DealDetailResponseV2 | null;
  dealDetailLoading: boolean;
  /** 최근 이벤트 캐시 */
  recentEvents: RiskEventV2[];
}

/** 상태 액션 타입 */
export type RiskV2Action =
  | { type: 'SET_DEALS'; payload: DealV2[] }
  | { type: 'SET_DEALS_LOADING'; payload: boolean }
  | { type: 'SET_SELECTED_DEAL'; payload: string | null }
  | { type: 'SET_SELECTED_COMPANY'; payload: string | null }
  | { type: 'SET_SELECTED_CATEGORY'; payload: CategoryCodeV2 | null }
  | { type: 'SET_SELECTED_ENTITY'; payload: string | null }
  | { type: 'SET_ACTIVE_VIEW'; payload: ViewType }
  | { type: 'TOGGLE_COPILOT' }
  | { type: 'SET_COPILOT_CONTEXT'; payload: CopilotContextData | null }
  | { type: 'DRILL_DOWN_TO_DEAL'; payload: string }
  | { type: 'DRILL_DOWN_TO_COMPANY'; payload: string }
  | { type: 'DRILL_DOWN_TO_CATEGORY'; payload: CategoryCodeV2 }
  | { type: 'DRILL_DOWN_TO_ENTITY'; payload: string }
  | { type: 'NAVIGATE_BACK_TO'; payload: 'deals' | 'company' | 'category' }
  | { type: 'SET_DEAL_DETAIL'; payload: DealDetailResponseV2 | null }
  | { type: 'SET_DEAL_DETAIL_LOADING'; payload: boolean }
  | { type: 'SET_RECENT_EVENTS'; payload: RiskEventV2[] };

// ============================================
// AI Briefing 타입
// ============================================

/** 리스크 기여 드라이버 */
export interface RiskDriver {
  categoryCode: string;
  categoryName: string;
  categoryIcon: string;
  score: number;
  weight: number;
  weightedScore: number;
  contribution: number;
  eventCount: number;
  isPropagated: boolean;
}

/** 리스크 드라이버 응답 */
export interface RiskDriversResponse {
  companyName: string;
  totalScore: number;
  directScore: number;
  propagatedScore: number;
  riskLevel: RiskLevelV2;
  topDrivers: RiskDriver[];
  allDrivers: RiskDriver[];
}

// ============================================
// Live Events Triage 타입
// ============================================

/** 소스 신뢰도 등급 */
export type SourceTier = 'OFFICIAL' | 'PRESS' | 'COMMUNITY' | 'BLOG';

/** 트리아지 레벨 */
export type TriageLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

/** 트리아지된 이벤트 (Smart Triage + Source Transparency) */
export interface TriagedEventV2 extends RiskEventV2 {
  /** 긴급도 0-100 (시간 기반 감쇠) */
  urgency: number;
  /** 신뢰도 0-100 (소스 신뢰 + 교차 참조) */
  confidence: number;
  /** 트리아지 점수 = severity*0.4 + urgency*0.3 + confidence*0.3 */
  triageScore: number;
  /** 트리아지 레벨 */
  triageLevel: TriageLevel;
  /** 소스 등급 */
  sourceTier: SourceTier;
  /** 소스 신뢰도 0-1 */
  sourceReliability: number;
  /** 충돌 여부 (동일 주제 상반 보도) */
  hasConflict?: boolean;
  /** 대응 플레이북 */
  playbook?: string[];
  /** 연관 카테고리 코드 */
  categoryCode?: string;
  /** 연관 카테고리 이름 */
  categoryName?: string;
}

// ============================================
// Case Management 타입
// ============================================

/** 케이스 상태 */
export type CaseStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'DISMISSED';

/** 케이스 (경량 워크플로우) */
export interface CaseV2 {
  id: string;
  eventId: string;
  eventTitle: string;
  status: CaseStatus;
  assignee: string;
  notes: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  createdAt: string;
  updatedAt: string;
}

/** AI 브리핑 응답 */
export interface BriefingResponse {
  company: string;
  riskScore: number;
  riskLevel: RiskLevelV2;
  executive_summary: string;
  /** 1줄 헤드라인 (없으면 executive_summary 첫 문장 사용) */
  headline?: string;
  /** 24시간 리스크 점수 변화 */
  delta_24h?: number;
  /** 7일 리스크 점수 변화 */
  delta_7d?: number;
  /** 다음 권장 액션 (1줄) */
  next_action?: string;
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
  key_concerns: {
    issue: string;
    why_it_matters: string;
    watch_for: string;
    /** Impact 등급 (없으면 인덱스 기반 추론) */
    impact?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    /** 발생 확률 등급 */
    probability?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    /** 트리거 조건 (없으면 watch_for 사용) */
    trigger?: string;
    /** 관련 근거 건수 */
    evidence_count?: number;
    /** 담당자 */
    owner?: string;
    /** 예상 조치 시한 */
    eta?: string;
  }[];
  recommendations: {
    immediate_actions: string[];
    monitoring_focus: string[];
    due_diligence_points: string[];
  };
  confidence: number;
  analysis_limitations: string;
  dataSources?: {
    newsCount: number;
    disclosureCount: number;
    relatedCompanyCount: number;
    categoryCount: number;
  };
}
