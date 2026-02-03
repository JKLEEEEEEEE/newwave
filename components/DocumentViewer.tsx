
import React, { useState, useMemo } from 'react';

interface Props {
  dealId: string;
  activePage: number | null;
}

const DocumentViewer: React.FC<Props> = ({ dealId, activePage }) => {
  const [activeTab, setActiveTab] = useState<'pdf' | 'excel'>('pdf');

  const content = useMemo(() => {
    const cases: Record<string, any> = {
      case1: {
        title: 'Project Golden',
        subtitle: '투자 설명서(IM): 골든락 유통 지분 인수금융',
        sector: '국내 온/오프라인 유통 및 이커머스 솔루션',
        context: '국내 중소 이커머스 판매자를 위한 통합 물류 및 정산 솔루션 시장의 독보적 선점자임.',
        highlight: '안정적 현금흐름(EBITDA 1,144억)을 바탕으로 한 원리금 상환 안정성 확보.',
        dealSize: 'KRW 1.1조',
        equity: 'KRW 4,500억',
        debt: 'KRW 6,500억',
        leverage: '2.75x (Net Debt/EBITDA)',
        risk: '이커머스 시장 경쟁 심화 및 물류 단가 상승 리스크 상존함.'
      },
      case2: {
        title: 'Project Orbit',
        subtitle: '투자 설명서(IM): 오비탈 에어로 리파이낸싱',
        sector: '차세대 저궤도 위성 통신 및 항공 우주 부품',
        context: '기술력은 독보적이나, R&D 비용 과다 지출로 인한 영업적자가 지속되고 있는 고위험 섹터임.',
        highlight: '적자 지속 및 부채 의존도 심화(Net Debt 5.18x)로 인해 추가 자금 조달에 제약 발생.',
        dealSize: 'KRW 4,200억',
        equity: 'KRW 1,000억',
        debt: 'KRW 3,200억',
        leverage: '5.18x (주의 레벨)',
        risk: '현금 흐름 악화에 따른 부도 위기 시그널 포착. DSCR 2.1x로 임계치 접근.'
      },
      case5: {
        title: 'Project Argentum',
        subtitle: '투자 설명서(IM): 아르젠텀 리소스 자산 유동화',
        sector: '글로벌 핵심 광물 공급망 및 자원 재생',
        context: '글로벌 공급망 재편의 핵심 수혜 기업으로, 업계 점유율 1위의 시장 지배력을 보유함.',
        highlight: '압도적 상환 능력(EBITDA 1,141억, 신용등급 A)을 보유한 최우량 딜 시나리오.',
        dealSize: 'KRW 1.5조',
        equity: 'KRW 6,000억',
        debt: 'KRW 9,000억',
        leverage: '2.65x (우수 수준)',
        risk: '정치적 지정학적 리스크 외에 재무적 리스크는 매우 제한적임.'
      },
    };

    return cases[dealId] || cases.case5;
  }, [dealId]);

  return (
    <div className="flex flex-col h-full bg-slate-100 font-sans">
      <div className="flex bg-slate-200 p-1 border-b border-slate-300">
        <button 
          onClick={() => setActiveTab('pdf')}
          className={`px-4 py-2 text-xs font-bold rounded-t transition-all ${activeTab === 'pdf' ? 'bg-white text-[#003366] border-b-2 border-[#003366] shadow-sm' : 'text-slate-500 hover:bg-slate-300'}`}
        >
          [IM 보고서: {content.title}]
        </button>
        <button 
          onClick={() => setActiveTab('excel')}
          className={`px-4 py-2 text-xs font-bold rounded-t transition-all ${activeTab === 'excel' ? 'bg-white text-[#003366] border-b-2 border-[#003366] shadow-sm' : 'text-slate-500 hover:bg-slate-300'}`}
        >
          [현금흐름 시뮬레이션]
        </button>
      </div>

      <div className="flex-1 p-8 overflow-y-auto custom-scrollbar flex flex-col items-center">
        <div className="w-full max-w-[700px] bg-white shadow-xl p-16 relative mb-12 min-h-[1000px] border border-slate-200">
          <div className="absolute top-8 right-12 text-[9px] text-rose-600 font-bold border border-rose-200 px-2 py-0.5 rounded uppercase">대외주의 - 사외 배포금지</div>
          
          <div className="mb-12 border-b border-slate-100 pb-8">
            <h2 className="text-3xl font-black text-slate-900 mb-2">{content.title}</h2>
            <p className="text-sm text-slate-500 font-bold tracking-tight">{content.subtitle}</p>
            <div className="h-1.5 w-20 bg-[#003366] mt-6"></div>
          </div>

          <div className="space-y-10 text-sm text-slate-700 leading-relaxed">
            <section>
              <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
                <span className="w-1.5 h-4 bg-[#003366] rounded-full"></span> 1. 산업 개요 및 핵심 하이라이트
              </h3>
              <p className="mb-4 text-slate-600">
                본 건은 <span className="font-bold text-slate-900">{content.sector}</span> 섹터의 선도 기업에 대한 투자 적정성 검토 건임.
              </p>
              <div className="bg-slate-50 p-6 rounded-lg border border-slate-100">
                <ul className="list-disc ml-4 space-y-3 text-slate-600">
                  <li><span className="font-bold text-slate-900">시장 지위:</span> {content.context}</li>
                  <li><span className="font-bold text-slate-900">핵심 강점:</span> {content.highlight}</li>
                </ul>
              </div>
            </section>

            <section className={`transition-all duration-700 rounded-lg p-8 border ${activePage === 2 ? 'bg-emerald-50 border-emerald-300 ring-4 ring-emerald-100 shadow-lg scale-[1.02]' : 'bg-slate-50 border-slate-100'}`}>
              <h3 className="text-base font-bold text-slate-900 mb-4">2. 딜 구조 및 자금 조달 계획</h3>
              <table className="w-full text-xs mb-6">
                <tbody>
                  <tr className="border-b border-slate-200"><td className="py-3 text-slate-400">총 펀딩 규모</td><td className="py-3 font-black text-[#003366] text-right">{content.dealSize}</td></tr>
                  <tr className="border-b border-slate-200"><td className="py-3 text-slate-400">자기 자본 (Equity)</td><td className="py-3 font-bold text-right">{content.equity}</td></tr>
                  <tr className="border-b border-slate-200"><td className="py-3 text-slate-400">인수 금융 (Debt)</td><td className="py-3 font-black text-rose-600 text-right">{content.debt}</td></tr>
                </tbody>
              </table>
              <p className="text-[11px] italic text-slate-500 leading-normal">
                * 주요 재무 임계치: 레버리지 비율 <span className="bg-[#003366] px-2 py-0.5 rounded text-white font-bold">{content.leverage}</span> 산출. 
              </p>
            </section>

            <section className={`transition-all duration-700 rounded-lg p-8 border ${activePage === 3 ? 'bg-amber-50 border-amber-300 ring-4 ring-amber-100 shadow-lg scale-[1.02]' : 'bg-slate-50 border-slate-100'}`}>
              <h3 className="text-base font-bold text-slate-900 mb-4">3. 주요 위험 요소 및 사후 관리 방안</h3>
              <p className="text-xs leading-relaxed text-slate-600">
                {content.risk}
                <br /><br />
                당사는 본 건의 <span className="font-bold text-slate-900">상환 순위</span> 및 <span className="font-bold text-slate-900">담보권</span> 실행 가능성을 최우선으로 검토하였으며, 부실 시나리오 발생 시 AI 리스크 관제 센터를 통해 즉각적인 대응 프로세스를 가동할 예정임.
              </p>
            </section>
          </div>

          <div className="absolute bottom-12 left-0 right-0 text-center">
            <div className="inline-block px-5 py-1.5 bg-slate-100 rounded-full text-[10px] text-slate-400 font-black tracking-widest uppercase">JB INTERNAL - Page {activePage || 1} of 12</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentViewer;
