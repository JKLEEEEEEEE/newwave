/**
 * Risk V2 - API 클라이언트
 * V2/V4 하이브리드 백엔드 연동 (API 실패 시 에러 반환)
 *
 * 엔드포인트 전략:
 *   - V4: 딜/카테고리 드릴다운 (구조화된 데이터)
 *   - V2: 시뮬레이션/AI/공급망 (기능 API)
 *   - V3: AI 인사이트
 */

import type {
  ApiResponseV2,
  DealsResponseV2,
  DealDetailResponseV2,
  CompanyDetailResponseV2,
  RiskCategoryV2,
  RiskEntityV2,
  RiskEventV2,
  Text2CypherResultV2,
  SimulationResultV2,
  SimulationScenarioV2,
  AIInsightResponseV2,
  BriefingResponse,
  RiskDriversResponse,
  RiskDriver,
  GraphData3D,
  GraphNode3D,
  GraphLink3D,
  CategoryCodeV2,
  CompanyV2,
  DealV2,
  RiskLevelV2,
  EventType,
  SeverityV2,
  TriagedEventV2,
  SourceTier,
  TriageLevel,
  CaseV2,
  CaseStatus,
} from './types-v2';

import { CATEGORY_DEFINITIONS_V2 } from './category-definitions';

// ============================================
// 설정
// ============================================
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API 서버 연결 상태 캐시 (불필요한 반복 호출 방지)
let _apiAvailable: boolean | null = null;
let _apiCheckTime = 0;
const API_CHECK_INTERVAL = 30000; // 30초

// ============================================
// 유틸리티
// ============================================

/** API 호출 래퍼 */
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<ApiResponseV2<T>> {
  const url = `${BASE_URL}${endpoint}`;

  try {
    // Content-Type은 body가 있는 요청(POST/PATCH)에만 설정 — GET에 설정하면 불필요한 CORS preflight 유발
    const headers: Record<string, string> = { ...options?.headers as Record<string, string> };
    if (options?.body) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    _apiAvailable = true;
    _apiCheckTime = Date.now();

    return {
      success: true,
      data,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    // AbortError는 정상적인 요청 취소이므로 무음 처리
    if (error instanceof DOMException && error.name === 'AbortError') {
      return {
        success: false,
        data: null as unknown as T,
        error: 'aborted',
        timestamp: new Date().toISOString(),
      };
    }
    console.error(`[RiskV2 API] Error (${endpoint}):`, error);
    return {
      success: false,
      data: null as unknown as T,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString(),
    };
  }
}

/** GPT 답변에서 JSON 래핑 제거 */
function cleanAnswer(raw: string): string {
  const trimmed = raw.trim();
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmed);
      return parsed.result || parsed.answer || parsed.text || parsed.content || trimmed;
    } catch { /* not JSON */ }
  }
  return trimmed;
}

/** 리스크 레벨 판정 */
function determineRiskLevel(score: number): RiskLevelV2 {
  if (score >= 50) return 'CRITICAL';
  if (score >= 30) return 'WARNING';
  return 'PASS';
}

/** 성공 응답 헬퍼 */
function success<T>(data: T): ApiResponseV2<T> {
  return { success: true, data, timestamp: new Date().toISOString() };
}

// ============================================
// 딜 관련 API
// ============================================

/** 전체 딜 목록 조회 (V4 → V2) */
async function fetchDealsV2(): Promise<ApiResponseV2<DealsResponseV2>> {
  // Try V4 first (structured data)
  const v4 = await fetchApi<any>('/api/v4/deals');
  if (v4.success && v4.data?.deals) {
    const deals: DealV2[] = v4.data.deals.map((d: any) => ({
      id: d.id,
      name: `${d.name} 검토`,
      status: 'ACTIVE' as const,
      analyst: '',
      targetCompanyId: d.id,
      targetCompanyName: d.name,
      registeredAt: new Date().toISOString(),
      notes: '',
      score: d.score || 0,
      riskLevel: (d.riskLevel as RiskLevelV2) || 'PASS',
    }));

    const avgRisk = deals.length > 0
      ? Math.round(v4.data.deals.reduce((s: number, d: any) => s + (d.score || 0), 0) / deals.length)
      : 0;

    return success({
      deals,
      summary: { total: deals.length, active: deals.length, avgRisk },
    });
  }

  // Try V2 fallback
  const v2 = await fetchApi<any>('/api/v2/deals');
  if (v2.success && v2.data?.deals) {
    const deals: DealV2[] = v2.data.deals.map((d: any) => ({
      id: d.id || d.name,
      name: d.name ? `${d.name} 검토` : d.id,
      status: 'ACTIVE' as const,
      analyst: '',
      targetCompanyId: d.id || d.name,
      targetCompanyName: d.name,
      registeredAt: new Date().toISOString(),
      notes: '',
    }));

    return success({
      deals,
      summary: {
        total: v2.data.summary?.total ?? deals.length,
        active: deals.length,
        avgRisk: v2.data.summary?.avgScore ?? 0,
      },
    });
  }

  // Both V4 and V2 failed
  return {
    success: false,
    data: { deals: [], summary: { total: 0, active: 0, avgRisk: 0 } },
    error: 'API 서버에 연결할 수 없습니다.',
    timestamp: new Date().toISOString(),
  };
}

/** 개별 딜 상세 조회 (V4) */
async function fetchDealDetailV2(dealId: string): Promise<ApiResponseV2<DealDetailResponseV2>> {
  // Try V4 (company name as dealId)
  const v4 = await fetchApi<any>(`/api/v4/deals/${encodeURIComponent(dealId)}`);
  if (v4.success && v4.data?.deal) {
    const d = v4.data.deal;
    const score = d.score || 0;
    const directScore = d.breakdown?.direct ?? score;
    const propagatedScore = d.breakdown?.propagated ?? 0;

    const deal: DealV2 = {
      id: dealId,
      name: `${d.name} 검토`,
      status: 'ACTIVE',
      analyst: '',
      targetCompanyId: d.id || dealId,
      targetCompanyName: d.name,
      registeredAt: new Date().toISOString(),
      notes: '',
    };

    const mainCompany: CompanyV2 = {
      id: d.id || dealId,
      name: d.name,
      ticker: '',
      sector: d.sector || '',
      market: '',
      isMain: true,
      directScore,
      propagatedScore,
      totalRiskScore: score,
      riskLevel: (d.riskLevel as RiskLevelV2) || determineRiskLevel(score),
      relatedCompanyIds: [],
    };

    // Convert V4 categories to frontend format
    const categories: RiskCategoryV2[] = (d.categories || []).map((c: any) => {
      const def = CATEGORY_DEFINITIONS_V2.find(cd => cd.code === c.code);
      return {
        id: `RC_${dealId}_${c.code}`,
        companyId: d.id || dealId,
        code: c.code as CategoryCodeV2,
        name: c.name || def?.name || c.code,
        icon: c.icon || def?.icon || '',
        weight: c.weight || def?.weight || 0,
        score: c.score || 0,
        weightedScore: c.weightedScore || (c.score || 0) * (c.weight || def?.weight || 0),
        entityCount: (c.personCount || 0) + (c.eventCount || 0),
        eventCount: c.eventCount || 0,
        trend: (c.trend as 'UP' | 'DOWN' | 'STABLE') || 'STABLE',
      };
    });

    // Fill missing categories with zeros
    for (const def of CATEGORY_DEFINITIONS_V2) {
      if (!categories.find(c => c.code === def.code)) {
        categories.push({
          id: `RC_${dealId}_${def.code}`,
          companyId: d.id || dealId,
          code: def.code,
          name: def.name,
          icon: def.icon,
          weight: def.weight,
          score: 0,
          weightedScore: 0,
          entityCount: 0,
          eventCount: 0,
          trend: 'STABLE',
        });
      }
    }

    // Try to fetch related companies from V3 supply chain
    const relatedCompanies: CompanyV2[] = [];
    const scRes = await fetchApi<any>(`/api/v3/companies/${encodeURIComponent(d.name || dealId)}/supply-chain`);
    if (scRes.success && scRes.data?.nodes) {
      for (const node of scRes.data.nodes) {
        if (node.id !== d.id && node.id !== d.name && node.type === 'company') {
          const relScore = node.riskScore || node.totalRiskScore || 0;
          relatedCompanies.push({
            id: node.id,
            name: node.name || node.id,
            ticker: '',
            sector: node.sector || '',
            market: '',
            isMain: false,
            directScore: relScore,
            propagatedScore: 0,
            totalRiskScore: relScore,
            riskLevel: determineRiskLevel(relScore),
            relatedCompanyIds: [],
            relationToMain: {
              mainId: d.id || dealId,
              relation: node.relation || node.relationship || '관련사',
              tier: node.tier || 1,
            },
          });
          mainCompany.relatedCompanyIds.push(node.id);
        }
      }
    }

    // Extract recentEvents from V4 response
    const recentEvents: RiskEventV2[] = (v4.data.deal.recentEvents || v4.data.recentEvents || []).map((e: any) => ({
      id: e.id || '',
      entityId: e.entityId || '',
      title: e.title || '',
      summary: e.summary || e.description || '',
      type: (e.type as EventType) || 'NEWS',
      score: e.score || 0,
      severity: (e.severity as SeverityV2) || 'MEDIUM',
      sourceName: e.sourceName || e.source || '',
      sourceUrl: e.sourceUrl || e.url || '',
      publishedAt: e.publishedAt || e.firstDetectedAt || e.date || new Date().toISOString(),
      isActive: e.isActive ?? true,
    }));

    return success({ deal, mainCompany, categories, relatedCompanies, recentEvents });
  }

  // API failed
  return {
    success: false,
    data: null as unknown as DealDetailResponseV2,
    error: 'API 서버에 연결할 수 없습니다. 딜 상세를 불러올 수 없습니다.',
    timestamp: new Date().toISOString(),
  };
}

// ============================================
// 기업 관련 API
// ============================================

/** 기업 상세 조회 */
async function fetchCompanyDetailV2(companyId: string): Promise<ApiResponseV2<CompanyDetailResponseV2>> {
  // Reuse deal detail logic (V4 treats company = deal)
  const detail = await fetchDealDetailV2(companyId);
  if (detail.success && detail.data) {
    const d = detail.data;
    const entities: RiskEntityV2[] = [];

    // Fetch entities for non-zero categories
    for (const cat of d.categories.filter(c => c.score > 0)) {
      const catDetail = await fetchApi<any>(
        `/api/v4/deals/${encodeURIComponent(companyId)}/categories/${cat.code}`
      );
      if (catDetail.success && catDetail.data?.category) {
        const cd = catDetail.data.category;
        // Convert events to entities (V4 structures differ from V2 types)
        for (const evt of (cd.events || [])) {
          if (evt.id) {
            entities.push({
              id: evt.id,
              companyId: companyId,
              categoryCode: cat.code,
              name: evt.title || evt.id,
              type: 'ISSUE',
              subType: cat.name,
              position: '',
              description: evt.title || '',
              riskScore: evt.score || 0,
              eventCount: (evt.newsCount || 0) + (evt.disclosureCount || 0),
            });
          }
        }
        for (const p of (cd.persons || [])) {
          if (p.id) {
            entities.push({
              id: p.id,
              companyId: companyId,
              categoryCode: cat.code,
              name: p.name || p.id,
              type: 'PERSON',
              subType: p.type || '임원',
              position: p.position || '',
              description: `${p.name} (${p.position || ''})`,
              riskScore: p.riskScore || 0,
              eventCount: 0,
            });
          }
        }
      }
    }

    return success({
      company: d.mainCompany,
      categories: d.categories,
      entities,
      relatedCompanies: d.relatedCompanies,
    });
  }

  // API failed
  return {
    success: false,
    data: null as unknown as CompanyDetailResponseV2,
    error: 'API 서버에 연결할 수 없습니다. 기업 상세를 불러올 수 없습니다.',
    timestamp: new Date().toISOString(),
  };
}

/** 기업 3D 그래프 데이터 조회 (V4 graph → client-side build) */
async function fetchCompanyGraphV2(dealId: string): Promise<ApiResponseV2<GraphData3D>> {
  // Try V4 server-side graph API first
  const graphRes = await fetchApi<any>(`/api/v4/deals/${encodeURIComponent(dealId)}/graph`);
  if (graphRes.success && graphRes.data?.nodes?.length > 0) {
    const nodes: GraphNode3D[] = graphRes.data.nodes.map((n: any) => ({
      id: n.id,
      name: n.name,
      nodeType: n.nodeType || n.type || 'relatedCompany',
      riskScore: n.riskScore || 0,
      riskLevel: n.riskLevel || 'PASS',
      tier: n.tier || 0,
      categoryCode: n.categoryCode,
      metadata: n.metadata || {},
    }));
    const links: GraphLink3D[] = (graphRes.data.links || []).map((l: any) => ({
      source: l.source,
      target: l.target,
      relationship: l.relationship || 'HAS_RELATED',
      dependency: l.dependency || 0,
      label: l.label || '',
      riskTransfer: l.riskTransfer || 0,
    }));
    return success({ nodes, links });
  }

  // Fallback: build graph from deal detail data (client-side)
  const detail = await fetchDealDetailV2(dealId);
  if (detail.success && detail.data) {
    const { deal, mainCompany, categories, relatedCompanies } = detail.data;
    const nodes: GraphNode3D[] = [];
    const links: GraphLink3D[] = [];

    // Deal node
    nodes.push({
      id: deal.id,
      name: deal.name,
      nodeType: 'deal',
      riskScore: 0,
      riskLevel: 'PASS',
      tier: 0,
      metadata: { analyst: deal.analyst, status: deal.status },
    });

    // Main company node
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

    // Category nodes (score > 0)
    for (const cat of categories.filter(c => c.score > 0)) {
      const catLevel = cat.weightedScore >= 15 ? 'CRITICAL' : cat.weightedScore >= 5 ? 'WARNING' : 'PASS';
      nodes.push({
        id: cat.id,
        name: cat.name,
        nodeType: 'riskCategory',
        riskScore: cat.score,
        riskLevel: catLevel as RiskLevelV2,
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
    }

    // Related company nodes
    for (const rel of relatedCompanies) {
      const relRelation = rel.relationToMain;
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

    return success({ nodes, links });
  }

  // Both graph API and deal detail failed
  return {
    success: false,
    data: { nodes: [], links: [] },
    error: 'API 서버에 연결할 수 없습니다.',
    timestamp: new Date().toISOString(),
  };
}

// ============================================
// 카테고리 / 엔티티 / 이벤트 드릴다운 API
// ============================================

/** 특정 카테고리의 엔티티 목록 조회 (V4) */
async function fetchCategoryEntitiesV2(
  companyId: string,
  categoryCode: CategoryCodeV2
): Promise<ApiResponseV2<RiskEntityV2[]>> {
  const v4 = await fetchApi<any>(
    `/api/v4/deals/${encodeURIComponent(companyId)}/categories/${categoryCode}`
  );

  if (v4.success && v4.data?.category) {
    const cd = v4.data.category;
    const entities: RiskEntityV2[] = [];

    // Convert V4 events to RiskEntity
    for (const evt of (cd.events || [])) {
      if (evt.id) {
        entities.push({
          id: evt.id,
          companyId,
          categoryCode,
          name: evt.title || evt.id,
          type: 'ISSUE',
          subType: cd.name || categoryCode,
          position: '',
          description: evt.title || '',
          riskScore: evt.score || 0,
          eventCount: (evt.newsCount || 0) + (evt.disclosureCount || 0),
        });
      }
    }

    // Convert V4 persons to RiskEntity
    for (const p of (cd.persons || [])) {
      if (p.id) {
        entities.push({
          id: p.id,
          companyId,
          categoryCode,
          name: p.name || p.id,
          type: 'PERSON',
          subType: p.type || '임원',
          position: p.position || '',
          description: `${p.name} (${p.position || ''})`,
          riskScore: p.riskScore || 0,
          eventCount: 0,
        });
      }
    }

    return success(entities);
  }

  // API failed - return empty array
  return success([] as RiskEntityV2[]);
}

/** 특정 엔티티의 이벤트 목록 조회 (V4) */
async function fetchEntityEventsV2(entityId: string): Promise<ApiResponseV2<RiskEventV2[]>> {
  const v4 = await fetchApi<any>(`/api/v4/events/${encodeURIComponent(entityId)}`);

  if (v4.success && v4.data?.event) {
    const evt = v4.data.event;
    const events: RiskEventV2[] = [];

    // Main event
    events.push({
      id: evt.id,
      entityId,
      title: evt.title || '',
      summary: evt.description || '',
      type: evt.isActive ? 'NEWS' : 'ISSUE',
      score: evt.score || 0,
      severity: (evt.severity as any) || 'MEDIUM',
      sourceName: '',
      sourceUrl: '',
      publishedAt: evt.firstDetectedAt || new Date().toISOString(),
      isActive: evt.isActive ?? true,
    });

    // Related news as events
    for (const n of (evt.news || [])) {
      if (n.id) {
        events.push({
          id: n.id,
          entityId,
          title: n.title || '',
          summary: n.title || '',
          type: 'NEWS',
          score: n.rawScore || 0,
          severity: n.rawScore >= 50 ? 'CRITICAL' : n.rawScore >= 30 ? 'HIGH' : n.rawScore >= 10 ? 'MEDIUM' : 'LOW',
          sourceName: n.source || '',
          sourceUrl: n.url || '',
          publishedAt: n.publishedAt || new Date().toISOString(),
          isActive: true,
        });
      }
    }

    // Related disclosures as events
    for (const d of (evt.disclosures || [])) {
      if (d.id) {
        events.push({
          id: d.id,
          entityId,
          title: d.title || '',
          summary: d.title || '',
          type: 'DISCLOSURE',
          score: d.rawScore || 0,
          severity: d.rawScore >= 50 ? 'CRITICAL' : d.rawScore >= 30 ? 'HIGH' : d.rawScore >= 10 ? 'MEDIUM' : 'LOW',
          sourceName: 'DART',
          sourceUrl: d.url || '',
          publishedAt: d.filingDate || new Date().toISOString(),
          isActive: true,
        });
      }
    }

    return success(events);
  }

  // API failed - return empty array
  return success([] as RiskEventV2[]);
}

// ============================================
// AI 기능 API
// ============================================

/** 자연어 질의 (Text2Cypher) → POST /api/v2/ai/query */
async function queryNaturalLanguageV2(question: string): Promise<ApiResponseV2<Text2CypherResultV2>> {
  const res = await fetchApi<any>('/api/v2/ai/query', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });

  if (res.success && res.data) {
    const d = res.data;
    return success({
      question: d.question || question,
      cypher: d.cypher || '',
      explanation: d.explanation || '',
      results: d.results || [],
      answer: cleanAnswer(d.answer || ''),
      visualizationType: d.visualizationType || 'table',
      success: d.success !== false,
    });
  }

  // Fallback: generic response
  return success({
    question,
    cypher: `MATCH (n) WHERE n.name CONTAINS "${question}" RETURN n LIMIT 10`,
    explanation: `"${question}"에 대한 검색 쿼리입니다. API 서버 연결을 확인하세요.`,
    results: [],
    answer: 'API 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인하세요.',
    visualizationType: 'table',
    success: false,
  });
}

/** 시뮬레이션 실행 → POST /api/v2/simulate */
async function runSimulationV2(
  scenarioId: string,
  dealIds?: string[]
): Promise<ApiResponseV2<SimulationResultV2[]>> {
  const res = await fetchApi<any>('/api/v2/simulate', {
    method: 'POST',
    body: JSON.stringify({ scenarioId, dealIds }),
  });

  if (res.success && Array.isArray(res.data)) {
    // Convert backend results to frontend format
    const results: SimulationResultV2[] = res.data.map((r: any) => ({
      dealId: r.dealId || r.id || '',
      dealName: r.dealName || r.name || '',
      companyId: r.companyId || r.id || '',
      originalScore: r.originalScore || r.original_score || 0,
      simulatedScore: r.simulatedScore || r.simulated_score || 0,
      delta: r.delta || 0,
      affectedCategories: r.affectedCategories || r.affected_categories || [],
      cascadePath: r.cascadePath || r.cascade_path || [],
      aiInterpretation: r.aiInterpretation || r.ai_interpretation || '',
    }));
    return success(results);
  }

  // API failed
  return {
    success: false,
    data: [],
    error: 'API 서버에 연결할 수 없습니다. 시뮬레이션을 실행할 수 없습니다.',
    timestamp: new Date().toISOString(),
  };
}

/** 시나리오 목록 조회 → GET /api/v2/scenarios */
async function fetchScenariosV2(): Promise<ApiResponseV2<SimulationScenarioV2[]>> {
  const res = await fetchApi<any>('/api/v2/scenarios');

  if (res.success && Array.isArray(res.data)) {
    const scenarios: SimulationScenarioV2[] = res.data.map((s: any) => ({
      id: s.id,
      name: s.name,
      description: s.description || '',
      affectedCategories: s.affectedCategories || s.affectedSectors || [],
      severity: s.severity || 'medium',
      propagationMultiplier: s.propagationMultiplier || 1.0,
      impactFactors: s.impactFactors || {},
    }));
    return success(scenarios);
  }

  // API failed
  return {
    success: false,
    data: [],
    error: 'API 서버에 연결할 수 없습니다. 시나리오를 불러올 수 없습니다.',
    timestamp: new Date().toISOString(),
  };
}

/** AI 인사이트 조회 → GET /api/v3/ai/insight/{companyName} */
async function fetchAIInsightV2(companyNameOrId: string): Promise<ApiResponseV2<AIInsightResponseV2>> {
  const res = await fetchApi<any>(`/api/v3/ai/insight/${encodeURIComponent(companyNameOrId)}`);

  if (res.success && res.data) {
    const d = res.data;
    const insight = d.insight || d;
    return success({
      summary: insight.summary || insight.executive_summary || d.company + ' 리스크 분석',
      keyFindings: insight.key_findings || insight.keyFindings || [],
      recommendation: insight.recommendations?.[0] || insight.recommendation || '',
      confidence: insight.confidence || 0.7,
      generatedAt: d.generatedAt || new Date().toISOString(),
    });
  }

  // Fallback: generic insight
  return success({
    summary: `${companyNameOrId}에 대한 AI 인사이트를 생성할 수 없습니다. API 서버 연결을 확인하세요.`,
    keyFindings: ['API 서버 연결 필요'],
    recommendation: 'FastAPI 서버를 시작한 후 다시 시도하세요.',
    confidence: 0,
    generatedAt: new Date().toISOString(),
  });
}

/** 리스크 드라이버 조회 → GET /api/v4/deals/{dealId}/drivers */
async function fetchRiskDriversV2(dealId: string, signal?: AbortSignal): Promise<ApiResponseV2<RiskDriversResponse>> {
  const res = await fetchApi<any>(`/api/v4/deals/${encodeURIComponent(dealId)}/drivers`, { signal });
  if (res.success && res.data) {
    const d = res.data;
    return success({
      companyName: d.companyName || dealId,
      totalScore: d.totalScore || 0,
      directScore: d.directScore || 0,
      propagatedScore: d.propagatedScore || 0,
      riskLevel: d.riskLevel || 'PASS',
      topDrivers: (d.topDrivers || []).map((dr: any) => ({
        categoryCode: dr.categoryCode || '',
        categoryName: dr.categoryName || '',
        categoryIcon: dr.categoryIcon || '',
        score: dr.score || 0,
        weight: dr.weight || 0,
        weightedScore: dr.weightedScore || 0,
        contribution: dr.contribution || 0,
        eventCount: dr.eventCount || 0,
        isPropagated: dr.isPropagated || false,
      })),
      allDrivers: (d.allDrivers || []).map((dr: any) => ({
        categoryCode: dr.categoryCode || '',
        categoryName: dr.categoryName || '',
        categoryIcon: dr.categoryIcon || '',
        score: dr.score || 0,
        weight: dr.weight || 0,
        weightedScore: dr.weightedScore || 0,
        contribution: dr.contribution || 0,
        eventCount: dr.eventCount || 0,
        isPropagated: dr.isPropagated || false,
      })),
    });
  }
  return {
    success: false,
    data: { companyName: dealId, totalScore: 0, directScore: 0, propagatedScore: 0, riskLevel: 'PASS', topDrivers: [], allDrivers: [] },
    error: res.error || 'Failed to fetch risk drivers',
    timestamp: new Date().toISOString(),
  };
}

/** AI 브리핑 조회 */
async function fetchBriefingV2(dealId: string, signal?: AbortSignal): Promise<ApiResponseV2<BriefingResponse>> {
  const url = `${BASE_URL}/api/v4/deals/${encodeURIComponent(dealId)}/briefing`;
  try {
    const res = await fetch(url, { signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { success: true, data, timestamp: new Date().toISOString() };
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      return { success: false, data: null as any, error: 'aborted', timestamp: new Date().toISOString() };
    }
    console.error('[fetchBriefingV2]', err);
    return { success: false, data: null as any, error: String(err), timestamp: new Date().toISOString() };
  }
}

// ============================================
// Smart Triage 이벤트 API
// ============================================

/** 트리아지된 이벤트 목록 조회 */
async function fetchTriagedEventsV2(dealId: string, limit = 30): Promise<ApiResponseV2<TriagedEventV2[]>> {
  const res = await fetchApi<any>(`/api/v4/deals/${encodeURIComponent(dealId)}/events/triaged?limit=${limit}`);
  if (res.success && res.data?.events) {
    const events: TriagedEventV2[] = res.data.events.map((e: any) => ({
      id: e.id || '',
      entityId: e.entityId || '',
      title: e.title || '',
      summary: e.summary || '',
      type: (e.type as EventType) || 'NEWS',
      score: e.score || 0,
      severity: (e.severity as SeverityV2) || 'MEDIUM',
      sourceName: e.sourceName || '',
      sourceUrl: e.sourceUrl || '',
      publishedAt: e.publishedAt || '',
      urgency: e.urgency || 0,
      confidence: e.confidence || 0,
      triageScore: e.triageScore || 0,
      triageLevel: (e.triageLevel || 'MEDIUM') as TriageLevel,
      sourceTier: (e.sourceTier || 'COMMUNITY') as SourceTier,
      sourceReliability: e.sourceReliability || 0,
      hasConflict: e.hasConflict || false,
      playbook: e.playbook || [],
      categoryCode: e.categoryCode || '',
      categoryName: e.categoryName || '',
    }));
    return success(events);
  }

  // API 실패 시 클라이언트 사이드 트리아지 폴백
  return success([] as TriagedEventV2[]);
}

// ============================================
// Global Critical Alerts API
// ============================================

/** 전체 딜 대상 CRITICAL 이벤트 독립 조회 (네비바 알림용) */
async function fetchCriticalAlertsV2(): Promise<ApiResponseV2<TriagedEventV2[]>> {
  const res = await fetchApi<any>('/api/v4/alerts/critical');
  if (res.success && res.data?.alerts) {
    const alerts: TriagedEventV2[] = res.data.alerts.map((e: any) => ({
      id: e.id || '',
      entityId: e.entityId || '',
      title: e.title || '',
      summary: e.summary || '',
      type: (e.type as EventType) || 'NEWS',
      score: e.score || 0,
      severity: (e.severity as SeverityV2) || 'MEDIUM',
      sourceName: e.sourceName || '',
      sourceUrl: e.sourceUrl || '',
      publishedAt: e.publishedAt || '',
      urgency: e.urgency || 0,
      confidence: e.confidence || 0,
      triageScore: e.triageScore || 0,
      triageLevel: (e.triageLevel || 'CRITICAL') as TriageLevel,
      sourceTier: (e.sourceTier || 'COMMUNITY') as SourceTier,
      sourceReliability: e.sourceReliability || 0,
      hasConflict: e.hasConflict || false,
      playbook: e.playbook || [],
      categoryCode: e.categoryCode || '',
      categoryName: e.categoryName || '',
      companyName: e.companyName || '',
    }));
    return success(alerts);
  }
  return success([] as TriagedEventV2[]);
}

// ============================================
// Case Management API
// ============================================

/** 케이스 목록 조회 */
async function fetchCasesV2(dealId: string): Promise<ApiResponseV2<CaseV2[]>> {
  const res = await fetchApi<any>(`/api/v4/deals/${encodeURIComponent(dealId)}/cases`);
  if (res.success && res.data?.cases) {
    return success(res.data.cases.map((c: any) => ({
      id: c.id,
      eventId: c.event_id,
      eventTitle: c.event_title,
      status: (c.status || 'OPEN') as CaseStatus,
      assignee: c.assignee || '',
      notes: c.notes || '',
      priority: c.priority || 'MEDIUM',
      createdAt: c.created_at || '',
      updatedAt: c.updated_at || '',
    })));
  }
  return success([] as CaseV2[]);
}

/** 케이스 생성 */
async function createCaseV2(dealId: string, eventId: string, eventTitle: string, assignee = ''): Promise<ApiResponseV2<CaseV2>> {
  const res = await fetchApi<any>(`/api/v4/deals/${encodeURIComponent(dealId)}/cases`, {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId, event_title: eventTitle, assignee }),
  });
  if (res.success && res.data) {
    const c = res.data;
    return success({
      id: c.id,
      eventId: c.event_id,
      eventTitle: c.event_title,
      status: c.status as CaseStatus,
      assignee: c.assignee || '',
      notes: c.notes || '',
      priority: c.priority || 'MEDIUM',
      createdAt: c.created_at || '',
      updatedAt: c.updated_at || '',
    });
  }
  return { success: false, data: null as any, error: res.error || 'Failed to create case', timestamp: new Date().toISOString() };
}

/** 케이스 업데이트 */
async function updateCaseV2(dealId: string, caseId: string, updates: Partial<{ status: CaseStatus; assignee: string; notes: string }>): Promise<ApiResponseV2<CaseV2>> {
  const res = await fetchApi<any>(`/api/v4/deals/${encodeURIComponent(dealId)}/cases/${caseId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
  if (res.success && res.data) {
    const c = res.data;
    return success({
      id: c.id,
      eventId: c.event_id,
      eventTitle: c.event_title,
      status: c.status as CaseStatus,
      assignee: c.assignee || '',
      notes: c.notes || '',
      priority: c.priority || 'MEDIUM',
      createdAt: c.created_at || '',
      updatedAt: c.updated_at || '',
    });
  }
  return { success: false, data: null as any, error: res.error || 'Failed to update case', timestamp: new Date().toISOString() };
}

// ============================================
// 건강 체크
// ============================================

/** API 서버 상태 확인 */
async function checkApiHealthV2(): Promise<boolean> {
  // 캐시된 결과 사용 (30초 이내)
  if (_apiAvailable !== null && Date.now() - _apiCheckTime < API_CHECK_INTERVAL) {
    return _apiAvailable;
  }

  try {
    const response = await fetch(`${BASE_URL}/health`, { method: 'GET' });
    _apiAvailable = response.ok;
    _apiCheckTime = Date.now();
    return _apiAvailable;
  } catch {
    _apiAvailable = false;
    _apiCheckTime = Date.now();
    return false;
  }
}

// ============================================
// 내보내기 (riskApiV2 객체)
// ============================================
export const riskApiV2 = {
  // 딜
  fetchDeals: fetchDealsV2,
  fetchDealDetail: fetchDealDetailV2,
  // 기업
  fetchCompanyDetail: fetchCompanyDetailV2,
  fetchCompanyGraph: fetchCompanyGraphV2,
  // 드릴다운
  fetchCategoryEntities: fetchCategoryEntitiesV2,
  fetchEntityEvents: fetchEntityEventsV2,
  // 시뮬레이션
  fetchScenarios: fetchScenariosV2,
  runSimulation: runSimulationV2,
  // AI
  fetchRiskDrivers: fetchRiskDriversV2,
  queryNaturalLanguage: queryNaturalLanguageV2,
  fetchAIInsight: fetchAIInsightV2,
  fetchBriefing: fetchBriefingV2,
  // Live Events (Smart Triage)
  fetchTriagedEvents: fetchTriagedEventsV2,
  // Critical Alerts (Global)
  fetchCriticalAlerts: fetchCriticalAlertsV2,
  // Case Management
  fetchCases: fetchCasesV2,
  createCase: createCaseV2,
  updateCase: updateCaseV2,
  // 유틸
  checkApiHealth: checkApiHealthV2,
  // 상태
  get isMockMode() { return false; },
} as const;

export default riskApiV2;
