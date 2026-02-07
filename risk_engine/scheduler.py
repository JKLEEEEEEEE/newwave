"""
============================================================================
자동 수집 스케줄러 (V3)
============================================================================
- APScheduler 기반 주기적 데이터 수집
- DART 공시, 뉴스 자동 수집
- 리스크 점수 자동 갱신
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

# APScheduler (선택적)
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None
    CronTrigger = None
    IntervalTrigger = None

from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class JobType(str, Enum):
    """작업 유형"""
    DART_COLLECT = "dart_collect"
    NEWS_COLLECT = "news_collect"
    SCORE_UPDATE = "score_update"
    FULL_SYNC = "full_sync"
    HEALTH_CHECK = "health_check"


@dataclass
class JobConfig:
    """작업 설정"""
    job_type: JobType
    interval_minutes: int = 60
    cron_expression: Optional[str] = None
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300


@dataclass
class JobResult:
    """작업 결과"""
    job_type: JobType
    success: bool
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    items_processed: int = 0
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class CollectionScheduler:
    """
    데이터 수집 스케줄러

    Usage:
        scheduler = CollectionScheduler()
        scheduler.start()
        # ...
        scheduler.stop()
    """

    # 기본 스케줄 설정
    DEFAULT_SCHEDULES = {
        JobType.DART_COLLECT: JobConfig(
            job_type=JobType.DART_COLLECT,
            interval_minutes=60,  # 1시간마다
            enabled=True
        ),
        JobType.NEWS_COLLECT: JobConfig(
            job_type=JobType.NEWS_COLLECT,
            interval_minutes=30,  # 30분마다
            enabled=True
        ),
        JobType.SCORE_UPDATE: JobConfig(
            job_type=JobType.SCORE_UPDATE,
            interval_minutes=15,  # 15분마다
            enabled=True
        ),
        JobType.FULL_SYNC: JobConfig(
            job_type=JobType.FULL_SYNC,
            cron_expression="0 6 * * *",  # 매일 06:00
            enabled=True
        ),
        JobType.HEALTH_CHECK: JobConfig(
            job_type=JobType.HEALTH_CHECK,
            interval_minutes=5,  # 5분마다
            enabled=True
        ),
    }

    def __init__(self, neo4j_client=None):
        self.neo4j_client = neo4j_client
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self.job_history: List[JobResult] = []
        self.max_history = 100
        self._collectors_loaded = False

        # 수집기 로드
        self._load_collectors()

    def _load_collectors(self):
        """수집기 모듈 로드"""
        try:
            from .dart_collector_v2 import DartCollectorV2
            from .news_collector_v2 import NewsCollectorV2
            from .risk_calculator_v3 import RiskCalculatorV3

            self.dart_collector = DartCollectorV2()
            self.news_collector = NewsCollectorV2()
            self.risk_calculator = RiskCalculatorV3(self.neo4j_client) if self.neo4j_client else None
            self._collectors_loaded = True
            logger.info("✅ 수집기 모듈 로드 완료")
        except ImportError as e:
            logger.warning(f"⚠️ 수집기 모듈 로드 실패: {e}")
            self.dart_collector = None
            self.news_collector = None
            self.risk_calculator = None

    @property
    def is_available(self) -> bool:
        """스케줄러 사용 가능 여부"""
        return APSCHEDULER_AVAILABLE

    def start(self):
        """스케줄러 시작"""
        if not APSCHEDULER_AVAILABLE:
            logger.warning("⚠️ APScheduler 미설치. pip install apscheduler")
            return False

        if self.is_running:
            logger.warning("⚠️ 스케줄러가 이미 실행 중입니다")
            return False

        try:
            self.scheduler = AsyncIOScheduler()

            # 기본 작업 등록
            for job_type, config in self.DEFAULT_SCHEDULES.items():
                if config.enabled:
                    self._add_job(config)

            self.scheduler.start()
            self.is_running = True
            logger.info("🚀 스케줄러 시작됨")
            return True

        except Exception as e:
            logger.error(f"❌ 스케줄러 시작 실패: {e}")
            return False

    def stop(self):
        """스케줄러 중지"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("🛑 스케줄러 중지됨")

    def _add_job(self, config: JobConfig):
        """작업 추가"""
        if not self.scheduler:
            return

        job_func = self._get_job_function(config.job_type)
        if not job_func:
            logger.warning(f"⚠️ 작업 함수 없음: {config.job_type}")
            return

        job_id = f"job_{config.job_type.value}"

        if config.cron_expression:
            # Cron 기반 스케줄
            trigger = CronTrigger.from_crontab(config.cron_expression)
        else:
            # Interval 기반 스케줄
            trigger = IntervalTrigger(minutes=config.interval_minutes)

        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=config.job_type.value,
            max_instances=1,
            replace_existing=True
        )

        logger.info(f"📋 작업 등록: {config.job_type.value}")

    def _get_job_function(self, job_type: JobType) -> Optional[Callable]:
        """작업 유형에 맞는 함수 반환"""
        job_map = {
            JobType.DART_COLLECT: self._job_dart_collect,
            JobType.NEWS_COLLECT: self._job_news_collect,
            JobType.SCORE_UPDATE: self._job_score_update,
            JobType.FULL_SYNC: self._job_full_sync,
            JobType.HEALTH_CHECK: self._job_health_check,
        }
        return job_map.get(job_type)

    async def _job_dart_collect(self):
        """DART 공시 수집 작업"""
        started_at = datetime.now()
        errors = []
        items_processed = 0

        try:
            if not self.dart_collector:
                raise Exception("DART 수집기 미로드")

            # 모니터링 대상 기업 조회
            companies = await self._get_monitored_companies()

            for company in companies:
                try:
                    corp_code = company.get("corpCode")
                    if not corp_code:
                        continue

                    result = self.dart_collector.collect_disclosures(corp_code, days=1)
                    items_processed += result.total_count

                    # 리스크 신호 저장
                    if result.risk_count > 0 and self.neo4j_client:
                        await self._save_signals(company["id"], result.items, "DART")

                except Exception as e:
                    errors.append(f"{company.get('name', 'Unknown')}: {str(e)}")

            success = len(errors) == 0

        except Exception as e:
            logger.error(f"DART 수집 실패: {e}")
            errors.append(str(e))
            success = False

        self._record_result(JobResult(
            job_type=JobType.DART_COLLECT,
            success=success,
            started_at=started_at,
            completed_at=datetime.now(),
            duration_seconds=(datetime.now() - started_at).total_seconds(),
            items_processed=items_processed,
            errors=errors
        ))

    async def _job_news_collect(self):
        """뉴스 수집 작업"""
        started_at = datetime.now()
        errors = []
        items_processed = 0

        try:
            if not self.news_collector:
                raise Exception("뉴스 수집기 미로드")

            companies = await self._get_monitored_companies()

            for company in companies:
                try:
                    result = self.news_collector.collect_news(
                        company_name=company.get("name", ""),
                        limit=10
                    )
                    items_processed += result.total_count

                    if result.risk_count > 0 and self.neo4j_client:
                        await self._save_signals(company["id"], result.items, "NEWS")

                except Exception as e:
                    errors.append(f"{company.get('name', 'Unknown')}: {str(e)}")

            success = len(errors) == 0

        except Exception as e:
            logger.error(f"뉴스 수집 실패: {e}")
            errors.append(str(e))
            success = False

        self._record_result(JobResult(
            job_type=JobType.NEWS_COLLECT,
            success=success,
            started_at=started_at,
            completed_at=datetime.now(),
            duration_seconds=(datetime.now() - started_at).total_seconds(),
            items_processed=items_processed,
            errors=errors
        ))

    async def _job_score_update(self):
        """리스크 점수 갱신 작업"""
        started_at = datetime.now()
        errors = []
        items_processed = 0

        try:
            if not self.risk_calculator:
                raise Exception("리스크 계산기 미로드")

            companies = await self._get_monitored_companies()

            for company in companies:
                try:
                    breakdown = self.risk_calculator.calculate_total_risk(company["id"])

                    # Neo4j에 점수 저장
                    if self.neo4j_client:
                        await self._update_company_score(
                            company["id"],
                            breakdown.total_score,
                            breakdown.status
                        )

                    items_processed += 1

                except Exception as e:
                    errors.append(f"{company.get('name', 'Unknown')}: {str(e)}")

            success = len(errors) == 0

        except Exception as e:
            logger.error(f"점수 갱신 실패: {e}")
            errors.append(str(e))
            success = False

        self._record_result(JobResult(
            job_type=JobType.SCORE_UPDATE,
            success=success,
            started_at=started_at,
            completed_at=datetime.now(),
            duration_seconds=(datetime.now() - started_at).total_seconds(),
            items_processed=items_processed,
            errors=errors
        ))

    async def _job_full_sync(self):
        """전체 동기화 작업 (매일 06:00)"""
        started_at = datetime.now()
        errors = []
        details = {}

        try:
            # DART 전체 수집
            await self._job_dart_collect()
            details["dart"] = "completed"

            # 뉴스 전체 수집
            await self._job_news_collect()
            details["news"] = "completed"

            # 점수 전체 갱신
            await self._job_score_update()
            details["scores"] = "completed"

            success = True
            logger.info("✅ 전체 동기화 완료")

        except Exception as e:
            logger.error(f"전체 동기화 실패: {e}")
            errors.append(str(e))
            success = False

        self._record_result(JobResult(
            job_type=JobType.FULL_SYNC,
            success=success,
            started_at=started_at,
            completed_at=datetime.now(),
            duration_seconds=(datetime.now() - started_at).total_seconds(),
            errors=errors,
            details=details
        ))

    async def _job_health_check(self):
        """헬스 체크 작업"""
        started_at = datetime.now()
        errors = []
        details = {}

        try:
            # Neo4j 연결 확인
            if self.neo4j_client:
                try:
                    self.neo4j_client.execute_read("RETURN 1 AS check")
                    details["neo4j"] = "healthy"
                except Exception as e:
                    details["neo4j"] = f"unhealthy: {e}"
                    errors.append(f"Neo4j: {e}")

            # 수집기 상태 확인
            details["dart_collector"] = "available" if self.dart_collector else "unavailable"
            details["news_collector"] = "available" if self.news_collector else "unavailable"
            details["risk_calculator"] = "available" if self.risk_calculator else "unavailable"

            success = len(errors) == 0

        except Exception as e:
            errors.append(str(e))
            success = False

        self._record_result(JobResult(
            job_type=JobType.HEALTH_CHECK,
            success=success,
            started_at=started_at,
            completed_at=datetime.now(),
            duration_seconds=(datetime.now() - started_at).total_seconds(),
            errors=errors,
            details=details
        ))

    async def _get_monitored_companies(self) -> List[Dict]:
        """모니터링 대상 기업 목록 조회"""
        if not self.neo4j_client:
            # Mock 데이터
            return [
                {"id": "sk_hynix", "name": "SK하이닉스", "corpCode": "00126380"},
                {"id": "samsung", "name": "삼성전자", "corpCode": "00126380"},
                {"id": "hanmi", "name": "한미반도체", "corpCode": "00156225"},
            ]

        try:
            query = """
            MATCH (c:Company)
            WHERE c.isMonitored = true OR c.isMonitored IS NULL
            RETURN c.id AS id, c.name AS name, c.corpCode AS corpCode
            LIMIT 100
            """
            results = self.neo4j_client.execute_read(query)
            return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"기업 목록 조회 실패: {e}")
            return []

    async def _save_signals(self, company_id: str, items: List, source: str):
        """리스크 신호 저장"""
        if not self.neo4j_client:
            return

        for item in items:
            if not hasattr(item, "risk_score") or item.risk_score <= 0:
                continue

            try:
                query = """
                MATCH (c:Company {id: $companyId})
                CREATE (sig:Signal {
                    id: $signalId,
                    source: $source,
                    title: $title,
                    riskScore: $score,
                    keywords: $keywords,
                    detectedAt: datetime()
                })
                CREATE (sig)-[:DETECTED_IN]->(c)
                """
                self.neo4j_client.execute_write(query, {
                    "companyId": company_id,
                    "signalId": f"{source}_{item.id}",
                    "source": source,
                    "title": getattr(item, "title", ""),
                    "score": item.risk_score,
                    "keywords": getattr(item, "matched_keywords", [])
                })
            except Exception as e:
                logger.warning(f"신호 저장 실패: {e}")

    async def _update_company_score(self, company_id: str, score: int, status: str):
        """기업 점수 업데이트"""
        if not self.neo4j_client:
            return

        try:
            query = """
            MATCH (c:Company {id: $companyId})
            SET c.totalRiskScore = $score,
                c.riskLevel = $status,
                c.lastScoreUpdate = datetime()
            WITH c
            MATCH (s:Status {id: $status})
            MERGE (c)-[:HAS_STATUS]->(s)
            """
            self.neo4j_client.execute_write(query, {
                "companyId": company_id,
                "score": score,
                "status": status
            })
        except Exception as e:
            logger.warning(f"점수 업데이트 실패: {e}")

    def _record_result(self, result: JobResult):
        """작업 결과 기록"""
        self.job_history.append(result)

        # 이력 크기 제한
        if len(self.job_history) > self.max_history:
            self.job_history = self.job_history[-self.max_history:]

        # 로깅
        status = "✅" if result.success else "❌"
        logger.info(
            f"{status} {result.job_type.value}: "
            f"{result.items_processed} items, "
            f"{result.duration_seconds:.2f}s"
        )

    def get_job_status(self) -> Dict:
        """작업 상태 조회"""
        if not self.scheduler:
            return {"running": False, "jobs": []}

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "pending": job.pending
            })

        return {
            "running": self.is_running,
            "jobs": jobs,
            "recent_results": [
                {
                    "job_type": r.job_type.value,
                    "success": r.success,
                    "completed_at": r.completed_at.isoformat(),
                    "duration": r.duration_seconds,
                    "items": r.items_processed
                }
                for r in self.job_history[-10:]
            ]
        }

    def trigger_job(self, job_type: JobType) -> bool:
        """작업 수동 실행"""
        if not self.scheduler or not self.is_running:
            return False

        job_id = f"job_{job_type.value}"
        job = self.scheduler.get_job(job_id)

        if job:
            job.modify(next_run_time=datetime.now())
            return True

        return False

    def update_schedule(self, job_type: JobType, interval_minutes: int = None, enabled: bool = None):
        """스케줄 설정 변경"""
        if job_type not in self.DEFAULT_SCHEDULES:
            return False

        config = self.DEFAULT_SCHEDULES[job_type]

        if interval_minutes is not None:
            config.interval_minutes = interval_minutes

        if enabled is not None:
            config.enabled = enabled

        # 스케줄러 재등록
        if self.scheduler and self.is_running:
            job_id = f"job_{job_type.value}"

            # 기존 작업 제거
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # 새 설정으로 등록
            if config.enabled:
                self._add_job(config)

        return True


# 싱글톤 인스턴스
scheduler: Optional[CollectionScheduler] = None


def get_scheduler(neo4j_client=None) -> CollectionScheduler:
    """스케줄러 인스턴스 반환"""
    global scheduler
    if scheduler is None:
        scheduler = CollectionScheduler(neo4j_client)
    return scheduler


if __name__ == "__main__":
    # 테스트 실행
    import asyncio

    async def test():
        sched = CollectionScheduler()

        if sched.is_available:
            sched.start()
            print("스케줄러 시작됨")
            print(sched.get_job_status())

            await asyncio.sleep(10)

            sched.stop()
            print("스케줄러 종료됨")
        else:
            print("APScheduler 미설치")

    asyncio.run(test())
