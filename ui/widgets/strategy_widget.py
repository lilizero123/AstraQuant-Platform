"""
策略编辑组件
支持代码模式和蓝图可视化模式
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox, QSplitter,
    QListWidget, QGroupBox, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QMessageBox, QStackedWidget,
    QButtonGroup, QRadioButton, QFrame,
    QListWidgetItem, QInputDialog, QScrollArea, QDialog,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
import re
import os
from pathlib import Path

from core.strategy.strategy_manager import StrategyManager
from core.assistant.ai_helper import AIHelper


class PythonHighlighter(QSyntaxHighlighter):
    """Python语法高亮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # 关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(86, 156, 214))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
            'global', 'if', 'import', 'in', 'is', 'lambda', 'not', 'or',
            'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
            'True', 'False', 'None'
        ]
        for word in keywords:
            pattern = f'\\b{word}\\b'
            self.highlighting_rules.append((re.compile(pattern), keyword_format))

        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(206, 145, 120))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(106, 153, 85))
        self.highlighting_rules.append((re.compile(r'#.*'), comment_format))

        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(181, 206, 168))
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*\b'), number_format))

        # 函数
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(220, 220, 170))
        self.highlighting_rules.append((re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\()'), function_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class StrategyCreateDialog(QDialog):
    """新建策略对话框，允许选择模板"""

    def __init__(self, parent, template_entries, existing_names, initial_key=None):
        super().__init__(parent)
        self.setWindowTitle("新建策略")
        self._existing_names = {name.lower() for name in existing_names}
        self.edit_name = QLineEdit("我的策略")
        self.template_combo = QComboBox()
        for label, key in template_entries:
            self.template_combo.addItem(label, key)
        if initial_key is not None:
            index = self.template_combo.findData(initial_key)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("策略名称:", self.edit_name)
        form.addRow("创建自模板:", self.template_combo)
        layout.addLayout(form)

        hint = QLabel("选择模板后代码会自动填充，空白模板将提供完全空白的编辑区。")
        hint.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "策略名称不能为空")
            return
        if name.lower() in self._existing_names:
            QMessageBox.warning(self, "提示", f'策略 "{name}" 已存在，请输入其他名称')
            return
        super().accept()

    def get_result(self):
        """返回名称与模板键"""
        return self.edit_name.text().strip(), self.template_combo.currentData()


class StrategyWidget(QWidget):
    """策略编辑组件 - 支持代码模式和蓝图模式"""

    strategies_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.blueprint_widget = None  # 延迟加载
        self.strategy_manager = StrategyManager()  # 策略管理器
        self.current_strategy_name = None  # 当前策略名称
        self.ai_helper = AIHelper()
        self.init_ui()
        self._load_strategy_list()  # 加载策略列表

    def reload_config(self):
        """重新载入 AI/配置"""
        if hasattr(self, "ai_helper"):
            self.ai_helper.reload_config()

    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 模式切换栏
        mode_bar = self._create_mode_bar()
        main_layout.addWidget(mode_bar)

        # 堆叠组件 (代码模式 / 蓝图模式)
        self.stack = QStackedWidget()

        # 代码模式
        code_widget = self._create_code_mode()
        self.stack.addWidget(code_widget)

        # 蓝图模式 (延迟加载)
        self.blueprint_placeholder = QWidget()
        self.stack.addWidget(self.blueprint_placeholder)

        main_layout.addWidget(self.stack)

    def _create_mode_bar(self) -> QWidget:
        """创建模式切换栏"""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)

        # 标题
        title = QLabel("策略编辑器")
        title.setStyleSheet("color: #e6edf3; font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        layout.addStretch()

        # 模式切换按钮
        self.btn_code_mode = QPushButton("代码模式")
        self.btn_code_mode.setCheckable(True)
        self.btn_code_mode.setChecked(True)
        self.btn_code_mode.clicked.connect(lambda: self._switch_mode(0))

        self.btn_blueprint_mode = QPushButton("蓝图模式")
        self.btn_blueprint_mode.setCheckable(True)
        self.btn_blueprint_mode.clicked.connect(lambda: self._switch_mode(1))

        btn_style = """
            QPushButton {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #e6edf3;
            }
            QPushButton:checked {
                background-color: #238636;
                color: #ffffff;
                border-color: #238636;
            }
        """
        self.btn_code_mode.setStyleSheet(btn_style)
        self.btn_blueprint_mode.setStyleSheet(btn_style)

        layout.addWidget(self.btn_code_mode)
        layout.addWidget(self.btn_blueprint_mode)

        return bar

    def _switch_mode(self, mode: int):
        """切换模式"""
        if mode == 0:
            # 代码模式
            self.btn_code_mode.setChecked(True)
            self.btn_blueprint_mode.setChecked(False)
            self.stack.setCurrentIndex(0)
        else:
            # 蓝图模式
            self.btn_code_mode.setChecked(False)
            self.btn_blueprint_mode.setChecked(True)

            # 延迟加载蓝图组件
            if self.blueprint_widget is None:
                self._load_blueprint_widget()

            self.stack.setCurrentIndex(1)

    def _load_blueprint_widget(self):
        """延迟加载蓝图组件"""
        try:
            from ..blueprint import BlueprintWidget
            self.blueprint_widget = BlueprintWidget()
            self.blueprint_widget.code_generated.connect(self._on_blueprint_code_generated)

            # 替换占位符
            self.stack.removeWidget(self.blueprint_placeholder)
            self.stack.addWidget(self.blueprint_widget)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"无法加载蓝图编辑器: {str(e)}")

    def _on_blueprint_code_generated(self, code: str):
        """蓝图生成代码后应用到代码编辑器"""
        self.code_editor.setPlainText(code)
        self._switch_mode(0)  # 切换到代码模式
        QMessageBox.information(self, "提示", "代码已应用到编辑器")

    def _create_code_mode(self) -> QWidget:
        """创建代码模式界面"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # 左侧 - 策略列表和模板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 策略列表
        list_group = QGroupBox("策略列表")
        list_layout = QVBoxLayout(list_group)
        self.strategy_list = QListWidget()
        self.strategy_list.addItems([
            "双均线策略",
            "MACD策略",
            "布林带策略",
            "海龟交易策略",
        ])
        self.strategy_list.itemClicked.connect(self.load_strategy)
        list_layout.addWidget(self.strategy_list)

        btn_layout = QHBoxLayout()
        btn_new = QPushButton("新建")
        btn_new.clicked.connect(self.new_strategy)
        btn_delete = QPushButton("删除")
        btn_delete.clicked.connect(self.delete_strategy)
        btn_layout.addWidget(btn_new)
        btn_layout.addWidget(btn_delete)
        list_layout.addLayout(btn_layout)

        left_layout.addWidget(list_group)

        # 策略模板
        template_group = QGroupBox("策略模板")
        template_layout = QVBoxLayout(template_group)
        self.template_combo = QComboBox()
        self._refresh_template_combo()
        template_layout.addWidget(self.template_combo)
        btn_use_template = QPushButton("使用模板")
        btn_use_template.clicked.connect(self.use_template)
        template_layout.addWidget(btn_use_template)
        left_layout.addWidget(template_group)

        left_layout.addStretch()

        # 中间 - 代码编辑器
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)

        editor_label = QLabel("策略代码")
        editor_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        middle_layout.addWidget(editor_label)

        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Consolas", 11))
        self.code_editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        self.code_editor.setPlaceholderText("在此编辑策略代码，保存后可在回测和交易中使用")
        self.highlighter = PythonHighlighter(self.code_editor.document())
        self.code_editor.setPlainText(self.get_default_code())
        middle_layout.addWidget(self.code_editor)

        # 按钮栏
        btn_bar = QHBoxLayout()
        btn_save = QPushButton("保存策略")
        btn_save.clicked.connect(self.save_strategy)
        btn_check = QPushButton("语法检查")
        btn_check.clicked.connect(self.check_syntax)
        btn_run = QPushButton("运行回测")
        btn_run.clicked.connect(self.run_backtest)
        btn_bar.addWidget(btn_save)
        btn_bar.addWidget(btn_check)
        btn_bar.addWidget(btn_run)
        btn_bar.addStretch()
        middle_layout.addLayout(btn_bar)

        # 右侧 - 参数配置（带滚动）
        right_panel = QWidget()
        right_main_layout = QVBoxLayout(right_panel)
        right_main_layout.setContentsMargins(0, 0, 0, 0)

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
        right_layout = QVBoxLayout(scroll_content)

        param_group = QGroupBox("策略参数")
        param_layout = QFormLayout(param_group)

        self.param_fast_period = QSpinBox()
        self.param_fast_period.setRange(1, 100)
        self.param_fast_period.setValue(5)
        param_layout.addRow("快线周期:", self.param_fast_period)

        self.param_slow_period = QSpinBox()
        self.param_slow_period.setRange(1, 200)
        self.param_slow_period.setValue(20)
        param_layout.addRow("慢线周期:", self.param_slow_period)

        self.param_stop_loss = QDoubleSpinBox()
        self.param_stop_loss.setRange(0, 100)
        self.param_stop_loss.setValue(5.0)
        self.param_stop_loss.setSuffix("%")
        param_layout.addRow("止损比例:", self.param_stop_loss)

        self.param_take_profit = QDoubleSpinBox()
        self.param_take_profit.setRange(0, 100)
        self.param_take_profit.setValue(10.0)
        self.param_take_profit.setSuffix("%")
        param_layout.addRow("止盈比例:", self.param_take_profit)

        self.btn_ai_params = QPushButton("AI参数建议")
        self.btn_ai_params.clicked.connect(self.apply_ai_parameters)
        param_layout.addRow("", self.btn_ai_params)

        right_layout.addWidget(param_group)

        # 风控设置
        risk_group = QGroupBox("风控设置")
        risk_layout = QFormLayout(risk_group)

        self.param_max_position = QDoubleSpinBox()
        self.param_max_position.setRange(0, 100)
        self.param_max_position.setValue(30.0)
        self.param_max_position.setSuffix("%")
        risk_layout.addRow("最大仓位:", self.param_max_position)

        self.param_max_drawdown = QDoubleSpinBox()
        self.param_max_drawdown.setRange(0, 100)
        self.param_max_drawdown.setValue(20.0)
        self.param_max_drawdown.setSuffix("%")
        risk_layout.addRow("最大回撤:", self.param_max_drawdown)

        right_layout.addWidget(risk_group)

        self._param_widgets = {
            "fast_period": self.param_fast_period,
            "slow_period": self.param_slow_period,
            "stop_loss": self.param_stop_loss,
            "take_profit": self.param_take_profit,
            "max_position": self.param_max_position,
            "max_drawdown": self.param_max_drawdown,
        }
        self._param_defaults = {
            key: self._get_param_value(widget)
            for key, widget in self._param_widgets.items()
        }

        # AI 策略助手
        ai_group = QGroupBox("AI策略助手")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(6)

        prompt_label = QLabel("需求描述")
        prompt_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        ai_layout.addWidget(prompt_label)

        self.ai_prompt = QTextEdit()
        self.ai_prompt.setPlaceholderText("例如：想要MACD顺势策略，加入止损")
        self.ai_prompt.setFixedHeight(80)
        ai_layout.addWidget(self.ai_prompt)

        ai_btns = QHBoxLayout()
        self.btn_ai_generate = QPushButton("AI生成策略")
        self.btn_ai_generate.clicked.connect(self.generate_strategy_with_ai)
        self.btn_ai_review = QPushButton("AI代码诊断")
        self.btn_ai_review.clicked.connect(self.review_strategy_with_ai)
        ai_btns.addWidget(self.btn_ai_generate)
        ai_btns.addWidget(self.btn_ai_review)
        ai_layout.addLayout(ai_btns)

        result_label = QLabel("AI建议")
        result_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        ai_layout.addWidget(result_label)

        self.ai_response = QTextEdit()
        self.ai_response.setReadOnly(True)
        self.ai_response.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #30363d;
            }
        """)
        self.ai_response.setFixedHeight(140)
        ai_layout.addWidget(self.ai_response)

        right_layout.addWidget(ai_group)
        right_layout.addStretch()

        # 将内容设置到滚动区域
        scroll_area.setWidget(scroll_content)
        right_main_layout.addWidget(scroll_area)

        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(middle_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 600, 200])

        layout.addWidget(splitter)

        return widget

    def _template_entries(self):
        """模板选项列表"""
        entries = [("空白模板", "__blank__")]
        templates = self.strategy_manager.get_templates()
        for name in templates.keys():
            entries.append((name, name))
        return entries

    def _select_template_in_combo(self, key: str):
        """在下拉框内选中指定模板"""
        if key is None:
            return
        index = self.template_combo.findData(key)
        if index >= 0:
            self.template_combo.blockSignals(True)
            self.template_combo.setCurrentIndex(index)
            self.template_combo.blockSignals(False)

    @staticmethod
    def _base_name(text: str) -> str:
        """去掉(未保存)等后缀"""
        if not text:
            return ""
        return text.split(" (", 1)[0].strip()

    def _find_strategy_row(self, name: str) -> int:
        """查找策略在列表中的行号"""
        if not name:
            return -1
        for row in range(self.strategy_list.count()):
            item = self.strategy_list.item(row)
            if item and self._base_name(item.text()) == name:
                return row
        return -1

    def _list_existing_names(self):
        """获取当前列表中的策略名称集合"""
        names = set()
        for row in range(self.strategy_list.count()):
            item = self.strategy_list.item(row)
            if item:
                names.add(self._base_name(item.text()))
        return names

    def _get_param_value(self, widget):
        """统一读取参数控件的值"""
        if isinstance(widget, QSpinBox):
            return int(widget.value())
        if isinstance(widget, QDoubleSpinBox):
            return float(widget.value())
        return widget.value()

    def _set_param_value(self, widget, value):
        """设置参数控件的值"""
        if isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))

    def _collect_parameters(self) -> dict:
        """收集当前参数面板的值"""
        params = {}
        for key, widget in self._param_widgets.items():
            params[key] = self._get_param_value(widget)
        return params

    def _apply_parameters(self, params=None):
        """根据存储值刷新参数面板"""
        params = params or {}
        for key, widget in self._param_widgets.items():
            value = params.get(key, self._param_defaults.get(key))
            if value is not None:
                self._set_param_value(widget, value)

    def _load_strategy_list(self):
        """加载策略列表"""
        target_name = self.current_strategy_name
        self.strategy_list.clear()

        templates = self.strategy_manager.get_templates()
        for name in templates.keys():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, "template")
            self.strategy_list.addItem(item)

        strategies = self.strategy_manager.get_all_strategies()
        for strategy in strategies:
            if strategy.name not in templates:
                item = QListWidgetItem(strategy.name)
                item.setData(Qt.UserRole, "saved")
                self.strategy_list.addItem(item)

        if target_name:
            row = self._find_strategy_row(target_name)
            if row >= 0:
                self.strategy_list.setCurrentRow(row)

    def _refresh_template_combo(self):
        """刷新策略模板下拉框"""
        current_data = self.template_combo.currentData()
        self.template_combo.clear()
        for label, key in self._template_entries():
            self.template_combo.addItem(label, key)
        if current_data:
            index = self.template_combo.findData(current_data)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)

    def get_default_code(self):
        """获取默认代码"""
        return '''"""
双均线交叉策略
当快线上穿慢线时买入，下穿时卖出
"""
from core.strategy.base import BaseStrategy


class DualMAStrategy(BaseStrategy):
    """双均线策略"""

    # 策略参数
    fast_period = 5   # 快线周期
    slow_period = 20  # 慢线周期

    def __init__(self):
        super().__init__()
        self.fast_ma = None
        self.slow_ma = None

    def on_bar(self, bar):
        """K线数据回调"""
        # 计算均线
        closes = self.get_close_prices(self.slow_period + 1)
        if len(closes) < self.slow_period:
            return

        self.fast_ma = sum(closes[-self.fast_period:]) / self.fast_period
        self.slow_ma = sum(closes[-self.slow_period:]) / self.slow_period

        # 交易逻辑
        if self.position == 0:
            # 无持仓，判断是否买入
            if self.fast_ma > self.slow_ma:
                self.buy(bar.close, 100)
        else:
            # 有持仓，判断是否卖出
            if self.fast_ma < self.slow_ma:
                self.sell(bar.close, self.position)

    def on_order(self, order):
        """订单回调"""
        self.log(f"订单成交: {order}")

    def on_trade(self, trade):
        """成交回调"""
        self.log(f"成交: {trade}")
'''

    def _get_blank_template_code(self) -> str:
        """空白模板代码"""
        return ""

    def _remove_draft_items(self):
        """移除未保存草稿"""
        for row in range(self.strategy_list.count() - 1, -1, -1):
            item = self.strategy_list.item(row)
            if item and item.data(Qt.UserRole) == "draft":
                self.strategy_list.takeItem(row)

    def new_strategy(self):
        """新建策略"""
        dialog = StrategyCreateDialog(
            self,
            self._template_entries(),
            self._list_existing_names(),
            initial_key=self.template_combo.currentData()
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        name, template_key = dialog.get_result()
        if not name:
            return

        self._remove_draft_items()
        draft_item = QListWidgetItem(f"{name} (未保存)")
        draft_item.setData(Qt.UserRole, "draft")
        self.strategy_list.insertItem(0, draft_item)
        self.strategy_list.setCurrentItem(draft_item)

        self.current_strategy_name = name
        self.use_template(template_key)
        QMessageBox.information(
            self,
            "提示",
            f'已创建策略 "{name}" 草稿，请编辑后保存。'
        )

    def load_strategy(self, item):
        """加载策略"""
        if item is None:
            return
        item_type = item.data(Qt.UserRole) or "saved"
        name = self._base_name(item.text())

        if item_type == "draft":
            self.current_strategy_name = name
            return

        if item_type == "template":
            self._select_template_in_combo(name)
            code = self.strategy_manager.get_template(name)
            if code:
                self.code_editor.setPlainText(code)
                self._apply_parameters()
                self.current_strategy_name = None
            return

        strategy_info = self.strategy_manager.load_strategy(name)
        if strategy_info:
            self.code_editor.setPlainText(strategy_info.code)
            self.current_strategy_name = name
            self._apply_parameters(strategy_info.parameters)

    def delete_strategy(self):
        """删除策略"""
        current = self.strategy_list.currentItem()
        if current:
            name = current.text()
            base_name = self._base_name(name)
            item_type = current.data(Qt.UserRole)

            if item_type == "template":
                QMessageBox.warning(self, "提示", "内置模板不能删除")
                return

            if item_type == "draft":
                reply = QMessageBox.question(
                    self, '确认删除',
                    f'确定要放弃草稿 "{base_name}" 吗？',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.strategy_list.takeItem(self.strategy_list.row(current))
                    if self.current_strategy_name == base_name:
                        self.current_strategy_name = None
                    QMessageBox.information(self, "提示", "已移除未保存草稿")
                return

            reply = QMessageBox.question(
                self, '确认删除',
                f'确定要删除策略 "{base_name}" 吗？',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.strategy_manager.delete_strategy(base_name):
                    self.strategy_list.takeItem(self.strategy_list.row(current))
                    if self.current_strategy_name == base_name:
                        self.current_strategy_name = None
                    QMessageBox.information(self, "提示", "策略删除成功")
                    self.strategies_changed.emit()
                else:
                    QMessageBox.warning(self, "错误", "策略删除失败")

    def use_template(self, template_key=None) -> bool:
        """使用模板"""
        if template_key is None:
            template_key = self.template_combo.currentData()
        if template_key is None:
            QMessageBox.warning(self, "提示", "请选择要使用的模板")
            return False
        self._select_template_in_combo(template_key)

        if template_key == "__blank__":
            self.code_editor.clear()
            self._apply_parameters()
            return True

        code = self.strategy_manager.get_template(template_key)
        if code:
            self.code_editor.setPlainText(code)
            self._apply_parameters()
            return True

        QMessageBox.warning(self, "提示", "未找到该模板，已加载默认策略。")
        self.code_editor.setPlainText(self.get_default_code())
        self._apply_parameters()
        return False

    def save_strategy(self):
        """保存策略"""
        code = self.code_editor.toPlainText()
        params = self._collect_parameters()

        # 验证代码
        is_valid, error = self.strategy_manager.validate_strategy(code)
        if not is_valid:
            QMessageBox.warning(self, "验证失败", error)
            return

        # 获取策略名称
        if self.current_strategy_name:
            name = self.current_strategy_name
        else:
            name, ok = QInputDialog.getText(
                self, "保存策略", "请输入策略名称:",
                text="我的策略"
            )
            if not ok or not name.strip():
                return
            name = name.strip()
            existing = self._list_existing_names()
            if name.lower() in {n.lower() for n in existing}:
                QMessageBox.warning(self, "提示", f'策略 "{name}" 已存在，请换一个名称')
                return

        # 保存策略
        if self.strategy_manager.save_strategy(name, code, parameters=params):
            self.current_strategy_name = name
            # 刷新列表
            self._load_strategy_list()
            QMessageBox.information(self, "提示", f"策略 '{name}' 保存成功！")
            self.strategies_changed.emit()
        else:
            QMessageBox.warning(self, "错误", "策略保存失败")

    def check_syntax(self):
        """语法检查"""
        code = self.code_editor.toPlainText()
        try:
            compile(code, '<string>', 'exec')
            QMessageBox.information(self, "语法检查", "语法检查通过！")
        except SyntaxError as e:
            QMessageBox.warning(self, "语法错误", f"第{e.lineno}行: {e.msg}")

    def run_backtest(self):
        """运行回测"""
        QMessageBox.information(self, "提示", "请切换到回测标签页运行回测")

    def generate_strategy_with_ai(self):
        """调用AI助手生成策略代码"""
        prompt = self.ai_prompt.toPlainText().strip()
        suggestion = self.ai_helper.generate_strategy(prompt or "趋势动量策略")
        self.code_editor.setPlainText(suggestion.code)
        self.ai_response.setPlainText(
            f"{suggestion.title}\n{suggestion.summary}"
        )

    def review_strategy_with_ai(self):
        """使用AI助手对当前代码进行诊断"""
        code = self.get_code().strip()
        if not code:
            QMessageBox.warning(self, "提示", "请先输入策略代码")
            return
        feedback = self.ai_helper.review_strategy(code)
        self.ai_response.setPlainText(feedback)

    def apply_ai_parameters(self):
        """根据模板/提示自动填充参数"""
        hint = self.template_combo.currentText()
        params = self.ai_helper.suggest_parameters(hint)
        self.param_fast_period.setValue(int(params.get("fast_period", self.param_fast_period.value())))
        self.param_slow_period.setValue(int(params.get("slow_period", self.param_slow_period.value())))
        self.param_stop_loss.setValue(float(params.get("stop_loss", self.param_stop_loss.value())))
        self.param_take_profit.setValue(float(params.get("take_profit", self.param_take_profit.value())))
        self.ai_response.setPlainText(params.get("comment", "已更新参数"))

    def get_code(self) -> str:
        """获取当前代码"""
        return self.code_editor.toPlainText()

    def set_code(self, code: str):
        """设置代码"""
        self.code_editor.setPlainText(code)
