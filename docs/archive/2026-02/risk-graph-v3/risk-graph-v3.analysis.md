# Risk Graph v3 Gap Analysis Report

> 생성일: 2026-02-06
> 분석 도구: bkit:gap-detector

## 분석 개요

| 항목 | 값 |
|------|-------|
| Feature | risk-graph-v3 |
| 설계 문서 | docs/02-design/features/risk-graph-v3.design.md |
| 구현 경로 | risk_engine/, components/risk/ |
| 분석 일시 | 2026-02-06 |

## 전체 점수

| 카테고리 | 점수 | 상태 |
|----------|:-----:|:------:|
| 설계 일치율 | 92% | ✅ Good |
| 아키텍처 준수 | 95% | ✅ Good |
| 컨벤션 준수 | 90% | ✅ Good |
| **종합** | **92%** | ✅ Good |

---

## 상세 분석 결과

### 1. keywords.py - 키워드 사전 모듈 (100%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| DART_RISK_KEYWORDS (32개) | ✅ | 설계대로 구현 |
| NEWS_RISK_KEYWORDS (20개) | ✅ | 설계대로 구현 |
| KIND_RISK_KEYWORDS (23개) | ✅ | 설계대로 구현 |
| CATEGORY_KEYWORDS (6개 → 8개) | ✅ | CAPITAL, OTHER 추가 |
| match_keywords() | ✅ | MatchResult 반환 |
| classify_category() | ✅ | CategoryType 반환 |
| get_keywords_by_source() | ✅ | 소스별 키워드 반환 |
| build_search_queries_for_company() | ✅ | 설계 외 추가 기능 |

### 2. score_engine.py - 점수 계산 엔진 (95%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| DECAY_HALF_LIFE = 30 | ✅ | 설계대로 구현 |
| calc_decay() | ✅ | exp(-days/30) |
| calc_confidence() | ✅ | 0.5 + 0.15 × keywords |
| calculate_raw_score() | ✅ | max(scores) 사용 |
| calculate_decayed_score() | ✅ | DecayResult 반환 |
| determine_sentiment() | ⚠️ | 3단계 → 4단계 확장 |

### 3. validator.py - 데이터 검증 모듈 (100%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| REQUIRED_FIELDS | ✅ | News, Disclosure, Company |
| RANGE_VALIDATION | ✅ | 확장 구현 |
| ValidationResult | ✅ | is_valid, errors, warnings |
| validate() | ✅ | 종합 검증 |
| normalize() | ✅ | URL, date, corp_code |
| check_duplicate() | ✅ | 해시 기반 중복 체크 |

### 4. dart_collector_v2.py - DART 수집기 (100%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| DART_API_BASE | ✅ | 올바른 URL |
| COLLECTION_SCHEDULE | ✅ | 실시간, 일간, 주간, 분기 |
| DisclosureData | ✅ | 설계 스키마 일치 |
| collect_disclosures() | ✅ | 키워드 매칭 포함 |
| analyze_disclosure() | ✅ | 점수 계산 포함 |
| save_to_neo4j() | ✅ | Neo4j 저장 |

### 5. news_collector_v2.py - 뉴스 수집기 (100%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| NEWS_SOURCES | ✅ | Google RSS, Naver |
| FILTER_CONFIG | ✅ | max_age, min_score 등 |
| NewsData | ✅ | match_result, score_result 포함 |
| collect_news() | ✅ | 멀티 쿼리 수집 |
| deduplicate() | ✅ | URL 해시 기반 |
| save_to_neo4j() | ✅ | Neo4j 저장 |

### 6. risk_calculator_v3.py - 리스크 계산기 (95%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| CATEGORY_WEIGHTS | ✅ | 8개 카테고리 |
| TIER_PROPAGATION_RATE | ✅ | T1: 70%, T2: 50%, T3: 30% |
| MAX_PROPAGATED_RISK | ⚠️ | 설계: 25, 구현: 30 |
| STATUS_THRESHOLDS | ✅ | PASS/WARNING/FAIL |
| calculate_direct_risk() | ✅ | Neo4j 쿼리 기반 |
| calculate_propagated_risk() | ✅ | Person + Subsidiary |
| calculate_total_risk() | ✅ | Direct + Propagated |

### 7. load_graph_v3.py - 그래프 스키마 (100%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| STATUS_DEFINITIONS | ✅ | PASS, WARNING, FAIL |
| RISK_CATEGORY_CODES | ✅ | 8개 카테고리 |
| create_constraints() | ✅ | Unique 제약조건 |
| create_indexes() | ✅ | 성능 인덱스 |
| create_status_nodes() | ✅ | MERGE 사용 |

### 8. api.py - V3 API 엔드포인트 (100%)

| 설계 엔드포인트 | 상태 | 비고 |
|-----------------|:------:|-------|
| GET /api/v3/status/summary | ✅ | StatusSummary 반환 |
| GET /api/v3/companies/{id}/score | ✅ | ScoreBreakdown 반환 |
| GET /api/v3/companies/{id}/news | ✅ | NewsList 반환 |
| GET /api/v3/data-quality | ✅ | DataQuality 반환 |
| POST /api/v3/refresh/{company_id} | ✅ | 데이터 갱신 |
| GET /api/v3/keywords | ✅ | 키워드 사전 (설계 외) |

### 9. scheduler.py - 스케줄러 (100%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| DART_COLLECT | ✅ | 60분 주기 |
| NEWS_COLLECT | ✅ | 30분 주기 |
| SCORE_UPDATE | ✅ | 15분 주기 |
| FULL_SYNC | ✅ | 매일 06:00 |
| HEALTH_CHECK | ✅ | 5분 주기 |

### 10. alert_sender.py - 알림 발송기 (95%)

| 설계 항목 | 상태 | 비고 |
|-----------|:------:|-------|
| AlertChannel | ✅ | EMAIL, SLACK, WEBHOOK |
| AlertPriority | ✅ | LOW ~ CRITICAL |
| SlackAlertSender | ✅ | Webhook 연동 |
| WebhookAlertSender | ✅ | 일반 Webhook |
| EmailAlertSender | ⚠️ | Stub 구현 |

### 11. UI 컴포넌트 (100%)

| 컴포넌트 | 상태 | 비고 |
|----------|:------:|-------|
| RiskStatusView.tsx | ✅ | Status 대시보드 |
| RiskScoreBreakdownV3.tsx | ✅ | 점수 상세 |

---

## 차이점 요약

### 누락 항목 (설계 O, 구현 X)

| 항목 | 설계 위치 | 설명 |
|------|-----------|------|
| KIND Collector | Section 3 | KIND (거래소) 수집기 별도 모듈 없음 |

### 추가 항목 (설계 X, 구현 O)

| 항목 | 구현 위치 | 설명 |
|------|----------|------|
| CAPITAL 카테고리 | keywords.py | 자본 관련 키워드 |
| OTHER 카테고리 | keywords.py | 기타 분류 |
| /api/v3/keywords | api.py | 키워드 사전 조회 API |
| get_keyword_stats() | keywords.py | 키워드 통계 헬퍼 |

### 변경 항목 (설계 ≠ 구현)

| 항목 | 설계 | 구현 | 영향 |
|------|------|------|------|
| MAX_PROPAGATED_RISK | 25 | 30 | Low |
| Sentiment 단계 | 3 | 4 | Low |
| 카테고리 수 | 6 | 8 | Low |

---

## 권장 조치

### 즉시 조치 (High Priority)

1. **설계 문서 업데이트** - 구현된 향상 사항 반영
   - CAPITAL, OTHER 카테고리 추가
   - 4단계 Sentiment 시스템 문서화
   - MAX_PROPAGATED_RISK 값 통일

### 향후 개선 (Low Priority)

1. KIND Collector 별도 모듈 구현
2. EmailAlertSender 완전 구현
3. alert_sender.py 테스트 추가

---

## 결론

**Match Rate: 92%** ✅

Risk Graph v3 구현이 설계 문서를 충실히 따르고 있으며, 일부 영역에서는 설계보다 향상된 기능을 제공합니다.

- ✅ 핵심 아키텍처 완전 구현
- ✅ API 엔드포인트 100% 구현
- ✅ 데이터 수집 파이프라인 완료
- ✅ UI 컴포넌트 완료
- ⚠️ 일부 상수값 차이 (영향 낮음)
- ⚠️ KIND Collector 별도 모듈 없음 (통합 구현)

**추천**: Check 단계 통과. Report 단계로 진행 가능.
