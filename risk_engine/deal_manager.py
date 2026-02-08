"""
DealService - 딜 관리 서비스 (5-Node 스키마)
==============================================
API에서 호출 가능한 딜 생성/삭제/수집 서비스

Usage (from API):
    from risk_engine.deal_manager import DealService
    service = DealService(neo4j_client)
    result = service.create_deal("카카오", "IT/플랫폼", "김철수")

CLI Usage (backward compat):
    python -m risk_engine.deal_manager --list
    python -m risk_engine.deal_manager --add "기업명" "섹터"
    python -m risk_engine.deal_manager --remove "DEAL_기업명"
"""

import argparse
import io
import logging
import os
import sys
import zipfile
from datetime import datetime
from typing import Optional
from xml.etree import ElementTree

import requests

logger = logging.getLogger(__name__)

# ============================================================
# 10개 카테고리 (LOCKED)
# ============================================================
CATEGORIES = [
    {"code": "SHARE", "name": "주주", "icon": "\U0001f4ca", "weight": 0.15},
    {"code": "EXEC",  "name": "임원", "icon": "\U0001f454", "weight": 0.15},
    {"code": "CREDIT","name": "신용", "icon": "\U0001f4b3", "weight": 0.15},
    {"code": "LEGAL", "name": "법률", "icon": "\u2696\ufe0f",  "weight": 0.12},
    {"code": "GOV",   "name": "지배구조", "icon": "\U0001f3db\ufe0f", "weight": 0.10},
    {"code": "OPS",   "name": "운영", "icon": "\u2699\ufe0f",  "weight": 0.10},
    {"code": "AUDIT", "name": "감사", "icon": "\U0001f4cb", "weight": 0.08},
    {"code": "ESG",   "name": "ESG",  "icon": "\U0001f331", "weight": 0.08},
    {"code": "SUPPLY","name": "공급망", "icon": "\U0001f517", "weight": 0.05},
    {"code": "OTHER", "name": "기타", "icon": "\U0001f4ce", "weight": 0.02},
]


class DealService:
    """딜 관리 서비스 (5-Node 스키마: Deal → Company → RiskCategory → RiskEntity → RiskEvent)"""

    def __init__(self, client):
        """
        Args:
            client: Neo4jClient instance (risk_engine.neo4j_client.Neo4jClient)
        """
        self.client = client

    # ================================================================
    # 1. create_deal
    # ================================================================
    def create_deal(
        self,
        company_name: str,
        sector: str,
        analyst: str = "",
        ticker: str = "",
        market: str = "",
    ) -> dict:
        """딜 생성 (Company + 10 Categories + Deal + TARGET)

        Returns:
            dict with dealId, companyName, categoriesCreated, etc.
        """
        # 1) Company 노드 (MERGE by name)
        self.client.execute_write("""
            MERGE (c:Company {name: $name})
            SET c.sector = $sector,
                c.ticker = $ticker,
                c.market = $market,
                c.isMain = true,
                c.directScore = 0,
                c.propagatedScore = 0,
                c.totalRiskScore = 0,
                c.riskLevel = 'PASS',
                c.createdAt = CASE WHEN c.createdAt IS NULL THEN datetime() ELSE c.createdAt END,
                c.updatedAt = datetime()
        """, {
            "name": company_name,
            "sector": sector,
            "ticker": ticker,
            "market": market,
        })

        # 2) 10개 RiskCategory 노드 (MERGE)
        for cat in CATEGORIES:
            cat_id = f"RC_{company_name}_{cat['code']}"
            self.client.execute_write("""
                MATCH (c:Company {name: $companyName})
                MERGE (rc:RiskCategory {id: $catId})
                SET rc.companyId = $companyName,
                    rc.code = $code,
                    rc.name = $catName,
                    rc.icon = $icon,
                    rc.weight = $weight,
                    rc.score = 0,
                    rc.weightedScore = 0,
                    rc.entityCount = 0,
                    rc.eventCount = 0,
                    rc.trend = 'STABLE',
                    rc.createdAt = CASE WHEN rc.createdAt IS NULL THEN datetime() ELSE rc.createdAt END
                MERGE (c)-[:HAS_CATEGORY]->(rc)
            """, {
                "companyName": company_name,
                "catId": cat_id,
                "code": cat["code"],
                "catName": cat["name"],
                "icon": cat["icon"],
                "weight": cat["weight"],
            })

        # 3) Deal 노드 + TARGET 관계
        deal_id = f"DEAL_{company_name}"
        self.client.execute_write("""
            MATCH (c:Company {name: $companyName})
            MERGE (d:Deal {id: $dealId})
            SET d.name = $dealName,
                d.analyst = $analyst,
                d.status = 'ACTIVE',
                d.registeredAt = CASE WHEN d.registeredAt IS NULL THEN datetime() ELSE d.registeredAt END,
                d.updatedAt = datetime()
            MERGE (d)-[:TARGET]->(c)
        """, {
            "companyName": company_name,
            "dealId": deal_id,
            "dealName": f"{company_name} 검토",
            "analyst": analyst,
        })

        logger.info(f"Deal created: {deal_id} -> {company_name}")

        return {
            "dealId": deal_id,
            "companyName": company_name,
            "sector": sector,
            "ticker": ticker,
            "market": market,
            "analyst": analyst,
            "categoriesCreated": len(CATEGORIES),
        }

    # ================================================================
    # 2. lookup_corp_code
    # ================================================================
    def lookup_corp_code(self, company_name: str) -> Optional[str]:
        """DART API corpCode.xml에서 기업코드(8자리) 탐색

        Returns:
            corpCode (str) or None
        """
        dart_api_key = os.getenv("OPENDART_API_KEY")
        if not dart_api_key:
            logger.warning("OPENDART_API_KEY not set, skipping corpCode lookup")
            return None

        url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={dart_api_key}"

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()

            # ZIP 해제 -> CORPCODE.xml 파싱
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                xml_name = zf.namelist()[0]  # 보통 CORPCODE.xml
                with zf.open(xml_name) as f:
                    tree = ElementTree.parse(f)

            root = tree.getroot()
            for item in root.iter("list"):
                corp_name_el = item.find("corp_name")
                corp_code_el = item.find("corp_code")
                if corp_name_el is not None and corp_code_el is not None:
                    if corp_name_el.text and corp_name_el.text.strip() == company_name:
                        corp_code = corp_code_el.text.strip()
                        # Neo4j 업데이트
                        self.client.execute_write("""
                            MATCH (c:Company {name: $name})
                            SET c.corpCode = $corpCode
                        """, {"name": company_name, "corpCode": corp_code})
                        logger.info(f"corpCode found: {company_name} -> {corp_code}")
                        return corp_code

            logger.info(f"corpCode not found for: {company_name}")
            return None

        except Exception as e:
            logger.error(f"corpCode lookup failed: {e}")
            return None

    # ================================================================
    # 3. discover_related_companies
    # ================================================================
    def discover_related_companies(self, company_name: str) -> list:
        """DART 타법인출자현황 API로 관련기업 탐색 + 생성

        Returns:
            list of {name, corpCode, relation, tier}
        """
        dart_api_key = os.getenv("OPENDART_API_KEY")
        if not dart_api_key:
            logger.warning("OPENDART_API_KEY not set, skipping related companies")
            return []

        # corpCode 조회
        result = self.client.execute_read_single("""
            MATCH (c:Company {name: $name})
            RETURN c.corpCode AS corpCode
        """, {"name": company_name})

        if not result or not result.get("corpCode"):
            logger.warning(f"No corpCode for {company_name}, cannot discover related")
            return []

        corp_code = result["corpCode"]
        current_year = datetime.now().year

        url = "https://opendart.fss.or.kr/api/otrCprInvstmntSttus.json"

        # 최신 연도부터 시도 (사업보고서가 아직 없을 수 있으므로)
        data = None
        for year in range(current_year - 1, current_year - 4, -1):
            params = {
                "crtfc_key": dart_api_key,
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": "11011",  # 사업보고서
            }
            try:
                resp = requests.get(url, params=params, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "000":
                    logger.info(f"DART related API hit: year={year}, {len(data.get('list', []))} items")
                    break
            except Exception:
                continue
            data = None

        related = []
        try:
            if not data or data.get("status") != "000":
                logger.info(f"DART related API: no data for {company_name}")
                return []

            # 한국어 기업만 필터 + 최대 10개
            import re
            items = data.get("list", [])
            # 줄바꿈 제거 + 비기업 행("합계", "소계") 필터
            SKIP_NAMES = {"합계", "소계", "계", "총계", "합 계"}
            korean_items = [
                item for item in items
                if re.search(r'[가-힣]', item.get("inv_prm", ""))
                and re.sub(r'\s+', '', item.get("inv_prm", "")).strip() != company_name
                and re.sub(r'\s+', '', item.get("inv_prm", "")).strip() not in SKIP_NAMES
            ][:7]

            for item in korean_items:
                rel_name = re.sub(r'\s+', '', (item.get("inv_prm") or "")).strip()
                if not rel_name:
                    continue

                # Company + 10 Categories 생성
                self._create_company_with_categories(rel_name, sector="")

                # HAS_RELATED 관계
                self.client.execute_write("""
                    MATCH (m:Company {name: $mainName}), (r:Company {name: $relName})
                    MERGE (m)-[rel:HAS_RELATED]->(r)
                    SET rel.relation = '계열사', rel.tier = 1
                """, {"mainName": company_name, "relName": rel_name})

                # corpCode 조회 시도
                rel_corp_code = self.lookup_corp_code(rel_name)

                related.append({
                    "name": rel_name,
                    "corpCode": rel_corp_code or "",
                    "relation": "계열사",
                    "tier": 1,
                })
                logger.info(f"Related company created: {company_name} -> {rel_name}")

        except Exception as e:
            logger.error(f"discover_related_companies failed: {e}")

        return related

    def _create_company_with_categories(self, company_name: str, sector: str = ""):
        """헬퍼: Company + 10 RiskCategory 생성 (MERGE)"""
        self.client.execute_write("""
            MERGE (c:Company {name: $name})
            SET c.sector = $sector,
                c.isMain = false,
                c.directScore = 0,
                c.propagatedScore = 0,
                c.totalRiskScore = 0,
                c.riskLevel = 'PASS',
                c.createdAt = CASE WHEN c.createdAt IS NULL THEN datetime() ELSE c.createdAt END,
                c.updatedAt = datetime()
        """, {"name": company_name, "sector": sector})

        for cat in CATEGORIES:
            cat_id = f"RC_{company_name}_{cat['code']}"
            self.client.execute_write("""
                MATCH (c:Company {name: $companyName})
                MERGE (rc:RiskCategory {id: $catId})
                SET rc.companyId = $companyName,
                    rc.code = $code,
                    rc.name = $catName,
                    rc.icon = $icon,
                    rc.weight = $weight,
                    rc.score = 0,
                    rc.weightedScore = 0,
                    rc.entityCount = 0,
                    rc.eventCount = 0,
                    rc.trend = 'STABLE',
                    rc.createdAt = CASE WHEN rc.createdAt IS NULL THEN datetime() ELSE rc.createdAt END
                MERGE (c)-[:HAS_CATEGORY]->(rc)
            """, {
                "companyName": company_name,
                "catId": cat_id,
                "code": cat["code"],
                "catName": cat["name"],
                "icon": cat["icon"],
                "weight": cat["weight"],
            })

    # ================================================================
    # 4. trigger_collection
    # ================================================================
    def trigger_collection(self, deal_id: str) -> dict:
        """수집 파이프라인 실행 (collect_for_deal 로직 호출)

        Returns:
            dict with collection results summary
        """
        try:
            # scripts/collect_for_deal.py 의 핵심 함수들 임포트
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from scripts.collect_for_deal import (
                get_deal_companies,
                collect_dart_for_company,
                collect_news_for_company,
                update_scores,
            )

            # deal_id에서 기업명 추출 (DEAL_카카오 -> 카카오)
            company_filter = deal_id.replace("DEAL_", "")

            companies = get_deal_companies(self.client, company_filter)
            if not companies:
                return {"status": "error", "message": "No companies found for deal"}

            # 중복 제거
            seen = set()
            unique = []
            for c in companies:
                if c["name"] not in seen:
                    seen.add(c["name"])
                    unique.append(c)

            total_dart = 0
            total_news = 0

            # DART 수집
            dart_api_key = os.getenv("OPENDART_API_KEY")
            if dart_api_key:
                from risk_engine.dart_collector_v2 import DartCollectorV2
                dart_collector = DartCollectorV2(dart_api_key, self.client)

                for comp in unique:
                    if comp.get("corpCode"):
                        stats = collect_dart_for_company(dart_collector, comp["name"], comp["corpCode"])
                        total_dart += sum(stats.values())

            # 뉴스 수집
            try:
                from risk_engine.news_collector_v2 import NewsCollectorV2
                news_collector = NewsCollectorV2(self.client)

                for comp in unique:
                    saved = collect_news_for_company(news_collector, comp["name"])
                    total_news += saved
            except Exception as e:
                logger.error(f"News collection error: {e}")

            # 점수 재계산
            all_names = [c["name"] for c in unique]
            update_scores(self.client, all_names)

            return {
                "status": "completed",
                "dealId": deal_id,
                "companiesProcessed": len(unique),
                "dartItemsCollected": total_dart,
                "newsItemsCollected": total_news,
            }

        except Exception as e:
            logger.error(f"trigger_collection failed: {e}")
            return {"status": "error", "message": str(e)}

    # ================================================================
    # 5. delete_deal
    # ================================================================
    def delete_deal(self, deal_id: str) -> dict:
        """딜 삭제 (Deal 노드 + TARGET 관계만. Company와 하위 노드는 유지)

        Returns:
            dict with success/failure
        """
        result = self.client.execute_write("""
            MATCH (d:Deal {id: $dealId})
            OPTIONAL MATCH (d)-[r:TARGET]->()
            DELETE r, d
        """, {"dealId": deal_id})

        logger.info(f"Deal deleted: {deal_id}")
        return {"deleted": deal_id, "details": result}

    # ================================================================
    # 6. list_deals
    # ================================================================
    def list_deals(self) -> list:
        """딜 목록 조회

        Returns:
            list of {dealId, companyName, sector, score, riskLevel}
        """
        query = """
        MATCH (d:Deal)-[:TARGET]->(c:Company)
        RETURN d.id AS dealId, c.name AS companyName, c.sector AS sector,
               c.totalRiskScore AS score, c.riskLevel AS riskLevel
        ORDER BY c.totalRiskScore DESC
        """
        results = self.client.execute_read(query, {})
        return [
            {
                "dealId": r.get("dealId", ""),
                "companyName": r.get("companyName", ""),
                "sector": r.get("sector", ""),
                "score": r.get("score", 0) or 0,
                "riskLevel": r.get("riskLevel", "PASS") or "PASS",
            }
            for r in (results or [])
        ]


# ================================================================
# CLI (backward compat)
# ================================================================

def _get_neo4j_client():
    """CLI 전용: Neo4j 클라이언트 로드"""
    from dotenv import load_dotenv
    import pathlib
    project_root = pathlib.Path(__file__).parent.parent
    load_dotenv(project_root / ".env.local")

    try:
        from risk_engine.neo4j_client import Neo4jClient
        client = Neo4jClient()
        client.connect()
        return client
    except Exception as e:
        print(f"[ERR] Neo4j 연결 실패: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Risk Monitoring - 딜 관리 CLI (DealService)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m risk_engine.deal_manager --list
  python -m risk_engine.deal_manager --add "카카오" "IT/플랫폼"
  python -m risk_engine.deal_manager --add "삼성전자" "반도체" --analyst "박민수"
  python -m risk_engine.deal_manager --remove "DEAL_카카오"
        """
    )

    parser.add_argument("--list", "-l", action="store_true", help="딜 목록 조회")
    parser.add_argument("--add", "-a", nargs=2, metavar=("NAME", "SECTOR"), help="딜 추가")
    parser.add_argument("--remove", "-r", metavar="DEAL_ID", help="딜 삭제 (예: DEAL_카카오)")
    parser.add_argument("--analyst", default="", help="애널리스트명")
    parser.add_argument("--ticker", default="", help="종목코드")
    parser.add_argument("--market", default="", help="시장 (KOSPI/KOSDAQ/...)")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    client = _get_neo4j_client()
    service = DealService(client)

    try:
        if args.list:
            deals = service.list_deals()
            if not deals:
                print("\n[INFO] 등록된 딜이 없습니다.\n")
                return
            print("\n" + "=" * 70)
            print("  RISK MONITORING - 딜 목록")
            print("=" * 70)
            print(f"  {'No.':<4} {'딜 ID':<20} {'기업명':<15} {'섹터':<12} {'점수':<6} {'상태':<8}")
            print("-" * 70)
            for idx, d in enumerate(deals, 1):
                print(f"  {idx:<4} {d['dealId']:<20} {d['companyName']:<15} "
                      f"{d['sector']:<12} {d['score']:<6} {d['riskLevel']:<8}")
            print("=" * 70)
            print(f"  Total: {len(deals)} deals\n")

        elif args.add:
            name, sector = args.add
            result = service.create_deal(name, sector, args.analyst, args.ticker, args.market)
            print(f"\n[OK] 딜 생성 완료!")
            print(f"     - Deal ID: {result['dealId']}")
            print(f"     - 기업명: {result['companyName']}")
            print(f"     - 섹터: {result['sector']}")
            print(f"     - 카테고리: {result['categoriesCreated']}개 생성")
            print()

        elif args.remove:
            service.delete_deal(args.remove)
            print(f"\n[OK] 딜 '{args.remove}' 삭제 완료\n")

    finally:
        client.close()


if __name__ == "__main__":
    main()
