"""
节点面板
显示可拖拽的节点列表
"""
from typing import Dict, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QColor, QFont

from ..nodes.node_factory import get_node_factory


class NodePaletteItem(QFrame):
    """节点面板项"""

    def __init__(self, node_type: str, title: str, description: str, color: str, parent=None):
        super().__init__(parent)

        self.node_type = node_type
        self.title = title
        self.color = color

        self._setup_ui(title, description, color)

    def _setup_ui(self, title: str, description: str, color: str):
        """设置UI"""
        self.setFixedHeight(50)
        self.setCursor(Qt.OpenHandCursor)

        # 样式
        self.setStyleSheet(f"""
            NodePaletteItem {{
                background-color: #21262d;
                border: 1px solid #30363d;
                border-left: 3px solid {color};
                border-radius: 4px;
                margin: 2px;
            }}
            NodePaletteItem:hover {{
                background-color: #30363d;
                border-color: #58a6ff;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #e6edf3; font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)

        # 描述
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #8b949e; font-size: 10px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

    def mousePressEvent(self, event):
        """鼠标按下开始拖拽"""
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        """鼠标移动进行拖拽"""
        if event.buttons() & Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.node_type)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.CopyAction)


class NodePalette(QWidget):
    """
    节点面板

    显示所有可用节点，支持拖拽到画布
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.factory = get_node_factory()
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel("节点")
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

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索节点...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px;
                margin: 8px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0d1117;
            }
            QScrollBar:vertical {
                background-color: #0d1117;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #30363d;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #484f58;
            }
        """)

        # 节点列表容器
        self.node_container = QWidget()
        self.node_layout = QVBoxLayout(self.node_container)
        self.node_layout.setContentsMargins(4, 4, 4, 4)
        self.node_layout.setSpacing(4)

        scroll.setWidget(self.node_container)
        layout.addWidget(scroll)

        # 填充节点
        self._populate_nodes()

    def _populate_nodes(self, filter_text: str = ""):
        """填充节点列表"""
        # 清空现有内容
        while self.node_layout.count():
            item = self.node_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filter_text = filter_text.lower()

        # 按分类添加节点
        for category in self.factory.get_categories():
            nodes_in_category = []

            for node_type in self.factory.get_nodes_in_category(category):
                info = self.factory.get_node_info(node_type)
                if info:
                    # 过滤
                    if filter_text:
                        if (filter_text not in info['title'].lower() and
                                filter_text not in info['description'].lower() and
                                filter_text not in category.lower()):
                            continue
                    nodes_in_category.append(info)

            if not nodes_in_category:
                continue

            # 分类标题
            category_label = QLabel(category)
            category_label.setStyleSheet("""
                QLabel {
                    color: #8b949e;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 8px 4px 4px 4px;
                }
            """)
            self.node_layout.addWidget(category_label)

            # 节点项
            for info in nodes_in_category:
                item = NodePaletteItem(
                    info['type'],
                    info['title'],
                    info['description'],
                    info['color']
                )
                self.node_layout.addWidget(item)

        # 添加弹性空间
        self.node_layout.addStretch()

    def _on_search(self, text: str):
        """搜索过滤"""
        self._populate_nodes(text)
