"""
技术指标测试
"""
import pytest
import numpy as np
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.indicators.technical import TechnicalIndicators


class TestMA:
    """移动平均线测试"""

    def test_ma_basic(self):
        """测试基本MA计算"""
        close = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        ma = TechnicalIndicators.MA(close, 5)

        # 前4个值应该是NaN
        assert np.isnan(ma[0])
        assert np.isnan(ma[3])

        # 第5个值应该是前5个数的平均
        assert ma[4] == pytest.approx(12.0)  # (10+11+12+13+14)/5

        # 最后一个值
        assert ma[9] == pytest.approx(17.0)  # (15+16+17+18+19)/5

    def test_ma_single_value(self):
        """测试单值MA"""
        close = [10, 11, 12]
        ma = TechnicalIndicators.MA(close, 3)
        assert ma[2] == pytest.approx(11.0)

    def test_ema_basic(self):
        """测试基本EMA计算"""
        close = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        ema = TechnicalIndicators.EMA(close, 5)

        # 前4个值应该是NaN
        assert np.isnan(ema[0])
        assert np.isnan(ema[3])

        # 第5个值应该等于SMA
        assert ema[4] == pytest.approx(12.0)

        # EMA应该比SMA更接近最新价格
        ma = TechnicalIndicators.MA(close, 5)
        assert ema[9] > ma[9]  # 上涨趋势中EMA > MA


class TestMACD:
    """MACD测试"""

    def test_macd_basic(self):
        """测试基本MACD计算"""
        # 生成测试数据
        np.random.seed(42)
        close = np.cumsum(np.random.randn(50)) + 100

        result = TechnicalIndicators.MACD(close, 12, 26, 9)

        # 检查返回结构
        assert hasattr(result, 'dif')
        assert hasattr(result, 'dea')
        assert hasattr(result, 'macd')

        # 检查长度
        assert len(result.dif) == len(close)
        assert len(result.dea) == len(close)
        assert len(result.macd) == len(close)

    def test_macd_values(self):
        """测试MACD值的合理性"""
        # 上涨趋势
        close = list(range(100, 150))
        result = TechnicalIndicators.MACD(close, 12, 26, 9)

        # 上涨趋势中DIF应该为正
        valid_dif = result.dif[~np.isnan(result.dif)]
        if len(valid_dif) > 0:
            assert valid_dif[-1] > 0


class TestKDJ:
    """KDJ测试"""

    def test_kdj_basic(self):
        """测试基本KDJ计算"""
        np.random.seed(42)
        n = 30
        close = np.cumsum(np.random.randn(n)) + 100
        high = close + np.abs(np.random.randn(n))
        low = close - np.abs(np.random.randn(n))

        result = TechnicalIndicators.KDJ(high, low, close, 9, 3, 3)

        # 检查返回结构
        assert hasattr(result, 'k')
        assert hasattr(result, 'd')
        assert hasattr(result, 'j')

        # K和D值应该在0-100之间
        valid_k = result.k[~np.isnan(result.k)]
        valid_d = result.d[~np.isnan(result.d)]

        assert all(0 <= k <= 100 for k in valid_k)
        assert all(0 <= d <= 100 for d in valid_d)

    def test_kdj_extreme(self):
        """测试极端情况"""
        # 持续上涨
        high = list(range(100, 120))
        low = list(range(90, 110))
        close = list(range(95, 115))

        result = TechnicalIndicators.KDJ(high, low, close, 9, 3, 3)

        # 持续上涨时K值应该较高
        assert result.k[-1] > 50


class TestRSI:
    """RSI测试"""

    def test_rsi_basic(self):
        """测试基本RSI计算"""
        np.random.seed(42)
        close = np.cumsum(np.random.randn(30)) + 100

        rsi = TechnicalIndicators.RSI(close, 14)

        # RSI值应该在0-100之间
        valid_rsi = rsi[~np.isnan(rsi)]
        assert all(0 <= r <= 100 for r in valid_rsi)

    def test_rsi_uptrend(self):
        """测试上涨趋势RSI"""
        close = list(range(100, 130))
        rsi = TechnicalIndicators.RSI(close, 14)

        # 持续上涨RSI应该接近100
        valid_rsi = rsi[~np.isnan(rsi)]
        if len(valid_rsi) > 0:
            assert valid_rsi[-1] > 70

    def test_rsi_downtrend(self):
        """测试下跌趋势RSI"""
        close = list(range(130, 100, -1))
        rsi = TechnicalIndicators.RSI(close, 14)

        # 持续下跌RSI应该接近0
        valid_rsi = rsi[~np.isnan(rsi)]
        if len(valid_rsi) > 0:
            assert valid_rsi[-1] < 30


class TestBOLL:
    """布林带测试"""

    def test_boll_basic(self):
        """测试基本布林带计算"""
        np.random.seed(42)
        close = np.cumsum(np.random.randn(30)) + 100

        result = TechnicalIndicators.BOLL(close, 20, 2.0)

        # 检查返回结构
        assert hasattr(result, 'upper')
        assert hasattr(result, 'middle')
        assert hasattr(result, 'lower')

        # 上轨 > 中轨 > 下轨
        valid_idx = ~np.isnan(result.middle)
        assert all(result.upper[valid_idx] > result.middle[valid_idx])
        assert all(result.middle[valid_idx] > result.lower[valid_idx])

    def test_boll_width(self):
        """测试布林带宽度"""
        close = [100] * 30  # 价格不变
        result = TechnicalIndicators.BOLL(close, 20, 2.0)

        # 价格不变时，上下轨应该等于中轨
        valid_idx = ~np.isnan(result.middle)
        assert np.allclose(result.upper[valid_idx], result.middle[valid_idx], atol=0.01)
        assert np.allclose(result.lower[valid_idx], result.middle[valid_idx], atol=0.01)


class TestATR:
    """ATR测试"""

    def test_atr_basic(self):
        """测试基本ATR计算"""
        np.random.seed(42)
        n = 30
        close = np.cumsum(np.random.randn(n)) + 100
        high = close + np.abs(np.random.randn(n)) * 2
        low = close - np.abs(np.random.randn(n)) * 2

        atr = TechnicalIndicators.ATR(high, low, close, 14)

        # ATR应该为正
        valid_atr = atr[~np.isnan(atr)]
        assert all(a > 0 for a in valid_atr)


class TestCrossSignals:
    """交叉信号测试"""

    def test_cross_over(self):
        """测试上穿信号"""
        series1 = np.array([1, 2, 3, 4, 5])
        series2 = np.array([3, 3, 3, 3, 3])

        cross = TechnicalIndicators.cross_over(series1, series2)

        # 在索引3处发生上穿 (series1从3变到4，穿过3)
        assert cross[3] == True
        assert cross[0] == False
        assert cross[4] == False

    def test_cross_under(self):
        """测试下穿信号"""
        series1 = np.array([5, 4, 3, 2, 1])
        series2 = np.array([3, 3, 3, 3, 3])

        cross = TechnicalIndicators.cross_under(series1, series2)

        # 在索引2处发生下穿 (series1从4变到3，穿过3)
        assert cross[2] == True


class TestOBV:
    """OBV测试"""

    def test_obv_basic(self):
        """测试基本OBV计算"""
        close = [10, 11, 10, 12, 11]
        volume = [100, 200, 150, 300, 100]

        obv = TechnicalIndicators.OBV(close, volume)

        # 验证OBV计算
        assert obv[0] == 100  # 初始值
        assert obv[1] == 300  # 上涨，+200
        assert obv[2] == 150  # 下跌，-150
        assert obv[3] == 450  # 上涨，+300
        assert obv[4] == 350  # 下跌，-100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
