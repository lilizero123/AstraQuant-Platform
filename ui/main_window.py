"""
主窗口模块 - 现代化深色主题
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QMenuBar, QMenu, QAction,
    QActionGroup, QToolBar, QDockWidget, QListWidget, QTextEdit,
    QSplitter, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QGraphicsDropShadowEffect, QInputDialog, QFileDialog,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, QShortcut,
    QApplication
)
from PyQt5.QtCore import Qt, QTimer, QSize, QUrl
from PyQt5.QtGui import QIcon, QFont, QColor, QKeySequence, QDesktopServices
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path

from ui.widgets.kline_widget import KLineWidget
from ui.widgets.strategy_widget import StrategyWidget
from ui.widgets.backtest_widget import BacktestWidget
from ui.widgets.trade_widget import TradeWidget
from ui.widgets.position_widget import PositionWidget
from ui.widgets.settings_dialog import SettingsDialog
from ui.styles import get_style
from ui.i18n import Translator, AVAILABLE_LANGUAGES
from core.assistant.ai_helper import AIHelper
from core.data.data_source import DataManager as DataSourceManager
from core.data_sources.china import ChinaStockProvider
from core.utils.stock import normalize_stock_code, add_market_prefix
from core.logger import get_log_manager
from config.settings import config_manager


@dataclass
class StockContext:
    """保存单只股票的专属视图状态"""

    code: str
    name: str = ""
    strategy: str = ""
    backtest_state: Dict[str, object] = field(default_factory=dict)
    trade_state: Dict[str, object] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return f"{self.code} {self.name}".strip()


class MainWindow(QMainWindow):
    """主窗口"""

    DISCLAIMER_VERSION = 1
    DISCLAIMER_TEXT = (
        "免责声明：\n"
        "1. 本软件仅供学习和个人研究使用，作者不是持牌金融从业人员；\n"
        "2. 使用本软件进行任何交易、投资或模拟，盈亏与作者无关；\n"
        "3. AI 功能产生的内容仅供参考，不构成投资建议；\n"
        "4. 未经作者书面许可，不得在商业环境中使用或转售本软件；\n"
        "5. 商用合作及授权请联系 QQ: 3946808002。\n"
    )

    DEFAULT_WATCHLIST = [
        "000001  平安银行",
        "000002  万科A",
        "600000  浦发银行",
        "600036  招商银行",
        "601318  中国平安",
    ]

    @staticmethod
    def _resolve_runtime_path(value: str, fallback_subdir: str) -> Path:
        """根据运行环境解析数据目录，确保相对路径以程序根目录为基准。"""
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent

        if value:
            target = Path(value)
            if not target.is_absolute():
                target = base_dir / target
        else:
            target = base_dir / fallback_subdir
        return target

    def t(self, key, fallback=""):
        return self.translator.translate(key, fallback)

    def __init__(self):
        super().__init__()
        self.config_manager = config_manager
        self.current_theme = self.config_manager.get("theme", "dark")
        language = self.config_manager.get("language", "zh")
        language = language if language in AVAILABLE_LANGUAGES else "zh"
        self.current_language = language
        self.translator = Translator(self.current_language)
        self.ai_helper = AIHelper()
        self.market_status_key = "disconnected"
        self.trade_status_key = "disconnected"
        self.stock_contexts: Dict[str, StockContext] = {}
        self.current_stock_code: Optional[str] = None
        data_path = self.config_manager.get("data_path", "./data")
        self.data_dir = self._resolve_runtime_path(data_path, "data")
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.watchlist_file = self.data_dir / "watchlist.json"
        self.setWindowTitle(self.t("app.title"))
        icon_path = Path(__file__).resolve().parent.parent / "resources" / "astra_icon.ico"
        if getattr(sys, "frozen", False):
            icon_path = Path(sys.executable).parent / "resources" / "astra_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(1400, 900)
        self.apply_style()
        self.init_ui()
        self.init_menu()
        self.init_toolbar()
        self.init_statusbar()
        self.init_shortcuts()
        self.apply_translations()
        self._show_disclaimer_if_needed()

    def apply_style(self):
        """应用样式"""
        self.setStyleSheet(get_style(self.current_theme))

    def init_ui(self):
        """初始化UI"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 左侧面板 - 股票列表
        left_panel = self.create_left_panel()

        # 中央区域 - 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(True)

        # K线图标签页
        self.kline_widget = KLineWidget(translator=self.translator)
        self.tab_widget.addTab(self.kline_widget, "  行情  ")
        if hasattr(self.kline_widget, "data_loaded"):
            self.kline_widget.data_loaded.connect(self._handle_market_data_status)

        # 策略标签页
        self.strategy_widget = StrategyWidget()
        self.tab_widget.addTab(self.strategy_widget, "  策略  ")
        if hasattr(self.strategy_widget, "strategies_changed"):
            self.strategy_widget.strategies_changed.connect(self.on_strategies_changed)

        # 回测标签页
        self.backtest_widget = BacktestWidget()
        if hasattr(self.backtest_widget, "set_stock_provider"):
            self.backtest_widget.set_stock_provider(self.get_watchlist_items)
        self.tab_widget.addTab(self.backtest_widget, "  回测  ")

        # 交易标签页
        self.trade_widget = TradeWidget()
        if hasattr(self.trade_widget, "set_strategy_change_callback"):
            self.trade_widget.set_strategy_change_callback(self._handle_stock_strategy_changed)
        if hasattr(self.trade_widget, "set_strategy_assignment_provider"):
            self.trade_widget.set_strategy_assignment_provider(self._get_strategy_assignments)
        if hasattr(self.trade_widget, "update_strategy_preview"):
            self.trade_widget.update_strategy_preview(self._get_strategy_assignments())
        self.tab_widget.addTab(self.trade_widget, "  交易  ")
        if hasattr(self.trade_widget, "reload_config"):
            self.trade_widget.reload_config()

        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # 右侧面板 - 持仓和日志
        right_panel = self.create_right_panel()

        if hasattr(self.trade_widget, "account_updated"):
            self.trade_widget.account_updated.connect(self._handle_trade_account_update)
        if hasattr(self.trade_widget, "positions_updated"):
            self.trade_widget.positions_updated.connect(self.position_widget.update_positions)

        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.tab_widget)
        splitter.addWidget(right_panel)
        splitter.setSizes([220, 900, 320])
        splitter.setHandleWidth(2)

        main_layout.addWidget(splitter)

        if self.stock_list.count() > 0:
            self.stock_list.setCurrentRow(0)

    def on_tab_changed(self, index):
        """标签页切换时的处理"""
        widget = self.tab_widget.widget(index)
        if widget is self.backtest_widget:
            self.backtest_widget.refresh_strategy_list()
            if hasattr(self.backtest_widget, "refresh_stock_list"):
                self.backtest_widget.refresh_stock_list()
        elif widget is self.trade_widget and hasattr(self.trade_widget, "_refresh_auto_strategies"):
            self.trade_widget._refresh_auto_strategies()

    def on_strategies_changed(self):
        """策略新增/删除后联动刷新"""
        self.backtest_widget.refresh_strategy_list()
        if hasattr(self.trade_widget, "_refresh_auto_strategies"):
            self.trade_widget._refresh_auto_strategies()

    def _handle_trade_account_update(self, info: dict):
        """更新右侧账户概览"""
        if not hasattr(self, "position_widget"):
            return
        total = info.get("total", 0.0)
        available = info.get("available", 0.0)
        market_value = info.get("market_value", 0.0)
        profit = info.get("profit", 0.0)
        profit_pct = info.get("profit_pct", 0.0)
        self.position_widget.update_account(total, available, market_value, profit, profit_pct)

    def _handle_market_data_status(self, live: bool):
        """根据行情加载结果更新状态"""
        self.market_status_key = "live" if live else "demo"
        color = "#3fb950" if live else "#d29922"
        self.status_dot_market.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._update_status_labels()

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QFrame()
        panel.setObjectName("leftPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 标题区域
        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(4, 0, 4, 0)

        self.left_panel_title = QLabel(self.t("left.favorites"))
        self.left_panel_title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_layout.addWidget(self.left_panel_title)

        # 股票数量标签
        self.stock_count_label = QLabel("5")
        self.stock_count_label.setStyleSheet("""
            background-color: #30363d;
            color: #8b949e;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
        """)
        title_layout.addWidget(self.stock_count_label)
        title_layout.addStretch()

        layout.addWidget(title_frame)

        # 股票列表
        self.stock_list = QListWidget()
        watchlist = self._load_watchlist()
        if not watchlist:
            watchlist = self.DEFAULT_WATCHLIST.copy()
            self._save_watchlist(watchlist)
        self.stock_list.addItems(watchlist)
        self.stock_list.currentItemChanged.connect(self.on_stock_selected)
        self._sync_context_with_watchlist(watchlist)
        self.stock_count_label.setText(str(self.stock_list.count()))
        layout.addWidget(self.stock_list)

        # 添加按钮
        self.btn_add_stock = QPushButton(self.t("button.add_stock"))
        self.btn_add_stock.setCursor(Qt.PointingHandCursor)
        self.btn_add_stock.clicked.connect(self.add_stock)
        layout.addWidget(self.btn_add_stock)

        return panel

    def create_right_panel(self):
        """创建右侧面板"""
        panel = QFrame()
        panel.setObjectName("rightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 持仓组件
        self.position_widget = PositionWidget()
        if hasattr(self.position_widget, "clear"):
            self.position_widget.clear()
        layout.addWidget(self.position_widget)

        # 日志区域
        log_frame = QFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(8)

        log_header = QHBoxLayout()
        self.log_label = QLabel(self.t("log.system"))
        self.log_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        log_header.addWidget(self.log_label)

        self.btn_clear_logs = QPushButton(self.t("button.clear_logs"))
        self.btn_clear_logs.setFixedWidth(60)
        self.btn_clear_logs.setCursor(Qt.PointingHandCursor)
        self.btn_clear_logs.clicked.connect(lambda: self.log_text.clear())
        log_header.addWidget(self.btn_clear_logs)

        log_layout.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: "Consolas", "Microsoft YaHei";
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_frame)

        self.disclaimer_label = QLabel()
        self.disclaimer_label.setWordWrap(True)
        self.disclaimer_label.setStyleSheet("""
            QLabel {
                background-color: #211f25;
                border: 1px solid #3c3c43;
                border-radius: 6px;
                color: #f85149;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.disclaimer_label)

        return panel

    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        self.menu_file = menubar.addMenu("")
        self.action_import_data = QAction(self)
        self.action_import_data.triggered.connect(self.import_data)
        self.menu_file.addAction(self.action_import_data)

        self.action_export_data = QAction(self)
        self.action_export_data.triggered.connect(self.export_data)
        self.menu_file.addAction(self.action_export_data)
        self.menu_file.addSeparator()

        self.action_exit = QAction(self)
        self.action_exit.triggered.connect(self.close)
        self.menu_file.addAction(self.action_exit)

        # 策略菜单
        self.menu_strategy = menubar.addMenu("")
        self.action_new_strategy = QAction(self)
        self.action_new_strategy.triggered.connect(self.new_strategy)
        self.menu_strategy.addAction(self.action_new_strategy)

        self.action_load_strategy = QAction(self)
        self.action_load_strategy.triggered.connect(self.load_strategy)
        self.menu_strategy.addAction(self.action_load_strategy)

        self.action_save_strategy = QAction(self)
        self.action_save_strategy.triggered.connect(self.save_strategy)
        self.menu_strategy.addAction(self.action_save_strategy)

        # 交易菜单
        self.menu_trade = menubar.addMenu("")
        self.action_connect_trade = QAction(self)
        self.action_connect_trade.triggered.connect(self.connect_trade)
        self.menu_trade.addAction(self.action_connect_trade)

        self.action_disconnect_trade = QAction(self)
        self.action_disconnect_trade.triggered.connect(self.disconnect_trade)
        self.menu_trade.addAction(self.action_disconnect_trade)

        # 视图菜单
        self.menu_view = menubar.addMenu("")
        self.menu_theme = self.menu_view.addMenu("")
        self.theme_group = QActionGroup(self)
        self.action_theme_dark = QAction(self, checkable=True)
        self.action_theme_dark.triggered.connect(lambda: self.switch_theme("dark"))
        self.action_theme_light = QAction(self, checkable=True)
        self.action_theme_light.triggered.connect(lambda: self.switch_theme("light"))
        self.theme_group.addAction(self.action_theme_dark)
        self.theme_group.addAction(self.action_theme_light)
        self.menu_theme.addAction(self.action_theme_dark)
        self.menu_theme.addAction(self.action_theme_light)

        self.menu_language = self.menu_view.addMenu("")
        self.language_group = QActionGroup(self)
        self.language_actions = {}
        for lang_code in AVAILABLE_LANGUAGES.keys():
            action = QAction(self, checkable=True)
            action.triggered.connect(lambda checked, code=lang_code: self.switch_language(code))
            self.language_group.addAction(action)
            self.menu_language.addAction(action)
            self.language_actions[lang_code] = action

        # 设置菜单
        self.menu_settings = menubar.addMenu("")
        self.action_settings = QAction(self)
        self.action_settings.triggered.connect(self.open_settings_dialog)
        self.menu_settings.addAction(self.action_settings)

        # 帮助菜单
        self.menu_help = menubar.addMenu("")
        self.action_help = QAction(self)
        self.action_help.triggered.connect(self.show_help)
        self.menu_help.addAction(self.action_help)

        self.action_about = QAction(self)
        self.action_about.triggered.connect(self.show_about)
        self.menu_help.addAction(self.action_about)

        self.action_ai_log = QAction(self)
        self.action_ai_log.triggered.connect(self.show_ai_log_summary)
        self.menu_help.addAction(self.action_ai_log)

        self.action_contact = QAction(self)
        self.action_contact.triggered.connect(self.contact_author)
        self.menu_help.addAction(self.action_contact)

    def init_toolbar(self):
        """初始化工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # 刷新按钮
        self.action_refresh = toolbar.addAction("")
        self.action_refresh.triggered.connect(self.refresh_data)

        toolbar.addSeparator()

        # 回测按钮
        self.action_backtest = toolbar.addAction("")
        self.action_backtest.triggered.connect(self.start_backtest)

        toolbar.addSeparator()

        # 交易按钮
        self.action_start_trade = toolbar.addAction("")
        self.action_start_trade.triggered.connect(self.start_trade)

        self.action_stop_trade = toolbar.addAction("")
        self.action_stop_trade.triggered.connect(self.stop_trade)

    def init_statusbar(self):
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # 连接状态指示器
        self.status_dot_market = QLabel("●")
        self.status_dot_market.setStyleSheet("color: #f85149; font-size: 10px;")
        self.statusbar.addWidget(self.status_dot_market)

        self.status_connection = QLabel("")
        self.status_connection.setStyleSheet("color: #8b949e; margin-right: 20px;")
        self.statusbar.addWidget(self.status_connection)

        # 交易状态
        self.status_dot_trade = QLabel("●")
        self.status_dot_trade.setStyleSheet("color: #f85149; font-size: 10px;")
        self.statusbar.addWidget(self.status_dot_trade)

        self.status_trade = QLabel("")
        self.status_trade.setStyleSheet("color: #8b949e;")
        self.statusbar.addWidget(self.status_trade)

        # 弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Expanding, spacer.sizePolicy().Preferred)
        self.statusbar.addWidget(spacer)

        # 时间
        self.status_time = QLabel("")
        self.status_time.setStyleSheet("color: #8b949e;")
        self.statusbar.addPermanentWidget(self.status_time)

        # 定时更新时间
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self._update_status_labels()

    def init_shortcuts(self):
        """注册常用快捷键"""
        self._shortcuts = []

        def add_shortcut(sequence, handler):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

        add_shortcut("Ctrl+N", self.new_strategy)
        add_shortcut("Ctrl+O", self.load_strategy)
        add_shortcut("Ctrl+S", self.save_strategy)
        add_shortcut("F5", self.refresh_data)
        add_shortcut("F9", self.start_backtest)
        add_shortcut("Ctrl+Shift+R", self.start_trade)
        add_shortcut("Ctrl+Shift+S", self.stop_trade)
        add_shortcut("Ctrl+T", self.toggle_theme)
        add_shortcut("Ctrl+Shift+L", self.toggle_language)

    def toggle_theme(self):
        """在深浅色主题之间切换"""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.switch_theme(new_theme)

    def switch_theme(self, theme: str):
        if theme == self.current_theme:
            return
        self.current_theme = theme
        self.apply_style()
        self._update_theme_actions()
        self.config_manager.set("theme", theme)

    def _update_theme_actions(self):
        if hasattr(self, "action_theme_dark"):
            self.action_theme_dark.setChecked(self.current_theme == "dark")
            self.action_theme_light.setChecked(self.current_theme == "light")

    def toggle_language(self):
        """快速切换语言"""
        new_lang = "en" if self.current_language == "zh" else "zh"
        self.switch_language(new_lang)

    def switch_language(self, language: str):
        if language == self.current_language or language not in AVAILABLE_LANGUAGES:
            return
        self.current_language = language
        self.translator.set_language(language)
        self.apply_translations()
        self.config_manager.set("language", language)

    def apply_translations(self):
        """根据当前语言刷新所有文本"""
        self.setWindowTitle(self.t("app.title"))

        if hasattr(self, "menu_file"):
            self.menu_file.setTitle(self.t("menu.file"))
            self.action_import_data.setText(self.t("action.import_data"))
            self.action_export_data.setText(self.t("action.export_data"))
            self.action_exit.setText(self.t("action.exit"))

        if hasattr(self, "menu_strategy"):
            self.menu_strategy.setTitle(self.t("menu.strategy"))
            self.action_new_strategy.setText(self.t("action.new_strategy"))
            self.action_load_strategy.setText(self.t("action.load_strategy"))
            self.action_save_strategy.setText(self.t("action.save_strategy"))

        if hasattr(self, "menu_trade"):
            self.menu_trade.setTitle(self.t("menu.trade"))
            self.action_connect_trade.setText(self.t("action.connect_trade"))
            self.action_disconnect_trade.setText(self.t("action.disconnect_trade"))

        if hasattr(self, "menu_view"):
            self.menu_view.setTitle(self.t("menu.view"))
            self.menu_theme.setTitle(self.t("menu.theme"))
            self.menu_language.setTitle(self.t("menu.language"))
            self.action_theme_dark.setText(self.t("theme.dark"))
            self.action_theme_light.setText(self.t("theme.light"))
            for code, action in self.language_actions.items():
                action.setText(self.t(f"lang.{code}"))
                action.setChecked(code == self.current_language)
        if hasattr(self, "menu_settings"):
            self.menu_settings.setTitle(self.t("menu.settings", "设置"))
            self.action_settings.setText(self.t("action.settings", "系统设置"))

        if hasattr(self, "menu_help"):
            self.menu_help.setTitle(self.t("menu.help"))
            self.action_help.setText(self.t("action.help"))
            self.action_about.setText(self.t("action.about"))
            self.action_ai_log.setText(self.t("action.ai_log_summary", "AI日志摘要"))
            self.action_contact.setText(self.t("action.contact_author", "联系作者（QQ:3946808002）"))

        # 工具栏
        self.action_refresh.setText(self.t("toolbar.refresh"))
        self.action_backtest.setText(self.t("toolbar.backtest"))
        self.action_start_trade.setText(self.t("toolbar.trade.start"))
        self.action_stop_trade.setText(self.t("toolbar.trade.stop"))

        # 标签页
        self.tab_widget.setTabText(0, self.t("tab.market"))
        self.tab_widget.setTabText(1, self.t("tab.strategy"))
        self.tab_widget.setTabText(2, self.t("tab.backtest"))
        self.tab_widget.setTabText(3, self.t("tab.trade"))

        # 左侧与日志区域
        self.left_panel_title.setText(self.t("left.favorites"))
        self.btn_add_stock.setText(self.t("button.add_stock"))
        self.log_label.setText(self.t("log.system"))
        self.btn_clear_logs.setText(self.t("button.clear_logs"))

        # 状态栏
        self._update_status_labels()
        self._update_disclaimer_message()

        # 语言和主题按钮状态
        self._update_theme_actions()

        # 子组件
        if hasattr(self, "kline_widget"):
            self.kline_widget.set_translator(self.translator)
        self._update_disclaimer_message()

    def update_time(self):
        """更新时间显示"""
        from datetime import datetime
        self.status_time.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._update_status_labels()

    def _update_status_labels(self):
        """根据当前语言刷新状态文本"""
        market_defaults = {
            "disconnected": "行情未连接",
            "live": "行情连接正常",
            "demo": "使用示例数据",
        }
        trade_defaults = {
            "disconnected": "交易未连接",
            "connecting": "交易连接中",
            "running": "交易已启动",
            "stopped": "交易已停止",
        }
        market_text = self.t(f"status.market.{self.market_status_key}", market_defaults.get(self.market_status_key, market_defaults["disconnected"]))
        trade_text = self.t(f"status.trade.{self.trade_status_key}", trade_defaults.get(self.trade_status_key, trade_defaults["disconnected"]))
        self.status_connection.setText(market_text)
        self.status_trade.setText(trade_text)

    def log(self, message, level="info"):
        """添加日志"""
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")

        colors = {
            "info": "#8b949e",
            "success": "#3fb950",
            "warning": "#d29922",
            "error": "#f85149"
        }
        color = colors.get(level, "#8b949e")

        self.log_text.append(
            f'<span style="color: #6e7681;">[{time_str}]</span> '
            f'<span style="color: {color};">{message}</span>'
        )

    def get_watchlist_items(self):
        """返回当前自选股文本列表"""
        items = []
        for i in range(self.stock_list.count()):
            text = self.stock_list.item(i).text().strip()
            if text:
                items.append(text)
        return items

    def _parse_stock_entry(self, text: str):
        parts = text.split()
        if not parts:
            return "", ""
        code = parts[0]
        name = parts[1] if len(parts) > 1 else ""
        return code, name

    def _sync_context_with_watchlist(self, watchlist):
        updated: Dict[str, StockContext] = {}
        for text in watchlist or []:
            code, name = self._parse_stock_entry(text)
            if not code:
                continue
            context = self.stock_contexts.get(code)
            if context:
                context.name = name or context.name
            else:
                context = StockContext(code=code, name=name)
            updated[code] = context
        self.stock_contexts = updated
        self._refresh_strategy_preview_display()

    def _persist_current_stock_context(self):
        if not self.current_stock_code:
            return
        context = self.stock_contexts.get(self.current_stock_code)
        if not context:
            return
        if hasattr(self, "backtest_widget") and hasattr(self.backtest_widget, "export_stock_state"):
            context.backtest_state = self.backtest_widget.export_stock_state() or {}
        if hasattr(self, "trade_widget") and hasattr(self.trade_widget, "export_stock_state"):
            trade_state = self.trade_widget.export_stock_state() or {}
            context.trade_state = trade_state
            strategy = trade_state.get("strategy")
            if strategy:
                context.strategy = strategy
        self._refresh_strategy_preview_display()

    def _apply_stock_context(self, context: StockContext):
        if hasattr(self, "kline_widget"):
            self.kline_widget.load_stock(context.code)
        if hasattr(self, "backtest_widget"):
            if hasattr(self.backtest_widget, "set_active_stock"):
                self.backtest_widget.set_active_stock(context.code, context.name)
            if hasattr(self.backtest_widget, "apply_stock_state"):
                self.backtest_widget.apply_stock_state(context.backtest_state or {})
        if hasattr(self, "trade_widget"):
            if hasattr(self.trade_widget, "set_active_stock"):
                self.trade_widget.set_active_stock(context.code, context.name)
            if hasattr(self.trade_widget, "apply_stock_state"):
                self.trade_widget.apply_stock_state(context.trade_state or {}, context.strategy)
        self._refresh_strategy_preview_display()

    def _handle_stock_strategy_changed(self, code: str, strategy: str):
        """交易面板回调：某只股票的策略发生变化"""
        if not code:
            return
        context = self.stock_contexts.get(code)
        if not context:
            context = StockContext(code=code)
            self.stock_contexts[code] = context
        cleaned = (strategy or "").strip()
        context.strategy = cleaned
        if not isinstance(context.trade_state, dict):
            context.trade_state = {}
        context.trade_state["strategy"] = cleaned
        self._refresh_strategy_preview_display()

    def _get_strategy_assignments(self) -> Dict[str, str]:
        """返回所有股票当前绑定的策略"""
        assignments: Dict[str, str] = {}
        for code, context in self.stock_contexts.items():
            strategy = (context.strategy or "").strip()
            if not strategy and isinstance(context.trade_state, dict):
                raw = context.trade_state.get("strategy")
                if isinstance(raw, str):
                    strategy = raw.strip()
            if strategy:
                assignments[code] = strategy
        return assignments

    def _refresh_strategy_preview_display(self):
        if hasattr(self, "trade_widget") and hasattr(self.trade_widget, "update_strategy_preview"):
            self.trade_widget.update_strategy_preview(self._get_strategy_assignments())

    def _load_watchlist(self):
        """从磁盘加载自选股列表"""
        try:
            if self.watchlist_file.exists():
                with open(self.watchlist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return [str(item).strip() for item in data if str(item).strip()]
        except Exception as err:
            print(f"加载自选股列表失败: {err}")
        return []

    def _save_watchlist(self, items=None):
        """将当前自选股列表保存到磁盘"""
        if items is None:
            items = self.get_watchlist_items()
        try:
            self.watchlist_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.watchlist_file, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as err:
            print(f"保存自选股列表失败: {err}")

    # 槽函数
    def on_stock_selected(self, current, previous=None):
        """股票选中事件"""
        if current is None:
            return
        text = current.text().strip()
        code, name = self._parse_stock_entry(text)
        if not code:
            return
        if self.current_stock_code == code:
            return
        self._persist_current_stock_context()
        context = self.stock_contexts.get(code)
        if not context:
            context = StockContext(code=code, name=name)
            self.stock_contexts[code] = context
        else:
            context.name = name or context.name
        self.current_stock_code = code
        self._apply_stock_context(context)
        self.log(self.t("log.stock_selected").format(code=code), "info")

    def _update_disclaimer_message(self):
        if hasattr(self, "disclaimer_label"):
            self.disclaimer_label.setText(
                "【风险提示】本软件仅供学习交流，盈亏自负；AI 内容仅供参考。商业用途请联系 QQ:3946808002。"
            )

    def _show_disclaimer_if_needed(self):
        accepted_version = 0
        try:
            accepted_version = int(self.config_manager.get("disclaimer_accepted_version", 0) or 0)
        except Exception:
            accepted_version = 0
        if accepted_version >= self.DISCLAIMER_VERSION:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("免责声明")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        info = QLabel("请务必阅读以下免责声明，继续使用即视为同意：")
        info.setWordWrap(True)
        layout.addWidget(info)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.DISCLAIMER_TEXT)
        layout.addWidget(text)
        button_box = QDialogButtonBox()
        btn_accept = QPushButton("我已阅读并同意")
        btn_cancel = QPushButton("拒绝并退出")
        button_box.addButton(btn_accept, QDialogButtonBox.AcceptRole)
        button_box.addButton(btn_cancel, QDialogButtonBox.RejectRole)
        layout.addWidget(button_box)

        def accept():
            self.config_manager.set("disclaimer_accepted_version", self.DISCLAIMER_VERSION)
            dialog.accept()

        def reject():
            dialog.reject()

        btn_accept.clicked.connect(accept)
        btn_cancel.clicked.connect(reject)

        if dialog.exec_() != QDialog.Accepted:
            QMessageBox.information(self, "提示", "您已拒绝免责声明，程序即将退出。")
            QApplication.instance().quit()

    def add_stock(self):
        """添加股票"""
        dialog = AddStockDialog(self, translator=self.translator)
        if dialog.exec_() == QDialog.Accepted:
            code = dialog.get_stock_code()
            name = dialog.get_stock_name()
            if code and name:
                # 检查是否已存在
                for i in range(self.stock_list.count()):
                    if self.stock_list.item(i).text().startswith(code):
                        self.log(self.t("log.stock_exists").format(code=code), "warning")
                        return
                # 添加到列表
                self.stock_list.addItem(f"{code}  {name}")
                self.stock_count_label.setText(str(self.stock_list.count()))
                self.log(self.t("log.stock_added").format(code=code, name=name), "success")
                self._save_watchlist()
                self._sync_context_with_watchlist(self.get_watchlist_items())
                if hasattr(self.backtest_widget, "refresh_stock_list"):
                    self.backtest_widget.refresh_stock_list()

    def remove_stock(self):
        """删除选中的股票"""
        current = self.stock_list.currentItem()
        if current:
            self._persist_current_stock_context()
            code = current.text().split()[0]
            self.stock_list.takeItem(self.stock_list.row(current))
            self.stock_count_label.setText(str(self.stock_list.count()))
            self.log(self.t("log.stock_removed").format(code=code), "info")
            self._save_watchlist()
            self._sync_context_with_watchlist(self.get_watchlist_items())
            if self.current_stock_code == code:
                self.current_stock_code = None
            if hasattr(self.backtest_widget, "refresh_stock_list"):
                self.backtest_widget.refresh_stock_list()

    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入数据", "",
            "CSV文件 (*.csv);;Excel文件 (*.xlsx *.xls);;所有文件 (*.*)"
        )
        if file_path:
            try:
                import pandas as pd
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                self.log(self.t("log.import_success").format(path=file_path), "success")
                self.log(f"数据行数: {len(df)}, 列数: {len(df.columns)}", "info")
                # 如果包含股票代码列，可以添加到自选
                if 'code' in df.columns or '股票代码' in df.columns:
                    code_col = 'code' if 'code' in df.columns else '股票代码'
                    codes = df[code_col].unique()
                    self.log(f"发现 {len(codes)} 只股票", "info")
            except Exception as e:
                self.log(self.t("log.import_fail").format(error=str(e)), "error")

    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "export_data.csv",
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*.*)"
        )
        if file_path:
            try:
                import pandas as pd
                # 导出自选股列表
                stocks = []
                for i in range(self.stock_list.count()):
                    text = self.stock_list.item(i).text()
                    parts = text.split()
                    stocks.append({'code': parts[0], 'name': parts[1] if len(parts) > 1 else ''})
                df = pd.DataFrame(stocks)
                if file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')
                self.log(self.t("log.export_success").format(path=file_path), "success")
            except Exception as e:
                self.log(self.t("log.export_fail").format(error=str(e)), "error")

    def new_strategy(self):
        """新建策略"""
        self.tab_widget.setCurrentWidget(self.strategy_widget)
        self.strategy_widget.new_strategy()

    def load_strategy(self):
        """加载策略"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载策略", "strategies",
            "Python文件 (*.py);;所有文件 (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.strategy_widget.code_editor.setPlainText(code)
                self.tab_widget.setCurrentWidget(self.strategy_widget)
                self.log(self.t("log.load_success").format(name=os.path.basename(file_path)), "success")
            except Exception as e:
                self.log(self.t("log.load_fail").format(error=str(e)), "error")

    def save_strategy(self):
        """保存策略"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存策略", "strategies/my_strategy.py",
            "Python文件 (*.py);;所有文件 (*.*)"
        )
        if file_path:
            try:
                code = self.strategy_widget.code_editor.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                self.log(self.t("log.save_success").format(name=os.path.basename(file_path)), "success")
            except Exception as e:
                self.log(self.t("log.save_fail").format(error=str(e)), "error")

    def connect_trade(self):
        """连接交易"""
        self.log(self.t("log.connecting_trade"), "info")
        self.status_dot_trade.setStyleSheet("color: #d29922; font-size: 10px;")
        self.trade_status_key = "connecting"
        self._update_status_labels()
        self.tab_widget.setCurrentWidget(self.trade_widget)
        if self.trade_widget.connect_broker():
            self.status_dot_trade.setStyleSheet("color: #3fb950; font-size: 10px;")
            self.trade_status_key = "running"
        else:
            self.status_dot_trade.setStyleSheet("color: #f85149; font-size: 10px;")
            self.trade_status_key = "disconnected"
        self._update_status_labels()

    def disconnect_trade(self):
        """断开交易连接"""
        self.log(self.t("log.trade_disconnected"), "info")
        if self.trade_widget.disconnect_broker():
            self.status_dot_trade.setStyleSheet("color: #f85149; font-size: 10px;")
            self.trade_status_key = "disconnected"
            self._update_status_labels()

    def refresh_data(self):
        """刷新行情数据"""
        self.log(self.t("log.refreshing"), "info")

    def start_backtest(self):
        """开始回测"""
        self.tab_widget.setCurrentWidget(self.backtest_widget)
        self.backtest_widget.start_backtest()

    def start_trade(self):
        """启动交易"""
        self.log(self.t("log.trade_start"), "success")
        if self.trade_widget.start_trading_session():
            self.status_dot_trade.setStyleSheet("color: #3fb950; font-size: 10px;")
            self.trade_status_key = "running"
            self._update_status_labels()

    def stop_trade(self):
        """停止交易"""
        self.log(self.t("log.trade_stop"), "warning")
        if self.trade_widget.stop_trading_session():
            self.status_dot_trade.setStyleSheet("color: #f85149; font-size: 10px;")
            self.trade_status_key = "stopped"
            self._update_status_labels()

    def open_settings_dialog(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._apply_config_runtime()

    def _apply_config_runtime(self):
        """根据最新配置刷新主题/语言等"""
        theme = self.config_manager.get("theme", "dark")
        if theme != self.current_theme:
            self.switch_theme(theme)

        language = self.config_manager.get("language", "zh")
        language = language if language in AVAILABLE_LANGUAGES else "zh"
        if language != self.current_language:
            self.switch_language(language)

        if hasattr(self, "trade_widget"):
            self.trade_widget.reload_config()
        if hasattr(self, "strategy_widget") and hasattr(self.strategy_widget, "reload_config"):
            self.strategy_widget.reload_config()
        if hasattr(self, "backtest_widget") and hasattr(self.backtest_widget, "reload_config"):
            self.backtest_widget.reload_config()
        if hasattr(self, "ai_helper"):
            self.ai_helper.reload_config(self.config_manager)

    def show_help(self):
        """显示帮助"""
        QMessageBox.information(
            self,
            self.t("action.help"),
            self.t("message.help")
        )

    def show_about(self):
        """显示关于"""
        QMessageBox.about(
            self,
            self.t("action.about"),
            self.t("message.about")
        )

    def show_ai_log_summary(self):
        """AI总结最近日志"""
        logs = get_log_manager().get_recent_logs(200)
        summary = self.ai_helper.summarize_logs(logs)
        QMessageBox.information(
            self,
            self.t("action.ai_log_summary", "AI日志摘要"),
            summary
        )

    def contact_author(self):
        """通过QQ联系作者"""
        url = QUrl("tencent://message/?uin=3946808002&Site=&Menu=yes")
        if not QDesktopServices.openUrl(url):
            QMessageBox.information(
                self,
                "联系QQ",
                "请在QQ中添加：3946808002"
            )


class AddStockDialog(QDialog):
    """添加股票对话框"""

    # 常用股票列表
    COMMON_STOCKS = {
        '000001': '平安银行', '000002': '万科A', '000063': '中兴通讯',
        '000333': '美的集团', '000651': '格力电器', '000725': '京东方A',
        '000858': '五粮液', '002415': '海康威视', '002594': '比亚迪',
        '300750': '宁德时代', '600000': '浦发银行', '600009': '上海机场',
        '600016': '民生银行', '600019': '宝钢股份', '600028': '中国石化',
        '600030': '中信证券', '600036': '招商银行', '600048': '保利发展',
        '600050': '中国联通', '600104': '上汽集团', '600276': '恒瑞医药',
        '600309': '万华化学', '600519': '贵州茅台', '600585': '海螺水泥',
        '600690': '海尔智家', '600887': '伊利股份', '600900': '长江电力',
        '601012': '隆基绿能', '601088': '中国神华', '601166': '兴业银行',
        '601318': '中国平安', '601398': '工商银行', '601628': '中国人寿',
        '601857': '中国石油', '601888': '中国中免', '603259': '药明康德',
    }

    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.translator = translator
        self.setWindowTitle(self._t("dialog.add_stock.title", "添加股票"))
        self.setFixedSize(350, 180)
        self._official_source_enabled = config_manager.get("data_source", "akshare") in {"akshare", "tushare"}
        self._data_manager = None
        self._official_stock_cache = {}
        self._official_cache_loaded = False
        self._builtin_cache = {}
        self._builtin_provider = None
        self._builtin_provider_error = ""
        self._data_source_available = self._official_source_enabled
        self._data_fetch_error = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText(self._t("dialog.add_stock.placeholder_code", "输入6位股票代码，如 600000"))
        self.code_edit.textChanged.connect(self.on_code_changed)
        form_layout.addRow(self._t("dialog.add_stock.code", "股票代码:"), self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self._t("dialog.add_stock.placeholder_name", "股票名称"))
        form_layout.addRow(self._t("dialog.add_stock.name", "股票名称:"), self.name_edit)

        layout.addLayout(form_layout)

        # 提示标签
        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.hint_label)

        layout.addStretch()

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def on_code_changed(self, text):
        """股票代码变化时自动填充名称"""
        raw_code = text.strip()
        code = normalize_stock_code(raw_code)
        if not code:
            self.hint_label.setText("")
            return

        if code in self.COMMON_STOCKS:
            self.name_edit.setText(self.COMMON_STOCKS[code])
            self.hint_label.setText(self._t("dialog.add_stock.hint_auto", "已自动识别股票名称"))
        elif len(code) == 6 and code.isdigit():
            name, source = self._resolve_stock_name(code)
            if name:
                self.name_edit.setText(name)
                if source == "official":
                    hint = self._t("dialog.add_stock.hint_remote_success", "已根据实时数据源匹配股票名称")
                else:
                    hint = self._t("dialog.add_stock.hint_local_success", "已通过内置接口匹配股票名称")
                self.hint_label.setText(hint)
            else:
                if self._official_source_enabled and not self._data_source_available:
                    hint = self._t("dialog.add_stock.hint_remote_fail", "实时数据源暂不可用，请手动输入名称")
                    reason = self._data_fetch_error or self._builtin_provider_error
                    if reason:
                        hint = f"{hint} ({reason})"
                else:
                    hint = self._t("dialog.add_stock.hint_manual", "未找到股票，请手动输入名称")
                self.hint_label.setText(hint)
        else:
            self.hint_label.setText("")

    def get_stock_code(self):
        return normalize_stock_code(self.code_edit.text().strip()).upper()

    def get_stock_name(self):
        return self.name_edit.text().strip()

    def _t(self, key, fallback=""):
        if self.translator:
            return self.translator.translate(key, fallback)
        return fallback or key

    def _resolve_stock_name(self, normalized: str):
        """综合判断使用官方数据源或内置接口"""
        if not normalized or len(normalized) != 6:
            return None, None

        official_name = self._lookup_official_stock_name(normalized)
        if official_name:
            self._data_source_available = True
            self._data_fetch_error = ""
            return official_name, "official"

        builtin_name = self._lookup_builtin_stock_name(normalized)
        if builtin_name:
            return builtin_name, "builtin"

        return None, None

    def _lookup_official_stock_name(self, normalized: str):
        if not self._official_source_enabled:
            return None

        manager = self._ensure_data_manager()
        if manager is None:
            return None

        try:
            if not self._official_cache_loaded:
                df = manager.get_stock_list()
                if df is None or df.empty:
                    self._data_source_available = False
                    return None
                code_col = "代码" if "代码" in df.columns else ("code" if "code" in df.columns else None)
                name_col = "名称" if "名称" in df.columns else ("name" if "name" in df.columns else None)
                if not code_col or not name_col:
                    self._data_source_available = False
                    return None

                cache = {}
                for _, row in df.iterrows():
                    raw_code = str(row[code_col]).strip()
                    name = str(row[name_col]).strip()
                    plain = normalize_stock_code(raw_code)
                    if not name or not plain:
                        continue
                    for key in self._build_lookup_keys(raw_code, plain):
                        cache[key] = name
                self._official_stock_cache = cache
                self._official_cache_loaded = True

            for key in self._build_lookup_keys(normalized, normalized):
                cached = self._official_stock_cache.get(key)
                if cached:
                    return cached
            return None
        except Exception as err:
            self._data_source_available = False
            self._data_fetch_error = str(err)
            return None

    def _lookup_builtin_stock_name(self, normalized: str):
        for key in self._build_lookup_keys(normalized, normalized):
            cached = self._builtin_cache.get(key)
            if cached:
                return cached

        provider = self._ensure_builtin_provider()
        if provider:
            try:
                prefixed = add_market_prefix(normalized)
                quotes = provider.get_realtime_quotes([prefixed])
                record = (
                    quotes.get(prefixed)
                    or quotes.get(prefixed.lower())
                    or quotes.get(prefixed.upper())
                    or quotes.get(normalized)
                )
                if record and record.name:
                    name = record.name.strip()
                    if name:
                        for key in self._build_lookup_keys(prefixed, normalized):
                            self._builtin_cache[key] = name
                        self._builtin_provider_error = ""
                        return name
            except Exception as err:
                self._builtin_provider_error = str(err)

        return self.COMMON_STOCKS.get(normalized)

    def _build_lookup_keys(self, raw_code: str, normalized: str):
        keys = {
            (raw_code or "").strip().lower(),
            normalized.lower() if normalized else "",
            add_market_prefix(normalized).lower() if normalized else "",
        }
        return {k for k in keys if k}

    def _ensure_builtin_provider(self):
        if self._builtin_provider is None:
            try:
                self._builtin_provider = ChinaStockProvider()
                self._builtin_provider_error = ""
            except Exception as err:
                self._builtin_provider_error = str(err)
                self._builtin_provider = None
        return self._builtin_provider
    def _ensure_data_manager(self):
        """惰性创建数据管理器"""
        if not self._official_source_enabled:
            return None
        if self._data_manager is None:
            try:
                source = config_manager.get("data_source", "akshare")
                token = config_manager.get("tushare_token", "")
                self._data_manager = DataSourceManager(source=source, token=token)
                self._data_source_available = True
                self._data_fetch_error = ""
            except Exception as err:
                self._data_source_available = False
                self._data_fetch_error = str(err)
                self._data_manager = None
        return self._data_manager
