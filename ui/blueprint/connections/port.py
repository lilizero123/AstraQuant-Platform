"""
蓝图端口类
定义节点的输入/输出端口
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, TYPE_CHECKING

from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QPen, QBrush, QPainter

from .type_system import DataType, get_type_color, can_connect

if TYPE_CHECKING:
    from .connection import Connection
    from ..nodes.base_node import BaseNode


class PortDirection(Enum):
    """端口方向"""
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class PortDefinition:
    """端口定义"""
    name: str                           # 端口名称 (唯一标识)
    data_type: DataType                 # 数据类型
    direction: PortDirection            # 方向 (输入/输出)
    label: str = ""                     # 显示标签
    default_value: Any = None           # 默认值
    required: bool = True               # 是否必须连接
    multi_connect: bool = False         # 是否允许多连接 (仅输入端口)

    def __post_init__(self):
        if not self.label:
            self.label = self.name


class Port(QGraphicsEllipseItem):
    """
    端口图形项
    显示在节点边缘，用于连接其他节点
    """

    RADIUS = 6  # 端口半径

    def __init__(self, definition: PortDefinition, parent_node: 'BaseNode'):
        # 创建圆形端口
        super().__init__(
            -self.RADIUS, -self.RADIUS,
            self.RADIUS * 2, self.RADIUS * 2,
            parent_node
        )

        self.definition = definition
        self.parent_node = parent_node
        self.connections: List['Connection'] = []

        # 悬停状态
        self._hovered = False

        # 设置交互
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setCursor(Qt.CrossCursor)

        # 设置外观
        self._setup_appearance()

    def _setup_appearance(self):
        """设置端口外观"""
        color = QColor(get_type_color(self.definition.data_type))
        self.base_color = color

        # 填充颜色
        if self.connections:
            self.setBrush(QBrush(color))
        else:
            # 未连接时显示空心
            self.setBrush(QBrush(QColor("#161b22")))

        # 边框
        self.setPen(QPen(color, 2))

    def update_appearance(self):
        """更新外观 (连接状态改变时调用)"""
        self._setup_appearance()

    def hoverEnterEvent(self, event):
        """鼠标进入"""
        self._hovered = True
        # 放大效果
        self.setScale(1.3)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """鼠标离开"""
        self._hovered = False
        self.setScale(1.0)
        super().hoverLeaveEvent(event)

    def can_accept_connection(self, source_port: 'Port') -> bool:
        """
        检查是否可以接受来自source_port的连接

        Args:
            source_port: 源端口

        Returns:
            是否可以连接
        """
        # 不能连接同方向的端口
        if self.definition.direction == source_port.definition.direction:
            return False

        # 不能连接同一个节点的端口
        if self.parent_node == source_port.parent_node:
            return False

        # 检查是否已有连接 (输入端口默认只能有一个连接)
        if self.definition.direction == PortDirection.INPUT:
            if not self.definition.multi_connect and self.connections:
                return False

        # 检查类型兼容性
        if self.definition.direction == PortDirection.INPUT:
            return can_connect(source_port.definition.data_type,
                               self.definition.data_type)
        else:
            return can_connect(self.definition.data_type,
                               source_port.definition.data_type)

    def get_scene_center(self) -> QPointF:
        """获取端口在场景中的中心位置"""
        return self.scenePos()

    def add_connection(self, connection: 'Connection'):
        """添加连接"""
        if connection not in self.connections:
            self.connections.append(connection)
            self.update_appearance()

    def remove_connection(self, connection: 'Connection'):
        """移除连接"""
        if connection in self.connections:
            self.connections.remove(connection)
            self.update_appearance()

    def get_connected_value_expression(self) -> Optional[str]:
        """
        获取连接的值表达式 (用于代码生成)

        Returns:
            连接的输出端口的代码表达式，如果未连接返回None
        """
        if not self.connections:
            return None

        # 获取第一个连接的源端口
        conn = self.connections[0]
        if self.definition.direction == PortDirection.INPUT:
            source_port = conn.source_port
        else:
            source_port = conn.target_port

        if source_port:
            return source_port.parent_node.get_output_expression(
                source_port.definition.name
            )
        return None
