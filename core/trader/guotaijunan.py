"""
国泰君安 REST 交易接口
"""
from dataclasses import dataclass

from core.trader.broker import BrokerConfig, BrokerFactory, BrokerType
from core.trader.rest_client import RestBrokerBase, RestEndpoints


@dataclass
class GuotaiEndpoints(RestEndpoints):
    ping: str = "/gtja/api/v1/ping"
    login: str = "/gtja/api/v1/login"
    logout: str = "/gtja/api/v1/logout"
    order: str = "/gtja/api/v1/orders"
    cancel: str = "/gtja/api/v1/orders/{order_id}/cancel"
    modify: str = "/gtja/api/v1/orders/{order_id}"
    account: str = "/gtja/api/v1/account"
    positions: str = "/gtja/api/v1/positions"
    orders: str = "/gtja/api/v1/orders"
    trades: str = "/gtja/api/v1/trades"


class GuotaiJunanTrader(RestBrokerBase):
    """国泰君安接口"""

    endpoints = GuotaiEndpoints()

    def __init__(self, config: BrokerConfig):
        config.extra.setdefault("base_url", config.extra.get("base_url", "http://127.0.0.1:7003"))
        config.extra.setdefault("timeout", config.extra.get("timeout", 8))
        super().__init__(config)


BrokerFactory.register(BrokerType.GUOTAIJUNAN, GuotaiJunanTrader)
