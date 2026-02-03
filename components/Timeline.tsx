
import React from 'react';
import { TimelineEvent } from '../types';

interface Props {
  events: TimelineEvent[];
}

const Timeline: React.FC<Props> = ({ events }) => {
  return (
    <div className="h-20 bg-slate-900 border-t border-slate-700 flex items-center px-12 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-blue-900/10 via-transparent to-transparent pointer-events-none"></div>
      
      <div className="flex-shrink-0 mr-12">
        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Collaboration</p>
        <p className="text-xs font-bold text-white">Timeline</p>
      </div>

      <div className="flex flex-1 items-center justify-between relative px-10">
        {/* Connection Line */}
        <div className="absolute left-10 right-10 h-0.5 bg-slate-700 top-1/2 -translate-y-1/2"></div>
        
        {events.map((event, idx) => (
          <div key={event.id} className="relative z-10 flex flex-col items-center">
            <div className={`text-[10px] font-bold mb-2 ${event.active ? 'text-blue-400' : 'text-slate-500'}`}>
              {event.date}
            </div>
            <div className={`w-3 h-3 rounded-full border-2 transition-all duration-500 ${event.active ? 'bg-blue-500 border-white shadow-[0_0_15px_rgba(59,130,246,0.8)] scale-125' : 'bg-slate-900 border-slate-600 hover:border-slate-400'}`}></div>
            <div className={`text-[11px] font-bold mt-2 whitespace-nowrap ${event.active ? 'text-white' : 'text-slate-500'}`}>
              {event.label}
              {event.type === 'news' && event.active && <span className="ml-1 text-[8px] animate-pulse">● LIVE</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="flex-shrink-0 ml-12 pl-12 border-l border-slate-700">
        <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-[11px] font-bold text-slate-300 transition-colors border border-slate-600">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          상세 이력 보기
        </button>
      </div>
    </div>
  );
};

export default Timeline;
