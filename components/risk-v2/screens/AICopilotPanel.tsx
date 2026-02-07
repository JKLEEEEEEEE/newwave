/**
 * AICopilotPanel - AI Copilot 슬라이딩 패널
 *
 * 우측에서 슬라이드인하는 AI 코파일럿.
 * 현재 화면 컨텍스트에 맞는 인사이트를 제공하고,
 * Text2Cypher 자연어 질의를 통해 Graph DB를 탐색.
 *
 * GPT-4 AI 활용을 시각적으로 증명하는 핵심 UI 요소.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRiskV2 } from '../context/RiskV2Context';
import { riskApiV2 } from '../api-v2';
import type { Text2CypherResultV2, BriefingResponse } from '../types-v2';

// 예제 질문 칩 목록
const EXAMPLE_QUERIES = [
  'SK하이닉스 리스크 요약',
  '법률 위험 상세',
  '공급망 전이 경로',
];

// ============================================
// 스파클 아이콘 SVG
// ============================================
function SparkleIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.456-2.456L14.25 6l1.035-.259a3.375 3.375 0 002.456-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
      />
    </svg>
  );
}

// ============================================
// 닫기 아이콘 SVG
// ============================================
function CloseIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

// ============================================
// 전송 아이콘 SVG
// ============================================
function SendIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
      />
    </svg>
  );
}

// ============================================
// 복사 아이콘 SVG
// ============================================
function CopyIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
      />
    </svg>
  );
}

// ============================================
// 체크 아이콘 SVG (복사 완료 피드백용)
// ============================================
function CheckIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4.5 12.75l6 6 9-13.5"
      />
    </svg>
  );
}

// ============================================
// 복사 버튼 컴포넌트 (U10)
// ============================================
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API 실패 시 fallback
      console.warn('[CopyButton] clipboard write failed');
    }
  }, [text]);

  // cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded-md hover:bg-white/10 transition-colors duration-150 flex-shrink-0
        focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500/50"
      aria-label={copied ? '복사됨' : '응답 복사'}
      title={copied ? '복사됨!' : '클립보드에 복사'}
    >
      {copied ? (
        <CheckIcon className="w-3.5 h-3.5 text-green-400" />
      ) : (
        <CopyIcon className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300" />
      )}
    </button>
  );
}

// ============================================
// 브리핑 복사 텍스트 생성 헬퍼
// ============================================
function generateBriefingCopyText(briefing: BriefingResponse): string {
  const lines = [
    `AI Investment Briefing: ${briefing.company}`,
    `Risk Score: ${briefing.riskScore} (${briefing.riskLevel})`,
    '',
    '=== EXECUTIVE SUMMARY ===',
    briefing.executive_summary,
    '',
    '=== CONTEXT ANALYSIS ===',
    `Industry: ${briefing.context_analysis.industry_context}`,
    `Timing: ${briefing.context_analysis.timing_significance}`,
    '',
    '=== CROSS-SIGNAL ANALYSIS ===',
    `Patterns: ${briefing.cross_signal_analysis.patterns_detected.join(', ')}`,
    `Correlations: ${briefing.cross_signal_analysis.correlations}`,
    `Anomalies: ${briefing.cross_signal_analysis.anomalies}`,
    '',
    '=== STAKEHOLDER INSIGHTS ===',
    `Executives: ${briefing.stakeholder_insights.executive_concerns}`,
    `Shareholders: ${briefing.stakeholder_insights.shareholder_dynamics}`,
    '',
    '=== KEY CONCERNS ===',
    ...briefing.key_concerns.map((kc, i) =>
      `${i+1}. ${kc.issue}\n   Why: ${kc.why_it_matters}\n   Watch: ${kc.watch_for}`
    ),
    '',
    '=== RECOMMENDATIONS ===',
    'Immediate Actions:',
    ...briefing.recommendations.immediate_actions.map((a, i) => `${i+1}. ${a}`),
    '',
    'Monitoring Focus:',
    ...briefing.recommendations.monitoring_focus.map((m, i) => `${i+1}. ${m}`),
    '',
    'Due Diligence Points:',
    ...briefing.recommendations.due_diligence_points.map((d, i) => `${i+1}. ${d}`),
    '',
    `Confidence: ${Math.round(briefing.confidence * 100)}%`,
    briefing.analysis_limitations ? `Limitations: ${briefing.analysis_limitations}` : '',
  ];
  return lines.filter(Boolean).join('\n');
}

// ============================================
// Text2Cypher 결과 표시 컴포넌트
// ============================================
function CypherResult({ result }: { result: Text2CypherResultV2 }) {
  // 복사용 텍스트 생성
  const copyText = [
    `Q: ${result.question}`,
    '',
    'Cypher Query:',
    result.cypher,
    '',
    result.explanation,
    '',
    'Answer:',
    result.answer,
    ...(result.results.length > 0
      ? ['', 'Results:', ...result.results.map((r) => JSON.stringify(r))]
      : []),
  ].join('\n');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-3"
    >
      {/* 질문 + 복사 버튼 */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <div className="w-5 h-5 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-[10px]">Q</span>
          </div>
          <p className="text-xs text-slate-300">{result.question}</p>
        </div>
        <CopyButton text={copyText} />
      </div>

      {/* Cypher 쿼리 코드 블록 */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">
            Cypher Query
          </span>
          <span className="text-[10px] text-purple-400">
            Auto-generated
          </span>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3 font-mono text-xs text-green-400 overflow-x-auto border border-white/5">
          <pre className="whitespace-pre-wrap break-all">{result.cypher}</pre>
        </div>
      </div>

      {/* 설명 */}
      <p className="text-[11px] text-slate-400 leading-relaxed">
        {result.explanation}
      </p>

      {/* 답변 */}
      <div className="bg-slate-800/30 rounded-xl p-3 border border-violet-500/10">
        <div className="flex items-start gap-2">
          <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
            style={{ background: 'linear-gradient(135deg, #a855f7, #6366f1)' }}>
            <SparkleIcon className="w-3 h-3 text-white" />
          </div>
          <p className="text-xs text-slate-200 leading-relaxed">{result.answer}</p>
        </div>
      </div>

      {/* 결과 테이블 (간단 표시) */}
      {result.results.length > 0 && (
        <div className="bg-slate-800/20 rounded-lg border border-white/5 overflow-hidden">
          <div className="px-3 py-1.5 bg-slate-800/40 border-b border-white/5">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
              Results ({result.results.length} rows)
            </span>
          </div>
          <div className="p-2 space-y-1 max-h-32 overflow-auto">
            {result.results.map((row, idx) => (
              <div
                key={idx}
                className="text-[10px] text-slate-400 font-mono bg-slate-800/30 rounded px-2 py-1"
              >
                {JSON.stringify(row)}
              </div>
            ))}
          </div>
        </div>
      )}

    </motion.div>
  );
}

// ============================================
// 메인 AICopilotPanel 컴포넌트
// ============================================
export default function AICopilotPanel() {
  const { state, toggleCopilot, currentDeal, currentCompany, currentCategories } = useRiskV2();
  const { activeView, selectedEntityId, selectedCategoryCode, selectedDealId, dealDetail } = state;

  // 로컬 상태
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [cypherResult, setCypherResult] = useState<Text2CypherResultV2 | null>(null);

  // 브리핑 상태
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [briefingError, setBriefingError] = useState<string | null>(null);

  // currentDeal 변경 시 briefing 자동 로드
  // currentDeal.name = "SK하이닉스 검토", targetCompanyName = "SK하이닉스"
  const dealCompanyName = currentDeal?.targetCompanyName || currentDeal?.id || '';
  useEffect(() => {
    if (!dealCompanyName) {
      setBriefing(null);
      setBriefingError(null);
      return;
    }

    let cancelled = false;
    setBriefingLoading(true);
    setBriefingError(null);

    riskApiV2.fetchBriefing(dealCompanyName).then(res => {
      if (!cancelled) {
        if (res.success && res.data) {
          setBriefing(res.data);
        } else {
          setBriefingError(res.error || 'Failed to load briefing');
        }
        setBriefingLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [dealCompanyName]);

  // Text2Cypher 쿼리 처리 (Real API)
  const handleSubmitQuery = useCallback(
    async (queryText: string) => {
      if (!queryText.trim()) return;
      setIsProcessing(true);
      setCypherResult(null);

      try {
        const res = await riskApiV2.queryNaturalLanguage(queryText);
        if (res.success && res.data) {
          setCypherResult(res.data);
        } else {
          setCypherResult({
            question: queryText,
            cypher: '',
            explanation: 'API 서버에 연결할 수 없습니다.',
            results: [],
            answer: res.error || 'API 서버가 실행 중인지 확인하세요. FastAPI 서버를 시작한 후 다시 시도하세요.',
            visualizationType: 'table',
            success: false,
          });
        }
      } catch (err) {
        console.error('[AICopilot] Query error:', err);
        setCypherResult({
          question: queryText,
          cypher: '',
          explanation: '오류가 발생했습니다.',
          results: [],
          answer: 'API 서버에 연결할 수 없습니다. 서버 상태를 확인하세요.',
          visualizationType: 'table',
          success: false,
        });
      } finally {
        setIsProcessing(false);
        setQuery('');
      }
    },
    []
  );

  // 예제 칩 클릭 핸들러
  const handleExampleClick = useCallback(
    (exampleQuery: string) => {
      setQuery(exampleQuery);
      handleSubmitQuery(exampleQuery);
    },
    [handleSubmitQuery]
  );

  // 키보드 전송
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmitQuery(query);
      }
    },
    [handleSubmitQuery, query]
  );

  return (
    <div className="flex flex-col h-full">
      {/* ======== 헤더 ======== */}
      <div className="flex justify-between items-center p-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <SparkleIcon className="w-4 h-4 text-purple-400" />
          <h3 className="text-sm font-semibold text-white">AI Investment Briefing</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleCopilot}
            className="p-1 rounded-lg hover:bg-white/5 transition-colors"
            aria-label="Close AI Copilot"
          >
            <CloseIcon className="w-4 h-4 text-slate-400 hover:text-white transition-colors" />
          </button>
        </div>
      </div>

      {/* ======== 브리핑 영역 (스크롤) ======== */}
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* 로딩 스켈레톤 (5섹션 구조와 동일한 레이아웃) */}
        {briefingLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            {/* 스피너 + 메시지 */}
            <div className="flex items-center gap-3 py-2">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="w-5 h-5 border-2 border-purple-500/30 border-t-purple-500 rounded-full flex-shrink-0"
              />
              <div>
                <p className="text-xs text-slate-300 font-medium">AI 브리핑 생성 중...</p>
                <p className="text-[10px] text-slate-500 mt-0.5">Neo4j 데이터를 분석하고 있습니다</p>
              </div>
            </div>
            {/* 1. Executive Summary 스켈레톤 */}
            <div className="rounded-xl overflow-hidden bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-500/10">
              <div className="p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-4 w-24 bg-white/10 rounded animate-pulse" />
                  <div className="h-4 w-16 bg-white/10 rounded-full animate-pulse" />
                </div>
                <div className="space-y-2">
                  <div className="h-3 w-full bg-white/8 rounded animate-pulse" />
                  <div className="h-3 w-[90%] bg-white/8 rounded animate-pulse" />
                  <div className="h-3 w-[70%] bg-white/8 rounded animate-pulse" />
                </div>
              </div>
            </div>
            {/* 2. Key Concerns 스켈레톤 */}
            <div className="space-y-3">
              <div className="h-3 w-24 bg-slate-700/50 rounded animate-pulse" />
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-slate-800/30 border border-red-500/10 rounded-lg p-3 space-y-2">
                  <div className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400/30 mt-1.5 flex-shrink-0" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3 w-[60%] bg-slate-700/40 rounded animate-pulse" />
                      <div className="h-2.5 w-full bg-slate-700/30 rounded animate-pulse" />
                      <div className="h-2.5 w-[80%] bg-amber-700/20 rounded animate-pulse" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {/* 3. Recommendations 스켈레톤 */}
            <div className="space-y-3">
              <div className="h-3 w-32 bg-slate-700/50 rounded animate-pulse" />
              <div className="bg-red-900/5 border border-red-500/10 rounded-lg p-3 space-y-2">
                <div className="h-2.5 w-28 bg-red-500/20 rounded animate-pulse" />
                <div className="h-2.5 w-[90%] bg-slate-700/30 rounded animate-pulse" />
                <div className="h-2.5 w-[75%] bg-slate-700/30 rounded animate-pulse" />
              </div>
              <div className="bg-amber-900/5 border border-amber-500/10 rounded-lg p-3 space-y-2">
                <div className="h-2.5 w-32 bg-amber-500/20 rounded animate-pulse" />
                <div className="h-2.5 w-[85%] bg-slate-700/30 rounded animate-pulse" />
                <div className="h-2.5 w-[70%] bg-slate-700/30 rounded animate-pulse" />
              </div>
            </div>
            {/* 4. Data Sources 스켈레톤 */}
            <div className="space-y-3">
              <div className="h-3 w-24 bg-slate-700/50 rounded animate-pulse" />
              <div className="grid grid-cols-2 gap-2">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="bg-slate-800/30 rounded-lg p-3 space-y-2">
                    <div className="h-2 w-12 bg-slate-700/40 rounded animate-pulse" />
                    <div className="h-5 w-8 bg-slate-700/30 rounded animate-pulse" />
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* 에러 상태 */}
        {briefingError && !briefingLoading && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 text-xs text-red-200">
            {briefingError}
          </div>
        )}

        {/* 브리핑 렌더링 */}
        {briefing && !briefingLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            {/* 1. Executive Summary (보라색 그라디언트) */}
            <div className="rounded-xl overflow-hidden"
              style={{ background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)' }}>
              <div className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-white">{briefing.company}</h4>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                      briefing.riskLevel === 'FAIL' ? 'bg-red-500 text-white' :
                      briefing.riskLevel === 'WARNING' ? 'bg-amber-500 text-white' :
                      'bg-green-500 text-white'
                    }`}>
                      {briefing.riskScore} / {briefing.riskLevel}
                    </span>
                  </div>
                  <CopyButton text={generateBriefingCopyText(briefing)} />
                </div>
                <p className="text-xs text-white/90 leading-relaxed">
                  {briefing.executive_summary}
                </p>
              </div>
            </div>

            {/* 2. Key Concerns (빨간 포인트) */}
            {briefing.key_concerns.length > 0 && (
              <div className="space-y-3">
                <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Key Concerns
                </h5>
                <div className="space-y-2">
                  {briefing.key_concerns.map((kc, idx) => (
                    <div key={idx} className="bg-slate-800/30 border border-red-500/20 rounded-lg p-3 space-y-1">
                      <div className="flex items-start gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
                        <div className="space-y-1 flex-1">
                          <p className="text-xs font-medium text-white">{kc.issue}</p>
                          <p className="text-[11px] text-slate-300 leading-relaxed">
                            <span className="text-slate-500">Why:</span> {kc.why_it_matters}
                          </p>
                          <p className="text-[11px] text-amber-300 leading-relaxed">
                            <span className="text-slate-500">Watch:</span> {kc.watch_for}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3. Recommendations (3단 색상) */}
            <div className="space-y-3">
              <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Recommendations
              </h5>
              <div className="grid gap-3">
                {/* Immediate Actions (빨강) */}
                {briefing.recommendations.immediate_actions.length > 0 && (
                  <div className="bg-red-900/10 border border-red-500/20 rounded-lg p-3 space-y-1.5">
                    <h6 className="text-[10px] font-semibold text-red-300 uppercase tracking-wider">
                      Immediate Actions
                    </h6>
                    <ul className="space-y-1">
                      {briefing.recommendations.immediate_actions.map((action, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-[11px] text-slate-300">
                          <span className="mt-1 w-1 h-1 rounded-full bg-red-400 flex-shrink-0" />
                          <span className="leading-relaxed">{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* Monitoring Focus (앰버) */}
                {briefing.recommendations.monitoring_focus.length > 0 && (
                  <div className="bg-amber-900/10 border border-amber-500/20 rounded-lg p-3 space-y-1.5"
                    style={{ borderColor: '#E2A855' }}>
                    <h6 className="text-[10px] font-semibold uppercase tracking-wider"
                      style={{ color: '#E2A855' }}>
                      Monitoring Focus
                    </h6>
                    <ul className="space-y-1">
                      {briefing.recommendations.monitoring_focus.map((mon, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-[11px] text-slate-300">
                          <span className="mt-1 w-1 h-1 rounded-full flex-shrink-0"
                            style={{ backgroundColor: '#E2A855' }} />
                          <span className="leading-relaxed">{mon}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* Due Diligence (파랑) */}
                {briefing.recommendations.due_diligence_points.length > 0 && (
                  <div className="bg-blue-900/10 border border-blue-500/20 rounded-lg p-3 space-y-1.5">
                    <h6 className="text-[10px] font-semibold text-blue-300 uppercase tracking-wider">
                      Due Diligence Points
                    </h6>
                    <ul className="space-y-1">
                      {briefing.recommendations.due_diligence_points.map((dd, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-[11px] text-slate-300">
                          <span className="mt-1 w-1 h-1 rounded-full bg-blue-400 flex-shrink-0" />
                          <span className="leading-relaxed">{dd}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* 4. Data Sources (2x2 그리드 + confidence) */}
            {briefing.dataSources && (
              <div className="space-y-3">
                <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Data Sources
                </h5>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-800/30 rounded-lg p-3 space-y-1">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">News</div>
                    <div className="text-lg font-bold text-white">{briefing.dataSources.newsCount}</div>
                  </div>
                  <div className="bg-slate-800/30 rounded-lg p-3 space-y-1">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">Disclosures</div>
                    <div className="text-lg font-bold text-white">{briefing.dataSources.disclosureCount}</div>
                  </div>
                  <div className="bg-slate-800/30 rounded-lg p-3 space-y-1">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">Related Co.</div>
                    <div className="text-lg font-bold text-white">{briefing.dataSources.relatedCompanyCount}</div>
                  </div>
                  <div className="bg-slate-800/30 rounded-lg p-3 space-y-1">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">Categories</div>
                    <div className="text-lg font-bold text-white">{briefing.dataSources.categoryCount}</div>
                  </div>
                </div>
                <div className="bg-purple-900/20 border border-purple-500/20 rounded-lg p-3 flex items-center justify-between">
                  <span className="text-xs text-slate-300">AI Confidence</span>
                  <span className="text-sm font-bold text-purple-300">{Math.round(briefing.confidence * 100)}%</span>
                </div>
              </div>
            )}

            {/* 5. Top Risk Drivers (dealDetail.categories에서) */}
            {dealDetail?.categories && (
              <div className="space-y-3">
                <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Top Risk Drivers
                </h5>
                <div className="space-y-2">
                  {dealDetail.categories
                    .filter(cat => cat.weightedScore > 0)
                    .sort((a, b) => b.weightedScore - a.weightedScore)
                    .slice(0, 5)
                    .map(cat => {
                      const pct = Math.min((cat.weightedScore / 20) * 100, 100);
                      return (
                        <div key={cat.code} className="space-y-1">
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="text-slate-300">{cat.name}</span>
                            <span className="text-slate-500">{cat.weightedScore.toFixed(1)}</span>
                          </div>
                          <div className="h-1.5 bg-slate-800/50 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${pct}%`,
                                background: pct > 75 ? '#ef4444' : pct > 50 ? '#f59e0b' : '#a855f7',
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* 딜 미선택 상태 */}
        {!briefing && !briefingLoading && !briefingError && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <SparkleIcon className="w-8 h-8 text-slate-600 mb-3" />
            <p className="text-sm text-slate-400 font-medium">딜을 선택하면 AI 브리핑이 시작됩니다</p>
            <p className="text-xs text-slate-500 mt-1">상단에서 딜을 선택하거나, 아래에서 질문을 입력하세요</p>
          </div>
        )}

        {/* 구분선 */}
        {briefing && (
          <div className="border-t border-white/5 pt-6" />
        )}

        {/* 예제 질문 칩 */}
        <div className="space-y-2">
          <h5 className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">
            Quick Queries
          </h5>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_QUERIES.map((example) => (
              <button
                key={example}
                onClick={() => handleExampleClick(example)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleExampleClick(example);
                  }
                }}
                tabIndex={0}
                className="px-2.5 py-1 text-[11px] text-slate-300 bg-slate-800/40
                  border border-white/5 rounded-full hover:bg-slate-700/40
                  hover:border-purple-500/30 hover:text-purple-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500/50
                  focus-visible:border-purple-500/40 focus-visible:bg-slate-700/40
                  transition-all duration-200"
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* Text2Cypher 결과 */}
        <AnimatePresence>
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-purple-500/30 border-t-purple-500 rounded-full"
                />
                <span>Cypher 쿼리를 생성하고 있습니다...</span>
              </div>
              {/* 스켈레톤 */}
              <div className="space-y-2">
                <div className="h-16 bg-slate-800/30 rounded-lg animate-pulse" />
                <div className="h-8 bg-slate-800/20 rounded-lg animate-pulse w-3/4" />
              </div>
            </motion.div>
          )}

          {cypherResult && !isProcessing && (
            <CypherResult result={cypherResult} />
          )}
        </AnimatePresence>
      </div>

      {/* ======== Text2Cypher 입력 (하단 고정) ======== */}
      <div className="border-t border-white/5 p-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="예: SK하이닉스의 법률 리스크는?"
              className="w-full bg-slate-800/40 border border-white/5 rounded-xl px-3 py-2.5
                text-xs text-slate-200 placeholder:text-slate-500
                focus:outline-none focus:border-purple-500/40 focus:ring-1 focus:ring-purple-500/20
                transition-all duration-200"
              disabled={isProcessing}
            />
          </div>
          <button
            onClick={() => handleSubmitQuery(query)}
            disabled={isProcessing || !query.trim()}
            className="flex items-center justify-center w-9 h-9 rounded-xl
              transition-all duration-200 flex-shrink-0
              disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
            }}
            aria-label="Send query"
          >
            <SendIcon className="w-4 h-4 text-white" />
          </button>
        </div>
        <p className="text-[10px] text-slate-600 mt-1.5 px-1">
          자연어로 Graph DB를 질문하세요
        </p>
      </div>
    </div>
  );
}
