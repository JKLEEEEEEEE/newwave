'use client';

import React from 'react';
import { PersonSummary, RiskLevel } from './types';

interface PersonListProps {
  persons: PersonSummary[];
  onPersonClick?: (id: string) => void;
}

const RiskLevelBadge: React.FC<{ level: RiskLevel; score: number }> = ({ level, score }) => {
  const colors: Record<RiskLevel, string> = {
    PASS: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    WARNING: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    FAIL: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };

  const getRiskLevel = (s: number): RiskLevel => {
    if (s >= 50) return 'FAIL';
    if (s >= 25) return 'WARNING';
    return 'PASS';
  };

  const displayLevel = level || getRiskLevel(score);

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colors[displayLevel]}`}>
      {score}점
    </span>
  );
};

const PersonTypeIcon: React.FC<{ type: string }> = ({ type }) => {
  return type === 'EXECUTIVE' ? (
    <span title="임원">👔</span>
  ) : (
    <span title="주주">💰</span>
  );
};

export const PersonList: React.FC<PersonListProps> = ({
  persons,
  onPersonClick,
}) => {
  if (persons.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          관련 인물
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-center py-8">
          등록된 인물이 없습니다
        </p>
      </div>
    );
  }

  // Sort by risk score descending
  const sortedPersons = [...persons].sort((a, b) => b.riskScore - a.riskScore);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
        관련 인물 ({persons.length})
      </h3>

      <div className="space-y-2">
        {sortedPersons.map((person) => (
          <div
            key={person.id}
            className={`p-3 rounded-lg border border-gray-200 dark:border-gray-700
                       hover:border-blue-400 dark:hover:border-blue-500 transition-colors
                       ${onPersonClick ? 'cursor-pointer' : ''}`}
            onClick={() => onPersonClick?.(person.id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <PersonTypeIcon type={person.type} />
                <div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">
                    {person.name}
                  </div>
                  {person.position && (
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {person.position}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="text-sm text-gray-500 dark:text-gray-400 text-right">
                  {person.relatedNewsCount > 0 && (
                    <div>뉴스 {person.relatedNewsCount}</div>
                  )}
                  {person.relatedEventCount > 0 && (
                    <div>이벤트 {person.relatedEventCount}</div>
                  )}
                </div>
                <RiskLevelBadge
                  level={person.riskScore >= 50 ? 'FAIL' : person.riskScore >= 25 ? 'WARNING' : 'PASS'}
                  score={person.riskScore}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PersonList;
