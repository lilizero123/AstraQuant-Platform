"""
布林带策略
价格触及下轨买入，触及上轨卖出
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class BollStrategy(BaseStrategy):
    """布林带策略"""

    # 策略参数
    period = 20
    std_dev = 2.0

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.period + 5)
        if len(bars) < self.period:
            return

        # 计算布林带
        closes = [b.close for b in bars]
        boll = TechnicalIndicators.BOLL(closes, self.period, self.std_dev)

        upper = boll.upper[-1]
        middle = boll.middle[-1]
        lower = boll.lower[-1]

        # 价格触及下轨，买入
        if bar.close <= lower:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"触及下轨买入: 价格={bar.close:.2f}, 下轨={lower:.2f}")

        # 价格触及上轨，卖出
        elif bar.close >= upper:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"触及上轨卖出: 价格={bar.close:.2f}, 上轨={upper:.2f}")
