from core.trader.huatai import HuataiTrader
from core.trader.broker import BrokerConfig, BrokerType

config = BrokerConfig(
    broker_type=BrokerType.HUATAI,
    account='mock_account',
    password='mock_pwd',
    extra={'base_url': 'http://mock'}
)

broker = HuataiTrader(config)
account_payload = {
    'account_id': 'mock_account',
    'cash': 1000000,
    'market_value': 500000,
    'total_value': 1500000,
    'profit': 5000,
    'profit_pct': 0.5,
}
pos_payload = [{'code': '000001', 'quantity': 1000, 'avg_cost': 10.0, 'current_price': 10.5}]
orders_payload = [{'order_id': 'REST1', 'code': '000001', 'side': 'buy', 'price': 10.0, 'quantity': 1000, 'status': 'filled', 'create_time': '2024-01-01 09:30:00'}]
trades_payload = [{'trade_id': 'T1', 'order_id': 'REST1', 'code': '000001', 'side': 'buy', 'price': 10.0, 'quantity': 1000, 'commission': 3.0, 'trade_time': '2024-01-01 09:30:01'}]
responses = {
    ('GET', broker._get_endpoint('ping')): {},
    ('POST', broker._get_endpoint('login')): {'token': 'mock_token', 'account': account_payload},
    ('GET', broker._get_endpoint('account')): account_payload,
    ('GET', broker._get_endpoint('positions')): {'positions': pos_payload},
    ('GET', broker._get_endpoint('orders')): {'orders': orders_payload},
    ('GET', broker._get_endpoint('trades')): {'trades': trades_payload},
}

def fake_request(method, path, **kwargs):
    print('adapter called', method, path)
    return responses[(method.upper(), path)]

broker.set_request_adapter(fake_request)
broker._start_polling = lambda: None
broker._stop_polling = lambda: None
print('connect', broker.connect())
print('login', broker.login())
print('trades', broker.query_trades())
