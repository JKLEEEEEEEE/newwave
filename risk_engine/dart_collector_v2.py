"""
DART 공시 수집기 v2 (Risk Graph v3)
- 책임: DART API에서 공시 수집, 키워드 매칭, 검증, Neo4j 저장
- 위치: risk_engine/dart_collector_v2.py

Design Doc: docs/02-design/features/risk-graph-v3.design.md Section 3.4
"""

from __future__ import annotations
import os
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Literal
import requests

from .keywords import match_keywords, get_keywords_by_source, MatchResult
from .score_engine import calculate_final_score, ScoreResult
from .validator import DataValidator, ValidationResult

logger = logging.getLogger(__name__)

# =============================================================================
# 상수 정의
# =============================================================================

DART_API_BASE = "https://opendart.fss.or.kr/api"

DART_ENDPOINTS = {
    # DS001: 공시정보
    "corp_code": "corpCode.xml",          # 기업코드 목록 (ZIP)
    "company": "company.json",             # 기업 기본정보
    "disclosure_list": "list.json",        # 공시 목록

    # DS002: 정기보고서 주요정보
    "financials": "fnlttSinglAcnt.json",   # 재무제표 (단일)
    "financials_all": "fnlttMultiAcnt.json",  # 재무제표 (다중)
    "shareholders": "hyslrSttus.json",     # 주주현황
    "executives": "elestock.json",         # 임원현황
    "shareholder_changes": "hyslrChgSttus.json",  # 최대주주 변동현황
    "investments": "otrCprInvstmntSttus.json",    # 타법인 출자현황

    # DS003: 정기보고서 재무정보
    "financial_indices": "fnlttSinglIndx.json",   # 주요 재무지표

    # DS004: 지분공시 종합정보
    "major_stock": "majorstock.json",      # 대량보유 상황보고

    # DS005: 주요사항보고서 (리스크 핵심!)
    "lawsuits": "lwstLg.json",             # 소송
    "default": "dfOcr.json",               # 부도발생
    "business_suspension": "bsnSp.json",   # 영업정지
    "rehabilitation": "ctrcvsBgrq.json",   # 회생절차 개시신청
    "creditor_mgmt": "bnkMngtPcbg.json",  # 채권자관리절차
}

# 보고서 유형 코드
REPORT_CODES = {
    "annual": "11011",      # 사업보고서
    "semi_annual": "11012", # 반기보고서
    "q1": "11013",          # 1분기보고서
    "q3": "11014",          # 3분기보고서
}

# 수집 스케줄 (공시 유형별)
COLLECTION_SCHEDULE = {
    "realtime": ["주요사항보고서", "공정공시", "조회공시"],
    "daily": ["임원·주요주주", "합병", "분할", "특수관계인"],
    "weekly": ["증권발행", "지분변동"],
    "quarterly": ["분기보고서", "반기보고서", "사업보고서"],
}

# 공시 유형 분류
DISCLOSURE_TYPES = {
    "AUDIT": ["감사보고서", "검토보고서", "의견거절", "한정", "부적정"],
    "GOVERNANCE": ["임원", "주요주주", "최대주주", "대표이사", "사임", "해임", "선임"],
    "FINANCE": ["유상증자", "전환사채", "신주인수권", "무상증자", "감자"],
    "RISK": ["소송", "횡령", "배임", "과징금", "제재", "부도", "파산", "회생",
             "주요사항보고서", "공시위반", "불성실공시"],
    "BUSINESS": ["사업보고서", "분기보고서", "반기보고서"],
}

# 루틴 공시 필터 (collect_people에서 이미 상세 수집하므로 스킵)
ROUTINE_FILING_PATTERNS = [
    "임원ㆍ주요주주특정증권등소유상황보고서",
    "임원·주요주주특정증권등소유상황보고서",
]

# 리스크 관련 DART 공시 유형 코드 (pblntf_ty)
# A=정기공시, B=주요사항보고, C=발행공시, D=지분공시, E=기타, F=외부감사, I=거래소, J=공정위
RISK_FILING_TYPES = ['B', 'C', 'F', 'I', 'J']

# 공시유형별 기본 위험 가중치 (키워드 매칭 없어도 부여)
DISCLOSURE_BASE_SCORES = {
    "RISK": 30,       # 소송, 횡령, 주요사항보고서 등
    "AUDIT": 20,      # 감사보고서
    "FINANCE": 15,    # 유상증자, 전환사채 등
    "GOVERNANCE": 5,  # 임원변경 (기본)
    "BUSINESS": 3,    # 정기보고서
    "OTHER": 0,
}


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class DisclosureData:
    """DART 공시 데이터"""
    # 필수 필드
    rcept_no: str                          # 접수번호 (PK)
    corp_code: str                         # 기업코드
    corp_name: str                         # 기업명
    title: str                             # 공시 제목
    filing_date: str                       # 공시일 (YYYYMMDD)

    # 분석 결과
    match_result: MatchResult | None = None
    score_result: ScoreResult | None = None
    category: str | None = None
    disclosure_type: str | None = None

    # 메타데이터
    source: str = "DART"
    source_url: str | None = None
    fetched_at: datetime | None = None
    confidence: float = 0.95               # DART는 높은 신뢰도

    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.now()
        if self.source_url is None:
            self.source_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={self.rcept_no}"

    @property
    def id(self) -> str:
        """고유 ID 생성"""
        return f"DISC_{self.rcept_no}"

    @property
    def url_hash(self) -> str:
        """URL 해시"""
        return hashlib.md5(self.source_url.encode()).hexdigest()

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "rcept_no": self.rcept_no,
            "corp_code": self.corp_code,
            "corp_name": self.corp_name,
            "title": self.title,
            "filing_date": self.filing_date,
            "category": self.category,
            "disclosure_type": self.disclosure_type,
            "source": self.source,
            "source_url": self.source_url,
            "url_hash": self.url_hash,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "confidence": self.confidence,
            "matched_keywords": self.match_result.to_dict() if self.match_result else None,
            "score": self.score_result.to_dict() if self.score_result else None,
        }

    def to_neo4j_props(self) -> dict:
        """Neo4j 노드 속성으로 변환"""
        props = {
            "id": self.id,
            "rceptNo": self.rcept_no,
            "corpCode": self.corp_code,
            "corpName": self.corp_name,
            "title": self.title,
            "filingDate": self.filing_date,
            "category": self.category,
            "disclosureType": self.disclosure_type,
            "source": self.source,
            "sourceUrl": self.source_url,
            "urlHash": self.url_hash,
            "confidence": self.confidence,
        }

        if self.match_result:
            props["matchedKeywords"] = [kw.keyword for kw in self.match_result.matched_keywords]
            props["rawScore"] = self.match_result.raw_score
            props["keywordCount"] = self.match_result.keyword_count

        if self.score_result:
            props["decayedScore"] = self.score_result.decayed_score
            props["finalScore"] = self.score_result.final_score
            props["status"] = self.score_result.status
            props["daysOld"] = self.score_result.days_old

        return props


@dataclass
class CollectionResult:
    """수집 결과"""
    total_fetched: int = 0
    total_analyzed: int = 0
    total_valid: int = 0
    total_saved: int = 0
    high_risk_count: int = 0              # 고위험 공시 수
    disclosures: list[DisclosureData] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "total_fetched": self.total_fetched,
            "total_analyzed": self.total_analyzed,
            "total_valid": self.total_valid,
            "total_saved": self.total_saved,
            "high_risk_count": self.high_risk_count,
            "error_count": len(self.errors),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds() if self.completed_at else None,
        }


# =============================================================================
# DART 수집기 클래스
# =============================================================================

class DartCollectorV2:
    """DART 공시 수집기 v2"""

    # 5-Node 스키마: CategoryType → RiskCategory.code 매핑
    CAT_CODE_MAP = {
        "LEGAL": "LEGAL", "CREDIT": "CREDIT", "GOVERNANCE": "GOV",
        "OPERATIONAL": "OPS", "AUDIT": "AUDIT", "ESG": "ESG",
        "CAPITAL": "SHARE", "SUPPLY": "SUPPLY", "OTHER": "OTHER",
    }

    # 공시유형 → RiskCategory.code 매핑 (키워드 매칭 실패 시 fallback)
    DISCLOSURE_TYPE_TO_CAT = {
        "AUDIT": "AUDIT", "GOVERNANCE": "GOV", "FINANCE": "SHARE",
        "RISK": "LEGAL", "BUSINESS": "OTHER", "OTHER": "OTHER",
    }

    def __init__(self, api_key: str | None = None, neo4j_client=None):
        """
        Args:
            api_key: DART API 키 (None이면 환경변수에서 로드)
            neo4j_client: Neo4j 클라이언트 (저장용, 선택)
        """
        self.api_key = api_key or os.getenv("OPENDART_API_KEY")
        if not self.api_key:
            raise ValueError("DART API 키가 필요합니다 (OPENDART_API_KEY 환경변수)")

        self.base_url = DART_API_BASE
        self.neo4j_client = neo4j_client
        self.validator = DataValidator(neo4j_client)
        self._cache: dict[str, dict] = {}

    def _request(self, endpoint: str, params: dict) -> dict:
        """
        DART API 요청

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터

        Returns:
            API 응답 (JSON)
        """
        # 캐시 키
        cache_key = f"{endpoint}:{hash(frozenset(params.items()))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # API 키 추가
        params["crtfc_key"] = self.api_key

        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()

            # 캐시 저장
            self._cache[cache_key] = result
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"DART API 요청 실패: {endpoint} - {e}")
            return {"status": "error", "message": str(e)}

    def collect_disclosures(
        self,
        corp_code: str,
        days: int = 90,
        analyze: bool = True,
    ) -> CollectionResult:
        """
        특정 기업의 공시 수집 (리스크 중심)

        1단계: 리스크 관련 공시 유형(주요사항보고, 발행공시, 외부감사 등) 우선 수집
        2단계: 일반 공시 중 루틴 필터링 (임원ㆍ주요주주 보고서 제외)
        3단계: 제목 보강 (제출인 명시) + 중복 제거
        """
        result = CollectionResult()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_params = {
            "corp_code": corp_code,
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_count": 100,
        }

        all_items = []
        seen_rcept = set()

        # 1단계: 리스크 관련 공시 유형별 수집 (B=주요사항보고, C=발행공시, F=외부감사, I=거래소, J=공정위)
        for pblntf_ty in RISK_FILING_TYPES:
            response = self._request(DART_ENDPOINTS["disclosure_list"], {
                **date_params,
                "pblntf_ty": pblntf_ty,
            })
            if response.get("status") == "000":
                for item in response.get("list", []):
                    rcept_no = item.get("rcept_no", "")
                    if rcept_no and rcept_no not in seen_rcept:
                        seen_rcept.add(rcept_no)
                        all_items.append(item)

        # 2단계: 일반 공시 (루틴 필터링 적용)
        response = self._request(DART_ENDPOINTS["disclosure_list"], date_params)
        if response.get("status") == "000":
            for item in response.get("list", []):
                rcept_no = item.get("rcept_no", "")
                title = item.get("report_nm", "")

                # 루틴 공시 스킵 (collect_people에서 이미 수집)
                if any(pattern in title for pattern in ROUTINE_FILING_PATTERNS):
                    continue

                if rcept_no and rcept_no not in seen_rcept:
                    seen_rcept.add(rcept_no)
                    all_items.append(item)

        result.total_fetched = len(all_items)

        # 3단계: 제목 보강 + 분석 + 중복 제거
        seen_titles = set()
        for item in all_items:
            try:
                title = item.get("report_nm", "")
                flr_nm = item.get("flr_nm", "")
                corp_name = item.get("corp_name", "")
                rcept_dt = item.get("rcept_dt", "")

                # 제목에 제출인 보강 (회사명 자체가 아닌 경우)
                if flr_nm and flr_nm != corp_name:
                    enriched_title = f"{title} ({flr_nm})"
                else:
                    enriched_title = title

                # 동일 날짜 + 동일 제목 중복 제거
                title_key = f"{title}_{rcept_dt}"
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                disclosure = DisclosureData(
                    rcept_no=item.get("rcept_no", ""),
                    corp_code=item.get("corp_code", corp_code),
                    corp_name=corp_name,
                    title=enriched_title,
                    filing_date=rcept_dt,
                )

                if analyze:
                    disclosure = self.analyze_disclosure(disclosure)

                validation = self.validator.validate(disclosure.to_dict(), "Disclosure")
                if validation.is_valid:
                    result.disclosures.append(disclosure)
                    result.total_valid += 1

                    if disclosure.score_result and disclosure.score_result.final_score >= 50:
                        result.high_risk_count += 1

                result.total_analyzed += 1

            except Exception as e:
                result.errors.append(f"공시 처리 오류 ({item.get('rcept_no')}): {e}")
                logger.warning(f"공시 처리 오류: {e}")

        result.completed_at = datetime.now()
        logger.info(f"공시 수집 완료: {corp_code} - {result.total_valid}/{result.total_fetched} 건 (루틴 제외)")
        return result

    def analyze_disclosure(self, disclosure: DisclosureData) -> DisclosureData:
        """
        공시 분석 (키워드 매칭 + 공시유형 기반 점수)

        1. 키워드 매칭 → 있으면 키워드 기반 점수
        2. 키워드 매칭 실패 → 공시유형(RISK/AUDIT/FINANCE 등) 기반 가중치 부여
        """
        # 키워드 매칭
        match_result = match_keywords(disclosure.title, source="DART")
        disclosure.match_result = match_result

        # 공시 유형 분류
        disclosure.disclosure_type = self._classify_disclosure_type(disclosure.title)

        try:
            filing_date = datetime.strptime(disclosure.filing_date, "%Y%m%d")
        except ValueError:
            filing_date = datetime.now()

        if match_result.keyword_count > 0:
            # 키워드 매칭 성공 → 키워드 기반 점수
            score_result = calculate_final_score(match_result, filing_date, source="DART")
            disclosure.score_result = score_result
            disclosure.category = match_result.primary_category
        else:
            # 키워드 매칭 실패 → 공시유형 기반 가중치 부여
            base_score = DISCLOSURE_BASE_SCORES.get(disclosure.disclosure_type, 0)
            if base_score > 0:
                from .score_engine import (
                    calculate_decayed_score, determine_status,
                    determine_sentiment, calc_confidence,
                )
                decay_result = calculate_decayed_score(base_score, filing_date)
                confidence = 0.95  # DART 공시는 높은 신뢰도
                final_score = decay_result.decayed_score * confidence
                disclosure.score_result = ScoreResult(
                    raw_score=base_score,
                    decayed_score=decay_result.decayed_score,
                    confidence=confidence,
                    final_score=final_score,
                    days_old=decay_result.days_old,
                    decay_rate=decay_result.decay_rate,
                    status=determine_status(round(final_score)),
                    sentiment=determine_sentiment(round(final_score)),
                    category_breakdown={disclosure.disclosure_type: base_score},
                )
                # disclosure_type → category 매핑
                dtype_to_cat = {
                    "AUDIT": "AUDIT", "GOVERNANCE": "GOVERNANCE",
                    "FINANCE": "CAPITAL", "RISK": "LEGAL",
                    "BUSINESS": "OTHER",
                }
                disclosure.category = dtype_to_cat.get(disclosure.disclosure_type, "OTHER")

        return disclosure

    def _classify_disclosure_type(self, title: str) -> str:
        """공시 유형 분류"""
        for dtype, keywords in DISCLOSURE_TYPES.items():
            if any(kw in title for kw in keywords):
                return dtype
        return "OTHER"

    def collect_company_info(self, corp_code: str) -> dict | None:
        """
        기업 기본정보 수집

        Args:
            corp_code: 기업코드

        Returns:
            기업 정보 딕셔너리 또는 None
        """
        response = self._request(DART_ENDPOINTS["company"], {
            "corp_code": corp_code,
        })

        if response.get("status") != "000":
            logger.warning(f"기업정보 조회 실패: {corp_code}")
            return None

        return {
            "corp_code": response.get("corp_code"),
            "corp_name": response.get("corp_name"),
            "corp_name_eng": response.get("corp_name_eng"),
            "stock_code": response.get("stock_code"),
            "ceo_name": response.get("ceo_nm"),
            "corp_cls": response.get("corp_cls"),  # Y: 유가증권, K: 코스닥, N: 코넥스, E: 기타
            "est_dt": response.get("est_dt"),      # 설립일
            "acc_mt": response.get("acc_mt"),      # 결산월
            "adres": response.get("adres"),        # 주소
            "hm_url": response.get("hm_url"),      # 홈페이지
            "induty_code": response.get("induty_code"),  # 업종코드
        }

    def collect_financials(
        self,
        corp_code: str,
        year: str | None = None,
        report_code: str = "11011",
    ) -> dict | None:
        """
        재무제표 수집

        Args:
            corp_code: 기업코드
            year: 사업연도 (None이면 전년도)
            report_code: 보고서코드 (11011: 사업보고서)

        Returns:
            재무제표 딕셔너리 또는 None
        """
        if year is None:
            year = str(datetime.now().year - 1)

        response = self._request(DART_ENDPOINTS["financials"], {
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": report_code,
        })

        if response.get("status") != "000":
            logger.warning(f"재무제표 조회 실패: {corp_code} ({year})")
            return None

        # 재무지표 추출
        financials = {"year": year, "items": []}
        for item in response.get("list", []):
            financials["items"].append({
                "account_nm": item.get("account_nm"),      # 계정명
                "thstrm_amount": item.get("thstrm_amount"),  # 당기금액
                "frmtrm_amount": item.get("frmtrm_amount"),  # 전기금액
                "bfefrmtrm_amount": item.get("bfefrmtrm_amount"),  # 전전기금액
            })

        return financials

    def collect_shareholders(self, corp_code: str, year: str | None = None) -> list[dict]:
        """
        주주현황 수집

        Args:
            corp_code: 기업코드
            year: 사업연도

        Returns:
            주주 목록
        """
        if year is None:
            years_to_try = [str(datetime.now().year - i) for i in range(1, 4)]
        else:
            years_to_try = [year]

        response = {"status": "error"}
        for try_year in years_to_try:
            response = self._request(DART_ENDPOINTS["shareholders"], {
                "corp_code": corp_code,
                "bsns_year": try_year,
                "reprt_code": "11011",
            })
            if response.get("status") == "000" and response.get("list"):
                break

        shareholders = []
        for item in response.get("list", []):
            shareholders.append({
                "nm": item.get("nm"),                    # 성명
                "relate": item.get("relate"),            # 관계
                "stock_knd": item.get("stock_knd"),      # 주식종류
                "bsis_posesn_stock_co": item.get("bsis_posesn_stock_co"),  # 기초보유주식
                "trmend_posesn_stock_co": item.get("trmend_posesn_stock_co"),  # 기말보유주식
                "trmend_posesn_stock_qota_rt": item.get("trmend_posesn_stock_qota_rt"),  # 기말지분율
            })

        return shareholders

    def collect_executives(self, corp_code: str) -> list[dict]:
        """
        임원현황 수집 (C-Level 핵심 임원만)

        필터: 대표이사, 회장, 부회장, 사외이사, 감사만
        (사내이사, 상무, 전무 등 제외)

        Args:
            corp_code: 기업코드

        Returns:
            핵심 임원 목록 (5-20명 수준)
        """
        response = self._request(DART_ENDPOINTS["executives"], {
            "corp_code": corp_code,
        })

        # 정확히 매칭할 직책 (부분 매칭 X)
        EXACT_POSITIONS = {'회장', '부회장', '감사'}

        # 포함 여부로 매칭할 직책
        INCLUDE_POSITIONS = ['대표이사', '대표사장', '대표부회장', '사외이사', '감사위원']

        # 제외할 직책 - 너무 많음 (사장/부사장도 역대 데이터가 많아서 제외)
        EXCLUDE_POSITIONS = ['사내이사', '상무', '전무', '사장', '부사장']

        # 최신 데이터 기준 중복 제거
        seen_names = {}  # name -> (rcept_dt, data)

        for item in response.get("list", []):
            name = item.get("repror")
            if not name:
                continue

            position = (item.get("isu_exctv_ofcps") or '').strip()
            rcept_dt = item.get("rcept_dt") or ''

            # 제외 조건 먼저 체크
            if any(ex in position for ex in EXCLUDE_POSITIONS):
                continue

            # 포함 조건 체크
            is_exact = position in EXACT_POSITIONS
            is_include = any(inc in position for inc in INCLUDE_POSITIONS)

            if not (is_exact or is_include):
                continue

            # 동일 인물이면 최신 데이터만 유지
            if name in seen_names:
                if rcept_dt <= seen_names[name][0]:
                    continue

            seen_names[name] = (rcept_dt, {
                "nm": name,
                "ofcps": position,
                "rgist_exctv_at": item.get("isu_exctv_rgist_at") or '',
                "chrg_job": position,
            })

        executives = [v[1] for v in seen_names.values()]
        return executives

    def save_to_neo4j(self, disclosures: list[DisclosureData]) -> int:
        """
        수집된 공시를 Neo4j 5-Node 스키마에 저장
        경로: Company → RiskCategory → RiskEntity(ISSUE/DART_DISCLOSURE) → RiskEvent(DISCLOSURE)
        """
        if self.neo4j_client is None:
            logger.warning("Neo4j 클라이언트가 설정되지 않았습니다")
            return 0

        saved_count = 0
        query = """
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE (c.name = $companyName OR c.corpCode = $corpCode)
          AND rc.code = $categoryCode
        WITH rc LIMIT 1
        MERGE (re:RiskEntity {id: $entityId})
        ON CREATE SET re.name = $entityName, re.type = 'ISSUE',
                      re.subType = 'DART_DISCLOSURE', re.createdAt = datetime()
        ON MATCH SET re.name = $entityName, re.updatedAt = datetime()
        MERGE (rc)-[:HAS_ENTITY]->(re)
        WITH re
        MERGE (ev:RiskEvent {id: $eventId})
        ON CREATE SET ev.title = $title, ev.type = 'DISCLOSURE',
                      ev.score = $score, ev.severity = $severity,
                      ev.sourceName = 'DART', ev.sourceUrl = $sourceUrl,
                      ev.publishedAt = $publishedAt, ev.disclosureType = $disclosureType,
                      ev.isActive = true, ev.createdAt = datetime()
        ON MATCH SET ev.title = $title, ev.score = $score, ev.updatedAt = datetime()
        MERGE (re)-[:HAS_EVENT]->(ev)
        RETURN ev.id as id
        """

        with self.neo4j_client.session() as session:
            for disc in disclosures:
                try:
                    # 카테고리 결정: 키워드 매칭 > 공시유형 분류 > OTHER
                    cat_code = "OTHER"
                    if disc.match_result and disc.match_result.primary_category:
                        cat_code = self.CAT_CODE_MAP.get(disc.match_result.primary_category, "OTHER")
                    elif disc.disclosure_type:
                        cat_code = self.DISCLOSURE_TYPE_TO_CAT.get(disc.disclosure_type, "OTHER")

                    score = disc.score_result.final_score if disc.score_result else 0
                    severity = "HIGH" if score >= 50 else "MEDIUM" if score >= 20 else "LOW"

                    # filing_date 포맷: YYYYMMDD → YYYY-MM-DD
                    published_at = disc.filing_date
                    if len(published_at) == 8:
                        published_at = f"{published_at[:4]}-{published_at[4:6]}-{published_at[6:8]}"

                    entity_id = f"ENTITY_DART_{disc.corp_code}_{cat_code}"

                    result = session.run(query, {
                        "companyName": disc.corp_name,
                        "corpCode": disc.corp_code,
                        "categoryCode": cat_code,
                        "entityId": entity_id,
                        "entityName": f"DART 공시 ({cat_code})",
                        "eventId": disc.id,
                        "title": disc.title,
                        "score": score,
                        "severity": severity,
                        "sourceUrl": disc.source_url,
                        "publishedAt": published_at,
                        "disclosureType": disc.disclosure_type or "OTHER",
                    })
                    if result.single():
                        saved_count += 1
                except Exception as e:
                    logger.error(f"공시 저장 실패 ({disc.id}): {e}")

        logger.info(f"Neo4j 저장 완료: {saved_count}/{len(disclosures)} 건")
        return saved_count

    def save_shareholders_to_neo4j(self, shareholders: list[dict], company_name: str, corp_code: str) -> int:
        """
        주주 정보를 Neo4j 5-Node 스키마에 저장
        경로: Company → RiskCategory(SHARE) → RiskEntity(SHAREHOLDER)
        """
        if self.neo4j_client is None:
            logger.warning("Neo4j 클라이언트가 설정되지 않았습니다")
            return 0

        saved_count = 0
        query = """
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE (c.name = $companyName OR c.corpCode = $corpCode)
          AND rc.code = 'SHARE'
        WITH rc LIMIT 1
        MERGE (re:RiskEntity {id: $entityId})
        ON CREATE SET re.name = $name, re.type = 'SHAREHOLDER',
                      re.relation = $relation, re.stockType = $stockType,
                      re.shareRatio = $shareRatio, re.shareCount = $shareCount,
                      re.createdAt = datetime()
        ON MATCH SET re.name = $name, re.relation = $relation,
                     re.shareRatio = $shareRatio, re.shareCount = $shareCount,
                     re.updatedAt = datetime()
        MERGE (rc)-[:HAS_ENTITY]->(re)
        RETURN re.id AS id
        """

        with self.neo4j_client.session() as session:
            for sh in shareholders:
                name = (sh.get('nm') or '').strip()
                if not name or name == '-':
                    continue

                entity_id = f"SH_{corp_code}_{name.replace(' ', '_')}"

                share_ratio_str = sh.get('trmend_posesn_stock_qota_rt', '0')
                try:
                    share_ratio = float(share_ratio_str.replace(',', '').replace('%', '')) if share_ratio_str else 0
                except:
                    share_ratio = 0

                share_count_str = sh.get('trmend_posesn_stock_co', '0')
                try:
                    share_count = int(share_count_str.replace(',', '')) if share_count_str else 0
                except:
                    share_count = 0

                try:
                    result = session.run(query, {
                        "companyName": company_name,
                        "corpCode": corp_code,
                        "entityId": entity_id,
                        "name": name,
                        "relation": sh.get('relate', ''),
                        "stockType": sh.get('stock_knd', ''),
                        "shareRatio": share_ratio,
                        "shareCount": share_count,
                    })
                    if result.single():
                        saved_count += 1
                except Exception as e:
                    logger.error(f"주주 저장 실패 ({name}): {e}")

        logger.info(f"주주 Neo4j 저장 완료: {saved_count}/{len(shareholders)} 건")
        return saved_count

    def save_executives_to_neo4j(self, executives: list[dict], company_name: str, corp_code: str) -> int:
        """
        임원 정보를 Neo4j 5-Node 스키마에 저장
        경로: Company → RiskCategory(EXEC) → RiskEntity(PERSON)
        """
        if self.neo4j_client is None:
            logger.warning("Neo4j 클라이언트가 설정되지 않았습니다")
            return 0

        saved_count = 0
        query = """
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE (c.name = $companyName OR c.corpCode = $corpCode)
          AND rc.code = 'EXEC'
        WITH rc LIMIT 1
        MERGE (re:RiskEntity {id: $entityId})
        ON CREATE SET re.name = $name, re.type = 'PERSON',
                      re.position = $position, re.responsibility = $responsibility,
                      re.isRegistered = $isRegistered,
                      re.createdAt = datetime()
        ON MATCH SET re.name = $name, re.position = $position,
                     re.responsibility = $responsibility,
                     re.updatedAt = datetime()
        MERGE (rc)-[:HAS_ENTITY]->(re)
        RETURN re.id AS id
        """

        with self.neo4j_client.session() as session:
            for ex in executives:
                name = (ex.get('nm') or '').strip()
                if not name or name == '-':
                    continue

                entity_id = f"EXEC_{corp_code}_{name.replace(' ', '_')}"

                try:
                    result = session.run(query, {
                        "companyName": company_name,
                        "corpCode": corp_code,
                        "entityId": entity_id,
                        "name": name,
                        "position": ex.get('ofcps', ''),
                        "responsibility": ex.get('chrg_job', ''),
                        "isRegistered": (ex.get('rgist_exctv_at') or '') == 'Y',
                    })
                    if result.single():
                        saved_count += 1
                except Exception as e:
                    logger.error(f"임원 저장 실패 ({name}): {e}")

        logger.info(f"임원 Neo4j 저장 완료: {saved_count}/{len(executives)} 건")
        return saved_count

    # =========================================================================
    # DS005: 주요사항보고서 리스크 수집 (소송, 부도, 영업정지, 회생, 채권관리)
    # =========================================================================

    def collect_risk_events(self, corp_code: str, days: int = 365) -> dict:
        """
        DS005 주요사항보고서 리스크 이벤트 수집
        부도, 영업정지, 회생절차, 채권관리, 소송 한번에 수집

        Returns:
            {endpoint_name: [items]} 형태의 딕셔너리
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_params = {
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
        }

        risk_apis = {
            "lawsuits":            ("소송",       "LEGAL",  80),
            "default":             ("부도발생",   "CREDIT", 100),
            "business_suspension": ("영업정지",   "OPS",    90),
            "rehabilitation":      ("회생절차",   "LEGAL",  95),
            "creditor_mgmt":       ("채권관리",   "CREDIT", 85),
        }

        results = {}
        for endpoint_key, (label, category, base_score) in risk_apis.items():
            try:
                response = self._request(DART_ENDPOINTS[endpoint_key], {
                    "corp_code": corp_code,
                    **date_params,
                })
                if response.get("status") == "000":
                    items = response.get("list", [])
                    if items:
                        results[endpoint_key] = {
                            "label": label,
                            "category": category,
                            "base_score": base_score,
                            "items": items,
                        }
                        logger.info(f"  [{label}] {len(items)}건 발견")
            except Exception as e:
                logger.warning(f"  [{label}] 수집 실패: {e}")

        return results

    def collect_major_stock(self, corp_code: str) -> list[dict]:
        """DS004: 대량보유 상황보고 수집"""
        response = self._request(DART_ENDPOINTS["major_stock"], {
            "corp_code": corp_code,
        })
        if response.get("status") != "000":
            return []
        return response.get("list", [])

    def collect_shareholder_changes(self, corp_code: str, year: str | None = None) -> list[dict]:
        """DS002: 최대주주 변동현황 수집"""
        if year is None:
            years_to_try = [str(datetime.now().year - i) for i in range(1, 4)]
        else:
            years_to_try = [year]

        for try_year in years_to_try:
            response = self._request(DART_ENDPOINTS["shareholder_changes"], {
                "corp_code": corp_code,
                "bsns_year": try_year,
                "reprt_code": "11011",
            })
            if response.get("status") == "000" and response.get("list"):
                return response.get("list", [])

        return []

    def collect_financial_indices(self, corp_code: str, year: str | None = None) -> list[dict]:
        """DS003: 주요 재무지표 수집 (수익성, 안정성, 성장성, 활동성)"""
        idx_codes = {
            "M210000": "수익성",
            "M220000": "안정성",
            "M230000": "성장성",
            "M240000": "활동성",
        }

        # 연도 자동 탐색 (최신 데이터가 있는 연도 찾기)
        if year is None:
            years_to_try = [str(datetime.now().year - i) for i in range(1, 4)]
        else:
            years_to_try = [year]

        for try_year in years_to_try:
            all_indices = []
            for idx_code, label in idx_codes.items():
                response = self._request(DART_ENDPOINTS["financial_indices"], {
                    "corp_code": corp_code,
                    "bsns_year": try_year,
                    "reprt_code": "11011",
                    "idx_cl_code": idx_code,
                })
                if response.get("status") == "000":
                    for item in response.get("list", []):
                        item["idx_category"] = label
                        all_indices.append(item)

            if all_indices:
                logger.info(f"재무지표 수집: {try_year}년 {len(all_indices)}개")
                return all_indices

        return []

    def collect_investments(self, corp_code: str, year: str | None = None) -> list[dict]:
        """DS002: 타법인 출자현황 수집"""
        if year is None:
            years_to_try = [str(datetime.now().year - i) for i in range(1, 4)]
        else:
            years_to_try = [year]

        for try_year in years_to_try:
            response = self._request(DART_ENDPOINTS["investments"], {
                "corp_code": corp_code,
                "bsns_year": try_year,
                "reprt_code": "11011",
            })
            if response.get("status") == "000" and response.get("list"):
                return response.get("list", [])

        return []

    # =========================================================================
    # Neo4j 저장: 리스크 이벤트 (5-Node 스키마)
    # =========================================================================

    def save_risk_events_to_neo4j(self, risk_data: dict, company_name: str) -> int:
        """
        DS005 리스크 이벤트를 5-Node 스키마에 저장
        경로: Company → RiskCategory → RiskEntity(CASE) → RiskEvent(DISCLOSURE)
        """
        if self.neo4j_client is None:
            return 0

        saved_count = 0
        query = """
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE (c.name = $companyName OR c.corpCode = $corpCode)
          AND rc.code = $categoryCode
        WITH rc LIMIT 1
        MERGE (re:RiskEntity {id: $entityId})
        ON CREATE SET re.name = $entityName, re.type = 'CASE',
                      re.subType = $subType, re.createdAt = datetime()
        ON MATCH SET re.name = $entityName, re.updatedAt = datetime()
        MERGE (rc)-[:HAS_ENTITY]->(re)
        WITH re
        MERGE (ev:RiskEvent {id: $eventId})
        ON CREATE SET ev.title = $title, ev.type = 'DISCLOSURE',
                      ev.summary = $summary, ev.score = $score,
                      ev.severity = $severity, ev.sourceName = 'DART',
                      ev.sourceUrl = $sourceUrl, ev.publishedAt = $publishedAt,
                      ev.isActive = true, ev.createdAt = datetime()
        ON MATCH SET ev.title = $title, ev.summary = $summary,
                     ev.score = $score, ev.updatedAt = datetime()
        MERGE (re)-[:HAS_EVENT]->(ev)
        RETURN ev.id as id
        """

        with self.neo4j_client.session() as session:
            for endpoint_key, data in risk_data.items():
                label = data["label"]
                cat_code = self.CAT_CODE_MAP.get(data["category"], "OTHER")
                base_score = data["base_score"]
                items = data["items"]

                for i, item in enumerate(items):
                    rcept_no = item.get("rcept_no", f"unknown_{i}")
                    corp_code = item.get("corp_code", "")

                    # 이벤트별 제목/요약 구성
                    title, summary = self._format_risk_event(endpoint_key, item, label)

                    # 날짜 파싱
                    published_at = self._parse_date_field(item, endpoint_key)

                    severity = "CRITICAL" if base_score >= 90 else "HIGH"
                    entity_id = f"CASE_{endpoint_key}_{corp_code}"
                    event_id = f"RISK_{rcept_no}"
                    source_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

                    try:
                        result = session.run(query, {
                            "companyName": company_name,
                            "corpCode": corp_code,
                            "categoryCode": cat_code,
                            "entityId": entity_id,
                            "entityName": f"{label} ({company_name})",
                            "subType": endpoint_key.upper(),
                            "eventId": event_id,
                            "title": title,
                            "summary": summary,
                            "score": base_score,
                            "severity": severity,
                            "sourceUrl": source_url,
                            "publishedAt": published_at,
                        })
                        if result.single():
                            saved_count += 1
                    except Exception as e:
                        logger.error(f"리스크 이벤트 저장 실패 ({event_id}): {e}")

        logger.info(f"리스크 이벤트 Neo4j 저장 완료: {saved_count} 건")
        return saved_count

    def save_major_stock_to_neo4j(self, stocks: list[dict], company_name: str, corp_code: str) -> int:
        """대량보유 상황보고를 5-Node SHARE 카테고리에 저장"""
        if self.neo4j_client is None or not stocks:
            return 0

        saved_count = 0
        query = """
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE (c.name = $companyName OR c.corpCode = $corpCode)
          AND rc.code = 'SHARE'
        WITH rc LIMIT 1
        MERGE (re:RiskEntity {id: $entityId})
        ON CREATE SET re.name = $name, re.type = 'SHAREHOLDER',
                      re.shareRatio = $shareRatio, re.reportType = $reportType,
                      re.reportReason = $reportReason,
                      re.createdAt = datetime()
        ON MATCH SET re.name = $name, re.shareRatio = $shareRatio,
                     re.reportReason = $reportReason,
                     re.updatedAt = datetime()
        MERGE (rc)-[:HAS_ENTITY]->(re)
        RETURN re.id AS id
        """

        with self.neo4j_client.session() as session:
            for item in stocks:
                name = (item.get("repror") or "").strip()
                if not name:
                    continue

                entity_id = f"MAJOR_{corp_code}_{name.replace(' ', '_')}"
                ratio_str = item.get("stkrt", "0")
                try:
                    share_ratio = float(ratio_str.replace(",", "").replace("%", "")) if ratio_str else 0
                except:
                    share_ratio = 0

                try:
                    result = session.run(query, {
                        "companyName": company_name,
                        "corpCode": corp_code,
                        "entityId": entity_id,
                        "name": name,
                        "shareRatio": share_ratio,
                        "reportType": item.get("report_tp", ""),
                        "reportReason": item.get("report_resn", ""),
                    })
                    if result.single():
                        saved_count += 1
                except Exception as e:
                    logger.error(f"대량보유 저장 실패 ({name}): {e}")

        logger.info(f"대량보유 Neo4j 저장 완료: {saved_count}/{len(stocks)} 건")
        return saved_count

    def save_financial_indices_to_neo4j(self, indices: list[dict], company_name: str, corp_code: str) -> int:
        """주요 재무지표를 Company 노드 속성으로 저장"""
        if self.neo4j_client is None or not indices:
            return 0

        # 재무지표를 카테고리별 딕셔너리로 변환
        fin_data = {}
        for item in indices:
            idx_nm = item.get("idx_nm", "")
            idx_val = item.get("idx_val", "")
            if idx_nm and idx_val and idx_val != '-':
                # 키 이름 정규화 (Neo4j 속성명에 허용되지 않는 문자 제거)
                import re as _re
                key = idx_nm.replace(" ", "")
                key = _re.sub(r'[^a-zA-Z0-9가-힣_]', '_', key)
                key = _re.sub(r'_+', '_', key).strip('_')
                fin_data[f"fin_{key}"] = idx_val

        if not fin_data:
            return 0

        # Company 노드에 재무지표 속성 추가
        set_clauses = ", ".join([f"c.{k} = ${k}" for k in fin_data.keys()])
        query = f"""
        MATCH (c:Company)
        WHERE c.name = $companyName OR c.corpCode = $corpCode
        SET {set_clauses}, c.finUpdatedAt = datetime()
        RETURN c.name
        """

        try:
            params = {"companyName": company_name, "corpCode": corp_code, **fin_data}
            result = self.neo4j_client.execute_write(query, params)
            if result:
                logger.info(f"재무지표 저장 완료: {company_name} ({len(fin_data)}개 지표)")
                return len(fin_data)
        except Exception as e:
            logger.error(f"재무지표 저장 실패: {e}")
        return 0

    def save_shareholder_changes_to_neo4j(self, changes: list[dict], company_name: str, corp_code: str) -> int:
        """최대주주 변동현황을 RiskEvent로 저장"""
        if self.neo4j_client is None or not changes:
            return 0

        saved_count = 0
        query = """
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WHERE (c.name = $companyName OR c.corpCode = $corpCode)
          AND rc.code = 'SHARE'
        WITH rc LIMIT 1
        MERGE (re:RiskEntity {id: $entityId})
        ON CREATE SET re.name = $name, re.type = 'SHAREHOLDER',
                      re.shareRatio = $shareRatio,
                      re.createdAt = datetime()
        ON MATCH SET re.name = $name, re.shareRatio = $shareRatio,
                     re.updatedAt = datetime()
        MERGE (rc)-[:HAS_ENTITY]->(re)
        WITH re
        MERGE (ev:RiskEvent {id: $eventId})
        ON CREATE SET ev.title = $title, ev.type = 'DISCLOSURE',
                      ev.summary = $changeCause, ev.score = $score,
                      ev.severity = 'MEDIUM', ev.sourceName = 'DART',
                      ev.publishedAt = $changeDate,
                      ev.isActive = true, ev.createdAt = datetime()
        ON MATCH SET ev.summary = $changeCause, ev.updatedAt = datetime()
        MERGE (re)-[:HAS_EVENT]->(ev)
        RETURN ev.id as id
        """

        with self.neo4j_client.session() as session:
            for item in changes:
                name = (item.get("mxmm_shrholdr_nm") or "").strip()
                if not name or name == '-':
                    continue

                entity_id = f"SHCHG_{corp_code}_{name.replace(' ', '_')}"
                change_date = item.get("change_on", "")
                change_cause = item.get("change_cause", "")
                ratio_str = item.get("qota_rt", "0")
                try:
                    share_ratio = float(ratio_str.replace(",", "").replace("%", "")) if ratio_str else 0
                except:
                    share_ratio = 0

                # 점수: 변동 사유에 따라 가중치
                score = 15
                if any(kw in change_cause for kw in ["매도", "처분", "감소"]):
                    score = 25
                elif any(kw in change_cause for kw in ["취득", "증가", "매수"]):
                    score = 10

                event_id = f"SHCHG_{corp_code}_{name.replace(' ', '_')}_{change_date.replace('.', '')}"

                try:
                    result = session.run(query, {
                        "companyName": company_name,
                        "corpCode": corp_code,
                        "entityId": entity_id,
                        "name": name,
                        "shareRatio": share_ratio,
                        "eventId": event_id,
                        "title": f"최대주주 변동: {name} ({change_cause})",
                        "changeCause": change_cause,
                        "score": score,
                        "changeDate": change_date,
                    })
                    if result.single():
                        saved_count += 1
                except Exception as e:
                    logger.error(f"주주 변동 저장 실패 ({name}): {e}")

        logger.info(f"주주 변동 Neo4j 저장 완료: {saved_count}/{len(changes)} 건")
        return saved_count

    # =========================================================================
    # 내부 유틸리티
    # =========================================================================

    @staticmethod
    def _format_risk_event(endpoint_key: str, item: dict, label: str) -> tuple[str, str]:
        """리스크 이벤트의 제목과 요약을 구성"""
        corp_name = item.get("corp_name", "")

        if endpoint_key == "lawsuits":
            case_name = item.get("icnm", "")
            plaintiff = item.get("ac_ap", "")
            claim = item.get("rq_cn", "")
            title = f"[소송] {case_name}" if case_name else f"[소송] {corp_name}"
            summary = f"원고: {plaintiff}. 청구내용: {claim}" if claim else ""
        elif endpoint_key == "default":
            content = item.get("df_cn", "")
            amount = item.get("df_amt", "")
            reason = item.get("df_rs", "")
            title = f"[부도] {corp_name} - {content}" if content else f"[부도] {corp_name}"
            summary = f"금액: {amount}. 사유: {reason}" if reason else ""
        elif endpoint_key == "business_suspension":
            category = item.get("bsnsp_rm", "")
            reason = item.get("bsnsp_rs", "")
            title = f"[영업정지] {corp_name} - {category}" if category else f"[영업정지] {corp_name}"
            summary = f"사유: {reason}" if reason else ""
        elif endpoint_key == "rehabilitation":
            reason = item.get("rq_rs", "")
            court = item.get("cpct", "")
            title = f"[회생절차] {corp_name}"
            summary = f"사유: {reason}. 관할법원: {court}" if reason else ""
        elif endpoint_key == "creditor_mgmt":
            institution = item.get("mngt_int", "")
            reason = item.get("mngt_rs", "")
            title = f"[채권관리] {corp_name} - {institution}" if institution else f"[채권관리] {corp_name}"
            summary = f"사유: {reason}" if reason else ""
        else:
            title = f"[{label}] {corp_name}"
            summary = ""

        return title, summary

    @staticmethod
    def _parse_date_field(item: dict, endpoint_key: str) -> str:
        """리스크 이벤트에서 날짜 필드 추출"""
        date_fields = {
            "lawsuits": "lgd",
            "default": "dfd",
            "business_suspension": "bsnspd",
            "rehabilitation": "rqd",
            "creditor_mgmt": "mngt_pcbg_dd",
        }
        date_val = item.get(date_fields.get(endpoint_key, ""), "")
        if not date_val:
            date_val = item.get("cfd", "")
        # YYYYMMDD → YYYY-MM-DD
        if date_val and len(date_val) == 8 and date_val.isdigit():
            return f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:8]}"
        return date_val


# =============================================================================
# 헬퍼 함수
# =============================================================================

def collect_all_disclosures(
    corp_codes: list[str],
    days: int = 30,
    api_key: str | None = None,
) -> dict[str, CollectionResult]:
    """
    여러 기업의 공시 일괄 수집

    Args:
        corp_codes: 기업코드 목록
        days: 수집 기간
        api_key: DART API 키

    Returns:
        기업코드별 수집 결과
    """
    collector = DartCollectorV2(api_key=api_key)
    results = {}

    for corp_code in corp_codes:
        try:
            results[corp_code] = collector.collect_disclosures(corp_code, days=days)
        except Exception as e:
            logger.error(f"수집 실패 ({corp_code}): {e}")
            results[corp_code] = CollectionResult(errors=[str(e)])

    return results


def get_high_risk_disclosures(
    result: CollectionResult,
    threshold: float = 50.0,
) -> list[DisclosureData]:
    """
    고위험 공시만 필터링

    Args:
        result: 수집 결과
        threshold: 점수 임계치

    Returns:
        고위험 공시 목록
    """
    return [
        d for d in result.disclosures
        if d.score_result and d.score_result.final_score >= threshold
    ]
