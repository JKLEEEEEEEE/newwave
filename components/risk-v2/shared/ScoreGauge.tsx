/**
 * ScoreGauge - 원형 점수 게이지 (SVG)
 * 중앙에 점수 크게 표시, 원형 프로그레스 바
 *
 * Props:
 *   - score: 현재 점수
 *   - maxScore: 최대 점수 (기본 100)
 *   - size: SVG 크기 (px)
 *   - showBreakdown: 직접/전이 점수 분해 표시
 *   - directScore / propagatedScore: 분해 점수 값
 *   - label: 하단 라벨
 */

import React, { useMemo } from 'react';
import { RISK_COLORS } from '../design-tokens';

interface ScoreGaugeProps {
  score: number;
  maxScore?: number;
  size?: number;
  showBreakdown?: boolean;
  directScore?: number;
  propagatedScore?: number;
  label?: string;
  className?: string;
  /** API에서 내려온 riskLevel로 색상 오버라이드 (CRITICAL 이벤트 기반 판정용) */
  riskLevel?: 'PASS' | 'WARNING' | 'CRITICAL';
}

/** 점수에 따른 색상 결정 (getScoreLevel 기준: 50/30) */
function getGaugeColor(score: number, _maxScore: number, riskLevel?: string): string {
  // riskLevel 오버라이드가 있으면 점수와 무관하게 해당 색상 사용
  if (riskLevel === 'CRITICAL') return RISK_COLORS.CRITICAL.primary;
  if (riskLevel === 'WARNING') return RISK_COLORS.WARNING.primary;
  if (riskLevel === 'PASS') return RISK_COLORS.PASS.primary;
  // 오버라이드 없으면 기존 점수 기반
  if (score >= 50) return RISK_COLORS.CRITICAL.primary;
  if (score >= 30) return RISK_COLORS.WARNING.primary;
  return RISK_COLORS.PASS.primary;
}

export default function ScoreGauge({
  score,
  maxScore = 100,
  size = 120,
  showBreakdown = false,
  directScore,
  propagatedScore,
  label,
  className = '',
  riskLevel,
}: ScoreGaugeProps) {
  // SVG 계산
  const strokeWidth = size * 0.08;
  const radius = (size - strokeWidth) / 2 - 4;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.max(0, Math.min(score, maxScore));
  const progress = clampedScore / maxScore;
  const strokeDashoffset = circumference * (1 - progress);

  // 색상 (riskLevel 오버라이드 우선)
  const gaugeColor = useMemo(() => getGaugeColor(score, maxScore, riskLevel), [score, maxScore, riskLevel]);

  // 폰트 크기 계산
  const scoreFontSize = size * 0.28;
  const labelFontSize = size * 0.11;
  const breakdownFontSize = size * 0.09;

  return (
    <div className={`inline-flex flex-col items-center ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="transform -rotate-90"
      >
        {/* 배경 원 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(148, 163, 184, 0.1)"
          strokeWidth={strokeWidth}
        />

        {/* 프로그레스 원 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={gaugeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
          style={{
            filter: `drop-shadow(0 0 6px ${gaugeColor}40)`,
          }}
        />

        {/* 중앙 텍스트 그룹 (rotate 복원) */}
        <g className="transform rotate-90" style={{ transformOrigin: 'center' }}>
          {/* 점수 */}
          <text
            x={size / 2}
            y={showBreakdown ? size / 2 - 4 : size / 2 + 2}
            textAnchor="middle"
            dominantBaseline="central"
            fill={gaugeColor}
            fontSize={scoreFontSize}
            fontWeight="bold"
            fontFamily="system-ui, -apple-system, sans-serif"
          >
            {Math.round(clampedScore)}
          </text>

          {/* 분해 점수 (직접/전이) */}
          {showBreakdown && directScore !== undefined && propagatedScore !== undefined && (
            <>
              <text
                x={size / 2}
                y={size / 2 + scoreFontSize * 0.6}
                textAnchor="middle"
                dominantBaseline="central"
                fill="rgb(148, 163, 184)"
                fontSize={breakdownFontSize}
                fontFamily="system-ui, -apple-system, sans-serif"
              >
                {`D:${directScore} / P:${propagatedScore}`}
              </text>
            </>
          )}
        </g>
      </svg>

      {/* 하단 라벨 */}
      {label && (
        <span
          className="mt-1 text-slate-400"
          style={{ fontSize: labelFontSize }}
        >
          {label}
        </span>
      )}
    </div>
  );
}
