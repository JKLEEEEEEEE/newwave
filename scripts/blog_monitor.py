"""
블로그 모니터 — 시연용 리스크 뉴스 실시간 탐지

네이버 블로그 RSS를 30초 간격으로 폴링하여
새 글이 올라오면 리스크 키워드 분석 → Neo4j 저장.

Usage:
    python scripts/blog_monitor.py                    # 전체 딜 대상
    python scripts/blog_monitor.py --deal 제일엠앤에스  # 특정 딜 대상
    python scripts/blog_monitor.py --interval 10       # 10초 간격

On/Off:
    - Ctrl+C 로 중지
    - 다시 실행하면 재개 (이미 처리된 글은 skip)
"""

from __future__ import annotations
import argparse
import hashlib
import logging
import signal
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 프로젝트 루트를 path에 추가
sys.path.insert(0, ".")
load_dotenv(".env.local")

from risk_engine.neo4j_client import Neo4jClient
from risk_engine.news_collector_v2 import NewsData, NewsCollectorV2
from risk_engine.keywords import match_keywords
from risk_engine.score_engine import calculate_final_score

logger = logging.getLogger(__name__)

BLOG_RSS_URL = "https://rss.blog.naver.com/cmylose0102.xml"
DEFAULT_INTERVAL = 30  # 초


class BlogMonitor:
    """네이버 블로그 RSS 실시간 모니터"""

    def __init__(self, neo4j_client: Neo4jClient, interval: int = DEFAULT_INTERVAL):
        self.client = neo4j_client
        self.collector = NewsCollectorV2(neo4j_client)
        self.interval = interval
        self.seen_hashes: set[str] = set()
        self.running = False
        self._load_existing_hashes()

    def _load_existing_hashes(self):
        """이미 저장된 블로그 뉴스 해시 로드 (중복 방지)"""
        try:
            results = self.client.execute_read("""
                MATCH (ev:RiskEvent)
                WHERE ev.sourceName = 'BlogMonitor'
                RETURN ev.id AS id
            """, {})
            for r in results:
                self.seen_hashes.add(r["id"])
            if self.seen_hashes:
                logger.info(f"기존 블로그 뉴스 {len(self.seen_hashes)}건 로드 (skip 대상)")
        except Exception as e:
            logger.warning(f"기존 해시 로드 실패: {e}")

    def _fetch_rss(self) -> list[dict]:
        """블로그 RSS 파싱"""
        try:
            resp = requests.get(BLOG_RSS_URL, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "xml")

            posts = []
            for item in soup.find_all("item"):
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                desc = item.find("description")

                if not title or not link:
                    continue

                url = link.get_text().strip()
                url_hash = hashlib.md5(url.lower().encode()).hexdigest()

                posts.append({
                    "title": title.get_text().strip(),
                    "url": url,
                    "url_hash": url_hash,
                    "id": f"BLOG_{url_hash[:12]}",
                    "published_at": pub_date.get_text().strip() if pub_date else "",
                    "description": desc.get_text().strip()[:200] if desc else "",
                })
            return posts

        except Exception as e:
            logger.error(f"RSS 요청 실패: {e}")
            return []

    def _analyze_and_save(self, post: dict, target_companies: list[str]) -> bool:
        """블로그 글 분석 → Neo4j 저장"""
        title = post["title"]
        desc = post.get("description", "")
        text = f"{title} {desc}"

        # 키워드 매칭 (제목 + 설명)
        match_result = match_keywords(text, source="NEWS")

        if match_result.keyword_count == 0:
            logger.info(f"  [SKIP] 키워드 없음: {title[:40]}")
            return False

        # 점수 계산
        score_result = calculate_final_score(match_result, datetime.now(), source="NEWS")

        keywords_str = ", ".join(f"{kw.keyword}({kw.score})" for kw in match_result.matched_keywords[:5])
        logger.info(
            f"  [RISK] {title[:40]}... "
            f"→ score={score_result.final_score:.1f} "
            f"keywords=[{keywords_str}]"
        )

        # 매칭되는 기업에 저장
        cat_code = self.collector.CAT_CODE_MAP.get(
            match_result.primary_category, "OTHER"
        ) if match_result.primary_category else "OTHER"

        saved = 0
        for company_name in target_companies:
            try:
                score = score_result.final_score
                severity = "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"

                self.client.execute_write("""
                    MATCH (c:Company {name: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory {code: $catCode})
                    WITH rc LIMIT 1
                    MERGE (re:RiskEntity {id: $entityId})
                    ON CREATE SET
                        re.name = $entityName, re.type = 'ISSUE',
                        re.subType = 'BLOG_MONITOR', re.createdAt = datetime()
                    ON MATCH SET re.updatedAt = datetime()
                    MERGE (rc)-[:HAS_ENTITY]->(re)
                    WITH re
                    MERGE (ev:RiskEvent {id: $eventId})
                    ON CREATE SET
                        ev.title = $title, ev.summary = $summary,
                        ev.type = 'NEWS', ev.score = $score, ev.severity = $severity,
                        ev.sourceName = 'BlogMonitor', ev.sourceUrl = $sourceUrl,
                        ev.publishedAt = $publishedAt, ev.isActive = true,
                        ev.createdAt = datetime()
                    ON MATCH SET
                        ev.title = $title, ev.score = $score, ev.updatedAt = datetime()
                    MERGE (re)-[:HAS_EVENT]->(ev)
                """, {
                    "companyId": company_name,
                    "catCode": cat_code,
                    "entityId": f"ENT_BLOG_{post['id'][:12]}",
                    "entityName": title[:30],
                    "eventId": f"EVT_{post['id']}",
                    "title": title,
                    "summary": title,
                    "score": score,
                    "severity": severity,
                    "sourceUrl": post["url"],
                    "publishedAt": post.get("published_at", ""),
                })
                saved += 1
            except Exception as e:
                logger.error(f"  저장 실패 ({company_name}): {e}")

        if saved > 0:
            # 점수 재계산
            for company_name in target_companies:
                self._recalc_score(company_name)

        return saved > 0

    def _recalc_score(self, company_name: str):
        """기업 점수 재계산"""
        try:
            from risk_engine.v4.pipelines.full_pipeline import run_full_pipeline
            run_full_pipeline(self.client, company_name)
        except Exception as e:
            logger.warning(f"점수 재계산 실패 ({company_name}): {e}")

    def _get_target_companies(self, deal_filter: str | None) -> list[str]:
        """모니터링 대상 기업 조회"""
        if deal_filter:
            query = """
                MATCH (d:Deal)-[:TARGET]->(c:Company)
                WHERE c.name CONTAINS $filter OR d.id CONTAINS $filter
                RETURN c.name AS name
            """
            results = self.client.execute_read(query, {"filter": deal_filter})
        else:
            query = """
                MATCH (d:Deal)-[:TARGET]->(c:Company)
                RETURN c.name AS name
            """
            results = self.client.execute_read(query, {})

        return [r["name"] for r in results]

    def start(self, deal_filter: str | None = None):
        """모니터링 시작"""
        target_companies = self._get_target_companies(deal_filter)
        if not target_companies:
            logger.error("모니터링 대상 기업이 없습니다")
            return

        self.running = True
        scope = deal_filter or "전체"
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"  Blog Monitor 시작")
        logger.info(f"  RSS: {BLOG_RSS_URL}")
        logger.info(f"  대상: {', '.join(target_companies)} ({scope})")
        logger.info(f"  간격: {self.interval}초")
        logger.info(f"  중지: Ctrl+C")
        logger.info(f"{'='*60}")
        logger.info(f"")

        cycle = 0
        while self.running:
            cycle += 1
            now = datetime.now().strftime("%H:%M:%S")
            posts = self._fetch_rss()

            new_posts = [p for p in posts if p["id"] not in self.seen_hashes]

            if new_posts:
                logger.info(f"[{now}] #{cycle} 새 글 {len(new_posts)}건 발견!")
                for post in new_posts:
                    self.seen_hashes.add(post["id"])
                    self._analyze_and_save(post, target_companies)
            else:
                logger.info(f"[{now}] #{cycle} 대기 중... (기존 {len(posts)}건, 신규 0건)")

            time.sleep(self.interval)

    def stop(self):
        """모니터링 중지"""
        self.running = False
        logger.info("\nBlog Monitor 중지됨")


def main():
    parser = argparse.ArgumentParser(description="블로그 리스크 모니터 (시연용)")
    parser.add_argument("--deal", type=str, default=None, help="특정 딜/기업명 필터")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="폴링 간격 (초)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    sys.stdout.reconfigure(encoding="utf-8")

    client = Neo4jClient()
    monitor = BlogMonitor(client, interval=args.interval)

    def _shutdown(sig, frame):
        monitor.stop()
        client.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        monitor.start(deal_filter=args.deal)
    finally:
        client.close()


if __name__ == "__main__":
    main()
