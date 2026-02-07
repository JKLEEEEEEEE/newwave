/**
 * Step 3. 리스크 모니터링 시스템 - WebSocket 훅
 * 실시간 리스크 신호 스트리밍
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { RiskSignal } from '../types';
import { riskApi } from '../api';

interface UseWebSocketOptions {
  onMessage?: (signal: RiskSignal) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    autoReconnect = true,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastSignal, setLastSignal] = useState<RiskSignal | null>(null);
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxRetries = 5;

  // WebSocket 연결
  const connect = useCallback(() => {
    try {
      const ws = riskApi.createSignalWebSocket((signal: RiskSignal) => {
        setLastSignal(signal);
        setSignals((prev) => [signal, ...prev].slice(0, 50)); // 최근 50개만 유지

        if (onMessage) {
          onMessage(signal);
        }
      });

      if (ws) {
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          reconnectAttemptsRef.current = 0;

          // v2.2: 하트비트 시작 (30초 간격)
          if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
          }
          heartbeatIntervalRef.current = setInterval(() => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send('ping');
            }
          }, 30000);

          if (onConnect) {
            onConnect();
          }
          console.log('[WebSocket] 연결됨');
        };

        ws.onerror = (error) => {
          console.error('[WebSocket] 에러:', error);
          if (onError) {
            onError(error);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          wsRef.current = null;

          // v2.2: 하트비트 정리
          if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
            heartbeatIntervalRef.current = null;
          }

          if (onDisconnect) {
            onDisconnect();
          }

          console.log('[WebSocket] 연결 종료');

          // 자동 재연결 (v2.2: 지수 백오프)
          if (autoReconnect && reconnectAttemptsRef.current < maxRetries) {
            reconnectAttemptsRef.current += 1;
            const delay = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1);
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log(
                `[WebSocket] 재연결 시도 (${reconnectAttemptsRef.current}/${maxRetries})...`
              );
              connect();
            }, Math.min(delay, 30000)); // 최대 30초
          } else if (reconnectAttemptsRef.current >= maxRetries) {
            console.error('[WebSocket] 재연결 실패 - 최대 재시도 횟수 초과');
          }
        };
      } else {
        console.log('[WebSocket] Mock 모드 - WebSocket 사용 불가');
      }
    } catch (error) {
      console.error('[WebSocket] 연결 실패:', error);
    }
  }, [onMessage, onError, onConnect, onDisconnect, autoReconnect, reconnectInterval]);

  // WebSocket 연결 종료
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // v2.2: 하트비트 정리
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  // 메시지 전송 (필요 시)
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] 연결되지 않음 - 메시지 전송 불가');
    }
  }, []);

  // 신호 목록 초기화
  const clearSignals = useCallback(() => {
    setSignals([]);
    setLastSignal(null);
  }, []);

  // 컴포넌트 마운트 시 연결
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastSignal,
    signals,
    connect,
    disconnect,
    sendMessage,
    clearSignals,
  };
}

// 실시간 신호 누적 훅 (UI용)
export function useRealtimeSignals(maxSignals: number = 20) {
  const [signals, setSignals] = useState<RiskSignal[]>([]);

  const handleNewSignal = useCallback(
    (signal: RiskSignal) => {
      setSignals((prev) => {
        // 중복 방지
        if (prev.some((s) => s.id === signal.id)) {
          return prev;
        }
        return [signal, ...prev].slice(0, maxSignals);
      });
    },
    [maxSignals]
  );

  const { isConnected, lastSignal } = useWebSocket({
    onMessage: handleNewSignal,
  });

  return {
    signals,
    isConnected,
    lastSignal,
    clearSignals: () => setSignals([]),
  };
}

export default useWebSocket;
