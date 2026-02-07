/**
 * RiskV2Context - 글로벌 상태 관리
 * useReducer 기반으로 딜 선택, 드릴다운, 뷰 전환, Copilot 상태 관리
 *
 * DRILL_DOWN 액션은 하위 선택을 자동 초기화:
 *   - DRILL_DOWN_TO_DEAL: company/category/entity → null
 *   - DRILL_DOWN_TO_COMPANY: category/entity → null
 *   - DRILL_DOWN_TO_CATEGORY: entity → null
 *   - NAVIGATE_BACK_TO: 지정 수준 이하 초기화
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect, useMemo } from 'react';
import type {
  RiskV2State,
  RiskV2Action,
  ViewType,
  CategoryCodeV2,
  CopilotContextData,
  DealV2,
  DealDetailResponseV2,
  CompanyV2,
  RiskCategoryV2,
  RiskEventV2,
} from '../types-v2';
import { riskApiV2 } from '../api-v2';

// ============================================
// 초기 상태
// ============================================
const initialState: RiskV2State = {
  selectedDealId: null,
  selectedCompanyId: null,
  selectedCategoryCode: null,
  selectedEntityId: null,
  activeView: 'command',
  copilotOpen: false,
  copilotContext: null,
  deals: [],
  dealsLoading: false,
  dealDetail: null,
  dealDetailLoading: false,
  recentEvents: [],
};

// ============================================
// 리듀서
// ============================================
function riskV2Reducer(state: RiskV2State, action: RiskV2Action): RiskV2State {
  switch (action.type) {
    case 'SET_DEALS':
      return { ...state, deals: action.payload, dealsLoading: false };

    case 'SET_DEALS_LOADING':
      return { ...state, dealsLoading: action.payload };

    case 'SET_SELECTED_DEAL':
      return { ...state, selectedDealId: action.payload };

    case 'SET_SELECTED_COMPANY':
      return { ...state, selectedCompanyId: action.payload };

    case 'SET_SELECTED_CATEGORY':
      return { ...state, selectedCategoryCode: action.payload };

    case 'SET_SELECTED_ENTITY':
      return { ...state, selectedEntityId: action.payload };

    case 'SET_ACTIVE_VIEW':
      return { ...state, activeView: action.payload };

    case 'TOGGLE_COPILOT':
      return { ...state, copilotOpen: !state.copilotOpen };

    case 'SET_COPILOT_CONTEXT':
      return { ...state, copilotContext: action.payload };

    // === 드릴다운 액션 ===
    case 'DRILL_DOWN_TO_DEAL':
      return {
        ...state,
        selectedDealId: action.payload,
        selectedCompanyId: null,
        selectedCategoryCode: null,
        selectedEntityId: null,
      };

    case 'DRILL_DOWN_TO_COMPANY':
      return {
        ...state,
        selectedCompanyId: action.payload,
        selectedCategoryCode: null,
        selectedEntityId: null,
      };

    case 'DRILL_DOWN_TO_CATEGORY':
      return {
        ...state,
        selectedCategoryCode: action.payload,
        selectedEntityId: null,
      };

    case 'DRILL_DOWN_TO_ENTITY':
      return {
        ...state,
        selectedEntityId: action.payload,
      };

    // === 네비게이션 백 ===
    case 'NAVIGATE_BACK_TO':
      switch (action.payload) {
        case 'deals':
          return {
            ...state,
            selectedDealId: null,
            selectedCompanyId: null,
            selectedCategoryCode: null,
            selectedEntityId: null,
          };
        case 'company':
          return {
            ...state,
            selectedCategoryCode: null,
            selectedEntityId: null,
          };
        case 'category':
          return {
            ...state,
            selectedEntityId: null,
          };
        default:
          return state;
      }

    // === 딜 상세 데이터 ===
    case 'SET_DEAL_DETAIL':
      return { ...state, dealDetail: action.payload, dealDetailLoading: false };

    case 'SET_DEAL_DETAIL_LOADING':
      return { ...state, dealDetailLoading: action.payload };

    case 'SET_RECENT_EVENTS':
      return { ...state, recentEvents: action.payload };

    default:
      return state;
  }
}

// ============================================
// Context 타입
// ============================================
interface RiskV2ContextType {
  state: RiskV2State;
  dispatch: React.Dispatch<RiskV2Action>;

  // 편의 액션 함수
  selectDeal: (dealId: string) => void;
  selectCompany: (companyId: string) => void;
  selectCategory: (code: CategoryCodeV2) => void;
  selectEntity: (entityId: string) => void;
  setActiveView: (view: ViewType) => void;
  toggleCopilot: () => void;
  setCopilotContext: (ctx: CopilotContextData | null) => void;
  navigateBack: (to: 'deals' | 'company' | 'category') => void;
  loadDeals: () => Promise<void>;
  loadDealDetail: (dealId: string) => Promise<void>;

  // 계산된 프로퍼티 (스크린에서 직접 사용)
  currentDeal: DealV2 | null;
  currentCompany: CompanyV2 | null;
  currentCategories: RiskCategoryV2[];
  currentRelatedCompanies: CompanyV2[];
}

// ============================================
// Context 생성
// ============================================
const RiskV2Context = createContext<RiskV2ContextType | null>(null);

// ============================================
// Provider 컴포넌트
// ============================================
interface RiskV2ProviderProps {
  children: React.ReactNode;
  /** 초기 딜 ID (선택, URL 파라미터 등에서 주입) */
  initialDealId?: string;
  /** 초기 뷰 타입 */
  initialView?: ViewType;
}

export function RiskV2Provider({
  children,
  initialDealId,
  initialView,
}: RiskV2ProviderProps) {
  const [state, dispatch] = useReducer(riskV2Reducer, {
    ...initialState,
    selectedDealId: initialDealId ?? null,
    activeView: initialView ?? 'command',
  });

  // 편의 액션 함수들
  const selectDeal = useCallback((dealId: string) => {
    dispatch({ type: 'DRILL_DOWN_TO_DEAL', payload: dealId });
  }, []);

  const selectCompany = useCallback((companyId: string) => {
    dispatch({ type: 'DRILL_DOWN_TO_COMPANY', payload: companyId });
  }, []);

  const selectCategory = useCallback((code: CategoryCodeV2) => {
    dispatch({ type: 'DRILL_DOWN_TO_CATEGORY', payload: code });
  }, []);

  const selectEntity = useCallback((entityId: string) => {
    dispatch({ type: 'DRILL_DOWN_TO_ENTITY', payload: entityId });
  }, []);

  const setActiveView = useCallback((view: ViewType) => {
    dispatch({ type: 'SET_ACTIVE_VIEW', payload: view });
  }, []);

  const toggleCopilot = useCallback(() => {
    dispatch({ type: 'TOGGLE_COPILOT' });
  }, []);

  const setCopilotContext = useCallback((ctx: CopilotContextData | null) => {
    dispatch({ type: 'SET_COPILOT_CONTEXT', payload: ctx });
  }, []);

  const navigateBack = useCallback((to: 'deals' | 'company' | 'category') => {
    dispatch({ type: 'NAVIGATE_BACK_TO', payload: to });
  }, []);

  /** 딜 목록 로드 */
  const loadDeals = useCallback(async () => {
    // 초기 로딩만 스켈레톤 표시 — 리프레시 시 기존 데이터 유지
    if (state.deals.length === 0) {
      dispatch({ type: 'SET_DEALS_LOADING', payload: true });
    }
    try {
      const response = await riskApiV2.fetchDeals();
      if (response.success && response.data) {
        dispatch({ type: 'SET_DEALS', payload: response.data.deals });

        // 첫 번째 딜 자동 선택 (선택된 딜이 없을 때)
        if (!state.selectedDealId && response.data.deals.length > 0) {
          dispatch({ type: 'SET_SELECTED_DEAL', payload: response.data.deals[0].id });
        }
      } else {
        console.error('[RiskV2] 딜 로드 실패:', response.error);
        dispatch({ type: 'SET_DEALS_LOADING', payload: false });
      }
    } catch (err) {
      console.error('[RiskV2] 딜 로드 에러:', err);
      dispatch({ type: 'SET_DEALS_LOADING', payload: false });
    }
  }, [state.selectedDealId, state.deals.length]);

  /** 딜 상세 데이터 로드 */
  const loadDealDetail = useCallback(async (dealId: string) => {
    dispatch({ type: 'SET_DEAL_DETAIL_LOADING', payload: true });
    try {
      const response = await riskApiV2.fetchDealDetail(dealId);
      if (response.success && response.data) {
        dispatch({ type: 'SET_DEAL_DETAIL', payload: response.data });

        // Extract recentEvents from API response
        if (response.data.recentEvents && response.data.recentEvents.length > 0) {
          dispatch({ type: 'SET_RECENT_EVENTS', payload: response.data.recentEvents });
        } else {
          dispatch({ type: 'SET_RECENT_EVENTS', payload: [] });
        }
      } else {
        console.error('[RiskV2] 딜 상세 로드 실패:', response.error);
        dispatch({ type: 'SET_DEAL_DETAIL_LOADING', payload: false });
      }
    } catch (err) {
      console.error('[RiskV2] 딜 상세 로드 에러:', err);
      dispatch({ type: 'SET_DEAL_DETAIL_LOADING', payload: false });
    }
  }, []);

  // 마운트 시 딜 목록 로드
  useEffect(() => {
    loadDeals();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // selectedDealId 변경 시 딜 상세 자동 로드
  useEffect(() => {
    if (state.selectedDealId) {
      loadDealDetail(state.selectedDealId);
    } else {
      dispatch({ type: 'SET_DEAL_DETAIL', payload: null });
    }
  }, [state.selectedDealId, loadDealDetail]);

  // 계산된 프로퍼티
  const currentDeal = useMemo(() => {
    if (!state.selectedDealId) return null;
    return state.deals.find(d => d.id === state.selectedDealId) ?? state.dealDetail?.deal ?? null;
  }, [state.selectedDealId, state.deals, state.dealDetail]);

  const currentCompany = useMemo(() => {
    if (!state.dealDetail) return null;
    if (state.selectedCompanyId) {
      const rel = state.dealDetail.relatedCompanies.find(c => c.id === state.selectedCompanyId);
      if (rel) return rel;
    }
    return state.dealDetail.mainCompany;
  }, [state.dealDetail, state.selectedCompanyId]);

  const currentCategories = useMemo(() => {
    return state.dealDetail?.categories ?? [];
  }, [state.dealDetail]);

  const currentRelatedCompanies = useMemo(() => {
    return state.dealDetail?.relatedCompanies ?? [];
  }, [state.dealDetail]);

  const contextValue: RiskV2ContextType = {
    state,
    dispatch,
    selectDeal,
    selectCompany,
    selectCategory,
    selectEntity,
    setActiveView,
    toggleCopilot,
    setCopilotContext,
    navigateBack,
    loadDeals,
    loadDealDetail,
    currentDeal,
    currentCompany,
    currentCategories,
    currentRelatedCompanies,
  };

  return (
    <RiskV2Context.Provider value={contextValue}>
      {children}
    </RiskV2Context.Provider>
  );
}

// ============================================
// Hook
// ============================================

/** RiskV2 컨텍스트 사용 Hook */
export function useRiskV2(): RiskV2ContextType {
  const context = useContext(RiskV2Context);
  if (!context) {
    throw new Error('useRiskV2 must be used within a RiskV2Provider');
  }
  return context;
}

export default RiskV2Context;
