"""
交易节点
提供买入、卖出等交易操作
"""
from typing import List, Dict

from .base_node import BaseNode, NodeConfig, CodeGenContext
from ..connections.port import PortDefinition, PortDirection
from ..connections.type_system import DataType


class BuyNode(BaseNode):
    """买入节点"""

    CONFIG = NodeConfig(
        node_type="trade.buy",
        category="交易",
        title="买入",
        description="条件满足时买入",
        color="#f85149",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("condition", DataType.BOOLEAN, PortDirection.INPUT, "条件"),
        PortDefinition("price", DataType.NUMBER, PortDirection.INPUT,
                       "价格", default_value=None, required=False),
        PortDefinition("quantity", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=100, required=False),
    ]

    OUTPUT_PORTS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"quantity": 100}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "quantity", "type": "int", "label": "买入数量",
             "default": 100, "min": 100, "max": 10000}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        condition = self.get_input_value("condition")
        price = self.get_input_value("price") or "bar.close"
        quantity = self.get_input_value("quantity") or self.parameters.get("quantity", 100)

        code = f"""if {condition}:
    if self.position == 0:
        self.buy({price}, {quantity})"""

        context.add_code(code)
        context.mark_generated(self)
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return ""


class SellNode(BaseNode):
    """卖出节点"""

    CONFIG = NodeConfig(
        node_type="trade.sell",
        category="交易",
        title="卖出",
        description="条件满足时卖出",
        color="#f85149",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("condition", DataType.BOOLEAN, PortDirection.INPUT, "条件"),
        PortDefinition("price", DataType.NUMBER, PortDirection.INPUT,
                       "价格", default_value=None, required=False),
        PortDefinition("quantity", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=None, required=False),
    ]

    OUTPUT_PORTS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {}

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        condition = self.get_input_value("condition")
        price = self.get_input_value("price") or "bar.close"
        quantity = self.get_input_value("quantity")

        if quantity:
            sell_qty = quantity
        else:
            sell_qty = "self.position"

        code = f"""if {condition}:
    if self.position > 0:
        self.sell({price}, {sell_qty})"""

        context.add_code(code)
        context.mark_generated(self)
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return ""


class SellAllNode(BaseNode):
    """全部卖出节点"""

    CONFIG = NodeConfig(
        node_type="trade.sell_all",
        category="交易",
        title="全部卖出",
        description="条件满足时清仓",
        color="#f85149",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("condition", DataType.BOOLEAN, PortDirection.INPUT, "条件"),
        PortDefinition("price", DataType.NUMBER, PortDirection.INPUT,
                       "价格", default_value=None, required=False),
    ]

    OUTPUT_PORTS = []

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        condition = self.get_input_value("condition")
        price = self.get_input_value("price") or "bar.close"

        code = f"""if {condition}:
    if self.position > 0:
        self.sell({price}, self.position)"""

        context.add_code(code)
        context.mark_generated(self)
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return ""


class ConditionalBuyNode(BaseNode):
    """条件买入节点 (无持仓时买入)"""

    CONFIG = NodeConfig(
        node_type="trade.conditional_buy",
        category="交易",
        title="无仓买入",
        description="无持仓且条件满足时买入",
        color="#f85149",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("condition", DataType.BOOLEAN, PortDirection.INPUT, "条件"),
        PortDefinition("price", DataType.NUMBER, PortDirection.INPUT,
                       "价格", default_value=None, required=False),
        PortDefinition("quantity", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=100, required=False),
    ]

    OUTPUT_PORTS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"quantity": 100}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "quantity", "type": "int", "label": "买入数量",
             "default": 100, "min": 100, "max": 10000}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        condition = self.get_input_value("condition")
        price = self.get_input_value("price") or "bar.close"
        quantity = self.get_input_value("quantity") or self.parameters.get("quantity", 100)

        code = f"""if self.position == 0 and {condition}:
    self.buy({price}, {quantity})"""

        context.add_code(code)
        context.mark_generated(self)
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return ""


class ConditionalSellNode(BaseNode):
    """条件卖出节点 (有持仓时卖出)"""

    CONFIG = NodeConfig(
        node_type="trade.conditional_sell",
        category="交易",
        title="有仓卖出",
        description="有持仓且条件满足时卖出",
        color="#f85149",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("condition", DataType.BOOLEAN, PortDirection.INPUT, "条件"),
        PortDefinition("price", DataType.NUMBER, PortDirection.INPUT,
                       "价格", default_value=None, required=False),
    ]

    OUTPUT_PORTS = []

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        condition = self.get_input_value("condition")
        price = self.get_input_value("price") or "bar.close"

        code = f"""if self.position > 0 and {condition}:
    self.sell({price}, self.position)"""

        context.add_code(code)
        context.mark_generated(self)
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return ""


# 导出所有交易节点
TRADE_NODES = [
    BuyNode,
    SellNode,
    SellAllNode,
    ConditionalBuyNode,
    ConditionalSellNode,
]
