
import React, { useState, useEffect } from 'react';
import { VerificationData, ScoringModule } from '../types';

interface Props {
  data: VerificationData;
  onHurdleClick: (page: number) => void;
  activeHurdlePage: number | null;
  onApprove?: () => void;
}

const AnalysisPanel: React.FC<Props> = ({ data, onHurdleClick, activeHurdlePage, onApprove }) => {
  const { dealInfo, modules, verdict } = data;
  const [activeModule, setActiveModule] = useState<string>(modules[0].id);

  useEffect(() => {
    const handleScroll = () => {
      const container = document.getElementById('analysis-scroll-container');
      if (!container) return;

      for (const module of modules) {
        const el = document.getElementById(`section-${module.id}`);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top >= 0 && rect.top <= 400) {
            setActiveModule(module.id);
            break;
          }
        }
      }
    };
    const container = document.getElementById('analysis-scroll-container');
    container?.addEventListener('scroll', handleScroll);
    return () => container?.removeEventListener('scroll', handleScroll);
  }, [modules]);

  const scrollToSection = (id: string) => {
    document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="flex h-full bg-white font-sans text-slate-900">
      {/* 1. Left Sidebar Navigation */}
      <aside className="w-64 border-r border-slate-200 bg-slate-50 flex flex-col shrink-0">

        <nav className="flex-1 overflow-y-auto py-4">
          {modules.map((m, idx) => {
            const mScore = m.details.reduce((acc, d) => acc + d.score, 0);
            const mMax = m.details.length * 5;
            return (
              <button
                key={m.id}
                onClick={() => scrollToSection(m.id)}
                className={`w-full text-left px-6 py-4 flex items-center gap-3 transition-all border-r-4 ${activeModule === m.id
                  ? 'bg-[#003366]/5 border-[#003366] text-[#003366]'
                  : 'border-transparent text-slate-500 hover:bg-slate-100'
                  }`}
              >
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black transition-colors shrink-0 ${activeModule === m.id ? 'bg-[#003366] text-white' : 'bg-slate-200 text-slate-500'}`}>
                  {idx + 1}
                </span>
                <span className="text-[11px] font-black tracking-tight truncate">{m.title.split('.')[1].trim()}</span>
                <span className="ml-auto text-[10px] font-bold font-mono opacity-80 whitespace-nowrap">
                  {mScore} <span className="text-[9px] opacity-60">/ {mMax}</span>
                </span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* 2. Main Content Area */}
      <div id="analysis-scroll-container" className="flex-1 overflow-y-auto custom-scrollbar p-12 space-y-20">

        <header className="space-y-10">
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                <span className="text-[10px] font-black text-blue-500 uppercase tracking-[0.3em]">Institutional Intelligence Report</span>
              </div>
              <h2 className="text-4xl font-black text-[#003366] tracking-tighter leading-tight">
                {dealInfo.projectName || "투자 자산 정밀 채점표"}
                <br />
                <span className="text-slate-400 text-xl mt-2 block font-bold">
                  {dealInfo.projectInfo || "Enterprise Due Diligence"}
                </span>
              </h2>
            </div>
            <div className="text-right">
              <span className="px-3 py-1 bg-rose-50 text-rose-700 border border-rose-200 rounded text-[10px] font-black uppercase block mb-3">SECRET / STRICTLY CONFIDENTIAL</span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">발행일: {new Date().toISOString().slice(0, 10).replace(/-/g, '.')} | 담당: 최환석 대리</span>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-px bg-slate-100 border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
            <SummaryStat label="Borrower" value={dealInfo.borrower} />
            <SummaryStat label="Sponsor" value={dealInfo.sponsor} />
            <SummaryStat label="Deal Size" value={dealInfo.dealSize} />
            <SummaryStat label="Target Equity" value={dealInfo.equity} />
          </div>

          {/* Total Score Display */}
          <div className="bg-[#003366] rounded-3xl p-8 text-white flex items-center justify-between shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -mr-16 -mt-16"></div>
            <div>
              <p className="text-[10px] font-black text-blue-200 uppercase tracking-widest mb-1 opacity-80">Total Analysis Score</p>
              <h2 className="text-3xl font-black tracking-tight">종합 평가 점수</h2>
            </div>
            <div className="flex items-baseline gap-3 relative z-10">
              <span className="text-5xl font-black tracking-tighter shadow-black drop-shadow-lg">
                {modules.reduce((acc, m) => acc + m.details.reduce((s, d) => s + d.score, 0), 0)}
              </span>
              <span className="text-xl font-bold text-blue-200/60">
                / {modules.reduce((acc, m) => acc + m.details.length * 5, 0)}
              </span>
            </div>
          </div>
        </header>

        {/* Hurdle Verification Table */}
        {modules.map((module) => (
          <section key={module.id} id={`section-${module.id}`} className="space-y-8 scroll-mt-20">
            <div className="flex items-end justify-between border-b-2 border-slate-900 pb-5">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-black text-blue-500/60 uppercase tracking-[0.2em]">Module Intelligence</span>
                <h3 className="text-2xl font-black text-slate-900 tracking-tight">{module.title}</h3>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Module Grade</p>
                  <p className="text-2xl font-black text-[#003366]">
                    {module.details.reduce((acc, d) => acc + d.score, 0)}
                    <span className="text-xs text-slate-300 ml-1">/ {module.details.length * 5}</span>
                  </p>
                </div>
              </div>
            </div>

            <div className="overflow-hidden border border-slate-200 rounded-3xl shadow-sm">
              <table className="w-full text-left border-collapse">
                <thead className="bg-slate-50/50 border-b border-slate-200">
                  <tr>
                    <th className="px-8 py-5 font-black text-slate-400 uppercase tracking-widest text-[9px] w-[25%]">평가 지표 (KPI)</th>
                    <th className="px-8 py-5 font-black text-slate-400 uppercase tracking-widest text-[9px] w-[20%] text-center">심사 추출값</th>
                    <th className="px-8 py-5 font-black text-slate-400 uppercase tracking-widest text-[9px] w-[10%] text-right">가중치</th>
                    <th className="px-8 py-5 font-black text-slate-400 uppercase tracking-widest text-[9px] w-[45%] text-right">성과 지표 스펙트럼 (Min 1 - Max 5)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {module.details.map((detail, idx) => (
                    <tr key={idx} className="group hover:bg-slate-50/20 transition-colors">
                      <td className="px-8 py-7">
                        <div className="flex flex-col">
                          <span className="text-[9px] font-bold text-blue-400 uppercase mb-1 tracking-tight">{detail.category}</span>
                          <span className="text-[13px] font-black text-slate-700 leading-tight">{detail.item}</span>
                        </div>
                      </td>
                      <td className="px-8 py-7 text-center">
                        <span className={`inline-block px-3 py-1.5 rounded-lg font-black text-[11px] border transition-all ${detail.score >= 4 ? 'bg-[#003366]/5 text-[#003366] border-[#003366]/20' : detail.score <= 2 ? 'bg-rose-50 text-rose-600 border-rose-100' : 'bg-slate-50 text-slate-500 border-slate-200'}`}>
                          {detail.value}
                        </span>
                      </td>
                      <td className="px-8 py-7 text-right font-bold text-slate-300 text-[11px]">
                        {detail.weight}%
                      </td>
                      <td className="px-8 py-7">
                        <div className="flex flex-col items-end gap-3 w-full">
                          <div className="w-full max-w-[280px] h-1.5 bg-slate-100 rounded-full relative">
                            {/* Central Benchmark Line (Score 3) */}
                            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-200 z-0"></div>

                            {/* Score Track */}
                            <div
                              className={`absolute left-0 top-0 bottom-0 rounded-full transition-all duration-1000 ease-out ${detail.score >= 4 ? 'bg-[#003366]' : detail.score <= 2 ? 'bg-rose-500' : 'bg-amber-400'}`}
                              style={{ width: `${((detail.score - 1) / 4) * 100}%` }}
                            ></div>

                            {/* Handle / Pin */}
                            <div
                              className={`absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-white shadow-lg transition-all duration-1000 ease-out ${detail.score >= 4 ? 'bg-[#003366] shadow-blue-500/40' : detail.score <= 2 ? 'bg-rose-500 shadow-rose-500/40' : 'bg-amber-400 shadow-amber-500/40'}`}
                              style={{ left: `calc(${((detail.score - 1) / 4) * 100}% - 8px)` }}
                            >
                              <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-black text-slate-900">{detail.score}</div>
                            </div>
                          </div>
                          <div className="w-full max-w-[280px] flex justify-between px-0.5">
                            <span className="text-[8px] font-black text-slate-300 uppercase tracking-tighter">Min 1.0</span>
                            <span className="text-[8px] font-black text-slate-300 uppercase tracking-tighter">Max 5.0</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))}

        {/* Executive Verdict Section */}
        <section className="bg-slate-50 border border-slate-200 rounded-[40px] p-16 relative overflow-hidden group">
          <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-[#003366]/5 rounded-full blur-3xl group-hover:bg-[#003366]/10 transition-all duration-1000"></div>
          <div className="max-w-3xl mx-auto space-y-10 relative z-10">
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 rounded-3xl bg-[#003366] flex items-center justify-center text-white text-3xl font-black shadow-2xl shadow-blue-900/40">JB</div>
              <div>
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.5em] mb-2">Investment Committee Summary</h4>
                <h3 className="text-4xl font-black text-[#003366] tracking-tighter">{verdict.status}</h3>
              </div>
            </div>
            <div className="bg-white p-10 rounded-3xl border border-slate-100 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 left-0 w-2.5 h-full bg-[#003366]"></div>
              <p className="text-xl text-slate-600 leading-relaxed font-medium italic">
                "{verdict.description}"
              </p>
            </div>
            <div className="grid grid-cols-2 gap-8 pt-6">
              <button
                onClick={onApprove}
                className="py-5 bg-[#003366] text-white rounded-2xl font-black text-[11px] uppercase tracking-[0.2em] shadow-2xl hover:scale-[1.03] transition-all active:scale-100"
              >
                최종 심사 승인 상신 (Group Approval)
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

const SummaryStat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="bg-white p-8">
    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">{label}</p>
    <p className="text-lg font-black text-[#003366] tracking-tight">{value}</p>
  </div>
);

export default AnalysisPanel;
