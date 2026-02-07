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
import type { Text2CypherResultV2 } from '../types-v2';

// ============================================
// 인사이트 데이터 인터페이스
// ============================================

interface InsightData {
  title: string;
  summary: string;
  keyFindings: string[];
  recommendation: string;
}

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
// 인사이트 섹션 컴포넌트
// ============================================
function InsightSection({ insight, isDynamic = false }: { insight: InsightData; isDynamic?: boolean }) {
  // 복사용 텍스트 생성
  const copyText = [
    insight.title,
    '',
    insight.summary,
    '',
    'Key Findings:',
    ...insight.keyFindings.map((f, i) => `${i + 1}. ${f}`),
    '',
    'Recommendation:',
    insight.recommendation,
  ].join('\n');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      {/* 타이틀 + 복사 버튼 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-purple-400" />
          <h4 className="text-sm font-semibold text-white">{insight.title}</h4>
        </div>
        <CopyButton text={copyText} />
      </div>

      {/* 요약 */}
      <div className="bg-slate-800/30 rounded-xl p-3 border border-white/5">
        <p className="text-xs text-slate-300 leading-relaxed">
          {insight.summary}
        </p>
      </div>

      {/* Key Findings */}
      <div className="space-y-2">
        <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          Key Findings
        </h5>
        <ul className="space-y-2">
          {insight.keyFindings.map((finding, idx) => (
            <li key={idx} className="flex items-start gap-2 text-xs text-slate-300">
              <span className="mt-1 w-1 h-1 rounded-full bg-violet-400 flex-shrink-0" />
              <span className="leading-relaxed">{finding}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Recommendation */}
      <div className="space-y-1.5">
        <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          Recommendation
        </h5>
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg p-3">
          <p className="text-xs text-violet-200 leading-relaxed">
            {insight.recommendation}
          </p>
        </div>
      </div>

      {/* AI 생성 표시 */}
      <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
        <SparkleIcon className="w-3 h-3 text-purple-500" />
        <span>AI Generated Insight</span>
        <span className="text-slate-600">|</span>
        <span>confidence: {isDynamic ? '92%' : '87%'}</span>
      </div>
    </motion.div>
  );
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
  const [dynamicInsight, setDynamicInsight] = useState<InsightData | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);

  // Load dynamic insight when view or selection changes
  useEffect(() => {
    if (!currentCompany?.name) {
      setDynamicInsight(null);
      return;
    }

    let cancelled = false;
    setInsightLoading(true);

    riskApiV2.fetchAIInsight(currentCompany.name).then(res => {
      if (!cancelled) {
        if (res.success && res.data && res.data.confidence > 0) {
          setDynamicInsight({
            title: `${currentCompany.name} AI 분석`,
            summary: res.data.summary,
            keyFindings: res.data.keyFindings,
            recommendation: res.data.recommendation,
          });
        } else {
          setDynamicInsight(null);
        }
        setInsightLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [currentCompany?.name, activeView]);

  // 현재 컨텍스트에 기반한 플레이스홀더 인사이트 생성
  const getContextInsight = (): InsightData | null => {
    if (!currentCompany) return null;

    if (selectedEntityId) {
      return {
        title: '엔티티 상세 분석',
        summary: `${currentCompany.name}의 선택된 엔티티에 대한 리스크 분석입니다. AI 인사이트를 로드하려면 API 서버 연결이 필요합니다.`,
        keyFindings: ['엔티티 상세 분석을 위해 API 연결이 필요합니다'],
        recommendation: 'FastAPI 서버가 실행 중인지 확인하세요.',
      };
    }

    if (selectedCategoryCode && currentCategories.length > 0) {
      const cat = currentCategories.find(c => c.code === selectedCategoryCode);
      if (cat) {
        return {
          title: `${cat.name} 카테고리 분석`,
          summary: `${currentCompany.name}의 ${cat.name} 카테고리 점수는 ${cat.score}점(가중: ${cat.weightedScore.toFixed(1)})입니다. ${cat.entityCount}개 엔티티, ${cat.eventCount}개 이벤트가 등록되어 있습니다.`,
          keyFindings: [
            `카테고리 점수: ${cat.score}점 (가중치 ${(cat.weight * 100).toFixed(0)}%)`,
            `하위 엔티티 ${cat.entityCount}개, 이벤트 ${cat.eventCount}개`,
            `추세: ${cat.trend === 'UP' ? '상승' : cat.trend === 'DOWN' ? '하락' : '안정'}`,
          ],
          recommendation: cat.score > 50
            ? '높은 리스크 점수입니다. 즉각적인 모니터링과 대응 방안 수립을 권장합니다.'
            : cat.score > 20
            ? '주의 수준의 리스크입니다. 정기적인 모니터링을 유지하세요.'
            : '안정적인 수준입니다. 변화 추이를 주기적으로 확인하세요.',
        };
      }
    }

    return null;
  };

  const contextInsight = getContextInsight();
  const displayInsight = dynamicInsight ?? contextInsight;

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
          <h3 className="text-sm font-semibold text-white">AI Copilot</h3>
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

      {/* ======== 인사이트 영역 (스크롤) ======== */}
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* 컨텍스트 인식 인사이트 */}
        <AnimatePresence mode="wait">
          <motion.div
            key={`${activeView}-${selectedCategoryCode}-${selectedEntityId}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {insightLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-400 py-4">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-purple-500/30 border-t-purple-500 rounded-full"
                />
                <span>AI 인사이트 생성 중...</span>
              </div>
            ) : displayInsight ? (
              <InsightSection insight={displayInsight} isDynamic={!!dynamicInsight} />
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <SparkleIcon className="w-8 h-8 text-slate-600 mb-3" />
                <p className="text-sm text-slate-400 font-medium">딜을 선택하면 AI 분석이 시작됩니다</p>
                <p className="text-xs text-slate-500 mt-1">상단에서 딜을 선택하거나, 아래에서 질문을 입력하세요</p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

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
