/**
 * Step 3. 리스크 모니터링 시스템 - Text2Cypher 자연어 질의
 * 자연어 → Neo4j Cypher 쿼리 자동 생성 및 실행
 */

import React, { useState } from 'react';
import { riskApi } from '../api';
import { Text2CypherResult } from '../types';

const EXAMPLE_QUESTIONS = [
  '리스크가 가장 높은 기업은?',
  '공급망 리스크가 있는 기업 목록',
  'SK하이닉스에 리스크를 전파하는 기업은?',
  '특허 소송이 있는 기업은?',
];

const Text2CypherInput: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<Text2CypherResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 질의 실행
  const handleQuery = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await riskApi.queryWithNaturalLanguage(question);
      if (response.success) {
        setResult(response.data);
      } else {
        setError(response.error || '질의 실패');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류');
    } finally {
      setLoading(false);
    }
  };

  // 예시 질문 클릭
  const handleExampleClick = (exampleQuestion: string) => {
    setQuestion(exampleQuestion);
    setResult(null);
    setError(null);
  };

  // Enter 키 처리
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  return (
    <div className="space-y-4">
      {/* 입력 영역 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="자연어로 질문하세요... (예: 리스크가 가장 높은 기업은?)"
          className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          onClick={handleQuery}
          disabled={loading || !question.trim()}
          className={`px-6 py-2 rounded-lg font-medium text-sm transition-all ${
            loading || !question.trim()
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              분석 중...
            </span>
          ) : (
            '검색'
          )}
        </button>
      </div>

      {/* 예시 질문 */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-slate-400">예시:</span>
        {EXAMPLE_QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleExampleClick(q)}
            className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1 rounded-full transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <div className="text-sm text-red-300">
            <span className="font-semibold">⚠️ 오류:</span> {error}
          </div>
        </div>
      )}

      {/* 결과 */}
      {result && (
        <div className="space-y-4">
          {/* AI 답변 */}
          <div className="p-4 bg-blue-900/20 border border-blue-700/30 rounded-lg">
            <div className="text-sm font-semibold text-blue-300 mb-2">
              🤖 AI 답변:
            </div>
            <div className="text-slate-200">{result.answer}</div>
          </div>

          {/* 생성된 Cypher 쿼리 */}
          <div className="p-4 bg-slate-700/30 border border-slate-600 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-semibold text-slate-400">
                생성된 Cypher 쿼리:
              </div>
              <div className="text-xs text-slate-500">{result.explanation}</div>
            </div>
            <pre className="text-xs bg-slate-900 text-green-400 p-3 rounded overflow-x-auto">
              {result.cypher}
            </pre>
          </div>

          {/* 조회 결과 */}
          {result.results && result.results.length > 0 && (
            <div className="p-4 bg-slate-700/30 border border-slate-600 rounded-lg">
              <div className="text-xs font-semibold text-slate-400 mb-3">
                조회 결과 ({result.results.length}건):
              </div>
              <div className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                {result.results.map((item, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-800 p-3 rounded text-sm"
                  >
                    <pre className="text-slate-300 whitespace-pre-wrap">
                      {JSON.stringify(item, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 안내 메시지 (결과 없을 때) */}
      {!result && !error && !loading && (
        <div className="text-center py-8 text-slate-500">
          <div className="text-4xl mb-2">💬</div>
          <div className="text-sm">
            자연어로 Neo4j 그래프를 질의하세요
          </div>
        </div>
      )}
    </div>
  );
};

export default Text2CypherInput;
