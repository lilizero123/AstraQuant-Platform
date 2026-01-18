"""
交易组件
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QComboBox, QMessageBox,
    QRadioButton, QButtonGroup, QTextEdit, QScrollArea,
    QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from typing import Optional, Dict, List
from datetime import datetime
import os

from core.trader.broker import (
    BrokerFactory, BrokerConfig, BrokerType, TradingEngine,
    SimulatedBroker, AccountInfo
)
from core.strategy.base import Order, Trade, OrderSide, OrderStatus, Position
from core.assistant.ai_helper import AIHelper
from core.strategy.strategy_manager import StrategyManager
from core.runtime.strategy_runner import StrategyRunner
from config.settings import config_manager


class TradeWidget(QWidget):
    """交易组件"""

    account_updated = pyqtSignal(dict)
    positions_updated = pyqtSignal(list)

    BROKER_OPTIONS = [
        ("模拟交易", "simulated"),
        ("华泰证券", "huatai"),
        ("中信证券", "zhongxin"),
        ("国泰君安", "guotai"),
        ("海通证券", "haitong"),
        ("广发证券", "guangfa"),
    ]
    BROKER_TEXT_TO_VALUE = {text: value for text, value in BROKER_OPTIONS}
    BROKER_VALUE_TO_TEXT = {value: text for text, value in BROKER_OPTIONS}

    def __init__(self):
        super().__init__()

        # 交易引擎
        self._engine = TradingEngine()
        self._broker = None
        self._last_account: Optional[AccountInfo] = None

        self.ai_helper = AIHelper()
        self.config = config_manager
        self.strategy_runner = StrategyRunner()
        self.strategy_runner.set_log_callback(self._append_strategy_log)
        self.strategy_runner.set_alert_callback(self._handle_risk_alert)
        self.strategy_runner.set_signal_callback(self._handle_strategy_signal)
        self.strategy_manager = StrategyManager()
        self._pending_stock_strategy = ""
        self._active_stock_code = ""
        self._strategy_change_callback = None
        self._strategy_assignment_provider = None
        self._loading_strategy = False
        self._orders_by_code: Dict[str, Dict[str, dict]] = {}
        self._trades_by_code: Dict[str, List[dict]] = {}
        self._current_display_order_keys: List[str] = []

        self.init_ui()
        self._setup_callbacks()

        # 定时刷新账户信息与风险信息
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._on_refresh_timer)
        self._refresh_timer.start(2000)  # 每2秒刷新

    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)

        # 左侧 - 下单面板（带滚动）
        left_panel = QWidget()
        left_main_layout = QVBoxLayout(left_panel)
        left_main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3c3c3c;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4c4c4c;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # 滚动区域内的内容容器
        scroll_content = QWidget()
        left_layout = QVBoxLayout(scroll_content)
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # 连接状态
        status_group = QGroupBox("连接状态")
        status_layout = QFormLayout(status_group)

        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addRow("状态:", self.status_label)

        self.broker_combo = QComboBox()
        for text, _ in self.BROKER_OPTIONS:
            self.broker_combo.addItem(text)
        status_layout.addRow("券商:", self.broker_combo)

        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("连接")
        self.btn_connect.clicked.connect(self.connect_broker)
        self.btn_disconnect = QPushButton("断开")
        self.btn_disconnect.clicked.connect(self.disconnect_broker)
        self.btn_disconnect.setEnabled(False)
        btn_layout.addWidget(self.btn_connect)
        btn_layout.addWidget(self.btn_disconnect)
        status_layout.addRow("", btn_layout)

        # 账户信息
        self.cash_label = QLabel("--")
        status_layout.addRow("可用资金:", self.cash_label)
        self.total_label = QLabel("--")
        status_layout.addRow("总资产:", self.total_label)

        left_layout.addWidget(status_group)

        # 下单面板
        order_group = QGroupBox("委托下单")
        order_layout = QFormLayout(order_group)

        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("输入股票代码，如 000001")
        order_layout.addRow("股票代码:", self.stock_input)

        self.stock_name = QLabel("--")
        order_layout.addRow("股票名称:", self.stock_name)

        self.current_price = QLabel("--")
        order_layout.addRow("当前价格:", self.current_price)

        # 买卖方向
        direction_layout = QHBoxLayout()
        self.btn_group = QButtonGroup()
        self.radio_buy = QRadioButton("买入")
        self.radio_buy.setChecked(True)
        self.radio_buy.setStyleSheet("color: red;")
        self.radio_sell = QRadioButton("卖出")
        self.radio_sell.setStyleSheet("color: green;")
        self.btn_group.addButton(self.radio_buy)
        self.btn_group.addButton(self.radio_sell)
        direction_layout.addWidget(self.radio_buy)
        direction_layout.addWidget(self.radio_sell)
        order_layout.addRow("方向:", direction_layout)

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 10000)
        self.price_input.setDecimals(2)
        self.price_input.setValue(10.00)
        order_layout.addRow("委托价格:", self.price_input)

        self.qty_input = QSpinBox()
        self.qty_input.setRange(100, 1000000)
        self.qty_input.setSingleStep(100)
        self.qty_input.setValue(100)
        order_layout.addRow("委托数量:", self.qty_input)

        self.amount_label = QLabel("¥1,000.00")
        order_layout.addRow("委托金额:", self.amount_label)

        # 更新金额
        self.price_input.valueChanged.connect(self.update_amount)
        self.qty_input.valueChanged.connect(self.update_amount)

        btn_order = QPushButton("下单")
        btn_order.setMinimumHeight(40)
        btn_order.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        btn_order.clicked.connect(self.place_order)
        order_layout.addRow("", btn_order)

        left_layout.addWidget(order_group)

        # 快捷操作
        quick_group = QGroupBox("快捷操作")
        quick_layout = QVBoxLayout(quick_group)

        btn_layout1 = QHBoxLayout()
        btn_buy_1 = QPushButton("买1手")
        btn_buy_1.clicked.connect(lambda: self.quick_order("buy", 100))
        btn_buy_5 = QPushButton("买5手")
        btn_buy_5.clicked.connect(lambda: self.quick_order("buy", 500))
        btn_buy_10 = QPushButton("买10手")
        btn_buy_10.clicked.connect(lambda: self.quick_order("buy", 1000))
        btn_layout1.addWidget(btn_buy_1)
        btn_layout1.addWidget(btn_buy_5)
        btn_layout1.addWidget(btn_buy_10)
        quick_layout.addLayout(btn_layout1)

        btn_layout2 = QHBoxLayout()
        btn_sell_1 = QPushButton("卖1手")
        btn_sell_1.clicked.connect(lambda: self.quick_order("sell", 100))
        btn_sell_half = QPushButton("卖半仓")
        btn_sell_half.clicked.connect(lambda: self.quick_order("sell", -1))
        btn_sell_all = QPushButton("清仓")
        btn_sell_all.clicked.connect(lambda: self.quick_order("sell", -2))
        btn_layout2.addWidget(btn_sell_1)
        btn_layout2.addWidget(btn_sell_half)
        btn_layout2.addWidget(btn_sell_all)
        quick_layout.addLayout(btn_layout2)

        left_layout.addWidget(quick_group)

        ai_group = QGroupBox("AI风控提示")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(8)

        self.ai_advice_box = QTextEdit()
        self.ai_advice_box.setReadOnly(True)
        self.ai_advice_box.setPlaceholderText("点击下方按钮获取当前委托的AI评估")
        self.ai_advice_box.setFixedHeight(100)
        self.ai_advice_box.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        ai_layout.addWidget(self.ai_advice_box)

        btn_ai_advise = QPushButton("AI下单建议")
        btn_ai_advise.setMinimumHeight(32)
        btn_ai_advise.clicked.connect(self.show_ai_trade_advice)
        ai_layout.addWidget(btn_ai_advise)
        left_layout.addWidget(ai_group)

        auto_group = QGroupBox("自动策略")
        auto_layout = QFormLayout(auto_group)
        auto_layout.setLabelAlignment(Qt.AlignRight)
        auto_layout.setSpacing(8)

        self.auto_strategy_combo = QComboBox()
        self.auto_strategy_combo.currentTextChanged.connect(self._on_strategy_combo_changed)

        self.auto_codes_input = QLineEdit()
        self.auto_codes_input.setPlaceholderText("自动同步自选股（代码:策略）")
        self.auto_codes_input.setReadOnly(True)

        btn_auto_box = QHBoxLayout()
        self.btn_auto_start = QPushButton("启动策略")
        self.btn_auto_start.setMinimumHeight(32)
        self.btn_auto_stop = QPushButton("停止策略")
        self.btn_auto_stop.setMinimumHeight(32)
        self.btn_auto_stop.setEnabled(False)
        self.btn_auto_start.clicked.connect(self.start_auto_strategy)
        self.btn_auto_stop.clicked.connect(self.stop_auto_strategy)
        btn_auto_box.addWidget(self.btn_auto_start)
        btn_auto_box.addWidget(self.btn_auto_stop)

        self.auto_log = QTextEdit()
        self.auto_log.setReadOnly(True)
        self.auto_log.setPlaceholderText("策略运行日志...")
        self.auto_log.setFixedHeight(100)
        self.auto_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)

        self._refresh_auto_strategies()
        auto_layout.addRow("选择策略:", self.auto_strategy_combo)
        auto_layout.addRow("标的列表:", self.auto_codes_input)
        auto_layout.addRow(btn_auto_box)
        auto_layout.addRow(self.auto_log)

        left_layout.addWidget(auto_group)

        risk_group = QGroupBox("风险监控")
        risk_layout = QFormLayout(risk_group)
        risk_layout.setLabelAlignment(Qt.AlignRight)
        self.label_risk_status = QLabel("未运行")
        self.label_risk_drawdown = QLabel("--")
        self.label_risk_position = QLabel("--")
        self.label_risk_trades = QLabel("--")
        self.label_risk_loss = QLabel("--")
        self.label_risk_alerts = QLabel("0")
        risk_layout.addRow("状态:", self.label_risk_status)
        risk_layout.addRow("回撤/上限:", self.label_risk_drawdown)
        risk_layout.addRow("总仓/上限:", self.label_risk_position)
        risk_layout.addRow("当日交易:", self.label_risk_trades)
        risk_layout.addRow("当日盈亏:", self.label_risk_loss)
        risk_layout.addRow("告警数:", self.label_risk_alerts)
        risk_btns = QHBoxLayout()
        btn_reset_risk = QPushButton("重置风控")
        btn_reset_risk.clicked.connect(self._reset_risk_state)
        btn_open_risk = QPushButton("查看日志")
        btn_open_risk.clicked.connect(self._open_risk_journal)
        risk_btns.addWidget(btn_reset_risk)
        risk_btns.addWidget(btn_open_risk)
        risk_layout.addRow(risk_btns)
        left_layout.addWidget(risk_group)

        # 将内容设置到滚动区域
        scroll_area.setWidget(scroll_content)
        left_main_layout.addWidget(scroll_area)

        # 右侧 - 委托和成交记录
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 当日委托
        orders_group = QGroupBox("当日委托")
        orders_layout = QVBoxLayout(orders_group)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(8)
        self.orders_table.setHorizontalHeaderLabels(
            ["订单号", "时间", "代码", "方向", "价格", "数量", "成交", "状态"]
        )
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        orders_layout.addWidget(self.orders_table)

        btn_cancel = QPushButton("撤单")
        btn_cancel.clicked.connect(self.cancel_order)
        orders_layout.addWidget(btn_cancel)

        right_layout.addWidget(orders_group)

        # 当日成交
        trades_group = QGroupBox("当日成交")
        trades_layout = QVBoxLayout(trades_group)

        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(7)
        self.trades_table.setHorizontalHeaderLabels(
            ["成交号", "时间", "代码", "方向", "价格", "数量", "手续费"]
        )
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        trades_layout.addWidget(self.trades_table)

        right_layout.addWidget(trades_group)

        # 添加到主布局
        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 2)

        self.reload_config()

    def _setup_callbacks(self):
        """设置回调函数"""
        self._engine.on_order = self._on_order_update
        self._engine.on_trade = self._on_trade_update
        self._engine.on_account = self._on_account_update
        self._engine.on_position = self._on_position_update

    # ------------------------------------------------------------------ 本地快照/渲染
    def _snapshot_order(self, order: Order) -> dict:
        create_time = order.create_time or datetime.now()
        update_time = order.update_time or create_time
        key = order.order_id or f"{order.code}-{int(create_time.timestamp()*1000)}-{id(order)}"
        return {
            "key": key,
            "order_id": order.order_id,
            "display_id": order.order_id or "--",
            "code": order.code,
            "side": order.side,
            "price": float(order.price or 0.0),
            "quantity": int(order.quantity or 0),
            "filled": int(order.filled_quantity or 0),
            "status": order.status,
            "create_time": create_time,
            "update_time": update_time,
        }

    def _snapshot_trade(self, trade: Trade) -> dict:
        trade_time = trade.trade_time or datetime.now()
        return {
            "trade_id": trade.trade_id or "--",
            "code": trade.code,
            "side": trade.side,
            "price": float(trade.price or 0.0),
            "quantity": int(trade.quantity or 0),
            "commission": float(trade.commission or 0.0),
            "trade_time": trade_time,
        }

    def _render_orders_for_code(self, code: str):
        self.orders_table.setRowCount(0)
        self._current_display_order_keys = []
        snapshots = list(self._orders_by_code.get(code, {}).values()) if code else []
        snapshots.sort(key=lambda item: item["create_time"])
        for snap in snapshots:
            row = self.orders_table.rowCount()
            self.orders_table.insertRow(row)
            self._current_display_order_keys.append(snap["key"])
            self.orders_table.setItem(row, 0, QTableWidgetItem(snap["display_id"]))
            self.orders_table.setItem(row, 1, QTableWidgetItem(snap["create_time"].strftime("%H:%M:%S")))
            self.orders_table.setItem(row, 2, QTableWidgetItem(snap["code"]))

            direction = "买入" if snap["side"] == OrderSide.BUY else "卖出"
            dir_item = QTableWidgetItem(direction)
            dir_item.setForeground(QColor(255, 0, 0) if snap["side"] == OrderSide.BUY else QColor(0, 128, 0))
            self.orders_table.setItem(row, 3, dir_item)

            self.orders_table.setItem(row, 4, QTableWidgetItem(f"{snap['price']:.2f}"))
            self.orders_table.setItem(row, 5, QTableWidgetItem(str(snap["quantity"])))
            self.orders_table.setItem(row, 6, QTableWidgetItem(str(snap["filled"])))

            status_text, status_color = self._format_order_status(snap["status"])
            status_item = QTableWidgetItem(status_text)
            if status_color:
                status_item.setForeground(status_color)
            self.orders_table.setItem(row, 7, status_item)

    def _render_trades_for_code(self, code: str):
        self.trades_table.setRowCount(0)
        snapshots = list(self._trades_by_code.get(code, [])) if code else []
        snapshots.sort(key=lambda item: item["trade_time"])
        for snap in snapshots:
            row = self.trades_table.rowCount()
            self.trades_table.insertRow(row)
            self.trades_table.setItem(row, 0, QTableWidgetItem(snap["trade_id"]))
            self.trades_table.setItem(row, 1, QTableWidgetItem(snap["trade_time"].strftime("%H:%M:%S")))
            self.trades_table.setItem(row, 2, QTableWidgetItem(snap["code"]))

            direction = "买入" if snap["side"] == OrderSide.BUY else "卖出"
            dir_item = QTableWidgetItem(direction)
            dir_item.setForeground(QColor(255, 0, 0) if snap["side"] == OrderSide.BUY else QColor(0, 128, 0))
            self.trades_table.setItem(row, 3, dir_item)

            self.trades_table.setItem(row, 4, QTableWidgetItem(f"{snap['price']:.2f}"))
            self.trades_table.setItem(row, 5, QTableWidgetItem(str(snap["quantity"])))
            self.trades_table.setItem(row, 6, QTableWidgetItem(f"{snap['commission']:.2f}"))

    def _format_order_status(self, status: OrderStatus):
        status_map = {
            OrderStatus.SUBMITTED: ("已报", None),
            OrderStatus.PENDING: ("待发送", None),
            OrderStatus.FILLED: ("已成", QColor(0, 128, 0)),
            OrderStatus.CANCELLED: ("已撤", QColor(128, 128, 128)),
            OrderStatus.REJECTED: ("废单", QColor(200, 0, 0)),
        }
        return status_map.get(status, (str(status), None))

    def reload_config(self):
        """从配置中读取默认券商等信息"""
        cfg = self.config.get_all()
        broker_value = cfg.get("broker_type", "simulated")
        broker_text = self.BROKER_VALUE_TO_TEXT.get(broker_value, "模拟交易")
        index = self.broker_combo.findText(broker_text)
        if index >= 0:
            self.broker_combo.setCurrentIndex(index)
        self.strategy_runner.reload_config()
        self.ai_helper.reload_config(self.config)
        self._refresh_auto_strategies()

    def _on_order_update(self, order: Order):
        """订单更新回调（按股票缓存并刷新当前激活股票）"""
        if not order or not order.code:
            return
        snapshot = self._snapshot_order(order)
        bucket = self._orders_by_code.setdefault(order.code, {})
        bucket[snapshot["key"]] = snapshot
        if order.code == self._active_stock_code:
            self._render_orders_for_code(order.code)

    def _on_trade_update(self, trade: Trade):
        """成交更新回调"""
        if not trade or not trade.code:
            return
        snapshot = self._snapshot_trade(trade)
        bucket = self._trades_by_code.setdefault(trade.code, [])
        bucket.append(snapshot)
        if trade.code == self._active_stock_code:
            self._render_trades_for_code(trade.code)

    def _on_account_update(self, account: AccountInfo):
        """账户更新回调"""
        self.cash_label.setText(f"¥{account.cash:,.2f}")
        self.total_label.setText(f"¥{account.total_value:,.2f}")
        self._last_account = account
        self._emit_account_snapshot(account)

    def _on_position_update(self, position: Position):
        """持仓更新回调"""
        self._emit_positions_snapshot()

    def _on_refresh_timer(self):
        self._refresh_account()
        self._refresh_risk_summary()

    def _refresh_account(self):
        """刷新账户信息"""
        if self._broker and self._broker.is_logged_in:
            self._engine.get_account()

    def update_amount(self):
        """更新委托金额"""
        price = self.price_input.value()
        qty = self.qty_input.value()
        amount = price * qty
        self.amount_label.setText(f"¥{amount:,.2f}")


    def connect_broker(self):
        """连接券商"""
        broker_text = self.broker_combo.currentText()
        broker_value = self.BROKER_TEXT_TO_VALUE.get(broker_text, "simulated")
        cfg = self.config.get_all()

        if broker_value == "simulated":
            config = BrokerConfig(
                broker_type=BrokerType.SIMULATED,
                extra={
                    'initial_capital': cfg.get('initial_capital', 1000000.0),
                    'commission_rate': cfg.get('commission_rate', 0.0003),
                    'slippage': cfg.get('slippage', 0.001),
                }
            )
            self._broker = SimulatedBroker(config)
        else:
            account = cfg.get('broker_account', '').strip()
            password = cfg.get('broker_password', '').strip()
            api_url = cfg.get('broker_api_url', '').strip()
            if not account or not password or not api_url:
                QMessageBox.warning(self, "提示", "请先在设置中填写券商账号/密码/API地址")
                return False
            try:
                broker_type = BrokerType(broker_value)
            except ValueError:
                QMessageBox.warning(self, "提示", f"暂不支持 {broker_text}")
                return False
            verify_ssl = cfg.get("broker_api_verify_ssl", True)
            client_cert = cfg.get("broker_api_client_cert", "").strip()
            config = BrokerConfig(
                broker_type=broker_type,
                account=account,
                password=password,
                extra={
                    "base_url": api_url,
                    "poll_interval": cfg.get("api_poll_interval", 3),
                    "timeout": cfg.get("api_timeout", 8),
                    "api_key": cfg.get("broker_api_key", ""),
                    "api_secret": cfg.get("broker_api_secret", ""),
                    "verify_ssl": verify_ssl,
                }
            )
            if client_cert:
                config.extra["client_cert"] = client_cert
            broker = BrokerFactory.create(config)
            if not broker:
                QMessageBox.warning(self, "提示", f"{broker_text} 暂无可用实现")
                return False
            self._broker = broker

        self._engine.set_broker(self._broker)

        if self._engine.connect() and self._engine.login():
            self._engine.start_trading()
            self.status_label.setText(f"已连接({broker_text})")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)

            account_info = self._engine.get_account()
            if account_info:
                self.cash_label.setText(f"¥{account_info.cash:,.2f}")
                self.total_label.setText(f"¥{account_info.total_value:,.2f}")
                self._emit_account_snapshot(account_info)
            else:
                self._emit_account_snapshot(None)
            self._emit_positions_snapshot()

            QMessageBox.information(self, "提示", f"已连接 {broker_text} 并开启交易")
            return True
        QMessageBox.warning(self, "提示", "连接或登录失败，请检查配置")
        return False

    def disconnect_broker(self):
        """断开连接"""
        if self._broker:
            self._engine.stop_trading()
            self._engine.disconnect()
            self._broker = None

            self.status_label.setText("未连接")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            self.cash_label.setText("--")
            self.total_label.setText("--")

            QMessageBox.information(self, "提示", "已断开连接")
            self._emit_account_snapshot(None)
            self.positions_updated.emit([])
            return True
        return False

    def start_trading_session(self):
        """启动交易引擎"""
        if not self._broker or not self._broker.is_logged_in:
            QMessageBox.warning(self, "提示", "请先连接券商")
            return False
        if self._engine.is_trading:
            return True
        self._engine.start_trading()
        QMessageBox.information(self, "提示", "交易已启动")
        return True

    def stop_trading_session(self):
        """停止交易引擎"""
        if not self._engine.is_trading:
            return True
        self._engine.stop_trading()
        QMessageBox.information(self, "提示", "交易已停止")
        return True

    def _emit_account_snapshot(self, account: Optional[AccountInfo]):
        """向外部发送账户快照"""
        info = {
            "total": float(getattr(account, "total_value", 0.0) or 0.0),
            "available": float(getattr(account, "cash", 0.0) or 0.0),
            "market_value": float(getattr(account, "market_value", 0.0) or 0.0),
            "profit": float(getattr(account, "profit", 0.0) or 0.0),
            "profit_pct": float(getattr(account, "profit_pct", 0.0) or 0.0),
        }
        self.account_updated.emit(info)

    def _emit_positions_snapshot(self):
        """向外部发送持仓列表"""
        positions = self._engine.get_positions() if self._broker else []
        payload = []
        for pos in positions or []:
            current_price = getattr(pos, "current_price", None)
            if not current_price:
                current_price = pos.avg_cost
            payload.append({
                "code": pos.code,
                "name": getattr(pos, "name", pos.code),
                "qty": int(getattr(pos, "quantity", 0) or 0),
                "cost": float(getattr(pos, "avg_cost", 0.0) or 0.0),
                "price": float(current_price or 0.0),
            })
        self.positions_updated.emit(payload)

    def _refresh_risk_summary(self):
        """刷新策略风控信息"""
        summary = self.strategy_runner.get_risk_summary()
        if not summary:
            self.label_risk_status.setText("未启用")
            self.label_risk_drawdown.setText("--")
            self.label_risk_position.setText("--")
            self.label_risk_trades.setText("--")
            self.label_risk_loss.setText("--")
            self.label_risk_alerts.setText("0")
            return

        running = summary.get("is_running", False)
        trading_allowed = summary.get("is_trading_allowed", True)
        if not running:
            status = "未运行"
        elif trading_allowed:
            status = "运行中"
        else:
            reason = summary.get("risk_paused_reason") or "已暂停"
            status = f"已暂停: {reason}"
        self.label_risk_status.setText(status)

        drawdown = summary.get("drawdown", 0.0)
        max_drawdown = summary.get("max_drawdown", 0.0)
        self.label_risk_drawdown.setText(f"{drawdown:.2f}% / {max_drawdown:.0f}%")

        position_pct = summary.get("position_pct", 0.0)
        max_position_pct = summary.get("max_position_pct", 0.0)
        self.label_risk_position.setText(f"{position_pct:.2f}% / {max_position_pct:.0f}%")

        daily_trades = summary.get("daily_trades", 0)
        max_daily_trades = summary.get("max_daily_trades", 0)
        self.label_risk_trades.setText(f"{daily_trades}/{max_daily_trades}")

        daily_loss = summary.get("daily_loss", 0.0)
        max_daily_loss = summary.get("max_daily_loss", 0.0)
        loss_text = f"-¥{daily_loss:,.2f}" if daily_loss > 0 else "0"
        self.label_risk_loss.setText(f"{loss_text} / ¥{max_daily_loss:,.0f}")

        self.label_risk_alerts.setText(str(summary.get("alert_count", 0)))

    def _reset_risk_state(self):
        """手动清空风控统计"""
        if not self.strategy_runner.is_running:
            reply = QMessageBox.question(
                self, "重置风控",
                "将清空当日统计和告警记录，确定继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        self.strategy_runner.reset_risk_state()
        QMessageBox.information(self, "提示", "风控统计已清空")
        self._refresh_risk_summary()

    def _open_risk_journal(self):
        """打开风控日志文件"""
        path = self.strategy_runner.get_risk_journal_file()
        if not path or not path.exists():
            QMessageBox.information(self, "提示", "暂无风控日志")
            return
        try:
            os.startfile(str(path))
        except OSError as err:
            QMessageBox.warning(self, "错误", f"无法打开日志: {err}")

    def place_order(self):
        """下单"""
        if not self._broker or not self._broker.is_logged_in:
            QMessageBox.warning(self, "提示", "请先连接交易服务器")
            return

        code = self.stock_input.text().strip()
        if not code:
            QMessageBox.warning(self, "提示", "请输入股票代码")
            return

        is_buy = self.radio_buy.isChecked()
        direction = "买入" if is_buy else "卖出"
        price = self.price_input.value()
        qty = self.qty_input.value()

        reply = QMessageBox.question(
            self, '确认下单',
            f'确认{direction} {code}\n价格: {price:.2f}\n数量: {qty}',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 设置模拟市场价格（用于成交）
            if isinstance(self._broker, SimulatedBroker):
                self._broker.set_market_price(code, price)

            # 发送订单
            if is_buy:
                result = self._engine.buy(code, price, qty)
            else:
                result = self._engine.sell(code, price, qty)

            if result.success:
                QMessageBox.information(self, "提示", f"委托已提交\n订单号: {result.order_id}")
            else:
                QMessageBox.warning(self, "下单失败", result.message)

    def quick_order(self, direction, qty):
        """快捷下单"""
        code = self.stock_input.text().strip()
        if not code:
            QMessageBox.warning(self, "提示", "请先输入股票代码")
            return

        if direction == "buy":
            self.radio_buy.setChecked(True)
        else:
            self.radio_sell.setChecked(True)

            # 处理卖半仓和清仓
            if qty < 0:
                positions = self._engine.get_positions()
                pos = next((p for p in positions if p.code == code), None)
                if not pos:
                    QMessageBox.warning(self, "提示", f"没有{code}的持仓")
                    return
                if qty == -1:  # 卖半仓
                    qty = (pos.quantity // 2 // 100) * 100
                else:  # 清仓
                    qty = pos.quantity
                if qty <= 0:
                    QMessageBox.warning(self, "提示", "持仓数量不足")
                    return

        if qty > 0:
            self.qty_input.setValue(qty)

        self.place_order()

    def cancel_order(self):
        """撤单"""
        current_row = self.orders_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请选择要撤销的委托")
            return

        if current_row >= len(self._current_display_order_keys):
            QMessageBox.warning(self, "提示", "无法定位订单")
            return

        key = self._current_display_order_keys[current_row]
        code_orders = self._orders_by_code.get(self._active_stock_code or "", {})
        snapshot = code_orders.get(key)
        if not snapshot or not snapshot.get("order_id"):
            QMessageBox.warning(self, "提示", "订单尚未生成可撤销的编号")
            return

        if self._engine.cancel(snapshot["order_id"]):
            QMessageBox.information(self, "提示", "撤单成功")
        else:
            QMessageBox.warning(self, "提示", "撤单失败，订单可能已成交或已撤销")

    def get_engine(self) -> TradingEngine:
        """获取交易引擎"""
        return self._engine

    def show_ai_trade_advice(self):
        """展示AI对当前输入的下单建议"""
        code = self.stock_input.text().strip() or "未填"
        direction = "买入" if self.radio_buy.isChecked() else "卖出"
        price = self.price_input.value()
        qty = self.qty_input.value()
        cash = self._last_account.cash if self._last_account else None
        pos = None
        positions = self._engine.get_positions()
        for position in positions:
            if position.code == code:
                pos = position.quantity
                break
        advice = self.ai_helper.advise_order(
            code=code,
            direction=direction,
            price=price,
            quantity=qty,
            cash_available=cash,
            position_size=pos,
        )
        self.ai_advice_box.setPlainText(advice)

    # ------------------------ 自选股上下文同步 ------------------------
    def set_active_stock(self, code: str, name: str = ""):
        """当左侧自选股切换时，更新手动下单信息"""
        self.stock_input.setText(code)
        self.stock_name.setText(name or "--")
        self._active_stock_code = code
        self._render_orders_for_code(code)
        self._render_trades_for_code(code)

    def export_stock_state(self) -> dict:
        """导出当前股票的下单参数与策略选择"""
        strategy_name = ""
        if self.auto_strategy_combo.isEnabled():
            strategy_name = self.auto_strategy_combo.currentText().strip()
        elif self._pending_stock_strategy:
            strategy_name = self._pending_stock_strategy
        return {
            "price": self.price_input.value(),
            "quantity": self.qty_input.value(),
            "strategy": strategy_name,
        }

    def apply_stock_state(self, state: dict, strategy_name: str = ""):
        """恢复指定股票缓存的交易参数"""
        cached_state = state or {}
        if isinstance(cached_state, dict):
            if "price" in cached_state:
                try:
                    self.price_input.setValue(float(cached_state["price"]))
                except (TypeError, ValueError):
                    pass
            if "quantity" in cached_state:
                try:
                    self.qty_input.setValue(int(cached_state["quantity"]))
                except (TypeError, ValueError):
                    pass
            cached_strategy = cached_state.get("strategy", "")
        else:
            cached_strategy = ""
        target_strategy = strategy_name or cached_strategy
        self._select_stock_strategy(target_strategy)

    def set_strategy_change_callback(self, callback):
        """注册策略切换回调，通知主窗口缓存策略绑定"""
        self._strategy_change_callback = callback

    def set_strategy_assignment_provider(self, provider):
        """设置一个回调以获取股票-策略映射"""
        self._strategy_assignment_provider = provider

    def update_strategy_preview(self, assignments: Dict[str, str]):
        """预览当前已绑定策略的股票概览"""
        if not assignments:
            self.auto_codes_input.setText("未绑定策略")
            return
        parts = []
        for code, strategy in assignments.items():
            if strategy:
                parts.append(f"{code}:{strategy}")
        self.auto_codes_input.setText(", ".join(parts) if parts else "未绑定策略")

    def _select_stock_strategy(self, name: str):
        """根据策略名称选择下拉项，若不存在则暂存等待刷新"""
        if not name:
            return
        if self.auto_strategy_combo.isEnabled():
            index = self.auto_strategy_combo.findText(name)
            if index >= 0:
                self._loading_strategy = True
                self.auto_strategy_combo.setCurrentIndex(index)
                self._loading_strategy = False
                self._pending_stock_strategy = ""
            else:
                self._pending_stock_strategy = name
        else:
            self._pending_stock_strategy = name

    def _on_strategy_combo_changed(self, text: str):
        """策略列表变更时通知主窗口刷新绑定"""
        if self._loading_strategy or not self.auto_strategy_combo.isEnabled():
            return
        strategy = text.strip()
        if self._strategy_change_callback and self._active_stock_code:
            self._strategy_change_callback(self._active_stock_code, strategy)
        self._pending_stock_strategy = strategy or self._pending_stock_strategy

    # ------------------------ 自动策略运行 ------------------------
    def _refresh_auto_strategies(self):
        self._loading_strategy = True
        self.auto_strategy_combo.clear()
        names = self.strategy_manager.get_available_strategy_names()
        has_strategies = bool(names)
        if not has_strategies:
            placeholder = "暂无策略，请先在“策略”页保存策略"
            self.auto_strategy_combo.addItem(placeholder)
            self.auto_strategy_combo.setEnabled(False)
            if not self.btn_auto_stop.isEnabled():
                self.btn_auto_start.setEnabled(False)
            self._loading_strategy = False
            return

        self.auto_strategy_combo.addItems(names)
        self.auto_strategy_combo.setEnabled(True)
        if not self.btn_auto_stop.isEnabled():
            self.btn_auto_start.setEnabled(True)
        target = self._pending_stock_strategy
        if target and target in names:
            self.auto_strategy_combo.setCurrentIndex(names.index(target))
            self._pending_stock_strategy = ""
        self._loading_strategy = False

    def start_auto_strategy(self):
        assignments: Dict[str, str] = {}
        if self._strategy_assignment_provider:
            try:
                assignments = self._strategy_assignment_provider() or {}
            except Exception as err:
                QMessageBox.warning(self, "错误", f"无法读取策略绑定: {err}")
                return
        if not assignments:
            QMessageBox.warning(self, "提示", "请先在每个自选股页面为股票选择策略。")
            return
        codes = [code for code, name in assignments.items() if name]
        if not codes:
            QMessageBox.warning(self, "提示", "尚未为任何股票绑定策略。")
            return
        try:
            self.strategy_runner.reload_config()
            display_codes = ", ".join(f"{code}:{assignments[code]}" for code in codes)
            self.auto_codes_input.setText(display_codes)
            self.strategy_runner.start("", codes, per_stock_strategies=assignments)
            self.btn_auto_start.setEnabled(False)
            self.btn_auto_stop.setEnabled(True)
            QMessageBox.information(self, "提示", "策略已启动，系统将自动执行。")
        except Exception as err:
            QMessageBox.warning(self, "错误", str(err))

    def stop_auto_strategy(self):
        self.strategy_runner.stop()
        self.btn_auto_stop.setEnabled(False)
        self._refresh_auto_strategies()
        QMessageBox.information(self, "提示", "已停止自动策略。")

    def _handle_risk_alert(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.auto_log.append(f"[{timestamp}] ⚠ {message}")
        QMessageBox.warning(self, "风控告警", message)

    def _handle_strategy_signal(self, order: Order):
        timestamp = datetime.now().strftime("%H:%M:%S")
        summary = f"{order.code} {order.side.value} {order.quantity}股 @ {order.price:.2f}"
        QApplication.beep()
        self.auto_log.append(f"[{timestamp}] 🔔 半自动信号: {summary}")
        QMessageBox.information(self, "策略信号提醒", f"检测到策略信号：\n{summary}\n请手动检查并下单。")

    def _append_strategy_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.auto_log.append(f"[{timestamp}] {message}")
