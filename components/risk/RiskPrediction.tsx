/**
 * 리스크 예측 차트
 * ML 모델 기반 미래 리스크 시각화
 * Risk Monitoring System - Phase 3
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
  ReferenceLine,
} from 'recharts';

interface PredictionData {
  date: string;
  predicted_score: number;
  lower_bound?: number;
  upper_bound?: number;
}

interface PredictionResult {
  company_id: string;
  periods: number;
  predictions: PredictionData[];
  trend: 'increasing' | 'decreasing' | 'stable';
  confidence: number | null;
  is_fallback: boolean;
  model_type: string;
}

interface Props {
  dealId: string;
  dealName: string;
  currentScore?: number;
}

const RiskPrediction: React.FC<Props> = ({ dealId, dealName, currentScore }) => {
  const [predictions, setPredictions] = useState<PredictionData[]>([]);
  const [periods, setPeriods] = useState<7 | 30 | 90>(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trend, setTrend] = useState<string>('stable');
  const [confidence, setConfidence] = useState<number>(0);
  const [isFallback, setIsFallback] = useState<boolean>(false);
  const [modelType, setModelType] = useState<string>('unknown');

  // 예측 데이터 로드
  const loadPredictions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v2/predict/${dealId}?periods=${periods}`
      );
      const result = await response.json();

      if (result.success && result.data) {
        const data: PredictionResult = result.data;
        setPredictions(data.predictions);
        setTrend(data.trend);
        setConfidence(data.confidence || 0);
        setIsFallback(data.is_fallback);
        setModelType(data.model_type);
      } else {
        setError(result.error || '예측 데이터 로드 실패');
      }
    } catch (err) {
      setError('서버 연결 실패');
      console.error('예측 로드 실패:', err);
    } finally {
      setLoading(false);
    }
  }, [dealId, periods]);

  useEffect(() => {
    loadPredictions();
  }, [loadPredictions]);

  // 트렌드 아이콘
  const getTrendIcon = () => {
    if (trend === 'increasing') return '📈';
    if (trend === 'decreasing') return '📉';
    return '➡️';
  };

  // 트렌드 색상
  const getTrendColor = () => {
    if (trend === 'increasing') return 'text-red-400';
    if (trend === 'decreasing') return 'text-green-400';
    return 'text-slate-400';
  };

  // 트렌드 레이블
  const getTrendLabel = () => {
    if (trend === 'increasing') return '상승';
    if (trend === 'decreasing') return '하락';
    return '유지';
  };

  // 모델 학습 요청
  const handleTrainModel = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v2/predict/train/${dealId}`, {
        method: 'POST',
      });
      const result = await response.json();

      if (result.success) {
        // 학습 성공 후 예측 재실행
        await loadPredictions();
      } else {
        setError(result.data?.error || '모델 학습 실패');
      }
    } catch (err) {
      setError('모델 학습 실패');
    } finally {
      setLoading(false);
    }
  };

  // 차트 데이터 가공
  const chartData = predictions.map((p) => ({
    ...p,
    displayDate: p.date.slice(5), // MM-DD 형식
    // 신뢰 구간 영역 표시를 위한 계산
    confidenceRange:
      p.upper_bound !== undefined && p.lower_bound !== undefined
        ? [p.lower_bound, p.upper_bound]
        : undefined,
  }));

  // 예측 기간 내 최대/최소값
  const maxScore =
    predictions.length > 0
      ? Math.max(
          ...predictions.map((p) => p.upper_bound ?? p.predicted_score)
        )
      : 100;
  const minScore =
    predictions.length > 0
      ? Math.min(
          ...predictions.map((p) => p.lower_bound ?? p.predicted_score)
        )
      : 0;

  // 위험 임계값
  const warningThreshold = 40;
  const dangerThreshold = 70;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">🔮</span>
          <span>리스크 예측</span>
          <span className="text-sm text-slate-400 font-normal">
            ({dealName})
          </span>
        </h3>

        {/* 기간 선택 */}
        <div className="flex gap-2">
          {([7, 30, 90] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriods(p)}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                periods === p
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {p}일
            </button>
          ))}
        </div>
      </div>

      {/* 트렌드 및 신뢰도 요약 */}
      <div className="flex gap-4 mb-4">
        <div className="bg-slate-700/30 px-4 py-2 rounded-lg">
          <span className="text-xs text-slate-400 block">트렌드</span>
          <div className={`text-lg font-bold ${getTrendColor()}`}>
            {getTrendIcon()} {getTrendLabel()}
          </div>
        </div>
        <div className="bg-slate-700/30 px-4 py-2 rounded-lg">
          <span className="text-xs text-slate-400 block">신뢰도</span>
          <div className="text-lg font-bold text-blue-400">
            {(confidence * 100).toFixed(0)}%
          </div>
        </div>
        <div className="bg-slate-700/30 px-4 py-2 rounded-lg">
          <span className="text-xs text-slate-400 block">모델</span>
          <div className="text-lg font-bold text-slate-300">
            {modelType === 'prophet'
              ? 'Prophet'
              : modelType === 'random_walk'
              ? 'RandomWalk'
              : 'Simple'}
          </div>
        </div>
        {currentScore !== undefined && (
          <div className="bg-slate-700/30 px-4 py-2 rounded-lg">
            <span className="text-xs text-slate-400 block">현재 점수</span>
            <div className="text-lg font-bold text-orange-400">
              {currentScore}점
            </div>
          </div>
        )}
      </div>

      {/* 폴백 경고 */}
      {isFallback && (
        <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-700/30 rounded-lg flex items-center justify-between">
          <div className="text-sm text-yellow-400">
            <span className="font-semibold">⚠️ 폴백 예측 사용 중</span>
            <span className="text-yellow-500 ml-2">
              Prophet 모델이 없어 간단 예측을 사용합니다.
            </span>
          </div>
          <button
            onClick={handleTrainModel}
            disabled={loading}
            className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            모델 학습
          </button>
        </div>
      )}

      {/* 에러 메시지 */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* 차트 */}
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : predictions.length === 0 ? (
        <div className="h-64 flex items-center justify-center text-slate-500">
          예측 데이터가 없습니다.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData}>
            <defs>
              <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="displayDate"
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
              interval={Math.floor(predictions.length / 7)}
            />
            <YAxis
              domain={[
                Math.max(0, minScore - 10),
                Math.min(100, maxScore + 10),
              ]}
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '8px',
              }}
              labelFormatter={(label) => `날짜: ${label}`}
              formatter={(value: number, name: string) => {
                const labels: Record<string, string> = {
                  predicted_score: '예측 점수',
                  upper_bound: '상한',
                  lower_bound: '하한',
                };
                return [`${value}점`, labels[name] || name];
              }}
            />

            {/* 위험 임계선 */}
            <ReferenceLine
              y={warningThreshold}
              stroke="#22c55e"
              strokeDasharray="5 5"
              label={{
                value: 'PASS',
                position: 'right',
                fill: '#22c55e',
                fontSize: 10,
              }}
            />
            <ReferenceLine
              y={dangerThreshold}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label={{
                value: 'FAIL',
                position: 'right',
                fill: '#ef4444',
                fontSize: 10,
              }}
            />

            {/* 신뢰 구간 (상한) */}
            <Area
              type="monotone"
              dataKey="upper_bound"
              stroke="none"
              fill="url(#confidenceGradient)"
              fillOpacity={1}
            />

            {/* 신뢰 구간 (하한 - 배경 덮기) */}
            <Area
              type="monotone"
              dataKey="lower_bound"
              stroke="none"
              fill="#1e293b"
              fillOpacity={1}
            />

            {/* 예측 선 */}
            <Line
              type="monotone"
              dataKey="predicted_score"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#3b82f6' }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* 예측 요약 */}
      {predictions.length > 0 && (
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div className="bg-slate-700/30 p-3 rounded-lg text-center">
            <div className="text-xs text-slate-400 mb-1">시작 예측</div>
            <div className="text-lg font-bold text-slate-200">
              {predictions[0]?.predicted_score}점
            </div>
            <div className="text-xs text-slate-500">
              {predictions[0]?.date}
            </div>
          </div>
          <div className="bg-slate-700/30 p-3 rounded-lg text-center">
            <div className="text-xs text-slate-400 mb-1">중간 예측</div>
            <div className="text-lg font-bold text-slate-200">
              {predictions[Math.floor(predictions.length / 2)]?.predicted_score}점
            </div>
            <div className="text-xs text-slate-500">
              {predictions[Math.floor(predictions.length / 2)]?.date}
            </div>
          </div>
          <div className="bg-slate-700/30 p-3 rounded-lg text-center">
            <div className="text-xs text-slate-400 mb-1">최종 예측</div>
            <div
              className={`text-lg font-bold ${
                (predictions[predictions.length - 1]?.predicted_score ?? 0) >=
                dangerThreshold
                  ? 'text-red-400'
                  : (predictions[predictions.length - 1]?.predicted_score ?? 0) >=
                    warningThreshold
                  ? 'text-yellow-400'
                  : 'text-green-400'
              }`}
            >
              {predictions[predictions.length - 1]?.predicted_score}점
            </div>
            <div className="text-xs text-slate-500">
              {predictions[predictions.length - 1]?.date}
            </div>
          </div>
        </div>
      )}

      {/* 범례 */}
      <div className="mt-4 flex items-center justify-center gap-6 text-xs text-slate-400">
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-blue-500"></div>
          <span>예측 점수</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-3 bg-blue-500/20 rounded"></div>
          <span>95% 신뢰 구간</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-red-500 border-dashed"></div>
          <span>위험 임계 (70점)</span>
        </div>
      </div>
    </div>
  );
};

export default RiskPrediction;
