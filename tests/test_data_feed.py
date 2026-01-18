"""
数据源测试
"""
import sys
import threading
import time
import types

import pandas as pd
import pytest

from core.data.cache import data_cache
from core.realtime.data_feed import AkShareDataFeed, SimulatedDataFeed
from core.realtime.quote_manager import QuoteManager


def test_simulated_data_feed_emits_tick():
    """模拟数据源能够产生Tick并推送到行情管理器"""
    manager = QuoteManager()
    feed = SimulatedDataFeed(interval=0.01)
    feed.set_quote_manager(manager)

    ticks = []
    event = threading.Event()

    def on_tick(tick):
        if tick.code == "000001":
            ticks.append(tick)
            event.set()

    manager.add_tick_callback(on_tick)
    feed.connect()
    feed.subscribe(["000001"])
    feed.start()

    assert event.wait(timeout=1.5), "未能在超时时间内收到Tick"

    feed.stop()
    feed.disconnect()
    manager.remove_callback(on_tick)

    assert len(ticks) > 0


def test_akshare_feed_uses_cache(monkeypatch):
    """AkShare数据源会复用缓存，避免重复请求"""
    manager = QuoteManager()
    feed = AkShareDataFeed()
    feed.set_quote_manager(manager)

    fake_module = types.ModuleType("akshare")
    fake_module.calls = 0

    df = pd.DataFrame({
        '代码': ['000001', '000002'],
        '名称': ['平安银行', '万科A'],
        '最新价': [10.5, 15.3],
        '今开': [10.3, 15.0],
        '最高': [10.8, 15.8],
        '最低': [10.1, 14.8],
        '昨收': [10.2, 15.1],
        '成交量': [1000, 2000],
        '成交额': [10500, 30600],
    })

    def fake_spot():
        fake_module.calls += 1
        return df.copy()

    fake_module.stock_zh_a_spot_em = fake_spot
    monkeypatch.setitem(sys.modules, "akshare", fake_module)

    assert feed.connect() is True
    feed.subscribe(["000001"])
    data_cache.invalidate(feed._cache_key)  # type: ignore[attr-defined]

    snapshots = []

    def on_snapshot(snapshot):
        snapshots.append(snapshot)

    manager.add_snapshot_callback(on_snapshot)

    feed._fetch_realtime_data()
    feed._fetch_realtime_data()

    manager.remove_callback(on_snapshot)
    feed.disconnect()

    assert fake_module.calls == 1, "重复调用导致未命中缓存"
    assert snapshots and snapshots[0].code == "000001"
