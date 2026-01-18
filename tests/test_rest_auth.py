from datetime import datetime

from core.trader.broker import BrokerConfig, BrokerType
from core.trader.rest_client import RestBrokerBase, RestEndpoints


class DummyRestBroker(RestBrokerBase):
    endpoints = RestEndpoints(order="/api/order")

    def connect(self):
        return True

    def disconnect(self):
        pass

    def login(self):
        return True

    def logout(self):
        pass

    def send_order(self, *args, **kwargs):
        raise NotImplementedError

    def cancel_order(self, *args, **kwargs):
        raise NotImplementedError

    def modify_order(self, *args, **kwargs):
        raise NotImplementedError

    def query_account(self):
        return None

    def query_positions(self):
        return []

    def query_orders(self, status=None):
        return []

    def query_trades(self):
        return []


def test_rest_request_signature():
    captured = {}

    def adapter(method, path, headers=None, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["headers"] = headers or {}
        captured["payload"] = kwargs
        return {"status": "ok"}

    config = BrokerConfig(
        broker_type=BrokerType.HUATAI,
        extra={
            "base_url": "https://mock",
            "api_key": "demo",
            "api_secret": "secret",
            "request_adapter": adapter,
            "clock": lambda: datetime(2024, 1, 1, 9, 30, 0),
        },
    )
    broker = DummyRestBroker(config)

    broker._request("POST", "/api/order", json={"price": 10}, params={"code": "000001"})

    headers = captured["headers"]
    assert headers["X-API-Key"] == "demo"
    expected_payload = "code=000001|{\"price\":10}"
    expected_message = f"POST|/api/order|{expected_payload}|2024-01-01T09:30:00"
    import hashlib
    import hmac

    expected_signature = hmac.new(
        b"secret",
        expected_message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert headers["X-Signature"] == expected_signature
