"""
Mock 데이터 투입 스크립트 - 7개 딜 + 관련기업 + RiskEntity + RiskEvent
==================================================================
App.tsx DEAL_RAW_DATA 7건에 대응하는 Neo4j 데이터 생성.
기존 코드(프론트/API/점수 로직) 수정 없음 — 데이터만 삽입.

Usage:
    python scripts/seed_mock_data.py
"""

import os
import sys
import pathlib
import uuid
from datetime import datetime, timedelta
import random

# Windows 콘솔 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 프로젝트 루트
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env.local")

from risk_engine.neo4j_client import Neo4jClient
from risk_engine.deal_manager import DealService
from risk_engine.v4.services.category_service import CategoryService
from risk_engine.v4.services.score_service import ScoreService


# ============================================================
# 7개 딜 정의
# ============================================================
DEALS = [
    {"name": "골든락 마이닝",       "sector": "광업",     "analyst": "최환석"},
    {"name": "오비탈 에어로스페이스", "sector": "우주항공", "analyst": "최환석"},
    {"name": "넥스트 로보틱스",      "sector": "로봇",     "analyst": "김민정"},
    {"name": "사이버다인 시스템즈",   "sector": "렌탈",     "analyst": "김민정"},
    {"name": "아르젠텀 리소스",      "sector": "제련",     "analyst": "박준혁"},
    {"name": "세미콘 퓨처테크",      "sector": "반도체",   "analyst": "박준혁"},
    {"name": "퀀텀 칩 솔루션",       "sector": "소재",     "analyst": "이서연"},
]

# ============================================================
# 관련기업 (전이 리스크용)
# ============================================================
RELATED_COMPANIES = {
    "골든락 마이닝": [
        {"name": "코리아 메탈 트레이딩", "sector": "금속유통", "relation": "원자재 납품", "tier": 1},
        {"name": "글로벌 지오서베이",     "sector": "지질조사", "relation": "탐사 용역",   "tier": 2},
    ],
    "오비탈 에어로스페이스": [
        {"name": "스타링크 커뮤니케이션", "sector": "위성통신", "relation": "합작법인",   "tier": 1},
        {"name": "에어로젯 프로펄전",     "sector": "추진체",   "relation": "핵심부품사", "tier": 1},
        {"name": "제니스 위성시스템",     "sector": "위성제조", "relation": "합작개발",   "tier": 1},
    ],
    "넥스트 로보틱스": [
        {"name": "비전AI 테크놀로지",     "sector": "AI/영상인식", "relation": "기술제휴",   "tier": 1},
        {"name": "프리시전 기어텍",       "sector": "정밀부품",    "relation": "핵심부품사", "tier": 1},
        {"name": "스마트팩토리 코리아",   "sector": "공장자동화",  "relation": "고객사",     "tier": 2},
    ],
    "사이버다인 시스템즈": [
        {"name": "유니렌탈 캐피탈",       "sector": "리스금융",   "relation": "자금조달",   "tier": 1},
        {"name": "테크서플라이 코리아",   "sector": "장비유통",   "relation": "장비공급사", "tier": 1},
        {"name": "디지털 서비스넷",       "sector": "IT서비스",   "relation": "유지보수",   "tier": 2},
    ],
    "아르젠텀 리소스": [
        {"name": "남미 실버마인",         "sector": "은광채굴",   "relation": "원광석 공급", "tier": 1},
        {"name": "코리아 리파이닝",       "sector": "정련가공",   "relation": "위탁가공",   "tier": 1},
    ],
    "세미콘 퓨처테크": [
        {"name": "실리콘밸리 웨이퍼",     "sector": "웨이퍼",     "relation": "원자재 공급", "tier": 1},
        {"name": "나노패킹 솔루션",       "sector": "패키징",     "relation": "후공정 파트너", "tier": 1},
        {"name": "칩테스트 프로",         "sector": "반도체검사", "relation": "테스트 하우스", "tier": 2},
    ],
    "퀀텀 칩 솔루션": [
        {"name": "어드밴스드 머티리얼",   "sector": "특수소재",   "relation": "원료공급사",   "tier": 1},
        {"name": "하이퍼 코팅테크",       "sector": "표면처리",   "relation": "후공정 파트너", "tier": 2},
    ],
}

# ============================================================
# 기업별 RiskEntity + RiskEvent Mock 데이터
# ============================================================
# 점수 설계 원칙:
#   - CategoryService.update_category_scores: Entity.riskScore = SUM(Event.score * decay)
#   - Category.score = SUM(Entity.riskScore) (cap 200)
#   - Category.weightedScore = score * weight
#   - ScoreService.calculate_company_score:
#       direct = SUM(category.weightedScore)
#       propagated = SUM(related.totalRiskScore * 0.3) (cap 30)
#       critical_boost = +15~+40 if Event.score >= 80
#       total = min(100, direct + propagated + critical_boost)
#   - riskLevel: CRITICAL if critical_boost > 0, else >=60 CRITICAL, >=35 WARNING, else PASS

def _days_ago(days):
    """publishedAt ISO 문자열 (days일 전)"""
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")

def _eid():
    return f"ENT_{uuid.uuid4().hex[:12]}"

def _evid():
    return f"EVT_{uuid.uuid4().hex[:12]}"


MOCK_DATA = {
    # ──────────────────────────────────────────────
    # 1. 골든락 마이닝 — PASS ~20
    #    계산: SHARE 40*0.3=12→w12*0.15=1.8, EXEC 50*0.3=15→w15*0.15=2.25,
    #          OPS 60*1.0=60→w60*0.10=6, LEGAL 55*0.55=30→w30*0.12=3.6,
    #          ESG 40*0.30=12→w12*0.08=0.96, CREDIT 35*0.55=19→w19*0.15=2.85
    #    direct ≈ 18~20
    # ──────────────────────────────────────────────
    "골든락 마이닝": {
        "SHARE": [
            {"entity": {"name": "김태호", "type": "SHAREHOLDER", "position": "최대주주 (32%)"},
             "events": [
                 {"title": "골든락 마이닝 대주주 지분 소폭 변동", "type": "DISCLOSURE", "score": 40, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(20)},
             ]},
        ],
        "EXEC": [
            {"entity": {"name": "박정훈", "type": "PERSON", "position": "대표이사"},
             "events": [
                 {"title": "골든락 마이닝 대표이사 연임 과정 잡음", "type": "NEWS", "score": 50, "severity": "LOW",
                  "sourceName": "매일경제", "publishedAt": _days_ago(20)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "광산 안전점검 이슈", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "골든락 마이닝 광산 일부 구역 안전 지적사항", "type": "NEWS", "score": 60, "severity": "MEDIUM",
                  "sourceName": "한국경제", "publishedAt": _days_ago(2)},
             ]},
        ],
        "LEGAL": [
            {"entity": {"name": "환경소송", "type": "CASE", "position": ""},
             "events": [
                 {"title": "골든락 마이닝 광산 먼지 관련 주민 민원", "type": "NEWS", "score": 55, "severity": "MEDIUM",
                  "sourceName": "서울경제", "publishedAt": _days_ago(10)},
             ]},
        ],
        "ESG": [
            {"entity": {"name": "환경 모니터링", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "골든락 마이닝 탄소배출 저감 지연 보도", "type": "NEWS", "score": 40, "severity": "LOW",
                  "sourceName": "서울경제", "publishedAt": _days_ago(18)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "차입 리스크", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "골든락 마이닝 차입금 소폭 증가", "type": "DISCLOSURE", "score": 35, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(10)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 2. 오비탈 에어로스페이스 — CRITICAL ~72
    #    direct ~45, propagated ~12 (관련기업2), critical_boost +15 (score>=80 이벤트 1개)
    #    → total ~72, CRITICAL (boost>0)
    # ──────────────────────────────────────────────
    "오비탈 에어로스페이스": {
        "CREDIT": [
            {"entity": {"name": "자본잠식 이슈", "type": "CASE", "position": ""},
             "events": [
                 {"title": "오비탈 에어로스페이스 3분기 자본잠식 위기", "type": "DISCLOSURE", "score": 85, "severity": "CRITICAL",
                  "sourceName": "DART", "publishedAt": _days_ago(5)},
             ]},
            {"entity": {"name": "채권단 협의", "type": "CASE", "position": ""},
             "events": [
                 {"title": "오비탈 에어로스페이스 채권단 자율협의 개시", "type": "NEWS", "score": 55, "severity": "HIGH",
                  "sourceName": "한국경제", "publishedAt": _days_ago(4)},
             ]},
        ],
        "LEGAL": [
            {"entity": {"name": "SEC 조사", "type": "CASE", "position": ""},
             "events": [
                 {"title": "오비탈 에어로스페이스 미국 SEC 예비조사 착수", "type": "NEWS", "score": 55, "severity": "HIGH",
                  "sourceName": "로이터", "publishedAt": _days_ago(7)},
             ]},
        ],
        "EXEC": [
            {"entity": {"name": "이강일", "type": "PERSON", "position": "대표이사"},
             "events": [
                 {"title": "오비탈 대표이사 배임혐의 고발", "type": "NEWS", "score": 60, "severity": "HIGH",
                  "sourceName": "SBS", "publishedAt": _days_ago(5)},
             ]},
            {"entity": {"name": "최영수", "type": "PERSON", "position": "CFO"},
             "events": [
                 {"title": "오비탈 CFO 전격 사임", "type": "NEWS", "score": 40, "severity": "MEDIUM",
                  "sourceName": "매일경제", "publishedAt": _days_ago(7)},
             ]},
        ],
        "GOV": [
            {"entity": {"name": "내부통제 부실", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "오비탈 에어로스페이스 내부통제 미비 지적", "type": "DISCLOSURE", "score": 40, "severity": "MEDIUM",
                  "sourceName": "DART", "publishedAt": _days_ago(10)},
             ]},
        ],
        "SHARE": [
            {"entity": {"name": "박재현", "type": "SHAREHOLDER", "position": "2대주주 (18%)"},
             "events": [
                 {"title": "오비탈 2대주주 지분 대량 매각", "type": "DISCLOSURE", "score": 50, "severity": "HIGH",
                  "sourceName": "DART", "publishedAt": _days_ago(7)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "발사체 개발 지연", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "오비탈 차세대 발사체 일정 6개월 지연", "type": "NEWS", "score": 35, "severity": "MEDIUM",
                  "sourceName": "조선비즈", "publishedAt": _days_ago(8)},
             ]},
        ],
        "SUPPLY": [
            {"entity": {"name": "핵심부품 수급 불안", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "에어로젯 핵심부품 납품 지연 통보", "type": "NEWS", "score": 30, "severity": "MEDIUM",
                  "sourceName": "전자신문", "publishedAt": _days_ago(9)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 3. 넥스트 로보틱스 — WARNING ~42
    #    direct ~37, propagated ~5 (관련기업1), critical_boost 0
    #    → total ~42, WARNING (35~59)
    # ──────────────────────────────────────────────
    "넥스트 로보틱스": {
        "LEGAL": [
            {"entity": {"name": "특허 소송", "type": "CASE", "position": ""},
             "events": [
                 {"title": "넥스트 로보틱스 특허침해 소송 피소", "type": "NEWS", "score": 60, "severity": "HIGH",
                  "sourceName": "한국경제", "publishedAt": _days_ago(5)},
                 {"title": "넥스트 로보틱스 특허소송 1심 패소", "type": "NEWS", "score": 50, "severity": "MEDIUM",
                  "sourceName": "매일경제", "publishedAt": _days_ago(10)},
             ]},
        ],
        "EXEC": [
            {"entity": {"name": "정우진", "type": "PERSON", "position": "CTO"},
             "events": [
                 {"title": "넥스트 로보틱스 CTO 경쟁사 이직설", "type": "NEWS", "score": 50, "severity": "MEDIUM",
                  "sourceName": "디지털타임스", "publishedAt": _days_ago(3)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "양산 일정 지연", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "넥스트 로보틱스 산업용 로봇 양산 3개월 지연", "type": "NEWS", "score": 45, "severity": "MEDIUM",
                  "sourceName": "전자신문", "publishedAt": _days_ago(5)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "운전자금 이슈", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "넥스트 로보틱스 운전자금 확보 위해 CB 발행", "type": "DISCLOSURE", "score": 50, "severity": "MEDIUM",
                  "sourceName": "DART", "publishedAt": _days_ago(7)},
             ]},
        ],
        "SHARE": [
            {"entity": {"name": "한성호", "type": "SHAREHOLDER", "position": "최대주주 (25%)"},
             "events": [
                 {"title": "넥스트 로보틱스 최대주주 담보제공 공시", "type": "DISCLOSURE", "score": 45, "severity": "MEDIUM",
                  "sourceName": "DART", "publishedAt": _days_ago(7)},
             ]},
        ],
        "GOV": [
            {"entity": {"name": "이사회 갈등", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "넥스트 로보틱스 이사회 내 경영권 갈등 보도", "type": "NEWS", "score": 40, "severity": "MEDIUM",
                  "sourceName": "조선비즈", "publishedAt": _days_ago(7)},
             ]},
        ],
        "ESG": [
            {"entity": {"name": "안전사고", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "넥스트 로보틱스 공장 안전사고 1건 발생", "type": "NEWS", "score": 35, "severity": "MEDIUM",
                  "sourceName": "MBC", "publishedAt": _days_ago(10)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 4. 사이버다인 시스템즈 — WARNING ~38
    #    direct ~38, propagated 0, critical_boost 0
    # ──────────────────────────────────────────────
    "사이버다인 시스템즈": {
        "OPS": [
            {"entity": {"name": "렌탈 자산 부실", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "사이버다인 렌탈 자산 대손율 급증", "type": "NEWS", "score": 70, "severity": "HIGH",
                  "sourceName": "한국경제", "publishedAt": _days_ago(2)},
                 {"title": "사이버다인 장비 렌탈 연체율 15% 돌파", "type": "NEWS", "score": 55, "severity": "MEDIUM",
                  "sourceName": "매일경제", "publishedAt": _days_ago(5)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "신용등급 하향", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "사이버다인 시스템즈 신용등급 BB+ → BB 하향", "type": "DISCLOSURE", "score": 65, "severity": "MEDIUM",
                  "sourceName": "한국신용평가", "publishedAt": _days_ago(3)},
             ]},
        ],
        "EXEC": [
            {"entity": {"name": "윤대성", "type": "PERSON", "position": "대표이사"},
             "events": [
                 {"title": "사이버다인 대표이사 개인 채무 논란", "type": "NEWS", "score": 55, "severity": "MEDIUM",
                  "sourceName": "SBS", "publishedAt": _days_ago(4)},
             ]},
        ],
        "LEGAL": [
            {"entity": {"name": "소비자 소송", "type": "CASE", "position": ""},
             "events": [
                 {"title": "사이버다인 렌탈 이용자 집단소송 제기", "type": "NEWS", "score": 60, "severity": "MEDIUM",
                  "sourceName": "MBC", "publishedAt": _days_ago(5)},
             ]},
        ],
        "AUDIT": [
            {"entity": {"name": "감사의견 한정", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "사이버다인 시스템즈 감사의견 한정 가능성 보도", "type": "NEWS", "score": 55, "severity": "MEDIUM",
                  "sourceName": "조선비즈", "publishedAt": _days_ago(5)},
             ]},
        ],
        "SHARE": [
            {"entity": {"name": "강민구", "type": "SHAREHOLDER", "position": "최대주주 (30%)"},
             "events": [
                 {"title": "사이버다인 최대주주 지분 5% 매각", "type": "DISCLOSURE", "score": 50, "severity": "MEDIUM",
                  "sourceName": "DART", "publishedAt": _days_ago(6)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 5. 아르젠텀 리소스 — PASS ~12
    #    direct ~12, propagated 0, critical_boost 0
    # ──────────────────────────────────────────────
    "아르젠텀 리소스": {
        "ESG": [
            {"entity": {"name": "환경 점검", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "아르젠텀 리소스 폐수처리 시설 점검 지적", "type": "NEWS", "score": 45, "severity": "MEDIUM",
                  "sourceName": "서울경제", "publishedAt": _days_ago(5)},
             ]},
        ],
        "SHARE": [
            {"entity": {"name": "이준택", "type": "SHAREHOLDER", "position": "최대주주 (45%)"},
             "events": [
                 {"title": "아르젠텀 리소스 대주주 일부 지분 이동", "type": "DISCLOSURE", "score": 30, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(15)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "생산 안정성", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "아르젠텀 리소스 제련소 일부 설비 노후화 보도", "type": "NEWS", "score": 35, "severity": "LOW",
                  "sourceName": "한국경제", "publishedAt": _days_ago(10)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "차입부담", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "아르젠텀 리소스 차입비율 소폭 상승", "type": "DISCLOSURE", "score": 25, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(12)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 6. 세미콘 퓨처테크 — PASS ~25
    #    direct ~25, propagated 0, critical_boost 0
    # ──────────────────────────────────────────────
    "세미콘 퓨처테크": {
        "LEGAL": [
            {"entity": {"name": "기술 분쟁", "type": "CASE", "position": ""},
             "events": [
                 {"title": "세미콘 퓨처테크 기술 라이선스 분쟁 조정중", "type": "NEWS", "score": 65, "severity": "MEDIUM",
                  "sourceName": "전자신문", "publishedAt": _days_ago(3)},
             ]},
        ],
        "EXEC": [
            {"entity": {"name": "김현우", "type": "PERSON", "position": "대표이사"},
             "events": [
                 {"title": "세미콘 퓨처테크 전 임원 횡령 혐의 수사", "type": "NEWS", "score": 50, "severity": "MEDIUM",
                  "sourceName": "매일경제", "publishedAt": _days_ago(5)},
             ]},
        ],
        "SUPPLY": [
            {"entity": {"name": "원자재 가격 변동", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "반도체 원자재 가격 10% 상승 영향", "type": "NEWS", "score": 50, "severity": "MEDIUM",
                  "sourceName": "조선비즈", "publishedAt": _days_ago(2)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "생산라인 증설", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "세미콘 퓨처테크 3공장 증설 일정 지연", "type": "NEWS", "score": 55, "severity": "MEDIUM",
                  "sourceName": "한국경제", "publishedAt": _days_ago(5)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "차입금 증가", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "세미콘 퓨처테크 시설투자 차입 증가", "type": "DISCLOSURE", "score": 40, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(7)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 7. 퀀텀 칩 솔루션 — PASS ~18
    #    direct ~18, propagated 0, critical_boost 0
    # ──────────────────────────────────────────────
    "퀀텀 칩 솔루션": {
        "SHARE": [
            {"entity": {"name": "문성민", "type": "SHAREHOLDER", "position": "최대주주 (38%)"},
             "events": [
                 {"title": "퀀텀 칩 솔루션 대주주 지분 담보 설정", "type": "DISCLOSURE", "score": 40, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(7)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "소재 품질 이슈", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "퀀텀 칩 솔루션 소재 품질 검사 지연", "type": "NEWS", "score": 50, "severity": "MEDIUM",
                  "sourceName": "전자신문", "publishedAt": _days_ago(3)},
             ]},
        ],
        "ESG": [
            {"entity": {"name": "안전관리", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "퀀텀 칩 솔루션 화학물질 관리 미흡 지적", "type": "NEWS", "score": 35, "severity": "LOW",
                  "sourceName": "서울경제", "publishedAt": _days_ago(10)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "재무 안정성", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "퀀텀 칩 솔루션 운전자금 일시 부족 보도", "type": "DISCLOSURE", "score": 35, "severity": "LOW",
                  "sourceName": "한국신용평가", "publishedAt": _days_ago(10)},
             ]},
        ],
        "LEGAL": [
            {"entity": {"name": "소재 계약분쟁", "type": "CASE", "position": ""},
             "events": [
                 {"title": "퀀텀 칩 솔루션 납품 계약 분쟁 조정", "type": "NEWS", "score": 30, "severity": "LOW",
                  "sourceName": "전자신문", "publishedAt": _days_ago(12)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업들 (오비탈 → 고위험, 넥스트 → 중위험)
    # ──────────────────────────────────────────────
    "스타링크 커뮤니케이션": {
        "CREDIT": [
            {"entity": {"name": "자금난", "type": "CASE", "position": ""},
             "events": [
                 {"title": "스타링크 커뮤니케이션 자금난 심화", "type": "NEWS", "score": 75, "severity": "HIGH",
                  "sourceName": "한국경제", "publishedAt": _days_ago(2)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "위성 발사 실패", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "스타링크 상업 위성 발사 실패", "type": "NEWS", "score": 65, "severity": "HIGH",
                  "sourceName": "로이터", "publishedAt": _days_ago(3)},
             ]},
        ],
    },

    "에어로젯 프로펄전": {
        "LEGAL": [
            {"entity": {"name": "수출 규제 위반", "type": "CASE", "position": ""},
             "events": [
                 {"title": "에어로젯 프로펄전 수출규제 위반 조사", "type": "NEWS", "score": 70, "severity": "HIGH",
                  "sourceName": "블룸버그", "publishedAt": _days_ago(2)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "생산 중단", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "에어로젯 주요 생산라인 일시 중단", "type": "NEWS", "score": 55, "severity": "MEDIUM",
                  "sourceName": "디지털타임스", "publishedAt": _days_ago(3)},
             ]},
        ],
    },

    "비전AI 테크놀로지": {
        "EXEC": [
            {"entity": {"name": "이상훈", "type": "PERSON", "position": "대표이사"},
             "events": [
                 {"title": "비전AI 테크놀로지 대표이사 교체", "type": "NEWS", "score": 40, "severity": "MEDIUM",
                  "sourceName": "매일경제", "publishedAt": _days_ago(3)},
             ]},
        ],
        "LEGAL": [
            {"entity": {"name": "데이터 프라이버시", "type": "CASE", "position": ""},
             "events": [
                 {"title": "비전AI 개인정보 수집 위반 과태료 부과", "type": "NEWS", "score": 50, "severity": "MEDIUM",
                  "sourceName": "한국경제", "publishedAt": _days_ago(5)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업 — 골든락 마이닝
    # ──────────────────────────────────────────────
    "코리아 메탈 트레이딩": {
        "SUPPLY": [
            {"entity": {"name": "원자재 수급 변동", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "코리아 메탈 트레이딩 금속 원자재 가격 급등 영향", "type": "NEWS", "score": 35, "severity": "LOW",
                  "sourceName": "한국경제", "publishedAt": _days_ago(5)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "매출채권 회수 지연", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "코리아 메탈 트레이딩 매출채권 회수율 하락", "type": "DISCLOSURE", "score": 30, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(8)},
             ]},
        ],
    },

    "글로벌 지오서베이": {
        "OPS": [
            {"entity": {"name": "탐사 장비 노후화", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "글로벌 지오서베이 탐사 장비 교체 지연", "type": "NEWS", "score": 25, "severity": "LOW",
                  "sourceName": "서울경제", "publishedAt": _days_ago(12)},
             ]},
        ],
        "ESG": [
            {"entity": {"name": "환경영향 평가", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "글로벌 지오서베이 해외 탐사 환경영향 지적", "type": "NEWS", "score": 30, "severity": "LOW",
                  "sourceName": "매일경제", "publishedAt": _days_ago(15)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업 — 오비탈 에어로스페이스 (추가)
    # ──────────────────────────────────────────────
    "제니스 위성시스템": {
        "OPS": [
            {"entity": {"name": "위성 조립 지연", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "제니스 위성시스템 차세대 위성 조립 일정 지연", "type": "NEWS", "score": 55, "severity": "MEDIUM",
                  "sourceName": "전자신문", "publishedAt": _days_ago(3)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "자금 조달 난항", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "제니스 위성시스템 시리즈C 투자유치 난항", "type": "NEWS", "score": 50, "severity": "MEDIUM",
                  "sourceName": "한국경제", "publishedAt": _days_ago(5)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업 — 넥스트 로보틱스 (추가)
    # ──────────────────────────────────────────────
    "프리시전 기어텍": {
        "SUPPLY": [
            {"entity": {"name": "정밀부품 납기 지연", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "프리시전 기어텍 핵심 감속기 납기 2주 지연", "type": "NEWS", "score": 40, "severity": "MEDIUM",
                  "sourceName": "디지털타임스", "publishedAt": _days_ago(4)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "품질 검사 이슈", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "프리시전 기어텍 일부 제품 품질 불량률 상승", "type": "NEWS", "score": 35, "severity": "LOW",
                  "sourceName": "전자신문", "publishedAt": _days_ago(7)},
             ]},
        ],
    },

    "스마트팩토리 코리아": {
        "CREDIT": [
            {"entity": {"name": "투자비 회수 지연", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "스마트팩토리 코리아 설비투자 회수율 저조", "type": "DISCLOSURE", "score": 25, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(10)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업 — 사이버다인 시스템즈
    # ──────────────────────────────────────────────
    "유니렌탈 캐피탈": {
        "CREDIT": [
            {"entity": {"name": "연체율 증가", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "유니렌탈 캐피탈 리스 연체율 급등", "type": "NEWS", "score": 45, "severity": "MEDIUM",
                  "sourceName": "한국경제", "publishedAt": _days_ago(3)},
             ]},
        ],
        "LEGAL": [
            {"entity": {"name": "금융감독 조치", "type": "CASE", "position": ""},
             "events": [
                 {"title": "유니렌탈 캐피탈 금감원 경영개선 권고", "type": "NEWS", "score": 40, "severity": "MEDIUM",
                  "sourceName": "매일경제", "publishedAt": _days_ago(5)},
             ]},
        ],
    },

    "테크서플라이 코리아": {
        "SUPPLY": [
            {"entity": {"name": "장비 수급 불안", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "테크서플라이 코리아 해외 장비 수입 지연", "type": "NEWS", "score": 40, "severity": "MEDIUM",
                  "sourceName": "전자신문", "publishedAt": _days_ago(4)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "물류 차질", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "테크서플라이 코리아 물류센터 이전으로 납기 차질", "type": "NEWS", "score": 35, "severity": "LOW",
                  "sourceName": "서울경제", "publishedAt": _days_ago(6)},
             ]},
        ],
    },

    "디지털 서비스넷": {
        "OPS": [
            {"entity": {"name": "서비스 장애", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "디지털 서비스넷 시스템 장애로 서비스 일시 중단", "type": "NEWS", "score": 25, "severity": "LOW",
                  "sourceName": "디지털타임스", "publishedAt": _days_ago(7)},
             ]},
        ],
        "ESG": [
            {"entity": {"name": "개인정보 관리", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "디지털 서비스넷 고객 데이터 관리 미흡 지적", "type": "NEWS", "score": 20, "severity": "LOW",
                  "sourceName": "매일경제", "publishedAt": _days_ago(10)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업 — 아르젠텀 리소스
    # ──────────────────────────────────────────────
    "남미 실버마인": {
        "OPS": [
            {"entity": {"name": "채굴 작업 중단", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "남미 실버마인 현지 광산 일부 작업 중단", "type": "NEWS", "score": 30, "severity": "LOW",
                  "sourceName": "로이터", "publishedAt": _days_ago(5)},
             ]},
        ],
        "LEGAL": [
            {"entity": {"name": "현지 규제 리스크", "type": "CASE", "position": ""},
             "events": [
                 {"title": "남미 실버마인 현지 정부 환경 규제 강화 영향", "type": "NEWS", "score": 25, "severity": "LOW",
                  "sourceName": "블룸버그", "publishedAt": _days_ago(8)},
             ]},
        ],
    },

    "코리아 리파이닝": {
        "OPS": [
            {"entity": {"name": "정련 설비 보수", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "코리아 리파이닝 주요 설비 정기보수 일정 연장", "type": "NEWS", "score": 30, "severity": "LOW",
                  "sourceName": "한국경제", "publishedAt": _days_ago(6)},
             ]},
        ],
        "ESG": [
            {"entity": {"name": "배출 기준 초과", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "코리아 리파이닝 대기오염 배출 기준 일시 초과", "type": "NEWS", "score": 25, "severity": "LOW",
                  "sourceName": "서울경제", "publishedAt": _days_ago(10)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업 — 세미콘 퓨처테크
    # ──────────────────────────────────────────────
    "실리콘밸리 웨이퍼": {
        "SUPPLY": [
            {"entity": {"name": "웨이퍼 공급 불안", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "실리콘밸리 웨이퍼 원재료 가격 상승 전가 우려", "type": "NEWS", "score": 35, "severity": "LOW",
                  "sourceName": "전자신문", "publishedAt": _days_ago(4)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "생산 가동률 저하", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "실리콘밸리 웨이퍼 공장 가동률 80% 하회", "type": "NEWS", "score": 30, "severity": "LOW",
                  "sourceName": "한국경제", "publishedAt": _days_ago(7)},
             ]},
        ],
    },

    "나노패킹 솔루션": {
        "OPS": [
            {"entity": {"name": "패키징 불량", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "나노패킹 솔루션 일부 공정 불량률 상승 보도", "type": "NEWS", "score": 35, "severity": "LOW",
                  "sourceName": "디지털타임스", "publishedAt": _days_ago(5)},
             ]},
        ],
        "CREDIT": [
            {"entity": {"name": "설비투자 부담", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "나노패킹 솔루션 신규 장비 투자 부담 증가", "type": "DISCLOSURE", "score": 30, "severity": "LOW",
                  "sourceName": "DART", "publishedAt": _days_ago(8)},
             ]},
        ],
    },

    "칩테스트 프로": {
        "OPS": [
            {"entity": {"name": "검사 장비 노후", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "칩테스트 프로 검사 장비 교체 일정 지연", "type": "NEWS", "score": 25, "severity": "LOW",
                  "sourceName": "전자신문", "publishedAt": _days_ago(10)},
             ]},
        ],
    },

    # ──────────────────────────────────────────────
    # 관련기업 — 퀀텀 칩 솔루션
    # ──────────────────────────────────────────────
    "어드밴스드 머티리얼": {
        "SUPPLY": [
            {"entity": {"name": "특수소재 수급", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "어드밴스드 머티리얼 핵심 원료 수입선 다변화 추진", "type": "NEWS", "score": 30, "severity": "LOW",
                  "sourceName": "한국경제", "publishedAt": _days_ago(5)},
             ]},
        ],
        "OPS": [
            {"entity": {"name": "연구개발 일정 지연", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "어드밴스드 머티리얼 신소재 개발 일정 소폭 지연", "type": "NEWS", "score": 25, "severity": "LOW",
                  "sourceName": "매일경제", "publishedAt": _days_ago(8)},
             ]},
        ],
    },

    "하이퍼 코팅테크": {
        "OPS": [
            {"entity": {"name": "코팅 공정 이슈", "type": "ISSUE", "position": ""},
             "events": [
                 {"title": "하이퍼 코팅테크 코팅 공정 수율 일시 저하", "type": "NEWS", "score": 20, "severity": "LOW",
                  "sourceName": "전자신문", "publishedAt": _days_ago(7)},
             ]},
        ],
    },
}


# ============================================================
# 실행 함수
# ============================================================

def step1_init_graph(client):
    """Step 1: 전체 삭제 + 인덱스 생성"""
    print("\n" + "=" * 60)
    print("  Step 1: 그래프 초기화 (전체 삭제 + 인덱스)")
    print("=" * 60)

    # init_graph_v7.py --clear 와 동일한 로직
    from neo4j import GraphDatabase
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    with driver.session(database=DATABASE) as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("  [OK] 기존 데이터 모두 삭제")

        indexes = [
            "CREATE INDEX deal_id IF NOT EXISTS FOR (d:Deal) ON (d.id)",
            "CREATE INDEX company_id IF NOT EXISTS FOR (c:Company) ON (c.id)",
            "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "CREATE INDEX company_corpcode IF NOT EXISTS FOR (c:Company) ON (c.corpCode)",
            "CREATE INDEX category_id IF NOT EXISTS FOR (c:RiskCategory) ON (c.id)",
            "CREATE INDEX category_code IF NOT EXISTS FOR (c:RiskCategory) ON (c.code)",
            "CREATE INDEX entity_id IF NOT EXISTS FOR (e:RiskEntity) ON (e.id)",
            "CREATE INDEX event_id IF NOT EXISTS FOR (e:RiskEvent) ON (e.id)",
        ]
        for idx in indexes:
            try:
                session.run(idx)
            except Exception:
                pass
        print("  [OK] 인덱스 8개 생성")
    driver.close()


def step2_create_deals(deal_service):
    """Step 2: 7개 딜 생성"""
    print("\n" + "=" * 60)
    print("  Step 2: 7개 딜 생성")
    print("=" * 60)

    for d in DEALS:
        result = deal_service.create_deal(d["name"], d["sector"], d["analyst"])
        print(f"  [OK] {result['dealId']} → {result['companyName']} ({result['sector']})")


def step3_create_related(client, deal_service):
    """Step 3: 관련기업 생성 + HAS_RELATED"""
    print("\n" + "=" * 60)
    print("  Step 3: 관련기업 생성")
    print("=" * 60)

    for main_name, related_list in RELATED_COMPANIES.items():
        for rel in related_list:
            # Company + 10 Categories 생성
            deal_service._create_company_with_categories(rel["name"], rel["sector"])

            # HAS_RELATED 관계
            client.execute_write("""
                MATCH (m:Company {name: $mainName}), (r:Company {name: $relName})
                MERGE (m)-[rel:HAS_RELATED]->(r)
                SET rel.relation = $relation, rel.tier = $tier
            """, {
                "mainName": main_name,
                "relName": rel["name"],
                "relation": rel["relation"],
                "tier": rel["tier"],
            })
            print(f"  [OK] {main_name} → {rel['name']} ({rel['relation']})")


def step4_insert_entities_events(client):
    """Step 4: RiskEntity + RiskEvent 대량 삽입"""
    print("\n" + "=" * 60)
    print("  Step 4: RiskEntity + RiskEvent 삽입")
    print("=" * 60)

    total_entities = 0
    total_events = 0

    for company_name, categories in MOCK_DATA.items():
        company_entities = 0
        company_events = 0

        for cat_code, entities in categories.items():
            cat_id = f"RC_{company_name}_{cat_code}"

            for ent_data in entities:
                ent = ent_data["entity"]
                ent_id = _eid()

                # RiskEntity 생성 + HAS_ENTITY 관계
                client.execute_write("""
                    MATCH (rc:RiskCategory {id: $catId})
                    CREATE (re:RiskEntity {
                        id: $entId,
                        name: $name,
                        type: $type,
                        position: $position,
                        riskScore: 0,
                        tier: CASE WHEN $type IN ['PERSON', 'SHAREHOLDER'] THEN 1 ELSE 2 END,
                        createdAt: datetime()
                    })
                    CREATE (rc)-[:HAS_ENTITY]->(re)
                """, {
                    "catId": cat_id,
                    "entId": ent_id,
                    "name": ent["name"],
                    "type": ent["type"],
                    "position": ent.get("position", ""),
                })
                company_entities += 1

                # RiskEvent 생성 + HAS_EVENT 관계
                for evt in ent_data["events"]:
                    evt_id = _evid()
                    client.execute_write("""
                        MATCH (re:RiskEntity {id: $entId})
                        CREATE (ev:RiskEvent {
                            id: $evtId,
                            title: $title,
                            summary: $title,
                            type: $type,
                            score: $score,
                            severity: $severity,
                            sourceName: $sourceName,
                            publishedAt: $publishedAt,
                            createdAt: datetime()
                        })
                        CREATE (re)-[:HAS_EVENT]->(ev)
                    """, {
                        "entId": ent_id,
                        "evtId": evt_id,
                        "title": evt["title"],
                        "type": evt["type"],
                        "score": evt["score"],
                        "severity": evt["severity"],
                        "sourceName": evt["sourceName"],
                        "publishedAt": evt["publishedAt"],
                    })
                    company_events += 1

        total_entities += company_entities
        total_events += company_events
        print(f"  [OK] {company_name}: {company_entities} entities, {company_events} events")

    print(f"\n  총 합계: {total_entities} entities, {total_events} events")


def step5_calculate_scores(client):
    """Step 5: 점수 계산 (기존 서비스 호출)"""
    print("\n" + "=" * 60)
    print("  Step 5: 점수 계산")
    print("=" * 60)

    cat_service = CategoryService(client)
    score_service = ScoreService(client)

    # 관련기업 먼저 점수 계산 (전이 리스크 반영을 위해)
    related_names = []
    for related_list in RELATED_COMPANIES.values():
        for rel in related_list:
            related_names.append(rel["name"])

    all_names = related_names + [d["name"] for d in DEALS]

    for name in all_names:
        cat_scores = cat_service.update_category_scores(name)
        score_result = score_service.calculate_company_score(name)
        print(f"  [{name}] direct={score_result['direct']}, propagated={score_result['propagated']}, "
              f"boost={score_result['criticalBoost']}, total={score_result['total']}, level={score_result['riskLevel']}")


def step6_verify(client):
    """Step 6: 검증"""
    print("\n" + "=" * 60)
    print("  Step 6: 검증")
    print("=" * 60)

    # 딜 목록
    deal_service = DealService(client)
    deals = deal_service.list_deals()

    print("\n  [딜 목록]")
    print(f"  {'No.':<4} {'딜 ID':<28} {'기업명':<20} {'섹터':<10} {'점수':<6} {'상태':<10}")
    print("  " + "-" * 78)
    for idx, d in enumerate(deals, 1):
        print(f"  {idx:<4} {d['dealId']:<28} {d['companyName']:<20} "
              f"{d['sector']:<10} {d['score']:<6} {d['riskLevel']:<10}")

    # 노드/관계 카운트
    counts = client.execute_read("""
        MATCH (d:Deal) RETURN 'Deal' AS label, count(d) AS count
        UNION ALL MATCH (c:Company) RETURN 'Company' AS label, count(c) AS count
        UNION ALL MATCH (rc:RiskCategory) RETURN 'RiskCategory' AS label, count(rc) AS count
        UNION ALL MATCH (e:RiskEntity) RETURN 'RiskEntity' AS label, count(e) AS count
        UNION ALL MATCH (ev:RiskEvent) RETURN 'RiskEvent' AS label, count(ev) AS count
    """, {})

    print("\n  [노드 현황]")
    for r in counts:
        print(f"    {r['label']}: {r['count']}개")

    rel_counts = client.execute_read("""
        MATCH ()-[r:TARGET]->() RETURN 'TARGET' AS type, count(r) AS count
        UNION ALL MATCH ()-[r:HAS_CATEGORY]->() RETURN 'HAS_CATEGORY' AS type, count(r) AS count
        UNION ALL MATCH ()-[r:HAS_RELATED]->() RETURN 'HAS_RELATED' AS type, count(r) AS count
        UNION ALL MATCH ()-[r:HAS_ENTITY]->() RETURN 'HAS_ENTITY' AS type, count(r) AS count
        UNION ALL MATCH ()-[r:HAS_EVENT]->() RETURN 'HAS_EVENT' AS type, count(r) AS count
    """, {})

    print("\n  [관계 현황]")
    for r in rel_counts:
        print(f"    {r['type']}: {r['count']}개")

    print("\n" + "=" * 60)
    print("  Mock 데이터 투입 완료!")
    print("=" * 60)


def main():
    print("\n" + "=" * 60)
    print("  Neo4j Mock 데이터 투입 스크립트")
    print("  (7개 딜 + 관련기업 + RiskEntity + RiskEvent)")
    print("=" * 60)

    client = Neo4jClient()
    client.connect()

    try:
        step1_init_graph(client)
        deal_service = DealService(client)
        step2_create_deals(deal_service)
        step3_create_related(client, deal_service)
        step4_insert_entities_events(client)
        step5_calculate_scores(client)
        step6_verify(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
