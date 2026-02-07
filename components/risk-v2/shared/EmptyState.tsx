/**
 * EmptyState - 데이터 없음 상태 UI + 다음 액션 가이드
 */

import React from 'react';
import GlassCard from './GlassCard';

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  variant?: 'inline' | 'card';
  className?: string;
}

export default function EmptyState({
  icon = '&#128269;',
  title,
  description,
  actionLabel,
  onAction,
  variant = 'card',
  className = '',
}: EmptyStateProps) {
  const content = (
    <div className="flex flex-col items-center gap-2 text-center py-6">
      <span className="text-3xl opacity-30" dangerouslySetInnerHTML={{ __html: icon }} />
      <p className="text-slate-400 text-sm font-medium">{title}</p>
      {description && <p className="text-slate-600 text-xs">{description}</p>}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-2 px-4 py-1.5 rounded-lg text-xs font-medium bg-white/5 text-slate-300 hover:bg-white/10 transition-colors border border-white/10"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );

  if (variant === 'inline') {
    return <div className={className}>{content}</div>;
  }

  return (
    <GlassCard className={className}>
      {content}
    </GlassCard>
  );
}
