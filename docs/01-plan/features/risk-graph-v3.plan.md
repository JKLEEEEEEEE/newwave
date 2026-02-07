# Risk Graph v3 - 그래프 DB 고도화 계획서

> **기능명**: risk-graph-v3
> **작성일**: 2026-02-06
> **상태**: Plan (수정)

---

## 1. 배경 및 목적

### 1.1 현재 문제점

| # | 문제 | 상세 |
|:-:|------|------|
| 1 | **Status 중심 뷰 부재** | PASS/WARNING/FAIL 그룹핑 없음 |
| 2 | **데이터 출처 불명확** | 각 정보가 어디서 오는지 모름 |
| 3 | **점수 산정 근거 불명확** | 총점 계산 로직 불투명 |
| 4 | **뉴스/공시 데이터 빈약** | 크롤링/수집 체계 미흡 |
| 5 | **데이터 검증 없음** | 실제로 데이터가 제대로 들어오는지 확인 불가 |

### 1.2 목표

```
[AS-IS]                              [TO-BE]

Company ─── Company                  Status (PASS/WARNING/FAIL)
    │                                    │
Company ─── Company                      ├── PASS
                                         │    ├── SK하이닉스 (출처: DART, 뉴스)
(출처 불명확, 점수 근거 없음)              │    └── 현대자동차
                                         │
                                         ├── WARNING
                                         │    └── LG에너지솔루션
                                         │
                                         └── FAIL
                                              └── (고위험 딜)

                                     + 모든 노드에 출처(source) 명시
                                     + 점수 산정 공식 투명화
```

---

## 2. Status 분류 기준 (3단계)

| Status | 점수 범위 | 의미 | 색상 | 조치 |
|--------|:---------:|------|:----:|------|
| **PASS** | 0-49 | 정상 | 🟢 | 정기 모니터링 |
| **WARNING** | 50-74 | 주의 | 🟠 | 집중 모니터링, 원인 분석 |
| **FAIL** | 75-100 | 위험 | 🔴 | 즉시 대응, 리스크 완화 조치 |

```cypher
// Status 노드
(:Status {id: "PASS", name: "정상", minScore: 0, maxScore: 49, color: "#22C55E"})
(:Status {id: "WARNING", name: "주의", minScore: 50, maxScore: 74, color: "#F97316"})
(:Status {id: "FAIL", name: "위험", minScore: 75, maxScore: 100, color: "#EF4444"})
```

---

## 3. 데이터 출처 정의

### 3.1 데이터 소스 매핑

| 데이터 | 출처 | API/방법 | 수집 주기 | 현재 상태 |
|--------|------|----------|:---------:|:---------:|
| **기업 기본정보** | DART 전자공시 | OpenDART API `company.json` | 월 1회 | ⚠️ 미구현 |
| **재무제표** | DART | OpenDART API `fnlttSinglAcnt.json` | 분기 | ⚠️ 미구현 |
| **공시 목록** | DART | OpenDART API `list.json` | 일 1회 | ⚠️ 미구현 |
| **주가 정보** | KRX/증권사 | 크롤링 또는 API | 일 1회 | ❌ 없음 |
| **뉴스** | 네이버뉴스/구글 | 크롤링 | 실시간 | ⚠️ Mock |
| **공급망 정보** | 수동입력/공시분석 | 관리자 입력 | 수시 | ⚠️ Mock |
| **신용등급** | 신용평가사 | 수동입력 | 변동 시 | ❌ 없음 |

### 3.2 노드별 출처 속성

모든 노드에 다음 속성 필수 포함:

```typescript
interface SourceMetadata {
  source: string;        // 데이터 출처 (DART, NEWS_CRAWL, MANUAL 등)
  sourceId: string;      // 원본 식별자 (공시번호, 뉴스URL 등)
  fetchedAt: datetime;   // 수집 일시
  isVerified: boolean;   // 검증 여부
  confidence: float;     // 신뢰도 (0-1)
}
```

---

## 4. 개선된 노드 스키마

### 4.1 Deal (딜)

```cypher
(:Deal {
  // 식별
  id: "DEAL_001",

  // 기본 정보
  name: "SK하이닉스 시설자금",
  type: "시설자금대출",          // 시설자금, 운영자금, 회사채, PF 등
  amount: 500000000000,         // 금액 (원)
  currency: "KRW",

  // 기간
  startDate: date("2024-01-15"),
  maturityDate: date("2029-01-15"),

  // 상태
  dealStatus: "ACTIVE",         // ACTIVE, CLOSED, DEFAULT

  // 출처
  source: "INTERNAL",           // 내부 시스템
  sourceId: "LMS-2024-001",     // 여신관리시스템 ID
  createdAt: datetime(),
  updatedAt: datetime()
})
```

### 4.2 Company (기업)

```cypher
(:Company:DealTarget {
  // 식별
  id: "COM_SKHYNIX",
  corpCode: "00126380",         // DART 고유번호
  stockCode: "000660",          // 종목코드

  // 기본 정보
  name: "SK하이닉스",
  nameEn: "SK Hynix Inc.",
  sector: "반도체",
  sectorCode: "26",             // 업종코드
  market: "KOSPI",

  // 리스크 점수
  totalRiskScore: 72,
  directRiskScore: 65,
  propagatedRiskScore: 7,
  riskLevel: "FAIL",            // PASS, WARNING, FAIL

  // 재무 정보 (DART 출처)
  revenue: 42998500000000,      // 매출액
  operatingProfit: 2200000000000,
  netIncome: 1800000000000,
  totalAssets: 85000000000000,
  fiscalYear: "2024",

  // 출처 메타데이터
  source: "DART",
  sourceId: "00126380",
  fetchedAt: datetime(),
  isVerified: true,

  // 플래그
  isDealTarget: true,           // 딜 대상 여부
  isActive: true
})
```

### 4.3 News (뉴스)

```cypher
(:News {
  // 식별
  id: "NEWS_0001",

  // 내용
  title: "SK하이닉스, 美 ITC 특허 소송 패소",
  summary: "미국 국제무역위원회가...",
  content: "...",               // 전문 (선택)

  // 분류
  category: "법률",             // 법률, 시장, 운영, 공급망, ESG
  sentiment: -0.8,              // -1 ~ +1
  importance: "HIGH",           // HIGH, MEDIUM, LOW

  // 영향도
  impactScore: 15,              // 리스크 점수 영향 (+/-)

  // 출처
  source: "NEWS_NAVER",
  sourceUrl: "https://news.naver.com/...",
  publisher: "한국경제",
  author: "김기자",
  publishedAt: datetime("2026-02-01T09:00:00"),

  // 수집
  fetchedAt: datetime(),
  crawlMethod: "NAVER_API",     // NAVER_API, GOOGLE_NEWS, RSS
  isVerified: false,            // AI 분석 검증 여부

  // AI 분석 결과
  aiAnalyzedAt: datetime(),
  aiModel: "gpt-4-turbo",
  keywords: ["특허", "소송", "ITC"]
})
```

### 4.4 Disclosure (DART 공시)

```cypher
(:Disclosure {
  // 식별
  id: "DISC_0001",
  rceptNo: "20260201000123",    // DART 접수번호

  // 기본 정보
  title: "주요사항보고서(소송등의제기)",
  reportType: "D",              // A:정기, B:주요사항, C:발행, D:기타
  reportName: "소송등의제기",

  // 기업 정보
  corpCode: "00126380",
  corpName: "SK하이닉스",
  stockCode: "000660",

  // 일시
  filingDate: date("2026-02-01"),

  // 분석
  category: "법률위험",
  importance: "HIGH",
  impactScore: 10,
  summary: "미국 ITC 특허 침해 소송 패소...",

  // 출처
  source: "DART",
  sourceUrl: "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260201000123",
  fetchedAt: datetime(),

  // AI 분석
  aiAnalyzedAt: datetime(),
  aiSentiment: -0.6
})
```

### 4.5 RiskCategory (리스크 카테고리)

```cypher
(:RiskCategory {
  id: "RC_SKHYNIX_LEGAL",

  // 카테고리
  name: "법률위험",
  code: "LEGAL",                // MARKET, CREDIT, OPERATIONAL, LEGAL, SUPPLY, ESG

  // 점수
  score: 82,
  weight: 0.15,                 // 가중치
  weightedScore: 12.3,

  // 트렌드
  trend: "UP",                  // UP, DOWN, STABLE
  previousScore: 65,
  changeAmount: 17,

  // 근거
  factors: [
    "ITC 특허 소송 패소 (+15)",
    "EU 반독점 조사 진행 중 (+5)"
  ],

  // 출처
  source: "CALCULATED",
  calculatedAt: datetime(),
  baseData: ["NEWS_0001", "DISC_0001"]  // 근거 데이터 참조
})
```

### 4.6 Supplier/Customer (공급사/고객사)

```cypher
// 공급 관계
(target:Company)-[:SUPPLIED_BY {
  tier: 1,                      // 1차, 2차, 3차
  dependency: 0.25,             // 의존도 (0-1)
  isCritical: true,             // 핵심 공급사 여부

  // 거래 정보
  transactionType: "장비공급",
  annualVolume: 50000000000,    // 연간 거래액
  contractStartDate: date("2022-01-01"),
  contractEndDate: date("2025-12-31"),

  // 출처
  source: "MANUAL",             // DART_ANALYSIS, MANUAL, NEWS_EXTRACT
  sourceNote: "2024 사업보고서 주요거래처 기재",
  verifiedAt: datetime(),
  verifiedBy: "admin"
}]->(supplier:Company)
```

---

## 5. 관계(Relationship) 스키마

| 관계 | 방향 | 속성 | 출처 |
|------|------|------|------|
| `(Deal)-[:TARGET]->(Company)` | 딜→기업 | since, amount | INTERNAL |
| `(Company)-[:IN_STATUS]->(Status)` | 기업→상태 | since, reason | CALCULATED |
| `(Company)-[:SUPPLIED_BY]->(Company)` | 기업→공급사 | tier, dependency, source | DART/MANUAL |
| `(Company)-[:SELLS_TO]->(Company)` | 기업→고객사 | revenueShare, source | DART/MANUAL |
| `(Company)-[:COMPETES_WITH]->(Company)` | 기업↔경쟁사 | similarity | MANUAL |
| `(Company)-[:MENTIONED_IN]->(News)` | 기업→뉴스 | relevance | NEWS_CRAWL |
| `(Company)-[:FILED]->(Disclosure)` | 기업→공시 | - | DART |
| `(Company)-[:HAS_RISK]->(RiskCategory)` | 기업→리스크 | - | CALCULATED |
| `(Company)-[:HAS_EVENT]->(RiskEvent)` | 기업→이벤트 | - | MULTI |

---

## 6. 점수 산정 공식 (투명화)

### 6.1 직접 리스크 (Direct Risk)

```python
CATEGORY_WEIGHTS = {
    "MARKET": 0.20,      # 시장위험
    "CREDIT": 0.20,      # 신용위험
    "OPERATIONAL": 0.15, # 운영위험
    "LEGAL": 0.15,       # 법률위험
    "SUPPLY": 0.20,      # 공급망위험
    "ESG": 0.10,         # ESG위험
}
# 합계: 1.00

def calculate_direct_risk(company_id: str) -> dict:
    categories = get_risk_categories(company_id)

    breakdown = []
    total = 0.0

    for cat in categories:
        weight = CATEGORY_WEIGHTS.get(cat.code, 0.1)
        weighted = cat.score * weight
        total += weighted
        breakdown.append({
            "category": cat.name,
            "score": cat.score,
            "weight": weight,
            "weighted": weighted,
            "factors": cat.factors  # 점수 근거
        })

    return {
        "directRiskScore": round(total),
        "breakdown": breakdown
    }
```

### 6.2 전이 리스크 (Propagated Risk)

```python
TIER_PROPAGATION_RATE = {
    1: 0.8,  # Tier 1: 80% 전이
    2: 0.5,  # Tier 2: 50% 전이
    3: 0.2,  # Tier 3: 20% 전이
}
MAX_PROPAGATED_RISK = 25  # 전이 리스크 상한

def calculate_propagated_risk(company_id: str) -> dict:
    suppliers = get_suppliers_with_risk(company_id)

    breakdown = []
    total = 0.0

    for supplier in suppliers:
        tier_rate = TIER_PROPAGATION_RATE.get(supplier.tier, 0.1)
        propagated = supplier.risk_score * supplier.dependency * tier_rate
        total += propagated
        breakdown.append({
            "supplier": supplier.name,
            "tier": supplier.tier,
            "supplierRisk": supplier.risk_score,
            "dependency": supplier.dependency,
            "tierRate": tier_rate,
            "propagated": propagated
        })

    capped_total = min(MAX_PROPAGATED_RISK, total)

    return {
        "propagatedRiskScore": round(capped_total),
        "breakdown": breakdown,
        "cappedAt": MAX_PROPAGATED_RISK if total > MAX_PROPAGATED_RISK else None
    }
```

### 6.3 총점 계산

```python
def calculate_total_risk(company_id: str) -> dict:
    direct = calculate_direct_risk(company_id)
    propagated = calculate_propagated_risk(company_id)

    total = direct["directRiskScore"] + propagated["propagatedRiskScore"]
    total = min(100, max(0, total))

    # Status 결정
    if total < 50:
        status = "PASS"
    elif total < 75:
        status = "WARNING"
    else:
        status = "FAIL"

    return {
        "totalRiskScore": total,
        "directRiskScore": direct["directRiskScore"],
        "propagatedRiskScore": propagated["propagatedRiskScore"],
        "status": status,
        "directBreakdown": direct["breakdown"],
        "propagatedBreakdown": propagated["breakdown"],
        "calculatedAt": datetime.now().isoformat()
    }
```

---

## 7. 신호 탐지 및 키워드 기준 (핵심)

### 7.1 리스크 키워드 사전 (점수 기반)

기존 risk_engine에서 검증된 부정 키워드 및 점수 체계:

#### 7.1.1 DART 공시 리스크 키워드

```python
DART_RISK_KEYWORDS = {
    # 🔴 고위험 (50-70점) - 즉시 대응 필요
    "횡령": 50,
    "배임": 50,
    "분식회계": 50,
    "부적정": 60,         # 감사의견
    "의견거절": 70,       # 감사의견 거절
    "부도": 60,
    "파산": 60,

    # 🟠 중위험 (30-49점) - 집중 모니터링
    "회생": 50,
    "워크아웃": 45,
    "자본잠식": 40,
    "채무불이행": 45,
    "계속기업불확실": 40,
    "과징금": 35,
    "한정": 35,           # 한정의견
    "경영권분쟁": 35,
    "제재": 30,
    "고발": 30,
    "감사범위제한": 30,

    # 🟡 저위험 (10-29점) - 일반 모니터링
    "소송": 25,
    "고소": 25,
    "벌금": 25,
    "해임": 25,
    "손해배상": 20,
    "최대주주변경": 20,
    "위반": 15,
    "사임": 15,
    "정정": 10,
    "대표이사": 10,       # 변경 시
    "조회공시": 5,
    "풍문": 5,
    "주주총회": 5,

    # 🔴 사업 위험 (40-50점)
    "사업중단": 40,
    "허가취소": 45,
    "영업정지": 40,
    "폐업": 50,
}
```

#### 7.1.2 뉴스 리스크 키워드

```python
NEWS_RISK_KEYWORDS = {
    # 🔴 사법/형사 (30-50점)
    "횡령": 50,
    "배임": 50,
    "분식회계": 50,
    "압수수색": 40,
    "구속": 40,
    "기소": 35,
    "검찰": 30,
    "고발": 25,

    # 🟠 재무/신용 (45-60점)
    "부도": 60,
    "파산": 60,
    "회생": 45,
    "과징금": 30,
    "제재": 30,

    # 🟡 평판/ESG (10-25점)
    "소송": 20,
    "위반": 15,
    "비리": 25,
    "갑질": 15,
    "스캔들": 15,
    "불매": 10,
    "논란": 10,
}
```

#### 7.1.3 KIND 공시 리스크 키워드

```python
KIND_RISK_KEYWORDS = {
    # 🔴 최고위험 (70-80점) - 상장/거래 위험
    "상장폐지": 80,
    "파산": 80,
    "감사의견거절": 75,
    "부도": 75,
    "관리종목": 70,
    "의견거절": 70,
    "채무불이행": 70,

    # 🟠 고위험 (45-65점)
    "계속기업": 65,
    "불성실공시": 60,
    "횡령": 60,
    "배임": 60,
    "자본잠식": 60,
    "회생": 55,
    "한정": 50,
    "가압류": 45,
    "무상감자": 45,

    # 🟡 중위험 (20-40점)
    "조회공시": 40,
    "피소": 40,
    "소송": 35,
    "최대주주변경": 35,
    "정정공시": 25,
    "유상증자": 20,
    "단일판매": 20,
}
```

### 7.2 키워드 카테고리 분류

```python
CATEGORY_KEYWORDS = {
    # 리스크 유형별 키워드 그룹
    "LEGAL": {          # 법률위험
        "keywords": ["횡령", "배임", "소송", "고발", "고소", "제재", "과징금", "압수수색", "구속", "기소"],
        "weight": 0.15,
        "alert_threshold": 30,  # 이 점수 이상이면 경보
    },
    "CREDIT": {         # 신용위험
        "keywords": ["부도", "파산", "회생", "워크아웃", "채무불이행", "자본잠식"],
        "weight": 0.20,
        "alert_threshold": 40,
    },
    "GOVERNANCE": {     # 지배구조위험
        "keywords": ["최대주주변경", "대표이사", "사임", "해임", "경영권분쟁", "주주총회"],
        "weight": 0.10,
        "alert_threshold": 20,
    },
    "OPERATIONAL": {    # 운영위험
        "keywords": ["사업중단", "허가취소", "영업정지", "폐업", "생산중단"],
        "weight": 0.15,
        "alert_threshold": 35,
    },
    "AUDIT": {          # 감사위험
        "keywords": ["부적정", "의견거절", "한정", "감사범위제한", "계속기업불확실"],
        "weight": 0.20,
        "alert_threshold": 30,
    },
    "ESG": {            # ESG위험
        "keywords": ["환경오염", "안전사고", "인권침해", "갑질", "비리", "스캔들", "불매"],
        "weight": 0.10,
        "alert_threshold": 15,
    },
}
```

### 7.3 점수 계산 및 시간 감쇠

```python
# 시간 감쇠 (Decay) 공식
DECAY_HALF_LIFE = 30  # 30일 반감기

def calc_decay(days_old: int) -> float:
    """오래된 정보일수록 점수 감소"""
    import math
    return math.exp(-days_old / DECAY_HALF_LIFE)

# 예시:
# - 오늘 뉴스: decay = 1.0 (100%)
# - 30일 전: decay = 0.37 (37%)
# - 60일 전: decay = 0.14 (14%)
# - 90일 전: decay = 0.05 (5%)

def calculate_news_risk_score(title: str, pub_date: datetime) -> dict:
    """뉴스 제목에서 리스크 점수 산출"""
    matched_keywords = []
    raw_score = 0

    for keyword, points in NEWS_RISK_KEYWORDS.items():
        if keyword in title:
            matched_keywords.append(f"{keyword}({points})")
            raw_score += points

    days_old = (datetime.now() - pub_date).days
    decay_rate = calc_decay(max(0, days_old))
    decayed_score = round(raw_score * decay_rate)

    return {
        "raw_score": min(raw_score, 100),
        "decayed_score": min(decayed_score, 100),
        "keywords": matched_keywords,
        "days_old": days_old,
        "decay_rate": round(decay_rate, 2),
        "sentiment": "부정" if decayed_score > 0 else "중립",
        "is_risk": decayed_score > 0,
    }
```

### 7.4 신뢰도(Confidence) 산정

```python
def calc_confidence(keywords: list, title_length: int) -> float:
    """
    신뢰도 계산:
    - 키워드가 많을수록 신뢰도 높음
    - 제목이 길면 맥락 파악 가능
    """
    if not keywords:
        return 0.3  # 키워드 없으면 낮은 신뢰도

    base = 0.5
    keyword_bonus = len(keywords) * 0.15
    return round(min(base + keyword_bonus, 0.95), 2)

# 신뢰도 해석:
# - 0.3-0.5: LOW - AI 검증 필요
# - 0.5-0.7: MEDIUM - 참고용
# - 0.7-0.95: HIGH - 신뢰 가능
```

---

## 8. 데이터 수집 상세 전략

### 8.1 DART 공시 수집 (확장)

#### 8.1.1 수집 대상 API 엔드포인트

```python
DART_API_ENDPOINTS = {
    # 1. 기업 기본정보
    "company.json": {
        "description": "기업 개황",
        "fields": ["corp_name", "corp_name_eng", "stock_code", "ceo_nm",
                   "corp_cls", "jurir_no", "bizr_no", "adres", "hm_url",
                   "ir_url", "phn_no", "fax_no", "induty_code", "est_dt"],
        "schedule": "monthly",
    },

    # 2. 재무제표
    "fnlttSinglAcnt.json": {
        "description": "단일회사 주요재무",
        "fields": ["rcept_no", "reprt_code", "bsns_year", "corp_code",
                   "sj_div", "sj_nm", "account_nm", "thstrm_nm",
                   "thstrm_amount", "frmtrm_nm", "frmtrm_amount"],
        "schedule": "quarterly",
    },

    # 3. 공시 목록 (핵심)
    "list.json": {
        "description": "공시 검색",
        "fields": ["corp_name", "corp_code", "stock_code", "report_nm",
                   "rcept_no", "flr_nm", "rcept_dt", "rm"],
        "schedule": "daily",
        "filter": "RISK_KEYWORDS 매칭",
    },

    # 4. 대주주 현황
    "hyslrSttus.json": {
        "description": "최대주주 현황",
        "fields": ["rcept_no", "corp_code", "corp_name", "nm",
                   "relate", "stock_knd", "bsis_posesn_stock_co",
                   "bsis_posesn_stock_qota_rt"],
        "schedule": "quarterly",
    },

    # 5. 임원 현황
    "elestock.json": {
        "description": "임원 주식 보유 현황",
        "fields": ["rcept_no", "corp_code", "corp_name", "nm", "rgist_exctv_at",
                   "fte_at", "chrg_job", "sp_stock_lmp_cnt", "sp_stock_lmp_irds_cnt"],
        "schedule": "quarterly",
    },

    # 6. 배당 정보
    "alotMatter.json": {
        "description": "배당에 관한 사항",
        "fields": ["se", "stock_knd", "thstrm", "frmtrm", "lwfr"],
        "schedule": "annually",
    },
}
```

#### 8.1.2 공시 유형 분류

```python
DART_REPORT_CLASSIFICATION = {
    # A: 정기공시 (분기별 수집)
    "A001": {"name": "사업보고서", "importance": "HIGH", "schedule": "annually"},
    "A002": {"name": "반기보고서", "importance": "HIGH", "schedule": "biannually"},
    "A003": {"name": "분기보고서", "importance": "MEDIUM", "schedule": "quarterly"},

    # B: 주요사항보고서 (일일 수집 - 핵심)
    "B001": {"name": "주요사항보고서(소송)", "importance": "CRITICAL", "schedule": "daily"},
    "B002": {"name": "주요사항보고서(채무)", "importance": "CRITICAL", "schedule": "daily"},
    "B003": {"name": "주요사항보고서(부도)", "importance": "CRITICAL", "schedule": "daily"},

    # C: 발행공시 (주간 수집)
    "C001": {"name": "증권발행실적보고서", "importance": "MEDIUM", "schedule": "weekly"},
    "C002": {"name": "유상증자결정", "importance": "MEDIUM", "schedule": "weekly"},

    # D: 지분공시 (일일 수집)
    "D001": {"name": "임원·주요주주특정증권등소유상황보고서", "importance": "MEDIUM", "schedule": "daily"},
    "D002": {"name": "주식등의대량보유상황보고서", "importance": "MEDIUM", "schedule": "daily"},

    # E: 합병분할 (일일 수집)
    "E001": {"name": "합병결정", "importance": "HIGH", "schedule": "daily"},
    "E002": {"name": "분할결정", "importance": "HIGH", "schedule": "daily"},
}

# 수집 스케줄
DART_COLLECTION_SCHEDULE = {
    "realtime": ["B001", "B002", "B003"],  # 실시간: 주요사항 (리스크)
    "daily": ["D001", "D002", "E001", "E002"],  # 일일: 지분, 합병
    "weekly": ["C001", "C002"],  # 주간: 발행
    "quarterly": ["A003"],  # 분기: 분기보고서
    "annually": ["A001"],  # 연간: 사업보고서
}
```

### 8.2 뉴스 수집 전략 (확장)

#### 8.2.1 뉴스 소스 및 우선순위

```python
NEWS_SOURCES = [
    {
        "name": "네이버뉴스",
        "method": "GOOGLE_RSS_NAVER",  # site:naver.com 필터
        "priority": 1,
        "reliability": 0.85,
        "coverage": "종합",
    },
    {
        "name": "구글뉴스",
        "method": "GOOGLE_RSS",
        "priority": 2,
        "reliability": 0.75,
        "coverage": "글로벌",
    },
    {
        "name": "한국거래소 KIND",
        "method": "KIND_RSS",
        "priority": 1,  # 공시는 최우선
        "reliability": 0.95,
        "coverage": "공시",
    },
    {
        "name": "증권사리서치",
        "method": "MANUAL",
        "priority": 3,
        "reliability": 0.90,
        "coverage": "분석리포트",
    },
]
```

#### 8.2.2 검색 키워드 전략

```python
# 기업별 검색 키워드 (동의어, 약어, 영문명 포함)
COMPANY_SEARCH_KEYWORDS = {
    "COM_SKHYNIX": {
        "primary": "SK하이닉스",
        "aliases": ["하이닉스", "SK Hynix", "에스케이하이닉스"],
        "products": ["HBM", "HBM3", "NAND", "DRAM"],
        "sector": ["반도체", "메모리"],
    },
    "COM_LGENERGY": {
        "primary": "LG에너지솔루션",
        "aliases": ["LG에너지", "LG ES", "LGES", "엘지에너지솔루션"],
        "products": ["배터리", "2차전지", "파우치셀", "원통형배터리"],
        "sector": ["배터리", "전기차"],
    },
    "COM_HYUNDAI": {
        "primary": "현대자동차",
        "aliases": ["현대차", "현대모터스", "Hyundai Motor"],
        "products": ["아이오닉", "제네시스", "싼타페", "전기차"],
        "sector": ["자동차", "모빌리티"],
    },
}

# 검색 쿼리 생성 로직
def generate_search_queries(company_id: str) -> list:
    """기업별 검색 쿼리 생성"""
    config = COMPANY_SEARCH_KEYWORDS.get(company_id, {})
    queries = []

    # 1. 기본 검색: 기업명 + 리스크 키워드
    primary = config.get("primary", "")
    for risk_kw in ["소송", "횡령", "부도", "제재", "실적"]:
        queries.append(f"{primary} {risk_kw}")

    # 2. 동의어 검색
    for alias in config.get("aliases", []):
        queries.append(alias)

    # 3. 제품/산업 검색 (공급망 파악용)
    for product in config.get("products", []):
        queries.append(f"{primary} {product}")

    return queries
```

#### 8.2.3 뉴스 필터링 및 중복 제거

```python
NEWS_FILTER_CONFIG = {
    # 수집 기간
    "max_age_days": 30,  # 30일 이내 뉴스만

    # 중복 제거
    "dedup_method": "url_hash",  # URL 해시로 중복 체크
    "similarity_threshold": 0.85,  # 제목 유사도 85% 이상이면 중복

    # 품질 필터
    "min_title_length": 10,  # 제목 10자 이상
    "blocked_sources": ["광고", "스팸"],  # 차단 소스

    # 리스크 필터
    "min_risk_score": 5,  # 최소 리스크 점수 (이하면 무시)
    "require_keyword_match": True,  # 키워드 매칭 필수
}
```

### 8.3 데이터 처리 파이프라인

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Data Collection & Processing Pipeline                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ COLLECT │───>│  PARSE  │───>│ ANALYZE │───>│ VALIDATE│───>│  STORE  │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       │              │              │              │              │         │
│       ▼              ▼              ▼              ▼              ▼         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │  DART   │    │ 제목추출  │    │키워드매칭│    │ 중복체크  │    │ Neo4j   │  │
│  │  NEWS   │    │ 날짜파싱  │    │점수계산 │    │ 범위검증  │    │ INSERT  │  │
│  │  KIND   │    │ 출처확인  │    │카테고리 │    │ AI검증   │    │ UPDATE  │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         분석(ANALYZE) 상세                              │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                        │ │
│  │   1. 키워드 매칭                                                       │ │
│  │      - DART_RISK_KEYWORDS 순회                                        │ │
│  │      - 제목/내용에서 키워드 검색                                        │ │
│  │      - 매칭된 키워드 점수 합산                                          │ │
│  │                                                                        │ │
│  │   2. 시간 감쇠 적용                                                    │ │
│  │      - 발행일 기준 경과일 계산                                          │ │
│  │      - decay = exp(-days / 30)                                        │ │
│  │      - 최종점수 = raw_score × decay                                   │ │
│  │                                                                        │ │
│  │   3. 카테고리 분류                                                     │ │
│  │      - CATEGORY_KEYWORDS 기준                                         │ │
│  │      - 가장 높은 점수의 카테고리 선택                                    │ │
│  │                                                                        │ │
│  │   4. 신뢰도 산정                                                       │ │
│  │      - 키워드 개수, 출처 신뢰도 기반                                     │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 8.4 데이터 검증 프로세스

```python
VALIDATION_RULES = {
    # 1. 필수 필드 검증
    "required_fields": {
        "News": ["title", "source", "sourceUrl", "publishedAt"],
        "Disclosure": ["rceptNo", "title", "corpCode", "filingDate"],
        "Company": ["id", "name", "source"],
    },

    # 2. 범위 검증
    "range_validation": {
        "riskScore": {"min": 0, "max": 100},
        "sentiment": {"min": -1, "max": 1},
        "confidence": {"min": 0, "max": 1},
    },

    # 3. 중복 검증
    "duplicate_check": {
        "News": ["sourceUrl"],  # URL로 중복 체크
        "Disclosure": ["rceptNo"],  # 접수번호로 중복 체크
    },

    # 4. 날짜 검증
    "date_validation": {
        "max_future_days": 1,  # 미래 날짜 허용 안함 (1일 버퍼)
        "max_past_days": 365,  # 1년 이상 오래된 데이터 경고
    },
}
```

---

## 9. 구현 항목 (확장)

### Phase 1: 키워드 엔진 & 스키마 (Week 1)

| # | 항목 | 파일 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 1 | 키워드 사전 모듈 | `keywords.py` | DART/NEWS/KIND 리스크 키워드 정의 | P0 |
| 2 | 점수 계산 엔진 | `score_engine.py` | 시간 감쇠, 신뢰도, 카테고리 분류 | P0 |
| 3 | Status 노드 (3개) | `load_graph_v3.py` | PASS/WARNING/FAIL 생성 | P0 |
| 4 | 노드 스키마 개선 | `load_graph_v3.py` | 출처 메타데이터 속성 추가 | P0 |

### Phase 2: 데이터 수집기 (Week 1-2)

| # | 항목 | 파일 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 5 | DART 수집기 v2 | `dart_collector_v2.py` | 6개 API 엔드포인트 지원 | P0 |
| 6 | 뉴스 수집기 v2 | `news_collector_v2.py` | 키워드 기반 필터링, 중복 제거 | P0 |
| 7 | KIND 수집기 | `kind_collector.py` | 한국거래소 공시 수집 | P1 |
| 8 | 검색 쿼리 생성기 | `query_generator.py` | 기업별 동의어/제품 키워드 생성 | P1 |

### Phase 3: API & 점수 산정 (Week 2)

| # | 항목 | 파일 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 9 | 리스크 점수 계산기 | `risk_calculator_v3.py` | 직접+전이+breakdown | P0 |
| 10 | Status 중심 API | `api.py` | GET /api/v3/status/summary | P0 |
| 11 | 점수 상세 API | `api.py` | GET /api/v3/companies/{id}/score | P0 |
| 12 | 데이터 품질 API | `api.py` | GET /api/v3/data-quality | P1 |

### Phase 4: 검증 & 스케줄러 (Week 2-3)

| # | 항목 | 파일 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 13 | 데이터 검증 모듈 | `validator.py` | 필수필드, 범위, 중복 검증 | P0 |
| 14 | 수집 스케줄러 | `scheduler.py` | 실시간/일일/주간 스케줄 | P1 |
| 15 | 알림 발송 모듈 | `alert_sender.py` | 임계치 초과 시 알림 | P2 |

### Phase 5: UI (Week 3)

| # | 항목 | 파일 | 설명 | 우선순위 |
|:-:|------|------|------|:--------:|
| 16 | Status 대시보드 | `RiskStatusView.tsx` | 3단계 PASS/WARNING/FAIL 뷰 | P0 |
| 17 | 점수 Breakdown UI | `RiskScoreBreakdown.tsx` | 카테고리별 점수 시각화 | P0 |
| 18 | 키워드 하이라이트 | `KeywordHighlight.tsx` | 매칭 키워드 강조 표시 | P1 |
| 19 | 데이터 품질 대시보드 | `DataQualityView.tsx` | 수집 현황 모니터링 | P2 |

### 총 구현 항목: 19개

```
P0 (필수): 12개 - 핵심 기능
P1 (중요): 5개 - 보조 기능
P2 (선택): 2개 - 고급 기능
```

---

## 10. 데이터 품질 지표

### 10.1 모니터링 대시보드

```
┌────────────────────────────────────────────────────────────────────────────┐
│  📊 Data Quality Dashboard - Risk Graph v3                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐       │
│  │ 📋 DART 공시                  │  │ 📰 뉴스                       │       │
│  │ ├─ 수집: 24건 (오늘)          │  │ ├─ 수집: 156건 (오늘)         │       │
│  │ ├─ 리스크매칭: 8건 (33%)      │  │ ├─ 리스크매칭: 42건 (27%)     │       │
│  │ ├─ 파싱 성공: 100%            │  │ ├─ 중복 제거: 28건            │       │
│  │ └─ 마지막: 10분 전            │  │ └─ 신뢰도 평균: 0.72          │       │
│  └──────────────────────────────┘  └──────────────────────────────┘       │
│                                                                            │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐       │
│  │ 🎯 키워드 매칭 통계            │  │ ⚡ 점수 변동                   │       │
│  │ ├─ LEGAL: 12건 (횡령, 소송)   │  │ ├─ 갱신: 3건 (오늘)           │       │
│  │ ├─ CREDIT: 5건 (부도, 회생)   │  │ ├─ Status 변경: 1건           │       │
│  │ ├─ AUDIT: 3건 (의견거절)      │  │ │   └─ WARNING→FAIL: LG에너지  │       │
│  │ └─ ESG: 8건 (환경, 갑질)      │  │ └─ 알림 발송: 2건             │       │
│  └──────────────────────────────┘  └──────────────────────────────┘       │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ 📈 출처별 신뢰도 (Source Reliability)                                │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ DART ████████████████████████████████████████████████ 100% ✅  │ │  │
│  │ │ KIND █████████████████████████████████████████████░░░ 95% ✅   │ │  │
│  │ │ NEWS ████████████████████████████████████░░░░░░░░░░░░ 78% ⚠️   │ │  │
│  │ │ MANUAL ███████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░ 45% ⚠️   │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 핵심 메트릭 (KPI)

| 메트릭 | 목표 | 측정 방법 |
|--------|:----:|----------|
| **DART 수집 성공률** | ≥ 99% | 성공 건수 / 시도 건수 |
| **뉴스 키워드 매칭률** | ≥ 25% | 리스크 매칭 / 전체 수집 |
| **중복 제거율** | ≥ 15% | 제거 건수 / 원본 건수 |
| **평균 신뢰도** | ≥ 0.70 | 전체 confidence 평균 |
| **점수 갱신 지연** | ≤ 1시간 | 데이터 수집~점수 반영 시간 |
| **Status 변경 감지** | ≤ 30분 | 변경 발생~알림 시간 |

### 10.3 검증 규칙

| 데이터 | 검증 항목 | 기준 | 실패 시 조치 |
|--------|----------|:----:|-------------|
| 기업정보 | DART corpCode 존재 | 필수 | 저장 거부 |
| 공급망 | 의존도 합계 | ≤ 1.0 | 정규화 |
| 뉴스 | 발행일 | 30일 이내 | 경고 후 저장 |
| 뉴스 | 키워드 매칭 | ≥ 1개 | is_risk=false 처리 |
| 점수 | 범위 | 0-100 | 클램핑 |
| 출처 | source 필드 | Not null | 저장 거부 |
| 신뢰도 | confidence | 0-1 | 클램핑 |

---

## 11. 성공 기준 (확장)

### 11.1 필수 (Must Have)

- [ ] 키워드 사전 모듈 구현 (DART/NEWS/KIND 40개+ 키워드)
- [ ] 시간 감쇠 함수 적용 (30일 반감기)
- [ ] Status 노드 3개 (PASS/WARNING/FAIL) 생성
- [ ] 모든 노드에 `source`, `fetchedAt`, `confidence` 속성 존재
- [ ] DART 공시 자동 수집 (일 1회 이상)
- [ ] 뉴스 키워드 기반 필터링 작동
- [ ] 점수 산정 시 카테고리별 breakdown 제공
- [ ] 중복 데이터 자동 제거

### 11.2 중요 (Should Have)

- [ ] KIND 공시 수집 지원
- [ ] 기업별 동의어/제품 키워드 검색
- [ ] 신뢰도(confidence) 자동 산정
- [ ] 데이터 품질 API 제공
- [ ] 키워드 하이라이트 UI

### 11.3 선택 (Nice to Have)

- [ ] 실시간 알림 발송 (Slack/Email)
- [ ] 데이터 품질 대시보드
- [ ] AI 기반 감성 분석 보강

---

## 12. 예상 결과물

### 12.1 Status 중심 대시보드

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Risk Monitor - Status View                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  🔴 FAIL (1)                                            Updated: 10분 전    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ SK하이닉스                                                 Score: 72   │ │
│  │ ├─ 직접: 65                                                            │ │
│  │ │   ├─ 법률 82 [횡령(50), 소송(25), 제재(30)] × decay 0.85            │ │
│  │ │   ├─ 공급망 68                                                       │ │
│  │ │   └─ 신용 45                                                         │ │
│  │ ├─ 전이: 7  (한미반도체 65점 × 0.25의존 × 0.8tier1)                    │ │
│  │ ├─ 출처: DART ✅ | NEWS 3건 (신뢰도 0.78)                              │ │
│  │ └─ 키워드: [횡령] [소송] [압수수색] ← 하이라이트                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  🟠 WARNING (1)                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LG에너지솔루션                                             Score: 58   │ │
│  │ ├─ 직접: 52 (운영 65, ESG 48)                                          │ │
│  │ ├─ 전이: 6                                                             │ │
│  │ └─ 출처: DART ✅ | NEWS 5건 | 키워드: [리콜] [안전사고]               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  🟢 PASS (1)                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 현대자동차                                                 Score: 38   │ │
│  │ └─ 출처: DART ✅ | NEWS 2건 | 키워드: (없음)                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 점수 상세 화면

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SK하이닉스 - Risk Score Breakdown                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  총점: 72 (FAIL)  |  직접: 65  |  전이: 7  |  갱신: 2026-02-06 15:30       │
│                                                                              │
│  ┌─ 직접 리스크 (Direct Risk) ───────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  카테고리      점수   가중치   가중점수   근거                          │  │
│  │  ──────────────────────────────────────────────────────────────────   │  │
│  │  🔴 법률위험    82    × 0.15    = 12.3   [ITC 특허소송 패소 +50]       │  │
│  │                                          [EU 반독점 조사 +15]          │  │
│  │  🟠 공급망위험  68    × 0.20    = 13.6   [ASML 장비 지연 +20]          │  │
│  │  🟡 시장위험    55    × 0.20    = 11.0   [반도체 가격 하락 +10]        │  │
│  │  🟢 신용위험    45    × 0.20    = 9.0    (양호)                        │  │
│  │  🟢 운영위험    38    × 0.15    = 5.7    (양호)                        │  │
│  │  🟢 ESG위험    25    × 0.10    = 2.5    (양호)                        │  │
│  │  ──────────────────────────────────────────────────────────────────   │  │
│  │                        합계     = 54.1 → 반올림 65                     │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ 전이 리스크 (Propagated Risk) ────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  공급사         Tier   점수   의존도   전이율   전이점수               │  │
│  │  ──────────────────────────────────────────────────────────────────   │  │
│  │  한미반도체      T1     65    0.25    0.80     = 13.0                 │  │
│  │  ASML           T1     40    0.15    0.80     = 4.8                  │  │
│  │  SK머티리얼즈   T2     35    0.20    0.50     = 3.5                  │  │
│  │  ──────────────────────────────────────────────────────────────────   │  │
│  │                        합계 = 21.3 → 상한적용(25) → 7                  │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ 데이터 출처 (Source Details) ─────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  유형     출처            수집일시           신뢰도   검증              │  │
│  │  ──────────────────────────────────────────────────────────────────   │  │
│  │  공시     DART            2026-02-06 14:00   0.95    ✅ 검증됨         │  │
│  │  뉴스     NEWS_NAVER      2026-02-06 15:20   0.78    ⚠️ AI분석         │  │
│  │  뉴스     NEWS_GOOGLE     2026-02-06 15:25   0.72    ⚠️ AI분석         │  │
│  │  공급망   MANUAL          2026-02-01 10:00   0.60    ⚠️ 수동입력       │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. 기존 코드 참조

### 13.1 키워드 시스템 (risk_engine/core.py)

기존 risk_engine에서 검증된 키워드 기반 신호 탐지 시스템:

| 클래스 | 역할 | 키워드 수 |
|--------|------|:--------:|
| `DartAPI.RISK_KEYWORDS` | DART 공시 리스크 키워드 | 32개 |
| `DartAPI.CATEGORY_KEYWORDS` | 카테고리 분류 키워드 | 3개 그룹 |
| `NewsScanner.RISK_KW` | 뉴스 리스크 키워드 | 18개 |
| `NaverNewsScanner.RISK_KW` | 네이버뉴스 키워드 | 18개 |
| `KindScanner.RISK_KW` | KIND 공시 키워드 | 21개 |

### 13.2 재사용 가능 함수

```python
# risk_engine/core.py에서 재사용
from risk_engine.core import (
    calc_decay,           # 시간 감쇠 계산
    calc_confidence,      # 신뢰도 계산
    parse_date,           # 날짜 파싱
)
```

---

## 14. 위험 요소 및 대응

| 위험 | 영향 | 확률 | 대응 방안 |
|------|:----:|:----:|----------|
| DART API 장애 | HIGH | LOW | 캐싱, 재시도 로직 |
| 뉴스 크롤링 차단 | MEDIUM | MEDIUM | User-Agent 로테이션, 요청 간격 조정 |
| 키워드 오탐지 | MEDIUM | MEDIUM | 컨텍스트 기반 필터링, AI 검증 |
| Neo4j 성능 이슈 | HIGH | LOW | 인덱스 최적화, 배치 처리 |

---

**작성일**: 2026-02-06 (v3.0 - 키워드 엔진 확장)
**다음 단계**: `/pdca design risk-graph-v3`

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|:----:|------|----------|
| v1.0 | 2026-02-06 | 초안 작성 |
| v2.0 | 2026-02-06 | Status 3단계, 출처 메타데이터 추가 |
| v3.0 | 2026-02-06 | 키워드 엔진 상세화, DART/뉴스 수집 전략 확장 |
