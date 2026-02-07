"""
Supply Chain E2E 테스트 - 공급망 그래프 전체 플로우 검증
Feature: supply-chain-e2e-test
"""

import pytest
from typing import List, Set


class TestSupplyChainGraphRendering:
    """공급망 그래프 렌더링 E2E 테스트"""

    @pytest.mark.asyncio
    async def test_graph_rendering_basic(self, client):
        """기본 그래프 렌더링 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        assert response.status_code == 200
        data = response.json()

        # 최소 노드 수 검증 (중심 + 공급사 + 고객 + 경쟁사)
        assert len(data["nodes"]) >= 5

        # 최소 엣지 수 검증
        assert len(data["edges"]) >= 4

    @pytest.mark.asyncio
    async def test_node_types_distribution(self, client):
        """노드 타입 분포 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        type_counts = {"company": 0, "supplier": 0, "customer": 0, "competitor": 0}
        for node in data["nodes"]:
            if node["type"] in type_counts:
                type_counts[node["type"]] += 1

        # 중심 기업 1개 이상
        assert type_counts["company"] >= 1, "중심 기업 노드가 없음"

        # 공급사 또는 고객 1개 이상
        assert type_counts["supplier"] + type_counts["customer"] >= 1, "공급사/고객 노드가 없음"

    @pytest.mark.asyncio
    async def test_node_risk_score_ranges(self, client):
        """노드 리스크 점수 범위 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        for node in data["nodes"]:
            score = node["riskScore"]
            assert 0 <= score <= 100, f"노드 {node['name']}의 점수 {score}가 범위 밖"

    @pytest.mark.asyncio
    async def test_edge_connectivity(self, client):
        """엣지 연결성 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        node_ids: Set[str] = {n["id"] for n in data["nodes"]}

        for edge in data["edges"]:
            # 모든 엣지의 source/target이 노드에 존재해야 함
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not in nodes"

    @pytest.mark.asyncio
    async def test_no_self_loops(self, client):
        """자기 참조 엣지 없음 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        for edge in data["edges"]:
            assert edge["source"] != edge["target"], f"Self-loop detected: {edge['source']}"

    @pytest.mark.asyncio
    async def test_no_duplicate_nodes(self, client):
        """중복 노드 없음 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        node_ids = [n["id"] for n in data["nodes"]]
        assert len(node_ids) == len(set(node_ids)), "중복 노드 ID가 존재함"


class TestSupplyChainNodeDetails:
    """공급망 노드 상세 정보 테스트"""

    @pytest.mark.asyncio
    async def test_node_required_fields(self, client):
        """노드 필수 필드 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        required_fields = ["id", "name", "type", "riskScore"]
        for node in data["nodes"]:
            for field in required_fields:
                assert field in node, f"노드에 필수 필드 {field}가 없음"

    @pytest.mark.asyncio
    async def test_supplier_node_properties(self, client):
        """공급사 노드 속성 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        suppliers = [n for n in data["nodes"] if n["type"] == "supplier"]
        assert len(suppliers) >= 1, "공급사 노드가 없음"

        for supplier in suppliers:
            assert supplier["riskScore"] >= 0
            assert supplier["riskScore"] <= 100

    @pytest.mark.asyncio
    async def test_customer_node_properties(self, client):
        """고객사 노드 속성 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        customers = [n for n in data["nodes"] if n["type"] == "customer"]
        assert len(customers) >= 1, "고객사 노드가 없음"

    @pytest.mark.asyncio
    async def test_competitor_node_properties(self, client):
        """경쟁사 노드 속성 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        competitors = [n for n in data["nodes"] if n["type"] == "competitor"]
        assert len(competitors) >= 1, "경쟁사 노드가 없음"


class TestSupplyChainEdgeDetails:
    """공급망 엣지 상세 정보 테스트"""

    @pytest.mark.asyncio
    async def test_edge_required_fields(self, client):
        """엣지 필수 필드 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        required_fields = ["source", "target", "riskTransfer"]
        for edge in data["edges"]:
            for field in required_fields:
                assert field in edge, f"엣지에 필수 필드 {field}가 없음"

    @pytest.mark.asyncio
    async def test_edge_risk_transfer_range(self, client):
        """엣지 riskTransfer 범위 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        for edge in data["edges"]:
            rt = edge["riskTransfer"]
            assert 0 <= rt <= 1, f"riskTransfer {rt}가 0-1 범위 밖"

    @pytest.mark.asyncio
    async def test_edge_direction_semantics(self, client):
        """엣지 방향 의미론 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        # 공급사 → 중심기업 방향 확인
        center_node = next((n for n in data["nodes"] if n["type"] == "company"), None)
        if center_node:
            # 공급사에서 중심으로 가는 엣지가 있어야 함
            supplier_ids = {n["id"] for n in data["nodes"] if n["type"] == "supplier"}
            has_supply_edge = any(
                edge["source"] in supplier_ids and edge["target"] == center_node["id"]
                for edge in data["edges"]
            )
            # 적어도 하나의 공급 관계가 있어야 함
            assert has_supply_edge or len(supplier_ids) == 0


class TestSupplyChainDataConsistency:
    """공급망 데이터 일관성 테스트"""

    @pytest.mark.asyncio
    async def test_score_propagation_logic(self, client):
        """점수 전이 로직 테스트"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        # 엣지별 전이 영향 검증
        for edge in data["edges"]:
            source_node = next((n for n in data["nodes"] if n["id"] == edge["source"]), None)
            if source_node:
                # 고위험 노드(riskScore > 70)의 전이율이 0보다 커야 함
                if source_node["riskScore"] > 70:
                    assert edge["riskTransfer"] > 0, "고위험 노드의 전이율이 0"

    @pytest.mark.asyncio
    async def test_graph_connectivity(self, client):
        """그래프 연결성 테스트 - 모든 노드가 연결되어야 함"""
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        data = response.json()

        if len(data["nodes"]) > 1:
            # 연결된 노드 ID 수집
            connected_nodes: Set[str] = set()
            for edge in data["edges"]:
                connected_nodes.add(edge["source"])
                connected_nodes.add(edge["target"])

            # 최소한 중심 노드는 연결되어야 함
            center_node = next((n for n in data["nodes"] if n["type"] == "company"), None)
            if center_node:
                assert center_node["id"] in connected_nodes, "중심 노드가 연결되지 않음"


class TestSupplyChainPerformance:
    """공급망 API 성능 테스트"""

    @pytest.mark.asyncio
    async def test_response_time(self, client):
        """응답 시간 테스트"""
        import time

        start = time.time()
        response = await client.get("/api/v3/companies/SK하이닉스/supply-chain")
        elapsed = time.time() - start

        assert response.status_code == 200
        # 3초 이내 응답 (Neo4j 연결 포함)
        assert elapsed < 3.0, f"응답 시간 {elapsed}초가 너무 김"

    @pytest.mark.asyncio
    async def test_multiple_requests(self, client):
        """다중 요청 테스트"""
        companies = ["SK하이닉스", "삼성전자"]

        for company in companies:
            response = await client.get(f"/api/v3/companies/{company}/supply-chain")
            assert response.status_code == 200


class TestSupplyChainErrorHandling:
    """공급망 API 에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_invalid_company_name(self, client):
        """존재하지 않는 기업명 처리 테스트"""
        response = await client.get("/api/v3/companies/존재하지않는회사/supply-chain")
        # 404 또는 빈 데이터 반환
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_special_characters_in_name(self, client):
        """특수문자 포함 기업명 처리 테스트"""
        response = await client.get("/api/v3/companies/Test%20Company/supply-chain")
        # 정상 응답 또는 에러 처리
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_empty_company_name(self, client):
        """빈 기업명 처리 테스트"""
        response = await client.get("/api/v3/companies//supply-chain")
        # 404 또는 에러 반환
        assert response.status_code in [404, 405, 400]
