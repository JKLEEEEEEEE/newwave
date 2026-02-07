"""
Graph DB V4 초기화 스크립트
- 4-노드 계층 구조: Deal → RiskCategory/Company → RiskEvent
"""

from neo4j import GraphDatabase
from datetime import datetime, timedelta
import random
import hashlib
import os
import sys
from dotenv import load_dotenv

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# .env.local 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Neo4j 연결
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def clear_database(tx):
    """모든 노드와 관계 삭제"""
    tx.run("MATCH (n) DETACH DELETE n")
    print("[OK] 기존 데이터 모두 삭제")


def create_constraints(tx):
    """인덱스 및 제약조건 생성"""
    # 먼저 기존 인덱스/제약조건 삭제
    drop_statements = [
        "DROP INDEX deal_id_index IF EXISTS",
        "DROP INDEX category_id_index IF EXISTS",
        "DROP INDEX company_id_index IF EXISTS",
        "DROP INDEX event_id_index IF EXISTS",
        "DROP CONSTRAINT deal_id IF EXISTS",
        "DROP CONSTRAINT category_id IF EXISTS",
        "DROP CONSTRAINT company_id IF EXISTS",
        "DROP CONSTRAINT event_id IF EXISTS",
        "DROP CONSTRAINT deal_id_unique IF EXISTS",
        "DROP CONSTRAINT category_id_unique IF EXISTS",
        "DROP CONSTRAINT company_id_unique IF EXISTS",
        "DROP CONSTRAINT event_id_unique IF EXISTS",
    ]
    for stmt in drop_statements:
        try:
            tx.run(stmt)
        except:
            pass

    # 인덱스 생성 (제약조건 대신)
    indexes = [
        "CREATE INDEX deal_id_index IF NOT EXISTS FOR (d:Deal) ON (d.id)",
        "CREATE INDEX category_id_index IF NOT EXISTS FOR (c:RiskCategory) ON (c.id)",
        "CREATE INDEX company_id_index IF NOT EXISTS FOR (c:Company) ON (c.id)",
        "CREATE INDEX event_id_index IF NOT EXISTS FOR (e:RiskEvent) ON (e.id)",
    ]
    for idx in indexes:
        try:
            tx.run(idx)
        except:
            pass
    print("[OK] 인덱스 생성")


def create_deals(tx):
    """Deal 노드 생성 (메인 기업)"""
    deals = [
        {
            "id": "DEAL_001",
            "name": "SK하이닉스",
            "ticker": "000660",
            "sector": "반도체",
            "market": "KOSPI",
            "status": "ACTIVE",
            "analyst": "김철수",
            "notes": "반도체 업황 점검 필요",
        },
        {
            "id": "DEAL_002",
            "name": "삼성전자",
            "ticker": "005930",
            "sector": "전자",
            "market": "KOSPI",
            "status": "ACTIVE",
            "analyst": "이영희",
            "notes": "AI 반도체 시장 확대 중",
        },
    ]

    for d in deals:
        tx.run("""
            CREATE (deal:Deal {
                id: $id,
                name: $name,
                ticker: $ticker,
                sector: $sector,
                market: $market,
                status: $status,
                analyst: $analyst,
                notes: $notes,
                directScore: 0,
                propagatedScore: 0,
                totalRiskScore: 0,
                riskLevel: 'PASS',
                registeredAt: datetime(),
                updatedAt: datetime()
            })
        """, d)

    print(f"[OK] Deal 노드 {len(deals)}개 생성")
    return deals


def create_risk_categories(tx, deals):
    """RiskCategory 노드 생성 (10개 카테고리)"""
    categories = [
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

    count = 0
    for deal in deals:
        for cat in categories:
            cat_id = f"RC_{deal['id']}_{cat['code']}"
            tx.run("""
                MATCH (d:Deal {id: $dealId})
                CREATE (rc:RiskCategory {
                    id: $catId,
                    dealId: $dealId,
                    code: $code,
                    name: $name,
                    icon: $icon,
                    weight: $weight,
                    score: 0,
                    weightedScore: 0,
                    eventCount: 0,
                    trend: 'STABLE',
                    createdAt: datetime(),
                    updatedAt: datetime()
                })
                CREATE (d)-[:HAS_CATEGORY]->(rc)
            """, {
                "dealId": deal["id"],
                "catId": cat_id,
                "code": cat["code"],
                "name": cat["name"],
                "icon": cat["icon"],
                "weight": cat["weight"],
            })
            count += 1

    print(f"[OK] RiskCategory 노드 {count}개 생성")


def create_related_companies(tx, deals):
    """Company 노드 생성 (관련기업)"""
    related_companies = {
        "DEAL_001": [  # SK하이닉스 관련기업
            {"name": "SK머티리얼즈", "relation": "계열사", "tier": 1},
            {"name": "SK실트론", "relation": "계열사", "tier": 1},
            {"name": "마이크론", "relation": "경쟁사", "tier": 2},
            {"name": "삼성전자 반도체", "relation": "경쟁사", "tier": 2},
            {"name": "애플", "relation": "고객사", "tier": 1},
        ],
        "DEAL_002": [  # 삼성전자 관련기업
            {"name": "삼성디스플레이", "relation": "계열사", "tier": 1},
            {"name": "삼성SDI", "relation": "계열사", "tier": 1},
            {"name": "TSMC", "relation": "경쟁사", "tier": 2},
            {"name": "LG전자", "relation": "경쟁사", "tier": 2},
            {"name": "화웨이", "relation": "고객사", "tier": 1},
        ],
    }

    count = 0
    for deal in deals:
        companies = related_companies.get(deal["id"], [])
        for comp in companies:
            comp_id = f"COMP_{deal['id']}_{hashlib.md5(comp['name'].encode()).hexdigest()[:8]}"
            tx.run("""
                MATCH (d:Deal {id: $dealId})
                CREATE (c:Company {
                    id: $compId,
                    name: $name,
                    relation: $relation,
                    tier: $tier,
                    riskScore: 0,
                    createdAt: datetime(),
                    updatedAt: datetime()
                })
                CREATE (d)-[:HAS_RELATED {relation: $relation}]->(c)
            """, {
                "dealId": deal["id"],
                "compId": comp_id,
                "name": comp["name"],
                "relation": comp["relation"],
                "tier": comp["tier"],
            })
            count += 1

    print(f"[OK] Company 노드 {count}개 생성")


def create_risk_events(tx):
    """RiskEvent 노드 생성 (정보 노드)"""
    events = [
        # SK하이닉스 - 주주 카테고리
        {
            "dealId": "DEAL_001",
            "categoryCode": "SHARE",
            "title": "SK하이닉스 최대주주 지분 변동",
            "summary": "SK텔레콤이 SK하이닉스 지분 일부를 매각하여 최대주주 지분율이 20.1%에서 18.5%로 감소",
            "type": "NEWS",
            "score": 35,
            "severity": "WARNING",
            "relatedPerson": "박정호 SK텔레콤 대표",
            "sourceName": "한국경제",
            "sourceUrl": "https://www.hankyung.com/news/12345",
        },
        {
            "dealId": "DEAL_001",
            "categoryCode": "SHARE",
            "title": "외국인 투자자 대량 매도",
            "summary": "외국인 투자자들이 3거래일 연속 SK하이닉스 주식을 순매도, 총 5천억원 규모",
            "type": "NEWS",
            "score": 25,
            "severity": "WARNING",
            "relatedPerson": "",
            "sourceName": "매일경제",
            "sourceUrl": "https://www.mk.co.kr/news/67890",
        },
        # SK하이닉스 - 임원 카테고리
        {
            "dealId": "DEAL_001",
            "categoryCode": "EXEC",
            "title": "SK하이닉스 CFO 사임",
            "summary": "노종원 CFO가 개인 사유로 사임, 후임자 선임까지 CEO가 겸직 예정",
            "type": "DISCLOSURE",
            "score": 45,
            "severity": "WARNING",
            "relatedPerson": "노종원 CFO",
            "sourceName": "DART",
            "sourceUrl": "https://dart.fss.or.kr/report/1234",
        },
        # SK하이닉스 - 법률 카테고리
        {
            "dealId": "DEAL_001",
            "categoryCode": "LEGAL",
            "title": "ITC 특허 침해 소송 제기",
            "summary": "마이크론이 미국 국제무역위원회(ITC)에 SK하이닉스 특허 침해 소송 제기. HBM 관련 특허 3건 포함",
            "type": "NEWS",
            "score": 60,
            "severity": "CRITICAL",
            "relatedPerson": "",
            "sourceName": "로이터",
            "sourceUrl": "https://www.reuters.com/tech/12345",
        },
        {
            "dealId": "DEAL_001",
            "categoryCode": "LEGAL",
            "title": "공정위 담합 조사 착수",
            "summary": "공정거래위원회가 DRAM 가격 담합 의혹으로 SK하이닉스 본사 현장조사 실시",
            "type": "NEWS",
            "score": 55,
            "severity": "CRITICAL",
            "relatedPerson": "",
            "sourceName": "연합뉴스",
            "sourceUrl": "https://www.yna.co.kr/view/12345",
        },
        # SK하이닉스 - ESG 카테고리
        {
            "dealId": "DEAL_001",
            "categoryCode": "ESG",
            "title": "이천 공장 폐수 유출 사고",
            "summary": "SK하이닉스 이천 공장에서 산업 폐수가 인근 하천으로 유출되어 환경부 조사 중",
            "type": "NEWS",
            "score": 40,
            "severity": "WARNING",
            "relatedPerson": "",
            "sourceName": "KBS",
            "sourceUrl": "https://news.kbs.co.kr/12345",
        },
        # SK하이닉스 관련기업 - SK머티리얼즈
        {
            "dealId": "DEAL_001",
            "companyName": "SK머티리얼즈",
            "title": "SK머티리얼즈 분식회계 의혹",
            "summary": "금융감독원이 SK머티리얼즈의 분식회계 의혹에 대해 감리 착수. 매출 과대계상 혐의",
            "type": "ISSUE",
            "score": 70,
            "severity": "CRITICAL",
            "relatedPerson": "이석희 대표이사",
            "sourceName": "조선일보",
            "sourceUrl": "https://www.chosun.com/economy/12345",
        },
        {
            "dealId": "DEAL_001",
            "companyName": "마이크론",
            "title": "마이크론 중국 사업 제재",
            "summary": "중국 정부가 마이크론 제품의 중국 내 사용을 금지. SK하이닉스 반사이익 기대",
            "type": "NEWS",
            "score": -20,  # 긍정적 뉴스
            "severity": "LOW",
            "relatedPerson": "",
            "sourceName": "블룸버그",
            "sourceUrl": "https://www.bloomberg.com/news/12345",
        },
        # 삼성전자 - 신용 카테고리
        {
            "dealId": "DEAL_002",
            "categoryCode": "CREDIT",
            "title": "삼성전자 신용등급 상향 조정",
            "summary": "무디스가 삼성전자 신용등급을 Aa3에서 Aa2로 상향. 재무건전성 개선 평가",
            "type": "NEWS",
            "score": -15,  # 긍정적
            "severity": "LOW",
            "relatedPerson": "",
            "sourceName": "무디스",
            "sourceUrl": "https://www.moodys.com/research/12345",
        },
        # 삼성전자 - 운영 카테고리
        {
            "dealId": "DEAL_002",
            "categoryCode": "OPS",
            "title": "파운드리 수율 이슈",
            "summary": "삼성전자 3nm 파운드리 수율이 목표치 대비 20%p 낮아 고객사 이탈 우려",
            "type": "NEWS",
            "score": 30,
            "severity": "WARNING",
            "relatedPerson": "",
            "sourceName": "디지타임스",
            "sourceUrl": "https://www.digitimes.com/news/12345",
        },
        # 삼성전자 관련기업
        {
            "dealId": "DEAL_002",
            "companyName": "삼성SDI",
            "title": "삼성SDI 배터리 화재 리콜",
            "summary": "삼성SDI 배터리가 탑재된 전기차에서 화재 발생. 대규모 리콜 예상",
            "type": "NEWS",
            "score": 50,
            "severity": "CRITICAL",
            "relatedPerson": "",
            "sourceName": "블룸버그",
            "sourceUrl": "https://www.bloomberg.com/news/67890",
        },
        {
            "dealId": "DEAL_002",
            "companyName": "TSMC",
            "title": "TSMC 일본 공장 가동 시작",
            "summary": "TSMC 구마모토 공장 양산 시작. 삼성전자 파운드리 경쟁 심화 전망",
            "type": "NEWS",
            "score": 20,
            "severity": "WARNING",
            "relatedPerson": "",
            "sourceName": "니케이",
            "sourceUrl": "https://www.nikkei.com/article/12345",
        },
    ]

    count = 0
    for i, evt in enumerate(events):
        evt_id = f"EVT_{hashlib.md5(evt['title'].encode()).hexdigest()[:8]}"
        pub_date = datetime.now() - timedelta(days=random.randint(1, 30))

        if "categoryCode" in evt:
            # 카테고리에 연결
            tx.run("""
                MATCH (rc:RiskCategory {dealId: $dealId, code: $categoryCode})
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
                "dealId": evt["dealId"],
                "categoryCode": evt["categoryCode"],
                "eventId": evt_id,
                "title": evt["title"],
                "summary": evt["summary"],
                "type": evt["type"],
                "score": evt["score"],
                "severity": evt["severity"],
                "relatedPerson": evt.get("relatedPerson", ""),
                "sourceName": evt["sourceName"],
                "sourceUrl": evt["sourceUrl"],
                "publishedAt": pub_date.isoformat(),
            })
        else:
            # 관련기업에 연결
            tx.run("""
                MATCH (d:Deal {id: $dealId})-[:HAS_RELATED]->(c:Company {name: $companyName})
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
                CREATE (c)-[:HAS_EVENT]->(e)
                SET c.riskScore = c.riskScore + CASE WHEN $score > 0 THEN $score ELSE 0 END
            """, {
                "dealId": evt["dealId"],
                "companyName": evt["companyName"],
                "eventId": evt_id,
                "title": evt["title"],
                "summary": evt["summary"],
                "type": evt["type"],
                "score": evt["score"],
                "severity": evt["severity"],
                "relatedPerson": evt.get("relatedPerson", ""),
                "sourceName": evt["sourceName"],
                "sourceUrl": evt["sourceUrl"],
                "publishedAt": pub_date.isoformat(),
            })
        count += 1

    print(f"[OK] RiskEvent 노드 {count}개 생성")


def calculate_scores(tx):
    """점수 계산"""
    # 1. 카테고리 가중 점수 계산
    tx.run("""
        MATCH (rc:RiskCategory)
        SET rc.weightedScore = rc.score * rc.weight
    """)

    # 2. Deal 직접 점수 계산 (카테고리 가중 점수 합계)
    tx.run("""
        MATCH (d:Deal)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WITH d, SUM(rc.weightedScore) AS directScore
        SET d.directScore = toInteger(directScore)
    """)

    # 3. Deal 전이 점수 계산 (관련기업 리스크 점수의 30%)
    tx.run("""
        MATCH (d:Deal)-[:HAS_RELATED]->(c:Company)
        WITH d, SUM(c.riskScore) * 0.3 AS propagatedScore
        SET d.propagatedScore = toInteger(propagatedScore)
    """)

    # 4. 총점 계산
    tx.run("""
        MATCH (d:Deal)
        SET d.totalRiskScore = d.directScore + d.propagatedScore,
            d.riskLevel = CASE
                WHEN d.directScore + d.propagatedScore >= 50 THEN 'FAIL'
                WHEN d.directScore + d.propagatedScore >= 30 THEN 'WARNING'
                ELSE 'PASS'
            END,
            d.updatedAt = datetime()
    """)

    print("[OK] 점수 계산 완료")


def print_summary(tx):
    """결과 요약 출력"""
    print("\n" + "="*60)
    print("               📊 그래프 DB 초기화 완료")
    print("="*60)

    # 노드 수 카운트
    result = tx.run("""
        MATCH (d:Deal) RETURN 'Deal' AS label, count(d) AS count
        UNION ALL
        MATCH (rc:RiskCategory) RETURN 'RiskCategory' AS label, count(rc) AS count
        UNION ALL
        MATCH (c:Company) RETURN 'Company' AS label, count(c) AS count
        UNION ALL
        MATCH (e:RiskEvent) RETURN 'RiskEvent' AS label, count(e) AS count
    """)

    print("\n📦 노드 현황:")
    for record in result:
        print(f"   {record['label']}: {record['count']}개")

    # 관계 수 카운트
    result = tx.run("""
        MATCH ()-[r:HAS_CATEGORY]->() RETURN 'HAS_CATEGORY' AS type, count(r) AS count
        UNION ALL
        MATCH ()-[r:HAS_RELATED]->() RETURN 'HAS_RELATED' AS type, count(r) AS count
        UNION ALL
        MATCH ()-[r:HAS_EVENT]->() RETURN 'HAS_EVENT' AS type, count(r) AS count
    """)

    print("\n🔗 관계 현황:")
    for record in result:
        print(f"   {record['type']}: {record['count']}개")

    # Deal별 점수
    result = tx.run("""
        MATCH (d:Deal)
        RETURN d.name AS name, d.directScore AS direct,
               d.propagatedScore AS propagated, d.totalRiskScore AS total,
               d.riskLevel AS level
        ORDER BY d.totalRiskScore DESC
    """)

    print("\n📈 Deal별 리스크 점수:")
    print("-"*60)
    print(f"{'기업명':<15} {'직접':<8} {'전이':<8} {'총점':<8} {'레벨':<10}")
    print("-"*60)
    for record in result:
        print(f"{record['name']:<15} {record['direct']:<8} {record['propagated']:<8} {record['total']:<8} {record['level']:<10}")

    # 주요 이벤트
    result = tx.run("""
        MATCH (e:RiskEvent)
        WHERE e.score > 0
        RETURN e.title AS title, e.score AS score, e.severity AS severity, e.type AS type
        ORDER BY e.score DESC
        LIMIT 5
    """)

    print("\n🔥 주요 리스크 이벤트 (Top 5):")
    print("-"*60)
    for record in result:
        emoji = "🔴" if record['severity'] == 'CRITICAL' else "🟡" if record['severity'] == 'WARNING' else "🟢"
        print(f"   {emoji} [{record['score']}점] {record['title'][:40]}...")

    print("\n" + "="*60)


def main():
    print(f"🔗 Neo4j 연결: {URI}")
    print(f"   Database: {DATABASE}")
    with driver.session(database=DATABASE) as session:
        # 1. 초기화
        session.execute_write(clear_database)
        session.execute_write(create_constraints)

        # 2. 노드 생성
        deals = session.execute_write(create_deals)
        session.execute_write(create_risk_categories, deals)
        session.execute_write(create_related_companies, deals)
        session.execute_write(create_risk_events)

        # 3. 점수 계산
        session.execute_write(calculate_scores)

        # 4. 결과 출력
        session.execute_read(print_summary)

    driver.close()
    print("\n[OK] 그래프 DB 초기화 및 샘플 데이터 생성 완료!")


if __name__ == "__main__":
    main()
