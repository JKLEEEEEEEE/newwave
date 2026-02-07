"""
실시간 신호 발행 시스템
Risk Monitoring System v2.2

WebSocket을 통해 리스크 신호를 브로드캐스트하는 모듈
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set, List, Dict, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SignalPublisher:
    """WebSocket 신호 발행자"""

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.running = False
        self._polling_task: Optional[asyncio.Task] = None
        self._last_check_time: Dict[str, datetime] = {}

    async def connect(self, websocket: WebSocket):
        """클라이언트 연결"""
        await websocket.accept()
        self.connections.add(websocket)
        logger.info(f"✅ WebSocket 클라이언트 연결됨. 총 {len(self.connections)}개")

        # 연결 시 초기 데이터 전송
        await self._send_initial_data(websocket)

    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        self.connections.discard(websocket)
        logger.info(f"❌ WebSocket 클라이언트 연결 해제. 총 {len(self.connections)}개")

    async def _send_initial_data(self, websocket: WebSocket):
        """초기 연결 시 데이터 전송"""
        try:
            # 연결 확인 메시지
            await websocket.send_json({
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.now().isoformat(),
                "message": "리스크 신호 수신 대기 중"
            })
        except Exception as e:
            logger.error(f"초기 데이터 전송 실패: {e}")

    async def broadcast(self, signal: Dict[str, Any]):
        """모든 클라이언트에 신호 브로드캐스트"""
        if not self.connections:
            return

        # 타임스탬프 추가
        if "timestamp" not in signal:
            signal["timestamp"] = datetime.now().isoformat()

        message = json.dumps(signal, ensure_ascii=False, default=str)

        disconnected = set()
        for websocket in self.connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"브로드캐스트 실패: {e}")
                disconnected.add(websocket)

        # 끊어진 연결 정리
        for ws in disconnected:
            self.disconnect(ws)

    async def publish_signal(self, signal_type: str, company: str, content: str,
                             category: str = "operational", is_urgent: bool = False,
                             source: str = "system", metadata: Dict = None):
        """신호 발행 헬퍼"""
        signal = {
            "type": "signal",
            "signalType": signal_type,
            "company": company,
            "content": content,
            "category": category,
            "isUrgent": is_urgent,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        await self.broadcast(signal)
        logger.info(f"📢 신호 발행: [{signal_type}] {company} - {content[:30]}...")

    async def start_polling(self, news_interval: int = 30, dart_interval: int = 60):
        """데이터 소스 폴링 시작"""
        self.running = True
        logger.info("🚀 신호 폴링 시작")

        news_counter = 0
        dart_counter = 0

        while self.running:
            try:
                # 1. 뉴스 폴링 (news_interval 초 간격)
                if news_counter >= news_interval:
                    news_signals = await self._poll_news()
                    for signal in news_signals:
                        await self.broadcast(signal)
                    news_counter = 0

                # 2. DART 공시 폴링 (dart_interval 초 간격)
                if dart_counter >= dart_interval:
                    dart_signals = await self._poll_dart()
                    for signal in dart_signals:
                        await self.broadcast(signal)
                    dart_counter = 0

                # 3. 주기적 상태 업데이트 (10초마다)
                if len(self.connections) > 0:
                    await self._send_heartbeat()

                await asyncio.sleep(10)
                news_counter += 10
                dart_counter += 10

            except asyncio.CancelledError:
                logger.info("폴링 태스크 취소됨")
                break
            except Exception as e:
                logger.error(f"폴링 에러: {e}")
                await asyncio.sleep(5)

    async def _poll_news(self) -> List[Dict[str, Any]]:
        """뉴스 소스 폴링"""
        # TODO: 실제 뉴스 API 연동 (네이버 뉴스, 구글 뉴스 등)
        # 현재는 시뮬레이션 데이터 반환

        # 실제 구현 시:
        # 1. 뉴스 API 호출
        # 2. 새로운 뉴스 필터링 (마지막 체크 이후)
        # 3. 리스크 분석 (ai_service_v2.analyze_news)
        # 4. 임계치 초과 시 신호 생성

        signals = []

        # 샘플: 랜덤 신호 생성 (데모용)
        # import random
        # if random.random() < 0.1:  # 10% 확률
        #     signals.append({
        #         "type": "signal",
        #         "signalType": "NEWS",
        #         "company": "SK하이닉스",
        #         "content": "[긴급] 특허 소송 관련 추가 보도",
        #         "category": "legal",
        #         "isUrgent": False,
        #         "source": "뉴스 폴링"
        #     })

        return signals

    async def _poll_dart(self) -> List[Dict[str, Any]]:
        """DART 공시 폴링"""
        # TODO: DART API 연동
        # 현재는 빈 리스트 반환

        # 실제 구현 시:
        # 1. DART API 호출 (최신 공시)
        # 2. 새로운 공시 필터링
        # 3. 중요 공시 판별 (횡령, 소송, 워크아웃 등)
        # 4. 신호 생성

        signals = []
        return signals

    async def _send_heartbeat(self):
        """연결 상태 확인 하트비트"""
        await self.broadcast({
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat(),
            "connections": len(self.connections)
        })

    def stop(self):
        """폴링 중지"""
        self.running = False
        if self._polling_task:
            self._polling_task.cancel()
        logger.info("🛑 신호 폴링 중지")

    async def close_all(self):
        """모든 연결 종료"""
        for websocket in list(self.connections):
            try:
                await websocket.close()
            except Exception:
                pass
        self.connections.clear()


# 싱글톤 인스턴스
signal_publisher = SignalPublisher()


# ========================================
# 신호 타입 정의
# ========================================

class SignalTypes:
    """신호 타입 상수"""
    LEGAL_CRISIS = "LEGAL_CRISIS"  # 법적 위기
    MARKET_CRISIS = "MARKET_CRISIS"  # 시장 위기
    OPERATIONAL = "OPERATIONAL"  # 운영 리스크
    FINANCIAL = "FINANCIAL"  # 재무 리스크
    SUPPLY_CHAIN = "SUPPLY_CHAIN"  # 공급망 리스크
    GOVERNANCE = "GOVERNANCE"  # 지배구조 리스크
    NEWS = "NEWS"  # 뉴스 감지
    DISCLOSURE = "DISCLOSURE"  # 공시 감지


class SignalSeverity:
    """신호 심각도"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ========================================
# 유틸리티 함수
# ========================================

def create_signal(
    signal_type: str,
    company: str,
    content: str,
    category: str = "operational",
    severity: int = SignalSeverity.MEDIUM,
    source: str = "system",
    metadata: Dict = None
) -> Dict[str, Any]:
    """신호 객체 생성 헬퍼"""
    return {
        "type": "signal",
        "signalType": signal_type,
        "company": company,
        "content": content,
        "category": category,
        "severity": severity,
        "isUrgent": severity >= SignalSeverity.HIGH,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
