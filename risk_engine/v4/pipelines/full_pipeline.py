"""
Full Pipeline - 점수 재계산 파이프라인 (5-Node 스키마)
데이터 수집은 dart_collector_v2 / news_collector_v2가 담당.
이 파이프라인은 기존 데이터 기반으로 점수만 재계산.
"""

from __future__ import annotations
import logging

from ..services.category_service import CategoryService
from ..services.score_service import ScoreService

logger = logging.getLogger(__name__)


def run_full_pipeline(neo4j_client, company_id: str) -> dict:
    """
    점수 재계산 파이프라인

    1. 카테고리 점수 계산 (RiskEntity.riskScore 합산)
    2. 기업 총점 계산 (카테고리 가중합 + 전이)
    """
    logger.info(f"[{company_id}] 점수 재계산 파이프라인 시작")

    results = {
        "companyId": company_id,
        "steps": {},
        "success": True,
    }

    try:
        # 1. 카테고리 점수 계산
        category_service = CategoryService(neo4j_client)
        category_scores = category_service.update_category_scores(company_id)
        results["steps"]["categoryScores"] = {
            "scores": category_scores,
            "status": "completed",
        }

        # 2. 기업 총점 계산
        score_service = ScoreService(neo4j_client)
        final_score = score_service.calculate_company_score(company_id)
        results["steps"]["finalScore"] = final_score
        results["finalScore"] = final_score

        logger.info(f"[{company_id}] 파이프라인 완료: {final_score}")

    except Exception as e:
        logger.error(f"[{company_id}] 파이프라인 오류: {e}")
        results["success"] = False
        results["error"] = str(e)

    return results


def run_pipeline_for_all_companies(neo4j_client) -> list[dict]:
    """모든 기업에 대해 파이프라인 실행"""
    query = """
    MATCH (c:Company)
    RETURN c.name AS name
    """
    companies = neo4j_client.execute_read(query, {})

    results = []
    for company in companies:
        company_id = company.get("name")
        if company_id:
            result = run_full_pipeline(neo4j_client, company_id)
            results.append(result)

    return results
