'use client';

import React, { useState, useEffect } from 'react';
import {
  DealDetail,
  CategoryDetail,
  EventDetail,
  PersonDetail,
  CategoryDetailResponse,
  EventDetailResponse,
  PersonDetailResponse,
} from './types';

type DrillDownType = 'category' | 'event' | 'person';
type DrillDownData = CategoryDetail | EventDetail | PersonDetail;

interface DrillDownPanelProps {
  dealId: string;
  type: DrillDownType;
  id: string;
  onClose: () => void;
}

const fetchCategoryDetail = async (dealId: string, code: string): Promise<CategoryDetail | null> => {
  try {
    const res = await fetch(`/api/v4/deals/${encodeURIComponent(dealId)}/categories/${code}`);
    if (!res.ok) return null;
    const data: CategoryDetailResponse = await res.json();
    return data.category;
  } catch (e) {
    console.error('Failed to fetch category detail:', e);
    return null;
  }
};

const fetchEventDetail = async (eventId: string): Promise<EventDetail | null> => {
  try {
    const res = await fetch(`/api/v4/events/${encodeURIComponent(eventId)}`);
    if (!res.ok) return null;
    const data: EventDetailResponse = await res.json();
    return data.event;
  } catch (e) {
    console.error('Failed to fetch event detail:', e);
    return null;
  }
};

const fetchPersonDetail = async (personId: string): Promise<PersonDetail | null> => {
  try {
    const res = await fetch(`/api/v4/persons/${encodeURIComponent(personId)}`);
    if (!res.ok) return null;
    const data: PersonDetailResponse = await res.json();
    return data.person;
  } catch (e) {
    console.error('Failed to fetch person detail:', e);
    return null;
  }
};

const CategoryDetailView: React.FC<{ detail: CategoryDetail }> = ({ detail }) => (
  <div className="space-y-4">
    <div className="flex items-center gap-3">
      <span className="text-3xl">{detail.icon}</span>
      <div>
        <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          {detail.name}
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          점수: {detail.score} | 가중치: {(detail.weight * 100).toFixed(0)}%
        </p>
      </div>
    </div>

    {detail.events.length > 0 && (
      <div>
        <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
          관련 이벤트 ({detail.events.length})
        </h4>
        <div className="space-y-2">
          {detail.events.map((e) => (
            <div key={e.id} className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <div className="font-medium">{e.title}</div>
              <div className="text-sm text-gray-500">점수: {e.score}</div>
            </div>
          ))}
        </div>
      </div>
    )}

    {detail.news.length > 0 && (
      <div>
        <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
          관련 뉴스 ({detail.news.length})
        </h4>
        <div className="space-y-2">
          {detail.news.map((n) => (
            <div key={n.id} className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <a
                href={n.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-blue-600 hover:underline"
              >
                {n.title}
              </a>
              <div className="text-sm text-gray-500">점수: {n.rawScore}</div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

const EventDetailView: React.FC<{ detail: EventDetail }> = ({ detail }) => (
  <div className="space-y-4">
    <div>
      <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
        {detail.title}
      </h3>
      <p className="text-gray-500 dark:text-gray-400 mt-1">
        {detail.description || '설명 없음'}
      </p>
    </div>

    <div className="grid grid-cols-2 gap-3">
      <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <div className="text-sm text-gray-500">점수</div>
        <div className="text-xl font-bold">{detail.score}</div>
      </div>
      <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <div className="text-sm text-gray-500">심각도</div>
        <div className="text-xl font-bold">{detail.severity}</div>
      </div>
    </div>

    {detail.matchedKeywords.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2">매칭 키워드</h4>
        <div className="flex flex-wrap gap-2">
          {detail.matchedKeywords.map((kw, i) => (
            <span
              key={i}
              className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-sm"
            >
              {kw}
            </span>
          ))}
        </div>
      </div>
    )}

    {detail.news.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2">관련 뉴스 ({detail.news.length})</h4>
        <div className="space-y-2">
          {detail.news.map((n) => (
            <div key={n.id} className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <a
                href={n.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-blue-600 hover:underline"
              >
                {n.title}
              </a>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

const PersonDetailView: React.FC<{ detail: PersonDetail }> = ({ detail }) => (
  <div className="space-y-4">
    <div className="flex items-center gap-3">
      <span className="text-3xl">{detail.type === 'EXECUTIVE' ? '👔' : '💰'}</span>
      <div>
        <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          {detail.name}
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          {detail.position || (detail.type === 'EXECUTIVE' ? '임원' : '주주')}
        </p>
      </div>
    </div>

    <div className="grid grid-cols-2 gap-3">
      <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <div className="text-sm text-gray-500">리스크 점수</div>
        <div className="text-xl font-bold">{detail.riskScore}</div>
      </div>
      <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <div className="text-sm text-gray-500">리스크 등급</div>
        <div className="text-xl font-bold">{detail.riskLevel}</div>
      </div>
    </div>

    {detail.companies.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2">관련 기업</h4>
        <div className="flex flex-wrap gap-2">
          {detail.companies.map((c, i) => (
            <span
              key={i}
              className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-sm"
            >
              {c}
            </span>
          ))}
        </div>
      </div>
    )}

    {detail.involvedEvents.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2">관련 이벤트 ({detail.involvedEvents.length})</h4>
        <div className="space-y-2">
          {detail.involvedEvents.map((e) => (
            <div key={e.id} className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <div className="font-medium">{e.title}</div>
              <div className="text-sm text-gray-500">점수: {e.score}</div>
            </div>
          ))}
        </div>
      </div>
    )}

    {detail.relatedNews.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2">관련 뉴스 ({detail.relatedNews.length})</h4>
        <div className="space-y-2">
          {detail.relatedNews.map((n) => (
            <div key={n.id} className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <a
                href={n.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-blue-600 hover:underline"
              >
                {n.title}
              </a>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

export const DrillDownPanel: React.FC<DrillDownPanelProps> = ({
  dealId,
  type,
  id,
  onClose,
}) => {
  const [data, setData] = useState<DrillDownData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      let result: DrillDownData | null = null;

      switch (type) {
        case 'category':
          result = await fetchCategoryDetail(dealId, id);
          break;
        case 'event':
          result = await fetchEventDetail(id);
          break;
        case 'person':
          result = await fetchPersonDetail(id);
          break;
      }

      if (result) {
        setData(result);
      } else {
        setError('데이터를 불러올 수 없습니다');
      }
      setLoading(false);
    };

    fetchData();
  }, [dealId, type, id]);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-full max-w-lg bg-white dark:bg-gray-800 shadow-xl">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {type === 'category' && '카테고리 상세'}
              {type === 'event' && '이벤트 상세'}
              {type === 'person' && '인물 상세'}
            </h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {loading && (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
              </div>
            )}

            {error && (
              <div className="text-center text-red-500 py-8">{error}</div>
            )}

            {!loading && !error && data && (
              <>
                {type === 'category' && (
                  <CategoryDetailView detail={data as CategoryDetail} />
                )}
                {type === 'event' && (
                  <EventDetailView detail={data as EventDetail} />
                )}
                {type === 'person' && (
                  <PersonDetailView detail={data as PersonDetail} />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DrillDownPanel;
