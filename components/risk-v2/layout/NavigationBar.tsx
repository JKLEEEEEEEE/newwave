/**
 * NavigationBar - Glassmorphism 스타일 상단 네비게이션
 *
 * 구성:
 *   - 좌측: 로고 + "Supply Chain Risk Intelligence" 타이틀
 *   - 중앙: 4개 뷰 버튼 (Command Center, X-Ray, Deep Dive, War Room)
 *   - 우측: AI Copilot 토글 + 알림 아이콘
 *
 * 선택된 뷰는 gradient underline으로 하이라이트
 */

import React from 'react';
import { NAV_ITEMS, GLASS, GRADIENTS, LAYOUT } from '../design-tokens';
import { useRiskV2 } from '../context/RiskV2Context';
import type { ViewType } from '../types-v2';

export default function NavigationBar() {
  const { state, setActiveView, toggleCopilot } = useRiskV2();
  const { activeView, copilotOpen } = state;

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

      {/* === 우측: Copilot + 알림 === */}
      <div className="flex items-center gap-3 min-w-[260px] justify-end">
        {/* 알림 아이콘 */}
        <button
          className="relative p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          title="알림"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
            />
          </svg>
          {/* 알림 뱃지 (미래 구현) */}
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>

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
