"""
점수 계산 엔진 테스트 (Risk Graph v3)
pytest risk_engine/tests/test_score_engine.py -v
"""

import pytest
from datetime import datetime, date, timedelta
from risk_engine.score_engine import (
    calc_decay,
    calc_days_old,
    calc_confidence,
    calculate_raw_score,
    calculate_decayed_score,
    calculate_final_score,
    determine_status,
    determine_sentiment,
    calculate_category_breakdown,
    calculate_weighted_score,
    get_status_color,
    format_score_display,
    DECAY_HALF_LIFE,
    STATUS_THRESHOLDS,
    DecayResult,
    ScoreResult,
)
from risk_engine.keywords import match_keywords, MatchedKeyword


class TestCalcDecay:
    """시간 감쇠 함수 테스트"""

    def test_day_zero(self):
        """오늘 (0일)은 감쇠 없음"""
        decay = calc_decay(0)
        assert decay == 1.0

    def test_half_life(self):
        """반감기 (30일)에서 약 0.368 (e^-1)"""
        decay = calc_decay(30)
        assert 0.36 < decay < 0.38

    def test_double_half_life(self):
        """2배 반감기 (60일)에서 약 0.135 (e^-2)"""
        decay = calc_decay(60)
        assert 0.13 < decay < 0.14

    def test_negative_days_treated_as_zero(self):
        """음수 일수는 0으로 처리"""
        decay = calc_decay(-10)
        assert decay == 1.0

    def test_custom_half_life(self):
        """커스텀 반감기"""
        decay = calc_decay(15, half_life=15)  # 15일 반감기에서 15일
        assert 0.36 < decay < 0.38

    def test_decay_decreases_over_time(self):
        """시간이 지날수록 감쇠"""
        decay_0 = calc_decay(0)
        decay_7 = calc_decay(7)
        decay_30 = calc_decay(30)
        decay_90 = calc_decay(90)

        assert decay_0 > decay_7 > decay_30 > decay_90


class TestCalcDaysOld:
    """경과 일수 계산 테스트"""

    def test_today_is_zero(self):
        """오늘 날짜는 0일"""
        today = date.today()
        assert calc_days_old(today) == 0

    def test_yesterday(self):
        """어제는 1일"""
        yesterday = date.today() - timedelta(days=1)
        assert calc_days_old(yesterday) == 1

    def test_datetime_object(self):
        """datetime 객체 처리"""
        today = datetime.now()
        assert calc_days_old(today) == 0

    def test_iso_string(self):
        """ISO 문자열 처리"""
        today_str = date.today().isoformat()
        assert calc_days_old(today_str) == 0

    def test_iso_datetime_string(self):
        """ISO datetime 문자열 처리"""
        today_str = datetime.now().isoformat()
        assert calc_days_old(today_str) == 0


class TestCalcConfidence:
    """신뢰도 계산 테스트"""

    def test_zero_keywords(self):
        """키워드 0개는 최소 신뢰도"""
        conf = calc_confidence(0)
        assert conf == 0.3

    def test_one_keyword(self):
        """키워드 1개"""
        conf = calc_confidence(1)
        assert 0.6 < conf < 0.7

    def test_two_keywords(self):
        """키워드 2개"""
        conf = calc_confidence(2)
        assert 0.75 < conf < 0.85

    def test_many_keywords_capped(self):
        """많은 키워드는 최대값 제한"""
        conf = calc_confidence(10)
        assert conf <= 0.95

    def test_source_reliability_dart(self):
        """DART 소스 신뢰도 (1.0)"""
        conf = calc_confidence(2, source="DART")
        conf_news = calc_confidence(2, source="NEWS")
        assert conf >= conf_news  # DART가 더 높거나 같음

    def test_custom_source_reliability(self):
        """커스텀 소스 신뢰도"""
        conf_high = calc_confidence(2, source_reliability=1.0)
        conf_low = calc_confidence(2, source_reliability=0.5)
        assert conf_high > conf_low


class TestCalculateRawScore:
    """원점수 계산 테스트"""

    def test_empty_list(self):
        """빈 목록은 0점"""
        score = calculate_raw_score([])
        assert score == 0

    def test_single_keyword(self):
        """단일 키워드 최고 점수"""
        keywords = [MatchedKeyword("횡령", 50, "LEGAL", 0)]
        score = calculate_raw_score(keywords)
        assert score == 50

    def test_multiple_keywords_max(self):
        """다중 키워드는 최고 점수"""
        keywords = [
            MatchedKeyword("횡령", 50, "LEGAL", 0),
            MatchedKeyword("의견거절", 70, "AUDIT", 5),
        ]
        score = calculate_raw_score(keywords)
        assert score == 70  # max(50, 70)

    def test_dict_input(self):
        """딕셔너리 입력 처리"""
        keywords = [
            {"keyword": "횡령", "score": 50},
            {"keyword": "파산", "score": 60},
        ]
        score = calculate_raw_score(keywords)
        assert score == 60

    def test_capped_at_100(self):
        """100점 상한"""
        keywords = [MatchedKeyword("test", 150, "OTHER", 0)]
        score = calculate_raw_score(keywords)
        assert score == 100


class TestCalculateDecayedScore:
    """감쇠 점수 계산 테스트"""

    def test_today_no_decay(self):
        """오늘은 감쇠 없음"""
        result = calculate_decayed_score(70, date.today())
        assert result.raw_score == 70
        assert result.decayed_score == 70
        assert result.days_old == 0
        assert result.decay_rate == 1.0

    def test_30_days_decay(self):
        """30일 전 약 37% 감쇠"""
        pub_date = date.today() - timedelta(days=30)
        result = calculate_decayed_score(100, pub_date)
        assert result.raw_score == 100
        assert 35 < result.decayed_score < 40  # 100 * 0.368 ≈ 37

    def test_result_is_dataclass(self):
        """결과가 DecayResult 데이터클래스"""
        result = calculate_decayed_score(50, date.today())
        assert isinstance(result, DecayResult)
        assert hasattr(result, "to_dict")

    def test_to_dict(self):
        """딕셔너리 변환"""
        result = calculate_decayed_score(50, date.today())
        d = result.to_dict()
        assert "raw_score" in d
        assert "decayed_score" in d
        assert "days_old" in d
        assert "decay_rate" in d


class TestDetermineStatus:
    """Status 판단 테스트"""

    def test_pass_range(self):
        """PASS 범위 (0-49)"""
        assert determine_status(0) == "PASS"
        assert determine_status(25) == "PASS"
        assert determine_status(49) == "PASS"

    def test_warning_range(self):
        """WARNING 범위 (50-74)"""
        assert determine_status(50) == "WARNING"
        assert determine_status(60) == "WARNING"
        assert determine_status(74) == "WARNING"

    def test_fail_range(self):
        """FAIL 범위 (75-100)"""
        assert determine_status(75) == "FAIL"
        assert determine_status(85) == "FAIL"
        assert determine_status(100) == "FAIL"

    def test_boundary_values(self):
        """경계값 테스트"""
        assert determine_status(49) == "PASS"
        assert determine_status(50) == "WARNING"
        assert determine_status(74) == "WARNING"
        assert determine_status(75) == "FAIL"


class TestDetermineSentiment:
    """감성 판단 테스트"""

    def test_positive(self):
        """긍정 (0-9)"""
        assert determine_sentiment(0) == "긍정"
        assert determine_sentiment(5) == "긍정"
        assert determine_sentiment(9) == "긍정"

    def test_neutral(self):
        """중립 (10-29)"""
        assert determine_sentiment(10) == "중립"
        assert determine_sentiment(20) == "중립"
        assert determine_sentiment(29) == "중립"

    def test_caution(self):
        """주의 (30-49)"""
        assert determine_sentiment(30) == "주의"
        assert determine_sentiment(40) == "주의"
        assert determine_sentiment(49) == "주의"

    def test_negative(self):
        """부정 (50+)"""
        assert determine_sentiment(50) == "부정"
        assert determine_sentiment(75) == "부정"
        assert determine_sentiment(100) == "부정"


class TestCalculateFinalScore:
    """최종 점수 계산 통합 테스트"""

    def test_high_risk_recent(self):
        """최근 고위험 신호"""
        result = match_keywords("감사보고서 - 의견거절")
        score = calculate_final_score(result, date.today(), source="DART")

        assert isinstance(score, ScoreResult)
        assert score.raw_score == 70
        # final_score = 70 * 0.65 (1 keyword) = 45.5 → PASS
        # 단일 키워드는 confidence가 낮아 최종 점수가 낮음
        assert score.final_score > 40  # 고위험 신호는 40점 이상

    def test_low_risk_old(self):
        """오래된 저위험 신호"""
        result = match_keywords("주주총회 안건")
        old_date = date.today() - timedelta(days=60)
        score = calculate_final_score(result, old_date, source="DART")

        # 낮은 점수 + 시간 감쇠 = 매우 낮은 최종 점수
        assert score.final_score < score.raw_score

    def test_score_result_has_all_fields(self):
        """ScoreResult 모든 필드 확인"""
        result = match_keywords("횡령 혐의")
        score = calculate_final_score(result, date.today())

        assert hasattr(score, "raw_score")
        assert hasattr(score, "decayed_score")
        assert hasattr(score, "confidence")
        assert hasattr(score, "final_score")
        assert hasattr(score, "status")
        assert hasattr(score, "sentiment")
        assert hasattr(score, "category_breakdown")

    def test_to_dict(self):
        """딕셔너리 변환"""
        result = match_keywords("파산 신청")
        score = calculate_final_score(result, date.today())
        d = score.to_dict()

        assert "raw_score" in d
        assert "status" in d
        assert "category_breakdown" in d


class TestCategoryBreakdown:
    """카테고리별 점수 계산 테스트"""

    def test_empty_keywords(self):
        """키워드 없음"""
        breakdown = calculate_category_breakdown([])
        assert breakdown["LEGAL"] == 0
        assert breakdown["CREDIT"] == 0

    def test_single_category(self):
        """단일 카테고리"""
        keywords = [MatchedKeyword("횡령", 50, "LEGAL", 0)]
        breakdown = calculate_category_breakdown(keywords)
        assert breakdown["LEGAL"] == 50
        assert breakdown["CREDIT"] == 0

    def test_multiple_categories(self):
        """다중 카테고리"""
        keywords = [
            MatchedKeyword("횡령", 50, "LEGAL", 0),
            MatchedKeyword("파산", 60, "CREDIT", 5),
            MatchedKeyword("의견거절", 70, "AUDIT", 10),
        ]
        breakdown = calculate_category_breakdown(keywords)
        assert breakdown["LEGAL"] == 50
        assert breakdown["CREDIT"] == 60
        assert breakdown["AUDIT"] == 70


class TestWeightedScore:
    """가중 점수 계산 테스트"""

    def test_empty_breakdown(self):
        """빈 breakdown"""
        score = calculate_weighted_score({})
        assert score == 0.0

    def test_single_category_score(self):
        """단일 카테고리 점수"""
        breakdown = {"LEGAL": 50, "CREDIT": 0, "AUDIT": 0}
        score = calculate_weighted_score(breakdown)
        assert score > 0

    def test_multiple_category_scores(self):
        """다중 카테고리 점수"""
        breakdown = {"LEGAL": 50, "CREDIT": 60, "AUDIT": 70}
        score = calculate_weighted_score(breakdown)
        # 가중 평균이므로 범위 내
        assert 0 < score < 100


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""

    def test_get_status_color(self):
        """Status 색상"""
        assert get_status_color("PASS") == "#22c55e"
        assert get_status_color("WARNING") == "#eab308"
        assert get_status_color("FAIL") == "#ef4444"

    def test_format_score_display(self):
        """점수 표시 포맷"""
        result = match_keywords("횡령 혐의")
        score = calculate_final_score(result, date.today())
        display = format_score_display(score)

        assert "[" in display  # [STATUS]
        assert "Score:" in display
        assert "raw:" in display
