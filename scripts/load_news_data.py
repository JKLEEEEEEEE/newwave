"""
뉴스 크롤링 데이터 → Neo4j 로드 스크립트
Risk Monitoring System v2.2
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
import hashlib

# 상위 디렉토리 추가 (risk_engine import를 위해)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('.env.local')

from risk_engine.neo4j_client import neo4j_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 리스크 키워드 정의
RISK_KEYWORDS = {
    "high": ["횡령", "배임", "소송", "검찰", "기소", "구속", "워크아웃", "부도", "파산", "제재"],
    "medium": ["분쟁", "조사", "감사", "적자", "손실", "하락", "감소", "지연"],
    "low": ["이슈", "논란", "우려", "변동"]
}

POSITIVE_KEYWORDS = ["흑자", "성장", "증가", "호실적", "사상최대", "인수", "계약"]


def generate_news_id(title: str, date: str, source: str) -> str:
    """뉴스 고유 ID 생성"""
    content = f"{title}:{date}:{source}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def analyze_sentiment(title: str, content: str = "") -> str:
    """뉴스 감성 분석 (키워드 기반)"""
    text = f"{title} {content}".lower()

    # 부정 키워드 카운트
    negative_count = 0
    for level, keywords in RISK_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                negative_count += 1 if level == "low" else 2 if level == "medium" else 3

    # 긍정 키워드 카운트
    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)

    if negative_count > positive_count + 2:
        return "부정"
    elif positive_count > negative_count + 1:
        return "긍정"
    else:
        return "중립"


def calculate_news_risk_score(title: str, content: str = "") -> int:
    """뉴스 리스크 점수 계산"""
    text = f"{title} {content}".lower()
    score = 30  # 기본 점수

    for kw in RISK_KEYWORDS["high"]:
        if kw in text:
            score += 15

    for kw in RISK_KEYWORDS["medium"]:
        if kw in text:
            score += 8

    for kw in RISK_KEYWORDS["low"]:
        if kw in text:
            score += 3

    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            score -= 5

    return max(0, min(100, score))


def extract_mentioned_companies(title: str, content: str, known_companies: List[str]) -> List[str]:
    """뉴스에서 언급된 기업 추출"""
    text = f"{title} {content}"
    mentioned = []

    for company in known_companies:
        if company in text:
            mentioned.append(company)

    return mentioned


def get_sample_news_data() -> List[Dict[str, Any]]:
    """샘플 뉴스 데이터 생성 (실제로는 뉴스 API 연동 필요)"""
    # 실제 환경에서는 네이버 뉴스 API, 구글 뉴스 API 등을 사용
    base_date = datetime.now()

    sample_news = [
        {
            "title": "[긴급] SK하이닉스, 美 특허 침해 소송 피소",
            "content": "SK하이닉스가 미국 특허 침해 소송에 휘말렸다. ITC 조사가 진행 중...",
            "source": "매일경제",
            "published_at": (base_date - timedelta(hours=2)).isoformat(),
            "url": "https://example.com/news/1"
        },
        {
            "title": "한미반도체, 대규모 감원 계획 발표",
            "content": "한미반도체가 실적 악화로 대규모 구조조정을 발표했다...",
            "source": "한국경제",
            "published_at": (base_date - timedelta(hours=5)).isoformat(),
            "url": "https://example.com/news/2"
        },
        {
            "title": "삼성전자, AI 반도체 수요 급증으로 사상 최대 실적",
            "content": "삼성전자가 AI 반도체 수요 급증에 힘입어 분기 사상 최대 매출...",
            "source": "조선비즈",
            "published_at": (base_date - timedelta(hours=8)).isoformat(),
            "url": "https://example.com/news/3"
        },
        {
            "title": "LG에너지솔루션, 美 배터리 공장 가동 지연 우려",
            "content": "LG에너지솔루션의 미국 배터리 공장 가동이 지연될 수 있다는 우려가...",
            "source": "서울경제",
            "published_at": (base_date - timedelta(hours=12)).isoformat(),
            "url": "https://example.com/news/4"
        },
        {
            "title": "현대자동차 대표이사, 배임 혐의 검찰 조사",
            "content": "현대자동차 대표이사가 배임 혐의로 검찰 조사를 받고 있다...",
            "source": "뉴스1",
            "published_at": (base_date - timedelta(hours=24)).isoformat(),
            "url": "https://example.com/news/5"
        },
        {
            "title": "금감원, 대한항공 회계 감리 착수",
            "content": "금융감독원이 대한항공에 대한 회계 감리를 착수했다...",
            "source": "이데일리",
            "published_at": (base_date - timedelta(hours=36)).isoformat(),
            "url": "https://example.com/news/6"
        },
        {
            "title": "카카오뱅크, 부실 대출 급증에 충당금 확대",
            "content": "카카오뱅크의 부실 대출이 급증하면서 대손충당금을 대폭 확대...",
            "source": "머니투데이",
            "published_at": (base_date - timedelta(hours=48)).isoformat(),
            "url": "https://example.com/news/7"
        }
    ]

    return sample_news


def get_known_companies_from_neo4j() -> List[str]:
    """Neo4j에서 기존 기업 목록 조회"""
    try:
        neo4j_client.connect()
        query = "MATCH (c:Company) RETURN c.name AS name"
        results = neo4j_client.execute_read(query)
        return [r["name"] for r in results if r.get("name")]
    except Exception as e:
        logger.warning(f"기업 목록 조회 실패: {e}")
        # 폴백: 알려진 기업명 목록
        return [
            "SK하이닉스", "한미반도체", "삼성전자", "LG에너지솔루션",
            "현대자동차", "대한항공", "카카오뱅크", "기아"
        ]


def load_news_to_neo4j(articles: List[Dict[str, Any]], known_companies: List[str]):
    """뉴스 데이터 Neo4j 로드"""
    logger.info(f"Neo4j 로드 시작: {len(articles)}개 뉴스")

    neo4j_client.connect()

    for article in articles:
        title = article["title"]
        content = article.get("content", "")

        # 뉴스 ID 생성
        news_id = generate_news_id(title, article["published_at"], article["source"])

        # 감성 및 리스크 분석
        sentiment = analyze_sentiment(title, content)
        risk_score = calculate_news_risk_score(title, content)

        # 언급된 기업 추출
        mentioned = extract_mentioned_companies(title, content, known_companies)

        # 뉴스 노드 생성
        create_news_query = """
        MERGE (n:NewsArticle {id: $newsId})
        SET n.title = $title,
            n.content = $content,
            n.source = $source,
            n.url = $url,
            n.publishedAt = datetime($publishedAt),
            n.sentiment = $sentiment,
            n.riskScore = $riskScore,
            n.createdAt = datetime()
        """

        neo4j_client.execute_write(create_news_query, {
            "newsId": news_id,
            "title": title,
            "content": content,
            "source": article["source"],
            "url": article.get("url", ""),
            "publishedAt": article["published_at"],
            "sentiment": sentiment,
            "riskScore": risk_score
        })

        # 기업 연결
        if mentioned:
            link_query = """
            MATCH (n:NewsArticle {id: $newsId})
            UNWIND $companies AS companyName
            MATCH (c:Company {name: companyName})
            MERGE (n)-[:MENTIONS]->(c)
            """
            neo4j_client.execute_write(link_query, {
                "newsId": news_id,
                "companies": mentioned
            })

        logger.info(f"뉴스 로드: {title[:30]}... ({sentiment}, 점수: {risk_score})")


def update_company_risk_from_news():
    """뉴스 기반 기업 리스크 점수 업데이트"""
    query = """
    MATCH (c:Company)<-[:MENTIONS]-(n:NewsArticle)
    WHERE n.publishedAt > datetime() - duration('P7D')
    WITH c, avg(n.riskScore) AS avgNewsRisk, count(n) AS newsCount
    SET c.newsRiskScore = toInteger(avgNewsRisk),
        c.recentNewsCount = newsCount,
        c.totalRiskScore = toInteger(
            c.directRiskScore * 0.6 +
            coalesce(avgNewsRisk, 50) * 0.3 +
            coalesce(c.propagatedRiskScore, 0) * 0.1
        )
    """

    try:
        result = neo4j_client.execute_write(query)
        logger.info(f"기업 리스크 점수 업데이트 완료: {result}")
    except Exception as e:
        logger.error(f"리스크 점수 업데이트 실패: {e}")


def main():
    """메인 실행"""
    logger.info("=" * 60)
    logger.info("뉴스 데이터 → Neo4j 로드 시작")
    logger.info("=" * 60)

    # 1. 알려진 기업 목록 조회
    known_companies = get_known_companies_from_neo4j()
    logger.info(f"알려진 기업 수: {len(known_companies)}")

    # 2. 뉴스 데이터 가져오기 (샘플 또는 실제 API)
    news_data = get_sample_news_data()

    # 3. Neo4j 로드
    load_news_to_neo4j(news_data, known_companies)

    # 4. 기업 리스크 점수 업데이트
    update_company_risk_from_news()

    logger.info("=" * 60)
    logger.info(f"완료! {len(news_data)}개 뉴스 로드됨")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
