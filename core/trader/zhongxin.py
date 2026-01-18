"""
中信证券 REST 交易接口
"""
from dataclasses import dataclass

from core.trader.broker import BrokerConfig, BrokerFactory, BrokerType
from core.trader.rest_client import RestBrokerBase, RestEndpoints


@dataclass
class ZhongxinEndpoints(RestEndpoints):
    ping: str = "/zttrade/api/ping"
    login: str = "/zttrade/api/login"
    logout: str = "/zttrade/api/logout"
    order: str = "/zttrade/api/orders"
    cancel: str = "/zttrade/api/orders/{order_id}/cancel"
    modify: str = "/zttrade/api/orders/{order_id}"
    account: str = "/zttrade/api/account"
    positions: str = "/zttrade/api/positions"
    orders: str = "/zttrade/api/orders"
    trades: str = "/zttrade/api/trades"


class ZhongxinTrader(RestBrokerBase):
    """中信证券接口"""

    endpoints = ZhongxinEndpoints()

    def __init__(self, config: BrokerConfig):
        config.extra.setdefault("base_url", config.extra.get("base_url", "http://127.0.0.1:7002"))
        super().__init__(config)


BrokerFactory.register(BrokerType.ZHONGXIN, ZhongxinTrader)
