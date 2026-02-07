"""
딜 중심(Deal-Centric) 그래프 데이터 로드
Risk Monitoring System v2.3

스키마 설계:
- Deal: 투자/대출 딜 (우리가 관리하는 대상)
- DealTarget: 딜의 핵심 기업 (모니터링 대상)
- Company: 관련 기업 (공급사, 고객사, 경쟁사)
- News: 뉴스 기사
- Disclosure: 공시 정보
- RiskEvent: 리스크 이벤트
"""

import os
import sys
import io
from datetime import datetime, timedelta
import random

# Windows 콘솔 UTF-8 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('.env.local')

from risk_engine.neo4j_client import neo4j_client


def clear_database():
    """기존 데이터 삭제"""
    print("기존 데이터 삭제 중...")
    with neo4j_client.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("✅ 데이터베이스 초기화 완료")


def create_constraints():
    """인덱스 및 제약조건 생성"""
    print("인덱스 생성 중...")
    constraints = [
        "CREATE INDEX IF NOT EXISTS FOR (d:Deal) ON (d.id)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:News) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (e:RiskEvent) ON (e.id)",
    ]
    with neo4j_client.session() as session:
        for c in constraints:
            try:
                session.run(c)
            except Exception as e:
                pass  # 이미 존재하면 무시
    print("✅ 인덱스 생성 완료")


def create_deals_and_targets():
    """딜과 딜 타겟(핵심 모니터링 대상) 생성"""

    # 딜 목록 - 우리가 투자/대출한 대상
    deals = [
        {
            "deal_id": "DEAL_001",
            "deal_name": "SK하이닉스 시설자금",
            "deal_type": "시설자금대출",
            "amount": 500000000000,  # 5000억
            "start_date": "2024-01-15",
            "maturity_date": "2029-01-15",
            "target": {
                "id": "COM_SKHYNIX",
                "name": "SK하이닉스",
                "name_en": "SK Hynix",
                "sector": "반도체",
                "stock_code": "000660",
                "market": "KOSPI",
            }
        },
        {
            "deal_id": "DEAL_002",
            "deal_name": "LG에너지솔루션 운영자금",
            "deal_type": "운영자금대출",
            "amount": 300000000000,  # 3000억
            "start_date": "2024-03-01",
            "maturity_date": "2027-03-01",
            "target": {
                "id": "COM_LGENERGY",
                "name": "LG에너지솔루션",
                "name_en": "LG Energy Solution",
                "sector": "2차전지",
                "stock_code": "373220",
                "market": "KOSPI",
            }
        },
        {
            "deal_id": "DEAL_003",
            "deal_name": "현대자동차 회사채",
            "deal_type": "회사채인수",
            "amount": 200000000000,  # 2000억
            "start_date": "2024-06-01",
            "maturity_date": "2027-06-01",
            "target": {
                "id": "COM_HYUNDAI",
                "name": "현대자동차",
                "name_en": "Hyundai Motor",
                "sector": "자동차",
                "stock_code": "005380",
                "market": "KOSPI",
            }
        },
    ]

    print(f"딜 {len(deals)}개 및 딜 타겟 생성 중...")

    with neo4j_client.session() as session:
        for d in deals:
            # Deal 노드 생성
            session.run("""
                CREATE (deal:Deal {
                    id: $deal_id,
                    name: $deal_name,
                    type: $deal_type,
                    amount: $amount,
                    startDate: $start_date,
                    maturityDate: $maturity_date,
                    status: 'ACTIVE',
                    createdAt: datetime()
                })
            """, deal_id=d["deal_id"], deal_name=d["deal_name"],
                deal_type=d["deal_type"], amount=d["amount"],
                start_date=d["start_date"], maturity_date=d["maturity_date"])

            # DealTarget (핵심 모니터링 대상) 노드 생성
            t = d["target"]
            session.run("""
                CREATE (c:Company:DealTarget {
                    id: $id,
                    name: $name,
                    nameEn: $name_en,
                    sector: $sector,
                    stockCode: $stock_code,
                    market: $market,
                    isDealTarget: true,
                    createdAt: datetime()
                })
            """, **t)

            # Deal -> DealTarget 관계
            session.run("""
                MATCH (deal:Deal {id: $deal_id})
                MATCH (target:Company {id: $target_id})
                CREATE (deal)-[:TARGET {since: $start_date}]->(target)
            """, deal_id=d["deal_id"], target_id=t["id"], start_date=d["start_date"])

    print("✅ 딜 및 딜 타겟 생성 완료")
    return deals


def create_supply_chain(deals):
    """공급망 생성 (딜 타겟 중심)"""

    # 각 딜 타겟별 공급망
    supply_chains = {
        "COM_SKHYNIX": {
            "suppliers_tier1": [
                {"id": "COM_HAMI", "name": "한미반도체", "sector": "반도체장비", "dependency": 0.25},
                {"id": "COM_ASMPT", "name": "ASM Pacific", "sector": "반도체장비", "dependency": 0.20},
                {"id": "COM_TECHWING", "name": "테크윙", "sector": "반도체장비", "dependency": 0.15},
            ],
            "suppliers_tier2": [
                {"id": "COM_SOULBRAIN", "name": "솔브레인", "sector": "반도체소재", "supplies_to": "COM_HAMI", "dependency": 0.10},
                {"id": "COM_DONGJIN", "name": "동진쎄미켐", "sector": "반도체소재", "supplies_to": "COM_HAMI", "dependency": 0.08},
            ],
            "customers": [
                {"id": "COM_APPLE", "name": "Apple", "sector": "IT", "revenue_share": 0.20},
                {"id": "COM_NVIDIA", "name": "NVIDIA", "sector": "반도체", "revenue_share": 0.15},
                {"id": "COM_AMAZON", "name": "Amazon", "sector": "IT", "revenue_share": 0.10},
            ],
            "competitors": [
                {"id": "COM_SAMSUNG", "name": "삼성전자", "sector": "반도체"},
                {"id": "COM_MICRON", "name": "Micron", "sector": "반도체"},
            ],
            "logistics": [
                {"id": "COM_HMM", "name": "HMM", "sector": "해운", "route": "미주/유럽"},
            ],
        },
        "COM_LGENERGY": {
            "suppliers_tier1": [
                {"id": "COM_POSCO", "name": "포스코홀딩스", "sector": "철강/소재", "dependency": 0.30},
                {"id": "COM_ECOPRO", "name": "에코프로비엠", "sector": "2차전지소재", "dependency": 0.25},
            ],
            "suppliers_tier2": [
                {"id": "COM_CHILE_LITHIUM", "name": "SQM (칠레)", "sector": "원자재", "supplies_to": "COM_ECOPRO", "dependency": 0.15},
            ],
            "customers": [
                {"id": "COM_TESLA", "name": "Tesla", "sector": "자동차", "revenue_share": 0.25},
                {"id": "COM_GM", "name": "General Motors", "sector": "자동차", "revenue_share": 0.20},
                {"id": "COM_HYUNDAI", "name": "현대자동차", "sector": "자동차", "revenue_share": 0.15},
            ],
            "competitors": [
                {"id": "COM_CATL", "name": "CATL", "sector": "2차전지"},
                {"id": "COM_SDI", "name": "삼성SDI", "sector": "2차전지"},
            ],
        },
        "COM_HYUNDAI": {
            "suppliers_tier1": [
                {"id": "COM_HYUNDAIMOBIS", "name": "현대모비스", "sector": "자동차부품", "dependency": 0.35},
                {"id": "COM_LGENERGY", "name": "LG에너지솔루션", "sector": "2차전지", "dependency": 0.20},
            ],
            "suppliers_tier2": [
                {"id": "COM_MANDO", "name": "만도", "sector": "자동차부품", "supplies_to": "COM_HYUNDAIMOBIS", "dependency": 0.10},
            ],
            "customers": [
                {"id": "COM_CUSTOMER_US", "name": "미국 시장", "sector": "소비자", "revenue_share": 0.30},
                {"id": "COM_CUSTOMER_EU", "name": "유럽 시장", "sector": "소비자", "revenue_share": 0.20},
            ],
            "competitors": [
                {"id": "COM_TOYOTA", "name": "Toyota", "sector": "자동차"},
                {"id": "COM_VW", "name": "Volkswagen", "sector": "자동차"},
                {"id": "COM_TESLA", "name": "Tesla", "sector": "자동차"},
            ],
        },
    }

    print("공급망 관계 생성 중...")

    with neo4j_client.session() as session:
        for target_id, chain in supply_chains.items():
            # Tier 1 공급사
            for supplier in chain.get("suppliers_tier1", []):
                # 공급사 노드 생성 (없으면)
                session.run("""
                    MERGE (c:Company {id: $id})
                    ON CREATE SET c.name = $name, c.sector = $sector, c.isDealTarget = false
                """, id=supplier["id"], name=supplier["name"], sector=supplier["sector"])

                # 공급 관계 생성
                session.run("""
                    MATCH (target:Company {id: $target_id})
                    MATCH (supplier:Company {id: $supplier_id})
                    CREATE (target)-[:SUPPLIED_BY {tier: 1, dependency: $dependency, critical: $dependency > 0.2}]->(supplier)
                """, target_id=target_id, supplier_id=supplier["id"], dependency=supplier["dependency"])

            # Tier 2 공급사
            for supplier in chain.get("suppliers_tier2", []):
                session.run("""
                    MERGE (c:Company {id: $id})
                    ON CREATE SET c.name = $name, c.sector = $sector, c.isDealTarget = false
                """, id=supplier["id"], name=supplier["name"], sector=supplier["sector"])

                # Tier 1에 공급
                session.run("""
                    MATCH (tier1:Company {id: $tier1_id})
                    MATCH (tier2:Company {id: $tier2_id})
                    CREATE (tier1)-[:SUPPLIED_BY {tier: 2, dependency: $dependency}]->(tier2)
                """, tier1_id=supplier["supplies_to"], tier2_id=supplier["id"], dependency=supplier["dependency"])

            # 고객사
            for customer in chain.get("customers", []):
                session.run("""
                    MERGE (c:Company {id: $id})
                    ON CREATE SET c.name = $name, c.sector = $sector, c.isDealTarget = false
                """, id=customer["id"], name=customer["name"], sector=customer["sector"])

                session.run("""
                    MATCH (target:Company {id: $target_id})
                    MATCH (customer:Company {id: $customer_id})
                    CREATE (target)-[:SELLS_TO {revenueShare: $revenue_share, critical: $revenue_share > 0.15}]->(customer)
                """, target_id=target_id, customer_id=customer["id"], revenue_share=customer["revenue_share"])

            # 경쟁사
            for competitor in chain.get("competitors", []):
                session.run("""
                    MERGE (c:Company {id: $id})
                    ON CREATE SET c.name = $name, c.sector = $sector, c.isDealTarget = false
                """, id=competitor["id"], name=competitor["name"], sector=competitor["sector"])

                session.run("""
                    MATCH (target:Company {id: $target_id})
                    MATCH (competitor:Company {id: $competitor_id})
                    MERGE (target)-[:COMPETES_WITH]->(competitor)
                """, target_id=target_id, competitor_id=competitor["id"])

            # 물류사
            for logistics in chain.get("logistics", []):
                session.run("""
                    MERGE (c:Company {id: $id})
                    ON CREATE SET c.name = $name, c.sector = $sector, c.isDealTarget = false
                """, id=logistics["id"], name=logistics["name"], sector=logistics["sector"])

                session.run("""
                    MATCH (target:Company {id: $target_id})
                    MATCH (logistics:Company {id: $logistics_id})
                    CREATE (target)-[:USES_LOGISTICS {route: $route}]->(logistics)
                """, target_id=target_id, logistics_id=logistics["id"], route=logistics["route"])

    print("✅ 공급망 관계 생성 완료")


def create_news_and_events():
    """뉴스 및 리스크 이벤트 생성"""

    news_items = [
        # SK하이닉스 관련
        {"target": "COM_SKHYNIX", "title": "SK하이닉스, 美 ITC 특허 소송 패소 판결", "sentiment": -0.8, "category": "법률", "impact": 15},
        {"target": "COM_SKHYNIX", "title": "HBM3E 양산 본격화...AI 수혜 기대", "sentiment": 0.7, "category": "시장", "impact": -10},
        {"target": "COM_SKHYNIX", "title": "한미반도체, 장비 납품 지연으로 라인 가동 차질", "sentiment": -0.5, "category": "공급망", "impact": 8},
        {"target": "COM_HAMI", "title": "한미반도체, 신규 장비 수주 2개월 지연", "sentiment": -0.6, "category": "운영", "impact": 5},

        # LG에너지솔루션 관련
        {"target": "COM_LGENERGY", "title": "LG에너지, 美 애리조나 공장 가동 시작", "sentiment": 0.6, "category": "운영", "impact": -5},
        {"target": "COM_LGENERGY", "title": "칠레 리튬 수출 규제 강화 우려", "sentiment": -0.7, "category": "공급망", "impact": 12},
        {"target": "COM_TESLA", "title": "Tesla, 배터리 내재화 가속...협력사 의존도 감소", "sentiment": -0.4, "category": "고객", "impact": 8},

        # 현대자동차 관련
        {"target": "COM_HYUNDAI", "title": "현대차, 전기차 판매 역대 최고 기록", "sentiment": 0.8, "category": "시장", "impact": -8},
        {"target": "COM_HYUNDAI", "title": "미국 IRA 보조금 불확실성 지속", "sentiment": -0.5, "category": "규제", "impact": 10},
    ]

    print(f"뉴스 {len(news_items)}개 생성 중...")

    with neo4j_client.session() as session:
        for i, news in enumerate(news_items):
            news_id = f"NEWS_{i+1:04d}"
            days_ago = random.randint(0, 30)
            pub_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

            # News 노드 생성
            session.run("""
                CREATE (n:News {
                    id: $news_id,
                    title: $title,
                    sentiment: $sentiment,
                    category: $category,
                    publishedAt: $pub_date,
                    source: '뉴스크롤링',
                    impact: $impact
                })
            """, news_id=news_id, title=news["title"], sentiment=news["sentiment"],
                category=news["category"], pub_date=pub_date, impact=news["impact"])

            # Company -> News 관계
            session.run("""
                MATCH (c:Company {id: $target_id})
                MATCH (n:News {id: $news_id})
                CREATE (c)-[:MENTIONED_IN {relevance: 0.9}]->(n)
            """, target_id=news["target"], news_id=news_id)

            # 부정적 뉴스는 RiskEvent로도 생성
            if news["sentiment"] < -0.3:
                event_id = f"EVENT_{i+1:04d}"
                session.run("""
                    CREATE (e:RiskEvent {
                        id: $event_id,
                        type: $category,
                        severity: $severity,
                        description: $title,
                        occurredAt: $pub_date,
                        impactScore: $impact
                    })
                """, event_id=event_id, category=news["category"],
                    severity="HIGH" if news["impact"] > 10 else "MEDIUM",
                    title=news["title"], pub_date=pub_date, impact=news["impact"])

                # Company -> RiskEvent 관계
                session.run("""
                    MATCH (c:Company {id: $target_id})
                    MATCH (e:RiskEvent {id: $event_id})
                    CREATE (c)-[:HAS_EVENT]->(e)
                """, target_id=news["target"], event_id=event_id)

    print("✅ 뉴스 및 이벤트 생성 완료")


def create_risk_scores():
    """리스크 점수 생성 (딜 타겟 기준)"""

    # 딜 타겟별 리스크 점수
    risk_data = {
        "COM_SKHYNIX": {
            "total": 72,
            "categories": {
                "시장위험": {"score": 45, "trend": "stable"},
                "신용위험": {"score": 35, "trend": "stable"},
                "운영위험": {"score": 55, "trend": "up"},
                "법률위험": {"score": 82, "trend": "up"},      # 특허 소송
                "공급망위험": {"score": 68, "trend": "up"},    # 한미반도체 이슈
                "ESG위험": {"score": 40, "trend": "stable"},
            }
        },
        "COM_LGENERGY": {
            "total": 58,
            "categories": {
                "시장위험": {"score": 50, "trend": "down"},
                "신용위험": {"score": 40, "trend": "stable"},
                "운영위험": {"score": 45, "trend": "stable"},
                "법률위험": {"score": 35, "trend": "stable"},
                "공급망위험": {"score": 75, "trend": "up"},    # 리튬 수급
                "ESG위험": {"score": 55, "trend": "up"},
            }
        },
        "COM_HYUNDAI": {
            "total": 48,
            "categories": {
                "시장위험": {"score": 40, "trend": "down"},
                "신용위험": {"score": 30, "trend": "stable"},
                "운영위험": {"score": 35, "trend": "stable"},
                "법률위험": {"score": 45, "trend": "stable"},
                "공급망위험": {"score": 55, "trend": "stable"},
                "ESG위험": {"score": 50, "trend": "stable"},
            }
        },
    }

    print("리스크 점수 생성 중...")

    with neo4j_client.session() as session:
        for company_id, data in risk_data.items():
            # 총점 업데이트
            status = "CRITICAL" if data["total"] >= 70 else "WARNING" if data["total"] >= 50 else "WATCH" if data["total"] >= 30 else "NORMAL"
            session.run("""
                MATCH (c:Company {id: $company_id})
                SET c.totalRiskScore = $total,
                    c.riskLevel = $status
            """, company_id=company_id, total=data["total"], status=status)

            # 카테고리별 점수
            for cat_name, cat_data in data["categories"].items():
                session.run("""
                    MATCH (c:Company {id: $company_id})
                    CREATE (r:RiskCategory {
                        name: $name,
                        score: $score,
                        trend: $trend,
                        updatedAt: datetime()
                    })
                    CREATE (c)-[:HAS_RISK]->(r)
                """, company_id=company_id, name=cat_name,
                    score=cat_data["score"], trend=cat_data["trend"])

    print("✅ 리스크 점수 생성 완료")


def create_risk_history():
    """리스크 점수 이력 생성 (30일)"""
    print("30일 리스크 이력 생성 중...")

    deal_targets = ["COM_SKHYNIX", "COM_LGENERGY", "COM_HYUNDAI"]
    base_scores = {"COM_SKHYNIX": 72, "COM_LGENERGY": 58, "COM_HYUNDAI": 48}

    with neo4j_client.session() as session:
        for company_id in deal_targets:
            score = base_scores[company_id]
            for days_ago in range(30, 0, -1):
                date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                # 랜덤 워크로 과거 점수 생성
                score = max(20, min(90, score + random.randint(-3, 3)))
                session.run("""
                    MATCH (c:Company {id: $company_id})
                    CREATE (h:RiskHistory {
                        date: $date,
                        score: $score
                    })
                    CREATE (c)-[:HISTORY]->(h)
                """, company_id=company_id, date=date, score=score)

    print("✅ 리스크 이력 생성 완료")


def verify_data():
    """데이터 검증"""
    print("\n" + "="*50)
    print("데이터 검증")
    print("="*50)

    with neo4j_client.session() as session:
        # 노드 통계
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY count DESC
        """)
        print("\n[노드 통계]")
        for r in result:
            print(f"  {r['label']}: {r['count']}개")

        # 관계 통계
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(r) AS count
            ORDER BY count DESC
        """)
        print("\n[관계 통계]")
        for r in result:
            print(f"  {r['type']}: {r['count']}개")

        # 딜 타겟 확인
        result = session.run("""
            MATCH (d:Deal)-[:TARGET]->(t:DealTarget)
            RETURN d.name AS deal, t.name AS target, t.totalRiskScore AS score
        """)
        print("\n[딜 -> 타겟 매핑]")
        for r in result:
            print(f"  {r['deal']} -> {r['target']} (Risk: {r['score']})")

        # SK하이닉스 중심 그래프 미리보기
        result = session.run("""
            MATCH (target:Company {id: 'COM_SKHYNIX'})
            OPTIONAL MATCH (target)-[r1:SUPPLIED_BY]->(supplier)
            OPTIONAL MATCH (target)-[r2:SELLS_TO]->(customer)
            OPTIONAL MATCH (target)-[r3:COMPETES_WITH]->(competitor)
            OPTIONAL MATCH (target)-[r4:MENTIONED_IN]->(news)
            RETURN target.name AS center,
                   count(DISTINCT supplier) AS suppliers,
                   count(DISTINCT customer) AS customers,
                   count(DISTINCT competitor) AS competitors,
                   count(DISTINCT news) AS news
        """)
        print("\n[SK하이닉스 중심 그래프]")
        for r in result:
            print(f"  중심: {r['center']}")
            print(f"  - 공급사: {r['suppliers']}개")
            print(f"  - 고객사: {r['customers']}개")
            print(f"  - 경쟁사: {r['competitors']}개")
            print(f"  - 관련뉴스: {r['news']}개")


def main():
    print("="*50)
    print("딜 중심(Deal-Centric) 그래프 데이터 로드")
    print("="*50)

    try:
        neo4j_client.connect()

        clear_database()
        create_constraints()
        deals = create_deals_and_targets()
        create_supply_chain(deals)
        create_news_and_events()
        create_risk_scores()
        create_risk_history()
        verify_data()

        print("\n" + "="*50)
        print("✅ 딜 중심 데이터 로드 완료!")
        print("="*50)
        print("\n그래프 구조:")
        print("  Deal ─[:TARGET]─> DealTarget(SK하이닉스 등)")
        print("                      │")
        print("         ┌────────────┼────────────┐")
        print("         ▼            ▼            ▼")
        print("    [:SUPPLIED_BY] [:SELLS_TO] [:COMPETES_WITH]")
        print("         │            │            │")
        print("       공급사       고객사       경쟁사")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        neo4j_client.close()


if __name__ == "__main__":
    main()
