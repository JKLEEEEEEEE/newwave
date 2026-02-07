"""
시뮬레이션 엔진 테스트
Risk Monitoring System - Phase 3
"""

import pytest
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_engine.simulation_engine import (
    SimulationEngine,
    CascadeConfig,
    ScenarioConfig,
    SimulationResult,
    PRESET_SCENARIOS
)


class TestCascadeConfig:
    """CascadeConfig 테스트"""

    def test_default_values(self):
        """기본값 검증"""
        config = CascadeConfig()
        assert config.tier1_multiplier == 0.8
        assert config.tier2_multiplier == 0.5
        assert config.tier3_multiplier == 0.2
        assert config.max_depth == 3
        assert config.base_propagation_rate == 0.1

    def test_custom_values(self):
        """커스텀 값 설정"""
        config = CascadeConfig(
            tier1_multiplier=0.9,
            tier2_multiplier=0.6,
            max_depth=5
        )
        assert config.tier1_multiplier == 0.9
        assert config.tier2_multiplier == 0.6
        assert config.max_depth == 5


class TestScenarioConfig:
    """ScenarioConfig 테스트"""

    def test_scenario_creation(self):
        """시나리오 생성"""
        scenario = ScenarioConfig(
            id="test_scenario",
            name="테스트 시나리오",
            affected_sectors=["반도체", "전자"],
            impact_factors={"시장위험": 10, "운영위험": 5},
            severity="high"
        )
        assert scenario.id == "test_scenario"
        assert len(scenario.affected_sectors) == 2
        assert scenario.impact_factors["시장위험"] == 10
        assert scenario.severity == "high"

    def test_default_values(self):
        """기본값 검증"""
        scenario = ScenarioConfig(
            id="test",
            name="Test",
            affected_sectors=[],
            impact_factors={}
        )
        assert scenario.propagation_multiplier == 1.5
        assert scenario.severity == "medium"
        assert scenario.is_custom == False


class TestSimulationEngine:
    """SimulationEngine 테스트"""

    @pytest.fixture
    def engine(self):
        """테스트용 엔진 인스턴스"""
        return SimulationEngine()

    @pytest.fixture
    def sample_scenario(self):
        """샘플 시나리오"""
        return ScenarioConfig(
            id="test_scenario",
            name="테스트 시나리오",
            affected_sectors=["반도체"],
            impact_factors={"시장위험": 15, "운영위험": 10},
            propagation_multiplier=1.5,
            severity="high"
        )

    def test_engine_initialization(self, engine):
        """엔진 초기화"""
        assert engine.cascade_config is not None
        assert isinstance(engine.cascade_config, CascadeConfig)

    def test_custom_cascade_config(self):
        """커스텀 설정으로 엔진 초기화"""
        custom_config = CascadeConfig(tier1_multiplier=0.9)
        engine = SimulationEngine(cascade_config=custom_config)
        assert engine.cascade_config.tier1_multiplier == 0.9

    def test_run_simulation_returns_list(self, engine, sample_scenario):
        """시뮬레이션 결과가 리스트로 반환"""
        results = engine.run_simulation(sample_scenario)
        assert isinstance(results, list)

    def test_simulation_result_structure(self, engine, sample_scenario):
        """시뮬레이션 결과 구조 검증"""
        results = engine.run_simulation(sample_scenario)
        if results:
            result = results[0]
            assert hasattr(result, 'deal_id')
            assert hasattr(result, 'deal_name')
            assert hasattr(result, 'original_score')
            assert hasattr(result, 'simulated_score')
            assert hasattr(result, 'delta')
            assert hasattr(result, 'cascade_path')

    def test_delta_calculation(self, engine, sample_scenario):
        """delta = simulated_score - original_score 검증"""
        results = engine.run_simulation(sample_scenario)
        for result in results:
            assert result.delta == result.simulated_score - result.original_score

    def test_results_sorted_by_impact(self, engine, sample_scenario):
        """결과가 영향도(delta) 순으로 정렬"""
        results = engine.run_simulation(sample_scenario)
        if len(results) > 1:
            deltas = [r.delta for r in results]
            assert deltas == sorted(deltas, reverse=True)


class TestPresetScenarios:
    """프리셋 시나리오 테스트"""

    def test_preset_scenarios_exist(self):
        """프리셋 시나리오가 정의되어 있음"""
        assert len(PRESET_SCENARIOS) > 0

    def test_busan_port_scenario(self):
        """부산항 파업 시나리오"""
        scenario = PRESET_SCENARIOS.get("busan_port")
        assert scenario is not None
        assert "물류" in scenario.affected_sectors or "해운" in scenario.affected_sectors

    def test_memory_crash_scenario(self):
        """메모리 가격 폭락 시나리오"""
        scenario = PRESET_SCENARIOS.get("memory_crash")
        assert scenario is not None
        assert "반도체" in scenario.affected_sectors

    def test_all_scenarios_valid(self):
        """모든 시나리오가 유효한 구조"""
        for name, scenario in PRESET_SCENARIOS.items():
            assert scenario.id is not None
            assert scenario.name is not None
            assert isinstance(scenario.affected_sectors, list)
            assert isinstance(scenario.impact_factors, dict)
            assert scenario.severity in ["low", "medium", "high"]


class TestCascadeEffect:
    """Cascade 효과 테스트"""

    @pytest.fixture
    def engine(self):
        return SimulationEngine()

    def test_tier_multipliers_decrease(self):
        """Tier 멀티플라이어가 단계별 감소"""
        config = CascadeConfig()
        assert config.tier1_multiplier > config.tier2_multiplier
        assert config.tier2_multiplier > config.tier3_multiplier

    def test_cascade_path_populated(self):
        """Cascade 경로가 기록됨"""
        engine = SimulationEngine()
        scenario = ScenarioConfig(
            id="cascade_test",
            name="Cascade Test",
            affected_sectors=["반도체", "전자", "자동차"],
            impact_factors={"공급망위험": 20},
            propagation_multiplier=2.0,
            severity="high"
        )
        results = engine.run_simulation(scenario)
        # Mock 데이터 사용 시 cascade_path가 생성됨
        for result in results:
            assert isinstance(result.cascade_path, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
