"""
交易执行模块
支持模拟交易和实盘交易
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import threading
import time

from core.strategy.base import Order, Trade, Position, OrderSide, OrderStatus, OrderType


class TraderStatus(Enum):
    """交易状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    TRADING = "trading"
    ERROR = "error"


class BaseTrader(ABC):
    """交易接口基类"""

    def __init__(self):
        self.status = TraderStatus.DISCONNECTED
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.cash = 0.0
        self.total_value = 0.0

        # 回调函数
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_order: Optional[Callable[[Order], None]] = None
        self.on_trade: Optional[Callable[[Trade], None]] = None
        self.on_position: Optional[Callable[[Position], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    @abstractmethod
    def connect(self) -> bool:
        """连接交易服务器"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def send_order(self, code: str, side: OrderSide, price: float, quantity: int,
                   order_type: OrderType = OrderType.LIMIT) -> Optional[Order]:
        """发送订单"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        pass

    @abstractmethod
    def query_positions(self) -> List[Position]:
        """查询持仓"""
        pass

    @abstractmethod
    def query_orders(self) -> List[Order]:
        """查询订单"""
        pass

    @abstractmethod
    def query_trades(self) -> List[Trade]:
        """查询成交"""
        pass

    @abstractmethod
    def query_account(self) -> Dict:
        """查询账户"""
        pass


class SimulatedTrader(BaseTrader):
    """模拟交易"""

    def __init__(self, initial_capital: float = 1000000.0):
        super().__init__()
        self.cash = initial_capital
        self.total_value = initial_capital
        self.commission_rate = 0.0003  # 手续费率
        self._order_id_counter = 0
        self._trade_id_counter = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 模拟行情数据
        self._market_prices: Dict[str, float] = {}

    def connect(self) -> bool:
        """连接模拟交易服务器"""
        self.status = TraderStatus.CONNECTING
        time.sleep(0.5)  # 模拟连接延迟
        self.status = TraderStatus.CONNECTED
        self._running = True

        # 启动订单处理线程
        self._thread = threading.Thread(target=self._process_orders_loop, daemon=True)
        self._thread.start()

        if self.on_connected:
            self.on_connected()
        return True

    def disconnect(self):
        """断开连接"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        self.status = TraderStatus.DISCONNECTED
        if self.on_disconnected:
            self.on_disconnected()

    def set_market_price(self, code: str, price: float):
        """设置市场价格 (用于模拟)"""
        self._market_prices[code] = price

    def send_order(self, code: str, side: OrderSide, price: float, quantity: int,
                   order_type: OrderType = OrderType.LIMIT) -> Optional[Order]:
        """发送订单"""
        if self.status != TraderStatus.CONNECTED:
            if self.on_error:
                self.on_error("交易未连接")
            return None

        # 检查买入资金
        if side == OrderSide.BUY:
            required = price * quantity * (1 + self.commission_rate)
            if required > self.cash:
                if self.on_error:
                    self.on_error(f"资金不足: 需要{required:.2f}, 可用{self.cash:.2f}")
                return None

        # 检查卖出持仓
        if side == OrderSide.SELL:
            if code not in self.positions or self.positions[code].quantity < quantity:
                if self.on_error:
                    self.on_error("持仓不足")
                return None

        # 创建订单
        self._order_id_counter += 1
        order = Order(
            order_id=f"SIM{self._order_id_counter:08d}",
            code=code,
            side=side,
            price=price,
            quantity=quantity,
            order_type=order_type,
            status=OrderStatus.SUBMITTED,
            create_time=datetime.now()
        )

        self.orders.append(order)

        if self.on_order:
            self.on_order(order)

        return order

    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        for order in self.orders:
            if order.order_id == order_id and order.status == OrderStatus.SUBMITTED:
                order.status = OrderStatus.CANCELLED
                order.update_time = datetime.now()
                if self.on_order:
                    self.on_order(order)
                return True
        return False

    def query_positions(self) -> List[Position]:
        """查询持仓"""
        return list(self.positions.values())

    def query_orders(self) -> List[Order]:
        """查询订单"""
        return self.orders

    def query_trades(self) -> List[Trade]:
        """查询成交"""
        return self.trades

    def query_account(self) -> Dict:
        """查询账户"""
        market_value = sum(pos.market_value for pos in self.positions.values())
        return {
            'cash': self.cash,
            'market_value': market_value,
            'total_value': self.cash + market_value,
            'frozen': 0
        }

    def _process_orders_loop(self):
        """订单处理循环"""
        while self._running:
            self._process_pending_orders()
            time.sleep(0.1)

    def _process_pending_orders(self):
        """处理待成交订单"""
        for order in self.orders:
            if order.status != OrderStatus.SUBMITTED:
                continue

            # 获取市场价格
            market_price = self._market_prices.get(order.code, order.price)

            # 判断是否可以成交
            can_fill = False
            if order.order_type == OrderType.MARKET:
                can_fill = True
            elif order.side == OrderSide.BUY and market_price <= order.price:
                can_fill = True
            elif order.side == OrderSide.SELL and market_price >= order.price:
                can_fill = True

            if can_fill:
                self._fill_order(order, market_price)

    def _fill_order(self, order: Order, fill_price: float):
        """成交订单"""
        # 计算手续费
        commission = fill_price * order.quantity * self.commission_rate
        if order.side == OrderSide.SELL:
            commission += fill_price * order.quantity * 0.001  # 印花税

        # 创建成交记录
        self._trade_id_counter += 1
        trade = Trade(
            trade_id=f"T{self._trade_id_counter:08d}",
            order_id=order.order_id,
            code=order.code,
            side=order.side,
            price=fill_price,
            quantity=order.quantity,
            commission=commission,
            trade_time=datetime.now()
        )

        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.update_time = datetime.now()

        # 更新资金和持仓
        if order.side == OrderSide.BUY:
            self.cash -= fill_price * order.quantity + commission
            if order.code in self.positions:
                pos = self.positions[order.code]
                total_cost = pos.avg_cost * pos.quantity + fill_price * order.quantity
                pos.quantity += order.quantity
                pos.avg_cost = total_cost / pos.quantity
            else:
                self.positions[order.code] = Position(
                    code=order.code,
                    quantity=order.quantity,
                    avg_cost=fill_price,
                    current_price=fill_price
                )
        else:
            self.cash += fill_price * order.quantity - commission
            if order.code in self.positions:
                self.positions[order.code].quantity -= order.quantity
                if self.positions[order.code].quantity <= 0:
                    del self.positions[order.code]

        self.trades.append(trade)

        # 回调
        if self.on_order:
            self.on_order(order)
        if self.on_trade:
            self.on_trade(trade)


class TradeManager:
    """交易管理器"""

    def __init__(self):
        self.trader: Optional[BaseTrader] = None
        self.is_trading = False

    def set_trader(self, trader: BaseTrader):
        """设置交易接口"""
        self.trader = trader

    def connect(self) -> bool:
        """连接"""
        if self.trader is None:
            return False
        return self.trader.connect()

    def disconnect(self):
        """断开"""
        if self.trader:
            self.trader.disconnect()

    def start_trading(self):
        """开始交易"""
        self.is_trading = True

    def stop_trading(self):
        """停止交易"""
        self.is_trading = False

    def buy(self, code: str, price: float, quantity: int) -> Optional[Order]:
        """买入"""
        if not self.is_trading or self.trader is None:
            return None
        return self.trader.send_order(code, OrderSide.BUY, price, quantity)

    def sell(self, code: str, price: float, quantity: int) -> Optional[Order]:
        """卖出"""
        if not self.is_trading or self.trader is None:
            return None
        return self.trader.send_order(code, OrderSide.SELL, price, quantity)

    def cancel(self, order_id: str) -> bool:
        """撤单"""
        if self.trader is None:
            return False
        return self.trader.cancel_order(order_id)

    def get_positions(self) -> List[Position]:
        """获取持仓"""
        if self.trader is None:
            return []
        return self.trader.query_positions()

    def get_account(self) -> Dict:
        """获取账户"""
        if self.trader is None:
            return {}
        return self.trader.query_account()
