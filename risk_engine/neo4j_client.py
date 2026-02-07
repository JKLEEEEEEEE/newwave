"""
Neo4j 연결 관리 클라이언트
Risk Monitoring System v2.2
"""

from neo4j import GraphDatabase
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import os
import logging

# 환경 변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
except ImportError:
    pass

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 연결 관리 싱글톤 클라이언트"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance._connected = False
        return cls._instance

    def connect(self) -> 'Neo4jClient':
        """드라이버 초기화 및 연결"""
        if self._driver is not None and self._connected:
            return self

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        max_pool_size = int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", 50))

        try:
            self._driver = GraphDatabase.driver(
                uri,
                auth=(username, password),
                max_connection_pool_size=max_pool_size
            )
            # 연결 테스트
            self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"✅ Neo4j 연결 성공: {uri}")
        except Exception as e:
            logger.error(f"❌ Neo4j 연결 실패: {e}")
            self._connected = False
            raise

        return self

    def close(self):
        """연결 종료"""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Neo4j 연결 종료")

    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected

    @contextmanager
    def session(self, database: Optional[str] = None):
        """세션 컨텍스트 매니저"""
        if not self._connected:
            self.connect()

        db = database or os.getenv("NEO4J_DATABASE", "neo4j")
        session = self._driver.session(database=db)
        try:
            yield session
        finally:
            session.close()

    def execute_read(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """읽기 쿼리 실행"""
        with self.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def execute_write(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """쓰기 쿼리 실행"""
        with self.session() as session:
            result = session.run(query, params or {})
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }

    def execute_read_single(self, query: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """단일 레코드 조회"""
        results = self.execute_read(query, params)
        return results[0] if results else None

    def execute_write_single(self, query: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """단일 레코드 반환하는 쓰기 쿼리 실행"""
        with self.session() as session:
            result = session.run(query, params or {})
            record = result.single()
            return record.data() if record else None

    def execute_write_with_results(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """쓰기 쿼리 실행 후 결과 레코드 반환 (SET + RETURN 조합용)"""
        with self.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    # ========================================
    # 공급망 그래프 조회
    # ========================================
    def get_supply_chain(self, company_id: str) -> Dict[str, Any]:
        """공급망 그래프 조회"""
        query = """
        MATCH (target:Company {id: $companyId})
        OPTIONAL MATCH (target)<-[r1:SUPPLIES_TO]-(supplier:Company)
        OPTIONAL MATCH (target)-[r2:SUPPLIES_TO]->(customer:Company)
        OPTIONAL MATCH (target)-[r3:COMPETES_WITH]-(competitor:Company)
        RETURN target,
               collect(DISTINCT {
                   node: supplier,
                   relationship: r1,
                   type: 'supplier'
               }) AS suppliers,
               collect(DISTINCT {
                   node: customer,
                   relationship: r2,
                   type: 'customer'
               }) AS customers,
               collect(DISTINCT {
                   node: competitor,
                   relationship: r3,
                   type: 'competitor'
               }) AS competitors
        """
        return self.execute_read_single(query, {"companyId": company_id})

    # ========================================
    # 리스크 전이 경로 조회
    # ========================================
    def get_risk_propagation(self, company_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """리스크 전이 경로 조회"""
        query = """
        MATCH path = (target:Company {id: $companyId})<-[:SUPPLIES_TO*1..$maxDepth]-(source:Company)
        WHERE source.totalRiskScore > 50
        RETURN
            [n IN nodes(path) | {
                id: n.id,
                name: n.name,
                riskScore: n.totalRiskScore
            }] AS riskPath,
            reduce(risk = 0.0, r IN relationships(path) |
                risk + coalesce(startNode(r).totalRiskScore * r.dependency / 100.0, 0)
            ) AS propagatedRisk,
            length(path) AS pathLength
        ORDER BY propagatedRisk DESC
        LIMIT 10
        """
        return self.execute_read(query, {"companyId": company_id, "maxDepth": max_depth})

    # ========================================
    # 기업 검색
    # ========================================
    def search_companies(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """기업명으로 검색"""
        query = """
        MATCH (c:Company)
        WHERE c.name CONTAINS $keyword OR c.sector CONTAINS $keyword
        RETURN c.id AS id, c.name AS name, c.sector AS sector, c.totalRiskScore AS riskScore
        ORDER BY c.totalRiskScore DESC
        LIMIT $limit
        """
        return self.execute_read(query, {"keyword": keyword, "limit": limit})

    # ========================================
    # 고위험 기업 조회
    # ========================================
    def get_high_risk_companies(self, threshold: int = 70, limit: int = 20) -> List[Dict[str, Any]]:
        """고위험 기업 목록 조회"""
        query = """
        MATCH (c:Company)
        WHERE c.totalRiskScore >= $threshold
        RETURN c.id AS id, c.name AS name, c.sector AS sector,
               c.totalRiskScore AS totalRiskScore,
               c.directRiskScore AS directRiskScore,
               c.propagatedRiskScore AS propagatedRiskScore,
               c.status AS status
        ORDER BY c.totalRiskScore DESC
        LIMIT $limit
        """
        return self.execute_read(query, {"threshold": threshold, "limit": limit})

    # ========================================
    # 연결 테스트
    # ========================================
    def test_connection(self) -> Dict[str, Any]:
        """연결 테스트 및 DB 정보 반환"""
        try:
            self.connect()
            result = self.execute_read_single("CALL dbms.components() YIELD name, versions RETURN name, versions")
            count = self.execute_read_single("MATCH (n) RETURN count(n) AS count")
            return {
                "connected": True,
                "database": result,
                "node_count": count.get("count", 0) if count else 0
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }


# 싱글톤 인스턴스
neo4j_client = Neo4jClient()


# ========================================
# 테스트 실행
# ========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Neo4j 연결 테스트...")
    result = neo4j_client.test_connection()
    print(f"결과: {result}")

    if result["connected"]:
        print("\n고위험 기업 조회 테스트...")
        companies = neo4j_client.get_high_risk_companies(threshold=50, limit=5)
        for c in companies:
            print(f"  - {c['name']}: {c['totalRiskScore']}점")

    neo4j_client.close()
