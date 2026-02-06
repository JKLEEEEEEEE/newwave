
import React, { useState, useCallback, useMemo } from 'react';
import Header from './components/Header';
import DocumentViewer from './components/DocumentViewer';
import AnalysisPanel from './components/AnalysisPanel';
import MonitoringDashboard from './components/MonitoringDashboard';
import GlobalDashboard from './components/GlobalDashboard';
import Timeline from './components/Timeline';
import ApiStatusBar from './components/ApiStatusBar';
import { HurdleStatus, VerificationData, DealSummary, ScoringModule, APIScoringResult } from './types';
import PDFUploadModal from './components/PDFUploadModal';

// GLOBAL_DEALS 데이터는 원본 보존
// --- 1. Centralized Raw Data ---
const DEAL_RAW_DATA: Record<string, any> = {
  case1: {
    _meta: { name: '골든락 마이닝', sector: '광업', sponsor: 'NW 투자에쿼티', status: HurdleStatus.PASS, progress: '관리', mainMetric: '1,144억', lastSignal: 'DSCR 4.3x 안정적', lastUpdated: '방금 전' },
    ocf: '15.00%', fcf: '안정적 흑자', dscr: '4.3x', netDebt: '2.75x', icr: '3.5x', currentRatio: '210%', cagr: '12%', opm: '15%', debtRatio: '85%', debtDep: '45%', roe: '12%', turnover: '5%', hiring: '8%', salary: '상위 10%', credit: 'BBB+', recruitment: '보통', sponsorBlind: '1', sponsorAUM: '5조', ltv: '45%', dealSize: '1.2조', seniority: '선순위', control: '일부 담보'
  },
  case2: {
    _meta: { name: '오비탈 에어로스페이스', sector: '우주항공', sponsor: 'NW 투자에쿼티', status: HurdleStatus.FAIL, progress: '심사', mainMetric: '278억', lastSignal: 'Net Debt 5.18x 위험', lastUpdated: '10분 전' },
    ocf: '4.00%', fcf: '소폭 적자', dscr: '2.1x', netDebt: '5.18x', icr: '1.2x', currentRatio: '85%', cagr: '25%', opm: '2%', debtRatio: '320%', debtDep: '65%', roe: '3%', turnover: '25%', hiring: '20%', salary: '상위 10%', credit: 'BB', recruitment: '매우 빈번', sponsorBlind: '0', sponsorAUM: '8,000억', ltv: '75%', dealSize: '4,200억', seniority: '후순위', control: '미확보'
  },
  case3: {
    _meta: { name: '넥스트 로보틱스', sector: '로봇', sponsor: 'NT 파트너스', status: HurdleStatus.WARNING, progress: '검토', mainMetric: '228억', lastSignal: '상장 준비중 (Pre-IPO)', lastUpdated: '1시간 전' },
    // Mocking missing data for case3 using case2 as base but better
    ocf: '8.00%', fcf: '균형', dscr: '2.5x', netDebt: '3.0x', icr: '2.0x', currentRatio: '150%', cagr: '20%', opm: '8%', debtRatio: '200%', debtDep: '50%', roe: '8%', turnover: '15%', hiring: '15%', salary: '상위 20%', credit: 'BBB', recruitment: '빈번', sponsorBlind: '0', sponsorAUM: '1조', ltv: '60%', dealSize: '3,000억', seniority: '선순위', control: '일부'
  },
  case4: {
    _meta: { name: '사이버다인 시스템즈', sector: '렌탈', sponsor: 'NT 파트너스', status: HurdleStatus.WARNING, progress: '심사', mainMetric: '260억', lastSignal: 'ICR 1.3x 주의', lastUpdated: '3시간 전' },
    ocf: '6.00%', fcf: '소폭 흑자', dscr: '1.8x', netDebt: '4.0x', icr: '1.5x', currentRatio: '100%', cagr: '15%', opm: '5%', debtRatio: '180%', debtDep: '55%', roe: '5%', turnover: '10%', hiring: '10%', salary: '상위 30%', credit: 'BB+', recruitment: '보통', sponsorBlind: '1', sponsorAUM: '2조', ltv: '55%', dealSize: '5,000억', seniority: '후순위', control: '미확보'
  },
  case5: {
    _meta: { name: '아르젠텀 리소스', sector: '제련', sponsor: '인피니티 에쿼티', status: HurdleStatus.PASS, progress: '집행', mainMetric: '1,141억', lastSignal: '신용등급 A 최우량', lastUpdated: '5시간 전' },
    ocf: '18.00%', fcf: '안정적 흑자', dscr: '4.4x', netDebt: '2.65x', icr: '4.0x', currentRatio: '250%', cagr: '5%', opm: '18%', debtRatio: '65%', debtDep: '35%', roe: '15%', turnover: '2%', hiring: '5%', salary: '상위 10%', credit: 'A', recruitment: '결원 시만', sponsorBlind: '1', sponsorAUM: '12조', ltv: '35%', dealSize: '1.5조', seniority: '선순위', control: '완전 확보'
  },
  case6: {
    _meta: { name: '세미콘 퓨처테크', sector: '반도체', sponsor: 'NW 투자에쿼티', status: HurdleStatus.PASS, progress: '심사', mainMetric: '1,288억', lastSignal: '흑자 전환 성공', lastUpdated: '2시간 전' },
    ocf: '12.00%', fcf: '흑자 전환', dscr: '3.0x', netDebt: '2.0x', icr: '3.0x', currentRatio: '180%', cagr: '10%', opm: '12%', debtRatio: '90%', debtDep: '40%', roe: '10%', turnover: '5%', hiring: '10%', salary: '상위 10%', credit: 'BBB', recruitment: '보통', sponsorBlind: '1', sponsorAUM: '4조', ltv: '40%', dealSize: '8,000억', seniority: '선순위', control: '확보'
  },
  case7: {
    _meta: { name: '퀀텀 칩 솔루션', sector: '소재', sponsor: 'NT 파트너스', status: HurdleStatus.PASS, progress: '검토', mainMetric: '1,279억', lastSignal: 'DSCR 3.4x 양호', lastUpdated: '6시간 전' },
    ocf: '10.00%', fcf: '안정적', dscr: '3.4x', netDebt: '2.2x', icr: '3.5x', currentRatio: '200%', cagr: '15%', opm: '10%', debtRatio: '100%', debtDep: '45%', roe: '8%', turnover: '8%', hiring: '10%', salary: '상위 20%', credit: 'BBB+', recruitment: '보통', sponsorBlind: '1', sponsorAUM: '3조', ltv: '50%', dealSize: '6,000억', seniority: '선순위', control: '일부'
  }
};

// --- 2. Calculation Helper ---
const generateModules = (dealName: string, id: string, raw: any): ScoringModule[] => {
  // Safe Accessor
  const r = raw || DEAL_RAW_DATA.case1; // Fallback

  // Use dealName or ID to pick data is redundant if passed raw, 
  // but keeping signature similar to logic if needed.

  return [
    {
      id: 'm1', title: '1. 상환능력 (Cash Flow)', description: '현금흐름 및 부채상환 커버리지', totalScore: 0,
      details: [
        { category: '현금흐름', item: 'EBITDA 규모(절대금액)', score: 5, value: r._meta ? r._meta.mainMetric : r.dealSize /* fallback */, weight: 15 },
        { category: '현금흐름', item: '영업활동현금흐름(OCF)', score: parseFloat(r.ocf) > 10 ? 5 : 2, value: r.ocf, weight: 15 },
        { category: '현금흐름', item: '잉여현금흐름(FCF)', score: r.fcf.includes('안정') || r.fcf.includes('흑자') ? 5 : 2, value: r.fcf, weight: 15 },
        { category: '커버리지', item: 'DSCR(총부채상환비율)', score: parseFloat(r.dscr) > 2.0 ? 5 : 3, value: r.dscr, weight: 15 },
        { category: '커버리지', item: 'Net Debt / EBITDA', score: parseFloat(r.netDebt) < 2.0 ? 5 : 2, value: r.netDebt, weight: 15 },
        { category: '커버리지', item: '이자보상배율(ICR)', score: parseFloat(r.icr) > 5.0 ? 5 : 2, value: r.icr, weight: 15 },
        { category: '재무안정성', item: '유동비율', score: parseFloat(r.currentRatio) > 200 ? 5 : 3, value: r.currentRatio, weight: 10 },
      ]
    },
    {
      id: 'm2', title: '2. 재무 기초 (Fundamentals)', description: '성장성, 수익성 및 재무 건전성', totalScore: 0,
      details: [
        { category: '성장성', item: '매출액 증가율(CAGR)', score: parseFloat(r.cagr) > 10 ? 5 : 3, value: r.cagr, weight: 20 },
        { category: '수익성', item: '영업이익률(OPM)', score: parseFloat(r.opm) > 10 ? 5 : 2, value: r.opm, weight: 20 },
        { category: '안정성', item: '부채비율', score: parseFloat(r.debtRatio) < 100 ? 5 : 2, value: r.debtRatio, weight: 20 },
        { category: '안정성', item: '차입금 의존도', score: parseFloat(r.debtDep) < 15 ? 5 : 3, value: r.debtDep, weight: 20 },
        { category: '수익성', item: 'ROE(자기자본이익률)', score: parseFloat(r.roe) > 15 ? 5 : 2, value: r.roe, weight: 20 },
      ]
    },
    {
      id: 'm3', title: '3. HR/비재무 (Soft Data)', description: '인력 리스크 및 대외 평판', totalScore: 0,
      details: [
        { category: '인력 이탈', item: '최근 1년 퇴사율', score: parseFloat(r.turnover) < 10 ? 5 : 2, value: r.turnover, weight: 20 },
        { category: '조직 활력', item: '고용 증가율(YoY)', score: parseFloat(r.hiring) > 10 ? 5 : 3, value: r.hiring, weight: 20 },
        { category: '처우 수준', item: '평균 연봉(업계 순위)', score: r.salary.includes('10%') ? 5 : 3, value: r.salary, weight: 20 },
        { category: '신용도', item: '기업 신용등급(NICE)', score: r.credit.startsWith('A') ? 5 : 3, value: r.credit, weight: 20 },
        { category: '평판', item: '채용 공고 빈도', score: r.recruitment.includes('결원') ? 5 : 2, value: r.recruitment, weight: 20 },
      ]
    },
    {
      id: 'm4', title: '4. Sponsor (운용사)', description: 'GP 역량 및 펀드 안정성', totalScore: 0,
      details: [
        { category: '신뢰도', item: '블라인드 펀드 유무', score: r.sponsorBlind === '1' ? 5 : 1, value: r.sponsorBlind === '1' ? '보유' : '미보유', weight: 15 },
        { category: '전문성', item: '운용 전문인력 수', score: 5, value: '25명 초과', weight: 15 },
        { category: '업력', item: '운용사 존속 기간', score: 5, value: '20년 초과', weight: 15 },
        { category: '규모', item: 'AUM(운용자산)', score: r.sponsorAUM.includes('10조') ? 5 : 3, value: r.sponsorAUM, weight: 20 },
        { category: '안정성', item: '만기시 리파이낸싱 비율', score: 4, value: '80% 이하', weight: 15 },
        { category: '경험', item: 'Track Record(유사 딜)', score: 5, value: '10건 이상', weight: 20 },
      ]
    },
    {
      id: 'm5', title: '5. Deal 구조 (Structure)', description: '구조적 안정성 및 담보 확보', totalScore: 0,
      details: [
        { category: '형태', item: '단일 스폰서 여부', score: 5, value: '1 (Single)', weight: 15 },
        { category: '담보', item: 'LTV(담보인정비율)', score: parseFloat(r.ltv) < 40 ? 5 : 3, value: r.ltv, weight: 15 },
        { category: '레버리지', item: 'LTC(Loan To Cost)', score: 4, value: '7배 이하', weight: 15 },
        { category: '규모', item: 'Deal Size(금액)', score: 5, value: r.dealSize, weight: 20 },
        { category: '우선권', item: '상환 우선순위', score: r.seniority === '선순위' ? 5 : 1, value: r.seniority, weight: 15 },
        { category: '통제권', item: '담보/경영권 확보', score: r.control.includes('완전') ? 5 : 2, value: r.control, weight: 20 },
      ]
    },
    {
      id: 'm6', title: '6. Target 구조 (Target)', description: '타겟 기업 시장 지배력', totalScore: 0,
      details: [
        { category: '지배력', item: '실질지배력 확보율', score: 5, value: '50% 초과', weight: 25 },
        { category: '지배력', item: '단일 최대주주 유지기간', score: 5, value: '최초 초달', weight: 25 },
        { category: '시장지위', item: 'Market Share (순위)', score: 5, value: '1위 (선도)', weight: 25 },
        { category: '수익성(상대)', item: '동종업계 대비 수익성', score: 4, value: '상위 20%', weight: 25 },
      ]
    }
  ].map(m => ({
    ...m,
    totalScore: m.details.reduce((acc, d) => acc + d.score, 0)
  }));
};

// --- 3. Generate Initial Deals ---
// Uses the logic above to ensure specific numbers match
const INITIAL_DEALS: DealSummary[] = Object.keys(DEAL_RAW_DATA).map(key => {
  const raw = DEAL_RAW_DATA[key];
  const meta = raw._meta;
  const modules = generateModules(meta.name, key, raw);

  // Calculate Total Score Sum and Max
  const currentScore = modules.reduce((acc, m) => acc + m.totalScore, 0);
  const maxScore = modules.reduce((acc, m) => acc + (m.details.length * 5), 0);

  return {
    id: key,
    name: meta.name,
    sector: meta.sector as any,
    sponsor: meta.sponsor,
    status: meta.status,
    progress: meta.progress as any,
    mainMetric: { label: 'Deal Size', value: raw.dealSize }, // Matching Detailed Report Header
    lastSignal: meta.lastSignal,
    lastUpdated: meta.lastUpdated,
    totalScore: currentScore,
    maxScore: maxScore
  };
});

const getAnalysisData = (caseId: string, allDeals: DealSummary[]): VerificationData => {
  const deal = allDeals.find(x => x.id === caseId) || allDeals[0];
  const dealRaw = DEAL_RAW_DATA[deal.id] || DEAL_RAW_DATA['case1'];

  // Use shared logic
  const modules = generateModules(deal.name, deal.id, dealRaw);

  return {
    dealInfo: {
      sponsor: deal.sponsor,
      borrower: `${deal.name} SPC`,
      target: deal.name,
      dealSize: dealRaw.dealSize,
      equity: 'KRW 4,800억',
      debt: 'KRW 7,200억',
    },
    modules,
    verdict: {
      status: deal.status === HurdleStatus.FAIL ? '투자 부적격 (REJECT)' : deal.status === HurdleStatus.WARNING ? '조건부 승인 (WATCH)' : '승인 권고 (BUY)',
      description: deal.status === HurdleStatus.FAIL
        ? "레버리지 비율(Net Debt 5.18x) 및 DSCR이 임계치를 크게 벗어남. 현금 흐름 악화에 따른 부도 위험이 매우 높음."
        : "이미지 속 32개 핵심 심사 지표를 벤치마킹한 결과, 상환 능력 및 딜 구조 측면에서 매우 견고한 안정성을 보여주고 있음.",
      totalScore: deal.totalScore || 0
    },
    timeline: [
      { id: 't1', label: 'IM 데이터 추출 완료', date: '2025-05-10', type: 'disclosure', active: false },
      { id: 't2', label: '32개 전 항목 자동 스코어링', date: '2025-05-12', type: 'news', active: false },
      { id: 't3', label: '최환석 대리 최종 검토', date: '2025-05-14', type: 'news', active: true },
    ]
  };
};

const mergeApiData = (baseData: VerificationData, apiResult: APIScoringResult | null): VerificationData => {
  if (!apiResult) return baseData;

  const { run, results } = apiResult;

  // 1. Module Mapping
  // Group results by module
  const moduleMap = new Map<string, typeof results>();
  results.forEach(r => {
    // Map module_name to id or use logic. 
    // Since we don't have exact ID mapping from DB to frontend static IDs, we'll try to map by name or order.
    // For now, let's look at the module_name string.
    // Frontend IDs: m1, m2, m3, m4, m5, m6
    // Database Modules: Cash Flow, Fundamentals, Soft Data, Sponsor, Structure, Target

    let mId = 'm1';
    if (r.module_name.includes('Cash')) mId = 'm1';
    else if (r.module_name.includes('Basic') || r.module_name.includes('Fundamental')) mId = 'm2';
    else if (r.module_name.includes('Soft') || r.module_name.includes('HR')) mId = 'm3';
    else if (r.module_name.includes('Sponsor') || r.module_name.includes('GP')) mId = 'm4';
    else if (r.module_name.includes('Structure') || r.module_name.includes('Deal')) mId = 'm5';
    else if (r.module_name.includes('Target') || r.module_name.includes('Market')) mId = 'm6';

    const list = moduleMap.get(mId) || [];
    list.push(r);
    moduleMap.set(mId, list);
  });

  const newModules = baseData.modules.map(mod => {
    const apiItems = moduleMap.get(mod.id);
    if (!apiItems) return mod;

    // Calculate new total score for module
    const totalScore = apiItems.reduce((acc, cur) => acc + (cur.score_raw || 0), 0) / (apiItems.length || 1);

    return {
      ...mod,
      totalScore: totalScore,
      details: apiItems.map(item => ({
        category: 'AI Analysis', // mapping category is hard without DB field, using placeholder
        item: item.item_name,
        score: item.score_raw,
        value: item.extracted_value,
        weight: 15 // Placeholder
      }))
    };
  });

  return {
    ...baseData,
    modules: newModules,
    verdict: {
      ...baseData.verdict,
      totalScore: run.total_score,
      description: run.project_summary.industry_overview_highlights[0] || baseData.verdict.description
    },
    // We can also pass the summary to be used in DocumentViewer if we prop drill different data, 
    // but VerificationData might not have a field for it. 
    // We will attach it loosely or extend type if needed. For now, let's stick to replacing existing fields.
  };
};

const App: React.FC = () => {
  const [deals, setDeals] = useState<DealSummary[]>(INITIAL_DEALS);
  const [viewMode, setViewMode] = useState<'analysis' | 'monitoring' | 'global'>('global');
  const [selectedDealId, setSelectedDealId] = useState<string>('case1');
  const [leftWidth, setLeftWidth] = useState(42);
  const [isResizing, setIsResizing] = useState(false);
  const [activeRefPage, setActiveRefPage] = useState<number | null>(null);

  // New States for IM Analysis
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  const [apiResult, setApiResult] = useState<APIScoringResult | null>(null);

  // Fetch API data when runId changes
  React.useEffect(() => {
    if (!currentRunId) return;

    fetch(`http://localhost:3001/api/im/run/${currentRunId}`)
      .then(res => res.json())
      .then(data => {
        setApiResult(data);
      })
      .catch(err => console.error("Failed to fetch run", err));
  }, [currentRunId]);

  // Force update deals when INITIAL_DEALS changes (to reflect new scoring logic in dev)
  React.useEffect(() => {
    setDeals(prev => {
      const dbDeals = new Map(INITIAL_DEALS.map(d => [d.id, d]));
      return prev.map(d => {
        if (dbDeals.has(d.id)) {
          // Update static deals with new calculated scores
          return dbDeals.get(d.id)!;
        }
        return d; // Keep dynamic deals as is
      });
    });
  }, []);

  const startResizing = useCallback(() => setIsResizing(true), []);
  const stopResizing = useCallback(() => setIsResizing(false), []);
  const onResize = useCallback((e: MouseEvent) => {
    if (isResizing) {
      const newWidth = (e.clientX / window.innerWidth) * 100;
      if (newWidth > 20 && newWidth < 80) setLeftWidth(newWidth);
    }
  }, [isResizing]);

  React.useEffect(() => {
    window.addEventListener('mousemove', onResize);
    window.addEventListener('mouseup', stopResizing);
    return () => {
      window.removeEventListener('mousemove', onResize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [onResize, stopResizing]);

  const analysisData = useMemo(() => {
    const base = getAnalysisData(selectedDealId, deals);
    return mergeApiData(base, apiResult);
  }, [selectedDealId, apiResult]);

  // Pass summary specifically to DocumentViewer if possible
  // We'll trust analysisData to carry enough info or modify DocumentViewer props
  const projectSummary = apiResult?.run.project_summary;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-50 font-['Pretendard']">
      <Header onViewChange={(v) => setViewMode(v)} currentView={viewMode} />
      <ApiStatusBar />

      <div className="flex-1 overflow-hidden relative flex flex-col">
        {viewMode === 'analysis' && (
          <main className="flex-1 flex overflow-hidden relative border-t border-slate-200">
            <div style={{ width: `${leftWidth}%` }} className="h-full overflow-hidden flex flex-col">
              <DocumentViewer
                dealId={selectedDealId}
                activePage={activeRefPage}
                onUploadClick={() => setIsUploadModalOpen(true)}
                aiSummary={projectSummary}
              />
            </div>
            <div className="w-1 cursor-col-resize resizable-handle z-10 bg-slate-200 hover:bg-[#003366] transition-colors" onMouseDown={startResizing} />
            <div style={{ width: `${100 - leftWidth}%` }} className="h-full overflow-hidden bg-white">
              <AnalysisPanel data={analysisData} onHurdleClick={(p) => setActiveRefPage(p)} activeHurdlePage={activeRefPage} />
            </div>
          </main>
        )}

        {viewMode === 'monitoring' && (
          <main className="flex-1 overflow-hidden bg-[#020617]">
            <MonitoringDashboard />
          </main>
        )}

        {viewMode === 'global' && (
          <main className="flex-1 overflow-y-auto custom-scrollbar">
            <GlobalDashboard
              deals={deals}
              alerts={[]}
              onDealClick={(id) => {
                setSelectedDealId(id);
                setViewMode('analysis');
              }}
              onAddClick={() => setIsUploadModalOpen(true)}
            />
          </main>
        )}
      </div>

      {viewMode === 'analysis' && <Timeline events={analysisData.timeline} />}

      <PDFUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={(runId) => {
          // 1. Set current run ID for fetching results
          setCurrentRunId(runId);

          // 2. Fetch run details immediately to create a deal entry
          fetch(`http://localhost:3001/api/im/run/${runId}`)
            .then(res => res.json())
            .then((data: APIScoringResult) => {
              // Create new deal object
              const newDeal: DealSummary = {
                id: `case_new_${runId}`,
                name: data.run.file_name.replace('.pdf', ''), // Simple name derivation
                sector: 'IB', // Default or extract if possible
                sponsor: 'Unknown',
                status: HurdleStatus.WARNING, // Default
                progress: '검토',
                mainMetric: { label: 'Total Score', value: `${data.run.total_score}pt` },
                lastSignal: 'AI 분석 완료',
                lastUpdated: '방금 전',
                totalScore: data.run.total_score,
                maxScore: 165 // Standard template max score
              };

              setDeals(prev => [newDeal, ...prev]);
              setSelectedDealId(newDeal.id);
              setViewMode('analysis');
            })
            .catch(err => console.error("Error fetching new run details", err));

          setIsUploadModalOpen(false);
        }}
      />
    </div>
  );
};

export default App;
