"""
AI 서비스 v2 - OpenAI 실제 연동
Risk Monitoring System v2.3

7대 AI 기능:
1. analyze_news - 뉴스 자동 분석
2. summarize_risk - 리스크 요약
3. text_to_cypher - 자연어 → Cypher 변환
4. interpret_simulation - 시뮬레이션 해석
5. explain_propagation - 전이 경로 설명
6. generate_action_guide - RM/OPS 대응 가이드
7. generate_comprehensive_insight - 종합 인사이트 분석 (NEW)
   - 리스크 점수는 알고리즘으로 계산됨, AI는 맥락적 해석 제공
   - 업계 컨텍스트, 신호 교차 분석, 패턴 인식, 권고사항 생성
"""

import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional
from functools import lru_cache
from datetime import datetime, timedelta

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI 라이브러리 미설치. pip install openai")

from dotenv import load_dotenv
load_dotenv('.env.local')

logger = logging.getLogger(__name__)


class AIServiceV2:
    """6대 AI 기능 구현 (OpenAI 연동)"""

    def __init__(self):
        self._client = None
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", 2000))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", 0.7))

        # 간단한 메모리 캐시 (TTL 1시간)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = int(os.getenv("OPENAI_CACHE_TTL_SECONDS", 3600))

    @property
    def client(self) -> Optional[OpenAI]:
        """OpenAI 클라이언트 (지연 초기화)"""
        if self._client is None and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._client = OpenAI(api_key=api_key)
        return self._client

    @property
    def is_available(self) -> bool:
        """AI 서비스 사용 가능 여부"""
        return OPENAI_AVAILABLE and self.client is not None

    @property
    def enrichment_enabled(self) -> bool:
        """AI enrichment 활성화 여부 (환경변수로 제어)"""
        return os.getenv("AI_ENRICHMENT_ENABLED", "false").lower() == "true"

    def _get_cache_key(self, func_name: str, params: dict) -> str:
        """캐시 키 생성"""
        param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(f"{func_name}:{param_str}".encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """캐시에서 조회"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if datetime.now() < entry["expires"]:
                return entry["data"]
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """캐시에 저장"""
        self._cache[cache_key] = {
            "data": data,
            "expires": datetime.now() + timedelta(seconds=self._cache_ttl)
        }

    def _call_gpt(self, system_prompt: str, user_prompt: str, use_json: bool = True) -> str:
        """GPT API 호출"""
        if not self.is_available:
            raise RuntimeError("OpenAI 서비스 사용 불가")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        if use_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # ========================================
    # 1. 뉴스 자동 분석
    # ========================================
    def analyze_news(self, news_content: str, title: str = "") -> Dict[str, Any]:
        """뉴스 본문 → 리스크 분석"""

        # 캐시 확인
        cache_key = self._get_cache_key("analyze_news", {"content": news_content[:200]})
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if not self.is_available:
            return self._fallback_analyze_news(news_content, title)

        system_prompt = """당신은 금융 리스크 분석 전문가입니다.
주어진 뉴스 기사를 분석하여 정확히 다음 JSON 형식으로 응답하세요:
{
  "severity": 1-5 (1=낮음, 5=매우높음),
  "category": "financial|legal|governance|supply_chain|market|reputation|operational|macro",
  "affected_companies": ["회사명1", "회사명2"],
  "summary": "한 줄 요약 (30자 이내)",
  "risk_factors": ["리스크1", "리스크2"],
  "confidence": 0.0-1.0
}"""

        user_prompt = f"제목: {title}\n\n본문:\n{news_content[:1500]}"

        try:
            result = self._call_gpt(system_prompt, user_prompt)
            parsed = json.loads(result)
            self._set_cache(cache_key, parsed)
            return parsed
        except Exception as e:
            logger.error(f"뉴스 분석 실패: {e}")
            return self._fallback_analyze_news(news_content, title)

    def _fallback_analyze_news(self, content: str, title: str) -> Dict[str, Any]:
        """뉴스 분석 폴백"""
        text = f"{title} {content}".lower()

        # 키워드 기반 간단 분석
        severity = 3
        category = "operational"

        if any(kw in text for kw in ["소송", "검찰", "기소", "조사"]):
            severity = 4
            category = "legal"
        elif any(kw in text for kw in ["손실", "적자", "하락"]):
            severity = 3
            category = "financial"
        elif any(kw in text for kw in ["공급", "부품", "납품"]):
            category = "supply_chain"

        return {
            "severity": severity,
            "category": category,
            "affected_companies": [],
            "summary": title[:30] if title else "분석 불가",
            "risk_factors": ["자동 분석 필요"],
            "confidence": 0.3
        }

    # ========================================
    # 2. 리스크 요약
    # ========================================
    def summarize_risk(self, deal_data: Dict[str, Any]) -> Dict[str, Any]:
        """딜 데이터 → 리스크 요약"""

        if not self.is_available:
            return self._fallback_summarize_risk(deal_data)

        system_prompt = """당신은 PE/IB 심사역입니다.
주어진 딜 데이터를 분석하여 정확히 다음 JSON 형식으로 응답하세요:
{
  "one_liner": "한 문장 핵심 요약 (50자 이내)",
  "key_risks": ["핵심 리스크1", "핵심 리스크2", "핵심 리스크3"],
  "recommendation": "권장 행동 (한 문장)",
  "confidence": 0.0-1.0
}"""

        try:
            result = self._call_gpt(system_prompt, json.dumps(deal_data, ensure_ascii=False))
            return json.loads(result)
        except Exception as e:
            logger.error(f"리스크 요약 실패: {e}")
            return self._fallback_summarize_risk(deal_data)

    def _fallback_summarize_risk(self, deal_data: Dict) -> Dict[str, Any]:
        """리스크 요약 폴백"""
        name = deal_data.get("name", "대상 기업")
        score = deal_data.get("score", 50)

        status = "정상" if score <= 40 else "주의" if score <= 70 else "위험"

        return {
            "one_liner": f"{name}은 현재 {status} 상태입니다. 지속 모니터링 필요.",
            "key_risks": ["데이터 부족으로 상세 분석 불가"],
            "recommendation": "추가 정보 수집 후 재분석 필요",
            "confidence": 0.3
        }

    # ========================================
    # 3. Text2Cypher
    # ========================================
    def text_to_cypher(self, natural_query: str) -> Dict[str, Any]:
        """자연어 → Cypher 쿼리 변환 (v5 5-Node 스키마)"""

        if not self.is_available:
            return self._fallback_text_to_cypher(natural_query)

        system_prompt = """당신은 Neo4j Cypher 전문가입니다.
자연어 질문을 Cypher 쿼리로 변환하세요.

=== 그래프 스키마 (5-Node Hierarchy) ===

노드:
- (:Deal {name, targetCompanyName, analyst, status, stage})
- (:Company {name, sector, market, totalRiskScore, directScore, propagatedScore, riskLevel})
- (:RiskCategory {code, name, riskScore, weight, weightedScore, eventCount})
  - code: SHARE, EXEC, CREDIT, LEGAL, GOV, OPS, AUDIT, ESG, SUPPLY, OTHER
- (:RiskEntity {name, type, position, description, riskScore})
  - type: PERSON, SHAREHOLDER, CASE, ISSUE
- (:RiskEvent {title, type, severity, score, source, publishedAt, summary})
  - type: NEWS, DISCLOSURE, ISSUE

관계:
- (Deal)-[:TARGET]->(Company)         -- 딜의 메인 기업
- (Company)-[:HAS_CATEGORY]->(RiskCategory) -- 기업의 10개 리스크 카테고리
- (Company)-[:HAS_RELATED]->(Company)       -- 관련기업
- (RiskCategory)-[:HAS_ENTITY]->(RiskEntity) -- 카테고리 내 엔티티
- (RiskEntity)-[:HAS_EVENT]->(RiskEvent)     -- 엔티티의 이벤트/뉴스

규칙:
1. 읽기 전용 쿼리만 (MATCH, RETURN, WHERE, ORDER BY, WITH, OPTIONAL MATCH)
2. DELETE, CREATE, SET, MERGE, REMOVE, DROP 절대 금지
3. LIMIT 20 기본 적용
4. 한국어 회사명 사용 (예: 'SK하이닉스', '삼성전자')

정확히 다음 JSON 형식으로 응답:
{
  "cypher": "MATCH ... RETURN ...",
  "explanation": "쿼리 설명 (한국어)"
}"""

        try:
            result = self._call_gpt(system_prompt, natural_query)
            parsed = json.loads(result)

            # 보안: 위험한 키워드 검사
            cypher = parsed.get("cypher", "")
            self._validate_cypher_safety(cypher)

            return parsed
        except ValueError as e:
            return {"cypher": None, "explanation": str(e), "error": True}
        except Exception as e:
            logger.error(f"Text2Cypher 실패: {e}")
            return self._fallback_text_to_cypher(natural_query)

    def generate_answer(self, question: str, cypher: str, results: list) -> str:
        """Cypher 쿼리 결과를 자연어 답변으로 변환"""
        if not self.is_available:
            return self._fallback_answer(question, results)

        results_str = json.dumps(results[:10], ensure_ascii=False, default=str) if results else "결과 없음"

        system_prompt = """당신은 투자 리스크 분석 어시스턴트입니다.
Neo4j 그래프 DB 쿼리 결과를 바탕으로 사용자 질문에 대한 명확한 한국어 답변을 작성하세요.

규칙:
1. 결과 데이터를 분석하여 핵심 인사이트를 추출
2. 간결하고 실용적인 답변 (3-5문장)
3. 숫자/점수가 있으면 구체적으로 인용
4. 결과가 없으면 "해당 데이터를 찾을 수 없습니다"라고 안내
5. 순수 텍스트만 반환 (JSON 아님)"""

        user_msg = f"질문: {question}\nCypher: {cypher}\n결과: {results_str}"

        try:
            return self._call_gpt(system_prompt, user_msg)
        except Exception as e:
            logger.error(f"답변 생성 실패: {e}")
            return self._fallback_answer(question, results)

    def _fallback_answer(self, question: str, results: list) -> str:
        """AI 없을 때 결과 기반 간단 답변"""
        if not results:
            return "해당 조건에 맞는 데이터를 찾을 수 없습니다. 질문을 다시 확인해주세요."
        count = len(results)
        return f"총 {count}건의 결과를 찾았습니다. 상세 내용은 아래 결과 테이블을 확인하세요."

    def _validate_cypher_safety(self, cypher: str):
        """Cypher 쿼리 안전성 검증"""
        dangerous_keywords = ["DELETE", "CREATE", "SET ", "MERGE", "REMOVE", "DROP", "DETACH"]
        cypher_upper = cypher.upper()

        for keyword in dangerous_keywords:
            if keyword in cypher_upper:
                raise ValueError(f"위험한 쿼리 감지: {keyword} 키워드 사용 불가")

    def _fallback_text_to_cypher(self, query: str) -> Dict[str, Any]:
        """Text2Cypher 폴백 (v5 5-Node 스키마)"""
        query_lower = query.lower()

        if "법률" in query_lower or "legal" in query_lower:
            return {
                "cypher": "MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory {code: 'LEGAL'}) RETURN c.name, rc.riskScore, rc.weightedScore, rc.eventCount ORDER BY rc.riskScore DESC LIMIT 20",
                "explanation": "법률(LEGAL) 카테고리 리스크 점수 조회"
            }
        elif "공급" in query_lower or "supply" in query_lower:
            return {
                "cypher": "MATCH (c:Company)-[:HAS_RELATED]->(rc:Company) RETURN c.name AS main, rc.name AS related, rc.totalRiskScore ORDER BY rc.totalRiskScore DESC LIMIT 20",
                "explanation": "관련기업(공급망) 리스크 전이 관계 조회"
            }
        elif "고위험" in query_lower or "위험" in query_lower or "리스크" in query_lower:
            return {
                "cypher": "MATCH (c:Company) RETURN c.name, c.totalRiskScore, c.riskLevel, c.directScore, c.propagatedScore ORDER BY c.totalRiskScore DESC LIMIT 20",
                "explanation": "기업별 리스크 점수 조회"
            }
        elif "임원" in query_lower or "경영" in query_lower or "exec" in query_lower:
            return {
                "cypher": "MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory {code: 'EXEC'})-[:HAS_ENTITY]->(re:RiskEntity) RETURN c.name, re.name, re.type, re.position, re.riskScore ORDER BY re.riskScore DESC LIMIT 20",
                "explanation": "경영진(EXEC) 관련 엔티티 조회"
            }
        elif "주주" in query_lower or "share" in query_lower:
            return {
                "cypher": "MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory {code: 'SHARE'})-[:HAS_ENTITY]->(re:RiskEntity) RETURN c.name, re.name, re.type, re.riskScore ORDER BY re.riskScore DESC LIMIT 20",
                "explanation": "주주(SHARE) 관련 엔티티 조회"
            }
        else:
            return {
                "cypher": "MATCH (d:Deal)-[:TARGET]->(c:Company) OPTIONAL MATCH (c)-[:HAS_CATEGORY]->(rc:RiskCategory) RETURN d.name AS deal, c.name AS company, c.totalRiskScore, collect(rc.code + ': ' + toString(rc.riskScore))[..5] AS topCategories LIMIT 20",
                "explanation": "딜 및 메인기업 리스크 요약 조회"
            }

    # ========================================
    # 4. 시뮬레이션 해석
    # ========================================
    def interpret_simulation(self, simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """시뮬레이션 결과 → 비즈니스 해석"""

        if not self.is_available:
            return self._fallback_interpret_simulation(simulation_result)

        system_prompt = """당신은 시나리오 분석 전문가입니다.
시뮬레이션 결과를 비즈니스 맥락에서 해석하세요.

정확히 다음 JSON 형식으로 응답:
{
  "impact_summary": "영향 요약 (50자 이내)",
  "most_affected": "가장 큰 영향을 받는 영역",
  "action_items": ["조치1", "조치2", "조치3"],
  "timeline": "예상 영향 기간 (예: 1-2주)"
}"""

        try:
            result = self._call_gpt(system_prompt, json.dumps(simulation_result, ensure_ascii=False))
            return json.loads(result)
        except Exception as e:
            logger.error(f"시뮬레이션 해석 실패: {e}")
            return self._fallback_interpret_simulation(simulation_result)

    def _fallback_interpret_simulation(self, result: Dict) -> Dict[str, Any]:
        """시뮬레이션 해석 폴백"""
        return {
            "impact_summary": "시뮬레이션 결과에 대한 상세 분석이 필요합니다.",
            "most_affected": "데이터 분석 필요",
            "action_items": ["결과 검토", "담당자 논의", "대응 방안 수립"],
            "timeline": "분석 필요"
        }

    # ========================================
    # 5. 전이 경로 설명
    # ========================================
    def explain_propagation(self, propagation_data: Dict[str, Any]) -> Dict[str, Any]:
        """리스크 전이 경로 → 비즈니스 설명"""

        if not self.is_available:
            return self._fallback_explain_propagation(propagation_data)

        system_prompt = """당신은 공급망 리스크 분석가입니다.
리스크 전이 경로를 비즈니스 맥락에서 설명하세요.

정확히 다음 JSON 형식으로 응답:
{
  "pathway_explanation": "전이 경로 설명 (100자 이내)",
  "critical_nodes": ["핵심 노드1", "핵심 노드2"],
  "risk_level": "high|medium|low",
  "mitigation": "완화 방안 (50자 이내)"
}"""

        try:
            result = self._call_gpt(system_prompt, json.dumps(propagation_data, ensure_ascii=False))
            return json.loads(result)
        except Exception as e:
            logger.error(f"전이 경로 설명 실패: {e}")
            return self._fallback_explain_propagation(propagation_data)

    def _fallback_explain_propagation(self, data: Dict) -> Dict[str, Any]:
        """전이 경로 설명 폴백"""
        propagators = data.get("topPropagators", [])
        nodes = [p.get("company", "") for p in propagators[:2]]

        return {
            "pathway_explanation": "공급망을 통해 리스크가 전이되고 있습니다. 상세 분석이 필요합니다.",
            "critical_nodes": nodes if nodes else ["분석 필요"],
            "risk_level": "medium",
            "mitigation": "공급망 다변화 및 모니터링 강화 필요"
        }

    # ========================================
    # 6. 대응 전략 (RM/OPS 가이드)
    # ========================================
    def generate_action_guide(self, deal_data: Dict[str, Any], signal_type: str = "OPERATIONAL") -> Dict[str, Any]:
        """상황별 RM/OPS 가이드 생성"""

        if not self.is_available:
            return self._fallback_action_guide(deal_data, signal_type)

        system_prompt = f"""당신은 PE/IB 리스크 관리 전문가입니다.
{signal_type} 상황에서의 대응 가이드를 작성하세요.

정확히 다음 JSON 형식으로 응답:
{{
  "rm_guide": {{
    "summary": "RM 대응 요약 (30자 이내)",
    "todo_list": ["할일1", "할일2", "할일3"],
    "talking_points": ["고객 대화 포인트1", "포인트2"]
  }},
  "ops_guide": {{
    "summary": "OPS 대응 요약 (30자 이내)",
    "todo_list": ["할일1", "할일2", "할일3"],
    "financial_impact": "재무 영향 분석 (한 문장)"
  }},
  "urgency": "immediate|within_24h|within_week"
}}"""

        try:
            result = self._call_gpt(system_prompt, json.dumps(deal_data, ensure_ascii=False))
            return json.loads(result)
        except Exception as e:
            logger.error(f"대응 가이드 생성 실패: {e}")
            return self._fallback_action_guide(deal_data, signal_type)

    def _fallback_action_guide(self, deal_data: Dict, signal_type: str) -> Dict[str, Any]:
        """대응 가이드 폴백"""
        guides = {
            "LEGAL_CRISIS": {
                "rm_guide": {
                    "summary": "법률 리스크 대응 필요",
                    "todo_list": ["고객 면담", "리스크 공유", "법무 검토"],
                    "talking_points": ["현재 상황 설명", "대응 방안 공유"]
                },
                "ops_guide": {
                    "summary": "충당금 및 계약 검토",
                    "todo_list": ["EOD 준비", "자산 점검", "법무법인 협의"],
                    "financial_impact": "손해배상 시나리오별 영향 분석 필요"
                },
                "urgency": "immediate"
            },
            "MARKET_CRISIS": {
                "rm_guide": {
                    "summary": "시장 리스크 모니터링 강화",
                    "todo_list": ["시장 동향 분석", "유동성 확보", "헤지 검토"],
                    "talking_points": ["시장 전망 공유", "대응 전략 논의"]
                },
                "ops_guide": {
                    "summary": "LTV 및 담보 재검토",
                    "todo_list": ["담보 가치 재평가", "Covenant 점검", "비상 시나리오"],
                    "financial_impact": "시장 변동에 따른 포트폴리오 영향 분석 필요"
                },
                "urgency": "within_24h"
            }
        }

        return guides.get(signal_type, {
            "rm_guide": {
                "summary": "정기 모니터링 수행",
                "todo_list": ["현황 점검", "보고서 검토", "이슈 추적"],
                "talking_points": ["정기 업데이트 공유"]
            },
            "ops_guide": {
                "summary": "운영 현황 점검",
                "todo_list": ["KPI 점검", "리스크 지표 확인", "보고서 작성"],
                "financial_impact": "특이사항 없음"
            },
            "urgency": "within_week"
        })


    # ========================================
    # 7. 종합 인사이트 분석 (NEW)
    # ========================================
    def generate_comprehensive_insight(self, deal_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        딜 대상에 대한 종합 인사이트 생성

        리스크 점수는 이미 알고리즘으로 계산되어 있으므로,
        AI는 맥락적 해석, 패턴 인식, 교차 분석, 권고사항을 제공

        Args:
            deal_context: {
                "company": str,              # 기업명
                "sector": str,               # 섹터
                "riskScore": int,            # 현재 리스크 점수 (알고리즘 계산)
                "riskLevel": str,            # PASS/WARNING/FAIL
                "signals": [                 # 최근 수집된 신호들
                    {
                        "type": "news|disclosure",
                        "category": str,
                        "title": str,
                        "score": int,
                        "date": str
                    }
                ],
                "executives": [              # 임원 목록
                    {"name": str, "position": str}
                ],
                "shareholders": [            # 주주 목록
                    {"name": str, "shareRatio": float}
                ],
                "relatedCompanies": [        # 관계기업
                    {"name": str, "relation": str}
                ],
                "categoryScores": {          # 카테고리별 점수
                    "financial": int,
                    "legal": int,
                    "governance": int,
                    "operational": int,
                    "market": int
                }
            }

        Returns:
            종합 인사이트 결과
        """

        if not self.is_available:
            return self._fallback_comprehensive_insight(deal_context)

        system_prompt = """당신은 PE/IB 딜 심사 전문가이자 리스크 분석가입니다.

주어진 딜 대상의 데이터를 종합 분석하여 **인사이트**를 제공하세요.
⚠️ 리스크 점수는 이미 알고리즘으로 계산되어 있습니다. 점수 재계산이 아닌 **맥락적 해석**에 집중하세요.

다음 JSON 형식으로 응답하세요:
{
  "executive_summary": "현재 상황 핵심 요약 (2-3문장, 점수가 아닌 의미 중심)",

  "context_analysis": {
    "industry_context": "해당 기업의 업계 상황 맥락 (시장 트렌드, 업황 등)",
    "timing_significance": "현 시점의 신호들이 갖는 시기적 의미"
  },

  "cross_signal_analysis": {
    "patterns_detected": ["감지된 패턴1", "패턴2"],
    "correlations": "서로 다른 신호들 간의 연관성 분석",
    "anomalies": "이상 징후나 주목할 점"
  },

  "stakeholder_insights": {
    "executive_concerns": "임원/지배구조 관련 시사점 (해당시)",
    "shareholder_dynamics": "주주 구성/변동 관련 시사점 (해당시)"
  },

  "key_concerns": [
    {
      "issue": "우려 사항",
      "why_it_matters": "왜 중요한지",
      "watch_for": "앞으로 주시해야 할 점"
    }
  ],

  "recommendations": {
    "immediate_actions": ["즉시 필요한 조치1", "조치2"],
    "monitoring_focus": ["집중 모니터링 항목1", "항목2"],
    "due_diligence_points": ["추가 실사 필요 항목1", "항목2"]
  },

  "confidence": 0.0-1.0,
  "analysis_limitations": "분석의 한계점이나 추가로 필요한 정보"
}"""

        user_prompt = f"""딜 대상 분석 요청:

기업명: {deal_context.get('company', 'N/A')}
섹터: {deal_context.get('sector', 'N/A')}
현재 리스크 점수: {deal_context.get('riskScore', 'N/A')} (알고리즘 산출)
리스크 등급: {deal_context.get('riskLevel', 'N/A')}

카테고리별 점수 (알고리즘 산출):
{json.dumps(deal_context.get('categoryScores', {}), ensure_ascii=False, indent=2)}

최근 신호들:
{json.dumps(deal_context.get('signals', [])[:10], ensure_ascii=False, indent=2)}

임원 현황:
{json.dumps(deal_context.get('executives', [])[:5], ensure_ascii=False, indent=2)}

주요 주주:
{json.dumps(deal_context.get('shareholders', [])[:5], ensure_ascii=False, indent=2)}

관계 기업:
{json.dumps(deal_context.get('relatedCompanies', [])[:5], ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 종합 인사이트를 제공해주세요.
점수 계산이 아닌, 맥락적 해석과 실무적 시사점에 집중해주세요."""

        try:
            result = self._call_gpt(system_prompt, user_prompt)
            parsed = json.loads(result)
            return parsed
        except Exception as e:
            logger.error(f"종합 인사이트 생성 실패: {e}")
            return self._fallback_comprehensive_insight(deal_context)

    def _fallback_comprehensive_insight(self, deal_context: Dict) -> Dict[str, Any]:
        """종합 인사이트 폴백 (AI 미사용 시)"""
        company = deal_context.get('company', '대상 기업')
        score = deal_context.get('riskScore', 50)
        level = deal_context.get('riskLevel', 'WARNING')
        signals = deal_context.get('signals', [])
        category_scores = deal_context.get('categoryScores', {})

        # 가장 높은 카테고리 찾기
        max_category = max(category_scores, key=category_scores.get) if category_scores else "operational"
        max_score = category_scores.get(max_category, 0)

        # 최근 신호 패턴 분석 (간단한 룰 기반)
        recent_categories = [s.get('category', '') for s in signals[:10]]
        category_counts = {}
        for cat in recent_categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1

        patterns = []
        if category_counts.get('legal', 0) >= 2:
            patterns.append("법적 이슈 신호 집중 발생")
        if category_counts.get('governance', 0) >= 2:
            patterns.append("지배구조 관련 신호 다수")
        if category_counts.get('financial', 0) >= 2:
            patterns.append("재무 관련 신호 누적")

        # 상태별 권고사항
        if level == 'FAIL':
            immediate_actions = ["긴급 내부 검토 회의 소집", "투자위원회 보고"]
            monitoring_focus = ["일간 뉴스 모니터링", "공시 실시간 추적"]
        elif level == 'WARNING':
            immediate_actions = ["주간 모니터링 빈도 상향", "담당자 면담 검토"]
            monitoring_focus = ["핵심 지표 추적", "업계 동향 파악"]
        else:
            immediate_actions = ["정기 모니터링 유지"]
            monitoring_focus = ["월간 리포트 검토"]

        return {
            "executive_summary": f"{company}은(는) 현재 {level} 등급으로, {max_category} 영역에서 가장 높은 리스크 신호({max_score}점)가 감지되었습니다. AI 분석 불가로 상세 맥락 해석은 제한됩니다.",

            "context_analysis": {
                "industry_context": "AI 서비스 미연결로 업계 맥락 분석 불가. 수동 검토 필요.",
                "timing_significance": f"최근 {len(signals)}건의 신호가 수집됨. 시계열 패턴 분석 필요."
            },

            "cross_signal_analysis": {
                "patterns_detected": patterns if patterns else ["뚜렷한 패턴 미감지"],
                "correlations": "AI 분석 필요",
                "anomalies": "수동 검토 필요"
            },

            "stakeholder_insights": {
                "executive_concerns": "임원 데이터 교차 분석 필요" if deal_context.get('executives') else "임원 데이터 없음",
                "shareholder_dynamics": "주주 변동 추적 필요" if deal_context.get('shareholders') else "주주 데이터 없음"
            },

            "key_concerns": [
                {
                    "issue": f"{max_category} 카테고리 리스크 집중",
                    "why_it_matters": f"해당 영역 점수가 {max_score}점으로 전체 리스크의 주요 원인",
                    "watch_for": "관련 카테고리 신규 신호 발생 여부"
                }
            ],

            "recommendations": {
                "immediate_actions": immediate_actions,
                "monitoring_focus": monitoring_focus,
                "due_diligence_points": ["AI 서비스 연결 후 상세 분석 권장"]
            },

            "confidence": 0.3,
            "analysis_limitations": "OpenAI API 미연결로 룰 기반 기본 분석만 수행됨. 맥락적 해석 및 교차 분석을 위해 AI 서비스 연결 필요."
        }


# 싱글톤 인스턴스
ai_service_v2 = AIServiceV2()


# ========================================
# 테스트 실행
# ========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print(f"🤖 AI Service v2 Status: {'✅ 활성화' if ai_service_v2.is_available else '❌ 비활성화'}")
    print(f"📌 Model: {ai_service_v2.model}")

    if ai_service_v2.is_available:
        # 테스트: 뉴스 분석
        print("\n🧪 뉴스 분석 테스트:")
        result = ai_service_v2.analyze_news(
            "SK하이닉스가 미국 특허 침해 소송에 휘말렸다.",
            "SK하이닉스, 美 특허 침해 소송 피소"
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 테스트: Text2Cypher
        print("\n🧪 Text2Cypher 테스트:")
        result = ai_service_v2.text_to_cypher("고위험 기업 목록 보여줘")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n⚠️ OpenAI API 키가 설정되지 않았습니다.")
        print("폴백 테스트:")
        result = ai_service_v2._fallback_text_to_cypher("고위험 기업")
        print(json.dumps(result, indent=2, ensure_ascii=False))
