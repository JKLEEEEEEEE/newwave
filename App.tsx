
import React, { useState, useCallback, useMemo } from 'react';
import Header from './components/Header';
import DocumentViewer from './components/DocumentViewer';
import AnalysisPanel from './components/AnalysisPanel';
import MonitoringDashboard from './components/MonitoringDashboard';
import GlobalDashboard from './components/GlobalDashboard';
import Timeline from './components/Timeline';
import ApiStatusBar from './components/ApiStatusBar';
import { RiskPage } from './components/risk';
import RiskShell from './components/risk-v2/layout/RiskShell';
import { HurdleStatus, VerificationData, DealSummary, ScoringModule } from './types';

// GLOBAL_DEALS 데이터는 원본 보존
const GLOBAL_DEALS: DealSummary[] = [
  { id: 'case1', name: '골든락 마이닝', sector: '광업', sponsor: 'NW 투자에쿼티', status: HurdleStatus.PASS, progress: '관리', mainMetric: { label: 'EBITDA', value: '1,144억' }, lastSignal: 'DSCR 4.3x 안정적', lastUpdated: '방금 전', totalScore: 89 },
  { id: 'case2', name: '오비탈 에어로스페이스', sector: '우주항공', sponsor: 'NW 투자에쿼티', status: HurdleStatus.FAIL, progress: '심사', mainMetric: { label: 'EBITDA', value: '278억' }, lastSignal: 'Net Debt 5.18x 위험', lastUpdated: '10분 전', totalScore: 42 },
  { id: 'case3', name: '넥스트 로보틱스', sector: '로봇', sponsor: 'NT 파트너스', status: HurdleStatus.WARNING, progress: '검토', mainMetric: { label: 'EBITDA', value: '228억' }, lastSignal: '상장 준비중 (Pre-IPO)', lastUpdated: '1시간 전', totalScore: 65 },
  { id: 'case4', name: '사이버다인 시스템즈', sector: '렌탈', sponsor: 'NT 파트너스', status: HurdleStatus.WARNING, progress: '심사', mainMetric: { label: 'EBITDA', value: '260억' }, lastSignal: 'ICR 1.3x 주의', lastUpdated: '3시간 전', totalScore: 58 },
  { id: 'case5', name: '아르젠텀 리소스', sector: '제련', sponsor: '인피니티 에쿼티', status: HurdleStatus.PASS, progress: '집행', mainMetric: { label: 'EBITDA', value: '1,141억' }, lastSignal: '신용등급 A 최우량', lastUpdated: '5시간 전', totalScore: 94 },
  { id: 'case6', name: '세미콘 퓨처테크', sector: '반도체', sponsor: 'NW 투자에쿼티', status: HurdleStatus.PASS, progress: '심사', mainMetric: { label: 'EBITDA', value: '1,288억' }, lastSignal: '흑자 전환 성공', lastUpdated: '2시간 전', totalScore: 91 },
  { id: 'case7', name: '퀀텀 칩 솔루션', sector: '소재', sponsor: 'NT 파트너스', status: HurdleStatus.PASS, progress: '검토', mainMetric: { label: 'EBITDA', value: '1,279억' }, lastSignal: 'DSCR 3.4x 양호', lastUpdated: '6시간 전', totalScore: 86 },
];

const getAnalysisData = (caseId: string): VerificationData => {
  const deal = GLOBAL_DEALS.find(x => x.id === caseId) || GLOBAL_DEALS[0];
  
  // 기존 인풋 데이터 절대 보존
  const rawData: Record<string, any> = {
    case1: { ocf: '15.00%', fcf: '안정적 흑자', dscr: '4.3x', netDebt: '2.75x', icr: '3.5x', currentRatio: '210%', cagr: '12%', opm: '15%', debtRatio: '85%', debtDep: '45%', roe: '12%', turnover: '5%', hiring: '8%', salary: '상위 10%', credit: 'BBB+', recruitment: '보통', sponsorBlind: '1', sponsorAUM: '5조', ltv: '45%', dealSize: '1.2조', seniority: '선순위', control: '일부 담보' },
    case2: { ocf: '4.00%', fcf: '소폭 적자', dscr: '2.1x', netDebt: '5.18x', icr: '1.2x', currentRatio: '85%', cagr: '25%', opm: '2%', debtRatio: '320%', debtDep: '65%', roe: '3%', turnover: '25%', hiring: '20%', salary: '상위 10%', credit: 'BB', recruitment: '매우 빈번', sponsorBlind: '0', sponsorAUM: '8,000억', ltv: '75%', dealSize: '4,200억', seniority: '후순위', control: '미확보' },
    case5: { ocf: '18.00%', fcf: '안정적 흑자', dscr: '4.4x', netDebt: '2.65x', icr: '4.0x', currentRatio: '250%', cagr: '5%', opm: '18%', debtRatio: '65%', debtDep: '35%', roe: '15%', turnover: '2%', hiring: '5%', salary: '상위 10%', credit: 'A', recruitment: '결원 시만', sponsorBlind: '1', sponsorAUM: '12조', ltv: '35%', dealSize: '1.5조', seniority: '선순위', control: '완전 확보' },
  };

  const currentRaw = rawData[caseId] || rawData.case1;

  const modules: ScoringModule[] = [
    {
      id: 'm1', title: '1. 상환능력 (Cash Flow)', description: '현금흐름 및 부채상환 커버리지', totalScore: 4.8,
      details: [
        { category: '현금흐름', item: 'EBITDA 규모(절대금액)', score: 5, value: deal.mainMetric.value, weight: 15 },
        { category: '현금흐름', item: '영업활동현금흐름(OCF)', score: parseFloat(currentRaw.ocf) > 10 ? 5 : 2, value: currentRaw.ocf, weight: 15 },
        { category: '현금흐름', item: '잉여현금흐름(FCF)', score: currentRaw.fcf.includes('안정') ? 5 : 2, value: currentRaw.fcf, weight: 15 },
        { category: '커버리지', item: 'DSCR(총부채상환비율)', score: parseFloat(currentRaw.dscr) > 2.0 ? 5 : 3, value: currentRaw.dscr, weight: 15 },
        { category: '커버리지', item: 'Net Debt / EBITDA', score: parseFloat(currentRaw.netDebt) < 2.0 ? 5 : 2, value: currentRaw.netDebt, weight: 15 },
        { category: '커버리지', item: '이자보상배율(ICR)', score: parseFloat(currentRaw.icr) > 5.0 ? 5 : 2, value: currentRaw.icr, weight: 15 },
        { category: '재무안정성', item: '유동비율', score: parseFloat(currentRaw.currentRatio) > 200 ? 5 : 3, value: currentRaw.currentRatio, weight: 10 },
      ]
    },
    {
      id: 'm2', title: '2. 재무 기초 (Fundamentals)', description: '성장성, 수익성 및 재무 건전성', totalScore: 4.2,
      details: [
        { category: '성장성', item: '매출액 증가율(CAGR)', score: parseFloat(currentRaw.cagr) > 10 ? 5 : 3, value: currentRaw.cagr, weight: 20 },
        { category: '수익성', item: '영업이익률(OPM)', score: parseFloat(currentRaw.opm) > 10 ? 5 : 2, value: currentRaw.opm, weight: 20 },
        { category: '안정성', item: '부채비율', score: parseFloat(currentRaw.debtRatio) < 100 ? 5 : 2, value: currentRaw.debtRatio, weight: 20 },
        { category: '안정성', item: '차입금 의존도', score: parseFloat(currentRaw.debtDep) < 15 ? 5 : 3, value: currentRaw.debtDep, weight: 20 },
        { category: '수익성', item: 'ROE(자기자본이익률)', score: parseFloat(currentRaw.roe) > 15 ? 5 : 2, value: currentRaw.roe, weight: 20 },
      ]
    },
    {
      id: 'm3', title: '3. HR/비재무 (Soft Data)', description: '인력 리스크 및 대외 평판', totalScore: 4.5,
      details: [
        { category: '인력 이탈', item: '최근 1년 퇴사율', score: parseFloat(currentRaw.turnover) < 10 ? 5 : 2, value: currentRaw.turnover, weight: 20 },
        { category: '조직 활력', item: '고용 증가율(YoY)', score: parseFloat(currentRaw.hiring) > 10 ? 5 : 3, value: currentRaw.hiring, weight: 20 },
        { category: '처우 수준', item: '평균 연봉(업계 순위)', score: currentRaw.salary.includes('10%') ? 5 : 3, value: currentRaw.salary, weight: 20 },
        { category: '신용도', item: '기업 신용등급(NICE)', score: currentRaw.credit.startsWith('A') ? 5 : 3, value: currentRaw.credit, weight: 20 },
        { category: '평판', item: '채용 공고 빈도', score: currentRaw.recruitment.includes('결원') ? 5 : 2, value: currentRaw.recruitment, weight: 20 },
      ]
    },
    {
      id: 'm4', title: '4. Sponsor (운용사)', description: 'GP 역량 및 펀드 안정성', totalScore: 4.1,
      details: [
        { category: '신뢰도', item: '블라인드 펀드 유무', score: currentRaw.sponsorBlind === '1' ? 5 : 1, value: currentRaw.sponsorBlind === '1' ? '보유' : '미보유', weight: 15 },
        { category: '전문성', item: '운용 전문인력 수', score: 5, value: '25명 초과', weight: 15 },
        { category: '업력', item: '운용사 존속 기간', score: 5, value: '20년 초과', weight: 15 },
        { category: '규모', item: 'AUM(운용자산)', score: currentRaw.sponsorAUM.includes('10조') ? 5 : 3, value: currentRaw.sponsorAUM, weight: 20 },
        { category: '안정성', item: '만기시 리파이낸싱 비율', score: 4, value: '80% 이하', weight: 15 },
        { category: '경험', item: 'Track Record(유사 딜)', score: 5, value: '10건 이상', weight: 20 },
      ]
    },
    {
      id: 'm5', title: '5. Deal 구조 (Structure)', description: '구조적 안정성 및 담보 확보', totalScore: 4.0,
      details: [
        { category: '형태', item: '단일 스폰서 여부', score: 5, value: '1 (Single)', weight: 15 },
        { category: '담보', item: 'LTV(담보인정비율)', score: parseFloat(currentRaw.ltv) < 40 ? 5 : 3, value: currentRaw.ltv, weight: 15 },
        { category: '레버리지', item: 'LTC(Loan To Cost)', score: 4, value: '7배 이하', weight: 15 },
        { category: '규모', item: 'Deal Size(금액)', score: 5, value: currentRaw.dealSize, weight: 20 },
        { category: '우선권', item: '상환 우선순위', score: currentRaw.seniority === '선순위' ? 5 : 1, value: currentRaw.seniority, weight: 15 },
        { category: '통제권', item: '담보/경영권 확보', score: currentRaw.control.includes('완전') ? 5 : 2, value: currentRaw.control, weight: 20 },
      ]
    },
    {
      id: 'm6', title: '6. Target 구조 (Target)', description: '타겟 기업 시장 지배력', totalScore: 4.4,
      details: [
        { category: '지배력', item: '실질지배력 확보율', score: 5, value: '50% 초과', weight: 25 },
        { category: '지배력', item: '단일 최대주주 유지기간', score: 5, value: '최초 초달', weight: 25 },
        { category: '시장지위', item: 'Market Share (순위)', score: 5, value: '1위 (선도)', weight: 25 },
        { category: '수익성(상대)', item: '동종업계 대비 수익성', score: 4, value: '상위 20%', weight: 25 },
      ]
    }
  ];

  return {
    dealInfo: {
      sponsor: deal.sponsor,
      borrower: `${deal.name} SPC`,
      target: deal.name,
      dealSize: currentRaw.dealSize,
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

const App: React.FC = () => {
  const [viewMode, setViewMode] = useState<'analysis' | 'monitoring' | 'global' | 'risk' | 'risk-v2'>('risk-v2');
  const [selectedDealId, setSelectedDealId] = useState<string>('case1');
  const [leftWidth, setLeftWidth] = useState(42);
  const [isResizing, setIsResizing] = useState(false);
  const [activeRefPage, setActiveRefPage] = useState<number | null>(null);

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

  const analysisData = useMemo(() => getAnalysisData(selectedDealId), [selectedDealId]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-50 font-['Pretendard']">
      <Header onViewChange={(v) => setViewMode(v)} currentView={viewMode} />
      <ApiStatusBar />
      
      <div className="flex-1 overflow-hidden relative flex flex-col">
        {viewMode === 'analysis' && (
          <main className="flex-1 flex overflow-hidden relative border-t border-slate-200">
            <div style={{ width: `${leftWidth}%` }} className="h-full overflow-hidden flex flex-col">
              <DocumentViewer dealId={selectedDealId} activePage={activeRefPage} />
            </div>
            <div className="w-1 cursor-col-resize resizable-handle z-10 bg-slate-200 hover:bg-[#003366] transition-colors" onMouseDown={startResizing} />
            <div style={{ width: `${100 - leftWidth}%` }} className="h-full overflow-y-auto custom-scrollbar bg-white">
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
              deals={GLOBAL_DEALS}
              alerts={[]}
              onDealClick={(id) => {
                setSelectedDealId(id);
                setViewMode('analysis');
              }}
            />
          </main>
        )}

        {viewMode === 'risk' && (
          <main className="flex-1 overflow-y-auto custom-scrollbar bg-slate-50">
            <RiskPage />
          </main>
        )}

        {viewMode === 'risk-v2' && (
          <main className="flex-1 overflow-hidden">
            <RiskShell />
          </main>
        )}
      </div>

      {viewMode === 'analysis' && <Timeline events={analysisData.timeline} />}
    </div>
  );
};

export default App;
