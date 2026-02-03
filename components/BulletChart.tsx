
import React from 'react';
import { HurdleStatus } from '../types';

interface Props {
  current: number;
  limit: number;
  status: HurdleStatus;
}

const BulletChart: React.FC<Props> = ({ current, limit, status }) => {
  const maxScale = limit * 1.5;
  const currentPos = Math.min((current / maxScale) * 100, 100);
  const limitPos = (limit / maxScale) * 100;

  const barColor = status === HurdleStatus.PASS ? 'bg-emerald-500' : 
                   status === HurdleStatus.WARNING ? 'bg-amber-500' : 'bg-rose-500';

  return (
    <div className="w-full h-10 flex items-center relative group">
      <div className="absolute inset-x-0 h-2 bg-slate-200/50 rounded-full"></div>
      
      <div 
        className={`absolute h-2 rounded-full z-10 transition-all duration-1000 ease-out shadow-sm ${barColor}`}
        style={{ width: `${currentPos}%` }}
      ></div>

      <div 
        className="absolute h-6 w-1 bg-slate-400 z-20 transition-all group-hover:bg-slate-900 shadow-sm"
        style={{ left: `${limitPos}%` }}
      >
        <div className="absolute top-7 left-1/2 -translate-x-1/2 text-[8px] font-black text-slate-400 whitespace-nowrap tracking-tighter group-hover:text-slate-900 transition-colors uppercase">
          승인 한도 ({limit}x)
        </div>
      </div>

      <div 
        className="absolute -top-2 flex flex-col items-center z-30 transition-transform hover:scale-110"
        style={{ left: `${currentPos}%`, transform: 'translateX(-50%)' }}
      >
        <div className="px-1.5 py-0.5 bg-slate-900 text-white text-[9px] font-black rounded-sm mb-1 shadow-md">
          {current}x
        </div>
        <div className="w-1.5 h-1.5 bg-white border-2 border-slate-900 rounded-full"></div>
      </div>
    </div>
  );
};

export default BulletChart;
