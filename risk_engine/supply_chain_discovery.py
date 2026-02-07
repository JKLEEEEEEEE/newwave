"""
============================================================================
Supply Chain 자동 탐색 모듈
============================================================================
DART 공시 및 뉴스에서 공급망 관계를 자동 추출하여 Neo4j에 저장합니다.

주요 기능:
1. DART 공시에서 주요주주/자회사/관계사 추출
2. 뉴스 공동 언급에서 거래 관계 추론
3. 산업 분류 기반 공급망 매핑
4. Neo4j 그래프 자동 확장
"""

import os
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# 산업별 공급망 매핑 (한국 산업 기준)
# =============================================================================

INDUSTRY_SUPPLY_CHAINS = {
    # 반도체 산업
    "반도체": {
        "suppliers": ["반도체장비", "소재", "화학", "가스"],
        "customers": ["전자", "IT", "자동차", "가전"],
        "competitors": ["반도체"],
    },
    "반도체장비": {
        "suppliers": ["정밀기계", "광학", "소재"],
        "customers": ["반도체"],
        "competitors": ["반도체장비"],
    },

    # 자동차 산업
    "자동차": {
        "suppliers": ["자동차부품", "배터리", "철강", "타이어", "전자", "소재"],
        "customers": [],  # 최종 소비자
        "competitors": ["자동차"],
    },
    "자동차부품": {
        "suppliers": ["철강", "소재", "전자", "플라스틱"],
        "customers": ["자동차"],
        "competitors": ["자동차부품"],
    },

    # 배터리/에너지 산업
    "배터리": {
        "suppliers": ["화학", "소재", "광물"],
        "customers": ["자동차", "전자", "에너지"],
        "competitors": ["배터리"],
    },

    # 전자/IT 산업
    "전자": {
        "suppliers": ["반도체", "디스플레이", "부품", "소재"],
        "customers": ["IT", "통신", "가전"],
        "competitors": ["전자"],
    },
    "IT": {
        "suppliers": ["반도체", "전자", "소프트웨어"],
        "customers": [],
        "competitors": ["IT"],
    },

    # 철강/소재 산업
    "철강": {
        "suppliers": ["광물", "에너지"],
        "customers": ["자동차", "조선", "건설", "기계"],
        "competitors": ["철강"],
    },
    "화학": {
        "suppliers": ["석유", "가스"],
        "customers": ["반도체", "배터리", "제약", "플라스틱"],
        "competitors": ["화학"],
    },
    "소재": {
        "suppliers": ["화학", "광물"],
        "customers": ["반도체", "배터리", "전자"],
        "competitors": ["소재"],
    },
}

# 주요 한국 기업 데이터베이스 (corpCode 포함)
MAJOR_KOREAN_COMPANIES = {
    # 반도체
    "SK하이닉스": {"sector": "반도체", "corpCode": "00126380", "aliases": ["SK Hynix", "하이닉스"]},
    "삼성전자": {"sector": "전자", "corpCode": "00126308", "aliases": ["Samsung Electronics", "삼전"]},
    "DB하이텍": {"sector": "반도체", "corpCode": "00149007", "aliases": ["DB HiTek"]},
    "SK실트론": {"sector": "소재", "corpCode": "00820852", "aliases": []},
    "원익IPS": {"sector": "반도체장비", "corpCode": "00545929", "aliases": []},
    "주성엔지니어링": {"sector": "반도체장비", "corpCode": "00425656", "aliases": []},
    "한미반도체": {"sector": "반도체장비", "corpCode": "00156225", "aliases": []},
    "리노공업": {"sector": "반도체장비", "corpCode": "00453693", "aliases": []},
    "테스": {"sector": "반도체장비", "corpCode": "00520315", "aliases": []},
    "피에스케이": {"sector": "반도체장비", "corpCode": "00515668", "aliases": ["PSK"]},

    # 자동차
    "현대자동차": {"sector": "자동차", "corpCode": "00164742", "aliases": ["현대차", "Hyundai Motor"]},
    "기아": {"sector": "자동차", "corpCode": "00164779", "aliases": ["Kia Motors", "기아차"]},
    "현대모비스": {"sector": "자동차부품", "corpCode": "00164788", "aliases": ["Hyundai Mobis"]},
    "현대트랜시스": {"sector": "자동차부품", "corpCode": "00423883", "aliases": []},
    "만도": {"sector": "자동차부품", "corpCode": "00164940", "aliases": ["Mando"]},
    "현대위아": {"sector": "자동차부품", "corpCode": "00164797", "aliases": []},
    "한온시스템": {"sector": "자동차부품", "corpCode": "00396721", "aliases": ["Hanon Systems"]},
    "현대제철": {"sector": "철강", "corpCode": "00164806", "aliases": []},

    # 배터리
    "LG에너지솔루션": {"sector": "배터리", "corpCode": "00401731", "aliases": ["LGES", "LG Energy"]},
    "삼성SDI": {"sector": "배터리", "corpCode": "00126362", "aliases": ["Samsung SDI"]},
    "SK온": {"sector": "배터리", "corpCode": "01666174", "aliases": ["SK On"]},
    "에코프로비엠": {"sector": "배터리", "corpCode": "00814247", "aliases": ["Ecopro BM"]},
    "포스코퓨처엠": {"sector": "배터리", "corpCode": "00195904", "aliases": ["POSCO Future M"]},
    "엘앤에프": {"sector": "배터리", "corpCode": "00437188", "aliases": ["L&F"]},

    # 화학/소재
    "LG화학": {"sector": "화학", "corpCode": "00356361", "aliases": ["LG Chem"]},
    "SK머티리얼즈": {"sector": "소재", "corpCode": "00628177", "aliases": ["SK Materials"]},
    "동우화인켐": {"sector": "화학", "corpCode": "00431449", "aliases": []},
    "솔브레인": {"sector": "화학", "corpCode": "00493665", "aliases": ["Soulbrain"]},
    "SK이노베이션": {"sector": "화학", "corpCode": "00631518", "aliases": ["SK Innovation"]},
    "롯데케미칼": {"sector": "화학", "corpCode": "00184855", "aliases": ["Lotte Chemical"]},

    # 철강
    "포스코홀딩스": {"sector": "철강", "corpCode": "00181093", "aliases": ["POSCO Holdings", "포스코"]},
    "현대제철": {"sector": "철강", "corpCode": "00164806", "aliases": []},
    "동국제강": {"sector": "철강", "corpCode": "00182038", "aliases": []},

    # IT/소프트웨어
    "네이버": {"sector": "IT", "corpCode": "00466603", "aliases": ["Naver"]},
    "카카오": {"sector": "IT", "corpCode": "00583838", "aliases": ["Kakao"]},
    "삼성SDS": {"sector": "IT", "corpCode": "00625989", "aliases": ["Samsung SDS"]},
    "NHN": {"sector": "IT", "corpCode": "00497767", "aliases": []},

    # 디스플레이
    "삼성디스플레이": {"sector": "디스플레이", "corpCode": "00774188", "aliases": ["Samsung Display"]},
    "LG디스플레이": {"sector": "디스플레이", "corpCode": "00401725", "aliases": ["LG Display", "LGD"]},

    # 조선
    "HD한국조선해양": {"sector": "조선", "corpCode": "00164815", "aliases": ["한국조선해양", "KSOE"]},
    "삼성중공업": {"sector": "조선", "corpCode": "00126353", "aliases": ["Samsung Heavy"]},
    "대우조선해양": {"sector": "조선", "corpCode": "00164824", "aliases": ["DSME"]},

    # 건설
    "삼성물산": {"sector": "건설", "corpCode": "00149520", "aliases": ["Samsung C&T"]},
    "현대건설": {"sector": "건설", "corpCode": "00185095", "aliases": ["Hyundai E&C"]},
    "대우건설": {"sector": "건설", "corpCode": "00184558", "aliases": []},
    "GS건설": {"sector": "건설", "corpCode": "00184810", "aliases": []},

    # 금융
    "KB금융": {"sector": "금융", "corpCode": "00685539", "aliases": ["KB Financial"]},
    "신한금융": {"sector": "금융", "corpCode": "00685548", "aliases": ["Shinhan Financial"]},
    "하나금융": {"sector": "금융", "corpCode": "00685566", "aliases": ["Hana Financial"]},
    "우리금융": {"sector": "금융", "corpCode": "00823124", "aliases": ["Woori Financial"]},
}

# 글로벌 파트너 기업
GLOBAL_PARTNERS = {
    # 반도체 장비
    "ASML": {"sector": "반도체장비", "country": "NL", "supplies_to": ["삼성전자", "SK하이닉스"]},
    "Applied Materials": {"sector": "반도체장비", "country": "US", "supplies_to": ["삼성전자", "SK하이닉스"]},
    "Lam Research": {"sector": "반도체장비", "country": "US", "supplies_to": ["삼성전자", "SK하이닉스"]},
    "Tokyo Electron": {"sector": "반도체장비", "country": "JP", "supplies_to": ["삼성전자", "SK하이닉스"]},
    "KLA": {"sector": "반도체장비", "country": "US", "supplies_to": ["삼성전자", "SK하이닉스"]},

    # 반도체 고객
    "Apple": {"sector": "IT", "country": "US", "buys_from": ["삼성전자", "SK하이닉스", "LG디스플레이"]},
    "NVIDIA": {"sector": "반도체", "country": "US", "buys_from": ["삼성전자", "SK하이닉스"]},
    "AMD": {"sector": "반도체", "country": "US", "buys_from": ["삼성전자"]},
    "Qualcomm": {"sector": "반도체", "country": "US", "buys_from": ["삼성전자"]},
    "Intel": {"sector": "반도체", "country": "US", "buys_from": ["삼성전자"]},
    "Microsoft": {"sector": "IT", "country": "US", "buys_from": ["삼성전자", "SK하이닉스"]},
    "Google": {"sector": "IT", "country": "US", "buys_from": ["삼성전자", "SK하이닉스"]},
    "Amazon": {"sector": "IT", "country": "US", "buys_from": ["삼성전자", "SK하이닉스"]},
    "Meta": {"sector": "IT", "country": "US", "buys_from": ["삼성전자"]},

    # 자동차 고객
    "Tesla": {"sector": "자동차", "country": "US", "buys_from": ["LG에너지솔루션", "삼성SDI"]},
    "Volkswagen": {"sector": "자동차", "country": "DE", "buys_from": ["LG에너지솔루션", "삼성SDI", "SK온"]},
    "BMW": {"sector": "자동차", "country": "DE", "buys_from": ["삼성SDI"]},
    "Mercedes-Benz": {"sector": "자동차", "country": "DE", "buys_from": ["삼성SDI", "SK온"]},
    "Ford": {"sector": "자동차", "country": "US", "buys_from": ["LG에너지솔루션", "SK온"]},
    "GM": {"sector": "자동차", "country": "US", "buys_from": ["LG에너지솔루션"]},
    "Stellantis": {"sector": "자동차", "country": "NL", "buys_from": ["LG에너지솔루션", "삼성SDI"]},
    "Rivian": {"sector": "자동차", "country": "US", "buys_from": ["삼성SDI"]},
    "Toyota": {"sector": "자동차", "country": "JP", "buys_from": []},
    "Honda": {"sector": "자동차", "country": "JP", "buys_from": []},
}


@dataclass
class CompanyRelation:
    """기업 간 관계"""
    source: str
    target: str
    relation_type: str  # SUPPLIES_TO, COMPETES_WITH, SUBSIDIARY_OF, PARTNER_OF
    dependency: float = 0.3  # 의존도 (0-1)
    confidence: float = 0.5  # 신뢰도
    source_info: str = ""  # 관계 출처 (DART, NEWS, INDUSTRY)
    discovered_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "dependency": self.dependency,
            "confidence": self.confidence,
            "source_info": self.source_info,
            "discovered_at": self.discovered_at.isoformat(),
        }


class SupplyChainDiscovery:
    """공급망 자동 탐색 서비스"""

    def __init__(self, neo4j_client=None, dart_collector=None, news_collector=None):
        self.neo4j_client = neo4j_client
        self.dart_collector = dart_collector
        self.news_collector = news_collector
        self.discovered_relations: List[CompanyRelation] = []

    def discover_all(self, target_companies: List[str] = None) -> List[CompanyRelation]:
        """
        모든 방법으로 공급망 관계 탐색

        Args:
            target_companies: 탐색 대상 기업 목록 (None이면 전체)

        Returns:
            발견된 관계 목록
        """
        if target_companies is None:
            target_companies = list(MAJOR_KOREAN_COMPANIES.keys())

        relations = []

        # 1. 산업 기반 관계 추론
        logger.info("1단계: 산업 기반 공급망 매핑...")
        relations.extend(self.discover_from_industry(target_companies))

        # 2. 글로벌 파트너 관계
        logger.info("2단계: 글로벌 파트너 관계 매핑...")
        relations.extend(self.discover_global_partners())

        # 3. DART 공시 기반 관계 (API 키 있을 때)
        if self.dart_collector:
            logger.info("3단계: DART 공시 분석...")
            relations.extend(self.discover_from_dart(target_companies))

        # 4. 뉴스 공동 언급 기반 관계
        if self.news_collector:
            logger.info("4단계: 뉴스 공동 언급 분석...")
            relations.extend(self.discover_from_news(target_companies))

        # 중복 제거
        unique_relations = self._deduplicate_relations(relations)
        self.discovered_relations = unique_relations

        logger.info(f"✅ 총 {len(unique_relations)}개 관계 발견")
        return unique_relations

    def discover_from_industry(self, companies: List[str]) -> List[CompanyRelation]:
        """산업 분류 기반 공급망 관계 추론"""
        relations = []

        for company in companies:
            if company not in MAJOR_KOREAN_COMPANIES:
                continue

            info = MAJOR_KOREAN_COMPANIES[company]
            sector = info["sector"]

            if sector not in INDUSTRY_SUPPLY_CHAINS:
                continue

            chain = INDUSTRY_SUPPLY_CHAINS[sector]

            # 공급사 관계 찾기
            for supplier_sector in chain["suppliers"]:
                for other_company, other_info in MAJOR_KOREAN_COMPANIES.items():
                    if other_company == company:
                        continue
                    if other_info["sector"] == supplier_sector:
                        relations.append(CompanyRelation(
                            source=other_company,
                            target=company,
                            relation_type="SUPPLIES_TO",
                            dependency=0.25,
                            confidence=0.6,
                            source_info="INDUSTRY_MAPPING"
                        ))

            # 고객사 관계 찾기
            for customer_sector in chain["customers"]:
                for other_company, other_info in MAJOR_KOREAN_COMPANIES.items():
                    if other_company == company:
                        continue
                    if other_info["sector"] == customer_sector:
                        relations.append(CompanyRelation(
                            source=company,
                            target=other_company,
                            relation_type="SUPPLIES_TO",
                            dependency=0.25,
                            confidence=0.6,
                            source_info="INDUSTRY_MAPPING"
                        ))

            # 경쟁사 관계 찾기
            for other_company, other_info in MAJOR_KOREAN_COMPANIES.items():
                if other_company == company:
                    continue
                if other_info["sector"] == sector:
                    # 중복 방지: 알파벳 순서로 한 방향만
                    if company < other_company:
                        relations.append(CompanyRelation(
                            source=company,
                            target=other_company,
                            relation_type="COMPETES_WITH",
                            dependency=0.0,
                            confidence=0.8,
                            source_info="SAME_SECTOR"
                        ))

        return relations

    def discover_global_partners(self) -> List[CompanyRelation]:
        """글로벌 파트너 관계 매핑"""
        relations = []

        for partner, info in GLOBAL_PARTNERS.items():
            # 공급 관계
            for target in info.get("supplies_to", []):
                relations.append(CompanyRelation(
                    source=partner,
                    target=target,
                    relation_type="SUPPLIES_TO",
                    dependency=0.35,
                    confidence=0.85,
                    source_info="KNOWN_PARTNERSHIP"
                ))

            # 구매 관계
            for source in info.get("buys_from", []):
                relations.append(CompanyRelation(
                    source=source,
                    target=partner,
                    relation_type="SUPPLIES_TO",
                    dependency=0.30,
                    confidence=0.85,
                    source_info="KNOWN_PARTNERSHIP"
                ))

        return relations

    def discover_from_dart(self, companies: List[str]) -> List[CompanyRelation]:
        """DART 공시에서 관계 추출"""
        relations = []

        if not self.dart_collector:
            return relations

        # 관계 키워드 패턴
        patterns = {
            "SUBSIDIARY_OF": [
                r"자회사.*?([가-힣]+(?:주식회사|㈜)?)",
                r"계열사.*?([가-힣]+(?:주식회사|㈜)?)",
                r"종속회사.*?([가-힣]+(?:주식회사|㈜)?)",
            ],
            "PARTNER_OF": [
                r"합작.*?([가-힣]+(?:주식회사|㈜)?)",
                r"제휴.*?([가-힣]+(?:주식회사|㈜)?)",
                r"협력.*?([가-힣]+(?:주식회사|㈜)?)",
            ],
            "SUPPLIES_TO": [
                r"납품.*?([가-힣]+(?:주식회사|㈜)?)",
                r"공급계약.*?([가-힣]+(?:주식회사|㈜)?)",
            ],
        }

        for company in companies[:10]:  # 상위 10개만 (API 제한)
            if company not in MAJOR_KOREAN_COMPANIES:
                continue

            corp_code = MAJOR_KOREAN_COMPANIES[company].get("corpCode")
            if not corp_code:
                continue

            try:
                result = self.dart_collector.collect_disclosures(corp_code, days=90)

                for disclosure in result.disclosures:
                    title = disclosure.title

                    for rel_type, regex_list in patterns.items():
                        for pattern in regex_list:
                            matches = re.findall(pattern, title)
                            for match in matches:
                                # 매칭된 기업이 우리 DB에 있는지 확인
                                matched_company = self._find_company_by_name(match)
                                if matched_company and matched_company != company:
                                    relations.append(CompanyRelation(
                                        source=company if rel_type != "SUBSIDIARY_OF" else matched_company,
                                        target=matched_company if rel_type != "SUBSIDIARY_OF" else company,
                                        relation_type=rel_type,
                                        dependency=0.4,
                                        confidence=0.75,
                                        source_info=f"DART:{disclosure.rcept_no}"
                                    ))
            except Exception as e:
                logger.warning(f"DART 수집 실패 ({company}): {e}")

        return relations

    def discover_from_news(self, companies: List[str]) -> List[CompanyRelation]:
        """뉴스 공동 언급에서 관계 추론"""
        relations = []

        if not self.news_collector:
            return relations

        # 공동 언급 카운트
        co_mentions: Dict[Tuple[str, str], int] = {}

        for company in companies[:10]:  # 상위 10개만
            try:
                result = self.news_collector.collect_news(company, limit=20)

                for news in result.news_list:
                    title = news.title

                    # 다른 기업 언급 확인
                    for other_company in companies:
                        if other_company == company:
                            continue

                        # 기업명 또는 별칭이 제목에 포함되어 있는지 확인
                        other_info = MAJOR_KOREAN_COMPANIES.get(other_company, {})
                        aliases = other_info.get("aliases", []) + [other_company]

                        for alias in aliases:
                            if alias in title:
                                key = tuple(sorted([company, other_company]))
                                co_mentions[key] = co_mentions.get(key, 0) + 1
                                break
            except Exception as e:
                logger.warning(f"뉴스 수집 실패 ({company}): {e}")

        # 공동 언급이 3회 이상이면 관계로 추론
        for (comp1, comp2), count in co_mentions.items():
            if count >= 3:
                # 같은 산업이면 경쟁, 다른 산업이면 파트너/공급 관계
                sector1 = MAJOR_KOREAN_COMPANIES.get(comp1, {}).get("sector", "")
                sector2 = MAJOR_KOREAN_COMPANIES.get(comp2, {}).get("sector", "")

                if sector1 == sector2:
                    rel_type = "COMPETES_WITH"
                else:
                    rel_type = "PARTNER_OF"

                relations.append(CompanyRelation(
                    source=comp1,
                    target=comp2,
                    relation_type=rel_type,
                    dependency=0.2,
                    confidence=min(0.5 + count * 0.1, 0.9),
                    source_info=f"NEWS_CO_MENTION:{count}"
                ))

        return relations

    def _find_company_by_name(self, name: str) -> Optional[str]:
        """이름으로 기업 찾기"""
        # 정규화
        name = name.replace("주식회사", "").replace("㈜", "").strip()

        # 정확한 매칭
        if name in MAJOR_KOREAN_COMPANIES:
            return name

        # 별칭 매칭
        for company, info in MAJOR_KOREAN_COMPANIES.items():
            if name in info.get("aliases", []):
                return company
            if name in company:
                return company

        return None

    def _deduplicate_relations(self, relations: List[CompanyRelation]) -> List[CompanyRelation]:
        """중복 관계 제거 (더 높은 confidence 유지)"""
        seen: Dict[str, CompanyRelation] = {}

        for rel in relations:
            key = f"{rel.source}:{rel.target}:{rel.relation_type}"

            if key not in seen or seen[key].confidence < rel.confidence:
                seen[key] = rel

        return list(seen.values())

    def save_to_neo4j(self) -> int:
        """발견된 관계를 Neo4j에 저장"""
        if not self.neo4j_client:
            logger.warning("Neo4j 클라이언트가 설정되지 않았습니다")
            return 0

        saved = 0

        # 1. 먼저 모든 기업 노드 생성
        for company, info in MAJOR_KOREAN_COMPANIES.items():
            try:
                query = """
                MERGE (c:Company {id: $id})
                SET c.name = $name,
                    c.sector = $sector,
                    c.corpCode = $corpCode,
                    c.totalRiskScore = coalesce(c.totalRiskScore, toInteger(rand() * 50 + 20)),
                    c.directRiskScore = coalesce(c.directRiskScore, toInteger(rand() * 40 + 15)),
                    c.propagatedRiskScore = coalesce(c.propagatedRiskScore, toInteger(rand() * 15 + 5)),
                    c.status = CASE
                        WHEN c.totalRiskScore >= 75 THEN 'FAIL'
                        WHEN c.totalRiskScore >= 50 THEN 'WARNING'
                        ELSE 'PASS'
                    END,
                    c.updatedAt = datetime()
                """
                self.neo4j_client.execute_write(query, {
                    "id": company,
                    "name": company,
                    "sector": info["sector"],
                    "corpCode": info.get("corpCode", ""),
                })
            except Exception as e:
                logger.warning(f"기업 노드 생성 실패 ({company}): {e}")

        # 글로벌 파트너 노드 생성
        for partner, info in GLOBAL_PARTNERS.items():
            try:
                query = """
                MERGE (c:Company {id: $id})
                SET c.name = $name,
                    c.sector = $sector,
                    c.country = $country,
                    c.isGlobal = true,
                    c.totalRiskScore = coalesce(c.totalRiskScore, toInteger(rand() * 30 + 10)),
                    c.status = 'PASS',
                    c.updatedAt = datetime()
                """
                self.neo4j_client.execute_write(query, {
                    "id": partner,
                    "name": partner,
                    "sector": info["sector"],
                    "country": info.get("country", ""),
                })
            except Exception as e:
                logger.warning(f"글로벌 파트너 노드 생성 실패 ({partner}): {e}")

        # 2. 관계 생성
        for rel in self.discovered_relations:
            try:
                if rel.relation_type == "SUPPLIES_TO":
                    query = """
                    MATCH (from:Company {id: $fromId})
                    MATCH (to:Company {id: $toId})
                    MERGE (from)-[r:SUPPLIES_TO]->(to)
                    SET r.dependency = $dependency,
                        r.confidence = $confidence,
                        r.sourceInfo = $sourceInfo,
                        r.riskTransfer = $dependency * from.totalRiskScore / 100.0,
                        r.updatedAt = datetime()
                    """
                elif rel.relation_type == "COMPETES_WITH":
                    query = """
                    MATCH (from:Company {id: $fromId})
                    MATCH (to:Company {id: $toId})
                    MERGE (from)-[r:COMPETES_WITH]->(to)
                    SET r.confidence = $confidence,
                        r.sourceInfo = $sourceInfo,
                        r.updatedAt = datetime()
                    """
                elif rel.relation_type == "SUBSIDIARY_OF":
                    query = """
                    MATCH (from:Company {id: $fromId})
                    MATCH (to:Company {id: $toId})
                    MERGE (from)-[r:SUBSIDIARY_OF]->(to)
                    SET r.confidence = $confidence,
                        r.sourceInfo = $sourceInfo,
                        r.updatedAt = datetime()
                    """
                else:  # PARTNER_OF
                    query = """
                    MATCH (from:Company {id: $fromId})
                    MATCH (to:Company {id: $toId})
                    MERGE (from)-[r:PARTNER_OF]->(to)
                    SET r.confidence = $confidence,
                        r.sourceInfo = $sourceInfo,
                        r.updatedAt = datetime()
                    """

                self.neo4j_client.execute_write(query, {
                    "fromId": rel.source,
                    "toId": rel.target,
                    "dependency": rel.dependency,
                    "confidence": rel.confidence,
                    "sourceInfo": rel.source_info,
                })
                saved += 1
            except Exception as e:
                logger.warning(f"관계 저장 실패 ({rel.source} -> {rel.target}): {e}")

        logger.info(f"✅ {saved}/{len(self.discovered_relations)}개 관계 Neo4j 저장 완료")
        return saved

    def get_statistics(self) -> dict:
        """탐색 통계"""
        by_type = {}
        by_source = {}

        for rel in self.discovered_relations:
            by_type[rel.relation_type] = by_type.get(rel.relation_type, 0) + 1
            source = rel.source_info.split(":")[0]
            by_source[source] = by_source.get(source, 0) + 1

        return {
            "total_relations": len(self.discovered_relations),
            "total_companies": len(MAJOR_KOREAN_COMPANIES) + len(GLOBAL_PARTNERS),
            "korean_companies": len(MAJOR_KOREAN_COMPANIES),
            "global_partners": len(GLOBAL_PARTNERS),
            "by_relation_type": by_type,
            "by_source": by_source,
        }


def run_discovery(neo4j_client=None) -> dict:
    """
    공급망 탐색 실행 (헬퍼 함수)

    Returns:
        탐색 통계
    """
    discovery = SupplyChainDiscovery(neo4j_client=neo4j_client)
    discovery.discover_all()

    if neo4j_client:
        discovery.save_to_neo4j()

    return discovery.get_statistics()


if __name__ == "__main__":
    # 테스트 실행
    logging.basicConfig(level=logging.INFO)

    discovery = SupplyChainDiscovery()
    relations = discovery.discover_all()

    print("\n" + "=" * 60)
    print("Supply Chain Discovery 결과")
    print("=" * 60)

    stats = discovery.get_statistics()
    print(f"\n총 기업 수: {stats['total_companies']}")
    print(f"  - 한국 기업: {stats['korean_companies']}")
    print(f"  - 글로벌 파트너: {stats['global_partners']}")
    print(f"\n총 관계 수: {stats['total_relations']}")

    print("\n관계 유형별:")
    for rel_type, count in stats['by_relation_type'].items():
        print(f"  - {rel_type}: {count}")

    print("\n출처별:")
    for source, count in stats['by_source'].items():
        print(f"  - {source}: {count}")
