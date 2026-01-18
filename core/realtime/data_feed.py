"""
数据源模块
提供实时行情数据的获取
"""
import csv
import threading
import time
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from abc import ABC, abstractmethod

from core.logger import get_log_manager, LogCategory
from core.data.cache import data_cache
from .quote_manager import (
    QuoteManager, QuoteType, TickData, KLineData, QuoteSnapshot
)


class DataFeed(ABC):
    """数据源基类"""

    def __init__(self):
        self.logger = get_log_manager()
        self._quote_manager: Optional[QuoteManager] = None
        self._running = False
        self._connected = False

    def set_quote_manager(self, manager: QuoteManager):
        """设置行情管理器"""
        self._quote_manager = manager

    @abstractmethod
    def connect(self) -> bool:
        """连接数据源"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def subscribe(self, codes: List[str], quote_types: List[QuoteType] = None):
        """订阅行情"""
        pass

    @abstractmethod
    def unsubscribe(self, codes: List[str]):
        """取消订阅"""
        pass

    @abstractmethod
    def start(self):
        """启动数据推送"""
        pass

    @abstractmethod
    def stop(self):
        """停止数据推送"""
        pass

    def push_tick(self, tick: TickData):
        """推送Tick数据"""
        if self._quote_manager:
            self._quote_manager.on_tick(tick)

    def push_kline(self, kline: KLineData):
        """推送K线数据"""
        if self._quote_manager:
            self._quote_manager.on_kline(kline)

    def push_snapshot(self, snapshot: QuoteSnapshot):
        """推送行情快照"""
        if self._quote_manager:
            self._quote_manager.on_snapshot(snapshot)


class SimulatedDataFeed(DataFeed):
    """模拟数据源（用于测试和演示）"""

    # 模拟股票数据
    STOCK_DATA = {
        '000001': {'name': '平安银行', 'price': 10.50, 'pre_close': 10.45},
        '000002': {'name': '万科A', 'price': 8.20, 'pre_close': 8.15},
        '600000': {'name': '浦发银行', 'price': 7.80, 'pre_close': 7.75},
        '600036': {'name': '招商银行', 'price': 32.50, 'pre_close': 32.30},
        '601318': {'name': '中国平安', 'price': 45.60, 'pre_close': 45.20},
    }

    def __init__(self, interval: float = 1.0, volatility: float = 0.01, seed: Optional[int] = None):
        """
        初始化模拟数据源

        Args:
            interval: 数据推送间隔（秒）
            volatility: 单次波动范围（例如 0.01 代表 ±1%）
            seed: 随机种子，便于回放
        """
        super().__init__()
        self.interval = interval
        self.volatility = max(0.0005, volatility)
        if seed is not None:
            random.seed(seed)
        self._subscribed_codes: List[str] = []
        self._thread: Optional[threading.Thread] = None
        self._stock_prices: Dict[str, float] = {}
        self._stock_volumes: Dict[str, int] = {}
        self._limit_pct = 0.1  # 默认 ±10%

        # 初始化价格
        for code, data in self.STOCK_DATA.items():
            self._stock_prices[code] = data['price']
            self._stock_volumes[code] = 0

    def connect(self) -> bool:
        """连接（模拟）"""
        self._connected = True
        self.logger.info("模拟数据源连接成功", LogCategory.DATA)
        return True

    def disconnect(self):
        """断开连接"""
        self._connected = False
        self.logger.info("模拟数据源断开连接", LogCategory.DATA)

    def subscribe(self, codes: List[str], quote_types: List[QuoteType] = None):
        """订阅行情"""
        for code in codes:
            if code not in self._subscribed_codes:
                self._subscribed_codes.append(code)
        self.logger.info(f"模拟订阅: {codes}", LogCategory.DATA)

    def unsubscribe(self, codes: List[str]):
        """取消订阅"""
        for code in codes:
            if code in self._subscribed_codes:
                self._subscribed_codes.remove(code)

    def start(self):
        """启动数据推送"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.logger.info("模拟数据源启动", LogCategory.DATA)

    def stop(self):
        """停止数据推送"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("模拟数据源停止", LogCategory.DATA)

    def _run(self):
        """数据推送线程"""
        while self._running:
            try:
                self._generate_data()
                time.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"模拟数据生成错误: {e}", LogCategory.DATA)

    def _generate_data(self):
        """生成模拟数据"""
        for code in self._subscribed_codes:
            if code not in self.STOCK_DATA:
                continue

            stock_info = self.STOCK_DATA[code]

            # 模拟价格波动
            change_pct = (random.random() - 0.5) * 2 * self.volatility
            current_price = self._stock_prices.get(code, stock_info['price'])
            new_price = round(current_price * (1 + change_pct), 2)

            # 限制涨跌幅 (±10%)
            pre_close = stock_info['pre_close']
            max_price = round(pre_close * (1 + self._limit_pct), 2)
            min_price = round(pre_close * (1 - self._limit_pct), 2)
            new_price = max(min_price, min(max_price, new_price))

            self._stock_prices[code] = new_price

            # 模拟成交量
            volume = random.randint(100, 10000) * 100
            self._stock_volumes[code] = self._stock_volumes.get(code, 0) + volume

            # 生成Tick数据
            tick = TickData(
                code=code,
                name=stock_info['name'],
                price=new_price,
                volume=volume,
                amount=new_price * volume,
                bid_price=round(new_price - 0.01, 2),
                ask_price=round(new_price + 0.01, 2),
                bid_volume=random.randint(10, 100) * 100,
                ask_volume=random.randint(10, 100) * 100,
                open=stock_info['price'],
                high=max(new_price, stock_info['price']),
                low=min(new_price, stock_info['price']),
                pre_close=pre_close,
                timestamp=datetime.now()
            )

            self.push_tick(tick)

            # 生成快照数据
            snapshot = QuoteSnapshot(
                code=code,
                name=stock_info['name'],
                price=new_price,
                open=stock_info['price'],
                high=max(new_price, stock_info['price']),
                low=min(new_price, stock_info['price']),
                pre_close=pre_close,
                volume=self._stock_volumes[code],
                amount=self._stock_volumes[code] * new_price,
                bid_prices=[round(new_price - 0.01 * i, 2) for i in range(1, 6)],
                bid_volumes=[random.randint(10, 100) * 100 for _ in range(5)],
                ask_prices=[round(new_price + 0.01 * i, 2) for i in range(1, 6)],
                ask_volumes=[random.randint(10, 100) * 100 for _ in range(5)],
                timestamp=datetime.now()
            )

            self.push_snapshot(snapshot)


class CSVDataFeed(DataFeed):
    """基于本地 CSV 的行情回放"""

    def __init__(
        self,
        file_path: str,
        datetime_column: str = "datetime",
        code_column: str = "code",
        loop: bool = False,
        speed: float = 1.0,
    ):
        super().__init__()
        self.file_path = Path(file_path)
        self.datetime_column = datetime_column
        self.code_column = code_column
        self.loop = loop
        self.speed = max(0.1, speed)
        self._prepared_rows: List[Tuple[QuoteSnapshot, float]] = []
        self._subscribed_codes: List[str] = []
        self._thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV 行情文件不存在: {self.file_path}")
        self._prepared_rows = self._load_rows()
        self._connected = True
        self.logger.info(f"CSV 数据源加载 {len(self._prepared_rows)} 条记录", LogCategory.DATA)
        return True

    def disconnect(self):
        self._connected = False
        self._prepared_rows = []

    def subscribe(self, codes: List[str], quote_types: List[QuoteType] = None):
        for code in codes:
            if code not in self._subscribed_codes:
                self._subscribed_codes.append(code)

    def unsubscribe(self, codes: List[str]):
        for code in codes:
            if code in self._subscribed_codes:
                self._subscribed_codes.remove(code)

    def start(self):
        if self._running:
            return
        if not self._connected:
            self.connect()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def replay_once(self):
        """同步回放一遍数据（主要用于测试）"""
        if not self._connected:
            self.connect()
        was_running = self._running
        self._running = True
        try:
            self._emit_rows()
        finally:
            self._running = was_running

    def _run(self):
        while self._running:
            self._emit_rows()
            if not self.loop:
                break
        self._running = False

    def _emit_rows(self):
        prev_interval = 0.0
        for snapshot, interval in self._prepared_rows:
            if self._subscribed_codes and snapshot.code not in self._subscribed_codes:
                continue
            if not self._running:
                break
            sleep_interval = interval / self.speed if interval > 0 else prev_interval / self.speed
            if sleep_interval > 0:
                time.sleep(min(sleep_interval, 5))
            self.push_snapshot(snapshot)
            prev_interval = interval

    def _load_rows(self) -> List[Tuple[QuoteSnapshot, float]]:
        rows: List[Tuple[QuoteSnapshot, float]] = []
        if not self.file_path.exists():
            return rows
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            prev_dt: Optional[datetime] = None
            for raw in reader:
                code = raw.get(self.code_column)
                if not code:
                    continue
                dt = self._parse_dt(raw.get(self.datetime_column))
                price = float(raw.get("close") or raw.get("price") or 0)
                snapshot = QuoteSnapshot(
                    code=code,
                    name=str(raw.get("name") or ""),
                    price=price,
                    open=float(raw.get("open") or price),
                    high=float(raw.get("high") or price),
                    low=float(raw.get("low") or price),
                    pre_close=float(raw.get("pre_close") or raw.get("previous_close") or price),
                    volume=int(float(raw.get("volume") or 0)),
                    amount=float(raw.get("amount") or price * float(raw.get("volume") or 0)),
                    timestamp=dt or datetime.now(),
                )
                interval = 0.0
                if prev_dt and dt:
                    interval = max((dt - prev_dt).total_seconds(), 0.0)
                rows.append((snapshot, interval))
                prev_dt = dt
        return rows

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None


class AkShareDataFeed(DataFeed):
    """AkShare数据源"""

    def __init__(self):
        super().__init__()
        self._subscribed_codes: List[str] = []
        self._thread: Optional[threading.Thread] = None
        self._ak = None
        self._cache_key = "akshare_spot_dataframe"
        self._cache_ttl = 2.0

    def connect(self) -> bool:
        """连接AkShare"""
        try:
            import akshare as ak
            self._ak = ak
            self._connected = True
            self.logger.info("AkShare数据源连接成功", LogCategory.DATA)
            return True
        except ImportError:
            self.logger.warning("AkShare 未安装，尝试自动安装...", LogCategory.DATA)
            if self._install_akshare():
                try:
                    import akshare as ak
                    self._ak = ak
                    self._connected = True
                    self.logger.info("自动安装 AkShare 成功", LogCategory.DATA)
                    return True
                except Exception as err:
                    self.logger.error(f"自动安装 AkShare 后仍无法导入: {err}", LogCategory.DATA)
            else:
                self.logger.error("AkShare 未安装，且自动安装失败", LogCategory.DATA)
            return False
        except Exception as e:
            self.logger.error(f"AkShare连接失败: {e}", LogCategory.DATA)
            return False

    def disconnect(self):
        """断开连接"""
        self._connected = False
        self._ak = None

    def subscribe(self, codes: List[str], quote_types: List[QuoteType] = None):
        """订阅行情"""
        for code in codes:
            if code not in self._subscribed_codes:
                self._subscribed_codes.append(code)

    def unsubscribe(self, codes: List[str]):
        """取消订阅"""
        for code in codes:
            if code in self._subscribed_codes:
                self._subscribed_codes.remove(code)

    def start(self):
        """启动数据推送"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止数据推送"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        """数据推送线程"""
        while self._running:
            try:
                self._fetch_realtime_data()
                time.sleep(3)  # AkShare限制请求频率
            except Exception as e:
                self.logger.error(f"AkShare数据获取错误: {e}", LogCategory.DATA)
                time.sleep(5)

    def _fetch_realtime_data(self):
        """获取实时数据"""
        if not self._ak or not self._subscribed_codes:
            return

        try:
            # 优先使用缓存，降低请求频率
            df = data_cache.get(self._cache_key)
            if df is None:
                df = self._ak.stock_zh_a_spot_em()
                data_cache.set(self._cache_key, df, ttl=self._cache_ttl)
            else:
                df = df.copy(deep=False)

            for code in self._subscribed_codes:
                # 查找股票数据
                stock_data = df[df['代码'] == code]
                if stock_data.empty:
                    continue

                row = stock_data.iloc[0]

                snapshot = QuoteSnapshot(
                    code=code,
                    name=str(row.get('名称', '')),
                    price=float(row.get('最新价', 0)),
                    open=float(row.get('今开', 0)),
                    high=float(row.get('最高', 0)),
                    low=float(row.get('最低', 0)),
                    pre_close=float(row.get('昨收', 0)),
                    volume=int(row.get('成交量', 0)),
                    amount=float(row.get('成交额', 0)),
                    timestamp=datetime.now()
                )

                self.push_snapshot(snapshot)

        except Exception as e:
            self.logger.error(f"获取实时数据失败: {e}", LogCategory.DATA)

    def _install_akshare(self) -> bool:
        """在可写环境中尝试安装 akshare"""
        if getattr(sys, "frozen", False):
            self.logger.error("打包环境无法自动安装 AkShare，请在构建时包含依赖", LogCategory.DATA)
            return False
        try:
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "akshare",
                    "-i",
                    "https://pypi.tuna.tsinghua.edu.cn/simple",
                ]
            )
            return True
        except Exception as err:
            self.logger.error(f"自动安装 AkShare 失败: {err}", LogCategory.DATA)
            return False
