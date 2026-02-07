/**
 * Step 3. 리스크 모니터링 시스템 - Mock 데이터
 * 실제 API 연동 전 테스트용
 */

import {
  RiskDeal,
  RiskSignal,
  TimelineEvent,
  CategoryScore,
  SupplyChainGraph,
  RiskPropagation,
  AIActionGuide,
  Evidence,
  SimulationScenario,
  SimulationResult,
  GraphNode,
  GraphEdge,
} from './types';

// ============================================
// 포트폴리오 딜 목록 - 핵심 딜 대상만 (공급사/경쟁사 제외)
// ============================================
export const MOCK_DEALS: RiskDeal[] = [
  {
    id: 'deal1',
    name: 'SK하이닉스',
    sector: '반도체',
    status: 'WARNING',
    score: 68,
    directRisk: 56,
    propagatedRisk: 12,
    topFactors: ['특허 소송', '공급망 리스크', '경쟁 심화'],
    lastSignal: '특허 침해 소송 - ITC 조사 개시',
    lastUpdated: '30분 전',
    metrics: {
      ltv: { current: '45.2%', prev: '43.8%', trend: 'up' },
      ebitda: '1,288억',
      covenant: '정상',
      dscr: '3.2x',
      netDebt: '2.8x',
    },
  },
  {
    id: 'deal2',
    name: 'LG에너지솔루션',
    sector: '배터리',
    status: 'WARNING',
    score: 58,
    directRisk: 48,
    propagatedRisk: 10,
    topFactors: ['원자재 가격', '경쟁 심화', '규제 리스크'],
    lastSignal: '리튬 가격 변동성 확대',
    lastUpdated: '1시간 전',
    metrics: {
      ltv: { current: '52.1%', prev: '50.8%', trend: 'up' },
      ebitda: '8,920억',
      covenant: '정상',
      dscr: '2.9x',
      netDebt: '3.1x',
    },
  },
  {
    id: 'deal3',
    name: '현대자동차',
    sector: '자동차',
    status: 'PASS',
    score: 42,
    directRisk: 38,
    propagatedRisk: 4,
    topFactors: ['노사 이슈', '공급망 안정'],
    lastSignal: '전기차 판매 호조',
    lastUpdated: '3시간 전',
    metrics: {
      ltv: { current: '38.7%', prev: '39.2%', trend: 'down' },
      ebitda: '6.2조',
      covenant: '양호',
      dscr: '4.1x',
      netDebt: '2.0x',
    },
  },
];

// ============================================
// 실시간 리스크 신호
// ============================================
export const MOCK_SIGNALS: RiskSignal[] = [
  {
    id: 'sig1',
    signalType: 'LEGAL_CRISIS',
    company: 'SK하이닉스',
    content: '[긴급] 특허 침해 소송 - 미국 ITC 조사 개시',
    time: '2026-02-05T10:30:00',
    isUrgent: true,
    category: 'legal',
    source: '금융감독원',
  },
  {
    id: 'sig2',
    signalType: 'MARKET_CRISIS',
    company: '반도체 섹터',
    content: '반도체 업황 악화 - 메모리 가격 15% 하락',
    time: '2026-02-05T09:15:00',
    isUrgent: false,
    category: 'market',
    source: '시장분석',
  },
  {
    id: 'sig3',
    signalType: 'OPERATIONAL',
    company: '한미반도체',
    content: '주요 고객사 주문 취소 - 수주 잔고 감소',
    time: '2026-02-05T08:45:00',
    isUrgent: true,
    category: 'supply_chain',
    source: '뉴스',
  },
  {
    id: 'sig4',
    signalType: 'OPERATIONAL',
    company: 'LG에너지솔루션',
    content: '리튬 가격 급등 - 원가 부담 증가 예상',
    time: '2026-02-05T08:00:00',
    isUrgent: false,
    category: 'macro',
    source: '원자재시장',
  },
  {
    id: 'sig5',
    signalType: 'LEGAL_CRISIS',
    company: '삼성전자',
    content: 'EU 반독점 조사 착수 - 과징금 가능성',
    time: '2026-02-04T16:30:00',
    isUrgent: false,
    category: 'legal',
    source: 'EU 집행위',
  },
];

// ============================================
// 타임라인 이벤트
// ============================================
export const MOCK_TIMELINE: TimelineEvent[] = [
  {
    id: 't1',
    stage: 1,
    stageLabel: '뉴스 보도',
    icon: '🔵',
    label: '반도체 특허 분쟁 관련 보도',
    description: '선행 감지 완료',
    date: '2026-02-03',
    source: '구글뉴스',
  },
  {
    id: 't2',
    stage: 2,
    stageLabel: '금융위 통지',
    icon: '🟡',
    label: 'ITC 조사 공식 개시 통보',
    description: '규제 리스크 발생',
    date: '2026-02-04',
    source: '금융위원회',
  },
  {
    id: 't3',
    stage: 3,
    stageLabel: '대주단 확인',
    icon: '🔴',
    label: '손해배상 규모 확정 대기',
    description: '담당자 조치 필요',
    date: '2026-02-05',
    source: '법무팀',
  },
];

// ============================================
// 카테고리별 점수 (SK하이닉스 예시)
// ============================================
export const MOCK_CATEGORY_SCORES: CategoryScore[] = [
  { categoryId: 'financial', name: '재무', icon: '💰', score: 45, weight: 0.20, weightedScore: 9, trend: 'stable', topEvents: ['신용등급 유지', '유동성 양호'] },
  { categoryId: 'legal', name: '법률/규제', icon: '⚖️', score: 78, weight: 0.15, weightedScore: 12, trend: 'up', topEvents: ['ITC 조사 개시', '특허 소송'] },
  { categoryId: 'governance', name: '지배구조', icon: '👔', score: 25, weight: 0.10, weightedScore: 3, trend: 'stable', topEvents: ['경영진 안정'] },
  { categoryId: 'supply_chain', name: '공급망', icon: '🔗', score: 72, weight: 0.20, weightedScore: 14, trend: 'up', topEvents: ['한미반도체 리스크 전이', '부품 수급 불안'] },
  { categoryId: 'market', name: '시장/경쟁', icon: '📊', score: 65, weight: 0.10, weightedScore: 7, trend: 'up', topEvents: ['메모리 가격 하락', '경쟁 심화'] },
  { categoryId: 'reputation', name: '평판/여론', icon: '📢', score: 55, weight: 0.10, weightedScore: 6, trend: 'stable', topEvents: ['언론 보도 증가'] },
  { categoryId: 'operational', name: '운영/IP', icon: '⚙️', score: 85, weight: 0.10, weightedScore: 9, trend: 'up', topEvents: ['특허 분쟁', '기술 유출 우려'] },
  { categoryId: 'macro', name: '거시환경', icon: '🌍', score: 40, weight: 0.05, weightedScore: 2, trend: 'down', topEvents: ['금리 안정'] },
];

// ============================================
// 공급망 그래프 (Neo4j 시각화용)
// ============================================
export const MOCK_SUPPLY_CHAIN: SupplyChainGraph = {
  centerNode: {
    id: 'sk_hynix',
    type: 'company',
    name: 'SK하이닉스',
    riskScore: 68,
    sector: '반도체',
  },
  suppliers: [
    { id: 'hanmi', type: 'supplier', name: '한미반도체', riskScore: 82, tier: 1 },
    { id: 'asml', type: 'supplier', name: 'ASML', riskScore: 35, tier: 1 },
    { id: 'lam', type: 'supplier', name: 'Lam Research', riskScore: 42, tier: 2 },
    { id: 'sumco', type: 'supplier', name: 'SUMCO', riskScore: 48, tier: 2 },
  ],
  customers: [
    { id: 'apple', type: 'customer', name: 'Apple', riskScore: 28 },
    { id: 'dell', type: 'customer', name: 'Dell', riskScore: 45 },
    { id: 'hp', type: 'customer', name: 'HP', riskScore: 52 },
  ],
  edges: [
    { id: 'e1', source: 'hanmi', target: 'sk_hynix', relationship: 'SUPPLIES_TO', dependency: 0.45, label: '장비 공급 45%' },
    { id: 'e2', source: 'asml', target: 'sk_hynix', relationship: 'SUPPLIES_TO', dependency: 0.30, label: '노광장비 30%' },
    { id: 'e3', source: 'lam', target: 'hanmi', relationship: 'SUPPLIES_TO', dependency: 0.25, label: '부품 25%' },
    { id: 'e4', source: 'sumco', target: 'sk_hynix', relationship: 'SUPPLIES_TO', dependency: 0.20, label: '웨이퍼 20%' },
    { id: 'e5', source: 'sk_hynix', target: 'apple', relationship: 'SUPPLIES_TO', dependency: 0.35, label: '메모리 35%' },
    { id: 'e6', source: 'sk_hynix', target: 'dell', relationship: 'SUPPLIES_TO', dependency: 0.20, label: '메모리 20%' },
  ],
  totalPropagatedRisk: 12,
};

// ============================================
// 리스크 전이 분석
// ============================================
export const MOCK_PROPAGATION: RiskPropagation = {
  directRisk: 56,
  propagatedRisk: 12,
  totalRisk: 68,
  topPropagators: [
    { company: '한미반도체', contribution: 8, pathway: '공급망', riskScore: 82 },
    { company: 'SK그룹', contribution: 3, pathway: '지분관계', riskScore: 45 },
    { company: '삼성전자', contribution: 1, pathway: '경쟁관계', riskScore: 35 },
  ],
  paths: [
    { path: ['한미반도체', 'SK하이닉스'], risk: 8, pathway: 'supply_chain' },
    { path: ['Lam Research', '한미반도체', 'SK하이닉스'], risk: 2, pathway: 'supply_chain' },
    { path: ['SK그룹', 'SK하이닉스'], risk: 3, pathway: 'ownership' },
  ],
};

// ============================================
// AI 대응 가이드
// ============================================
export const MOCK_AI_GUIDE: AIActionGuide = {
  rmTitle: '💡 RM 영업 가이드 (AI v3.0 - 반도체)',
  rmGuide: '특허 소송 리스크로 인한 고객 이탈 방지가 최우선. 주요 고객사와 선제적 커뮤니케이션 필요.',
  rmTodos: [
    '주요 고객사(Apple, Dell) 긴급 미팅 일정 조율',
    '특허 분쟁 관련 고객 FAQ 자료 준비',
    '대체 공급 옵션 제시 준비 (삼성전자 대비)',
  ],
  opsTitle: '🛡️ OPS 방어 가이드 (AI v3.0 - 반도체)',
  opsGuide: '특허 소송 손해배상 시나리오별 충당금 검토. 공급망 대체 옵션 확보 필요.',
  opsTodos: [
    '손해배상 시나리오별 재무 영향 분석',
    '한미반도체 대체 공급사 리스트업',
    '법무팀과 소송 대응 전략 협의',
  ],
  industry: '반도체',
  industryInsight: '메모리 가격 하락 추세 지속 예상. 특허 분쟁은 생산 중단 리스크로 이어질 수 있어 조기 합의 검토 권장.',
  propagationAction: '한미반도체 리스크(82점) 모니터링 강화 - 의존도 45%로 높은 편, 대체 공급사 확보 시급',
};

// ============================================
// 증거 자료
// ============================================
export const MOCK_EVIDENCE: Evidence[] = [
  {
    id: 'ev1',
    title: 'SK하이닉스, 美 ITC 특허 침해 조사 착수',
    source: '한국경제',
    date: '2026-02-05',
    sentiment: '부정',
    category: 'legal',
    url: 'https://example.com/news1',
  },
  {
    id: 'ev2',
    title: '반도체 업황 악화...메모리 가격 15% 하락',
    source: '머니투데이',
    date: '2026-02-04',
    sentiment: '부정',
    category: 'market',
  },
  {
    id: 'ev3',
    title: '한미반도체, 주요 고객사 주문 취소로 실적 악화 우려',
    source: '이데일리',
    date: '2026-02-03',
    sentiment: '부정',
    category: 'supply_chain',
  },
  {
    id: 'ev4',
    title: 'SK하이닉스 신용등급 유지 (AA-)',
    source: 'NICE신용평가',
    date: '2026-02-01',
    sentiment: '긍정',
    category: 'financial',
  },
];

// ============================================
// 시뮬레이션 시나리오
// ============================================
export const MOCK_SCENARIOS: SimulationScenario[] = [
  {
    id: 'busan_port',
    name: '부산항 파업',
    description: '부산항 물류 마비로 인한 공급망 차질 (2주 이상)',
    affectedSectors: ['물류', '해운', '제조', '반도체'],
    impactFactors: {
      supply_chain: 20,
      operational: 10,
      market: 5,
    },
    propagationMultiplier: 1.5,
    severity: 'high',
  },
  {
    id: 'memory_crash',
    name: '반도체 수요 급감',
    description: '글로벌 경기 침체로 메모리 가격 30% 하락',
    affectedSectors: ['반도체', '전자', '디스플레이'],
    impactFactors: {
      market: 25,
      financial: 15,
      reputation: 10,
    },
    propagationMultiplier: 1.3,
    severity: 'high',
  },
  {
    id: 'rate_hike',
    name: '금리 급등',
    description: '기준금리 100bp 인상',
    affectedSectors: ['전체'],
    impactFactors: {
      financial: 30,
      macro: 20,
    },
    propagationMultiplier: 1.2,
    severity: 'medium',
  },
  {
    id: 'supplier_bankrupt',
    name: '핵심 공급사 부도',
    description: '1차 공급사 중 1곳 부도 발생',
    affectedSectors: ['대상 기업 공급망'],
    impactFactors: {
      supply_chain: 40,
      operational: 25,
      financial: 10,
    },
    propagationMultiplier: 2.0,
    severity: 'high',
  },
  {
    id: 'forex_shock',
    name: '환율 급등',
    description: '원/달러 환율 1,500원 돌파',
    affectedSectors: ['수출기업', '원자재 수입기업'],
    impactFactors: {
      macro: 25,
      financial: 15,
    },
    propagationMultiplier: 1.1,
    severity: 'medium',
  },
];

// ============================================
// 시뮬레이션 결과 예시 (부산항 파업)
// ============================================
export const MOCK_SIMULATION_RESULT: SimulationResult[] = [
  {
    dealId: 'deal1',
    dealName: 'SK하이닉스',
    originalScore: 68,
    simulatedScore: 78,
    delta: 10,
    affectedCategories: [
      { category: 'supply_chain', delta: 8 },
      { category: 'operational', delta: 2 },
    ],
    interpretation: 'SK하이닉스는 부산항 물류 의존도가 높아(45%) 가장 큰 영향을 받을 것으로 예상됩니다. 대체 물류 루트 확보가 시급합니다.',
  },
  {
    dealId: 'deal2',
    dealName: 'LG에너지솔루션',
    originalScore: 58,
    simulatedScore: 70,
    delta: 12,
    affectedCategories: [
      { category: 'supply_chain', delta: 9 },
      { category: 'operational', delta: 3 },
    ],
    interpretation: 'LG에너지솔루션은 배터리 원자재 수입 의존도가 높아 물류 차질 시 생산 지연 우려가 있습니다.',
  },
  {
    dealId: 'deal3',
    dealName: '현대자동차',
    originalScore: 42,
    simulatedScore: 50,
    delta: 8,
    affectedCategories: [
      { category: 'supply_chain', delta: 6 },
      { category: 'operational', delta: 2 },
    ],
    interpretation: '현대자동차는 다변화된 물류 네트워크로 상대적으로 영향이 제한적이나, 부품 수급 모니터링이 필요합니다.',
  },
];

// ============================================
// 포트폴리오 요약 계산
// ============================================
export function getPortfolioSummary(deals: RiskDeal[]) {
  const total = deals.length;
  const pass = deals.filter(d => d.status === 'PASS').length;
  const warning = deals.filter(d => d.status === 'WARNING').length;
  const fail = deals.filter(d => d.status === 'FAIL').length;
  const avgScore = Math.round(deals.reduce((sum, d) => sum + d.score, 0) / total);

  return { total, pass, warning, fail, avgScore };
}
