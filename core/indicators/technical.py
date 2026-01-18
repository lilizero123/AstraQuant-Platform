"""
技术指标计算模块
提供常用技术指标的计算方法
"""
import numpy as np
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass


@dataclass
class MACDResult:
    """MACD计算结果"""
    dif: np.ndarray      # DIF线 (快线-慢线)
    dea: np.ndarray      # DEA线 (DIF的EMA)
    macd: np.ndarray     # MACD柱状图 (DIF-DEA)*2


@dataclass
class KDJResult:
    """KDJ计算结果"""
    k: np.ndarray
    d: np.ndarray
    j: np.ndarray


@dataclass
class BOLLResult:
    """布林带计算结果"""
    upper: np.ndarray    # 上轨
    middle: np.ndarray   # 中轨
    lower: np.ndarray    # 下轨


class TechnicalIndicators:
    """技术指标计算类"""

    @staticmethod
    def _to_numpy(data: Union[List, np.ndarray]) -> np.ndarray:
        """转换为numpy数组"""
        if isinstance(data, np.ndarray):
            return data.astype(float)
        return np.array(data, dtype=float)

    # ==================== 移动平均线 ====================

    @staticmethod
    def MA(close: Union[List, np.ndarray], period: int) -> np.ndarray:
        """
        简单移动平均线 (Simple Moving Average)

        Args:
            close: 收盘价序列
            period: 周期

        Returns:
            MA值序列
        """
        close = TechnicalIndicators._to_numpy(close)
        ma = np.full(len(close), np.nan)

        for i in range(period - 1, len(close)):
            ma[i] = np.mean(close[i - period + 1:i + 1])

        return ma

    @staticmethod
    def EMA(close: Union[List, np.ndarray], period: int) -> np.ndarray:
        """
        指数移动平均线 (Exponential Moving Average)

        Args:
            close: 收盘价序列
            period: 周期

        Returns:
            EMA值序列
        """
        if period <= 0:
            raise ValueError("period must be positive")

        close = TechnicalIndicators._to_numpy(close)
        ema = np.full(len(close), np.nan)

        # 计算平滑系数
        multiplier = min(2 / period, 1.0)

        # 第一个EMA值使用SMA
        if len(close) >= period:
            ema[period - 1] = np.mean(close[:period])

            # 后续使用EMA公式
            for i in range(period, len(close)):
                ema[i] = close[i] * multiplier + ema[i - 1] * (1 - multiplier)

        return ema

    @staticmethod
    def WMA(close: Union[List, np.ndarray], period: int) -> np.ndarray:
        """
        加权移动平均线 (Weighted Moving Average)

        Args:
            close: 收盘价序列
            period: 周期

        Returns:
            WMA值序列
        """
        close = TechnicalIndicators._to_numpy(close)
        wma = np.full(len(close), np.nan)

        weights = np.arange(1, period + 1)
        weight_sum = weights.sum()

        for i in range(period - 1, len(close)):
            wma[i] = np.sum(close[i - period + 1:i + 1] * weights) / weight_sum

        return wma

    # ==================== MACD ====================

    @staticmethod
    def MACD(close: Union[List, np.ndarray],
             fast_period: int = 12,
             slow_period: int = 26,
             signal_period: int = 9) -> MACDResult:
        """
        MACD指标 (Moving Average Convergence Divergence)

        Args:
            close: 收盘价序列
            fast_period: 快线周期，默认12
            slow_period: 慢线周期，默认26
            signal_period: 信号线周期，默认9

        Returns:
            MACDResult: 包含DIF, DEA, MACD
        """
        close = TechnicalIndicators._to_numpy(close)

        # 计算快慢EMA
        ema_fast = TechnicalIndicators.EMA(close, fast_period)
        ema_slow = TechnicalIndicators.EMA(close, slow_period)

        # DIF = 快线EMA - 慢线EMA
        dif = ema_fast - ema_slow

        # DEA = DIF的EMA
        dea = np.full(len(close), np.nan)
        multiplier = 2 / (signal_period + 1)

        # 找到第一个有效的DIF值
        first_valid = slow_period - 1
        if first_valid < len(dif):
            # 初始DEA使用DIF的SMA
            valid_dif = dif[first_valid:first_valid + signal_period]
            valid_dif = valid_dif[~np.isnan(valid_dif)]
            if len(valid_dif) >= signal_period:
                dea[first_valid + signal_period - 1] = np.mean(valid_dif)

                for i in range(first_valid + signal_period, len(close)):
                    if not np.isnan(dif[i]) and not np.isnan(dea[i - 1]):
                        dea[i] = dif[i] * multiplier + dea[i - 1] * (1 - multiplier)

        # MACD柱状图 = (DIF - DEA) * 2
        macd = (dif - dea) * 2

        return MACDResult(dif=dif, dea=dea, macd=macd)

    # ==================== KDJ ====================

    @staticmethod
    def KDJ(high: Union[List, np.ndarray],
            low: Union[List, np.ndarray],
            close: Union[List, np.ndarray],
            n: int = 9,
            m1: int = 3,
            m2: int = 3) -> KDJResult:
        """
        KDJ随机指标

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            n: RSV周期，默认9
            m1: K值平滑周期，默认3
            m2: D值平滑周期，默认3

        Returns:
            KDJResult: 包含K, D, J值
        """
        high = TechnicalIndicators._to_numpy(high)
        low = TechnicalIndicators._to_numpy(low)
        close = TechnicalIndicators._to_numpy(close)

        length = len(close)
        rsv = np.full(length, np.nan)
        k = np.full(length, 50.0)  # K初始值50
        d = np.full(length, 50.0)  # D初始值50
        j = np.full(length, np.nan)

        for i in range(n - 1, length):
            # 计算N日内最高价和最低价
            highest = np.max(high[i - n + 1:i + 1])
            lowest = np.min(low[i - n + 1:i + 1])

            # RSV = (收盘价 - N日最低价) / (N日最高价 - N日最低价) * 100
            if highest != lowest:
                rsv[i] = (close[i] - lowest) / (highest - lowest) * 100
            else:
                rsv[i] = 50

            # K = 前一日K * (m1-1)/m1 + 当日RSV * 1/m1
            if i == n - 1:
                k[i] = rsv[i]
            else:
                k[i] = k[i - 1] * (m1 - 1) / m1 + rsv[i] / m1

            # D = 前一日D * (m2-1)/m2 + 当日K * 1/m2
            if i == n - 1:
                d[i] = k[i]
            else:
                d[i] = d[i - 1] * (m2 - 1) / m2 + k[i] / m2

            # J = 3K - 2D
            j[i] = 3 * k[i] - 2 * d[i]

        return KDJResult(k=k, d=d, j=j)

    # ==================== RSI ====================

    @staticmethod
    def RSI(close: Union[List, np.ndarray], period: int = 14) -> np.ndarray:
        """
        相对强弱指标 (Relative Strength Index)

        Args:
            close: 收盘价序列
            period: 周期，默认14

        Returns:
            RSI值序列
        """
        close = TechnicalIndicators._to_numpy(close)
        rsi = np.full(len(close), np.nan)

        # 计算价格变化
        delta = np.diff(close)

        # 分离上涨和下跌
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)

        # 计算平均涨跌幅
        for i in range(period, len(close)):
            avg_gain = np.mean(gains[i - period:i])
            avg_loss = np.mean(losses[i - period:i])

            if avg_loss == 0:
                rsi[i] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def RSI_EMA(close: Union[List, np.ndarray], period: int = 14) -> np.ndarray:
        """
        RSI (使用EMA平滑)

        Args:
            close: 收盘价序列
            period: 周期，默认14

        Returns:
            RSI值序列
        """
        close = TechnicalIndicators._to_numpy(close)
        rsi = np.full(len(close), np.nan)

        delta = np.diff(close)
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)

        # 使用EMA计算平均涨跌幅
        multiplier = 1 / period

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(close)):
            avg_gain = gains[i - 1] * multiplier + avg_gain * (1 - multiplier)
            avg_loss = losses[i - 1] * multiplier + avg_loss * (1 - multiplier)

            if avg_loss == 0:
                rsi[i] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))

        return rsi

    # ==================== 布林带 ====================

    @staticmethod
    def BOLL(close: Union[List, np.ndarray],
             period: int = 20,
             std_dev: float = 2.0) -> BOLLResult:
        """
        布林带 (Bollinger Bands)

        Args:
            close: 收盘价序列
            period: 周期，默认20
            std_dev: 标准差倍数，默认2

        Returns:
            BOLLResult: 包含上轨、中轨、下轨
        """
        close = TechnicalIndicators._to_numpy(close)

        middle = TechnicalIndicators.MA(close, period)
        upper = np.full(len(close), np.nan)
        lower = np.full(len(close), np.nan)

        for i in range(period - 1, len(close)):
            std = np.std(close[i - period + 1:i + 1], ddof=1)
            upper[i] = middle[i] + std_dev * std
            lower[i] = middle[i] - std_dev * std

        return BOLLResult(upper=upper, middle=middle, lower=lower)

    # ==================== ATR ====================

    @staticmethod
    def ATR(high: Union[List, np.ndarray],
            low: Union[List, np.ndarray],
            close: Union[List, np.ndarray],
            period: int = 14) -> np.ndarray:
        """
        真实波幅均值 (Average True Range)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期，默认14

        Returns:
            ATR值序列
        """
        high = TechnicalIndicators._to_numpy(high)
        low = TechnicalIndicators._to_numpy(low)
        close = TechnicalIndicators._to_numpy(close)

        length = len(close)
        tr = np.full(length, np.nan)
        atr = np.full(length, np.nan)

        # 计算真实波幅 (True Range)
        tr[0] = high[0] - low[0]
        for i in range(1, length):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1])
            )

        # 计算ATR (使用EMA)
        atr[period - 1] = np.mean(tr[:period])
        multiplier = 1 / period

        for i in range(period, length):
            atr[i] = tr[i] * multiplier + atr[i - 1] * (1 - multiplier)

        return atr

    # ==================== CCI ====================

    @staticmethod
    def CCI(high: Union[List, np.ndarray],
            low: Union[List, np.ndarray],
            close: Union[List, np.ndarray],
            period: int = 20) -> np.ndarray:
        """
        顺势指标 (Commodity Channel Index)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期，默认20

        Returns:
            CCI值序列
        """
        high = TechnicalIndicators._to_numpy(high)
        low = TechnicalIndicators._to_numpy(low)
        close = TechnicalIndicators._to_numpy(close)

        # 典型价格 = (最高价 + 最低价 + 收盘价) / 3
        tp = (high + low + close) / 3

        cci = np.full(len(close), np.nan)

        for i in range(period - 1, len(close)):
            tp_slice = tp[i - period + 1:i + 1]
            ma = np.mean(tp_slice)
            md = np.mean(np.abs(tp_slice - ma))

            if md != 0:
                cci[i] = (tp[i] - ma) / (0.015 * md)
            else:
                cci[i] = 0

        return cci

    # ==================== OBV ====================

    @staticmethod
    def OBV(close: Union[List, np.ndarray],
            volume: Union[List, np.ndarray]) -> np.ndarray:
        """
        能量潮指标 (On Balance Volume)

        Args:
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            OBV值序列
        """
        close = TechnicalIndicators._to_numpy(close)
        volume = TechnicalIndicators._to_numpy(volume)

        obv = np.zeros(len(close))
        obv[0] = volume[0]

        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                obv[i] = obv[i - 1] + volume[i]
            elif close[i] < close[i - 1]:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]

        return obv

    # ==================== VWAP ====================

    @staticmethod
    def VWAP(high: Union[List, np.ndarray],
             low: Union[List, np.ndarray],
             close: Union[List, np.ndarray],
             volume: Union[List, np.ndarray]) -> np.ndarray:
        """
        成交量加权平均价格 (Volume Weighted Average Price)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            VWAP值序列
        """
        high = TechnicalIndicators._to_numpy(high)
        low = TechnicalIndicators._to_numpy(low)
        close = TechnicalIndicators._to_numpy(close)
        volume = TechnicalIndicators._to_numpy(volume)

        # 典型价格
        tp = (high + low + close) / 3

        # 累计成交量加权价格
        cum_tp_vol = np.cumsum(tp * volume)
        cum_vol = np.cumsum(volume)

        vwap = cum_tp_vol / cum_vol

        return vwap

    # ==================== DMI ====================

    @staticmethod
    def DMI(high: Union[List, np.ndarray],
            low: Union[List, np.ndarray],
            close: Union[List, np.ndarray],
            period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        动向指标 (Directional Movement Index)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期，默认14

        Returns:
            Tuple[PDI, MDI, ADX]: 正向指标、负向指标、平均趋向指标
        """
        high = TechnicalIndicators._to_numpy(high)
        low = TechnicalIndicators._to_numpy(low)
        close = TechnicalIndicators._to_numpy(close)

        length = len(close)

        # 计算+DM和-DM
        plus_dm = np.zeros(length)
        minus_dm = np.zeros(length)

        for i in range(1, length):
            up_move = high[i] - high[i - 1]
            down_move = low[i - 1] - low[i]

            if up_move > down_move and up_move > 0:
                plus_dm[i] = up_move
            if down_move > up_move and down_move > 0:
                minus_dm[i] = down_move

        # 计算TR
        tr = np.zeros(length)
        tr[0] = high[0] - low[0]
        for i in range(1, length):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1])
            )

        # 平滑计算
        atr = TechnicalIndicators._smooth(tr, period)
        smooth_plus_dm = TechnicalIndicators._smooth(plus_dm, period)
        smooth_minus_dm = TechnicalIndicators._smooth(minus_dm, period)

        # 计算+DI和-DI
        pdi = np.full(length, np.nan)
        mdi = np.full(length, np.nan)

        for i in range(period - 1, length):
            if atr[i] != 0:
                pdi[i] = 100 * smooth_plus_dm[i] / atr[i]
                mdi[i] = 100 * smooth_minus_dm[i] / atr[i]

        # 计算DX和ADX
        dx = np.full(length, np.nan)
        for i in range(period - 1, length):
            if not np.isnan(pdi[i]) and not np.isnan(mdi[i]):
                if pdi[i] + mdi[i] != 0:
                    dx[i] = 100 * abs(pdi[i] - mdi[i]) / (pdi[i] + mdi[i])

        adx = TechnicalIndicators.MA(dx, period)

        return pdi, mdi, adx

    @staticmethod
    def _smooth(data: np.ndarray, period: int) -> np.ndarray:
        """Wilder平滑方法"""
        result = np.full(len(data), np.nan)
        result[period - 1] = np.sum(data[:period])

        for i in range(period, len(data)):
            result[i] = result[i - 1] - result[i - 1] / period + data[i]

        return result

    # ==================== 信号生成 ====================

    @staticmethod
    def cross_over(series1: np.ndarray, series2: np.ndarray) -> np.ndarray:
        """
        判断series1上穿series2

        Returns:
            布尔数组，True表示发生上穿
        """
        cross = np.zeros(len(series1), dtype=bool)
        for i in range(1, len(series1)):
            if (not np.isnan(series1[i]) and not np.isnan(series2[i]) and
                not np.isnan(series1[i-1]) and not np.isnan(series2[i-1])):
                if series1[i-1] <= series2[i-1] and series1[i] > series2[i]:
                    cross[i] = True
        return cross

    @staticmethod
    def cross_under(series1: np.ndarray, series2: np.ndarray) -> np.ndarray:
        """
        判断series1下穿series2

        Returns:
            布尔数组，True表示发生下穿
        """
        cross = np.zeros(len(series1), dtype=bool)
        for i in range(1, len(series1)):
            if (not np.isnan(series1[i]) and not np.isnan(series2[i]) and
                not np.isnan(series1[i-1]) and not np.isnan(series2[i-1])):
                if (series1[i-1] >= series2[i-1] and
                        series1[i] <= series2[i] and
                        series1[i] < series1[i-1]):
                    cross[i] = True
        return cross
