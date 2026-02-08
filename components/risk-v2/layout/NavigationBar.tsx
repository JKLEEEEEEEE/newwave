/**
 * NavigationBar - Glassmorphism 스타일 상단 네비게이션
 *
 * 구성:
 *   - 좌측: 로고 + "Supply Chain Risk Intelligence" 타이틀
 *   - 중앙: 4개 뷰 버튼 (Command Center, X-Ray, Deep Dive, What-If)
 *   - 우측: CRITICAL 알림 버튼 + AI Copilot 토글
 *
 * 선택된 뷰는 gradient underline으로 하이라이트
 */

import React, { useState, useRef, useEffect } from 'react';
import { NAV_ITEMS, GLASS, GRADIENTS, LAYOUT } from '../design-tokens';
import { useRiskV2 } from '../context/RiskV2Context';
import { formatRelativeTime } from '../utils-v2';
import type { ViewType } from '../types-v2';

export default function NavigationBar() {
  const { state, setActiveView, toggleCopilot, acknowledgeCriticalAlerts } = useRiskV2();
  const { activeView, copilotOpen, criticalAlerts, criticalAcknowledged } = state;

  // CRITICAL 알림 드롭다운 상태
  const [alertDropdownOpen, setAlertDropdownOpen] = useState(false);
  const alertDropdownRef = useRef<HTMLDivElement>(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    if (!alertDropdownOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (alertDropdownRef.current && !alertDropdownRef.current.contains(e.target as Node)) {
        setAlertDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [alertDropdownOpen]);

  return (
    <nav
      className="relative z-50 flex items-center justify-between px-6 border-b border-white/5"
      style={{
        height: LAYOUT.navHeight,
        backgroundColor: GLASS.bg,
        backdropFilter: `blur(${GLASS.blur})`,
      }}
    >
      {/* === 좌측: 로고 + 타이틀 === */}
      <div className="flex items-center gap-3 min-w-[260px]">
        {/* 로고 아이콘 */}
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
          style={{ background: GRADIENTS.primary }}
        >
          R
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-white leading-tight">
            Supply Chain Risk
          </span>
          <span className="text-[10px] text-slate-400 leading-tight">
            Intelligence Platform V2
          </span>
        </div>
      </div>

      {/* === 중앙: 네비게이션 버튼 === */}
      <div className="flex items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = activeView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id as ViewType)}
              className={`
                relative px-4 py-2 rounded-lg text-sm font-medium
                transition-all duration-200 ease-out
                ${isActive
                  ? 'text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }
              `}
            >
              {/* 아이콘 + 라벨 */}
              <span className="flex items-center gap-2">
                <span className="text-base">{item.icon}</span>
                <span className="hidden lg:inline">{item.label}</span>
              </span>

              {/* 활성 상태: gradient underline */}
              {isActive && (
                <div
                  className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full"
                  style={{ background: GRADIENTS.primary }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* === 우측: CRITICAL 알림 + Copilot === */}
      <div className="flex items-center gap-3 min-w-[260px] justify-end">
        {/* CRITICAL 알림 버튼 — alerts > 0이면 항상 표시 */}
        {criticalAlerts.length > 0 && (
          <div className="relative" ref={alertDropdownRef}>
            <button
              onClick={() => setAlertDropdownOpen(prev => !prev)}
              className={`relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium
                         border border-red-500/30 bg-red-500/10 hover:bg-red-500/20
                         transition-all duration-200 ease-out
                         ${!criticalAcknowledged ? 'animate-bounce' : ''}`}
              title="CRITICAL Alerts"
            >
              {/* 경고 아이콘 */}
              <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span className="text-red-400 font-bold text-xs">{criticalAlerts.length}</span>
              {/* ping 뱃지 — 미확인 시에만 */}
              {!criticalAcknowledged && (
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                </span>
              )}
            </button>

            {/* 드롭다운 패널 */}
            {alertDropdownOpen && (
              <div className="absolute top-full right-0 mt-2 w-[360px] bg-slate-900/95 backdrop-blur-xl
                              border border-red-500/30 rounded-xl shadow-2xl shadow-red-500/10 z-50">
                {/* 헤더 */}
                <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
                  <span className="text-sm font-bold text-red-400">CRITICAL ALERTS ({criticalAlerts.length})</span>
                  <button
                    onClick={() => setAlertDropdownOpen(false)}
                    className="text-slate-400 hover:text-white transition-colors text-sm"
                  >
                    &#10005;
                  </button>
                </div>

                {/* 이벤트 리스트 */}
                <div className="max-h-[300px] overflow-y-auto p-2 space-y-1.5"
                     style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(148,163,184,0.2) transparent' }}>
                  {criticalAlerts.map(event => (
                    <div key={event.id} className="p-2.5 rounded-lg bg-red-500/5 border border-red-500/10">
                      <p className="text-sm text-white font-medium">{event.title}</p>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400">
                        <span>Score: {event.score}</span>
                        {event.companyName && <span className="text-slate-300">{event.companyName}</span>}
                        {event.categoryName && <span>{event.categoryName}</span>}
                        <span>{formatRelativeTime(event.publishedAt)}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 하단: 확인 버튼 (애니메이션 멈춤, 알림은 유지) */}
                {!criticalAcknowledged && (
                  <div className="px-4 py-3 border-t border-white/5">
                    <button
                      onClick={() => { acknowledgeCriticalAlerts(); }}
                      className="w-full py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors"
                    >
                      확인 ({criticalAlerts.length}건)
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* AI Copilot 토글 */}
        <button
          onClick={toggleCopilot}
          className={`
            flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium
            transition-all duration-200 ease-out border
            ${copilotOpen
              ? 'text-white border-purple-500/50 bg-purple-500/10'
              : 'text-slate-400 border-white/5 hover:text-white hover:bg-white/5'
            }
          `}
          title="AI Copilot 토글"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"
            />
          </svg>
          <span className="hidden sm:inline">AI Copilot</span>
        </button>
      </div>
    </nav>
  );
}
