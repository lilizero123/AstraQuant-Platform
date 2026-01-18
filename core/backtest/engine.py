"""
回测引擎
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Type
from dataclasses import dataclass, field

from core.strategy.base import BaseStrategy, Bar, Order, Trade, OrderSide, OrderStatus


@dataclass
class BacktestResult:
    """回测结果"""
    # 基本信息
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 0.0
    final_capital: float = 0.0

    # 收益指标
    total_return: float = 0.0        # 总收益率
    annual_return: float = 0.0       # 年化收益率
    benchmark_return: float = 0.0    # 基准收益率

    # 风险指标
    max_drawdown: float = 0.0        # 最大回撤
    max_drawdown_duration: int = 0   # 最大回撤持续天数
    volatility: float = 0.0          # 波动率
    sharpe_ratio: float = 0.0        # 夏普比率
    sortino_ratio: float = 0.0       # 索提诺比率
    calmar_ratio: float = 0.0        # 卡玛比率

    # 交易统计
    total_trades: int = 0            # 总交易次数
    win_trades: int = 0              # 盈利次数
    loss_trades: int = 0             # 亏损次数
    win_rate: float = 0.0            # 胜率
    profit_loss_ratio: float = 0.0   # 盈亏比
    avg_profit: float = 0.0          # 平均盈利
    avg_loss: float = 0.0            # 平均亏损
    max_profit: float = 0.0          # 最大单笔盈利
    max_loss: float = 0.0            # 最大单笔亏损

    # 详细数据
    equity_curve: List[float] = field(default_factory=list)  # 资金曲线
    trades: List[Trade] = field(default_factory=list)        # 交易记录
    daily_returns: List[float] = field(default_factory=list) # 日收益率
    dates: List = field(default_factory=list)                # 对应的日期序列


class BacktestEngine:
    """回测引擎"""

    def __init__(self):
        self.strategy: Optional[BaseStrategy] = None
        self.data: Dict[str, pd.DataFrame] = {}
        self.initial_capital = 1000000.0
        self.commission_rate = 0.0003  # 手续费率
        self.slippage = 0.001          # 滑点
        self.result: Optional[BacktestResult] = None
        self._indexed_data: Dict[str, pd.DataFrame] = {}

    def set_strategy(self, strategy: BaseStrategy):
        """设置策略"""
        self.strategy = strategy

    def set_capital(self, capital: float):
        """设置初始资金"""
        self.initial_capital = capital

    def set_commission(self, rate: float):
        """设置手续费率"""
        self.commission_rate = rate

    def set_slippage(self, slippage: float):
        """设置滑点"""
        self.slippage = slippage

    def add_data(self, code: str, data: pd.DataFrame):
        """
        添加回测数据

        Args:
            code: 股票代码
            data: K线数据 (需包含 date, open, high, low, close, volume 列)
        """
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"数据缺少必要列: {col}")

        df = data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        self.data[code] = df
        indexed = df.set_index('date', drop=False)
        self._indexed_data[code] = indexed

    def run(self) -> BacktestResult:
        """运行回测"""
        if self.strategy is None:
            raise ValueError("请先设置策略")
        if not self.data:
            raise ValueError("请先添加回测数据")

        # 初始化策略
        self.strategy.set_capital(self.initial_capital)
        self.strategy.on_start()

        # 获取所有日期（已去重）
        indexed_data = self._indexed_data or {
            code: df.set_index('date', drop=False)
            for code, df in self.data.items()
        }
        self._indexed_data = indexed_data
        all_dates = sorted({date for df in indexed_data.values() for date in df.index.unique()})

        # 资金曲线
        equity_curve = [self.initial_capital]

        # 按日期遍历
        for date in all_dates:
            for code, df in indexed_data.items():
                if date not in df.index:
                    continue

                row = df.loc[date]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]

                bar = self._row_to_bar(row)

                # 处理待成交订单
                self._process_orders(code, bar)

                # 调用策略
                self.strategy._on_bar(code, bar)

            # 记录资金曲线
            equity_curve.append(self.strategy.total_value)

        # 策略结束
        self.strategy.on_stop()

        # 计算回测结果
        self.result = self._calculate_result(equity_curve, all_dates)
        return self.result

    @staticmethod
    def _row_to_bar(row: pd.Series) -> Bar:
        """将DataFrame行转换为Bar对象"""
        amount = row.get('amount')
        if amount is None:
            amount = float(row.get('close', 0)) * float(row.get('volume', 0))
        return Bar(
            datetime=row['date'],
            open=float(row.get('open', 0)),
            high=float(row.get('high', 0)),
            low=float(row.get('low', 0)),
            close=float(row.get('close', 0)),
            volume=float(row.get('volume', 0)),
            amount=float(amount)
        )

    def _process_orders(self, code: str, bar: Bar):
        """处理订单成交"""
        for order in self.strategy.orders:
            if order.code != code or order.status != OrderStatus.SUBMITTED:
                continue

            # 判断是否可以成交
            can_fill = False
            fill_price = order.price

            if order.side == OrderSide.BUY:
                # 买入: 价格 >= 委托价
                if bar.low <= order.price:
                    can_fill = True
                    fill_price = min(order.price, bar.open)
                    # 加滑点
                    fill_price *= (1 + self.slippage)
            else:
                # 卖出: 价格 <= 委托价
                if bar.high >= order.price:
                    can_fill = True
                    fill_price = max(order.price, bar.open)
                    # 减滑点
                    fill_price *= (1 - self.slippage)

            if can_fill:
                # 计算手续费
                commission = fill_price * order.quantity * self.commission_rate
                # 印花税 (卖出时收取)
                if order.side == OrderSide.SELL:
                    commission += fill_price * order.quantity * 0.001

                trade = Trade(
                    trade_id=f"T{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    order_id=order.order_id,
                    code=code,
                    side=order.side,
                    price=fill_price,
                    quantity=order.quantity,
                    commission=commission,
                    trade_time=bar.datetime
                )

                self.strategy._on_order_filled(order, trade)

    def _calculate_result(self, equity_curve: List[float], dates: List) -> BacktestResult:
        """计算回测结果"""
        result = BacktestResult()

        equity = np.array(equity_curve, dtype=float)

        # 基本信息
        result.start_date = dates[0].strftime("%Y-%m-%d") if dates else ""
        result.end_date = dates[-1].strftime("%Y-%m-%d") if dates else ""
        result.initial_capital = float(equity[0]) if equity.size else self.initial_capital
        result.final_capital = float(equity[-1]) if equity.size else self.initial_capital
        result.equity_curve = equity_curve
        result.dates = list(dates)

        if equity.size > 0 and result.initial_capital > 0:
            growth = result.final_capital / result.initial_capital
            result.total_return = (growth - 1) * 100

        # 年化收益率
        if len(dates) > 1 and result.initial_capital > 0 and result.final_capital > 0:
            delta_days = max((dates[-1] - dates[0]).days, len(dates))
            if delta_days > 0:
                result.annual_return = (pow(result.final_capital / result.initial_capital, 365 / delta_days) - 1) * 100

        # 向量化计算日收益率
        if equity.size > 1:
            returns = np.diff(equity) / equity[:-1]
            result.daily_returns = returns.tolist()

            # 波动率（年化）
            if returns.size > 1:
                result.volatility = float(np.std(returns, ddof=1) * np.sqrt(252) * 100)

            # 最大回撤
            running_max = np.maximum.accumulate(equity)
            running_max[running_max == 0] = 1
            drawdown = (running_max - equity) / running_max
            result.max_drawdown = float(drawdown.max() * 100)
        else:
            result.daily_returns = []

        # 夏普与卡玛
        if result.volatility > 0:
            result.sharpe_ratio = (result.annual_return - 3) / result.volatility
        if result.max_drawdown > 0:
            result.calmar_ratio = result.annual_return / result.max_drawdown

        # 交易统计
        trades = self.strategy.trades
        result.trades = trades
        result.total_trades = len(trades)

        # 计算每笔交易盈亏
        trade_profits = []
        buy_trades = {}

        for trade in trades:
            if trade.side == OrderSide.BUY:
                if trade.code not in buy_trades:
                    buy_trades[trade.code] = []
                buy_trades[trade.code].append(trade)
            else:
                # 卖出时计算盈亏
                if trade.code in buy_trades and buy_trades[trade.code]:
                    buy_trade = buy_trades[trade.code].pop(0)
                    profit = (trade.price - buy_trade.price) * trade.quantity - trade.commission - buy_trade.commission
                    trade_profits.append(profit)

        if trade_profits:
            wins = [p for p in trade_profits if p > 0]
            losses = [p for p in trade_profits if p < 0]

            result.win_trades = len(wins)
            result.loss_trades = len(losses)
            result.win_rate = len(wins) / len(trade_profits) * 100 if trade_profits else 0

            result.avg_profit = np.mean(wins) if wins else 0
            result.avg_loss = np.mean(losses) if losses else 0
            result.max_profit = max(wins) if wins else 0
            result.max_loss = min(losses) if losses else 0

            if result.avg_loss != 0:
                result.profit_loss_ratio = abs(result.avg_profit / result.avg_loss)

        return result

    def get_report(self) -> str:
        """生成回测报告"""
        if self.result is None:
            return "请先运行回测"

        r = self.result
        report = f"""
========== 回测报告 ==========

【基本信息】
回测区间: {r.start_date} ~ {r.end_date}
初始资金: ¥{r.initial_capital:,.2f}
最终资金: ¥{r.final_capital:,.2f}

【收益指标】
总收益率: {r.total_return:.2f}%
年化收益率: {r.annual_return:.2f}%

【风险指标】
最大回撤: {r.max_drawdown:.2f}%
波动率: {r.volatility:.2f}%
夏普比率: {r.sharpe_ratio:.2f}
卡玛比率: {r.calmar_ratio:.2f}

【交易统计】
总交易次数: {r.total_trades}
盈利次数: {r.win_trades}
亏损次数: {r.loss_trades}
胜率: {r.win_rate:.2f}%
盈亏比: {r.profit_loss_ratio:.2f}
平均盈利: ¥{r.avg_profit:,.2f}
平均亏损: ¥{r.avg_loss:,.2f}
最大单笔盈利: ¥{r.max_profit:,.2f}
最大单笔亏损: ¥{r.max_loss:,.2f}

==============================
"""
        return report
