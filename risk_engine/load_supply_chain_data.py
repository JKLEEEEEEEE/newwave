"""
============================================================================
Supply Chain 샘플 데이터 로드
============================================================================
Neo4j에 공급망 관계 데이터를 생성합니다.
"""

import os
import logging
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 샘플 기업 데이터 (id = name으로 통일하여 테스트에서 이름으로 조회 가능)
# directScore + propagatedScore = totalRiskScore
COMPANIES = [
    # 대상 기업 (Deal Targets)
    {"id": "SK하이닉스", "name": "SK하이닉스", "sector": "반도체", "corpCode": "00126380",
     "riskScore": 58, "directScore": 46, "propagatedScore": 12},
    {"id": "삼성전자", "name": "삼성전자", "sector": "전자", "corpCode": "00126308",
     "riskScore": 35, "directScore": 28, "propagatedScore": 7},
    {"id": "LG에너지솔루션", "name": "LG에너지솔루션", "sector": "배터리", "corpCode": "00401731",
     "riskScore": 42, "directScore": 35, "propagatedScore": 7},
    {"id": "현대자동차", "name": "현대자동차", "sector": "자동차", "corpCode": "00164742",
     "riskScore": 48, "directScore": 38, "propagatedScore": 10},
    {"id": "한미반도체", "name": "한미반도체", "sector": "반도체장비", "corpCode": "00156225",
     "riskScore": 78, "directScore": 65, "propagatedScore": 13},

    # 공급사 (Suppliers)
    {"id": "ASML", "name": "ASML", "sector": "반도체장비",
     "riskScore": 25, "directScore": 22, "propagatedScore": 3},
    {"id": "Lam Research", "name": "Lam Research", "sector": "반도체장비",
     "riskScore": 30, "directScore": 26, "propagatedScore": 4},
    {"id": "Applied Materials", "name": "Applied Materials", "sector": "반도체장비",
     "riskScore": 28, "directScore": 24, "propagatedScore": 4},
    {"id": "도쿄일렉트론", "name": "도쿄일렉트론", "sector": "반도체장비",
     "riskScore": 32, "directScore": 28, "propagatedScore": 4},
    {"id": "SK머티리얼즈", "name": "SK머티리얼즈", "sector": "소재",
     "riskScore": 45, "directScore": 38, "propagatedScore": 7},
    {"id": "동우화인켐", "name": "동우화인켐", "sector": "화학",
     "riskScore": 52, "directScore": 44, "propagatedScore": 8},
    {"id": "LG화학", "name": "LG화학", "sector": "화학",
     "riskScore": 38, "directScore": 32, "propagatedScore": 6},
    {"id": "포스코", "name": "포스코", "sector": "철강",
     "riskScore": 41, "directScore": 35, "propagatedScore": 6},
    {"id": "현대제철", "name": "현대제철", "sector": "철강",
     "riskScore": 44, "directScore": 37, "propagatedScore": 7},
    {"id": "삼성SDI", "name": "삼성SDI", "sector": "배터리",
     "riskScore": 36, "directScore": 30, "propagatedScore": 6},

    # 고객사 (Customers)
    {"id": "Apple", "name": "Apple", "sector": "IT",
     "riskScore": 22, "directScore": 18, "propagatedScore": 4},
    {"id": "NVIDIA", "name": "NVIDIA", "sector": "반도체",
     "riskScore": 18, "directScore": 15, "propagatedScore": 3},
    {"id": "Tesla", "name": "Tesla", "sector": "자동차",
     "riskScore": 35, "directScore": 29, "propagatedScore": 6},
    {"id": "Amazon", "name": "Amazon", "sector": "IT",
     "riskScore": 20, "directScore": 17, "propagatedScore": 3},
    {"id": "Microsoft", "name": "Microsoft", "sector": "IT",
     "riskScore": 15, "directScore": 12, "propagatedScore": 3},
    {"id": "Google", "name": "Google", "sector": "IT",
     "riskScore": 17, "directScore": 14, "propagatedScore": 3},
    {"id": "Volkswagen", "name": "Volkswagen", "sector": "자동차",
     "riskScore": 42, "directScore": 35, "propagatedScore": 7},
    {"id": "BMW", "name": "BMW", "sector": "자동차",
     "riskScore": 38, "directScore": 32, "propagatedScore": 6},
    {"id": "Ford", "name": "Ford", "sector": "자동차",
     "riskScore": 48, "directScore": 40, "propagatedScore": 8},
    {"id": "GM", "name": "GM", "sector": "자동차",
     "riskScore": 45, "directScore": 38, "propagatedScore": 7},
]

# 공급망 관계 (SUPPLIES_TO) - id = name 으로 통일
SUPPLY_RELATIONS = [
    # SK하이닉스 공급망
    {"from": "ASML", "to": "SK하이닉스", "dependency": 0.3, "type": "SUPPLIES_TO"},
    {"from": "Lam Research", "to": "SK하이닉스", "dependency": 0.25, "type": "SUPPLIES_TO"},
    {"from": "Applied Materials", "to": "SK하이닉스", "dependency": 0.2, "type": "SUPPLIES_TO"},
    {"from": "SK머티리얼즈", "to": "SK하이닉스", "dependency": 0.45, "type": "SUPPLIES_TO"},
    {"from": "동우화인켐", "to": "SK하이닉스", "dependency": 0.35, "type": "SUPPLIES_TO"},
    {"from": "한미반도체", "to": "SK하이닉스", "dependency": 0.5, "type": "SUPPLIES_TO"},

    # SK하이닉스 고객
    {"from": "SK하이닉스", "to": "Apple", "dependency": 0.4, "type": "SUPPLIES_TO"},
    {"from": "SK하이닉스", "to": "NVIDIA", "dependency": 0.35, "type": "SUPPLIES_TO"},
    {"from": "SK하이닉스", "to": "Amazon", "dependency": 0.25, "type": "SUPPLIES_TO"},
    {"from": "SK하이닉스", "to": "Microsoft", "dependency": 0.3, "type": "SUPPLIES_TO"},

    # 삼성전자 공급망
    {"from": "ASML", "to": "삼성전자", "dependency": 0.35, "type": "SUPPLIES_TO"},
    {"from": "도쿄일렉트론", "to": "삼성전자", "dependency": 0.2, "type": "SUPPLIES_TO"},
    {"from": "Applied Materials", "to": "삼성전자", "dependency": 0.25, "type": "SUPPLIES_TO"},

    # 삼성전자 고객
    {"from": "삼성전자", "to": "Apple", "dependency": 0.5, "type": "SUPPLIES_TO"},
    {"from": "삼성전자", "to": "Google", "dependency": 0.3, "type": "SUPPLIES_TO"},

    # LG에너지솔루션 공급망
    {"from": "LG화학", "to": "LG에너지솔루션", "dependency": 0.6, "type": "SUPPLIES_TO"},
    {"from": "포스코", "to": "LG에너지솔루션", "dependency": 0.3, "type": "SUPPLIES_TO"},

    # LG에너지솔루션 고객
    {"from": "LG에너지솔루션", "to": "Tesla", "dependency": 0.45, "type": "SUPPLIES_TO"},
    {"from": "LG에너지솔루션", "to": "Volkswagen", "dependency": 0.35, "type": "SUPPLIES_TO"},
    {"from": "LG에너지솔루션", "to": "GM", "dependency": 0.4, "type": "SUPPLIES_TO"},
    {"from": "LG에너지솔루션", "to": "Ford", "dependency": 0.3, "type": "SUPPLIES_TO"},

    # 현대자동차 공급망
    {"from": "현대제철", "to": "현대자동차", "dependency": 0.5, "type": "SUPPLIES_TO"},
    {"from": "LG에너지솔루션", "to": "현대자동차", "dependency": 0.4, "type": "SUPPLIES_TO"},
    {"from": "삼성SDI", "to": "현대자동차", "dependency": 0.35, "type": "SUPPLIES_TO"},

    # 한미반도체 고객
    {"from": "한미반도체", "to": "삼성전자", "dependency": 0.3, "type": "SUPPLIES_TO"},
]

# 경쟁 관계
COMPETES_WITH = [
    {"from": "SK하이닉스", "to": "삼성전자", "type": "COMPETES_WITH"},
    {"from": "LG에너지솔루션", "to": "삼성SDI", "type": "COMPETES_WITH"},
    {"from": "Tesla", "to": "현대자동차", "type": "COMPETES_WITH"},
]


def load_supply_chain_data():
    """Supply Chain 데이터를 Neo4j에 로드"""
    try:
        from risk_engine.neo4j_client import neo4j_client
    except ImportError:
        logger.error("neo4j_client를 import할 수 없습니다")
        return False

    try:
        neo4j_client.connect()
        logger.info("Neo4j 연결 성공")

        # 0. Status 노드 생성 (PASS, WARNING, FAIL)
        status_create_query = """
        MERGE (s:Status {id: 'PASS'}) SET s.name = 'PASS', s.level = 0
        MERGE (s2:Status {id: 'WARNING'}) SET s2.name = 'WARNING', s2.level = 1
        MERGE (s3:Status {id: 'FAIL'}) SET s3.name = 'FAIL', s3.level = 2
        """
        neo4j_client.execute_write(status_create_query)
        logger.info("✅ Status 노드 생성 완료")

        # 1. Company 노드 생성
        for company in COMPANIES:
            query = """
            MERGE (c:Company {id: $id})
            SET c.name = $name,
                c.sector = $sector,
                c.corpCode = $corpCode,
                c.totalRiskScore = $riskScore,
                c.directRiskScore = $directScore,
                c.propagatedRiskScore = $propagatedScore,
                c.status = CASE
                    WHEN $riskScore >= 75 THEN 'FAIL'
                    WHEN $riskScore >= 50 THEN 'WARNING'
                    ELSE 'PASS'
                END,
                c.riskLevel = CASE
                    WHEN $riskScore >= 75 THEN 'FAIL'
                    WHEN $riskScore >= 50 THEN 'WARNING'
                    ELSE 'PASS'
                END,
                c.updatedAt = datetime()
            """
            neo4j_client.execute_write(query, {
                "id": company["id"],
                "name": company["name"],
                "sector": company["sector"],
                "corpCode": company.get("corpCode", ""),
                "riskScore": company["riskScore"],
                "directScore": company.get("directScore", company["riskScore"]),
                "propagatedScore": company.get("propagatedScore", 0)
            })

        logger.info(f"✅ {len(COMPANIES)}개 Company 노드 생성 완료")

        # 2. Status 노드 연결
        status_query = """
        MATCH (c:Company)
        MATCH (s:Status {id: c.riskLevel})
        MERGE (c)-[:HAS_STATUS]->(s)
        """
        neo4j_client.execute_write(status_query)
        logger.info("✅ Status 관계 연결 완료")

        # 3. SUPPLIES_TO 관계 생성
        for rel in SUPPLY_RELATIONS:
            query = """
            MATCH (from:Company {id: $fromId})
            MATCH (to:Company {id: $toId})
            MERGE (from)-[r:SUPPLIES_TO]->(to)
            SET r.dependency = $dependency,
                r.riskTransfer = $dependency * from.totalRiskScore / 100.0,
                r.updatedAt = datetime()
            """
            neo4j_client.execute_write(query, {
                "fromId": rel["from"],
                "toId": rel["to"],
                "dependency": rel["dependency"]
            })

        logger.info(f"✅ {len(SUPPLY_RELATIONS)}개 SUPPLIES_TO 관계 생성 완료")

        # 4. COMPETES_WITH 관계 생성
        for rel in COMPETES_WITH:
            query = """
            MATCH (from:Company {id: $fromId})
            MATCH (to:Company {id: $toId})
            MERGE (from)-[r:COMPETES_WITH]->(to)
            SET r.updatedAt = datetime()
            """
            neo4j_client.execute_write(query, {
                "fromId": rel["from"],
                "toId": rel["to"]
            })

        logger.info(f"✅ {len(COMPETES_WITH)}개 COMPETES_WITH 관계 생성 완료")

        # 5. DealTarget 노드 생성 (핵심 딜 대상만, 공급사/경쟁사 제외)
        # 한미반도체: SK하이닉스의 공급사이므로 Deal Target에서 제외
        # 삼성전자: SK하이닉스의 경쟁사이므로 Deal Target에서 제외
        deal_targets = ["SK하이닉스", "LG에너지솔루션", "현대자동차"]
        for idx, target_id in enumerate(deal_targets, 1):
            query = """
            MATCH (c:Company {id: $companyId})
            MERGE (d:Deal {id: $dealId})
            SET d.name = 'Deal ' + toString($idx),
                d.type = 'EQUITY'
            MERGE (dt:DealTarget {id: $companyId})
            SET dt.name = c.name,
                dt.sector = c.sector,
                dt.totalRiskScore = c.totalRiskScore,
                dt.riskLevel = c.riskLevel
            MERGE (d)-[:TARGET]->(dt)
            """
            neo4j_client.execute_write(query, {
                "companyId": target_id,
                "dealId": f"deal{idx}",
                "idx": idx
            })

        logger.info(f"✅ {len(deal_targets)}개 Deal/DealTarget 생성 완료")

        # 6. RiskCategory 노드 생성 (Score Breakdown 테스트용)
        categories = [
            {"name": "시장위험", "weight": 0.20},
            {"name": "신용위험", "weight": 0.25},
            {"name": "운영위험", "weight": 0.15},
            {"name": "법률위험", "weight": 0.15},
            {"name": "공급망위험", "weight": 0.15},
            {"name": "ESG위험", "weight": 0.10},
        ]

        for company in COMPANIES[:5]:  # 주요 5개 기업만
            for cat in categories:
                cat_query = """
                MATCH (c:Company {id: $companyId})
                MERGE (cat:RiskCategory {id: $catId})
                SET cat.name = $catName,
                    cat.score = toInteger(rand() * 50 + 20),
                    cat.weight = $weight
                MERGE (c)-[:HAS_CATEGORY]->(cat)
                """
                neo4j_client.execute_write(cat_query, {
                    "companyId": company["id"],
                    "catId": f"{company['id']}_{cat['name']}",
                    "catName": cat["name"],
                    "weight": cat["weight"]
                })

        logger.info("✅ RiskCategory 노드 생성 완료")

        # 7. Signal 노드 생성 (최근 신호 테스트용)
        signals = [
            {"type": "DART", "title": "분기 실적 공시", "score": 15, "severity": "LOW"},
            {"type": "NEWS", "title": "공급망 관련 뉴스", "score": 25, "severity": "MEDIUM"},
            {"type": "DART", "title": "임원 변경 공시", "score": 10, "severity": "LOW"},
            {"type": "NEWS", "title": "시장 변동성 보도", "score": 35, "severity": "HIGH"},
        ]

        for company in COMPANIES[:5]:  # 주요 5개 기업만
            for idx, sig in enumerate(signals):
                sig_query = """
                MATCH (c:Company {id: $companyId})
                MERGE (s:Signal {id: $sigId})
                SET s.source = $type,
                    s.title = $title,
                    s.score = $score,
                    s.severity = $severity,
                    s.detectedAt = datetime() - duration({days: $dayOffset})
                MERGE (s)-[:DETECTED_IN]->(c)
                """
                neo4j_client.execute_write(sig_query, {
                    "companyId": company["id"],
                    "sigId": f"{company['id']}_sig{idx}",
                    "type": sig["type"],
                    "title": sig["title"],
                    "score": sig["score"],
                    "severity": sig["severity"],
                    "dayOffset": idx
                })

        logger.info("✅ Signal 노드 생성 완료")

        # 8. 검증
        verify_query = """
        MATCH (c:Company)
        OPTIONAL MATCH (c)-[r:SUPPLIES_TO]->()
        RETURN count(DISTINCT c) as companies, count(r) as relations
        """
        result = neo4j_client.execute_read_single(verify_query)

        logger.info(f"""
╔════════════════════════════════════════════════╗
║  Supply Chain 데이터 로드 완료                    ║
╠════════════════════════════════════════════════╣
║  Company 노드: {result['companies']} 개                       ║
║  SUPPLIES_TO 관계: {result['relations']} 개                   ║
╚════════════════════════════════════════════════╝
        """)

        return True

    except Exception as e:
        logger.error(f"데이터 로드 실패: {e}")
        return False
    finally:
        neo4j_client.close()


def get_supply_chain_for_company(company_id: str) -> dict:
    """특정 기업의 공급망 데이터 조회"""
    try:
        from risk_engine.neo4j_client import neo4j_client
    except ImportError:
        return get_mock_supply_chain(company_id)

    try:
        neo4j_client.connect()

        query = """
        // 중심 기업
        MATCH (center:Company {id: $companyId})

        // 공급사 (center로 공급하는 기업)
        OPTIONAL MATCH (supplier:Company)-[sr:SUPPLIES_TO]->(center)

        // 고객사 (center가 공급하는 기업)
        OPTIONAL MATCH (center)-[cr:SUPPLIES_TO]->(customer:Company)

        // 경쟁사
        OPTIONAL MATCH (center)-[:COMPETES_WITH]-(competitor:Company)

        RETURN center,
               collect(DISTINCT {
                   node: supplier,
                   rel: sr
               }) as suppliers,
               collect(DISTINCT {
                   node: customer,
                   rel: cr
               }) as customers,
               collect(DISTINCT competitor) as competitors
        """

        result = neo4j_client.execute_read_single(query, {"companyId": company_id})

        if not result:
            return get_mock_supply_chain(company_id)

        # 노드 변환
        nodes = []
        edges = []

        # 중심 노드
        center = result["center"]
        center_node = {
            "id": center["id"],
            "name": center["name"],
            "type": "company",
            "riskScore": center.get("totalRiskScore", 50),
            "sector": center.get("sector", "")
        }
        nodes.append(center_node)

        # 공급사 노드
        for item in result.get("suppliers", []):
            node = item.get("node")
            rel = item.get("rel")
            if node and node.get("id"):
                nodes.append({
                    "id": node["id"],
                    "name": node["name"],
                    "type": "supplier",
                    "riskScore": node.get("totalRiskScore", 50),
                    "sector": node.get("sector", "")
                })
                edges.append({
                    "id": f"e_{node['id']}_{center['id']}",
                    "source": node["id"],
                    "target": center["id"],
                    "relationship": "SUPPLIES_TO",
                    "dependency": rel.get("dependency", 0.3) if rel else 0.3,
                    "riskTransfer": rel.get("riskTransfer", 0.1) if rel else 0.1
                })

        # 고객사 노드
        for item in result.get("customers", []):
            node = item.get("node")
            rel = item.get("rel")
            if node and node.get("id"):
                # 중복 체크
                if not any(n["id"] == node["id"] for n in nodes):
                    nodes.append({
                        "id": node["id"],
                        "name": node["name"],
                        "type": "customer",
                        "riskScore": node.get("totalRiskScore", 50),
                        "sector": node.get("sector", "")
                    })
                edges.append({
                    "id": f"e_{center['id']}_{node['id']}",
                    "source": center["id"],
                    "target": node["id"],
                    "relationship": "SUPPLIES_TO",
                    "dependency": rel.get("dependency", 0.3) if rel else 0.3,
                    "riskTransfer": rel.get("riskTransfer", 0.1) if rel else 0.1
                })

        # 경쟁사 노드
        for comp in result.get("competitors", []):
            if comp and comp.get("id"):
                if not any(n["id"] == comp["id"] for n in nodes):
                    nodes.append({
                        "id": comp["id"],
                        "name": comp["name"],
                        "type": "competitor",
                        "riskScore": comp.get("totalRiskScore", 50),
                        "sector": comp.get("sector", "")
                    })
                edges.append({
                    "id": f"e_comp_{center['id']}_{comp['id']}",
                    "source": center["id"],
                    "target": comp["id"],
                    "relationship": "COMPETES_WITH",
                    "dependency": 0,
                    "riskTransfer": 0
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "centerNode": center_node,
            "totalPropagatedRisk": sum(e.get("riskTransfer", 0) * 100 for e in edges if e["target"] == center["id"])
        }

    except Exception as e:
        logger.error(f"공급망 조회 실패: {e}")
        return get_mock_supply_chain(company_id)
    finally:
        neo4j_client.close()


def get_mock_supply_chain(company_id: str = "sk_hynix") -> dict:
    """Mock 공급망 데이터"""
    company_name = {
        "sk_hynix": "SK하이닉스",
        "samsung_elec": "삼성전자",
        "lg_energy": "LG에너지솔루션",
        "hyundai_motor": "현대자동차",
        "hanmi_semi": "한미반도체",
        "deal1": "SK하이닉스",
        "deal2": "한미반도체",
        "deal3": "삼성전자",
    }.get(company_id, "SK하이닉스")

    return {
        "nodes": [
            {"id": company_id, "name": company_name, "type": "company", "riskScore": 58, "sector": "반도체"},
            {"id": "hanmi_semi", "name": "한미반도체", "type": "supplier", "riskScore": 78, "sector": "반도체장비"},
            {"id": "asml", "name": "ASML", "type": "supplier", "riskScore": 25, "sector": "반도체장비"},
            {"id": "sk_materials", "name": "SK머티리얼즈", "type": "supplier", "riskScore": 45, "sector": "소재"},
            {"id": "apple", "name": "Apple", "type": "customer", "riskScore": 22, "sector": "IT"},
            {"id": "nvidia", "name": "NVIDIA", "type": "customer", "riskScore": 18, "sector": "반도체"},
            {"id": "samsung_elec", "name": "삼성전자", "type": "competitor", "riskScore": 35, "sector": "전자"},
        ],
        "edges": [
            {"id": "e1", "source": "hanmi_semi", "target": company_id, "relationship": "SUPPLIES_TO", "dependency": 0.5, "riskTransfer": 0.39},
            {"id": "e2", "source": "asml", "target": company_id, "relationship": "SUPPLIES_TO", "dependency": 0.3, "riskTransfer": 0.075},
            {"id": "e3", "source": "sk_materials", "target": company_id, "relationship": "SUPPLIES_TO", "dependency": 0.45, "riskTransfer": 0.2},
            {"id": "e4", "source": company_id, "target": "apple", "relationship": "SUPPLIES_TO", "dependency": 0.4, "riskTransfer": 0.23},
            {"id": "e5", "source": company_id, "target": "nvidia", "relationship": "SUPPLIES_TO", "dependency": 0.35, "riskTransfer": 0.2},
            {"id": "e6", "source": company_id, "target": "samsung_elec", "relationship": "COMPETES_WITH", "dependency": 0, "riskTransfer": 0},
        ],
        "centerNode": {"id": company_id, "name": company_name, "type": "company", "riskScore": 58},
        "totalPropagatedRisk": 66
    }


if __name__ == "__main__":
    load_supply_chain_data()
