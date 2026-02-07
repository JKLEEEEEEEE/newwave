"""
ML 예측 및 피처 엔지니어링 테스트
Risk Monitoring System - Phase 3
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_engine.feature_engineering import FeatureEngineer
from risk_engine.ml_predictor import RiskPredictor


class TestFeatureEngineer:
    """FeatureEngineer 테스트"""

    @pytest.fixture
    def engineer(self):
        """테스트용 피처 엔지니어 인스턴스"""
        return FeatureEngineer()

    def test_initialization(self, engineer):
        """초기화 검증"""
        assert engineer is not None

    def test_extract_features_returns_dict(self, engineer):
        """피처 추출이 딕셔너리 반환"""
        features = engineer.extract_features("deal_001", days=30)
        assert isinstance(features, dict)

    def test_feature_keys(self, engineer):
        """필수 피처 키 존재"""
        features = engineer.extract_features("deal_001", days=30)
        expected_keys = [
            "risk_history",
            "ma7",
            "ma30",
            "volatility",
            "trend"
        ]
        for key in expected_keys:
            assert key in features, f"Missing feature: {key}"

    def test_risk_history_structure(self, engineer):
        """risk_history 구조 검증"""
        features = engineer.extract_features("deal_001", days=30)
        history = features.get("risk_history", [])
        assert isinstance(history, list)
        if history:
            assert "date" in history[0]
            assert "score" in history[0]

    def test_ma7_calculation(self, engineer):
        """7일 이동평균 계산"""
        features = engineer.extract_features("deal_001", days=30)
        ma7 = features.get("ma7")
        assert ma7 is not None
        assert isinstance(ma7, (int, float))

    def test_ma30_calculation(self, engineer):
        """30일 이동평균 계산"""
        features = engineer.extract_features("deal_001", days=60)
        ma30 = features.get("ma30")
        assert ma30 is not None
        assert isinstance(ma30, (int, float))

    def test_volatility_non_negative(self, engineer):
        """변동성이 음수가 아님"""
        features = engineer.extract_features("deal_001", days=30)
        volatility = features.get("volatility", 0)
        assert volatility >= 0

    def test_trend_values(self, engineer):
        """트렌드 값이 유효"""
        features = engineer.extract_features("deal_001", days=30)
        trend = features.get("trend")
        assert trend in ["up", "down", "stable", None] or isinstance(trend, (int, float))


class TestRiskPredictor:
    """RiskPredictor 테스트"""

    @pytest.fixture
    def predictor(self):
        """테스트용 예측기 인스턴스"""
        return RiskPredictor()

    def test_initialization(self, predictor):
        """초기화 검증"""
        assert predictor is not None

    def test_predict_returns_dict(self, predictor):
        """예측 결과가 딕셔너리 반환"""
        result = predictor.predict("deal_001", periods=7)
        assert isinstance(result, dict)

    def test_prediction_keys(self, predictor):
        """예측 결과 필수 키 존재"""
        result = predictor.predict("deal_001", periods=7)
        expected_keys = ["predictions", "model_type", "deal_id"]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_predictions_structure(self, predictor):
        """predictions 배열 구조"""
        result = predictor.predict("deal_001", periods=7)
        predictions = result.get("predictions", [])
        assert isinstance(predictions, list)
        assert len(predictions) == 7

    def test_prediction_item_structure(self, predictor):
        """개별 예측 항목 구조"""
        result = predictor.predict("deal_001", periods=7)
        predictions = result.get("predictions", [])
        if predictions:
            pred = predictions[0]
            assert "date" in pred
            assert "predicted_score" in pred
            assert "lower_bound" in pred
            assert "upper_bound" in pred

    def test_confidence_interval(self, predictor):
        """신뢰구간 검증 (lower <= predicted <= upper)"""
        result = predictor.predict("deal_001", periods=7)
        predictions = result.get("predictions", [])
        for pred in predictions:
            lower = pred.get("lower_bound", 0)
            predicted = pred.get("predicted_score", 0)
            upper = pred.get("upper_bound", 100)
            assert lower <= predicted <= upper

    def test_different_periods(self, predictor):
        """다양한 예측 기간"""
        for periods in [7, 30, 90]:
            result = predictor.predict("deal_001", periods=periods)
            predictions = result.get("predictions", [])
            assert len(predictions) == periods

    def test_score_bounds(self, predictor):
        """점수가 0-100 범위"""
        result = predictor.predict("deal_001", periods=30)
        predictions = result.get("predictions", [])
        for pred in predictions:
            score = pred.get("predicted_score", 0)
            assert 0 <= score <= 100


class TestModelTraining:
    """모델 학습 테스트"""

    @pytest.fixture
    def predictor(self):
        return RiskPredictor()

    def test_train_model(self, predictor):
        """모델 학습 실행"""
        result = predictor.train_model("deal_001", historical_days=60)
        assert result is not None

    def test_train_result_structure(self, predictor):
        """학습 결과 구조"""
        result = predictor.train_model("deal_001", historical_days=60)
        if result:
            assert "status" in result or "model_id" in result


class TestModelPersistence:
    """모델 저장/로드 테스트"""

    @pytest.fixture
    def predictor(self):
        return RiskPredictor()

    def test_model_save_path(self, predictor):
        """모델 저장 경로"""
        # models/ 디렉토리 존재 확인
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models"
        )
        assert os.path.exists(models_dir)


class TestFallbackMechanism:
    """폴백 메커니즘 테스트"""

    def test_predictor_without_prophet(self):
        """Prophet 없이 폴백 예측"""
        predictor = RiskPredictor()
        result = predictor.predict("deal_001", periods=7)
        # Prophet 없어도 결과 반환 (random walk fallback)
        assert result is not None
        assert "predictions" in result

    def test_feature_engineer_without_neo4j(self):
        """Neo4j 없이 폴백 피처"""
        engineer = FeatureEngineer()
        features = engineer.extract_features("deal_001", days=30)
        # Neo4j 없어도 mock 데이터로 피처 반환
        assert features is not None
        assert "risk_history" in features


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
