"""
MACD策略
基于MACD指标的金叉死叉进行交易
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class MACDStrategy(BaseStrategy):
    """MACD策略"""

    # 策略参数
    fast_period = 12
    slow_period = 26
    signal_period = 9

    def on_bar(self, bar: Bar):
        # 获取足够的历史数据
        bars = self.get_bars(self.slow_period + self.signal_period + 10)
        if len(bars) < self.slow_period + self.signal_period:
            return

        # 计算MACD
        closes = [b.close for b in bars]
        macd_result = TechnicalIndicators.MACD(
            closes, self.fast_period, self.slow_period, self.signal_period
        )

        # 获取当前和前一个MACD值
        dif = macd_result.dif
        dea = macd_result.dea

        if len(dif) < 2:
            return

        # 金叉买入 (DIF上穿DEA)
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"MACD金叉买入: DIF={dif[-1]:.4f}, DEA={dea[-1]:.4f}")

        # 死叉卖出 (DIF下穿DEA)
        elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"MACD死叉卖出: DIF={dif[-1]:.4f}, DEA={dea[-1]:.4f}")
