"""
华泰证券 REST 交易接口
"""
from dataclasses import dataclass

from core.trader.broker import BrokerConfig, BrokerFactory, BrokerType
from core.trader.rest_client import RestBrokerBase, RestEndpoints


@dataclass
class HuataiEndpoints(RestEndpoints):
    """华泰证券默认 REST 路径"""

    ping: str = "/xtquant/ping"
    login: str = "/xtquant/auth/login"
    logout: str = "/xtquant/auth/logout"
    order: str = "/xtquant/order"
    cancel: str = "/xtquant/order/{order_id}/cancel"
    modify: str = "/xtquant/order/{order_id}"
    account: str = "/xtquant/account"
    positions: str = "/xtquant/positions"
    orders: str = "/xtquant/orders"
    trades: str = "/xtquant/trades"


class HuataiTrader(RestBrokerBase):
    """华泰交易接口实现"""

    endpoints = HuataiEndpoints()

    def __init__(self, config: BrokerConfig):
        config.extra.setdefault("base_url", config.extra.get("base_url", "http://127.0.0.1:7001"))
        config.extra.setdefault("poll_interval", config.extra.get("poll_interval", 2))
        super().__init__(config)


# 在导入时注册
BrokerFactory.register(BrokerType.HUATAI, HuataiTrader)
