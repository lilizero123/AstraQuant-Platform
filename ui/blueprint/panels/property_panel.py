"""
属性面板
显示和编辑选中节点的属性
"""
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QLineEdit, QCheckBox,
    QFormLayout, QGroupBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal

from ..nodes.base_node import BaseNode
from ..connections.type_system import DataType


class PropertyPanel(QWidget):
    """属性面板 - 显示选中节点的参数，支持编辑"""

    parameter_changed = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_node: Optional[BaseNode] = None
        self._param_widgets: Dict[str, QWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel("属性")
        title.setStyleSheet("""
            QLabel {
                background-color: #161b22;
                color: #e6edf3;
                font-weight: bold;
                font-size: 13px;
                padding: 8px;
                border-bottom: 1px solid #30363d;
            }
        """)
        layout.addWidget(title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: #0d1117; }
            QScrollBar:vertical { background-color: #0d1117; width: 8px; }
            QScrollBar::handle:vertical { background-color: #30363d; border-radius: 4px; }
        """)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(8)

        group_style = """
            QGroupBox {
                color: #e6edf3; font-weight: bold;
                border: 1px solid #30363d; border-radius: 4px;
                margin-top: 8px; padding-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
        """

        # 节点信息组
        self.info_group = QGroupBox("节点信息")
        self.info_group.setStyleSheet(group_style)
        info_layout = QFormLayout(self.info_group)
        info_layout.setContentsMargins(8, 16, 8, 8)

        self.node_type_label = QLabel("-")
        self.node_type_label.setStyleSheet("color: #8b949e;")
        info_layout.addRow("类型:", self.node_type_label)

        self.node_id_label = QLabel("-")
        self.node_id_label.setStyleSheet("color: #8b949e;")
        info_layout.addRow("ID:", self.node_id_label)

        self.content_layout.addWidget(self.info_group)

        # 参数组
        self.param_group = QGroupBox("参数")
        self.param_group.setStyleSheet(group_style)
        self.param_layout = QFormLayout(self.param_group)
        self.param_layout.setContentsMargins(8, 16, 8, 8)
        self.content_layout.addWidget(self.param_group)

        # 输入值组（未连接的端口）
        self.input_group = QGroupBox("输入值")
        self.input_group.setStyleSheet(group_style)
        self.input_layout = QFormLayout(self.input_group)
        self.input_layout.setContentsMargins(8, 16, 8, 8)
        self.content_layout.addWidget(self.input_group)

        # 提示
        self.hint_label = QLabel("选择一个节点查看属性")
        self.hint_label.setStyleSheet("color: #8b949e; padding: 20px;")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.hint_label)

        self.content_layout.addStretch()
        scroll.setWidget(self.content)
        layout.addWidget(scroll)

        self._show_empty_state()

    def _show_empty_state(self):
        self.info_group.hide()
        self.param_group.hide()
        self.input_group.hide()
        self.hint_label.show()

    def _show_node_state(self):
        self.hint_label.hide()
        self.info_group.show()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_node(self, node: Optional[BaseNode]):
        self._current_node = node
        self._param_widgets.clear()
        self._clear_layout(self.param_layout)
        self._clear_layout(self.input_layout)

        if not node:
            self._show_empty_state()
            return

        self._show_node_state()

        # 节点信息
        self.node_type_label.setText(node.CONFIG.title)
        self.node_id_label.setText(node.node_id)

        widget_style = """
            QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #0d1117; color: #e6edf3;
                border: 1px solid #30363d; border-radius: 4px; padding: 4px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus { border-color: #58a6ff; }
        """

        # 参数控件
        param_defs = node.get_parameter_definitions()
        if param_defs:
            self.param_group.show()
            for param_def in param_defs:
                widget = self._create_widget(param_def, node, widget_style)
                if widget:
                    label = QLabel(param_def.get('label', param_def['name']))
                    label.setStyleSheet("color: #8b949e;")
                    self.param_layout.addRow(label, widget)
                    self._param_widgets[param_def['name']] = widget
        else:
            self.param_group.hide()

        # 输入端口值控件（未连接的 NUMBER、BOOLEAN 和 ANY 端口）
        has_inputs = False
        for port_name, port in node.input_ports.items():
            if not port.connections:
                if port.definition.data_type == DataType.NUMBER:
                    has_inputs = True
                    default = port.definition.default_value
                    current = node.parameters.get(f"_input_{port_name}", default if default is not None else 0)

                    widget = QDoubleSpinBox()
                    widget.setStyleSheet(widget_style)
                    widget.setRange(-999999, 999999)
                    widget.setDecimals(2)
                    widget.setValue(float(current) if current is not None else 0)
                    widget.valueChanged.connect(lambda v, n=port_name: self._on_input_changed(n, v))

                    label = QLabel(port.definition.label)
                    label.setStyleSheet("color: #8b949e;")
                    self.input_layout.addRow(label, widget)

                elif port.definition.data_type == DataType.BOOLEAN:
                    has_inputs = True
                    default = port.definition.default_value
                    current = node.parameters.get(f"_input_{port_name}", default if default is not None else False)

                    widget = QCheckBox()
                    widget.setStyleSheet("color: #e6edf3;")
                    widget.setChecked(bool(current) if current is not None else False)
                    widget.stateChanged.connect(lambda v, n=port_name: self._on_input_changed(n, bool(v)))

                    label = QLabel(port.definition.label)
                    label.setStyleSheet("color: #8b949e;")
                    self.input_layout.addRow(label, widget)

                elif port.definition.data_type == DataType.ANY:
                    has_inputs = True
                    default = port.definition.default_value
                    current = node.parameters.get(f"_input_{port_name}", default if default is not None else "")

                    widget = QLineEdit()
                    widget.setStyleSheet(widget_style)
                    widget.setText(str(current) if current is not None else "")
                    widget.setPlaceholderText("输入值...")
                    widget.textChanged.connect(lambda v, n=port_name: self._on_input_changed(n, v))

                    label = QLabel(port.definition.label)
                    label.setStyleSheet("color: #8b949e;")
                    self.input_layout.addRow(label, widget)

        self.input_group.show() if has_inputs else self.input_group.hide()

    def _create_widget(self, param_def: Dict, node: BaseNode, style: str) -> Optional[QWidget]:
        name = param_def['name']
        ptype = param_def.get('type', 'float')
        default = param_def.get('default', 0)
        current = node.parameters.get(name, default)

        if ptype == 'int':
            w = QSpinBox()
            w.setStyleSheet(style)
            w.setRange(param_def.get('min', 0), param_def.get('max', 999999))
            w.setValue(int(current))
            w.valueChanged.connect(lambda v, n=name: self._on_param_changed(n, v))
            return w
        elif ptype == 'float':
            w = QDoubleSpinBox()
            w.setStyleSheet(style)
            w.setRange(param_def.get('min', 0), param_def.get('max', 999999))
            w.setDecimals(2)
            w.setValue(float(current))
            w.valueChanged.connect(lambda v, n=name: self._on_param_changed(n, v))
            return w
        elif ptype == 'str':
            w = QLineEdit()
            w.setStyleSheet(style)
            w.setText(str(current))
            w.textChanged.connect(lambda v, n=name: self._on_param_changed(n, v))
            return w
        elif ptype == 'bool':
            w = QCheckBox()
            w.setStyleSheet("color: #e6edf3;")
            w.setChecked(bool(current))
            w.stateChanged.connect(lambda v, n=name: self._on_param_changed(n, bool(v)))
            return w
        return None

    def _on_param_changed(self, name: str, value: Any):
        if self._current_node:
            self._current_node.parameters[name] = value
            self.parameter_changed.emit(name, value)

    def _on_input_changed(self, port_name: str, value: Any):
        if self._current_node:
            self._current_node.parameters[f"_input_{port_name}"] = value
            self.parameter_changed.emit(f"_input_{port_name}", value)

    def clear(self):
        self.set_node(None)
