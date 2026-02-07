"""
🏆 JB DealScanner AI Service
경진대회용 AI 분석 모듈 - OpenAI GPT-4.1 Mini 연동
"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

# .env.local 로드
load_dotenv(".env.local")

# OpenAI 클라이언트 초기화
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    AI_AVAILABLE = True
except ImportError:
    client = None
    AI_AVAILABLE = False
    print("⚠️ OpenAI 라이브러리 미설치. pip install openai 실행 필요")


# 모델 설정 (테스트용: gpt-4.1-mini)
MODEL = "gpt-4.1-mini"


def generate_action_guide_ai(signal_type: str, company: str, news_content: str = "") -> Dict:
    """
    🏆 AI 기반 RM/OPS 대응 가이드 생성
    """
    if not AI_AVAILABLE or not client:
        return _fallback_guide(signal_type, company)
    
    # 시그널 타입별 컨텍스트
    context_map = {
        'LEGAL_CRISIS': '법적 위기 (횡령, 배임, 수사, 검찰 등)',
        'MARKET_CRISIS': '시장 위기 (부도, 파산, 구조조정, 신용등급 하락 등)',
        'OPERATIONAL': '운영 리스크 (일반 모니터링 필요)'
    }
    
    context = context_map.get(signal_type, '일반 리스크')
    
    prompt = f"""당신은 금융기관의 리스크 관리 전문가입니다.
    
다음 상황에 대해 RM(영업담당)과 OPS(운영담당) 각각에게 제공할 대응 가이드를 생성해주세요.

[상황]
- 기업: {company}
- 리스크 유형: {context}
- 관련 뉴스: {news_content[:200] if news_content else '없음'}

[요구사항]
1. RM 영업 가이드: 1-2문장의 핵심 대응 방향 (공격적/선제적 관점)
2. RM To-Do: 영업 담당자가 즉시 실행할 3가지 액션
3. OPS 방어 가이드: 1-2문장의 핵심 대응 방향 (방어적/리스크 관리 관점)
4. OPS To-Do: 운영 담당자가 즉시 실행할 3가지 액션

[출력 형식] 정확히 다음 JSON 형식으로 응답:
{{
    "rm_guide": "RM 가이드 내용 (한글, 50자 이내)",
    "rm_todos": ["액션1", "액션2", "액션3"],
    "ops_guide": "OPS 가이드 내용 (한글, 50자 이내)",
    "ops_todos": ["액션1", "액션2", "액션3"]
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "당신은 금융 리스크 관리 전문가입니다. 항상 JSON 형식으로만 응답합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        return {
            'rm_title': '💡 RM 영업 가이드 (AI)',
            'rm_guide': f'"{result.get("rm_guide", "")}"',
            'rm_todos': result.get('rm_todos', ['스폰서 면담', '공동 투자자 협의', 'M&A 탐색']),
            'ops_title': '🛡️ OPS 방어 가이드 (AI)',
            'ops_guide': f'"{result.get("ops_guide", "")}"',
            'ops_todos': result.get('ops_todos', ['EOD 통지서 준비', '자산 점검', '법무 검토'])
        }
        
    except Exception as e:
        print(f"⚠️ AI 생성 실패: {e}")
        return _fallback_guide(signal_type, company)


# ==============================================================================
# 🏆 AI Action Guide v2.0 - 산업별 맞춤 가이드 (Day 4)
# ==============================================================================

# 산업별 컨텍스트 정의
INDUSTRY_CONTEXTS = {
    '반도체': {
        'context': '메모리 가격 변동, 설비투자 리스크, 글로벌 수요 변화, 미중 기술 분쟁',
        'key_risks': ['설비투자 지연', '수요 급감', '재고 급증', '기술 제재'],
        'rm_focus': '글로벌 고객사 다변화, 선제적 재고 관리, 기술 경쟁력 확보',
        'ops_focus': 'Capex 모니터링, 재고 회전율 점검, 가동률 추적'
    },
    '금융': {
        'context': '금리 변동, 규제 리스크, 신용 리스크, 유동성 리스크',
        'key_risks': ['금리 급변', 'NPL 급증', '규제 제재', '유동성 위기'],
        'rm_focus': '금리 헤지, 포트폴리오 다각화, 규제 준수 강화',
        'ops_focus': 'BIS 비율 점검, LCR/NSFR 모니터링, 충당금 적정성'
    },
    '건설': {
        'context': '부동산 경기, 분양률, 자금 조달, PF 리스크',
        'key_risks': ['미분양 증가', 'PF 연장 불가', '자재비 급등', '원가율 악화'],
        'rm_focus': '분양 촉진, 자금 조달 대안, 협력사 리스크 관리',
        'ops_focus': '미분양 모니터링, 원가율 추적, PF 만기 관리'
    },
    '유통': {
        'context': '소비 트렌드, 온라인 전환, 물류 효율성, 재고 관리',
        'key_risks': ['소비 위축', '온라인 경쟁', '물류비 급등', '폐점 증가'],
        'rm_focus': '채널 다각화, 물류 효율화, 고객 데이터 활용',
        'ops_focus': '매출/매장 추이, 재고 회전율, 임대료 부담률'
    },
    '기타': {
        'context': '일반 사업 리스크, 경기 변동, 경쟁 심화',
        'key_risks': ['매출 감소', '비용 증가', '경쟁 심화', '규제 변화'],
        'rm_focus': '고객 유지, 비용 효율화, 신규 시장 개척',
        'ops_focus': '손익 모니터링, 현금흐름 추적, 주요 계약 관리'
    }
}


def detect_industry(company: str) -> str:
    """기업명에서 산업 분류 추정"""
    if any(kw in company for kw in ['은행', '금융', '캐피탈', '카드', '저축', '보험', '증권']):
        return '금융'
    if any(kw in company for kw in ['반도체', '하이닉스', '삼성전자', 'SK', '마이크론', '메모리']):
        return '반도체'
    if any(kw in company for kw in ['건설', '건축', 'E&C', '엔지니어링', '주택', '개발']):
        return '건설'
    if any(kw in company for kw in ['유통', '마트', '백화점', '쇼핑', '리테일', '편의점']):
        return '유통'
    return '기타'


def generate_action_guide_ai_v2(
    signal_type: str, 
    company: str, 
    industry: str = None,
    news_content: str = "",
    risk_score: int = 0
) -> Dict:
    """
    🏆 AI Action Guide v2.0 - 산업별 맞춤 가이드 생성
    
    Args:
        signal_type: LEGAL_CRISIS, MARKET_CRISIS, OPERATIONAL
        company: 기업명
        industry: 산업 분류 (None이면 자동 감지)
        news_content: 관련 뉴스 내용
        risk_score: 현재 리스크 점수
    """
    if not AI_AVAILABLE or not client:
        return _fallback_guide_v2(signal_type, company, industry)
    
    # 산업 자동 감지
    if not industry:
        industry = detect_industry(company)
    
    ind_ctx = INDUSTRY_CONTEXTS.get(industry, INDUSTRY_CONTEXTS['기타'])
    
    # 시그널 타입별 컨텍스트
    signal_context = {
        'LEGAL_CRISIS': '법적 위기 (횡령, 배임, 수사, 검찰 등)',
        'MARKET_CRISIS': '시장 위기 (부도, 파산, 구조조정, 신용등급 하락 등)',
        'OPERATIONAL': '운영 리스크 (일반 모니터링 필요)'
    }.get(signal_type, '일반 리스크')
    
    prompt = f"""당신은 금융기관의 {industry} 산업 전문 리스크 관리자입니다.

[산업 컨텍스트: {industry}]
- 주요 리스크 요인: {ind_ctx['context']}
- 핵심 위험 지표: {', '.join(ind_ctx['key_risks'])}

[현재 상황]
- 기업: {company}
- 리스크 유형: {signal_context}
- 리스크 점수: {risk_score}점 (100점 만점)
- 관련 뉴스: {news_content[:300] if news_content else '없음'}

[{industry} 산업 특화 가이드 요청]
1. RM 영업 가이드: {industry} 산업 특성을 반영한 선제적 대응 방향
2. RM To-Do: {industry} 산업 특화 3가지 액션 아이템
3. OPS 방어 가이드: {industry} 산업 특성을 반영한 방어적 대응 방향
4. OPS To-Do: {industry} 산업 특화 3가지 점검 항목

[출력 형식] JSON:
{{
    "rm_guide": "RM 가이드 (50자 이내)",
    "rm_todos": ["액션1", "액션2", "액션3"],
    "ops_guide": "OPS 가이드 (50자 이내)",
    "ops_todos": ["액션1", "액션2", "액션3"],
    "industry_insight": "{industry} 산업 특화 인사이트 (30자)"
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"당신은 {industry} 산업 전문 금융 리스크 관리자입니다. JSON만 응답."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=700,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        return {
            'rm_title': f'💡 RM 영업 가이드 (AI v2.0 - {industry})',
            'rm_guide': f'"{result.get("rm_guide", "")}"',
            'rm_todos': result.get('rm_todos', ['고객 면담', '리스크 공유', '대안 검토']),
            'ops_title': f'🛡️ OPS 방어 가이드 (AI v2.0 - {industry})',
            'ops_guide': f'"{result.get("ops_guide", "")}"',
            'ops_todos': result.get('ops_todos', ['현황 점검', '충당금 검토', '보고서 작성']),
            'industry': industry,
            'industry_insight': result.get('industry_insight', f'{industry} 산업 특화 분석')
        }
        
    except Exception as e:
        print(f"⚠️ AI v2.0 생성 실패: {e}")
        return _fallback_guide_v2(signal_type, company, industry)


def _fallback_guide_v2(signal_type: str, company: str, industry: str = None) -> Dict:
    """AI 호출 실패 시 산업별 기본 가이드"""
    if not industry:
        industry = detect_industry(company)
    
    ind_ctx = INDUSTRY_CONTEXTS.get(industry, INDUSTRY_CONTEXTS['기타'])
    
    return {
        'rm_guide': f"{ind_ctx['rm_focus'][:20]}... (기본)",
        'rm_todos': ind_ctx['key_risks'][:3],
        'ops_guide': f"{ind_ctx['ops_focus'][:20]}... (기본)",
        'ops_todos': ['현황 점검', '충당금 검토', '보고서 작성'],
        'industry_insight': f'{industry} 산업 기본 가이드',
        # 호환성 필드
        'rm_title': f'💡 RM 영업 가이드 ({industry})',
        'ops_title': f'🛡️ OPS 방어 가이드 ({industry})',
        'industry': industry
    }


def predict_risk_trajectory(company: str, current_score: int, recent_news_summary: str) -> Dict:
    """
    🔮 [New] AI 기반 미래 리스크 시나리오 예측 (Predictive AI)
    """
    if not AI_AVAILABLE or not client:
        return _fallback_prediction(company)

    prompt = f"""당신은 금융 리스크 예측 모델입니다. 
다음 기업의 현재 리스크 정보를 바탕으로 향후 1개월 내 예상되는 리스크 전개 방향(Trajectory)을 3가지 시나리오로 예측해주세요.

[기업 정보]
- 기업: {company}
- 현재 리스크 점수: {current_score}점 (100점 만점, 높을수록 위험)
- 최근 뉴스 요약: {recent_news_summary[:300]}

[요구사항]
향후 4주간 발생 가능한 시나리오를 'Best', 'Base', 'Worst' 케이스로 나누어 예측.
각 시나리오는 "핵심 이벤트"와 "예상 리스크 점수"를 포함해야 함.

[출력 형식] JSON:
{{
    "trend": "상승세" or "하락세" or "변동성 확대",
    "scenarios": {{
        "best": {{ "event": "이벤트 설명 (20자)", "prob": "20%", "score": 30 }},
        "base": {{ "event": "이벤트 설명 (20자)", "prob": "60%", "score": 50 }},
        "worst": {{ "event": "이벤트 설명 (20자)", "prob": "20%", "score": 80 }}
    }}
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "금융 리스크 예측 모델. JSON 응답."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception:
        return _fallback_prediction(company)


def _fallback_guide(signal_type: str, company: str) -> Dict:
    """AI 호출 실패 시 기본 가이드 (룰 기반)"""
    GUIDES = {
        'LEGAL_CRISIS': {
            'rm_title': '💡 RM 영업 가이드',
            'rm_guide': '"스폰서 부도 리스크 심화, 신규 대출 중단 및 기존 자금 점검 필요."',
            'rm_todos': ['스폰서 자금 관리인 면담', '공동 투자자 리스크 분담 타진', 'White Knight 탐색'],
            'ops_title': '🛡️ OPS 방어 가이드',
            'ops_guide': '"금융약정 위반 EOD 통지서 작성, 계좌 모니터링 및 자금 이탈 차단."',
            'ops_todos': ['☑ EOD 통지서 발송 준비', '자산 현황 재점검', '법무법인 선임']
        },
        'MARKET_CRISIS': {
            'rm_title': '💡 RM 영업 가이드',
            'rm_guide': f'"{company} 시장 위기 감지. 헤지 포지션 및 유동성 확보 검토."',
            'rm_todos': ['시장 동향 모니터링 강화', '유동성 확보 방안 검토', '파트너사 커뮤니케이션'],
            'ops_title': '🛡️ OPS 방어 가이드',
            'ops_guide': '"LTV 한도 재검토 및 추가 담보 요청. 시장 변동성 대응 시나리오."',
            'ops_todos': ['담보 가치 재평가', 'Covenant 위반 점검', '비상 유동성 확보']
        },
        'OPERATIONAL': {
            'rm_title': '💡 RM 영업 가이드',
            'rm_guide': f'"{company} 운영 리스크 주의. 정기 모니터링 및 경영진 면담 권장."',
            'rm_todos': ['정기 경영 보고서 검토', '현장 실사 일정 조율', '경영진 면담 요청'],
            'ops_title': '🛡️ OPS 방어 가이드',
            'ops_guide': '"내부 통제 점검 및 운영 효율성 분석. 이상 징후 발견 시 즉시 보고."',
            'ops_todos': ['내부 감사 결과 확인', '운영 효율성 분석', 'IT 보안 점검']
        }
    }
    return GUIDES.get(signal_type, GUIDES['OPERATIONAL'])


def classify_timeline_event_ai(event_title: str, event_date: str = "") -> Dict:
    """
    🏆 AI 기반 타임라인 이벤트 3단계 분류
    """
    if not AI_AVAILABLE or not client:
        return _fallback_classify(event_title)
    
    prompt = f"""당신은 금융 리스크 전문가입니다. 다음 뉴스 제목을 분석하여 리스크 단계를 분류해주세요.

[뉴스 제목]
{event_title}

[3단계 분류 기준]
- Stage 1 (뉴스 보도): 언론 최초 보도, 루머, 확인되지 않은 정보
- Stage 2 (금융위 통지): 금융당국/검찰/공정위 개입, 수사, 조사, 제재, 과징금
- Stage 3 (대주단 확인): 대주단/채권단 개입, 상환 요구, 워크아웃, EOD, 채무 관련

[출력 형식] 정확히 다음 JSON 형식:
{{
    "stage": 1,
    "stage_label": "뉴스 보도",
    "description": "선행 감지 완료 (20자 이내 설명)"
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "금융 리스크 분류 전문가. JSON만 응답."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        stage = result.get('stage', 1)
        icons = {1: '🔵', 2: '🟡', 3: '🔴'}
        
        return {
            "stage": stage,
            "stage_label": result.get('stage_label', '뉴스 보도'),
            "icon": icons.get(stage, '🔵'),
            "description": result.get('description', '리스크 감지')
        }
        
    except Exception as e:
        return _fallback_classify(event_title)


def _fallback_classify(event_title: str) -> Dict:
    """AI 실패 시 키워드 기반 분류"""
    STAGE_KEYWORDS = {
        'stage3': ['대주단', '채권단', '상환', '만기', 'EOD', '기한이익', '워크아웃', '채무'],
        'stage2': ['금융위', '금감원', '검찰', '수사', '조사', '제재', '과징금', '기소']
    }
    
    for kw in STAGE_KEYWORDS['stage3']:
        if kw in event_title:
            return {"stage": 3, "stage_label": "대주단 확인", "icon": "🔴", "description": "담당자 조치 필요"}
    
    for kw in STAGE_KEYWORDS['stage2']:
        if kw in event_title:
            return {"stage": 2, "stage_label": "금융위 통지", "icon": "🟡", "description": "규제 리스크 발생"}
    
    return {"stage": 1, "stage_label": "뉴스 보도", "icon": "🔵", "description": "선행 감지 완료"}


def _fallback_prediction(company: str) -> Dict:
    return {
        "trend": "변동성 확대",
        "scenarios": {
            "best": {"event": "리스크 요인 해소", "prob": "20%", "score": 30},
            "base": {"event": "현 상태 유지", "prob": "60%", "score": 50},
            "worst": {"event": "추가 악재 발생", "prob": "20%", "score": 80}
        }
    }


def analyze_timeline_with_ai(events: list) -> list:
    """
    🏆 여러 이벤트를 한번에 AI로 분석 (배치 처리)
    """
    if not AI_AVAILABLE or not client or not events:
        return [_fallback_classify(e.get('title', '')) for e in events]
    
    # 이벤트 목록 정리
    event_texts = "\n".join([f"{i+1}. {e.get('title', '')[:60]}" for i, e in enumerate(events[:5])])
    
    prompt = f"""다음 뉴스 제목들을 각각 리스크 단계로 분류해주세요.

[뉴스 목록]
{event_texts}

[3단계 분류 기준]
- Stage 1: 언론 최초 보도
- Stage 2: 금융당국/검찰 개입
- Stage 3: 대주단/채권단 개입

[출력 형식] JSON:
{{
    "classifications": [
        {{"index": 1, "stage": 1, "stage_label": "뉴스 보도", "description": "설명"}},
        ...
    ]
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "금융 리스크 분류 전문가. JSON만 응답."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=600,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        classifications = result.get('classifications', [])
        
        icons = {1: '🔵', 2: '🟡', 3: '🔴'}
        
        output = []
        for i, event in enumerate(events[:5]):
            if i < len(classifications):
                c = classifications[i]
                stage = c.get('stage', 1)
                output.append({
                    "stage": stage,
                    "stage_label": c.get('stage_label', '뉴스 보도'),
                    "icon": icons.get(stage, '🔵'),
                    "description": c.get('description', '리스크 감지')
                })
            else:
                output.append(_fallback_classify(event.get('title', '')))
        
        return output
        
    except Exception as e:
        return [_fallback_classify(e.get('title', '')) for e in events]


def analyze_risk_with_ai(company: str, news_list: list, score: int) -> str:
    """
    🏆 AI 기반 종합 리스크 분석 코멘트 생성
    """
    if not AI_AVAILABLE or not client:
        return f"{company}: 리스크 점수 {score}점. 지속적인 모니터링 필요."
    
    news_summary = "\n".join([f"- {n.get('title', '')[:50]}" for n in news_list[:3]])
    
    prompt = f"""다음 기업의 리스크 상황을 1-2문장으로 요약해주세요.

기업: {company}
리스크 점수: {score}점 (100점 만점)
최근 뉴스:
{news_summary}

요약 (한글, 50자 이내, 전문가 톤):"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "당신은 금융 리스크 분석가입니다. 간결하게 응답합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"{company}: 리스크 점수 {score}점. 모니터링 필요."


# ==============================================================================
# 🏆 Text2Cypher - 자연어 → Cypher 쿼리 변환 (Day 3)
# ==============================================================================

# 그래프 스키마 정의 (Text2Cypher AI 프롬프트용)
GRAPH_SCHEMA = """
## Neo4j Graph Schema

### Nodes
- (:Company {name: STRING, corp_code: STRING, total_score: INT, propagated_risk: INT})
- (:Person {name: STRING})
- (:Category {id: STRING, type: STRING, label: STRING, score: INT})
- (:NewsCategory {id: STRING, type: STRING, label: STRING})
- (:DisclosureCategory {id: STRING, type: STRING, label: STRING, count: INT, risk_score: INT})
- (:NewsArticle {url: STRING, title: STRING, date: STRING, source: STRING, risk_score: INT, sentiment: STRING})
- (:Disclosure {code: STRING, title: STRING, date: STRING, category: STRING, risk_score: INT})
- (:RiskLevel {level: STRING, label: STRING})  # level: GREEN, YELLOW, RED

### Relationships
- (:RiskLevel)-[:HAS_STATUS]->(:Company)
- (:Company)-[:HAS_CATEGORY]->(:Category)
- (:Category)-[:HAS_SUBCATEGORY]->(:NewsCategory|:DisclosureCategory)
- (:Category)-[:CONTAINS]->(:Person)
- (:NewsCategory)-[:HAS_ARTICLE]->(:NewsArticle)
- (:DisclosureCategory)-[:HAS_DISCLOSURE]->(:Disclosure)

### Key Properties
- Company.total_score: 리스크 총점 (0-100, 높을수록 위험)
- RiskLevel.level: GREEN(정상), YELLOW(주의), RED(위험)
- NewsArticle.sentiment: 부정, 중립, 긍정
"""


def text2cypher(question: str, graph=None) -> Dict:
    """
    🏆 Text2Cypher - 자연어 질문을 Cypher 쿼리로 변환하고 실행
    
    Args:
        question: 사용자 질문 (한국어)
        graph: Neo4jGraph 인스턴스 (None이면 내부에서 생성)
    
    Returns:
        {
            "question": 원본 질문,
            "cypher": 생성된 Cypher 쿼리,
            "results": 쿼리 실행 결과,
            "answer": 자연어 응답,
            "success": 성공 여부
        }
    """
    if not AI_AVAILABLE or not client:
        return {
            "question": question,
            "cypher": None,
            "results": None,
            "answer": "⚠️ AI 서비스를 사용할 수 없습니다.",
            "success": False
        }
    
    # Cypher 생성 프롬프트
    prompt = f"""당신은 Neo4j Cypher 쿼리 전문가입니다.
사용자의 자연어 질문을 Cypher 쿼리로 변환해주세요.

{GRAPH_SCHEMA}

## Rules
1. 읽기 전용 쿼리만 생성 (MATCH, RETURN, WHERE, ORDER BY, LIMIT)
2. CREATE, DELETE, SET, MERGE 등 쓰기 명령 절대 금지
3. 정렬 시 반드시 IS NOT NULL 체크 추가
4. 결과는 최대 20개로 제한 (LIMIT 20)
5. 한국어 속성값 검색 시 정확한 값 사용

## 사용자 질문
{question}

## 출력 형식 (JSON만 응답)
{{
    "cypher": "MATCH (c:Company) WHERE c.name = 'SK하이닉스' RETURN c.total_score AS score",
    "explanation": "SK하이닉스의 리스크 점수를 조회합니다."
}}"""

    try:
        # 1. Cypher 쿼리 생성
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Neo4j Cypher 전문가. JSON만 응답."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        cypher = result.get("cypher", "")
        explanation = result.get("explanation", "")
        
        # 2. 안전성 검증 (읽기 전용만 허용)
        cypher_upper = cypher.upper()
        forbidden = ["CREATE", "DELETE", "SET ", "MERGE", "REMOVE", "DROP", "DETACH"]
        for kw in forbidden:
            if kw in cypher_upper:
                return {
                    "question": question,
                    "cypher": cypher,
                    "results": None,
                    "answer": f"⚠️ 읽기 전용 쿼리만 허용됩니다. ({kw} 감지)",
                    "success": False
                }
        
        # 3. Neo4j 연결 및 쿼리 실행
        if graph is None:
            from langchain_neo4j import Neo4jGraph
            graph = Neo4jGraph(
                url=os.getenv("NEO4J_URI"),
                username=os.getenv("NEO4J_USERNAME"),
                password=os.getenv("NEO4J_PASSWORD"),
                database=os.getenv("NEO4J_DATABASE", "neo4j")
            )
        
        results = graph.query(cypher)
        
        # 4. 결과 포맷팅
        if not results:
            answer = f"검색 결과가 없습니다. ({explanation})"
        elif len(results) == 1:
            answer = _format_single_result(results[0], explanation)
        else:
            answer = _format_multiple_results(results, explanation)
        
        return {
            "question": question,
            "cypher": cypher,
            "results": results,
            "answer": answer,
            "success": True
        }
        
    except Exception as e:
        return {
            "question": question,
            "cypher": None,
            "results": None,
            "answer": f"⚠️ 쿼리 실행 오류: {str(e)}",
            "success": False
        }


def _format_single_result(result: Dict, explanation: str) -> str:
    """단일 결과 포맷팅"""
    parts = []
    for key, value in result.items():
        if value is not None:
            parts.append(f"{key}: {value}")
    return " | ".join(parts) if parts else explanation


def _format_multiple_results(results: list, explanation: str) -> str:
    """다중 결과 포맷팅"""
    lines = [f"📊 {len(results)}건 조회됨:"]
    for i, r in enumerate(results[:10], 1):
        parts = [f"{v}" for v in r.values() if v is not None]
        lines.append(f"  {i}. {' | '.join(parts[:3])}")
    if len(results) > 10:
        lines.append(f"  ... 외 {len(results) - 10}건")
    return "\n".join(lines)


def ask_graph(question: str) -> str:
    """
    🏆 간편 인터페이스 - 질문하고 답변만 받기
    """
    result = text2cypher(question)
    return result["answer"]


if __name__ == "__main__":
    print(f"🤖 AI Service Status: {'✅ 활성화' if AI_AVAILABLE else '❌ 비활성화'}")
    print(f"📌 Model: {MODEL}")
    
    if AI_AVAILABLE:
        # Prediction Test
        print("\n🧪 Prediction 테스트:")
        pred = predict_risk_trajectory("테스트기업", 60, "검찰 압수수색 시작 및 주가 급락")
        import json
        print(json.dumps(pred, indent=2, ensure_ascii=False))

