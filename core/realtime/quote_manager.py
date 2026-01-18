"""
实时行情管理模块
提供行情订阅、推送和管理功能
"""
import threading
import time
from datetime import datetime
from typing import Dict, List, Callable, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from core.logger import get_log_manager, LogCategory


class QuoteType(Enum):
    """行情类型"""
    TICK = "tick"           # 逐笔行情
    LEVEL1 = "level1"       # Level1行情
    LEVEL2 = "level2"       # Level2行情
    KLINE_1M = "kline_1m"   # 1分钟K线
    KLINE_5M = "kline_5m"   # 5分钟K线
    KLINE_15M = "kline_15m" # 15分钟K线
    KLINE_30M = "kline_30m" # 30分钟K线
    KLINE_60M = "kline_60m" # 60分钟K线
    KLINE_D = "kline_d"     # 日K线


@dataclass
class TickData:
    """逐笔数据"""
    code: str
    name: str = ""
    price: float = 0.0
    volume: int = 0
    amount: float = 0.0
    bid_price: float = 0.0      # 买一价
    ask_price: float = 0.0      # 卖一价
    bid_volume: int = 0         # 买一量
    ask_volume: int = 0         # 卖一量
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0      # 昨收
    timestamp: datetime = None

    @property
    def change(self) -> float:
        """涨跌额"""
        return self.price - self.pre_close if self.pre_close else 0

    @property
    def change_pct(self) -> float:
        """涨跌幅"""
        if self.pre_close:
            return (self.price - self.pre_close) / self.pre_close * 100
        return 0


@dataclass
class KLineData:
    """K线数据"""
    code: str
    period: str
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0


@dataclass
class QuoteSnapshot:
    """行情快照"""
    code: str
    name: str = ""
    price: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    bid_prices: List[float] = field(default_factory=list)   # 买5档价格
    bid_volumes: List[int] = field(default_factory=list)    # 买5档数量
    ask_prices: List[float] = field(default_factory=list)   # 卖5档价格
    ask_volumes: List[int] = field(default_factory=list)    # 卖5档数量
    timestamp: datetime = None

    @property
    def change(self) -> float:
        return self.price - self.pre_close if self.pre_close else 0

    @property
    def change_pct(self) -> float:
        if self.pre_close:
            return (self.price - self.pre_close) / self.pre_close * 100
        return 0


class QuoteSubscriber(ABC):
    """行情订阅者接口"""

    @abstractmethod
    def on_tick(self, tick: TickData):
        """收到Tick数据"""
        pass

    @abstractmethod
    def on_kline(self, kline: KLineData):
        """收到K线数据"""
        pass

    @abstractmethod
    def on_snapshot(self, snapshot: QuoteSnapshot):
        """收到行情快照"""
        pass


class QuoteCallback:
    """行情回调包装"""

    def __init__(self):
        self.tick_callbacks: List[Callable[[TickData], None]] = []
        self.kline_callbacks: List[Callable[[KLineData], None]] = []
        self.snapshot_callbacks: List[Callable[[QuoteSnapshot], None]] = []

    def add_tick_callback(self, callback: Callable[[TickData], None]):
        if callback not in self.tick_callbacks:
            self.tick_callbacks.append(callback)

    def add_kline_callback(self, callback: Callable[[KLineData], None]):
        if callback not in self.kline_callbacks:
            self.kline_callbacks.append(callback)

    def add_snapshot_callback(self, callback: Callable[[QuoteSnapshot], None]):
        if callback not in self.snapshot_callbacks:
            self.snapshot_callbacks.append(callback)

    def remove_tick_callback(self, callback: Callable):
        if callback in self.tick_callbacks:
            self.tick_callbacks.remove(callback)

    def remove_kline_callback(self, callback: Callable):
        if callback in self.kline_callbacks:
            self.kline_callbacks.remove(callback)

    def remove_snapshot_callback(self, callback: Callable):
        if callback in self.snapshot_callbacks:
            self.snapshot_callbacks.remove(callback)


class QuoteManager:
    """行情管理器"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self.logger = get_log_manager()

        # 订阅的股票代码
        self._subscribed_codes: Set[str] = set()

        # 行情回调
        self._callbacks: Dict[str, QuoteCallback] = {}  # code -> callbacks
        self._global_callbacks = QuoteCallback()        # 全局回调

        # 最新行情缓存
        self._latest_ticks: Dict[str, TickData] = {}
        self._latest_snapshots: Dict[str, QuoteSnapshot] = {}
        self._kline_cache: Dict[str, Dict[str, List[KLineData]]] = {}  # code -> period -> klines

        # 数据源
        self._data_feed = None

        # 状态
        self._running = False
        self._connected = False

        # 线程锁
        self._lock = threading.Lock()

        self._initialized = True

    def set_data_feed(self, data_feed):
        """设置数据源"""
        self._data_feed = data_feed
        if data_feed:
            data_feed.set_quote_manager(self)

    def subscribe(self, codes: List[str], quote_types: List[QuoteType] = None):
        """
        订阅行情

        Args:
            codes: 股票代码列表
            quote_types: 行情类型列表
        """
        with self._lock:
            for code in codes:
                self._subscribed_codes.add(code)
                if code not in self._callbacks:
                    self._callbacks[code] = QuoteCallback()

        if self._data_feed and self._connected:
            self._data_feed.subscribe(codes, quote_types)

        self.logger.info(f"订阅行情: {codes}", LogCategory.DATA)

    def unsubscribe(self, codes: List[str]):
        """取消订阅"""
        with self._lock:
            for code in codes:
                self._subscribed_codes.discard(code)
                if code in self._callbacks:
                    del self._callbacks[code]

        if self._data_feed and self._connected:
            self._data_feed.unsubscribe(codes)

        self.logger.info(f"取消订阅: {codes}", LogCategory.DATA)

    def add_tick_callback(self, callback: Callable[[TickData], None], code: str = None):
        """
        添加Tick回调

        Args:
            callback: 回调函数
            code: 股票代码，None表示全局回调
        """
        if code:
            if code not in self._callbacks:
                self._callbacks[code] = QuoteCallback()
            self._callbacks[code].add_tick_callback(callback)
        else:
            self._global_callbacks.add_tick_callback(callback)

    def add_kline_callback(self, callback: Callable[[KLineData], None], code: str = None):
        """添加K线回调"""
        if code:
            if code not in self._callbacks:
                self._callbacks[code] = QuoteCallback()
            self._callbacks[code].add_kline_callback(callback)
        else:
            self._global_callbacks.add_kline_callback(callback)

    def add_snapshot_callback(self, callback: Callable[[QuoteSnapshot], None], code: str = None):
        """添加快照回调"""
        if code:
            if code not in self._callbacks:
                self._callbacks[code] = QuoteCallback()
            self._callbacks[code].add_snapshot_callback(callback)
        else:
            self._global_callbacks.add_snapshot_callback(callback)

    def remove_callback(self, callback: Callable, code: str = None):
        """移除回调"""
        if code and code in self._callbacks:
            self._callbacks[code].remove_tick_callback(callback)
            self._callbacks[code].remove_kline_callback(callback)
            self._callbacks[code].remove_snapshot_callback(callback)
        else:
            self._global_callbacks.remove_tick_callback(callback)
            self._global_callbacks.remove_kline_callback(callback)
            self._global_callbacks.remove_snapshot_callback(callback)

    def on_tick(self, tick: TickData):
        """处理Tick数据（由数据源调用）"""
        with self._lock:
            self._latest_ticks[tick.code] = tick

        # 触发回调
        self._trigger_tick_callbacks(tick)

    def on_kline(self, kline: KLineData):
        """处理K线数据（由数据源调用）"""
        with self._lock:
            if kline.code not in self._kline_cache:
                self._kline_cache[kline.code] = {}
            if kline.period not in self._kline_cache[kline.code]:
                self._kline_cache[kline.code][kline.period] = []

            klines = self._kline_cache[kline.code][kline.period]
            # 更新或添加K线
            if klines and klines[-1].datetime == kline.datetime:
                klines[-1] = kline
            else:
                klines.append(kline)
                # 保留最近1000根K线
                if len(klines) > 1000:
                    self._kline_cache[kline.code][kline.period] = klines[-1000:]

        # 触发回调
        self._trigger_kline_callbacks(kline)

    def on_snapshot(self, snapshot: QuoteSnapshot):
        """处理行情快照（由数据源调用）"""
        with self._lock:
            self._latest_snapshots[snapshot.code] = snapshot

        # 触发回调
        self._trigger_snapshot_callbacks(snapshot)

    def _trigger_tick_callbacks(self, tick: TickData):
        """触发Tick回调"""
        # 全局回调
        for callback in self._global_callbacks.tick_callbacks:
            try:
                callback(tick)
            except Exception as e:
                self.logger.error(f"Tick回调错误: {e}", LogCategory.DATA)

        # 特定股票回调
        if tick.code in self._callbacks:
            for callback in self._callbacks[tick.code].tick_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    self.logger.error(f"Tick回调错误: {e}", LogCategory.DATA)

    def _trigger_kline_callbacks(self, kline: KLineData):
        """触发K线回调"""
        for callback in self._global_callbacks.kline_callbacks:
            try:
                callback(kline)
            except Exception as e:
                self.logger.error(f"K线回调错误: {e}", LogCategory.DATA)

        if kline.code in self._callbacks:
            for callback in self._callbacks[kline.code].kline_callbacks:
                try:
                    callback(kline)
                except Exception as e:
                    self.logger.error(f"K线回调错误: {e}", LogCategory.DATA)

    def _trigger_snapshot_callbacks(self, snapshot: QuoteSnapshot):
        """触发快照回调"""
        for callback in self._global_callbacks.snapshot_callbacks:
            try:
                callback(snapshot)
            except Exception as e:
                self.logger.error(f"快照回调错误: {e}", LogCategory.DATA)

        if snapshot.code in self._callbacks:
            for callback in self._callbacks[snapshot.code].snapshot_callbacks:
                try:
                    callback(snapshot)
                except Exception as e:
                    self.logger.error(f"快照回调错误: {e}", LogCategory.DATA)

    def get_latest_tick(self, code: str) -> Optional[TickData]:
        """获取最新Tick"""
        return self._latest_ticks.get(code)

    def get_latest_snapshot(self, code: str) -> Optional[QuoteSnapshot]:
        """获取最新快照"""
        return self._latest_snapshots.get(code)

    def get_klines(self, code: str, period: str, count: int = 100) -> List[KLineData]:
        """获取K线数据"""
        if code in self._kline_cache and period in self._kline_cache[code]:
            return self._kline_cache[code][period][-count:]
        return []

    def connect(self) -> bool:
        """连接数据源"""
        if self._data_feed:
            self._connected = self._data_feed.connect()
            if self._connected:
                self.logger.info("行情连接成功", LogCategory.DATA)
                # 重新订阅
                if self._subscribed_codes:
                    self._data_feed.subscribe(list(self._subscribed_codes))
            return self._connected
        return False

    def disconnect(self):
        """断开连接"""
        if self._data_feed:
            self._data_feed.disconnect()
        self._connected = False
        self.logger.info("行情断开连接", LogCategory.DATA)

    def start(self):
        """启动行情服务"""
        if self._running:
            return

        self._running = True
        if self._data_feed:
            self._data_feed.start()
        self.logger.info("行情服务启动", LogCategory.DATA)

    def stop(self):
        """停止行情服务"""
        self._running = False
        if self._data_feed:
            self._data_feed.stop()
        self.logger.info("行情服务停止", LogCategory.DATA)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def subscribed_codes(self) -> List[str]:
        return list(self._subscribed_codes)
