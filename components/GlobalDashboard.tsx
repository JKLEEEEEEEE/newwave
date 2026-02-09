import React from 'react';
import { DealSummary, HurdleStatus } from '../types';
import StatusBadge from './StatusBadge';

interface Props {
  deals: DealSummary[];
  alerts: any[]; // 현재 사용 안 함. 타입 맞추려면 GlobalAlert import 유지해도 됨
  onDealClick: (dealId: string) => void;
  onAddClick?: () => void;
}

/** 한글 통화 문자열 → 억 단위 숫자 변환 (예: '1.2조' → 12000, '4,200억' → 4200) */
function parseKrwToEok(value: string): number {
  if (!value) return 0;
  const cleaned = value.replace(/,/g, '').replace(/\s/g, '');
  // '조' 포함
  const joMatch = cleaned.match(/([\d.]+)\s*조/);
  if (joMatch) return parseFloat(joMatch[1]) * 10000;
  // '억' 포함
  const eokMatch = cleaned.match(/([\d.]+)\s*억/);
  if (eokMatch) return parseFloat(eokMatch[1]);
  return 0;
}

/** 억 단위 합산 → 백억 단위 반올림 → 'KRW X.X조' 포맷 */
function formatAum(totalEok: number): string {
  // 백억 단위 반올림: 1000억 단위에서 100억 자리 반올림
  const rounded = Math.round(totalEok / 1000) * 1000;
  const jo = rounded / 10000;
  return `KRW ${jo.toFixed(1)}조`;
}

const GlobalDashboard: React.FC<Props> = ({ deals, onDealClick, onAddClick }) => {
  const totalAum = React.useMemo(() => {
    const totalEok = deals.reduce((sum, deal) => sum + parseKrwToEok(deal.mainMetric?.value || ''), 0);
    return formatAum(totalEok);
  }, [deals]);

  return (
    <div className="p-8 space-y-10 bg-[#f8fafc] min-h-full">
      {/* 1. 상단 요약 스탯 */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard label="총 운용 자산 (AUM)" value={totalAum} icon="🏦" />
        <StatCard label="현재 검토 중인 딜" value={`${deals.length} 건`} icon="📄" />
        <StatCard
          label="평균 리스크 점수"
          value={`${(deals.reduce((acc, d) => acc + (d.totalScore || 0), 0) / (deals.length || 1)).toFixed(1)} pt`}
          icon="📊"
        />
        <StatCard label="데이터 파이프라인" value="정상" icon="🛡️" />
      </section>

      {/* 2. 포트폴리오 그리드 컨테이너 */}
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-5">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-4 bg-[#003366] rounded-full shadow-[0_0_8px_rgba(0,51,102,0.3)]"></div>
            <h3 className="text-sm font-black text-[#003366] uppercase tracking-widest">
              투자 자산 목록
            </h3>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-[10px] font-bold text-slate-400">
              전체 포트폴리오:
              <span className="text-[#003366] font-black ml-1">{deals.length}</span>
            </div>

            <button
              onClick={onAddClick}
              className="flex items-center gap-2 bg-[#003366] text-white px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-[#002244] transition-all shadow-lg shadow-blue-900/20 active:scale-95"
              type="button"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 4v16m8-8H4" />
              </svg>
              Add New IM
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-8">
          {deals.map((deal, idx) => (
            <div
              key={deal.id}
              onClick={() => onDealClick(deal.id)}
              className="bg-white p-7 rounded-3xl border border-slate-200 shadow-sm hover:shadow-2xl hover:border-[#003366]/30 transition-all cursor-pointer group flex flex-col min-h-[260px] relative overflow-hidden"
            >
              {/* 카드 배경 효과 */}
              <div className="absolute -right-4 -top-4 w-24 h-24 bg-slate-50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>

              <div className="flex justify-between items-start mb-8 relative z-10">
                <div className="flex items-center gap-4">
                  {/* 숫자 인덱스 (01, 02...) */}
                  <div
                    className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-sm border transition-all duration-300 ${deal.status === HurdleStatus.FAIL
                      ? 'bg-rose-50 text-rose-600 border-rose-100'
                      : 'bg-slate-50 text-slate-400 border-slate-100 group-hover:bg-[#003366] group-hover:text-white group-hover:scale-110 shadow-sm'
                      }`}
                  >
                    {(idx + 1).toString().padStart(2, '0')}
                  </div>

                  <div className="overflow-hidden">
                    <h4 className="font-black text-[#003366] text-base truncate leading-tight group-hover:text-blue-700 transition-colors">
                      {deal.name}
                    </h4>
                    <p className="text-[10px] font-bold text-slate-400 uppercase mt-1 tracking-tight">
                      {deal.sector} | {deal.sponsor}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex-1 space-y-5 mb-8 relative z-10">
                <div className="flex justify-between items-end border-b border-slate-50 pb-2.5">
                  <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">핵심 지표</span>
                  <span className="text-sm font-black text-slate-900">{deal.mainMetric.value}</span>
                </div>

                <div className="flex justify-between items-end border-b border-slate-50 pb-2.5">
                  <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">진행 단계</span>
                  <span className={`text-xs font-black ${deal.progress === '관리' ? 'text-emerald-600' : 'text-[#003366]'}`}>
                    {deal.progress}
                  </span>
                </div>
              </div>

              <div className="flex justify-between items-center mt-auto relative z-10">
                <StatusBadge status={deal.status} />
                <div className="text-right">
                  <p className="text-2xl font-black text-[#003366] tracking-tighter drop-shadow-sm">
                    {deal.totalScore}
                    <span className="text-[14px] text-slate-400/80 ml-1.5 font-bold tracking-tight">
                      / {deal.maxScore}
                    </span>
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ label, value, icon }: { label: string; value: string; icon: string }) => (
  <div className="bg-white p-7 rounded-3xl border border-slate-200 shadow-sm flex items-center gap-5 hover:border-[#003366]/20 transition-all hover:shadow-md">
    <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center text-2xl shadow-inner border border-slate-100">
      {icon}
    </div>
    <div>
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-1">{label}</p>
      <p className="text-2xl font-black text-[#003366] tracking-tight">{value}</p>
    </div>
  </div>
);

export default GlobalDashboard;
