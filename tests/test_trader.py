"""
交易接口测试
"""
import pytest
import time
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.trader.broker import (
    BrokerConfig,
    BrokerType,
    BrokerFactory,
    SimulatedBroker,
    TradingEngine,
    AccountInfo,
    OrderResult,
)
from core.trader.huatai import HuataiTrader
from core.strategy.base import OrderSide, OrderStatus, OrderType


class TestBrokerConfig:
    """券商配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = BrokerConfig(broker_type=BrokerType.SIMULATED)
        assert config.broker_type == BrokerType.SIMULATED
        assert config.account == ""
        assert config.extra == {}

    def test_custom_config(self):
        """测试自定义配置"""
        config = BrokerConfig(
            broker_type=BrokerType.HUATAI,
            account="12345678",
            password="password",
            server="127.0.0.1",
            port=8080,
            extra={'initial_capital': 500000}
        )
        assert config.broker_type == BrokerType.HUATAI
        assert config.account == "12345678"
        assert config.extra['initial_capital'] == 500000


class TestBrokerFactory:
    """券商工厂测试"""

    def test_create_simulated(self):
        """测试创建模拟券商"""
        config = BrokerConfig(broker_type=BrokerType.SIMULATED)
        broker = BrokerFactory.create(config)
        assert broker is not None
        assert isinstance(broker, SimulatedBroker)

    def test_get_supported_brokers(self):
        """测试获取支持的券商"""
        brokers = BrokerFactory.get_supported_brokers()
        assert BrokerType.SIMULATED in brokers


class TestSimulatedBroker:
    """模拟券商测试"""

    @pytest.fixture
    def broker(self):
        """创建模拟券商"""
        config = BrokerConfig(
            broker_type=BrokerType.SIMULATED,
            extra={'initial_capital': 100000}
        )
        return SimulatedBroker(config)

    def test_connect(self, broker):
        """测试连接"""
        result = broker.connect()
        assert result == True
        assert broker.is_connected == True
        broker.disconnect()

    def test_login(self, broker):
        """测试登录"""
        broker.connect()
        result = broker.login()
        assert result == True
        assert broker.is_logged_in == True
        broker.disconnect()

    def test_login_without_connect(self, broker):
        """测试未连接时登录"""
        result = broker.login()
        assert result == False

    def test_send_order_buy(self, broker):
        """测试买入订单"""
        broker.connect()
        broker.login()

        result = broker.send_order(
            code='000001',
            side=OrderSide.BUY,
            price=10.0,
            quantity=1000
        )

        assert result.success == True
        assert result.order_id != ""
        assert result.order is not None
        assert result.order.side == OrderSide.BUY

        broker.disconnect()

    def test_send_order_insufficient_funds(self, broker):
        """测试资金不足"""
        broker.connect()
        broker.login()

        # 尝试买入超过资金的数量
        result = broker.send_order(
            code='000001',
            side=OrderSide.BUY,
            price=100.0,
            quantity=100000  # 需要1000万
        )

        assert result.success == False
        assert "资金不足" in result.message

        broker.disconnect()

    def test_send_order_sell_no_position(self, broker):
        """测试无持仓卖出"""
        broker.connect()
        broker.login()

        result = broker.send_order(
            code='000001',
            side=OrderSide.SELL,
            price=10.0,
            quantity=1000
        )

        assert result.success == False
        assert "持仓不足" in result.message

        broker.disconnect()

    def test_cancel_order(self, broker):
        """测试撤单"""
        broker.connect()
        broker.login()

        # 先下单
        result = broker.send_order(
            code='000001',
            side=OrderSide.BUY,
            price=5.0,  # 低价，不会立即成交
            quantity=100
        )

        # 撤单
        cancel_result = broker.cancel_order(result.order_id)
        assert cancel_result == True

        # 查询订单状态
        orders = broker.query_orders()
        order = next((o for o in orders if o.order_id == result.order_id), None)
        assert order is not None
        assert order.status == OrderStatus.CANCELLED

        broker.disconnect()

    def test_query_account(self, broker):
        """测试查询账户"""
        broker.connect()
        broker.login()

        account = broker.query_account()

        assert account is not None
        assert isinstance(account, AccountInfo)
        assert account.cash == 100000  # 初始资金

        broker.disconnect()

    def test_order_fill(self, broker):
        """测试订单成交"""
        broker.connect()
        broker.login()

        # 设置市场价格
        broker.set_market_price('000001', 10.0)

        # 下单（价格等于市场价，应该成交）
        result = broker.send_order(
            code='000001',
            side=OrderSide.BUY,
            price=10.0,
            quantity=100
        )

        # 等待成交
        time.sleep(0.3)

        # 查询订单
        orders = broker.query_orders()
        order = next((o for o in orders if o.order_id == result.order_id), None)

        assert order is not None
        assert order.status == OrderStatus.FILLED

        # 查询持仓
        positions = broker.query_positions()
        assert len(positions) == 1
        assert positions[0].code == '000001'
        assert positions[0].quantity == 100

        broker.disconnect()


class TestTradingEngine:
    """交易引擎测试"""

    @pytest.fixture
    def engine(self):
        """创建交易引擎"""
        engine = TradingEngine()
        config = BrokerConfig(
            broker_type=BrokerType.SIMULATED,
            extra={'initial_capital': 100000}
        )
        broker = SimulatedBroker(config)
        engine.set_broker(broker)
        return engine

    def test_connect_and_login(self, engine):
        """测试连接和登录"""
        assert engine.connect() == True
        assert engine.login() == True
        engine.disconnect()

    def test_trading_flow(self, engine):
        """测试交易流程"""
        engine.connect()
        engine.login()
        engine.start_trading()

        assert engine.is_trading == True

        # 设置市场价格
        engine._broker.set_market_price('000001', 10.0)

        # 买入
        result = engine.buy('000001', 10.0, 100)
        assert result.success == True

        # 等待成交
        time.sleep(0.3)

        # 查询持仓
        positions = engine.get_positions()
        assert len(positions) == 1

        # 查询账户
        account = engine.get_account()
        assert account is not None
        assert account.cash < 100000  # 资金减少

        engine.stop_trading()
        engine.disconnect()

    def test_buy_without_trading(self, engine):
        """测试未启动交易时买入"""
        engine.connect()
        engine.login()
        # 不调用 start_trading()

        result = engine.buy('000001', 10.0, 100)
        assert result.success == False
        assert "未启动" in result.message

        engine.disconnect()

    def test_callbacks(self, engine):
        """测试回调函数"""
        orders_received = []
        trades_received = []

        def on_order(order):
            orders_received.append(order)

        def on_trade(trade):
            trades_received.append(trade)

        engine.on_order = on_order
        engine.on_trade = on_trade

        engine.connect()
        engine.login()
        engine.start_trading()

        engine._broker.set_market_price('000001', 10.0)
        engine.buy('000001', 10.0, 100)

        time.sleep(0.3)

        assert len(orders_received) >= 1
        assert len(trades_received) >= 1

        engine.disconnect()


class TestRestBroker:
    """REST 券商测试（通过Mock验证请求流程）"""

    @pytest.fixture
    def rest_broker(self, monkeypatch):
        """构建带有伪 HTTP 响应的券商实例"""
        endpoints = HuataiTrader.endpoints
        account_payload = {
            "account_id": "mock_account",
            "cash": 1000000,
            "market_value": 500000,
            "total_value": 1500000,
            "profit": 5000,
            "profit_pct": 0.5,
        }
        positions_payload = [
            {"code": "000001", "quantity": 1000, "avg_cost": 10.0, "current_price": 10.5}
        ]
        orders_payload = [
            {
                "order_id": "REST1",
                "code": "000001",
                "side": "buy",
                "price": 10.0,
                "quantity": 1000,
                "status": "filled",
                "create_time": "2024-01-01 09:30:00",
            }
        ]
        trades_payload = [
            {
                "trade_id": "T1",
                "order_id": "REST1",
                "code": "000001",
                "side": "buy",
                "price": 10.0,
                "quantity": 1000,
                "commission": 3.0,
                "trade_time": "2024-01-01 09:30:01",
            }
        ]

        responses = {
            ("GET", endpoints.ping): {},
            ("POST", endpoints.login): {"token": "mock_token", "account": account_payload},
            ("POST", endpoints.logout): {},
            ("GET", endpoints.account): account_payload,
            ("GET", endpoints.positions): {"positions": positions_payload},
            ("GET", endpoints.orders): {"orders": orders_payload},
            ("GET", endpoints.trades): {"trades": trades_payload},
            ("POST", endpoints.order): {"order": orders_payload[0]},
            ("POST", endpoints.cancel.format(order_id="REST1")): {},
        }

        config = BrokerConfig(
            broker_type=BrokerType.HUATAI,
            account="mock_account",
            password="mock_pwd",
            extra={
                "base_url": "http://mock",
                "mock_responses": responses,
            },
        )
        broker = HuataiTrader(config)

        # 禁用自动轮询线程，便于测试
        monkeypatch.setattr(broker, "_start_polling", lambda: None)
        monkeypatch.setattr(broker, "_stop_polling", lambda: None)
        return broker

    def test_rest_connect_and_login(self, rest_broker):
        assert rest_broker.connect() is True
        assert rest_broker.login() is True
        assert rest_broker.is_logged_in is True
        account = rest_broker.query_account()
        assert account is not None
        assert account.cash == 1000000

    def test_rest_send_and_cancel_order(self, rest_broker):
        rest_broker.connect()
        rest_broker.login()
        result = rest_broker.send_order("000001", OrderSide.BUY, 10.0, 1000)
        assert result.success is True
        assert result.order_id == "REST1"
        assert rest_broker.cancel_order("REST1") is True

    def test_rest_queries(self, rest_broker):
        rest_broker.connect()
        rest_broker.login()

        positions = rest_broker.query_positions()
        assert positions and positions[0].code == "000001"

        orders = rest_broker.query_orders()
        assert orders and orders[0].order_id == "REST1"

        trades = rest_broker.query_trades()
        assert trades and trades[0].trade_id == "T1"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
