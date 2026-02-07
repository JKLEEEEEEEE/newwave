"""
============================================================================
Risk Monitoring Control CLI - 데이터 수집 및 모니터링 제어
============================================================================
실시간 모니터링, 스케줄러, 데이터 수집 제어

Usage:
    # 스케줄러 제어
    python -m risk_engine.monitor_control scheduler start     # 자동 수집 스케줄러 시작
    python -m risk_engine.monitor_control scheduler stop      # 스케줄러 중지
    python -m risk_engine.monitor_control scheduler status    # 스케줄러 상태 확인

    # 수동 데이터 수집
    python -m risk_engine.monitor_control collect dart        # DART 공시 수집
    python -m risk_engine.monitor_control collect news        # 뉴스 수집
    python -m risk_engine.monitor_control collect people      # 주주/임원 수집
    python -m risk_engine.monitor_control collect all         # 전체 수집 (공시+뉴스+주주/임원)
    python -m risk_engine.monitor_control collect --company "SK하이닉스"  # 특정 기업

    # 실시간 모니터링
    python -m risk_engine.monitor_control monitor start       # 실시간 모니터링 시작
    python -m risk_engine.monitor_control monitor status      # 모니터링 상태

    # 리스크 점수 갱신
    python -m risk_engine.monitor_control score update        # 전체 점수 갱신
    python -m risk_engine.monitor_control score update --company "SK하이닉스"
"""

import argparse
import sys
import os
import asyncio
import signal
from datetime import datetime
from typing import Optional, List

# 환경 변수 로드
from dotenv import load_dotenv
import pathlib
project_root = pathlib.Path(__file__).parent.parent
load_dotenv(project_root / ".env.local")

import logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def get_neo4j_client():
    """Neo4j 클라이언트"""
    try:
        from .neo4j_client import Neo4jClient
        return Neo4jClient()
    except Exception as e:
        logger.error(f"Neo4j 연결 실패: {e}")
        return None


def get_target_companies(client) -> List[str]:
    """딜 대상 기업 목록 조회"""
    query = """
    MATCH (dt:DealTarget)
    RETURN dt.name AS name
    """
    results = client.execute_read(query)
    return [r['name'] for r in results] if results else []


def get_companies_by_deal(client, deal_name: str) -> List[str]:
    """딜 이름으로 대상 기업 조회"""
    query = """
    MATCH (d:Deal)-[:TARGET]->(c:Company)
    WHERE d.name CONTAINS $deal
    RETURN c.name AS name
    """
    results = client.execute_read(query, {"deal": deal_name})
    if results:
        return [r['name'] for r in results]

    # DealTarget 테이블도 검색
    query2 = """
    MATCH (dt:DealTarget)
    WHERE dt.name CONTAINS $deal
    RETURN dt.name AS name
    """
    results2 = client.execute_read(query2, {"deal": deal_name})
    return [r['name'] for r in results2] if results2 else []


# ============================================
# 스케줄러 제어
# ============================================

def scheduler_start():
    """스케줄러 시작"""
    print("\n[SCHEDULER] 자동 수집 스케줄러 시작...")

    try:
        from .scheduler import CollectionScheduler

        scheduler = CollectionScheduler()

        if not scheduler.is_available:
            print("[ERR] APScheduler 미설치. pip install apscheduler")
            return

        if scheduler.start():
            print("[OK] 스케줄러 시작됨")
            print("\n스케줄 설정:")
            print("  - DART 공시 수집: 60분 간격")
            print("  - 뉴스 수집: 30분 간격")
            print("  - 점수 갱신: 15분 간격")
            print("  - 전체 동기화: 매일 06:00")
            print("\n종료하려면 Ctrl+C를 누르세요...\n")

            # 이벤트 루프 유지
            try:
                loop = asyncio.get_event_loop()
                loop.run_forever()
            except KeyboardInterrupt:
                print("\n[STOP] 스케줄러 중지 중...")
                scheduler.stop()
                print("[OK] 스케줄러 종료됨\n")
        else:
            print("[ERR] 스케줄러 시작 실패")

    except ImportError as e:
        print(f"[ERR] 스케줄러 모듈 로드 실패: {e}")


def scheduler_stop():
    """스케줄러 중지 (API 호출)"""
    import requests
    try:
        resp = requests.post("http://localhost:8080/api/v3/scheduler/stop", timeout=5)
        if resp.ok:
            print("[OK] 스케줄러 중지 요청 완료")
        else:
            print(f"[ERR] {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERR] API 연결 실패: {e}")
        print("     서버가 실행 중인지 확인하세요.")


def scheduler_status():
    """스케줄러 상태 확인"""
    import requests
    try:
        resp = requests.get("http://localhost:8080/api/v3/scheduler/status", timeout=5)
        if resp.ok:
            data = resp.json()
            print("\n" + "=" * 60)
            print("  SCHEDULER STATUS")
            print("=" * 60)
            print(f"  Running: {data.get('is_running', False)}")
            print(f"  Available: {data.get('is_available', False)}")

            jobs = data.get('jobs', [])
            if jobs:
                print("\n  Jobs:")
                for job in jobs:
                    status = "[ON]" if job.get('enabled') else "[OFF]"
                    print(f"    {status} {job.get('job_type')}: {job.get('interval_minutes')}분 간격")

            history = data.get('recent_history', [])
            if history:
                print("\n  Recent Executions:")
                for h in history[:5]:
                    status = "[OK]" if h.get('success') else "[ERR]"
                    print(f"    {status} {h.get('job_type')} - {h.get('completed_at')}")

            print("=" * 60 + "\n")
        else:
            print(f"[ERR] {resp.status_code}: {resp.text}")

    except requests.exceptions.ConnectionError:
        print("[WARN] API 서버 연결 불가 (http://localhost:8080)")
        print("       uvicorn risk_engine.api:app --port 8080 으로 서버 시작 필요")
    except Exception as e:
        print(f"[ERR] {e}")


# ============================================
# 데이터 수집
# ============================================

def collect_dart(companies: List[str] = None):
    """DART 공시 종합 수집 (DS001~DS005)"""
    print("\n[COLLECT] DART 종합 수집 시작...")

    try:
        from .dart_collector_v2 import DartCollectorV2

        api_key = os.getenv("OPENDART_API_KEY")
        if not api_key:
            print("[ERR] OPENDART_API_KEY 환경변수 필요")
            return

        client = get_neo4j_client()
        if not client:
            return

        # 딜 대상 기업 조회
        if not companies:
            companies = get_target_companies(client)

        if not companies:
            print("[WARN] 수집할 딜 대상 기업이 없습니다.")
            print("       먼저 deal_manager로 딜을 등록하세요.")
            return

        print(f"  대상 기업: {', '.join(companies)}")

        collector = DartCollectorV2(api_key, client)

        # 각 기업의 corpCode 조회
        query = """
        MATCH (c:Company)
        WHERE c.name IN $names AND c.corpCode IS NOT NULL AND c.corpCode <> ''
        RETURN c.name AS name, c.corpCode AS corpCode
        """
        results = client.execute_read(query, {"names": companies})

        if not results:
            print("[WARN] DART corpCode가 등록된 기업이 없습니다.")
            print("       deal_manager --add 시 --corp-code 옵션으로 등록하세요.")
            return

        total_collected = 0
        for r in results:
            name = r['name']
            corp_code = r['corpCode']
            print(f"\n  [{name}] (corpCode: {corp_code})")

            # 1) DS001: 공시 목록 (루틴 필터링 적용)
            try:
                result = collector.collect_disclosures(corp_code)
                if result and result.total_valid > 0:
                    saved = collector.save_to_neo4j(result.disclosures)
                    print(f"    [공시] {result.total_valid}건 수집 → {saved}건 저장 (고위험: {result.high_risk_count}건)")
                    total_collected += saved
                    for disc in result.disclosures[:3]:
                        title = disc.title[:50] + "..." if len(disc.title) > 50 else disc.title
                        score = disc.score_result.final_score if disc.score_result else 0
                        print(f"           [{int(score)}] {title}")
                else:
                    print(f"    [공시] 리스크 관련 공시 없음")
            except Exception as e:
                print(f"    [공시] ERR: {e}")

            # 2) DS005: 주요사항보고서 리스크 (소송, 부도, 영업정지, 회생, 채권관리)
            try:
                risk_data = collector.collect_risk_events(corp_code)
                if risk_data:
                    saved = collector.save_risk_events_to_neo4j(risk_data, name)
                    for key, data in risk_data.items():
                        print(f"    [{data['label']}] {len(data['items'])}건 발견 (score: {data['base_score']})")
                    total_collected += saved
                else:
                    print(f"    [리스크] 부도/소송/영업정지/회생 없음")
            except Exception as e:
                print(f"    [리스크] ERR: {e}")

            # 3) DS004: 대량보유 상황보고
            try:
                major_stocks = collector.collect_major_stock(corp_code)
                if major_stocks:
                    saved = collector.save_major_stock_to_neo4j(major_stocks, name, corp_code)
                    print(f"    [대량보유] {saved}건 저장")
                    for ms in major_stocks[:3]:
                        reporter = ms.get('repror', 'N/A')
                        ratio = ms.get('stkrt', '0')
                        reason = ms.get('report_resn', '')
                        print(f"           · {reporter} ({ratio}%) {reason[:20]}")
                    total_collected += saved
                else:
                    print(f"    [대량보유] 보고 없음")
            except Exception as e:
                print(f"    [대량보유] ERR: {e}")

            # 4) DS002: 최대주주 변동현황
            try:
                sh_changes = collector.collect_shareholder_changes(corp_code)
                if sh_changes:
                    saved = collector.save_shareholder_changes_to_neo4j(sh_changes, name, corp_code)
                    print(f"    [주주변동] {saved}건 저장")
                    for sc in sh_changes[:3]:
                        sh_name = sc.get('mxmm_shrholdr_nm', 'N/A')
                        ratio = sc.get('qota_rt', '0')
                        cause = sc.get('change_cause', '')
                        print(f"           · {sh_name} ({ratio}%) {cause[:20]}")
                    total_collected += saved
                else:
                    print(f"    [주주변동] 변동 없음")
            except Exception as e:
                print(f"    [주주변동] ERR: {e}")

            # 5) DS003: 주요 재무지표
            try:
                indices = collector.collect_financial_indices(corp_code)
                if indices:
                    saved = collector.save_financial_indices_to_neo4j(indices, name, corp_code)
                    print(f"    [재무지표] {saved}개 지표 저장")
                    for idx in indices[:5]:
                        idx_nm = idx.get('idx_nm', '')
                        idx_val = idx.get('idx_val', '')
                        print(f"           · {idx_nm}: {idx_val}")
                else:
                    print(f"    [재무지표] 데이터 없음")
            except Exception as e:
                print(f"    [재무지표] ERR: {e}")

        print(f"\n[OK] DART 종합 수집 완료: 총 {total_collected}건\n")

    except ImportError as e:
        print(f"[ERR] DART 수집기 로드 실패: {e}")
    finally:
        if client:
            client.close()


def collect_news(companies: List[str] = None):
    """뉴스 수집"""
    print("\n[COLLECT] 뉴스 수집 시작...")

    try:
        from .news_collector_v2 import NewsCollectorV2

        client = get_neo4j_client()
        if not client:
            return

        # 딜 대상 기업 조회
        if not companies:
            companies = get_target_companies(client)

        if not companies:
            print("[WARN] 수집할 딜 대상 기업이 없습니다.")
            return

        print(f"  대상 기업: {', '.join(companies)}")

        collector = NewsCollectorV2(client)

        total_collected = 0
        for company in companies:
            print(f"\n  [{company}]")

            try:
                result = collector.collect_news(company, limit=30)
                if result and result.news_list:
                    print(f"    - {len(result.news_list)}건 수집됨")

                    # Neo4j에 저장
                    saved = collector.save_to_neo4j(result.news_list, company)
                    print(f"    - {saved}건 Neo4j 저장 완료")
                    total_collected += saved

                    # 최근 3개 헤드라인 출력
                    for news in result.news_list[:3]:
                        title = news.title[:40] + "..." if len(news.title) > 40 else news.title
                        score = news.score_result.final_score if news.score_result else 0
                        print(f"      [{int(score)}] {title}")
                else:
                    print(f"    - 새 뉴스 없음")
            except Exception as e:
                print(f"    - [ERR] {e}")

        print(f"\n[OK] 뉴스 수집 완료: 총 {total_collected}건\n")

    except ImportError as e:
        print(f"[ERR] 뉴스 수집기 로드 실패: {e}")
    finally:
        if client:
            client.close()


def collect_people(companies: List[str] = None):
    """주주/임원 정보 수집"""
    print("\n[COLLECT] 주주/임원 정보 수집 시작...")

    try:
        from .dart_collector_v2 import DartCollectorV2

        api_key = os.getenv("OPENDART_API_KEY")
        if not api_key:
            print("[ERR] OPENDART_API_KEY 환경변수 필요")
            return

        client = get_neo4j_client()
        if not client:
            return

        # 딜 대상 기업 조회
        if not companies:
            companies = get_target_companies(client)

        if not companies:
            print("[WARN] 수집할 딜 대상 기업이 없습니다.")
            return

        print(f"  대상 기업: {', '.join(companies)}")

        collector = DartCollectorV2(api_key, client)

        # 각 기업의 corpCode 조회
        query = """
        MATCH (c:Company)
        WHERE c.name IN $names AND c.corpCode IS NOT NULL AND c.corpCode <> ''
        RETURN c.name AS name, c.corpCode AS corpCode
        """
        results = client.execute_read(query, {"names": companies})

        if not results:
            print("[WARN] DART corpCode가 등록된 기업이 없습니다.")
            return

        total_shareholders = 0
        total_executives = 0

        for r in results:
            name = r['name']
            corp_code = r['corpCode']
            print(f"\n  [{name}] (corpCode: {corp_code})")

            # 주주 수집
            try:
                shareholders = collector.collect_shareholders(corp_code)
                if shareholders:
                    saved = collector.save_shareholders_to_neo4j(shareholders, name, corp_code)
                    print(f"    - 주주 {saved}명 저장")
                    total_shareholders += saved

                    # 상위 3명 출력
                    for sh in shareholders[:3]:
                        sh_name = sh.get('nm', 'N/A')
                        ratio = sh.get('trmend_posesn_stock_qota_rt', '0')
                        print(f"      · {sh_name} ({ratio}%)")
                else:
                    print(f"    - 주주 정보 없음")
            except Exception as e:
                print(f"    - [ERR] 주주 수집 실패: {e}")

            # 임원 수집
            try:
                executives = collector.collect_executives(corp_code)
                if executives:
                    saved = collector.save_executives_to_neo4j(executives, name, corp_code)
                    print(f"    - 임원 {saved}명 저장")
                    total_executives += saved

                    # 상위 3명 출력
                    for ex in executives[:3]:
                        ex_name = ex.get('nm', 'N/A')
                        position = ex.get('ofcps', 'N/A')
                        print(f"      · {ex_name} ({position})")
                else:
                    print(f"    - 임원 정보 없음")
            except Exception as e:
                print(f"    - [ERR] 임원 수집 실패: {e}")

        print(f"\n[OK] 주주/임원 수집 완료: 주주 {total_shareholders}명, 임원 {total_executives}명\n")

    except ImportError as e:
        print(f"[ERR] DART 수집기 로드 실패: {e}")
    finally:
        if client:
            client.close()


def collect_all(companies: List[str] = None):
    """전체 데이터 수집 + 점수 갱신 + AI enrichment"""
    print("\n" + "=" * 60)
    print("  전체 데이터 수집 파이프라인")
    print("=" * 60)

    collect_dart(companies)
    collect_news(companies)
    collect_people(companies)

    # 점수 자동 갱신
    print("\n[AUTO] 점수 갱신 실행...")
    score_update(companies)

    # AI enrichment (환경변수 체크)
    ai_enabled = os.getenv("AI_ENRICHMENT_ENABLED", "false").lower() == "true"
    if ai_enabled:
        print("\n[AI] AI enrichment 파이프라인 실행...")
        run_ai_enrichment(companies)
    else:
        print("\n[AI] AI_ENRICHMENT_ENABLED=false → AI 분석 스킵")

    # 수집 결과 리포트
    print_collection_report(companies)

    print("\n" + "=" * 60)
    print("  전체 파이프라인 완료")
    print("=" * 60 + "\n")


# ============================================
# 실시간 모니터링
# ============================================

def monitor_start():
    """실시간 모니터링 시작"""
    print("\n[MONITOR] 실시간 모니터링 시작...")
    print("          24/7 자동 스캔 및 알림 기능")
    print("          종료: Ctrl+C\n")

    try:
        from .monitoring_agent import main as run_monitoring

        try:
            run_monitoring()
        except KeyboardInterrupt:
            print("\n[STOP] 모니터링 종료됨\n")

    except ImportError as e:
        print(f"[ERR] 모니터링 에이전트 로드 실패: {e}")


def monitor_status():
    """모니터링 상태"""
    import requests
    try:
        resp = requests.get("http://localhost:8080/api/v3/status/summary", timeout=5)
        if resp.ok:
            data = resp.json()
            print("\n" + "=" * 60)
            print("  MONITORING STATUS")
            print("=" * 60)
            print(f"  총 기업 수: {data.get('total_companies', 0)}")
            print(f"  총 신호 수: {data.get('total_signals', 0)}")
            print(f"  PASS: {data.get('pass_count', 0)}")
            print(f"  WARNING: {data.get('warning_count', 0)}")
            print(f"  FAIL: {data.get('fail_count', 0)}")
            print("=" * 60 + "\n")
        else:
            print(f"[ERR] {resp.status_code}")
    except requests.exceptions.ConnectionError:
        print("[WARN] API 서버 연결 불가")
    except Exception as e:
        print(f"[ERR] {e}")


# ============================================
# 리스크 점수 갱신
# ============================================

def score_update(companies: List[str] = None):
    """리스크 점수 갱신"""
    print("\n[SCORE] 리스크 점수 갱신 시작...")

    client = get_neo4j_client()
    if not client:
        return

    try:
        # 딜 대상 기업 조회
        if not companies:
            companies = get_target_companies(client)

        if not companies:
            print("[WARN] 점수 갱신할 딜 대상 기업이 없습니다.")
            return

        print(f"  대상 기업: {', '.join(companies)}")

        # 각 기업의 점수 재계산 (5-Node: RiskEvent 기반)
        for company in companies:
            print(f"\n  [{company}]")

            # 5-Node 경로: Company → RiskCategory → RiskEntity → RiskEvent
            event_query = """
            MATCH (c:Company {name: $name})-[:HAS_CATEGORY]->(rc:RiskCategory)
                  -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
            WHERE ev.createdAt > datetime() - duration('P30D') AND ev.score > 0
            RETURN avg(ev.score) AS avgScore, count(ev) AS eventCount
            """
            result = client.execute_read(event_query, {"name": company})

            if result and result[0].get('eventCount', 0) > 0:
                avg_score = int(result[0].get('avgScore', 50))
                event_count = result[0].get('eventCount', 0)

                # 점수 업데이트
                update_query = """
                MATCH (c:Company {name: $name})
                SET c.totalRiskScore = $score,
                    c.riskLevel = CASE
                        WHEN $score < 50 THEN 'PASS'
                        WHEN $score < 75 THEN 'WARNING'
                        ELSE 'FAIL'
                    END,
                    c.updatedAt = datetime()
                RETURN c.totalRiskScore AS score, c.riskLevel AS status
                """
                update_result = client.execute_write_single(update_query, {
                    "name": company,
                    "score": avg_score
                })

                if update_result:
                    print(f"    - 이벤트 {event_count}건 기반 점수 갱신: {update_result['score']}점 ({update_result['status']})")
            else:
                print(f"    - 최근 30일 신호 없음, 기존 점수 유지")

        print(f"\n[OK] 점수 갱신 완료\n")

    finally:
        client.close()


def run_ai_enrichment(companies: List[str] = None):
    """AI enrichment 파이프라인 실행"""
    try:
        from .ai_service_v2 import ai_service_v2

        if not ai_service_v2.is_available:
            print("[AI] OpenAI 서비스 사용 불가 (API 키 확인 필요)")
            return

        client = get_neo4j_client()
        if not client:
            return

        if not companies:
            companies = get_target_companies(client)

        if not companies:
            print("[AI] 대상 기업이 없습니다.")
            return

        for company in companies:
            print(f"\n  [AI] {company} 분석 중...")

            # 1. 리스크 요약 생성
            try:
                deal_data = _build_deal_context(client, company)
                summary = ai_service_v2.summarize_risk(deal_data)
                if summary:
                    print(f"    - 리스크 요약: {summary.get('one_liner', 'N/A')[:60]}")
            except Exception as e:
                print(f"    - [ERR] 리스크 요약 실패: {e}")

            # 2. 종합 인사이트 생성
            try:
                context = _build_deal_context(client, company)
                insight = ai_service_v2.generate_comprehensive_insight(context)
                if insight:
                    exec_summary = insight.get('executive_summary', '')
                    print(f"    - 종합 인사이트: {exec_summary[:60]}...")

                    # Neo4j에 AI 인사이트를 RiskEvent로 저장
                    _save_ai_insight_to_neo4j(client, company, insight)
            except Exception as e:
                print(f"    - [ERR] 종합 인사이트 실패: {e}")

        print(f"\n[AI] AI enrichment 완료")

    except ImportError as e:
        print(f"[ERR] AI 서비스 로드 실패: {e}")
    finally:
        if client:
            client.close()


def _build_deal_context(client, company: str) -> dict:
    """AI 분석용 딜 컨텍스트 빌드"""
    # 기업 기본 정보
    base_query = """
    MATCH (c:Company {name: $name})
    RETURN c.totalRiskScore AS riskScore, c.riskLevel AS riskLevel,
           c.sector AS sector
    """
    base = client.execute_read_single(base_query, {"name": company})

    # 최근 신호 (5-Node 경로: Company → RiskCategory → RiskEntity → RiskEvent)
    signal_query = """
    MATCH (c:Company {name: $name})-[:HAS_CATEGORY]->(rc:RiskCategory)
          -[:HAS_ENTITY]->(re:RiskEntity)-[:HAS_EVENT]->(ev:RiskEvent)
    WHERE ev.score > 0
    RETURN ev.type AS type, ev.title AS title, ev.score AS score,
           toString(ev.publishedAt) AS date
    ORDER BY ev.publishedAt DESC LIMIT 10
    """
    signals = client.execute_read(signal_query, {"name": company}) or []

    return {
        "company": company,
        "sector": base.get("sector", "") if base else "",
        "riskScore": base.get("riskScore", 0) if base else 0,
        "riskLevel": base.get("riskLevel", "PASS") if base else "PASS",
        "signals": [{"type": s.get("type", ""), "title": s.get("title", ""), "score": s.get("score", 0), "date": s.get("date", "")} for s in signals],
        "categoryScores": {},
    }


def _save_ai_insight_to_neo4j(client, company: str, insight: dict):
    """AI 인사이트를 5-Node 스키마 RiskEvent로 저장
    경로: Company → RiskCategory(OTHER) → RiskEntity(ISSUE/AI_INSIGHT) → RiskEvent(ISSUE)
    """
    import hashlib
    date_str = datetime.now().strftime("%Y%m%d")
    raw = f"{company}_{date_str}"
    event_id = f"AI_{hashlib.md5(raw.encode()).hexdigest()[:8]}"
    entity_id = f"ENTITY_AI_{company.replace(' ', '_')}"

    query = """
    MATCH (c:Company)-[:HAS_CATEGORY]->(rc:RiskCategory)
    WHERE c.name = $company AND rc.code = 'OTHER'
    WITH rc LIMIT 1
    MERGE (re:RiskEntity {id: $entityId})
    ON CREATE SET re.name = 'AI 종합 분석', re.type = 'ISSUE',
                  re.subType = 'AI_INSIGHT', re.createdAt = datetime()
    ON MATCH SET re.updatedAt = datetime()
    MERGE (rc)-[:HAS_ENTITY]->(re)
    WITH re
    MERGE (ev:RiskEvent {id: $eventId})
    ON CREATE SET ev.title = $title, ev.type = 'ISSUE',
                  ev.summary = $description, ev.score = 0,
                  ev.severity = 'LOW', ev.sourceName = 'AI',
                  ev.isActive = true, ev.aiGenerated = true,
                  ev.createdAt = datetime()
    ON MATCH SET ev.summary = $description, ev.updatedAt = datetime()
    MERGE (re)-[:HAS_EVENT]->(ev)
    """
    try:
        client.execute_write(query, {
            "eventId": event_id,
            "entityId": entity_id,
            "title": f"[AI 분석] {company} 종합 인사이트",
            "description": insight.get("executive_summary", ""),
            "company": company,
        })
    except Exception as e:
        logger.error(f"AI 인사이트 저장 실패: {e}")


def print_collection_report(companies: List[str] = None):
    """수집 결과 리포트 출력"""
    client = get_neo4j_client()
    if not client:
        return

    try:
        print("\n" + "-" * 60)
        print("  수집 결과 리포트")
        print("-" * 60)

        # 총 수집 건수 (5-Node 스키마: RiskEvent 유형별)
        count_query = """
        MATCH (ev:RiskEvent)
        WHERE ev.createdAt > datetime() - duration('P1D')
        RETURN ev.type AS type, count(ev) AS cnt
        """
        count_result = client.execute_read(count_query, {})
        news_count = 0
        dart_count = 0
        for row in (count_result or []):
            if row.get('type') == 'NEWS':
                news_count = row.get('cnt', 0)
            elif row.get('type') == 'DISCLOSURE':
                dart_count = row.get('cnt', 0)

        print(f"  총 수집 건수: 뉴스 {news_count}건, 공시 {dart_count}건")

        # 고위험 이벤트 요약
        high_risk_query = """
        MATCH (e:RiskEvent)
        WHERE e.isActive = true AND e.score >= 40
        RETURN e.title AS title, e.score AS score, e.companyId AS company
        ORDER BY e.score DESC LIMIT 5
        """
        high_risks = client.execute_read(high_risk_query, {})
        if high_risks:
            print(f"\n  고위험 이벤트 (상위 {len(high_risks)}건):")
            for hr in high_risks:
                title = hr.get('title', 'N/A')[:40]
                score = hr.get('score', 0)
                company = hr.get('company', 'N/A')
                print(f"    [{score}] {company}: {title}")

        print("-" * 60)

    finally:
        client.close()


# ============================================
# 메인
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Risk Monitoring Control - 데이터 수집 및 모니터링 제어",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # scheduler 서브커맨드
    sched_parser = subparsers.add_parser("scheduler", help="자동 수집 스케줄러 제어")
    sched_parser.add_argument("action", choices=["start", "stop", "status"], help="동작")

    # collect 서브커맨드
    collect_parser = subparsers.add_parser("collect", help="데이터 수집")
    collect_parser.add_argument("type", choices=["dart", "news", "people", "all"], help="수집 유형")
    collect_parser.add_argument("--company", "-c", help="특정 기업만 수집")
    collect_parser.add_argument("--deal", "-d", help="딜 이름으로 대상 기업 자동 조회")

    # monitor 서브커맨드
    monitor_parser = subparsers.add_parser("monitor", help="실시간 모니터링")
    monitor_parser.add_argument("action", choices=["start", "status"], help="동작")

    # score 서브커맨드
    score_parser = subparsers.add_parser("score", help="리스크 점수 관리")
    score_parser.add_argument("action", choices=["update"], help="동작")
    score_parser.add_argument("--company", "-c", help="특정 기업만")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\n예시:")
        print("  python -m risk_engine.monitor_control scheduler start")
        print("  python -m risk_engine.monitor_control collect all")
        print("  python -m risk_engine.monitor_control monitor start")
        print("  python -m risk_engine.monitor_control score update")
        sys.exit(0)

    # 명령 실행
    if args.command == "scheduler":
        if args.action == "start":
            scheduler_start()
        elif args.action == "stop":
            scheduler_stop()
        elif args.action == "status":
            scheduler_status()

    elif args.command == "collect":
        companies = [args.company] if args.company else None

        # --deal 플래그로 기업 조회
        if hasattr(args, 'deal') and args.deal and not companies:
            client = get_neo4j_client()
            if client:
                try:
                    companies = get_companies_by_deal(client, args.deal)
                    if companies:
                        print(f"[DEAL] '{args.deal}' → 대상 기업: {', '.join(companies)}")
                    else:
                        print(f"[WARN] '{args.deal}' 딜에 해당하는 기업이 없습니다.")
                        return
                finally:
                    client.close()

        if args.type == "dart":
            collect_dart(companies)
        elif args.type == "news":
            collect_news(companies)
        elif args.type == "people":
            collect_people(companies)
        elif args.type == "all":
            collect_all(companies)

    elif args.command == "monitor":
        if args.action == "start":
            monitor_start()
        elif args.action == "status":
            monitor_status()

    elif args.command == "score":
        companies = [args.company] if args.company else None
        if args.action == "update":
            score_update(companies)


if __name__ == "__main__":
    main()
