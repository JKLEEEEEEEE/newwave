"""
딜 단위 전체 수집 오케스트레이터
================================
init_graph_v7.py 실행 후 호출하여 실제 데이터를 수집합니다.

흐름:
  1. Neo4j에서 Deal → Company → Related Company 조회
  2. 각 Company에 대해:
     - corpCode 있으면 → DartCollectorV2 (공시, 주주, 임원, 리스크이벤트, 대량보유, 재무지표)
     - 모든 기업 → NewsCollectorV2 (뉴스)
  3. CategoryService → 카테고리 점수 재계산
  4. ScoreService → 기업 총점 재계산
  5. 수집 결과 리포트 출력

Usage:
    python scripts/collect_for_deal.py                   # 모든 딜 대상 수집
    python scripts/collect_for_deal.py --deal 카카오      # 특정 딜만
    python scripts/collect_for_deal.py --news-only        # 뉴스만 수집
    python scripts/collect_for_deal.py --dart-only        # DART만 수집
"""

import argparse
import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional

# 프로젝트 루트 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# DART API 호출 딜레이 (분당 100건 제한 준수)
DART_DELAY = 0.7  # 초
NEWS_DELAY = 1.0  # 기업 간 딜레이


def get_neo4j_client():
    from risk_engine.neo4j_client import Neo4jClient
    client = Neo4jClient()
    client.connect()
    return client


def get_deal_companies(client, deal_filter: Optional[str] = None) -> list[dict]:
    """딜별 메인 + 관련 기업 조회

    Returns:
        [{"deal": "카카오 검토", "name": "카카오", "corpCode": "00258801", "isMain": True}, ...]
    """
    if deal_filter:
        query = """
        MATCH (d:Deal)-[:TARGET]->(c:Company)
        WHERE d.name CONTAINS $deal OR c.name CONTAINS $deal
        OPTIONAL MATCH (c)-[:HAS_RELATED]->(rel:Company)
        WITH d.name AS deal,
             collect(DISTINCT {name: c.name, corpCode: coalesce(c.corpCode, ''), isMain: true}) +
             collect(DISTINCT {name: rel.name, corpCode: coalesce(rel.corpCode, ''), isMain: false}) AS companies
        UNWIND companies AS comp
        RETURN DISTINCT deal, comp.name AS name, comp.corpCode AS corpCode, comp.isMain AS isMain
        """
        results = client.execute_read(query, {"deal": deal_filter})
    else:
        query = """
        MATCH (d:Deal)-[:TARGET]->(c:Company)
        OPTIONAL MATCH (c)-[:HAS_RELATED]->(rel:Company)
        WITH d.name AS deal,
             collect(DISTINCT {name: c.name, corpCode: coalesce(c.corpCode, ''), isMain: true}) +
             collect(DISTINCT {name: rel.name, corpCode: coalesce(rel.corpCode, ''), isMain: false}) AS companies
        UNWIND companies AS comp
        RETURN DISTINCT deal, comp.name AS name, comp.corpCode AS corpCode, comp.isMain AS isMain
        """
        results = client.execute_read(query)

    # null 이름 필터링
    return [r for r in (results or []) if r.get('name')]


def collect_dart_for_company(collector, company_name: str, corp_code: str) -> dict:
    """단일 기업 DART 전체 수집"""
    stats = {"disclosures": 0, "risk_events": 0, "shareholders": 0,
             "executives": 0, "major_stock": 0, "sh_changes": 0, "financials": 0}

    # 1) 공시 목록
    try:
        result = collector.collect_disclosures(corp_code)
        if result and result.total_valid > 0:
            saved = collector.save_to_neo4j(result.disclosures)
            stats["disclosures"] = saved
            print(f"    [공시] {result.total_valid}건 수집 → {saved}건 저장")
        else:
            print(f"    [공시] 리스크 관련 공시 없음")
    except Exception as e:
        print(f"    [공시] ERR: {e}")
    time.sleep(DART_DELAY)

    # 2) 주요사항보고서 리스크
    try:
        risk_data = collector.collect_risk_events(corp_code)
        if risk_data:
            saved = collector.save_risk_events_to_neo4j(risk_data, company_name)
            stats["risk_events"] = saved
            for key, data in risk_data.items():
                print(f"    [{data['label']}] {len(data['items'])}건 (score: {data['base_score']})")
        else:
            print(f"    [리스크] 해당 없음")
    except Exception as e:
        print(f"    [리스크] ERR: {e}")
    time.sleep(DART_DELAY)

    # 3) 주주 수집
    try:
        shareholders = collector.collect_shareholders(corp_code)
        if shareholders:
            saved = collector.save_shareholders_to_neo4j(shareholders, company_name, corp_code)
            stats["shareholders"] = saved
            print(f"    [주주] {saved}명 저장")
        else:
            print(f"    [주주] 정보 없음")
    except Exception as e:
        print(f"    [주주] ERR: {e}")
    time.sleep(DART_DELAY)

    # 4) 임원 수집
    try:
        executives = collector.collect_executives(corp_code)
        if executives:
            saved = collector.save_executives_to_neo4j(executives, company_name, corp_code)
            stats["executives"] = saved
            print(f"    [임원] {saved}명 저장")
        else:
            print(f"    [임원] 정보 없음")
    except Exception as e:
        print(f"    [임원] ERR: {e}")
    time.sleep(DART_DELAY)

    # 5) 대량보유 상황보고
    try:
        major_stocks = collector.collect_major_stock(corp_code)
        if major_stocks:
            saved = collector.save_major_stock_to_neo4j(major_stocks, company_name, corp_code)
            stats["major_stock"] = saved
            print(f"    [대량보유] {saved}건 저장")
        else:
            print(f"    [대량보유] 보고 없음")
    except Exception as e:
        print(f"    [대량보유] ERR: {e}")
    time.sleep(DART_DELAY)

    # 6) 최대주주 변동현황
    try:
        sh_changes = collector.collect_shareholder_changes(corp_code)
        if sh_changes:
            saved = collector.save_shareholder_changes_to_neo4j(sh_changes, company_name, corp_code)
            stats["sh_changes"] = saved
            print(f"    [주주변동] {saved}건 저장")
        else:
            print(f"    [주주변동] 변동 없음")
    except Exception as e:
        print(f"    [주주변동] ERR: {e}")
    time.sleep(DART_DELAY)

    # 7) 주요 재무지표
    try:
        indices = collector.collect_financial_indices(corp_code)
        if indices:
            saved = collector.save_financial_indices_to_neo4j(indices, company_name, corp_code)
            stats["financials"] = saved
            print(f"    [재무지표] {saved}개 지표 저장")
        else:
            print(f"    [재무지표] 데이터 없음")
    except Exception as e:
        print(f"    [재무지표] ERR: {e}")
    time.sleep(DART_DELAY)

    return stats


def collect_news_for_company(collector, company_name: str) -> int:
    """단일 기업 뉴스 수집"""
    try:
        result = collector.collect_news(company_name, limit=30)
        if result and result.news_list:
            saved = collector.save_to_neo4j(result.news_list, company_name)
            print(f"    [뉴스] {len(result.news_list)}건 수집 → {saved}건 저장")
            return saved
        else:
            print(f"    [뉴스] 새 뉴스 없음")
            return 0
    except Exception as e:
        print(f"    [뉴스] ERR: {e}")
        return 0


def update_scores(client, companies: list[str]):
    """카테고리 + 기업 점수 재계산 (5-Node 스키마)"""
    print("\n[SCORE] 점수 재계산 시작...")

    # Entity 점수 = 소속 이벤트 시간감쇠 합산
    # publishedAt이 ISO 형식이 아닐 수 있으므로 collectedAt(datetime)을 우선 사용
    client.execute_write("""
        MATCH (ent:RiskEntity)-[:HAS_EVENT]->(evt:RiskEvent)
        WHERE evt.score > 0
        WITH ent, evt,
             evt.score AS rawScore,
             CASE
               WHEN evt.collectedAt IS NOT NULL AND evt.collectedAt <> ''
                 THEN toInteger((datetime().epochMillis - evt.collectedAt.epochMillis) / 86400000)
               WHEN evt.createdAt IS NOT NULL AND evt.createdAt <> ''
                 THEN toInteger((datetime().epochMillis - evt.createdAt.epochMillis) / 86400000)
               ELSE 30
             END AS daysAgo
        WITH ent, rawScore, CASE WHEN daysAgo < 0 THEN 0 ELSE daysAgo END AS daysAgo
        WITH ent, rawScore, daysAgo,
             CASE
               WHEN daysAgo <= 3  THEN 1.0
               WHEN daysAgo <= 7  THEN 0.80
               WHEN daysAgo <= 14 THEN 0.55
               WHEN daysAgo <= 30 THEN 0.30
               WHEN daysAgo <= 60 THEN 0.15
               ELSE 0.05
             END AS decay
        WITH ent, SUM(rawScore * decay) AS decayed, COUNT(*) AS cnt
        SET ent.riskScore = CASE WHEN decayed > 100 THEN 100 ELSE toInteger(decayed) END,
            ent.eventCount = cnt
    """)

    # 이벤트 없는 Entity 초기화
    client.execute_write("""
        MATCH (ent:RiskEntity)
        WHERE NOT (ent)-[:HAS_EVENT]->()
        SET ent.riskScore = 0, ent.eventCount = 0
    """)

    # Category 점수 집계
    client.execute_write("""
        MATCH (rc:RiskCategory)-[:HAS_ENTITY]->(ent:RiskEntity)
        WITH rc, SUM(ent.riskScore) AS raw, COUNT(ent) AS entCount
        WITH rc, CASE WHEN raw > 200 THEN 200 ELSE raw END AS totalScore, entCount
        SET rc.score = totalScore, rc.entityCount = entCount,
            rc.weightedScore = totalScore * rc.weight
    """)

    # Category 이벤트 수
    client.execute_write("""
        MATCH (rc:RiskCategory)-[:HAS_ENTITY]->(ent:RiskEntity)-[:HAS_EVENT]->(evt:RiskEvent)
        WITH rc, COUNT(evt) AS evtCount
        SET rc.eventCount = evtCount
    """)

    # 이벤트 없는 카테고리 초기화
    client.execute_write("""
        MATCH (rc:RiskCategory)
        WHERE NOT (rc)-[:HAS_ENTITY]->(:RiskEntity)-[:HAS_EVENT]->()
        SET rc.score = 0, rc.weightedScore = 0, rc.eventCount = 0
    """)

    # Company 직접 점수
    client.execute_write("""
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WITH c, SUM(rc.weightedScore) AS directScore
        SET c.directScore = toInteger(directScore)
    """)

    # Company 전이 점수
    client.execute_write("""
        MATCH (c:Company)-[:HAS_RELATED]->(r:Company)
        WITH c, SUM(r.directScore) * 0.3 AS propagatedScore
        SET c.propagatedScore = toInteger(propagatedScore)
    """)
    client.execute_write("""
        MATCH (c:Company)
        WHERE NOT (c)-[:HAS_RELATED]->()
        SET c.propagatedScore = 0
    """)

    # 총점 (cap 100) 및 레벨
    client.execute_write("""
        MATCH (c:Company)
        WITH c, c.directScore + c.propagatedScore AS raw
        SET c.totalRiskScore = CASE WHEN raw > 100 THEN 100 ELSE raw END,
            c.riskLevel = CASE
                WHEN raw >= 60 THEN 'FAIL'
                WHEN raw >= 35 THEN 'WARNING'
                ELSE 'PASS'
            END,
            c.updatedAt = datetime()
    """)

    # 결과 출력
    for company in companies:
        result = client.execute_read_single("""
            MATCH (c:Company {name: $name})
            RETURN c.directScore AS direct, c.propagatedScore AS propagated,
                   c.totalRiskScore AS total, c.riskLevel AS level
        """, {"name": company})
        if result:
            print(f"  [{company}] direct:{result['direct']} propagated:{result['propagated']} "
                  f"total:{result['total']} ({result['level']})")

    print("[OK] 점수 재계산 완료\n")


def print_report(client):
    """수집 결과 리포트"""
    print("\n" + "=" * 60)
    print("  수집 결과 리포트")
    print("=" * 60)

    # 노드 현황
    result = client.execute_read("""
        MATCH (d:Deal) RETURN 'Deal' AS label, count(d) AS count
        UNION ALL MATCH (c:Company) RETURN 'Company' AS label, count(c) AS count
        UNION ALL MATCH (rc:RiskCategory) RETURN 'RiskCategory' AS label, count(rc) AS count
        UNION ALL MATCH (e:RiskEntity) RETURN 'RiskEntity' AS label, count(e) AS count
        UNION ALL MATCH (ev:RiskEvent) RETURN 'RiskEvent' AS label, count(ev) AS count
    """)
    print("\n[노드 현황]")
    for r in (result or []):
        print(f"   {r['label']}: {r['count']}개")

    # 기업별 점수
    result = client.execute_read("""
        MATCH (d:Deal)-[:TARGET]->(c:Company)
        RETURN d.name AS deal, c.name AS company,
               c.totalRiskScore AS score, c.riskLevel AS level
        ORDER BY c.totalRiskScore DESC
    """)
    if result:
        print("\n[딜별 리스크 점수]")
        for r in result:
            print(f"   {r['deal']}: {r['company']} → {r['score']}점 ({r['level']})")

    # 고위험 이벤트
    result = client.execute_read("""
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
              -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
        WHERE ev.score >= 40
        RETURN c.name AS company, ev.title AS title, ev.score AS score, ev.type AS type
        ORDER BY ev.score DESC LIMIT 10
    """)
    if result:
        print(f"\n[고위험 이벤트 Top {len(result)}]")
        for r in result:
            title = r['title'][:45] + "..." if len(r.get('title', '') or '') > 45 else r.get('title', '')
            print(f"   [{r['score']}] {r['company']}: {title} ({r['type']})")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="딜 단위 전체 수집 오케스트레이터")
    parser.add_argument("--deal", "-d", help="특정 딜/기업명으로 필터")
    parser.add_argument("--news-only", action="store_true", help="뉴스만 수집")
    parser.add_argument("--dart-only", action="store_true", help="DART만 수집")
    parser.add_argument("--no-score", action="store_true", help="점수 계산 스킵")
    args = parser.parse_args()

    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("  딜 단위 데이터 수집 파이프라인")
    print(f"  시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if args.deal:
        print(f"  필터: {args.deal}")
    print("=" * 60)

    client = get_neo4j_client()

    # 1. 딜별 기업 조회
    companies = get_deal_companies(client, args.deal)
    if not companies:
        print("\n[ERR] 수집할 기업이 없습니다.")
        print("  먼저 python scripts/init_graph_v7.py 를 실행하세요.")
        client.close()
        return

    # 기업 목록 출력
    main_companies = [c for c in companies if c.get('isMain')]
    related_companies = [c for c in companies if not c.get('isMain')]
    dart_companies = [c for c in companies if c.get('corpCode')]
    news_only_companies = [c for c in companies if not c.get('corpCode')]

    print(f"\n[대상] 메인 {len(main_companies)}개, 관련 {len(related_companies)}개")
    print(f"  DART 수집 가능: {len(dart_companies)}개")
    print(f"  뉴스만 수집: {len(news_only_companies)}개")

    # 중복 제거 (이름 기준)
    seen_names = set()
    unique_companies = []
    for c in companies:
        if c['name'] not in seen_names:
            seen_names.add(c['name'])
            unique_companies.append(c)

    total_dart = 0
    total_news = 0

    # 2. DART 수집
    if not args.news_only:
        api_key = os.getenv("OPENDART_API_KEY")
        if api_key:
            from risk_engine.dart_collector_v2 import DartCollectorV2
            dart_collector = DartCollectorV2(api_key, client)

            dart_targets = [c for c in unique_companies if c.get('corpCode')]
            if dart_targets:
                print(f"\n{'='*40}")
                print(f"  DART 수집 ({len(dart_targets)}개 기업)")
                print(f"{'='*40}")

                for comp in dart_targets:
                    name = comp['name']
                    corp_code = comp['corpCode']
                    tag = "[메인]" if comp.get('isMain') else "[관련]"
                    print(f"\n  {tag} {name} (corpCode: {corp_code})")

                    stats = collect_dart_for_company(dart_collector, name, corp_code)
                    total_dart += sum(stats.values())
        else:
            print("\n[WARN] OPENDART_API_KEY 미설정 → DART 수집 스킵")

    # 3. 뉴스 수집
    if not args.dart_only:
        from risk_engine.news_collector_v2 import NewsCollectorV2
        news_collector = NewsCollectorV2(client)

        print(f"\n{'='*40}")
        print(f"  뉴스 수집 ({len(unique_companies)}개 기업)")
        print(f"{'='*40}")

        for comp in unique_companies:
            name = comp['name']
            tag = "[메인]" if comp.get('isMain') else "[관련]"
            print(f"\n  {tag} {name}")

            saved = collect_news_for_company(news_collector, name)
            total_news += saved
            time.sleep(NEWS_DELAY)

    # 4. 점수 재계산
    if not args.no_score:
        all_names = [c['name'] for c in unique_companies]
        update_scores(client, all_names)

    # 5. 리포트
    print_report(client)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n  DART: {total_dart}건, NEWS: {total_news}건")
    print(f"  소요 시간: {int(elapsed)}초")
    print("=" * 60 + "\n")

    client.close()


if __name__ == "__main__":
    main()
