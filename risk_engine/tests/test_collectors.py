"""
데이터 수집기 테스트 (Risk Graph v3)
pytest risk_engine/tests/test_collectors.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from risk_engine.dart_collector_v2 import (
    DartCollectorV2,
    DisclosureData,
    CollectionResult,
    DART_ENDPOINTS,
    DISCLOSURE_TYPES,
    collect_all_disclosures,
    get_high_risk_disclosures,
)
from risk_engine.news_collector_v2 import (
    NewsCollectorV2,
    NewsData,
    CollectionResult as NewsCollectionResult,
    NEWS_SOURCES,
    FILTER_CONFIG,
    collect_news_for_companies,
    get_risk_news,
)
from risk_engine.validator import DataValidator, ValidationResult


# =============================================================================
# DART Collector 테스트
# =============================================================================

class TestDisclosureData:
    """DisclosureData 데이터클래스 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        disclosure = DisclosureData(
            rcept_no="20240101000001",
            corp_code="00126380",
            corp_name="SK하이닉스",
            title="감사보고서",
            filing_date="20240101",
        )
        assert disclosure.rcept_no == "20240101000001"
        assert disclosure.source == "DART"
        assert disclosure.fetched_at is not None

    def test_id_generation(self):
        """ID 생성"""
        disclosure = DisclosureData(
            rcept_no="20240101000001",
            corp_code="00126380",
            corp_name="SK하이닉스",
            title="감사보고서",
            filing_date="20240101",
        )
        assert disclosure.id == "DISC_20240101000001"

    def test_source_url_generation(self):
        """소스 URL 생성"""
        disclosure = DisclosureData(
            rcept_no="20240101000001",
            corp_code="00126380",
            corp_name="SK하이닉스",
            title="감사보고서",
            filing_date="20240101",
        )
        assert "20240101000001" in disclosure.source_url

    def test_to_dict(self):
        """딕셔너리 변환"""
        disclosure = DisclosureData(
            rcept_no="20240101000001",
            corp_code="00126380",
            corp_name="SK하이닉스",
            title="감사보고서",
            filing_date="20240101",
        )
        d = disclosure.to_dict()
        assert "id" in d
        assert "rcept_no" in d
        assert "corp_code" in d

    def test_to_neo4j_props(self):
        """Neo4j 속성 변환"""
        disclosure = DisclosureData(
            rcept_no="20240101000001",
            corp_code="00126380",
            corp_name="SK하이닉스",
            title="감사보고서",
            filing_date="20240101",
        )
        props = disclosure.to_neo4j_props()
        assert "rceptNo" in props  # camelCase
        assert "corpCode" in props


class TestDartCollectorV2:
    """DartCollectorV2 클래스 테스트"""

    def test_init_with_api_key(self):
        """API 키로 초기화"""
        collector = DartCollectorV2(api_key="test_key")
        assert collector.api_key == "test_key"

    def test_init_without_api_key_raises(self):
        """API 키 없으면 에러"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError):
                DartCollectorV2(api_key=None)

    @patch("risk_engine.dart_collector_v2.requests.get")
    def test_collect_disclosures_success(self, mock_get):
        """공시 수집 성공"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "000",
            "list": [
                {
                    "rcept_no": "20240101000001",
                    "corp_code": "00126380",
                    "corp_name": "SK하이닉스",
                    "report_nm": "감사보고서 - 의견거절",
                    "rcept_dt": "20240101",
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = DartCollectorV2(api_key="test_key")
        result = collector.collect_disclosures("00126380", days=30)

        assert isinstance(result, CollectionResult)
        assert result.total_fetched == 1
        assert result.total_valid == 1

    @patch("risk_engine.dart_collector_v2.requests.get")
    def test_collect_disclosures_api_error(self, mock_get):
        """API 오류 처리"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "013",
            "message": "no data"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = DartCollectorV2(api_key="test_key")
        result = collector.collect_disclosures("00126380", days=30)

        assert len(result.errors) > 0

    def test_analyze_disclosure(self):
        """공시 분석"""
        collector = DartCollectorV2(api_key="test_key")
        disclosure = DisclosureData(
            rcept_no="20240101000001",
            corp_code="00126380",
            corp_name="SK하이닉스",
            title="감사보고서 - 의견거절",
            filing_date="20240101",
        )

        analyzed = collector.analyze_disclosure(disclosure)

        assert analyzed.match_result is not None
        assert analyzed.match_result.keyword_count > 0
        assert analyzed.score_result is not None
        assert analyzed.category is not None

    def test_classify_disclosure_type(self):
        """공시 유형 분류"""
        collector = DartCollectorV2(api_key="test_key")

        assert collector._classify_disclosure_type("감사보고서") == "AUDIT"
        assert collector._classify_disclosure_type("최대주주 변경") == "GOVERNANCE"
        assert collector._classify_disclosure_type("횡령 혐의") == "RISK"
        assert collector._classify_disclosure_type("일반 공시") == "OTHER"


class TestDartCollectionResult:
    """CollectionResult 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        result = CollectionResult()
        assert result.total_fetched == 0
        assert result.disclosures == []

    def test_to_dict(self):
        """딕셔너리 변환"""
        result = CollectionResult(
            total_fetched=10,
            total_valid=8,
            high_risk_count=2,
        )
        d = result.to_dict()
        assert d["total_fetched"] == 10
        assert d["total_valid"] == 8
        assert d["high_risk_count"] == 2


class TestHighRiskDisclosures:
    """고위험 공시 필터링 테스트"""

    def test_filter_high_risk(self):
        """고위험 공시 필터링"""
        from risk_engine.score_engine import ScoreResult

        disclosures = [
            DisclosureData(
                rcept_no="001", corp_code="123", corp_name="A",
                title="횡령", filing_date="20240101"
            ),
            DisclosureData(
                rcept_no="002", corp_code="123", corp_name="A",
                title="일반", filing_date="20240101"
            ),
        ]

        # 점수 설정
        disclosures[0].score_result = ScoreResult(
            raw_score=60, decayed_score=60, confidence=0.8,
            final_score=55.0, days_old=0, decay_rate=1.0,
            status="WARNING", sentiment="부정",
            category_breakdown={}
        )
        disclosures[1].score_result = ScoreResult(
            raw_score=10, decayed_score=10, confidence=0.5,
            final_score=5.0, days_old=0, decay_rate=1.0,
            status="PASS", sentiment="중립",
            category_breakdown={}
        )

        result = CollectionResult(disclosures=disclosures)
        high_risk = get_high_risk_disclosures(result, threshold=50.0)

        assert len(high_risk) == 1
        assert high_risk[0].rcept_no == "001"


# =============================================================================
# News Collector 테스트
# =============================================================================

class TestNewsData:
    """NewsData 데이터클래스 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        news = NewsData(
            title="삼성전자 횡령 혐의",
            url="https://example.com/news/1",
            published_at=datetime.now(),
            source="구글뉴스",
        )
        assert news.title == "삼성전자 횡령 혐의"
        assert news.fetched_at is not None

    def test_id_and_hash_generation(self):
        """ID 및 해시 생성"""
        news = NewsData(
            title="테스트",
            url="https://example.com/news/1",
            published_at=datetime.now(),
            source="구글뉴스",
        )
        assert news.id.startswith("NEWS_")
        assert len(news.url_hash) == 32  # MD5

    def test_days_old_calculation(self):
        """연령 계산"""
        yesterday = datetime.now() - timedelta(days=1)
        news = NewsData(
            title="테스트",
            url="https://example.com/news/1",
            published_at=yesterday,
            source="구글뉴스",
        )
        assert news.days_old == 1

    def test_is_risk_without_analysis(self):
        """분석 전 리스크 여부"""
        news = NewsData(
            title="테스트",
            url="https://example.com/news/1",
            published_at=datetime.now(),
            source="구글뉴스",
        )
        assert news.is_risk == False

    def test_publisher_confidence(self):
        """주요 언론사 신뢰도"""
        news_major = NewsData(
            title="테스트",
            url="https://example.com/1",
            published_at=datetime.now(),
            source="구글뉴스",
            publisher="연합뉴스",
        )
        news_minor = NewsData(
            title="테스트",
            url="https://example.com/2",
            published_at=datetime.now(),
            source="구글뉴스",
            publisher="Unknown",
        )
        assert news_major.confidence > news_minor.confidence


class TestNewsCollectorV2:
    """NewsCollectorV2 클래스 테스트"""

    def test_init(self):
        """초기화"""
        collector = NewsCollectorV2()
        assert len(collector.seen_urls) == 0

    def test_reset_session(self):
        """세션 리셋"""
        collector = NewsCollectorV2()
        collector.seen_urls.add("test")
        collector.reset_session()
        assert len(collector.seen_urls) == 0

    def test_generate_queries(self):
        """검색 쿼리 생성"""
        collector = NewsCollectorV2()
        queries = collector.generate_queries(
            company_name="삼성전자",
            aliases=["삼성"],
            products=["갤럭시"],
            persons=["이재용"],
        )
        assert len(queries) > 0
        assert "삼성전자" in queries

    def test_deduplicate(self):
        """중복 제거"""
        collector = NewsCollectorV2()
        news_list = [
            NewsData(title="A", url="https://a.com", published_at=datetime.now(), source="G"),
            NewsData(title="B", url="https://a.com", published_at=datetime.now(), source="G"),  # 중복
            NewsData(title="C", url="https://b.com", published_at=datetime.now(), source="G"),
        ]

        unique = collector.deduplicate(news_list)
        assert len(unique) == 2

    def test_analyze_news(self):
        """뉴스 분석"""
        collector = NewsCollectorV2()
        news = NewsData(
            title="삼성전자 횡령 혐의 조사",
            url="https://example.com/news/1",
            published_at=datetime.now(),
            source="구글뉴스",
        )

        analyzed = collector.analyze_news(news)

        assert analyzed.match_result is not None
        assert analyzed.match_result.keyword_count > 0
        assert analyzed.is_risk == True

    def test_apply_filters_age(self):
        """연령 필터"""
        collector = NewsCollectorV2()

        old_news = NewsData(
            title="This is an old news article title for testing",
            url="https://a.com",
            published_at=datetime.now() - timedelta(days=60),
            source="G",
        )
        new_news = NewsData(
            title="This is a new news article title for testing",
            url="https://b.com",
            published_at=datetime.now(),
            source="G",
        )

        assert collector._apply_filters(old_news) == False
        assert collector._apply_filters(new_news) == True

    def test_apply_filters_title_length(self):
        """제목 길이 필터"""
        collector = NewsCollectorV2()

        short = NewsData(title="짧음", url="https://a.com", published_at=datetime.now(), source="G")
        long = NewsData(title="충분히 긴 뉴스 제목입니다", url="https://b.com", published_at=datetime.now(), source="G")

        assert collector._apply_filters(short) == False
        assert collector._apply_filters(long) == True

    @patch("risk_engine.news_collector_v2.requests.get")
    def test_fetch_from_source(self, mock_get):
        """소스에서 뉴스 가져오기"""
        mock_response = Mock()
        # UTF-8 인코딩된 XML
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss>
            <channel>
                <item>
                    <title>Samsung Embezzlement - Reuters</title>
                    <link>https://news.example.com/1</link>
                    <pubDate>Thu, 01 Feb 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """
        mock_response.content = xml_content.encode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = NewsCollectorV2()
        news_list = collector._fetch_from_source("Samsung", "GOOGLE_RSS", limit=10)

        assert len(news_list) == 1
        assert "Embezzlement" in news_list[0].title


class TestNewsCollectionResult:
    """NewsCollectionResult 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        result = NewsCollectionResult(
            query="삼성전자",
            total_fetched=20,
            total_valid=15,
            risk_news_count=5,
        )
        d = result.to_dict()
        assert d["query"] == "삼성전자"
        assert d["total_fetched"] == 20
        assert d["risk_news_count"] == 5


# =============================================================================
# Validator 테스트
# =============================================================================

class TestDataValidator:
    """DataValidator 테스트"""

    def test_validate_news_success(self):
        """뉴스 검증 성공"""
        validator = DataValidator()
        data = {
            "title": "테스트 뉴스 제목입니다",
            "source": "구글뉴스",
            "url": "https://example.com/news/1",
            "published_at": "2024-01-01T12:00:00",
        }
        result = validator.validate(data, "News")
        assert result.is_valid == True
        assert result.normalized_data is not None

    def test_validate_news_missing_field(self):
        """뉴스 필수 필드 누락"""
        validator = DataValidator()
        data = {
            "title": "테스트",
            # source 누락
            "url": "https://example.com",
        }
        result = validator.validate(data, "News")
        assert result.is_valid == False
        assert len(result.errors) > 0

    def test_validate_disclosure_success(self):
        """공시 검증 성공"""
        validator = DataValidator()
        data = {
            "rcept_no": "20240101000001",
            "title": "감사보고서",
            "corp_code": "00126380",
            "filing_date": "20240101",
        }
        result = validator.validate(data, "Disclosure")
        assert result.is_valid == True

    def test_validate_range_error(self):
        """범위 검증 오류"""
        validator = DataValidator()
        data = {
            "title": "테스트",
            "source": "G",
            "url": "https://a.com",
            "published_at": "2024-01-01",
            "risk_score": 150,  # 범위 초과
        }
        result = validator.validate(data, "News")
        assert result.is_valid == False

    def test_normalize_url(self):
        """URL 정규화"""
        validator = DataValidator()
        data = {
            "title": "Test news article title",
            "source": "Google",
            "url": "https://example.com/news",  # 정상 URL
            "published_at": "2024-01-01",
        }
        result = validator.validate(data, "News")
        assert result.is_valid == True
        assert result.normalized_data["url"].startswith("https://")
        assert "url_hash" in result.normalized_data

    def test_normalize_date(self):
        """날짜 정규화"""
        validator = DataValidator()
        data = {
            "title": "테스트 뉴스",
            "source": "G",
            "url": "https://a.com",
            "published_at": "20240101",  # YYYYMMDD
        }
        result = validator.validate(data, "News")
        assert result.is_valid == True
        assert "-" in result.normalized_data["published_at"]  # ISO 형식


class TestValidatorHelpers:
    """Validator 헬퍼 함수 테스트"""

    def test_validate_batch(self):
        """배치 검증"""
        from risk_engine.validator import validate_batch, get_validation_summary

        data_list = [
            {"title": "뉴스 1", "source": "G", "url": "https://a.com", "published_at": "2024-01-01"},
            {"title": "뉴스 2", "source": "G", "url": "https://b.com", "published_at": "2024-01-02"},
            {"title": "잘못된 데이터"},  # 필수 필드 누락
        ]

        valid_data, results = validate_batch(data_list, "News")

        assert len(valid_data) == 2
        assert len(results) == 3

        summary = get_validation_summary(results)
        assert summary["total"] == 3
        assert summary["valid"] == 2
        assert summary["invalid"] == 1
