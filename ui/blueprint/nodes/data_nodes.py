"""
数据节点
提供K线数据、价格序列、持仓信息等
"""
from typing import List, Dict

from .base_node import BaseNode, NodeConfig, CodeGenContext
from ..connections.port import PortDefinition, PortDirection
from ..connections.type_system import DataType


class BarDataNode(BaseNode):
    """K线数据节点 - 获取当前K线"""

    CONFIG = NodeConfig(
        node_type="data.bar",
        category="数据",
        title="K线数据",
        description="获取当前K线的开高低收量数据",
        color="#d29922",
        width=140
    )

    INPUT_PORTS = []

    OUTPUT_PORTS = [
        PortDefinition("open", DataType.NUMBER, PortDirection.OUTPUT, "开盘价"),
        PortDefinition("high", DataType.NUMBER, PortDirection.OUTPUT, "最高价"),
        PortDefinition("low", DataType.NUMBER, PortDirection.OUTPUT, "最低价"),
        PortDefinition("close", DataType.NUMBER, PortDirection.OUTPUT, "收盘价"),
        PortDefinition("volume", DataType.NUMBER, PortDirection.OUTPUT, "成交量"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""  # 不需要生成代码，直接使用bar参数

    def get_output_expression(self, port_name: str) -> str:
        mapping = {
            "open": "bar.open",
            "high": "bar.high",
            "low": "bar.low",
            "close": "bar.close",
            "volume": "bar.volume",
        }
        return mapping.get(port_name, "bar.close")


class ClosePricesNode(BaseNode):
    """收盘价序列节点 - 获取历史收盘价"""

    CONFIG = NodeConfig(
        node_type="data.close_prices",
        category="数据",
        title="收盘价序列",
        description="获取最近N个收盘价",
        color="#d29922",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("count", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("prices", DataType.SERIES, PortDirection.OUTPUT, "价格序列"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"count": 20}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "count", "type": "int", "label": "数量",
             "default": 20, "min": 1, "max": 500}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        count = self.get_input_value("count") or self.parameters.get("count", 20)
        var_name = self.get_variable_name("closes")
        context.add_code(f"{var_name} = self.get_close_prices({count})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        return self.get_variable_name("closes")


class HighPricesNode(BaseNode):
    """最高价序列节点"""

    CONFIG = NodeConfig(
        node_type="data.high_prices",
        category="数据",
        title="最高价序列",
        description="获取最近N个最高价",
        color="#d29922",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("count", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("prices", DataType.SERIES, PortDirection.OUTPUT, "价格序列"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"count": 20}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "count", "type": "int", "label": "数量",
             "default": 20, "min": 1, "max": 500}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        count = self.get_input_value("count") or self.parameters.get("count", 20)
        var_name = self.get_variable_name("highs")
        context.add_code(f"{var_name} = [b.high for b in self.get_bars({count})]")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        return self.get_variable_name("highs")


class LowPricesNode(BaseNode):
    """最低价序列节点"""

    CONFIG = NodeConfig(
        node_type="data.low_prices",
        category="数据",
        title="最低价序列",
        description="获取最近N个最低价",
        color="#d29922",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("count", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("prices", DataType.SERIES, PortDirection.OUTPUT, "价格序列"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"count": 20}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "count", "type": "int", "label": "数量",
             "default": 20, "min": 1, "max": 500}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        count = self.get_input_value("count") or self.parameters.get("count", 20)
        var_name = self.get_variable_name("lows")
        context.add_code(f"{var_name} = [b.low for b in self.get_bars({count})]")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        return self.get_variable_name("lows")


class OpenPricesNode(BaseNode):
    """开盘价序列节点"""

    CONFIG = NodeConfig(
        node_type="data.open_prices",
        category="数据",
        title="开盘价序列",
        description="获取最近N个开盘价",
        color="#d29922",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("count", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("prices", DataType.SERIES, PortDirection.OUTPUT, "价格序列"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"count": 20}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "count", "type": "int", "label": "数量",
             "default": 20, "min": 1, "max": 500}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        count = self.get_input_value("count") or self.parameters.get("count", 20)
        var_name = self.get_variable_name("opens")
        context.add_code(f"{var_name} = [b.open for b in self.get_bars({count})]")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        return self.get_variable_name("opens")


class PositionNode(BaseNode):
    """持仓信息节点"""

    CONFIG = NodeConfig(
        node_type="data.position",
        category="数据",
        title="持仓信息",
        description="获取当前持仓数量",
        color="#d29922",
        width=140
    )

    INPUT_PORTS = []

    OUTPUT_PORTS = [
        PortDefinition("quantity", DataType.NUMBER, PortDirection.OUTPUT, "持仓数量"),
        PortDefinition("has_position", DataType.BOOLEAN, PortDirection.OUTPUT, "有持仓"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        if port_name == "quantity":
            return "self.position"
        elif port_name == "has_position":
            return "(self.position > 0)"
        return "self.position"


class CashNode(BaseNode):
    """资金信息节点"""

    CONFIG = NodeConfig(
        node_type="data.cash",
        category="数据",
        title="资金信息",
        description="获取可用资金",
        color="#d29922",
        width=140
    )

    INPUT_PORTS = []

    OUTPUT_PORTS = [
        PortDefinition("cash", DataType.NUMBER, PortDirection.OUTPUT, "可用资金"),
        PortDefinition("total", DataType.NUMBER, PortDirection.OUTPUT, "总资产"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        return ""

    def get_output_expression(self, port_name: str) -> str:
        if port_name == "cash":
            return "self.cash"
        elif port_name == "total":
            return "self.total_value"
        return "self.cash"


class VolumeSeriesNode(BaseNode):
    """成交量序列节点"""

    CONFIG = NodeConfig(
        node_type="data.volume_series",
        category="数据",
        title="成交量序列",
        description="获取最近N个成交量",
        color="#d29922",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("count", DataType.NUMBER, PortDirection.INPUT,
                       "数量", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("volumes", DataType.SERIES, PortDirection.OUTPUT, "成交量序列"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"count": 20}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "count", "type": "int", "label": "数量",
             "default": 20, "min": 1, "max": 500}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        count = self.get_input_value("count") or self.parameters.get("count", 20)
        var_name = self.get_variable_name("volumes")
        context.add_code(f"{var_name} = [b.volume for b in self.get_bars({count})]")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        return self.get_variable_name("volumes")


# 导出所有数据节点
DATA_NODES = [
    BarDataNode,
    ClosePricesNode,
    HighPricesNode,
    LowPricesNode,
    PositionNode,
    CashNode,
    OpenPricesNode,
    VolumeSeriesNode,
]
