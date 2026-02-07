/**
 * Step 3. 리스크 모니터링 시스템 - AI 대응 가이드
 * OpenAI GPT-4 기반 산업별 맞춤 대응 전략
 */

import React, { useState } from 'react';
import { AIActionGuide as ActionGuideType } from './types';

interface RiskActionGuideProps {
  guide: ActionGuideType;
}

const RiskActionGuide: React.FC<RiskActionGuideProps> = ({ guide }) => {
  const [rmCompleted, setRmCompleted] = useState<Set<number>>(new Set());
  const [opsCompleted, setOpsCompleted] = useState<Set<number>>(new Set());

  // RM To-Do 토글
  const toggleRmTodo = (idx: number) => {
    const newCompleted = new Set(rmCompleted);
    if (newCompleted.has(idx)) {
      newCompleted.delete(idx);
    } else {
      newCompleted.add(idx);
    }
    setRmCompleted(newCompleted);
  };

  // OPS To-Do 토글
  const toggleOpsTodo = (idx: number) => {
    const newCompleted = new Set(opsCompleted);
    if (newCompleted.has(idx)) {
      newCompleted.delete(idx);
    } else {
      newCompleted.add(idx);
    }
    setOpsCompleted(newCompleted);
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          <span>AI ACTION GUIDE</span>
        </h3>
        <div className="flex items-center gap-2 text-xs">
          <div className="bg-blue-600 text-white px-2 py-1 rounded">
            GPT-4
          </div>
          <div className="bg-purple-600 text-white px-2 py-1 rounded">
            {guide.industry}
          </div>
        </div>
      </div>

      {/* 산업 인사이트 */}
      {guide.industryInsight && (
        <div className="mb-6 p-4 bg-purple-900/20 border border-purple-700/30 rounded-lg">
          <div className="text-sm text-purple-300">
            <span className="font-semibold">🔍 산업 인사이트:</span>
            {' '}
            {guide.industryInsight}
          </div>
        </div>
      )}

      {/* 전이 리스크 대응 (있을 경우) */}
      {guide.propagationAction && (
        <div className="mb-6 p-4 bg-orange-900/20 border border-orange-700/30 rounded-lg">
          <div className="text-sm text-orange-300">
            <span className="font-semibold">🔗 공급망 리스크 대응:</span>
            {' '}
            {guide.propagationAction}
          </div>
        </div>
      )}

      {/* RM 영업 가이드 */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">💡</span>
          <h4 className="font-semibold text-slate-200">{guide.rmTitle}</h4>
        </div>

        {/* 가이드 설명 */}
        <div className="mb-3 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
          <p className="text-sm text-blue-200">{guide.rmGuide}</p>
        </div>

        {/* RM To-Do 리스트 */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-400 mb-2">
            RM 액션 아이템:
          </div>
          {guide.rmTodos.map((todo, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer"
              onClick={() => toggleRmTodo(idx)}
            >
              <div className="flex-shrink-0 mt-0.5">
                <input
                  type="checkbox"
                  checked={rmCompleted.has(idx)}
                  onChange={() => toggleRmTodo(idx)}
                  className="w-4 h-4 rounded border-slate-500 text-blue-600 focus:ring-blue-500"
                />
              </div>
              <div className={`flex-1 text-sm ${rmCompleted.has(idx) ? 'line-through text-slate-500' : 'text-slate-300'}`}>
                {todo}
              </div>
            </div>
          ))}
        </div>

        {/* RM 진행률 */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>RM 액션 진행률</span>
            <span>{rmCompleted.size} / {guide.rmTodos.length}</span>
          </div>
          <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${(rmCompleted.size / guide.rmTodos.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* OPS 방어 가이드 */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">🛡️</span>
          <h4 className="font-semibold text-slate-200">{guide.opsTitle}</h4>
        </div>

        {/* 가이드 설명 */}
        <div className="mb-3 p-3 bg-green-900/20 border border-green-700/30 rounded-lg">
          <p className="text-sm text-green-200">{guide.opsGuide}</p>
        </div>

        {/* OPS To-Do 리스트 */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-400 mb-2">
            OPS 액션 아이템:
          </div>
          {guide.opsTodos.map((todo, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer"
              onClick={() => toggleOpsTodo(idx)}
            >
              <div className="flex-shrink-0 mt-0.5">
                <input
                  type="checkbox"
                  checked={opsCompleted.has(idx)}
                  onChange={() => toggleOpsTodo(idx)}
                  className="w-4 h-4 rounded border-slate-500 text-green-600 focus:ring-green-500"
                />
              </div>
              <div className={`flex-1 text-sm ${opsCompleted.has(idx) ? 'line-through text-slate-500' : 'text-slate-300'}`}>
                {todo}
              </div>
            </div>
          ))}
        </div>

        {/* OPS 진행률 */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>OPS 액션 진행률</span>
            <span>{opsCompleted.size} / {guide.opsTodos.length}</span>
          </div>
          <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-300"
              style={{ width: `${(opsCompleted.size / guide.opsTodos.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* 전체 완료 시 축하 메시지 */}
      {rmCompleted.size === guide.rmTodos.length && opsCompleted.size === guide.opsTodos.length && (
        <div className="mt-4 p-3 bg-green-900/20 border border-green-700/30 rounded-lg">
          <div className="text-sm text-green-300 text-center font-semibold">
            ✅ 모든 대응 액션이 완료되었습니다!
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskActionGuide;
