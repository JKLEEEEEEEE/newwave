
import React from 'react';
import { HurdleStatus } from '../types';

interface Props {
  status: HurdleStatus;
}

const StatusBadge: React.FC<Props> = ({ status }) => {
  const configs = {
    [HurdleStatus.PASS]: {
      label: '투자 적정 (STABLE)',
      bg: 'bg-emerald-50 text-emerald-800 border-emerald-100',
      dot: 'bg-emerald-500'
    },
    [HurdleStatus.WARNING]: {
      label: '주의 관찰 (CAUTION)',
      bg: 'bg-amber-50 text-amber-800 border-amber-100',
      dot: 'bg-amber-500'
    },
    [HurdleStatus.FAIL]: {
      label: '부적격 판정 (CRITICAL)',
      bg: 'bg-rose-50 text-rose-800 border-rose-100',
      dot: 'bg-rose-500'
    }
  };

  const config = configs[status];

  return (
    <span className={`px-4 py-1.5 rounded border text-[10px] font-black flex items-center gap-2.5 shadow-sm uppercase tracking-tighter ${config.bg}`}>
      <span className={`w-2 h-2 rounded-full ${config.dot}`}></span>
      {config.label}
    </span>
  );
};

export default StatusBadge;
