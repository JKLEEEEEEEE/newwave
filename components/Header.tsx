
import React from 'react';

interface Props {
  onViewChange: (view: 'analysis' | 'monitoring' | 'global') => void;
  currentView: 'analysis' | 'monitoring' | 'global';
  crisisAlert?: boolean;
}

const Header: React.FC<Props> = ({ onViewChange, currentView }) => {
  return (
    <header className="h-16 flex items-center justify-between px-8 bg-[#003366] border-b border-white/10 z-50">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-3 group cursor-pointer" onClick={() => onViewChange('global')}>
          <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center font-black text-xl text-[#003366] shadow-md group-hover:bg-slate-100 transition-colors">JB</div>
          <div className="flex flex-col">
            <h1 className="font-bold text-lg tracking-tight text-white leading-none">JB DealValidator Pro</h1>
            <span className="text-[9px] font-bold text-blue-200 uppercase tracking-widest mt-1">기업금융 AI 통합 심사 시스템</span>
          </div>
        </div>
        
        <div className="h-8 w-px bg-white/10 mx-2"></div>
        
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-bold text-blue-200/60 uppercase tracking-widest">분석 엔진 상태:</span>
          <div className="flex items-center gap-2 bg-white/5 px-3 py-1 rounded-md border border-white/10">
             <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)] animate-pulse"></div>
             <span className="text-[10px] font-bold text-slate-100 uppercase">최적화 가동중</span>
          </div>
        </div>
      </div>

      <nav className="flex items-center h-full text-[11px] font-bold uppercase tracking-widest">
        <NavItem 
          active={currentView === 'global'} 
          onClick={() => onViewChange('global')} 
          label="포트폴리오 대시보드" 
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M4 6h16M4 12h16m-7 6h7" strokeWidth={2.5}/></svg>}
        />
        <NavItem 
          active={currentView === 'analysis'} 
          onClick={() => onViewChange('analysis')} 
          label="상세 심사 보고서" 
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeWidth={2.5}/></svg>}
        />
        <NavItem 
          active={currentView === 'monitoring'} 
          onClick={() => onViewChange('monitoring')} 
          label="실시간 리스크 관제" 
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" strokeWidth={2.5}/></svg>}
        />
      </nav>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-4 pr-6 border-r border-white/10">
           <button className="relative p-2 text-blue-200 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" strokeWidth={2}/></svg>
           </button>
        </div>
        
        <div className="flex items-center gap-3 bg-white/5 pl-4 py-1 pr-1 rounded-lg border border-white/10">
          <div className="flex flex-col items-end">
            <span className="text-[10px] font-bold text-white leading-none">최환석 대리</span>
            <span className="text-[8px] font-bold text-blue-200/50 uppercase tracking-tighter mt-1">AX추진팀</span>
          </div>
          <div className="w-8 h-8 rounded bg-white text-[#003366] flex items-center justify-center text-xs font-black">HS</div>
        </div>
      </div>
    </header>
  );
};

const NavItem: React.FC<{ active: boolean; onClick: () => void; label: string; icon: React.ReactNode }> = ({ active, onClick, label, icon }) => (
  <button 
    onClick={onClick}
    className={`px-8 h-full border-b-[3px] transition-all flex items-center gap-2.5 ${active ? 'text-white border-white bg-white/5' : 'text-blue-200/60 hover:text-white border-transparent'}`}
  >
    {icon}
    {label}
  </button>
);

export default Header;
