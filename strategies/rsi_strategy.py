"""
RSI策略
基于RSI指标的超买超卖进行交易
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class RSIStrategy(BaseStrategy):
    """RSI策略"""

    # 策略参数
    period = 14
    oversold = 30    # 超卖线
    overbought = 70  # 超买线

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.period + 5)
        if len(bars) < self.period + 2:
            return

        # 计算RSI
        closes = [b.close for b in bars]
        rsi = TechnicalIndicators.RSI(closes, self.period)

        current_rsi = rsi[-1]
        prev_rsi = rsi[-2]

        # RSI从超卖区回升，买入
        if prev_rsi < self.oversold and current_rsi >= self.oversold:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"RSI超卖回升买入: RSI={current_rsi:.2f}")

        # RSI从超买区回落，卖出
        elif prev_rsi > self.overbought and current_rsi <= self.overbought:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"RSI超买回落卖出: RSI={current_rsi:.2f}")
