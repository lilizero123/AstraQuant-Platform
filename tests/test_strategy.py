"""
策略基类测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.strategy.base import (
    BaseStrategy, Bar, Order, Trade, Position,
    OrderType, OrderSide, OrderStatus
)


class SimpleStrategy(BaseStrategy):
    """简单测试策略"""

    def on_bar(self, bar: Bar):
        # 简单的买入逻辑
        if self.position == 0 and bar.close < 100:
            self.buy(bar.close, 100)
        elif self.position > 0 and bar.close > 110:
            self.sell(bar.close, self.position)


class TestBar:
    """K线数据测试"""

    def test_bar_creation(self):
        """测试K线创建"""
        bar = Bar(
            datetime=datetime.now(),
            open=10.0,
            high=11.0,
            low=9.0,
            close=10.5,
            volume=1000
        )

        assert bar.open == 10.0
        assert bar.high == 11.0
        assert bar.low == 9.0
        assert bar.close == 10.5
        assert bar.volume == 1000


class TestPosition:
    """持仓测试"""

    def test_position_profit(self):
        """测试持仓盈亏计算"""
        pos = Position(
            code='000001',
            quantity=1000,
            avg_cost=10.0,
            current_price=11.0
        )

        assert pos.market_value == 11000
        assert pos.profit == 1000
        assert pos.profit_pct == pytest.approx(10.0)

    def test_position_loss(self):
        """测试持仓亏损计算"""
        pos = Position(
            code='000001',
            quantity=1000,
            avg_cost=10.0,
            current_price=9.0
        )

        assert pos.profit == -1000
        assert pos.profit_pct == pytest.approx(-10.0)


class TestBaseStrategy:
    """策略基类测试"""

    @pytest.fixture
    def strategy(self):
        """创建策略实例"""
        s = SimpleStrategy()
        s.set_capital(1000000)
        return s

    def test_initial_state(self, strategy):
        """测试初始状态"""
        assert strategy.cash == 1000000
        assert strategy.initial_capital == 1000000
        assert strategy.position == 0
        assert len(strategy.positions) == 0
        assert len(strategy.orders) == 0
        assert len(strategy.trades) == 0

    def test_buy_order(self, strategy):
        """测试买入订单"""
        strategy._current_code = '000001'

        order = strategy.buy(10.0, 100)

        assert order is not None
        assert order.side == OrderSide.BUY
        assert order.price == 10.0
        assert order.quantity == 100
        assert order.status == OrderStatus.SUBMITTED

    def test_buy_insufficient_funds(self, strategy):
        """测试资金不足"""
        strategy._current_code = '000001'
        strategy.cash = 100  # 设置很少的资金

        order = strategy.buy(10.0, 100)

        assert order is None

    def test_buy_quantity_round(self, strategy):
        """测试买入数量取整"""
        strategy._current_code = '000001'

        order = strategy.buy(10.0, 150)  # 150会被取整为100

        assert order.quantity == 100

    def test_sell_order(self, strategy):
        """测试卖出订单"""
        strategy._current_code = '000001'
        strategy.positions['000001'] = Position(
            code='000001',
            quantity=1000,
            avg_cost=10.0
        )

        order = strategy.sell(11.0, 500)

        assert order is not None
        assert order.side == OrderSide.SELL
        assert order.quantity == 500

    def test_sell_insufficient_position(self, strategy):
        """测试持仓不足"""
        strategy._current_code = '000001'

        order = strategy.sell(10.0, 100)

        assert order is None

    def test_cancel_order(self, strategy):
        """测试撤单"""
        strategy._current_code = '000001'
        order = strategy.buy(10.0, 100)

        result = strategy.cancel_order(order.order_id)

        assert result == True
        assert order.status == OrderStatus.CANCELLED

    def test_on_bar_callback(self, strategy):
        """测试K线回调"""
        bar = Bar(
            datetime=datetime.now(),
            open=95.0,
            high=96.0,
            low=94.0,
            close=95.0,
            volume=1000
        )

        strategy._on_bar('000001', bar)

        # 应该触发买入
        assert len(strategy.orders) == 1
        assert strategy.orders[0].side == OrderSide.BUY

    def test_order_filled(self, strategy):
        """测试订单成交"""
        strategy._current_code = '000001'
        order = strategy.buy(10.0, 100)

        trade = Trade(
            trade_id='T001',
            order_id=order.order_id,
            code='000001',
            side=OrderSide.BUY,
            price=10.0,
            quantity=100,
            commission=3.0,
            trade_time=datetime.now()
        )

        strategy._on_order_filled(order, trade)

        assert order.status == OrderStatus.FILLED
        assert '000001' in strategy.positions
        assert strategy.positions['000001'].quantity == 100
        assert strategy.cash == 1000000 - 10.0 * 100 - 3.0

    def test_total_value(self, strategy):
        """测试总资产计算"""
        strategy.positions['000001'] = Position(
            code='000001',
            quantity=1000,
            avg_cost=10.0,
            current_price=11.0
        )
        strategy.cash = 900000

        assert strategy.total_value == 900000 + 11000

    def test_get_close_prices(self, strategy):
        """测试获取历史收盘价"""
        strategy._current_code = '000001'
        strategy._bars['000001'] = [
            Bar(datetime.now(), 10, 11, 9, 10, 100),
            Bar(datetime.now(), 10, 12, 9, 11, 100),
            Bar(datetime.now(), 11, 13, 10, 12, 100),
        ]

        closes = strategy.get_close_prices(3)

        assert closes == [10, 11, 12]


class TestOrder:
    """订单测试"""

    def test_order_creation(self):
        """测试订单创建"""
        order = Order(
            order_id='O001',
            code='000001',
            side=OrderSide.BUY,
            price=10.0,
            quantity=100
        )

        assert order.order_id == 'O001'
        assert order.status == OrderStatus.PENDING
        assert order.filled_quantity == 0


class TestTrade:
    """成交记录测试"""

    def test_trade_creation(self):
        """测试成交记录创建"""
        trade = Trade(
            trade_id='T001',
            order_id='O001',
            code='000001',
            side=OrderSide.BUY,
            price=10.0,
            quantity=100,
            commission=3.0,
            trade_time=datetime.now()
        )

        assert trade.trade_id == 'T001'
        assert trade.price == 10.0
        assert trade.commission == 3.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
