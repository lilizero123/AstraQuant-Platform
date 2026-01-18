"""
风险管理测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.risk.risk_manager import (
    RiskManager, RiskConfig, RiskLevel, RiskAlert
)
from core.strategy.base import Order, Position, OrderSide, OrderType, OrderStatus


class TestRiskConfig:
    """风控配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = RiskConfig()

        assert config.max_position_pct == 30.0
        assert config.max_total_position_pct == 80.0
        assert config.stop_loss_pct == 5.0
        assert config.take_profit_pct == 10.0
        assert config.max_drawdown_pct == 20.0
        assert config.max_daily_trades == 50
        assert config.max_daily_loss == 50000.0

    def test_custom_config(self):
        """测试自定义配置"""
        config = RiskConfig(
            max_position_pct=20.0,
            stop_loss_pct=3.0,
            max_drawdown_pct=15.0
        )

        assert config.max_position_pct == 20.0
        assert config.stop_loss_pct == 3.0
        assert config.max_drawdown_pct == 15.0


class TestRiskManager:
    """风险管理器测试"""

    @pytest.fixture
    def risk_manager(self):
        """创建风险管理器"""
        config = RiskConfig(
            max_position_pct=30.0,
            max_total_position_pct=80.0,
            stop_loss_pct=5.0,
            take_profit_pct=10.0,
            max_drawdown_pct=20.0,
            max_daily_trades=10,
            max_daily_loss=10000.0,
            min_trade_interval=0  # 测试时禁用交易间隔
        )
        return RiskManager(config)

    @pytest.fixture
    def sample_order(self):
        """创建示例订单"""
        return Order(
            order_id='O001',
            code='000001',
            side=OrderSide.BUY,
            price=10.0,
            quantity=1000,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING
        )

    @pytest.fixture
    def sample_positions(self):
        """创建示例持仓"""
        return {
            '000001': Position(
                code='000001',
                quantity=1000,
                avg_cost=10.0,
                current_price=10.5
            )
        }

    def test_init(self, risk_manager):
        """测试初始化"""
        assert risk_manager.is_trading_allowed == True
        assert risk_manager.daily_trades == 0
        assert risk_manager.daily_loss == 0.0
        assert len(risk_manager.alerts) == 0

    def test_reset_daily(self, risk_manager):
        """测试重置每日统计"""
        risk_manager.daily_trades = 5
        risk_manager.daily_loss = 1000.0
        risk_manager.is_trading_allowed = False

        risk_manager.reset_daily()

        assert risk_manager.daily_trades == 0
        assert risk_manager.daily_loss == 0.0
        assert risk_manager.is_trading_allowed == True

    def test_update_peak_value(self, risk_manager):
        """测试更新历史最高资产"""
        risk_manager.update_peak_value(100000)
        assert risk_manager.peak_value == 100000

        risk_manager.update_peak_value(90000)
        assert risk_manager.peak_value == 100000  # 不应该降低

        risk_manager.update_peak_value(110000)
        assert risk_manager.peak_value == 110000

    def test_check_order_pass(self, risk_manager, sample_order):
        """测试订单检查通过"""
        positions = {}
        cash = 100000
        total_value = 100000
        current_price = 10.0

        passed, reason = risk_manager.check_order(
            sample_order, positions, cash, total_value, current_price
        )

        assert passed == True
        assert reason == ""

    def test_check_order_trading_disabled(self, risk_manager, sample_order):
        """测试交易被禁止"""
        risk_manager.is_trading_allowed = False

        passed, reason = risk_manager.check_order(
            sample_order, {}, 100000, 100000, 10.0
        )

        assert passed == False
        assert "风控暂停" in reason

    def test_check_order_max_daily_trades(self, risk_manager, sample_order):
        """测试每日最大交易次数"""
        risk_manager.daily_trades = 10  # 达到限制

        passed, reason = risk_manager.check_order(
            sample_order, {}, 100000, 100000, 10.0
        )

        assert passed == False
        assert "交易次数" in reason

    def test_check_order_price_deviation(self, risk_manager, sample_order):
        """测试价格偏离"""
        sample_order.price = 15.0  # 偏离50%
        current_price = 10.0

        passed, reason = risk_manager.check_order(
            sample_order, {}, 100000, 100000, current_price
        )

        assert passed == False
        assert "偏离" in reason

    def test_check_order_max_position(self, risk_manager, sample_order):
        """测试单只股票最大仓位"""
        sample_order.quantity = 5000  # 50000元，超过30%
        total_value = 100000

        passed, reason = risk_manager.check_order(
            sample_order, {}, 100000, total_value, 10.0
        )

        assert passed == False
        assert "仓位" in reason

    def test_check_order_insufficient_cash(self, risk_manager, sample_order):
        """测试资金不足"""
        sample_order.quantity = 10000  # 需要100000元
        cash = 50000

        passed, reason = risk_manager.check_order(
            sample_order, {}, cash, 100000, 10.0
        )

        assert passed == False
        assert "资金不足" in reason

    def test_check_position_stop_loss(self, risk_manager):
        """测试止损检查"""
        position = Position(
            code='000001',
            quantity=1000,
            avg_cost=10.0,
            current_price=9.0  # 亏损10%
        )

        alerts = risk_manager.check_position(position)

        assert len(alerts) == 1
        assert alerts[0].level == RiskLevel.HIGH
        assert "止损" in alerts[0].message

    def test_check_position_take_profit(self, risk_manager):
        """测试止盈检查"""
        position = Position(
            code='000001',
            quantity=1000,
            avg_cost=10.0,
            current_price=12.0  # 盈利20%
        )

        alerts = risk_manager.check_position(position)

        assert len(alerts) == 1
        assert alerts[0].level == RiskLevel.MEDIUM
        assert "止盈" in alerts[0].message

    def test_check_position_normal(self, risk_manager):
        """测试正常持仓"""
        position = Position(
            code='000001',
            quantity=1000,
            avg_cost=10.0,
            current_price=10.2  # 盈利2%
        )

        alerts = risk_manager.check_position(position)

        assert len(alerts) == 0

    def test_check_drawdown_trigger(self, risk_manager):
        """测试触发最大回撤"""
        risk_manager.peak_value = 100000
        total_value = 75000  # 回撤25%

        triggered = risk_manager.check_drawdown(total_value)

        assert triggered == True
        assert risk_manager.is_trading_allowed == False

    def test_check_drawdown_normal(self, risk_manager):
        """测试正常回撤"""
        risk_manager.peak_value = 100000
        total_value = 90000  # 回撤10%

        triggered = risk_manager.check_drawdown(total_value)

        assert triggered == False
        assert risk_manager.is_trading_allowed == True

    def test_check_daily_loss_trigger(self, risk_manager):
        """测试触发每日最大亏损"""
        triggered = risk_manager.check_daily_loss(15000)  # 超过10000限制

        assert triggered == True
        assert risk_manager.is_trading_allowed == False

    def test_check_daily_loss_normal(self, risk_manager):
        """测试正常每日亏损"""
        triggered = risk_manager.check_daily_loss(5000)

        assert triggered == False
        assert risk_manager.is_trading_allowed == True
        assert risk_manager.daily_loss == 5000

    def test_on_trade_completed(self, risk_manager):
        """测试交易完成回调"""
        risk_manager.on_trade_completed()

        assert risk_manager.daily_trades == 1
        assert risk_manager.last_trade_time is not None

    def test_get_alerts(self, risk_manager):
        """测试获取警报"""
        risk_manager._add_alert(RiskLevel.LOW, "测试1", "000001")
        risk_manager._add_alert(RiskLevel.HIGH, "测试2", "000002")
        risk_manager._add_alert(RiskLevel.HIGH, "测试3", "000003")

        all_alerts = risk_manager.get_alerts()
        assert len(all_alerts) == 3

        high_alerts = risk_manager.get_alerts(RiskLevel.HIGH)
        assert len(high_alerts) == 2

    def test_clear_alerts(self, risk_manager):
        """测试清除警报"""
        risk_manager._add_alert(RiskLevel.LOW, "测试", "000001")
        assert len(risk_manager.alerts) == 1

        risk_manager.clear_alerts()
        assert len(risk_manager.alerts) == 0

    def test_get_risk_summary(self, risk_manager, sample_positions):
        """测试获取风险摘要"""
        risk_manager.peak_value = 100000
        risk_manager.daily_trades = 3
        risk_manager.daily_loss = 500

        summary = risk_manager.get_risk_summary(sample_positions, 95000)

        assert 'drawdown' in summary
        assert 'position_pct' in summary
        assert 'daily_trades' in summary
        assert summary['daily_trades'] == 3
        assert summary['is_trading_allowed'] == True

    def test_alert_callback(self, risk_manager):
        """测试警报回调"""
        alerts_received = []

        def on_alert(alert):
            alerts_received.append(alert)

        risk_manager.on_alert = on_alert
        risk_manager._add_alert(RiskLevel.HIGH, "测试警报", "000001")

        assert len(alerts_received) == 1
        assert alerts_received[0].message == "测试警报"

    def test_stop_trading_callback(self, risk_manager):
        """测试停止交易回调"""
        stop_reasons = []

        def on_stop(reason):
            stop_reasons.append(reason)

        risk_manager.on_stop_trading = on_stop
        risk_manager.peak_value = 100000
        risk_manager.check_drawdown(70000)  # 触发30%回撤

        assert len(stop_reasons) == 1
        assert "回撤" in stop_reasons[0]


class TestRiskAlert:
    """风险警报测试"""

    def test_alert_creation(self):
        """测试警报创建"""
        alert = RiskAlert(
            level=RiskLevel.HIGH,
            message="测试警报",
            timestamp=datetime.now(),
            code="000001"
        )

        assert alert.level == RiskLevel.HIGH
        assert alert.message == "测试警报"
        assert alert.code == "000001"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
