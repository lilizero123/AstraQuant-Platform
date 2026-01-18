"""
双均线交叉策略
当快线上穿慢线时买入，下穿时卖出
"""
from core.strategy.base import BaseStrategy, Bar


class DualMAStrategy(BaseStrategy):
    """双均线策略"""

    # 策略参数
    fast_period = 5   # 快线周期
    slow_period = 20  # 慢线周期

    def on_bar(self, bar: Bar):
        # 获取历史收盘价
        closes = self.get_close_prices(self.slow_period + 1)
        if len(closes) < self.slow_period:
            return

        # 计算均线
        fast_ma = sum(closes[-self.fast_period:]) / self.fast_period
        slow_ma = sum(closes[-self.slow_period:]) / self.slow_period

        # 计算前一根K线的均线
        prev_closes = closes[:-1]
        prev_fast_ma = sum(prev_closes[-self.fast_period:]) / self.fast_period
        prev_slow_ma = sum(prev_closes[-self.slow_period:]) / self.slow_period

        # 金叉买入
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"金叉买入: 价格={bar.close:.2f}, 数量={quantity}")

        # 死叉卖出
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"死叉卖出: 价格={bar.close:.2f}, 数量={self.position}")
