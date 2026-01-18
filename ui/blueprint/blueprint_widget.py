"""
蓝图编辑器主组件
整合画布、节点面板、属性面板和代码预览
"""
import json
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QToolBar, QAction, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import QIcon

from .canvas.blueprint_scene import BlueprintScene
from .canvas.blueprint_view import BlueprintView
from .panels.node_palette import NodePalette
from .panels.property_panel import PropertyPanel
from .panels.code_preview import CodePreview
from .nodes.node_factory import get_node_factory
from .nodes.base_node import BaseNode
from .codegen.code_generator import CodeGenerator


class BlueprintWidget(QWidget):
    """
    蓝图编辑器主组件

    包含:
    - 左侧: 节点面板 (可拖拽节点)
    - 中间: 画布 (节点编辑区)
    - 右侧: 属性面板 (节点参数)
    - 底部: 代码预览
    """

    # 信号
    code_generated = pyqtSignal(str)  # 代码生成完成

    def __init__(self, parent=None):
        super().__init__(parent)

        self.factory = get_node_factory()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主分割器 (上下)
        main_splitter = QSplitter(Qt.Vertical)

        # 上部分割器 (左中右)
        top_splitter = QSplitter(Qt.Horizontal)

        # 左侧 - 节点面板
        self.node_palette = NodePalette()
        self.node_palette.setMinimumWidth(180)
        self.node_palette.setMaximumWidth(250)
        top_splitter.addWidget(self.node_palette)

        # 中间 - 画布
        self.scene = BlueprintScene()
        self.view = BlueprintView(self.scene)
        top_splitter.addWidget(self.view)

        # 右侧 - 属性面板
        self.property_panel = PropertyPanel()
        self.property_panel.setMinimumWidth(200)
        self.property_panel.setMaximumWidth(280)
        top_splitter.addWidget(self.property_panel)

        # 设置分割比例
        top_splitter.setSizes([200, 600, 220])

        main_splitter.addWidget(top_splitter)

        # 底部 - 代码预览
        self.code_preview = CodePreview()
        self.code_preview.setMinimumHeight(120)
        self.code_preview.setMaximumHeight(250)
        main_splitter.addWidget(self.code_preview)

        # 设置分割比例
        main_splitter.setSizes([500, 150])

        # 工具栏 (在画布创建后添加)
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        layout.addWidget(main_splitter)

    def _create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
                padding: 4px;
                spacing: 4px;
            }
            QToolButton {
                background-color: transparent;
                color: #e6edf3;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QToolButton:hover {
                background-color: #30363d;
            }
            QToolButton:pressed {
                background-color: #21262d;
            }
        """)

        # 新建
        action_new = QAction("新建", self)
        action_new.triggered.connect(self._on_new)
        toolbar.addAction(action_new)

        action_load = QAction("加载蓝图", self)
        action_load.triggered.connect(self._on_load_blueprint)
        toolbar.addAction(action_load)

        action_save = QAction("保存蓝图", self)
        action_save.triggered.connect(self._on_save_blueprint)
        toolbar.addAction(action_save)

        toolbar.addSeparator()

        # 缩放
        action_zoom_in = QAction("放大", self)
        action_zoom_in.triggered.connect(self.view.zoom_in)
        toolbar.addAction(action_zoom_in)

        action_zoom_out = QAction("缩小", self)
        action_zoom_out.triggered.connect(self.view.zoom_out)
        toolbar.addAction(action_zoom_out)

        action_zoom_reset = QAction("重置", self)
        action_zoom_reset.triggered.connect(self.view.zoom_reset)
        toolbar.addAction(action_zoom_reset)

        action_center = QAction("居中", self)
        action_center.triggered.connect(self.view.center_on_nodes)
        toolbar.addAction(action_center)

        toolbar.addSeparator()

        # 删除
        action_delete = QAction("删除选中", self)
        action_delete.triggered.connect(self.scene.delete_selected)
        toolbar.addAction(action_delete)

        toolbar.addSeparator()

        # 生成代码
        action_generate = QAction("生成代码", self)
        action_generate.triggered.connect(self._generate_code)
        toolbar.addAction(action_generate)

        # 验证
        action_validate = QAction("验证", self)
        action_validate.triggered.connect(self._validate)
        toolbar.addAction(action_validate)

        return toolbar

    def _connect_signals(self):
        """连接信号"""
        # 节点拖放
        self.view.node_dropped.connect(self._on_node_dropped)

        # 场景变化
        self.scene.scene_changed.connect(self._on_scene_changed)

        # 节点选择
        self.scene.selectionChanged.connect(self._on_selection_changed)

        # 属性变化
        self.property_panel.parameter_changed.connect(self._on_parameter_changed)

        # 代码应用
        self.code_preview.code_applied.connect(self._on_code_applied)

    def _on_node_dropped(self, node_type: str, pos: QPointF):
        """节点拖放到画布"""
        node = self.factory.create_node(node_type, pos)
        if node:
            self.scene.add_node(node, pos)

    def _on_scene_changed(self):
        """场景变化时更新代码预览"""
        self._update_code_preview()

    def _on_selection_changed(self):
        """选择变化时更新属性面板"""
        selected = self.scene.selectedItems()
        if selected:
            # 找到选中的节点
            for item in selected:
                if isinstance(item, BaseNode):
                    self.property_panel.set_node(item)
                    return
        self.property_panel.clear()

    def _on_parameter_changed(self, name: str, value):
        """参数变化时更新代码预览"""
        self._update_code_preview()

    def _on_code_applied(self, code: str):
        """代码应用到编辑器"""
        self.code_generated.emit(code)

    def _on_new(self):
        """新建蓝图"""
        reply = QMessageBox.question(
            self, '确认',
            '确定要清空当前蓝图吗？',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.scene.clear_all()
            self.property_panel.clear()

    def _generate_code(self):
        """生成代码"""
        self._update_code_preview()
        code = self.code_preview.get_code()
        if code and not code.startswith("#"):
            QMessageBox.information(self, "提示", "代码已生成，可以点击'应用到编辑器'使用")

    def _validate(self):
        """验证蓝图"""
        from .codegen.graph_analyzer import GraphAnalyzer

        if not self.scene.nodes:
            QMessageBox.warning(self, "验证", "画布为空，请先添加节点")
            return

        analyzer = GraphAnalyzer(self.scene.nodes)
        is_valid, errors = analyzer.validate()

        if is_valid:
            QMessageBox.information(self, "验证", "蓝图验证通过！")
        else:
            error_msg = "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "验证失败", f"发现以下问题:\n\n{error_msg}")

    def _update_code_preview(self):
        """更新代码预览"""
        if not self.scene.nodes:
            self.code_preview.set_code("# 在画布上创建节点并连接，代码将自动生成")
            return

        generator = CodeGenerator(self.scene.nodes)
        code = generator.generate_preview()
        self.code_preview.set_code(code)

    def get_generated_code(self) -> str:
        """获取生成的代码"""
        if not self.scene.nodes:
            return ""

        generator = CodeGenerator(self.scene.nodes)
        return generator.generate()

    def load_blueprint(self, data: dict):
        """加载蓝图数据"""
        self.scene.from_dict(data, self.factory)
        self._update_code_preview()

    def save_blueprint(self) -> dict:
        """保存蓝图数据"""
        return self.scene.to_dict()

    def _on_save_blueprint(self):
        if not self.scene.nodes:
            QMessageBox.information(self, "提示", "画布为空，无需保存。")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存蓝图",
            "blueprint.json",
            "Blueprint (*.json)"
        )
        if not file_path:
            return
        try:
            data = self.save_blueprint()
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "提示", "蓝图已保存。")
        except OSError as err:
            QMessageBox.warning(self, "错误", f"保存失败: {err}")

    def _on_load_blueprint(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载蓝图",
            "",
            "Blueprint (*.json)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            self.load_blueprint(data)
            QMessageBox.information(self, "提示", "蓝图已加载。")
        except (OSError, json.JSONDecodeError) as err:
            QMessageBox.warning(self, "错误", f"加载失败: {err}")
