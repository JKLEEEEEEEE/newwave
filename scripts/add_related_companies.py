"""
관련기업 데이터 보강 스크립트
- 기존 빈약한 관련기업(TSMC, 마이크론, 삼성SDI, SK머티리얼즈) 엔티티/이벤트 추가
- 신규 관련기업 추가: ASML, 한미반도체, Apple, NVIDIA, LG에너지솔루션, Qualcomm
- HAS_RELATED 관계에 dependencyScore 추가
- 점수 재계산
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

# ============================================================
# 신규 관련기업 정의
# ============================================================
NEW_COMPANIES = [
    # SK하이닉스 공급망
    {"id": "ASML", "name": "ASML", "ticker": "ASML", "sector": "반도체장비", "market": "NASDAQ", "isMain": False},
    {"id": "한미반도체", "name": "한미반도체", "ticker": "042700", "sector": "반도체장비", "market": "KOSDAQ", "isMain": False},
    {"id": "Apple", "name": "Apple", "ticker": "AAPL", "sector": "IT", "market": "NASDAQ", "isMain": False},
    {"id": "NVIDIA", "name": "NVIDIA", "ticker": "NVDA", "sector": "반도체", "market": "NASDAQ", "isMain": False},
    # 삼성전자 공급망
    {"id": "LG에너지솔루션", "name": "LG에너지솔루션", "ticker": "373220", "sector": "배터리", "market": "KOSPI", "isMain": False},
    {"id": "Qualcomm", "name": "Qualcomm", "ticker": "QCOM", "sector": "반도체", "market": "NASDAQ", "isMain": False},
]

# 관련기업 연결 (신규)
NEW_RELATIONS = [
    # SK하이닉스
    {"main": "SK하이닉스", "related": "ASML", "relation": "장비공급사", "tier": 1, "dep": 0.35},
    {"main": "SK하이닉스", "related": "한미반도체", "relation": "장비공급사", "tier": 1, "dep": 0.25},
    {"main": "SK하이닉스", "related": "Apple", "relation": "고객사", "tier": 1, "dep": 0.40},
    {"main": "SK하이닉스", "related": "NVIDIA", "relation": "고객사", "tier": 1, "dep": 0.45},
    # 삼성전자
    {"main": "삼성전자", "related": "LG에너지솔루션", "relation": "배터리공급사", "tier": 1, "dep": 0.30},
    {"main": "삼성전자", "related": "Qualcomm", "relation": "AP공급사", "tier": 1, "dep": 0.35},
]

# 기존 관련기업 HAS_RELATED에 dependencyScore 업데이트
EXISTING_RELATIONS_UPDATE = [
    {"main": "SK하이닉스", "related": "SK머티리얼즈", "dep": 0.40},
    {"main": "SK하이닉스", "related": "마이크론", "dep": 0.20},
    {"main": "삼성전자", "related": "삼성SDI", "dep": 0.35},
    {"main": "삼성전자", "related": "TSMC", "dep": 0.25},
]

# ============================================================
# 각 관련기업별 엔티티+이벤트 데이터
# ============================================================
COMPANY_DATA = {
    # -- 기존 빈약한 관련기업 보강 --
    "마이크론": {
        "entities": [
            {"cat": "LEGAL", "name": "중국 독점규제 조사", "type": "CASE", "desc": "중국 반독점법 위반 조사",
             "events": [
                 {"title": "중국 시장감독총국 마이크론 조사 착수", "summary": "사이버보안 심사 명목 중국 내 판매 제한 가능성", "type": "NEWS", "score": 45, "severity": "CRITICAL", "source": "Reuters"},
                 {"title": "마이크론 중국 매출 30% 감소 전망", "summary": "중국 정부 조달 금지로 매출 타격 불가피", "type": "NEWS", "score": 35, "severity": "HIGH", "source": "Bloomberg"},
             ]},
            {"cat": "OPS", "name": "히로시마 공장 운영", "type": "ISSUE", "desc": "일본 히로시마 DRAM 팹 운영 현황",
             "events": [
                 {"title": "마이크론 히로시마 팹 증설 완료", "summary": "EUV 기반 1β DRAM 양산 시작", "type": "NEWS", "score": 5, "severity": "LOW", "source": "日経"},
             ]},
            {"cat": "CREDIT", "name": "신용등급 변동", "type": "ISSUE", "desc": "마이크론 신용등급 평가",
             "events": [
                 {"title": "S&P 마이크론 신용등급 BBB 유지", "summary": "HBM 수요 급증으로 실적 개선 반영", "type": "DISCLOSURE", "score": 5, "severity": "LOW", "source": "S&P"},
             ]},
        ]
    },
    "SK머티리얼즈": {
        "entities": [
            {"cat": "ESG", "name": "특수가스 유출 사고", "type": "ISSUE", "desc": "영주 공장 NF3 가스 유출",
             "events": [
                 {"title": "SK머티리얼즈 영주공장 NF3 유출 사고", "summary": "환경부 조사 착수, 주민 민원 발생", "type": "NEWS", "score": 30, "severity": "HIGH", "source": "환경부"},
                 {"title": "SK머티리얼즈 환경부 시정명령", "summary": "특수가스 저장시설 개선 명령 및 과태료 부과", "type": "DISCLOSURE", "score": 20, "severity": "MEDIUM", "source": "DART"},
             ]},
            {"cat": "SUPPLY", "name": "원료 수급 리스크", "type": "ISSUE", "desc": "네온가스 등 원료 수급",
             "events": [
                 {"title": "우크라이나 사태로 네온가스 수급 불안", "summary": "반도체 특수가스 원료 가격 300% 급등", "type": "NEWS", "score": 25, "severity": "HIGH", "source": "연합뉴스"},
             ]},
            {"cat": "EXEC", "name": "박원철 대표이사", "type": "PERSON", "position": "대표이사", "desc": "SK머티리얼즈 CEO",
             "events": [
                 {"title": "박원철 대표 소재 국산화 전략 발표", "summary": "2027년까지 핵심소재 국산화율 80% 목표", "type": "NEWS", "score": 3, "severity": "LOW", "source": "매경"},
             ]},
        ]
    },
    "TSMC": {
        "entities": [
            {"cat": "OPS", "name": "미국 애리조나 팹 건설", "type": "ISSUE", "desc": "TSMC 미국 공장 진출",
             "events": [
                 {"title": "TSMC 애리조나 팹 건설 1년 지연", "summary": "숙련 인력 부족으로 3nm 팹 가동 시점 2026년으로 연기", "type": "NEWS", "score": 30, "severity": "HIGH", "source": "WSJ"},
                 {"title": "미 상무부 TSMC에 66억달러 보조금 확정", "summary": "CHIPS법 기반 반도체 보조금 지급 확정", "type": "DISCLOSURE", "score": 5, "severity": "LOW", "source": "Commerce.gov"},
             ]},
            {"cat": "LEGAL", "name": "삼성전자 특허 분쟁", "type": "CASE", "desc": "GAA 공정 특허 소송",
             "events": [
                 {"title": "TSMC-삼성전자 GAA 특허 분쟁 격화", "summary": "3nm GAA 공정 관련 상호 특허 침해 소송", "type": "NEWS", "score": 25, "severity": "HIGH", "source": "DigiTimes"},
             ]},
            {"cat": "GOV", "name": "대만해협 지정학 리스크", "type": "ISSUE", "desc": "중국-대만 긴장 고조",
             "events": [
                 {"title": "중국 대만해협 군사훈련 확대", "summary": "TSMC 공급 중단 시 글로벌 반도체 공급망 마비 우려", "type": "NEWS", "score": 40, "severity": "CRITICAL", "source": "FT"},
                 {"title": "TSMC 일본·유럽 생산 다변화 가속", "summary": "구마모토 2공장, 독일 드레스덴 팹 건설 추진", "type": "NEWS", "score": 5, "severity": "LOW", "source": "Nikkei"},
             ]},
        ]
    },
    "삼성SDI": {
        "entities": [
            {"cat": "OPS", "name": "헝가리 공장 화재", "type": "ISSUE", "desc": "괴드 공장 배터리 화재 사고",
             "events": [
                 {"title": "삼성SDI 헝가리 괴드공장 화재 발생", "summary": "배터리 셀 생산라인 일부 소실, 인명피해 없음", "type": "NEWS", "score": 35, "severity": "CRITICAL", "source": "연합뉴스"},
                 {"title": "삼성SDI 헝가리 공장 복구 3개월 소요", "summary": "유럽 OEM 납품 지연으로 위약금 우려", "type": "NEWS", "score": 25, "severity": "HIGH", "source": "한경"},
             ]},
            {"cat": "CREDIT", "name": "전고체 배터리 투자", "type": "ISSUE", "desc": "차세대 배터리 대규모 투자",
             "events": [
                 {"title": "삼성SDI 전고체 배터리 2조원 투자 결정", "summary": "2027년 양산 목표, 기존 리튬이온 대비 에너지밀도 2배", "type": "DISCLOSURE", "score": 10, "severity": "MEDIUM", "source": "DART"},
             ]},
            {"cat": "LEGAL", "name": "LG에너지솔루션 영업비밀 소송", "type": "CASE", "desc": "배터리 기술 유출 소송",
             "events": [
                 {"title": "LG에너지솔루션, 삼성SDI 기술유출 소송", "summary": "원통형 배터리 양극재 기술 영업비밀 침해 주장", "type": "NEWS", "score": 20, "severity": "HIGH", "source": "조선일보"},
             ]},
        ]
    },
    # -- 신규 관련기업 --
    "ASML": {
        "entities": [
            {"cat": "SUPPLY", "name": "EUV 장비 납품 지연", "type": "ISSUE", "desc": "High-NA EUV 장비 수급",
             "events": [
                 {"title": "ASML High-NA EUV 장비 납기 6개월 지연", "summary": "2nm 이하 공정 전환 일정에 차질 우려", "type": "NEWS", "score": 35, "severity": "CRITICAL", "source": "Reuters"},
                 {"title": "ASML 2026년 EUV 출하량 50대→40대 하향", "summary": "광학계 부품 수급 병목으로 생산능력 제한", "type": "NEWS", "score": 25, "severity": "HIGH", "source": "Bloomberg"},
             ]},
            {"cat": "GOV", "name": "네덜란드 수출규제", "type": "ISSUE", "desc": "대중국 EUV 수출 통제",
             "events": [
                 {"title": "네덜란드 정부 대중국 DUV 추가 수출규제", "summary": "ASML DUV 장비도 수출허가 대상에 포함", "type": "DISCLOSURE", "score": 20, "severity": "HIGH", "source": "Dutch Gov"},
             ]},
            {"cat": "EXEC", "name": "크리스토프 푸케 CEO", "type": "PERSON", "position": "CEO", "desc": "ASML CEO",
             "events": [
                 {"title": "ASML CEO 수주잔고 사상 최대 발표", "summary": "2026년 수주잔고 390억유로, AI 반도체 수요 견인", "type": "DISCLOSURE", "score": 3, "severity": "LOW", "source": "ASML IR"},
             ]},
        ]
    },
    "한미반도체": {
        "entities": [
            {"cat": "OPS", "name": "TC본더 생산능력", "type": "ISSUE", "desc": "HBM용 TC본더 생산 현황",
             "events": [
                 {"title": "한미반도체 TC본더 수주 폭주", "summary": "SK하이닉스 HBM4 대응 TC본더 100대 추가 수주", "type": "NEWS", "score": 5, "severity": "LOW", "source": "전자신문"},
             ]},
            {"cat": "SHARE", "name": "곽동신 회장 지분", "type": "SHAREHOLDER", "desc": "최대주주 지분 변동",
             "events": [
                 {"title": "한미반도체 곽동신 회장 주식 매각", "summary": "보유지분 2% 장내매도, 세금 납부 목적", "type": "DISCLOSURE", "score": 15, "severity": "MEDIUM", "source": "DART"},
             ]},
            {"cat": "CREDIT", "name": "매출 급성장", "type": "ISSUE", "desc": "HBM 수혜 실적 급등",
             "events": [
                 {"title": "한미반도체 매출 전년비 180% 성장", "summary": "HBM 패키징 장비 독점 수혜, 영업이익률 45%", "type": "DISCLOSURE", "score": 3, "severity": "LOW", "source": "DART"},
             ]},
        ]
    },
    "Apple": {
        "entities": [
            {"cat": "LEGAL", "name": "EU 반독점 과징금", "type": "CASE", "desc": "유럽연합 독점규제",
             "events": [
                 {"title": "EU, Apple에 18억유로 과징금 부과", "summary": "앱스토어 결제 독점 행위 제재", "type": "NEWS", "score": 30, "severity": "HIGH", "source": "EU Commission"},
                 {"title": "Apple 미국 DOJ 반독점 소송", "summary": "스마트폰 시장 독점 행위 관련 연방소송 제기", "type": "NEWS", "score": 25, "severity": "HIGH", "source": "DOJ"},
             ]},
            {"cat": "SUPPLY", "name": "중국 생산 의존도", "type": "ISSUE", "desc": "중국 공장 의존도 리스크",
             "events": [
                 {"title": "Apple 인도 생산비중 25%로 확대", "summary": "중국 리스크 분산 위해 인도·베트남 생산 가속", "type": "NEWS", "score": 10, "severity": "MEDIUM", "source": "WSJ"},
             ]},
            {"cat": "OPS", "name": "AI 전략 지연", "type": "ISSUE", "desc": "Apple Intelligence 출시 지연",
             "events": [
                 {"title": "Apple Intelligence 중국 출시 무기한 연기", "summary": "중국 AI 규제로 현지 서비스 출시 불투명", "type": "NEWS", "score": 15, "severity": "MEDIUM", "source": "Bloomberg"},
             ]},
        ]
    },
    "NVIDIA": {
        "entities": [
            {"cat": "GOV", "name": "대중국 수출규제", "type": "ISSUE", "desc": "미국 대중국 AI칩 수출 통제",
             "events": [
                 {"title": "미 상무부 NVIDIA H20 중국 수출 금지", "summary": "중국향 AI 가속기 전면 수출 통제, 연간 매출 120억달러 영향", "type": "DISCLOSURE", "score": 40, "severity": "CRITICAL", "source": "BIS"},
                 {"title": "NVIDIA 중국 전용 칩 개발 중단", "summary": "수출규제 강화로 중국 맞춤형 AI칩 전략 포기", "type": "NEWS", "score": 20, "severity": "HIGH", "source": "Reuters"},
             ]},
            {"cat": "LEGAL", "name": "Arm 라이선스 분쟁", "type": "CASE", "desc": "Arm과 GPU 아키텍처 라이선스 소송",
             "events": [
                 {"title": "Arm, NVIDIA에 라이선스 해지 통보", "summary": "GPU 설계 관련 Arm 아키텍처 라이선스 분쟁 격화", "type": "NEWS", "score": 20, "severity": "HIGH", "source": "FT"},
             ]},
            {"cat": "SUPPLY", "name": "CoWoS 패키징 병목", "type": "ISSUE", "desc": "TSMC CoWoS 생산능력 한계",
             "events": [
                 {"title": "NVIDIA B200 출하 지연 3개월", "summary": "TSMC CoWoS 2.5D 패키징 생산능력 부족으로 납기 연기", "type": "NEWS", "score": 30, "severity": "HIGH", "source": "DigiTimes"},
             ]},
        ]
    },
    "LG에너지솔루션": {
        "entities": [
            {"cat": "OPS", "name": "미국 공장 가동률", "type": "ISSUE", "desc": "오하이오·미시간 공장 가동 현황",
             "events": [
                 {"title": "LG에너지솔루션 오하이오 공장 가동률 60%", "summary": "EV 수요 둔화로 생산라인 가동 축소", "type": "NEWS", "score": 20, "severity": "MEDIUM", "source": "한경"},
             ]},
            {"cat": "CREDIT", "name": "대규모 차입", "type": "ISSUE", "desc": "설비투자 자금조달",
             "events": [
                 {"title": "LG에너지솔루션 5조원 회사채 발행", "summary": "북미 배터리 공장 건설 자금 조달, 부채비율 상승", "type": "DISCLOSURE", "score": 25, "severity": "HIGH", "source": "DART"},
                 {"title": "무디스 LG에너지솔루션 등급전망 '부정적'", "summary": "설비투자 부담 및 EV 수요 불확실성 반영", "type": "NEWS", "score": 20, "severity": "HIGH", "source": "Moody's"},
             ]},
            {"cat": "ESG", "name": "배터리 재활용", "type": "ISSUE", "desc": "폐배터리 회수·재활용",
             "events": [
                 {"title": "LG에너지솔루션 폐배터리 회수체계 구축", "summary": "EU 배터리법 대응, 2025년부터 리사이클링 의무화", "type": "DISCLOSURE", "score": 5, "severity": "LOW", "source": "DART"},
             ]},
        ]
    },
    "Qualcomm": {
        "entities": [
            {"cat": "LEGAL", "name": "Arm 라이선스 소송", "type": "CASE", "desc": "Arm과 Nuvia 인수 관련 라이선스 분쟁",
             "events": [
                 {"title": "Qualcomm-Arm 라이선스 소송 배심 평결", "summary": "Nuvia 기술 기반 칩 설계 라이선스 유효 판결", "type": "NEWS", "score": 15, "severity": "MEDIUM", "source": "Reuters"},
             ]},
            {"cat": "GOV", "name": "EU 독점규제", "type": "CASE", "desc": "유럽 모바일AP 시장 독점 조사",
             "events": [
                 {"title": "EU Qualcomm 과징금 2.4억유로 확정", "summary": "3G 모뎀칩 시장 독점 행위에 대한 최종 판결", "type": "DISCLOSURE", "score": 20, "severity": "HIGH", "source": "EU Commission"},
             ]},
            {"cat": "OPS", "name": "PC용 AP 진출", "type": "ISSUE", "desc": "Snapdragon X Elite PC 시장 진출",
             "events": [
                 {"title": "Qualcomm Snapdragon X Elite 초기 판매 부진", "summary": "앱 호환성 문제로 Windows on ARM 채택률 저조", "type": "NEWS", "score": 10, "severity": "MEDIUM", "source": "The Verge"},
             ]},
        ]
    },
}


def make_id(prefix, *parts):
    raw = "".join(str(p) for p in parts)
    return f"{prefix}_{hashlib.md5(raw.encode()).hexdigest()[:8]}"


def create_company_with_categories(tx, company_data):
    """Company + 10개 RiskCategory 생성 (이미 존재하면 스킵)"""
    comp_name = company_data["name"]

    # Check if already exists
    existing = tx.run("MATCH (c:Company {name: $name}) RETURN c.name", {"name": comp_name}).single()
    if existing:
        print(f"  [SKIP] {comp_name} 이미 존재")
        return

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

    print(f"  [NEW] {comp_name} + 10 카테고리 생성")


def create_related_link(tx, main_name, related_name, relation, tier, dep):
    """HAS_RELATED 관계 생성 (이미 존재하면 스킵)"""
    existing = tx.run("""
        MATCH (m:Company {name: $main})-[r:HAS_RELATED]->(rel:Company {name: $related})
        RETURN r
    """, {"main": main_name, "related": related_name}).single()

    if existing:
        print(f"  [SKIP] {main_name} → {related_name} 관계 이미 존재")
        return

    tx.run("""
        MATCH (m:Company {name: $main}), (r:Company {name: $related})
        CREATE (m)-[:HAS_RELATED {relation: $relation, tier: $tier, dependencyScore: $dep}]->(r)
    """, {"main": main_name, "related": related_name, "relation": relation, "tier": tier, "dep": dep})
    print(f"  [LINK] {main_name} -[{relation}]-> {related_name} (dep: {dep})")


def update_dependency_score(tx, main_name, related_name, dep):
    """기존 관계에 dependencyScore 추가"""
    tx.run("""
        MATCH (m:Company {name: $main})-[r:HAS_RELATED]->(rel:Company {name: $related})
        SET r.dependencyScore = $dep
    """, {"main": main_name, "related": related_name, "dep": dep})
    print(f"  [UPD] {main_name} → {related_name} dependencyScore = {dep}")


def add_entities_and_events(tx, company_name, entities_data):
    """기업에 엔티티와 이벤트 추가"""
    count_ent = 0
    count_evt = 0

    for ent_info in entities_data:
        cat_code = ent_info["cat"]
        ent_name = ent_info["name"]
        ent_id = make_id("ENT", company_name, ent_name)

        # Check if entity already exists
        existing = tx.run("MATCH (e:RiskEntity {id: $id}) RETURN e.id", {"id": ent_id}).single()
        if existing:
            continue

        tx.run("""
            MATCH (c:Company {name: $companyName})-[:HAS_CATEGORY]->(rc:RiskCategory {code: $catCode})
            CREATE (e:RiskEntity {
                id: $entId, name: $name, type: $type, subType: $subType,
                position: $position, description: $desc,
                riskScore: 0, eventCount: 0, createdAt: datetime()
            })
            CREATE (rc)-[:HAS_ENTITY]->(e)
            SET rc.entityCount = rc.entityCount + 1
        """, {
            "companyName": company_name,
            "catCode": cat_code,
            "entId": ent_id,
            "name": ent_name,
            "type": ent_info.get("type", "ISSUE"),
            "subType": ent_info.get("subType", ""),
            "position": ent_info.get("position", ""),
            "desc": ent_info.get("desc", ""),
        })
        count_ent += 1

        # Add events
        for evt in ent_info.get("events", []):
            evt_id = make_id("EVT", ent_id, evt["title"])
            pub_date = datetime.now() - timedelta(days=random.randint(1, 60))

            tx.run("""
                MATCH (ent:RiskEntity {id: $entityId})
                CREATE (e:RiskEvent {
                    id: $evtId, title: $title, summary: $summary, type: $type,
                    score: $score, severity: $severity,
                    sourceName: $source, sourceUrl: '',
                    publishedAt: $publishedAt, createdAt: datetime(), isActive: true
                })
                CREATE (ent)-[:HAS_EVENT]->(e)
                SET ent.eventCount = ent.eventCount + 1,
                    ent.riskScore = ent.riskScore + $score
            """, {
                "entityId": ent_id,
                "evtId": evt_id,
                "title": evt["title"],
                "summary": evt["summary"],
                "type": evt.get("type", "NEWS"),
                "score": evt.get("score", 0),
                "severity": evt.get("severity", "MEDIUM"),
                "source": evt.get("source", ""),
                "publishedAt": pub_date.isoformat(),
            })
            count_evt += 1

    print(f"  [DATA] {company_name}: +{count_ent} 엔티티, +{count_evt} 이벤트")


def calculate_scores(tx):
    """점수 재계산 (전체)"""
    # Category scores
    tx.run("""
        MATCH (rc:RiskCategory)-[:HAS_ENTITY]->(ent:RiskEntity)
        WITH rc, SUM(ent.riskScore) AS totalScore, COUNT(ent) AS entCount
        SET rc.score = totalScore, rc.entityCount = entCount,
            rc.weightedScore = totalScore * rc.weight
    """)
    # Category event counts
    tx.run("""
        MATCH (rc:RiskCategory)-[:HAS_ENTITY]->(ent:RiskEntity)-[:HAS_EVENT]->(evt:RiskEvent)
        WITH rc, COUNT(evt) AS evtCount
        SET rc.eventCount = evtCount
    """)
    # Company direct scores
    tx.run("""
        MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
        WITH c, SUM(rc.weightedScore) AS directScore
        SET c.directScore = toInteger(directScore)
    """)
    # Company propagated scores
    tx.run("""
        MATCH (c:Company)-[:HAS_RELATED]->(r:Company)
        WITH c, SUM(r.directScore) * 0.3 AS propagatedScore
        SET c.propagatedScore = toInteger(propagatedScore)
    """)
    # Total + risk level
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
    print("  [OK] 전체 점수 재계산 완료")


def print_summary(tx):
    print("\n" + "=" * 60)
    result = tx.run("""
        MATCH (c:Company)
        OPTIONAL MATCH (c)-[:HAS_CATEGORY]->(rc:RiskCategory)-[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
        WITH c, COUNT(DISTINCT re) as ents, COUNT(DISTINCT ev) as evts
        OPTIONAL MATCH (c)-[:HAS_RELATED]->(rel:Company)
        RETURN c.name as name, c.sector as sector,
               c.totalRiskScore as score, c.riskLevel as level,
               ents, evts, collect(DISTINCT rel.name) as related
        ORDER BY c.totalRiskScore DESC
    """)
    for r in result:
        related = [x for x in (r["related"] or []) if x]
        print(f"  {r['name']:15s} | {r['sector']:8s} | score:{r['score']:4d} | {r['level']:7s} | {r['ents']}ent {r['evts']}evt | → {related}")

    counts = tx.run("""
        MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt
        ORDER BY label
    """)
    print("\n  [노드 합계]")
    for r in counts:
        print(f"    {r['label']}: {r['cnt']}개")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  관련기업 데이터 보강 스크립트")
    print("=" * 60)

    with driver.session(database=DATABASE) as session:
        # 1. 신규 관련기업 생성
        print("\n[1] 신규 관련기업 생성...")
        for comp in NEW_COMPANIES:
            session.execute_write(create_company_with_categories, comp)

        # 2. 관계 연결
        print("\n[2] HAS_RELATED 관계 생성...")
        for rel in NEW_RELATIONS:
            session.execute_write(create_related_link, rel["main"], rel["related"], rel["relation"], rel["tier"], rel["dep"])

        # 3. 기존 관계 dependencyScore 업데이트
        print("\n[3] 기존 관계 dependencyScore 업데이트...")
        for rel in EXISTING_RELATIONS_UPDATE:
            session.execute_write(update_dependency_score, rel["main"], rel["related"], rel["dep"])

        # 4. 엔티티+이벤트 추가
        print("\n[4] 엔티티 & 이벤트 추가...")
        for comp_name, data in COMPANY_DATA.items():
            session.execute_write(add_entities_and_events, comp_name, data["entities"])

        # 5. 점수 재계산
        print("\n[5] 점수 재계산...")
        session.execute_write(calculate_scores)

        # 6. 요약
        session.execute_read(print_summary)

    driver.close()
    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
