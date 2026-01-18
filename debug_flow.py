from core.trader.huatai import HuataiTrader
from core.trader.broker import BrokerConfig, BrokerType
from core.trader.rest_client import RestBrokerBase

config = BrokerConfig(broker_type=BrokerType.HUATAI, account="a", password="b", extra={"base_url": "http://mock"})
broker = HuataiTrader(config)
broker._start_polling = lambda: None
broker._stop_polling = lambda: None
responses = {
    ("GET", broker._get_endpoint("ping")): {},
    ("POST", broker._get_endpoint("login")): {"token": "t", "account": {"account_id": "a", "cash": 1000, "market_value": 0, "total_value": 1000, "profit": 0, "profit_pct": 0}},
    ("GET", broker._get_endpoint("account")): {"account_id": "a", "cash": 1000, "market_value": 0, "total_value": 1000, "profit": 0, "profit_pct": 0},
    ("GET", broker._get_endpoint("positions")): {"positions": []},
    ("GET", broker._get_endpoint("orders")): {"orders": []},
    ("GET", broker._get_endpoint("trades")): {"trades": []},
}

original_request = RestBrokerBase._request

def fake_request(self, method, path, **kwargs):
    mapping = responses
    normalized = path
    if normalized.startswith(self.base_url):
        normalized = normalized[len(self.base_url):]
    print('fake request', method, normalized)
    return mapping[(method, normalized)]

RestBrokerBase._request = fake_request
print('connect start')
print('connect result', broker.connect())
print('login result', broker.login())
print('trades result', broker.query_trades())
