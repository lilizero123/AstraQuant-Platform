"""
K线图组件 - 现代化深色主题
支持多种技术指标显示
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QFrame, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QThread
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPixmap
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional, List, Dict

from core.assistant.ai_helper import AIHelper
from core.data.data_source import DataManager as DataSourceManager

# 导入技术指标模块
try:
    from core.indicators import TechnicalIndicators
    HAS_INDICATORS = True
except ImportError:
    HAS_INDICATORS = False


class KLineFetchThread(QThread):
    """后台线程，用于异步加载K线数据，防止阻塞UI"""

    data_ready = pyqtSignal(str, object)
    error = pyqtSignal(str, str)

    def __init__(self, data_manager, code: str, start_date: str, end_date: str):
        super().__init__()
        self._manager = data_manager
        self._code = code
        self._start = start_date
        self._end = end_date

    def run(self):
        try:
            df = self._manager.get_daily_data(self._code, self._start, self._end)
            if df is None or df.empty:
                self.error.emit(self._code, "empty")
            else:
                self.data_ready.emit(self._code, df)
        except Exception as err:  # pragma: no cover - 网络异常
            self.error.emit(self._code, str(err))


class KLineWidget(QWidget):
    """K线图组件"""

    stock_changed = pyqtSignal(str)
    data_loaded = pyqtSignal(bool)

    def __init__(self, translator=None):
        super().__init__()
        self.translator = translator
        self.stock_code = None
        self.kline_data = None
        self.base_data = None
        self.ai_helper = AIHelper()
        self.data_manager = DataSourceManager()
        self.data_fetch_error = ""
        self.history_days = 250
        self._fetch_thread: Optional[KLineFetchThread] = None
        self.init_ui()
        self.apply_translations()

    def set_translator(self, translator):
        self.translator = translator
        self.apply_translations()
        self.canvas.set_translator(translator)

    def apply_translations(self):
        if not self.stock_code:
            self.label_code.setText(self._t("kline.select_stock", "选择股票查看行情"))
        self.period_label.setText(self._t("kline.period_label", "周期"))
        self.indicator_label.setText(self._t("kline.indicator_label", "指标"))
        current_key = self.combo_period.currentData()
        self.combo_period.blockSignals(True)
        self.combo_period.clear()
        for label, key in self._get_period_options():
            self.combo_period.addItem(label, key)
        if current_key is not None:
            index = self.combo_period.findData(current_key)
            if index >= 0:
                self.combo_period.setCurrentIndex(index)
        self.combo_period.blockSignals(False)
        self.canvas.set_translator(self.translator)
        self.canvas.update()

    def _get_period_options(self):
        base = ["日K", "周K", "月K"]
        keys = ["daily", "weekly", "monthly"]
        if self.translator:
            labels = self.translator.translate_list("kline.periods", base)
        else:
            labels = base
        return list(zip(labels, keys))

    def _t(self, key, fallback):
        if self.translator:
            return self.translator.translate(key, fallback)
        return fallback

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 顶部信息栏
        top_bar = QFrame()
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 12, 16, 12)

        # 股票信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.label_code = QLabel(self._t("kline.select_stock", "选择股票查看行情"))
        self.label_code.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        self.label_code.setStyleSheet("color: #e6edf3;")
        info_layout.addWidget(self.label_code)

        # 价格行
        price_layout = QHBoxLayout()
        price_layout.setSpacing(16)

        self.label_price = QLabel("--")
        self.label_price.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        self.label_price.setStyleSheet("color: #e6edf3;")
        price_layout.addWidget(self.label_price)

        self.label_change = QLabel("--")
        self.label_change.setFont(QFont("Microsoft YaHei", 12))
        self.label_change.setStyleSheet("""
            background-color: #21262d;
            padding: 4px 12px;
            border-radius: 4px;
            color: #8b949e;
        """)
        price_layout.addWidget(self.label_change)
        price_layout.addStretch()

        info_layout.addLayout(price_layout)
        top_layout.addLayout(info_layout)
        top_layout.addStretch()

        # 右侧控制区
        control_layout = QHBoxLayout()
        control_layout.setSpacing(12)

        self.period_label = QLabel(self._t("kline.period_label", "周期"))
        self.period_label.setStyleSheet("color: #8b949e;")
        control_layout.addWidget(self.period_label)

        self.combo_period = QComboBox()
        for label, key in self._get_period_options():
            self.combo_period.addItem(label, key)
        self.combo_period.setFixedWidth(80)
        self.combo_period.currentTextChanged.connect(self.on_period_changed)
        control_layout.addWidget(self.combo_period)

        self.indicator_label = QLabel(self._t("kline.indicator_label", "指标"))
        self.indicator_label.setStyleSheet("color: #8b949e;")
        control_layout.addWidget(self.indicator_label)

        self.combo_indicator = QComboBox()
        self.combo_indicator.addItems(["MA", "MACD", "KDJ", "RSI", "BOLL"])
        self.combo_indicator.setFixedWidth(80)
        self.combo_indicator.currentTextChanged.connect(self.on_indicator_changed)
        control_layout.addWidget(self.combo_indicator)

        self.btn_ai_insight = QPushButton("AI点评")
        self.btn_ai_insight.clicked.connect(self.show_ai_quote_insight)
        control_layout.addWidget(self.btn_ai_insight)

        top_layout.addLayout(control_layout)
        layout.addWidget(top_bar)

        # K线绑定区域
        self.canvas = KLineCanvas(translator=self.translator)
        layout.addWidget(self.canvas, 1)

        self.indicator_panel = IndicatorPanel()
        self.indicator_panel.hide()
        layout.addWidget(self.indicator_panel)

        # 底部OHLCV信息栏
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 10, 16, 10)
        bottom_layout.setSpacing(24)

        self.label_open = QLabel("开: --")
        self.label_open.setStyleSheet("color: #8b949e;")
        self.label_high = QLabel("高: --")
        self.label_high.setStyleSheet("color: #8b949e;")
        self.label_low = QLabel("低: --")
        self.label_low.setStyleSheet("color: #8b949e;")
        self.label_close = QLabel("收: --")
        self.label_close.setStyleSheet("color: #8b949e;")
        self.label_volume = QLabel("量: --")
        self.label_volume.setStyleSheet("color: #8b949e;")

        bottom_layout.addWidget(self.label_open)
        bottom_layout.addWidget(self.label_high)
        bottom_layout.addWidget(self.label_low)
        bottom_layout.addWidget(self.label_close)
        bottom_layout.addWidget(self.label_volume)
        bottom_layout.addStretch()

        layout.addWidget(bottom_bar)

        self.ai_quote_box = QTextEdit()
        self.ai_quote_box.setReadOnly(True)
        self.ai_quote_box.setPlaceholderText("点击“AI点评”获取该标的的即时解读")
        self.ai_quote_box.setStyleSheet("""
            QTextEdit {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
            }
        """)
        layout.addWidget(self.ai_quote_box)

    def load_stock(self, code):
        """加载股票数据（异步避免阻塞UI）"""
        self.stock_code = code
        display = code or self._t("kline.select_stock", "选择股票查看行情")
        self.label_code.setText(display)
        if not code:
            self.load_demo_data()
            self._finish_loading(False)
            return
        self._start_fetch_thread(code)

    def load_demo_data(self):
        """加载演示数据"""
        import random
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []

        base_price = 10.0
        for i in range(100):
            date = datetime.now() - timedelta(days=100-i)
            dates.append(date)

            open_price = base_price + random.uniform(-0.5, 0.5)
            close_price = open_price + random.uniform(-0.3, 0.3)
            high_price = max(open_price, close_price) + random.uniform(0, 0.2)
            low_price = min(open_price, close_price) - random.uniform(0, 0.2)
            volume = random.randint(100000, 1000000)

            opens.append(open_price)
            closes.append(close_price)
            highs.append(high_price)
            lows.append(low_price)
            volumes.append(volume)

            base_price = close_price

        demo_df = pd.DataFrame({
            'date': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

        self._apply_loaded_data(demo_df)

    def _start_fetch_thread(self, code: str):
        """创建后台线程加载数据"""
        self._set_loading_state(True, f"{code} 行情加载中…")
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=self.history_days)).strftime("%Y-%m-%d")
        self._cancel_fetch_thread()
        thread = KLineFetchThread(self.data_manager, code, start_date, end_date)
        thread.data_ready.connect(self._on_fetch_success)
        thread.error.connect(self._on_fetch_error)
        self._fetch_thread = thread
        thread.start()

    def _cancel_fetch_thread(self):
        if self._fetch_thread:
            try:
                self._fetch_thread.data_ready.disconnect(self._on_fetch_success)
            except Exception:
                pass
            try:
                self._fetch_thread.error.disconnect(self._on_fetch_error)
            except Exception:
                pass
            self._fetch_thread = None

    def _on_fetch_success(self, code: str, df):
        if code != self.stock_code:
            return
        self._apply_loaded_data(df)
        self._finish_loading(True)

    def _on_fetch_error(self, code: str, message: str):
        if code != self.stock_code:
            return
        self.data_fetch_error = message or ""
        self.load_demo_data()
        self._finish_loading(False)

    def _set_loading_state(self, loading: bool, hint: str = ""):
        """更新加载提示状态"""
        if loading:
            self.label_price.setText("--")
            self.label_change.setText(hint or "加载中...")
            self.label_change.setStyleSheet("""
                background-color: #30363d;
                padding: 4px 12px;
                border-radius: 4px;
                color: #8b949e;
            """)
            self.combo_period.setEnabled(False)
            self.combo_indicator.setEnabled(False)
            self.btn_ai_insight.setEnabled(False)
        else:
            self.combo_period.setEnabled(True)
            self.combo_indicator.setEnabled(True)
            self.btn_ai_insight.setEnabled(True)

    def _finish_loading(self, success: bool):
        self._set_loading_state(False)
        self.data_loaded.emit(success)
        if self.stock_code:
            self.stock_changed.emit(self.stock_code)

    def _apply_loaded_data(self, df: pd.DataFrame):
        """统一处理加载后的数据与界面"""
        required_cols = ["date", "open", "high", "low", "close", "volume"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"缺少必要的行情列: {', '.join(missing)}")

        clean_df = df.copy()
        clean_df = clean_df.sort_values("date")
        clean_df["date"] = pd.to_datetime(clean_df["date"])
        self.base_data = clean_df.reset_index(drop=True)
        self._apply_period_filter(self.combo_period.currentData() or "daily")

    def _update_price_labels(self):
        if self.kline_data is None or self.kline_data.empty:
            return

        last = self.kline_data.iloc[-1]
        prev = self.kline_data.iloc[-2] if len(self.kline_data) > 1 else last
        change = ((last['close'] - prev['close']) / prev['close'] * 100) if prev['close'] else 0
        change_val = last['close'] - prev['close']

        self.label_price.setText(f"{last['close']:.2f}")

        if change >= 0:
            self.label_change.setText(f"+{change_val:.2f}  +{change:.2f}%")
            self.label_change.setStyleSheet("""
                background-color: rgba(239, 83, 80, 0.2);
                padding: 4px 12px;
                border-radius: 4px;
                color: #ef5350;
                font-weight: 500;
            """)
            self.label_price.setStyleSheet("color: #ef5350; font-size: 24px; font-weight: bold;")
        else:
            self.label_change.setText(f"{change_val:.2f}  {change:.2f}%")
            self.label_change.setStyleSheet("""
                background-color: rgba(38, 166, 154, 0.2);
                padding: 4px 12px;
                border-radius: 4px;
                color: #26a69a;
                font-weight: 500;
            """)
            self.label_price.setStyleSheet("color: #26a69a; font-size: 24px; font-weight: bold;")

        self.label_open.setText(f"开: {last['open']:.2f}")
        self.label_high.setText(f"高: {last['high']:.2f}")
        self.label_low.setText(f"低: {last['low']:.2f}")
        self.label_close.setText(f"收: {last['close']:.2f}")
        self.label_volume.setText(f"量: {last['volume']/10000:.0f}万")

    def _update_indicator_panel(self):
        indicator = self.combo_indicator.currentText()
        if self.kline_data is None or self.kline_data.empty:
            self.indicator_panel.hide()
            self.canvas.set_indicator(indicator)
            return

        uses_panel = indicator in {"MACD", "KDJ", "RSI"}
        if uses_panel:
            self.indicator_panel.set_indicator(indicator)
            self.indicator_panel.set_data(self.kline_data)
            self.indicator_panel.show()
        else:
            self.indicator_panel.hide()
        self.canvas.set_indicator(indicator)

    def _apply_period_filter(self, period_key: str):
        if self.base_data is None or self.base_data.empty:
            self.kline_data = self.base_data
        else:
            df = self.base_data.copy()
            df = df.set_index("date")
            if period_key == "weekly":
                agg = df.resample("W").agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum"
                }).dropna().reset_index()
            elif period_key == "monthly":
                agg = df.resample("M").agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum"
                }).dropna().reset_index()
            else:
                agg = self.base_data.copy()
            self.kline_data = agg

        self.canvas.set_data(self.kline_data)
        self._update_price_labels()
        self._update_indicator_panel()

    def show_ai_quote_insight(self):
        """调用AI助手输出行情点评"""
        if self.kline_data is None or self.kline_data.empty:
            self.ai_quote_box.setPlainText("暂无行情数据，无法生成点评。")
            return
        last = self.kline_data.iloc[-1]
        prev = self.kline_data.iloc[-2] if len(self.kline_data) >= 2 else last
        change_pct = (last['close'] - prev['close']) / prev['close'] * 100 if prev['close'] else 0
        text = self.ai_helper.analyze_quote(
            code=self.stock_code or "未选",
            last_price=last['close'],
            change_pct=change_pct,
            volume=last['volume'],
        )
        self.ai_quote_box.setPlainText(text)

    def on_period_changed(self, period):
        """周期改变"""
        key = self.combo_period.currentData()
        if self.base_data is not None and key:
            self._apply_period_filter(key)

    def on_indicator_changed(self, indicator):
        """指标改变"""
        self._update_indicator_panel()


class KLineCanvas(QFrame):
    """K线绑定画布"""

    def __init__(self, translator=None):
        super().__init__()
        self.translator = translator
        self.setMinimumHeight(400)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        self.data = None
        self.indicator = "MA"
        self._buffer: Optional[QPixmap] = None
        self._buffer_size = None
        self._dirty = True
        self._hover_pos: Optional[QPoint] = None
        self._bar_positions: List[Dict[str, float]] = []
        self._chart_area: Optional[Tuple[int, int, int, int]] = None
        self._price_stats: Optional[Tuple[float, float]] = None

    def set_translator(self, translator):
        self.translator = translator
        self._dirty = True

    def set_data(self, data):
        """设置数据"""
        self.data = data
        self._dirty = True
        self.update()

    def set_indicator(self, indicator):
        """设置指标"""
        self.indicator = indicator
        self._dirty = True
        self.update()

    def paintEvent(self, event):
        """绑定事件"""
        super().paintEvent(event)
        if self._buffer is None or self._dirty or self._buffer_size != self.size():
            self._render_buffer()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._buffer:
            painter.drawPixmap(0, 0, self._buffer)
        if self._hover_pos and self.data is not None and not self.data.empty:
            self._draw_crosshair(painter)

    def resizeEvent(self, event):
        self._dirty = True
        super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        if self.data is None or self.data.empty:
            return super().mouseMoveEvent(event)
        pos = event.pos()
        self._hover_pos = pos
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_pos = None
        self.update()
        super().leaveEvent(event)

    def _render_buffer(self):
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return

        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.data is None or len(self.data) == 0:
            painter.setPen(QColor(110, 118, 129))
            painter.setFont(QFont("Microsoft YaHei", 14))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, self._t("kline.select_prompt", "请选择股票查看K线图"))
        else:
            self.draw_klines(painter)

        painter.end()
        self._buffer = pixmap
        self._buffer_size = size
        self._dirty = False

    def _t(self, key, fallback):
        if self.translator:
            return self.translator.translate(key, fallback)
        return fallback

    def draw_klines(self, painter):
        """绘制K线"""
        if self.data is None:
            return

        width = self.width()
        height = self.height()
        margin_left = 60
        margin_right = 20
        margin_top = 30
        margin_bottom = 40

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        price_min = self.data['low'].min() * 0.998
        price_max = self.data['high'].max() * 1.002
        price_range = price_max - price_min

        num_bars = len(self.data)
        bar_width = chart_width / num_bars
        candle_width = bar_width * 0.7
        self._chart_area = (margin_left, margin_top, chart_width, chart_height)
        self._price_stats = (price_max, price_range)
        self._bar_positions = []

        # 绘制网格
        painter.setPen(QPen(QColor(33, 38, 45), 1))
        for i in range(5):
            y = margin_top + chart_height * i / 4
            painter.drawLine(margin_left, int(y), width - margin_right, int(y))

        # 绘制价格标签
        painter.setPen(QColor(139, 148, 158))
        painter.setFont(QFont("Consolas", 10))
        for i in range(5):
            price = price_max - price_range * i / 4
            y = margin_top + chart_height * i / 4
            painter.drawText(5, int(y + 4), f"{price:.2f}")

        # 绘制K线
        for i, (_, row) in enumerate(self.data.iterrows()):
            x = margin_left + i * bar_width + bar_width / 2

            y_open = margin_top + (price_max - row['open']) / price_range * chart_height
            y_close = margin_top + (price_max - row['close']) / price_range * chart_height
            y_high = margin_top + (price_max - row['high']) / price_range * chart_height
            y_low = margin_top + (price_max - row['low']) / price_range * chart_height

            # 颜色 (红涨绿跌 - 中国标准)
            if row['close'] >= row['open']:
                color = QColor(239, 83, 80)   # 红色涨
            else:
                color = QColor(38, 166, 154)  # 绿色跌

            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))

            painter.drawLine(int(x), int(y_high), int(x), int(y_low))

            body_top = min(y_open, y_close)
            body_height = abs(y_close - y_open)
            if body_height < 1:
                body_height = 1
            painter.drawRect(int(x - candle_width/2), int(body_top),
                           int(candle_width), int(body_height))
            self._bar_positions.append({"index": i, "x": float(x)})

        if self.indicator == "MA":
            self.draw_ma(painter, margin_left, margin_top, chart_width, chart_height, price_max, price_range)
        elif self.indicator == "BOLL":
            self.draw_boll(painter, margin_left, margin_top, chart_width, chart_height, price_max, price_range)

    def draw_ma(self, painter, margin_left, margin_top, chart_width, chart_height, price_max, price_range):
        """绘制均线"""
        if len(self.data) < 20:
            return

        num_bars = len(self.data)
        bar_width = chart_width / num_bars
        closes = self.data['close'].values

        if HAS_INDICATORS:
            # 使用技术指标模块
            ma5 = TechnicalIndicators.MA(closes, 5)
            ma10 = TechnicalIndicators.MA(closes, 10)
            ma20 = TechnicalIndicators.MA(closes, 20)
        else:
            # 使用pandas计算
            ma5 = self.data['close'].rolling(5).mean().values
            ma10 = self.data['close'].rolling(10).mean().values
            ma20 = self.data['close'].rolling(20).mean().values

        # MA5 - 黄色
        painter.setPen(QPen(QColor(255, 193, 7), 1.5))
        self.draw_line(painter, ma5, margin_left, margin_top, bar_width, chart_height, price_max, price_range)

        # MA10 - 紫色
        painter.setPen(QPen(QColor(156, 39, 176), 1.5))
        self.draw_line(painter, ma10, margin_left, margin_top, bar_width, chart_height, price_max, price_range)

        # MA20 - 青色
        painter.setPen(QPen(QColor(0, 188, 212), 1.5))
        self.draw_line(painter, ma20, margin_left, margin_top, bar_width, chart_height, price_max, price_range)

        # 绘制图例
        self.draw_legend(painter, margin_left, margin_top - 15, [
            ("MA5", QColor(255, 193, 7)),
            ("MA10", QColor(156, 39, 176)),
            ("MA20", QColor(0, 188, 212))
        ])

    def draw_boll(self, painter, margin_left, margin_top, chart_width, chart_height, price_max, price_range):
        """绘制布林带"""
        if len(self.data) < 20:
            return

        num_bars = len(self.data)
        bar_width = chart_width / num_bars
        closes = self.data['close'].values

        if HAS_INDICATORS:
            boll = TechnicalIndicators.BOLL(closes, 20, 2.0)
            upper = boll.upper
            middle = boll.middle
            lower = boll.lower
        else:
            middle = self.data['close'].rolling(20).mean().values
            std = self.data['close'].rolling(20).std().values
            upper = middle + 2 * std
            lower = middle - 2 * std

        # 上轨 - 黄色
        painter.setPen(QPen(QColor(255, 193, 7), 1.5))
        self.draw_line(painter, upper, margin_left, margin_top, bar_width, chart_height, price_max, price_range)

        # 中轨 - 白色
        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        self.draw_line(painter, middle, margin_left, margin_top, bar_width, chart_height, price_max, price_range)

        # 下轨 - 紫色
        painter.setPen(QPen(QColor(156, 39, 176), 1.5))
        self.draw_line(painter, lower, margin_left, margin_top, bar_width, chart_height, price_max, price_range)

        # 绘制图例
        self.draw_legend(painter, margin_left, margin_top - 15, [
            ("上轨", QColor(255, 193, 7)),
            ("中轨", QColor(200, 200, 200)),
            ("下轨", QColor(156, 39, 176))
        ])

    def draw_legend(self, painter, x, y, items):
        """绘制图例"""
        painter.setFont(QFont("Microsoft YaHei", 9))
        offset = 0
        for name, color in items:
            painter.setPen(QPen(color, 2))
            painter.drawLine(x + offset, y, x + offset + 20, y)
            painter.setPen(QColor(139, 148, 158))
            painter.drawText(x + offset + 25, y + 4, name)
            offset += 70

    def draw_line(self, painter, series, margin_left, margin_top, bar_width, chart_height, price_max, price_range):
        """绘制线条"""
        points = []
        for i, val in enumerate(series):
            if not np.isnan(val):
                x = margin_left + i * bar_width + bar_width / 2
                y = margin_top + (price_max - val) / price_range * chart_height
                points.append((int(x), int(y)))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

    def _draw_crosshair(self, painter: QPainter):
        if not self._chart_area or not self._bar_positions or self._price_stats is None:
            return
        margin_left, margin_top, chart_width, chart_height = self._chart_area
        price_max, price_range = self._price_stats
        pos = self._hover_pos
        if pos is None:
            return
        if not (margin_left <= pos.x() <= margin_left + chart_width and margin_top <= pos.y() <= margin_top + chart_height):
            return

        nearest = min(self._bar_positions, key=lambda item: abs(item["x"] - pos.x()))
        index = nearest["index"]
        if index < 0 or index >= len(self.data):
            return
        row = self.data.iloc[index]

        close_price = row.get("close", 0.0)
        cross_x = nearest["x"]
        cross_y = margin_top + (price_max - close_price) / price_range * chart_height

        painter.setPen(QPen(QColor(90, 108, 134, 200), 1, Qt.DashLine))
        painter.drawLine(int(cross_x), margin_top, int(cross_x), margin_top + chart_height)
        painter.drawLine(margin_left, int(cross_y), margin_left + chart_width, int(cross_y))
        painter.setBrush(QColor(255, 194, 38))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cross_x) - 3, int(cross_y) - 3, 6, 6)

        date_value = row.get("date")
        if hasattr(date_value, "strftime"):
            date_text = date_value.strftime("%Y-%m-%d")
        else:
            date_text = str(date_value)
        change_pct = row.get("pct_change")
        if change_pct is None and index > 0:
            prev_close = self.data.iloc[index - 1].get("close", 0)
            if prev_close:
                change_pct = (close_price - prev_close) / prev_close * 100
        change_text = f"{change_pct:+.2f}%" if change_pct is not None else "--"
        volume_value = row.get("volume", 0)
        volume_text = f"{volume_value/10000:.2f}万" if volume_value else "--"

        lines = [
            f"{date_text}",
            f"开 {row.get('open', 0):.2f}  高 {row.get('high', 0):.2f}",
            f"低 {row.get('low', 0):.2f}  收 {close_price:.2f}",
            f"涨幅 {change_text}  成交量 {volume_text}",
        ]

        painter.setFont(QFont("Microsoft YaHei", 9))
        metrics = painter.fontMetrics()
        width_text = max(metrics.horizontalAdvance(line) for line in lines)
        height_text = metrics.height() * len(lines)
        padding = 8
        info_width = width_text + padding * 2
        info_height = height_text + padding * 2
        info_x = int(cross_x + 12)
        info_y = int(cross_y - info_height - 12)
        if info_x + info_width > margin_left + chart_width:
            info_x = int(cross_x - info_width - 12)
        if info_y < margin_top:
            info_y = int(cross_y + 12)

        painter.setPen(QPen(QColor(70, 80, 96), 1))
        painter.setBrush(QColor(13, 17, 23, 220))
        painter.drawRoundedRect(info_x, info_y, info_width, info_height, 6, 6)
        painter.setPen(QColor(222, 230, 240))
        y_offset = info_y + padding + metrics.ascent()
        for line in lines:
            painter.drawText(info_x + padding, y_offset, line)
            y_offset += metrics.height()


class IndicatorPanel(QFrame):
    """独立指标面板（用于MACD、KDJ、RSI等副图指标）"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(120)
        self.setMaximumHeight(150)
        self.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        self.data = None
        self.indicator = "MACD"

    def set_data(self, data):
        """设置数据"""
        self.data = data
        self.update()

    def set_indicator(self, indicator):
        """设置指标"""
        self.indicator = indicator
        self.update()

    def paintEvent(self, event):
        """绑定事件"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.data is None or len(self.data) == 0:
            return

        if self.indicator == "MACD":
            self.draw_macd(painter)
        elif self.indicator == "KDJ":
            self.draw_kdj(painter)
        elif self.indicator == "RSI":
            self.draw_rsi(painter)

    def draw_macd(self, painter):
        """绘制MACD指标"""
        if not HAS_INDICATORS or len(self.data) < 35:
            return

        width = self.width()
        height = self.height()
        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 20

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        closes = self.data['close'].values
        macd_result = TechnicalIndicators.MACD(closes, 12, 26, 9)

        dif = macd_result.dif
        dea = macd_result.dea
        macd = macd_result.macd

        # 计算范围
        valid_dif = dif[~np.isnan(dif)]
        valid_dea = dea[~np.isnan(dea)]
        valid_macd = macd[~np.isnan(macd)]

        if len(valid_macd) == 0:
            return

        all_values = np.concatenate([valid_dif, valid_dea, valid_macd])
        val_max = np.max(all_values) * 1.1
        val_min = np.min(all_values) * 1.1
        val_range = val_max - val_min if val_max != val_min else 1

        num_bars = len(self.data)
        bar_width = chart_width / num_bars

        # 绘制零轴
        zero_y = margin_top + (val_max - 0) / val_range * chart_height
        painter.setPen(QPen(QColor(48, 54, 61), 1))
        painter.drawLine(margin_left, int(zero_y), width - margin_right, int(zero_y))

        # 绘制MACD柱状图
        for i, val in enumerate(macd):
            if np.isnan(val):
                continue
            x = margin_left + i * bar_width + bar_width / 2
            y = margin_top + (val_max - val) / val_range * chart_height

            if val >= 0:
                color = QColor(239, 83, 80)  # 红色
            else:
                color = QColor(38, 166, 154)  # 绿色

            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            painter.drawRect(int(x - bar_width * 0.3), int(min(y, zero_y)),
                           int(bar_width * 0.6), int(abs(y - zero_y)))

        # 绘制DIF线 - 黄色
        painter.setPen(QPen(QColor(255, 193, 7), 1.5))
        self._draw_indicator_line(painter, dif, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制DEA线 - 白色
        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        self._draw_indicator_line(painter, dea, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制标签
        painter.setPen(QColor(139, 148, 158))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(margin_left, margin_top - 5, "MACD(12,26,9)")

    def draw_kdj(self, painter):
        """绘制KDJ指标"""
        if not HAS_INDICATORS or len(self.data) < 15:
            return

        width = self.width()
        height = self.height()
        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 20

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        highs = self.data['high'].values
        lows = self.data['low'].values
        closes = self.data['close'].values

        kdj = TechnicalIndicators.KDJ(highs, lows, closes, 9, 3, 3)

        num_bars = len(self.data)
        bar_width = chart_width / num_bars

        # KDJ范围固定为0-100
        val_max = 100
        val_min = 0
        val_range = 100

        # 绘制超买超卖线
        painter.setPen(QPen(QColor(48, 54, 61), 1, Qt.DashLine))
        y80 = margin_top + (val_max - 80) / val_range * chart_height
        y20 = margin_top + (val_max - 20) / val_range * chart_height
        painter.drawLine(margin_left, int(y80), width - margin_right, int(y80))
        painter.drawLine(margin_left, int(y20), width - margin_right, int(y20))

        # 绘制K线 - 黄色
        painter.setPen(QPen(QColor(255, 193, 7), 1.5))
        self._draw_indicator_line(painter, kdj.k, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制D线 - 蓝色
        painter.setPen(QPen(QColor(88, 166, 255), 1.5))
        self._draw_indicator_line(painter, kdj.d, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制J线 - 紫色
        painter.setPen(QPen(QColor(156, 39, 176), 1.5))
        self._draw_indicator_line(painter, kdj.j, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制标签
        painter.setPen(QColor(139, 148, 158))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(margin_left, margin_top - 5, "KDJ(9,3,3)")

    def draw_rsi(self, painter):
        """绘制RSI指标"""
        if not HAS_INDICATORS or len(self.data) < 20:
            return

        width = self.width()
        height = self.height()
        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 20

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        closes = self.data['close'].values

        rsi6 = TechnicalIndicators.RSI(closes, 6)
        rsi12 = TechnicalIndicators.RSI(closes, 12)
        rsi24 = TechnicalIndicators.RSI(closes, 24)

        num_bars = len(self.data)
        bar_width = chart_width / num_bars

        # RSI范围固定为0-100
        val_max = 100
        val_min = 0
        val_range = 100

        # 绘制超买超卖线
        painter.setPen(QPen(QColor(48, 54, 61), 1, Qt.DashLine))
        y70 = margin_top + (val_max - 70) / val_range * chart_height
        y30 = margin_top + (val_max - 30) / val_range * chart_height
        painter.drawLine(margin_left, int(y70), width - margin_right, int(y70))
        painter.drawLine(margin_left, int(y30), width - margin_right, int(y30))

        # 绘制RSI6 - 黄色
        painter.setPen(QPen(QColor(255, 193, 7), 1.5))
        self._draw_indicator_line(painter, rsi6, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制RSI12 - 蓝色
        painter.setPen(QPen(QColor(88, 166, 255), 1.5))
        self._draw_indicator_line(painter, rsi12, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制RSI24 - 紫色
        painter.setPen(QPen(QColor(156, 39, 176), 1.5))
        self._draw_indicator_line(painter, rsi24, margin_left, margin_top, bar_width, chart_height, val_max, val_range)

        # 绘制标签
        painter.setPen(QColor(139, 148, 158))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(margin_left, margin_top - 5, "RSI(6,12,24)")

    def _draw_indicator_line(self, painter, series, margin_left, margin_top, bar_width, chart_height, val_max, val_range):
        """绘制指标线条"""
        points = []
        for i, val in enumerate(series):
            if not np.isnan(val):
                x = margin_left + i * bar_width + bar_width / 2
                y = margin_top + (val_max - val) / val_range * chart_height
                points.append((int(x), int(y)))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
