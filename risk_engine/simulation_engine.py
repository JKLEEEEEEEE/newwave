"""
시뮬레이션 엔진 v2.3
Cascade 효과 기반 동적 리스크 계산
Risk Monitoring System - Phase 3
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from functools import lru_cache
import logging
import hashlib

logger = logging.getLogger(__name__)

# Neo4j 클라이언트 임포트
try:
    from .neo4j_client import neo4j_client
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    neo4j_client = None
    logger.warning("neo4j_client 로드 실패")

# AI 서비스 v2 임포트
try:
    from .ai_service_v2 import ai_service_v2
    AI_AVAILABLE = ai_service_v2.is_available if ai_service_v2 else False
except ImportError:
    AI_AVAILABLE = False
    ai_service_v2 = None
    logger.warning("ai_service_v2 로드 실패")


@dataclass
class CascadeConfig:
    """Cascade 효과 설정"""
    tier1_multiplier: float = 0.8  # 1차 영향 (직접 공급사)
    tier2_multiplier: float = 0.5  # 2차 영향
    tier3_multiplier: float = 0.2  # 3차 영향
    max_depth: int = 3             # 최대 탐색 깊이
    base_propagation_rate: float = 0.1  # 기본 전이율


@dataclass
class ScenarioConfig:
    """시나리오 설정"""
    id: str
    name: str
    affected_sectors: List[str]
    impact_factors: Dict[str, int]  # category -> impact points
    propagation_multiplier: float = 1.5
    severity: str = "medium"  # low, medium, high
    description: str = ""
    is_custom: bool = False


@dataclass
class SimulationResult:
    """시뮬레이션 결과"""
    deal_id: str
    deal_name: str
    original_score: int
    simulated_score: int
    delta: int
    affected_categories: List[Dict[str, Any]] = field(default_factory=list)
    cascade_path: List[str] = field(default_factory=list)
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
        """
        시뮬레이션 실행

        Args:
            scenario: 시나리오 설정
            target_deal_ids: 특정 대상 기업 ID 목록 (None이면 전체)

        Returns:
            시뮬레이션 결과 목록 (영향도 순 정렬)
        """
        logger.info(f"시뮬레이션 실행: {scenario.name}")

        # 1. 영향받는 기업 추출
        affected_companies = self._get_affected_companies(
            scenario.affected_sectors,
            target_deal_ids
        )

        if not affected_companies:
            logger.warning("영향받는 기업이 없습니다")
            return []

        # 2. Cascade 효과 계산
        results = []
        for company in affected_companies:
            result = self._calculate_cascade_impact(company, scenario)
            results.append(result)

        # 3. AI 해석 추가 (상위 5개만)
        if AI_AVAILABLE and ai_service_v2:
            results = self._add_ai_interpretation(results, scenario)

        # 4. 영향도 순 정렬
        return sorted(results, key=lambda r: r.delta, reverse=True)

    def _get_affected_companies(
        self,
        sectors: List[str],
        target_deal_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        영향받는 기업 추출 (Neo4j)

        1. 지정된 섹터에 속한 기업
        2. 해당 기업의 공급망 연결 기업 (3 depth까지)
        """
        if not NEO4J_AVAILABLE or not neo4j_client:
            logger.warning("Neo4j 미연결, Mock 데이터 반환")
            return self._get_mock_affected_companies(sectors, target_deal_ids)

        query = """
        MATCH (c:Company)
        WHERE c.sector IN $sectors
           OR c.corpCode IN $targetIds
           OR c.name IN $targetIds
        OPTIONAL MATCH (c)<-[:SUPPLIES_TO*1..3]-(supplier:Company)
        WHERE supplier.totalRiskScore > 50
        RETURN c.name AS name,
               c.corpCode AS corpCode,
               c.sector AS sector,
               c.totalRiskScore AS currentScore,
               collect(DISTINCT {
                   name: supplier.name,
                   score: supplier.totalRiskScore,
                   tier: CASE
                       WHEN exists((supplier)-[:SUPPLIES_TO]->(c)) THEN 1
                       WHEN exists((supplier)-[:SUPPLIES_TO*2]->(c)) THEN 2
                       ELSE 3
                   END
               }) AS suppliers
        """

        try:
            neo4j_client.connect()
            results = neo4j_client.execute_read(query, {
                "sectors": sectors,
                "targetIds": target_deal_ids or []
            })
            logger.info(f"영향 기업 {len(results)}개 조회됨")
            return results
        except Exception as e:
            logger.error(f"영향 기업 조회 실패: {e}")
            return self._get_mock_affected_companies(sectors, target_deal_ids)

    def _calculate_cascade_impact(
        self,
        company: Dict[str, Any],
        scenario: ScenarioConfig
    ) -> SimulationResult:
        """
        개별 기업 Cascade 영향 계산

        1. 직접 영향: 섹터 매칭 시 카테고리별 영향도 적용
        2. Cascade 영향: 공급망 전이 (Tier별 감쇠)
        """
        original_score = company.get("currentScore") or 50
        cascade_path = []
        total_delta = 0
        affected_categories = []

        # 1. 직접 영향 (섹터 매칭 시)
        company_sector = company.get("sector", "")
        if company_sector in scenario.affected_sectors:
            for category, impact in scenario.impact_factors.items():
                direct_impact = int(impact * scenario.propagation_multiplier)
                affected_categories.append({
                    "category": category,
                    "delta": direct_impact,
                    "source": "direct",
                    "description": f"{scenario.name}에 의한 직접 영향"
                })
                total_delta += direct_impact

        # 2. Cascade 영향 (공급망 전이)
        suppliers = company.get("suppliers", [])
        for supplier in suppliers:
            if not supplier or not supplier.get("name"):
                continue

            tier = supplier.get("tier", 1)
            supplier_score = supplier.get("score", 0)

            # Tier별 감쇠 계수
            multiplier = self._get_tier_multiplier(tier)

            # 전이 영향 계산
            cascade_impact = int(
                supplier_score *
                self.cascade_config.base_propagation_rate *
                multiplier *
                scenario.propagation_multiplier
            )

            if cascade_impact > 0:
                cascade_path.append(f"{supplier['name']} (Tier{tier}, +{cascade_impact}점)")
                total_delta += cascade_impact
                affected_categories.append({
                    "category": "supply_chain",
                    "delta": cascade_impact,
                    "source": supplier["name"],
                    "tier": tier,
                    "description": f"{supplier['name']}에서 전이된 리스크"
                })

        # 점수 상한 적용 (0-100)
        simulated_score = min(100, max(0, original_score + total_delta))

        return SimulationResult(
            deal_id=company.get("corpCode") or company.get("name", "").replace(" ", "_").lower(),
            deal_name=company.get("name", "Unknown"),
            original_score=original_score,
            simulated_score=simulated_score,
            delta=simulated_score - original_score,
            affected_categories=affected_categories,
            cascade_path=cascade_path
        )

    def _get_tier_multiplier(self, tier: int) -> float:
        """Tier별 감쇠 계수 반환"""
        if tier <= 1:
            return self.cascade_config.tier1_multiplier
        elif tier == 2:
            return self.cascade_config.tier2_multiplier
        else:
            return self.cascade_config.tier3_multiplier

    def _add_ai_interpretation(
        self,
        results: List[SimulationResult],
        scenario: ScenarioConfig
    ) -> List[SimulationResult]:
        """AI 기반 결과 해석 추가 (상위 5개)"""
        for result in results[:5]:
            try:
                interpretation = ai_service_v2.interpret_simulation({
                    "scenario": scenario.name,
                    "scenario_severity": scenario.severity,
                    "company": result.deal_name,
                    "original_score": result.original_score,
                    "simulated_score": result.simulated_score,
                    "delta": result.delta,
                    "categories": result.affected_categories,
                    "cascade_path": result.cascade_path
                })
                result.interpretation = interpretation.get("impact_summary", "")
            except Exception as e:
                logger.warning(f"AI 해석 실패 ({result.deal_name}): {e}")

        return results

    def get_cached_result(self, scenario_id: str, deal_ids: Optional[List[str]] = None) -> Optional[List[SimulationResult]]:
        """캐시된 결과 조회"""
        cache_key = self._make_cache_key(scenario_id, deal_ids)
        return self._cache.get(cache_key)

    def set_cached_result(self, scenario_id: str, deal_ids: Optional[List[str]], results: List[SimulationResult]):
        """결과 캐싱"""
        cache_key = self._make_cache_key(scenario_id, deal_ids)
        self._cache[cache_key] = results

    def _make_cache_key(self, scenario_id: str, deal_ids: Optional[List[str]]) -> str:
        """캐시 키 생성"""
        ids_str = ",".join(sorted(deal_ids)) if deal_ids else "all"
        return f"{scenario_id}:{hashlib.md5(ids_str.encode()).hexdigest()[:8]}"

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()

    # ========================================
    # Mock 데이터 (Neo4j 미연결 시)
    # ========================================
    def _get_mock_affected_companies(
        self,
        sectors: List[str],
        target_deal_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Mock 영향 기업 데이터"""
        mock_companies = [
            {
                "name": "SK하이닉스",
                "corpCode": "sk_hynix",
                "sector": "반도체",
                "currentScore": 68,
                "suppliers": [
                    {"name": "한미반도체", "score": 82, "tier": 1},
                    {"name": "원익IPS", "score": 55, "tier": 1},
                ]
            },
            {
                "name": "삼성전자",
                "corpCode": "samsung",
                "sector": "반도체",
                "currentScore": 35,
                "suppliers": [
                    {"name": "삼성SDI", "score": 45, "tier": 1},
                ]
            },
            {
                "name": "현대글로비스",
                "corpCode": "hyundai_glovis",
                "sector": "물류",
                "currentScore": 42,
                "suppliers": []
            },
            {
                "name": "한진",
                "corpCode": "hanjin",
                "sector": "물류",
                "currentScore": 58,
                "suppliers": []
            },
        ]

        # 섹터 필터링
        filtered = [
            c for c in mock_companies
            if c["sector"] in sectors or
               c["corpCode"] in (target_deal_ids or []) or
               c["name"] in (target_deal_ids or [])
        ]

        return filtered if filtered else mock_companies[:2]


# ========================================
# 프리셋 시나리오
# ========================================
PRESET_SCENARIOS: Dict[str, ScenarioConfig] = {
    "busan_port": ScenarioConfig(
        id="busan_port",
        name="부산항 파업",
        description="부산항 노조 파업으로 인한 물류 마비 시나리오",
        affected_sectors=["물류", "반도체", "자동차"],
        impact_factors={
            "supply_chain": 20,
            "operational": 15,
            "financial": 10
        },
        propagation_multiplier=1.5,
        severity="high"
    ),
    "memory_crash": ScenarioConfig(
        id="memory_crash",
        name="반도체 수요 급감",
        description="글로벌 메모리 수요 급감으로 인한 가격 하락",
        affected_sectors=["반도체", "반도체장비"],
        impact_factors={
            "market": 25,
            "financial": 20,
            "operational": 10
        },
        propagation_multiplier=1.3,
        severity="high"
    ),
    "china_rare_earth": ScenarioConfig(
        id="china_rare_earth",
        name="중국 희토류 수출 제한",
        description="중국의 희토류 수출 규제 강화",
        affected_sectors=["반도체", "배터리", "자동차"],
        impact_factors={
            "supply_chain": 30,
            "operational": 15,
            "market": 10
        },
        propagation_multiplier=2.0,
        severity="high"
    ),
    "interest_rate_hike": ScenarioConfig(
        id="interest_rate_hike",
        name="금리 인상",
        description="미국 연준 금리 인상 시나리오",
        affected_sectors=["금융", "부동산", "건설"],
        impact_factors={
            "financial": 15,
            "market": 10
        },
        propagation_multiplier=1.2,
        severity="medium"
    ),
}


def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioConfig]:
    """ID로 시나리오 조회"""
    return PRESET_SCENARIOS.get(scenario_id)


def get_all_scenarios() -> List[Dict[str, Any]]:
    """모든 프리셋 시나리오 목록"""
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "affectedSectors": s.affected_sectors,
            "impactFactors": s.impact_factors,
            "propagationMultiplier": s.propagation_multiplier,
            "severity": s.severity,
            "isCustom": s.is_custom
        }
        for s in PRESET_SCENARIOS.values()
    ]


# 싱글톤 인스턴스
simulation_engine = SimulationEngine()


# ========================================
# 테스트 실행
# ========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("시뮬레이션 엔진 테스트")
    print("=" * 60)

    # 부산항 파업 시나리오 테스트
    scenario = PRESET_SCENARIOS["busan_port"]
    print(f"\n📌 시나리오: {scenario.name}")
    print(f"   영향 섹터: {scenario.affected_sectors}")
    print(f"   심각도: {scenario.severity}")

    results = simulation_engine.run_simulation(scenario)

    print(f"\n📊 시뮬레이션 결과 ({len(results)}개 기업):")
    for r in results:
        print(f"   - {r.deal_name}: {r.original_score} → {r.simulated_score} (+{r.delta})")
        if r.cascade_path:
            print(f"     전이 경로: {' → '.join(r.cascade_path[:3])}")
