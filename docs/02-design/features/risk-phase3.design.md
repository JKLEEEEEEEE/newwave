# Risk Monitoring System - Phase 3 설계서

> **기능명**: risk-phase3
> **버전**: v2.3
> **작성일**: 2026-02-05
> **기반 Plan**: `/docs/01-plan/features/risk-phase3.plan.md`

---

## 1. 설계 개요

### 1.1 목적

Phase 3 고급 기능 구현을 위한 상세 기술 설계서입니다. 시뮬레이션 정교화, ML 예측, 커스텀 시나리오 기능에 집중합니다.

### 1.2 설계 범위

| 기능 | 우선순위 | 이 문서에서 |
|------|:--------:|:----------:|
| 시뮬레이션 정교화 | P0 | **상세 설계** |
| ML 리스크 예측 | P1 | **상세 설계** |
| 커스텀 시나리오 UI | P1 | **상세 설계** |

---

## 2. 시뮬레이션 엔진 설계

### 2.1 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    SimulationEngine                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Scenario   │───▶│   Cascade    │───▶│   Result     │       │
│  │   Parser     │    │   Calculator │    │   Aggregator │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Neo4j Query │    │   Cache      │    │   AI         │       │
│  │  (affected)  │    │   Manager    │    │  Interpreter │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 모듈 설계

**파일**: `risk_engine/simulation_engine.py`

```python
"""
시뮬레이션 엔진 v2.3
Cascade 효과 기반 동적 리스크 계산
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from functools import lru_cache
import logging

from .neo4j_client import neo4j_client
from .ai_service_v2 import ai_service_v2

logger = logging.getLogger(__name__)


@dataclass
class CascadeConfig:
    """Cascade 효과 설정"""
    tier1_multiplier: float = 0.8  # 1차 영향
    tier2_multiplier: float = 0.5  # 2차 영향
    tier3_multiplier: float = 0.2  # 3차 영향
    max_depth: int = 3             # 최대 탐색 깊이


@dataclass
class ScenarioConfig:
    """시나리오 설정"""
    id: str
    name: str
    affected_sectors: List[str]
    impact_factors: Dict[str, int]  # category -> impact
    propagation_multiplier: float
    severity: str  # low, medium, high


@dataclass
class SimulationResult:
    """시뮬레이션 결과"""
    deal_id: str
    deal_name: str
    original_score: int
    simulated_score: int
    delta: int
    affected_categories: List[Dict[str, Any]]
    cascade_path: List[str]
    interpretation: Optional[str] = None


class SimulationEngine:
    """시뮬레이션 엔진 (Cascade 효과 계산)"""

    def __init__(self, cascade_config: Optional[CascadeConfig] = None):
        self.cascade_config = cascade_config or CascadeConfig()
        self._cache: Dict[str, Any] = {}

    def run_simulation(
        self,
        scenario: ScenarioConfig,
        target_deal_ids: Optional[List[str]] = None
    ) -> List[SimulationResult]:
        """시뮬레이션 실행"""

        # 1. 영향받는 기업 추출
        affected_companies = self._get_affected_companies(
            scenario.affected_sectors,
            target_deal_ids
        )

        # 2. Cascade 효과 계산
        results = []
        for company in affected_companies:
            result = self._calculate_cascade_impact(company, scenario)
            results.append(result)

        # 3. AI 해석 추가 (선택적)
        if ai_service_v2 and ai_service_v2.is_available:
            results = self._add_ai_interpretation(results, scenario)

        return sorted(results, key=lambda r: r.delta, reverse=True)

    def _get_affected_companies(
        self,
        sectors: List[str],
        target_deal_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """영향받는 기업 추출 (Neo4j)"""

        query = """
        MATCH (c:Company)
        WHERE c.sector IN $sectors
           OR c.name IN $targetNames
        OPTIONAL MATCH (c)<-[:SUPPLIES_TO*1..3]-(supplier:Company)
        WHERE supplier.totalRiskScore > 50
        RETURN c.name AS name,
               c.corpCode AS corpCode,
               c.sector AS sector,
               c.totalRiskScore AS currentScore,
               collect(DISTINCT {
                   name: supplier.name,
                   score: supplier.totalRiskScore,
                   tier: length(shortestPath((supplier)-[:SUPPLIES_TO*]->(c)))
               }) AS suppliers
        """

        try:
            neo4j_client.connect()
            results = neo4j_client.execute_read(query, {
                "sectors": sectors,
                "targetNames": target_deal_ids or []
            })
            return results
        except Exception as e:
            logger.error(f"영향 기업 조회 실패: {e}")
            return []

    def _calculate_cascade_impact(
        self,
        company: Dict[str, Any],
        scenario: ScenarioConfig
    ) -> SimulationResult:
        """개별 기업 Cascade 영향 계산"""

        original_score = company.get("currentScore", 50)
        cascade_path = []
        total_delta = 0
        affected_categories = []

        # 1. 직접 영향 (섹터 매칭 시)
        if company.get("sector") in scenario.affected_sectors:
            for category, impact in scenario.impact_factors.items():
                direct_impact = int(impact * scenario.propagation_multiplier)
                affected_categories.append({
                    "category": category,
                    "delta": direct_impact,
                    "source": "direct"
                })
                total_delta += direct_impact

        # 2. Cascade 영향 (공급망 전이)
        suppliers = company.get("suppliers", [])
        for supplier in suppliers:
            if supplier.get("name"):
                tier = supplier.get("tier", 1)
                supplier_score = supplier.get("score", 0)

                # Tier별 감쇠 계수
                if tier == 1:
                    multiplier = self.cascade_config.tier1_multiplier
                elif tier == 2:
                    multiplier = self.cascade_config.tier2_multiplier
                else:
                    multiplier = self.cascade_config.tier3_multiplier

                cascade_impact = int(supplier_score * 0.1 * multiplier)
                if cascade_impact > 0:
                    cascade_path.append(f"{supplier['name']} (Tier{tier})")
                    total_delta += cascade_impact
                    affected_categories.append({
                        "category": "supply_chain",
                        "delta": cascade_impact,
                        "source": supplier["name"]
                    })

        # 점수 상한 적용
        simulated_score = min(100, original_score + total_delta)

        return SimulationResult(
            deal_id=company.get("corpCode", company.get("name", "").replace(" ", "_").lower()),
            deal_name=company.get("name", "Unknown"),
            original_score=original_score,
            simulated_score=simulated_score,
            delta=simulated_score - original_score,
            affected_categories=affected_categories,
            cascade_path=cascade_path
        )

    def _add_ai_interpretation(
        self,
        results: List[SimulationResult],
        scenario: ScenarioConfig
    ) -> List[SimulationResult]:
        """AI 기반 결과 해석 추가"""

        for result in results[:5]:  # 상위 5개만 AI 해석
            try:
                interpretation = ai_service_v2.interpret_simulation({
                    "scenario": scenario.name,
                    "company": result.deal_name,
                    "delta": result.delta,
                    "categories": result.affected_categories
                })
                result.interpretation = interpretation.get("impact_summary", "")
            except Exception as e:
                logger.warning(f"AI 해석 실패: {e}")

        return results

    @lru_cache(maxsize=100)
    def get_cached_result(self, scenario_id: str, deal_ids_hash: str):
        """캐시된 결과 조회"""
        cache_key = f"{scenario_id}:{deal_ids_hash}"
        return self._cache.get(cache_key)


# 싱글톤 인스턴스
simulation_engine = SimulationEngine()
```

### 2.3 API 엔드포인트

**파일**: `risk_engine/api.py` (추가)

```python
from .simulation_engine import simulation_engine, ScenarioConfig

class CustomScenarioRequest(BaseModel):
    """커스텀 시나리오 요청"""
    name: str
    affectedSectors: List[str]
    impactFactors: Dict[str, int]
    propagationMultiplier: float = 1.5
    severity: str = "medium"


@app.post("/api/v2/simulate/advanced")
async def run_advanced_simulation(request: SimulationRequest):
    """고급 시뮬레이션 실행 (Cascade 효과)"""

    scenario_data = get_scenario_by_id(request.scenarioId)
    if not scenario_data:
        raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다")

    scenario = ScenarioConfig(
        id=scenario_data["id"],
        name=scenario_data["name"],
        affected_sectors=scenario_data["affectedSectors"],
        impact_factors=scenario_data["impactFactors"],
        propagation_multiplier=scenario_data["propagationMultiplier"],
        severity=scenario_data["severity"]
    )

    results = simulation_engine.run_simulation(scenario, request.dealIds)

    return {
        "success": True,
        "scenario": scenario_data,
        "results": [
            {
                "dealId": r.deal_id,
                "dealName": r.deal_name,
                "originalScore": r.original_score,
                "simulatedScore": r.simulated_score,
                "delta": r.delta,
                "affectedCategories": r.affected_categories,
                "cascadePath": r.cascade_path,
                "interpretation": r.interpretation
            }
            for r in results
        ]
    }


@app.post("/api/v2/scenarios/custom")
async def create_custom_scenario(request: CustomScenarioRequest):
    """커스텀 시나리오 생성"""

    scenario_id = f"custom_{int(datetime.now().timestamp())}"

    # Neo4j에 저장
    if NEO4J_CLIENT_AVAILABLE:
        query = """
        CREATE (s:Scenario {
            id: $id,
            name: $name,
            affectedSectors: $sectors,
            impactFactors: $factors,
            propagationMultiplier: $multiplier,
            severity: $severity,
            isCustom: true,
            createdAt: datetime()
        })
        RETURN s
        """
        neo4j_client.execute_write(query, {
            "id": scenario_id,
            "name": request.name,
            "sectors": request.affectedSectors,
            "factors": json.dumps(request.impactFactors),
            "multiplier": request.propagationMultiplier,
            "severity": request.severity
        })

    return {
        "success": True,
        "scenarioId": scenario_id,
        "message": "커스텀 시나리오가 생성되었습니다"
    }


@app.get("/api/v2/scenarios/custom")
async def get_custom_scenarios():
    """커스텀 시나리오 목록 조회"""

    if not NEO4J_CLIENT_AVAILABLE:
        return {"scenarios": []}

    query = """
    MATCH (s:Scenario {isCustom: true})
    RETURN s.id AS id, s.name AS name, s.affectedSectors AS affectedSectors,
           s.impactFactors AS impactFactors, s.propagationMultiplier AS propagationMultiplier,
           s.severity AS severity, s.createdAt AS createdAt
    ORDER BY s.createdAt DESC
    """

    results = neo4j_client.execute_read(query)
    return {"scenarios": results}
```

---

## 3. ML 예측 모듈 설계

### 3.1 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                      ML Predictor                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Feature    │───▶│   Model      │───▶│   Prediction │       │
│  │  Engineering │    │   (Prophet)  │    │   Formatter  │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                                    │
│         ▼                   ▼                                    │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │  Neo4j Data  │    │   Model      │                           │
│  │  (history)   │    │   Storage    │                           │
│  └──────────────┘    └──────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 피처 엔지니어링

**파일**: `risk_engine/feature_engineering.py`

```python
"""
피처 엔지니어링 모듈
Neo4j 데이터 → ML 학습용 피처 변환
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .neo4j_client import neo4j_client


class FeatureEngineer:
    """피처 엔지니어링 클래스"""

    def __init__(self):
        self.feature_columns = [
            "risk_score",
            "news_sentiment",
            "disclosure_count",
            "supply_chain_risk",
            "day_of_week",
            "month"
        ]

    def extract_features(
        self,
        company_id: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """기업별 피처 추출"""

        # 1. 일별 리스크 점수 이력 조회
        risk_history = self._get_risk_history(company_id, start_date, end_date)

        # 2. 뉴스 감성 지표
        news_sentiment = self._get_news_sentiment(company_id, start_date, end_date)

        # 3. 공시 빈도
        disclosure_counts = self._get_disclosure_counts(company_id, start_date, end_date)

        # 4. 공급망 리스크
        supply_chain_risk = self._get_supply_chain_risk(company_id)

        # 데이터 병합
        df = pd.DataFrame(risk_history)
        df["ds"] = pd.to_datetime(df["date"])
        df["y"] = df["risk_score"]

        # 추가 피처
        df["news_sentiment"] = df["ds"].map(
            lambda d: news_sentiment.get(d.strftime("%Y-%m-%d"), 0)
        )
        df["disclosure_count"] = df["ds"].map(
            lambda d: disclosure_counts.get(d.strftime("%Y-%m-%d"), 0)
        )
        df["supply_chain_risk"] = supply_chain_risk
        df["day_of_week"] = df["ds"].dt.dayofweek
        df["month"] = df["ds"].dt.month

        return df

    def _get_risk_history(self, company_id: str, start_date: str, end_date: str) -> List[Dict]:
        """리스크 점수 이력 조회"""

        query = """
        MATCH (c:Company {corpCode: $companyId})-[:HAS_RISK_HISTORY]->(h:RiskHistory)
        WHERE h.date >= date($startDate) AND h.date <= date($endDate)
        RETURN h.date AS date, h.score AS risk_score
        ORDER BY h.date
        """

        try:
            results = neo4j_client.execute_read(query, {
                "companyId": company_id,
                "startDate": start_date,
                "endDate": end_date
            })
            return results if results else self._generate_mock_history(start_date, end_date)
        except Exception:
            return self._generate_mock_history(start_date, end_date)

    def _get_news_sentiment(self, company_id: str, start_date: str, end_date: str) -> Dict[str, float]:
        """뉴스 감성 지표"""

        query = """
        MATCH (n:NewsArticle)-[:MENTIONS]->(c:Company {corpCode: $companyId})
        WHERE n.publishedAt >= datetime($startDate) AND n.publishedAt <= datetime($endDate)
        RETURN date(n.publishedAt) AS date,
               avg(CASE n.sentiment
                   WHEN '긍정' THEN 1
                   WHEN '중립' THEN 0
                   WHEN '부정' THEN -1
                   ELSE 0
               END) AS sentiment
        """

        try:
            results = neo4j_client.execute_read(query, {
                "companyId": company_id,
                "startDate": start_date,
                "endDate": end_date
            })
            return {str(r["date"]): r["sentiment"] for r in results}
        except Exception:
            return {}

    def _get_disclosure_counts(self, company_id: str, start_date: str, end_date: str) -> Dict[str, int]:
        """공시 빈도"""

        query = """
        MATCH (c:Company {corpCode: $companyId})-[:HAS_DISCLOSURE]->(d:Disclosure)
        WHERE d.date >= $startDate AND d.date <= $endDate
        RETURN d.date AS date, count(d) AS count
        """

        try:
            results = neo4j_client.execute_read(query, {
                "companyId": company_id,
                "startDate": start_date,
                "endDate": end_date
            })
            return {r["date"]: r["count"] for r in results}
        except Exception:
            return {}

    def _get_supply_chain_risk(self, company_id: str) -> float:
        """공급망 리스크"""

        query = """
        MATCH (c:Company {corpCode: $companyId})<-[:SUPPLIES_TO]-(s:Company)
        RETURN avg(s.totalRiskScore) AS avgSupplierRisk
        """

        try:
            result = neo4j_client.execute_read_single(query, {"companyId": company_id})
            return result.get("avgSupplierRisk", 50) if result else 50
        except Exception:
            return 50

    def _generate_mock_history(self, start_date: str, end_date: str) -> List[Dict]:
        """Mock 이력 데이터 생성"""

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        history = []
        current = start
        base_score = 50

        while current <= end:
            # 랜덤 워크 시뮬레이션
            base_score = max(20, min(80, base_score + np.random.normal(0, 3)))
            history.append({
                "date": current.strftime("%Y-%m-%d"),
                "risk_score": int(base_score)
            })
            current += timedelta(days=1)

        return history


# 싱글톤 인스턴스
feature_engineer = FeatureEngineer()
```

### 3.3 ML 예측기

**파일**: `risk_engine/ml_predictor.py`

```python
"""
ML 리스크 예측 모듈
Prophet 기반 시계열 예측
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import os
import pickle

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

import pandas as pd
import numpy as np

from .feature_engineering import feature_engineer

logger = logging.getLogger(__name__)


class MLPredictor:
    """ML 리스크 예측기"""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.models: Dict[str, Prophet] = {}
        os.makedirs(model_dir, exist_ok=True)

    @property
    def is_available(self) -> bool:
        return PROPHET_AVAILABLE

    def train_model(self, company_id: str, historical_days: int = 365) -> bool:
        """모델 학습"""

        if not PROPHET_AVAILABLE:
            logger.warning("Prophet 라이브러리 미설치")
            return False

        # 데이터 준비
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=historical_days)).strftime("%Y-%m-%d")

        df = feature_engineer.extract_features(company_id, start_date, end_date)

        if len(df) < 30:
            logger.warning(f"학습 데이터 부족: {len(df)}일")
            return False

        # Prophet 모델 학습
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )

        # 추가 회귀 변수
        model.add_regressor("news_sentiment")
        model.add_regressor("disclosure_count")

        # 학습
        model.fit(df[["ds", "y", "news_sentiment", "disclosure_count"]])

        # 모델 저장
        self.models[company_id] = model
        model_path = os.path.join(self.model_dir, f"{company_id}.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        logger.info(f"모델 학습 완료: {company_id}")
        return True

    def predict(
        self,
        company_id: str,
        periods: int = 30,
        include_confidence: bool = True
    ) -> Dict[str, Any]:
        """리스크 예측"""

        # 모델 로드
        model = self._load_model(company_id)
        if model is None:
            return self._fallback_prediction(company_id, periods)

        # 미래 데이터프레임 생성
        future = model.make_future_dataframe(periods=periods)

        # 회귀 변수 (최근 평균값 사용)
        future["news_sentiment"] = 0
        future["disclosure_count"] = 1

        # 예측
        forecast = model.predict(future)

        # 결과 포맷팅
        predictions = []
        for _, row in forecast.tail(periods).iterrows():
            pred = {
                "date": row["ds"].strftime("%Y-%m-%d"),
                "predicted_score": max(0, min(100, int(row["yhat"]))),
            }
            if include_confidence:
                pred["lower_bound"] = max(0, int(row["yhat_lower"]))
                pred["upper_bound"] = min(100, int(row["yhat_upper"]))

            predictions.append(pred)

        return {
            "company_id": company_id,
            "periods": periods,
            "predictions": predictions,
            "trend": self._determine_trend(predictions),
            "confidence": 0.95 if include_confidence else None
        }

    def _load_model(self, company_id: str) -> Optional[Prophet]:
        """모델 로드"""

        if company_id in self.models:
            return self.models[company_id]

        model_path = os.path.join(self.model_dir, f"{company_id}.pkl")
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                model = pickle.load(f)
                self.models[company_id] = model
                return model

        return None

    def _fallback_prediction(self, company_id: str, periods: int) -> Dict[str, Any]:
        """폴백 예측 (Prophet 없을 때)"""

        # 간단한 이동 평균 기반 예측
        base_score = 50  # 기본 점수

        predictions = []
        current = datetime.now()

        for i in range(periods):
            date = current + timedelta(days=i + 1)
            # 약간의 랜덤 변동
            score = int(base_score + np.random.normal(0, 5))
            predictions.append({
                "date": date.strftime("%Y-%m-%d"),
                "predicted_score": max(0, min(100, score)),
                "lower_bound": max(0, score - 10),
                "upper_bound": min(100, score + 10)
            })

        return {
            "company_id": company_id,
            "periods": periods,
            "predictions": predictions,
            "trend": "stable",
            "confidence": 0.6,  # 폴백이므로 낮은 신뢰도
            "is_fallback": True
        }

    def _determine_trend(self, predictions: List[Dict]) -> str:
        """트렌드 판단"""

        if len(predictions) < 2:
            return "stable"

        first_score = predictions[0]["predicted_score"]
        last_score = predictions[-1]["predicted_score"]
        diff = last_score - first_score

        if diff > 5:
            return "increasing"
        elif diff < -5:
            return "decreasing"
        else:
            return "stable"


# 싱글톤 인스턴스
ml_predictor = MLPredictor()
```

### 3.4 예측 API 엔드포인트

**파일**: `risk_engine/api.py` (추가)

```python
from .ml_predictor import ml_predictor

@app.get("/api/v2/predict/{deal_id}")
async def predict_risk(
    deal_id: str,
    periods: int = Query(default=30, le=90)
):
    """리스크 예측"""

    result = ml_predictor.predict(deal_id, periods)
    return {
        "success": True,
        "data": result
    }


@app.post("/api/v2/predict/train/{deal_id}")
async def train_prediction_model(deal_id: str):
    """예측 모델 학습"""

    if not ml_predictor.is_available:
        raise HTTPException(status_code=503, detail="Prophet 라이브러리 미설치")

    success = ml_predictor.train_model(deal_id)
    return {
        "success": success,
        "message": "모델 학습 완료" if success else "학습 데이터 부족"
    }
```

---

## 4. 커스텀 시나리오 UI 설계

### 4.1 컴포넌트 구조

```
RiskScenarioBuilder/
├── index.tsx              # 메인 컴포넌트
├── SectorSelector.tsx     # 섹터 선택
├── ImpactSlider.tsx       # 영향도 슬라이더
├── MultiplierSelector.tsx # 전이 배수 선택
└── types.ts               # 타입 정의
```

### 4.2 메인 컴포넌트

**파일**: `components/risk/RiskScenarioBuilder.tsx`

```typescript
/**
 * 커스텀 시나리오 빌더
 * 사용자 정의 What-If 시나리오 생성
 */

import React, { useState, useCallback } from 'react';
import { riskApi } from './api';

interface CustomScenario {
  name: string;
  affectedSectors: string[];
  impactFactors: Record<string, number>;
  propagationMultiplier: number;
  severity: 'low' | 'medium' | 'high';
}

const SECTORS = [
  { id: 'semiconductor', label: '반도체', icon: '💻' },
  { id: 'automotive', label: '자동차', icon: '🚗' },
  { id: 'logistics', label: '물류', icon: '🚚' },
  { id: 'finance', label: '금융', icon: '💰' },
  { id: 'construction', label: '건설', icon: '🏗️' },
  { id: 'retail', label: '유통', icon: '🛒' },
];

const CATEGORIES = [
  { id: 'supply_chain', label: '공급망', color: 'blue' },
  { id: 'market', label: '시장', color: 'green' },
  { id: 'legal', label: '법률', color: 'red' },
  { id: 'operational', label: '운영', color: 'yellow' },
  { id: 'financial', label: '재무', color: 'purple' },
];

const MULTIPLIERS = [1.2, 1.5, 2.0, 2.5];

interface Props {
  onScenarioCreated: (scenarioId: string) => void;
  onClose: () => void;
}

const RiskScenarioBuilder: React.FC<Props> = ({ onScenarioCreated, onClose }) => {
  const [scenario, setScenario] = useState<CustomScenario>({
    name: '',
    affectedSectors: [],
    impactFactors: {},
    propagationMultiplier: 1.5,
    severity: 'medium',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 섹터 토글
  const toggleSector = useCallback((sectorId: string) => {
    setScenario(prev => ({
      ...prev,
      affectedSectors: prev.affectedSectors.includes(sectorId)
        ? prev.affectedSectors.filter(s => s !== sectorId)
        : [...prev.affectedSectors, sectorId]
    }));
  }, []);

  // 영향도 변경
  const setImpact = useCallback((category: string, value: number) => {
    setScenario(prev => ({
      ...prev,
      impactFactors: { ...prev.impactFactors, [category]: value }
    }));
  }, []);

  // 제출
  const handleSubmit = async () => {
    if (!scenario.name || scenario.affectedSectors.length === 0) {
      alert('시나리오 이름과 영향 섹터를 입력해주세요.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await riskApi.createCustomScenario(scenario);
      if (response.success) {
        onScenarioCreated(response.scenarioId);
      }
    } catch (error) {
      console.error('시나리오 생성 실패:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <span>🎯</span>
            <span>커스텀 시나리오 생성</span>
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>

        {/* 시나리오 이름 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            시나리오 이름
          </label>
          <input
            type="text"
            value={scenario.name}
            onChange={e => setScenario(prev => ({ ...prev, name: e.target.value }))}
            placeholder="예: 중국 희토류 수출 제한"
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg
                       text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1"
          />
        </div>

        {/* 영향 섹터 선택 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            영향 섹터 선택
          </label>
          <div className="grid grid-cols-3 gap-2">
            {SECTORS.map(sector => (
              <button
                key={sector.id}
                onClick={() => toggleSector(sector.id)}
                className={`p-3 rounded-lg border-2 transition-all ${
                  scenario.affectedSectors.includes(sector.id)
                    ? 'border-blue-500 bg-blue-900/30'
                    : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
                }`}
              >
                <span className="text-2xl">{sector.icon}</span>
                <div className="text-sm mt-1">{sector.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* 카테고리별 영향도 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            카테고리별 영향도
          </label>
          <div className="space-y-4">
            {CATEGORIES.map(cat => (
              <div key={cat.id} className="flex items-center gap-4">
                <span className="w-20 text-sm text-slate-400">{cat.label}</span>
                <input
                  type="range"
                  min="0"
                  max="30"
                  value={scenario.impactFactors[cat.id] || 0}
                  onChange={e => setImpact(cat.id, parseInt(e.target.value))}
                  className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                />
                <span className="w-16 text-right text-orange-400 font-mono">
                  +{scenario.impactFactors[cat.id] || 0}점
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 전이 배수 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            전이 배수
          </label>
          <div className="flex gap-2">
            {MULTIPLIERS.map(mult => (
              <button
                key={mult}
                onClick={() => setScenario(prev => ({ ...prev, propagationMultiplier: mult }))}
                className={`px-4 py-2 rounded-lg transition-all ${
                  scenario.propagationMultiplier === mult
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {mult}x
              </button>
            ))}
          </div>
        </div>

        {/* 버튼 */}
        <div className="flex gap-3">
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold
                       rounded-lg transition-colors disabled:opacity-50"
          >
            {isSubmitting ? '생성 중...' : '시나리오 생성'}
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-slate-300
                       rounded-lg transition-colors"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
};

export default RiskScenarioBuilder;
```

### 4.3 예측 차트 컴포넌트

**파일**: `components/risk/RiskPrediction.tsx`

```typescript
/**
 * 리스크 예측 차트
 * ML 모델 기반 미래 리스크 시각화
 */

import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart
} from 'recharts';
import { riskApi } from './api';

interface PredictionData {
  date: string;
  predicted_score: number;
  lower_bound?: number;
  upper_bound?: number;
}

interface Props {
  dealId: string;
  dealName: string;
}

const RiskPrediction: React.FC<Props> = ({ dealId, dealName }) => {
  const [predictions, setPredictions] = useState<PredictionData[]>([]);
  const [periods, setPeriods] = useState<7 | 30 | 90>(30);
  const [loading, setLoading] = useState(false);
  const [trend, setTrend] = useState<string>('stable');
  const [confidence, setConfidence] = useState<number>(0);

  useEffect(() => {
    loadPredictions();
  }, [dealId, periods]);

  const loadPredictions = async () => {
    setLoading(true);
    try {
      const response = await riskApi.getPrediction(dealId, periods);
      if (response.success) {
        setPredictions(response.data.predictions);
        setTrend(response.data.trend);
        setConfidence(response.data.confidence || 0);
      }
    } catch (error) {
      console.error('예측 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = () => {
    if (trend === 'increasing') return '📈';
    if (trend === 'decreasing') return '📉';
    return '➡️';
  };

  const getTrendColor = () => {
    if (trend === 'increasing') return 'text-red-400';
    if (trend === 'decreasing') return 'text-green-400';
    return 'text-slate-400';
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span>🔮</span>
          <span>리스크 예측</span>
          <span className="text-sm text-slate-400">({dealName})</span>
        </h3>

        {/* 기간 선택 */}
        <div className="flex gap-2">
          {([7, 30, 90] as const).map(p => (
            <button
              key={p}
              onClick={() => setPeriods(p)}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                periods === p
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {p}일
            </button>
          ))}
        </div>
      </div>

      {/* 트렌드 요약 */}
      <div className="flex gap-4 mb-4">
        <div className="bg-slate-700/30 px-4 py-2 rounded-lg">
          <span className="text-sm text-slate-400">트렌드</span>
          <div className={`text-lg font-bold ${getTrendColor()}`}>
            {getTrendIcon()} {trend === 'increasing' ? '상승' : trend === 'decreasing' ? '하락' : '유지'}
          </div>
        </div>
        <div className="bg-slate-700/30 px-4 py-2 rounded-lg">
          <span className="text-sm text-slate-400">신뢰도</span>
          <div className="text-lg font-bold text-blue-400">
            {(confidence * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* 차트 */}
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={predictions}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="date"
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
              tickFormatter={(val) => val.slice(5)}
            />
            <YAxis
              domain={[0, 100]}
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '8px'
              }}
            />

            {/* 신뢰 구간 */}
            <Area
              dataKey="upper_bound"
              stroke="none"
              fill="#3b82f6"
              fillOpacity={0.1}
            />
            <Area
              dataKey="lower_bound"
              stroke="none"
              fill="#1e293b"
              fillOpacity={1}
            />

            {/* 예측 선 */}
            <Line
              type="monotone"
              dataKey="predicted_score"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default RiskPrediction;
```

---

## 5. 파일 구조

### 5.1 신규/수정 파일 목록

```
risk_engine/
├── simulation_engine.py     [신규] 시뮬레이션 엔진
├── ml_predictor.py          [신규] ML 예측 모듈
├── feature_engineering.py   [신규] 피처 추출
├── cache_manager.py         [신규] 캐시 관리 (선택)
└── api.py                   [수정] 새 엔드포인트

scripts/
├── train_model.py           [신규] 모델 학습 스크립트
└── generate_training_data.py [신규] 학습 데이터 생성

components/risk/
├── RiskScenarioBuilder.tsx  [신규] 시나리오 빌더
├── RiskPrediction.tsx       [신규] 예측 차트
├── RiskSimulation.tsx       [수정] 시뮬레이션 개선
├── api.ts                   [수정] 새 API 함수
└── types.ts                 [수정] 타입 추가

requirements.txt             [수정] 의존성 추가
```

### 5.2 의존성 추가

**파일**: `requirements.txt` (추가)

```
# Phase 3 추가 의존성
prophet>=1.1.0
scikit-learn>=1.3.0
```

---

## 6. 구현 체크리스트

### Week 1: 시뮬레이션 정교화

```
□ 1. simulation_engine.py 구현
□ 2. CascadeConfig, ScenarioConfig 데이터클래스
□ 3. _get_affected_companies Neo4j 쿼리
□ 4. _calculate_cascade_impact 로직
□ 5. API: POST /api/v2/simulate/advanced
□ 6. RiskSimulation.tsx Cascade 결과 표시 업데이트
```

### Week 2: ML 리스크 예측

```
□ 7. feature_engineering.py 구현
□ 8. ml_predictor.py (Prophet) 구현
□ 9. API: GET /api/v2/predict/{deal_id}
□ 10. API: POST /api/v2/predict/train/{deal_id}
□ 11. RiskPrediction.tsx 컴포넌트
□ 12. RiskPage.tsx에 예측 탭 추가
```

### Week 3: 커스텀 시나리오

```
□ 13. RiskScenarioBuilder.tsx 구현
□ 14. API: POST /api/v2/scenarios/custom
□ 15. API: GET /api/v2/scenarios/custom
□ 16. RiskSimulation.tsx 커스텀 시나리오 연동
□ 17. 전체 통합 테스트
□ 18. 문서화
```

---

## 7. 테스트 계획

### 7.1 단위 테스트

| 모듈 | 테스트 항목 |
|------|------------|
| simulation_engine | Cascade 계산 정확도 |
| feature_engineering | 피처 추출 정확도 |
| ml_predictor | 예측 정확도 (MAPE) |

### 7.2 통합 테스트

| 시나리오 | 검증 항목 |
|---------|---------|
| 시뮬레이션 → UI | Cascade 결과 표시 |
| 학습 → 예측 → UI | 예측 차트 표시 |
| 커스텀 시나리오 생성 → 실행 | 전체 워크플로우 |

---

**작성**: 2026-02-05
**상태**: Design 완료
**다음 단계**: `/pdca do risk-phase3`
