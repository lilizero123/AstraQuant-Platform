"""
海通证券 REST 交易接口
"""
from dataclasses import dataclass

from core.trader.broker import BrokerConfig, BrokerFactory, BrokerType
from core.trader.rest_client import RestBrokerBase, RestEndpoints


@dataclass
class HaitongEndpoints(RestEndpoints):
    ping: str = "/haitong/api/v1/ping"
    login: str = "/haitong/api/v1/login"
    logout: str = "/haitong/api/v1/logout"
    order: str = "/haitong/api/v1/orders"
    cancel: str = "/haitong/api/v1/orders/{order_id}/cancel"
    modify: str = "/haitong/api/v1/orders/{order_id}"
    account: str = "/haitong/api/v1/account"
    positions: str = "/haitong/api/v1/positions"
    orders: str = "/haitong/api/v1/orders"
    trades: str = "/haitong/api/v1/trades"


class HaitongTrader(RestBrokerBase):
    """海通证券交易接口"""

    endpoints = HaitongEndpoints()

    def __init__(self, config: BrokerConfig):
        config.extra.setdefault("base_url", config.extra.get("base_url", "https://127.0.0.1:7004"))
        # 默认强制启用签名，方便与生产系统对接
        config.extra.setdefault("sign_method", config.extra.get("sign_method", "hmac_sha512"))
        config.extra.setdefault("verify_ssl", config.extra.get("verify_ssl", True))
        super().__init__(config)


BrokerFactory.register(BrokerType.HAITONG, HaitongTrader)
