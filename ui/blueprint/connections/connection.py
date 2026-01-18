"""
蓝图连接线
连接两个端口的贝塞尔曲线
"""
from typing import Optional, TYPE_CHECKING, Dict

from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsItem
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath

from .type_system import get_type_color

if TYPE_CHECKING:
    from .port import Port


class Connection(QGraphicsPathItem):
    """
    连接线
    使用贝塞尔曲线连接两个端口
    """

    def __init__(self, source_port: 'Port' = None, target_port: 'Port' = None):
        super().__init__()

        self.source_port: Optional['Port'] = source_port
        self.target_port: Optional['Port'] = target_port

        # 临时终点 (拖拽时使用)
        self.temp_end_point: Optional[QPointF] = None

        # 设置层级 (在节点下方)
        self.setZValue(-1)

        # 设置外观
        self._setup_appearance()

        # 注册到端口
        if source_port:
            source_port.add_connection(self)
        if target_port:
            target_port.add_connection(self)

        # 更新路径
        self.update_path()

    def _setup_appearance(self):
        """设置连接线外观"""
        # 根据源端口类型设置颜色
        if self.source_port:
            color = QColor(get_type_color(self.source_port.definition.data_type))
        else:
            color = QColor("#8b949e")

        pen = QPen(color, 2.5)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)

        # 设置可选中
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def update_path(self):
        """更新贝塞尔曲线路径"""
        if not self.source_port:
            return

        # 获取起点
        start = self.source_port.get_scene_center()

        # 获取终点
        if self.target_port:
            end = self.target_port.get_scene_center()
        elif self.temp_end_point:
            end = self.temp_end_point
        else:
            return

        # 计算控制点
        dx = abs(end.x() - start.x())
        ctrl_offset = max(dx * 0.5, 60)

        ctrl1 = QPointF(start.x() + ctrl_offset, start.y())
        ctrl2 = QPointF(end.x() - ctrl_offset, end.y())

        # 创建贝塞尔曲线路径
        path = QPainterPath()
        path.moveTo(start)
        path.cubicTo(ctrl1, ctrl2, end)

        self.setPath(path)

    def set_temp_end(self, point: QPointF):
        """设置临时终点 (拖拽时)"""
        self.temp_end_point = point
        self.update_path()

    def finalize_connection(self, target_port: 'Port') -> bool:
        """
        完成连接

        Args:
            target_port: 目标端口

        Returns:
            是否成功连接
        """
        # 检查是否可以连接
        if not target_port.can_accept_connection(self.source_port):
            return False

        self.target_port = target_port
        self.temp_end_point = None

        # 注册到目标端口
        target_port.add_connection(self)

        # 更新路径
        self.update_path()

        return True

    def disconnect(self):
        """断开连接"""
        if self.source_port:
            self.source_port.remove_connection(self)
        if self.target_port:
            self.target_port.remove_connection(self)

        self.source_port = None
        self.target_port = None

    def paint(self, painter: QPainter, option, widget=None):
        """绘制连接线"""
        # 选中时高亮
        if self.isSelected():
            pen = QPen(QColor("#58a6ff"), 3)
            pen.setCapStyle(Qt.RoundCap)
            self.setPen(pen)
        else:
            self._setup_appearance()

        super().paint(painter, option, widget)

    def hoverEnterEvent(self, event):
        """鼠标进入"""
        pen = self.pen()
        pen.setWidth(4)
        self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """鼠标离开"""
        self._setup_appearance()
        super().hoverLeaveEvent(event)

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            'source_node': self.source_port.parent_node.node_id if self.source_port else None,
            'source_port': self.source_port.definition.name if self.source_port else None,
            'target_node': self.target_port.parent_node.node_id if self.target_port else None,
            'target_port': self.target_port.definition.name if self.target_port else None,
        }
