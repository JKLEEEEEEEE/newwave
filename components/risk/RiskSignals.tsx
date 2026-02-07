/**
 * Step 3. 리스크 모니터링 시스템 - 실시간 신호
 */

import React, { useState, useEffect } from 'react';
import { RiskSignal, SIGNAL_STYLES, SignalType } from './types';
import { riskApi } from './api';

interface RiskSignalsProps {
  maxSignals?: number;
}

const RiskSignals: React.FC<RiskSignalsProps> = ({ maxSignals = 5 }) => {
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSignals();
    // 30초마다 갱신
    const interval = setInterval(loadSignals, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSignals = async () => {
    try {
      const res = await riskApi.fetchSignals(maxSignals);
      if (res.success) {
        setSignals(res.data.signals);
      }
    } catch (error) {
      console.error('신호 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timeStr: string) => {
    try {
      const date = new Date(timeStr);
      return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return timeStr;
    }
  };

  const getRelativeTime = (timeStr: string) => {
    try {
      const date = new Date(timeStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return '방금 전';
      if (diffMins < 60) return `${diffMins}분 전`;
      if (diffMins < 1440) return `${Math.floor(diffMins / 60)}시간 전`;
      return `${Math.floor(diffMins / 1440)}일 전`;
    } catch {
      return timeStr;
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-700 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-20 bg-slate-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700">
      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
          <span>REAL-TIME RISK SIGNALS</span>
        </h2>
        <span className="text-xs text-slate-400">
          최근 1시간 <span className="text-white font-bold">{signals.length}건</span> 감지
        </span>
      </div>

      {/* 신호 목록 */}
      <div className="p-4 space-y-3">
        {signals.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <span className="text-3xl">✓</span>
            <p className="mt-2">현재 감지된 리스크 신호가 없습니다.</p>
          </div>
        ) : (
          signals.map(signal => {
            const style = SIGNAL_STYLES[signal.signalType];
            return (
              <div
                key={signal.id}
                className={`p-3 rounded-lg border transition-all hover:border-slate-500 ${style.bg} border-slate-600`}
              >
                {/* 배지 + 시간 */}
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs px-2 py-1 rounded font-medium ${style.badge} text-white`}>
                    {style.label}
                  </span>
                  <span className="text-xs text-slate-400">
                    {formatTime(signal.time)}
                  </span>
                </div>

                {/* 내용 */}
                <div className={`text-sm ${style.text} font-medium`}>
                  {signal.isUrgent && (
                    <span className="text-red-400 mr-1">[긴급]</span>
                  )}
                  {signal.content}
                </div>

                {/* 기업명 + 소스 */}
                <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                  <span>{signal.company}</span>
                  <div className="flex items-center gap-2">
                    <span className="bg-slate-600/50 px-2 py-0.5 rounded">{signal.source}</span>
                    <span className="text-cyan-400 cursor-pointer hover:underline">
                      RM 긴급 가이드 ↗
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 푸터 */}
      {signals.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-700 text-center">
          <button className="text-xs text-blue-400 hover:text-blue-300">
            전체 신호 보기 →
          </button>
        </div>
      )}
    </div>
  );
};

export default RiskSignals;
