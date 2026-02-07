# Risk Graph v3 - Design Document

> **Summary**: 그래프 DB 고도화 - 키워드 엔진 + Status 중심 구조 + 점수 산정 투명화
>
> **Project**: new_wave (Risk Monitoring System)
> **Version**: 3.0
> **Author**: AI Assistant
> **Date**: 2026-02-06
> **Status**: Draft
> **Planning Doc**: [risk-graph-v3.plan.md](../01-plan/features/risk-graph-v3.plan.md)

---

## 1. Overview

### 1.1 Design Goals

| # | 목표 | 측정 가능 기준 |
|:-:|------|---------------|
| 1 | **키워드 기반 신호 탐지** | 70개+ 리스크 키워드 사전 구현 |
| 2 | **Status 중심 대시보드** | PASS/WARNING/FAIL 3단계 분류 |
| 3 | **점수 산정 투명화** | 카테고리별 breakdown 제공 |
| 4 | **데이터 출처 명시** | 모든 노드에 source, fetchedAt, confidence 속성 |
| 5 | **데이터 수집 자동화** | DART/뉴스 자동 수집 파이프라인 |

### 1.2 Design Principles

- **Single Responsibility**: 각 모듈은 하나의 책임만 가짐 (키워드 = 점수계산, 수집기 = 데이터수집)
- **Extensibility**: 새로운 데이터 소스나 키워드 추가 시 설정만 변경
- **Transparency**: 모든 점수 산정에 근거(breakdown) 제공
- **Traceability**: 모든 데이터에 출처와 수집 시점 기록

---

## 2. Architecture

### 2.1 System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                             Risk Graph v3 Architecture                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         DATA COLLECTION LAYER                            ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ││
│  │  │ DART Collector│  │News Collector│  │KIND Collector│  │  Scheduler  │  ││
│  │  │   (공시수집)   │  │  (뉴스수집)   │  │ (거래소공시)  │  │  (스케줄러)  │  ││
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  ││
│  │         │                 │                 │                 │          ││
│  └─────────┼─────────────────┼─────────────────┼─────────────────┼──────────┘│
│            ▼                 ▼                 ▼                 ▼           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         PROCESSING LAYER                                 ││
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   ││
│  │  │  Keywords Module  │  │   Score Engine   │  │     Validator        │   ││
│  │  │ (키워드 사전/매칭) │  │  (점수 계산/감쇠) │  │   (데이터 검증)       │   ││
│  │  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘   ││
│  │           │                     │                       │               ││
│  └───────────┼─────────────────────┼───────────────────────┼───────────────┘│
│              ▼                     ▼                       ▼                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         STORAGE LAYER                                    ││
│  │  ┌──────────────────────────────────────────────────────────────────┐   ││
│  │  │                         Neo4j Graph DB                            │   ││
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │   ││
│  │  │  │ Status │ │Company │ │  News  │ │Disclos.│ │RiskCat.│          │   ││
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘          │   ││
│  │  └──────────────────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│              │                                                              │
│              ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         API LAYER                                        ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ││
│  │  │GET /v3/status│  │GET /v3/score │  │GET /v3/data- │  │ Risk Calc   │  ││
│  │  │   /summary   │  │  /{id}       │  │   quality    │  │   API       │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│              │                                                              │
│              ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         UI LAYER                                         ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ││
│  │  │RiskStatusView│  │ScoreBreakdown│  │ KeywordHigh- │  │DataQuality  │  ││
│  │  │    .tsx      │  │     .tsx     │  │   light.tsx  │  │  View.tsx   │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Module Dependencies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Module Dependency Graph                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  keywords.py ◄──────────┬─────────────┬────────────────────────────────│
│      │                  │             │                                 │
│      ▼                  │             │                                 │
│  score_engine.py ◄──────┤             │                                 │
│      │                  │             │                                 │
│      ▼                  ▼             ▼                                 │
│  risk_calculator_v3.py  dart_collector_v2.py  news_collector_v2.py     │
│      │                  │             │                                 │
│      │                  ▼             ▼                                 │
│      │              validator.py ◄────┴────────────────────────────────│
│      │                  │                                               │
│      ▼                  ▼                                               │
│  neo4j_client.py ◄──────┴──────────────────────────────────────────────│
│      │                                                                  │
│      ▼                                                                  │
│  api.py ◄───────────────────────────────────────────────────────────────│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow

```
[외부 소스]           [수집]              [처리]              [저장]           [제공]
    │                   │                   │                   │                │
    ▼                   ▼                   ▼                   ▼                ▼

┌────────┐        ┌──────────┐        ┌──────────┐        ┌────────┐       ┌─────────┐
│  DART  │───────▶│dart_coll.│───────▶│validator │───────▶│ Neo4j  │──────▶│   API   │
│  API   │        │   v2.py  │        │   .py    │        │  DB    │       │  /v3/*  │
└────────┘        └──────────┘        └──────────┘        └────────┘       └─────────┘
                       │                   │                   ▲                │
┌────────┐             │                   │                   │                ▼
│  NEWS  │───────▶┌──────────┐             ▼                   │           ┌─────────┐
│  RSS   │        │news_coll.│───────▶┌──────────┐─────────────┘           │Frontend │
└────────┘        │   v2.py  │        │keywords  │                         │   UI    │
                  └──────────┘        │   .py    │                         └─────────┘
                       │              └──────────┘
                       │                   │
                       ▼                   ▼
                  ┌──────────┐        ┌──────────┐
                  │score_eng.│◀───────│risk_calc │
                  │   .py    │        │  _v3.py  │
                  └──────────┘        └──────────┘
```

### 2.4 End-to-End Risk Detection Flow (핵심: 데이터 모델 → 리스크 감지)

> **핵심 질문**: "데이터 모델을 구축했는데, 이걸로 어떻게 리스크를 감지하나?"

#### 2.4.1 전체 흐름 개요

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    END-TO-END RISK DETECTION PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  STEP 1: CRAWL CONFIG (무엇을 크롤링할지 결정)                                        │
│  ═══════════════════════════════════════════                                        │
│                                                                                     │
│  ┌─────────────────┐                                                                │
│  │  Deal (거래)     │──▶ DealTarget.corp_code ──▶ "005930" (삼성전자)                │
│  │  + DealTarget   │──▶ DealTarget.aliases    ──▶ ["삼성", "Samsung", "SEC"]        │
│  │  + Company      │──▶ Company.products      ──▶ ["반도체", "갤럭시", "DRAM"]        │
│  │  + Person       │──▶ Person.name           ──▶ ["이재용", "한종희", "경계현"]       │
│  └─────────────────┘                                                                │
│         │                                                                           │
│         ▼                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐       │
│  │  SearchConfig (자동 생성되는 검색 쿼리들)                                   │       │
│  │  ─────────────────────────────────────────────────────────────────────  │       │
│  │  DART API:  corp_code="005930"                                          │       │
│  │  NEWS RSS:  "삼성전자" OR "삼성 횡령" OR "이재용 구속" OR "갤럭시 리콜"      │       │
│  │  KIND API:  issuer_code="005930"                                        │       │
│  └─────────────────────────────────────────────────────────────────────────┘       │
│         │                                                                           │
│         ▼                                                                           │
│  STEP 2: DATA COLLECTION (데이터 수집)                                               │
│  ═══════════════════════════════════════                                            │
│                                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ DART API 호출     │  │ NEWS RSS 크롤링   │  │ KIND API 호출     │                  │
│  │ ────────────────  │  │ ────────────────  │  │ ────────────────  │                  │
│  │ list.json?       │  │ Google RSS:       │  │ 거래소 공시      │                  │
│  │  corp_code=005930│  │  q="삼성전자+횡령" │  │  issuer=005930   │                  │
│  │                  │  │ Naver News:       │  │                  │                  │
│  │ fnlttSinglAcnt:  │  │  q="이재용+구속"   │  │                  │                  │
│  │  재무제표 조회    │  │                  │  │                  │                  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘                  │
│           │                     │                     │                            │
│           ▼                     ▼                     ▼                            │
│  STEP 3: KEYWORD MATCHING (키워드 매칭 → 리스크 신호 생성)                            │
│  ════════════════════════════════════════════════════════                           │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐       │
│  │  수집된 공시 제목: "감사보고서 - 의견거절 (계속기업불확실 사유)"              │       │
│  │  ──────────────────────────────────────────────────────────────────────  │       │
│  │                                                                          │       │
│  │  ▼ keywords.match_keywords(title, DART_RISK_KEYWORDS)                    │       │
│  │                                                                          │       │
│  │  매칭 결과:                                                               │       │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │       │
│  │  │ "의견거절" → score=70, category="AUDIT"                           │   │       │
│  │  │ "계속기업불확실" → score=40, category="AUDIT"                      │   │       │
│  │  └──────────────────────────────────────────────────────────────────┘   │       │
│  │                                                                          │       │
│  │  ▼ 신뢰도 계산: confidence = 0.5 + (2 × 0.15) = 0.80                    │       │
│  │  ▼ 시간감쇠: decay = exp(-0/30) = 1.0 (오늘)                            │       │
│  │  ▼ 최종 raw_score = max(70, 40) = 70                                    │       │
│  └─────────────────────────────────────────────────────────────────────────┘       │
│           │                                                                         │
│           ▼                                                                         │
│  STEP 4: DATA MODEL POPULATION (데이터 모델에 저장)                                   │
│  ══════════════════════════════════════════════════                                 │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐       │
│  │  Neo4j에 저장되는 노드 & 관계                                             │       │
│  │  ──────────────────────────────────────────────────────────────────────  │       │
│  │                                                                          │       │
│  │  (Disclosure:공시) ──[MENTIONS]──▶ (Company:삼성전자)                    │       │
│  │       │                                                                  │       │
│  │       │ properties:                                                      │       │
│  │       │   title: "감사보고서 - 의견거절"                                   │       │
│  │       │   matched_keywords: ["의견거절", "계속기업불확실"]                 │       │
│  │       │   raw_score: 70                                                  │       │
│  │       │   confidence: 0.80                                               │       │
│  │       │   category: "AUDIT"                                              │       │
│  │       │   publishedAt: "2026-02-06"                                      │       │
│  │       │                                                                  │       │
│  │       ▼                                                                  │       │
│  │  (RiskCategory:AUDIT) ──[CATEGORIZED_AS]──▶ (Disclosure)                │       │
│  │                                                                          │       │
│  └─────────────────────────────────────────────────────────────────────────┘       │
│           │                                                                         │
│           ▼                                                                         │
│  STEP 5: RISK SCORE CALCULATION (리스크 점수 집계)                                   │
│  ═══════════════════════════════════════════════════                                │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐       │
│  │  Company 전체 리스크 점수 산정 (Cypher Query)                             │       │
│  │  ──────────────────────────────────────────────────────────────────────  │       │
│  │                                                                          │       │
│  │  MATCH (c:Company {corpCode: "005930"})                                  │       │
│  │  OPTIONAL MATCH (c)<-[:MENTIONS]-(d:Disclosure)                          │       │
│  │  OPTIONAL MATCH (c)<-[:MENTIONS]-(n:News)                                │       │
│  │  OPTIONAL MATCH (c)-[:WORKS_AT]-(p:Person)-[:MENTIONED_IN_NEWS]-(n2)     │       │
│  │                                                                          │       │
│  │  WITH c,                                                                 │       │
│  │    SUM(d.raw_score * d.confidence * exp(-d.days_ago/30)) as disc_score,  │       │
│  │    SUM(n.raw_score * n.confidence * exp(-n.days_ago/30)) as news_score,  │       │
│  │    SUM(n2.raw_score * 0.7) as person_propagated_score                    │       │
│  │                                                                          │       │
│  │  ┌────────────────────────────────────────────────────────────────┐     │       │
│  │  │ Direct Risk:      disc_score + news_score = 70 + 0 = 70        │     │       │
│  │  │ Propagated Risk:  person_propagated_score × 0.3 = 0            │     │       │
│  │  │ ─────────────────────────────────────────────────────────────  │     │       │
│  │  │ TOTAL SCORE:      70 → Status = "FAIL"                         │     │       │
│  │  └────────────────────────────────────────────────────────────────┘     │       │
│  │                                                                          │       │
│  └─────────────────────────────────────────────────────────────────────────┘       │
│           │                                                                         │
│           ▼                                                                         │
│  STEP 6: STATUS UPDATE & ALERT (상태 업데이트 & 알림)                                │
│  ════════════════════════════════════════════════════                               │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐       │
│  │  (:Status)-[:HAS_STATUS]->(Company:삼성전자)                              │       │
│  │                                                                          │       │
│  │  status: "FAIL"  (score >= 75)                                           │       │
│  │  previousStatus: "WARNING"                                               │       │
│  │  score: 70                                                               │       │
│  │  breakdown: {AUDIT: 70, LEGAL: 0, CREDIT: 0, ...}                        │       │
│  │  updatedAt: "2026-02-06T12:00:00Z"                                       │       │
│  │                                                                          │       │
│  │  ▼ 상태 변경 감지 → Alert 발생                                            │       │
│  │  ▼ RiskHistory 노드 생성 (변경 이력 추적)                                  │       │
│  └─────────────────────────────────────────────────────────────────────────┘       │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

#### 2.4.2 데이터 모델이 리스크 감지에 기여하는 방식

| 데이터 모델 | 리스크 감지에서의 역할 | 구체적 활용 |
|------------|---------------------|-----------|
| **Deal** | 모니터링 대상 정의 | 어떤 기업들을 감시할지 결정 |
| **DealTarget** | 검색 쿼리 생성 원천 | corpCode, aliases → API 호출 & 검색어 |
| **Company** | 기업 정보 + 제품/관계 | products, subsidiaries → 확장 검색 |
| **Person** | 임원/주주 감시 | 이름으로 뉴스 검색 → 기업에 전이 |
| **Disclosure** | DART 공시 → 키워드 매칭 | title에서 DART_RISK_KEYWORDS 탐지 |
| **News** | 뉴스 → 키워드 매칭 | headline/content에서 NEWS_KEYWORDS 탐지 |
| **Financials** | 재무 이상 탐지 | 부채비율, 자본잠식 자동 감지 |
| **RiskCategory** | 점수 분류 | LEGAL/CREDIT/AUDIT 등 카테고리별 가중치 |
| **Status** | 최종 상태 판정 | PASS/WARNING/FAIL 분류 + 알림 |
| **RiskHistory** | 변화 추적 | 상태 변경 이력 → 트렌드 분석 |

#### 2.4.3 검색 쿼리 자동 생성 규칙

```python
def build_search_queries(deal_target: DealTarget, company: Company, persons: list[Person]) -> SearchConfig:
    """데이터 모델을 기반으로 검색 쿼리 자동 생성"""

    queries = SearchConfig(corp_code=deal_target.corp_code)

    # 1. 기본 기업명 쿼리
    base_names = [deal_target.companyName] + deal_target.aliases

    # 2. 기업명 + 리스크 키워드 조합
    for name in base_names:
        for keyword in RISK_KEYWORDS[:10]:  # 상위 10개 고위험 키워드
            queries.news_queries.append(f"{name} {keyword}")

    # 3. 제품/서비스명 + 리스크 키워드
    for product in company.products:
        queries.news_queries.append(f"{product} 결함")
        queries.news_queries.append(f"{product} 리콜")
        queries.news_queries.append(f"{product} 불량")

    # 4. 임원/주주 이름 + 리스크 키워드
    for person in persons:
        if person.role in ["CEO", "대표이사", "회장", "대주주"]:
            queries.news_queries.append(f"{person.name} 구속")
            queries.news_queries.append(f"{person.name} 횡령")
            queries.news_queries.append(f"{person.name} 배임")

    # 5. DART API 쿼리 (corpCode 직접 사용)
    queries.dart_params = {"corp_code": deal_target.corp_code}

    return queries
```

#### 2.4.4 리스크 전이 규칙 (Person → Company)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RISK PROPAGATION (리스크 전이)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CASE 1: 임원 관련 뉴스 → 기업 리스크 전이                                    │
│  ═══════════════════════════════════════════                                │
│                                                                             │
│  (News: "이재용 회장 구속")                                                  │
│       │                                                                     │
│       │ matched: "구속" (score=40)                                          │
│       ▼                                                                     │
│  (Person: 이재용) ──[WORKS_AT {role: "회장"}]──▶ (Company: 삼성전자)         │
│       │                                                                     │
│       │ 전이율: 70% (고위직)                                                 │
│       ▼                                                                     │
│  Company.propagated_score += 40 × 0.7 = 28점 추가                           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CASE 2: 자회사 → 모회사 리스크 전이                                          │
│  ═══════════════════════════════════════                                    │
│                                                                             │
│  (Company: 삼성SDI) ──[SUBSIDIARY_OF]──▶ (Company: 삼성전자)                │
│       │                                                                     │
│       │ SDI 리스크 점수: 60                                                 │
│       │ 전이율: 50% (자회사)                                                 │
│       ▼                                                                     │
│  삼성전자.propagated_score += 60 × 0.5 = 30점 추가                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  전이율 기준표:                                                              │
│  ┌───────────────────┬───────────┬────────────────────────────────┐        │
│  │ 관계 유형         │ 전이율     │ 근거                          │        │
│  ├───────────────────┼───────────┼────────────────────────────────┤        │
│  │ 대표이사/회장     │ 70%       │ 경영 책임 직접 연결             │        │
│  │ 이사/임원         │ 50%       │ 의사결정 참여                  │        │
│  │ 대주주 (>5%)     │ 40%       │ 지배력 행사                    │        │
│  │ 자회사           │ 50%       │ 연결 실적 영향                 │        │
│  │ 공급업체         │ 30%       │ 공급망 의존도                  │        │
│  │ 관계사           │ 20%       │ 간접 영향                      │        │
│  └───────────────────┴───────────┴────────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Specifications

### 3.1 keywords.py - 키워드 사전 모듈

```python
"""
키워드 사전 및 매칭 엔진
- 책임: 리스크 키워드 정의 및 제목/내용에서 키워드 매칭
- 위치: risk_engine/keywords.py
"""

# === 상수 정의 ===

DART_RISK_KEYWORDS: dict[str, int] = {
    # 고위험 (50-70점)
    "횡령": 50, "배임": 50, "분식회계": 50,
    "부적정": 60, "의견거절": 70, "부도": 60, "파산": 60,
    # 중위험 (30-49점)
    "회생": 50, "워크아웃": 45, "자본잠식": 40, "채무불이행": 45,
    "계속기업불확실": 40, "과징금": 35, "한정": 35, "경영권분쟁": 35,
    "제재": 30, "고발": 30, "감사범위제한": 30,
    # 저위험 (10-29점)
    "소송": 25, "고소": 25, "벌금": 25, "해임": 25, "손해배상": 20,
    "최대주주변경": 20, "위반": 15, "사임": 15, "정정": 10,
    "대표이사": 10, "조회공시": 5, "풍문": 5, "주주총회": 5,
    # 사업 위험 (40-50점)
    "사업중단": 40, "허가취소": 45, "영업정지": 40, "폐업": 50,
}

NEWS_RISK_KEYWORDS: dict[str, int] = {
    "횡령": 50, "배임": 50, "분식회계": 50, "압수수색": 40,
    "구속": 40, "기소": 35, "검찰": 30, "고발": 25,
    "부도": 60, "파산": 60, "회생": 45, "과징금": 30, "제재": 30,
    "소송": 20, "위반": 15, "비리": 25, "갑질": 15,
    "스캔들": 15, "불매": 10, "논란": 10,
}

KIND_RISK_KEYWORDS: dict[str, int] = {
    "상장폐지": 80, "파산": 80, "감사의견거절": 75, "부도": 75,
    "관리종목": 70, "의견거절": 70, "채무불이행": 70,
    "계속기업": 65, "불성실공시": 60, "횡령": 60, "배임": 60,
    "자본잠식": 60, "회생": 55, "한정": 50, "가압류": 45, "무상감자": 45,
    "조회공시": 40, "피소": 40, "소송": 35, "최대주주변경": 35,
    "정정공시": 25, "유상증자": 20, "단일판매": 20,
}

CATEGORY_KEYWORDS: dict[str, dict] = {
    "LEGAL": {
        "keywords": ["횡령", "배임", "소송", "고발", "고소", "제재", "과징금", "압수수색", "구속", "기소"],
        "weight": 0.15,
        "alert_threshold": 30,
    },
    "CREDIT": {
        "keywords": ["부도", "파산", "회생", "워크아웃", "채무불이행", "자본잠식"],
        "weight": 0.20,
        "alert_threshold": 40,
    },
    "GOVERNANCE": {
        "keywords": ["최대주주변경", "대표이사", "사임", "해임", "경영권분쟁", "주주총회"],
        "weight": 0.10,
        "alert_threshold": 20,
    },
    "OPERATIONAL": {
        "keywords": ["사업중단", "허가취소", "영업정지", "폐업", "생산중단"],
        "weight": 0.15,
        "alert_threshold": 35,
    },
    "AUDIT": {
        "keywords": ["부적정", "의견거절", "한정", "감사범위제한", "계속기업불확실"],
        "weight": 0.20,
        "alert_threshold": 30,
    },
    "ESG": {
        "keywords": ["환경오염", "안전사고", "인권침해", "갑질", "비리", "스캔들", "불매"],
        "weight": 0.10,
        "alert_threshold": 15,
    },
}

# === 함수 정의 ===

def match_keywords(text: str, keyword_dict: dict[str, int]) -> list[dict]:
    """텍스트에서 키워드 매칭"""
    pass

def classify_category(keywords: list[str]) -> str:
    """매칭된 키워드로 카테고리 분류"""
    pass

def get_keywords_by_source(source: str) -> dict[str, int]:
    """소스 타입에 따른 키워드 사전 반환"""
    pass
```

### 3.2 score_engine.py - 점수 계산 엔진

```python
"""
점수 계산 엔진
- 책임: 시간 감쇠, 신뢰도, 카테고리 점수 계산
- 위치: risk_engine/score_engine.py
"""
import math
from datetime import datetime
from typing import Optional

# === 상수 ===
DECAY_HALF_LIFE = 30  # 30일 반감기

# === 함수 ===

def calc_decay(days_old: int, half_life: int = DECAY_HALF_LIFE) -> float:
    """시간 감쇠 계산 (지수 감쇠)"""
    return math.exp(-days_old / half_life)


def calc_confidence(keywords: list[str], source_reliability: float = 0.5) -> float:
    """신뢰도 계산"""
    if not keywords:
        return 0.3
    base = 0.5
    keyword_bonus = len(keywords) * 0.15
    return round(min(base + keyword_bonus, 0.95) * source_reliability / 0.5, 2)


def calculate_raw_score(keywords: list[dict]) -> int:
    """매칭된 키워드들의 원점수 합산"""
    return min(sum(kw["score"] for kw in keywords), 100)


def calculate_decayed_score(raw_score: int, pub_date: datetime) -> dict:
    """감쇠 적용 점수 계산"""
    days_old = max(0, (datetime.now() - pub_date).days)
    decay_rate = calc_decay(days_old)
    decayed = round(raw_score * decay_rate)

    return {
        "raw_score": raw_score,
        "decayed_score": min(decayed, 100),
        "days_old": days_old,
        "decay_rate": round(decay_rate, 3),
    }


def determine_sentiment(score: int) -> str:
    """점수 기반 감성 판단"""
    if score >= 30:
        return "부정"
    elif score >= 10:
        return "주의"
    else:
        return "중립"
```

### 3.3 risk_calculator_v3.py - 리스크 점수 계산기

```python
"""
리스크 점수 계산기 v3
- 책임: 직접 리스크 + 전이 리스크 통합 계산, breakdown 제공
- 위치: risk_engine/risk_calculator_v3.py
"""
from dataclasses import dataclass
from typing import Optional

# === 상수 ===

CATEGORY_WEIGHTS = {
    "MARKET": 0.20,
    "CREDIT": 0.20,
    "OPERATIONAL": 0.15,
    "LEGAL": 0.15,
    "SUPPLY": 0.20,
    "ESG": 0.10,
}

TIER_PROPAGATION_RATE = {
    1: 0.8,  # Tier 1: 80% 전이
    2: 0.5,  # Tier 2: 50% 전이
    3: 0.2,  # Tier 3: 20% 전이
}

MAX_PROPAGATED_RISK = 25  # 전이 리스크 상한

STATUS_THRESHOLDS = {
    "PASS": (0, 49),
    "WARNING": (50, 74),
    "FAIL": (75, 100),
}

# === 데이터 클래스 ===

@dataclass
class CategoryScore:
    code: str
    name: str
    score: int
    weight: float
    weighted_score: float
    factors: list[str]

@dataclass
class PropagatedScore:
    supplier_name: str
    tier: int
    supplier_risk: int
    dependency: float
    tier_rate: float
    propagated: float

@dataclass
class RiskBreakdown:
    total_score: int
    status: str
    direct_score: int
    propagated_score: int
    direct_breakdown: list[CategoryScore]
    propagated_breakdown: list[PropagatedScore]
    calculated_at: str

# === 함수 ===

def calculate_direct_risk(company_id: str) -> tuple[int, list[CategoryScore]]:
    """직접 리스크 계산 + breakdown"""
    pass

def calculate_propagated_risk(company_id: str) -> tuple[int, list[PropagatedScore]]:
    """전이 리스크 계산 + breakdown"""
    pass

def calculate_total_risk(company_id: str) -> RiskBreakdown:
    """총 리스크 점수 계산"""
    pass

def determine_status(score: int) -> str:
    """점수로 Status 결정"""
    if score < 50:
        return "PASS"
    elif score < 75:
        return "WARNING"
    else:
        return "FAIL"
```

### 3.4 dart_collector_v2.py - DART 수집기

```python
"""
DART 공시 수집기 v2
- 책임: DART API에서 공시 수집, 키워드 매칭, 저장
- 위치: risk_engine/dart_collector_v2.py
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import requests

# === 상수 ===

DART_API_BASE = "https://opendart.fss.or.kr/api"

DART_ENDPOINTS = {
    "company": "company.json",
    "disclosure_list": "list.json",
    "financials": "fnlttSinglAcnt.json",
    "shareholders": "hyslrSttus.json",
    "executives": "elestock.json",
}

COLLECTION_SCHEDULE = {
    "realtime": ["주요사항보고서"],
    "daily": ["임원·주요주주", "합병", "분할"],
    "weekly": ["증권발행"],
    "quarterly": ["분기보고서"],
}

# === 데이터 클래스 ===

@dataclass
class DisclosureData:
    rcept_no: str
    corp_code: str
    corp_name: str
    title: str
    filing_date: str
    source: str = "DART"
    source_url: Optional[str] = None
    keywords: list[str] = None
    risk_score: int = 0
    category: Optional[str] = None
    fetched_at: Optional[datetime] = None
    confidence: float = 0.95

# === 클래스 ===

class DartCollectorV2:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = DART_API_BASE

    def collect_disclosures(self, corp_code: str, days: int = 30) -> list[DisclosureData]:
        """공시 수집"""
        pass

    def collect_company_info(self, corp_code: str) -> dict:
        """기업 기본정보 수집"""
        pass

    def collect_financials(self, corp_code: str, year: str) -> dict:
        """재무제표 수집"""
        pass

    def analyze_disclosure(self, disclosure: DisclosureData) -> DisclosureData:
        """공시 분석 (키워드 매칭)"""
        pass
```

### 3.5 news_collector_v2.py - 뉴스 수집기

```python
"""
뉴스 수집기 v2
- 책임: Google/Naver RSS에서 뉴스 수집, 키워드 매칭, 중복 제거
- 위치: risk_engine/news_collector_v2.py
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set
import hashlib

# === 상수 ===

NEWS_SOURCES = [
    {"name": "네이버뉴스", "method": "GOOGLE_RSS_NAVER", "reliability": 0.85},
    {"name": "구글뉴스", "method": "GOOGLE_RSS", "reliability": 0.75},
]

FILTER_CONFIG = {
    "max_age_days": 30,
    "min_title_length": 10,
    "min_risk_score": 5,
}

# === 데이터 클래스 ===

@dataclass
class NewsData:
    title: str
    url: str
    published_at: datetime
    source: str
    publisher: Optional[str] = None
    keywords: list[str] = None
    raw_score: int = 0
    decayed_score: int = 0
    sentiment: str = "중립"
    confidence: float = 0.5
    is_risk: bool = False
    fetched_at: Optional[datetime] = None

# === 클래스 ===

class NewsCollectorV2:
    def __init__(self):
        self.seen_urls: Set[str] = set()

    def collect_news(self, company_name: str, aliases: list[str] = None, limit: int = 20) -> list[NewsData]:
        """뉴스 수집"""
        pass

    def deduplicate(self, news_list: list[NewsData]) -> list[NewsData]:
        """중복 제거"""
        pass

    def analyze_news(self, news: NewsData) -> NewsData:
        """뉴스 분석 (키워드 매칭)"""
        pass

    def generate_queries(self, company_id: str) -> list[str]:
        """검색 쿼리 생성"""
        pass

    def _url_hash(self, url: str) -> str:
        """URL 해시 생성"""
        return hashlib.md5(url.encode()).hexdigest()
```

### 3.6 validator.py - 데이터 검증 모듈

```python
"""
데이터 검증 모듈
- 책임: 수집 데이터의 유효성 검증, 정규화
- 위치: risk_engine/validator.py
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

# === 상수 ===

REQUIRED_FIELDS = {
    "News": ["title", "source", "url", "published_at"],
    "Disclosure": ["rcept_no", "title", "corp_code", "filing_date"],
    "Company": ["id", "name", "source"],
}

RANGE_VALIDATION = {
    "risk_score": (0, 100),
    "sentiment": (-1, 1),
    "confidence": (0, 1),
}

# === 데이터 클래스 ===

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_data: Optional[dict]

# === 클래스 ===

class DataValidator:
    def validate(self, data: dict, data_type: str) -> ValidationResult:
        """데이터 검증"""
        pass

    def validate_required_fields(self, data: dict, data_type: str) -> list[str]:
        """필수 필드 검증"""
        pass

    def validate_ranges(self, data: dict) -> list[str]:
        """범위 검증"""
        pass

    def check_duplicate(self, data: dict, data_type: str) -> bool:
        """중복 검사"""
        pass

    def normalize(self, data: dict) -> dict:
        """데이터 정규화"""
        pass
```

---

## 4. Data Model

### 4.1 Entity Relationship Diagram (ERD)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              Risk Graph v3 - Entity Relationships (with Person)                   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│                                         ┌─────────────┐                                          │
│                                         │   Status    │                                          │
│                                         │ ─────────── │                                          │
│                                         │ PASS/WARN/  │                                          │
│                                         │ FAIL        │                                          │
│                                         └──────▲──────┘                                          │
│                                                │                                                 │
│                                           IN_STATUS                                              │
│                                                │                                                 │
│  ┌─────────────┐       TARGET        ┌────────┴────────┐       SUPPLIED_BY    ┌─────────────┐   │
│  │    Deal     │────────────────────▶│     Company     │◀─────────────────────│   Company   │   │
│  │ ─────────── │                     │   (DealTarget)  │                      │  (Supplier) │   │
│  │ id, name    │                     │ ─────────────── │       SELLS_TO       └─────────────┘   │
│  │ type, amount│                     │ id, corpCode    │──────────────────────▶                 │
│  └─────────────┘                     │ name, riskScore │                                        │
│                                      │ riskLevel       │       COMPETES_WITH                    │
│                                      └────────┬────────┘◀─────────────────────▶                 │
│                                               │                                                 │
│           ┌───────────────────────────────────┼───────────────────────────────────┐             │
│           │                │                  │                  │                │             │
│      MENTIONED_IN       FILED            HAS_RISK          HAS_FINANCIALS    WORKS_AT          │
│           │                │                  │                  │           OWNS_SHARES        │
│           ▼                ▼                  ▼                  ▼           MANAGES            │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    ┌─────────────┐         │              │
│    │    News     │  │ Disclosure  │  │RiskCategory │    │ Financials  │         │              │
│    │ ─────────── │  │ ─────────── │  │ ─────────── │    │ ─────────── │         │              │
│    │ id, title   │  │ id, rceptNo │  │ id, code    │    │ revenue     │         │              │
│    │ keywords[]  │  │ title       │  │ score       │    │ netIncome   │         │              │
│    │ rawScore    │  │ reportType  │  │ factors[]   │    │ fiscalYear  │         │              │
│    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    └─────────────┘         │              │
│           │                │                │                                    │              │
│           │                │         CONTRIBUTES_TO                              ▼              │
│           │                │                │                          ┌─────────────────┐      │
│           │                │                ▼                          │     Person      │      │
│           │                │        ┌─────────────┐                    │ ─────────────── │      │
│           │                │        │ RiskHistory │                    │ id, name        │      │
│           │                │        │ ─────────── │                    │ personType[]    │      │
│           │                │        │ scoreChange │                    │ currentPosition │      │
│           │                │        │ recordedAt  │                    │ riskScore       │      │
│           │                │        └─────────────┘                    └────────┬────────┘      │
│           │                │                                                    │               │
│           │      MENTIONED_IN_DISCLOSURE                      ┌─────────────────┼───────────┐   │
│           │                │                                  │                 │           │   │
│           │                ▼                            HOLDS_POSITION    HAS_SHAREHOLDING  │   │
│      MENTIONED_IN_NEWS     │                                  │                 │      RELATED_ │
│           │                │                                  ▼                 ▼       TO     │
│           ▼                │                          ┌─────────────┐   ┌─────────────┐  │     │
│    ┌──────┴──────┐         │                          │  Position   │   │Shareholding │  │     │
│    │   Person    │◀────────┘                          │ ─────────── │   │ ─────────── │  │     │
│    └─────────────┘                                    │ title       │   │ shares      │  │     │
│                                                       │ startDate   │   │ ownership % │  │     │
│                                                       │ isCurrent   │   │ reportDate  │  │     │
│                                                       └─────────────┘   └─────────────┘  │     │
│                                                                                          │     │
│    Person ◀─────────────────────────────────────────────────────────────────────────────┘     │
│    (특수관계인)                                                                                │
│                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1.2 Person 중심 상세 ERD

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                Person-Centric Relationships                               │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│                                    ┌─────────────────┐                                   │
│                                    │     Person      │                                   │
│                                    │ ─────────────── │                                   │
│                                    │ id              │                                   │
│                                    │ name            │                                   │
│                                    │ personType[]    │ ← [CEO, SHAREHOLDER, EXECUTIVE]  │
│                                    │ riskScore       │                                   │
│                                    │ riskLevel       │                                   │
│                                    └────────┬────────┘                                   │
│                                             │                                            │
│        ┌──────────────────┬─────────────────┼─────────────────┬────────────────┐        │
│        │                  │                 │                 │                │        │
│    WORKS_AT          OWNS_SHARES        MANAGES         RELATED_TO      MENTIONED_IN   │
│        │                  │                 │                 │                │        │
│        ▼                  ▼                 ▼                 ▼                ▼        │
│  ┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐    ┌──────────┐  │
│  │  Company  │     │  Company  │     │  Company  │     │  Person   │    │News/Disc │  │
│  │ (employer)│     │ (invested)│     │ (managed) │     │ (related) │    │(mentioned│  │
│  └─────┬─────┘     └─────┬─────┘     └───────────┘     └───────────┘    └──────────┘  │
│        │                 │                                                             │
│        │                 ▼                                                             │
│        │          ┌─────────────┐                                                      │
│        │          │Shareholding │                                                      │
│        │          │ ─────────── │                                                      │
│        │          │ shares      │                                                      │
│        │          │ ownership % │                                                      │
│        │          │ rank        │                                                      │
│        │          └─────────────┘                                                      │
│        ▼                                                                               │
│  ┌─────────────┐                                                                       │
│  │  Position   │                                                                       │
│  │ ─────────── │                                                                       │
│  │ title       │ ← "대표이사", "사내이사", "감사"                                        │
│  │ department  │                                                                       │
│  │ startDate   │                                                                       │
│  │ endDate     │ ← null이면 현직                                                       │
│  │ isCurrent   │                                                                       │
│  └─────────────┘                                                                       │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐ │
│  │ Person Types (personType 배열)                                                    │ │
│  ├──────────────────────────────────────────────────────────────────────────────────┤ │
│  │ CEO           : 대표이사                                                          │ │
│  │ CFO           : 재무담당임원                                                       │ │
│  │ EXECUTIVE     : 임원 (등기/비등기)                                                 │ │
│  │ BOARD_MEMBER  : 이사회 구성원                                                      │ │
│  │ SHAREHOLDER   : 주주 (5% 이상)                                                    │ │
│  │ FOUNDER       : 창업자                                                            │ │
│  │ RELATED_PARTY : 특수관계인 (가족 등)                                               │ │
│  └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Node Schemas (전체)

#### 4.2.1 Status 노드 (System)

```cypher
// 시스템 초기화 시 3개 고정 생성 (수정 불가)
(:Status {
  // 식별
  id: String,                    // "PASS" | "WARNING" | "FAIL" (PK)

  // 정의
  name: String,                  // "정상" | "주의" | "위험"
  minScore: Integer,             // 경계값 (하한)
  maxScore: Integer,             // 경계값 (상한)

  // UI
  color: String,                 // "#22C55E" | "#F97316" | "#EF4444"
  icon: String,                  // "check-circle" | "alert-triangle" | "x-circle"
  description: String,           // 조치 설명

  // 메타
  priority: Integer,             // 정렬 우선순위 (FAIL:1, WARNING:2, PASS:3)
  createdAt: DateTime
})

// 예시 데이터
(:Status {id: "PASS", name: "정상", minScore: 0, maxScore: 49, color: "#22C55E", icon: "check-circle", description: "정기 모니터링", priority: 3})
(:Status {id: "WARNING", name: "주의", minScore: 50, maxScore: 74, color: "#F97316", icon: "alert-triangle", description: "집중 모니터링, 원인 분석", priority: 2})
(:Status {id: "FAIL", name: "위험", minScore: 75, maxScore: 100, color: "#EF4444", icon: "x-circle", description: "즉시 대응, 리스크 완화 조치", priority: 1})
```

#### 4.2.2 Deal 노드 (Business)

```cypher
(:Deal {
  // 식별
  id: String,                    // "DEAL_001" (PK)

  // 기본 정보
  name: String,                  // "SK하이닉스 시설자금"
  type: String,                  // "시설자금대출" | "운영자금대출" | "회사채" | "PF"
  amount: Long,                  // 금액 (원)
  currency: String,              // "KRW" | "USD"

  // 기간
  startDate: Date,               // 시작일
  maturityDate: Date,            // 만기일
  durationMonths: Integer,       // 기간 (월)

  // 상태
  dealStatus: String,            // "PIPELINE" | "ACTIVE" | "CLOSED" | "DEFAULT"
  riskLevel: String,             // 딜 대상 기업의 리스크 레벨 (계산값)

  // 담당
  rmName: String,                // 담당 RM
  department: String,            // 담당 부서

  // 출처 메타데이터
  source: String,                // "INTERNAL" (여신관리시스템)
  sourceId: String,              // "LMS-2024-001"

  // 타임스탬프
  createdAt: DateTime,
  updatedAt: DateTime
})
```

#### 4.2.3 Company 노드 (Core)

```cypher
(:Company {
  // === 식별자 ===
  id: String,                    // "COM_SKHYNIX" (PK, 시스템 생성)
  corpCode: String,              // "00126380" (DART 고유번호, UK)
  stockCode: String,             // "000660" (종목코드)
  bizNo: String,                 // "123-45-67890" (사업자등록번호)

  // === 기본 정보 ===
  name: String,                  // "SK하이닉스" (NOT NULL)
  nameEn: String,                // "SK Hynix Inc."
  ceoName: String,               // "곽노정"
  sector: String,                // "반도체"
  sectorCode: String,            // "26"
  market: String,                // "KOSPI" | "KOSDAQ" | "KONEX" | "UNLISTED"

  // === 리스크 점수 (v3 핵심) ===
  totalRiskScore: Integer,       // 0-100 (직접+전이)
  directRiskScore: Integer,      // 직접 리스크 점수
  propagatedRiskScore: Integer,  // 전이 리스크 점수
  riskLevel: String,             // "PASS" | "WARNING" | "FAIL"
  riskTrend: String,             // "UP" | "DOWN" | "STABLE"
  previousScore: Integer,        // 이전 점수 (비교용)
  scoreChangedAt: DateTime,      // 점수 변경 시점

  // === 재무 요약 (Financials 노드에서 복사) ===
  revenue: Long,                 // 매출액 (최신)
  operatingProfit: Long,         // 영업이익
  netIncome: Long,               // 당기순이익
  totalAssets: Long,             // 총자산
  fiscalYear: String,            // "2024"
  fiscalQuarter: String,         // "Q4"

  // === 출처 메타데이터 (v3 필수) ===
  source: String,                // "DART" | "KRX" | "MANUAL" (NOT NULL)
  sourceId: String,              // 원본 식별자
  fetchedAt: DateTime,           // 수집 일시 (NOT NULL)
  isVerified: Boolean,           // 검증 여부
  confidence: Float,             // 신뢰도 0.0-1.0

  // === 플래그 ===
  isDealTarget: Boolean,         // 딜 대상 기업 여부
  isSupplier: Boolean,           // 공급사 여부
  isMonitored: Boolean,          // 모니터링 대상 여부
  isActive: Boolean,             // 활성 상태

  // === 검색 지원 ===
  aliases: [String],             // ["하이닉스", "SK Hynix"]
  products: [String],            // ["HBM", "DRAM", "NAND"]

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})

// 라벨 추가: DealTarget (딜 대상인 경우)
(:Company:DealTarget {...})
```

#### 4.2.4 RiskCategory 노드 (Core)

```cypher
(:RiskCategory {
  // === 식별자 ===
  id: String,                    // "RC_SKHYNIX_LEGAL" (PK)
  companyId: String,             // "COM_SKHYNIX" (FK)

  // === 카테고리 정보 ===
  code: String,                  // "LEGAL" | "CREDIT" | "OPERATIONAL" | "MARKET" | "SUPPLY" | "ESG"
  name: String,                  // "법률위험"
  description: String,           // 카테고리 설명

  // === 점수 (v3 핵심) ===
  score: Integer,                // 0-100 (카테고리 점수)
  weight: Float,                 // 가중치 (0.0-1.0)
  weightedScore: Float,          // score × weight
  maxPossibleScore: Integer,     // 최대 가능 점수 (참고용)

  // === 트렌드 ===
  trend: String,                 // "UP" | "DOWN" | "STABLE"
  previousScore: Integer,        // 이전 점수
  changeAmount: Integer,         // 변화량 (양수/음수)
  changePercent: Float,          // 변화율 (%)

  // === 근거 (v3 투명화) ===
  factors: [String],             // ["ITC 특허소송 패소 (+50)", "EU 반독점 조사 (+15)"]
  factorCount: Integer,          // 근거 개수
  topFactor: String,             // 가장 영향 큰 요소
  baseDataIds: [String],         // 근거 데이터 참조 ["NEWS_0001", "DISC_0001"]

  // === 출처 ===
  source: String,                // "CALCULATED"
  calculatedAt: DateTime,        // 계산 시점

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

#### 4.2.5 News 노드 (Data)

```cypher
(:News {
  // === 식별자 ===
  id: String,                    // "NEWS_0001" (PK)
  urlHash: String,               // MD5(sourceUrl) - 중복 체크용 (UK)

  // === 내용 ===
  title: String,                 // 제목 (NOT NULL)
  summary: String,               // 요약 (AI 생성 또는 원문 일부)
  content: String,               // 전문 (선택적)

  // === 분류 (v3 키워드 기반) ===
  category: String,              // "LEGAL" | "CREDIT" | "GOVERNANCE" | "OPERATIONAL" | "AUDIT" | "ESG"
  sentiment: Float,              // -1.0 ~ +1.0
  sentimentLabel: String,        // "부정" | "중립" | "긍정"
  importance: String,            // "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"

  // === 점수 (v3 계산) ===
  rawScore: Integer,             // 원점수 (감쇠 전)
  decayedScore: Integer,         // 감쇠 후 점수
  impactScore: Integer,          // 기업 점수에 미치는 영향
  daysOld: Integer,              // 발행 후 경과일
  decayRate: Float,              // 적용된 감쇠율

  // === 키워드 (v3 매칭 결과) ===
  matchedKeywords: [String],     // ["횡령(50)", "소송(25)"]
  keywordScores: [Integer],      // [50, 25]
  keywordCount: Integer,         // 매칭 키워드 수
  primaryKeyword: String,        // 가장 높은 점수 키워드

  // === 출처 (v3 필수) ===
  source: String,                // "NEWS_NAVER" | "NEWS_GOOGLE" | "NEWS_DAUM"
  sourceUrl: String,             // 원본 URL (NOT NULL)
  publisher: String,             // "한국경제" | "매일경제"
  author: String,                // 기자명
  publishedAt: DateTime,         // 발행 일시 (NOT NULL)

  // === 수집 정보 ===
  fetchedAt: DateTime,           // 수집 일시 (NOT NULL)
  crawlMethod: String,           // "GOOGLE_RSS" | "NAVER_API" | "DIRECT"
  searchQuery: String,           // 검색에 사용된 쿼리

  // === 품질 ===
  confidence: Float,             // 신뢰도 0.0-1.0
  isVerified: Boolean,           // AI 분석 검증 여부
  isRisk: Boolean,               // 리스크 뉴스 여부

  // === AI 분석 (선택적) ===
  aiAnalyzedAt: DateTime,
  aiModel: String,               // "gpt-4-turbo"
  aiSummary: String,

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

#### 4.2.6 Disclosure 노드 (Data)

```cypher
(:Disclosure {
  // === 식별자 ===
  id: String,                    // "DISC_0001" (PK)
  rceptNo: String,               // "20260201000123" (DART 접수번호, UK)

  // === 기본 정보 ===
  title: String,                 // "주요사항보고서(소송등의제기)" (NOT NULL)
  reportType: String,            // "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I"
  reportTypeCode: String,        // "A001" | "B001" 등
  reportTypeName: String,        // "사업보고서" | "주요사항보고서"

  // === 기업 정보 ===
  corpCode: String,              // "00126380" (FK → Company)
  corpName: String,              // "SK하이닉스"
  stockCode: String,             // "000660"
  submitter: String,             // 제출인 (보고서 제출자)

  // === 일시 ===
  filingDate: Date,              // 접수일 (NOT NULL)
  filingDateTime: DateTime,      // 접수 일시 (정밀)

  // === 분석 (v3) ===
  category: String,              // "LEGAL" | "CREDIT" | ...
  importance: String,            // "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  rawScore: Integer,             // 원점수
  decayedScore: Integer,         // 감쇠 후 점수
  impactScore: Integer,

  // === 키워드 (v3 매칭 결과) ===
  matchedKeywords: [String],
  keywordCount: Integer,
  primaryKeyword: String,

  // === 요약 ===
  summary: String,               // AI 요약 또는 주요 내용
  remark: String,                // DART 비고 (rm 필드)

  // === 출처 (v3 필수) ===
  source: String,                // "DART"
  sourceUrl: String,             // https://dart.fss.or.kr/dsaf001/main.do?rcpNo=...
  fetchedAt: DateTime,
  confidence: Float,             // DART = 1.0 (공신력)
  isVerified: Boolean,           // true (공식 데이터)

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

#### 4.2.7 Financials 노드 (Data)

```cypher
(:Financials {
  // === 식별자 ===
  id: String,                    // "FIN_SKHYNIX_2024Q4" (PK)
  companyId: String,             // "COM_SKHYNIX" (FK)

  // === 기간 ===
  fiscalYear: String,            // "2024"
  fiscalQuarter: String,         // "Q4" | "ANNUAL"
  reportCode: String,            // "11011" (사업보고서) | "11012" (반기) | "11013" | "11014" (분기)

  // === 손익계산서 (IS) ===
  revenue: Long,                 // 매출액
  costOfSales: Long,             // 매출원가
  grossProfit: Long,             // 매출총이익
  operatingProfit: Long,         // 영업이익
  netIncome: Long,               // 당기순이익
  eps: Float,                    // 주당순이익

  // === 재무상태표 (BS) ===
  totalAssets: Long,             // 총자산
  totalLiabilities: Long,        // 총부채
  totalEquity: Long,             // 총자본
  currentAssets: Long,           // 유동자산
  currentLiabilities: Long,      // 유동부채

  // === 현금흐름표 (CF) ===
  operatingCashFlow: Long,       // 영업활동현금흐름
  investingCashFlow: Long,       // 투자활동현금흐름
  financingCashFlow: Long,       // 재무활동현금흐름

  // === 재무비율 (계산) ===
  debtRatio: Float,              // 부채비율 = 총부채/총자본
  currentRatio: Float,           // 유동비율 = 유동자산/유동부채
  operatingMargin: Float,        // 영업이익률 = 영업이익/매출액
  netMargin: Float,              // 순이익률 = 당기순이익/매출액
  roe: Float,                    // ROE = 당기순이익/총자본

  // === 전기 비교 ===
  prevRevenue: Long,
  revenueGrowth: Float,          // 매출 성장률
  prevNetIncome: Long,
  netIncomeGrowth: Float,        // 순이익 성장률

  // === 출처 ===
  source: String,                // "DART"
  sourceId: String,              // 접수번호
  fetchedAt: DateTime,
  confidence: Float,

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

#### 4.2.8 RiskHistory 노드 (Audit)

```cypher
(:RiskHistory {
  // === 식별자 ===
  id: String,                    // "RH_0001" (PK)
  companyId: String,             // "COM_SKHYNIX" (FK)

  // === 이벤트 정보 ===
  eventType: String,             // "SCORE_CHANGE" | "STATUS_CHANGE" | "NEW_RISK" | "RISK_RESOLVED"
  eventDescription: String,      // 이벤트 설명

  // === 점수 변화 ===
  previousScore: Integer,
  newScore: Integer,
  scoreChange: Integer,          // 변화량 (양수/음수)

  // === Status 변화 ===
  previousStatus: String,        // "WARNING"
  newStatus: String,             // "FAIL"

  // === 원인 ===
  triggerType: String,           // "NEWS" | "DISCLOSURE" | "PROPAGATION" | "MANUAL"
  triggerId: String,             // 트리거 데이터 ID
  triggerSummary: String,        // 트리거 요약

  // === 카테고리 영향 ===
  affectedCategory: String,      // "LEGAL"
  categoryScoreChange: Integer,

  // === 타임스탬프 ===
  recordedAt: DateTime,          // 기록 시점 (NOT NULL)
  createdAt: DateTime
})
```

#### 4.2.9 Person 노드 (Core)

```cypher
(:Person {
  // === 식별자 ===
  id: String,                    // "PER_0001" (PK)

  // === 기본 정보 ===
  name: String,                  // "홍길동" (NOT NULL)
  nameEn: String,                // "Gil-Dong Hong"
  birthYear: Integer,            // 1970 (선택)

  // === 유형 ===
  personType: [String],          // ["EXECUTIVE", "SHAREHOLDER", "BOARD_MEMBER"]
                                 // EXECUTIVE: 임원
                                 // SHAREHOLDER: 주주
                                 // BOARD_MEMBER: 이사회 구성원
                                 // CEO: 대표이사
                                 // CFO: 재무담당
                                 // FOUNDER: 창업자
                                 // RELATED_PARTY: 특수관계인

  // === 현재 직책 (주요 기업 기준) ===
  currentPosition: String,       // "대표이사"
  currentCompanyId: String,      // "COM_SKHYNIX" (주요 소속 기업)
  currentCompanyName: String,    // "SK하이닉스"

  // === 리스크 관련 ===
  riskScore: Integer,            // 인물 관련 리스크 점수 (0-100)
  riskLevel: String,             // "PASS" | "WARNING" | "FAIL"
  riskFactors: [String],         // ["횡령 혐의", "배임 전력"]
  hasNegativeNews: Boolean,      // 부정적 뉴스 존재 여부
  negativeNewsCount: Integer,    // 부정 뉴스 건수

  // === 이력 요약 ===
  totalCompanies: Integer,       // 관련 기업 수
  totalPositions: Integer,       // 역임 직책 수
  yearsOfExperience: Integer,    // 경력 년수

  // === 출처 ===
  source: String,                // "DART" | "NEWS" | "MANUAL"
  sourceId: String,
  fetchedAt: DateTime,
  confidence: Float,
  isVerified: Boolean,

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})

// 라벨 추가
(:Person:Executive {...})        // 임원인 경우
(:Person:Shareholder {...})      // 주주인 경우
(:Person:CEO {...})              // 대표이사인 경우
```

#### 4.2.10 Shareholding 노드 (Data)

```cypher
(:Shareholding {
  // === 식별자 ===
  id: String,                    // "SH_0001" (PK)

  // === 지분 정보 ===
  sharesOwned: Long,             // 보유 주식 수
  sharesTotal: Long,             // 발행 주식 총수
  ownershipPercent: Float,       // 지분율 (%) - 0.0-100.0
  ownershipRank: Integer,        // 지분 순위 (1=최대주주)

  // === 지분 유형 ===
  shareType: String,             // "COMMON" | "PREFERRED" (보통주/우선주)
  holderType: String,            // "INDIVIDUAL" | "INSTITUTION" | "FOREIGN"
                                 // INDIVIDUAL: 개인
                                 // INSTITUTION: 기관
                                 // FOREIGN: 외국인

  // === 변동 정보 ===
  previousShares: Long,          // 이전 보유량
  sharesChange: Long,            // 변동량 (양수/음수)
  changePercent: Float,          // 변동률 (%)
  changeReason: String,          // "장내매수" | "장내매도" | "상속" | "증여"

  // === 기간 ===
  reportDate: Date,              // 보고 기준일
  acquiredDate: Date,            // 취득일 (최초)

  // === 출처 ===
  source: String,                // "DART"
  sourceId: String,              // 접수번호
  reportType: String,            // "hyslrSttus" | "elestock"
  fetchedAt: DateTime,
  confidence: Float,

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

#### 4.2.11 Position 노드 (Data)

```cypher
(:Position {
  // === 식별자 ===
  id: String,                    // "POS_0001" (PK)

  // === 직책 정보 ===
  title: String,                 // "대표이사" | "사내이사" | "사외이사" | "감사"
  titleEn: String,               // "CEO" | "Director" | "Outside Director" | "Auditor"
  department: String,            // "경영총괄" | "재무" | "기술"
  rank: String,                  // "임원" | "등기임원" | "비등기임원"

  // === 분류 ===
  positionType: String,          // "EXECUTIVE" | "BOARD" | "AUDIT"
                                 // EXECUTIVE: 집행임원
                                 // BOARD: 이사회
                                 // AUDIT: 감사/감사위원
  isRegistered: Boolean,         // 등기임원 여부
  isFullTime: Boolean,           // 상근 여부

  // === 보수 정보 (선택) ===
  annualSalary: Long,            // 연간 보수 (원)
  stockOptions: Long,            // 스톡옵션 (주)

  // === 기간 ===
  startDate: Date,               // 취임일
  endDate: Date,                 // 퇴임일 (null이면 현직)
  tenure: Integer,               // 재임 기간 (월)
  isCurrent: Boolean,            // 현직 여부

  // === 변동 이력 ===
  appointmentType: String,       // "NEW" | "REAPPOINTMENT" | "INTERNAL_PROMOTION"
  terminationType: String,       // "RESIGNATION" | "DISMISSAL" | "TERM_END" | "DEATH"
  terminationReason: String,     // 퇴임 사유

  // === 출처 ===
  source: String,                // "DART" | "NEWS"
  sourceId: String,
  fetchedAt: DateTime,
  confidence: Float,

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

### 4.3 Relationship Schemas (전체)

#### 4.3.1 Deal ↔ Company 관계

```cypher
// 딜 → 대상 기업
(d:Deal)-[:TARGET {
  // 딜 정보
  amount: Long,                  // 이 딜에서의 금액
  since: Date,                   // 관계 시작일
  role: String,                  // "BORROWER" | "GUARANTOR" | "COLLATERAL_PROVIDER"

  // 출처
  source: String,
  createdAt: DateTime
}]->(c:Company)

// 제약: 하나의 Deal에 하나의 TARGET만 (주 차주)
```

#### 4.3.2 Company ↔ Status 관계

```cypher
// 기업 → 상태 (v3 핵심)
(c:Company)-[:IN_STATUS {
  // 변경 정보
  since: DateTime,               // 이 Status가 된 시점 (NOT NULL)
  reason: String,                // 변경 사유
  previousStatus: String,        // 이전 Status
  scoreAtChange: Integer,        // 변경 시점의 점수

  // 트리거
  triggeredBy: String,           // "NEWS_0001" | "DISC_0001" | "SYSTEM"
  triggerType: String,           // "NEWS" | "DISCLOSURE" | "CALCULATION"

  // 출처
  source: String,                // "CALCULATED"
  createdAt: DateTime
}]->(s:Status)

// 제약: Company는 정확히 하나의 Status와 연결
```

#### 4.3.3 Company ↔ Company 관계 (공급망)

```cypher
// 공급 관계 (target ← supplier)
(target:Company)-[:SUPPLIED_BY {
  // Tier 정보
  tier: Integer,                 // 1 | 2 | 3 (NOT NULL)
  tierLabel: String,             // "Tier 1 (직접)"

  // 의존도
  dependency: Float,             // 0.0-1.0 (NOT NULL)
  dependencyLabel: String,       // "HIGH" | "MEDIUM" | "LOW"
  isCritical: Boolean,           // 핵심 공급사 여부

  // 거래 정보
  transactionType: String,       // "장비공급" | "원자재" | "서비스"
  annualVolume: Long,            // 연간 거래액
  contractStartDate: Date,
  contractEndDate: Date,

  // 리스크 전이
  supplierRiskScore: Integer,    // 공급사의 현재 리스크 점수
  propagatedRisk: Float,         // 전이된 리스크 점수

  // 출처
  source: String,                // "DART_ANALYSIS" | "MANUAL" | "NEWS_EXTRACT"
  sourceNote: String,            // "2024 사업보고서 주요거래처"
  verifiedAt: DateTime,
  verifiedBy: String,

  // 타임스탬프
  createdAt: DateTime,
  updatedAt: DateTime
}]->(supplier:Company)

// 판매 관계 (seller → customer)
(seller:Company)-[:SELLS_TO {
  revenueShare: Float,           // 매출 비중 (0.0-1.0)
  isTopCustomer: Boolean,        // 주요 고객사 여부
  source: String,
  createdAt: DateTime
}]->(customer:Company)

// 경쟁 관계 (양방향)
(c1:Company)-[:COMPETES_WITH {
  similarity: Float,             // 사업 유사도 (0.0-1.0)
  competitionArea: String,       // "반도체" | "배터리"
  source: String,
  createdAt: DateTime
}]->(c2:Company)
```

#### 4.3.4 Company ↔ News 관계

```cypher
(c:Company)-[:MENTIONED_IN {
  // 관련도
  relevance: Float,              // 0.0-1.0 (기사에서 기업의 중요도)
  mentionType: String,           // "PRIMARY" | "SECONDARY" | "MENTIONED"
  mentionCount: Integer,         // 기사 내 언급 횟수

  // 영향
  impactOnScore: Integer,        // 이 뉴스가 기업 점수에 미친 영향

  // 타임스탬프
  mentionedAt: DateTime,         // 언급 시점 (기사 발행일)
  processedAt: DateTime,         // 처리 시점
  createdAt: DateTime
}]->(n:News)
```

#### 4.3.5 Company ↔ Disclosure 관계

```cypher
(c:Company)-[:FILED {
  // 공시 역할
  role: String,                  // "FILER" | "SUBJECT" | "RELATED"

  // 영향
  impactOnScore: Integer,

  // 타임스탬프
  filedAt: DateTime,             // 공시 접수일
  processedAt: DateTime,
  createdAt: DateTime
}]->(d:Disclosure)
```

#### 4.3.6 Company ↔ RiskCategory 관계

```cypher
(c:Company)-[:HAS_RISK {
  // 점수 영향
  contribution: Float,           // 이 카테고리가 총점에 기여하는 점수

  // 타임스탬프
  calculatedAt: DateTime,
  createdAt: DateTime
}]->(rc:RiskCategory)
```

#### 4.3.7 Company ↔ Financials 관계

```cypher
(c:Company)-[:HAS_FINANCIALS {
  // 기간
  fiscalPeriod: String,          // "2024Q4"
  isLatest: Boolean,             // 최신 재무정보 여부

  // 타임스탬프
  createdAt: DateTime
}]->(f:Financials)
```

#### 4.3.8 RiskCategory ↔ RiskHistory 관계

```cypher
(rc:RiskCategory)-[:CONTRIBUTES_TO {
  // 기여도
  contribution: Integer,         // 점수 변화에 기여한 양

  // 타임스탬프
  contributedAt: DateTime,
  createdAt: DateTime
}]->(rh:RiskHistory)
```

#### 4.3.9 Person ↔ Company 관계

```cypher
// 임원/경영진 관계 (Person이 Company에서 직책 보유)
(p:Person)-[:WORKS_AT {
  // 직책 참조
  positionId: String,            // Position 노드 ID (상세 정보)
  position: String,              // "대표이사" | "사내이사" | "감사"
  department: String,            // "경영총괄"

  // 유형
  role: String,                  // "CEO" | "CFO" | "CTO" | "DIRECTOR" | "AUDITOR"
  isExecutive: Boolean,          // 임원 여부
  isRegistered: Boolean,         // 등기임원 여부
  isCurrent: Boolean,            // 현직 여부

  // 기간
  startDate: Date,               // 취임일
  endDate: Date,                 // 퇴임일 (null = 현직)
  tenure: Integer,               // 재임 기간 (월)

  // 출처
  source: String,                // "DART" | "NEWS"
  sourceId: String,
  fetchedAt: DateTime,
  createdAt: DateTime,
  updatedAt: DateTime
}]->(c:Company)

// 지분 보유 관계 (Person이 Company 주식 보유)
(p:Person)-[:OWNS_SHARES {
  // 지분 참조
  shareholdingId: String,        // Shareholding 노드 ID (상세 정보)

  // 지분 요약
  sharesOwned: Long,             // 보유 주식 수
  ownershipPercent: Float,       // 지분율 (%)
  ownershipRank: Integer,        // 지분 순위

  // 유형
  holderType: String,            // "MAJOR" | "EXECUTIVE" | "RELATED_PARTY"
                                 // MAJOR: 최대주주/주요주주
                                 // EXECUTIVE: 임원 주주
                                 // RELATED_PARTY: 특수관계인
  isMajorShareholder: Boolean,   // 최대주주 여부 (5% 이상)
  isControlling: Boolean,        // 지배주주 여부

  // 변동
  previousPercent: Float,        // 이전 지분율
  changePercent: Float,          // 변동률

  // 기간
  reportDate: Date,              // 보고 기준일
  acquiredDate: Date,            // 최초 취득일

  // 출처
  source: String,                // "DART"
  sourceId: String,
  fetchedAt: DateTime,
  createdAt: DateTime,
  updatedAt: DateTime
}]->(c:Company)

// 경영 책임 관계 (대표이사/CEO 특별 관계)
(p:Person)-[:MANAGES {
  // 역할
  managementRole: String,        // "CEO" | "CO_CEO" | "ACTING_CEO"
  responsibility: String,        // "전체 경영" | "국내 사업" | "해외 사업"

  // 기간
  startDate: Date,
  endDate: Date,
  isCurrent: Boolean,

  // 출처
  source: String,
  createdAt: DateTime
}]->(c:Company)
```

#### 4.3.10 Person ↔ Person 관계

```cypher
// 특수관계인 관계
(p1:Person)-[:RELATED_TO {
  // 관계 유형
  relationType: String,          // "FAMILY" | "BUSINESS" | "AFFILIATION"
  relationDetail: String,        // "배우자" | "자녀" | "형제" | "계열사 임원"

  // 가족 관계 상세
  familyRelation: String,        // "SPOUSE" | "CHILD" | "PARENT" | "SIBLING"

  // 출처
  source: String,
  sourceNote: String,
  createdAt: DateTime
}]->(p2:Person)

// 공동 임원 관계 (같은 회사 임원)
(p1:Person)-[:COLLEAGUE_WITH {
  companyId: String,             // 공동 근무 기업
  companyName: String,
  overlapPeriod: Integer,        // 중복 기간 (월)
  createdAt: DateTime
}]->(p2:Person)
```

#### 4.3.11 Person ↔ News/Disclosure 관계

```cypher
// Person이 뉴스에 언급됨
(p:Person)-[:MENTIONED_IN_NEWS {
  // 언급 정보
  mentionType: String,           // "SUBJECT" | "RELATED" | "QUOTE"
                                 // SUBJECT: 기사 주인공
                                 // RELATED: 관련자로 언급
                                 // QUOTE: 인용/코멘트
  mentionContext: String,        // "횡령 혐의" | "신임 대표이사" | "인터뷰"
  sentiment: Float,              // 기사의 인물 관련 감성 (-1 ~ +1)

  // 영향
  impactOnPersonRisk: Integer,   // 인물 리스크 점수 영향

  // 타임스탬프
  mentionedAt: DateTime,
  createdAt: DateTime
}]->(n:News)

// Person이 공시에 언급됨
(p:Person)-[:MENTIONED_IN_DISCLOSURE {
  // 언급 유형
  mentionType: String,           // "FILER" | "SUBJECT" | "APPOINTEE" | "RESIGNED"
                                 // FILER: 보고서 제출자
                                 // SUBJECT: 보고 대상
                                 // APPOINTEE: 선임된 인물
                                 // RESIGNED: 퇴임한 인물
  role: String,                  // 공시에서의 역할

  // 변동 정보
  eventType: String,             // "APPOINTMENT" | "RESIGNATION" | "SHARES_CHANGE"
  eventDetail: String,           // 상세 내용

  // 타임스탬프
  mentionedAt: DateTime,
  createdAt: DateTime
}]->(d:Disclosure)
```

#### 4.3.12 Company ↔ Shareholding/Position 관계

```cypher
// Company의 지분 구조
(c:Company)-[:HAS_SHAREHOLDING {
  reportDate: Date,              // 보고 기준일
  totalShareholders: Integer,    // 주주 수
  createdAt: DateTime
}]->(sh:Shareholding)

// Company의 직책
(c:Company)-[:HAS_POSITION {
  isCurrent: Boolean,
  createdAt: DateTime
}]->(pos:Position)

// Person과 Position 연결
(p:Person)-[:HOLDS_POSITION {
  isCurrent: Boolean,
  startDate: Date,
  endDate: Date,
  createdAt: DateTime
}]->(pos:Position)

// Person과 Shareholding 연결
(p:Person)-[:HAS_SHAREHOLDING {
  createdAt: DateTime
}]->(sh:Shareholding)
```

### 4.4 Constraints & Indexes

```cypher
// === 유일성 제약조건 (Unique Constraints) ===
CREATE CONSTRAINT company_id_unique FOR (c:Company) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT company_corp_code_unique FOR (c:Company) REQUIRE c.corpCode IS UNIQUE;
CREATE CONSTRAINT status_id_unique FOR (s:Status) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT deal_id_unique FOR (d:Deal) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT news_id_unique FOR (n:News) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT news_url_hash_unique FOR (n:News) REQUIRE n.urlHash IS UNIQUE;
CREATE CONSTRAINT disclosure_id_unique FOR (d:Disclosure) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT disclosure_rcept_unique FOR (d:Disclosure) REQUIRE d.rceptNo IS UNIQUE;
CREATE CONSTRAINT risk_category_id_unique FOR (rc:RiskCategory) REQUIRE rc.id IS UNIQUE;
CREATE CONSTRAINT financials_id_unique FOR (f:Financials) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT risk_history_id_unique FOR (rh:RiskHistory) REQUIRE rh.id IS UNIQUE;

// === 존재 제약조건 (Not Null) ===
CREATE CONSTRAINT company_name_exists FOR (c:Company) REQUIRE c.name IS NOT NULL;
CREATE CONSTRAINT company_source_exists FOR (c:Company) REQUIRE c.source IS NOT NULL;
CREATE CONSTRAINT news_title_exists FOR (n:News) REQUIRE n.title IS NOT NULL;
CREATE CONSTRAINT news_source_url_exists FOR (n:News) REQUIRE n.sourceUrl IS NOT NULL;

// === 성능 최적화 인덱스 ===
// Company
CREATE INDEX company_risk_level_idx FOR (c:Company) ON (c.riskLevel);
CREATE INDEX company_total_score_idx FOR (c:Company) ON (c.totalRiskScore);
CREATE INDEX company_is_deal_target_idx FOR (c:Company) ON (c.isDealTarget);
CREATE INDEX company_market_idx FOR (c:Company) ON (c.market);
CREATE INDEX company_sector_idx FOR (c:Company) ON (c.sector);

// News
CREATE INDEX news_published_at_idx FOR (n:News) ON (n.publishedAt);
CREATE INDEX news_source_idx FOR (n:News) ON (n.source);
CREATE INDEX news_category_idx FOR (n:News) ON (n.category);
CREATE INDEX news_is_risk_idx FOR (n:News) ON (n.isRisk);
CREATE INDEX news_decayed_score_idx FOR (n:News) ON (n.decayedScore);

// Disclosure
CREATE INDEX disclosure_filing_date_idx FOR (d:Disclosure) ON (d.filingDate);
CREATE INDEX disclosure_corp_code_idx FOR (d:Disclosure) ON (d.corpCode);
CREATE INDEX disclosure_report_type_idx FOR (d:Disclosure) ON (d.reportType);
CREATE INDEX disclosure_category_idx FOR (d:Disclosure) ON (d.category);

// RiskCategory
CREATE INDEX risk_category_company_idx FOR (rc:RiskCategory) ON (rc.companyId);
CREATE INDEX risk_category_code_idx FOR (rc:RiskCategory) ON (rc.code);
CREATE INDEX risk_category_score_idx FOR (rc:RiskCategory) ON (rc.score);

// RiskHistory
CREATE INDEX risk_history_company_idx FOR (rh:RiskHistory) ON (rh.companyId);
CREATE INDEX risk_history_recorded_at_idx FOR (rh:RiskHistory) ON (rh.recordedAt);
CREATE INDEX risk_history_event_type_idx FOR (rh:RiskHistory) ON (rh.eventType);

// Financials
CREATE INDEX financials_company_idx FOR (f:Financials) ON (f.companyId);
CREATE INDEX financials_fiscal_year_idx FOR (f:Financials) ON (f.fiscalYear);

// Person
CREATE INDEX person_name_idx FOR (p:Person) ON (p.name);
CREATE INDEX person_type_idx FOR (p:Person) ON (p.personType);
CREATE INDEX person_risk_level_idx FOR (p:Person) ON (p.riskLevel);
CREATE INDEX person_current_company_idx FOR (p:Person) ON (p.currentCompanyId);

// Shareholding
CREATE INDEX shareholding_ownership_idx FOR (sh:Shareholding) ON (sh.ownershipPercent);
CREATE INDEX shareholding_report_date_idx FOR (sh:Shareholding) ON (sh.reportDate);

// Position
CREATE INDEX position_title_idx FOR (pos:Position) ON (pos.title);
CREATE INDEX position_is_current_idx FOR (pos:Position) ON (pos.isCurrent);

// 복합 인덱스
CREATE INDEX news_source_published_idx FOR (n:News) ON (n.source, n.publishedAt);
CREATE INDEX company_level_score_idx FOR (c:Company) ON (c.riskLevel, c.totalRiskScore);
CREATE INDEX person_company_role_idx FOR (p:Person) ON (p.currentCompanyId, p.personType);
```

// === Person 관련 제약조건 ===
CREATE CONSTRAINT person_id_unique FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT person_name_exists FOR (p:Person) REQUIRE p.name IS NOT NULL;
CREATE CONSTRAINT shareholding_id_unique FOR (sh:Shareholding) REQUIRE sh.id IS UNIQUE;
CREATE CONSTRAINT position_id_unique FOR (pos:Position) REQUIRE pos.id IS UNIQUE;
```

### 4.5 Data Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                            Data Lifecycle & Retention                                 │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  [CREATE]                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │  News          : 수집 시 생성 (30일 이내 뉴스만)                                  ││
│  │  Disclosure    : 수집 시 생성 (1년 이내 공시)                                     ││
│  │  RiskCategory  : 점수 계산 시 생성/갱신                                           ││
│  │  RiskHistory   : Status 또는 점수 변경 시 생성                                    ││
│  │  Financials    : 분기/연간 보고서 수집 시 생성                                    ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  [UPDATE]                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │  Company.riskScore : 관련 News/Disclosure 변경 시 재계산                         ││
│  │  Company.riskLevel : 점수 임계치 초과 시 Status 변경                              ││
│  │  News.decayedScore : 매일 감쇠 재계산 (선택적)                                    ││
│  │  RiskCategory      : 관련 데이터 변경 시 재계산                                   ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  [RETENTION (보존 기간)]                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │  Status         : 영구 (시스템 노드)                                             ││
│  │  Deal           : 영구 (비즈니스 핵심)                                            ││
│  │  Company        : 영구 (isActive=false로 비활성화)                                ││
│  │  RiskCategory   : 영구 (이력 유지)                                               ││
│  │  News           : 1년 (이후 archive 또는 삭제)                                    ││
│  │  Disclosure     : 5년 (법적 보존 기간)                                            ││
│  │  RiskHistory    : 3년 (감사 목적)                                                 ││
│  │  Financials     : 5년 (재무 이력)                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  [ARCHIVE/DELETE]                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │  News           : 1년 후 → archived=true 또는 삭제                               ││
│  │  RiskHistory    : 3년 후 → 월별 집계로 요약 후 삭제                               ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.6 Sample Data

#### 4.6.1 Company 예시

```cypher
CREATE (c:Company:DealTarget {
  id: "COM_SKHYNIX",
  corpCode: "00126380",
  stockCode: "000660",
  name: "SK하이닉스",
  nameEn: "SK Hynix Inc.",
  ceoName: "곽노정",
  sector: "반도체",
  sectorCode: "26",
  market: "KOSPI",

  totalRiskScore: 72,
  directRiskScore: 65,
  propagatedRiskScore: 7,
  riskLevel: "FAIL",
  riskTrend: "UP",
  previousScore: 58,
  scoreChangedAt: datetime("2026-02-06T15:30:00"),

  revenue: 42998500000000,
  operatingProfit: 2200000000000,
  netIncome: 1800000000000,
  totalAssets: 85000000000000,
  fiscalYear: "2024",
  fiscalQuarter: "Q4",

  source: "DART",
  sourceId: "00126380",
  fetchedAt: datetime("2026-02-06T10:00:00"),
  isVerified: true,
  confidence: 0.95,

  isDealTarget: true,
  isSupplier: false,
  isMonitored: true,
  isActive: true,

  aliases: ["하이닉스", "SK Hynix", "에스케이하이닉스"],
  products: ["HBM", "HBM3", "DRAM", "NAND"],

  createdAt: datetime("2026-01-01T00:00:00"),
  updatedAt: datetime("2026-02-06T15:30:00")
})
```

#### 4.6.2 News 예시

```cypher
CREATE (n:News {
  id: "NEWS_0001",
  urlHash: "a1b2c3d4e5f6",

  title: "SK하이닉스, 美 ITC 특허 소송 패소",
  summary: "미국 국제무역위원회가 SK하이닉스의 특허 침해를 인정...",

  category: "LEGAL",
  sentiment: -0.8,
  sentimentLabel: "부정",
  importance: "HIGH",

  rawScore: 75,
  decayedScore: 71,
  impactScore: 15,
  daysOld: 2,
  decayRate: 0.935,

  matchedKeywords: ["소송(25)", "특허(20)", "패소(30)"],
  keywordScores: [25, 20, 30],
  keywordCount: 3,
  primaryKeyword: "패소",

  source: "NEWS_NAVER",
  sourceUrl: "https://news.naver.com/article/...",
  publisher: "한국경제",
  author: "김기자",
  publishedAt: datetime("2026-02-04T09:00:00"),

  fetchedAt: datetime("2026-02-04T09:30:00"),
  crawlMethod: "GOOGLE_RSS",
  searchQuery: "SK하이닉스",

  confidence: 0.78,
  isVerified: false,
  isRisk: true,

  createdAt: datetime("2026-02-04T09:30:00"),
  updatedAt: datetime("2026-02-04T09:30:00")
})
```

#### 4.6.3 관계 예시

```cypher
// Company → Status
MATCH (c:Company {id: "COM_SKHYNIX"}), (s:Status {id: "FAIL"})
CREATE (c)-[:IN_STATUS {
  since: datetime("2026-02-06T15:30:00"),
  reason: "ITC 특허 소송 패소로 법률위험 급등",
  previousStatus: "WARNING",
  scoreAtChange: 72,
  triggeredBy: "NEWS_0001",
  triggerType: "NEWS",
  source: "CALCULATED",
  createdAt: datetime("2026-02-06T15:30:00")
}]->(s)

// Company → News
MATCH (c:Company {id: "COM_SKHYNIX"}), (n:News {id: "NEWS_0001"})
CREATE (c)-[:MENTIONED_IN {
  relevance: 0.95,
  mentionType: "PRIMARY",
  mentionCount: 5,
  impactOnScore: 15,
  mentionedAt: datetime("2026-02-04T09:00:00"),
  processedAt: datetime("2026-02-04T09:35:00"),
  createdAt: datetime("2026-02-04T09:35:00")
}]->(n)

// Company → Company (공급망)
MATCH (target:Company {id: "COM_SKHYNIX"}), (supplier:Company {id: "COM_HANAMC"})
CREATE (target)-[:SUPPLIED_BY {
  tier: 1,
  tierLabel: "Tier 1 (직접)",
  dependency: 0.25,
  dependencyLabel: "MEDIUM",
  isCritical: true,
  transactionType: "장비공급",
  annualVolume: 50000000000,
  supplierRiskScore: 65,
  propagatedRisk: 13.0,
  source: "DART_ANALYSIS",
  sourceNote: "2024 사업보고서 주요거래처",
  verifiedAt: datetime("2026-01-15T10:00:00"),
  verifiedBy: "admin",
  createdAt: datetime("2026-01-15T10:00:00"),
  updatedAt: datetime("2026-02-06T15:30:00")
}]->(supplier)
```

#### 4.6.4 Person 예시

```cypher
// Person 노드 생성 (대표이사 + 주주)
CREATE (p:Person:Executive:Shareholder:CEO {
  id: "PER_0001",
  name: "곽노정",
  nameEn: "Kwak Noh-Jung",
  birthYear: 1963,

  personType: ["CEO", "EXECUTIVE", "SHAREHOLDER", "BOARD_MEMBER"],

  currentPosition: "대표이사",
  currentCompanyId: "COM_SKHYNIX",
  currentCompanyName: "SK하이닉스",

  riskScore: 15,
  riskLevel: "PASS",
  riskFactors: [],
  hasNegativeNews: false,
  negativeNewsCount: 0,

  totalCompanies: 2,
  totalPositions: 5,
  yearsOfExperience: 35,

  source: "DART",
  sourceId: "00126380",
  fetchedAt: datetime("2026-02-01T10:00:00"),
  confidence: 0.95,
  isVerified: true,

  createdAt: datetime("2026-01-01T00:00:00"),
  updatedAt: datetime("2026-02-01T10:00:00")
})

// Position 노드 생성
CREATE (pos:Position {
  id: "POS_0001",
  title: "대표이사",
  titleEn: "CEO",
  department: "경영총괄",
  rank: "등기임원",

  positionType: "EXECUTIVE",
  isRegistered: true,
  isFullTime: true,

  startDate: date("2022-03-25"),
  endDate: null,
  tenure: 47,
  isCurrent: true,

  appointmentType: "NEW",
  terminationType: null,

  source: "DART",
  fetchedAt: datetime("2026-02-01T10:00:00"),
  confidence: 0.95,

  createdAt: datetime("2022-03-25T00:00:00"),
  updatedAt: datetime("2026-02-01T10:00:00")
})

// Shareholding 노드 생성
CREATE (sh:Shareholding {
  id: "SH_0001",
  sharesOwned: 125000,
  sharesTotal: 728002365,
  ownershipPercent: 0.017,
  ownershipRank: 15,

  shareType: "COMMON",
  holderType: "INDIVIDUAL",

  reportDate: date("2024-12-31"),

  source: "DART",
  sourceId: "elestock_2024",
  reportType: "elestock",
  fetchedAt: datetime("2026-02-01T10:00:00"),
  confidence: 0.95,

  createdAt: datetime("2026-02-01T10:00:00"),
  updatedAt: datetime("2026-02-01T10:00:00")
})

// Person → Company 관계 (WORKS_AT)
MATCH (p:Person {id: "PER_0001"}), (c:Company {id: "COM_SKHYNIX"})
CREATE (p)-[:WORKS_AT {
  positionId: "POS_0001",
  position: "대표이사",
  department: "경영총괄",
  role: "CEO",
  isExecutive: true,
  isRegistered: true,
  isCurrent: true,
  startDate: date("2022-03-25"),
  endDate: null,
  tenure: 47,
  source: "DART",
  fetchedAt: datetime("2026-02-01T10:00:00"),
  createdAt: datetime("2022-03-25T00:00:00"),
  updatedAt: datetime("2026-02-01T10:00:00")
}]->(c)

// Person → Company 관계 (OWNS_SHARES)
MATCH (p:Person {id: "PER_0001"}), (c:Company {id: "COM_SKHYNIX"})
CREATE (p)-[:OWNS_SHARES {
  shareholdingId: "SH_0001",
  sharesOwned: 125000,
  ownershipPercent: 0.017,
  ownershipRank: 15,
  holderType: "EXECUTIVE",
  isMajorShareholder: false,
  isControlling: false,
  reportDate: date("2024-12-31"),
  source: "DART",
  fetchedAt: datetime("2026-02-01T10:00:00"),
  createdAt: datetime("2026-02-01T10:00:00"),
  updatedAt: datetime("2026-02-01T10:00:00")
}]->(c)

// Person → Company 관계 (MANAGES)
MATCH (p:Person {id: "PER_0001"}), (c:Company {id: "COM_SKHYNIX"})
CREATE (p)-[:MANAGES {
  managementRole: "CEO",
  responsibility: "전체 경영",
  startDate: date("2022-03-25"),
  endDate: null,
  isCurrent: true,
  source: "DART",
  createdAt: datetime("2022-03-25T00:00:00")
}]->(c)

// Person → Person 관계 (특수관계인)
MATCH (p1:Person {id: "PER_0001"}), (p2:Person {id: "PER_0002"})
CREATE (p1)-[:RELATED_TO {
  relationType: "FAMILY",
  relationDetail: "배우자",
  familyRelation: "SPOUSE",
  source: "DART",
  sourceNote: "주주명부 특수관계인",
  createdAt: datetime("2026-02-01T10:00:00")
}]->(p2)
```

---

## 5. API Specification

### 5.1 Endpoint Summary

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/api/v3/status/summary` | Status별 기업 요약 | StatusSummary |
| GET | `/api/v3/companies/{id}/score` | 기업 점수 상세 (breakdown 포함) | ScoreBreakdown |
| GET | `/api/v3/companies/{id}/news` | 기업 관련 뉴스 (키워드 포함) | NewsList |
| GET | `/api/v3/data-quality` | 데이터 수집 현황 | DataQuality |
| POST | `/api/v3/refresh/{company_id}` | 특정 기업 데이터 갱신 | RefreshResult |

### 5.2 Detailed Specifications

#### GET /api/v3/status/summary

**Response (200 OK):**
```json
{
  "summary": {
    "PASS": {
      "count": 5,
      "companies": [
        {
          "id": "COM_HYUNDAI",
          "name": "현대자동차",
          "score": 38,
          "lastUpdated": "2026-02-06T15:30:00Z"
        }
      ]
    },
    "WARNING": {
      "count": 2,
      "companies": [...]
    },
    "FAIL": {
      "count": 1,
      "companies": [...]
    }
  },
  "totalCompanies": 8,
  "lastCalculated": "2026-02-06T15:30:00Z"
}
```

#### GET /api/v3/companies/{id}/score

**Response (200 OK):**
```json
{
  "companyId": "COM_SKHYNIX",
  "companyName": "SK하이닉스",
  "totalScore": 72,
  "status": "FAIL",
  "directScore": 65,
  "propagatedScore": 7,
  "directBreakdown": [
    {
      "category": "LEGAL",
      "categoryName": "법률위험",
      "score": 82,
      "weight": 0.15,
      "weightedScore": 12.3,
      "factors": [
        {"keyword": "횡령", "score": 50, "source": "NEWS_0001"},
        {"keyword": "소송", "score": 25, "source": "DISC_0001"}
      ]
    }
  ],
  "propagatedBreakdown": [
    {
      "supplier": "한미반도체",
      "tier": 1,
      "supplierRisk": 65,
      "dependency": 0.25,
      "tierRate": 0.8,
      "propagated": 13.0
    }
  ],
  "sources": [
    {"type": "DART", "count": 5, "reliability": 0.95},
    {"type": "NEWS", "count": 12, "reliability": 0.78}
  ],
  "calculatedAt": "2026-02-06T15:30:00Z"
}
```

#### GET /api/v3/data-quality

**Response (200 OK):**
```json
{
  "dart": {
    "collectedToday": 24,
    "riskMatched": 8,
    "successRate": 1.0,
    "lastFetch": "2026-02-06T15:20:00Z"
  },
  "news": {
    "collectedToday": 156,
    "riskMatched": 42,
    "duplicatesRemoved": 28,
    "avgConfidence": 0.72,
    "lastFetch": "2026-02-06T15:25:00Z"
  },
  "keywordStats": {
    "LEGAL": 12,
    "CREDIT": 5,
    "AUDIT": 3,
    "ESG": 8
  },
  "scoreChanges": {
    "updated": 3,
    "statusChanged": 1,
    "alertsSent": 2
  }
}
```

---

## 6. UI Components

### 6.1 Component Structure

```
components/risk/
├── RiskStatusView.tsx          # Status 중심 대시보드
├── RiskScoreBreakdown.tsx      # 점수 상세 breakdown
├── KeywordHighlight.tsx        # 키워드 하이라이트
├── DataQualityView.tsx         # 데이터 품질 대시보드
├── SourceBadge.tsx             # 출처 표시 뱃지
└── StatusCard.tsx              # 각 Status 그룹 카드
```

### 6.2 RiskStatusView.tsx

```tsx
interface StatusGroup {
  status: 'PASS' | 'WARNING' | 'FAIL';
  companies: CompanySummary[];
  count: number;
}

interface RiskStatusViewProps {
  onCompanyClick: (companyId: string) => void;
}

// 렌더링:
// - 3개 Status 그룹 (FAIL > WARNING > PASS 순서)
// - 각 그룹 내 기업 카드
// - 점수, 출처, 키워드 표시
```

### 6.3 RiskScoreBreakdown.tsx

```tsx
interface BreakdownProps {
  companyId: string;
  breakdown: ScoreBreakdown;
}

// 렌더링:
// - 직접 리스크 테이블 (카테고리별)
// - 전이 리스크 테이블 (공급사별)
// - 출처 상세
// - 매칭 키워드 목록
```

### 6.4 KeywordHighlight.tsx

```tsx
interface KeywordHighlightProps {
  text: string;
  keywords: string[];
}

// 렌더링:
// - 텍스트 내 키워드 강조 (빨간색/주황색 배경)
// - 키워드 호버 시 점수 표시
```

---

## 7. Implementation Order

### Phase 1: 키워드 엔진 & 스키마 (Week 1)

```
1. [ ] keywords.py 생성
       - DART_RISK_KEYWORDS, NEWS_RISK_KEYWORDS, KIND_RISK_KEYWORDS 정의
       - match_keywords(), classify_category() 구현

2. [ ] score_engine.py 생성
       - calc_decay(), calc_confidence() 구현
       - calculate_raw_score(), calculate_decayed_score() 구현

3. [ ] load_graph_v3.py 생성 (Status 노드)
       - Status 3개 노드 생성
       - 기존 Company 노드 스키마 마이그레이션

4. [ ] 테스트
       - test_keywords.py
       - test_score_engine.py
```

### Phase 2: 데이터 수집기 (Week 1-2)

```
5. [ ] dart_collector_v2.py 생성
       - DART API 6개 엔드포인트 지원
       - keywords.py 연동
       - validator.py 연동

6. [ ] news_collector_v2.py 생성
       - Google/Naver RSS 수집
       - 중복 제거 로직
       - keywords.py 연동

7. [ ] validator.py 생성
       - 필수 필드 검증
       - 범위 검증
       - 중복 검사

8. [ ] 테스트
       - test_dart_collector.py
       - test_news_collector.py
```

### Phase 3: API & 점수 계산 (Week 2)

```
9. [ ] risk_calculator_v3.py 생성
        - calculate_direct_risk()
        - calculate_propagated_risk()
        - calculate_total_risk() with breakdown

10. [ ] api.py 확장
        - GET /api/v3/status/summary
        - GET /api/v3/companies/{id}/score
        - GET /api/v3/data-quality

11. [ ] 테스트
        - test_risk_calculator.py
        - test_api_v3.py
```

### Phase 4: 검증 & 스케줄러 (Week 2-3)

```
12. [ ] validator.py 확장
        - check_duplicate() Neo4j 연동
        - normalize() 구현

13. [ ] scheduler.py 생성 (P1)
        - 실시간/일일/주간 스케줄

14. [ ] alert_sender.py 생성 (P2)
        - 임계치 초과 알림
```

### Phase 5: UI (Week 3)

```
15. [ ] RiskStatusView.tsx 생성
        - Status 3단계 그룹 뷰

16. [ ] RiskScoreBreakdown.tsx 생성
        - 카테고리별 breakdown

17. [ ] KeywordHighlight.tsx 생성 (P1)
        - 키워드 강조

18. [ ] DataQualityView.tsx 생성 (P2)
        - 수집 현황 대시보드
```

---

## 8. Error Handling

### 8.1 Error Code Definition

| Code | Message | Cause | Handling |
|------|---------|-------|----------|
| 400 | Invalid parameters | 잘못된 요청 파라미터 | 파라미터 검증 메시지 |
| 404 | Company not found | 존재하지 않는 기업 ID | 404 페이지 |
| 500 | Score calculation failed | 점수 계산 오류 | 로깅 + 재시도 |
| 503 | DART API unavailable | DART API 장애 | 캐시 데이터 사용 |

### 8.2 Error Response Format

```json
{
  "error": {
    "code": "SCORE_CALCULATION_FAILED",
    "message": "점수 계산에 실패했습니다",
    "details": {
      "companyId": "COM_SKHYNIX",
      "reason": "Missing RiskCategory data"
    }
  }
}
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Module | Test File | Coverage Target |
|--------|-----------|-----------------|
| keywords.py | test_keywords.py | 90% |
| score_engine.py | test_score_engine.py | 95% |
| risk_calculator_v3.py | test_risk_calculator.py | 90% |
| validator.py | test_validator.py | 85% |

### 9.2 Integration Tests

| Test | Description | Dependencies |
|------|-------------|--------------|
| test_dart_integration | DART API 수집 → Neo4j 저장 | Neo4j, DART API |
| test_score_pipeline | 수집 → 분석 → 점수계산 → 저장 | All modules |
| test_api_v3 | API 엔드포인트 테스트 | FastAPI, Neo4j |

### 9.3 Key Test Cases

- [ ] 키워드 매칭: "횡령" 포함 제목 → 50점 매칭
- [ ] 시간 감쇠: 30일 전 뉴스 → 37% 감쇠
- [ ] Status 결정: 72점 → FAIL
- [ ] 중복 제거: 동일 URL 뉴스 → 1건만 저장
- [ ] API 응답: breakdown 포함 여부

---

## 10. Security Considerations

- [ ] DART API 키 환경변수 관리 (`.env.local`)
- [ ] Neo4j 비밀번호 환경변수 관리
- [ ] API Rate Limiting 적용
- [ ] Input Validation (XSS 방지)
- [ ] CORS 설정 (프로덕션에서는 특정 도메인만 허용)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-06 | Initial draft based on Plan v3.0 | AI Assistant |
