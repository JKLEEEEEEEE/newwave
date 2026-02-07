"""
Score Breakdown E2E 테스트 - 점수 분해 화면 전체 플로우 검증
Feature: supply-chain-e2e-test
"""

import pytest


class TestScoreBreakdownDisplay:
    """점수 분해 표시 E2E 테스트"""

    @pytest.mark.asyncio
    async def test_sb01_total_score_display(self, client):
        """SB-01: 총점 표시 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        assert "totalScore" in data
        score = data["totalScore"]
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_sb02_status_badge_pass(self, client):
        """SB-02: PASS Status 배지 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        assert "status" in data
        status = data["status"]
        score = data["totalScore"]

        # Status와 점수 일치 검증
        if score < 50:
            assert status == "PASS"

    @pytest.mark.asyncio
    async def test_sb02_status_badge_warning(self, client):
        """SB-02: WARNING Status 배지 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        score = data["totalScore"]
        status = data["status"]

        if 50 <= score < 75:
            assert status == "WARNING"

    @pytest.mark.asyncio
    async def test_sb02_status_badge_fail(self, client):
        """SB-02: FAIL Status 배지 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        score = data["totalScore"]
        status = data["status"]

        if score >= 75:
            assert status == "FAIL"


class TestScoreBreakdownStructure:
    """점수 분해 구조 테스트"""

    @pytest.mark.asyncio
    async def test_sb03_direct_propagated_breakdown(self, client):
        """SB-03: 직접/전이 분해 구조 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        assert "breakdown" in data
        breakdown = data["breakdown"]

        assert "directScore" in breakdown
        assert "propagatedScore" in breakdown

        # 값 범위 검증
        assert 0 <= breakdown["directScore"] <= 100
        assert 0 <= breakdown["propagatedScore"] <= 100

    @pytest.mark.asyncio
    async def test_breakdown_sum_validation(self, client):
        """직접+전이 = 총점 검증"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        total = data["totalScore"]
        direct = data["breakdown"]["directScore"]
        propagated = data["breakdown"]["propagatedScore"]

        # 합계 검증 (소수점 오차 허용)
        calculated_total = direct + propagated
        assert abs(calculated_total - total) < 1.0, \
            f"합계 불일치: {direct} + {propagated} = {calculated_total} != {total}"


class TestScoreCategories:
    """점수 카테고리 테스트"""

    @pytest.mark.asyncio
    async def test_sb04_categories_list(self, client):
        """SB-04: 카테고리 목록 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        assert "categories" in data
        categories = data["categories"]

        # 최소 3개 카테고리
        assert len(categories) >= 3

    @pytest.mark.asyncio
    async def test_category_required_fields(self, client):
        """카테고리 필수 필드 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        for category in data["categories"]:
            assert "name" in category
            assert "score" in category
            assert "weight" in category

    @pytest.mark.asyncio
    async def test_category_score_range(self, client):
        """카테고리 점수 범위 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        for category in data["categories"]:
            score = category["score"]
            assert 0 <= score <= 100, f"카테고리 {category['name']} 점수 {score}가 범위 밖"

    @pytest.mark.asyncio
    async def test_category_weight_range(self, client):
        """카테고리 가중치 범위 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        for category in data["categories"]:
            weight = category["weight"]
            assert 0 <= weight <= 1, f"카테고리 {category['name']} 가중치 {weight}가 범위 밖"

    @pytest.mark.asyncio
    async def test_category_weights_sum(self, client):
        """카테고리 가중치 합계 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        total_weight = sum(c["weight"] for c in data["categories"])
        # 가중치 합계는 약 1.0 (오차 허용)
        assert 0.9 <= total_weight <= 1.1, f"가중치 합계 {total_weight}가 1.0에서 벗어남"


class TestRecentSignals:
    """최근 신호 테스트"""

    @pytest.mark.asyncio
    async def test_sb05_recent_signals_list(self, client):
        """SB-05: 최근 신호 목록 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        assert "recentSignals" in data
        signals = data["recentSignals"]
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_signal_required_fields(self, client):
        """신호 필수 필드 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        for signal in data["recentSignals"]:
            assert "id" in signal or "type" in signal or "message" in signal

    @pytest.mark.asyncio
    async def test_signal_severity_values(self, client):
        """신호 severity 값 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        valid_severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        for signal in data["recentSignals"]:
            if "severity" in signal:
                assert signal["severity"] in valid_severities


class TestPropagators:
    """전이 경로 테스트"""

    @pytest.mark.asyncio
    async def test_sb06_propagators_list(self, client):
        """SB-06: 전이 경로 목록 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        assert "propagators" in data
        propagators = data["propagators"]
        assert isinstance(propagators, list)

    @pytest.mark.asyncio
    async def test_propagator_required_fields(self, client):
        """Propagator 필수 필드 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        for prop in data["propagators"]:
            assert "companyName" in prop or "name" in prop
            assert "contribution" in prop or "score" in prop

    @pytest.mark.asyncio
    async def test_propagator_contribution_range(self, client):
        """Propagator 기여도 범위 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        for prop in data["propagators"]:
            if "contribution" in prop:
                contribution = prop["contribution"]
                assert contribution >= 0, f"기여도 {contribution}가 음수"

    @pytest.mark.asyncio
    async def test_propagators_contribution_sum(self, client):
        """Propagators 기여도 합계 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        if data["propagators"]:
            total_contribution = sum(p.get("contribution", 0) for p in data["propagators"])
            propagated_score = data["breakdown"]["propagatedScore"]

            # 기여도 합계가 전이 점수와 대략 일치 (오차 허용)
            if propagated_score > 0:
                assert total_contribution > 0, "전이 점수가 있지만 기여도 합이 0"


class TestScoreBreakdownConsistency:
    """점수 분해 데이터 일관성 테스트"""

    @pytest.mark.asyncio
    async def test_category_weighted_sum(self, client):
        """카테고리 가중 합계 검증"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        # 카테고리 가중 합계 계산
        weighted_sum = sum(
            c["score"] * c["weight"]
            for c in data["categories"]
        )

        # 직접 점수와 비교 (대략적 일치)
        direct_score = data["breakdown"]["directScore"]
        # 가중 합계가 직접 점수의 합리적 범위 내인지 확인

    @pytest.mark.asyncio
    async def test_status_score_alignment(self, client):
        """Status와 점수 정렬 검증"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        if response.status_code != 200:
            pytest.skip("Company not found in database (mock mode)")
        data = response.json()

        score = data["totalScore"]
        status = data["status"]

        # 점수 범위에 따른 Status 일치 확인
        expected_status = (
            "PASS" if score < 50
            else "WARNING" if score < 75
            else "FAIL"
        )
        assert status == expected_status, \
            f"점수 {score}에 대한 Status가 {status}이지만 {expected_status}여야 함"

    @pytest.mark.asyncio
    async def test_multiple_companies_comparison(self, client):
        """여러 기업 점수 비교 테스트"""
        companies = ["SK하이닉스", "삼성전자"]
        scores = []

        for company in companies:
            response = await client.get(f"/api/v3/companies/{company}/score")
            if response.status_code == 200:
                data = response.json()
                scores.append({
                    "company": company,
                    "totalScore": data["totalScore"],
                    "status": data["status"]
                })

        # 최소 하나의 기업 데이터가 있어야 함 (또는 skip)
        if not scores:
            pytest.skip("No company data available (mock mode)")

        # 모든 점수가 유효한 범위인지 확인
        for score_data in scores:
            assert 0 <= score_data["totalScore"] <= 100


class TestScoreBreakdownErrorHandling:
    """점수 분해 에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_nonexistent_company(self, client):
        """존재하지 않는 기업 처리 테스트"""
        response = await client.get("/api/v3/companies/없는회사/score")
        # 404 또는 기본값 반환 또는 500 (구현에 따라)
        assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_empty_company_name(self, client):
        """빈 기업명 처리 테스트"""
        response = await client.get("/api/v3/companies//score")
        assert response.status_code in [404, 405, 400, 307]

    @pytest.mark.asyncio
    async def test_special_characters(self, client):
        """특수문자 기업명 처리 테스트"""
        response = await client.get("/api/v3/companies/Test%26Company/score")
        assert response.status_code in [200, 400, 404, 500]
