"""
샘플 데이터 로드 스크립트
Neo4j에 테스트용 기업/공급망/리스크 데이터 생성
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


def create_companies():
    """샘플 기업 생성"""
    companies = [
        {"id": "deal_001", "name": "SK하이닉스", "sector": "반도체", "stock_code": "000660", "score": 72},
        {"id": "deal_002", "name": "삼성전자", "sector": "반도체", "stock_code": "005930", "score": 45},
        {"id": "deal_003", "name": "현대자동차", "sector": "자동차", "stock_code": "005380", "score": 38},
        {"id": "deal_004", "name": "LG에너지솔루션", "sector": "2차전지", "stock_code": "373220", "score": 55},
        {"id": "deal_005", "name": "포스코홀딩스", "sector": "철강", "stock_code": "005490", "score": 42},
        {"id": "deal_006", "name": "한미반도체", "sector": "반도체장비", "stock_code": "042700", "score": 68},
        {"id": "deal_007", "name": "네이버", "sector": "IT서비스", "stock_code": "035420", "score": 35},
        {"id": "deal_008", "name": "카카오", "sector": "IT서비스", "stock_code": "035720", "score": 48},
        {"id": "deal_009", "name": "셀트리온", "sector": "바이오", "stock_code": "068270", "score": 52},
        {"id": "deal_010", "name": "HMM", "sector": "해운", "stock_code": "011200", "score": 61},
    ]

    print(f"기업 {len(companies)}개 생성 중...")
    with neo4j_client.session() as session:
        for c in companies:
            session.run("""
                CREATE (c:Company {
                    id: $id,
                    name: $name,
                    sector: $sector,
                    stockCode: $stock_code,
                    totalRiskScore: $score,
                    riskLevel: CASE
                        WHEN $score >= 70 THEN 'CRITICAL'
                        WHEN $score >= 50 THEN 'WARNING'
                        WHEN $score >= 30 THEN 'WATCH'
                        ELSE 'NORMAL'
                    END,
                    createdAt: datetime()
                })
            """, **c)
    print("✅ 기업 노드 생성 완료")


def create_supply_chain():
    """공급망 관계 생성"""
    relationships = [
        # SK하이닉스 공급망
        ("deal_001", "deal_006", "SUPPLIED_BY", 1),  # 한미반도체 → SK하이닉스
        ("deal_001", "deal_002", "COMPETES_WITH", 0),  # 삼성전자와 경쟁

        # 삼성전자 공급망
        ("deal_002", "deal_006", "SUPPLIED_BY", 1),  # 한미반도체 → 삼성전자
        ("deal_002", "deal_004", "SUPPLIED_BY", 1),  # LG에너지솔루션 → 삼성전자

        # 현대자동차 공급망
        ("deal_003", "deal_004", "SUPPLIED_BY", 1),  # LG에너지솔루션 → 현대차
        ("deal_003", "deal_005", "SUPPLIED_BY", 2),  # 포스코 → 현대차 (Tier 2)

        # LG에너지솔루션 공급망
        ("deal_004", "deal_005", "SUPPLIED_BY", 1),  # 포스코 → LG에너지

        # HMM 물류
        ("deal_001", "deal_010", "LOGISTICS_BY", 1),  # HMM → SK하이닉스
        ("deal_002", "deal_010", "LOGISTICS_BY", 1),  # HMM → 삼성전자

        # IT 서비스 연결
        ("deal_007", "deal_008", "COMPETES_WITH", 0),  # 네이버 vs 카카오
    ]

    print(f"공급망 관계 {len(relationships)}개 생성 중...")
    with neo4j_client.session() as session:
        for source, target, rel_type, tier in relationships:
            session.run(f"""
                MATCH (a:Company {{id: $source}})
                MATCH (b:Company {{id: $target}})
                CREATE (a)-[:{rel_type} {{tier: $tier, weight: $weight}}]->(b)
            """, source=source, target=target, tier=tier, weight=random.uniform(0.5, 1.0))
    print("✅ 공급망 관계 생성 완료")


def create_risk_scores():
    """카테고리별 리스크 점수 생성"""
    categories = ["시장위험", "신용위험", "운영위험", "법률위험", "공급망위험", "ESG위험"]

    print("카테고리별 리스크 점수 생성 중...")
    with neo4j_client.session() as session:
        # 모든 기업 조회
        result = session.run("MATCH (c:Company) RETURN c.id as id")
        company_ids = [r["id"] for r in result]

        for company_id in company_ids:
            for cat in categories:
                score = random.randint(20, 85)
                trend = random.choice(["up", "down", "stable"])
                session.run("""
                    MATCH (c:Company {id: $company_id})
                    CREATE (r:RiskCategory {
                        category: $category,
                        score: $score,
                        trend: $trend,
                        updatedAt: datetime()
                    })
                    CREATE (c)-[:HAS_RISK]->(r)
                """, company_id=company_id, category=cat, score=score, trend=trend)
    print("✅ 리스크 점수 생성 완료")


def create_risk_history():
    """리스크 점수 이력 생성 (30일)"""
    print("30일 리스크 이력 생성 중...")
    with neo4j_client.session() as session:
        result = session.run("MATCH (c:Company) RETURN c.id as id, c.totalRiskScore as score")
        companies = [(r["id"], r["score"]) for r in result]

        for company_id, current_score in companies:
            # 30일 이력 생성 (랜덤 워크)
            score = current_score
            for days_ago in range(30, 0, -1):
                date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                score = max(0, min(100, score + random.randint(-5, 5)))
                session.run("""
                    MATCH (c:Company {id: $company_id})
                    CREATE (h:RiskHistory {
                        date: $date,
                        score: $score
                    })
                    CREATE (c)-[:HISTORY]->(h)
                """, company_id=company_id, date=date, score=score)
    print("✅ 리스크 이력 생성 완료")


def create_news_and_disclosures():
    """뉴스/공시 데이터 생성"""
    news_items = [
        {"company": "deal_001", "title": "SK하이닉스, 美 특허 소송 패소", "sentiment": -0.7, "category": "법률위험"},
        {"company": "deal_001", "title": "HBM 주문 급증으로 실적 개선 기대", "sentiment": 0.6, "category": "시장위험"},
        {"company": "deal_006", "title": "한미반도체, 신규 장비 수주 지연", "sentiment": -0.5, "category": "운영위험"},
        {"company": "deal_003", "title": "현대차, 전기차 판매 역대 최고", "sentiment": 0.8, "category": "시장위험"},
        {"company": "deal_010", "title": "HMM, 부산항 파업 영향 우려", "sentiment": -0.6, "category": "운영위험"},
        {"company": "deal_004", "title": "LG에너지, 美 공장 가동 시작", "sentiment": 0.5, "category": "운영위험"},
        {"company": "deal_002", "title": "삼성전자, 메모리 감산 결정", "sentiment": -0.3, "category": "시장위험"},
        {"company": "deal_009", "title": "셀트리온, FDA 승인 획득", "sentiment": 0.9, "category": "법률위험"},
    ]

    print(f"뉴스/공시 {len(news_items)}개 생성 중...")
    with neo4j_client.session() as session:
        for i, news in enumerate(news_items):
            days_ago = random.randint(0, 14)
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            session.run("""
                MATCH (c:Company {id: $company})
                CREATE (n:News {
                    id: $news_id,
                    title: $title,
                    sentiment: $sentiment,
                    category: $category,
                    date: $date,
                    source: '매일경제'
                })
                CREATE (c)-[:MENTIONED_IN]->(n)
            """, company=news["company"], news_id=f"news_{i+1:03d}",
                title=news["title"], sentiment=news["sentiment"],
                category=news["category"], date=date)
    print("✅ 뉴스/공시 생성 완료")


def create_scenarios():
    """시뮬레이션 시나리오 저장"""
    scenarios = [
        {
            "id": "busan_port",
            "name": "부산항 파업",
            "sectors": ["해운", "물류"],
            "severity": "high",
            "multiplier": 2.0
        },
        {
            "id": "memory_crash",
            "name": "메모리 가격 폭락",
            "sectors": ["반도체", "반도체장비"],
            "severity": "high",
            "multiplier": 1.8
        },
        {
            "id": "ev_demand_surge",
            "name": "전기차 수요 급증",
            "sectors": ["자동차", "2차전지"],
            "severity": "medium",
            "multiplier": 1.5
        },
    ]

    print(f"시나리오 {len(scenarios)}개 생성 중...")
    with neo4j_client.session() as session:
        for s in scenarios:
            session.run("""
                CREATE (s:Scenario {
                    id: $id,
                    name: $name,
                    affectedSectors: $sectors,
                    severity: $severity,
                    propagationMultiplier: $multiplier,
                    isPreset: true
                })
            """, id=s["id"], name=s["name"], sectors=s["sectors"],
                severity=s["severity"], multiplier=s["multiplier"])
    print("✅ 시나리오 생성 완료")


def verify_data():
    """데이터 확인"""
    print("\n=== 데이터 확인 ===")
    with neo4j_client.session() as session:
        # 노드 카운트
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)
        for r in result:
            print(f"  {r['label']}: {r['count']}개")

        # 관계 카운트
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        print("\n  관계:")
        for r in result:
            print(f"    {r['type']}: {r['count']}개")


def main():
    print("=" * 50)
    print("Neo4j 샘플 데이터 로드")
    print("=" * 50)

    try:
        neo4j_client.connect()

        clear_database()
        create_companies()
        create_supply_chain()
        create_risk_scores()
        create_risk_history()
        create_news_and_disclosures()
        create_scenarios()
        verify_data()

        print("\n✅ 샘플 데이터 로드 완료!")
        print("\n다음 단계:")
        print("1. .env.local에 VITE_USE_MOCK=false 추가")
        print("2. npm run dev 재시작")
        print("3. Backend API 실행: cd risk_engine && uvicorn api:app --reload")

    except Exception as e:
        print(f"❌ 오류: {e}")
        raise
    finally:
        neo4j_client.close()


if __name__ == "__main__":
    main()
