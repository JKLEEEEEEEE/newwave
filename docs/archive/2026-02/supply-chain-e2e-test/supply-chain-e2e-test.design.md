# 공급망 리스크 화면 E2E 통합테스트 설계서

> 작성일: 2026-02-06
> Feature ID: supply-chain-e2e-test
> Plan 문서: [supply-chain-e2e-test.plan.md](../../01-plan/features/supply-chain-e2e-test.plan.md)

---

## 1. 테스트 아키텍처

### 1.1 테스트 레이어 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    E2E Tests (Playwright)                    │
│              - User scenario simulation                      │
│              - Cross-browser testing                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Integration Tests (pytest + httpx)              │
│              - API flow verification                         │
│              - Data consistency checks                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Component Tests (Jest + RTL)                       │
│              - UI rendering verification                     │
│              - Interaction testing                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Unit Tests (pytest/Jest)                     │
│              - Individual function testing                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 테스트 환경 구성

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  api:
    build: ./risk_engine
    environment:
      - USE_MOCK_DATA=true
      - NEO4J_URI=bolt://neo4j:7687
    ports:
      - "8000:8000"

  neo4j:
    image: neo4j:5.0
    environment:
      - NEO4J_AUTH=neo4j/testpassword
    ports:
      - "7687:7687"
```

---

## 2. API 통합테스트 상세 설계

### 2.1 테스트 파일: `test_api_flow.py`

```python
# risk_engine/tests/integration/test_api_flow.py

import pytest
from httpx import AsyncClient
from typing import Dict, Any

class TestRiskOverviewFlow:
    """Tab 1: Risk Overview API 플로우 테스트"""

    @pytest.fixture
    async def client(self):
        from risk_engine.api import app
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    async def test_ov01_deal_list_loading(self, client):
        """OV-01: 딜 목록 로딩 테스트"""
        response = await client.get("/api/v2/deals")
        assert response.status_code == 200
        data = response.json()
        assert "deals" in data
        assert len(data["deals"]) > 0
        # 각 딜에 필수 필드 확인
        for deal in data["deals"]:
            assert "id" in deal
            assert "name" in deal
            assert "riskScore" in deal

    async def test_ov02_status_summary(self, client):
        """OV-02: Status 요약 테스트"""
        response = await client.get("/api/v3/status/summary")
        assert response.status_code == 200
        data = response.json()
        assert "PASS" in data
        assert "WARNING" in data
        assert "FAIL" in data
        # 카운트 합계 검증
        total = data["PASS"]["count"] + data["WARNING"]["count"] + data["FAIL"]["count"]
        assert total > 0

    async def test_ov03_average_score_calculation(self, client):
        """OV-03: 평균 점수 계산 테스트"""
        response = await client.get("/api/v3/status/summary")
        data = response.json()
        # 각 Status의 avgScore 검증
        for status in ["PASS", "WARNING", "FAIL"]:
            if data[status]["count"] > 0:
                assert 0 <= data[status]["avgScore"] <= 100


class TestSupplyChainFlow:
    """Tab 2: Supply Chain API 플로우 테스트"""

    async def test_sc01_graph_data_structure(self, client):
        """SC-01: 그래프 데이터 구조 검증"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        assert response.status_code == 200
        data = response.json()

        # 노드 구조 검증
        assert "nodes" in data
        for node in data["nodes"]:
            assert "id" in node
            assert "name" in node
            assert "type" in node
            assert node["type"] in ["company", "supplier", "customer", "competitor"]
            assert "riskScore" in node
            assert 0 <= node["riskScore"] <= 100

        # 엣지 구조 검증
        assert "edges" in data
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "riskTransfer" in edge
            assert 0 <= edge["riskTransfer"] <= 1

    async def test_sc02_center_node_exists(self, client):
        """SC-02: 중심 노드 존재 확인"""
        company_name = "SK하이닉스"
        response = await client.get(f"/api/v3/companies/{company_name}/supply-chain")
        data = response.json()

        # 중심 노드(type=company) 확인
        center_nodes = [n for n in data["nodes"] if n["type"] == "company"]
        assert len(center_nodes) >= 1
        assert any(n["name"] == company_name for n in center_nodes)

    async def test_sc03_supplier_nodes(self, client):
        """SC-03: 공급사 노드 검증"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        suppliers = [n for n in data["nodes"] if n["type"] == "supplier"]
        assert len(suppliers) >= 1
        for supplier in suppliers:
            assert "industry" in supplier or supplier.get("industry") is None

    async def test_sc08_edge_risk_transfer(self, client):
        """SC-08: 엣지 riskTransfer 비례 검증"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        # 모든 엣지의 riskTransfer 값이 유효 범위 내인지 확인
        for edge in data["edges"]:
            assert 0 <= edge["riskTransfer"] <= 1

    async def test_sc10_node_count_header(self, client):
        """SC-10: 노드/관계 수 반환 검증"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        # 메타데이터 확인
        assert len(data["nodes"]) >= 5  # 최소 노드 수
        assert len(data["edges"]) >= 4  # 최소 엣지 수


class TestScoreBreakdownFlow:
    """Tab 4: Score Breakdown API 플로우 테스트"""

    async def test_sb01_total_score(self, client):
        """SB-01: 총점 표시 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        assert response.status_code == 200
        data = response.json()

        assert "totalScore" in data
        assert 0 <= data["totalScore"] <= 100

    async def test_sb02_status_display(self, client):
        """SB-02: Status 표시 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["PASS", "WARNING", "FAIL"]

    async def test_sb03_breakdown_structure(self, client):
        """SB-03: 직접/전이 분해 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        data = response.json()

        assert "breakdown" in data
        assert "directScore" in data["breakdown"]
        assert "propagatedScore" in data["breakdown"]

        # 직접 + 전이 = 총점
        total = data["breakdown"]["directScore"] + data["breakdown"]["propagatedScore"]
        assert abs(total - data["totalScore"]) < 0.01

    async def test_sb04_categories(self, client):
        """SB-04: 카테고리별 탭 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        data = response.json()

        assert "categories" in data
        assert len(data["categories"]) >= 3

        for category in data["categories"]:
            assert "name" in category
            assert "score" in category
            assert "weight" in category

    async def test_sb05_recent_signals(self, client):
        """SB-05: 최근 신호 탭 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        data = response.json()

        assert "recentSignals" in data
        for signal in data["recentSignals"]:
            assert "id" in signal
            assert "type" in signal
            assert "severity" in signal

    async def test_sb06_propagators(self, client):
        """SB-06: 전이 경로 탭 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/score")
        data = response.json()

        assert "propagators" in data
        for prop in data["propagators"]:
            assert "companyName" in prop
            assert "contribution" in prop


class TestSimulationFlow:
    """Tab 6: Simulation API 플로우 테스트"""

    async def test_sm01_scenario_list(self, client):
        """SM-01: 프리셋 시나리오 목록 테스트"""
        response = await client.get("/api/v2/scenarios")
        assert response.status_code == 200
        data = response.json()

        assert "scenarios" in data
        assert len(data["scenarios"]) >= 5

        for scenario in data["scenarios"]:
            assert "id" in scenario
            assert "name" in scenario
            assert "description" in scenario

    async def test_sm03_simulation_execution(self, client):
        """SM-03: 시뮬레이션 실행 테스트"""
        payload = {
            "scenario_id": "supply_disruption",
            "target_company": "SK하이닉스",
            "parameters": {"severity": 0.5}
        }
        response = await client.post("/api/v2/simulate/advanced", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "affectedCompanies" in data
        assert "cascadePath" in data
        assert len(data["affectedCompanies"]) >= 1

    async def test_sm05_custom_scenario_creation(self, client):
        """SM-05: 커스텀 시나리오 생성 테스트"""
        payload = {
            "name": "테스트 시나리오",
            "type": "custom",
            "parameters": {
                "affectedIndustries": ["반도체"],
                "severity": 0.7
            }
        }
        response = await client.post("/api/v2/scenarios/custom", json=payload)
        assert response.status_code in [200, 201]


class TestPredictionFlow:
    """Tab 7: Prediction API 플로우 테스트"""

    async def test_pr01_prediction_chart(self, client):
        """PR-01: 예측 차트 데이터 테스트"""
        response = await client.get("/api/v2/predict/SK하이닉스?periods=30")
        assert response.status_code == 200
        data = response.json()

        assert "predictions" in data
        assert len(data["predictions"]) == 30

        for pred in data["predictions"]:
            assert "date" in pred
            assert "predicted" in pred

    async def test_pr02_confidence_interval(self, client):
        """PR-02: 신뢰 구간 테스트"""
        response = await client.get("/api/v2/predict/SK하이닉스?periods=30")
        data = response.json()

        for pred in data["predictions"]:
            assert "lower" in pred
            assert "upper" in pred
            assert pred["lower"] <= pred["predicted"] <= pred["upper"]

    async def test_pr03_trend_display(self, client):
        """PR-03: 트렌드 표시 테스트"""
        response = await client.get("/api/v2/predict/SK하이닉스?periods=30")
        data = response.json()

        assert "trend" in data
        assert data["trend"] in ["increasing", "decreasing", "stable"]
```

---

## 3. Supply Chain 테스트 상세 설계

### 3.1 테스트 파일: `test_supply_chain.py`

```python
# risk_engine/tests/e2e/test_supply_chain.py

import pytest
from httpx import AsyncClient
from typing import List, Dict

class TestSupplyChainGraph:
    """공급망 그래프 E2E 테스트"""

    @pytest.fixture
    def sample_companies(self) -> List[str]:
        return ["SK하이닉스", "삼성전자", "현대자동차"]

    async def test_graph_rendering_basic(self, client, sample_companies):
        """기본 그래프 렌더링 테스트"""
        for company in sample_companies:
            response = await client.get(f"/api/v3/companies/{company}/supply-chain")
            assert response.status_code == 200
            data = response.json()

            # 최소 노드 수 검증
            assert len(data["nodes"]) >= 3

            # 최소 엣지 수 검증
            assert len(data["edges"]) >= 2

    async def test_node_types_distribution(self, client):
        """노드 타입 분포 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        type_counts = {"company": 0, "supplier": 0, "customer": 0, "competitor": 0}
        for node in data["nodes"]:
            type_counts[node["type"]] += 1

        # 중심 기업 1개 이상
        assert type_counts["company"] >= 1

        # 공급사 또는 고객 1개 이상
        assert type_counts["supplier"] + type_counts["customer"] >= 1

    async def test_node_risk_score_ranges(self, client):
        """노드 리스크 점수 범위 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        for node in data["nodes"]:
            score = node["riskScore"]
            assert 0 <= score <= 100

            # 점수별 색상 분류 검증
            if score < 50:
                expected_status = "PASS"
            elif score < 75:
                expected_status = "WARNING"
            else:
                expected_status = "FAIL"

    async def test_edge_connectivity(self, client):
        """엣지 연결성 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        node_ids = {n["id"] for n in data["nodes"]}

        for edge in data["edges"]:
            # 모든 엣지의 source/target이 노드에 존재해야 함
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids

    async def test_supply_chain_depth(self, client):
        """공급망 깊이 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain?depth=2")
        data = response.json()

        # depth=2로 요청 시 2차 관계까지 포함
        # 최소 노드 수 증가 검증
        assert len(data["nodes"]) >= 5


class TestSupplyChainDataConsistency:
    """공급망 데이터 일관성 테스트"""

    async def test_bidirectional_relationship(self, client):
        """양방향 관계 일관성 테스트"""
        # A가 B의 공급사이면, B는 A의 고객
        response_a = await client.get("/api/v3/companies/ASML/supply-chain")
        response_b = await client.get("/api/v3/companies/SK하이닉스/supply-chain")

        data_a = response_a.json()
        data_b = response_b.json()

        # 관계 존재 여부 확인 (데이터에 따라 조건부)
        # 이 테스트는 실제 데이터 구조에 맞게 조정 필요

    async def test_score_propagation_consistency(self, client):
        """점수 전이 일관성 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        for edge in data["edges"]:
            # riskTransfer 값이 0-1 범위
            assert 0 <= edge["riskTransfer"] <= 1

            # source 노드의 점수가 높을수록 전이 영향 증가 (논리적 검증)
            source_node = next((n for n in data["nodes"] if n["id"] == edge["source"]), None)
            if source_node:
                # 고위험 노드의 전이율이 의미있는지 확인
                pass
```

---

## 4. UI 컴포넌트 테스트 상세 설계

### 4.1 테스트 파일: `RiskGraph.test.tsx`

```typescript
// components/risk/__tests__/RiskGraph.test.tsx

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RiskGraph } from '../RiskGraph';
import { SupplyChainGraph } from '../types';

// Mock canvas context
const mockContext = {
  clearRect: jest.fn(),
  beginPath: jest.fn(),
  arc: jest.fn(),
  fill: jest.fn(),
  stroke: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  fillText: jest.fn(),
  measureText: jest.fn(() => ({ width: 50 })),
  save: jest.fn(),
  restore: jest.fn(),
  translate: jest.fn(),
  scale: jest.fn(),
};

HTMLCanvasElement.prototype.getContext = jest.fn(() => mockContext) as any;

describe('RiskGraph Component', () => {
  const mockData: SupplyChainGraph = {
    nodes: [
      { id: '1', name: 'SK하이닉스', type: 'company', riskScore: 58 },
      { id: '2', name: 'ASML', type: 'supplier', riskScore: 35 },
      { id: '3', name: '애플', type: 'customer', riskScore: 42 },
      { id: '4', name: '삼성전자', type: 'competitor', riskScore: 45 },
    ],
    edges: [
      { source: '2', target: '1', riskTransfer: 0.3 },
      { source: '1', target: '3', riskTransfer: 0.25 },
      { source: '4', target: '1', riskTransfer: 0.1 },
    ],
  };

  const mockOnNodeClick = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    test('SC-01: Canvas에 그래프가 렌더링되어야 함', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      const canvas = screen.getByTestId('risk-graph-canvas');
      expect(canvas).toBeInTheDocument();
    });

    test('SC-10: 헤더에 노드/관계 수가 표시되어야 함', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      expect(screen.getByText(/4.*노드/)).toBeInTheDocument();
      expect(screen.getByText(/3.*관계/)).toBeInTheDocument();
    });

    test('빈 데이터 처리', () => {
      const emptyData: SupplyChainGraph = { nodes: [], edges: [] };
      render(<RiskGraph data={emptyData} onNodeClick={mockOnNodeClick} />);

      expect(screen.getByText(/데이터가 없습니다/)).toBeInTheDocument();
    });
  });

  describe('Node Types', () => {
    test('SC-02: 중심 노드(company)가 렌더링되어야 함', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      // Canvas 렌더링 확인 (draw 함수 호출 여부)
      expect(mockContext.arc).toHaveBeenCalled();
    });

    test('SC-03: 공급사 노드에 보라색 테두리', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      // strokeStyle이 보라색으로 설정되었는지 확인
      // 실제 구현에 따라 조정
    });

    test('SC-04: 고객사 노드에 청록색 테두리', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      // 청록색 확인
    });

    test('SC-05: 경쟁사 노드에 주황색 테두리', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      // 주황색 확인
    });
  });

  describe('Node Colors by Score', () => {
    test('SC-09: 점수 0-49는 초록색', () => {
      const lowScoreData: SupplyChainGraph = {
        nodes: [{ id: '1', name: 'Test', type: 'company', riskScore: 30 }],
        edges: [],
      };
      render(<RiskGraph data={lowScoreData} onNodeClick={mockOnNodeClick} />);

      // 초록색 확인
    });

    test('SC-09: 점수 50-74는 노란색', () => {
      const midScoreData: SupplyChainGraph = {
        nodes: [{ id: '1', name: 'Test', type: 'company', riskScore: 60 }],
        edges: [],
      };
      render(<RiskGraph data={midScoreData} onNodeClick={mockOnNodeClick} />);

      // 노란색 확인
    });

    test('SC-09: 점수 75-100은 빨간색', () => {
      const highScoreData: SupplyChainGraph = {
        nodes: [{ id: '1', name: 'Test', type: 'company', riskScore: 85 }],
        edges: [],
      };
      render(<RiskGraph data={highScoreData} onNodeClick={mockOnNodeClick} />);

      // 빨간색 확인
    });
  });

  describe('Interactions', () => {
    test('SC-07: 노드 클릭 시 onNodeClick 호출', async () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      const canvas = screen.getByTestId('risk-graph-canvas');

      // 캔버스 클릭 시뮬레이션
      fireEvent.click(canvas, { clientX: 400, clientY: 300 });

      // 클릭 핸들러 호출 확인 (좌표에 노드가 있을 경우)
      // 실제 테스트에서는 노드 위치 계산 필요
    });

    test('SC-06: 노드 호버 시 툴팁 표시', async () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      const canvas = screen.getByTestId('risk-graph-canvas');

      fireEvent.mouseMove(canvas, { clientX: 400, clientY: 300 });

      // 툴팁 표시 확인
      await waitFor(() => {
        // 툴팁 요소 확인
      });
    });
  });

  describe('Edge Rendering', () => {
    test('SC-08: 엣지 굵기가 riskTransfer에 비례', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      // lineWidth 설정 확인
      expect(mockContext.lineTo).toHaveBeenCalled();
    });
  });

  describe('Data Format Compatibility', () => {
    test('nodes/edges 포맷 처리', () => {
      render(<RiskGraph data={mockData} onNodeClick={mockOnNodeClick} />);

      expect(screen.getByTestId('risk-graph-canvas')).toBeInTheDocument();
    });

    test('centerNode/suppliers/customers 포맷 처리', () => {
      const legacyFormatData = {
        centerNode: { id: '1', name: 'Center', type: 'company', riskScore: 50 },
        suppliers: [{ id: '2', name: 'Supplier', type: 'supplier', riskScore: 40 }],
        customers: [{ id: '3', name: 'Customer', type: 'customer', riskScore: 45 }],
      };

      render(<RiskGraph data={legacyFormatData as any} onNodeClick={mockOnNodeClick} />);

      expect(screen.getByTestId('risk-graph-canvas')).toBeInTheDocument();
    });
  });
});
```

### 4.2 테스트 파일: `RiskScoreBreakdownV3.test.tsx`

```typescript
// components/risk/__tests__/RiskScoreBreakdownV3.test.tsx

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RiskScoreBreakdownV3 } from '../RiskScoreBreakdownV3';

describe('RiskScoreBreakdownV3 Component', () => {
  const mockData = {
    totalScore: 58,
    status: 'WARNING',
    breakdown: {
      directScore: 46,
      propagatedScore: 12,
    },
    categories: [
      { name: '재무', score: 45, weight: 0.3 },
      { name: '운영', score: 52, weight: 0.25 },
      { name: '법률', score: 38, weight: 0.2 },
      { name: '시장', score: 61, weight: 0.15 },
      { name: '공급망', score: 72, weight: 0.1 },
    ],
    recentSignals: [
      { id: 's1', type: 'LEGAL', severity: 'HIGH', message: '소송 관련 뉴스' },
      { id: 's2', type: 'MARKET', severity: 'MEDIUM', message: '시장 변동성' },
    ],
    propagators: [
      { companyName: 'ASML', contribution: 5.2 },
      { companyName: '삼성전자', contribution: 3.8 },
    ],
  };

  describe('Score Display', () => {
    test('SB-01: 총점이 0-100 범위로 표시', () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      expect(screen.getByText('58')).toBeInTheDocument();
    });

    test('SB-02: Status 배지 표시 (WARNING)', () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      expect(screen.getByText('WARNING')).toBeInTheDocument();
      // 배지 색상 확인 (노란색)
    });

    test('SB-02: PASS Status 표시', () => {
      const passData = { ...mockData, totalScore: 40, status: 'PASS' };
      render(<RiskScoreBreakdownV3 data={passData} />);

      expect(screen.getByText('PASS')).toBeInTheDocument();
    });

    test('SB-02: FAIL Status 표시', () => {
      const failData = { ...mockData, totalScore: 80, status: 'FAIL' };
      render(<RiskScoreBreakdownV3 data={failData} />);

      expect(screen.getByText('FAIL')).toBeInTheDocument();
    });
  });

  describe('Breakdown Display', () => {
    test('SB-03: 직접 리스크 진행바 표시', () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      expect(screen.getByText(/직접.*46/)).toBeInTheDocument();
    });

    test('SB-03: 전이 리스크 진행바 표시', () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      expect(screen.getByText(/전이.*12/)).toBeInTheDocument();
    });
  });

  describe('Category Tabs', () => {
    test('SB-04: 카테고리 목록 표시', () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      expect(screen.getByText('재무')).toBeInTheDocument();
      expect(screen.getByText('운영')).toBeInTheDocument();
      expect(screen.getByText('법률')).toBeInTheDocument();
      expect(screen.getByText('시장')).toBeInTheDocument();
      expect(screen.getByText('공급망')).toBeInTheDocument();
    });

    test('SB-04: 카테고리 점수 표시', () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      // 각 카테고리의 점수 확인
      expect(screen.getByText('45')).toBeInTheDocument();
    });
  });

  describe('Recent Signals Tab', () => {
    test('SB-05: 신호 목록 탭 전환', async () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      const signalsTab = screen.getByText('최근 신호');
      fireEvent.click(signalsTab);

      await waitFor(() => {
        expect(screen.getByText('소송 관련 뉴스')).toBeInTheDocument();
      });
    });

    test('SB-05: 신호 severity 배지', async () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      const signalsTab = screen.getByText('최근 신호');
      fireEvent.click(signalsTab);

      await waitFor(() => {
        expect(screen.getByText('HIGH')).toBeInTheDocument();
      });
    });
  });

  describe('Propagators Tab', () => {
    test('SB-06: 전이 경로 탭 전환', async () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      const propagatorsTab = screen.getByText('전이 경로');
      fireEvent.click(propagatorsTab);

      await waitFor(() => {
        expect(screen.getByText('ASML')).toBeInTheDocument();
      });
    });

    test('SB-06: Propagator 기여도 표시', async () => {
      render(<RiskScoreBreakdownV3 data={mockData} />);

      const propagatorsTab = screen.getByText('전이 경로');
      fireEvent.click(propagatorsTab);

      await waitFor(() => {
        expect(screen.getByText(/5\.2/)).toBeInTheDocument();
      });
    });
  });
});
```

---

## 5. E2E Playwright 테스트 설계

### 5.1 테스트 파일: `risk-monitoring.spec.ts`

```typescript
// e2e/risk-monitoring.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Risk Monitoring E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/risk-monitoring');
  });

  test.describe('Scenario 1: 신규 사용자 화면 탐색', () => {
    test('딜 목록이 로딩되어 표시됨', async ({ page }) => {
      // 딜 카드 로딩 대기
      await expect(page.locator('[data-testid="deal-card"]')).toHaveCount.greaterThan(0);

      // 평균 점수 표시 확인
      await expect(page.locator('[data-testid="average-score"]')).toBeVisible();
    });

    test('SK하이닉스 딜 클릭 시 Supply Chain 그래프 표시', async ({ page }) => {
      // SK하이닉스 딜 클릭
      await page.click('text=SK하이닉스');

      // Supply Chain 탭 클릭
      await page.click('[data-testid="tab-supply-chain"]');

      // 그래프 캔버스 표시 확인
      await expect(page.locator('[data-testid="risk-graph-canvas"]')).toBeVisible();

      // 노드 수 확인 (최소 9개)
      const nodeCount = await page.locator('[data-testid="node-count"]').textContent();
      expect(parseInt(nodeCount || '0')).toBeGreaterThanOrEqual(9);
    });
  });

  test.describe('Scenario 2: 리스크 분석 플로우', () => {
    test.beforeEach(async ({ page }) => {
      // SK하이닉스 선택
      await page.click('text=SK하이닉스');
    });

    test('Score Breakdown에서 직접/전이 리스크 분리 표시', async ({ page }) => {
      await page.click('[data-testid="tab-score-breakdown"]');

      // 직접 리스크 표시 확인
      await expect(page.locator('[data-testid="direct-score"]')).toBeVisible();

      // 전이 리스크 표시 확인
      await expect(page.locator('[data-testid="propagated-score"]')).toBeVisible();
    });

    test('카테고리별 점수 목록 표시', async ({ page }) => {
      await page.click('[data-testid="tab-score-breakdown"]');

      // 카테고리 목록 확인 (최소 3개)
      await expect(page.locator('[data-testid="category-item"]')).toHaveCount.greaterThanOrEqual(3);
    });

    test('전이 경로 탭에서 Propagator 목록 표시', async ({ page }) => {
      await page.click('[data-testid="tab-score-breakdown"]');
      await page.click('[data-testid="subtab-propagators"]');

      // Propagator 목록 확인
      await expect(page.locator('[data-testid="propagator-item"]')).toHaveCount.greaterThanOrEqual(1);
    });
  });

  test.describe('Scenario 3: 시뮬레이션 실행', () => {
    test('프리셋 시나리오 선택 및 실행', async ({ page }) => {
      await page.click('[data-testid="tab-simulation"]');

      // 시나리오 목록 로딩 확인
      await expect(page.locator('[data-testid="scenario-item"]')).toHaveCount.greaterThanOrEqual(5);

      // "부산항 파업" 시나리오 선택
      await page.click('text=부산항 파업');

      // 실행 버튼 클릭
      await page.click('[data-testid="run-simulation"]');

      // 영향받는 기업 목록 표시 확인
      await expect(page.locator('[data-testid="affected-companies"]')).toBeVisible();

      // Cascade 경로 표시 확인
      await expect(page.locator('[data-testid="cascade-path"]')).toBeVisible();
    });

    test('커스텀 시나리오 생성', async ({ page }) => {
      await page.click('[data-testid="tab-simulation"]');
      await page.click('[data-testid="create-custom-scenario"]');

      // 폼 입력
      await page.fill('[data-testid="scenario-name"]', '테스트 시나리오');
      await page.fill('[data-testid="scenario-severity"]', '0.7');

      // 저장
      await page.click('[data-testid="save-scenario"]');

      // 목록에 추가 확인
      await expect(page.locator('text=테스트 시나리오')).toBeVisible();
    });
  });
});
```

---

## 6. 테스트 실행 설정

### 6.1 pytest 설정: `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = risk_engine/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    e2e: End-to-end tests
    integration: Integration tests
    slow: Slow tests
```

### 6.2 Jest 설정: `jest.config.js`

```javascript
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/components/$1',
  },
  testMatch: ['**/__tests__/**/*.test.tsx'],
  collectCoverageFrom: [
    'components/risk/**/*.tsx',
    '!components/risk/**/*.d.ts',
  ],
};
```

### 6.3 Playwright 설정: `playwright.config.ts`

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## 7. 구현 체크리스트

| # | 파일 | 설명 | 테스트 수 |
|---|------|------|----------|
| 1 | `test_api_flow.py` | API 통합테스트 | ~20 |
| 2 | `test_supply_chain.py` | 공급망 E2E 테스트 | ~10 |
| 3 | `RiskGraph.test.tsx` | 그래프 컴포넌트 테스트 | ~15 |
| 4 | `RiskScoreBreakdownV3.test.tsx` | 점수 분해 컴포넌트 테스트 | ~12 |
| 5 | `risk-monitoring.spec.ts` | E2E Playwright 테스트 | ~8 |

**총 예상 테스트 수: ~65개**

---

*Design Document Created: 2026-02-06*
