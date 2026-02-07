# Archive Index - 2026-02

> 2026년 2월 아카이브된 PDCA 문서 목록

---

## 아카이브 목록

| Feature | Match Rate | 아카이브 날짜 | 상태 |
|---------|:----------:|:-------------:|:----:|
| [risk-system-v4](./risk-system-v4/) | 100% | 2026-02-06 | ✅ 완료 |
| [risk-ui-ux-optimization](./risk-ui-ux-optimization/) | 100% | 2026-02-06 | ✅ 완료 |
| [supply-chain-e2e-test](./supply-chain-e2e-test/) | 92% | 2026-02-06 | ✅ 완료 |
| [risk-graph-v3](./risk-graph-v3/) | 92% | 2026-02-06 | ✅ 완료 |
| [risk-improvements](./risk-improvements/) | 92% | 2026-02-05 | ✅ 완료 |
| [risk-phase3](./risk-phase3/) | 91.7% | 2026-02-05 | ✅ 완료 |

---

## risk-ui-ux-optimization

**설명**: 공급망 리스크 화면 UI/UX 최적화 - 이모지 통일, 인터렉티브 그래프, 스타일 일관성

**포함 문서**:
- `risk-ui-ux-optimization.plan.md` - 계획서
- `risk-ui-ux-optimization.design.md` - 설계서
- `risk-ui-ux-optimization.report.md` - 완료 보고서

**주요 성과**:
- 중앙 상수 시스템 (`constants.ts`) - EMOJI_MAP, RISK_SCORE_COLORS, STATUS_THRESHOLDS
- 유틸리티 함수 (`utils.ts`) - getStatusFromScore, getScoreTextClass 등
- 줌 컨트롤 컴포넌트 (`ZoomControls.tsx`)
- Supply Chain Graph 인터렉티브 개선 (줌/팬/드래그)
- 7개 컴포넌트 스타일 통일

**핵심 기능**:
- 마우스 휠 줌 (0.3x ~ 3.0x)
- 캔버스 팬/드래그
- 키보드 네비게이션 (+/-/0/방향키)
- 통일된 STATUS_THRESHOLDS (0-49: PASS, 50-74: WARNING, 75+: FAIL)

**버그 수정**:
- RiskStatusView.tsx 재귀 호출 버그 수정 (line 41)

**Match Rate**: 100% ✅

---

## risk-graph-v3

**설명**: Risk Graph v3.0 - 키워드 엔진 + Status 중심 구조 + 점수 산정 투명화

**포함 문서**:
- `risk-graph-v3.plan.md` - 계획서
- `risk-graph-v3.design.md` - 설계서
- `risk-graph-v3.analysis.md` - Gap 분석 보고서
- `risk-graph-v3.report.md` - 완료 보고서

**주요 성과**:
- 키워드 사전 모듈 (75개 리스크 키워드)
- 점수 계산 엔진 (시간 감쇠 + 신뢰도)
- V3 API 엔드포인트 (6개)
- Status 중심 대시보드 UI
- 자동 수집 스케줄러
- 알림 발송 시스템

**핵심 기능**:
- PASS/WARNING/FAIL Status 기반 분류
- 직접 리스크 vs 전이 리스크 투명화
- 점수 계산 근거 추적 가능

**Match Rate**: 92% ✅

---

## risk-improvements

**설명**: Risk Monitoring System v2.2 개선 - Phase 2 (실제 데이터 연동)

**포함 문서**:
- `risk-improvements.plan.md` - 계획서
- `risk-improvements.design.md` - 설계서
- `risk-improvements.analysis.md` - Gap 분석 보고서
- `risk-improvements.report.md` - 완료 보고서

**주요 성과**:
- Neo4j 클라이언트 구현
- OpenAI 6대 AI 기능 연동
- WebSocket 실시간 신호 시스템
- DART/뉴스 데이터 로드 스크립트

**Match Rate**: 92% ✅

---

## risk-phase3

**설명**: Risk Monitoring System v2.3 - Phase 3 (고급 분석 기능)

**포함 문서**:
- `risk-phase3.plan.md` - 계획서
- `risk-phase3.design.md` - 설계서
- `risk-phase3.analysis.md` - Gap 분석 보고서
- `risk-phase3.report.md` - 완료 보고서

**주요 성과**:
- Cascade 시뮬레이션 엔진 (`simulation_engine.py`)
- ML 피처 엔지니어링 (`feature_engineering.py`)
- Prophet 기반 시계열 예측기 (`ml_predictor.py`)
- 커스텀 시나리오 빌더 (`RiskScenarioBuilder.tsx`)
- ML 예측 차트 UI (`RiskPrediction.tsx`)

**핵심 기능**:
- 3-Tier Cascade 리스크 전이 분석
- 7/30/90일 리스크 점수 예측 (95% 신뢰구간)
- 사용자 정의 What-If 시나리오 생성

**Match Rate**: 91.7% ✅

---

## supply-chain-e2e-test

**설명**: Supply Chain E2E 통합테스트 - 공급망 리스크 화면 전체 기능 검증

**포함 문서**:
- `supply-chain-e2e-test.plan.md` - 계획서
- `supply-chain-e2e-test.design.md` - 설계서
- `supply-chain-e2e-test.analysis.md` - Gap 분석 보고서
- `supply-chain-e2e-test.report.md` - 완료 보고서

**주요 성과**:
- API 통합테스트 (test_api_flow.py) - 26개 테스트
- Supply Chain E2E (test_supply_chain.py) - 20개 테스트
- Score Breakdown E2E (test_score_breakdown.py) - 24개 테스트
- UI 컴포넌트 테스트 (RiskGraph, RiskScoreBreakdownV3) - 53개 테스트

**핵심 기능**:
- 7개 탭 (Overview, Supply Chain, Signals, Score Breakdown, AI, Simulation, Prediction) 커버리지
- 41 pytest passed, 29 skipped, 0 failed
- UI 53개 테스트 100% 통과
- 총 124개 테스트 구현

**Match Rate**: 92% ✅

---

## risk-system-v4

**설명**: Risk System V4 전면 재설계 - 그래프 DB 4-노드 계층 구조

**포함 문서**:
- `risk-system-v4.plan.md` - 계획서
- `risk-system-v4.design.md` - 설계서
- `risk-system-v4.analysis.md` - Gap 분석 보고서
- `risk-system-v4.report.md` - 완료 보고서

**주요 성과**:
- 그래프 DB 4-노드 계층 구조 설계 및 구현
- V4 API 9개 엔드포인트 구현
- 점수 계산 파이프라인 (direct + propagated = total)
- 드릴다운 분석 네비게이션

**그래프 스키마 (4-노드)**:
```
Deal (메인 기업)
├── HAS_CATEGORY → RiskCategory (10개)
│   └── HAS_EVENT → RiskEvent
└── HAS_RELATED → Company (관련기업)
    └── HAS_EVENT → RiskEvent
```

**노드 현황**:
- Deal: 2개 (SK하이닉스, 삼성전자)
- RiskCategory: 20개 (10개 카테고리 × 2 Deals)
- Company: 10개 (관련기업)
- RiskEvent: 12개 (정보 노드)

**RiskCategory 10개**:
주주, 임원, 신용, 법률, 지배구조, 운영, 감사, ESG, 공급망, 기타

**핵심 변경사항**:
- Spider Web → 계층 구조로 재설계
- Person 노드 → RiskEvent.relatedPerson 속성으로 통합
- News/Disclosure 노드 → RiskEvent (type: NEWS/ISSUE/DISCLOSURE)로 통합
- 출처 정보 필수 포함 (summary, sourceName, sourceUrl)

**Match Rate**: 100% ✅

---

*Last Updated: 2026-02-06*
