"""
KDJ策略
基于KDJ指标的超买超卖进行交易
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class KDJStrategy(BaseStrategy):
    """KDJ策略"""

    # 策略参数
    n = 9
    m1 = 3
    m2 = 3
    oversold = 20    # 超卖线
    overbought = 80  # 超买线

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.n + 10)
        if len(bars) < self.n + 2:
            return

        # 计算KDJ
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        closes = [b.close for b in bars]

        kdj = TechnicalIndicators.KDJ(highs, lows, closes, self.n, self.m1, self.m2)

        k, d, j = kdj.k[-1], kdj.d[-1], kdj.j[-1]
        prev_k, prev_d = kdj.k[-2], kdj.d[-2]

        # J值从超卖区上穿，买入
        if j < self.oversold and prev_k <= prev_d and k > d:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"KDJ超卖买入: K={k:.2f}, D={d:.2f}, J={j:.2f}")

        # J值从超买区下穿，卖出
        elif j > self.overbought and prev_k >= prev_d and k < d:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"KDJ超买卖出: K={k:.2f}, D={d:.2f}, J={j:.2f}")
