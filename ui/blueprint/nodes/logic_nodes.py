"""
逻辑节点
提供比较、逻辑运算等功能
"""
from typing import List, Dict

from .base_node import BaseNode, NodeConfig, CodeGenContext
from ..connections.port import PortDefinition, PortDirection
from ..connections.type_system import DataType


class GreaterThanNode(BaseNode):
    """大于比较节点"""

    CONFIG = NodeConfig(
        node_type="logic.greater",
        category="逻辑",
        title="大于 >",
        description="判断A是否大于B",
        color="#58a6ff",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        var_name = self.get_variable_name("gt")
        context.add_code(f"{var_name} = ({a} > {b})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        return f"({a} > {b})"


class LessThanNode(BaseNode):
    """小于比较节点"""

    CONFIG = NodeConfig(
        node_type="logic.less",
        category="逻辑",
        title="小于 <",
        description="判断A是否小于B",
        color="#58a6ff",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        var_name = self.get_variable_name("lt")
        context.add_code(f"{var_name} = ({a} < {b})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        return f"({a} < {b})"


class EqualNode(BaseNode):
    """等于比较节点"""

    CONFIG = NodeConfig(
        node_type="logic.equal",
        category="逻辑",
        title="等于 ==",
        description="判断A是否等于B",
        color="#58a6ff",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        var_name = self.get_variable_name("eq")
        context.add_code(f"{var_name} = ({a} == {b})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        return f"({a} == {b})"


class AndNode(BaseNode):
    """与逻辑节点"""

    CONFIG = NodeConfig(
        node_type="logic.and",
        category="逻辑",
        title="与 AND",
        description="逻辑与运算",
        color="#58a6ff",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.BOOLEAN, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.BOOLEAN, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        var_name = self.get_variable_name("and")
        context.add_code(f"{var_name} = ({a} and {b})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        return f"({a} and {b})"


class OrNode(BaseNode):
    """或逻辑节点"""

    CONFIG = NodeConfig(
        node_type="logic.or",
        category="逻辑",
        title="或 OR",
        description="逻辑或运算",
        color="#58a6ff",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.BOOLEAN, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.BOOLEAN, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        var_name = self.get_variable_name("or")
        context.add_code(f"{var_name} = ({a} or {b})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        return f"({a} or {b})"


class NotNode(BaseNode):
    """非逻辑节点"""

    CONFIG = NodeConfig(
        node_type="logic.not",
        category="逻辑",
        title="非 NOT",
        description="逻辑非运算",
        color="#58a6ff",
        width=120
    )

    INPUT_PORTS = [
        PortDefinition("input", DataType.BOOLEAN, PortDirection.INPUT, "输入"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        input_val = self.get_input_value("input")
        var_name = self.get_variable_name("not")
        context.add_code(f"{var_name} = (not {input_val})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        input_val = self.get_input_value("input")
        return f"(not {input_val})"


class GreaterEqualNode(BaseNode):
    """大于等于比较节点"""

    CONFIG = NodeConfig(
        node_type="logic.greater_equal",
        category="逻辑",
        title="大于等于 >=",
        description="判断A是否大于等于B",
        color="#58a6ff",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        var_name = self.get_variable_name("ge")
        context.add_code(f"{var_name} = ({a} >= {b})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        return f"({a} >= {b})"


class LessEqualNode(BaseNode):
    """小于等于比较节点"""

    CONFIG = NodeConfig(
        node_type="logic.less_equal",
        category="逻辑",
        title="小于等于 <=",
        description="判断A是否小于等于B",
        color="#58a6ff",
        width=140
    )

    INPUT_PORTS = [
        PortDefinition("a", DataType.NUMBER, PortDirection.INPUT, "A"),
        PortDefinition("b", DataType.NUMBER, PortDirection.INPUT, "B"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT, "结果"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        var_name = self.get_variable_name("le")
        context.add_code(f"{var_name} = ({a} <= {b})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        a = self.get_input_value("a")
        b = self.get_input_value("b")
        return f"({a} <= {b})"


# 导出所有逻辑节点
LOGIC_NODES = [
    GreaterThanNode,
    LessThanNode,
    EqualNode,
    GreaterEqualNode,
    LessEqualNode,
    AndNode,
    OrNode,
    NotNode,
]
