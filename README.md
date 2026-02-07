<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Risk Monitoring System v2.3

Graph-First + AI Enhanced 리스크 모니터링 시스템

## Run Locally

**Prerequisites:** Node.js, Python 3.9+

1. Install dependencies:
   ```bash
   npm install
   pip install -r requirements.txt
   ```

2. Set environment variables in `.env.local`:
   ```
   GEMINI_API_KEY=your_key
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   OPENAI_API_KEY=your_key
   ```

3. Run the app:
   ```bash
   npm run dev
   ```

4. Run backend API:
   ```bash
   cd risk_engine && uvicorn api:app --reload --port 8000
   ```

---

## Features

### Phase 1: 기본 리스크 모니터링
- 포트폴리오 대시보드
- 딜별 리스크 점수 (0-100)
- 카테고리별 분석 (시장위험, 신용위험, 운영위험 등)

### Phase 2: 실제 데이터 연동
- Neo4j 그래프 DB 연동
- DART 공시 데이터 수집
- 뉴스 감성 분석
- 6대 AI 분석 기능 (OpenAI)
- WebSocket 실시간 신호

### Phase 3: 고급 분석 기능

#### Cascade 시뮬레이션
3-Tier 기반 리스크 전이 분석

```
Tier 1 (직접 공급사): 80% 영향
Tier 2 (2차 공급사):  50% 영향
Tier 3 (3차 공급사):  20% 영향
```

**프리셋 시나리오:**
- 부산항 파업 (`busan_port`)
- 메모리 가격 폭락 (`memory_crash`)
- 중국 희토류 수출 제한 (`china_rare_earth`)
- 금리 급등 (`interest_rate_hike`)

#### ML 리스크 예측
Prophet 기반 시계열 예측

- 7일 / 30일 / 90일 예측 기간
- 95% 신뢰구간 제공
- 자동 폴백 (Prophet 미설치 시 Random Walk)

#### 커스텀 시나리오 빌더
사용자 정의 What-If 분석

- 영향 섹터 선택 (반도체, 자동차, 물류 등)
- 카테고리별 영향도 슬라이더
- 전이 배수 설정 (1.0x ~ 3.0x)

---

## Project Structure

```
new_wave/
├── components/risk/          # React 컴포넌트
│   ├── RiskPage.tsx          # 메인 페이지
│   ├── RiskOverview.tsx      # 포트폴리오 요약
│   ├── RiskSimulation.tsx    # 시뮬레이션 UI
│   ├── RiskPrediction.tsx    # ML 예측 차트
│   ├── RiskScenarioBuilder.tsx # 커스텀 시나리오
│   └── types.ts              # TypeScript 타입
│
├── risk_engine/              # Python 백엔드
│   ├── api.py                # FastAPI 엔드포인트
│   ├── neo4j_client.py       # Neo4j 클라이언트
│   ├── ai_service_v2.py      # OpenAI 6대 기능
│   ├── simulation_engine.py  # Cascade 시뮬레이션
│   ├── feature_engineering.py # ML 피처 추출
│   └── ml_predictor.py       # Prophet 예측기
│
├── tests/                    # 테스트
│   ├── test_simulation.py    # 시뮬레이션 테스트
│   └── test_prediction.py    # 예측 테스트
│
├── models/                   # ML 모델 저장
└── docs/                     # 문서
```

---

## API Endpoints

### Phase 3 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v2/simulate/advanced` | Cascade 시뮬레이션 실행 |
| GET | `/api/v2/predict/{deal_id}` | 리스크 점수 예측 |
| POST | `/api/v2/predict/train/{deal_id}` | 예측 모델 학습 |
| POST | `/api/v2/scenarios/custom` | 커스텀 시나리오 생성 |
| GET | `/api/v2/scenarios/custom` | 커스텀 시나리오 목록 |

---

## Testing

```bash
# 전체 테스트
pytest tests/ -v

# 시뮬레이션 테스트
pytest tests/test_simulation.py -v

# 예측 테스트
pytest tests/test_prediction.py -v
```

---

## Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Recharts

**Backend:**
- FastAPI
- Neo4j (Graph DB)
- Prophet (Time Series)
- OpenAI API

---

## License

MIT
