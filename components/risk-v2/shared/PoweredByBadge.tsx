/**
 * PoweredByBadge - 기술 스택 뱃지
 * "Neo4j Powered" / "GPT-5.2 Powered" / "Both" 표시
 *
 * Props:
 *   - type: 뱃지 타입 ('neo4j' | 'gpt4' | 'both')
 */

import React from 'react';
import { GRADIENTS } from '../design-tokens';

interface PoweredByBadgeProps {
  type: 'neo4j' | 'gpt4' | 'both';
  className?: string;
}

/** 타입별 설정 */
const BADGE_CONFIG = {
  neo4j: {
    label: 'Neo4j Powered',
    icon: '\uD83D\uDD35',  // 파란 원
    gradient: GRADIENTS.success,
    color: '#00f2fe',
  },
  gpt4: {
    label: 'GPT-5.2 Powered',
    icon: '\u2728',  // 반짝
    gradient: GRADIENTS.purple,
    color: '#a855f7',
  },
};

export default function PoweredByBadge({
  type,
  className = '',
}: PoweredByBadgeProps) {
  if (type === 'both') {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`}>
        <SingleBadge config={BADGE_CONFIG.neo4j} />
        <span className="text-slate-600">|</span>
        <SingleBadge config={BADGE_CONFIG.gpt4} />
      </div>
    );
  }

  return <SingleBadge config={BADGE_CONFIG[type]} className={className} />;
}

/** 개별 뱃지 렌더링 */
function SingleBadge({
  config,
  className = '',
}: {
  config: { label: string; icon: string; gradient: string; color: string };
  className?: string;
}) {
  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1
        text-xs font-medium rounded-full
        border border-white/5
        ${className}
      `}
      style={{
        background: `${config.gradient.replace('linear-gradient', 'linear-gradient').replace('100%', '100%')}`,
        opacity: 0.85,
        color: 'white',
        textShadow: '0 1px 2px rgba(0,0,0,0.3)',
      }}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
