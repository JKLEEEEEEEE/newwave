/**
 * V3: Status 중심 대시보드
 * PASS / WARNING / FAIL 기업을 시각적으로 분류하여 표시
 */

import React, { useState, useEffect } from 'react';
import { RiskStatus } from './types';
import { STATUS_CONFIG } from './constants';

// V3 API 응답 타입
interface StatusSummary {
  summary: {
    PASS: number;
    WARNING: number;
    FAIL: number;
    total: number;
  };
  companies: {
    PASS: CompanyItem[];
    WARNING: CompanyItem[];
    FAIL: CompanyItem[];
  };
  updatedAt: string;
}

interface CompanyItem {
  id: string;
  name: string;
  score: number;
  sector: string;
}

interface RiskStatusViewProps {
  onCompanySelect?: (companyId: string) => void;
  selectedCompanyId?: string | null;
}

// STATUS_CONFIG는 constants.ts에서 import하여 사용
// 호환성을 위한 매핑 (기존 속성명 유지)
const getStatusConfig = (status: RiskStatus) => {
  const config = STATUS_CONFIG[status];
  return {
    label: config.label,
    icon: config.icon,
    bgColor: config.bg,
    textColor: config.text,
    borderColor: config.border,
    progressColor: config.progress,
    description: config.description,
  };
};

const RiskStatusView: React.FC<RiskStatusViewProps> = ({
  onCompanySelect,
  selectedCompanyId,
}) => {
  const [data, setData] = useState<StatusSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedStatus, setExpandedStatus] = useState<RiskStatus | null>('FAIL');

  // V3 API에서 Status 요약 조회
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/v3/status/summary');
        if (!response.ok) throw new Error('Failed to fetch status summary');
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // 30초마다 자동 갱신
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-8">
        <div className="flex items-center justify-center gap-3">
          <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-400">Status 데이터 로딩 중...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-xl border border-red-700 p-8">
        <div className="text-center text-red-400">
          <span className="text-2xl mb-2 block">⚠️</span>
          <p>데이터 로드 실패: {error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { summary, companies, updatedAt } = data;
  const totalCompanies = summary.total || 1;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700">
      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <span>🎯</span>
          <span>STATUS OVERVIEW</span>
          <span className="text-xs bg-blue-600 px-2 py-0.5 rounded ml-2">V3</span>
        </h2>
        <span className="text-xs text-slate-400">
          업데이트: {new Date(updatedAt).toLocaleTimeString('ko-KR')}
        </span>
      </div>

      {/* 전체 통계 바 */}
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm text-slate-400">전체 기업:</span>
          <span className="font-bold text-xl">{summary.total}</span>
        </div>

        {/* Progress Bar */}
        <div className="h-4 bg-slate-700 rounded-full overflow-hidden flex">
          {(['PASS', 'WARNING', 'FAIL'] as RiskStatus[]).map((status) => {
            const count = summary[status];
            const percentage = (count / totalCompanies) * 100;
            const config = getStatusConfig(status);

            return percentage > 0 ? (
              <div
                key={status}
                className={`${config.progressColor} h-full transition-all duration-500`}
                style={{ width: `${percentage}%` }}
                title={`${status}: ${count}개 (${percentage.toFixed(1)}%)`}
              />
            ) : null;
          })}
        </div>

        {/* 범례 */}
        <div className="flex justify-center gap-6 mt-3">
          {(['PASS', 'WARNING', 'FAIL'] as RiskStatus[]).map((status) => {
            const count = summary[status];
            const percentage = ((count / totalCompanies) * 100).toFixed(1);
            const config = getStatusConfig(status);

            return (
              <div key={status} className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${config.progressColor}`} />
                <span className={`text-sm ${config.textColor}`}>
                  {config.label}: {count} ({percentage}%)
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Status별 기업 목록 */}
      <div className="border-t border-slate-700">
        {(['FAIL', 'WARNING', 'PASS'] as RiskStatus[]).map((status) => {
          const config = getStatusConfig(status);
          const statusCompanies = companies[status] || [];
          const isExpanded = expandedStatus === status;

          return (
            <div key={status} className="border-b border-slate-700 last:border-b-0">
              {/* Status 헤더 (클릭 가능) */}
              <button
                onClick={() => setExpandedStatus(isExpanded ? null : status)}
                className={`w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/50 transition-colors ${config.bgColor}`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{config.icon}</span>
                  <div className="text-left">
                    <div className={`font-semibold ${config.textColor}`}>
                      {config.label}
                    </div>
                    <div className="text-xs text-slate-400">
                      {config.description}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-2xl font-bold ${config.textColor}`}>
                    {statusCompanies.length}
                  </span>
                  <svg
                    className={`w-5 h-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {/* 기업 목록 (확장 시) */}
              {isExpanded && statusCompanies.length > 0 && (
                <div className="px-4 pb-4 pt-2 space-y-2">
                  {statusCompanies.map((company) => (
                    <button
                      key={company.id}
                      onClick={() => onCompanySelect?.(company.id)}
                      className={`w-full p-3 rounded-lg border transition-all ${
                        selectedCompanyId === company.id
                          ? `${config.bgColor} ${config.borderColor} border-2`
                          : 'bg-slate-700/50 border-slate-600 hover:bg-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="text-left">
                          <div className="font-medium text-slate-100">
                            {company.name}
                          </div>
                          <div className="text-xs text-slate-400">
                            {company.sector}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-xl font-bold ${config.textColor}`}>
                            {company.score}
                          </div>
                          <div className="text-xs text-slate-400">점</div>
                        </div>
                      </div>

                      {/* 점수 미니 바 */}
                      <div className="mt-2 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${config.progressColor} transition-all`}
                          style={{ width: `${Math.min(company.score, 100)}%` }}
                        />
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* 빈 상태 */}
              {isExpanded && statusCompanies.length === 0 && (
                <div className="px-4 pb-4 pt-2">
                  <div className="text-center text-slate-500 py-4">
                    해당 Status의 기업이 없습니다
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 빠른 필터 */}
      <div className="p-4 border-t border-slate-700 bg-slate-800/50">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">빠른 필터</span>
          <div className="flex gap-2">
            {(['FAIL', 'WARNING', 'PASS'] as RiskStatus[]).map((status) => {
              const config = getStatusConfig(status);
              return (
                <button
                  key={status}
                  onClick={() => setExpandedStatus(status)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    expandedStatus === status
                      ? `${config.bgColor} ${config.textColor} border ${config.borderColor}`
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {config.icon} {config.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskStatusView;
