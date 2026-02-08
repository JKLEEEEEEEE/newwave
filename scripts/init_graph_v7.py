"""
Graph DB V7 초기화 스크립트 - 구조만 생성 (경량)
==============================================
- Deal, Company (corpCode 포함), RiskCategory, Relationships만 생성
- RiskEntity / RiskEvent는 수집 파이프라인(collect_for_deal.py)에서 실제 데이터로 채움
- 인덱스 / 제약조건 포함

Usage:
    python scripts/init_graph_v7.py              # 전체 초기화 (기존 데이터 삭제)
    python scripts/init_graph_v7.py --keep       # 기존 데이터 유지, 누락분만 생성
"""

from neo4j import GraphDatabase
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.local'))

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

# ============================================================
# 10개 카테고리 (LOCKED)
# ============================================================
CATEGORIES = [
    {"code": "SHARE", "name": "주주", "icon": "📊", "weight": 0.15},
    {"code": "EXEC", "name": "임원", "icon": "👔", "weight": 0.15},
    {"code": "CREDIT", "name": "신용", "icon": "💳", "weight": 0.15},
    {"code": "LEGAL", "name": "법률", "icon": "⚖️", "weight": 0.12},
    {"code": "GOV", "name": "지배구조", "icon": "🏛️", "weight": 0.10},
    {"code": "OPS", "name": "운영", "icon": "⚙️", "weight": 0.10},
    {"code": "AUDIT", "name": "감사", "icon": "📋", "weight": 0.08},
    {"code": "ESG", "name": "ESG", "icon": "🌱", "weight": 0.08},
    {"code": "SUPPLY", "name": "공급망", "icon": "🔗", "weight": 0.05},
    {"code": "OTHER", "name": "기타", "icon": "📎", "weight": 0.02},
]

# ============================================================
# 메인 기업 4개 (corpCode = DART API 조회용 8자리 코드)
# ============================================================
MAIN_COMPANIES = [
    {
        "id": "COMP_KKO", "name": "카카오", "ticker": "035720",
        "corpCode": "00258801", "sector": "IT/플랫폼", "market": "KOSPI", "isMain": True,
    },
    {
        "id": "COMP_NVR", "name": "네이버", "ticker": "035420",
        "corpCode": "00266961", "sector": "IT/검색", "market": "KOSPI", "isMain": True,
    },
    {
        "id": "COMP_SS", "name": "삼성전자", "ticker": "005930",
        "corpCode": "00126380", "sector": "전자/반도체", "market": "KOSPI", "isMain": True,
    },
    {
        "id": "COMP_JK", "name": "잡코리아", "ticker": "000000",
        "corpCode": "", "sector": "HR/채용", "market": "비상장", "isMain": True,
    },
]

# ============================================================
# 관련 기업 11개
# ============================================================
RELATED_COMPANIES = [
    # 카카오 관련
    {"id": "COMP_KBANK", "name": "카카오뱅크", "ticker": "323410", "corpCode": "01133217",
     "sector": "금융", "market": "KOSPI", "isMain": False, "main": "COMP_KKO", "rel": "계열사", "tier": 1},
    {"id": "COMP_KPAY", "name": "카카오페이", "ticker": "377300", "corpCode": "01244601",
     "sector": "핀테크", "market": "KOSPI", "isMain": False, "main": "COMP_KKO", "rel": "계열사", "tier": 1},
    {"id": "COMP_SM", "name": "SM엔터테인먼트", "ticker": "041510", "corpCode": "00260930",
     "sector": "엔터", "market": "KOSDAQ", "isMain": False, "main": "COMP_KKO", "rel": "인수대상", "tier": 2},
    # 네이버 관련
    {"id": "COMP_LY", "name": "라인야후", "ticker": "", "corpCode": "",
     "sector": "IT/메신저", "market": "TSE", "isMain": False, "main": "COMP_NVR", "rel": "합작사", "tier": 1},
    {"id": "COMP_WEBT", "name": "네이버웹툰", "ticker": "", "corpCode": "",
     "sector": "콘텐츠", "market": "NASDAQ", "isMain": False, "main": "COMP_NVR", "rel": "계열사", "tier": 1},
    {"id": "COMP_NCLD", "name": "네이버클라우드", "ticker": "", "corpCode": "",
     "sector": "클라우드", "market": "비상장", "isMain": False, "main": "COMP_NVR", "rel": "계열사", "tier": 2},
    # 삼성전자 관련
    {"id": "COMP_SDI", "name": "삼성SDI", "ticker": "006400", "corpCode": "00126362",
     "sector": "배터리", "market": "KOSPI", "isMain": False, "main": "COMP_SS", "rel": "계열사", "tier": 1},
    {"id": "COMP_TSMC", "name": "TSMC", "ticker": "TSM", "corpCode": "",
     "sector": "반도체", "market": "NYSE", "isMain": False, "main": "COMP_SS", "rel": "경쟁사", "tier": 2},
    {"id": "COMP_SDP", "name": "삼성디스플레이", "ticker": "", "corpCode": "",
     "sector": "디스플레이", "market": "비상장", "isMain": False, "main": "COMP_SS", "rel": "계열사", "tier": 1},
    # 잡코리아 관련
    {"id": "COMP_ALB", "name": "알바몬", "ticker": "", "corpCode": "",
     "sector": "HR/채용", "market": "비상장", "isMain": False, "main": "COMP_JK", "rel": "계열사", "tier": 1},
    {"id": "COMP_SRI", "name": "사람인", "ticker": "143240", "corpCode": "00857480",
     "sector": "HR/채용", "market": "KOSDAQ", "isMain": False, "main": "COMP_JK", "rel": "경쟁사", "tier": 2},
]

# ============================================================
# Deal 4개
# ============================================================
DEALS = [
    {"id": "DEAL_001", "name": "카카오 검토", "status": "ACTIVE", "analyst": "김철수",
     "notes": "플랫폼 규제 리스크 중점", "mainCompanyId": "COMP_KKO"},
    {"id": "DEAL_002", "name": "네이버 검토", "status": "ACTIVE", "analyst": "이영희",
     "notes": "라인야후 리스크 중점", "mainCompanyId": "COMP_NVR"},
    {"id": "DEAL_003", "name": "삼성전자 검토", "status": "ACTIVE", "analyst": "박민수",
     "notes": "파운드리/HBM 경쟁력", "mainCompanyId": "COMP_SS"},
    {"id": "DEAL_004", "name": "잡코리아 검토", "status": "ACTIVE", "analyst": "정다은",
     "notes": "채용시장 변화 대응", "mainCompanyId": "COMP_JK"},
]


# ============================================================
# DB 초기화 함수
# ============================================================

def clear_database(tx):
    tx.run("MATCH (n) DETACH DELETE n")
    print("[OK] 기존 데이터 모두 삭제")


def create_indexes(tx):
    indexes = [
        "CREATE INDEX deal_id IF NOT EXISTS FOR (d:Deal) ON (d.id)",
        "CREATE INDEX company_id IF NOT EXISTS FOR (c:Company) ON (c.id)",
        "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
        "CREATE INDEX company_corpcode IF NOT EXISTS FOR (c:Company) ON (c.corpCode)",
        "CREATE INDEX category_id IF NOT EXISTS FOR (c:RiskCategory) ON (c.id)",
        "CREATE INDEX category_code IF NOT EXISTS FOR (c:RiskCategory) ON (c.code)",
        "CREATE INDEX entity_id IF NOT EXISTS FOR (e:RiskEntity) ON (e.id)",
        "CREATE INDEX event_id IF NOT EXISTS FOR (e:RiskEvent) ON (e.id)",
    ]
    for idx in indexes:
        try:
            tx.run(idx)
        except Exception:
            pass
    print("[OK] 인덱스 생성 (8개)")


def create_company_with_categories(tx, company_data):
    """Company + 10개 RiskCategory 생성"""
    comp_id = company_data["id"]
    tx.run("""
        MERGE (c:Company {id: $id})
        SET c.name = $name, c.ticker = $ticker, c.corpCode = $corpCode,
            c.sector = $sector, c.market = $market, c.isMain = $isMain,
            c.directScore = 0, c.propagatedScore = 0,
            c.totalRiskScore = 0, c.riskLevel = 'PASS',
            c.createdAt = datetime(), c.updatedAt = datetime()
    """, company_data)

    for cat in CATEGORIES:
        cat_id = f"RC_{comp_id}_{cat['code']}"
        tx.run("""
            MATCH (c:Company {id: $compId})
            MERGE (rc:RiskCategory {id: $catId})
            SET rc.companyId = $compId, rc.code = $code, rc.name = $name,
                rc.icon = $icon, rc.weight = $weight,
                rc.score = 0, rc.weightedScore = 0,
                rc.entityCount = 0, rc.eventCount = 0,
                rc.trend = 'STABLE', rc.createdAt = datetime()
            MERGE (c)-[:HAS_CATEGORY]->(rc)
        """, {"compId": comp_id, "catId": cat_id, **cat})


def create_deal(tx, deal_data):
    """Deal 생성 + TARGET 관계"""
    tx.run("""
        MATCH (c:Company {id: $mainCompanyId})
        MERGE (d:Deal {id: $id})
        SET d.name = $name, d.status = $status, d.analyst = $analyst, d.notes = $notes,
            d.registeredAt = datetime(), d.updatedAt = datetime()
        MERGE (d)-[:TARGET]->(c)
    """, deal_data)


def create_related_link(tx, main_id, related_id, relation, tier):
    """관련기업 연결"""
    tx.run("""
        MATCH (m:Company {id: $mainId}), (r:Company {id: $relatedId})
        MERGE (m)-[:HAS_RELATED {relation: $relation, tier: $tier}]->(r)
    """, {"mainId": main_id, "relatedId": related_id, "relation": relation, "tier": tier})


def print_summary(tx):
    print("\n" + "=" * 70)
    print("          Graph DB V7 초기화 완료 (구조만, 수집 대기)")
    print("=" * 70)

    result = tx.run("""
        MATCH (d:Deal) RETURN 'Deal' AS label, count(d) AS count
        UNION ALL MATCH (c:Company) RETURN 'Company' AS label, count(c) AS count
        UNION ALL MATCH (rc:RiskCategory) RETURN 'RiskCategory' AS label, count(rc) AS count
        UNION ALL MATCH (e:RiskEntity) RETURN 'RiskEntity' AS label, count(e) AS count
        UNION ALL MATCH (ev:RiskEvent) RETURN 'RiskEvent' AS label, count(ev) AS count
    """)
    print("\n[노드 현황]")
    for r in result:
        print(f"   {r['label']}: {r['count']}개")

    result = tx.run("""
        MATCH ()-[r:TARGET]->() RETURN 'TARGET' AS type, count(r) AS count
        UNION ALL MATCH ()-[r:HAS_CATEGORY]->() RETURN 'HAS_CATEGORY' AS type, count(r) AS count
        UNION ALL MATCH ()-[r:HAS_RELATED]->() RETURN 'HAS_RELATED' AS type, count(r) AS count
    """)
    print("\n[관계 현황]")
    for r in result:
        print(f"   {r['type']}: {r['count']}개")

    # corpCode 현황
    result = tx.run("""
        MATCH (c:Company)
        WHERE c.corpCode IS NOT NULL AND c.corpCode <> ''
        RETURN c.name AS name, c.corpCode AS corpCode, c.ticker AS ticker
        ORDER BY c.name
    """)
    records = list(result)
    print(f"\n[DART corpCode 등록 기업: {len(records)}개]")
    for r in records:
        print(f"   {r['name']} (ticker:{r['ticker']}) → corpCode:{r['corpCode']}")

    # corpCode 미등록 기업 (뉴스만 수집 가능)
    result = tx.run("""
        MATCH (c:Company)
        WHERE c.corpCode IS NULL OR c.corpCode = ''
        RETURN c.name AS name, c.market AS market
        ORDER BY c.name
    """)
    no_code = list(result)
    if no_code:
        print(f"\n[corpCode 미등록 (뉴스만 수집): {len(no_code)}개]")
        for r in no_code:
            print(f"   {r['name']} ({r['market']})")

    print("\n" + "=" * 70)
    print("다음 단계: python scripts/collect_for_deal.py")
    print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Graph DB V7 초기화 (구조만)")
    parser.add_argument("--keep", action="store_true", help="기존 데이터 유지, 누락분만 MERGE")
    args = parser.parse_args()

    print(f"Neo4j: {URI}, DB: {DATABASE}")
    print(f"Mode: {'MERGE (기존 유지)' if args.keep else 'CLEAN (전체 재생성)'}")

    with driver.session(database=DATABASE) as session:
        if not args.keep:
            session.execute_write(clear_database)

        session.execute_write(create_indexes)

        # 1. 메인 기업 4개 + 10개 카테고리
        for c in MAIN_COMPANIES:
            session.execute_write(create_company_with_categories, c)
        print(f"[OK] 메인 Company {len(MAIN_COMPANIES)}개 (각 10개 카테고리)")

        # 2. 관련 기업 11개 + 연결
        for r in RELATED_COMPANIES:
            comp_data = {k: v for k, v in r.items() if k not in ("main", "rel", "tier")}
            session.execute_write(create_company_with_categories, comp_data)
            session.execute_write(create_related_link, r["main"], r["id"], r["rel"], r["tier"])
        print(f"[OK] 관련 Company {len(RELATED_COMPANIES)}개")

        # 3. Deal 4개
        for d in DEALS:
            session.execute_write(create_deal, d)
        print(f"[OK] Deal {len(DEALS)}개")

        # 요약
        session.execute_read(print_summary)

    driver.close()


if __name__ == "__main__":
    main()
