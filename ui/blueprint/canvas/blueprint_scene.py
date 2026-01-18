"""
蓝图画布场景
管理所有节点和连接
"""
from typing import List, Optional, Dict, TYPE_CHECKING

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem
from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import QColor, QPen, QBrush

from ..connections.port import Port, PortDirection
from ..connections.connection import Connection

if TYPE_CHECKING:
    from ..nodes.base_node import BaseNode


class BlueprintScene(QGraphicsScene):
    """
    蓝图画布场景

    管理节点和连接的添加、删除、选择等操作
    """

    # 信号
    node_selected = pyqtSignal(object)  # 节点被选中
    node_deselected = pyqtSignal()      # 取消选中
    connection_created = pyqtSignal(object)  # 连接创建
    connection_deleted = pyqtSignal(object)  # 连接删除
    scene_changed = pyqtSignal()        # 场景变化

    # 网格设置
    GRID_SIZE = 20
    GRID_COLOR = QColor("#21262d")
    GRID_COLOR_MAJOR = QColor("#30363d")

    def __init__(self, parent=None):
        super().__init__(parent)

        # 节点和连接列表
        self.nodes: List['BaseNode'] = []
        self.connections: List[Connection] = []

        # 当前拖拽的连接
        self._dragging_connection: Optional[Connection] = None
        self._dragging_source_port: Optional[Port] = None

        # 设置场景大小
        self.setSceneRect(-5000, -5000, 10000, 10000)

        # 设置背景色
        self.setBackgroundBrush(QBrush(QColor("#0d1117")))

    def drawBackground(self, painter, rect):
        """绘制网格背景"""
        super().drawBackground(painter, rect)

        # 计算网格范围
        left = int(rect.left()) - (int(rect.left()) % self.GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % self.GRID_SIZE)

        # 绘制小网格
        painter.setPen(QPen(self.GRID_COLOR, 0.5))
        lines = []
        x = left
        while x < rect.right():
            lines.append((x, rect.top(), x, rect.bottom()))
            x += self.GRID_SIZE
        y = top
        while y < rect.bottom():
            lines.append((rect.left(), y, rect.right(), y))
            y += self.GRID_SIZE

        for line in lines:
            painter.drawLine(int(line[0]), int(line[1]), int(line[2]), int(line[3]))

        # 绘制大网格
        painter.setPen(QPen(self.GRID_COLOR_MAJOR, 1))
        major_size = self.GRID_SIZE * 5
        left = int(rect.left()) - (int(rect.left()) % major_size)
        top = int(rect.top()) - (int(rect.top()) % major_size)

        x = left
        while x < rect.right():
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += major_size
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += major_size

    def add_node(self, node: 'BaseNode', pos: QPointF = None):
        """添加节点到场景"""
        if pos:
            # 对齐到网格
            x = round(pos.x() / self.GRID_SIZE) * self.GRID_SIZE
            y = round(pos.y() / self.GRID_SIZE) * self.GRID_SIZE
            node.setPos(x, y)

        self.addItem(node)
        self.nodes.append(node)
        self.scene_changed.emit()

    def remove_node(self, node: 'BaseNode'):
        """从场景移除节点"""
        # 先删除所有连接
        for conn in node.get_all_connections():
            self.remove_connection(conn)

        # 移除节点
        self.removeItem(node)
        if node in self.nodes:
            self.nodes.remove(node)
        self.scene_changed.emit()

    def add_connection(self, connection: Connection):
        """添加连接"""
        self.addItem(connection)
        self.connections.append(connection)
        self.connection_created.emit(connection)
        self.scene_changed.emit()

    def remove_connection(self, connection: Connection):
        """移除连接"""
        connection.disconnect()
        self.removeItem(connection)
        if connection in self.connections:
            self.connections.remove(connection)
        self.connection_deleted.emit(connection)
        self.scene_changed.emit()

    def start_connection(self, port: Port):
        """开始创建连接"""
        self._dragging_source_port = port

        # 创建临时连接
        if port.definition.direction == PortDirection.OUTPUT:
            self._dragging_connection = Connection(source_port=port)
        else:
            # 从输入端口开始拖拽 (反向)
            self._dragging_connection = Connection()
            self._dragging_connection.temp_end_point = port.get_scene_center()

        self.addItem(self._dragging_connection)

    def update_dragging_connection(self, scene_pos: QPointF):
        """更新拖拽中的连接"""
        if self._dragging_connection:
            self._dragging_connection.set_temp_end(scene_pos)

    def finish_connection(self, target_port: Port) -> bool:
        """
        完成连接

        Args:
            target_port: 目标端口

        Returns:
            是否成功创建连接
        """
        if not self._dragging_connection or not self._dragging_source_port:
            self.cancel_connection()
            return False

        # 检查是否可以连接
        if not target_port.can_accept_connection(self._dragging_source_port):
            self.cancel_connection()
            return False

        # 确定源和目标
        if self._dragging_source_port.definition.direction == PortDirection.OUTPUT:
            source = self._dragging_source_port
            target = target_port
        else:
            source = target_port
            target = self._dragging_source_port

        # 如果目标端口已有连接，先删除
        if target.connections and not target.definition.multi_connect:
            for conn in target.connections[:]:
                self.remove_connection(conn)

        # 创建正式连接
        self.removeItem(self._dragging_connection)
        connection = Connection(source_port=source, target_port=target)
        self.add_connection(connection)

        self._dragging_connection = None
        self._dragging_source_port = None

        return True

    def cancel_connection(self):
        """取消连接"""
        if self._dragging_connection:
            self.removeItem(self._dragging_connection)
            self._dragging_connection = None
        self._dragging_source_port = None

    def get_port_at(self, scene_pos: QPointF) -> Optional[Port]:
        """获取指定位置的端口"""
        items = self.items(scene_pos)
        for item in items:
            if isinstance(item, Port):
                return item
        return None

    def get_node_at(self, scene_pos: QPointF) -> Optional['BaseNode']:
        """获取指定位置的节点"""
        from ..nodes.base_node import BaseNode
        items = self.items(scene_pos)
        for item in items:
            if isinstance(item, BaseNode):
                return item
        return None

    def delete_selected(self):
        """删除选中的项目"""
        selected = self.selectedItems()
        for item in selected:
            if isinstance(item, Connection):
                self.remove_connection(item)
            elif hasattr(item, 'node_id'):  # BaseNode
                self.remove_node(item)

    def clear_all(self):
        """清空场景"""
        for conn in self.connections[:]:
            self.remove_connection(conn)
        for node in self.nodes[:]:
            self.remove_node(node)

    def get_node_by_id(self, node_id: str) -> Optional['BaseNode']:
        """根据ID获取节点"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def to_dict(self) -> Dict:
        """序列化场景"""
        return {
            'nodes': [node.to_dict() for node in self.nodes],
            'connections': [conn.to_dict() for conn in self.connections
                            if conn.source_port and conn.target_port]
        }

    def from_dict(self, data: Dict, node_factory):
        """从字典恢复场景"""
        self.clear_all()

        # 创建节点
        node_map = {}
        for node_data in data.get('nodes', []):
            node = node_factory.create_node(
                node_data['node_type'],
                QPointF(node_data['position']['x'], node_data['position']['y'])
            )
            if node:
                node.node_id = node_data['node_id']
                node.parameters = node_data.get('parameters', {})
                self.add_node(node)
                node_map[node.node_id] = node

        # 创建连接
        for conn_data in data.get('connections', []):
            source_node = node_map.get(conn_data['source_node'])
            target_node = node_map.get(conn_data['target_node'])

            if source_node and target_node:
                source_port = source_node.output_ports.get(conn_data['source_port'])
                target_port = target_node.input_ports.get(conn_data['target_port'])

                if source_port and target_port:
                    connection = Connection(source_port=source_port, target_port=target_port)
                    self.add_connection(connection)
