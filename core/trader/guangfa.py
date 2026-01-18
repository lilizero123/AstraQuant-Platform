"""
广发证券 REST 交易接口
"""
from dataclasses import dataclass

from core.trader.broker import BrokerConfig, BrokerFactory, BrokerType
from core.trader.rest_client import RestBrokerBase, RestEndpoints


@dataclass
class GuangfaEndpoints(RestEndpoints):
    ping: str = "/gf/api/ping"
    login: str = "/gf/api/login"
    logout: str = "/gf/api/logout"
    order: str = "/gf/api/orders"
    cancel: str = "/gf/api/orders/{order_id}/cancel"
    modify: str = "/gf/api/orders/{order_id}"
    account: str = "/gf/api/account"
    positions: str = "/gf/api/positions"
    orders: str = "/gf/api/orders"
    trades: str = "/gf/api/trades"


class GuangfaTrader(RestBrokerBase):
    """广发证券交易接口"""

    endpoints = GuangfaEndpoints()

    def __init__(self, config: BrokerConfig):
        config.extra.setdefault("base_url", config.extra.get("base_url", "https://127.0.0.1:7005"))
        config.extra.setdefault("verify_ssl", config.extra.get("verify_ssl", True))
        super().__init__(config)


BrokerFactory.register(BrokerType.GUANGFA, GuangfaTrader)
