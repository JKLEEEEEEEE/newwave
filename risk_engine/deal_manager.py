"""
============================================================================
Deal Manager CLI - 딜 대상 수기 관리 도구
============================================================================
시연 및 테스트를 위한 딜 관리 CLI

Usage:
    python -m risk_engine.deal_manager --list                      # 딜 목록 조회
    python -m risk_engine.deal_manager --add "기업명" "섹터"       # 딜 추가
    python -m risk_engine.deal_manager --add "기업명" "섹터" --score 60 --corp-code 00126380
    python -m risk_engine.deal_manager --remove "기업명"           # 딜 삭제
    python -m risk_engine.deal_manager --update "기업명" --score 75 # 점수 업데이트
"""

import argparse
import sys
import os
from datetime import datetime

# 환경 변수 로드
from dotenv import load_dotenv
import pathlib
project_root = pathlib.Path(__file__).parent.parent
load_dotenv(project_root / ".env.local")


def get_neo4j_client():
    """Neo4j 클라이언트 로드"""
    try:
        from .neo4j_client import Neo4jClient
        return Neo4jClient()
    except Exception as e:
        print(f"[ERR] Neo4j 연결 실패: {e}")
        sys.exit(1)


def list_deals(client):
    """딜 목록 조회"""
    query = """
    MATCH (d:Deal)-[:TARGET]->(dt:DealTarget)
    RETURN d.id AS dealId, dt.name AS name, dt.sector AS sector,
           dt.totalRiskScore AS score, dt.riskLevel AS status
    ORDER BY dt.totalRiskScore DESC
    """
    results = client.execute_read(query)

    if not results:
        print("\n[INFO] 등록된 딜이 없습니다.\n")
        return

    print("\n" + "=" * 70)
    print("  RISK MONITORING - 딜 대상 목록")
    print("=" * 70)
    print(f"  {'No.':<4} {'기업명':<20} {'섹터':<12} {'점수':<8} {'상태':<10}")
    print("-" * 70)

    for idx, r in enumerate(results, 1):
        name = r.get('name', 'N/A')
        sector = r.get('sector', 'N/A')
        score = r.get('score', 0) or 0
        status = r.get('status', 'N/A')

        # 상태별 색상 (ANSI)
        status_display = status
        if status == 'PASS':
            status_display = f"\033[92m{status}\033[0m"  # Green
        elif status == 'WARNING':
            status_display = f"\033[93m{status}\033[0m"  # Yellow
        elif status == 'FAIL':
            status_display = f"\033[91m{status}\033[0m"  # Red

        print(f"  {idx:<4} {name:<20} {sector:<12} {score:<8} {status_display:<10}")

    print("=" * 70)
    print(f"  Total: {len(results)} deals\n")


def add_deal(client, name: str, sector: str, score: int = 50, corp_code: str = ""):
    """딜 추가"""
    print(f"\n[ADD] 딜 추가 중: {name} ({sector})")

    # 1. Company 노드 생성/갱신
    company_query = """
    MERGE (c:Company {id: $name})
    SET c.name = $name,
        c.sector = $sector,
        c.corpCode = $corpCode,
        c.totalRiskScore = $score,
        c.directScore = $score,
        c.propagatedScore = 0,
        c.riskLevel = CASE
            WHEN $score < 50 THEN 'PASS'
            WHEN $score < 75 THEN 'WARNING'
            ELSE 'FAIL'
        END,
        c.createdAt = datetime(),
        c.updatedAt = datetime()
    RETURN c.id AS id
    """
    client.execute_write(company_query, {
        "name": name,
        "sector": sector,
        "corpCode": corp_code,
        "score": score,
    })

    # 2. Deal -> DealTarget 생성
    deal_id = f"deal_{name.replace(' ', '_').lower()}"
    deal_query = """
    MERGE (d:Deal {id: $dealId})
    SET d.name = $dealName,
        d.type = 'EQUITY',
        d.createdAt = datetime()
    WITH d
    MATCH (c:Company {id: $companyName})
    MERGE (dt:DealTarget {id: $companyName})
    SET dt.name = c.name,
        dt.sector = c.sector,
        dt.totalRiskScore = c.totalRiskScore,
        dt.riskLevel = c.riskLevel
    MERGE (d)-[:TARGET]->(dt)
    RETURN d.id AS dealId
    """
    client.execute_write(deal_query, {
        "dealId": deal_id,
        "dealName": f"Deal - {name}",
        "companyName": name,
    })

    status = 'PASS' if score < 50 else 'WARNING' if score < 75 else 'FAIL'
    print(f"[OK] 딜 추가 완료!")
    print(f"     - 기업명: {name}")
    print(f"     - 섹터: {sector}")
    print(f"     - 초기 점수: {score}")
    print(f"     - 상태: {status}")
    if corp_code:
        print(f"     - DART 코드: {corp_code}")
    print()


def remove_deal(client, name: str):
    """딜 삭제"""
    print(f"\n[DEL] 딜 삭제 중: {name}")

    # DealTarget과 Deal 관계/노드 삭제 (Company는 유지)
    delete_query = """
    MATCH (d:Deal)-[r:TARGET]->(dt:DealTarget)
    WHERE dt.name = $name OR dt.id = $name
    DELETE r
    WITH dt, d
    DELETE dt
    WITH d
    DELETE d
    RETURN count(*) AS deleted
    """
    result = client.execute_write(delete_query, {"name": name})

    print(f"[OK] 딜 '{name}' 삭제 완료\n")


def update_deal(client, name: str, score: int = None, sector: str = None):
    """딜 점수/정보 업데이트"""
    print(f"\n[UPD] 딜 업데이트 중: {name}")

    updates = []
    params = {"name": name}

    if score is not None:
        updates.append("c.totalRiskScore = $score")
        updates.append("c.directScore = $score")
        updates.append("""c.riskLevel = CASE
            WHEN $score < 50 THEN 'PASS'
            WHEN $score < 75 THEN 'WARNING'
            ELSE 'FAIL'
        END""")
        updates.append("dt.totalRiskScore = $score")
        updates.append("""dt.riskLevel = CASE
            WHEN $score < 50 THEN 'PASS'
            WHEN $score < 75 THEN 'WARNING'
            ELSE 'FAIL'
        END""")
        params["score"] = score

    if sector is not None:
        updates.append("c.sector = $sector")
        updates.append("dt.sector = $sector")
        params["sector"] = sector

    if not updates:
        print("[WARN] 업데이트할 항목이 없습니다.\n")
        return

    update_query = f"""
    MATCH (c:Company {{id: $name}})
    OPTIONAL MATCH (dt:DealTarget {{id: $name}})
    SET {', '.join(updates)}, c.updatedAt = datetime()
    RETURN c.name AS name, c.totalRiskScore AS score, c.riskLevel AS status
    """
    result = client.execute_write(update_query, params)

    if result:
        r = result[0]
        print(f"[OK] 업데이트 완료!")
        print(f"     - 기업명: {r.get('name')}")
        if score is not None:
            print(f"     - 새 점수: {r.get('score')}")
            print(f"     - 새 상태: {r.get('status')}")
        if sector is not None:
            print(f"     - 새 섹터: {sector}")
    else:
        print(f"[WARN] '{name}' 딜을 찾을 수 없습니다.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Risk Monitoring - 딜 대상 관리 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m risk_engine.deal_manager --list
  python -m risk_engine.deal_manager --add "카카오" "IT" --score 55
  python -m risk_engine.deal_manager --add "삼성SDI" "배터리" --score 48 --corp-code 00126362
  python -m risk_engine.deal_manager --remove "카카오"
  python -m risk_engine.deal_manager --update "SK하이닉스" --score 70
        """
    )

    parser.add_argument("--list", "-l", action="store_true", help="딜 목록 조회")
    parser.add_argument("--add", "-a", nargs=2, metavar=("NAME", "SECTOR"), help="딜 추가")
    parser.add_argument("--remove", "-r", metavar="NAME", help="딜 삭제")
    parser.add_argument("--update", "-u", metavar="NAME", help="딜 업데이트")
    parser.add_argument("--score", "-s", type=int, help="리스크 점수 (0-100)")
    parser.add_argument("--corp-code", "-c", default="", help="DART 기업코드")

    args = parser.parse_args()

    # 인자가 없으면 도움말 출력
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    client = get_neo4j_client()

    try:
        if args.list:
            list_deals(client)

        elif args.add:
            name, sector = args.add
            add_deal(client, name, sector, args.score or 50, args.corp_code)

        elif args.remove:
            remove_deal(client, args.remove)

        elif args.update:
            if args.score is None:
                print("[ERR] --update 시 --score 필수")
                sys.exit(1)
            update_deal(client, args.update, args.score)

    finally:
        client.close()


if __name__ == "__main__":
    main()
