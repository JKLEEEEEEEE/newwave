"""
Graph DB V7 초기화 스크립트 - 스키마/인덱스만 생성
==============================================
- 인덱스 및 제약조건만 생성
- 기업/딜은 API (POST /api/v4/deals) 또는 DealService로 등록
- 기존 데이터 삭제 옵션 제공

Usage:
    python scripts/init_graph_v7.py              # 인덱스 생성 (기존 데이터 유지)
    python scripts/init_graph_v7.py --clear       # 기존 데이터 삭제 후 인덱스 생성
"""

from neo4j import GraphDatabase
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
# DB 초기화 함수
# ============================================================

def clear_database(tx):
    """전체 데이터 삭제"""
    tx.run("MATCH (n) DETACH DELETE n")
    print("[OK] 기존 데이터 모두 삭제")


def create_indexes(tx):
    """인덱스 생성 (8개)"""
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


def print_summary(tx):
    """현재 노드/관계 현황 출력"""
    print("\n" + "=" * 70)
    print("          Graph DB V7 - 스키마 초기화 완료")
    print("          (기업/딜은 API로 등록: POST /api/v4/deals)")
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
        UNION ALL MATCH ()-[r:HAS_ENTITY]->() RETURN 'HAS_ENTITY' AS type, count(r) AS count
        UNION ALL MATCH ()-[r:HAS_EVENT]->() RETURN 'HAS_EVENT' AS type, count(r) AS count
    """)
    print("\n[관계 현황]")
    for r in result:
        print(f"   {r['type']}: {r['count']}개")

    print("\n" + "=" * 70)
    print("다음 단계:")
    print("  - API로 딜 등록: POST /api/v4/deals {companyName, sector, ...}")
    print("  - CLI로 딜 등록: python -m risk_engine.deal_manager --add '기업명' '섹터'")
    print("  - 수집 실행:     python scripts/collect_for_deal.py")
    print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Graph DB V7 초기화 (스키마/인덱스만 생성, 기업/딜은 API로 등록)")
    parser.add_argument("--clear", action="store_true", help="기존 데이터 모두 삭제 후 인덱스 생성")
    args = parser.parse_args()

    print(f"Neo4j: {URI}, DB: {DATABASE}")
    print(f"Mode: {'CLEAR (데이터 삭제 + 인덱스)' if args.clear else 'INDEX ONLY (인덱스만 생성)'}")

    with driver.session(database=DATABASE) as session:
        if args.clear:
            session.execute_write(clear_database)

        session.execute_write(create_indexes)

        # 현재 상태 출력
        session.execute_read(print_summary)

    driver.close()


if __name__ == "__main__":
    main()
