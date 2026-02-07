/**
 * ErrorState - API 에러/실패 상태 UI
 * variant: inline (카드 내), card (독립 카드), fullpage (전체 화면)
 */

import React from 'react';
import GlassCard from './GlassCard';

interface ErrorStateProps {
  message?: string;
  detail?: string;
  variant?: 'inline' | 'card' | 'fullpage';
  onRetry?: () => void;
  className?: string;
}

export default function ErrorState({
  message = 'API 연결에 실패했습니다',
  detail,
  variant = 'card',
  onRetry,
  className = '',
}: ErrorStateProps) {
  const content = (
    <div className={`flex flex-col items-center gap-3 text-center ${variant === 'fullpage' ? 'py-16' : 'py-6'}`}>
      <span className="text-2xl opacity-60">&#9888;</span>
      <p className="text-slate-300 text-sm font-medium">{message}</p>
      {detail && <p className="text-slate-500 text-xs">{detail}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-4 py-1.5 rounded-lg text-xs font-medium bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 transition-colors border border-purple-500/20"
        >
          다시 시도
        </button>
      )}
    </div>
  );

  if (variant === 'inline') {
    return <div className={className}>{content}</div>;
  }

  return (
    <GlassCard className={`${className}`}>
      {content}
    </GlassCard>
  );
}
