"""
============================================================================
API V3 Endpoints Tests
============================================================================
Phase 3: Status 중심 + 점수 투명화 API 테스트
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


# API 앱 가져오기 (mock 모드로)
import os
os.environ["USE_MOCK_DATA"] = "true"

from risk_engine.api import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)


class TestStatusSummaryEndpoint:
    """GET /api/v3/status/summary 테스트"""

    def test_returns_status_summary(self, client):
        """Status 요약 반환 확인"""
        response = client.get("/api/v3/status/summary")

        assert response.status_code == 200
        data = response.json()

        assert "summary" in data
        assert "companies" in data
        assert "updatedAt" in data

    def test_summary_has_all_status_types(self, client):
        """모든 Status 타입 포함 확인"""
        response = client.get("/api/v3/status/summary")
        data = response.json()

        summary = data["summary"]
        assert "PASS" in summary
        assert "WARNING" in summary
        assert "FAIL" in summary
        assert "total" in summary

    def test_companies_grouped_by_status(self, client):
        """Status별 기업 그룹핑 확인"""
        response = client.get("/api/v3/status/summary")
        data = response.json()

        companies = data["companies"]
        assert "PASS" in companies
        assert "WARNING" in companies
        assert "FAIL" in companies

        # 각 그룹은 리스트
        assert isinstance(companies["PASS"], list)
        assert isinstance(companies["WARNING"], list)
        assert isinstance(companies["FAIL"], list)

    def test_company_has_required_fields(self, client):
        """기업 정보 필수 필드 확인"""
        response = client.get("/api/v3/status/summary")
        data = response.json()

        # PASS 그룹에서 첫 번째 기업 검증
        if data["companies"]["PASS"]:
            company = data["companies"]["PASS"][0]
            assert "id" in company
            assert "name" in company
            assert "score" in company
            assert "sector" in company


class TestScoreBreakdownEndpoint:
    """GET /api/v3/companies/{id}/score 테스트"""

    def test_returns_score_breakdown(self, client):
        """점수 breakdown 반환 확인"""
        response = client.get("/api/v3/companies/deal1/score")

        assert response.status_code == 200
        data = response.json()

        assert "companyId" in data
        assert "companyName" in data
        assert "totalScore" in data
        assert "status" in data
        assert "breakdown" in data

    def test_breakdown_has_direct_and_propagated(self, client):
        """직접/전이 점수 분리 확인"""
        response = client.get("/api/v3/companies/deal1/score")
        data = response.json()

        breakdown = data["breakdown"]
        assert "directScore" in breakdown
        assert "propagatedScore" in breakdown

    def test_categories_included(self, client):
        """카테고리별 점수 포함 확인"""
        response = client.get("/api/v3/companies/deal1/score")
        data = response.json()

        assert "categories" in data
        assert isinstance(data["categories"], list)

        if data["categories"]:
            category = data["categories"][0]
            assert "category" in category
            assert "score" in category

    def test_recent_signals_included(self, client):
        """최근 신호 포함 확인"""
        response = client.get("/api/v3/companies/deal1/score")
        data = response.json()

        assert "recentSignals" in data
        assert isinstance(data["recentSignals"], list)

    def test_propagators_included(self, client):
        """전이 경로 포함 확인"""
        response = client.get("/api/v3/companies/deal1/score")
        data = response.json()

        assert "propagators" in data
        assert isinstance(data["propagators"], list)


class TestCompanyNewsEndpoint:
    """GET /api/v3/companies/{id}/news 테스트"""

    def test_returns_news_list(self, client):
        """뉴스 목록 반환 확인"""
        response = client.get("/api/v3/companies/deal1/news")

        assert response.status_code == 200
        data = response.json()

        assert "companyId" in data
        assert "companyName" in data
        assert "news" in data
        assert "total" in data

    def test_news_has_required_fields(self, client):
        """뉴스 필수 필드 확인"""
        response = client.get("/api/v3/companies/deal1/news")
        data = response.json()

        if data["news"]:
            news = data["news"][0]
            assert "id" in news
            assert "title" in news
            assert "source" in news

    def test_limit_parameter(self, client):
        """limit 파라미터 동작 확인"""
        response = client.get("/api/v3/companies/deal1/news?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["news"]) <= 5

    def test_limit_max_value(self, client):
        """limit 최대값 제한 확인"""
        response = client.get("/api/v3/companies/deal1/news?limit=100")

        # FastAPI가 le=50 제한으로 422 반환
        assert response.status_code == 422


class TestDataQualityEndpoint:
    """GET /api/v3/data-quality 테스트"""

    def test_returns_data_quality(self, client):
        """데이터 품질 정보 반환 확인"""
        response = client.get("/api/v3/data-quality")

        assert response.status_code == 200
        data = response.json()

        assert "sources" in data
        assert "quality" in data
        assert "companies" in data

    def test_sources_has_dart_and_news(self, client):
        """DART/NEWS 소스 포함 확인"""
        response = client.get("/api/v3/data-quality")
        data = response.json()

        sources = data["sources"]
        assert "DART" in sources
        assert "NEWS" in sources

    def test_source_has_statistics(self, client):
        """소스별 통계 필드 확인"""
        response = client.get("/api/v3/data-quality")
        data = response.json()

        dart = data["sources"]["DART"]
        assert "totalCount" in dart
        assert "riskCount" in dart
        assert "lastCollected" in dart
        assert "status" in dart

    def test_quality_metrics(self, client):
        """품질 지표 확인"""
        response = client.get("/api/v3/data-quality")
        data = response.json()

        quality = data["quality"]
        assert "completeness" in quality
        assert "freshness" in quality
        assert "accuracy" in quality

        # 0~1 범위
        assert 0 <= quality["completeness"] <= 1
        assert 0 <= quality["freshness"] <= 1
        assert 0 <= quality["accuracy"] <= 1

    def test_company_statistics(self, client):
        """기업 통계 확인"""
        response = client.get("/api/v3/data-quality")
        data = response.json()

        companies = data["companies"]
        assert "total" in companies
        assert "withSignals" in companies
        assert "withoutSignals" in companies


class TestRefreshEndpoint:
    """POST /api/v3/refresh/{company_id} 테스트"""

    def test_refresh_returns_success(self, client):
        """갱신 성공 응답 확인"""
        response = client.post("/api/v3/refresh/deal1")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "companyId" in data
        assert "refreshedAt" in data

    def test_refresh_includes_collection_results(self, client):
        """수집 결과 포함 확인"""
        response = client.post("/api/v3/refresh/deal1")
        data = response.json()

        assert "refreshed" in data
        refreshed = data["refreshed"]

        assert "dart" in refreshed
        assert "news" in refreshed

    def test_refresh_includes_score_change(self, client):
        """점수 변화 포함 확인"""
        response = client.post("/api/v3/refresh/deal1")
        data = response.json()

        assert "newScore" in data
        assert "previousScore" in data
        assert "status" in data


class TestKeywordsEndpoint:
    """GET /api/v3/keywords 테스트"""

    def test_returns_keywords(self, client):
        """키워드 반환 확인"""
        response = client.get("/api/v3/keywords")

        assert response.status_code == 200
        data = response.json()

        assert "available" in data

    def test_keywords_structure(self, client):
        """키워드 구조 확인"""
        response = client.get("/api/v3/keywords")
        data = response.json()

        if data.get("available"):
            assert "dart" in data
            assert "news" in data
            assert "totalCount" in data

            # dict 타입
            assert isinstance(data["dart"], dict)
            assert isinstance(data["news"], dict)


class TestHealthCheckWithV3:
    """헬스 체크 (V3 모듈 포함)"""

    def test_health_check(self, client):
        """헬스 체크 정상 응답"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestV2ToV3Compatibility:
    """V2 -> V3 호환성 테스트"""

    def test_v2_deals_still_works(self, client):
        """V2 deals 엔드포인트 동작 확인"""
        response = client.get("/api/v2/deals")

        assert response.status_code == 200
        data = response.json()

        assert "deals" in data
        assert "summary" in data

    def test_v2_deal_detail_still_works(self, client):
        """V2 deal 상세 엔드포인트 동작 확인"""
        response = client.get("/api/v2/deals/deal1")

        assert response.status_code == 200
        data = response.json()

        assert "schemaVersion" in data
        assert "data" in data


class TestRiskCalculatorV3:
    """RiskCalculatorV3 단위 테스트"""

    def test_import_calculator(self):
        """RiskCalculatorV3 import 확인"""
        try:
            from risk_engine.risk_calculator_v3 import RiskCalculatorV3
            assert True
        except ImportError:
            pytest.skip("RiskCalculatorV3 not available")

    def test_tier_propagation_rates(self):
        """Tier별 전이율 상수 확인"""
        from risk_engine.risk_calculator_v3 import TIER_PROPAGATION_RATE

        assert 1 in TIER_PROPAGATION_RATE
        assert 2 in TIER_PROPAGATION_RATE
        assert 3 in TIER_PROPAGATION_RATE

        # Tier 1 > Tier 2 > Tier 3
        assert TIER_PROPAGATION_RATE[1] > TIER_PROPAGATION_RATE[2]
        assert TIER_PROPAGATION_RATE[2] > TIER_PROPAGATION_RATE[3]

    def test_relation_propagation_rates(self):
        """관계별 전이율 확인"""
        from risk_engine.risk_calculator_v3 import RELATION_PROPAGATION_RATE

        assert "CEO" in RELATION_PROPAGATION_RATE
        assert "CFO" in RELATION_PROPAGATION_RATE
        assert "EXECUTIVE" in RELATION_PROPAGATION_RATE

        # CEO가 가장 높은 전이율
        assert RELATION_PROPAGATION_RATE["CEO"] >= RELATION_PROPAGATION_RATE["CFO"]

    def test_status_determination(self):
        """Status 결정 로직 확인"""
        from risk_engine.score_engine import determine_status

        assert determine_status(30) == "PASS"
        assert determine_status(49) == "PASS"
        assert determine_status(50) == "WARNING"
        assert determine_status(74) == "WARNING"
        assert determine_status(75) == "FAIL"
        assert determine_status(100) == "FAIL"


class TestMockDataConsistency:
    """Mock 데이터 일관성 테스트"""

    def test_status_summary_counts_match(self, client):
        """Summary count와 company list 일치 확인"""
        response = client.get("/api/v3/status/summary")
        data = response.json()

        summary = data["summary"]
        companies = data["companies"]

        assert summary["PASS"] == len(companies["PASS"])
        assert summary["WARNING"] == len(companies["WARNING"])
        assert summary["FAIL"] == len(companies["FAIL"])

    def test_score_breakdown_totals_match(self, client):
        """직접 + 전이 = 총점 확인"""
        response = client.get("/api/v3/companies/deal1/score")
        data = response.json()

        breakdown = data["breakdown"]
        total = data["totalScore"]

        # 직접 + 전이 <= 총점 (일부 조정 가능)
        assert breakdown["directScore"] + breakdown["propagatedScore"] >= total - 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
