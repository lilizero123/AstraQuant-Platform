"""
券商交易接口模块
提供统一的券商API对接框架
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import threading
import time
import json

from core.strategy.base import Order, Trade, Position, OrderSide, OrderStatus, OrderType
from core.logger import get_log_manager, LogCategory


class BrokerType(Enum):
    """券商类型"""
    SIMULATED = "simulated"     # 模拟交易
    HUATAI = "huatai"           # 华泰证券
    ZHONGXIN = "zhongxin"       # 中信证券
    GUOTAIJUNAN = "guotaijunan" # 国泰君安
    HAITONG = "haitong"         # 海通证券
    GUANGFA = "guangfa"         # 广发证券


@dataclass
class BrokerConfig:
    """券商配置"""
    broker_type: BrokerType
    account: str = ""
    password: str = ""
    server: str = ""
    port: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountInfo:
    """账户信息"""
    account_id: str
    broker: str
    cash: float                 # 可用资金
    frozen: float = 0.0         # 冻结资金
    market_value: float = 0.0   # 持仓市值
    total_value: float = 0.0    # 总资产
    profit: float = 0.0         # 当日盈亏
    profit_pct: float = 0.0     # 当日盈亏比例


@dataclass
class OrderResult:
    """下单结果"""
    success: bool
    order_id: str = ""
    message: str = ""
    order: Optional[Order] = None


class BrokerTrader(ABC):
    """券商交易接口基类"""

    def __init__(self, config: BrokerConfig):
        self.config = config
        self.logger = get_log_manager()
        self._connected = False
        self._logged_in = False

        # 数据缓存
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Order] = {}
        self._trades: List[Trade] = []
        self._account: Optional[AccountInfo] = None

        # 回调函数
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_login: Optional[Callable] = None
        self.on_logout: Optional[Callable] = None
        self.on_order_update: Optional[Callable[[Order], None]] = None
        self.on_trade_update: Optional[Callable[[Trade], None]] = None
        self.on_position_update: Optional[Callable[[Position], None]] = None
        self.on_account_update: Optional[Callable[[AccountInfo], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # 线程锁
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    # ==================== 连接管理 ====================

    @abstractmethod
    def connect(self) -> bool:
        """连接交易服务器"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def login(self) -> bool:
        """登录账户"""
        pass

    @abstractmethod
    def logout(self):
        """登出账户"""
        pass

    # ==================== 交易操作 ====================

    @abstractmethod
    def send_order(self, code: str, side: OrderSide, price: float, quantity: int,
                   order_type: OrderType = OrderType.LIMIT) -> OrderResult:
        """
        发送订单

        Args:
            code: 股票代码
            side: 买卖方向
            price: 价格
            quantity: 数量
            order_type: 订单类型

        Returns:
            下单结果
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        pass

    @abstractmethod
    def modify_order(self, order_id: str, price: float = None, quantity: int = None) -> bool:
        """修改订单（部分券商支持）"""
        pass

    # ==================== 查询操作 ====================

    @abstractmethod
    def query_account(self) -> Optional[AccountInfo]:
        """查询账户信息"""
        pass

    @abstractmethod
    def query_positions(self) -> List[Position]:
        """查询持仓"""
        pass

    @abstractmethod
    def query_orders(self, status: OrderStatus = None) -> List[Order]:
        """查询订单"""
        pass

    @abstractmethod
    def query_trades(self) -> List[Trade]:
        """查询成交"""
        pass

    # ==================== 辅助方法 ====================

    def _log_info(self, message: str):
        self.logger.info(f"[{self.config.broker_type.value}] {message}", LogCategory.TRADE)

    def _log_error(self, message: str):
        self.logger.error(f"[{self.config.broker_type.value}] {message}", LogCategory.TRADE)
        if self.on_error:
            self.on_error(message)

    def _notify_order_update(self, order: Order):
        with self._lock:
            self._orders[order.order_id] = order
        if self.on_order_update:
            self.on_order_update(order)

    def _notify_trade_update(self, trade: Trade):
        with self._lock:
            self._trades.append(trade)
        if self.on_trade_update:
            self.on_trade_update(trade)

    def _notify_position_update(self, position: Position):
        with self._lock:
            self._positions[position.code] = position
        if self.on_position_update:
            self.on_position_update(position)


class SimulatedBroker(BrokerTrader):
    """模拟券商（用于测试和演示）"""

    def __init__(self, config: BrokerConfig = None):
        if config is None:
            config = BrokerConfig(broker_type=BrokerType.SIMULATED)
        super().__init__(config)

        self._initial_capital = config.extra.get('initial_capital', 1000000.0)
        self._cash = self._initial_capital
        self._commission_rate = config.extra.get('commission_rate', 0.0003)
        self._slippage = config.extra.get('slippage', 0.001)

        self._order_counter = 0
        self._trade_counter = 0
        self._market_prices: Dict[str, float] = {}

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._position_lots: Dict[str, List[Dict[str, Any]]] = {}

    def set_market_price(self, code: str, price: float):
        """设置市场价格"""
        self._market_prices[code] = price

    def connect(self) -> bool:
        self._log_info("连接模拟交易服务器...")
        time.sleep(0.3)
        self._connected = True
        self._log_info("连接成功")
        if self.on_connected:
            self.on_connected()
        return True

    def disconnect(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._connected = False
        self._logged_in = False
        self._log_info("已断开连接")
        if self.on_disconnected:
            self.on_disconnected()

    def login(self) -> bool:
        if not self._connected:
            self._log_error("请先连接服务器")
            return False

        self._log_info("登录模拟账户...")
        time.sleep(0.2)
        self._logged_in = True

        # 启动订单处理线程
        self._running = True
        self._thread = threading.Thread(target=self._order_process_loop, daemon=True)
        self._thread.start()

        self._log_info("登录成功")
        if self.on_login:
            self.on_login()
        return True

    def logout(self):
        self._running = False
        self._logged_in = False
        self._log_info("已登出")
        if self.on_logout:
            self.on_logout()

    def send_order(self, code: str, side: OrderSide, price: float, quantity: int,
                   order_type: OrderType = OrderType.LIMIT) -> OrderResult:
        if not self._logged_in:
            return OrderResult(success=False, message="请先登录")

        # 数量必须是100的整数倍
        quantity = (quantity // 100) * 100
        if quantity <= 0:
            return OrderResult(success=False, message="数量必须大于0")

        # 检查资金/持仓
        if side == OrderSide.BUY:
            required = price * quantity * (1 + self._commission_rate)
            if required > self._cash:
                return OrderResult(success=False, message=f"资金不足: 需要{required:.2f}, 可用{self._cash:.2f}")
        else:
            pos = self._positions.get(code)
            sellable = self._get_sellable_quantity(code)
            if not pos or pos.quantity < quantity:
                return OrderResult(success=False, message="持仓不足")
            if sellable < quantity:
                return OrderResult(success=False, message="T+1 限制：当日买入的股份需下一个交易日才能卖出")

        # 创建订单
        self._order_counter += 1
        order = Order(
            order_id=f"SIM{self._order_counter:08d}",
            code=code,
            side=side,
            price=price,
            quantity=quantity,
            order_type=order_type,
            status=OrderStatus.SUBMITTED,
            create_time=datetime.now()
        )

        with self._lock:
            self._orders[order.order_id] = order

        self._log_info(f"委托已提交: {order.order_id} {code} {'买入' if side == OrderSide.BUY else '卖出'} {quantity}股 @ {price:.2f}")

        if self.on_order_update:
            self.on_order_update(order)

        return OrderResult(success=True, order_id=order.order_id, order=order)

    def cancel_order(self, order_id: str) -> bool:
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                return False
            if order.status != OrderStatus.SUBMITTED:
                return False

            order.status = OrderStatus.CANCELLED
            order.update_time = datetime.now()

        self._log_info(f"订单已撤销: {order_id}")
        if self.on_order_update:
            self.on_order_update(order)
        return True

    def modify_order(self, order_id: str, price: float = None, quantity: int = None) -> bool:
        # 模拟交易不支持改单，需要撤单后重新下单
        return False

    def query_account(self) -> Optional[AccountInfo]:
        market_value = sum(pos.market_value for pos in self._positions.values())
        total_value = self._cash + market_value
        profit = total_value - self._initial_capital

        self._account = AccountInfo(
            account_id="SIM001",
            broker="模拟交易",
            cash=self._cash,
            frozen=0,
            market_value=market_value,
            total_value=total_value,
            profit=profit,
            profit_pct=profit / self._initial_capital * 100 if self._initial_capital > 0 else 0
        )

        if self.on_account_update:
            self.on_account_update(self._account)

        return self._account

    def query_positions(self) -> List[Position]:
        return list(self._positions.values())

    def query_orders(self, status: OrderStatus = None) -> List[Order]:
        with self._lock:
            if status:
                return [o for o in self._orders.values() if o.status == status]
            return list(self._orders.values())

    def query_trades(self) -> List[Trade]:
        return self._trades.copy()

    def get_sellable_quantity(self, code: str) -> int:
        return self._get_sellable_quantity(code)

    def _order_process_loop(self):
        """订单处理循环"""
        while self._running:
            self._process_pending_orders()
            time.sleep(0.1)

    def _process_pending_orders(self):
        """处理待成交订单"""
        with self._lock:
            pending_orders = [o for o in self._orders.values() if o.status == OrderStatus.SUBMITTED]

        for order in pending_orders:
            market_price = self._market_prices.get(order.code, order.price)

            # 判断是否可以成交
            can_fill = False
            fill_price = market_price

            if order.order_type == OrderType.MARKET:
                can_fill = True
            elif order.side == OrderSide.BUY:
                if market_price <= order.price:
                    can_fill = True
                    fill_price = min(market_price * (1 + self._slippage), order.price)
            else:
                if market_price >= order.price:
                    can_fill = True
                    fill_price = max(market_price * (1 - self._slippage), order.price)

            if can_fill:
                self._fill_order(order, fill_price)

    def _fill_order(self, order: Order, fill_price: float):
        """成交订单"""
        # 计算手续费
        commission = fill_price * order.quantity * self._commission_rate
        if order.side == OrderSide.SELL:
            commission += fill_price * order.quantity * 0.001  # 印花税

        # 创建成交记录
        self._trade_counter += 1
        trade = Trade(
            trade_id=f"T{self._trade_counter:08d}",
            order_id=order.order_id,
            code=order.code,
            side=order.side,
            price=fill_price,
            quantity=order.quantity,
            commission=commission,
            trade_time=datetime.now()
        )

        # 更新订单状态
        with self._lock:
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_price = fill_price
            order.update_time = datetime.now()

            # 更新资金和持仓
            if order.side == OrderSide.BUY:
                self._cash -= fill_price * order.quantity + commission
                if order.code in self._positions:
                    pos = self._positions[order.code]
                    total_cost = pos.avg_cost * pos.quantity + fill_price * order.quantity
                    pos.quantity += order.quantity
                    pos.avg_cost = total_cost / pos.quantity
                    pos.current_price = fill_price
                else:
                    self._positions[order.code] = Position(
                        code=order.code,
                        quantity=order.quantity,
                        avg_cost=fill_price,
                        current_price=fill_price
                    )
                self._record_buy_lot(order.code, order.quantity, datetime.now().date())
            else:
                self._cash += fill_price * order.quantity - commission
                if order.code in self._positions:
                    self._positions[order.code].quantity -= order.quantity
                    if self._positions[order.code].quantity <= 0:
                        del self._positions[order.code]
                self._consume_sell_quantity(order.code, order.quantity)

            self._trades.append(trade)

        self._log_info(f"订单成交: {order.order_id} {order.code} {'买入' if order.side == OrderSide.BUY else '卖出'} {order.quantity}股 @ {fill_price:.2f}")

        if self.on_order_update:
            self.on_order_update(order)
        if self.on_trade_update:
            self.on_trade_update(trade)

    def _record_buy_lot(self, code: str, quantity: int, trade_date):
        lots = self._position_lots.setdefault(code, [])
        lots.append({"date": trade_date, "qty": quantity})

    def _get_sellable_quantity(self, code: str) -> int:
        today = datetime.now().date()
        lots = self._position_lots.get(code, [])
        return sum(lot["qty"] for lot in lots if lot["date"] < today)

    def _consume_sell_quantity(self, code: str, quantity: int):
        if quantity <= 0:
            return
        today = datetime.now().date()
        lots = self._position_lots.get(code, [])
        idx = 0
        while quantity > 0 and idx < len(lots):
            lot = lots[idx]
            if lot["date"] >= today:
                idx += 1
                continue
            take = min(lot["qty"], quantity)
            lot["qty"] -= take
            quantity -= take
            if lot["qty"] <= 0:
                lots.pop(idx)
            else:
                idx += 1
        if quantity > 0:
            # 出现异常时清理
            lots[:] = [lot for lot in lots if lot["qty"] > 0]


class BrokerFactory:
    """券商工厂类"""

    _brokers: Dict[BrokerType, type] = {
        BrokerType.SIMULATED: SimulatedBroker,
    }

    @classmethod
    def register(cls, broker_type: BrokerType, broker_class: type):
        """注册券商实现"""
        cls._brokers[broker_type] = broker_class

    @classmethod
    def create(cls, config: BrokerConfig) -> Optional[BrokerTrader]:
        """创建券商实例"""
        broker_class = cls._brokers.get(config.broker_type)
        if broker_class:
            return broker_class(config)
        return None

    @classmethod
    def get_supported_brokers(cls) -> List[BrokerType]:
        """获取支持的券商列表"""
        return list(cls._brokers.keys())


class TradingEngine:
    """交易引擎"""

    def __init__(self):
        self.logger = get_log_manager()
        self._broker: Optional[BrokerTrader] = None
        self._is_trading = False

        # 回调
        self.on_order: Optional[Callable[[Order], None]] = None
        self.on_trade: Optional[Callable[[Trade], None]] = None
        self.on_position: Optional[Callable[[Position], None]] = None
        self.on_account: Optional[Callable[[AccountInfo], None]] = None

    def set_broker(self, broker: BrokerTrader):
        """设置券商接口"""
        self._broker = broker

        # 设置回调
        broker.on_order_update = self._on_order_update
        broker.on_trade_update = self._on_trade_update
        broker.on_position_update = self._on_position_update
        broker.on_account_update = self._on_account_update

    def connect(self) -> bool:
        """连接"""
        if not self._broker:
            return False
        return self._broker.connect()

    def login(self) -> bool:
        """登录"""
        if not self._broker:
            return False
        return self._broker.login()

    def disconnect(self):
        """断开"""
        if self._broker:
            self._broker.disconnect()

    def start_trading(self):
        """开始交易"""
        self._is_trading = True
        self.logger.info("交易已启动", LogCategory.TRADE)

    def stop_trading(self):
        """停止交易"""
        self._is_trading = False
        self.logger.info("交易已停止", LogCategory.TRADE)

    @property
    def is_trading(self) -> bool:
        return self._is_trading

    def buy(self, code: str, price: float, quantity: int,
            order_type: OrderType = OrderType.LIMIT) -> OrderResult:
        """买入"""
        if not self._is_trading:
            return OrderResult(success=False, message="交易未启动")
        if not self._broker or not self._broker.is_logged_in:
            return OrderResult(success=False, message="未登录")
        return self._broker.send_order(code, OrderSide.BUY, price, quantity, order_type)

    def sell(self, code: str, price: float, quantity: int,
             order_type: OrderType = OrderType.LIMIT) -> OrderResult:
        """卖出"""
        if not self._is_trading:
            return OrderResult(success=False, message="交易未启动")
        if not self._broker or not self._broker.is_logged_in:
            return OrderResult(success=False, message="未登录")
        return self._broker.send_order(code, OrderSide.SELL, price, quantity, order_type)

    def cancel(self, order_id: str) -> bool:
        """撤单"""
        if not self._broker:
            return False
        return self._broker.cancel_order(order_id)

    def get_account(self) -> Optional[AccountInfo]:
        """获取账户"""
        if not self._broker:
            return None
        return self._broker.query_account()

    def get_positions(self) -> List[Position]:
        """获取持仓"""
        if not self._broker:
            return []
        return self._broker.query_positions()

    def get_orders(self, status: OrderStatus = None) -> List[Order]:
        """获取订单"""
        if not self._broker:
            return []
        return self._broker.query_orders(status)

    def get_trades(self) -> List[Trade]:
        """获取成交"""
        if not self._broker:
            return []
        return self._broker.query_trades()

    def get_sellable_quantity(self, code: str) -> int:
        """查询可卖数量（适配 T+1）"""
        if not self._broker:
            return 0
        return self._broker.get_sellable_quantity(code)

    def _on_order_update(self, order: Order):
        if self.on_order:
            self.on_order(order)

    def _on_trade_update(self, trade: Trade):
        if self.on_trade:
            self.on_trade(trade)

    def _on_position_update(self, position: Position):
        if self.on_position:
            self.on_position(position)

    def _on_account_update(self, account: AccountInfo):
        if self.on_account:
            self.on_account(account)


# 注册 REST 券商实现
try:  # pragma: no cover - 动态导入
    from . import huatai  # noqa: F401
    from . import zhongxin  # noqa: F401
    from . import guotaijunan  # noqa: F401
    from . import haitong  # noqa: F401
    from . import guangfa  # noqa: F401
except Exception:
    pass
    def get_sellable_quantity(self, code: str) -> int:
        """可卖出数量，默认返回持仓数量（T+0）。"""
        position = self._positions.get(code)
        return position.quantity if position else 0
