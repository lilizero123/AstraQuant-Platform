from core.trader.huatai import HuataiTrader
from core.trader.broker import BrokerConfig, BrokerType

config = BrokerConfig(broker_type=BrokerType.HUATAI, account='a', password='b', extra={'base_url': 'http://mock'})
broker = HuataiTrader(config)

account_payload = {
    'account_id': 'a',
    'cash': 1000,
    'market_value': 0,
    'total_value': 1000,
    'profit': 0,
    'profit_pct': 0
}
responses = {
    ('GET', broker._get_endpoint('ping')): {},
    ('POST', broker._get_endpoint('login')): {'token': 'token', 'account': account_payload},
    ('GET', broker._get_endpoint('account')): account_payload,
    ('GET', broker._get_endpoint('positions')): {'positions': []},
    ('GET', broker._get_endpoint('orders')): {'orders': []},
    ('GET', broker._get_endpoint('trades')): {'trades': [{'trade_id': 'T', 'order_id': 'O', 'code': '000001', 'side': 'buy', 'price': 10, 'quantity': 100, 'commission': 1, 'trade_time': '2024-01-01 09:30:00'}]}
}

def fake(method, path, **kwargs):
    print('adapter invoked', method, path)
    return responses[(method.upper(), path)]

broker.set_request_adapter(fake)
broker._start_polling = lambda: None
broker._stop_polling = lambda: None
print('connect', broker.connect())
print('login', broker.login())
print('trades', broker.query_trades())
