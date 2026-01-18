"""
回测组件
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QDateEdit, QDoubleSpinBox, QComboBox,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QSplitter, QTextEdit, QFrame,
    QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QPen

from core.data.data_source import DataManager as DataSourceManager
from core.backtest.engine import BacktestEngine, BacktestResult
from core.strategy.strategy_manager import StrategyManager
from core.strategy.base import OrderSide
from core.assistant.ai_helper import AIHelper
from config.settings import config_manager


class BacktestThread(QThread):
    """回测线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)  # 改为object以传递BacktestResult
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        cfg = config_manager.get_all()
        source = cfg.get("data_source", "akshare")
        token = cfg.get("tushare_token", "")
        try:
            self.data_manager = DataSourceManager(source=source, token=token)
        except ValueError:
            # 回退到默认 AkShare 数据源，避免设置中不受支持的选项导致崩溃
            self.data_manager = DataSourceManager()
        self.strategy_manager = StrategyManager()

    def run(self):
        """运行回测"""
        try:
            self.progress.emit(10)

            # 获取股票代码
            stock_text = self.params['stock']
            parts = stock_text.split()
            if not parts:
                self.error.emit("未能解析股票代码，请重新选择标的")
                return
            stock_code = parts[0]

            # 获取真实K线数据
            self.progress.emit(20)
            df = self.data_manager.get_daily_data(
                stock_code,
                self.params['start_date'],
                self.params['end_date']
            )

            if df is None or df.empty:
                self.error.emit(
                    f"无法获取股票 {stock_code} 的数据，请检查网络连接或股票代码，详细日志见 logs/data.log"
                )
                return

            self.progress.emit(40)

            # 创建回测引擎
            engine = BacktestEngine()
            engine.set_capital(self.params['initial_capital'])
            engine.set_commission(self.params['commission'] / 100)  # 转换为小数
            engine.set_slippage(self.params['slippage'] / 100)

            # 添加数据
            engine.add_data(stock_code, df)

            self.progress.emit(60)

            # 创建策略实例
            strategy_name = self.params['strategy']
            strategy = self.strategy_manager.create_strategy_instance(strategy_name)

            if strategy is None:
                self.error.emit(f"无法加载策略: {strategy_name}")
                return

            engine.set_strategy(strategy)

            self.progress.emit(80)

            # 运行回测
            result = engine.run()

            self.progress.emit(100)
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(f"回测出错: {str(e)}")


class EquityCurve(QFrame):
    """资金曲线图"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setStyleSheet("background-color: #1a1a2e;")
        self.data = None
        self.dates = None  # 存储日期数据
        self.mouse_pos = None  # 鼠标位置
        self.setMouseTracking(True)  # 启用鼠标跟踪

    def set_data(self, data, dates=None):
        """设置数据

        Args:
            data: 资金曲线数据列表
            dates: 日期列表（可选）
        """
        self.data = data
        self.dates = dates
        self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        self.mouse_pos = event.pos()
        self.update()

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.mouse_pos = None
        self.update()

    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.data is None:
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Microsoft YaHei", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "运行回测后显示资金曲线")
            return

        # 绘制资金曲线
        width = self.width()
        height = self.height()
        margin = 40

        min_val = min(self.data)
        max_val = max(self.data)
        val_range = max_val - min_val if max_val != min_val else 1

        # 绘制网格
        painter.setPen(QPen(QColor(50, 50, 70), 1))
        for i in range(5):
            y = margin + (height - 2 * margin) * i / 4
            painter.drawLine(margin, int(y), width - margin, int(y))

        # 绘制曲线
        painter.setPen(QPen(QColor(0, 200, 255), 2))
        points = []
        for i, val in enumerate(self.data):
            x = margin + (width - 2 * margin) * i / (len(self.data) - 1)
            y = margin + (max_val - val) / val_range * (height - 2 * margin)
            points.append((int(x), int(y)))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

        # 绘制十字光标和信息
        if self.mouse_pos and margin <= self.mouse_pos.x() <= width - margin:
            mouse_x = self.mouse_pos.x()
            mouse_y = self.mouse_pos.y()

            # 计算最近的数据点索引
            data_index = int((mouse_x - margin) / (width - 2 * margin) * (len(self.data) - 1))
            data_index = max(0, min(data_index, len(self.data) - 1))

            # 获取对应的数据点坐标
            point_x, point_y = points[data_index]
            value = self.data[data_index]

            # 绘制十字光标
            painter.setPen(QPen(QColor(150, 150, 150, 180), 1, Qt.DashLine))
            # 垂直线
            painter.drawLine(point_x, margin, point_x, height - margin)
            # 水平线
            painter.drawLine(margin, point_y, width - margin, point_y)

            # 绘制数据点高亮
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.setBrush(QColor(255, 255, 0))
            painter.drawEllipse(point_x - 4, point_y - 4, 8, 8)

            # 绘制信息框
            info_text = f"资金: ¥{value:,.2f}"
            if self.dates and data_index < len(self.dates):
                date_str = self.dates[data_index]
                info_text = f"{date_str}\n{info_text}"

            # 计算信息框位置和大小
            painter.setFont(QFont("Microsoft YaHei", 10))
            metrics = painter.fontMetrics()
            lines = info_text.split('\n')
            text_width = max(metrics.horizontalAdvance(line) for line in lines)
            text_height = metrics.height() * len(lines)
            padding = 8

            # 确定信息框位置（避免超出边界）
            info_x = point_x + 15
            info_y = point_y - text_height - padding * 2 - 10

            if info_x + text_width + padding * 2 > width - margin:
                info_x = point_x - text_width - padding * 2 - 15
            if info_y < margin:
                info_y = point_y + 15

            # 绘制信息框背景
            painter.setPen(QPen(QColor(100, 100, 120), 1))
            painter.setBrush(QColor(30, 30, 50, 230))
            painter.drawRoundedRect(
                info_x, info_y,
                text_width + padding * 2,
                text_height + padding * 2,
                5, 5
            )

            # 绘制文本
            painter.setPen(QColor(255, 255, 255))
            y_offset = info_y + padding + metrics.ascent()
            for line in lines:
                painter.drawText(info_x + padding, y_offset, line)
                y_offset += metrics.height()


class BacktestWidget(QWidget):
    """回测组件"""

    def __init__(self):
        super().__init__()
        self.backtest_thread = None
        self.strategy_manager = StrategyManager()
        self.ai_helper = AIHelper()
        self.stock_provider = None
        self._active_stock_code = ""
        self._active_stock_name = ""
        self._active_stock_display = ""
        self._pending_strategy_name = ""
        self.init_ui()

    def reload_config(self):
        """重新载入 AI 相关设置"""
        if hasattr(self, "ai_helper"):
            self.ai_helper.reload_config()

    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

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
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(10)

        # 顶部配置区
        config_layout = QHBoxLayout()

        # 回测参数
        param_group = QGroupBox("回测参数")
        param_layout = QFormLayout(param_group)

        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate().addYears(-1))
        self.date_start.setCalendarPopup(True)
        param_layout.addRow("开始日期:", self.date_start)

        self.date_end = QDateEdit()
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        param_layout.addRow("结束日期:", self.date_end)

        self.initial_capital = QDoubleSpinBox()
        self.initial_capital.setRange(10000, 100000000)
        self.initial_capital.setValue(1000000)
        self.initial_capital.setPrefix("¥")
        self.initial_capital.setSingleStep(100000)
        param_layout.addRow("初始资金:", self.initial_capital)

        config_layout.addWidget(param_group)

        # 交易设置
        trade_group = QGroupBox("交易设置")
        trade_layout = QFormLayout(trade_group)

        self.commission = QDoubleSpinBox()
        self.commission.setRange(0, 1)
        self.commission.setValue(0.0003)
        self.commission.setDecimals(4)
        self.commission.setSuffix("%")
        trade_layout.addRow("手续费率:", self.commission)

        self.slippage = QDoubleSpinBox()
        self.slippage.setRange(0, 10)
        self.slippage.setValue(0.01)
        self.slippage.setSuffix("%")
        trade_layout.addRow("滑点:", self.slippage)

        strategy_selector = QWidget()
        strategy_selector_layout = QHBoxLayout(strategy_selector)
        strategy_selector_layout.setContentsMargins(0, 0, 0, 0)
        self.strategy_combo = QComboBox()
        self.btn_refresh_strategies = QPushButton("刷新")
        self.btn_refresh_strategies.setFixedWidth(60)
        self.btn_refresh_strategies.clicked.connect(self.refresh_strategy_list)
        strategy_selector_layout.addWidget(self.strategy_combo)
        strategy_selector_layout.addWidget(self.btn_refresh_strategies)
        trade_layout.addRow("选择策略:", strategy_selector)

        config_layout.addWidget(trade_group)

        # 股票选择
        stock_group = QGroupBox("回测标的")
        stock_layout = QFormLayout(stock_group)

        self.stock_label = QLabel("请在左侧选择股票")
        self.stock_label.setStyleSheet("color: #e6edf3; font-weight: bold;")
        self.stock_label.setWordWrap(True)
        stock_layout.addRow("当前股票:", self.stock_label)

        self.benchmark_combo = QComboBox()
        self.benchmark_combo.addItems(["000300 沪深300", "000001 上证指数", "399006 创业板指"])
        stock_layout.addRow("基准指数:", self.benchmark_combo)

        config_layout.addWidget(stock_group)

        # 运行按钮
        btn_group = QWidget()
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.addStretch()
        self.btn_run = QPushButton("开始回测")
        self.btn_run.setMinimumHeight(50)
        self.btn_run.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.btn_run.clicked.connect(self.start_backtest)
        btn_layout.addWidget(self.btn_run)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        btn_layout.addWidget(self.progress_bar)
        btn_layout.addStretch()

        config_layout.addWidget(btn_group)

        layout.addLayout(config_layout)

        # 结果区域
        result_splitter = QSplitter(Qt.Vertical)
        result_splitter.setMinimumHeight(800)  # 设置最小高度，确保触发滚动

        # 资金曲线
        curve_group = QGroupBox("资金曲线")
        curve_layout = QVBoxLayout(curve_group)
        self.equity_curve = EquityCurve()
        curve_layout.addWidget(self.equity_curve)
        result_splitter.addWidget(curve_group)

        # 底部区域
        bottom_splitter = QSplitter(Qt.Horizontal)

        # 绩效指标
        metrics_group = QGroupBox("绩效指标")
        metrics_layout = QVBoxLayout(metrics_group)
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["指标", "数值"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.setRowCount(9)
        metrics = [
            "总收益率", "年化收益率", "最大回撤", "夏普比率",
            "胜率", "盈亏比", "总交易次数", "盈利次数", "亏损次数"
        ]
        for i, metric in enumerate(metrics):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(metric))
            self.metrics_table.setItem(i, 1, QTableWidgetItem("--"))
        metrics_layout.addWidget(self.metrics_table)
        bottom_splitter.addWidget(metrics_group)

        # 交易记录
        trades_group = QGroupBox("交易记录")
        trades_layout = QVBoxLayout(trades_group)
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels(["时间", "方向", "价格", "数量", "金额", "盈亏"])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        trades_layout.addWidget(self.trades_table)
        bottom_splitter.addWidget(trades_group)

        result_splitter.addWidget(bottom_splitter)

        # AI 回测点评
        ai_group = QGroupBox("AI回测点评")
        ai_layout = QVBoxLayout(ai_group)
        self.ai_summary = QTextEdit()
        self.ai_summary.setReadOnly(True)
        self.ai_summary.setPlaceholderText("运行回测后，AI会在此给出文字分析")
        self.ai_summary.setStyleSheet("""
            QTextEdit {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        ai_layout.addWidget(self.ai_summary)
        result_splitter.addWidget(ai_group)

        # 设置分割器比例：资金曲线:绩效/交易:AI点评 = 1:4:1
        # 这样绩效/交易区域会占据更大空间
        result_splitter.setSizes([150, 600, 150])

        layout.addWidget(result_splitter)

        # 将内容设置到滚动区域
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # 初始加载策略列表
        self.refresh_strategy_list()
        self.refresh_stock_list()
        self.backtest_thread = None

    def refresh_strategy_list(self):
        """同步策略下拉列表"""
        current = self.strategy_combo.currentText()
        names = self.strategy_manager.get_available_strategy_names()
        has_strategies = bool(names)

        self.strategy_combo.blockSignals(True)
        self.strategy_combo.clear()

        if not has_strategies:
            self.strategy_combo.addItem("暂无策略，请先创建")
            self.strategy_combo.setEnabled(False)
            self.btn_run.setEnabled(False)
            self.btn_run.setToolTip("请先在“策略”页创建并保存策略")
        else:
            self.strategy_combo.addItems(names)
            self.strategy_combo.setEnabled(True)
            self.btn_run.setEnabled(True)
            self.btn_run.setToolTip("")
            target = self._pending_strategy_name or current
            if target in names:
                self.strategy_combo.setCurrentIndex(names.index(target))
                self._pending_strategy_name = ""
        self.strategy_combo.blockSignals(False)

    def set_stock_provider(self, provider):
        """设置股票列表数据源（回调返回 ['000001 平安银行', ...]）"""
        self.stock_provider = provider
        self.refresh_stock_list()

    def refresh_stock_list(self):
        """同步股票下拉列表"""
        items = []

        if callable(self.stock_provider):
            try:
                items = [text for text in self.stock_provider() if text]
            except Exception as err:  # pragma: no cover - UI 日志
                print(f"刷新回测股票列表失败: {err}")

        if not items:
            items = [
                "000001 平安银行",
                "000002 万科A",
                "600000 浦发银行",
                "600036 招商银行",
            ]

        # 兼容旧接口：仅更新提示文本
        display = self._active_stock_display or (items[0] if items else "")
        if display:
            self.stock_label.setText(display)
            self._active_stock_display = display

    def set_active_stock(self, code: str, name: str = ""):
        """锁定当前自选股标的"""
        display = f"{code} {name}".strip() or code
        self._active_stock_code = code
        self._active_stock_name = name
        self._active_stock_display = display
        if hasattr(self, "stock_label"):
            self.stock_label.setText(display or "请在左侧选择股票")

    def export_stock_state(self) -> dict:
        """导出当前回测页面配置"""
        return {
            "start_date": self.date_start.date().toString("yyyy-MM-dd"),
            "end_date": self.date_end.date().toString("yyyy-MM-dd"),
            "initial_capital": self.initial_capital.value(),
            "commission": self.commission.value(),
            "slippage": self.slippage.value(),
            "strategy": self.strategy_combo.currentText().strip() if self.strategy_combo.isEnabled() else "",
            "benchmark": self.benchmark_combo.currentText().strip(),
            "stock": self._active_stock_display,
        }

    def apply_stock_state(self, state: dict):
        """恢复缓存的回测配置"""
        if not isinstance(state, dict):
            return
        start = QDate.fromString(str(state.get("start_date", "")), "yyyy-MM-dd")
        if start.isValid():
            self.date_start.setDate(start)
        end = QDate.fromString(str(state.get("end_date", "")), "yyyy-MM-dd")
        if end.isValid():
            self.date_end.setDate(end)
        if "initial_capital" in state:
            self.initial_capital.setValue(float(state.get("initial_capital", self.initial_capital.value())))
        if "commission" in state:
            self.commission.setValue(float(state.get("commission", self.commission.value())))
        if "slippage" in state:
            self.slippage.setValue(float(state.get("slippage", self.slippage.value())))
        benchmark = state.get("benchmark")
        if benchmark:
            idx = self.benchmark_combo.findText(benchmark)
            if idx >= 0:
                self.benchmark_combo.setCurrentIndex(idx)
        strategy = state.get("strategy")
        if strategy:
            if self.strategy_combo.isEnabled():
                idx = self.strategy_combo.findText(strategy)
                if idx >= 0:
                    self.strategy_combo.setCurrentIndex(idx)
                    self._pending_strategy_name = ""
                else:
                    self._pending_strategy_name = strategy
            else:
                self._pending_strategy_name = strategy
        stock_display = state.get("stock")
        if stock_display:
            self._active_stock_display = stock_display
            if hasattr(self, "stock_label"):
                self.stock_label.setText(stock_display)

    def start_backtest(self):
        """开始回测"""
        if self.backtest_thread and self.backtest_thread.isRunning():
            QMessageBox.information(self, "提示", "回测正在运行，请等待当前任务完成")
            return

        if not self.strategy_combo.isEnabled():
            QMessageBox.warning(self, "提示", "请先在策略管理中创建或保存至少一个策略")
            return

        stock_code = self._active_stock_code.strip()
        stock_name = self._active_stock_name.strip()
        stock_text = f"{stock_code} {stock_name}".strip()
        if not stock_code:
            QMessageBox.warning(self, "提示", "请选择要回测的股票或在左侧自选股中添加标的")
            return

        start_date = self.date_start.date()
        end_date = self.date_end.date()
        if start_date > end_date:
            QMessageBox.warning(self, "提示", "开始日期不能晚于结束日期")
            return

        self.btn_run.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.ai_summary.clear()

        params = {
            'start_date': start_date.toString("yyyy-MM-dd"),
            'end_date': end_date.toString("yyyy-MM-dd"),
            'initial_capital': self.initial_capital.value(),
            'commission': self.commission.value(),
            'slippage': self.slippage.value(),
            'strategy': self.strategy_combo.currentText(),
            'stock': stock_text,
        }

        self.backtest_thread = BacktestThread(params)
        self.backtest_thread.progress.connect(self.on_progress)
        self.backtest_thread.finished.connect(self.on_finished)
        self.backtest_thread.error.connect(self.on_error)
        self.backtest_thread.start()

    def on_progress(self, value):
        """进度更新"""
        self.progress_bar.setValue(value)

    def on_error(self, message):
        """回测出错"""
        self.btn_run.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.ai_summary.setPlainText(f"AI 未生成点评：{message}")
        QMessageBox.warning(self, "回测错误", message)
        self.backtest_thread = None

    def on_finished(self, result: BacktestResult):
        """回测完成"""
        self.btn_run.setEnabled(True)
        self.progress_bar.setVisible(False)

        # 更新绩效指标
        metrics_values = [
            f"{result.total_return:.2f}%",
            f"{result.annual_return:.2f}%",
            f"{result.max_drawdown:.2f}%",
            f"{result.sharpe_ratio:.2f}",
            f"{result.win_rate:.2f}%",
            f"{result.profit_loss_ratio:.2f}",
            str(result.total_trades),
            str(result.win_trades),
            str(result.loss_trades),
        ]
        for i, value in enumerate(metrics_values):
            self.metrics_table.setItem(i, 1, QTableWidgetItem(value))

        # 显示真实资金曲线
        if result.equity_curve:
            # 提取日期数据
            dates = None
            if result.dates:
                dates = [d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d) for d in result.dates]
            self.equity_curve.set_data(result.equity_curve, dates)

        # 显示真实交易记录
        trades = result.trades
        self.trades_table.setRowCount(len(trades))
        for i, trade in enumerate(trades):
            # 时间
            time_str = trade.trade_time.strftime("%Y-%m-%d") if trade.trade_time else "--"
            self.trades_table.setItem(i, 0, QTableWidgetItem(time_str))

            # 方向
            direction = "买入" if trade.side == OrderSide.BUY else "卖出"
            dir_item = QTableWidgetItem(direction)
            dir_item.setForeground(QColor(255, 0, 0) if trade.side == OrderSide.BUY else QColor(0, 255, 0))
            self.trades_table.setItem(i, 1, dir_item)

            # 价格
            self.trades_table.setItem(i, 2, QTableWidgetItem(f"{trade.price:.2f}"))

            # 数量
            self.trades_table.setItem(i, 3, QTableWidgetItem(str(trade.quantity)))

            # 金额
            amount = trade.price * trade.quantity
            self.trades_table.setItem(i, 4, QTableWidgetItem(f"{amount:.2f}"))

            # 手续费
            self.trades_table.setItem(i, 5, QTableWidgetItem(f"{trade.commission:.2f}"))

        # AI 总结
        context = {
            "strategy": self.strategy_combo.currentText(),
            "stock": self._active_stock_display,
        }
        ai_text = self.ai_helper.summarize_backtest(result, context)
        self.ai_summary.setPlainText(ai_text)
        self.backtest_thread = None
