"""
점수 계산 엔진 (Risk Graph v3)
- 책임: 시간 감쇠, 신뢰도, 카테고리 점수 계산
- 위치: risk_engine/score_engine.py

Design Doc: docs/02-design/features/risk-graph-v3.design.md Section 3.2
"""

from __future__ import annotations
import math
from datetime import datetime, date
from dataclasses import dataclass
from typing import Literal

from .keywords import MatchResult, MatchedKeyword, CategoryType, get_category_weight

# =============================================================================
# 상수 정의
# =============================================================================

DECAY_HALF_LIFE = 30  # 30일 반감기
CONFIDENCE_BASE = 0.5
CONFIDENCE_INCREMENT = 0.15
CONFIDENCE_MAX = 0.95
CONFIDENCE_MIN = 0.3

# 소스별 신뢰도 계수
SOURCE_RELIABILITY: dict[str, float] = {
    "DART": 1.0,     # 공식 공시 (가장 신뢰)
    "KIND": 0.95,    # 거래소 공시
    "NEWS_MAJOR": 0.8,  # 주요 언론사
    "NEWS_MINOR": 0.6,  # 일반 언론사
    "NEWS": 0.7,     # 기본 뉴스
}

# Status 임계값
STATUS_THRESHOLDS = {
    "PASS": (0, 49),      # 0-49: 안전
    "WARNING": (50, 74),  # 50-74: 주의
    "FAIL": (75, 100),    # 75-100: 위험
}

StatusType = Literal["PASS", "WARNING", "FAIL"]
SentimentType = Literal["긍정", "중립", "주의", "부정"]


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class DecayResult:
    """시간 감쇠 계산 결과"""
    raw_score: int
    decayed_score: int
    days_old: int
    decay_rate: float

    def to_dict(self) -> dict:
        return {
            "raw_score": self.raw_score,
            "decayed_score": self.decayed_score,
            "days_old": self.days_old,
            "decay_rate": round(self.decay_rate, 3),
        }


@dataclass
class ScoreResult:
    """최종 점수 계산 결과"""
    raw_score: int
    decayed_score: int
    confidence: float
    final_score: float  # decayed_score * confidence
    days_old: int
    decay_rate: float
    status: StatusType
    sentiment: SentimentType
    category_breakdown: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "raw_score": self.raw_score,
            "decayed_score": self.decayed_score,
            "confidence": round(self.confidence, 2),
            "final_score": round(self.final_score, 1),
            "days_old": self.days_old,
            "decay_rate": round(self.decay_rate, 3),
            "status": self.status,
            "sentiment": self.sentiment,
            "category_breakdown": self.category_breakdown,
        }


# =============================================================================
# 시간 감쇠 함수
# =============================================================================

def calc_decay(days_old: int, half_life: int = DECAY_HALF_LIFE) -> float:
    """
    시간 감쇠 계산 (지수 감쇠)

    Args:
        days_old: 경과 일수
        half_life: 반감기 (기본 30일)

    Returns:
        감쇠율 (0.0 ~ 1.0)

    Example:
        >>> calc_decay(0)   # 오늘
        1.0
        >>> calc_decay(30)  # 30일 전 (반감기)
        0.368  # e^(-1)
        >>> calc_decay(60)  # 60일 전
        0.135  # e^(-2)
    """
    if days_old < 0:
        days_old = 0
    return math.exp(-days_old / half_life)


def calc_days_old(pub_date: datetime | date | str) -> int:
    """
    발행일로부터 경과 일수 계산

    Args:
        pub_date: 발행일 (datetime, date, 또는 ISO 문자열)

    Returns:
        경과 일수
    """
    if isinstance(pub_date, str):
        # ISO 형식 파싱 (YYYY-MM-DD 또는 YYYY-MM-DDTHH:MM:SS)
        try:
            pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
        except ValueError:
            pub_date = datetime.strptime(pub_date[:10], "%Y-%m-%d")

    if isinstance(pub_date, datetime):
        pub_date = pub_date.date()

    today = date.today()
    return max(0, (today - pub_date).days)


# =============================================================================
# 신뢰도 함수
# =============================================================================

def calc_confidence(
    keyword_count: int,
    source: str = "DART",
    source_reliability: float | None = None,
) -> float:
    """
    신뢰도 계산

    신뢰도 = min(base + keyword_count * increment, max) * source_reliability

    Args:
        keyword_count: 매칭된 키워드 개수
        source: 소스 타입
        source_reliability: 소스 신뢰도 (None이면 source에서 조회)

    Returns:
        신뢰도 (0.3 ~ 0.95)

    Example:
        >>> calc_confidence(0)
        0.3
        >>> calc_confidence(1)
        0.65
        >>> calc_confidence(2)
        0.8
        >>> calc_confidence(5)
        0.95  # 최대값
    """
    if keyword_count == 0:
        return CONFIDENCE_MIN

    # 소스 신뢰도
    if source_reliability is None:
        source_reliability = SOURCE_RELIABILITY.get(source, 0.7)

    # 기본 신뢰도 + 키워드 보너스
    base_confidence = CONFIDENCE_BASE + (keyword_count * CONFIDENCE_INCREMENT)
    capped = min(base_confidence, CONFIDENCE_MAX)

    # 소스 신뢰도 반영
    final = capped * source_reliability
    return round(max(CONFIDENCE_MIN, min(final, CONFIDENCE_MAX)), 2)


# =============================================================================
# 점수 계산 함수
# =============================================================================

def calculate_raw_score(matched_keywords: list[MatchedKeyword] | list[dict]) -> int:
    """
    매칭된 키워드들의 원점수 계산

    Design 문서 기준: max(scores) 사용

    Args:
        matched_keywords: 매칭된 키워드 목록

    Returns:
        원점수 (0-100)
    """
    if not matched_keywords:
        return 0

    scores = []
    for kw in matched_keywords:
        if isinstance(kw, MatchedKeyword):
            scores.append(kw.score)
        elif isinstance(kw, dict):
            scores.append(kw.get("score", 0))

    return min(max(scores), 100) if scores else 0


def calculate_raw_score_sum(matched_keywords: list[MatchedKeyword] | list[dict]) -> int:
    """
    매칭된 키워드들의 원점수 합산 (대안 방식)

    Args:
        matched_keywords: 매칭된 키워드 목록

    Returns:
        원점수 합 (0-100, 캡 적용)
    """
    if not matched_keywords:
        return 0

    total = 0
    for kw in matched_keywords:
        if isinstance(kw, MatchedKeyword):
            total += kw.score
        elif isinstance(kw, dict):
            total += kw.get("score", 0)

    return min(total, 100)


def calculate_decayed_score(raw_score: int, pub_date: datetime | date | str) -> DecayResult:
    """
    감쇠 적용 점수 계산

    Args:
        raw_score: 원점수
        pub_date: 발행일

    Returns:
        DecayResult: 감쇠 결과
    """
    days_old = calc_days_old(pub_date)
    decay_rate = calc_decay(days_old)
    decayed = round(raw_score * decay_rate)

    return DecayResult(
        raw_score=raw_score,
        decayed_score=min(decayed, 100),
        days_old=days_old,
        decay_rate=decay_rate,
    )


def calculate_final_score(
    match_result: MatchResult,
    pub_date: datetime | date | str,
    source: str = "DART",
) -> ScoreResult:
    """
    최종 점수 계산 (통합)

    final_score = decayed_score * confidence

    Args:
        match_result: 키워드 매칭 결과
        pub_date: 발행일
        source: 소스 타입

    Returns:
        ScoreResult: 최종 점수 결과
    """
    # 원점수
    raw_score = match_result.raw_score

    # 시간 감쇠
    decay_result = calculate_decayed_score(raw_score, pub_date)

    # 신뢰도
    confidence = calc_confidence(match_result.keyword_count, source)

    # 최종 점수
    final_score = decay_result.decayed_score * confidence

    # Status 결정
    status = determine_status(round(final_score))

    # 감성 판단
    sentiment = determine_sentiment(round(final_score))

    # 카테고리별 점수 breakdown
    category_breakdown = calculate_category_breakdown(match_result.matched_keywords)

    return ScoreResult(
        raw_score=raw_score,
        decayed_score=decay_result.decayed_score,
        confidence=confidence,
        final_score=final_score,
        days_old=decay_result.days_old,
        decay_rate=decay_result.decay_rate,
        status=status,
        sentiment=sentiment,
        category_breakdown=category_breakdown,
    )


# =============================================================================
# Status & Sentiment 판단
# =============================================================================

def determine_status(score: int) -> StatusType:
    """
    점수 기반 Status 판단

    Args:
        score: 리스크 점수 (0-100)

    Returns:
        Status ("PASS", "WARNING", "FAIL")
    """
    if score >= 75:
        return "FAIL"
    elif score >= 50:
        return "WARNING"
    else:
        return "PASS"


def determine_sentiment(score: int) -> SentimentType:
    """
    점수 기반 감성 판단

    Args:
        score: 리스크 점수 (0-100)

    Returns:
        감성 ("긍정", "중립", "주의", "부정")
    """
    if score >= 50:
        return "부정"
    elif score >= 30:
        return "주의"
    elif score >= 10:
        return "중립"
    else:
        return "긍정"


# =============================================================================
# Category Breakdown
# =============================================================================

def calculate_category_breakdown(matched_keywords: list[MatchedKeyword]) -> dict[str, int]:
    """
    카테고리별 점수 breakdown 계산

    Args:
        matched_keywords: 매칭된 키워드 목록

    Returns:
        카테고리별 최고 점수 딕셔너리
    """
    breakdown: dict[str, int] = {
        "LEGAL": 0,
        "CREDIT": 0,
        "GOVERNANCE": 0,
        "OPERATIONAL": 0,
        "AUDIT": 0,
        "ESG": 0,
        "CAPITAL": 0,
        "OTHER": 0,
    }

    for kw in matched_keywords:
        category = kw.category
        if kw.score > breakdown.get(category, 0):
            breakdown[category] = kw.score

    return breakdown


def calculate_weighted_score(category_breakdown: dict[str, int]) -> float:
    """
    카테고리 가중치 적용 점수 계산

    Args:
        category_breakdown: 카테고리별 점수

    Returns:
        가중 평균 점수
    """
    total = 0.0
    weight_sum = 0.0

    for category, score in category_breakdown.items():
        weight = get_category_weight(category)  # type: ignore
        total += score * weight
        weight_sum += weight

    if weight_sum == 0:
        return 0.0

    return round(total / weight_sum, 1)


# =============================================================================
# 유틸리티 함수
# =============================================================================

def get_status_color(status: StatusType) -> str:
    """Status별 색상 코드 반환"""
    colors = {
        "PASS": "#22c55e",    # Green
        "WARNING": "#eab308",  # Yellow
        "FAIL": "#ef4444",    # Red
    }
    return colors.get(status, "#6b7280")


def get_status_emoji(status: StatusType) -> str:
    """Status별 이모지 반환"""
    emojis = {
        "PASS": "OK",
        "WARNING": "!",
        "FAIL": "X",
    }
    return emojis.get(status, "?")


def format_score_display(score_result: ScoreResult) -> str:
    """점수 결과를 표시용 문자열로 포맷"""
    return (
        f"[{score_result.status}] "
        f"Score: {score_result.final_score:.1f} "
        f"(raw: {score_result.raw_score}, "
        f"decay: {score_result.decay_rate:.2f}, "
        f"conf: {score_result.confidence:.2f})"
    )
