"""
持仓组件 - 现代化深色主题
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor


class PositionWidget(QWidget):
    """持仓组件"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 账户信息卡片
        account_card = QFrame()
        account_card.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        account_layout = QVBoxLayout(account_card)
        account_layout.setContentsMargins(16, 12, 16, 12)
        account_layout.setSpacing(8)

        # 标题
        title = QLabel("账户概览")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title.setStyleSheet("color: #e6edf3;")
        account_layout.addWidget(title)

        # 总资产
        self.label_total = QLabel("¥1,000,000.00")
        self.label_total.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        self.label_total.setStyleSheet("color: #e6edf3;")
        account_layout.addWidget(self.label_total)

        # 盈亏 (红涨绿跌 - 中国标准)
        self.label_profit = QLabel("+¥15,000.00 (+1.5%)")
        self.label_profit.setStyleSheet("""
            color: #ef5350;
            font-size: 14px;
            font-weight: 500;
        """)
        account_layout.addWidget(self.label_profit)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #30363d;")
        line.setFixedHeight(1)
        account_layout.addWidget(line)

        # 详细信息行
        detail_layout = QHBoxLayout()
        detail_layout.setSpacing(20)

        # 可用资金
        available_frame = QVBoxLayout()
        available_label = QLabel("可用资金")
        available_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.label_available = QLabel("¥800,000.00")
        self.label_available.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: 500;")
        available_frame.addWidget(available_label)
        available_frame.addWidget(self.label_available)
        detail_layout.addLayout(available_frame)

        # 持仓市值
        market_frame = QVBoxLayout()
        market_label = QLabel("持仓市值")
        market_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.label_market_value = QLabel("¥200,000.00")
        self.label_market_value.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: 500;")
        market_frame.addWidget(market_label)
        market_frame.addWidget(self.label_market_value)
        detail_layout.addLayout(market_frame)

        detail_layout.addStretch()
        account_layout.addLayout(detail_layout)

        layout.addWidget(account_card)

        # 持仓列表
        position_card = QFrame()
        position_card.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        position_layout = QVBoxLayout(position_card)
        position_layout.setContentsMargins(16, 12, 16, 12)
        position_layout.setSpacing(8)

        position_title = QLabel("当前持仓")
        position_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        position_title.setStyleSheet("color: #e6edf3;")
        position_layout.addWidget(position_title)

        self.position_table = QTableWidget()
        self.position_table.setColumnCount(6)
        self.position_table.setHorizontalHeaderLabels(
            ["代码", "名称", "数量", "成本", "现价", "盈亏"]
        )
        self.position_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.position_table.verticalHeader().setVisible(False)
        self.position_table.setShowGrid(False)
        self.position_table.setAlternatingRowColors(True)
        self.position_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
                alternate-background-color: #21262d;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #21262d;
            }
        """)

        position_layout.addWidget(self.position_table)

        layout.addWidget(position_card)

    def update_account(self, total, available, market_value, profit, profit_pct):
        """更新账户信息"""
        self.label_total.setText(f"¥{total:,.2f}")
        self.label_available.setText(f"¥{available:,.2f}")
        self.label_market_value.setText(f"¥{market_value:,.2f}")

        # 红涨绿跌 - 中国标准
        if profit >= 0:
            self.label_profit.setText(f"+¥{profit:,.2f} (+{profit_pct:.2f}%)")
            self.label_profit.setStyleSheet("color: #ef5350; font-size: 14px; font-weight: 500;")
        else:
            self.label_profit.setText(f"-¥{abs(profit):,.2f} ({profit_pct:.2f}%)")
            self.label_profit.setStyleSheet("color: #26a69a; font-size: 14px; font-weight: 500;")

    def update_positions(self, positions):
        """更新持仓列表"""
        self.position_table.setRowCount(len(positions or []))
        for row, pos in enumerate(positions or []):
            code = pos.get('code', '--')
            name = pos.get('name', code)
            qty = pos.get('qty', 0)
            cost = pos.get('cost', 0.0) or 0.0
            price = pos.get('price', cost) or 0.0

            self.position_table.setItem(row, 0, QTableWidgetItem(str(code)))
            self.position_table.setItem(row, 1, QTableWidgetItem(str(name)))
            self.position_table.setItem(row, 2, QTableWidgetItem(str(qty)))
            self.position_table.setItem(row, 3, QTableWidgetItem(f"{float(cost):.2f}"))
            self.position_table.setItem(row, 4, QTableWidgetItem(f"{float(price):.2f}"))

            pnl = (float(price) - float(cost)) * float(qty)
            pnl_item = QTableWidgetItem(f"{pnl:+.2f}")
            pnl_item.setTextAlignment(Qt.AlignCenter)
            # 红涨绿跌 - 中国标准
            if pnl >= 0:
                pnl_item.setForeground(QColor(239, 83, 80))   # 红色盈利
            else:
                pnl_item.setForeground(QColor(38, 166, 154))  # 绿色亏损
            self.position_table.setItem(row, 5, pnl_item)

    def clear(self):
        """清空显示"""
        self.update_account(0, 0, 0, 0, 0)
        self.position_table.setRowCount(0)
