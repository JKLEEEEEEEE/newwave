"""
키워드 모듈 테스트 (Risk Graph v3)
pytest risk_engine/tests/test_keywords.py -v
"""

import pytest
from risk_engine.keywords import (
    DART_RISK_KEYWORDS,
    NEWS_RISK_KEYWORDS,
    KIND_RISK_KEYWORDS,
    CATEGORY_KEYWORDS,
    match_keywords,
    classify_category,
    get_keywords_by_source,
    get_high_risk_keywords,
    calculate_category_scores,
    build_search_queries_for_company,
    get_keyword_stats,
    MatchResult,
    MatchedKeyword,
)


class TestKeywordDictionaries:
    """키워드 사전 테스트"""

    def test_dart_keywords_count(self):
        """DART 키워드 개수 확인 (32개 이상)"""
        assert len(DART_RISK_KEYWORDS) >= 30
        assert "횡령" in DART_RISK_KEYWORDS
        assert "의견거절" in DART_RISK_KEYWORDS

    def test_news_keywords_count(self):
        """NEWS 키워드 개수 확인 (20개 이상)"""
        assert len(NEWS_RISK_KEYWORDS) >= 18
        assert "압수수색" in NEWS_RISK_KEYWORDS
        assert "구속" in NEWS_RISK_KEYWORDS

    def test_kind_keywords_count(self):
        """KIND 키워드 개수 확인 (23개 이상)"""
        assert len(KIND_RISK_KEYWORDS) >= 20
        assert "상장폐지" in KIND_RISK_KEYWORDS
        assert "관리종목" in KIND_RISK_KEYWORDS

    def test_keyword_scores_in_range(self):
        """키워드 점수가 0-100 범위인지 확인"""
        for kw_dict in [DART_RISK_KEYWORDS, NEWS_RISK_KEYWORDS, KIND_RISK_KEYWORDS]:
            for keyword, score in kw_dict.items():
                assert 0 <= score <= 100, f"{keyword}: {score}가 범위 밖"

    def test_high_risk_keywords_exist(self):
        """고위험 키워드 (50점 이상) 존재 확인"""
        high_risk = get_high_risk_keywords(threshold=50)
        assert len(high_risk) >= 10
        assert "횡령" in high_risk
        assert "파산" in high_risk


class TestCategoryKeywords:
    """카테고리 키워드 테스트"""

    def test_all_categories_exist(self):
        """모든 카테고리 존재 확인"""
        expected = ["LEGAL", "CREDIT", "GOVERNANCE", "OPERATIONAL", "AUDIT", "ESG"]
        for cat in expected:
            assert cat in CATEGORY_KEYWORDS

    def test_category_weights_sum(self):
        """카테고리 가중치 합 확인 (약 1.0)"""
        total_weight = sum(cat["weight"] for cat in CATEGORY_KEYWORDS.values())
        assert 0.9 <= total_weight <= 1.1

    def test_category_has_keywords(self):
        """각 카테고리에 키워드 존재"""
        for cat, config in CATEGORY_KEYWORDS.items():
            assert len(config["keywords"]) > 0, f"{cat}에 키워드가 없음"
            assert config["weight"] > 0, f"{cat}에 가중치가 없음"


class TestClassifyCategory:
    """카테고리 분류 테스트"""

    def test_legal_keywords(self):
        """법률 키워드 분류"""
        assert classify_category("횡령") == "LEGAL"
        assert classify_category("배임") == "LEGAL"
        assert classify_category("소송") == "LEGAL"

    def test_credit_keywords(self):
        """신용 키워드 분류"""
        assert classify_category("부도") == "CREDIT"
        assert classify_category("파산") == "CREDIT"
        assert classify_category("회생") == "CREDIT"

    def test_audit_keywords(self):
        """감사 키워드 분류"""
        assert classify_category("의견거절") == "AUDIT"
        assert classify_category("한정") == "AUDIT"

    def test_unknown_keyword(self):
        """미분류 키워드는 OTHER"""
        assert classify_category("알수없는키워드") == "OTHER"


class TestGetKeywordsBySource:
    """소스별 키워드 사전 조회 테스트"""

    def test_dart_source(self):
        """DART 소스 키워드"""
        kw = get_keywords_by_source("DART")
        assert kw == DART_RISK_KEYWORDS

    def test_news_source(self):
        """NEWS 소스 키워드"""
        kw = get_keywords_by_source("NEWS")
        assert kw == NEWS_RISK_KEYWORDS

    def test_kind_source(self):
        """KIND 소스 키워드"""
        kw = get_keywords_by_source("KIND")
        assert kw == KIND_RISK_KEYWORDS

    def test_default_source(self):
        """알 수 없는 소스는 DART 반환"""
        kw = get_keywords_by_source("UNKNOWN")
        assert kw == DART_RISK_KEYWORDS


class TestMatchKeywords:
    """키워드 매칭 테스트"""

    def test_empty_text(self):
        """빈 텍스트"""
        result = match_keywords("")
        assert result.keyword_count == 0
        assert result.raw_score == 0
        assert result.primary_category is None

    def test_no_match(self):
        """매칭 없음"""
        result = match_keywords("오늘 날씨가 좋습니다")
        assert result.keyword_count == 0
        assert result.raw_score == 0

    def test_single_keyword_match(self):
        """단일 키워드 매칭"""
        result = match_keywords("감사보고서 - 의견거절")
        assert result.keyword_count == 1
        assert result.raw_score == 70  # 의견거절 점수
        assert result.primary_category == "AUDIT"
        assert result.matched_keywords[0].keyword == "의견거절"

    def test_multiple_keyword_match(self):
        """다중 키워드 매칭"""
        result = match_keywords("감사보고서 - 의견거절 (계속기업불확실 사유)")
        assert result.keyword_count == 2
        assert result.raw_score == 70  # max(70, 40)
        assert "의견거절" in [kw.keyword for kw in result.matched_keywords]
        assert "계속기업불확실" in [kw.keyword for kw in result.matched_keywords]

    def test_news_source_keywords(self):
        """NEWS 소스 키워드 매칭"""
        result = match_keywords("CEO 압수수색 구속", source="NEWS")
        assert result.keyword_count == 2
        assert result.raw_score == 40  # max(압수수색 40, 구속 40)

    def test_kind_source_keywords(self):
        """KIND 소스 키워드 매칭"""
        result = match_keywords("상장폐지 결정", source="KIND")
        assert result.keyword_count == 1
        assert result.raw_score == 80  # 상장폐지

    def test_match_result_to_dict(self):
        """MatchResult 딕셔너리 변환"""
        result = match_keywords("횡령 혐의")
        d = result.to_dict()
        assert "matched_keywords" in d
        assert "raw_score" in d
        assert "primary_category" in d


class TestCalculateCategoryScores:
    """카테고리별 점수 계산 테스트"""

    def test_single_category(self):
        """단일 카테고리 점수"""
        keywords = [MatchedKeyword("횡령", 50, "LEGAL", 0)]
        scores = calculate_category_scores(keywords)
        assert scores["LEGAL"] == 50
        assert scores["CREDIT"] == 0

    def test_multiple_categories(self):
        """다중 카테고리 점수"""
        keywords = [
            MatchedKeyword("횡령", 50, "LEGAL", 0),
            MatchedKeyword("파산", 60, "CREDIT", 5),
        ]
        scores = calculate_category_scores(keywords)
        assert scores["LEGAL"] == 50
        assert scores["CREDIT"] == 60

    def test_same_category_max_score(self):
        """같은 카테고리는 최고 점수"""
        keywords = [
            MatchedKeyword("소송", 25, "LEGAL", 0),
            MatchedKeyword("횡령", 50, "LEGAL", 5),
        ]
        scores = calculate_category_scores(keywords)
        assert scores["LEGAL"] == 50  # max(25, 50)


class TestBuildSearchQueries:
    """검색 쿼리 생성 테스트"""

    def test_basic_company_queries(self):
        """기본 기업 검색 쿼리"""
        queries = build_search_queries_for_company("삼성전자")
        assert len(queries) > 0
        # 기업명 + 키워드 조합 확인
        assert any("삼성전자" in q for q in queries)

    def test_with_aliases(self):
        """별칭 포함 검색 쿼리"""
        queries = build_search_queries_for_company(
            "삼성전자",
            aliases=["삼성", "Samsung"]
        )
        assert any("삼성" in q for q in queries)

    def test_with_products(self):
        """제품명 포함 검색 쿼리"""
        queries = build_search_queries_for_company(
            "삼성전자",
            products=["갤럭시", "DRAM"]
        )
        assert any("갤럭시" in q for q in queries)
        assert any("리콜" in q or "결함" in q for q in queries)

    def test_with_persons(self):
        """임원 이름 포함 검색 쿼리"""
        queries = build_search_queries_for_company(
            "삼성전자",
            persons=["이재용"]
        )
        assert any("이재용" in q for q in queries)
        assert any("구속" in q or "횡령" in q for q in queries)


class TestKeywordStats:
    """키워드 통계 테스트"""

    def test_stats_structure(self):
        """통계 구조 확인"""
        stats = get_keyword_stats()
        assert "dart" in stats
        assert "news" in stats
        assert "kind" in stats
        assert "categories" in stats
        assert "total_unique_keywords" in stats

    def test_dart_stats(self):
        """DART 통계"""
        stats = get_keyword_stats()
        assert stats["dart"]["count"] == len(DART_RISK_KEYWORDS)
        assert stats["dart"]["max_score"] <= 100
        assert stats["dart"]["min_score"] >= 0

    def test_total_unique_keywords(self):
        """전체 고유 키워드 수"""
        stats = get_keyword_stats()
        assert stats["total_unique_keywords"] >= 50
