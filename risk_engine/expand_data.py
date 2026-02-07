#!/usr/bin/env python3
"""
============================================================================
Supply Chain 데이터 확장 CLI
============================================================================
Neo4j에 확장된 공급망 데이터를 로드합니다.

사용법:
    python -m risk_engine.expand_data
    python -m risk_engine.expand_data --discover
    python -m risk_engine.expand_data --stats
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트 설정
import pathlib
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env.local")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_banner():
    """배너 출력"""
    print("""
================================================================
          Supply Chain Data Expansion Tool v1.0
================================================================
  Neo4j Graph DB에 공급망 데이터를 확장합니다.
================================================================
    """)


def check_neo4j_connection():
    """Neo4j 연결 확인"""
    try:
        from risk_engine.neo4j_client import neo4j_client
        neo4j_client.connect()
        result = neo4j_client.execute_read_single("RETURN 1 AS check")
        neo4j_client.close()
        return result is not None
    except Exception as e:
        logger.error(f"Neo4j 연결 실패: {e}")
        return False


def load_sample_data():
    """샘플 데이터 로드"""
    print("\n[1] Step 1: 샘플 데이터 로드...")
    try:
        from risk_engine.load_supply_chain_data import load_supply_chain_data
        success = load_supply_chain_data()
        if success:
            print("   [OK] 샘플 데이터 로드 완료")
        else:
            print("   [WARN] 샘플 데이터 로드 부분 실패")
        return success
    except Exception as e:
        print(f"   [ERR] 샘플 데이터 로드 실패: {e}")
        return False


def run_discovery():
    """Supply Chain Discovery 실행"""
    print("\n[2] Step 2: Supply Chain 자동 탐색...")
    try:
        from risk_engine.neo4j_client import neo4j_client
        from risk_engine.supply_chain_discovery import SupplyChainDiscovery

        neo4j_client.connect()

        # DART 수집기 (선택적)
        dart_collector = None
        try:
            from risk_engine.dart_collector_v2 import DartCollectorV2
            dart_collector = DartCollectorV2()
            print("   * DART 수집기 활성화")
        except Exception as e:
            print(f"   [WARN] DART 수집기 미사용: {e}")

        # 뉴스 수집기 (선택적)
        news_collector = None
        try:
            from risk_engine.news_collector_v2 import NewsCollectorV2
            news_collector = NewsCollectorV2()
            print("   * 뉴스 수집기 활성화")
        except Exception as e:
            print(f"   [WARN] 뉴스 수집기 미사용: {e}")

        # Discovery 실행
        discovery = SupplyChainDiscovery(
            neo4j_client=neo4j_client,
            dart_collector=dart_collector,
            news_collector=news_collector,
        )

        relations = discovery.discover_all()
        print(f"   [STAT] {len(relations)}개 관계 발견")

        # Neo4j 저장
        saved = discovery.save_to_neo4j()
        print(f"   [SAVE] {saved}개 관계 Neo4j 저장 완료")

        # 통계
        stats = discovery.get_statistics()
        print(f"\n   [RESULT] 탐색 결과:")
        print(f"      - 한국 기업: {stats['korean_companies']}개")
        print(f"      - 글로벌 파트너: {stats['global_partners']}개")
        print(f"      - 관계 유형별:")
        for rel_type, count in stats['by_relation_type'].items():
            print(f"        - {rel_type}: {count}개")

        neo4j_client.close()
        return True

    except Exception as e:
        print(f"   [ERR] Discovery 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_statistics():
    """현재 데이터 통계 표시"""
    print("\n[STAT] 현재 데이터 통계:")
    try:
        from risk_engine.neo4j_client import neo4j_client
        neo4j_client.connect()

        # 기업 수
        company_query = """
        MATCH (c:Company)
        RETURN count(c) AS total,
               count(CASE WHEN c.isGlobal = true THEN 1 END) AS global,
               count(CASE WHEN c.isGlobal IS NULL OR c.isGlobal = false THEN 1 END) AS korean
        """
        company_result = neo4j_client.execute_read_single(company_query)
        if company_result:
            print(f"\n   [COMPANY] 기업 노드:")
            print(f"      - 총: {company_result['total']}개")
            print(f"      - 한국: {company_result['korean']}개")
            print(f"      - 글로벌: {company_result['global']}개")

        # 관계 수
        relation_query = """
        MATCH ()-[r]->()
        WHERE type(r) IN ['SUPPLIES_TO', 'COMPETES_WITH', 'PARTNER_OF', 'SUBSIDIARY_OF']
        RETURN type(r) AS relType, count(r) AS count
        ORDER BY count DESC
        """
        relation_results = neo4j_client.execute_read(relation_query)
        print(f"\n   [REL] 관계:")
        total_rels = 0
        for r in relation_results:
            print(f"      - {r['relType']}: {r['count']}개")
            total_rels += r['count']
        print(f"      - 총: {total_rels}개")

        # 산업별 분포
        sector_query = """
        MATCH (c:Company)
        RETURN c.sector AS sector, count(c) AS count
        ORDER BY count DESC
        LIMIT 10
        """
        sector_results = neo4j_client.execute_read(sector_query)
        print(f"\n   [SECTOR] 산업별 분포 (Top 10):")
        for r in sector_results:
            sector = r['sector'] or '미분류'
            print(f"      - {sector}: {r['count']}개")

        # Status별 분포
        status_query = """
        MATCH (c:Company)
        RETURN c.status AS status, count(c) AS count
        ORDER BY count DESC
        """
        status_results = neo4j_client.execute_read(status_query)
        print(f"\n   [STATUS] Status별 분포:")
        for r in status_results:
            status = r['status'] or 'UNKNOWN'
            emoji = {"PASS": "(G)", "WARNING": "(Y)", "FAIL": "(R)"}.get(status, "(?)")
            print(f"      {emoji} {status}: {r['count']}개")

        neo4j_client.close()
        return True

    except Exception as e:
        print(f"   [ERR] 통계 조회 실패: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Supply Chain 데이터 확장 도구"
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="자동 탐색 실행 (산업 매핑 + DART + 뉴스)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="현재 데이터 통계만 표시"
    )
    parser.add_argument(
        "--skip-sample",
        action="store_true",
        help="샘플 데이터 로드 건너뛰기"
    )

    args = parser.parse_args()

    print_banner()

    # Neo4j 연결 확인
    print("[CONN] Neo4j 연결 확인...")
    if not check_neo4j_connection():
        print("[ERR] Neo4j에 연결할 수 없습니다.")
        print("   환경 변수를 확인하세요: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD")
        sys.exit(1)
    print("   [OK] Neo4j 연결 성공")

    # 통계만 표시
    if args.stats:
        show_statistics()
        return

    # 샘플 데이터 로드
    if not args.skip_sample:
        load_sample_data()

    # Discovery 실행
    if args.discover:
        run_discovery()

    # 최종 통계
    show_statistics()

    print("\n" + "=" * 60)
    print("[OK] 데이터 확장 완료!")
    print("=" * 60)
    print(f"\n[TIP] API 서버 시작: uvicorn risk_engine.api:app --reload")
    print(f"[STAT] 통계 확인: GET /api/v3/supply-chain/statistics")
    print(f"[2] 추가 탐색: POST /api/v3/supply-chain/discover")


if __name__ == "__main__":
    main()
