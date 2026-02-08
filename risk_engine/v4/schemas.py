"""
Risk Engine V4 - Pydantic Schemas
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel


# =============================================================================
# 카테고리 상수
# =============================================================================

CATEGORY_CONFIG = {
    "SHARE":  {"name": "주주",     "icon": "📊", "weight": 0.15},
    "EXEC":   {"name": "임원",     "icon": "👔", "weight": 0.15},
    "CREDIT": {"name": "신용",     "icon": "💳", "weight": 0.15},
    "LEGAL":  {"name": "법률",     "icon": "⚖️", "weight": 0.12},
    "GOV":    {"name": "지배구조", "icon": "🏛️", "weight": 0.10},
    "OPS":    {"name": "운영",     "icon": "⚙️", "weight": 0.10},
    "AUDIT":  {"name": "감사",     "icon": "📋", "weight": 0.08},
    "ESG":    {"name": "ESG",      "icon": "🌱", "weight": 0.08},
    "SUPPLY": {"name": "공급망",   "icon": "🔗", "weight": 0.05},
    "OTHER":  {"name": "기타",     "icon": "📎", "weight": 0.02},
}

CategoryCode = Literal["SHARE", "EXEC", "CREDIT", "LEGAL", "GOV", "OPS", "AUDIT", "ESG", "SUPPLY", "OTHER"]
RiskLevel = Literal["PASS", "WARNING", "CRITICAL"]
Trend = Literal["UP", "DOWN", "STABLE"]
Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


# =============================================================================
# 키워드 → 카테고리 매핑
# =============================================================================

KEYWORD_CATEGORY_MAP = {
    # SHARE (주주)
    "주주": "SHARE", "지분": "SHARE", "대량보유": "SHARE", "주식양도": "SHARE",
    "유상증자": "SHARE", "자사주": "SHARE", "배당": "SHARE",

    # EXEC (임원)
    "대표이사": "EXEC", "사임": "EXEC", "해임": "EXEC", "스톡옵션": "EXEC",
    "경영권분쟁": "EXEC", "CFO": "EXEC", "CEO": "EXEC",

    # CREDIT (신용)
    "부도": "CREDIT", "파산": "CREDIT", "회생": "CREDIT", "워크아웃": "CREDIT",
    "채무불이행": "CREDIT", "자본잠식": "CREDIT", "가압류": "CREDIT",

    # LEGAL (법률)
    "소송": "LEGAL", "고발": "LEGAL", "고소": "LEGAL", "제재": "LEGAL",
    "과징금": "LEGAL", "압수수색": "LEGAL", "구속": "LEGAL", "기소": "LEGAL",
    "벌금": "LEGAL", "피소": "LEGAL", "특허": "LEGAL",

    # GOV (지배구조)
    "횡령": "GOV", "배임": "GOV", "최대주주변경": "GOV",
    "내부통제": "GOV", "이사회": "GOV",

    # OPS (운영)
    "사업중단": "OPS", "허가취소": "OPS", "영업정지": "OPS",
    "폐업": "OPS", "생산중단": "OPS",

    # AUDIT (감사)
    "부적정": "AUDIT", "의견거절": "AUDIT", "한정": "AUDIT",
    "감사범위제한": "AUDIT", "분식회계": "AUDIT", "계속기업불확실": "AUDIT",
    "불성실공시": "AUDIT",

    # ESG
    "환경오염": "ESG", "안전사고": "ESG", "갑질": "ESG", "비리": "ESG",
    "스캔들": "ESG", "불매": "ESG", "논란": "ESG",

    # SUPPLY (공급망)
    "공급망": "SUPPLY", "부품": "SUPPLY", "원자재": "SUPPLY",
}


# =============================================================================
# Node Schemas (Dataclasses for internal use)
# =============================================================================

@dataclass
class RiskCategoryNode:
    """RiskCategory 노드"""
    id: str                              # RC_{companyId}_{code}
    company_id: str
    code: CategoryCode
    name: str
    icon: str
    score: int = 0
    weight: float = 0.0
    weighted_score: float = 0.0
    event_count: int = 0
    person_count: int = 0
    news_count: int = 0
    disclosure_count: int = 0
    trend: Trend = "STABLE"
    previous_score: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, company_id: str, code: CategoryCode) -> "RiskCategoryNode":
        config = CATEGORY_CONFIG[code]
        return cls(
            id=f"RC_{company_id}_{code}",
            company_id=company_id,
            code=code,
            name=config["name"],
            icon=config["icon"],
            weight=config["weight"],
        )


@dataclass
class RiskEventNode:
    """RiskEvent 노드"""
    id: str                              # EVT_{hash}
    title: str
    description: str = ""
    category: CategoryCode = "OTHER"
    score: int = 0
    severity: Severity = "MEDIUM"
    company_id: str = ""
    person_ids: list[str] = field(default_factory=list)
    news_ids: list[str] = field(default_factory=list)
    disclosure_ids: list[str] = field(default_factory=list)
    news_count: int = 0
    disclosure_count: int = 0
    matched_keywords: list[str] = field(default_factory=list)
    primary_keyword: str = ""
    first_detected_at: datetime = field(default_factory=datetime.now)
    last_updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# API Response Schemas (Pydantic for API)
# =============================================================================

class NewsItem(BaseModel):
    id: str
    title: str
    source: str = ""
    publishedAt: str = ""
    rawScore: int = 0
    sentiment: str = "NEUTRAL"
    url: str = ""


class DisclosureItem(BaseModel):
    id: str
    title: str
    filingDate: str = ""
    rawScore: int = 0
    category: str = ""
    url: str = ""


class PersonSummary(BaseModel):
    id: str
    name: str
    position: str = ""
    type: str = "EXECUTIVE"
    riskScore: int = 0
    relatedNewsCount: int = 0
    relatedEventCount: int = 0


class EventSummary(BaseModel):
    id: str
    title: str
    category: str
    score: int = 0
    severity: str = "MEDIUM"
    type: str = "NEWS"
    source: str = ""
    newsCount: int = 0
    disclosureCount: int = 0
    firstDetectedAt: str = ""


class CategorySummary(BaseModel):
    code: str
    name: str
    icon: str
    score: int = 0
    weight: float = 0.0
    weightedScore: float = 0.0
    eventCount: int = 0
    personCount: int = 0
    trend: str = "STABLE"


class EvidenceSummary(BaseModel):
    totalNews: int = 0
    totalDisclosures: int = 0
    topFactors: list[str] = []


class ScoreBreakdown(BaseModel):
    direct: int = 0
    propagated: int = 0


class DealDetail(BaseModel):
    id: str
    name: str
    sector: str = ""
    score: int = 0
    riskLevel: str = "PASS"
    breakdown: ScoreBreakdown
    trend: str = "STABLE"
    categories: list[CategorySummary] = []
    topEvents: list[EventSummary] = []
    topPersons: list[PersonSummary] = []
    recentEvents: list[EventSummary] = []
    evidence: EvidenceSummary
    lastUpdated: str = ""


class DealDetailResponse(BaseModel):
    schemaVersion: str = "v4"
    generatedAt: str
    deal: DealDetail


class CategoryDetail(BaseModel):
    code: str
    name: str
    icon: str
    score: int = 0
    weight: float = 0.0
    events: list[EventSummary] = []
    persons: list[PersonSummary] = []
    news: list[NewsItem] = []
    disclosures: list[DisclosureItem] = []


class CategoryDetailResponse(BaseModel):
    schemaVersion: str = "v4"
    generatedAt: str
    category: CategoryDetail


class EventDetail(BaseModel):
    id: str
    title: str
    description: str = ""
    category: str
    score: int = 0
    severity: str = "MEDIUM"
    matchedKeywords: list[str] = []
    involvedPersons: list[PersonSummary] = []
    news: list[NewsItem] = []
    disclosures: list[DisclosureItem] = []
    firstDetectedAt: str = ""
    isActive: bool = True


class EventDetailResponse(BaseModel):
    schemaVersion: str = "v4"
    generatedAt: str
    event: EventDetail


class PersonDetail(BaseModel):
    id: str
    name: str
    position: str = ""
    type: str = "EXECUTIVE"
    tier: int = 2
    riskScore: int = 0
    riskLevel: str = "PASS"
    riskFactors: list[str] = []
    companies: list[dict] = []
    involvedEvents: list[EventSummary] = []
    relatedNews: list[NewsItem] = []


class PersonDetailResponse(BaseModel):
    schemaVersion: str = "v4"
    generatedAt: str
    person: PersonDetail
