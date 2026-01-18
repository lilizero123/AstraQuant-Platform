"""
指标节点
提供各种技术指标计算
"""
from typing import List, Dict

from .base_node import BaseNode, NodeConfig, CodeGenContext
from ..connections.port import PortDefinition, PortDirection
from ..connections.type_system import DataType


class MANode(BaseNode):
    """简单移动平均线节点"""

    CONFIG = NodeConfig(
        node_type="indicator.ma",
        category="指标",
        title="MA均线",
        description="简单移动平均线",
        color="#3fb950",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("data", DataType.SERIES, PortDirection.INPUT, "数据"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("ma", DataType.SERIES, PortDirection.OUTPUT, "MA序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
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
        data_expr = self.get_input_value("data")
        period = self.get_input_value("period") or self.parameters.get("period", 20)
        var_name = self.get_variable_name("ma")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.MA({data_expr}, {period})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("ma")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class EMANode(BaseNode):
    """指数移动平均线节点"""

    CONFIG = NodeConfig(
        node_type="indicator.ema",
        category="指标",
        title="EMA均线",
        description="指数移动平均线",
        color="#3fb950",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("data", DataType.SERIES, PortDirection.INPUT, "数据"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("ema", DataType.SERIES, PortDirection.OUTPUT, "EMA序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
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
        data_expr = self.get_input_value("data")
        period = self.get_input_value("period") or self.parameters.get("period", 20)
        var_name = self.get_variable_name("ema")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.EMA({data_expr}, {period})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("ema")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class WMANode(BaseNode):
    """加权移动平均线节点"""

    CONFIG = NodeConfig(
        node_type="indicator.wma",
        category="指标",
        title="WMA均线",
        description="加权移动平均线",
        color="#3fb950",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("data", DataType.SERIES, PortDirection.INPUT, "数据"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("wma", DataType.SERIES, PortDirection.OUTPUT, "WMA序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
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
        data_expr = self.get_input_value("data")
        period = self.get_input_value("period") or self.parameters.get("period", 20)
        var_name = self.get_variable_name("wma")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.WMA({data_expr}, {period})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("wma")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class MACDNode(BaseNode):
    """MACD指标节点"""

    CONFIG = NodeConfig(
        node_type="indicator.macd",
        category="指标",
        title="MACD",
        description="MACD指标",
        color="#3fb950",
        width=180
    )

    INPUT_PORTS = [
        PortDefinition("data", DataType.SERIES, PortDirection.INPUT, "数据"),
        PortDefinition("fast", DataType.NUMBER, PortDirection.INPUT,
                       "快线", default_value=12, required=False),
        PortDefinition("slow", DataType.NUMBER, PortDirection.INPUT,
                       "慢线", default_value=26, required=False),
        PortDefinition("signal", DataType.NUMBER, PortDirection.INPUT,
                       "信号", default_value=9, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("dif", DataType.SERIES, PortDirection.OUTPUT, "DIF"),
        PortDefinition("dea", DataType.SERIES, PortDirection.OUTPUT, "DEA"),
        PortDefinition("macd", DataType.SERIES, PortDirection.OUTPUT, "MACD柱"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"fast": 12, "slow": 26, "signal": 9}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "fast", "type": "int", "label": "快线周期",
             "default": 12, "min": 1, "max": 100},
            {"name": "slow", "type": "int", "label": "慢线周期",
             "default": 26, "min": 1, "max": 200},
            {"name": "signal", "type": "int", "label": "信号周期",
             "default": 9, "min": 1, "max": 50},
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        data_expr = self.get_input_value("data")
        fast = self.get_input_value("fast") or self.parameters.get("fast", 12)
        slow = self.get_input_value("slow") or self.parameters.get("slow", 26)
        signal = self.get_input_value("signal") or self.parameters.get("signal", 9)
        var_name = self.get_variable_name("macd_result")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.MACD({data_expr}, {fast}, {slow}, {signal})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("macd_result")
        mapping = {
            "dif": f"{var_name}.dif",
            "dea": f"{var_name}.dea",
            "macd": f"{var_name}.macd",
        }
        return mapping.get(port_name, var_name)


class RSINode(BaseNode):
    """RSI指标节点"""

    CONFIG = NodeConfig(
        node_type="indicator.rsi",
        category="指标",
        title="RSI",
        description="相对强弱指标",
        color="#3fb950",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("data", DataType.SERIES, PortDirection.INPUT, "数据"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=14, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("rsi", DataType.SERIES, PortDirection.OUTPUT, "RSI序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"period": 14}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "period", "type": "int", "label": "周期",
             "default": 14, "min": 1, "max": 100}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        data_expr = self.get_input_value("data")
        period = self.get_input_value("period") or self.parameters.get("period", 14)
        var_name = self.get_variable_name("rsi")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.RSI({data_expr}, {period})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("rsi")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class BOLLNode(BaseNode):
    """布林带指标节点"""

    CONFIG = NodeConfig(
        node_type="indicator.boll",
        category="指标",
        title="布林带",
        description="布林带指标",
        color="#3fb950",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("data", DataType.SERIES, PortDirection.INPUT, "数据"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=20, required=False),
        PortDefinition("std", DataType.NUMBER, PortDirection.INPUT,
                       "标准差", default_value=2.0, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("upper", DataType.SERIES, PortDirection.OUTPUT, "上轨"),
        PortDefinition("middle", DataType.SERIES, PortDirection.OUTPUT, "中轨"),
        PortDefinition("lower", DataType.SERIES, PortDirection.OUTPUT, "下轨"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"period": 20, "std": 2.0}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "period", "type": "int", "label": "周期",
             "default": 20, "min": 1, "max": 200},
            {"name": "std", "type": "float", "label": "标准差倍数",
             "default": 2.0, "min": 0.5, "max": 5.0},
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        data_expr = self.get_input_value("data")
        period = self.get_input_value("period") or self.parameters.get("period", 20)
        std = self.get_input_value("std") or self.parameters.get("std", 2.0)
        var_name = self.get_variable_name("boll")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.BOLL({data_expr}, {period}, {std})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("boll")
        mapping = {
            "upper": f"{var_name}.upper",
            "middle": f"{var_name}.middle",
            "lower": f"{var_name}.lower",
        }
        return mapping.get(port_name, var_name)


class KDJNode(BaseNode):
    """KDJ指标节点"""

    CONFIG = NodeConfig(
        node_type="indicator.kdj",
        category="指标",
        title="KDJ",
        description="KDJ随机指标",
        color="#3fb950",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("high", DataType.SERIES, PortDirection.INPUT, "最高价"),
        PortDefinition("low", DataType.SERIES, PortDirection.INPUT, "最低价"),
        PortDefinition("close", DataType.SERIES, PortDirection.INPUT, "收盘价"),
        PortDefinition("n", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=9, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("k", DataType.SERIES, PortDirection.OUTPUT, "K值"),
        PortDefinition("d", DataType.SERIES, PortDirection.OUTPUT, "D值"),
        PortDefinition("j", DataType.SERIES, PortDirection.OUTPUT, "J值"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"n": 9}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "n", "type": "int", "label": "周期",
             "default": 9, "min": 1, "max": 100},
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        high_expr = self.get_input_value("high")
        low_expr = self.get_input_value("low")
        close_expr = self.get_input_value("close")
        n = self.get_input_value("n") or self.parameters.get("n", 9)
        var_name = self.get_variable_name("kdj")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.KDJ({high_expr}, {low_expr}, {close_expr}, {n})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("kdj")
        mapping = {
            "k": f"{var_name}.k",
            "d": f"{var_name}.d",
            "j": f"{var_name}.j",
        }
        return mapping.get(port_name, var_name)


class ATRNode(BaseNode):
    """ATR指标节点"""

    CONFIG = NodeConfig(
        node_type="indicator.atr",
        category="指标",
        title="ATR",
        description="真实波幅均值",
        color="#3fb950",
        width=160
    )

    INPUT_PORTS = [
        PortDefinition("high", DataType.SERIES, PortDirection.INPUT, "最高价"),
        PortDefinition("low", DataType.SERIES, PortDirection.INPUT, "最低价"),
        PortDefinition("close", DataType.SERIES, PortDirection.INPUT, "收盘价"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=14, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("atr", DataType.SERIES, PortDirection.OUTPUT, "ATR序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"period": 14}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "period", "type": "int", "label": "周期",
             "default": 14, "min": 1, "max": 100},
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        high_expr = self.get_input_value("high")
        low_expr = self.get_input_value("low")
        close_expr = self.get_input_value("close")
        period = self.get_input_value("period") or self.parameters.get("period", 14)
        var_name = self.get_variable_name("atr")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.ATR({high_expr}, {low_expr}, {close_expr}, {period})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("atr")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class CCINode(BaseNode):
    """CCI顺势指标节点"""

    CONFIG = NodeConfig(
        node_type="indicator.cci",
        category="指标",
        title="CCI",
        description="顺势指标判断偏离程度",
        color="#3fb950",
        width=180
    )

    INPUT_PORTS = [
        PortDefinition("high", DataType.SERIES, PortDirection.INPUT, "最高价"),
        PortDefinition("low", DataType.SERIES, PortDirection.INPUT, "最低价"),
        PortDefinition("close", DataType.SERIES, PortDirection.INPUT, "收盘价"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=20, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("cci", DataType.SERIES, PortDirection.OUTPUT, "CCI序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"period": 20}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "period", "type": "int", "label": "周期",
             "default": 20, "min": 1, "max": 200}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        high_expr = self.get_input_value("high")
        low_expr = self.get_input_value("low")
        close_expr = self.get_input_value("close")
        period = self.get_input_value("period") or self.parameters.get("period", 20)
        var_name = self.get_variable_name("cci")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.CCI({high_expr}, {low_expr}, {close_expr}, {period})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("cci")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class OBVNode(BaseNode):
    """OBV能量潮节点"""

    CONFIG = NodeConfig(
        node_type="indicator.obv",
        category="指标",
        title="OBV",
        description="能量潮指标，结合价格与成交量",
        color="#3fb950",
        width=180
    )

    INPUT_PORTS = [
        PortDefinition("close", DataType.SERIES, PortDirection.INPUT, "收盘价"),
        PortDefinition("volume", DataType.SERIES, PortDirection.INPUT, "成交量"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("obv", DataType.SERIES, PortDirection.OUTPUT, "OBV序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        close_expr = self.get_input_value("close")
        volume_expr = self.get_input_value("volume")
        var_name = self.get_variable_name("obv")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.OBV({close_expr}, {volume_expr})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("obv")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class VWAPNode(BaseNode):
    """成交量加权价格节点"""

    CONFIG = NodeConfig(
        node_type="indicator.vwap",
        category="指标",
        title="VWAP",
        description="成交量加权平均价格",
        color="#3fb950",
        width=200
    )

    INPUT_PORTS = [
        PortDefinition("high", DataType.SERIES, PortDirection.INPUT, "最高价"),
        PortDefinition("low", DataType.SERIES, PortDirection.INPUT, "最低价"),
        PortDefinition("close", DataType.SERIES, PortDirection.INPUT, "收盘价"),
        PortDefinition("volume", DataType.SERIES, PortDirection.INPUT, "成交量"),
    ]

    OUTPUT_PORTS = [
        PortDefinition("vwap", DataType.SERIES, PortDirection.OUTPUT, "VWAP序列"),
        PortDefinition("current", DataType.NUMBER, PortDirection.OUTPUT, "当前值"),
    ]

    def get_parameter_definitions(self) -> List[Dict]:
        return []

    def generate_code(self, context: CodeGenContext) -> str:
        high_expr = self.get_input_value("high")
        low_expr = self.get_input_value("low")
        close_expr = self.get_input_value("close")
        volume_expr = self.get_input_value("volume")
        var_name = self.get_variable_name("vwap")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(f"{var_name} = TechnicalIndicators.VWAP({high_expr}, {low_expr}, {close_expr}, {volume_expr})")
        context.mark_generated(self)
        return var_name

    def get_output_expression(self, port_name: str) -> str:
        var_name = self.get_variable_name("vwap")
        if port_name == "current":
            return f"{var_name}[-1]"
        return var_name


class DMINode(BaseNode):
    """DMI动向指标节点"""

    CONFIG = NodeConfig(
        node_type="indicator.dmi",
        category="指标",
        title="DMI",
        description="获得PDI/MDI/ADX三条动向指标",
        color="#3fb950",
        width=220
    )

    INPUT_PORTS = [
        PortDefinition("high", DataType.SERIES, PortDirection.INPUT, "最高价"),
        PortDefinition("low", DataType.SERIES, PortDirection.INPUT, "最低价"),
        PortDefinition("close", DataType.SERIES, PortDirection.INPUT, "收盘价"),
        PortDefinition("period", DataType.NUMBER, PortDirection.INPUT,
                       "周期", default_value=14, required=False),
    ]

    OUTPUT_PORTS = [
        PortDefinition("pdi", DataType.SERIES, PortDirection.OUTPUT, "PDI"),
        PortDefinition("mdi", DataType.SERIES, PortDirection.OUTPUT, "MDI"),
        PortDefinition("adx", DataType.SERIES, PortDirection.OUTPUT, "ADX"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = {"period": 14}

    def get_parameter_definitions(self) -> List[Dict]:
        return [
            {"name": "period", "type": "int", "label": "周期",
             "default": 14, "min": 2, "max": 200}
        ]

    def generate_code(self, context: CodeGenContext) -> str:
        high_expr = self.get_input_value("high")
        low_expr = self.get_input_value("low")
        close_expr = self.get_input_value("close")
        period = self.get_input_value("period") or self.parameters.get("period", 14)
        base_name = self.get_variable_name("dmi")

        context.add_import("from core.indicators.technical import TechnicalIndicators")
        context.add_code(
            f"{base_name}_pdi, {base_name}_mdi, {base_name}_adx = TechnicalIndicators.DMI({high_expr}, {low_expr}, {close_expr}, {period})"
        )
        context.mark_generated(self)
        return base_name

    def get_output_expression(self, port_name: str) -> str:
        base_name = self.get_variable_name("dmi")
        mapping = {
            "pdi": f"{base_name}_pdi",
            "mdi": f"{base_name}_mdi",
            "adx": f"{base_name}_adx",
        }
        return mapping.get(port_name, f"{base_name}_pdi")


# 导出所有指标节点
INDICATOR_NODES = [
    MANode,
    EMANode,
    WMANode,
    MACDNode,
    RSINode,
    BOLLNode,
    KDJNode,
    ATRNode,
    CCINode,
    OBVNode,
    VWAPNode,
    DMINode,
]
