"""
蓝图画布视图
支持缩放、平移等交互
"""
from typing import Optional

from PyQt5.QtWidgets import QGraphicsView, QGraphicsItem
from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QMouseEvent, QWheelEvent, QKeyEvent

from .blueprint_scene import BlueprintScene
from ..connections.port import Port


class BlueprintView(QGraphicsView):
    """
    蓝图画布视图

    支持:
    - 鼠标滚轮缩放
    - 中键/右键拖拽平移
    - 节点拖拽
    - 端口连接
    """

    # 信号
    node_dropped = pyqtSignal(str, QPointF)  # 节点类型, 位置

    # 缩放限制
    MIN_ZOOM = 0.2
    MAX_ZOOM = 3.0

    def __init__(self, scene: BlueprintScene = None, parent=None):
        super().__init__(parent)

        # 创建或使用场景
        self._scene = scene or BlueprintScene()
        self.setScene(self._scene)

        # 状态
        self._panning = False
        self._pan_start = QPointF()
        self._connecting = False
        self._zoom_level = 1.0

        # 设置视图属性
        self._setup_view()

    def _setup_view(self):
        """设置视图属性"""
        # 渲染设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        # 视图设置
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # 拖放设置
        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.NoDrag)

        # 样式
        self.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #30363d;
                background-color: #0d1117;
            }
        """)

    def get_scene(self) -> BlueprintScene:
        """获取场景"""
        return self._scene

    def wheelEvent(self, event: QWheelEvent):
        """鼠标滚轮缩放"""
        # 计算缩放因子
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.15
        else:
            factor = 1 / 1.15

        # 限制缩放范围
        new_zoom = self._zoom_level * factor
        if new_zoom < self.MIN_ZOOM or new_zoom > self.MAX_ZOOM:
            return

        self._zoom_level = new_zoom
        self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        # 中键或右键开始平移
        if event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        # 左键
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            port = self._scene.get_port_at(scene_pos)

            if port:
                # 点击端口，开始连接
                self._connecting = True
                self._scene.start_connection(port)
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        # 平移
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            return

        # 连接拖拽
        if self._connecting:
            scene_pos = self.mapToScene(event.pos())
            self._scene.update_dragging_connection(scene_pos)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        # 结束平移
        if event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            return

        # 结束连接
        if event.button() == Qt.LeftButton and self._connecting:
            self._connecting = False
            scene_pos = self.mapToScene(event.pos())
            port = self._scene.get_port_at(scene_pos)

            if port:
                self._scene.finish_connection(port)
            else:
                self._scene.cancel_connection()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """键盘按下"""
        # Delete 删除选中项
        if event.key() == Qt.Key_Delete:
            self._scene.delete_selected()
            return

        # Escape 取消连接
        if event.key() == Qt.Key_Escape:
            if self._connecting:
                self._connecting = False
                self._scene.cancel_connection()
            return

        # Ctrl+A 全选
        if event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            for item in self._scene.items():
                item.setSelected(True)
            return

        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        """拖拽进入"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """拖拽移动"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """拖拽放下"""
        if event.mimeData().hasText():
            node_type = event.mimeData().text()
            scene_pos = self.mapToScene(event.pos())
            self.node_dropped.emit(node_type, scene_pos)
            event.acceptProposedAction()

    def zoom_in(self):
        """放大"""
        if self._zoom_level < self.MAX_ZOOM:
            self._zoom_level *= 1.15
            self.scale(1.15, 1.15)

    def zoom_out(self):
        """缩小"""
        if self._zoom_level > self.MIN_ZOOM:
            self._zoom_level /= 1.15
            self.scale(1 / 1.15, 1 / 1.15)

    def zoom_reset(self):
        """重置缩放"""
        self.resetTransform()
        self._zoom_level = 1.0

    def center_on_nodes(self):
        """居中显示所有节点"""
        if self._scene.nodes:
            # 计算所有节点的边界
            rect = None
            for node in self._scene.nodes:
                node_rect = node.sceneBoundingRect()
                if rect is None:
                    rect = node_rect
                else:
                    rect = rect.united(node_rect)

            if rect:
                self.fitInView(rect, Qt.KeepAspectRatio)
                # 稍微缩小一点，留出边距
                self.scale(0.9, 0.9)
                self._zoom_level = self.transform().m11()
