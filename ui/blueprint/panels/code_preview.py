"""
代码预览面板
显示蓝图生成的Python代码
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
import re


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
            'True', 'False', 'None', 'self'
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

        # 类名
        class_format = QTextCharFormat()
        class_format.setForeground(QColor(78, 201, 176))
        self.highlighting_rules.append((re.compile(r'\bclass\s+(\w+)'), class_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class CodePreview(QWidget):
    """
    代码预览面板

    显示蓝图生成的Python策略代码
    """

    # 信号
    code_copied = pyqtSignal()
    code_applied = pyqtSignal(str)  # 应用代码到代码编辑器

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel("生成代码")
        title.setStyleSheet("color: #e6edf3; font-weight: bold; font-size: 12px;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 复制按钮
        btn_copy = QPushButton("复制")
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
        """)
        btn_copy.clicked.connect(self._copy_code)
        header_layout.addWidget(btn_copy)

        # 应用按钮
        btn_apply = QPushButton("应用到编辑器")
        btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        btn_apply.clicked.connect(self._apply_code)
        header_layout.addWidget(btn_apply)

        layout.addWidget(header)

        # 代码编辑器
        self.code_editor = QTextEdit()
        self.code_editor.setReadOnly(True)
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #e6edf3;
                border: none;
                padding: 8px;
            }
        """)

        # 语法高亮
        self.highlighter = PythonHighlighter(self.code_editor.document())

        layout.addWidget(self.code_editor)

        # 设置默认提示
        self.set_code("# 在画布上创建节点并连接，代码将自动生成")

    def set_code(self, code: str):
        """设置代码内容"""
        self.code_editor.setPlainText(code)

    def get_code(self) -> str:
        """获取代码内容"""
        return self.code_editor.toPlainText()

    def _copy_code(self):
        """复制代码到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_code())
        self.code_copied.emit()

    def _apply_code(self):
        """应用代码到编辑器"""
        code = self.get_code()
        if code and not code.startswith("#"):
            self.code_applied.emit(code)
