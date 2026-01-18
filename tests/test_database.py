"""
数据库管理器测试
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database.db_manager import DatabaseManager


class TestDatabaseManager:
    """数据库管理器测试"""

    @pytest.fixture
    def db_manager(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        manager = DatabaseManager(db_path)
        yield manager

        # 清理
        try:
            os.unlink(db_path)
        except Exception:
            pass

    def test_init(self, db_manager):
        """测试初始化"""
        assert db_manager.db_path.exists()

    def test_save_and_get_strategy(self, db_manager):
        """测试策略保存和获取"""
        # 保存策略
        db_manager.save_strategy(
            name="测试策略",
            code="class TestStrategy: pass",
            parameters={"period": 20},
            description="测试描述"
        )

        # 获取策略
        strategy = db_manager.get_strategy("测试策略")

        assert strategy is not None
        assert strategy['name'] == "测试策略"
        assert strategy['code'] == "class TestStrategy: pass"
        assert strategy['parameters'] == {"period": 20}
        assert strategy['description'] == "测试描述"

    def test_update_strategy(self, db_manager):
        """测试策略更新"""
        # 保存策略
        db_manager.save_strategy(
            name="测试策略",
            code="class TestStrategy: pass",
            parameters={"period": 20}
        )

        # 更新策略
        db_manager.save_strategy(
            name="测试策略",
            code="class TestStrategy: updated",
            parameters={"period": 30}
        )

        # 获取策略
        strategy = db_manager.get_strategy("测试策略")

        assert strategy['code'] == "class TestStrategy: updated"
        assert strategy['parameters'] == {"period": 30}

    def test_delete_strategy(self, db_manager):
        """测试策略删除"""
        # 保存策略
        db_manager.save_strategy(name="测试策略", code="test")

        # 删除策略
        result = db_manager.delete_strategy("测试策略")
        assert result == True

        # 验证删除
        strategy = db_manager.get_strategy("测试策略")
        assert strategy is None

    def test_get_all_strategies(self, db_manager):
        """测试获取所有策略"""
        # 保存多个策略
        db_manager.save_strategy(name="策略1", code="code1")
        db_manager.save_strategy(name="策略2", code="code2")
        db_manager.save_strategy(name="策略3", code="code3")

        # 获取所有策略
        strategies = db_manager.get_all_strategies()

        assert len(strategies) == 3

    def test_save_backtest_result(self, db_manager):
        """测试保存回测结果"""
        result = {
            'strategy_name': '测试策略',
            'stock_code': '000001',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'initial_capital': 1000000,
            'final_capital': 1200000,
            'total_return': 20.0,
            'annual_return': 20.0,
            'max_drawdown': 10.0,
            'sharpe_ratio': 1.5,
            'win_rate': 60.0,
            'profit_loss_ratio': 2.0,
            'total_trades': 50
        }

        result_id = db_manager.save_backtest_result(result)
        assert result_id > 0

        # 获取回测结果
        results = db_manager.get_backtest_results('测试策略')
        assert len(results) == 1
        assert results[0]['total_return'] == 20.0

    def test_save_trade(self, db_manager):
        """测试保存交易记录"""
        trade = {
            'trade_id': 'T001',
            'order_id': 'O001',
            'stock_code': '000001',
            'stock_name': '平安银行',
            'side': 'buy',
            'price': 10.5,
            'quantity': 1000,
            'amount': 10500,
            'commission': 5.25,
            'trade_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        db_manager.save_trade(trade)

        # 获取交易记录
        trades = db_manager.get_trades('000001')
        assert len(trades) == 1
        assert trades[0]['price'] == 10.5

    def test_save_position(self, db_manager):
        """测试保存持仓"""
        position = {
            'stock_code': '000001',
            'stock_name': '平安银行',
            'quantity': 1000,
            'avg_cost': 10.5,
            'current_price': 11.0,
            'market_value': 11000,
            'profit': 500,
            'profit_pct': 4.76,
            'strategy_name': '测试策略'
        }

        db_manager.save_position(position)

        # 获取持仓
        positions = db_manager.get_positions()
        assert len(positions) == 1
        assert positions[0]['quantity'] == 1000

    def test_save_kline_data(self, db_manager):
        """测试保存K线数据"""
        data = [
            {'datetime': '2023-01-01', 'open': 10, 'high': 11, 'low': 9, 'close': 10.5, 'volume': 1000},
            {'datetime': '2023-01-02', 'open': 10.5, 'high': 12, 'low': 10, 'close': 11, 'volume': 1200},
        ]

        count = db_manager.save_kline_data('000001', 'daily', data)
        assert count == 2

        # 获取K线数据
        klines = db_manager.get_kline_data('000001', 'daily')
        assert len(klines) == 2

    def test_trade_statistics(self, db_manager):
        """测试交易统计"""
        # 添加一些交易记录
        trades = [
            {'trade_id': 'T001', 'order_id': 'O001', 'stock_code': '000001',
             'side': 'buy', 'price': 10, 'quantity': 100, 'amount': 1000,
             'commission': 5, 'profit': 0, 'trade_time': '2023-01-01 10:00:00'},
            {'trade_id': 'T002', 'order_id': 'O002', 'stock_code': '000001',
             'side': 'sell', 'price': 11, 'quantity': 100, 'amount': 1100,
             'commission': 5, 'profit': 100, 'trade_time': '2023-01-02 10:00:00'},
        ]

        for trade in trades:
            db_manager.save_trade(trade)

        # 获取统计
        stats = db_manager.get_trade_statistics()

        assert stats['total_trades'] == 2
        assert stats['buy_count'] == 1
        assert stats['sell_count'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
