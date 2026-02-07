/**
 * 그래프 줌 컨트롤 컴포넌트
 * +/-/Reset 버튼과 줌 퍼센트 표시
 */

import React from 'react';
import { ZOOM_CONFIG } from './constants';

interface ZoomControlsProps {
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  disabled?: boolean;
}

export const ZoomControls: React.FC<ZoomControlsProps> = ({
  scale,
  onZoomIn,
  onZoomOut,
  onReset,
  disabled = false,
}) => {
  const percentage = Math.round(scale * 100);
  const canZoomIn = scale < ZOOM_CONFIG.max;
  const canZoomOut = scale > ZOOM_CONFIG.min;

  return (
    <div className="absolute bottom-4 right-4 flex flex-col gap-1 bg-slate-900/90 rounded-lg p-2 shadow-lg border border-slate-700">
      {/* 줌 인 */}
      <button
        onClick={onZoomIn}
        disabled={disabled || !canZoomIn}
        className={`w-8 h-8 flex items-center justify-center rounded transition-colors ${
          canZoomIn && !disabled
            ? 'bg-slate-700 hover:bg-slate-600 text-white'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
        }`}
        aria-label="확대"
        title="확대 (+)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v12M6 12h12" />
        </svg>
      </button>

      {/* 퍼센트 표시 */}
      <div className="text-center text-xs text-slate-400 py-1 select-none">
        {percentage}%
      </div>

      {/* 줌 아웃 */}
      <button
        onClick={onZoomOut}
        disabled={disabled || !canZoomOut}
        className={`w-8 h-8 flex items-center justify-center rounded transition-colors ${
          canZoomOut && !disabled
            ? 'bg-slate-700 hover:bg-slate-600 text-white'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
        }`}
        aria-label="축소"
        title="축소 (-)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 12h12" />
        </svg>
      </button>

      {/* 구분선 */}
      <div className="border-t border-slate-700 my-1" />

      {/* 리셋 */}
      <button
        onClick={onReset}
        disabled={disabled}
        className={`w-8 h-8 flex items-center justify-center rounded text-xs transition-colors ${
          !disabled
            ? 'bg-slate-700 hover:bg-slate-600 text-white'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
        }`}
        aria-label="초기화"
        title="초기화 (0)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>

      {/* 키보드 단축키 안내 */}
      <div className="text-center text-[10px] text-slate-500 pt-1 border-t border-slate-700 mt-1">
        <div>+/- 줌</div>
        <div>화살표 이동</div>
        <div>0 리셋</div>
      </div>
    </div>
  );
};

export default ZoomControls;
