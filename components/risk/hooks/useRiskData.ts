/**
 * Step 3. 리스크 모니터링 시스템 - 데이터 페칭 훅
 * React Query 기반 리스크 데이터 관리
 */

import { useState, useEffect, useCallback } from 'react';
import {
  RiskDeal,
  RiskSnapshot,
  CategoryScore,
  SupplyChainGraph,
  RiskPropagation,
  AIActionGuide,
  TimelineEvent,
  RiskSignal,
  SimulationScenario,
  SimulationResult,
  DealsResponse,
} from '../types';
import { riskApi } from '../api';

// 딜 목록 훅
export function useDeals() {
  const [data, setData] = useState<DealsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchDeals();
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch deals');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 딜 상세 훅
export function useDealDetail(dealId: string | null) {
  const [data, setData] = useState<RiskSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!dealId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchDealDetail(dealId);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch deal detail');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 카테고리 분석 훅
export function useRiskBreakdown(dealId: string | null) {
  const [data, setData] = useState<CategoryScore[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!dealId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchRiskBreakdown(dealId);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch risk breakdown');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 공급망 그래프 훅
export function useSupplyChain(dealId: string | null) {
  const [data, setData] = useState<SupplyChainGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!dealId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchSupplyChain(dealId);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch supply chain');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 리스크 전이 분석 훅
export function usePropagation(dealId: string | null) {
  const [data, setData] = useState<RiskPropagation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!dealId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchPropagation(dealId);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch propagation');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 실시간 신호 훅
export function useSignals(limit: number = 10) {
  const [data, setData] = useState<RiskSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchSignals(limit);
      if (response.success) {
        setData(response.data.signals);
      } else {
        setError(response.error || 'Failed to fetch signals');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 타임라인 훅
export function useTimeline(dealId: string | null) {
  const [data, setData] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!dealId) {
      setData([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchTimeline(dealId);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch timeline');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// AI 가이드 훅
export function useAIGuide(dealId: string | null, signalType: string = 'OPERATIONAL') {
  const [data, setData] = useState<AIActionGuide | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!dealId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchAIGuide(dealId, signalType);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch AI guide');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [dealId, signalType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 시뮬레이션 시나리오 훅
export function useScenarios() {
  const [data, setData] = useState<SimulationScenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await riskApi.fetchScenarios();
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to fetch scenarios');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// 시뮬레이션 실행 훅
export function useSimulation() {
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = useCallback(async (scenarioId: string, dealIds?: string[]) => {
    setLoading(true);
    setError(null);
    setResults([]);

    try {
      const response = await riskApi.runSimulation(scenarioId, dealIds);
      if (response.success) {
        setResults(response.data);
      } else {
        setError(response.error || 'Failed to run simulation');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, loading, error, runSimulation, clearResults: () => setResults([]) };
}
