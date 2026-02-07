"""
DART 전자공시 데이터 → Neo4j 로드 스크립트
Risk Monitoring System v2.2
"""

import os
import sys
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import requests
import logging

# 상위 디렉토리 추가 (risk_engine import를 위해)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('.env.local')

from risk_engine.neo4j_client import neo4j_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DART API 설정
DART_API_KEY = os.getenv("OPENDART_API_KEY")
DART_BASE_URL = "https://opendart.fss.or.kr/api"


def fetch_corp_code_list() -> List[Dict[str, str]]:
    """DART 기업 코드 목록 조회 (XML ZIP)"""
    url = f"{DART_BASE_URL}/corpCode.xml"
    params = {"crtfc_key": DART_API_KEY}

    logger.info("DART 기업 코드 목록 다운로드 중...")

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()

        # ZIP 파일 압축 해제
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_filename = zf.namelist()[0]
            with zf.open(xml_filename) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

        companies = []
        for item in root.findall('.//list'):
            corp_code = item.findtext('corp_code', '')
            corp_name = item.findtext('corp_name', '')
            stock_code = item.findtext('stock_code', '')
            modify_date = item.findtext('modify_date', '')

            # 상장사만 필터링 (stock_code가 있는 기업)
            if stock_code and stock_code.strip():
                companies.append({
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "modify_date": modify_date
                })

        logger.info(f"상장사 {len(companies)}개 조회 완료")
        return companies

    except Exception as e:
        logger.error(f"기업 코드 목록 조회 실패: {e}")
        return []


def fetch_company_info(corp_code: str) -> Optional[Dict[str, Any]]:
    """개별 기업 상세 정보 조회"""
    url = f"{DART_BASE_URL}/company.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "000":
            return {
                "corp_code": data.get("corp_code"),
                "corp_name": data.get("corp_name"),
                "corp_name_eng": data.get("corp_name_eng"),
                "stock_code": data.get("stock_code"),
                "ceo_nm": data.get("ceo_nm"),
                "corp_cls": data.get("corp_cls"),  # Y: 유가, K: 코스닥, N: 코넥스
                "induty_code": data.get("induty_code"),
                "est_dt": data.get("est_dt"),
                "acc_mt": data.get("acc_mt"),
            }
    except Exception as e:
        logger.error(f"기업 정보 조회 실패 ({corp_code}): {e}")

    return None


def fetch_disclosures(corp_code: str, bgn_de: str = "20250101", end_de: str = "20260205") -> List[Dict[str, Any]]:
    """기업별 공시 목록 조회"""
    url = f"{DART_BASE_URL}/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": 100
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "000":
            return data.get("list", [])
    except Exception as e:
        logger.error(f"공시 목록 조회 실패 ({corp_code}): {e}")

    return []


def classify_sector(induty_code: str, corp_name: str) -> str:
    """업종 코드 → 섹터 분류"""
    # 업종 코드 기반 분류
    sector_map = {
        "26": "반도체",
        "261": "반도체",
        "262": "반도체장비",
        "29": "자동차",
        "30": "자동차부품",
        "35": "전자",
        "64": "금융",
        "65": "보험",
        "41": "건설",
        "47": "유통"
    }

    # 업종 코드 매칭
    for code, sector in sector_map.items():
        if induty_code and induty_code.startswith(code):
            return sector

    # 기업명 기반 추가 분류
    name_keywords = {
        "반도체": "반도체",
        "하이닉스": "반도체",
        "삼성전자": "전자",
        "배터리": "배터리",
        "에너지솔루션": "배터리",
        "자동차": "자동차",
        "현대": "자동차",
        "기아": "자동차",
        "은행": "금융",
        "증권": "금융",
        "건설": "건설"
    }

    for keyword, sector in name_keywords.items():
        if keyword in corp_name:
            return sector

    return "기타"


def calculate_risk_score(disclosures: List[Dict]) -> int:
    """공시 내용 기반 리스크 점수 계산"""
    base_score = 50
    risk_delta = 0

    # 리스크 키워드
    high_risk_keywords = ["횡령", "배임", "소송", "조사", "제재", "워크아웃", "기한이익상실"]
    medium_risk_keywords = ["정정", "지연", "손실", "감소", "하락"]
    positive_keywords = ["증가", "성장", "흑자", "인수"]

    for disc in disclosures[:20]:  # 최근 20건만 분석
        title = disc.get("report_nm", "")

        for kw in high_risk_keywords:
            if kw in title:
                risk_delta += 5

        for kw in medium_risk_keywords:
            if kw in title:
                risk_delta += 2

        for kw in positive_keywords:
            if kw in title:
                risk_delta -= 1

    final_score = max(0, min(100, base_score + risk_delta))
    return final_score


def load_companies_to_neo4j(companies: List[Dict[str, Any]], batch_size: int = 100):
    """기업 데이터 Neo4j 로드"""
    logger.info(f"Neo4j 로드 시작: {len(companies)}개 기업")

    neo4j_client.connect()

    # 배치 처리
    for i in range(0, len(companies), batch_size):
        batch = companies[i:i + batch_size]

        create_query = """
        UNWIND $companies AS company
        MERGE (c:Company {corpCode: company.corp_code})
        SET c.name = company.corp_name,
            c.stockCode = company.stock_code,
            c.sector = company.sector,
            c.totalRiskScore = company.risk_score,
            c.directRiskScore = company.risk_score,
            c.propagatedRiskScore = 0,
            c.status = CASE
                WHEN company.risk_score <= 40 THEN 'PASS'
                WHEN company.risk_score <= 70 THEN 'WARNING'
                ELSE 'FAIL'
            END,
            c.updatedAt = datetime()
        """

        result = neo4j_client.execute_write(create_query, {"companies": batch})
        logger.info(f"배치 {i // batch_size + 1}: {result.get('nodes_created', 0)}개 노드 생성")


def load_disclosures_to_neo4j(corp_code: str, disclosures: List[Dict[str, Any]]):
    """공시 데이터 Neo4j 로드"""
    if not disclosures:
        return

    create_query = """
    MATCH (c:Company {corpCode: $corpCode})
    UNWIND $disclosures AS disc
    MERGE (d:Disclosure {rceptNo: disc.rcept_no})
    SET d.title = disc.report_nm,
        d.date = disc.rcept_dt,
        d.corpName = disc.corp_name,
        d.corpCls = disc.corp_cls
    MERGE (c)-[:HAS_DISCLOSURE]->(d)
    """

    neo4j_client.execute_write(create_query, {
        "corpCode": corp_code,
        "disclosures": disclosures
    })


def create_supply_chain_relationships():
    """공급망 관계 생성 (샘플 데이터 기반)"""
    # 실제로는 기업간 거래 데이터나 산업 분석 데이터 필요
    # 여기서는 샘플 관계 생성
    sample_relationships = [
        ("SK하이닉스", "한미반도체", 0.45, "supplier"),
        ("SK하이닉스", "삼성전자", 0.30, "competitor"),
        ("삼성전자", "애플", 0.35, "customer"),
        ("LG에너지솔루션", "현대자동차", 0.50, "supplier"),
    ]

    for source, target, dependency, rel_type in sample_relationships:
        if rel_type == "supplier":
            query = """
            MATCH (s:Company {name: $source}), (t:Company {name: $target})
            MERGE (s)-[r:SUPPLIES_TO]->(t)
            SET r.dependency = $dependency
            """
        elif rel_type == "competitor":
            query = """
            MATCH (s:Company {name: $source}), (t:Company {name: $target})
            MERGE (s)-[r:COMPETES_WITH]-(t)
            """
        elif rel_type == "customer":
            query = """
            MATCH (s:Company {name: $source}), (t:Company {name: $target})
            MERGE (s)-[r:SUPPLIES_TO]->(t)
            SET r.dependency = $dependency
            """

        try:
            neo4j_client.execute_write(query, {"source": source, "target": target, "dependency": dependency})
            logger.info(f"관계 생성: {source} -> {target} ({rel_type})")
        except Exception as e:
            logger.error(f"관계 생성 실패: {e}")


def main(limit: int = 50):
    """메인 실행"""
    logger.info("=" * 60)
    logger.info("DART 데이터 → Neo4j 로드 시작")
    logger.info("=" * 60)

    # 1. 기업 코드 목록 조회
    corp_list = fetch_corp_code_list()

    if not corp_list:
        logger.error("기업 목록 조회 실패. 종료.")
        return

    # 상위 N개만 처리 (테스트용)
    corp_list = corp_list[:limit]

    # 2. 기업별 상세 정보 + 공시 조회
    processed_companies = []
    for i, corp in enumerate(corp_list):
        corp_code = corp["corp_code"]
        corp_name = corp["corp_name"]

        logger.info(f"[{i + 1}/{len(corp_list)}] {corp_name} 처리 중...")

        # 상세 정보
        info = fetch_company_info(corp_code)

        # 공시 목록
        disclosures = fetch_disclosures(corp_code)

        # 섹터 분류
        sector = classify_sector(
            info.get("induty_code", "") if info else "",
            corp_name
        )

        # 리스크 점수 계산
        risk_score = calculate_risk_score(disclosures)

        processed_companies.append({
            "corp_code": corp_code,
            "corp_name": corp_name,
            "stock_code": corp.get("stock_code", ""),
            "sector": sector,
            "risk_score": risk_score
        })

        # 공시 데이터도 저장
        if disclosures:
            load_disclosures_to_neo4j(corp_code, disclosures[:10])  # 최근 10건만

    # 3. Neo4j 로드
    load_companies_to_neo4j(processed_companies)

    # 4. 공급망 관계 생성
    create_supply_chain_relationships()

    logger.info("=" * 60)
    logger.info(f"완료! {len(processed_companies)}개 기업 로드됨")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DART 데이터 Neo4j 로드")
    parser.add_argument("--limit", type=int, default=50, help="처리할 기업 수 (기본: 50)")
    args = parser.parse_args()

    main(limit=args.limit)
