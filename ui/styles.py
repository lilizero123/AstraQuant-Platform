"""
现代化深色主题样式
"""

# 颜色定义
COLORS = {
    'bg_dark': '#0d1117',        # 最深背景
    'bg_primary': '#161b22',     # 主背景
    'bg_secondary': '#21262d',   # 次级背景
    'bg_tertiary': '#30363d',    # 第三级背景
    'bg_hover': '#388bfd1a',     # 悬停背景

    'border': '#30363d',         # 边框
    'border_light': '#484f58',   # 浅边框

    'text_primary': '#e6edf3',   # 主文字
    'text_secondary': '#8b949e', # 次级文字
    'text_muted': '#6e7681',     # 弱化文字

    'accent': '#58a6ff',         # 强调色（蓝）
    'accent_hover': '#79c0ff',   # 强调色悬停

    'success': '#3fb950',        # 成功/涨（绿）
    'danger': '#f85149',         # 危险/跌（红）
    'warning': '#d29922',        # 警告（黄）

    'chart_up': '#26a69a',       # K线涨
    'chart_down': '#ef5350',     # K线跌
}

# 全局样式表
DARK_STYLE = """
/* ==================== 全局样式 ==================== */
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ==================== 菜单栏 ==================== */
QMenuBar {
    background-color: #161b22;
    color: #e6edf3;
    border-bottom: 1px solid #30363d;
    padding: 4px 0;
}

QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 6px;
    margin: 2px 4px;
}

QMenuBar::item:selected {
    background-color: #21262d;
}

QMenu {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background-color: #388bfd1a;
    color: #58a6ff;
}

QMenu::separator {
    height: 1px;
    background-color: #30363d;
    margin: 4px 8px;
}

/* ==================== 工具栏 ==================== */
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 4px 8px;
    spacing: 8px;
}

QToolBar::separator {
    width: 1px;
    background-color: #30363d;
    margin: 4px 8px;
}

QToolButton {
    background-color: transparent;
    color: #e6edf3;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #21262d;
    border-color: #30363d;
}

QToolButton:pressed {
    background-color: #30363d;
}

/* ==================== 标签页 ==================== */
QTabWidget::pane {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: transparent;
    color: #8b949e;
    border: none;
    padding: 10px 20px;
    margin-right: 4px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #e6edf3;
    border-bottom: 2px solid #58a6ff;
}

QTabBar::tab:hover:!selected {
    color: #e6edf3;
    background-color: #21262d;
    border-radius: 6px 6px 0 0;
}

/* ==================== 按钮 ==================== */
QPushButton {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #484f58;
}

QPushButton:pressed {
    background-color: #484f58;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

/* 主要按钮 */
QPushButton#primaryButton, QPushButton[primary="true"] {
    background-color: #238636;
    border-color: #238636;
    color: #ffffff;
}

QPushButton#primaryButton:hover, QPushButton[primary="true"]:hover {
    background-color: #2ea043;
    border-color: #2ea043;
}

/* 危险按钮 */
QPushButton#dangerButton, QPushButton[danger="true"] {
    background-color: #da3633;
    border-color: #da3633;
    color: #ffffff;
}

QPushButton#dangerButton:hover, QPushButton[danger="true"]:hover {
    background-color: #f85149;
    border-color: #f85149;
}

/* ==================== 输入框 ==================== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #388bfd66;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #58a6ff;
    outline: none;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #161b22;
    color: #484f58;
}

/* ==================== 下拉框 ==================== */
QComboBox {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #484f58;
}

QComboBox:focus {
    border-color: #58a6ff;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8b949e;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    selection-background-color: #388bfd1a;
    selection-color: #58a6ff;
    padding: 4px;
}

/* ==================== 数值输入框 ==================== */
QSpinBox, QDoubleSpinBox {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #58a6ff;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #21262d;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #30363d;
}

/* ==================== 日期选择器 ==================== */
QDateEdit {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
}

QDateEdit:focus {
    border-color: #58a6ff;
}

QCalendarWidget {
    background-color: #161b22;
    color: #e6edf3;
}

QCalendarWidget QToolButton {
    background-color: transparent;
    color: #e6edf3;
}

QCalendarWidget QMenu {
    background-color: #161b22;
}

/* ==================== 列表 ==================== */
QListWidget {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 0;
}

QListWidget::item:hover {
    background-color: #21262d;
}

QListWidget::item:selected {
    background-color: #388bfd1a;
    color: #58a6ff;
}

/* ==================== 表格 ==================== */
QTableWidget, QTableView {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    gridline-color: #21262d;
    outline: none;
}

QTableWidget::item, QTableView::item {
    padding: 8px;
    border-bottom: 1px solid #21262d;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #388bfd1a;
    color: #58a6ff;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    border: none;
    border-bottom: 1px solid #30363d;
    border-right: 1px solid #21262d;
    padding: 10px 8px;
    font-weight: 600;
}

QHeaderView::section:hover {
    background-color: #21262d;
    color: #e6edf3;
}

/* ==================== 滚动条 ==================== */
QScrollBar:vertical {
    background-color: #0d1117;
    width: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #0d1117;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #484f58;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ==================== 分组框 ==================== */
QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 0px;
    padding: 0 8px;
    background-color: #161b22;
    color: #e6edf3;
}

/* ==================== 进度条 ==================== */
QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #58a6ff, stop:1 #a371f7);
    border-radius: 4px;
}

/* ==================== 状态栏 ==================== */
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
    padding: 4px 8px;
}

QStatusBar::item {
    border: none;
}

/* ==================== 分割器 ==================== */
QSplitter::handle {
    background-color: #30363d;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #58a6ff;
}

/* ==================== 标签 ==================== */
QLabel {
    color: #e6edf3;
}

QLabel[secondary="true"] {
    color: #8b949e;
}

/* ==================== 单选/复选框 ==================== */
QRadioButton, QCheckBox {
    color: #e6edf3;
    spacing: 8px;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #30363d;
    border-radius: 4px;
    background-color: #0d1117;
}

QRadioButton::indicator {
    border-radius: 10px;
}

QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #58a6ff;
    border-color: #58a6ff;
}

/* ==================== 工具提示 ==================== */
QToolTip {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
}

/* ==================== Frame ==================== */
QFrame {
    border: none;
}

QFrame[frameShape="4"], QFrame[frameShape="5"] {
    background-color: #30363d;
}
"""

# K线图专用样式
CHART_STYLE = """
QFrame#chartFrame {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
}
"""

LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f5f7fb;
    color: #1f2328;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMenuBar, QToolBar, QStatusBar {
    background-color: #ffffff;
    border-color: #d0d7de;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
}

QPushButton {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 12px;
}

QPushButton:hover {
    background-color: #f1f5f9;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px 12px;
}

QListWidget, QTableWidget, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
}

QTabWidget::pane {
    border: 1px solid #d0d7de;
    border-radius: 8px;
    background-color: #ffffff;
}

QTabBar::tab:selected {
    color: #0969da;
    border-bottom: 2px solid #0969da;
}
"""

THEMES = {
    "dark": DARK_STYLE,
    "light": LIGHT_STYLE,
}


def get_style(theme: str) -> str:
    """根据主题名称返回样式"""
    return THEMES.get(theme, DARK_STYLE)
