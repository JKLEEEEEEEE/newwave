"""
Graph DB V5 초기화 스크립트
- Deal: 투자검토 관리
- Company: 메인 + 관련기업 (동일 구조)
- RiskCategory: 10개 카테고리
- RiskEntity: 구체적 대상 (인물, 주주, 소송 등)
- RiskEvent: 뉴스/이슈/공시
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

# 10개 카테고리
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
        "CREATE INDEX entity_id IF NOT EXISTS FOR (e:RiskEntity) ON (e.id)",
        "CREATE INDEX event_id IF NOT EXISTS FOR (e:RiskEvent) ON (e.id)",
    ]
    for idx in indexes:
        try:
            tx.run(idx)
        except:
            pass
    print("[OK] 인덱스 생성")


def create_company_with_categories(tx, company_data):
    """Company + 10개 RiskCategory 생성"""
    comp_id = company_data["id"]

    tx.run("""
        CREATE (c:Company {
            id: $id, name: $name, ticker: $ticker, sector: $sector,
            market: $market, isMain: $isMain,
            directScore: 0, propagatedScore: 0, totalRiskScore: 0, riskLevel: 'PASS',
            createdAt: datetime(), updatedAt: datetime()
        })
    """, company_data)

    for cat in CATEGORIES:
        cat_id = f"RC_{comp_id}_{cat['code']}"
        tx.run("""
            MATCH (c:Company {id: $compId})
            CREATE (rc:RiskCategory {
                id: $catId, companyId: $compId, code: $code, name: $name,
                icon: $icon, weight: $weight, score: 0, weightedScore: 0,
                entityCount: 0, eventCount: 0, trend: 'STABLE', createdAt: datetime()
            })
            CREATE (c)-[:HAS_CATEGORY]->(rc)
        """, {"compId": comp_id, "catId": cat_id, **cat})


def create_deal(tx, deal_data, main_company_id):
    """Deal 생성 + TARGET 관계"""
    tx.run("""
        MATCH (c:Company {id: $mainCompanyId})
        CREATE (d:Deal {
            id: $id, name: $name, status: $status, analyst: $analyst, notes: $notes,
            registeredAt: datetime(), updatedAt: datetime()
        })
        CREATE (d)-[:TARGET]->(c)
    """, {**deal_data, "mainCompanyId": main_company_id})


def create_related_link(tx, main_id, related_id, relation, tier):
    """관련기업 연결"""
    tx.run("""
        MATCH (m:Company {id: $mainId}), (r:Company {id: $relatedId})
        CREATE (m)-[:HAS_RELATED {relation: $relation, tier: $tier}]->(r)
    """, {"mainId": main_id, "relatedId": related_id, "relation": relation, "tier": tier})


def create_risk_entity(tx, company_id, category_code, entity_data):
    """RiskEntity 생성 (카테고리 하위의 구체적 대상)"""
    ent_id = entity_data.get("id") or f"ENT_{hashlib.md5((company_id + entity_data['name']).encode()).hexdigest()[:8]}"

    tx.run("""
        MATCH (c:Company {id: $companyId})-[:HAS_CATEGORY]->(rc:RiskCategory {code: $categoryCode})
        CREATE (e:RiskEntity {
            id: $entId, name: $name, type: $type, subType: $subType,
            position: $position, description: $description,
            riskScore: 0, eventCount: 0, createdAt: datetime()
        })
        CREATE (rc)-[:HAS_ENTITY]->(e)
        SET rc.entityCount = rc.entityCount + 1
    """, {
        "companyId": company_id,
        "categoryCode": category_code,
        "entId": ent_id,
        "name": entity_data["name"],
        "type": entity_data.get("type", "OTHER"),
        "subType": entity_data.get("subType", ""),
        "position": entity_data.get("position", ""),
        "description": entity_data.get("description", ""),
    })
    return ent_id


def create_risk_event(tx, entity_id, event_data):
    """RiskEvent 생성 (Entity 하위)"""
    evt_id = f"EVT_{hashlib.md5((entity_id + event_data['title']).encode()).hexdigest()[:8]}"
    pub_date = datetime.now() - timedelta(days=random.randint(1, 30))

    tx.run("""
        MATCH (ent:RiskEntity {id: $entityId})
        CREATE (e:RiskEvent {
            id: $evtId, title: $title, summary: $summary, type: $type,
            score: $score, severity: $severity,
            sourceName: $sourceName, sourceUrl: $sourceUrl,
            publishedAt: $publishedAt, collectedAt: datetime(), isActive: true
        })
        CREATE (ent)-[:HAS_EVENT]->(e)
        SET ent.eventCount = ent.eventCount + 1,
            ent.riskScore = ent.riskScore + CASE WHEN $score > 0 THEN $score ELSE 0 END
    """, {
        "entityId": entity_id,
        "evtId": evt_id,
        "title": event_data["title"],
        "summary": event_data["summary"],
        "type": event_data.get("type", "NEWS"),
        "score": event_data.get("score", 0),
        "severity": event_data.get("severity", "LOW"),
        "sourceName": event_data.get("sourceName", ""),
        "sourceUrl": event_data.get("sourceUrl", ""),
        "publishedAt": pub_date.isoformat(),
    })


def calculate_scores(tx):
    """점수 계산"""
    # 1. Entity → Category 점수 집계
    tx.run("""
        MATCH (rc:RiskCategory)-[:HAS_ENTITY]->(ent:RiskEntity)
        WITH rc, SUM(ent.riskScore) AS totalScore, COUNT(ent) AS entCount
        SET rc.score = totalScore, rc.entityCount = entCount,
            rc.weightedScore = totalScore * rc.weight
    """)

    # 2. Category 이벤트 수 집계
    tx.run("""
        MATCH (rc:RiskCategory)-[:HAS_ENTITY]->(ent:RiskEntity)-[:HAS_EVENT]->(evt:RiskEvent)
        WITH rc, COUNT(evt) AS evtCount
        SET rc.eventCount = evtCount
    """)

    # 3. Company 직접 점수
    tx.run("""
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WITH c, SUM(rc.weightedScore) AS directScore
        SET c.directScore = toInteger(directScore)
    """)

    # 4. Company 전이 점수
    tx.run("""
        MATCH (c:Company)-[:HAS_RELATED]->(r:Company)
        WITH c, SUM(r.directScore) * 0.3 AS propagatedScore
        SET c.propagatedScore = toInteger(propagatedScore)
    """)

    # 5. 총점 및 레벨
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
    print("                    그래프 DB V5 초기화 완료")
    print("="*70)

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

    result = tx.run("""
        MATCH (d:Deal)-[:TARGET]->(c:Company)
        RETURN d.name AS deal, c.name AS company, c.directScore AS direct,
               c.propagatedScore AS propagated, c.totalRiskScore AS total, c.riskLevel AS level
        ORDER BY c.totalRiskScore DESC
    """)
    print("\n[메인 기업]")
    print("-"*70)
    for r in result:
        print(f"   {r['deal']}: {r['company']} | 직접:{r['direct']} 전이:{r['propagated']} 총:{r['total']} ({r['level']})")

    # 드릴다운 예시
    result = tx.run("""
        MATCH (c:Company {name: 'SK하이닉스'})-[:HAS_CATEGORY]->(rc:RiskCategory)-[:HAS_ENTITY]->(ent:RiskEntity)
        WHERE rc.score > 0
        RETURN rc.name AS category, ent.name AS entity, ent.type AS type, ent.riskScore AS score
        ORDER BY ent.riskScore DESC LIMIT 10
    """)
    print("\n[드릴다운 예시: SK하이닉스 → 카테고리 → 엔티티]")
    print("-"*70)
    for r in result:
        print(f"   {r['category']} → {r['entity']} ({r['type']}) | 점수: {r['score']}")

    print("\n" + "="*70)


def main():
    print(f"Neo4j: {URI}, DB: {DATABASE}")

    with driver.session(database=DATABASE) as session:
        session.execute_write(clear_database)
        session.execute_write(create_indexes)

        # 1. 메인 기업 생성
        main_companies = [
            {"id": "COMP_SK", "name": "SK하이닉스", "ticker": "000660", "sector": "반도체", "market": "KOSPI", "isMain": True},
            {"id": "COMP_SS", "name": "삼성전자", "ticker": "005930", "sector": "전자", "market": "KOSPI", "isMain": True},
        ]
        for c in main_companies:
            session.execute_write(create_company_with_categories, c)
        print(f"[OK] 메인 Company {len(main_companies)}개 (각 10개 카테고리)")

        # 2. 관련 기업 생성
        related = [
            {"id": "COMP_SKM", "name": "SK머티리얼즈", "ticker": "", "sector": "소재", "market": "KOSPI", "isMain": False, "main": "COMP_SK", "rel": "계열사", "tier": 1},
            {"id": "COMP_MU", "name": "마이크론", "ticker": "MU", "sector": "반도체", "market": "NASDAQ", "isMain": False, "main": "COMP_SK", "rel": "경쟁사", "tier": 2},
            {"id": "COMP_SDI", "name": "삼성SDI", "ticker": "006400", "sector": "배터리", "market": "KOSPI", "isMain": False, "main": "COMP_SS", "rel": "계열사", "tier": 1},
            {"id": "COMP_TSMC", "name": "TSMC", "ticker": "TSM", "sector": "반도체", "market": "NYSE", "isMain": False, "main": "COMP_SS", "rel": "경쟁사", "tier": 2},
        ]
        for r in related:
            main_id, rel, tier = r.pop("main"), r.pop("rel"), r.pop("tier")
            session.execute_write(create_company_with_categories, r)
            session.execute_write(create_related_link, main_id, r["id"], rel, tier)
        print(f"[OK] 관련 Company {len(related)}개")

        # 3. Deal 생성
        session.execute_write(create_deal, {"id": "DEAL_001", "name": "SK하이닉스 검토", "status": "ACTIVE", "analyst": "김철수", "notes": ""}, "COMP_SK")
        session.execute_write(create_deal, {"id": "DEAL_002", "name": "삼성전자 검토", "status": "ACTIVE", "analyst": "이영희", "notes": ""}, "COMP_SS")
        print("[OK] Deal 2개")

        # 4. SK하이닉스 - RiskEntity + RiskEvent
        # 임원 카테고리
        ent_cfo = session.execute_write(create_risk_entity, "COMP_SK", "EXEC", {
            "name": "노종원", "type": "PERSON", "subType": "임원", "position": "CFO", "description": "SK하이닉스 최고재무책임자"
        })
        session.execute_write(create_risk_event, ent_cfo, {"title": "SK하이닉스 CFO 사임", "summary": "노종원 CFO 개인 사유로 사임 발표", "type": "DISCLOSURE", "score": 45, "severity": "WARNING", "sourceName": "DART", "sourceUrl": "https://dart.fss.or.kr/1"})
        session.execute_write(create_risk_event, ent_cfo, {"title": "CFO 사임 후 주가 하락", "summary": "CFO 사임 소식에 주가 3% 하락", "type": "NEWS", "score": 20, "severity": "WARNING", "sourceName": "한경", "sourceUrl": "https://hankyung.com/1"})

        ent_ceo = session.execute_write(create_risk_entity, "COMP_SK", "EXEC", {
            "name": "곽노정", "type": "PERSON", "subType": "임원", "position": "CEO", "description": "SK하이닉스 대표이사"
        })
        session.execute_write(create_risk_event, ent_ceo, {"title": "CEO 스톡옵션 행사", "summary": "곽노정 CEO 100억원 규모 스톡옵션 행사", "type": "DISCLOSURE", "score": 15, "severity": "LOW", "sourceName": "DART", "sourceUrl": "https://dart.fss.or.kr/2"})

        # 주주 카테고리
        ent_skt = session.execute_write(create_risk_entity, "COMP_SK", "SHARE", {
            "name": "SK텔레콤", "type": "SHAREHOLDER", "subType": "최대주주", "position": "20.1%", "description": "최대주주"
        })
        session.execute_write(create_risk_event, ent_skt, {"title": "SK텔레콤 지분 매각", "summary": "SK텔레콤이 지분 일부 매각, 20.1%→18.5%", "type": "NEWS", "score": 35, "severity": "WARNING", "sourceName": "연합뉴스", "sourceUrl": "https://yna.co.kr/1"})

        ent_nps = session.execute_write(create_risk_entity, "COMP_SK", "SHARE", {
            "name": "국민연금", "type": "SHAREHOLDER", "subType": "기관투자자", "position": "9.8%", "description": "기관투자자"
        })
        session.execute_write(create_risk_event, ent_nps, {"title": "국민연금 지분 확대", "summary": "국민연금 지분 9.5%→9.8% 확대", "type": "NEWS", "score": -10, "severity": "LOW", "sourceName": "머니투데이", "sourceUrl": "https://mt.co.kr/1"})

        # 법률 카테고리
        ent_itc = session.execute_write(create_risk_entity, "COMP_SK", "LEGAL", {
            "name": "ITC 특허소송", "type": "CASE", "subType": "특허침해", "position": "", "description": "마이크론 제소 HBM 특허 침해"
        })
        session.execute_write(create_risk_event, ent_itc, {"title": "ITC 특허 침해 소송 제기", "summary": "마이크론이 ITC에 HBM 특허 침해 소송 제기", "type": "NEWS", "score": 60, "severity": "CRITICAL", "sourceName": "로이터", "sourceUrl": "https://reuters.com/1"})
        session.execute_write(create_risk_event, ent_itc, {"title": "ITC 예비판정 SK 불리", "summary": "ITC 예비판정에서 SK하이닉스에 불리한 결정", "type": "NEWS", "score": 40, "severity": "CRITICAL", "sourceName": "블룸버그", "sourceUrl": "https://bloomberg.com/1"})

        ent_ftc = session.execute_write(create_risk_entity, "COMP_SK", "LEGAL", {
            "name": "공정위 담합조사", "type": "CASE", "subType": "담합", "position": "", "description": "DRAM 가격 담합 의혹"
        })
        session.execute_write(create_risk_event, ent_ftc, {"title": "공정위 담합 조사 착수", "summary": "DRAM 가격 담합 의혹으로 본사 현장조사", "type": "NEWS", "score": 55, "severity": "CRITICAL", "sourceName": "연합뉴스", "sourceUrl": "https://yna.co.kr/2"})

        # ESG 카테고리
        ent_env = session.execute_write(create_risk_entity, "COMP_SK", "ESG", {
            "name": "이천공장 환경이슈", "type": "ISSUE", "subType": "환경오염", "position": "", "description": "폐수 유출 사고"
        })
        session.execute_write(create_risk_event, ent_env, {"title": "이천 공장 폐수 유출", "summary": "산업 폐수가 인근 하천으로 유출", "type": "NEWS", "score": 40, "severity": "WARNING", "sourceName": "KBS", "sourceUrl": "https://kbs.co.kr/1"})

        print("[OK] SK하이닉스 Entity 7개, Event 10개")

        # 5. 삼성전자 - RiskEntity + RiskEvent
        ent_jy = session.execute_write(create_risk_entity, "COMP_SS", "EXEC", {
            "name": "이재용", "type": "PERSON", "subType": "임원", "position": "회장", "description": "삼성전자 회장"
        })
        session.execute_write(create_risk_event, ent_jy, {"title": "이재용 회장 경영복귀", "summary": "이재용 회장 본격 경영 복귀", "type": "NEWS", "score": -15, "severity": "LOW", "sourceName": "조선일보", "sourceUrl": "https://chosun.com/1"})

        ent_yield = session.execute_write(create_risk_entity, "COMP_SS", "OPS", {
            "name": "3nm 수율이슈", "type": "ISSUE", "subType": "생산", "position": "", "description": "파운드리 수율 문제"
        })
        session.execute_write(create_risk_event, ent_yield, {"title": "3nm 파운드리 수율 저조", "summary": "3nm 수율 목표 대비 20%p 낮음", "type": "NEWS", "score": 30, "severity": "WARNING", "sourceName": "디지타임스", "sourceUrl": "https://digitimes.com/1"})

        print("[OK] 삼성전자 Entity 2개, Event 2개")

        # 6. 관련기업 Entity + Event
        ent_skm_audit = session.execute_write(create_risk_entity, "COMP_SKM", "AUDIT", {
            "name": "분식회계 의혹", "type": "ISSUE", "subType": "회계", "position": "", "description": "매출 과대계상 의혹"
        })
        session.execute_write(create_risk_event, ent_skm_audit, {"title": "SK머티리얼즈 분식회계 의혹", "summary": "금감원 감리 착수, 매출 과대계상 혐의", "type": "NEWS", "score": 70, "severity": "CRITICAL", "sourceName": "조선일보", "sourceUrl": "https://chosun.com/2"})

        ent_sdi_fire = session.execute_write(create_risk_entity, "COMP_SDI", "OPS", {
            "name": "배터리 화재", "type": "ISSUE", "subType": "안전", "position": "", "description": "전기차 배터리 화재"
        })
        session.execute_write(create_risk_event, ent_sdi_fire, {"title": "삼성SDI 배터리 화재 리콜", "summary": "전기차 탑재 배터리 화재, 대규모 리콜 예상", "type": "NEWS", "score": 50, "severity": "CRITICAL", "sourceName": "블룸버그", "sourceUrl": "https://bloomberg.com/2"})

        print("[OK] 관련기업 Entity 2개, Event 2개")

        # 7. 점수 계산
        session.execute_write(calculate_scores)

        # 8. 결과 출력
        session.execute_read(print_summary)

    driver.close()
    print("\n[OK] 완료!")


if __name__ == "__main__":
    main()
