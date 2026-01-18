"""
信号节点
提供金叉、死叉等交易信号
"""
from typing import List, Dict

from .base_node import BaseNode, NodeConfig, CodeGenContext
from ..connections.port import PortDefinition, PortDirection
from ..connections.type_system import DataType


class CrossOverNode(BaseNode):
    """金叉信号节点"""

    CONFIG = NodeConfig(
        node_type="signal.cross_over",
        category="信号",
        title="金叉",
        description="快线上穿慢线信号",
        color="#a371f7",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("fast", DataType.SERIES, PortDirection.INPUT, "快线"),
        PortDefinition("slow", DataType.SERIES, PortDirection.INPUT, "慢线"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("signal", DataType.BOOLEAN, PortDirection.OUTPUT, "信号"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        fast = self.get_input_value("fast")
        slow = self.get_input_value("slow")
        var_name = self.get_variable_name("cross_over")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.cross_over({fast}, {slow})[-1]")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        return self.get_variable_name("cross_over")


class CrossUnderNode(BaseNode):
    """死叉信号节点"""

    CONFIG = NodeConfig(
        node_type="signal.cross_under",
        category="信号",
        title="死叉",
        description="快线下穿慢线信号",
        color="#a371f7",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("fast", DataType.SERIES, PortDirection.INPUT, "快线"),
        PortDefinition("slow", DataType.SERIES, PortDirection.INPUT, "慢线"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("signal", DataType.BOOLEAN, PortDirection.OUTPUT, "信号"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        fast = self.get_input_value("fast")
        slow = self.get_input_value("slow")
        var_name = self.get_variable_name("cross_under")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.cross_under({fast}, {slow})[-1]")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        return self.get_variable_name("cross_under")


class BreakUpNode(BaseNode):
    """突破上轨信号节点"""

    CONFIG = NodeConfig(
        node_type="signal.break_up",
        category="信号",
        title="突破上轨",
        description="价格突破上轨信号",
        color="#a371f7",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("price", DataType.NUMBER, PortDirection.INPUT, "价格"),
        PortDefinition("level", DataType.NUMBER, PortDirection.INPUT, "上轨"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("signal", DataType.BOOLEAN, PortDirection.OUTPUT, "信号"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        price = self.get_input_value("price")
        level = self.get_input_value("level")
        var_name = self.get_variable_name("break_up")
        context.add_code(f"{var_name} = ({price} > {level})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        price = self.get_input_value("price")
        level = self.get_input_value("level")
        return f"({price} > {level})"


class BreakDownNode(BaseNode):
    """跌破下轨信号节点"""

    CONFIG = NodeConfig(
        node_type="signal.break_down",
        category="信号",
        title="跌破下轨",
        description="价格跌破下轨信号",
        color="#a371f7",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("price", DataType.NUMBER, PortDirection.INPUT, "价格"),
        PortDefinition("level", DataType.NUMBER, PortDirection.INPUT, "下轨"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("signal", DataType.BOOLEAN, PortDirection.OUTPUT, "信号"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        price = self.get_input_value("price")
        level = self.get_input_value("level")
        var_name = self.get_variable_name("break_down")
        context.add_code(f"{var_name} = ({price} < {level})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        price = self.get_input_value("price")
        level = self.get_input_value("level")
        return f"({price} < {level})"


class OversoldNode(BaseNode):
    """超卖信号节点"""

    CONFIG = NodeConfig(
        node_type="signal.oversold",
        category="信号",
        title="超卖",
        description="指标进入超卖区域",
        color="#a371f7",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("value", DataType.NUMBER, PortDirection.INPUT, "指标值"),
        PortDefinition("threshold", DataType.NUMBER, PortDirection.INPUT,
                       "阈值", default_value=30, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("signal", DataType.BOOLEAN, PortDirection.OUTPUT, "信号"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"threshold": 30}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "threshold", "type": "float", "label": "超卖阈值",
             "default": 30, "min": 0, "max": 100}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        value = self.get_input_value("value")
        threshold = self.get_input_value("threshold") or self.parameters.get("threshold", 30)
        var_name = self.get_variable_name("oversold")
        context.add_code(f"{var_name} = ({value} < {threshold})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        value = self.get_input_value("value")
        threshold = self.get_input_value("threshold") or self.parameters.get("threshold", 30)
        return f"({value} < {threshold})"


class OverboughtNode(BaseNode):
    """超买信号节点"""

    CONFIG = NodeConfig(
        node_type="signal.overbought",
        category="信号",
        title="超买",
        description="指标进入超买区域",
        color="#a371f7",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("value", DataType.NUMBER, PortDirection.INPUT, "指标值"),
        PortDefinition("threshold", DataType.NUMBER, PortDirection.INPUT,
                       "阈值", default_value=70, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("signal", DataType.BOOLEAN, PortDirection.OUTPUT, "信号"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"threshold": 70}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "threshold", "type": "float", "label": "超买阈值",
             "default": 70, "min": 0, "max": 100}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        value = self.get_input_value("value")
        threshold = self.get_input_value("threshold") or self.parameters.get("threshold", 70)
        var_name = self.get_variable_name("overbought")
        context.add_code(f"{var_name} = ({value} > {threshold})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        value = self.get_input_value("value")
        threshold = self.get_input_value("threshold") or self.parameters.get("threshold", 70)
        return f"({value} > {threshold})"


# 导出所有信号节点
SIGNAL_NODES = [
    CrossOverNode,
    CrossUnderNode,
    BreakUpNode,
    BreakDownNode,
    OversoldNode,
    OverboughtNode,
]
