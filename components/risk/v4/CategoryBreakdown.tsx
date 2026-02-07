'use client';

import React from 'react';
import { CategorySummary, CATEGORY_CONFIG, Trend } from './types';

interface CategoryBreakdownProps {
  categories: CategorySummary[];
  onCategoryClick?: (code: string) => void;
}

const TrendIcon: React.FC<{ trend: Trend }> = ({ trend }) => {
  switch (trend) {
    case 'UP':
      return <span className="text-red-500">↑</span>;
    case 'DOWN':
      return <span className="text-green-500">↓</span>;
    default:
      return <span className="text-gray-400">→</span>;
  }
};

const getScoreColor = (score: number): string => {
  if (score >= 75) return 'bg-red-500';
  if (score >= 50) return 'bg-orange-500';
  if (score >= 25) return 'bg-yellow-500';
  return 'bg-green-500';
};

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({
  categories,
  onCategoryClick,
}) => {
  const sortedCategories = [...categories].sort((a, b) => b.score - a.score);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
        카테고리별 리스크
      </h3>

      <div className="space-y-3">
        {sortedCategories.map((category) => {
          const config = CATEGORY_CONFIG[category.code];

          return (
            <div
              key={category.code}
              className={`p-3 rounded-lg border border-gray-200 dark:border-gray-700
                         hover:border-blue-400 dark:hover:border-blue-500 transition-colors
                         ${onCategoryClick ? 'cursor-pointer' : ''}`}
              onClick={() => onCategoryClick?.(category.code)}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{config?.icon || category.icon}</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {config?.name || category.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {category.score}
                  </span>
                  <TrendIcon trend={category.trend} />
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getScoreColor(category.score)} transition-all duration-300`}
                  style={{ width: `${category.score}%` }}
                />
              </div>

              {/* Stats */}
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-500 dark:text-gray-400">
                <span>가중치: {(category.weight * 100).toFixed(0)}%</span>
                <span>이벤트: {category.eventCount}</span>
                {category.personCount > 0 && (
                  <span>인물: {category.personCount}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CategoryBreakdown;
