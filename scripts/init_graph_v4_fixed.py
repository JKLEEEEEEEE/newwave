"""
Graph DB V4 초기화 스크립트 (수정)
- Deal: 투자검토 관리 테이블
- Company: 메인 + 관련기업 (동일한 구조)
- 관련기업도 RiskCategory, RiskEvent를 가짐
"""

from neo4j import GraphDatabase
from datetime import datetime, timedelta
import random
import hashlib
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

# 10개 카테고리 정의
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


def clear_database(tx):
    tx.run("MATCH (n) DETACH DELETE n")
    print("[OK] 기존 데이터 모두 삭제")


def create_indexes(tx):
    indexes = [
        "CREATE INDEX deal_id IF NOT EXISTS FOR (d:Deal) ON (d.id)",
        "CREATE INDEX company_id IF NOT EXISTS FOR (c:Company) ON (c.id)",
        "CREATE INDEX category_id IF NOT EXISTS FOR (c:RiskCategory) ON (c.id)",
        "CREATE INDEX event_id IF NOT EXISTS FOR (e:RiskEvent) ON (e.id)",
    ]
    for idx in indexes:
        try:
            tx.run(idx)
        except:
            pass
    print("[OK] 인덱스 생성")


def create_company_with_categories(tx, company_data):
    """Company 노드 생성 + 10개 RiskCategory 연결"""
    comp_id = company_data["id"]

    # Company 생성
    tx.run("""
        CREATE (c:Company {
            id: $id,
            name: $name,
            ticker: $ticker,
            sector: $sector,
            market: $market,
            isMain: $isMain,
            directScore: 0,
            propagatedScore: 0,
            totalRiskScore: 0,
            riskLevel: 'PASS',
            createdAt: datetime(),
            updatedAt: datetime()
        })
    """, company_data)

    # 10개 카테고리 생성 및 연결
    for cat in CATEGORIES:
        cat_id = f"RC_{comp_id}_{cat['code']}"
        tx.run("""
            MATCH (c:Company {id: $compId})
            CREATE (rc:RiskCategory {
                id: $catId,
                companyId: $compId,
                code: $code,
                name: $name,
                icon: $icon,
                weight: $weight,
                score: 0,
                weightedScore: 0,
                eventCount: 0,
                trend: 'STABLE',
                createdAt: datetime()
            })
            CREATE (c)-[:HAS_CATEGORY]->(rc)
        """, {
            "compId": comp_id,
            "catId": cat_id,
            "code": cat["code"],
            "name": cat["name"],
            "icon": cat["icon"],
            "weight": cat["weight"],
        })


def create_deal(tx, deal_data, main_company_id):
    """Deal 노드 생성 + 메인 Company와 TARGET 관계"""
    tx.run("""
        MATCH (c:Company {id: $mainCompanyId})
        CREATE (d:Deal {
            id: $id,
            name: $name,
            status: $status,
            analyst: $analyst,
            notes: $notes,
            registeredAt: datetime(),
            updatedAt: datetime()
        })
        CREATE (d)-[:TARGET]->(c)
    """, {
        "id": deal_data["id"],
        "name": deal_data["name"],
        "status": deal_data.get("status", "ACTIVE"),
        "analyst": deal_data.get("analyst", ""),
        "notes": deal_data.get("notes", ""),
        "mainCompanyId": main_company_id,
    })


def create_related_company_link(tx, main_company_id, related_company_id, relation, tier):
    """관련기업 연결 (HAS_RELATED)"""
    tx.run("""
        MATCH (main:Company {id: $mainId})
        MATCH (related:Company {id: $relatedId})
        CREATE (main)-[:HAS_RELATED {relation: $relation, tier: $tier}]->(related)
    """, {
        "mainId": main_company_id,
        "relatedId": related_company_id,
        "relation": relation,
        "tier": tier,
    })


def create_risk_event(tx, company_id, category_code, event_data):
    """RiskEvent 생성 및 카테고리 연결"""
    evt_id = f"EVT_{hashlib.md5((company_id + event_data['title']).encode()).hexdigest()[:8]}"
    pub_date = datetime.now() - timedelta(days=random.randint(1, 30))

    tx.run("""
        MATCH (c:Company {id: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory {code: $categoryCode})
        CREATE (e:RiskEvent {
            id: $eventId,
            title: $title,
            summary: $summary,
            type: $type,
            score: $score,
            severity: $severity,
            relatedPerson: $relatedPerson,
            sourceName: $sourceName,
            sourceUrl: $sourceUrl,
            publishedAt: $publishedAt,
            collectedAt: datetime(),
            isActive: true
        })
        CREATE (rc)-[:HAS_EVENT]->(e)
        SET rc.eventCount = rc.eventCount + 1,
            rc.score = rc.score + CASE WHEN $score > 0 THEN $score ELSE 0 END
    """, {
        "companyId": company_id,
        "categoryCode": category_code,
        "eventId": evt_id,
        "title": event_data["title"],
        "summary": event_data["summary"],
        "type": event_data["type"],
        "score": event_data["score"],
        "severity": event_data["severity"],
        "relatedPerson": event_data.get("relatedPerson", ""),
        "sourceName": event_data["sourceName"],
        "sourceUrl": event_data["sourceUrl"],
        "publishedAt": pub_date.isoformat(),
    })


def calculate_scores(tx):
    """점수 계산"""
    # 1. 카테고리 가중 점수
    tx.run("MATCH (rc:RiskCategory) SET rc.weightedScore = rc.score * rc.weight")

    # 2. Company 직접 점수
    tx.run("""
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WITH c, SUM(rc.weightedScore) AS directScore
        SET c.directScore = toInteger(directScore)
    """)

    # 3. Company 전이 점수 (관련기업 점수의 30%)
    tx.run("""
        MATCH (c:Company)-[:HAS_RELATED]->(related:Company)
        WITH c, SUM(related.directScore) * 0.3 AS propagatedScore
        SET c.propagatedScore = toInteger(propagatedScore)
    """)

    # 4. 총점 및 레벨
    tx.run("""
        MATCH (c:Company)
        SET c.totalRiskScore = c.directScore + c.propagatedScore,
            c.riskLevel = CASE
                WHEN c.directScore + c.propagatedScore >= 50 THEN 'FAIL'
                WHEN c.directScore + c.propagatedScore >= 30 THEN 'WARNING'
                ELSE 'PASS'
            END,
            c.updatedAt = datetime()
    """)

    print("[OK] 점수 계산 완료")


def print_summary(tx):
    print("\n" + "="*70)
    print("                    그래프 DB V4 초기화 완료")
    print("="*70)

    # 노드 카운트
    result = tx.run("""
        MATCH (d:Deal) RETURN 'Deal' AS label, count(d) AS count
        UNION ALL
        MATCH (c:Company) RETURN 'Company' AS label, count(c) AS count
        UNION ALL
        MATCH (rc:RiskCategory) RETURN 'RiskCategory' AS label, count(rc) AS count
        UNION ALL
        MATCH (e:RiskEvent) RETURN 'RiskEvent' AS label, count(e) AS count
    """)

    print("\n[노드 현황]")
    for r in result:
        print(f"   {r['label']}: {r['count']}개")

    # 관계 카운트
    result = tx.run("""
        MATCH ()-[r:TARGET]->() RETURN 'TARGET' AS type, count(r) AS count
        UNION ALL
        MATCH ()-[r:HAS_CATEGORY]->() RETURN 'HAS_CATEGORY' AS type, count(r) AS count
        UNION ALL
        MATCH ()-[r:HAS_RELATED]->() RETURN 'HAS_RELATED' AS type, count(r) AS count
        UNION ALL
        MATCH ()-[r:HAS_EVENT]->() RETURN 'HAS_EVENT' AS type, count(r) AS count
    """)

    print("\n[관계 현황]")
    for r in result:
        print(f"   {r['type']}: {r['count']}개")

    # 메인 기업 (Deal 대상)
    result = tx.run("""
        MATCH (d:Deal)-[:TARGET]->(c:Company)
        RETURN d.name AS deal, c.name AS company, c.directScore AS direct,
               c.propagatedScore AS propagated, c.totalRiskScore AS total, c.riskLevel AS level
        ORDER BY c.totalRiskScore DESC
    """)

    print("\n[메인 기업 (Deal 대상)]")
    print("-"*70)
    print(f"{'Deal':<12} {'Company':<15} {'직접':<8} {'전이':<8} {'총점':<8} {'레벨'}")
    print("-"*70)
    for r in result:
        print(f"{r['deal']:<12} {r['company']:<15} {r['direct']:<8} {r['propagated']:<8} {r['total']:<8} {r['level']}")

    # 관련기업
    result = tx.run("""
        MATCH (main:Company)-[r:HAS_RELATED]->(related:Company)
        RETURN main.name AS main, related.name AS related, r.relation AS relation,
               related.directScore AS direct, related.totalRiskScore AS total, related.riskLevel AS level
        ORDER BY main.name, related.totalRiskScore DESC
        LIMIT 10
    """)

    print("\n[관련기업 (상위 10개)]")
    print("-"*70)
    print(f"{'메인기업':<15} {'관련기업':<15} {'관계':<10} {'직접':<8} {'총점':<8} {'레벨'}")
    print("-"*70)
    for r in result:
        print(f"{r['main']:<15} {r['related']:<15} {r['relation']:<10} {r['direct']:<8} {r['total']:<8} {r['level']}")

    print("\n" + "="*70)


def main():
    print(f"Neo4j 연결: {URI}, Database: {DATABASE}")

    with driver.session(database=DATABASE) as session:
        # 1. 초기화
        session.execute_write(clear_database)
        session.execute_write(create_indexes)

        # 2. 메인 기업 (Company) 생성 - 10개 카테고리 포함
        main_companies = [
            {"id": "COMP_SK", "name": "SK하이닉스", "ticker": "000660", "sector": "반도체", "market": "KOSPI", "isMain": True},
            {"id": "COMP_SS", "name": "삼성전자", "ticker": "005930", "sector": "전자", "market": "KOSPI", "isMain": True},
        ]

        for comp in main_companies:
            session.execute_write(create_company_with_categories, comp)
        print(f"[OK] 메인 Company {len(main_companies)}개 생성 (각 10개 카테고리)")

        # 3. 관련기업 (Company) 생성 - 10개 카테고리 포함
        related_companies = [
            # SK하이닉스 관련
            {"id": "COMP_SKM", "name": "SK머티리얼즈", "ticker": "", "sector": "소재", "market": "KOSPI", "isMain": False, "mainId": "COMP_SK", "relation": "계열사", "tier": 1},
            {"id": "COMP_SKS", "name": "SK실트론", "ticker": "", "sector": "소재", "market": "KOSPI", "isMain": False, "mainId": "COMP_SK", "relation": "계열사", "tier": 1},
            {"id": "COMP_MU", "name": "마이크론", "ticker": "MU", "sector": "반도체", "market": "NASDAQ", "isMain": False, "mainId": "COMP_SK", "relation": "경쟁사", "tier": 2},
            {"id": "COMP_AAPL", "name": "애플", "ticker": "AAPL", "sector": "IT", "market": "NASDAQ", "isMain": False, "mainId": "COMP_SK", "relation": "고객사", "tier": 1},
            # 삼성전자 관련
            {"id": "COMP_SSD", "name": "삼성디스플레이", "ticker": "", "sector": "디스플레이", "market": "", "isMain": False, "mainId": "COMP_SS", "relation": "계열사", "tier": 1},
            {"id": "COMP_SDI", "name": "삼성SDI", "ticker": "006400", "sector": "배터리", "market": "KOSPI", "isMain": False, "mainId": "COMP_SS", "relation": "계열사", "tier": 1},
            {"id": "COMP_TSMC", "name": "TSMC", "ticker": "TSM", "sector": "반도체", "market": "NYSE", "isMain": False, "mainId": "COMP_SS", "relation": "경쟁사", "tier": 2},
            {"id": "COMP_LG", "name": "LG전자", "ticker": "066570", "sector": "전자", "market": "KOSPI", "isMain": False, "mainId": "COMP_SS", "relation": "경쟁사", "tier": 2},
        ]

        for comp in related_companies:
            main_id = comp.pop("mainId")
            relation = comp.pop("relation")
            tier = comp.pop("tier")
            session.execute_write(create_company_with_categories, comp)
            session.execute_write(create_related_company_link, main_id, comp["id"], relation, tier)
        print(f"[OK] 관련 Company {len(related_companies)}개 생성 (각 10개 카테고리)")

        # 4. Deal 생성 (메인 기업 연결)
        deals = [
            {"id": "DEAL_001", "name": "SK하이닉스 검토", "status": "ACTIVE", "analyst": "김철수", "notes": "반도체 업황 점검"},
            {"id": "DEAL_002", "name": "삼성전자 검토", "status": "ACTIVE", "analyst": "이영희", "notes": "AI 반도체 확대"},
        ]

        session.execute_write(create_deal, deals[0], "COMP_SK")
        session.execute_write(create_deal, deals[1], "COMP_SS")
        print(f"[OK] Deal {len(deals)}개 생성")

        # 5. RiskEvent 생성 - 메인 기업
        events_sk = [
            {"category": "SHARE", "title": "SK하이닉스 최대주주 지분 변동", "summary": "SK텔레콤이 지분 일부 매각, 20.1%→18.5%로 감소", "type": "NEWS", "score": 35, "severity": "WARNING", "sourceName": "한국경제", "sourceUrl": "https://hankyung.com/1"},
            {"category": "EXEC", "title": "SK하이닉스 CFO 사임", "summary": "노종원 CFO 개인 사유로 사임, CEO 겸직 예정", "type": "DISCLOSURE", "score": 45, "severity": "WARNING", "relatedPerson": "노종원", "sourceName": "DART", "sourceUrl": "https://dart.fss.or.kr/1"},
            {"category": "LEGAL", "title": "ITC 특허 침해 소송 제기", "summary": "마이크론이 ITC에 특허 침해 소송 제기, HBM 관련 특허 3건", "type": "NEWS", "score": 60, "severity": "CRITICAL", "sourceName": "로이터", "sourceUrl": "https://reuters.com/1"},
            {"category": "LEGAL", "title": "공정위 담합 조사 착수", "summary": "DRAM 가격 담합 의혹으로 본사 현장조사 실시", "type": "NEWS", "score": 55, "severity": "CRITICAL", "sourceName": "연합뉴스", "sourceUrl": "https://yna.co.kr/1"},
            {"category": "ESG", "title": "이천 공장 폐수 유출", "summary": "산업 폐수가 인근 하천으로 유출, 환경부 조사 중", "type": "NEWS", "score": 40, "severity": "WARNING", "sourceName": "KBS", "sourceUrl": "https://kbs.co.kr/1"},
        ]

        events_ss = [
            {"category": "OPS", "title": "파운드리 수율 이슈", "summary": "3nm 파운드리 수율이 목표치 대비 20%p 낮음", "type": "NEWS", "score": 30, "severity": "WARNING", "sourceName": "디지타임스", "sourceUrl": "https://digitimes.com/1"},
            {"category": "CREDIT", "title": "삼성전자 신용등급 상향", "summary": "무디스 신용등급 Aa3→Aa2 상향, 재무건전성 개선", "type": "NEWS", "score": -15, "severity": "LOW", "sourceName": "무디스", "sourceUrl": "https://moodys.com/1"},
        ]

        for evt in events_sk:
            cat = evt.pop("category")
            session.execute_write(create_risk_event, "COMP_SK", cat, evt)

        for evt in events_ss:
            cat = evt.pop("category")
            session.execute_write(create_risk_event, "COMP_SS", cat, evt)

        print(f"[OK] 메인 기업 RiskEvent {len(events_sk) + len(events_ss)}개 생성")

        # 6. RiskEvent 생성 - 관련기업 (동일한 구조!)
        events_related = [
            {"companyId": "COMP_SKM", "category": "AUDIT", "title": "SK머티리얼즈 분식회계 의혹", "summary": "금감원 감리 착수, 매출 과대계상 혐의", "type": "ISSUE", "score": 70, "severity": "CRITICAL", "relatedPerson": "이석희", "sourceName": "조선일보", "sourceUrl": "https://chosun.com/1"},
            {"companyId": "COMP_MU", "category": "LEGAL", "title": "마이크론 중국 제재", "summary": "중국 정부 마이크론 제품 사용 금지, SK반사이익 기대", "type": "NEWS", "score": -20, "severity": "LOW", "sourceName": "블룸버그", "sourceUrl": "https://bloomberg.com/1"},
            {"companyId": "COMP_SDI", "category": "OPS", "title": "삼성SDI 배터리 화재 리콜", "summary": "전기차 탑재 배터리 화재 발생, 대규모 리콜 예상", "type": "NEWS", "score": 50, "severity": "CRITICAL", "sourceName": "블룸버그", "sourceUrl": "https://bloomberg.com/2"},
            {"companyId": "COMP_TSMC", "category": "OPS", "title": "TSMC 일본 공장 가동", "summary": "구마모토 공장 양산 시작, 삼성 파운드리 경쟁 심화", "type": "NEWS", "score": 20, "severity": "WARNING", "sourceName": "니케이", "sourceUrl": "https://nikkei.com/1"},
            {"companyId": "COMP_SSD", "category": "SUPPLY", "title": "삼성디스플레이 OLED 공급 부족", "summary": "아이폰용 OLED 패널 수급 차질 우려", "type": "NEWS", "score": 25, "severity": "WARNING", "sourceName": "디지타임스", "sourceUrl": "https://digitimes.com/2"},
        ]

        for evt in events_related:
            comp_id = evt.pop("companyId")
            cat = evt.pop("category")
            session.execute_write(create_risk_event, comp_id, cat, evt)

        print(f"[OK] 관련 기업 RiskEvent {len(events_related)}개 생성")

        # 7. 점수 계산
        session.execute_write(calculate_scores)

        # 8. 결과 출력
        session.execute_read(print_summary)

    driver.close()
    print("\n[OK] 그래프 DB 초기화 완료!")


if __name__ == "__main__":
    main()
