/**
 * Step 3. 리스크 모니터링 시스템 - 3단계 타임라인
 * 뉴스 보도 → 규제 통보 → 채권단 확인
 */

import React from 'react';
import { TimelineEvent, TimelineStage, TIMELINE_STAGES } from './types';

interface RiskTimelineProps {
  events: TimelineEvent[];
}

const RiskTimeline: React.FC<RiskTimelineProps> = ({ events }) => {
  // 스테이지별 이벤트 그룹화 (1: 뉴스, 2: 규제, 3: 채권단)
  const groupedEvents = React.useMemo(() => {
    const groups: Record<TimelineStage, TimelineEvent[]> = {
      1: [],
      2: [],
      3: [],
    };

    events.forEach(event => {
      if (groups[event.stage]) {
        groups[event.stage].push(event);
      }
    });

    return groups;
  }, [events]);

  const getStageIcon = (stage: TimelineStage) => {
    switch (stage) {
      case 1: return '📰';
      case 2: return '⚖️';
      case 3: return '🏦';
    }
  };

  const getStageColor = (stage: TimelineStage) => {
    switch (stage) {
      case 1: return {
        bg: 'bg-blue-900/30',
        border: 'border-blue-600',
        text: 'text-blue-400',
        dot: 'bg-blue-500',
      };
      case 2: return {
        bg: 'bg-yellow-900/30',
        border: 'border-yellow-600',
        text: 'text-yellow-400',
        dot: 'bg-yellow-500',
      };
      case 3: return {
        bg: 'bg-red-900/30',
        border: 'border-red-600',
        text: 'text-red-400',
        dot: 'bg-red-500',
      };
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('ko-KR', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700">
      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <span>📅</span>
          <span>RISK TIMELINE</span>
        </h2>
        <span className="text-xs text-slate-400">
          3-Stage Early Warning System
        </span>
      </div>

      {/* 3단계 헤더 */}
      <div className="px-4 py-3 grid grid-cols-3 gap-2 border-b border-slate-700">
        {([1, 2, 3] as TimelineStage[]).map(stage => {
          const stageInfo = TIMELINE_STAGES[stage];
          const colors = getStageColor(stage);
          const count = groupedEvents[stage].length;

          return (
            <div
              key={stage}
              className={`p-2 rounded-lg ${colors.bg} border ${colors.border}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span>{getStageIcon(stage)}</span>
                  <span className={`text-sm font-medium ${colors.text}`}>
                    {stageInfo.label}
                  </span>
                </div>
                <span className={`text-lg font-bold ${colors.text}`}>
                  {count}
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {stageInfo.description}
              </div>
            </div>
          );
        })}
      </div>

      {/* 타임라인 */}
      <div className="p-4 max-h-80 overflow-y-auto custom-scrollbar">
        {events.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <span className="text-3xl">📭</span>
            <p className="mt-2">타임라인 이벤트가 없습니다.</p>
          </div>
        ) : (
          <div className="relative">
            {/* 세로 라인 */}
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-600"></div>

            {/* 이벤트 목록 */}
            <div className="space-y-4">
              {events.map((event, idx) => {
                const colors = getStageColor(event.stage);
                return (
                  <div key={event.id} className="relative pl-10">
                    {/* 점 */}
                    <div
                      className={`absolute left-2.5 top-1.5 w-3 h-3 rounded-full ${colors.dot} ring-4 ring-slate-800`}
                    ></div>

                    {/* 카드 */}
                    <div className={`p-3 rounded-lg ${colors.bg} border border-slate-600`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-xs px-2 py-0.5 rounded ${colors.text} bg-slate-700`}>
                          {TIMELINE_STAGES[event.stage].label}
                        </span>
                        <span className="text-xs text-slate-400">
                          {formatDate(event.date)}
                        </span>
                      </div>
                      <div className="text-sm text-slate-200">
                        {event.content}
                      </div>
                      {event.source && (
                        <div className="mt-2 text-xs text-slate-400">
                          출처: {event.source}
                        </div>
                      )}
                      {event.impact && (
                        <div className="mt-1 flex items-center gap-1">
                          <span className="text-xs text-slate-400">영향도:</span>
                          <div className="flex gap-0.5">
                            {[1, 2, 3, 4, 5].map(i => (
                              <div
                                key={i}
                                className={`w-2 h-2 rounded-full ${
                                  i <= event.impact!
                                    ? colors.dot
                                    : 'bg-slate-600'
                                }`}
                              ></div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RiskTimeline;
