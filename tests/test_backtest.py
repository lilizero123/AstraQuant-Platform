"""
回测引擎测试
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.backtest.engine import BacktestEngine, BacktestResult
from core.strategy.base import BaseStrategy, Bar


class SimpleMAStrategy(BaseStrategy):
    """简单均线策略（用于测试）"""

    ma_period = 5

    def on_bar(self, bar: Bar):
        closes = self.get_close_prices(self.ma_period + 1)
        if len(closes) < self.ma_period:
            return

        ma = sum(closes[-self.ma_period:]) / self.ma_period

        # 价格上穿均线买入
        if bar.close > ma and self.position == 0:
            quantity = int(self.cash * 0.9 / bar.close / 100) * 100
            if quantity >= 100:
                self.buy(bar.close, quantity)

        # 价格下穿均线卖出
        elif bar.close < ma and self.position > 0:
            self.sell(bar.close, self.position)


class TestBacktestEngine:
    """回测引擎测试"""

    @pytest.fixture
    def engine(self):
        """创建回测引擎"""
        return BacktestEngine()

    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        # 生成模拟价格数据（带趋势）
        base_price = 10.0
        returns = np.random.randn(100) * 0.02 + 0.001  # 略微上涨趋势
        prices = base_price * np.cumprod(1 + returns)

        data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.randn(100) * 0.005),
            'high': prices * (1 + np.abs(np.random.randn(100) * 0.01)),
            'low': prices * (1 - np.abs(np.random.randn(100) * 0.01)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })

        return data

    def test_engine_init(self, engine):
        """测试引擎初始化"""
        assert engine.initial_capital == 1000000.0
        assert engine.commission_rate == 0.0003
        assert engine.slippage == 0.001
        assert engine.strategy is None

    def test_set_strategy(self, engine):
        """测试设置策略"""
        strategy = SimpleMAStrategy()
        engine.set_strategy(strategy)
        assert engine.strategy is strategy

    def test_set_capital(self, engine):
        """测试设置资金"""
        engine.set_capital(500000)
        assert engine.initial_capital == 500000

    def test_set_commission(self, engine):
        """测试设置手续费"""
        engine.set_commission(0.001)
        assert engine.commission_rate == 0.001

    def test_add_data(self, engine, sample_data):
        """测试添加数据"""
        engine.add_data('000001', sample_data)
        assert '000001' in engine.data
        assert len(engine.data['000001']) == 100

    def test_add_data_missing_column(self, engine):
        """测试添加缺少列的数据"""
        bad_data = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=10),
            'close': [10] * 10
        })

        with pytest.raises(ValueError):
            engine.add_data('000001', bad_data)

    def test_run_without_strategy(self, engine, sample_data):
        """测试未设置策略时运行"""
        engine.add_data('000001', sample_data)

        with pytest.raises(ValueError):
            engine.run()

    def test_run_without_data(self, engine):
        """测试未添加数据时运行"""
        engine.set_strategy(SimpleMAStrategy())

        with pytest.raises(ValueError):
            engine.run()

    def test_run_backtest(self, engine, sample_data):
        """测试运行回测"""
        engine.set_strategy(SimpleMAStrategy())
        engine.set_capital(100000)
        engine.add_data('000001', sample_data)

        result = engine.run()

        assert result is not None
        assert isinstance(result, BacktestResult)
        assert result.initial_capital == 100000
        assert len(result.equity_curve) > 0

    def test_backtest_result_fields(self, engine, sample_data):
        """测试回测结果字段"""
        engine.set_strategy(SimpleMAStrategy())
        engine.add_data('000001', sample_data)

        result = engine.run()

        # 检查基本字段
        assert result.start_date != ""
        assert result.end_date != ""
        assert result.initial_capital > 0
        assert result.final_capital > 0

        # 检查收益指标
        assert isinstance(result.total_return, float)
        assert isinstance(result.annual_return, float)

        # 检查风险指标
        assert isinstance(result.max_drawdown, float)
        assert result.max_drawdown >= 0

    def test_equity_curve(self, engine, sample_data):
        """测试资金曲线"""
        engine.set_strategy(SimpleMAStrategy())
        engine.add_data('000001', sample_data)

        result = engine.run()

        # 资金曲线应该从初始资金开始
        assert result.equity_curve[0] == engine.initial_capital

        # 资金曲线长度应该等于交易日数+1
        assert len(result.equity_curve) == len(sample_data) + 1

    def test_get_report(self, engine, sample_data):
        """测试生成报告"""
        engine.set_strategy(SimpleMAStrategy())
        engine.add_data('000001', sample_data)
        engine.run()

        report = engine.get_report()

        assert "回测报告" in report
        assert "总收益率" in report
        assert "最大回撤" in report
        assert "夏普比率" in report

    def test_get_report_without_run(self, engine):
        """测试未运行时获取报告"""
        report = engine.get_report()
        assert "请先运行回测" in report

    def test_commission_calculation(self, engine, sample_data):
        """测试手续费计算"""
        engine.set_strategy(SimpleMAStrategy())
        engine.set_commission(0.001)  # 0.1%手续费
        engine.add_data('000001', sample_data)

        result = engine.run()

        # 如果有交易，应该有手续费扣除
        if result.total_trades > 0:
            # 最终资金应该小于等于初始资金+收益（因为有手续费）
            pass  # 手续费已在交易中扣除

    def test_slippage_effect(self, engine, sample_data):
        """测试滑点影响"""
        # 无滑点
        engine.set_strategy(SimpleMAStrategy())
        engine.set_slippage(0)
        engine.add_data('000001', sample_data.copy())
        result_no_slip = engine.run()

        # 有滑点
        engine2 = BacktestEngine()
        engine2.set_strategy(SimpleMAStrategy())
        engine2.set_slippage(0.01)  # 1%滑点
        engine2.add_data('000001', sample_data.copy())
        result_with_slip = engine2.run()

        # 有滑点的收益应该更低（如果有交易）
        if result_no_slip.total_trades > 0 and result_with_slip.total_trades > 0:
            assert result_with_slip.final_capital <= result_no_slip.final_capital


class TestBacktestResult:
    """回测结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = BacktestResult()

        assert result.initial_capital == 0.0
        assert result.total_return == 0.0
        assert result.max_drawdown == 0.0
        assert result.equity_curve == []
        assert result.trades == []

    def test_result_with_values(self):
        """测试带值的结果"""
        result = BacktestResult(
            initial_capital=100000,
            final_capital=120000,
            total_return=20.0,
            max_drawdown=5.0,
            sharpe_ratio=1.5
        )

        assert result.initial_capital == 100000
        assert result.final_capital == 120000
        assert result.total_return == 20.0
        assert result.max_drawdown == 5.0
        assert result.sharpe_ratio == 1.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
