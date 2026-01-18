"""
风险控制模块
"""
import csv
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.strategy.base import Order, Position, OrderSide


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAlert:
    """风险警报"""
    level: RiskLevel
    message: str
    timestamp: datetime
    code: str = ""


@dataclass
class RiskConfig:
    """风控配置"""
    # 仓位控制
    max_position_pct: float = 30.0      # 单只股票最大仓位比例 (%)
    max_total_position_pct: float = 80.0  # 总仓位最大比例 (%)

    # 止损止盈
    stop_loss_pct: float = 5.0          # 止损比例 (%)
    take_profit_pct: float = 10.0       # 止盈比例 (%)
    trailing_stop_pct: float = 0.0      # 移动止损比例 (%)

    # 回撤控制
    max_drawdown_pct: float = 20.0      # 最大回撤比例 (%)

    # 交易限制
    max_daily_trades: int = 50          # 每日最大交易次数
    max_daily_loss: float = 50000.0     # 每日最大亏损金额
    min_trade_interval: int = 60        # 最小交易间隔 (秒)

    # 价格限制
    max_price_deviation: float = 3.0    # 最大价格偏离 (%)


class RiskManager:
    """风险管理器"""

    def __init__(self, config: RiskConfig = None, journal_path: Optional[str] = None):
        self.config = config or RiskConfig()
        self.alerts: List[RiskAlert] = []
        self.journal_path = Path(journal_path) if journal_path else None

        # 状态跟踪
        self.peak_value = 0.0           # 历史最高资产
        self.daily_trades = 0           # 当日交易次数
        self.daily_loss = 0.0           # 当日亏损
        self.last_trade_time: Optional[datetime] = None
        self.is_trading_allowed = True

        # 回调
        self.on_alert: Optional[Callable[[RiskAlert], None]] = None
        self.on_stop_trading: Optional[Callable[[str], None]] = None

    def reset_daily(self):
        """重置每日统计"""
        self.daily_trades = 0
        self.daily_loss = 0.0
        self.is_trading_allowed = True

    def update_peak_value(self, total_value: float):
        """更新历史最高资产"""
        if total_value > self.peak_value:
            self.peak_value = total_value

    def check_order(self, order: Order, positions: Dict[str, Position],
                    cash: float, total_value: float, current_price: float) -> tuple[bool, str]:
        """
        检查订单是否符合风控规则

        Returns:
            (是否通过, 原因)
        """
        # 检查交易是否被禁止
        if not self.is_trading_allowed:
            return False, "交易已被风控暂停"

        # 检查每日交易次数
        if self.daily_trades >= self.config.max_daily_trades:
            self._add_alert(RiskLevel.HIGH, "已达到每日最大交易次数限制", order.code)
            return False, "已达到每日最大交易次数限制"

        # 检查交易间隔
        if self.last_trade_time:
            elapsed = (datetime.now() - self.last_trade_time).total_seconds()
            if elapsed < self.config.min_trade_interval:
                return False, f"交易间隔过短，请等待{self.config.min_trade_interval - elapsed:.0f}秒"

        # 检查价格偏离
        if current_price > 0:
            deviation = abs(order.price - current_price) / current_price * 100
            if deviation > self.config.max_price_deviation:
                self._add_alert(RiskLevel.MEDIUM, f"委托价格偏离当前价格{deviation:.2f}%", order.code)
                return False, f"价格偏离过大: {deviation:.2f}%"

        # 买入检查
        if order.side == OrderSide.BUY:
            # 检查单只股票仓位
            order_value = order.price * order.quantity
            if order_value > cash:
                return False, "资金不足"

            existing_value = 0
            if order.code in positions:
                existing_value = positions[order.code].market_value

            new_position_pct = (existing_value + order_value) / total_value * 100
            if new_position_pct > self.config.max_position_pct:
                self._add_alert(RiskLevel.MEDIUM, f"单只股票仓位将超过{self.config.max_position_pct}%", order.code)
                return False, f"单只股票仓位将超过{self.config.max_position_pct}%"

            # 检查总仓位
            total_position_value = sum(pos.market_value for pos in positions.values())
            new_total_pct = (total_position_value + order_value) / total_value * 100
            if new_total_pct > self.config.max_total_position_pct:
                self._add_alert(RiskLevel.MEDIUM, f"总仓位将超过{self.config.max_total_position_pct}%", order.code)
                return False, f"总仓位将超过{self.config.max_total_position_pct}%"

        return True, ""

    def check_position(self, position: Position) -> List[RiskAlert]:
        """
        检查持仓风险

        Returns:
            风险警报列表
        """
        alerts = []

        if position.quantity <= 0:
            return alerts

        profit_pct = position.profit_pct

        # 检查止损
        if profit_pct <= -self.config.stop_loss_pct:
            alert = RiskAlert(
                level=RiskLevel.HIGH,
                message=f"触发止损: 亏损{abs(profit_pct):.2f}%",
                timestamp=datetime.now(),
                code=position.code
            )
            alerts.append(alert)
            self._add_alert(alert.level, alert.message, alert.code)

        # 检查止盈
        elif profit_pct >= self.config.take_profit_pct:
            alert = RiskAlert(
                level=RiskLevel.MEDIUM,
                message=f"触发止盈: 盈利{profit_pct:.2f}%",
                timestamp=datetime.now(),
                code=position.code
            )
            alerts.append(alert)
            self._add_alert(alert.level, alert.message, alert.code)

        return alerts

    def check_drawdown(self, total_value: float) -> bool:
        """
        检查回撤

        Returns:
            是否触发最大回撤
        """
        if self.peak_value <= 0:
            return False

        drawdown = (self.peak_value - total_value) / self.peak_value * 100

        if drawdown >= self.config.max_drawdown_pct:
            self._add_alert(
                RiskLevel.CRITICAL,
                f"触发最大回撤限制: {drawdown:.2f}%",
                ""
            )
            self.is_trading_allowed = False
            if self.on_stop_trading:
                self.on_stop_trading(f"触发最大回撤限制: {drawdown:.2f}%")
            return True

        return False

    def check_daily_loss(self, loss: float) -> bool:
        """
        检查每日亏损

        Returns:
            是否触发每日最大亏损
        """
        self.daily_loss += loss

        if self.daily_loss >= self.config.max_daily_loss:
            self._add_alert(
                RiskLevel.CRITICAL,
                f"触发每日最大亏损限制: ¥{self.daily_loss:.2f}",
                ""
            )
            self.is_trading_allowed = False
            if self.on_stop_trading:
                self.on_stop_trading(f"触发每日最大亏损限制: ¥{self.daily_loss:.2f}")
            return True

        return False

    def on_trade_completed(self):
        """交易完成回调"""
        self.daily_trades += 1
        self.last_trade_time = datetime.now()

    def _add_alert(self, level: RiskLevel, message: str, code: str):
        """添加警报"""
        alert = RiskAlert(
            level=level,
            message=message,
            timestamp=datetime.now(),
            code=code
        )
        self.alerts.append(alert)
        self._persist_alert(alert)

        if self.on_alert:
            self.on_alert(alert)

    def get_alerts(self, level: RiskLevel = None) -> List[RiskAlert]:
        """获取警报"""
        if level is None:
            return self.alerts
        return [a for a in self.alerts if a.level == level]

    def clear_alerts(self):
        """清除警报"""
        self.alerts.clear()

    def get_risk_summary(self, positions: Dict[str, Position], total_value: float) -> Dict:
        """获取风险摘要"""
        # 计算当前回撤
        drawdown = 0
        if self.peak_value > 0:
            drawdown = (self.peak_value - total_value) / self.peak_value * 100

        # 计算总仓位
        total_position = sum(pos.market_value for pos in positions.values())
        position_pct = total_position / total_value * 100 if total_value > 0 else 0

        # 统计持仓风险
        stop_loss_count = 0
        take_profit_count = 0
        for pos in positions.values():
            if pos.profit_pct <= -self.config.stop_loss_pct:
                stop_loss_count += 1
            elif pos.profit_pct >= self.config.take_profit_pct:
                take_profit_count += 1

        return {
            'drawdown': drawdown,
            'max_drawdown': self.config.max_drawdown_pct,
            'position_pct': position_pct,
            'max_position_pct': self.config.max_total_position_pct,
            'daily_trades': self.daily_trades,
            'max_daily_trades': self.config.max_daily_trades,
            'daily_loss': self.daily_loss,
            'max_daily_loss': self.config.max_daily_loss,
            'stop_loss_count': stop_loss_count,
            'take_profit_count': take_profit_count,
            'is_trading_allowed': self.is_trading_allowed,
            'alert_count': len(self.alerts)
        }

    def _persist_alert(self, alert: RiskAlert):
        if not self.journal_path:
            return
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self.journal_path.exists()
        with self.journal_path.open('a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["timestamp", "level", "code", "message"])
            writer.writerow([alert.timestamp.isoformat(), alert.level.value, alert.code, alert.message])
