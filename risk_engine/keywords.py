"""
키워드 사전 및 매칭 엔진 (Risk Graph v3)
- 책임: 리스크 키워드 정의 및 제목/내용에서 키워드 매칭
- 위치: risk_engine/keywords.py

Design Doc: docs/02-design/features/risk-graph-v3.design.md Section 3.1
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

# =============================================================================
# 키워드 사전 정의
# =============================================================================

# DART 공시 리스크 키워드 (32개)
DART_RISK_KEYWORDS: dict[str, int] = {
    # 고위험 (50-70점)
    "횡령": 50, "배임": 50, "분식회계": 50,
    "부적정": 60, "의견거절": 70, "부도": 60, "파산": 60,
    # 중위험 (30-49점)
    "회생": 50, "워크아웃": 45, "자본잠식": 40, "채무불이행": 45,
    "계속기업불확실": 40, "과징금": 35, "한정": 35, "경영권분쟁": 35,
    "제재": 30, "고발": 30, "감사범위제한": 30,
    # 저위험 (10-29점)
    "소송": 25, "고소": 25, "벌금": 25, "해임": 25, "손해배상": 20,
    "최대주주변경": 20, "위반": 15, "사임": 15, "정정": 10,
    "대표이사": 10, "조회공시": 5, "풍문": 5, "주주총회": 5,
    # 사업 위험 (40-50점)
    "사업중단": 40, "허가취소": 45, "영업정지": 40, "폐업": 50,
}

# 뉴스 리스크 키워드 (투자심사 DD 관점 확장)
NEWS_RISK_KEYWORDS: dict[str, int] = {
    # === 법률/규제 (LEGAL) ===
    "횡령": 50, "배임": 50, "분식회계": 50, "압수수색": 40,
    "구속": 40, "기소": 35, "검찰": 30, "고발": 25,
    "소송": 20, "위반": 15, "비리": 25,
    "특허침해": 30, "특허": 15, "침해": 15, "제소": 25,
    "과징금": 30, "제재": 30, "벌금": 20, "피소": 20,
    "공정위": 25, "금감원": 20, "규제": 15, "분쟁": 20,
    "ITC": 20, "반덤핑": 25, "무역분쟁": 20,
    # === 신용/재무 (CREDIT) ===
    "부도": 60, "파산": 60, "회생": 45,
    "신용등급": 25, "등급하향": 35, "등급": 10,
    "채무불이행": 50, "자본잠식": 45, "워크아웃": 40,
    "부채": 15, "차입": 10, "만기": 10, "유동성": 15,
    "적자": 20, "손실": 15, "영업손실": 25, "적자전환": 30,
    "재무": 8, "부채비율": 15, "이자비용": 10,
    # === 주주/자본 (CAPITAL/SHARE) ===
    "주가하락": 20, "주가급락": 30, "주가폭락": 40, "급락": 25, "폭락": 35,
    "주가": 5, "시세": 5, "하락": 10, "매도": 15,
    "공매도": 20, "대량매도": 25,
    "전환사채": 15, "사채": 10, "유상증자": 15, "무상감자": 30,
    "최대주주변경": 25, "대주주": 10, "지분매각": 20, "지분": 5,
    "배당삭감": 20, "배당축소": 15, "배당": 5, "배당금": 5,
    "주주환원": 5, "자사주": 5, "액면분할": 5,
    "상장폐지": 40, "관리종목": 30, "레버리지": 5, "ETF": 3,
    # === 지배구조 (GOVERNANCE) ===
    "사임": 15, "해임": 25, "교체": 10, "경영권분쟁": 35,
    "대표이사": 10, "이사회": 10, "경영권": 20,
    "오너리스크": 30, "내부갈등": 20,
    "CFO": 10, "CEO": 8, "인사": 8, "선임": 5,
    # === 운영 (OPERATIONAL) ===
    "사업중단": 40, "허가취소": 45, "영업정지": 40, "폐업": 50,
    "감산": 20, "가동중단": 30, "생산차질": 25, "생산중단": 35,
    "실적악화": 25, "실적부진": 20, "매출감소": 20, "영업이익감소": 20,
    "구조조정": 25, "인원감축": 20, "정리해고": 25,
    "리콜": 25, "결함": 20, "불량": 15,
    "실적": 5, "매출": 5, "영업이익": 5, "영업익": 5, "순이익": 5,
    "경쟁": 5, "점유율": 8, "시장점유율": 10,
    "설비투자": 8, "설비": 5, "증설": 5, "공장": 5,
    "성과급": 5, "연봉": 3, "퇴직금": 10, "인건비": 8,
    # === 공급망 (SUPPLY) ===
    "공급차질": 25, "공급망": 10, "수출규제": 25, "수출통제": 25,
    "관세": 15, "수입규제": 20, "원자재": 10,
    "반도체": 5, "메모리": 5, "D램": 5, "HBM": 5, "NAND": 5, "낸드": 5,
    "업황": 8, "수급": 8, "재고": 10, "가격하락": 15,
    "낸드플래시": 8, "파운드리": 5, "웨이퍼": 5,
    # === 감사 (AUDIT) ===
    "부적정": 60, "의견거절": 70, "한정": 35,
    "감사범위제한": 30, "계속기업불확실": 40,
    "감사의견거절": 70, "계속기업": 30, "불성실공시": 35,
    # === ESG ===
    "환경오염": 25, "안전사고": 25, "인권침해": 20,
    "갑질": 15, "스캔들": 15, "불매": 10, "논란": 10,
    "탄소배출": 15, "산업재해": 25, "유해물질": 20,
    # === 투자/시장 모니터링 (낮은 점수) ===
    "투자": 5, "조달": 5, "자금": 5,
    "전망": 3, "리스크": 8, "우려": 8, "불확실": 10,
    "변동성": 8, "약세": 10, "강세": 3,
}

# KIND (거래소 공시) 리스크 키워드 (23개)
KIND_RISK_KEYWORDS: dict[str, int] = {
    "상장폐지": 80, "파산": 80, "감사의견거절": 75, "부도": 75,
    "관리종목": 70, "의견거절": 70, "채무불이행": 70,
    "계속기업": 65, "불성실공시": 60, "횡령": 60, "배임": 60,
    "자본잠식": 60, "회생": 55, "한정": 50, "가압류": 45, "무상감자": 45,
    "조회공시": 40, "피소": 40, "소송": 35, "최대주주변경": 35,
    "정정공시": 25, "유상증자": 20, "단일판매": 20,
}

# 카테고리별 키워드 분류
CATEGORY_KEYWORDS: dict[str, dict] = {
    "LEGAL": {
        "keywords": [
            "횡령", "배임", "소송", "고발", "고소", "제재", "과징금",
            "압수수색", "구속", "기소", "벌금", "피소",
            "특허침해", "특허", "침해", "제소", "공정위", "금감원", "규제", "분쟁",
            "ITC", "반덤핑", "무역분쟁",
        ],
        "weight": 0.15,
        "alert_threshold": 30,
    },
    "CREDIT": {
        "keywords": [
            "부도", "파산", "회생", "워크아웃", "채무불이행", "자본잠식", "가압류",
            "신용등급", "등급하향", "등급",
            "부채", "차입", "만기", "유동성",
            "적자", "손실", "영업손실", "적자전환",
            "재무", "부채비율", "이자비용",
        ],
        "weight": 0.20,
        "alert_threshold": 40,
    },
    "GOVERNANCE": {
        "keywords": [
            "최대주주변경", "대표이사", "사임", "해임", "경영권분쟁", "주주총회",
            "교체", "경영권", "오너리스크", "내부갈등", "이사회",
            "CFO", "CEO", "인사", "선임",
        ],
        "weight": 0.10,
        "alert_threshold": 20,
    },
    "OPERATIONAL": {
        "keywords": [
            "사업중단", "허가취소", "영업정지", "폐업", "생산중단",
            "감산", "가동중단", "생산차질",
            "실적악화", "실적부진", "매출감소", "영업이익감소",
            "구조조정", "인원감축", "정리해고",
            "리콜", "결함", "불량",
            "실적", "매출", "영업이익", "영업익", "순이익",
            "경쟁", "점유율", "시장점유율",
            "설비투자", "설비", "증설", "공장",
            "성과급", "연봉", "퇴직금", "인건비",
        ],
        "weight": 0.15,
        "alert_threshold": 35,
    },
    "AUDIT": {
        "keywords": [
            "부적정", "의견거절", "한정", "감사범위제한", "계속기업불확실",
            "감사의견거절", "계속기업", "불성실공시",
        ],
        "weight": 0.20,
        "alert_threshold": 30,
    },
    "ESG": {
        "keywords": [
            "환경오염", "안전사고", "인권침해", "갑질", "비리", "스캔들", "불매", "논란",
            "탄소배출", "산업재해", "유해물질",
        ],
        "weight": 0.10,
        "alert_threshold": 15,
    },
    "CAPITAL": {
        "keywords": [
            "유상증자", "무상감자", "정정공시", "정정", "조회공시", "풍문",
            "주가하락", "주가급락", "주가폭락", "급락", "폭락",
            "주가", "시세", "하락", "매도", "공매도", "대량매도",
            "전환사채", "사채", "최대주주변경", "대주주", "지분매각", "지분",
            "배당삭감", "배당축소", "배당", "배당금",
            "주주환원", "자사주", "액면분할",
            "상장폐지", "관리종목", "레버리지", "ETF",
            "투자", "조달", "자금",
        ],
        "weight": 0.05,
        "alert_threshold": 10,
    },
    "SUPPLY": {
        "keywords": [
            "공급차질", "공급망", "수출규제", "수출통제",
            "관세", "수입규제", "원자재",
            "반도체", "메모리", "D램", "HBM", "NAND", "낸드", "낸드플래시",
            "업황", "수급", "재고", "가격하락",
            "파운드리", "웨이퍼",
        ],
        "weight": 0.10,
        "alert_threshold": 20,
    },
    "OTHER": {
        "keywords": ["위반", "손해배상", "단일판매"],
        "weight": 0.05,
        "alert_threshold": 15,
    },
}

# 소스 타입
SourceType = Literal["DART", "NEWS", "KIND"]

# 카테고리 타입
CategoryType = Literal["LEGAL", "CREDIT", "GOVERNANCE", "OPERATIONAL", "AUDIT", "ESG", "CAPITAL", "SUPPLY", "OTHER"]


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class MatchedKeyword:
    """매칭된 키워드 정보"""
    keyword: str
    score: int
    category: CategoryType
    position: int  # 텍스트 내 위치


@dataclass
class MatchResult:
    """키워드 매칭 결과"""
    matched_keywords: list[MatchedKeyword]
    raw_score: int  # max(scores) 또는 sum(scores) 중 선택
    primary_category: CategoryType | None
    keyword_count: int

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "matched_keywords": [kw.keyword for kw in self.matched_keywords],
            "scores": [kw.score for kw in self.matched_keywords],
            "raw_score": self.raw_score,
            "primary_category": self.primary_category,
            "keyword_count": self.keyword_count,
        }


# =============================================================================
# 함수 정의
# =============================================================================

def get_keywords_by_source(source: SourceType) -> dict[str, int]:
    """
    소스 타입에 따른 키워드 사전 반환

    Args:
        source: "DART", "NEWS", "KIND" 중 하나

    Returns:
        해당 소스의 키워드 사전 (키워드 -> 점수)
    """
    keyword_dicts = {
        "DART": DART_RISK_KEYWORDS,
        "NEWS": NEWS_RISK_KEYWORDS,
        "KIND": KIND_RISK_KEYWORDS,
    }
    return keyword_dicts.get(source, DART_RISK_KEYWORDS)


def classify_category(keyword: str) -> CategoryType:
    """
    키워드를 카테고리로 분류

    Args:
        keyword: 분류할 키워드

    Returns:
        카테고리 (LEGAL, CREDIT, GOVERNANCE, OPERATIONAL, AUDIT, ESG, CAPITAL, OTHER)
    """
    for category, config in CATEGORY_KEYWORDS.items():
        if keyword in config["keywords"]:
            return category  # type: ignore
    return "OTHER"


def get_category_weight(category: CategoryType) -> float:
    """카테고리별 가중치 반환"""
    return CATEGORY_KEYWORDS.get(category, {}).get("weight", 0.05)


def get_category_threshold(category: CategoryType) -> int:
    """카테고리별 알림 임계치 반환"""
    return CATEGORY_KEYWORDS.get(category, {}).get("alert_threshold", 15)


def match_keywords(text: str, keyword_dict: dict[str, int] | None = None,
                   source: SourceType = "DART") -> MatchResult:
    """
    텍스트에서 리스크 키워드를 매칭

    Args:
        text: 검색할 텍스트 (제목, 내용 등)
        keyword_dict: 키워드 사전 (None이면 source 기반으로 선택)
        source: 소스 타입 ("DART", "NEWS", "KIND")

    Returns:
        MatchResult: 매칭 결과

    Example:
        >>> result = match_keywords("감사보고서 - 의견거절 (계속기업불확실 사유)")
        >>> result.matched_keywords
        [MatchedKeyword(keyword='의견거절', score=70, category='AUDIT', position=9),
         MatchedKeyword(keyword='계속기업불확실', score=40, category='AUDIT', position=15)]
        >>> result.raw_score
        70
    """
    if not text:
        return MatchResult(
            matched_keywords=[],
            raw_score=0,
            primary_category=None,
            keyword_count=0,
        )

    # 키워드 사전 선택
    if keyword_dict is None:
        keyword_dict = get_keywords_by_source(source)

    # 매칭 수행
    matched: list[MatchedKeyword] = []
    text_lower = text.lower()  # 대소문자 무시 (한글은 영향 없음)

    for keyword, score in keyword_dict.items():
        position = text.find(keyword)
        if position != -1:
            category = classify_category(keyword)
            matched.append(MatchedKeyword(
                keyword=keyword,
                score=score,
                category=category,
                position=position,
            ))

    # 결과 정렬 (점수 내림차순)
    matched.sort(key=lambda x: x.score, reverse=True)

    # raw_score 계산: 최고 점수 사용 (Design 문서 기준)
    raw_score = matched[0].score if matched else 0

    # 주요 카테고리 결정 (가장 높은 점수의 카테고리)
    primary_category = matched[0].category if matched else None

    return MatchResult(
        matched_keywords=matched,
        raw_score=raw_score,
        primary_category=primary_category,
        keyword_count=len(matched),
    )


def match_keywords_multi_source(text: str) -> dict[str, MatchResult]:
    """
    모든 소스 타입에 대해 키워드 매칭 수행

    Args:
        text: 검색할 텍스트

    Returns:
        소스별 매칭 결과 딕셔너리
    """
    return {
        "DART": match_keywords(text, source="DART"),
        "NEWS": match_keywords(text, source="NEWS"),
        "KIND": match_keywords(text, source="KIND"),
    }


def get_high_risk_keywords(threshold: int = 50) -> dict[str, int]:
    """
    모든 소스에서 고위험 키워드 추출

    Args:
        threshold: 점수 임계치 (이상)

    Returns:
        고위험 키워드 딕셔너리 (중복 제거, 최고 점수 유지)
    """
    all_keywords: dict[str, int] = {}

    for source in ["DART", "NEWS", "KIND"]:
        for keyword, score in get_keywords_by_source(source).items():  # type: ignore
            if score >= threshold:
                # 이미 있으면 더 높은 점수로 업데이트
                if keyword not in all_keywords or all_keywords[keyword] < score:
                    all_keywords[keyword] = score

    return dict(sorted(all_keywords.items(), key=lambda x: x[1], reverse=True))


def get_category_keywords_list(category: CategoryType) -> list[str]:
    """특정 카테고리의 키워드 목록 반환"""
    return CATEGORY_KEYWORDS.get(category, {}).get("keywords", [])


def get_all_categories() -> list[CategoryType]:
    """모든 카테고리 목록 반환"""
    return list(CATEGORY_KEYWORDS.keys())  # type: ignore


def calculate_category_scores(matched_keywords: list[MatchedKeyword]) -> dict[str, int]:
    """
    카테고리별 점수 집계 (breakdown용)

    Args:
        matched_keywords: 매칭된 키워드 목록

    Returns:
        카테고리별 최고 점수 딕셔너리
    """
    category_scores: dict[str, int] = {cat: 0 for cat in CATEGORY_KEYWORDS.keys()}

    for kw in matched_keywords:
        if kw.score > category_scores.get(kw.category, 0):
            category_scores[kw.category] = kw.score

    return category_scores


# =============================================================================
# 검색 쿼리 생성 헬퍼
# =============================================================================

def build_search_queries_for_company(
    company_name: str,
    aliases: list[str] | None = None,
    products: list[str] | None = None,
    persons: list[str] | None = None,
    top_n_keywords: int = 10,
) -> list[str]:
    """
    기업 정보를 기반으로 뉴스 검색 쿼리 생성 (카테고리 다양화 전략)

    7개 리스크 카테고리에서 골고루 키워드를 선택하여
    극단적 키워드 편중을 방지하고 다양한 리스크 신호를 포착.

    Args:
        company_name: 기업명
        aliases: 기업 별칭 목록
        products: 주요 제품/서비스 목록
        persons: 주요 임원/주주 이름 목록
        top_n_keywords: 사용할 상위 N개 키워드

    Returns:
        검색 쿼리 목록
    """
    queries: list[str] = []

    names = [company_name]
    if aliases:
        names.extend(aliases)

    # 카테고리별 대표 검색 키워드 (검색 적중률 높은 것 우선)
    _SEARCH_KEYWORDS_BY_CATEGORY = {
        "LEGAL":  ["소송", "횡령", "검찰"],
        "CREDIT": ["부도", "적자전환", "채무불이행"],
        "GOV":    ["경영권분쟁", "해임", "배임"],
        "OPS":    ["실적악화", "구조조정", "사업중단"],
        "AUDIT":  ["감사의견거절", "부적정"],
        "ESG":    ["환경오염", "안전사고"],
        "SUPPLY": ["공급차질", "수출규제"],
    }

    # 각 카테고리에서 상위 키워드 선택 → 카테고리 다양성 보장
    diverse_keywords: list[str] = []
    for cat_keywords in _SEARCH_KEYWORDS_BY_CATEGORY.values():
        diverse_keywords.extend(cat_keywords[:2])

    # 1. 기업명 + 카테고리 다양화 키워드
    for name in names[:2]:
        for kw in diverse_keywords[:top_n_keywords]:
            queries.append(f"{name} {kw}")

    # 2. 제품/서비스 + 결함/리콜 키워드
    if products:
        for product in products[:3]:
            for kw in ["결함", "리콜", "불량", "사고"]:
                queries.append(f"{product} {kw}")

    # 3. 임원/주주 + 법적 키워드
    if persons:
        for person in persons[:3]:
            for kw in ["구속", "횡령", "배임", "기소"]:
                queries.append(f"{person} {kw}")

    return queries


# =============================================================================
# 통계 헬퍼
# =============================================================================

def get_keyword_stats() -> dict:
    """키워드 사전 통계 반환"""
    return {
        "dart": {
            "count": len(DART_RISK_KEYWORDS),
            "max_score": max(DART_RISK_KEYWORDS.values()),
            "min_score": min(DART_RISK_KEYWORDS.values()),
            "avg_score": sum(DART_RISK_KEYWORDS.values()) / len(DART_RISK_KEYWORDS),
        },
        "news": {
            "count": len(NEWS_RISK_KEYWORDS),
            "max_score": max(NEWS_RISK_KEYWORDS.values()),
            "min_score": min(NEWS_RISK_KEYWORDS.values()),
            "avg_score": sum(NEWS_RISK_KEYWORDS.values()) / len(NEWS_RISK_KEYWORDS),
        },
        "kind": {
            "count": len(KIND_RISK_KEYWORDS),
            "max_score": max(KIND_RISK_KEYWORDS.values()),
            "min_score": min(KIND_RISK_KEYWORDS.values()),
            "avg_score": sum(KIND_RISK_KEYWORDS.values()) / len(KIND_RISK_KEYWORDS),
        },
        "categories": {
            cat: len(config["keywords"])
            for cat, config in CATEGORY_KEYWORDS.items()
        },
        "total_unique_keywords": len(
            set(DART_RISK_KEYWORDS.keys()) |
            set(NEWS_RISK_KEYWORDS.keys()) |
            set(KIND_RISK_KEYWORDS.keys())
        ),
    }
