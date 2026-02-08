/**
 * @deprecated 이 파일은 더 이상 사용되지 않습니다. Mock 데이터 대신 실제 API를 사용합니다.
 * CATEGORY_DEFINITIONS_V2는 category-definitions.ts로 이동했습니다.
 *
 * Risk V2 - Mock 데이터 (DEPRECATED)
 * init_graph_v5.py의 데이터를 TypeScript로 완전 변환
 *
 * 점수 계산 로직:
 *   Entity.riskScore = SUM(Event.score) (음수 이벤트는 0으로 처리)
 *   Category.score = SUM(Entity.riskScore)
 *   Category.weightedScore = score * weight
 *   Company.directScore = SUM(Category.weightedScore)  (반올림)
 *   Company.propagatedScore = SUM(RelatedCompany.directScore) * 0.3 (반올림)
 *   Company.totalRiskScore = directScore + propagatedScore
 */

import type {
  DealV2,
  CompanyV2,
  CategoryDefinitionV2,
  RiskCategoryV2,
  RiskEntityV2,
  RiskEventV2,
  CompanyRelationV2,
  SimulationScenarioV2,
  GraphNode3D,
  GraphLink3D,
  GraphData3D,
  CategoryCodeV2,
  TrendV2,
} from './types-v2';

import { CATEGORY_DEFINITIONS_V2 } from './category-definitions';
export { CATEGORY_DEFINITIONS_V2 };

// ============================================
// Deal 데이터 (2개)
// ============================================
export const MOCK_DEALS_V2: DealV2[] = [
  {
    id: 'DEAL_001',
    name: 'SK하이닉스 검토',
    status: 'ACTIVE',
    analyst: '김철수',
    targetCompanyId: 'COMP_SK',
    targetCompanyName: 'SK하이닉스',
    registeredAt: '2026-01-15T09:00:00Z',
    notes: '',
  },
  {
    id: 'DEAL_002',
    name: '삼성전자 검토',
    status: 'ACTIVE',
    analyst: '이영희',
    targetCompanyId: 'COMP_SS',
    targetCompanyName: '삼성전자',
    registeredAt: '2026-01-20T10:00:00Z',
    notes: '',
  },
];

// ============================================
// Company 데이터 (6개: 메인 2 + 관련 4)
// ============================================

/**
 * SK하이닉스 점수 계산:
 *   EXEC: 노종원(65) + 곽노정(15) = 80, weighted = 80 * 0.15 = 12
 *   SHARE: SK텔레콤(35) + 국민연금(0, 음수제외) = 35, weighted = 35 * 0.15 = 5.25
 *   LEGAL: ITC(100) + 공정위(55) = 155, weighted = 155 * 0.12 = 18.6
 *   ESG: 이천공장(40) = 40, weighted = 40 * 0.08 = 3.2
 *   directScore = 12 + 5.25 + 18.6 + 3.2 = 39.05 → 39
 *   SK머티리얼즈 directScore = AUDIT(70 * 0.08) = 5.6 → 5 (반올림)
 *   propagatedScore = 5 * 0.3 = 1.5 → 1 (반올림)
 *   totalRiskScore = 39 + 1 = 40 → WARNING
 *
 * 참고: Neo4j 실행에서는 반올림 방식에 따라 미세한 차이 가능
 *       여기서는 init_graph_v5.py 로직을 충실히 재현
 */

/**
 * 삼성전자 점수 계산:
 *   EXEC: 이재용(-15) → riskScore=0 (음수이벤트, Entity 집계 시 양수만)
 *   OPS: 3nm(30) = 30, weighted = 30 * 0.10 = 3
 *   directScore = 3
 *   SDI directScore = OPS(50 * 0.10) = 5
 *   propagatedScore = 5 * 0.3 = 1.5 → 1
 *   totalRiskScore = 3 + 1 = 4 → PASS
 */

export const MOCK_COMPANIES_V2: CompanyV2[] = [
  // ---- 메인 기업 ----
  {
    id: 'COMP_SK',
    name: 'SK하이닉스',
    ticker: '000660',
    sector: '반도체',
    market: 'KOSPI',
    isMain: true,
    directScore: 39,
    propagatedScore: 1,
    totalRiskScore: 40,
    riskLevel: 'WARNING',
    relatedCompanyIds: ['COMP_SKM', 'COMP_MU'],
  },
  {
    id: 'COMP_SS',
    name: '삼성전자',
    ticker: '005930',
    sector: '전자',
    market: 'KOSPI',
    isMain: true,
    directScore: 3,
    propagatedScore: 1,
    totalRiskScore: 4,
    riskLevel: 'PASS',
    relatedCompanyIds: ['COMP_SDI', 'COMP_TSMC'],
  },
  // ---- SK하이닉스 관련기업 ----
  {
    id: 'COMP_SKM',
    name: 'SK머티리얼즈',
    ticker: '',
    sector: '소재',
    market: 'KOSPI',
    isMain: false,
    directScore: 5,
    propagatedScore: 0,
    totalRiskScore: 5,
    riskLevel: 'PASS',
    relatedCompanyIds: [],
    relationToMain: { mainId: 'COMP_SK', relation: '계열사', tier: 1 },
  },
  {
    id: 'COMP_MU',
    name: '마이크론',
    ticker: 'MU',
    sector: '반도체',
    market: 'NASDAQ',
    isMain: false,
    directScore: 0,
    propagatedScore: 0,
    totalRiskScore: 0,
    riskLevel: 'PASS',
    relatedCompanyIds: [],
    relationToMain: { mainId: 'COMP_SK', relation: '경쟁사', tier: 2 },
  },
  // ---- 삼성전자 관련기업 ----
  {
    id: 'COMP_SDI',
    name: '삼성SDI',
    ticker: '006400',
    sector: '배터리',
    market: 'KOSPI',
    isMain: false,
    directScore: 5,
    propagatedScore: 0,
    totalRiskScore: 5,
    riskLevel: 'PASS',
    relatedCompanyIds: [],
    relationToMain: { mainId: 'COMP_SS', relation: '계열사', tier: 1 },
  },
  {
    id: 'COMP_TSMC',
    name: 'TSMC',
    ticker: 'TSM',
    sector: '반도체',
    market: 'NYSE',
    isMain: false,
    directScore: 0,
    propagatedScore: 0,
    totalRiskScore: 0,
    riskLevel: 'PASS',
    relatedCompanyIds: [],
    relationToMain: { mainId: 'COMP_SS', relation: '경쟁사', tier: 2 },
  },
];

// ============================================
// RiskCategory 데이터 (SK하이닉스 10 + 삼성전자 10 = 20개)
// ============================================

/** 카테고리 생성 헬퍼: 기업별 10개 카테고리 일괄 생성 */
function buildCategories(
  companyId: string,
  overrides: Partial<Record<CategoryCodeV2, { score: number; entityCount: number; eventCount: number; trend: TrendV2 }>>
): RiskCategoryV2[] {
  return CATEGORY_DEFINITIONS_V2.map((def) => {
    const ov = overrides[def.code];
    const score = ov?.score ?? 0;
    return {
      id: `RC_${companyId}_${def.code}`,
      companyId,
      code: def.code,
      name: def.name,
      icon: def.icon,
      weight: def.weight,
      score,
      weightedScore: Math.round(score * def.weight * 100) / 100,
      entityCount: ov?.entityCount ?? 0,
      eventCount: ov?.eventCount ?? 0,
      trend: ov?.trend ?? ('STABLE' as const),
    };
  });
}

/** SK하이닉스 카테고리 */
const SK_CATEGORIES = buildCategories('COMP_SK', {
  EXEC:  { score: 80,  entityCount: 2, eventCount: 3, trend: 'UP' },
  SHARE: { score: 35,  entityCount: 2, eventCount: 2, trend: 'STABLE' },
  LEGAL: { score: 155, entityCount: 2, eventCount: 3, trend: 'UP' },
  ESG:   { score: 40,  entityCount: 1, eventCount: 1, trend: 'STABLE' },
});

/** 삼성전자 카테고리 */
const SS_CATEGORIES = buildCategories('COMP_SS', {
  EXEC: { score: 0, entityCount: 1, eventCount: 1, trend: 'DOWN' },
  OPS:  { score: 30, entityCount: 1, eventCount: 1, trend: 'UP' },
});

/** SK머티리얼즈 카테고리 */
const SKM_CATEGORIES = buildCategories('COMP_SKM', {
  AUDIT: { score: 70, entityCount: 1, eventCount: 1, trend: 'UP' },
});

/** 삼성SDI 카테고리 */
const SDI_CATEGORIES = buildCategories('COMP_SDI', {
  OPS: { score: 50, entityCount: 1, eventCount: 1, trend: 'UP' },
});

/** 마이크론 카테고리 (데이터 없음) */
const MU_CATEGORIES = buildCategories('COMP_MU', {});

/** TSMC 카테고리 (데이터 없음) */
const TSMC_CATEGORIES = buildCategories('COMP_TSMC', {});

/** 전체 카테고리 */
export const MOCK_CATEGORIES_V2: RiskCategoryV2[] = [
  ...SK_CATEGORIES,
  ...SS_CATEGORIES,
  ...SKM_CATEGORIES,
  ...SDI_CATEGORIES,
  ...MU_CATEGORIES,
  ...TSMC_CATEGORIES,
];

// ============================================
// RiskEntity 데이터 (11개: SK 7 + Samsung 2 + Related 2)
// ============================================
export const MOCK_ENTITIES_V2: RiskEntityV2[] = [
  // ---- SK하이닉스 임원 (EXEC) ----
  {
    id: 'ENT_SK_CFO',
    companyId: 'COMP_SK',
    categoryCode: 'EXEC',
    name: '노종원',
    type: 'PERSON',
    subType: '임원',
    position: 'CFO',
    description: 'SK하이닉스 최고재무책임자',
    riskScore: 65,  // 45 + 20 = 65
    eventCount: 2,
  },
  {
    id: 'ENT_SK_CEO',
    companyId: 'COMP_SK',
    categoryCode: 'EXEC',
    name: '곽노정',
    type: 'PERSON',
    subType: '임원',
    position: 'CEO',
    description: 'SK하이닉스 대표이사',
    riskScore: 15,
    eventCount: 1,
  },
  // ---- SK하이닉스 주주 (SHARE) ----
  {
    id: 'ENT_SK_SKT',
    companyId: 'COMP_SK',
    categoryCode: 'SHARE',
    name: 'SK텔레콤',
    type: 'SHAREHOLDER',
    subType: '최대주주',
    position: '20.1%',
    description: '최대주주',
    riskScore: 35,
    eventCount: 1,
  },
  {
    id: 'ENT_SK_NPS',
    companyId: 'COMP_SK',
    categoryCode: 'SHARE',
    name: '국민연금',
    type: 'SHAREHOLDER',
    subType: '기관투자자',
    position: '9.8%',
    description: '기관투자자',
    riskScore: 0,  // -10 이벤트이지만 양수만 집계
    eventCount: 1,
  },
  // ---- SK하이닉스 법률 (LEGAL) ----
  {
    id: 'ENT_SK_ITC',
    companyId: 'COMP_SK',
    categoryCode: 'LEGAL',
    name: 'ITC 특허소송',
    type: 'CASE',
    subType: '특허침해',
    position: '',
    description: '마이크론 제소 HBM 특허 침해',
    riskScore: 100,  // 60 + 40 = 100
    eventCount: 2,
  },
  {
    id: 'ENT_SK_FTC',
    companyId: 'COMP_SK',
    categoryCode: 'LEGAL',
    name: '공정위 담합조사',
    type: 'CASE',
    subType: '담합',
    position: '',
    description: 'DRAM 가격 담합 의혹',
    riskScore: 55,
    eventCount: 1,
  },
  // ---- SK하이닉스 ESG ----
  {
    id: 'ENT_SK_ENV',
    companyId: 'COMP_SK',
    categoryCode: 'ESG',
    name: '이천공장 환경이슈',
    type: 'ISSUE',
    subType: '환경오염',
    position: '',
    description: '폐수 유출 사고',
    riskScore: 40,
    eventCount: 1,
  },
  // ---- 삼성전자 임원 (EXEC) ----
  {
    id: 'ENT_SS_JY',
    companyId: 'COMP_SS',
    categoryCode: 'EXEC',
    name: '이재용',
    type: 'PERSON',
    subType: '임원',
    position: '회장',
    description: '삼성전자 회장',
    riskScore: 0,  // -15 이벤트이지만 양수만 집계
    eventCount: 1,
  },
  // ---- 삼성전자 운영 (OPS) ----
  {
    id: 'ENT_SS_3NM',
    companyId: 'COMP_SS',
    categoryCode: 'OPS',
    name: '3nm 수율이슈',
    type: 'ISSUE',
    subType: '생산',
    position: '',
    description: '파운드리 수율 문제',
    riskScore: 30,
    eventCount: 1,
  },
  // ---- SK머티리얼즈 감사 (AUDIT) ----
  {
    id: 'ENT_SKM_AUDIT',
    companyId: 'COMP_SKM',
    categoryCode: 'AUDIT',
    name: '분식회계 의혹',
    type: 'ISSUE',
    subType: '회계',
    position: '',
    description: '매출 과대계상 의혹',
    riskScore: 70,
    eventCount: 1,
  },
  // ---- 삼성SDI 운영 (OPS) ----
  {
    id: 'ENT_SDI_FIRE',
    companyId: 'COMP_SDI',
    categoryCode: 'OPS',
    name: '배터리 화재',
    type: 'ISSUE',
    subType: '안전',
    position: '',
    description: '전기차 배터리 화재',
    riskScore: 50,
    eventCount: 1,
  },
];

// ============================================
// RiskEvent 데이터 (14개)
// ============================================
export const MOCK_EVENTS_V2: RiskEventV2[] = [
  // ---- 노종원 CFO 이벤트 ----
  {
    id: 'EVT_SK_CFO_01',
    entityId: 'ENT_SK_CFO',
    title: 'SK하이닉스 CFO 사임',
    summary: '노종원 CFO 개인 사유로 사임 발표',
    type: 'DISCLOSURE',
    score: 45,
    severity: 'HIGH',
    sourceName: 'DART',
    sourceUrl: 'https://dart.fss.or.kr/1',
    publishedAt: '2026-01-28T09:00:00Z',
    isActive: true,
  },
  {
    id: 'EVT_SK_CFO_02',
    entityId: 'ENT_SK_CFO',
    title: 'CFO 사임 후 주가 하락',
    summary: 'CFO 사임 소식에 주가 3% 하락',
    type: 'NEWS',
    score: 20,
    severity: 'MEDIUM',
    sourceName: '한경',
    sourceUrl: 'https://hankyung.com/1',
    publishedAt: '2026-01-29T10:30:00Z',
    isActive: true,
  },
  // ---- 곽노정 CEO 이벤트 ----
  {
    id: 'EVT_SK_CEO_01',
    entityId: 'ENT_SK_CEO',
    title: 'CEO 스톡옵션 행사',
    summary: '곽노정 CEO 100억원 규모 스톡옵션 행사',
    type: 'DISCLOSURE',
    score: 15,
    severity: 'LOW',
    sourceName: 'DART',
    sourceUrl: 'https://dart.fss.or.kr/2',
    publishedAt: '2026-01-25T14:00:00Z',
    isActive: true,
  },
  // ---- SK텔레콤 주주 이벤트 ----
  {
    id: 'EVT_SK_SKT_01',
    entityId: 'ENT_SK_SKT',
    title: 'SK텔레콤 지분 매각',
    summary: 'SK텔레콤이 지분 일부 매각, 20.1% -> 18.5%',
    type: 'NEWS',
    score: 35,
    severity: 'HIGH',
    sourceName: '연합뉴스',
    sourceUrl: 'https://yna.co.kr/1',
    publishedAt: '2026-02-01T08:00:00Z',
    isActive: true,
  },
  // ---- 국민연금 주주 이벤트 ----
  {
    id: 'EVT_SK_NPS_01',
    entityId: 'ENT_SK_NPS',
    title: '국민연금 지분 확대',
    summary: '국민연금 지분 9.5% -> 9.8% 확대',
    type: 'NEWS',
    score: -10,
    severity: 'LOW',
    sourceName: '머니투데이',
    sourceUrl: 'https://mt.co.kr/1',
    publishedAt: '2026-02-02T09:00:00Z',
    isActive: true,
  },
  // ---- ITC 특허소송 이벤트 ----
  {
    id: 'EVT_SK_ITC_01',
    entityId: 'ENT_SK_ITC',
    title: 'ITC 특허 침해 소송 제기',
    summary: '마이크론이 ITC에 HBM 특허 침해 소송 제기',
    type: 'NEWS',
    score: 60,
    severity: 'CRITICAL',
    sourceName: '로이터',
    sourceUrl: 'https://reuters.com/1',
    publishedAt: '2026-02-03T16:00:00Z',
    isActive: true,
  },
  {
    id: 'EVT_SK_ITC_02',
    entityId: 'ENT_SK_ITC',
    title: 'ITC 예비판정 SK 불리',
    summary: 'ITC 예비판정에서 SK하이닉스에 불리한 결정',
    type: 'NEWS',
    score: 40,
    severity: 'CRITICAL',
    sourceName: '블룸버그',
    sourceUrl: 'https://bloomberg.com/1',
    publishedAt: '2026-02-04T11:00:00Z',
    isActive: true,
  },
  // ---- 공정위 담합조사 이벤트 ----
  {
    id: 'EVT_SK_FTC_01',
    entityId: 'ENT_SK_FTC',
    title: '공정위 담합 조사 착수',
    summary: 'DRAM 가격 담합 의혹으로 본사 현장조사',
    type: 'NEWS',
    score: 55,
    severity: 'CRITICAL',
    sourceName: '연합뉴스',
    sourceUrl: 'https://yna.co.kr/2',
    publishedAt: '2026-02-05T08:00:00Z',
    isActive: true,
  },
  // ---- 이천공장 ESG 이벤트 ----
  {
    id: 'EVT_SK_ENV_01',
    entityId: 'ENT_SK_ENV',
    title: '이천 공장 폐수 유출',
    summary: '산업 폐수가 인근 하천으로 유출',
    type: 'NEWS',
    score: 40,
    severity: 'HIGH',
    sourceName: 'KBS',
    sourceUrl: 'https://kbs.co.kr/1',
    publishedAt: '2026-01-20T18:00:00Z',
    isActive: true,
  },
  // ---- 이재용 회장 이벤트 ----
  {
    id: 'EVT_SS_JY_01',
    entityId: 'ENT_SS_JY',
    title: '이재용 회장 경영복귀',
    summary: '이재용 회장 본격 경영 복귀',
    type: 'NEWS',
    score: -15,
    severity: 'LOW',
    sourceName: '조선일보',
    sourceUrl: 'https://chosun.com/1',
    publishedAt: '2026-01-22T07:00:00Z',
    isActive: true,
  },
  // ---- 3nm 수율이슈 이벤트 ----
  {
    id: 'EVT_SS_3NM_01',
    entityId: 'ENT_SS_3NM',
    title: '3nm 파운드리 수율 저조',
    summary: '3nm 수율 목표 대비 20%p 낮음',
    type: 'NEWS',
    score: 30,
    severity: 'HIGH',
    sourceName: '디지타임스',
    sourceUrl: 'https://digitimes.com/1',
    publishedAt: '2026-02-01T15:00:00Z',
    isActive: true,
  },
  // ---- SK머티리얼즈 분식회계 이벤트 ----
  {
    id: 'EVT_SKM_AUDIT_01',
    entityId: 'ENT_SKM_AUDIT',
    title: 'SK머티리얼즈 분식회계 의혹',
    summary: '금감원 감리 착수, 매출 과대계상 혐의',
    type: 'NEWS',
    score: 70,
    severity: 'CRITICAL',
    sourceName: '조선일보',
    sourceUrl: 'https://chosun.com/2',
    publishedAt: '2026-02-04T09:00:00Z',
    isActive: true,
  },
  // ---- 삼성SDI 배터리 화재 이벤트 ----
  {
    id: 'EVT_SDI_FIRE_01',
    entityId: 'ENT_SDI_FIRE',
    title: '삼성SDI 배터리 화재 리콜',
    summary: '전기차 탑재 배터리 화재, 대규모 리콜 예상',
    type: 'NEWS',
    score: 50,
    severity: 'CRITICAL',
    sourceName: '블룸버그',
    sourceUrl: 'https://bloomberg.com/2',
    publishedAt: '2026-02-03T14:00:00Z',
    isActive: true,
  },
];

// ============================================
// 관련기업 관계 (4개)
// ============================================
export const MOCK_RELATIONS_V2: CompanyRelationV2[] = [
  { mainCompanyId: 'COMP_SK', relatedCompanyId: 'COMP_SKM',  relation: '계열사', tier: 1 },
  { mainCompanyId: 'COMP_SK', relatedCompanyId: 'COMP_MU',   relation: '경쟁사', tier: 2 },
  { mainCompanyId: 'COMP_SS', relatedCompanyId: 'COMP_SDI',  relation: '계열사', tier: 1 },
  { mainCompanyId: 'COMP_SS', relatedCompanyId: 'COMP_TSMC', relation: '경쟁사', tier: 2 },
];

// ============================================
// 시뮬레이션 시나리오 (3개)
// ============================================
export const MOCK_SCENARIOS_V2: SimulationScenarioV2[] = [
  {
    id: 'SIM_BUSAN_PORT',
    name: '부산항 파업',
    description: '부산항 물류 마비로 인한 공급망 차질 (2주 이상). 수출입 물류 전면 중단 시나리오.',
    affectedCategories: ['SUPPLY', 'OPS'],
    severity: 'high',
    propagationMultiplier: 1.5,
    impactFactors: {
      SUPPLY: 30,
      OPS: 15,
    },
  },
  {
    id: 'SIM_TAIWAN_STRAIT',
    name: '대만해협 봉쇄',
    description: '대만해협 군사적 긴장 고조로 TSMC 공급 중단 위기. 글로벌 반도체 공급망 재편 필요.',
    affectedCategories: ['SUPPLY', 'OPS', 'CREDIT'],
    severity: 'high',
    propagationMultiplier: 2.0,
    impactFactors: {
      SUPPLY: 50,
      OPS: 30,
      CREDIT: 20,
    },
  },
  {
    id: 'SIM_MEMORY_CRASH',
    name: '반도체 수요 급감',
    description: '글로벌 경기 침체로 메모리 수요 30% 급감. AI 투자 감소와 동시에 소비자 수요 위축.',
    affectedCategories: ['CREDIT', 'OPS', 'SHARE'],
    severity: 'medium',
    propagationMultiplier: 1.3,
    impactFactors: {
      CREDIT: 25,
      OPS: 15,
      SHARE: 10,
    },
  },
];

// ============================================
// 점수 계산 함수
// ============================================

/** 기업별 점수 재계산 (Mock 데이터 검증용) */
export function computeCompanyScores(
  companyId: string,
  categories: RiskCategoryV2[],
  relatedCompanies: CompanyV2[]
): { directScore: number; propagatedScore: number; totalRiskScore: number; riskLevel: 'PASS' | 'WARNING' | 'CRITICAL' } {
  // 직접 점수: 해당 기업 카테고리 가중합
  const companyCats = categories.filter(c => c.companyId === companyId);
  const directScore = Math.round(companyCats.reduce((sum, c) => sum + c.weightedScore, 0));

  // 전이 점수: 관련기업 직접점수 * 0.3
  const propagatedScore = Math.round(
    relatedCompanies.reduce((sum, rc) => sum + rc.directScore, 0) * 0.3
  );

  const totalRiskScore = directScore + propagatedScore;
  const riskLevel = totalRiskScore >= 50 ? 'CRITICAL' : totalRiskScore >= 30 ? 'WARNING' : 'PASS';

  return { directScore, propagatedScore, totalRiskScore, riskLevel };
}

// ============================================
// 3D 그래프 데이터 빌더
// ============================================

/** 딜 기준 3D 그래프 데이터 생성 */
export function buildGraphData(dealId: string): GraphData3D {
  const deal = MOCK_DEALS_V2.find(d => d.id === dealId);
  if (!deal) return { nodes: [], links: [] };

  const nodes: GraphNode3D[] = [];
  const links: GraphLink3D[] = [];

  // 1. Deal 노드
  nodes.push({
    id: deal.id,
    name: deal.name,
    nodeType: 'deal',
    riskScore: 0,
    riskLevel: 'PASS',
    tier: 0,
    metadata: { analyst: deal.analyst, status: deal.status },
  });

  // 2. 메인 기업 노드
  const mainCompany = MOCK_COMPANIES_V2.find(c => c.id === deal.targetCompanyId);
  if (!mainCompany) return { nodes, links };

  nodes.push({
    id: mainCompany.id,
    name: mainCompany.name,
    nodeType: 'mainCompany',
    riskScore: mainCompany.totalRiskScore,
    riskLevel: mainCompany.riskLevel,
    tier: 1,
    metadata: { sector: mainCompany.sector, ticker: mainCompany.ticker },
  });

  links.push({
    source: deal.id,
    target: mainCompany.id,
    relationship: 'TARGET',
    dependency: 1.0,
    label: '투자대상',
    riskTransfer: 0,
  });

  // 3. 카테고리 노드 (점수 있는 것만)
  const mainCats = MOCK_CATEGORIES_V2.filter(
    c => c.companyId === mainCompany.id && c.score > 0
  );
  for (const cat of mainCats) {
    const catLevel = cat.weightedScore >= 15 ? 'CRITICAL' : cat.weightedScore >= 5 ? 'WARNING' : 'PASS';
    nodes.push({
      id: cat.id,
      name: cat.name,
      nodeType: 'riskCategory',
      riskScore: cat.score,
      riskLevel: catLevel,
      tier: 2,
      categoryCode: cat.code,
      metadata: { weight: cat.weight, weightedScore: cat.weightedScore },
    });

    links.push({
      source: mainCompany.id,
      target: cat.id,
      relationship: 'HAS_CATEGORY',
      dependency: cat.weight,
      label: cat.name,
      riskTransfer: cat.weightedScore,
    });

    // 4. 해당 카테고리의 Entity 노드
    const catEntities = MOCK_ENTITIES_V2.filter(
      e => e.companyId === mainCompany.id && e.categoryCode === cat.code
    );
    for (const ent of catEntities) {
      const entLevel = ent.riskScore >= 80 ? 'CRITICAL' : ent.riskScore >= 30 ? 'WARNING' : 'PASS';
      nodes.push({
        id: ent.id,
        name: ent.name,
        nodeType: 'riskEntity',
        riskScore: ent.riskScore,
        riskLevel: entLevel,
        tier: 3,
        entityType: ent.type,
        categoryCode: ent.categoryCode,
        metadata: { position: ent.position, subType: ent.subType },
      });

      links.push({
        source: cat.id,
        target: ent.id,
        relationship: 'HAS_ENTITY',
        dependency: 0,
        label: ent.type,
        riskTransfer: ent.riskScore,
      });
    }
  }

  // 5. 관련기업 노드
  const relatedIds = mainCompany.relatedCompanyIds;
  for (const relId of relatedIds) {
    const rel = MOCK_COMPANIES_V2.find(c => c.id === relId);
    if (!rel) continue;

    const relRelation = MOCK_RELATIONS_V2.find(
      r => r.mainCompanyId === mainCompany.id && r.relatedCompanyId === relId
    );

    nodes.push({
      id: rel.id,
      name: rel.name,
      nodeType: 'relatedCompany',
      riskScore: rel.totalRiskScore,
      riskLevel: rel.riskLevel,
      tier: relRelation?.tier ?? 1,
      metadata: {
        relation: relRelation?.relation ?? '',
        sector: rel.sector,
      },
    });

    links.push({
      source: mainCompany.id,
      target: rel.id,
      relationship: 'HAS_RELATED',
      dependency: relRelation?.tier === 1 ? 0.3 : 0.1,
      label: relRelation?.relation ?? '관련',
      riskTransfer: Math.round(rel.directScore * 0.3),
    });
  }

  return { nodes, links };
}

// ============================================
// 유틸리티 조회 함수
// ============================================

/** 기업 ID로 카테고리 목록 조회 */
export function getCategoriesByCompany(companyId: string): RiskCategoryV2[] {
  return MOCK_CATEGORIES_V2.filter(c => c.companyId === companyId);
}

/** 기업 ID + 카테고리 코드로 엔티티 목록 조회 */
export function getEntitiesByCategory(companyId: string, categoryCode: CategoryCodeV2): RiskEntityV2[] {
  return MOCK_ENTITIES_V2.filter(
    e => e.companyId === companyId && e.categoryCode === categoryCode
  );
}

/** 엔티티 ID로 이벤트 목록 조회 */
export function getEventsByEntity(entityId: string): RiskEventV2[] {
  return MOCK_EVENTS_V2.filter(e => e.entityId === entityId);
}

/** 기업 ID로 관련기업 목록 조회 */
export function getRelatedCompanies(companyId: string): CompanyV2[] {
  const company = MOCK_COMPANIES_V2.find(c => c.id === companyId);
  if (!company) return [];
  return MOCK_COMPANIES_V2.filter(c => company.relatedCompanyIds.includes(c.id));
}

/** 딜 요약 정보 계산 */
export function getDealsSummary() {
  const total = MOCK_DEALS_V2.length;
  const active = MOCK_DEALS_V2.filter(d => d.status === 'ACTIVE').length;
  const companies = MOCK_DEALS_V2.map(d =>
    MOCK_COMPANIES_V2.find(c => c.id === d.targetCompanyId)
  ).filter(Boolean) as CompanyV2[];
  const avgRisk = companies.length > 0
    ? Math.round(companies.reduce((sum, c) => sum + c.totalRiskScore, 0) / companies.length)
    : 0;
  return { total, active, avgRisk };
}
