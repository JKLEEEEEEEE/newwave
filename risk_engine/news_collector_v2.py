"""
뉴스 수집기 v2 (Risk Graph v3)
- 책임: Google/Naver RSS에서 뉴스 수집, 키워드 매칭, 중복 제거, Neo4j 저장
- 위치: risk_engine/news_collector_v2.py

Design Doc: docs/02-design/features/risk-graph-v3.design.md Section 3.5
"""

from __future__ import annotations
import hashlib
import logging
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Literal
import requests
from bs4 import BeautifulSoup

from .keywords import (
    match_keywords,
    build_search_queries_for_company,
    get_high_risk_keywords,
    MatchResult,
)
from .score_engine import calculate_final_score, ScoreResult, calc_days_old
from .validator import DataValidator, ValidationResult

logger = logging.getLogger(__name__)

# =============================================================================
# 상수 정의
# =============================================================================

# 뉴스 소스 설정
NEWS_SOURCES = {
    "GOOGLE_RSS": {
        "name": "구글뉴스",
        "url": "https://news.google.com/rss/search",
        "reliability": 0.75,
    },
    "GOOGLE_RSS_NAVER": {
        "name": "네이버뉴스",
        "url": "https://news.google.com/rss/search",
        "suffix": "+site:naver.com",
        "reliability": 0.85,
    },
    "NAVER_BLOG_RSS": {
        "name": "네이버블로그",
        "url": "https://rss.blog.naver.com/cmylose0102.xml",
        "reliability": 0.40,
        "tier": "BLOG",
    },
}

# 수집 필터 설정
FILTER_CONFIG = {
    "max_age_days": 30,          # 최대 뉴스 연령
    "min_title_length": 10,       # 최소 제목 길이
    "min_risk_score": 5,          # 최소 리스크 점수 (0이면 모두 수집)
    "require_keyword_match": False,  # 키워드 매칭 필수 여부
}

# 주요 언론사 (신뢰도 높음)
MAJOR_PUBLISHERS = [
    "연합뉴스", "조선일보", "중앙일보", "동아일보", "한겨레", "경향신문",
    "매일경제", "한국경제", "서울경제", "머니투데이", "이데일리", "아시아경제",
    "SBS", "KBS", "MBC", "JTBC", "YTN", "뉴스1", "뉴시스",
]

# 요청 간격 (초)
REQUEST_DELAY = 0.3

SourceType = Literal["GOOGLE_RSS", "GOOGLE_RSS_NAVER", "NAVER_BLOG_RSS"]


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class NewsData:
    """뉴스 데이터"""
    # 필수 필드
    title: str
    url: str
    published_at: datetime | str
    source: str

    # 분석 결과
    match_result: MatchResult | None = None
    score_result: ScoreResult | None = None

    # 메타데이터
    publisher: str | None = None
    source_type: SourceType = "GOOGLE_RSS"
    fetched_at: datetime | None = None
    confidence: float = 0.5

    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.now()

        # published_at 정규화
        if isinstance(self.published_at, str):
            self.published_at = self._parse_date(self.published_at)

        # 신뢰도 설정
        if self.publisher and self.publisher in MAJOR_PUBLISHERS:
            self.confidence = 0.85
        else:
            source_config = NEWS_SOURCES.get(self.source_type, {})
            self.confidence = source_config.get("reliability", 0.7)

    def _parse_date(self, date_str: str) -> datetime:
        """날짜 문자열 파싱"""
        try:
            # RFC 2822 형식 (Google RSS)
            return parsedate_to_datetime(date_str)
        except (TypeError, ValueError):
            pass

        try:
            # ISO 형식
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # 실패시 현재 시간
        return datetime.now()

    @property
    def id(self) -> str:
        """고유 ID 생성"""
        return f"NEWS_{self.url_hash[:12]}"

    @property
    def url_hash(self) -> str:
        """URL 해시"""
        normalized = self.url.lower().strip().rstrip("/")
        return hashlib.md5(normalized.encode()).hexdigest()

    @property
    def days_old(self) -> int:
        """뉴스 연령 (일)"""
        if isinstance(self.published_at, datetime):
            return calc_days_old(self.published_at)
        return 0

    @property
    def is_risk(self) -> bool:
        """리스크 뉴스 여부"""
        if self.score_result:
            return self.score_result.final_score > 0
        if self.match_result:
            return self.match_result.keyword_count > 0
        return False

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "url_hash": self.url_hash,
            "published_at": self.published_at.isoformat() if isinstance(self.published_at, datetime) else str(self.published_at),
            "source": self.source,
            "publisher": self.publisher,
            "source_type": self.source_type,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "confidence": self.confidence,
            "days_old": self.days_old,
            "is_risk": self.is_risk,
            "matched_keywords": self.match_result.to_dict() if self.match_result else None,
            "score": self.score_result.to_dict() if self.score_result else None,
        }

    def to_neo4j_props(self) -> dict:
        """Neo4j 노드 속성으로 변환"""
        props = {
            "id": self.id,
            "title": self.title,
            "sourceUrl": self.url,
            "urlHash": self.url_hash,
            "publishedAt": self.published_at.isoformat() if isinstance(self.published_at, datetime) else str(self.published_at),
            "source": self.source,
            "publisher": self.publisher,
            "sourceType": self.source_type,
            "confidence": self.confidence,
            "daysOld": self.days_old,
        }

        if self.match_result:
            props["matchedKeywords"] = [kw.keyword for kw in self.match_result.matched_keywords]
            props["rawScore"] = self.match_result.raw_score
            props["keywordCount"] = self.match_result.keyword_count
            props["category"] = self.match_result.primary_category

        if self.score_result:
            props["decayedScore"] = self.score_result.decayed_score
            props["finalScore"] = self.score_result.final_score
            props["status"] = self.score_result.status
            props["sentiment"] = self.score_result.sentiment

        return props


@dataclass
class CollectionResult:
    """뉴스 수집 결과"""
    query: str = ""
    total_fetched: int = 0
    total_analyzed: int = 0
    total_valid: int = 0
    total_saved: int = 0
    duplicates_removed: int = 0
    risk_news_count: int = 0
    news_list: list[NewsData] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_fetched": self.total_fetched,
            "total_analyzed": self.total_analyzed,
            "total_valid": self.total_valid,
            "total_saved": self.total_saved,
            "duplicates_removed": self.duplicates_removed,
            "risk_news_count": self.risk_news_count,
            "error_count": len(self.errors),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds() if self.completed_at else None,
        }


# =============================================================================
# 뉴스 수집기 클래스
# =============================================================================

class NewsCollectorV2:
    """뉴스 수집기 v2"""

    def __init__(self, neo4j_client=None):
        """
        Args:
            neo4j_client: Neo4j 클라이언트 (저장용, 선택)
        """
        self.neo4j_client = neo4j_client
        self.validator = DataValidator(neo4j_client)
        self.seen_urls: set[str] = set()
        self._session_queries: list[str] = []

    def reset_session(self):
        """세션 초기화 (중복 추적 리셋)"""
        self.seen_urls.clear()
        self._session_queries.clear()

    def collect_news(
        self,
        company_name: str,
        aliases: list[str] | None = None,
        products: list[str] | None = None,
        persons: list[str] | None = None,
        limit: int = 20,
        source_types: list[SourceType] | None = None,
        analyze: bool = True,
    ) -> CollectionResult:
        """
        기업 관련 뉴스 수집

        Args:
            company_name: 기업명
            aliases: 기업 별칭 목록
            products: 주요 제품 목록
            persons: 주요 임원 목록
            limit: 수집 제한 (쿼리당)
            source_types: 소스 타입 목록 (기본: 모두)
            analyze: 키워드 분석 수행 여부

        Returns:
            CollectionResult: 수집 결과
        """
        result = CollectionResult()

        # 검색 쿼리 생성
        queries = self.generate_queries(company_name, aliases, products, persons)
        result.query = f"{company_name} ({len(queries)} queries)"

        if source_types is None:
            source_types = list(NEWS_SOURCES.keys())

        all_news: list[NewsData] = []

        # 각 쿼리 & 소스 조합으로 수집
        for query in queries[:10]:  # 최대 10개 쿼리
            for source_type in source_types:
                try:
                    news_list = self._fetch_from_source(query, source_type, limit=limit)
                    all_news.extend(news_list)
                    result.total_fetched += len(news_list)
                except Exception as e:
                    result.errors.append(f"수집 오류 ({query}, {source_type}): {e}")
                    logger.warning(f"뉴스 수집 오류: {e}")

                time.sleep(REQUEST_DELAY)

        # 중복 제거
        unique_news = self.deduplicate(all_news)
        result.duplicates_removed = len(all_news) - len(unique_news)

        # 분석 및 필터링
        for news in unique_news:
            try:
                if analyze:
                    news = self.analyze_news(news)

                # 검증
                validation = self.validator.validate(news.to_dict(), "News")
                if validation.is_valid:
                    # 필터 적용
                    if self._apply_filters(news):
                        result.news_list.append(news)
                        result.total_valid += 1

                        if news.is_risk:
                            result.risk_news_count += 1

                result.total_analyzed += 1

            except Exception as e:
                result.errors.append(f"분석 오류: {e}")

        result.completed_at = datetime.now()
        logger.info(f"뉴스 수집 완료: {company_name} - {result.total_valid}/{result.total_fetched} 건")
        return result

    def _fetch_from_source(
        self,
        query: str,
        source_type: SourceType,
        limit: int = 20,
    ) -> list[NewsData]:
        """
        특정 소스에서 뉴스 수집

        Args:
            query: 검색 쿼리
            source_type: 소스 타입
            limit: 수집 제한

        Returns:
            뉴스 목록
        """
        source_config = NEWS_SOURCES.get(source_type, NEWS_SOURCES["GOOGLE_RSS"])
        base_url = source_config["url"]
        suffix = source_config.get("suffix", "")

        # 쿼리 인코딩
        encoded_query = urllib.parse.quote(f"{query}{suffix}")
        url = f"{base_url}?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")

            news_list = []
            for item in soup.find_all("item")[:limit]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")

                if not title or not link:
                    continue

                title_text = title.get_text()
                url_text = link.get_text()
                pub_date_text = pub_date.get_text() if pub_date else ""

                # 출처 추출 (제목에서 " - 출처" 형태)
                publisher = None
                if " - " in title_text:
                    parts = title_text.rsplit(" - ", 1)
                    if len(parts) == 2:
                        title_text, publisher = parts

                news = NewsData(
                    title=title_text.strip(),
                    url=url_text.strip(),
                    published_at=pub_date_text,
                    source=source_config["name"],
                    publisher=publisher,
                    source_type=source_type,
                )
                news_list.append(news)

            return news_list

        except requests.exceptions.RequestException as e:
            logger.error(f"뉴스 RSS 요청 실패: {url} - {e}")
            return []

    def generate_queries(
        self,
        company_name: str,
        aliases: list[str] | None = None,
        products: list[str] | None = None,
        persons: list[str] | None = None,
    ) -> list[str]:
        """
        검색 쿼리 생성

        Args:
            company_name: 기업명
            aliases: 별칭
            products: 제품
            persons: 임원

        Returns:
            검색 쿼리 목록
        """
        queries = build_search_queries_for_company(
            company_name=company_name,
            aliases=aliases,
            products=products,
            persons=persons,
            top_n_keywords=5,
        )

        # 기본 기업명 쿼리 추가
        queries.insert(0, company_name)

        # 중복 제거
        return list(dict.fromkeys(queries))

    def deduplicate(self, news_list: list[NewsData]) -> list[NewsData]:
        """
        중복 제거

        Args:
            news_list: 뉴스 목록

        Returns:
            중복 제거된 목록
        """
        unique = []
        for news in news_list:
            if news.url_hash not in self.seen_urls:
                self.seen_urls.add(news.url_hash)
                unique.append(news)
        return unique

    def analyze_news(self, news: NewsData) -> NewsData:
        """
        뉴스 분석 (키워드 매칭 + 점수 계산)

        Args:
            news: 뉴스 데이터

        Returns:
            분석된 뉴스 데이터
        """
        # 키워드 매칭
        match_result = match_keywords(news.title, source="NEWS")
        news.match_result = match_result

        # 점수 계산
        if match_result.keyword_count > 0:
            score_result = calculate_final_score(
                match_result,
                news.published_at,
                source="NEWS",
            )
            news.score_result = score_result

        return news

    # 노이즈 제목 패턴 (분석 가치 없는 콘텐츠)
    NOISE_PREFIXES = ["댓글 :", "댓글:", "#", "댓글 :"]
    NOISE_KEYWORDS = ["네이버 블로그", "네이버 프리미엄 콘텐츠", "프리미엄콘텐츠", "Earlthday"]

    def _apply_filters(self, news: NewsData) -> bool:
        """
        필터 적용

        Args:
            news: 뉴스 데이터

        Returns:
            통과 여부
        """
        # 연령 필터
        if news.days_old > FILTER_CONFIG["max_age_days"]:
            return False

        # 제목 길이 필터
        if len(news.title) < FILTER_CONFIG["min_title_length"]:
            return False

        # 노이즈 필터: 댓글, SNS, 블로그 등 분석 가치 없는 콘텐츠
        title_stripped = news.title.strip()
        for prefix in self.NOISE_PREFIXES:
            if title_stripped.startswith(prefix):
                return False
        for noise in self.NOISE_KEYWORDS:
            if noise in news.title:
                return False

        # 최소 리스크 점수 필터
        if FILTER_CONFIG["min_risk_score"] > 0:
            if news.score_result:
                if news.score_result.final_score < FILTER_CONFIG["min_risk_score"]:
                    return False
            elif FILTER_CONFIG["require_keyword_match"]:
                return False

        return True

    # keywords.py CategoryType → Neo4j RiskCategory.code 매핑
    CAT_CODE_MAP = {
        "LEGAL": "LEGAL", "CREDIT": "CREDIT", "GOVERNANCE": "GOV",
        "OPERATIONAL": "OPS", "AUDIT": "AUDIT", "ESG": "ESG",
        "CAPITAL": "SHARE", "SUPPLY": "SUPPLY", "OTHER": "OTHER",
    }

    def save_to_neo4j(self, news_list: list[NewsData], company_id: str) -> int:
        """
        수집된 뉴스를 5-Node 스키마로 Neo4j에 저장

        경로: Company -[HAS_CATEGORY]-> RiskCategory -[HAS_ENTITY]-> RiskEntity -[HAS_EVENT]-> RiskEvent

        Args:
            news_list: 뉴스 데이터 목록
            company_id: 기업명 또는 기업 ID

        Returns:
            저장된 건수
        """
        if self.neo4j_client is None:
            logger.warning("Neo4j 클라이언트가 설정되지 않았습니다")
            return 0

        saved_count = 0

        query = """
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE (c.name = $companyId OR c.id = $companyId)
          AND rc.code = $categoryCode
        WITH rc LIMIT 1

        MERGE (re:RiskEntity {id: $entityId})
        ON CREATE SET
            re.name = $entityName,
            re.type = 'ISSUE',
            re.subType = 'NEWS_COLLECTION',
            re.createdAt = datetime()
        ON MATCH SET
            re.name = $entityName,
            re.updatedAt = datetime()
        MERGE (rc)-[:HAS_ENTITY]->(re)

        WITH re
        MERGE (ev:RiskEvent {id: $eventId})
        ON CREATE SET
            ev.title = $title,
            ev.summary = $summary,
            ev.type = 'NEWS',
            ev.score = $score,
            ev.severity = $severity,
            ev.sourceName = $sourceName,
            ev.sourceUrl = $sourceUrl,
            ev.publishedAt = $publishedAt,
            ev.isActive = true,
            ev.createdAt = datetime()
        ON MATCH SET
            ev.title = $title,
            ev.summary = $summary,
            ev.score = $score,
            ev.updatedAt = datetime()
        MERGE (re)-[:HAS_EVENT]->(ev)

        RETURN ev.id as id
        """

        with self.neo4j_client.session() as session:
            for news in news_list:
                try:
                    score = news.score_result.final_score if news.score_result else 0
                    severity = "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"

                    eng_category = news.match_result.primary_category if news.match_result and news.match_result.primary_category else None
                    mapped_cat = self.CAT_CODE_MAP.get(eng_category, "OTHER") if eng_category else "OTHER"

                    published = ""
                    if news.published_at:
                        published = news.published_at.isoformat() if hasattr(news.published_at, 'isoformat') else str(news.published_at)

                    result = session.run(query, {
                        "companyId": company_id,
                        "categoryCode": mapped_cat,
                        "entityId": f"ENT_NEWS_{news.id[:12]}",
                        "entityName": news.title[:30] if news.title else "뉴스",
                        "eventId": f"EVT_{news.id}",
                        "title": news.title,
                        "summary": news.title,
                        "score": score,
                        "severity": severity,
                        "sourceName": news.source or "",
                        "sourceUrl": news.url or "",
                        "publishedAt": published,
                    })
                    if result.single():
                        saved_count += 1

                except Exception as e:
                    logger.error(f"뉴스 저장 실패 ({news.id}): {e}")

        logger.info(f"Neo4j 저장 완료: {saved_count}/{len(news_list)} 건")
        return saved_count


# =============================================================================
# 헬퍼 함수
# =============================================================================

def collect_news_for_companies(
    companies: list[dict],
    limit: int = 20,
) -> dict[str, CollectionResult]:
    """
    여러 기업의 뉴스 일괄 수집

    Args:
        companies: 기업 정보 목록 [{"name": str, "aliases": list, ...}, ...]
        limit: 기업당 수집 제한

    Returns:
        기업명별 수집 결과
    """
    collector = NewsCollectorV2()
    results = {}

    for company in companies:
        try:
            result = collector.collect_news(
                company_name=company.get("name", ""),
                aliases=company.get("aliases"),
                products=company.get("products"),
                persons=company.get("persons"),
                limit=limit,
            )
            results[company["name"]] = result
        except Exception as e:
            logger.error(f"수집 실패 ({company.get('name')}): {e}")
            results[company["name"]] = CollectionResult(errors=[str(e)])

    return results


def get_risk_news(
    result: CollectionResult,
    threshold: float = 0.0,
) -> list[NewsData]:
    """
    리스크 뉴스만 필터링

    Args:
        result: 수집 결과
        threshold: 점수 임계치

    Returns:
        리스크 뉴스 목록
    """
    return [
        n for n in result.news_list
        if n.is_risk and (n.score_result is None or n.score_result.final_score >= threshold)
    ]
