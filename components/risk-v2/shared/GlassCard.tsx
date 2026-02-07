/**
 * GlassCard - Glassmorphism 카드 컨테이너
 * backdrop-blur + 반투명 배경 + 미세 테두리
 *
 * Props:
 *   - gradient: 상단에 2px gradient stripe 추가
 *   - hover: 호버 시 scale + 테두리 전환 효과
 *   - onClick: 클릭 가능한 카드
 */

import React from 'react';
import { GLASS, GRADIENTS } from '../design-tokens';

type GradientType = 'primary' | 'danger' | 'success' | 'warning' | 'purple' | 'none';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  /** 상단 gradient stripe 타입 */
  gradient?: GradientType;
  /** 호버 애니메이션 활성화 */
  hover?: boolean;
  /** 클릭 핸들러 */
  onClick?: () => void;
  /** 더블클릭 핸들러 */
  onDoubleClick?: () => void;
  /** 추가 스타일 */
  style?: React.CSSProperties;
}

export default function GlassCard({
  children,
  className = '',
  gradient = 'none',
  hover = false,
  onClick,
  onDoubleClick,
  style,
}: GlassCardProps) {
  // Gradient stripe 매핑
  const gradientValue = gradient !== 'none' ? GRADIENTS[gradient] : undefined;

  // 기본 클래스: Glassmorphism 스타일
  const baseClasses = [
    'relative',
    'backdrop-blur-xl',
    'bg-slate-900/40',
    'border',
    'border-white/5',
    'rounded-2xl',
    'overflow-hidden',
  ];

  // 호버 효과 클래스
  if (hover) {
    baseClasses.push(
      'transition-all',
      'duration-300',
      'ease-out',
      'hover:scale-[1.02]',
      'hover:border-white/10',
      'hover:shadow-lg',
      'hover:shadow-black/20'
    );
  }

  // 클릭 가능한 경우 커서 변경
  if (onClick) {
    baseClasses.push('cursor-pointer');
  }

  return (
    <div
      className={`${baseClasses.join(' ')} ${className}`}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      style={{
        backdropFilter: `blur(${GLASS.blur})`,
        ...style,
      }}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); } : undefined}
    >
      {/* Gradient stripe (상단 2px) */}
      {gradientValue && (
        <div
          className="absolute top-0 left-0 right-0 h-[2px]"
          style={{ background: gradientValue }}
        />
      )}

      {children}
    </div>
  );
}
