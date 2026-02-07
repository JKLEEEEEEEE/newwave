# Risk System V4 - 상세 설계서

> **Version**: 4.0
> **Created**: 2026-02-06
> **Status**: Design
> **Plan Reference**: `docs/01-plan/features/risk-system-v4.plan.md`

---

## 1. 개요

### 1.1 설계 목표
현업이 보자마자 유용하고 이해 가능한 리스크 모니터링 시스템 구축

### 1.2 핵심 요구사항
1. **드릴다운 분석**: 기업 → 카테고리 → 엔티티 → 이슈 → 증거
2. **완전한 데이터 연결**: 모든 엔티티에 관련 뉴스/이슈 연결
3. **투명한 점수**: 점수 근거 즉시 확인 가능
4. **현대적 UI/UX**: Figma 수준 디자인

---

## 2. Neo4j 그래프 스키마 (Phase 1)

### 2.1 노드 정의

#### 2.1.1 RiskCategory 노드 (신규)

```cypher
(:RiskCategory {
  // === 식별자 ===
  id: String,                    // "RC_{companyId}_{code}" (PK)
  companyId: String,             // "SK하이닉스" (FK)

  // === 카테고리 정보 ===
  code: String,                  // "LEGAL" | "CREDIT" | "GOVERNANCE" | "OPERATIONAL" | "AUDIT" | "ESG" | "SUPPLY" | "OTHER"
  name: String,                  // "법률위험", "신용위험" 등
  icon: String,                  // "⚖️", "💳" 등

  // === 점수 ===
  score: Integer,                // 0-100
  weight: Float,                 // 가중치 (0.0-1.0)
  weightedScore: Float,          // score × weight

  // === 구성요소 카운트 ===
  eventCount: Integer,           // 관련 이벤트 수
  personCount: Integer,          // 관련 인물 수
  newsCount: Integer,            // 관련 뉴스 수
  disclosureCount: Integer,      // 관련 공시 수

  // === 트렌드 ===
  trend: String,                 // "UP" | "DOWN" | "STABLE"
  previousScore: Integer,

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

**카테고리 코드 및 가중치:**

| Code | Name | Icon | Weight |
|------|------|------|--------|
| LEGAL | 법률위험 | ⚖️ | 0.15 |
| CREDIT | 신용위험 | 💳 | 0.20 |
| GOVERNANCE | 지배구조 | 👥 | 0.15 |
| OPERATIONAL | 운영위험 | ⚙️ | 0.10 |
| AUDIT | 감사위험 | 📋 | 0.15 |
| ESG | ESG위험 | 🌱 | 0.10 |
| SUPPLY | 공급망위험 | 🔗 | 0.10 |
| OTHER | 기타위험 | 📊 | 0.05 |

#### 2.1.2 RiskEvent 노드 (신규)

```cypher
(:RiskEvent {
  // === 식별자 ===
  id: String,                    // "EVT_{hash}" (PK)

  // === 이벤트 정보 ===
  title: String,                 // "ITC 특허소송 제기"
  description: String,           // 상세 설명
  category: String,              // "LEGAL" (RiskCategory.code)

  // === 점수 ===
  score: Integer,                // 0-100 (이벤트 자체 점수)
  severity: String,              // "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"

  // === 관련 엔티티 ===
  companyId: String,             // 관련 기업
  personIds: [String],           // 관련 인물 IDs

  // === 증거 ===
  newsIds: [String],             // 관련 뉴스 IDs
  disclosureIds: [String],       // 관련 공시 IDs
  newsCount: Integer,
  disclosureCount: Integer,

  // === 키워드 ===
  matchedKeywords: [String],     // ["특허", "소송", "ITC"]
  primaryKeyword: String,        // "소송"

  // === 시간 ===
  firstDetectedAt: DateTime,     // 최초 탐지 시점
  lastUpdatedAt: DateTime,
  isActive: Boolean,             // 활성 이벤트 여부

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

#### 2.1.3 Person 노드 (확장)

```cypher
(:Person {
  // === 기존 필드 ===
  id: String,
  name: String,
  type: String,                  // "EXECUTIVE" | "SHAREHOLDER" | "BOTH"

  // === 신규 필드 ===
  position: String,              // "대표이사", "사외이사" 등
  tier: Integer,                 // 1: C-Level, 2: 임원, 3: 일반

  // === 리스크 점수 ===
  riskScore: Integer,            // 인물 자체 리스크 점수 (0-100)
  riskLevel: String,             // "PASS" | "WARNING" | "FAIL"

  // === 관련 카운트 ===
  relatedNewsCount: Integer,     // 관련 뉴스 수
  relatedEventCount: Integer,    // 관련 이벤트 수

  // === 타임스탬프 ===
  createdAt: DateTime,
  updatedAt: DateTime
})
```

### 2.2 관계 정의

#### 2.2.1 새로운 관계 타입

```cypher
// Company → RiskCategory
(c:Company)-[:HAS_CATEGORY {
  createdAt: DateTime
}]->(rc:RiskCategory)

// RiskCategory → RiskEvent
(rc:RiskCategory)-[:HAS_EVENT {
  contribution: Float,           // 이 이벤트가 카테고리 점수에 기여하는 비율
  createdAt: DateTime
}]->(e:RiskEvent)

// RiskEvent → News (증거)
(e:RiskEvent)-[:EVIDENCED_BY {
  relevance: Float,              // 관련도 0.0-1.0
  extractedAt: DateTime
}]->(n:News)

// RiskEvent → Disclosure (증거)
(e:RiskEvent)-[:EVIDENCED_BY {
  relevance: Float,
  extractedAt: DateTime
}]->(d:Disclosure)

// Person → RiskEvent (연루)
(p:Person)-[:INVOLVED_IN {
  role: String,                  // "주체" | "관련자"
  detectedAt: DateTime
}]->(e:RiskEvent)

// Person → News (언급)
(p:Person)-[:MENTIONED_IN {
  sentiment: String,             // "NEGATIVE" | "NEUTRAL" | "POSITIVE"
  context: String,               // 언급 맥락
  detectedAt: DateTime
}]->(n:News)
```

### 2.3 스키마 다이어그램

```
                    ┌──────────────────┐
                    │     Company      │
                    │   SK하이닉스      │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │ HAS_CATEGORY   │ HAS_CATEGORY   │
            ▼                ▼                ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │RiskCategory │  │RiskCategory │  │RiskCategory │
     │ LEGAL (25)  │  │GOVERNANCE(15)│ │ CREDIT (0)  │
     └──────┬──────┘  └──────┬──────┘  └─────────────┘
            │                │
   HAS_EVENT│       HAS_EVENT│
            ▼                │
     ┌─────────────┐         │
     │ RiskEvent   │         │
     │ITC 특허소송 │         │
     │  Score: 25  │         │
     └──────┬──────┘         │
            │                │
  EVIDENCED_BY               │INVOLVED_IN
            │                │
            ▼                ▼
     ┌─────────────┐  ┌─────────────┐
     │    News     │  │   Person    │
     │"특허소송..."│  │  홍길동     │
     │ rawScore:25 │  │ riskScore:15│
     └─────────────┘  └──────┬──────┘
                             │
                    MENTIONED_IN
                             │
                             ▼
                      ┌─────────────┐
                      │    News     │
                      │"횡령혐의..."│
                      └─────────────┘
```

### 2.4 인덱스 및 제약조건

```cypher
// 고유 제약조건
CREATE CONSTRAINT risk_category_id_unique FOR (rc:RiskCategory) REQUIRE rc.id IS UNIQUE;
CREATE CONSTRAINT risk_event_id_unique FOR (e:RiskEvent) REQUIRE e.id IS UNIQUE;

// 인덱스
CREATE INDEX risk_category_company_idx FOR (rc:RiskCategory) ON (rc.companyId);
CREATE INDEX risk_category_code_idx FOR (rc:RiskCategory) ON (rc.code);
CREATE INDEX risk_event_category_idx FOR (e:RiskEvent) ON (e.category);
CREATE INDEX risk_event_company_idx FOR (e:RiskEvent) ON (e.companyId);
CREATE INDEX person_risk_score_idx FOR (p:Person) ON (p.riskScore);
```

---

## 3. API 설계 (Phase 2)

### 3.1 API 엔드포인트 목록

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v4/deals` | 딜 목록 (카테고리 요약 포함) |
| GET | `/api/v4/deals/{id}` | 딜 상세 (전체 드릴다운 데이터) |
| GET | `/api/v4/deals/{id}/categories` | 카테고리별 breakdown |
| GET | `/api/v4/deals/{id}/categories/{code}` | 특정 카테고리 상세 |
| GET | `/api/v4/deals/{id}/events` | 이벤트 목록 |
| GET | `/api/v4/deals/{id}/persons` | 관련 인물 목록 |
| GET | `/api/v4/persons/{id}` | 인물 상세 (관련 뉴스/이벤트) |
| GET | `/api/v4/events/{id}` | 이벤트 상세 (증거 목록) |
| GET | `/api/v4/deals/{id}/evidence` | 전체 증거 목록 |

### 3.2 API 응답 스키마

#### 3.2.1 GET `/api/v4/deals/{id}` - 딜 상세

```typescript
interface DealDetailResponse {
  schemaVersion: "v4";
  generatedAt: string;

  deal: {
    id: string;
    name: string;
    sector: string;

    // 점수
    score: number;                    // 총점 (0-100)
    riskLevel: "PASS" | "WARNING" | "FAIL";
    breakdown: {
      direct: number;                 // 직접 리스크
      propagated: number;             // 전이 리스크
    };
    trend: "UP" | "DOWN" | "STABLE";

    // 카테고리 요약
    categories: CategorySummary[];

    // 주요 이벤트 (Top 5)
    topEvents: EventSummary[];

    // 주요 인물 (Top 5)
    topPersons: PersonSummary[];

    // 증거 요약
    evidence: {
      totalNews: number;
      totalDisclosures: number;
      topFactors: string[];           // ["ITC 특허소송", "임원 리스크"]
    };

    // 타임스탬프
    lastUpdated: string;
  };
}

interface CategorySummary {
  code: string;                       // "LEGAL"
  name: string;                       // "법률위험"
  icon: string;                       // "⚖️"
  score: number;                      // 25
  weight: number;                     // 0.15
  weightedScore: number;              // 3.75
  eventCount: number;
  personCount: number;
  trend: "UP" | "DOWN" | "STABLE";
}

interface EventSummary {
  id: string;
  title: string;
  category: string;
  score: number;
  severity: string;
  newsCount: number;
  disclosureCount: number;
  firstDetectedAt: string;
}

interface PersonSummary {
  id: string;
  name: string;
  position: string;
  type: "EXECUTIVE" | "SHAREHOLDER" | "BOTH";
  riskScore: number;
  relatedNewsCount: number;
  relatedEventCount: number;
}
```

#### 3.2.2 GET `/api/v4/deals/{id}/categories/{code}` - 카테고리 상세

```typescript
interface CategoryDetailResponse {
  category: {
    code: string;
    name: string;
    icon: string;
    score: number;
    weight: number;

    // 관련 이벤트 전체
    events: EventDetail[];

    // 관련 인물 전체
    persons: PersonDetail[];

    // 관련 뉴스 전체
    news: NewsItem[];

    // 관련 공시 전체
    disclosures: DisclosureItem[];
  };
}

interface EventDetail {
  id: string;
  title: string;
  description: string;
  score: number;
  severity: string;
  matchedKeywords: string[];

  // 이 이벤트의 증거
  evidence: {
    news: NewsItem[];
    disclosures: DisclosureItem[];
  };

  // 관련 인물
  involvedPersons: PersonSummary[];

  firstDetectedAt: string;
  isActive: boolean;
}

interface PersonDetail {
  id: string;
  name: string;
  position: string;
  type: string;
  tier: number;
  riskScore: number;
  riskLevel: string;

  // 관련 뉴스
  relatedNews: NewsItem[];

  // 연루된 이벤트
  involvedEvents: EventSummary[];
}

interface NewsItem {
  id: string;
  title: string;
  source: string;
  publishedAt: string;
  rawScore: number;
  sentiment: string;
  url: string;
}

interface DisclosureItem {
  id: string;
  title: string;
  filingDate: string;
  rawScore: number;
  category: string;
  url: string;
}
```

#### 3.2.3 GET `/api/v4/persons/{id}` - 인물 상세

```typescript
interface PersonDetailResponse {
  person: {
    id: string;
    name: string;
    position: string;
    type: "EXECUTIVE" | "SHAREHOLDER" | "BOTH";
    tier: number;

    // 리스크
    riskScore: number;
    riskLevel: string;
    riskFactors: string[];            // ["횡령 혐의", "분식회계 관련"]

    // 소속 기업
    companies: {
      id: string;
      name: string;
      relationship: string;           // "EXECUTIVE_OF" | "SHAREHOLDER_OF"
      position?: string;              // 임원인 경우
      sharePercent?: number;          // 주주인 경우
    }[];

    // 연루 이벤트
    involvedEvents: EventSummary[];

    // 관련 뉴스 (전체)
    relatedNews: NewsItem[];

    // 타임라인
    timeline: TimelineItem[];
  };
}

interface TimelineItem {
  date: string;
  type: "NEWS" | "EVENT" | "DISCLOSURE";
  title: string;
  score: number;
  id: string;
}
```

---

## 4. 점수 계산 로직 (Phase 1)

### 4.1 점수 계산 파이프라인

```
┌─────────────────────────────────────────────────────────────────────┐
│                        점수 계산 파이프라인                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 데이터 수집                                                      │
│     News/Disclosure → 키워드 매칭 → rawScore 계산                    │
│                                                                     │
│  2. 이벤트 그룹핑                                                    │
│     유사 뉴스/공시 → RiskEvent 생성 → 점수 집계                      │
│                                                                     │
│  3. 인물 연결                                                        │
│     뉴스 본문에서 인물명 추출 → Person-News MENTIONED_IN 생성        │
│     이벤트와 인물 연결 → Person-Event INVOLVED_IN 생성               │
│                                                                     │
│  4. 카테고리 집계                                                    │
│     이벤트별 카테고리 분류 → RiskCategory 점수 계산                   │
│                                                                     │
│  5. 기업 총점 계산                                                   │
│     Σ(카테고리 가중 점수) + 전이 리스크 = 총점                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 이벤트 생성 로직

```python
def create_risk_events(company_id: str):
    """
    뉴스/공시에서 리스크 이벤트 추출 및 생성
    """
    # 1. 키워드 매칭된 뉴스/공시 조회
    query = """
    MATCH (n:News)-[:MENTIONS]->(c:Company {id: $companyId})
    WHERE n.rawScore > 0
    RETURN n.id, n.title, n.matchedKeywords, n.rawScore, n.publishedAt
    """

    # 2. 유사 뉴스 클러스터링 (제목 유사도 기반)
    clusters = cluster_similar_news(news_list, threshold=0.7)

    # 3. 클러스터별 RiskEvent 생성
    for cluster in clusters:
        event = RiskEvent(
            id=generate_event_id(cluster),
            title=extract_event_title(cluster),
            category=determine_category(cluster),
            score=calculate_event_score(cluster),
            newsIds=[n.id for n in cluster],
            matchedKeywords=merge_keywords(cluster)
        )
        save_event(event)
```

### 4.3 인물-뉴스 연결 로직

```python
def link_person_to_news(company_id: str):
    """
    뉴스에서 인물 언급 탐지 및 관계 생성
    """
    # 1. 기업의 임원/주주 목록 조회
    persons = get_company_persons(company_id)

    # 2. 뉴스 본문에서 인물명 검색
    for news in get_company_news(company_id):
        for person in persons:
            if person.name in news.title or person.name in news.content:
                # 3. MENTIONED_IN 관계 생성
                create_mentioned_in_relation(
                    person_id=person.id,
                    news_id=news.id,
                    sentiment=analyze_sentiment(news, person),
                    context=extract_context(news, person)
                )

                # 4. Person 리스크 점수 업데이트
                update_person_risk_score(person.id)
```

### 4.4 카테고리 점수 계산

```python
def calculate_category_score(company_id: str, category_code: str) -> int:
    """
    카테고리별 점수 계산
    """
    # 1. 해당 카테고리의 이벤트 조회
    events = get_category_events(company_id, category_code)

    # 2. 이벤트 점수 합산 (시간 감쇠 적용)
    total_score = 0
    for event in events:
        decayed_score = apply_time_decay(event.score, event.firstDetectedAt)
        total_score += decayed_score

    # 3. 정규화 (0-100)
    normalized_score = min(100, total_score)

    return normalized_score
```

### 4.5 기업 총점 계산

```python
def calculate_company_score(company_id: str) -> dict:
    """
    기업 총 리스크 점수 계산
    """
    categories = get_company_categories(company_id)

    # 1. 직접 리스크 (카테고리 가중 합산)
    direct_score = sum(
        cat.score * cat.weight
        for cat in categories
    )

    # 2. 전이 리스크 (임원/주주 리스크)
    propagated_score = calculate_propagated_risk(company_id)

    # 3. 총점
    total_score = min(100, direct_score + propagated_score)

    # 4. 상태 결정
    risk_level = determine_status(total_score)

    return {
        "direct": round(direct_score),
        "propagated": round(propagated_score),
        "total": round(total_score),
        "riskLevel": risk_level
    }
```

---

## 5. UI/UX 설계 (Phase 3)

### 5.1 컴포넌트 구조

```
src/components/risk/v4/
├── RiskDashboard.tsx              # 메인 대시보드
├── CategoryBreakdown/
│   ├── CategoryCard.tsx           # 카테고리 카드
│   ├── CategoryDetail.tsx         # 카테고리 상세 패널
│   └── CategoryGrid.tsx           # 카테고리 그리드
├── EventList/
│   ├── EventCard.tsx              # 이벤트 카드
│   ├── EventDetail.tsx            # 이벤트 상세 모달
│   └── EventTimeline.tsx          # 이벤트 타임라인
├── PersonList/
│   ├── PersonCard.tsx             # 인물 카드
│   ├── PersonDetail.tsx           # 인물 상세 모달
│   └── PersonRiskBadge.tsx        # 인물 리스크 뱃지
├── Evidence/
│   ├── NewsCard.tsx               # 뉴스 카드
│   ├── DisclosureCard.tsx         # 공시 카드
│   └── EvidenceList.tsx           # 증거 목록
├── DrillDown/
│   ├── Breadcrumb.tsx             # 드릴다운 경로
│   ├── DrillDownPanel.tsx         # 드릴다운 패널
│   └── BackButton.tsx             # 뒤로가기 버튼
└── shared/
    ├── RiskScoreBadge.tsx         # 점수 뱃지
    ├── TrendIndicator.tsx         # 트렌드 표시
    └── LoadingSkeleton.tsx        # 로딩 스켈레톤
```

### 5.2 화면 레이아웃

#### 5.2.1 메인 대시보드

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🏢 SK하이닉스 리스크 대시보드                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌─────────────────┐  ┌──────────────────────────────────────────────┐  │
│ │   총 리스크     │  │              카테고리별 리스크                 │  │
│ │                 │  │                                              │  │
│ │      40        │  │  ⚖️ 법률    💳 신용    👥 지배    🌱 ESG     │  │
│ │     점        │  │   25        0        15        0            │  │
│ │   WARNING     │  │   ▲         -        ▼         -            │  │
│ │                 │  │                                              │  │
│ │ 직접: 35       │  │  ⚙️ 운영    📋 감사    🔗 공급    📊 기타     │  │
│ │ 전이: 5        │  │   0         0         0         0            │  │
│ └─────────────────┘  └──────────────────────────────────────────────┘  │
│                                                                         │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────┐ │
│ │      📌 주요 리스크 이벤트       │  │      👤 관련 인물              │ │
│ │                                 │  │                               │ │
│ │  🔴 ITC 특허소송 제기           │  │  ⚠️ 홍길동 (대표이사)          │ │
│ │     Score: 25 | 뉴스 3건        │  │     Score: 15 | 뉴스 2건       │ │
│ │     [상세보기]                  │  │     [상세보기]                 │ │
│ │                                 │  │                               │ │
│ │  🟡 공정위 조사                 │  │  ✅ 김철수 (CFO)              │ │
│ │     Score: 10 | 뉴스 2건        │  │     Score: 0 | 뉴스 0건        │ │
│ │     [상세보기]                  │  │     [상세보기]                 │ │
│ └─────────────────────────────────┘  └───────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │                        📰 최근 증거 (뉴스/공시)                     │  │
│ │                                                                   │  │
│ │  2026-02-06  "SK하이닉스, ITC 특허소송에서..." (rawScore: 25)     │  │
│ │  2026-02-05  "반도체 업계 특허 분쟁 심화..." (rawScore: 15)       │  │
│ │  2026-02-04  [공시] 소송 등의 제기 (rawScore: 20)                 │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 5.2.2 드릴다운 - 카테고리 상세

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🏢 SK하이닉스 > ⚖️ 법률위험                         [← 뒤로]           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐│
│ │  ⚖️ 법률위험                                           Score: 25    ││
│ │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                      ││
│ │  가중치: 15% | 가중점수: 3.75 | 이벤트 2건 | 인물 1명                ││
│ └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ ┌──────────────────────────────────┐  ┌────────────────────────────────┐│
│ │      📌 관련 이벤트               │  │      👤 관련 인물               ││
│ │                                  │  │                                ││
│ │  ┌────────────────────────────┐  │  │  ┌────────────────────────┐   ││
│ │  │ 🔴 ITC 특허소송 제기        │  │  │  │ 홍길동                 │   ││
│ │  │    Score: 25               │  │  │  │ 대표이사 | Score: 15   │   ││
│ │  │    뉴스 3건 | 공시 1건     │  │  │  │ 뉴스 2건 | 이벤트 1건  │   ││
│ │  │    [클릭하여 상세보기]      │  │  │  │ [클릭하여 상세보기]    │   ││
│ │  └────────────────────────────┘  │  │  └────────────────────────┘   ││
│ │                                  │  │                                ││
│ │  ┌────────────────────────────┐  │  │                                ││
│ │  │ 🟡 공정위 조사              │  │  │                                ││
│ │  │    Score: 10               │  │  │                                ││
│ │  │    뉴스 2건 | 공시 0건     │  │  │                                ││
│ │  └────────────────────────────┘  │  │                                ││
│ └──────────────────────────────────┘  └────────────────────────────────┘│
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │                         📰 관련 증거                               │  │
│ │                                                                   │  │
│ │  📰 뉴스                              📋 공시                     │  │
│ │  • "ITC, SK하이닉스 특허침해..."      • 소송 등의 제기            │  │
│ │  • "반도체 특허 분쟁 격화..."                                     │  │
│ │  • "SK하이닉스 vs 마이크론..."                                    │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 5.2.3 드릴다운 - 이벤트 상세 (모달)

```
┌─────────────────────────────────────────────────────────────────┐
│                    📌 ITC 특허소송 제기                    [✕]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Score: 25                   Severity: 🔴 HIGH                  │
│  카테고리: ⚖️ 법률위험        최초 탐지: 2026-02-04             │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━       │
│                                                                 │
│  📝 설명                                                        │
│  미국 국제무역위원회(ITC)가 SK하이닉스를 대상으로 특허침해      │
│  조사를 개시. 마이크론 테크놀로지의 제소에 따른 것으로...       │
│                                                                 │
│  🏷️ 매칭 키워드                                                 │
│  [소송] [특허] [ITC] [침해]                                     │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━       │
│                                                                 │
│  👤 관련 인물                                                   │
│  • 홍길동 (대표이사) - 역할: 관련자                             │
│                                                                 │
│  📰 관련 뉴스 (3건)                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ • "ITC, SK하이닉스 특허침해 조사 개시"                     │ │
│  │   한국경제 | 2026-02-04 | rawScore: 25 | [원문보기]        │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ • "반도체 특허 분쟁 격화...마이크론 vs SK하이닉스"         │ │
│  │   매일경제 | 2026-02-05 | rawScore: 20 | [원문보기]        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  📋 관련 공시 (1건)                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ • 소송 등의 제기                                           │ │
│  │   DART | 2026-02-04 | rawScore: 20 | [원문보기]            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 디자인 시스템

#### 5.3.1 색상 팔레트

```css
/* 리스크 레벨 색상 */
--risk-pass: #22C55E;           /* 초록 (PASS: 0-49) */
--risk-warning: #F59E0B;        /* 노랑 (WARNING: 50-74) */
--risk-fail: #EF4444;           /* 빨강 (FAIL: 75-100) */

/* 트렌드 색상 */
--trend-up: #EF4444;            /* 상승 (악화) */
--trend-down: #22C55E;          /* 하락 (개선) */
--trend-stable: #6B7280;        /* 안정 */

/* 배경 색상 */
--bg-primary: #FFFFFF;
--bg-secondary: #F9FAFB;
--bg-card: #FFFFFF;
--bg-hover: #F3F4F6;

/* 테두리 */
--border-default: #E5E7EB;
--border-focus: #3B82F6;

/* 텍스트 */
--text-primary: #111827;
--text-secondary: #6B7280;
--text-muted: #9CA3AF;
```

#### 5.3.2 타이포그래피

```css
/* 제목 */
--font-title: 'Pretendard', -apple-system, sans-serif;
--font-size-title: 24px;
--font-weight-title: 700;

/* 부제목 */
--font-size-subtitle: 18px;
--font-weight-subtitle: 600;

/* 본문 */
--font-size-body: 14px;
--font-weight-body: 400;

/* 라벨 */
--font-size-label: 12px;
--font-weight-label: 500;
```

#### 5.3.3 컴포넌트 스타일

```tsx
// RiskScoreBadge.tsx
interface RiskScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

// 점수에 따른 색상
const getScoreColor = (score: number) => {
  if (score < 50) return 'bg-green-100 text-green-800 border-green-200';
  if (score < 75) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
  return 'bg-red-100 text-red-800 border-red-200';
};

// TrendIndicator.tsx
const TrendIndicator = ({ trend }: { trend: 'UP' | 'DOWN' | 'STABLE' }) => {
  const config = {
    UP: { icon: '▲', color: 'text-red-500', label: '상승' },
    DOWN: { icon: '▼', color: 'text-green-500', label: '하락' },
    STABLE: { icon: '―', color: 'text-gray-500', label: '유지' },
  };
  // ...
};
```

---

## 6. 백엔드 구현 상세 (Phase 1)

### 6.1 파일 구조

```
risk_engine/
├── v4/
│   ├── __init__.py
│   ├── schemas.py               # Pydantic 스키마
│   ├── api.py                   # V4 API 라우터
│   ├── services/
│   │   ├── event_service.py     # 이벤트 관리
│   │   ├── category_service.py  # 카테고리 관리
│   │   ├── person_service.py    # 인물 관리
│   │   └── score_service.py     # 점수 계산
│   ├── repositories/
│   │   ├── event_repo.py        # 이벤트 Neo4j 쿼리
│   │   ├── category_repo.py     # 카테고리 Neo4j 쿼리
│   │   └── person_repo.py       # 인물 Neo4j 쿼리
│   └── pipelines/
│       ├── event_pipeline.py    # 이벤트 생성 파이프라인
│       ├── linking_pipeline.py  # 관계 연결 파이프라인
│       └── score_pipeline.py    # 점수 계산 파이프라인
```

### 6.2 핵심 서비스 구현

#### 6.2.1 EventService

```python
# risk_engine/v4/services/event_service.py

class EventService:
    def __init__(self, neo4j_client):
        self.client = neo4j_client
        self.repo = EventRepository(neo4j_client)

    def create_events_from_news(self, company_id: str) -> list[RiskEvent]:
        """
        뉴스에서 리스크 이벤트 추출 및 생성
        """
        # 1. 키워드 매칭된 뉴스 조회
        news_list = self.repo.get_risk_news(company_id)

        # 2. 유사 뉴스 클러스터링
        clusters = self._cluster_news(news_list)

        # 3. 클러스터별 이벤트 생성
        events = []
        for cluster in clusters:
            event = self._create_event_from_cluster(cluster, company_id)
            self.repo.save_event(event)
            events.append(event)

        return events

    def _cluster_news(self, news_list: list) -> list[list]:
        """제목 유사도 기반 클러스터링"""
        # TF-IDF + 코사인 유사도 사용
        # 임계값 0.6 이상이면 같은 클러스터
        pass

    def _create_event_from_cluster(self, cluster: list, company_id: str) -> RiskEvent:
        """클러스터에서 이벤트 생성"""
        return RiskEvent(
            id=self._generate_event_id(cluster),
            title=self._extract_title(cluster),
            category=self._determine_category(cluster),
            score=self._calculate_score(cluster),
            companyId=company_id,
            newsIds=[n.id for n in cluster],
            matchedKeywords=self._merge_keywords(cluster),
            firstDetectedAt=min(n.publishedAt for n in cluster)
        )
```

#### 6.2.2 PersonLinkingService

```python
# risk_engine/v4/services/person_service.py

class PersonLinkingService:
    def __init__(self, neo4j_client):
        self.client = neo4j_client
        self.repo = PersonRepository(neo4j_client)

    def link_persons_to_news(self, company_id: str) -> int:
        """
        인물-뉴스 MENTIONED_IN 관계 생성
        """
        # 1. 기업의 임원/주주 목록
        persons = self.repo.get_company_persons(company_id)

        # 2. 기업 관련 뉴스 목록
        news_list = self.repo.get_company_news(company_id)

        # 3. 매칭 및 관계 생성
        link_count = 0
        for news in news_list:
            for person in persons:
                if self._is_mentioned(person.name, news.title):
                    self.repo.create_mentioned_in(
                        person_id=person.id,
                        news_id=news.id,
                        sentiment=self._analyze_sentiment(news, person)
                    )
                    link_count += 1

        # 4. 인물 리스크 점수 업데이트
        self._update_person_scores(company_id)

        return link_count

    def _is_mentioned(self, name: str, text: str) -> bool:
        """인물명이 텍스트에 언급되었는지 확인"""
        # 성+이름, 이름만, 직책+이름 등 다양한 패턴 체크
        patterns = [
            name,                           # 홍길동
            name[1:],                       # 길동
            f"{name[0]}씨",                 # 홍씨
        ]
        return any(p in text for p in patterns)
```

---

## 7. 테스트 전략 (Phase 4)

### 7.1 테스트 범위

| 레벨 | 대상 | 도구 |
|------|------|------|
| Unit | 점수 계산, 클러스터링 | pytest |
| Integration | Neo4j 쿼리, 파이프라인 | pytest + Neo4j testcontainers |
| API | V4 엔드포인트 | pytest + httpx |
| E2E | 전체 드릴다운 플로우 | Playwright |
| UI | 컴포넌트 렌더링 | Vitest + Testing Library |

### 7.2 핵심 테스트 시나리오

```python
# tests/e2e/test_drilldown_flow.py

class TestDrilldownFlow:
    """
    드릴다운 E2E 테스트
    기업 → 카테고리 → 이벤트 → 증거
    """

    def test_company_to_category_drilldown(self):
        """기업에서 카테고리 드릴다운"""
        # 1. 딜 상세 조회
        response = client.get("/api/v4/deals/SK하이닉스")
        assert response.status_code == 200

        deal = response.json()["deal"]
        assert len(deal["categories"]) > 0

        # 2. 카테고리 상세 조회
        category = deal["categories"][0]
        response = client.get(f"/api/v4/deals/SK하이닉스/categories/{category['code']}")
        assert response.status_code == 200

        category_detail = response.json()["category"]
        assert category_detail["events"] is not None

    def test_event_to_evidence_drilldown(self):
        """이벤트에서 증거 드릴다운"""
        # 1. 이벤트 조회
        response = client.get("/api/v4/deals/SK하이닉스/events")
        events = response.json()["events"]

        if len(events) > 0:
            event_id = events[0]["id"]

            # 2. 이벤트 상세 조회
            response = client.get(f"/api/v4/events/{event_id}")
            assert response.status_code == 200

            event = response.json()["event"]
            assert event["evidence"]["news"] is not None
```

### 7.3 API-UI 일치성 검증

```typescript
// tests/e2e/api-ui-consistency.spec.ts

test('API 응답과 UI 표시 일치 검증', async ({ page }) => {
  // 1. API 직접 호출
  const apiResponse = await fetch('/api/v4/deals/SK하이닉스');
  const apiData = await apiResponse.json();

  // 2. UI 페이지 로드
  await page.goto('/risk/SK하이닉스');

  // 3. 점수 일치 확인
  const uiScore = await page.locator('[data-testid="total-score"]').textContent();
  expect(parseInt(uiScore)).toBe(apiData.deal.score);

  // 4. 카테고리 수 일치 확인
  const categoryCards = await page.locator('[data-testid="category-card"]').count();
  expect(categoryCards).toBe(apiData.deal.categories.length);

  // 5. 이벤트 수 일치 확인
  const eventCards = await page.locator('[data-testid="event-card"]').count();
  expect(eventCards).toBe(apiData.deal.topEvents.length);
});
```

---

## 8. 구현 순서

### Phase 1: 데이터 구조 완성 (백엔드)

| # | 작업 | 파일 | 우선순위 |
|---|------|------|---------|
| 1.1 | RiskEvent 노드 스키마 정의 | `v4/schemas.py` | P0 |
| 1.2 | RiskCategory 노드 스키마 정의 | `v4/schemas.py` | P0 |
| 1.3 | Neo4j 인덱스/제약조건 생성 | `v4/migrations/` | P0 |
| 1.4 | EventService 구현 | `v4/services/event_service.py` | P0 |
| 1.5 | PersonLinkingService 구현 | `v4/services/person_service.py` | P0 |
| 1.6 | CategoryService 구현 | `v4/services/category_service.py` | P1 |
| 1.7 | ScoreService 구현 | `v4/services/score_service.py` | P1 |
| 1.8 | 파이프라인 연결 | `v4/pipelines/` | P1 |

### Phase 2: API 재설계

| # | 작업 | 파일 | 우선순위 |
|---|------|------|---------|
| 2.1 | V4 API 라우터 생성 | `v4/api.py` | P0 |
| 2.2 | 딜 상세 API | `v4/api.py` | P0 |
| 2.3 | 카테고리 API | `v4/api.py` | P0 |
| 2.4 | 이벤트 API | `v4/api.py` | P1 |
| 2.5 | 인물 API | `v4/api.py` | P1 |
| 2.6 | 증거 API | `v4/api.py` | P1 |

### Phase 3: UI/UX 전면 개편

| # | 작업 | 파일 | 우선순위 |
|---|------|------|---------|
| 3.1 | shadcn/ui 설치 및 설정 | `components/ui/` | P0 |
| 3.2 | RiskDashboard 리팩토링 | `v4/RiskDashboard.tsx` | P0 |
| 3.3 | CategoryBreakdown 컴포넌트 | `v4/CategoryBreakdown/` | P0 |
| 3.4 | EventList 컴포넌트 | `v4/EventList/` | P0 |
| 3.5 | PersonList 컴포넌트 | `v4/PersonList/` | P1 |
| 3.6 | DrillDown 컴포넌트 | `v4/DrillDown/` | P1 |
| 3.7 | Evidence 컴포넌트 | `v4/Evidence/` | P1 |

### Phase 4: 검증 및 테스트

| # | 작업 | 파일 | 우선순위 |
|---|------|------|---------|
| 4.1 | Unit 테스트 | `tests/unit/` | P0 |
| 4.2 | Integration 테스트 | `tests/integration/` | P0 |
| 4.3 | API 테스트 | `tests/api/` | P0 |
| 4.4 | E2E 테스트 | `tests/e2e/` | P1 |
| 4.5 | API-UI 일치성 검증 | `tests/e2e/` | P1 |

---

## 9. 검증 체크리스트

### Phase 1 완료 기준

- [ ] RiskEvent 노드 생성됨 (> 0개)
- [ ] RiskCategory 노드 생성됨 (8개 카테고리)
- [ ] Person → News 관계 생성됨 (> 0개)
- [ ] 점수 계산 파이프라인 동작 확인

### Phase 2 완료 기준

- [ ] `/api/v4/deals/{id}` 응답에 categories, events, persons 포함
- [ ] 드릴다운 API 정상 동작
- [ ] API 응답 스키마 일치

### Phase 3 완료 기준

- [ ] 메인 대시보드 렌더링
- [ ] 카테고리 드릴다운 동작
- [ ] 이벤트 상세 모달 동작
- [ ] 인물 상세 모달 동작

### Phase 4 완료 기준

- [ ] 테스트 커버리지 80% 이상
- [ ] API-UI 데이터 일치율 100%
- [ ] E2E 핵심 플로우 테스트 통과

---

## Appendix

### A. 키워드 → 카테고리 매핑

```python
KEYWORD_CATEGORY_MAP = {
    # LEGAL
    "소송": "LEGAL", "고발": "LEGAL", "고소": "LEGAL", "제재": "LEGAL",
    "과징금": "LEGAL", "압수수색": "LEGAL", "구속": "LEGAL", "기소": "LEGAL",

    # CREDIT
    "부도": "CREDIT", "파산": "CREDIT", "회생": "CREDIT", "워크아웃": "CREDIT",
    "채무불이행": "CREDIT", "자본잠식": "CREDIT",

    # GOVERNANCE
    "횡령": "GOVERNANCE", "배임": "GOVERNANCE", "최대주주변경": "GOVERNANCE",
    "대표이사": "GOVERNANCE", "사임": "GOVERNANCE", "해임": "GOVERNANCE",

    # AUDIT
    "부적정": "AUDIT", "의견거절": "AUDIT", "한정": "AUDIT",
    "감사범위제한": "AUDIT", "분식회계": "AUDIT",

    # OPERATIONAL
    "사업중단": "OPERATIONAL", "허가취소": "OPERATIONAL", "영업정지": "OPERATIONAL",

    # ESG
    "환경오염": "ESG", "안전사고": "ESG", "갑질": "ESG", "비리": "ESG",

    # SUPPLY
    "공급망": "SUPPLY", "부품": "SUPPLY", "원자재": "SUPPLY",
}
```

### B. 시간 감쇠 함수

```python
import math
from datetime import datetime, timedelta

HALF_LIFE_DAYS = 30  # 30일 반감기

def apply_time_decay(score: int, detected_at: datetime) -> float:
    """
    시간 감쇠 적용
    30일 반감기 지수 감쇠
    """
    days_old = (datetime.now() - detected_at).days
    decay_factor = math.exp(-days_old * math.log(2) / HALF_LIFE_DAYS)
    return score * decay_factor
```

### C. Neo4j 초기화 스크립트

```cypher
// 1. 제약조건 생성
CREATE CONSTRAINT risk_category_id_unique IF NOT EXISTS
FOR (rc:RiskCategory) REQUIRE rc.id IS UNIQUE;

CREATE CONSTRAINT risk_event_id_unique IF NOT EXISTS
FOR (e:RiskEvent) REQUIRE e.id IS UNIQUE;

// 2. 인덱스 생성
CREATE INDEX risk_category_company_idx IF NOT EXISTS
FOR (rc:RiskCategory) ON (rc.companyId);

CREATE INDEX risk_event_company_idx IF NOT EXISTS
FOR (e:RiskEvent) ON (e.companyId);

CREATE INDEX person_risk_score_idx IF NOT EXISTS
FOR (p:Person) ON (p.riskScore);

// 3. 기본 카테고리 코드
// (런타임에 회사별로 생성)
```
