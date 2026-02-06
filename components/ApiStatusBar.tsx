
import React from 'react';

const ApiStatusBar: React.FC = () => {
  const apis = [

    { name: 'HR AUDIT', status: 'maintenance' },
  ];

  return (
    <div className="h-10 bg-white border-b border-slate-200 flex items-center px-8 gap-10 overflow-x-auto no-scrollbar shadow-sm">
      <div className="flex items-center gap-3 pr-8 border-r border-slate-200">
        <span className="text-[10px] font-black text-[#003366] uppercase tracking-[0.2em]">Data Pipeline</span>
        <div className="w-2 h-2 rounded-full bg-[#003366] animate-pulse"></div>
      </div>

      {apis.map((api) => (
        <div key={api.name} className="flex items-center gap-3 whitespace-nowrap group">
          <div className={`w-1.5 h-1.5 rounded-full transition-shadow duration-500 ${api.status === 'online' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]'}`}></div>
          <span className="text-[10px] font-black text-slate-400 group-hover:text-[#003366] transition-colors uppercase tracking-tight">{api.name}</span>
        </div>
      ))}

      <div className="ml-auto flex items-center gap-6">
        <div className="h-4 w-px bg-slate-200"></div>
        <div className="flex items-center gap-3">
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Update: 5.0s</span>
          <button className="p-1.5 bg-slate-50 hover:bg-slate-100 rounded border border-slate-200 transition-all group active:scale-95">
            <svg className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#003366]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApiStatusBar;
