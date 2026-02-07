"""
피처 엔지니어링 모듈
Neo4j 데이터 → ML 학습용 피처 변환
Risk Monitoring System - Phase 3
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Pandas/Numpy 임포트
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    np = None
    logger.warning("pandas/numpy 미설치. pip install pandas numpy")

# Neo4j 클라이언트 임포트
try:
    from .neo4j_client import neo4j_client
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    neo4j_client = None
    logger.warning("neo4j_client 로드 실패")


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

    @property
    def is_available(self) -> bool:
        """피처 엔지니어링 사용 가능 여부"""
        return PANDAS_AVAILABLE

    def extract_features(
        self,
        company_id: str,
        start_date: str,
        end_date: str
    ) -> Optional['pd.DataFrame']:
        """
        기업별 피처 추출

        Args:
            company_id: 기업 ID (corpCode)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            Prophet 학습용 DataFrame (ds, y, 추가 피처)
        """
        if not PANDAS_AVAILABLE:
            logger.error("pandas 미설치")
            return None

        # 1. 일별 리스크 점수 이력 조회
        risk_history = self._get_risk_history(company_id, start_date, end_date)

        # 2. 뉴스 감성 지표
        news_sentiment = self._get_news_sentiment(company_id, start_date, end_date)

        # 3. 공시 빈도
        disclosure_counts = self._get_disclosure_counts(company_id, start_date, end_date)

        # 4. 공급망 리스크 (정적 값)
        supply_chain_risk = self._get_supply_chain_risk(company_id)

        # 데이터 병합
        df = pd.DataFrame(risk_history)

        if df.empty:
            logger.warning(f"리스크 이력 데이터 없음: {company_id}")
            return None

        # Prophet 필수 컬럼
        df["ds"] = pd.to_datetime(df["date"])
        df["y"] = df["risk_score"]

        # 추가 피처
        df["news_sentiment"] = df["ds"].apply(
            lambda d: news_sentiment.get(d.strftime("%Y-%m-%d"), 0.0)
        )
        df["disclosure_count"] = df["ds"].apply(
            lambda d: disclosure_counts.get(d.strftime("%Y-%m-%d"), 0)
        )
        df["supply_chain_risk"] = supply_chain_risk
        df["day_of_week"] = df["ds"].dt.dayofweek
        df["month"] = df["ds"].dt.month

        # 이동 평균 피처
        df["risk_ma7"] = df["y"].rolling(window=7, min_periods=1).mean()
        df["risk_ma30"] = df["y"].rolling(window=30, min_periods=1).mean()

        # 변동성 피처
        df["risk_std7"] = df["y"].rolling(window=7, min_periods=1).std().fillna(0)

        return df

    def _get_risk_history(
        self,
        company_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """리스크 점수 이력 조회"""

        if not NEO4J_AVAILABLE or not neo4j_client:
            return self._generate_mock_history(start_date, end_date)

        query = """
        MATCH (c:Company {corpCode: $companyId})-[:HAS_RISK_HISTORY]->(h:RiskHistory)
        WHERE h.date >= date($startDate) AND h.date <= date($endDate)
        RETURN toString(h.date) AS date, h.score AS risk_score
        ORDER BY h.date
        """

        try:
            neo4j_client.connect()
            results = neo4j_client.execute_read(query, {
                "companyId": company_id,
                "startDate": start_date,
                "endDate": end_date
            })

            if results:
                return results
            else:
                logger.info(f"리스크 이력 없음, Mock 데이터 생성: {company_id}")
                return self._generate_mock_history(start_date, end_date)

        except Exception as e:
            logger.error(f"리스크 이력 조회 실패: {e}")
            return self._generate_mock_history(start_date, end_date)

    def _get_news_sentiment(
        self,
        company_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, float]:
        """
        뉴스 감성 지표 조회

        Returns:
            날짜 → 감성 점수 (-1 ~ 1)
        """
        if not NEO4J_AVAILABLE or not neo4j_client:
            return {}

        query = """
        MATCH (n:NewsArticle)-[:MENTIONS]->(c:Company {corpCode: $companyId})
        WHERE n.publishedAt >= datetime($startDate) AND n.publishedAt <= datetime($endDate)
        WITH date(n.publishedAt) AS newsDate, n.sentiment AS sentiment
        RETURN toString(newsDate) AS date,
               avg(CASE sentiment
                   WHEN '긍정' THEN 1.0
                   WHEN 'positive' THEN 1.0
                   WHEN '중립' THEN 0.0
                   WHEN 'neutral' THEN 0.0
                   WHEN '부정' THEN -1.0
                   WHEN 'negative' THEN -1.0
                   ELSE 0.0
               END) AS sentiment
        """

        try:
            results = neo4j_client.execute_read(query, {
                "companyId": company_id,
                "startDate": f"{start_date}T00:00:00",
                "endDate": f"{end_date}T23:59:59"
            })
            return {r["date"]: r["sentiment"] for r in results if r.get("date")}
        except Exception as e:
            logger.warning(f"뉴스 감성 조회 실패: {e}")
            return {}

    def _get_disclosure_counts(
        self,
        company_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, int]:
        """
        공시 빈도 조회

        Returns:
            날짜 → 공시 건수
        """
        if not NEO4J_AVAILABLE or not neo4j_client:
            return {}

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
            return {r["date"]: r["count"] for r in results if r.get("date")}
        except Exception as e:
            logger.warning(f"공시 빈도 조회 실패: {e}")
            return {}

    def _get_supply_chain_risk(self, company_id: str) -> float:
        """
        공급망 리스크 조회

        공급사들의 평균 리스크 점수
        """
        if not NEO4J_AVAILABLE or not neo4j_client:
            return 50.0

        query = """
        MATCH (c:Company {corpCode: $companyId})<-[:SUPPLIES_TO]-(s:Company)
        RETURN avg(s.totalRiskScore) AS avgSupplierRisk
        """

        try:
            result = neo4j_client.execute_read_single(query, {"companyId": company_id})
            return result.get("avgSupplierRisk", 50.0) if result else 50.0
        except Exception as e:
            logger.warning(f"공급망 리스크 조회 실패: {e}")
            return 50.0

    def _generate_mock_history(
        self,
        start_date: str,
        end_date: str,
        base_score: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Mock 이력 데이터 생성

        랜덤 워크 시뮬레이션으로 현실적인 점수 변동 생성
        """
        if not PANDAS_AVAILABLE:
            return []

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        history = []
        current = start
        score = float(base_score)

        # 시드 설정 (재현 가능성)
        np.random.seed(hash(start_date) % 2**32)

        while current <= end:
            # 랜덤 워크 + 평균 회귀
            drift = (50 - score) * 0.01  # 평균 회귀 (50점으로)
            shock = np.random.normal(0, 3)  # 일일 변동
            score = max(20, min(80, score + drift + shock))

            # 주말 효과 (변동 작음)
            if current.weekday() >= 5:
                score = max(20, min(80, score + np.random.normal(0, 1)))

            history.append({
                "date": current.strftime("%Y-%m-%d"),
                "risk_score": int(round(score))
            })
            current += timedelta(days=1)

        return history

    def get_feature_importance(self, model_weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        피처 중요도 반환 (모델 가중치 또는 기본값)
        """
        default_importance = {
            "risk_score": 0.25,
            "risk_ma7": 0.15,
            "risk_ma30": 0.10,
            "news_sentiment": 0.15,
            "disclosure_count": 0.10,
            "supply_chain_risk": 0.15,
            "risk_std7": 0.10
        }

        weights = model_weights or default_importance

        return [
            {"feature": k, "importance": v}
            for k, v in sorted(weights.items(), key=lambda x: x[1], reverse=True)
        ]


# 싱글톤 인스턴스
feature_engineer = FeatureEngineer()


# ========================================
# 테스트 실행
# ========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("피처 엔지니어링 테스트")
    print("=" * 60)

    if not PANDAS_AVAILABLE:
        print("❌ pandas/numpy 미설치")
        exit(1)

    # 테스트 기간
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    print(f"\n📅 기간: {start_date} ~ {end_date}")

    # 피처 추출 테스트
    df = feature_engineer.extract_features("sk_hynix", start_date, end_date)

    if df is not None:
        print(f"\n📊 추출된 피처 (총 {len(df)}일):")
        print(df.head(10).to_string())

        print(f"\n📈 피처 통계:")
        print(df[["y", "news_sentiment", "disclosure_count", "supply_chain_risk", "risk_ma7"]].describe())

        print(f"\n🎯 피처 중요도:")
        for fi in feature_engineer.get_feature_importance():
            print(f"   - {fi['feature']}: {fi['importance']:.2%}")
    else:
        print("❌ 피처 추출 실패")
