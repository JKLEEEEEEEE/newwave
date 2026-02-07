'use client';

import React, { useState, useEffect } from 'react';
import { DealDetail, DealDetailResponse } from './types';
import { DealSummaryCard } from './DealSummaryCard';
import { CategoryBreakdown } from './CategoryBreakdown';
import { EventList } from './EventList';
import { PersonList } from './PersonList';
import { DrillDownPanel } from './DrillDownPanel';

interface RiskDashboardV4Props {
  dealId: string;
}

type DrillDownState = {
  type: 'category' | 'event' | 'person';
  id: string;
} | null;

const fetchDealDetail = async (dealId: string): Promise<DealDetail | null> => {
  try {
    const res = await fetch(`/api/v4/deals/${encodeURIComponent(dealId)}`);
    if (!res.ok) return null;
    const data: DealDetailResponse = await res.json();
    return data.deal;
  } catch (e) {
    console.error('Failed to fetch deal detail:', e);
    return null;
  }
};

export const RiskDashboardV4: React.FC<RiskDashboardV4Props> = ({ dealId }) => {
  const [deal, setDeal] = useState<DealDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drillDown, setDrillDown] = useState<DrillDownState>(null);

  useEffect(() => {
    const loadDeal = async () => {
      setLoading(true);
      setError(null);

      const data = await fetchDealDetail(dealId);
      if (data) {
        setDeal(data);
      } else {
        setError('딜 정보를 불러올 수 없습니다');
      }
      setLoading(false);
    };

    loadDeal();
  }, [dealId]);

  const handleCategoryClick = (code: string) => {
    setDrillDown({ type: 'category', id: code });
  };

  const handleEventClick = (id: string) => {
    setDrillDown({ type: 'event', id });
  };

  const handlePersonClick = (id: string) => {
    setDrillDown({ type: 'person', id });
  };

  const closeDrillDown = () => {
    setDrillDown(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !deal) {
    return (
      <div className="text-center py-16">
        <div className="text-red-500 text-lg">{error || '데이터를 불러올 수 없습니다'}</div>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Deal Summary */}
      <DealSummaryCard deal={deal} />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <CategoryBreakdown
          categories={deal.categories}
          onCategoryClick={handleCategoryClick}
        />

        {/* Events */}
        <EventList
          events={deal.topEvents}
          onEventClick={handleEventClick}
        />

        {/* Persons */}
        <PersonList
          persons={deal.topPersons}
          onPersonClick={handlePersonClick}
        />

        {/* Evidence Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
            주요 근거
          </h3>
          <div className="space-y-2">
            {deal.evidence.topFactors.map((factor, i) => (
              <div
                key={i}
                className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300"
              >
                {factor}
              </div>
            ))}
            {deal.evidence.topFactors.length === 0 && (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                등록된 근거가 없습니다
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Drill Down Panel */}
      {drillDown && (
        <DrillDownPanel
          dealId={dealId}
          type={drillDown.type}
          id={drillDown.id}
          onClose={closeDrillDown}
        />
      )}
    </div>
  );
};

export default RiskDashboardV4;
