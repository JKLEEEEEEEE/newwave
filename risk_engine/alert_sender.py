"""
============================================================================
알림 발송기 (V3)
============================================================================
- 리스크 신호 알림 발송
- 이메일, Slack, Webhook 지원
- 알림 규칙 기반 필터링
"""

import os
import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class AlertChannel(str, Enum):
    """알림 채널"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    TELEGRAM = "telegram"


class AlertPriority(str, Enum):
    """알림 우선순위"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """알림 규칙"""
    id: str
    name: str
    enabled: bool = True
    min_score: int = 50  # 최소 점수
    status_filter: List[str] = field(default_factory=lambda: ["WARNING", "FAIL"])
    source_filter: List[str] = field(default_factory=list)  # 빈 리스트 = 모든 소스
    company_filter: List[str] = field(default_factory=list)  # 빈 리스트 = 모든 기업
    channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.CONSOLE])
    priority: AlertPriority = AlertPriority.MEDIUM
    cooldown_minutes: int = 60  # 동일 알림 재발송 대기


@dataclass
class Alert:
    """알림 데이터"""
    id: str
    title: str
    message: str
    company_id: str
    company_name: str
    score: int
    status: str
    source: str
    priority: AlertPriority
    created_at: datetime
    keywords: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertResult:
    """알림 발송 결과"""
    alert_id: str
    channel: AlertChannel
    success: bool
    sent_at: datetime
    error: Optional[str] = None


class AlertSenderBase(ABC):
    """알림 발송기 베이스 클래스"""

    @abstractmethod
    async def send(self, alert: Alert) -> AlertResult:
        """알림 발송"""
        pass


class ConsoleAlertSender(AlertSenderBase):
    """콘솔 알림 발송기 (개발/테스트용)"""

    async def send(self, alert: Alert) -> AlertResult:
        priority_icons = {
            AlertPriority.LOW: "🔵",
            AlertPriority.MEDIUM: "🟡",
            AlertPriority.HIGH: "🟠",
            AlertPriority.CRITICAL: "🔴"
        }

        icon = priority_icons.get(alert.priority, "⚪")

        print(f"\n{'='*60}")
        print(f"{icon} [{alert.priority.value.upper()}] {alert.title}")
        print(f"{'='*60}")
        print(f"기업: {alert.company_name} ({alert.company_id})")
        print(f"점수: {alert.score} | Status: {alert.status}")
        print(f"소스: {alert.source}")
        print(f"키워드: {', '.join(alert.keywords) if alert.keywords else 'N/A'}")
        print(f"시간: {alert.created_at.isoformat()}")
        print(f"\n{alert.message}")
        print(f"{'='*60}\n")

        return AlertResult(
            alert_id=alert.id,
            channel=AlertChannel.CONSOLE,
            success=True,
            sent_at=datetime.now()
        )


class SlackAlertSender(AlertSenderBase):
    """Slack 알림 발송기"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    async def send(self, alert: Alert) -> AlertResult:
        if not self.is_configured:
            return AlertResult(
                alert_id=alert.id,
                channel=AlertChannel.SLACK,
                success=False,
                sent_at=datetime.now(),
                error="Slack webhook URL not configured"
            )

        # Slack 메시지 포맷
        color_map = {
            AlertPriority.LOW: "#36a64f",
            AlertPriority.MEDIUM: "#daa038",
            AlertPriority.HIGH: "#ff9800",
            AlertPriority.CRITICAL: "#ff0000"
        }

        status_emoji = {
            "PASS": ":white_check_mark:",
            "WARNING": ":warning:",
            "FAIL": ":x:"
        }

        payload = {
            "attachments": [{
                "color": color_map.get(alert.priority, "#808080"),
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{status_emoji.get(alert.status, '')} {alert.title}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*기업:*\n{alert.company_name}"},
                            {"type": "mrkdwn", "text": f"*점수:*\n{alert.score}"},
                            {"type": "mrkdwn", "text": f"*Status:*\n{alert.status}"},
                            {"type": "mrkdwn", "text": f"*소스:*\n{alert.source}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": alert.message
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"키워드: {', '.join(alert.keywords)}" if alert.keywords else "키워드: N/A"
                            }
                        ]
                    }
                ]
            }]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return AlertResult(
                            alert_id=alert.id,
                            channel=AlertChannel.SLACK,
                            success=True,
                            sent_at=datetime.now()
                        )
                    else:
                        return AlertResult(
                            alert_id=alert.id,
                            channel=AlertChannel.SLACK,
                            success=False,
                            sent_at=datetime.now(),
                            error=f"HTTP {response.status}"
                        )

        except Exception as e:
            return AlertResult(
                alert_id=alert.id,
                channel=AlertChannel.SLACK,
                success=False,
                sent_at=datetime.now(),
                error=str(e)
            )


class WebhookAlertSender(AlertSenderBase):
    """Webhook 알림 발송기"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL")

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    async def send(self, alert: Alert) -> AlertResult:
        if not self.is_configured:
            return AlertResult(
                alert_id=alert.id,
                channel=AlertChannel.WEBHOOK,
                success=False,
                sent_at=datetime.now(),
                error="Webhook URL not configured"
            )

        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "company_id": alert.company_id,
            "company_name": alert.company_name,
            "score": alert.score,
            "status": alert.status,
            "source": alert.source,
            "priority": alert.priority.value,
            "keywords": alert.keywords,
            "created_at": alert.created_at.isoformat(),
            "details": alert.details
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    success = 200 <= response.status < 300
                    return AlertResult(
                        alert_id=alert.id,
                        channel=AlertChannel.WEBHOOK,
                        success=success,
                        sent_at=datetime.now(),
                        error=None if success else f"HTTP {response.status}"
                    )

        except Exception as e:
            return AlertResult(
                alert_id=alert.id,
                channel=AlertChannel.WEBHOOK,
                success=False,
                sent_at=datetime.now(),
                error=str(e)
            )


class EmailAlertSender(AlertSenderBase):
    """이메일 알림 발송기 (Stub)"""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("ALERT_FROM_EMAIL")
        self.to_emails = os.getenv("ALERT_TO_EMAILS", "").split(",")

    @property
    def is_configured(self) -> bool:
        return all([
            self.smtp_host,
            self.smtp_user,
            self.smtp_password,
            self.from_email,
            any(self.to_emails)
        ])

    async def send(self, alert: Alert) -> AlertResult:
        if not self.is_configured:
            return AlertResult(
                alert_id=alert.id,
                channel=AlertChannel.EMAIL,
                success=False,
                sent_at=datetime.now(),
                error="Email not configured"
            )

        # TODO: 실제 이메일 발송 구현
        # aiosmtplib 등 사용

        logger.info(f"📧 이메일 발송 (stub): {alert.title}")

        return AlertResult(
            alert_id=alert.id,
            channel=AlertChannel.EMAIL,
            success=True,
            sent_at=datetime.now()
        )


class TelegramAlertSender(AlertSenderBase):
    """Telegram Bot API 알림 발송기"""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send(self, alert: Alert) -> AlertResult:
        if not self.is_configured:
            return AlertResult(
                alert_id=alert.id,
                channel=AlertChannel.TELEGRAM,
                success=False,
                sent_at=datetime.now(),
                error="Telegram bot_token or chat_id not configured"
            )

        priority_emoji = {
            AlertPriority.LOW: "\U0001f535",      # blue
            AlertPriority.MEDIUM: "\U0001f7e1",   # yellow
            AlertPriority.HIGH: "\U0001f7e0",     # orange
            AlertPriority.CRITICAL: "\U0001f534",  # red
        }

        emoji = priority_emoji.get(alert.priority, "\u26aa")
        keywords_text = ", ".join(alert.keywords) if alert.keywords else "N/A"

        text = (
            f"{emoji} <b>[{alert.priority.value.upper()}] {alert.title}</b>\n\n"
            f"\U0001f3e2 <b>기업:</b> {alert.company_name}\n"
            f"\U0001f4ca <b>점수:</b> {alert.score} | <b>Status:</b> {alert.status}\n"
            f"\U0001f4f0 <b>소스:</b> {alert.source}\n"
            f"\U0001f50d <b>키워드:</b> {keywords_text}\n\n"
            f"{alert.message}"
        )

        # chat_id: @username 형식이면 그대로, 숫자이면 그대로
        chat_id = self.chat_id
        if not chat_id.startswith("@") and not chat_id.lstrip("-").isdigit():
            chat_id = f"@{chat_id}"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            url = self.API_URL.format(token=self.bot_token)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    body = await response.json()
                    if response.status == 200 and body.get("ok"):
                        logger.info(f"Telegram 발송 성공: {alert.title[:30]}")
                        return AlertResult(
                            alert_id=alert.id,
                            channel=AlertChannel.TELEGRAM,
                            success=True,
                            sent_at=datetime.now()
                        )
                    else:
                        error_msg = body.get("description", f"HTTP {response.status}")
                        logger.warning(f"Telegram 발송 실패: {error_msg}")
                        return AlertResult(
                            alert_id=alert.id,
                            channel=AlertChannel.TELEGRAM,
                            success=False,
                            sent_at=datetime.now(),
                            error=error_msg
                        )

        except Exception as e:
            return AlertResult(
                alert_id=alert.id,
                channel=AlertChannel.TELEGRAM,
                success=False,
                sent_at=datetime.now(),
                error=str(e)
            )


class AlertManager:
    """
    알림 관리자

    Usage:
        manager = AlertManager()
        await manager.send_alert(alert, [AlertChannel.SLACK, AlertChannel.CONSOLE])
    """

    # 기본 알림 규칙
    DEFAULT_RULES = [
        AlertRule(
            id="rule_critical",
            name="Critical Alert",
            min_score=50,
            status_filter=["FAIL"],
            priority=AlertPriority.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.TELEGRAM, AlertChannel.CONSOLE]
        ),
        AlertRule(
            id="rule_warning",
            name="Warning Alert",
            min_score=50,
            status_filter=["WARNING"],
            priority=AlertPriority.MEDIUM,
            channels=[AlertChannel.CONSOLE]
        ),
        AlertRule(
            id="rule_daily",
            name="Daily Summary",
            min_score=0,
            status_filter=["PASS", "WARNING", "FAIL"],
            priority=AlertPriority.LOW,
            channels=[AlertChannel.CONSOLE]
        )
    ]

    def __init__(self):
        self.senders: Dict[AlertChannel, AlertSenderBase] = {
            AlertChannel.CONSOLE: ConsoleAlertSender(),
            AlertChannel.SLACK: SlackAlertSender(),
            AlertChannel.WEBHOOK: WebhookAlertSender(),
            AlertChannel.EMAIL: EmailAlertSender(),
            AlertChannel.TELEGRAM: TelegramAlertSender(),
        }
        self.rules: List[AlertRule] = self.DEFAULT_RULES.copy()
        self.alert_history: List[Alert] = []
        self.result_history: List[AlertResult] = []
        self.cooldown_cache: Dict[str, datetime] = {}
        self.max_history = 1000

    def add_rule(self, rule: AlertRule):
        """알림 규칙 추가"""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """알림 규칙 제거"""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                return True
        return False

    def get_matching_rules(self, alert: Alert) -> List[AlertRule]:
        """알림에 매칭되는 규칙 조회"""
        matching = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # 점수 필터
            if alert.score < rule.min_score:
                continue

            # Status 필터
            if rule.status_filter and alert.status not in rule.status_filter:
                continue

            # 소스 필터
            if rule.source_filter and alert.source not in rule.source_filter:
                continue

            # 기업 필터
            if rule.company_filter and alert.company_id not in rule.company_filter:
                continue

            # Cooldown 체크
            cooldown_key = f"{rule.id}:{alert.company_id}:{alert.source}"
            last_sent = self.cooldown_cache.get(cooldown_key)
            if last_sent:
                elapsed = (datetime.now() - last_sent).total_seconds() / 60
                if elapsed < rule.cooldown_minutes:
                    continue

            matching.append(rule)

        return matching

    async def send_alert(
        self,
        alert: Alert,
        channels: Optional[List[AlertChannel]] = None
    ) -> List[AlertResult]:
        """알림 발송"""
        results = []

        target_channels = channels or [AlertChannel.CONSOLE]

        for channel in target_channels:
            sender = self.senders.get(channel)
            if not sender:
                results.append(AlertResult(
                    alert_id=alert.id,
                    channel=channel,
                    success=False,
                    sent_at=datetime.now(),
                    error=f"Unknown channel: {channel}"
                ))
                continue

            try:
                result = await sender.send(alert)
                results.append(result)
            except Exception as e:
                results.append(AlertResult(
                    alert_id=alert.id,
                    channel=channel,
                    success=False,
                    sent_at=datetime.now(),
                    error=str(e)
                ))

        # 이력 기록
        self.alert_history.append(alert)
        self.result_history.extend(results)

        # 이력 크기 제한
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        if len(self.result_history) > self.max_history * 3:
            self.result_history = self.result_history[-(self.max_history * 3):]

        return results

    async def process_signal(
        self,
        company_id: str,
        company_name: str,
        score: int,
        status: str,
        source: str,
        title: str,
        message: str,
        keywords: List[str] = None
    ) -> List[AlertResult]:
        """리스크 신호 처리 및 알림 발송"""

        # Alert 생성
        alert = Alert(
            id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{company_id}",
            title=title,
            message=message,
            company_id=company_id,
            company_name=company_name,
            score=score,
            status=status,
            source=source,
            priority=self._determine_priority(score, status),
            created_at=datetime.now(),
            keywords=keywords or []
        )

        # 매칭 규칙 조회
        matching_rules = self.get_matching_rules(alert)

        if not matching_rules:
            logger.debug(f"매칭 규칙 없음: {alert.id}")
            return []

        # 모든 채널 수집 (중복 제거)
        all_channels = set()
        for rule in matching_rules:
            for channel in rule.channels:
                all_channels.add(channel)

            # Cooldown 업데이트
            cooldown_key = f"{rule.id}:{alert.company_id}:{alert.source}"
            self.cooldown_cache[cooldown_key] = datetime.now()

        # 알림 발송
        results = await self.send_alert(alert, list(all_channels))

        return results

    def _determine_priority(self, score: int, status: str) -> AlertPriority:
        """우선순위 결정"""
        if score >= 75 or status == "FAIL":
            return AlertPriority.CRITICAL
        elif score >= 60:
            return AlertPriority.HIGH
        elif score >= 50 or status == "WARNING":
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW

    def get_status(self) -> Dict:
        """알림 상태 조회"""
        return {
            "rules_count": len(self.rules),
            "active_rules": len([r for r in self.rules if r.enabled]),
            "channels": {
                channel.value: {
                    "available": True,
                    "configured": getattr(self.senders[channel], "is_configured", True)
                }
                for channel in AlertChannel
            },
            "recent_alerts": len(self.alert_history),
            "recent_results": {
                "total": len(self.result_history[-100:]),
                "success": len([r for r in self.result_history[-100:] if r.success]),
                "failed": len([r for r in self.result_history[-100:] if not r.success])
            }
        }


# 싱글톤 인스턴스
alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """알림 관리자 인스턴스 반환"""
    global alert_manager
    if alert_manager is None:
        alert_manager = AlertManager()
    return alert_manager


if __name__ == "__main__":
    # 테스트 실행
    async def test():
        manager = AlertManager()

        # 테스트 알림 발송
        results = await manager.process_signal(
            company_id="sk_hynix",
            company_name="SK하이닉스",
            score=78,
            status="FAIL",
            source="DART",
            title="[긴급] 특허 침해 소송 공시",
            message="SK하이닉스가 특허 침해 관련 소송에 휘말렸습니다. 상세 내용을 확인하세요.",
            keywords=["특허", "소송", "법률위험"]
        )

        print(f"\n발송 결과: {len(results)} 건")
        for r in results:
            print(f"  - {r.channel.value}: {'성공' if r.success else '실패'}")

        print("\n알림 상태:")
        print(json.dumps(manager.get_status(), indent=2, ensure_ascii=False))

    asyncio.run(test())
