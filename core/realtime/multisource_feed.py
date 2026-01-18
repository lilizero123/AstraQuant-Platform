"""
多数据源 HTTP 行情 DataFeed。
"""
import threading
import time
from typing import Dict, List, Optional

from core.data_sources import MarketDataService
from core.logger import get_log_manager, LogCategory
from core.realtime.quote_manager import QuoteSnapshot

from .data_feed import DataFeed


class MultiSourceHTTPFeed(DataFeed):
    """轮询公开数据源得到实时行情，适用于无法接入正式 API 的场景。"""

    def __init__(self, tushare_token: str = "", interval: float = 2.0):
        super().__init__()
        self.interval = max(1.0, float(interval))
        self.service = MarketDataService(tushare_token=tushare_token)
        self.logger = get_log_manager()
        self._subscribed: List[str] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        self._connected = True
        self.logger.info("多数据源行情已连接", LogCategory.DATA)
        return True

    def disconnect(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._connected = False

    def subscribe(self, codes: List[str], quote_types=None):
        for code in codes:
            if code not in self._subscribed:
                self._subscribed.append(code)

    def unsubscribe(self, codes: List[str]):
        for code in codes:
            if code in self._subscribed:
                self._subscribed.remove(code)

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("多数据源行情开始推送", LogCategory.DATA)

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    # ------------------------ 内部轮询 ------------------------
    def _run_loop(self):
        while not self._stop_event.wait(self.interval):
            if not self._subscribed:
                continue
            try:
                data = self.service.get_realtime_quotes(self._subscribed)
                for record in data.values():
                    snapshot = self._record_to_snapshot(record)
                    self.push_snapshot(snapshot)
            except Exception as exc:  # pragma: no cover - 网络异常
                self.logger.warning(f"多数据源行情抓取失败: {exc}", LogCategory.DATA)

    @staticmethod
    def _record_to_snapshot(record) -> QuoteSnapshot:
        return QuoteSnapshot(
            code=record.code,
            name=record.name,
            price=record.price,
            open=record.open,
            high=record.high,
            low=record.low,
            pre_close=record.pre_close,
            volume=int(record.volume),
            amount=record.amount,
            timestamp=record.timestamp,
        )
