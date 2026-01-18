"""
实时策略运行控制器
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Callable, Dict, List, Optional, Tuple

from core.assistant.ai_helper import AIHelper
from core.logger import get_log_manager, LogCategory
from core.realtime.quote_manager import QuoteManager, QuoteSnapshot
from core.realtime.data_feed import AkShareDataFeed, CSVDataFeed, SimulatedDataFeed
from core.realtime.multisource_feed import MultiSourceHTTPFeed
from core.strategy.base import Bar, Order, OrderSide, OrderStatus, OrderType, Trade, Position
from core.strategy.strategy_manager import StrategyManager
from core.trader.broker import (
    BrokerConfig,
    BrokerFactory,
    BrokerType,
    SimulatedBroker,
    TradingEngine,
)
from core.risk.risk_manager import RiskConfig, RiskManager, RiskAlert
from config.settings import config_manager


class StrategyRunner:
    """简单的实时策略运行器"""

    @staticmethod
    def _runtime_base_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent

    def _resolve_runtime_path(self, value: Optional[str], fallback: str) -> Path:
        base_dir = self._runtime_base_dir()
        if value:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = base_dir / candidate
        else:
            candidate = base_dir / fallback
        return candidate

    def __init__(self, config=None):
        self.logger = get_log_manager()
        self.config = config or config_manager
        self.strategy_manager = StrategyManager()
        self.quote_manager = QuoteManager()
        self.trading_engine = TradingEngine()
        self.trading_engine.on_order = self._on_broker_order
        self.trading_engine.on_trade = self._on_broker_trade
        self.trading_engine.on_account = self._on_account_update
        self.trading_engine.on_position = self._on_position_update

        self.strategy = None
        self._strategy_instances: Dict[str, object] = {}
        self._order_strategy_map: Dict[str, object] = {}
        self.ai_helper = AIHelper(self.config)
        self.risk_manager: Optional[RiskManager] = None
        self._data_feed = None
        self._codes: List[str] = []
        self._running = False
        self._order_map: Dict[str, Order] = {}
        self._snapshot_callback = None
        self.log_callback: Optional[Callable[[str], None]] = None
        self.signal_callback: Optional[Callable[[Order], None]] = None
        self._latest_prices: Dict[str, float] = {}
        self._last_account = None
        self._positions: Dict[str, Position] = {}
        self._risk_pause_reason: Optional[str] = None

        self._init_risk_manager(reset_state=True)
        self.risk_alert_callback: Optional[Callable[[str], None]] = None

    def set_log_callback(self, callback: Callable[[str], None]):
        self.log_callback = callback

    def set_signal_callback(self, callback: Callable[[Order], None]):
        """半自动模式下，提供订单信号给UI"""
        self.signal_callback = callback

    def set_alert_callback(self, callback: Callable[[str], None]):
        """外部接收风险告警时调用"""
        self.risk_alert_callback = callback

    # ------------------------------------------------------------------ control
    def start(self, strategy_name: str, codes: List[str], per_stock_strategies: Optional[Dict[str, str]] = None):
        if self._running:
            raise RuntimeError("策略运行中，请先停止")

        assignments: Dict[str, str] = {}
        if per_stock_strategies:
            assignments = {
                code: name
                for code, name in per_stock_strategies.items()
                if code and name
            }
        else:
            assignments = {code: strategy_name for code in codes if code}
        if not assignments:
            raise ValueError("请至少输入一个标的代码")
        codes = list(assignments.keys())

        self._init_risk_manager(reset_state=True)
        self._order_map.clear()
        self._order_strategy_map.clear()
        self._latest_prices.clear()
        self._positions.clear()
        self._last_account = None
        self._risk_pause_reason = None
        self._strategy_instances.clear()

        if per_stock_strategies:
            desc = ", ".join(f"{code}:{name}" for code, name in assignments.items())
            self._log(f"准备启动多策略运行，标的: {desc}")
        else:
            self._log(f"准备启动策略 {strategy_name}，标的: {', '.join(codes)}")

        initial_capital = self.config.get("initial_capital", 1000000.0)
        for code, name in assignments.items():
            strategy_instance = self.strategy_manager.create_strategy_instance(name)
            if not strategy_instance:
                raise ValueError(f"无法加载策略 {name}")
            strategy_instance.set_capital(initial_capital)
            strategy_instance.set_callbacks(
                order_callback=lambda order, s=strategy_instance: self._on_strategy_order(order, s),
                trade_callback=self._on_strategy_trade,
                log_callback=lambda msg, c=code: self._log(f"[{c}] {msg}"),
            )
            self._strategy_instances[code] = strategy_instance
            if self.strategy is None:
                self.strategy = strategy_instance

        broker = self._create_broker()
        if broker is None:
            raise RuntimeError("无法创建券商接口，请检查设置")
        self.trading_engine.set_broker(broker)

        if not (self.trading_engine.connect() and self.trading_engine.login()):
            raise RuntimeError("连接或登录券商失败")
        self.trading_engine.start_trading()
        self._refresh_positions()
        account = self.trading_engine.get_account()
        if account:
            self._update_account_state(account)

        self._init_data_feed()
        self._codes = codes
        self._register_quote_callbacks()
        self.quote_manager.subscribe(codes)
        if not self.quote_manager.is_connected:
            self.quote_manager.connect()
        if not self.quote_manager.is_running:
            self.quote_manager.start()

        self._running = True
        self._log("策略运行已启动")

    def stop(self):
        if not self._running:
            return
        self._log("正在停止策略运行...")
        self._running = False
        if self.risk_manager:
            self.risk_manager.is_trading_allowed = True
        self._risk_pause_reason = None
        self._unregister_quote_callbacks()
        if self._codes:
            try:
                self.quote_manager.unsubscribe(self._codes)
            except Exception:  # pragma: no cover - 防御
                pass
        if self._data_feed:
            try:
                self._data_feed.stop()
            except Exception:
                pass
            self._data_feed = None
        self._codes = []
        self.trading_engine.stop_trading()
        self.trading_engine.disconnect()
        self.strategy = None
        self._strategy_instances.clear()
        self._order_strategy_map.clear()
        self._order_map.clear()
        self._log("策略运行已停止")

    @property
    def is_running(self) -> bool:
        return self._running

    def reload_config(self):
        self.ai_helper.reload_config(self.config)
        self._init_risk_manager(reset_state=not self._running)

    # ----------------------------------------------------------------- internals
    def _create_broker(self):
        cfg = self.config.get_all()
        broker_type_value = cfg.get("broker_type", "simulated")
        if broker_type_value == "simulated":
            config = BrokerConfig(
                broker_type=BrokerType.SIMULATED,
                extra={
                    "initial_capital": cfg.get("initial_capital", 1000000.0),
                    "commission_rate": cfg.get("commission_rate", 0.0003),
                    "slippage": cfg.get("slippage", 0.001),
                },
            )
            return SimulatedBroker(config)

        account = cfg.get("broker_account", "").strip()
        password = cfg.get("broker_password", "").strip()
        api_url = cfg.get("broker_api_url", "").strip()
        if not account or not password or not api_url:
            raise ValueError("请在设置中填写券商账号/密码/API地址")

        try:
            broker_type = BrokerType(broker_type_value)
        except ValueError:
            raise ValueError(f"不支持的券商类型: {broker_type_value}") from None

        extra = {
            "base_url": api_url,
            "poll_interval": cfg.get("api_poll_interval", 3),
            "timeout": cfg.get("api_timeout", 8),
            "api_key": cfg.get("broker_api_key", ""),
            "api_secret": cfg.get("broker_api_secret", ""),
            "verify_ssl": cfg.get("broker_api_verify_ssl", True),
        }
        client_cert = cfg.get("broker_api_client_cert")
        if client_cert:
            extra["client_cert"] = client_cert
        config = BrokerConfig(
            broker_type=broker_type,
            account=account,
            password=password,
            extra=extra,
        )
        broker = BrokerFactory.create(config)
        if broker is None:
            raise ValueError(f"券商 {broker_type_value} 暂无可用实现")
        return broker

    def _init_data_feed(self):
        if self._data_feed:
            self._data_feed.stop()
            self._data_feed = None
        source = (self.config.get("data_source", "akshare") or "akshare").lower()
        if source == "akshare":
            self._data_feed = AkShareDataFeed()
        elif source == "csv":
            csv_path = self.config.get("csv_data_path", "").strip()
            if not csv_path:
                raise ValueError("CSV 数据源需要在设置中填写 csv_data_path")
            resolved_csv = self._resolve_runtime_path(csv_path, "data/quotes.csv")
            self._data_feed = CSVDataFeed(
                file_path=str(resolved_csv),
                loop=self.config.get("csv_loop", False),
                speed=self.config.get("csv_speed", 1.0),
            )
        elif source == "tushare":
            self._data_feed = MultiSourceHTTPFeed(
                tushare_token=self.config.get("tushare_token", ""),
                interval=self.config.get("http_data_interval", 2.0),
            )
        elif source in ("multisource", "china_online"):
            self._data_feed = MultiSourceHTTPFeed(
                tushare_token=self.config.get("tushare_token", ""),
                interval=self.config.get("http_data_interval", 2.0),
            )
        else:
            self._data_feed = SimulatedDataFeed(
                interval=self.config.get("sim_interval", 1.0),
                volatility=self.config.get("sim_volatility", 0.01),
            )
        self.quote_manager.set_data_feed(self._data_feed)
        if not self._data_feed.connect():
            raise RuntimeError("数据源连接失败")

    def _register_quote_callbacks(self):
        if self._snapshot_callback is None:
            self._snapshot_callback = self._on_snapshot
            self.quote_manager.add_snapshot_callback(self._snapshot_callback)

    def _unregister_quote_callbacks(self):
        if self._snapshot_callback:
            self.quote_manager.remove_callback(self._snapshot_callback)
            self._snapshot_callback = None

    # ----------------------------------------------------------------- callbacks
    def _on_snapshot(self, snapshot: QuoteSnapshot):
        if not self._running or (not self._strategy_instances and self.strategy is None):
            return
        price = snapshot.price or snapshot.close or snapshot.open or 0.0
        self._latest_prices[snapshot.code] = price
        if self.risk_manager and snapshot.code in self._positions:
            position = self._positions[snapshot.code]
            position.current_price = price or position.current_price
            self.risk_manager.check_position(position)
        bar = self._snapshot_to_bar(snapshot)
        target_strategy = self._strategy_instances.get(snapshot.code) or self.strategy
        if target_strategy:
            target_strategy._on_bar(snapshot.code, bar)

    def _snapshot_to_bar(self, snapshot: QuoteSnapshot) -> Bar:
        price = snapshot.price or snapshot.open or snapshot.close or 0.0
        return Bar(
            datetime=snapshot.timestamp or datetime.now(),
            open=snapshot.open or price,
            high=snapshot.high or price,
            low=snapshot.low or price,
            close=price,
            volume=snapshot.volume or 0.0,
            amount=snapshot.amount or 0.0,
        )

    def _on_strategy_order(self, order: Order, strategy_instance=None):
        if not self.trading_engine.is_trading:
            self._log("交易尚未启动，无法执行下单")
            return
        if order.quantity <= 0:
            return
        owner_strategy = strategy_instance or self._strategy_instances.get(order.code)
        allowed, reason = self._check_risk_before_order(order)
        if not allowed:
            order.status = OrderStatus.REJECTED
            self._log(f"风控拒绝委托: {reason or '未知原因'}")
            return
        auto_execute = True
        try:
            auto_execute = self.config.get("strategy_auto_execute", True)
        except Exception:
            auto_execute = True
        if not auto_execute:
            order.status = OrderStatus.PENDING
            message = f"策略信号: {order.code} {order.side.value} {order.quantity}@{order.price:.2f}"
            self._log(message)
            if self.signal_callback:
                self.signal_callback(order)
            return
        if order.side == OrderSide.BUY:
            result = self.trading_engine.buy(order.code, order.price, order.quantity, order.order_type)
        else:
            result = self.trading_engine.sell(order.code, order.price, order.quantity, order.order_type)

        if result.success:
            broker_order = result.order
            if broker_order:
                order.order_id = broker_order.order_id
                self._order_map[broker_order.order_id] = order
                if owner_strategy:
                    self._order_strategy_map[broker_order.order_id] = owner_strategy
            self._log(f"策略下单成功: {order.code} {order.side.value} {order.quantity}")
        else:
            order.status = OrderStatus.REJECTED
            self._log(f"策略下单失败: {result.message}")

    def _on_strategy_trade(self, trade: Trade):
        self._log(f"策略成交[{trade.code}]: {trade.side.value} {trade.quantity}@{trade.price:.2f}")
        if self.risk_manager:
            self.risk_manager.on_trade_completed()
        self._refresh_positions()
        account = self.trading_engine.get_account()
        if account:
            self._update_account_state(account)

    def _on_broker_order(self, broker_order: Order):
        strategy_order = self._order_map.get(broker_order.order_id)
        if strategy_order:
            strategy_order.status = broker_order.status
            strategy_order.filled_quantity = broker_order.filled_quantity
            strategy_order.filled_price = broker_order.filled_price
        self._log(f"订单更新: {broker_order.order_id} 状态 {broker_order.status.value}")

    def _on_broker_trade(self, trade: Trade):
        strategy_order = self._order_map.get(trade.order_id)
        strategy_instance = self._order_strategy_map.get(trade.order_id)
        if strategy_instance is None:
            strategy_instance = self._strategy_instances.get(trade.code) or self.strategy
        if strategy_instance and strategy_order:
            strategy_instance._on_order_filled(strategy_order, trade)
            self._order_strategy_map.pop(trade.order_id, None)
        self._log(f"成交回报: {trade.code} {trade.side.value} 数量{trade.quantity} 价格{trade.price:.2f}")
        self._refresh_positions()
        account = self.trading_engine.get_account()
        if account:
            self._update_account_state(account)

    # ----------------------------------------------------------------- utils
    def _log(self, message: str):
        self.logger.info(f"[StrategyRunner] {message}", LogCategory.STRATEGY)
        if self.log_callback:
            self.log_callback(message)

    # ---------------------------------------------------------------- risk helpers
    def _refresh_positions(self):
        if not self.trading_engine:
            self._positions.clear()
            return
        try:
            current_positions = self.trading_engine.get_positions() or []
        except Exception:
            current_positions = []
        self._positions = {pos.code: pos for pos in current_positions}

    def _update_account_state(self, account):
        if account is None:
            return
        self._last_account = account
        if not self.risk_manager:
            return
        total_value = getattr(account, "total_value", 0.0)
        cash = getattr(account, "cash", 0.0) or 0.0
        if not total_value or total_value <= 0:
            total_value = cash + sum(pos.market_value for pos in self._positions.values())
        self.risk_manager.update_peak_value(total_value)
        self.risk_manager.check_drawdown(total_value)

    def _on_account_update(self, account):
        self._update_account_state(account)

    def _on_position_update(self, position: Position):
        if position.quantity <= 0:
            self._positions.pop(position.code, None)
        else:
            latest = self._latest_prices.get(position.code)
            if latest:
                position.current_price = latest
            self._positions[position.code] = position
        if self.risk_manager and position.quantity > 0:
            self.risk_manager.check_position(position)

    def _on_risk_alert(self, alert: RiskAlert):
        message = f"风控提醒[{alert.level.value}]{alert.message}"
        if alert.code:
            message += f" ({alert.code})"
        self._log(message)
        if self.risk_alert_callback:
            self.risk_alert_callback(message)

    def _handle_risk_stop(self, reason: str):
        self._risk_pause_reason = reason
        self._log(f"风控触发停止: {reason}")
        self.stop()

    def _check_risk_before_order(self, order: Order) -> Tuple[bool, str]:
        if not self.risk_manager:
            return True, ""
        account = self._last_account or self.trading_engine.get_account()
        if not account:
            return True, ""
        # refresh local cache lazily when broker没有推送
        if not self._positions:
            self._refresh_positions()
        positions = dict(self._positions)
        for code, pos in positions.items():
            latest_price = self._latest_prices.get(code)
            if latest_price:
                pos.current_price = latest_price
        total_value = getattr(account, "total_value", 0.0)
        cash = getattr(account, "cash", 0.0) or 0.0
        if not total_value or total_value <= 0:
            total_value = cash + sum(pos.market_value for pos in positions.values())
        if total_value <= 0:
            total_value = max(order.price * max(order.quantity, 1), 1.0)
        current_price = self._latest_prices.get(order.code, 0.0) or order.price
        if order.side == OrderSide.SELL:
            sellable_qty = self.trading_engine.get_sellable_quantity(order.code)
            if sellable_qty < order.quantity:
                return False, "T+1 限制：当日买入的仓位需下一个交易日才能卖出"
        return self.risk_manager.check_order(order, positions, cash, total_value, current_price)

    def _init_risk_manager(self, reset_state: bool = False):
        config = self._build_risk_config()
        raw_journal_path = None
        try:
            raw_journal_path = self.config.get("risk_journal_path")
        except Exception:
            raw_journal_path = None
        journal_path = None
        if raw_journal_path:
            journal_path = self._resolve_runtime_path(raw_journal_path, "logs/risk_journal.csv")

        if self.risk_manager is None:
            self.risk_manager = RiskManager(config, journal_path=journal_path)
            self.risk_manager.on_alert = self._on_risk_alert
            self.risk_manager.on_stop_trading = self._handle_risk_stop
        else:
            self.risk_manager.config = config
            self.risk_manager.journal_path = Path(journal_path) if journal_path else None
        if reset_state and self.risk_manager:
            self.risk_manager.clear_alerts()
            self.risk_manager.reset_daily()
            self.risk_manager.is_trading_allowed = True
            self.risk_manager.peak_value = 0.0

    def _build_risk_config(self) -> RiskConfig:
        cfg = {}
        if self.config:
            cfg = getattr(self.config, "get_all", lambda: {})()
        base = RiskConfig()

        def _num(key: str, default):
            value = cfg.get(key, default)
            try:
                if isinstance(default, int):
                    return int(value)
                return float(value)
            except (TypeError, ValueError):
                return default

        return RiskConfig(
            max_position_pct=_num("max_position_pct", base.max_position_pct),
            max_total_position_pct=_num("max_total_position_pct", base.max_total_position_pct),
            stop_loss_pct=_num("stop_loss_pct", base.stop_loss_pct),
            take_profit_pct=_num("take_profit_pct", base.take_profit_pct),
            trailing_stop_pct=_num("trailing_stop_pct", base.trailing_stop_pct),
            max_drawdown_pct=_num("max_drawdown_pct", base.max_drawdown_pct),
            max_daily_trades=int(cfg.get("max_daily_trades", base.max_daily_trades)),
            max_daily_loss=_num("max_daily_loss", base.max_daily_loss),
            min_trade_interval=int(cfg.get("min_trade_interval", base.min_trade_interval)),
            max_price_deviation=_num("max_price_deviation", base.max_price_deviation),
        )

    def get_risk_summary(self) -> Optional[Dict[str, float]]:
        """返回当前风险概览，供 UI 展示"""
        if not self.risk_manager:
            return None
        positions = dict(self._positions)
        cash = 0.0
        total_value = 0.0
        if self._last_account:
            cash = getattr(self._last_account, "cash", 0.0) or 0.0
            total_value = getattr(self._last_account, "total_value", 0.0) or 0.0
        if total_value <= 0:
            total_value = cash + sum(pos.market_value for pos in positions.values())
        summary = self.risk_manager.get_risk_summary(positions, total_value)
        summary["is_running"] = self._running
        summary["risk_paused_reason"] = self._risk_pause_reason or ""
        summary["alert_count"] = len(self.risk_manager.alerts)
        return summary

    def reset_risk_state(self):
        """手动清空风控统计"""
        if not self.risk_manager:
            return
        self.risk_manager.clear_alerts()
        self.risk_manager.reset_daily()
        self.risk_manager.is_trading_allowed = True
        self._risk_pause_reason = None
        self._log("风控统计已被手动重置")

    def get_risk_journal_file(self) -> Optional[Path]:
        if self.risk_manager and self.risk_manager.journal_path:
            return self.risk_manager.journal_path
        return None
