"""
参数节点
提供常量数值、周期等参数输入
"""
from typing import List, Dict

from .base_node import BaseNode, NodeConfig, CodeGenContext
from ..connections.port import PortDefinition, PortDirection
from ..connections.type_system import DataType


class NumberNode(BaseNode):
    """数值常量节点"""

    CONFIG = NodeConfig(
        node_type="param.number",
        category="参数",
        title="数值",
        description="常量数值",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = []

    OUTPUT_PORTS = [
        PortDefinition("value", DataType.NUMBER, PortDirection.OUTPUT, "值"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"value": 0}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "value", "type": "float", "label": "数值",
             "default": 0, "min": -999999, "max": 999999}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return str(self.parameters.get("value", 0))


class PeriodNode(BaseNode):
    """周期参数节点"""

    CONFIG = NodeConfig(
        node_type="param.period",
        category="参数",
        title="周期",
        description="周期参数",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = []

    OUTPUT_PORTS = [
        PortDefinition("period", DataType.NUMBER, PortDirection.OUTPUT, "周期"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"period": 20}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "period", "type": "int", "label": "周期",
             "default": 20, "min": 1, "max": 500}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return str(self.parameters.get("period", 20))


class QuantityNode(BaseNode):
    """数量参数节点"""

    CONFIG = NodeConfig(
        node_type="param.quantity",
        category="参数",
        title="数量",
        description="交易数量",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = []

    OUTPUT_PORTS = [
        PortDefinition("quantity", DataType.NUMBER, PortDirection.OUTPUT, "数量"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"quantity": 100}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "quantity", "type": "int", "label": "数量",
             "default": 100, "min": 100, "max": 100000}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return str(self.parameters.get("quantity", 100))


class PercentNode(BaseNode):
    """百分比参数节点"""

    CONFIG = NodeConfig(
        node_type="param.percent",
        category="参数",
        title="百分比",
        description="百分比参数",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = []

    OUTPUT_PORTS = [
        PortDefinition("percent", DataType.NUMBER, PortDirection.OUTPUT, "百分比"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"percent": 5.0}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "percent", "type": "float", "label": "百分比",
             "default": 5.0, "min": 0, "max": 100}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        return str(self.parameters.get("percent", 5.0))


class MathAddNode(BaseNode):
    """加法节点"""

    CONFIG = NodeConfig(
        node_type="param.add",
        category="参数",
        title="加法 +",
        description="A + B",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.NUMBER, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a") or "0"
        b = self.get_input_value("b") or "0"
        return f"({a} + {b})"


class MathSubNode(BaseNode):
    """减法节点"""

    CONFIG = NodeConfig(
        node_type="param.sub",
        category="参数",
        title="减法 -",
        description="A - B",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.NUMBER, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a") or "0"
        b = self.get_input_value("b") or "0"
        return f"({a} - {b})"


class MathMulNode(BaseNode):
    """乘法节点"""

    CONFIG = NodeConfig(
        node_type="param.mul",
        category="参数",
        title="乘法 ×",
        description="A × B",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.NUMBER, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a") or "0"
        b = self.get_input_value("b") or "0"
        return f"({a} * {b})"


class MathDivNode(BaseNode):
    """除法节点"""

    CONFIG = NodeConfig(
        node_type="param.div",
        category="参数",
        title="除法 ÷",
        description="A ÷ B",
        color="#8b949e",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.NUMBER, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a") or "0"
        b = self.get_input_value("b") or "1"
        return f"({a} / {b})"


class GetLastNode(BaseNode):
    """获取序列最后一个值节点"""

    CONFIG = NodeConfig(
        node_type="param.get_last",
        category="参数",
        title="取最新值",
        description="获取序列最后一个值",
        color="#8b949e",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("series", DataType.SERIES, PortDirection.INPUT, "序列"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("value", DataType.NUMBER, PortDirection.OUTPUT, "值"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        series = self.get_input_value("series")
        return f"{series}[-1]"


# 导出所有参数节点
PARAM_NODES = [
    NumberNode,
    PeriodNode,
    QuantityNode,
    PercentNode,
    MathAddNode,
    MathSubNode,
    MathMulNode,
    MathDivNode,
    GetLastNode,
]
