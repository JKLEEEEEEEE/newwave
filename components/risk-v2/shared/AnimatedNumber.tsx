/**
 * AnimatedNumber - 숫자 카운트업 애니메이션
 * 0에서 목표 값까지 부드럽게 증가하는 애니메이션 효과
 *
 * Props:
 *   - value: 목표 숫자
 *   - duration: 애니메이션 시간 (ms, 기본 800)
 *   - prefix: 접두사 (예: "$", "+")
 *   - suffix: 접미사 (예: "점", "%")
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ANIMATION } from '../design-tokens';

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  /** 소수점 자리수 (기본 0) */
  decimals?: number;
}

/** easeOutQuart 이징 함수 */
function easeOutQuart(t: number): number {
  return 1 - Math.pow(1 - t, 4);
}

export default function AnimatedNumber({
  value,
  duration = ANIMATION.countUpDuration,
  prefix = '',
  suffix = '',
  className = '',
  decimals = 0,
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const animationRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const previousValueRef = useRef<number>(0);

  const animate = useCallback((timestamp: number) => {
    if (!startTimeRef.current) {
      startTimeRef.current = timestamp;
    }

    const elapsed = timestamp - startTimeRef.current;
    const progress = Math.min(elapsed / duration, 1);
    const easedProgress = easeOutQuart(progress);

    const from = previousValueRef.current;
    const current = from + (value - from) * easedProgress;
    setDisplayValue(current);

    if (progress < 1) {
      animationRef.current = requestAnimationFrame(animate);
    } else {
      setDisplayValue(value);
    }
  }, [value, duration]);

  useEffect(() => {
    // 이전 애니메이션 취소
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    // 새 애니메이션 시작
    startTimeRef.current = 0;
    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      // 현재 표시값을 이전값으로 저장
      previousValueRef.current = value;
    };
  }, [value, animate]);

  // 포맷팅
  const formattedValue = decimals > 0
    ? displayValue.toFixed(decimals)
    : Math.round(displayValue).toString();

  return (
    <span className={`tabular-nums ${className}`}>
      {prefix}{formattedValue}{suffix}
    </span>
  );
}
