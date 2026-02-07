'use client';

import React from 'react';
import { EventSummary, Severity, CATEGORY_CONFIG } from './types';

interface EventListProps {
  events: EventSummary[];
  onEventClick?: (id: string) => void;
  showCategory?: boolean;
}

const SeverityBadge: React.FC<{ severity: Severity }> = ({ severity }) => {
  const colors: Record<Severity, string> = {
    CRITICAL: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    MEDIUM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    LOW: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  };

  const labels: Record<Severity, string> = {
    CRITICAL: '심각',
    HIGH: '높음',
    MEDIUM: '중간',
    LOW: '낮음',
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colors[severity]}`}>
      {labels[severity]}
    </span>
  );
};

const formatDate = (dateString: string): string => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
};

export const EventList: React.FC<EventListProps> = ({
  events,
  onEventClick,
  showCategory = true,
}) => {
  if (events.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          리스크 이벤트
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-center py-8">
          등록된 이벤트가 없습니다
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
        리스크 이벤트 ({events.length})
      </h3>

      <div className="space-y-3">
        {events.map((event) => {
          const categoryConfig = CATEGORY_CONFIG[event.category];

          return (
            <div
              key={event.id}
              className={`p-3 rounded-lg border border-gray-200 dark:border-gray-700
                         hover:border-blue-400 dark:hover:border-blue-500 transition-colors
                         ${onEventClick ? 'cursor-pointer' : ''}`}
              onClick={() => onEventClick?.(event.id)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {showCategory && categoryConfig && (
                      <span className="text-sm">{categoryConfig.icon}</span>
                    )}
                    <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                      {event.title}
                    </h4>
                  </div>

                  <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                    {showCategory && categoryConfig && (
                      <span>{categoryConfig.name}</span>
                    )}
                    {event.firstDetectedAt && (
                      <span>{formatDate(event.firstDetectedAt)}</span>
                    )}
                    <span>뉴스 {event.newsCount}</span>
                    {event.disclosureCount > 0 && (
                      <span>공시 {event.disclosureCount}</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1">
                  <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {event.score}
                  </span>
                  <SeverityBadge severity={event.severity} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EventList;
