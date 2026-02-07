"""
ML 리스크 예측 모듈
Prophet 기반 시계열 예측
Risk Monitoring System - Phase 3
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import os
import pickle

logger = logging.getLogger(__name__)

# Prophet 임포트
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    Prophet = None
    logger.warning("Prophet 미설치. pip install prophet")

# Pandas/Numpy 임포트
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    np = None
    logger.warning("pandas/numpy 미설치")

# 피처 엔지니어링 임포트
try:
    from .feature_engineering import feature_engineer
    FEATURE_ENGINEER_AVAILABLE = True
except ImportError:
    FEATURE_ENGINEER_AVAILABLE = False
    feature_engineer = None
    logger.warning("feature_engineering 로드 실패")


class MLPredictor:
    """ML 리스크 예측기 (Prophet 기반)"""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.models: Dict[str, Any] = {}  # company_id -> Prophet model
        os.makedirs(model_dir, exist_ok=True)

    @property
    def is_available(self) -> bool:
        """ML 예측 사용 가능 여부"""
        return PROPHET_AVAILABLE and PANDAS_AVAILABLE

    def train_model(
        self,
        company_id: str,
        historical_days: int = 365,
        use_regressors: bool = True
    ) -> Dict[str, Any]:
        """
        모델 학습

        Args:
            company_id: 기업 ID
            historical_days: 학습 데이터 기간 (일)
            use_regressors: 추가 회귀 변수 사용 여부

        Returns:
            학습 결과 정보
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "Prophet 또는 pandas 미설치",
                "is_fallback": True
            }

        if not FEATURE_ENGINEER_AVAILABLE or not feature_engineer:
            return {
                "success": False,
                "error": "feature_engineering 모듈 로드 실패"
            }

        # 데이터 준비
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=historical_days)).strftime("%Y-%m-%d")

        logger.info(f"모델 학습 시작: {company_id} ({start_date} ~ {end_date})")

        df = feature_engineer.extract_features(company_id, start_date, end_date)

        if df is None or len(df) < 30:
            return {
                "success": False,
                "error": f"학습 데이터 부족: {len(df) if df is not None else 0}일 (최소 30일 필요)"
            }

        # Prophet 모델 생성
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=0.1,
            interval_width=0.95  # 95% 신뢰 구간
        )

        # 추가 회귀 변수 등록
        if use_regressors:
            model.add_regressor("news_sentiment", mode="additive")
            model.add_regressor("disclosure_count", mode="additive")

        # 학습 데이터 준비
        train_cols = ["ds", "y"]
        if use_regressors:
            train_cols.extend(["news_sentiment", "disclosure_count"])

        train_df = df[train_cols].copy()

        # 학습 실행
        try:
            model.fit(train_df)
        except Exception as e:
            logger.error(f"모델 학습 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

        # 모델 저장
        self.models[company_id] = model
        model_path = os.path.join(self.model_dir, f"{company_id}.pkl")

        try:
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
            logger.info(f"모델 저장: {model_path}")
        except Exception as e:
            logger.warning(f"모델 저장 실패: {e}")

        return {
            "success": True,
            "company_id": company_id,
            "training_days": len(df),
            "date_range": f"{start_date} ~ {end_date}",
            "model_path": model_path,
            "use_regressors": use_regressors
        }

    def predict(
        self,
        company_id: str,
        periods: int = 30,
        include_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        리스크 예측

        Args:
            company_id: 기업 ID
            periods: 예측 기간 (일)
            include_confidence: 신뢰 구간 포함 여부

        Returns:
            예측 결과
        """
        # 모델 로드
        model = self._load_model(company_id)

        if model is None:
            logger.info(f"모델 없음, 폴백 예측 사용: {company_id}")
            return self._fallback_prediction(company_id, periods, include_confidence)

        # 미래 데이터프레임 생성
        future = model.make_future_dataframe(periods=periods)

        # 회귀 변수 기본값 설정
        if "news_sentiment" in model.extra_regressors:
            future["news_sentiment"] = 0.0
        if "disclosure_count" in model.extra_regressors:
            future["disclosure_count"] = 1

        # 예측 실행
        try:
            forecast = model.predict(future)
        except Exception as e:
            logger.error(f"예측 실패: {e}")
            return self._fallback_prediction(company_id, periods, include_confidence)

        # 결과 포맷팅
        predictions = []
        for _, row in forecast.tail(periods).iterrows():
            pred = {
                "date": row["ds"].strftime("%Y-%m-%d"),
                "predicted_score": self._clamp_score(row["yhat"]),
            }
            if include_confidence:
                pred["lower_bound"] = self._clamp_score(row["yhat_lower"])
                pred["upper_bound"] = self._clamp_score(row["yhat_upper"])

            predictions.append(pred)

        # 트렌드 분석
        trend = self._determine_trend(predictions)

        return {
            "company_id": company_id,
            "periods": periods,
            "predictions": predictions,
            "trend": trend,
            "confidence": 0.95 if include_confidence else None,
            "is_fallback": False,
            "model_type": "prophet"
        }

    def _load_model(self, company_id: str) -> Optional[Any]:
        """모델 로드 (메모리 캐시 → 파일)"""
        # 메모리 캐시 확인
        if company_id in self.models:
            return self.models[company_id]

        # 파일에서 로드
        model_path = os.path.join(self.model_dir, f"{company_id}.pkl")
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                    self.models[company_id] = model
                    logger.info(f"모델 로드: {model_path}")
                    return model
            except Exception as e:
                logger.warning(f"모델 로드 실패: {e}")

        return None

    def _fallback_prediction(
        self,
        company_id: str,
        periods: int,
        include_confidence: bool
    ) -> Dict[str, Any]:
        """
        폴백 예측 (Prophet 없을 때)

        이동 평균 + 랜덤 변동 기반 간단 예측
        """
        if not PANDAS_AVAILABLE:
            # 최소한의 폴백
            base_score = 50
            predictions = [
                {
                    "date": (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                    "predicted_score": base_score,
                    "lower_bound": max(0, base_score - 10),
                    "upper_bound": min(100, base_score + 10)
                }
                for i in range(periods)
            ]
            return {
                "company_id": company_id,
                "periods": periods,
                "predictions": predictions,
                "trend": "stable",
                "confidence": 0.5,
                "is_fallback": True,
                "model_type": "simple"
            }

        # 최근 데이터 기반 예측
        base_score = 50

        # 피처 엔지니어링에서 최근 점수 가져오기 시도
        if FEATURE_ENGINEER_AVAILABLE and feature_engineer:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            try:
                df = feature_engineer.extract_features(company_id, start_date, end_date)
                if df is not None and len(df) > 0:
                    base_score = df["y"].iloc[-1]
            except Exception:
                pass

        # 랜덤 워크 예측
        np.random.seed(hash(company_id) % 2**32)
        predictions = []
        current_score = float(base_score)

        for i in range(periods):
            # 평균 회귀 + 랜덤 변동
            drift = (50 - current_score) * 0.02
            shock = np.random.normal(0, 2)
            current_score = max(20, min(80, current_score + drift + shock))

            date = datetime.now() + timedelta(days=i + 1)
            pred = {
                "date": date.strftime("%Y-%m-%d"),
                "predicted_score": int(round(current_score)),
            }
            if include_confidence:
                pred["lower_bound"] = max(0, int(current_score - 10))
                pred["upper_bound"] = min(100, int(current_score + 10))

            predictions.append(pred)

        return {
            "company_id": company_id,
            "periods": periods,
            "predictions": predictions,
            "trend": self._determine_trend(predictions),
            "confidence": 0.6,  # 폴백이므로 낮은 신뢰도
            "is_fallback": True,
            "model_type": "random_walk"
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

    def _clamp_score(self, value: float) -> int:
        """점수 범위 제한 (0-100)"""
        return max(0, min(100, int(round(value))))

    def get_model_info(self, company_id: str) -> Optional[Dict[str, Any]]:
        """모델 정보 조회"""
        model_path = os.path.join(self.model_dir, f"{company_id}.pkl")

        if not os.path.exists(model_path):
            return None

        stat = os.stat(model_path)
        return {
            "company_id": company_id,
            "model_path": model_path,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_loaded": company_id in self.models
        }

    def list_models(self) -> List[Dict[str, Any]]:
        """저장된 모델 목록"""
        models = []

        if not os.path.exists(self.model_dir):
            return models

        for filename in os.listdir(self.model_dir):
            if filename.endswith(".pkl"):
                company_id = filename[:-4]
                info = self.get_model_info(company_id)
                if info:
                    models.append(info)

        return models

    def delete_model(self, company_id: str) -> bool:
        """모델 삭제"""
        # 메모리에서 제거
        if company_id in self.models:
            del self.models[company_id]

        # 파일 삭제
        model_path = os.path.join(self.model_dir, f"{company_id}.pkl")
        if os.path.exists(model_path):
            try:
                os.remove(model_path)
                logger.info(f"모델 삭제: {model_path}")
                return True
            except Exception as e:
                logger.error(f"모델 삭제 실패: {e}")
                return False

        return False


# 싱글톤 인스턴스
ml_predictor = MLPredictor()


# ========================================
# 테스트 실행
# ========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("ML 예측기 테스트")
    print("=" * 60)

    print(f"\n🔧 Prophet 사용 가능: {'✅' if PROPHET_AVAILABLE else '❌'}")
    print(f"🔧 Pandas 사용 가능: {'✅' if PANDAS_AVAILABLE else '❌'}")
    print(f"🔧 ML 예측 사용 가능: {'✅' if ml_predictor.is_available else '❌'}")

    # 폴백 예측 테스트 (Prophet 없어도 동작)
    print("\n📊 폴백 예측 테스트 (sk_hynix, 30일):")
    result = ml_predictor.predict("sk_hynix", periods=30)

    print(f"   모델 타입: {result['model_type']}")
    print(f"   트렌드: {result['trend']}")
    print(f"   신뢰도: {result['confidence']}")
    print(f"   폴백: {result['is_fallback']}")
    print(f"\n   예측 샘플 (처음 5일):")
    for p in result["predictions"][:5]:
        bounds = f"[{p.get('lower_bound', '-')} - {p.get('upper_bound', '-')}]" if 'lower_bound' in p else ""
        print(f"     {p['date']}: {p['predicted_score']}점 {bounds}")

    # Prophet 사용 가능 시 학습 테스트
    if ml_predictor.is_available:
        print("\n📚 모델 학습 테스트:")
        train_result = ml_predictor.train_model("sk_hynix", historical_days=90)
        print(f"   결과: {train_result}")

        if train_result.get("success"):
            print("\n📊 Prophet 예측 테스트:")
            result = ml_predictor.predict("sk_hynix", periods=30)
            print(f"   모델 타입: {result['model_type']}")
            print(f"   트렌드: {result['trend']}")

    # 모델 목록
    print("\n📁 저장된 모델:")
    for m in ml_predictor.list_models():
        print(f"   - {m['company_id']}: {m['size_bytes']} bytes")
