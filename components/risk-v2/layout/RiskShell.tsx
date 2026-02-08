/**
 * RiskShell - V2 메인 레이아웃 쉘
 *
 * 구조:
 *   <RiskV2Provider>
 *     <NavigationBar />
 *     <div.content-area> (relative 컨테이너)
 *       <main> (뷰 전환 with AnimatePresence)
 *       <aside> (AICopilotPanel 슬라이딩 패널)
 *     </div>
 *     <footer> (Powered by 상태바)
 *   </RiskV2Provider>
 *
 * aside는 content-area 내 absolute 위치 → 상위 앱 Header/ApiStatusBar와 무관하게 정확히 배치
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RiskV2Provider, useRiskV2 } from '../context/RiskV2Context';
import NavigationBar from './NavigationBar';
import { LAYOUT, GRADIENTS } from '../design-tokens';
import type { ViewType } from '../types-v2';
import CommandCenter from '../screens/CommandCenter';
import SupplyChainXRay from '../screens/SupplyChainXRay';
import RiskDeepDive from '../screens/RiskDeepDive';
import WhatIf from '../screens/WhatIf';
import AICopilotPanel from '../screens/AICopilotPanel';

// ============================================
// 뷰 렌더러 매핑
// ============================================
const VIEW_COMPONENTS: Record<ViewType, React.ComponentType> = {
  command: CommandCenter,
  xray: SupplyChainXRay,
  deepdive: RiskDeepDive,
  whatif: WhatIf,
};

// ============================================
// 내부 레이아웃 (Provider 안에서 사용)
// ============================================
function RiskShellInner() {
  const { state } = useRiskV2();
  const { activeView, copilotOpen } = state;

  const ActiveViewComponent = VIEW_COMPONENTS[activeView];

  return (
    <div className="h-full flex flex-col bg-[#0a0f1e] text-slate-100 overflow-hidden">
      {/* 상단 네비게이션 */}
      <NavigationBar />

      {/* 컨텐츠 영역 (main + aside의 공통 relative 컨테이너) */}
      <div className="flex-1 overflow-hidden relative">
        {/* 메인 컨텐츠 */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeView}
            className="absolute inset-0"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <div className="h-full overflow-auto">
              <ActiveViewComponent />
            </div>
          </motion.div>
        </AnimatePresence>

        {/* AI Copilot 슬라이딩 패널 - absolute로 content area 내부 배치 */}
        <aside
          className={`
            absolute top-0 right-0 bottom-0 z-40
            bg-slate-900/95 backdrop-blur-xl border-l border-white/5
            transition-transform duration-300 ease-out
            ${copilotOpen ? 'translate-x-0' : 'translate-x-full'}
          `}
          style={{ width: LAYOUT.sidePanelWidth }}
        >
          <AICopilotPanel />
        </aside>
      </div>

      {/* 하단 상태바 */}
      <footer
        className="relative z-50 flex items-center justify-between px-6 border-t border-white/5 text-xs text-slate-500"
        style={{
          height: LAYOUT.footerHeight,
          backgroundColor: 'rgba(10, 15, 30, 0.8)',
        }}
      >
        <div className="flex items-center gap-3" />
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            System Online
          </span>
          <span>V2.0-alpha</span>
        </div>
      </footer>
    </div>
  );
}

// ============================================
// 메인 RiskShell (Provider 포함)
// ============================================
interface RiskShellProps {
  /** 초기 딜 ID */
  initialDealId?: string;
  /** 초기 뷰 */
  initialView?: ViewType;
}

export default function RiskShell({
  initialDealId,
  initialView,
}: RiskShellProps) {
  return (
    <RiskV2Provider initialDealId={initialDealId} initialView={initialView}>
      <RiskShellInner />
    </RiskV2Provider>
  );
}
