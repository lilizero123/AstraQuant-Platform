"""
蓝图节点基类
所有节点类型都继承此基类
"""
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import uuid

from PyQt5.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsDropShadowEffect, QStyleOptionGraphicsItem, QWidget
)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QPainterPath
)

from ..connections.port import Port, PortDefinition, PortDirection
from ..connections.type_system import DataType


@dataclass
class NodeConfig:
    """节点配置"""
    node_type: str           # 节点类型标识 (如 "data.bar", "indicator.ma")
    category: str            # 分类 (如 "数据", "指标", "逻辑")
    title: str               # 显示标题
    description: str = ""    # 描述 (用于工具提示)
    color: str = "#21262d"   # 标题栏颜色
    icon: str = ""           # 图标 (可选)
    width: int = 160         # 节点宽度
    min_height: int = 60     # 最小高度


# 解决ABC和QGraphicsRectItem的元类冲突
class NodeMeta(ABCMeta, type(QGraphicsRectItem)):
    pass


class BaseNode(QGraphicsRectItem, metaclass=NodeMeta):
    """
    节点基类

    所有蓝图节点都继承此类，需要实现:
    - CONFIG: 节点配置
    - INPUT_PORTS: 输入端口定义列表
    - OUTPUT_PORTS: 输出端口定义列表
    - get_parameter_definitions(): 返回参数定义
    - generate_code(): 生成Python代码
    - get_output_expression(): 获取输出端口的代码表达式
    """

    # 子类需要覆盖这些类属性
    CONFIG: NodeConfig = None
    INPUT_PORTS: List[PortDefinition] = []
    OUTPUT_PORTS: List[PortDefinition] = []

    # 端口间距
    PORT_SPACING = 24
    HEADER_HEIGHT = 28
    PORT_START_Y = 36

    def __init__(self, scene_pos: QPointF = None):
        super().__init__()

        # 唯一标识
        self.node_id = str(uuid.uuid4())[:8]

        # 端口字典
        self.input_ports: Dict[str, Port] = {}
        self.output_ports: Dict[str, Port] = {}

        # 参数值
        self.parameters: Dict[str, Any] = {}

        # 选中状态
        self._selected = False

        # 设置交互标志
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        # 初始化外观
        self._setup_visual()
        self._create_ports()
        self._init_parameters()

        # 设置位置
        if scene_pos:
            self.setPos(scene_pos)

    def _setup_visual(self):
        """设置节点外观"""
        config = self.CONFIG

        # 计算高度
        port_count = max(len(self.INPUT_PORTS), len(self.OUTPUT_PORTS))
        height = max(config.min_height, self.PORT_START_Y + port_count * self.PORT_SPACING + 8)

        self.setRect(0, 0, config.width, height)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        # 标题文本
        self.title_item = QGraphicsTextItem(config.title, self)
        self.title_item.setDefaultTextColor(QColor("#e6edf3"))
        self.title_item.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.title_item.setPos(8, 4)

    def _create_ports(self):
        """创建输入输出端口"""
        config = self.CONFIG

        # 创建输入端口 (左侧)
        for i, port_def in enumerate(self.INPUT_PORTS):
            port = Port(port_def, self)
            port.setPos(0, self.PORT_START_Y + i * self.PORT_SPACING)
            self.input_ports[port_def.name] = port

            # 端口标签
            label = QGraphicsTextItem(port_def.label, self)
            label.setDefaultTextColor(QColor("#8b949e"))
            label.setFont(QFont("Microsoft YaHei", 8))
            label.setPos(10, self.PORT_START_Y + i * self.PORT_SPACING - 8)

        # 创建输出端口 (右侧)
        for i, port_def in enumerate(self.OUTPUT_PORTS):
            port = Port(port_def, self)
            port.setPos(config.width, self.PORT_START_Y + i * self.PORT_SPACING)
            self.output_ports[port_def.name] = port

            # 端口标签 (右对齐)
            label = QGraphicsTextItem(port_def.label, self)
            label.setDefaultTextColor(QColor("#8b949e"))
            label.setFont(QFont("Microsoft YaHei", 8))
            text_width = label.boundingRect().width()
            label.setPos(config.width - text_width - 10,
                         self.PORT_START_Y + i * self.PORT_SPACING - 8)

    def _init_parameters(self):
        """初始化参数默认值"""
        for port_def in self.INPUT_PORTS:
            if port_def.default_value is not None:
                self.parameters[port_def.name] = port_def.default_value

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: QWidget = None):
        """绘制节点"""
        rect = self.rect()
        config = self.CONFIG

        # 背景路径 (圆角矩形)
        path = QPainterPath()
        path.addRoundedRect(rect, 6, 6)

        # 渐变背景
        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QColor("#21262d"))
        gradient.setColorAt(1, QColor("#161b22"))
        painter.fillPath(path, gradient)

        # 标题栏
        header_path = QPainterPath()
        header_rect = QRectF(0, 0, rect.width(), self.HEADER_HEIGHT)
        header_path.addRoundedRect(header_rect, 6, 6)
        # 裁剪底部圆角
        clip_rect = QRectF(0, self.HEADER_HEIGHT - 6, rect.width(), 6)
        header_path.addRect(clip_rect)
        painter.fillPath(header_path, QColor(config.color))

        # 边框
        if self.isSelected():
            border_color = QColor("#58a6ff")
            border_width = 2
        else:
            border_color = QColor("#30363d")
            border_width = 1

        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(rect, 6, 6)

    def itemChange(self, change, value):
        """处理项目变化"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            # 位置改变时更新所有连接线
            self._update_connections()
        return super().itemChange(change, value)

    def _update_connections(self):
        """更新所有连接线"""
        for port in list(self.input_ports.values()) + list(self.output_ports.values()):
            for conn in port.connections:
                conn.update_path()

    def get_all_connections(self) -> List:
        """获取所有连接"""
        connections = []
        for port in list(self.input_ports.values()) + list(self.output_ports.values()):
            connections.extend(port.connections)
        return list(set(connections))

    def get_input_value(self, port_name: str) -> Optional[str]:
        """
        获取输入端口的值表达式

        如果端口已连接，返回连接的输出表达式
        否则返回参数值或默认值
        """
        port = self.input_ports.get(port_name)
        if not port:
            return None

        # 检查是否有连接
        if port.connections:
            conn = port.connections[0]
            source_port = conn.source_port
            if source_port:
                return source_port.parent_node.get_output_expression(
                    source_port.definition.name
                )

        # 返回参数值（优先检查属性面板设置的 _input_ 前缀格式）
        value = self.parameters.get(f"_input_{port_name}")
        if value is None:
            value = self.parameters.get(port_name)
        if value is not None:
            # 布尔值需要转换为 Python 格式
            if isinstance(value, bool):
                return "True" if value else "False"
            return str(value)

        # 返回默认值
        if port.definition.default_value is not None:
            default = port.definition.default_value
            if isinstance(default, bool):
                return "True" if default else "False"
            return str(default)

        return None

    @abstractmethod
    def get_parameter_definitions(self) -> List[Dict]:
        """
        返回参数定义列表

        每个参数定义是一个字典:
        {
            "name": "period",
            "type": "int",  # int, float, bool, str
            "label": "周期",
            "default": 20,
            "min": 1,
            "max": 500
        }
        """
        pass

    @abstractmethod
    def generate_code(self, context: 'CodeGenContext') -> str:
        """
        生成Python代码

        Args:
            context: 代码生成上下文

        Returns:
            生成的代码行
        """
        pass

    @abstractmethod
    def get_output_expression(self, port_name: str) -> str:
        """
        获取输出端口的代码表达式

        Args:
            port_name: 输出端口名称

        Returns:
            代码表达式字符串
        """
        pass

    def get_variable_name(self, suffix: str = "") -> str:
        """获取此节点的变量名"""
        base = f"_{self.CONFIG.node_type.replace('.', '_')}_{self.node_id}"
        if suffix:
            return f"{base}_{suffix}"
        return base

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            'node_id': self.node_id,
            'node_type': self.CONFIG.node_type,
            'position': {'x': self.pos().x(), 'y': self.pos().y()},
            'parameters': self.parameters.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BaseNode':
        """从字典反序列化"""
        node = cls(QPointF(data['position']['x'], data['position']['y']))
        node.node_id = data['node_id']
        node.parameters = data.get('parameters', {})
        return node


class CodeGenContext:
    """代码生成上下文"""

    def __init__(self):
        self.variables: Dict[str, str] = {}  # node_id -> variable_name
        self.code_lines: List[str] = []
        self.imports: set = set()
        self.generated_nodes: set = set()

    def get_variable_name(self, node: BaseNode, suffix: str = "") -> str:
        """获取或创建节点的变量名"""
        key = f"{node.node_id}_{suffix}" if suffix else node.node_id
        if key not in self.variables:
            self.variables[key] = node.get_variable_name(suffix)
        return self.variables[key]

    def add_import(self, import_statement: str):
        """添加导入语句"""
        self.imports.add(import_statement)

    def add_code(self, code: str):
        """添加代码行"""
        self.code_lines.append(code)

    def mark_generated(self, node: BaseNode):
        """标记节点已生成代码"""
        self.generated_nodes.add(node.node_id)

    def is_generated(self, node: BaseNode) -> bool:
        """检查节点是否已生成代码"""
        return node.node_id in self.generated_nodes
