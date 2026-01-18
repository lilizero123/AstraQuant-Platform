"""
策略基类
所有交易策略都应继承此基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"  # 市价单
    LIMIT = "limit"    # 限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"      # 待提交
    SUBMITTED = "submitted"  # 已提交
    FILLED = "filled"        # 已成交
    CANCELLED = "cancelled"  # 已撤销
    REJECTED = "rejected"    # 已拒绝


@dataclass
class Bar:
    """K线数据"""
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0


@dataclass
class Order:
    """订单"""
    order_id: str
    code: str
    side: OrderSide
    price: float
    quantity: int
    order_type: OrderType = OrderType.LIMIT
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    create_time: datetime = None
    update_time: datetime = None


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    order_id: str
    code: str
    side: OrderSide
    price: float
    quantity: int
    commission: float
    trade_time: datetime


@dataclass
class Position:
    """持仓"""
    code: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price

    @property
    def profit(self) -> float:
        """盈亏"""
        return (self.current_price - self.avg_cost) * self.quantity

    @property
    def profit_pct(self) -> float:
        """盈亏比例"""
        if self.avg_cost == 0:
            return 0
        return (self.current_price - self.avg_cost) / self.avg_cost * 100


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self):
        self.name = self.__class__.__name__
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.cash = 0.0
        self.initial_capital = 0.0

        # 历史数据
        self._bars: Dict[str, List[Bar]] = {}
        self._current_bar: Optional[Bar] = None
        self._current_code: str = ""

        # 回调函数
        self._order_callback = None
        self._trade_callback = None
        self._log_callback = None

    def set_capital(self, capital: float):
        """设置初始资金"""
        self.initial_capital = capital
        self.cash = capital

    def set_callbacks(self, order_callback=None, trade_callback=None, log_callback=None):
        """设置回调函数"""
        self._order_callback = order_callback
        self._trade_callback = trade_callback
        self._log_callback = log_callback

    def log(self, message: str):
        """输出日志"""
        if self._log_callback:
            self._log_callback(message)
        else:
            print(f"[{self.name}] {message}")

    @property
    def position(self) -> int:
        """当前股票持仓数量"""
        if self._current_code in self.positions:
            return self.positions[self._current_code].quantity
        return 0

    @property
    def total_value(self) -> float:
        """总资产"""
        market_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + market_value

    def get_close_prices(self, count: int) -> List[float]:
        """获取最近N个收盘价"""
        if self._current_code not in self._bars:
            return []
        bars = self._bars[self._current_code]
        return [bar.close for bar in bars[-count:]]

    def get_bars(self, count: int) -> List[Bar]:
        """获取最近N根K线"""
        if self._current_code not in self._bars:
            return []
        return self._bars[self._current_code][-count:]

    def buy(self, price: float, quantity: int, order_type: OrderType = OrderType.LIMIT) -> Optional[Order]:
        """
        买入

        Args:
            price: 价格
            quantity: 数量 (必须是100的整数倍)
            order_type: 订单类型
        """
        # 检查数量
        quantity = (quantity // 100) * 100
        if quantity <= 0:
            self.log("买入数量必须大于0")
            return None

        # 检查资金
        required = price * quantity
        if required > self.cash:
            self.log(f"资金不足: 需要{required:.2f}, 可用{self.cash:.2f}")
            return None

        # 创建订单
        order = Order(
            order_id=f"O{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            code=self._current_code,
            side=OrderSide.BUY,
            price=price,
            quantity=quantity,
            order_type=order_type,
            status=OrderStatus.SUBMITTED,
            create_time=datetime.now()
        )

        self.orders.append(order)
        self.log(f"买入委托: {self._current_code} 价格:{price:.2f} 数量:{quantity}")

        if self._order_callback:
            self._order_callback(order)

        return order

    def sell(self, price: float, quantity: int, order_type: OrderType = OrderType.LIMIT) -> Optional[Order]:
        """
        卖出

        Args:
            price: 价格
            quantity: 数量
            order_type: 订单类型
        """
        # 检查持仓
        if self.position < quantity:
            self.log(f"持仓不足: 需要{quantity}, 持有{self.position}")
            return None

        # 创建订单
        order = Order(
            order_id=f"O{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            code=self._current_code,
            side=OrderSide.SELL,
            price=price,
            quantity=quantity,
            order_type=order_type,
            status=OrderStatus.SUBMITTED,
            create_time=datetime.now()
        )

        self.orders.append(order)
        self.log(f"卖出委托: {self._current_code} 价格:{price:.2f} 数量:{quantity}")

        if self._order_callback:
            self._order_callback(order)

        return order

    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        for order in self.orders:
            if order.order_id == order_id and order.status == OrderStatus.SUBMITTED:
                order.status = OrderStatus.CANCELLED
                order.update_time = datetime.now()
                self.log(f"撤单成功: {order_id}")
                return True
        return False

    # 以下方法由回测引擎或交易引擎调用
    def _on_bar(self, code: str, bar: Bar):
        """K线数据回调 (内部使用)"""
        self._current_code = code
        self._current_bar = bar

        if code not in self._bars:
            self._bars[code] = []
        self._bars[code].append(bar)

        # 更新持仓价格
        if code in self.positions:
            self.positions[code].current_price = bar.close

        # 调用策略的on_bar方法
        self.on_bar(bar)

    def _on_order_filled(self, order: Order, trade: Trade):
        """订单成交回调 (内部使用)"""
        order.status = OrderStatus.FILLED
        order.filled_quantity = trade.quantity
        order.filled_price = trade.price
        order.update_time = datetime.now()

        self.trades.append(trade)

        # 更新持仓和资金
        if trade.side == OrderSide.BUY:
            self.cash -= trade.price * trade.quantity + trade.commission
            if trade.code in self.positions:
                pos = self.positions[trade.code]
                total_cost = pos.avg_cost * pos.quantity + trade.price * trade.quantity
                pos.quantity += trade.quantity
                pos.avg_cost = total_cost / pos.quantity
            else:
                self.positions[trade.code] = Position(
                    code=trade.code,
                    quantity=trade.quantity,
                    avg_cost=trade.price,
                    current_price=trade.price
                )
        else:
            self.cash += trade.price * trade.quantity - trade.commission
            if trade.code in self.positions:
                self.positions[trade.code].quantity -= trade.quantity
                if self.positions[trade.code].quantity <= 0:
                    del self.positions[trade.code]

        if self._trade_callback:
            self._trade_callback(trade)

        self.on_trade(trade)

    # 以下方法需要子类实现
    @abstractmethod
    def on_bar(self, bar: Bar):
        """
        K线数据回调

        Args:
            bar: K线数据
        """
        pass

    def on_order(self, order: Order):
        """订单回调"""
        pass

    def on_trade(self, trade: Trade):
        """成交回调"""
        pass

    def on_start(self):
        """策略启动"""
        pass

    def on_stop(self):
        """策略停止"""
        pass
