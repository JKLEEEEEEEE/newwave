/**
 * Risk V2 - 디자인 토큰
 * Glassmorphism + Dark Theme + Gradient 디자인 시스템
 * 모든 V2 컴포넌트가 참조하는 디자인 상수
 */

// ============================================
// Glassmorphism 기본값
// ============================================
export const GLASS = {
  /** 기본 배경 (반투명 다크) */
  bg: 'rgba(15, 23, 42, 0.6)',
  /** 호버 시 배경 */
  bgHover: 'rgba(15, 23, 42, 0.8)',
  /** 기본 테두리 */
  border: 'rgba(148, 163, 184, 0.1)',
  /** 호버 시 테두리 */
  borderHover: 'rgba(148, 163, 184, 0.2)',
  /** 블러 강도 */
  blur: '20px',
  /** 모서리 반경 */
  radius: '16px',
} as const;

// ============================================
// 그래디언트 색상
// ============================================
export const GRADIENTS = {
  /** 메인 퍼플-바이올렛 */
  primary: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  /** 위험 레드 */
  danger: 'linear-gradient(135deg, #f5576c 0%, #ff6b6b 100%)',
  /** 안전 블루-시안 */
  success: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  /** 경고 옐로-오렌지 */
  warning: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
  /** 보라-인디고 */
  purple: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
  /** 다크 백그라운드 */
  dark: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
} as const;

// ============================================
// 리스크 레벨 색상 (PASS / WARNING / CRITICAL)
// ============================================
export const RISK_COLORS = {
  PASS: {
    primary: '#10b981',
    light: '#34d399',
    bg: 'rgba(16, 185, 129, 0.1)',
    border: 'rgba(16, 185, 129, 0.3)',
  },
  WARNING: {
    primary: '#f59e0b',
    light: '#fbbf24',
    bg: 'rgba(245, 158, 11, 0.1)',
    border: 'rgba(245, 158, 11, 0.3)',
  },
  CRITICAL: {
    primary: '#ef4444',
    light: '#f87171',
    bg: 'rgba(239, 68, 68, 0.1)',
    border: 'rgba(239, 68, 68, 0.3)',
  },
} as const;

// ============================================
// 10개 카테고리 색상 매핑
// ============================================
export const CATEGORY_COLORS: Record<string, { color: string; bg: string }> = {
  /** 주주 */
  SHARE:  { color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)' },
  /** 임원 */
  EXEC:   { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
  /** 신용 */
  CREDIT: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
  /** 법률 */
  LEGAL:  { color: '#6366f1', bg: 'rgba(99, 102, 241, 0.15)' },
  /** 지배구조 */
  GOV:    { color: '#14b8a6', bg: 'rgba(20, 184, 166, 0.15)' },
  /** 운영 */
  OPS:    { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.15)' },
  /** 감사 */
  AUDIT:  { color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' },
  /** ESG */
  ESG:    { color: '#22c55e', bg: 'rgba(34, 197, 94, 0.15)' },
  /** 공급망 */
  SUPPLY: { color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)' },
  /** 기타 */
  OTHER:  { color: '#6b7280', bg: 'rgba(107, 114, 128, 0.15)' },
};

// ============================================
// Severity 색상 (이벤트 심각도)
// ============================================
export const SEVERITY_COLORS: Record<string, { color: string; bg: string }> = {
  CRITICAL: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
  HIGH:     { color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)' },
  WARNING:  { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
  MEDIUM:   { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
  LOW:      { color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' },
};

// ============================================
// 네비게이션 아이템 정의
// ============================================
export const NAV_ITEMS = [
  { id: 'command',  label: 'Command Center',     icon: '\uD83C\uDFAF' },
  { id: 'xray',     label: 'Supply Chain X-Ray', icon: '\uD83D\uDD2C' },
  { id: 'deepdive', label: 'Risk Deep Dive',     icon: '\uD83D\uDD0D' },
  { id: 'whatif',    label: 'What-If',             icon: '\u2694\uFE0F' },
] as const;

// ============================================
// 애니메이션 설정
// ============================================
export const ANIMATION = {
  /** 페이지 전환 속도 (초) */
  pageTransition: 0.3,
  /** 요소 등장 속도 (초) */
  stagger: 0.05,
  /** 카운트업 애니메이션 기본 시간 (ms) */
  countUpDuration: 800,
  /** 스프링 설정 */
  spring: { stiffness: 300, damping: 30 },
} as const;

// ============================================
// 레이아웃 상수
// ============================================
export const LAYOUT = {
  /** 네비게이션 바 높이 */
  navHeight: '64px',
  /** 사이드 패널 너비 */
  sidePanelWidth: '400px',
  /** 최대 컨텐츠 너비 */
  maxContentWidth: '1920px',
  /** 풋터 높이 */
  footerHeight: '32px',
} as const;
