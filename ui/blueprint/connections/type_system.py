"""
蓝图数据类型系统
定义节点端口的数据类型和类型兼容性检查
"""
from enum import Enum, auto
from typing import Dict, List


class DataType(Enum):
    """蓝图数据类型"""
    NUMBER = auto()      # 单个数值 (float/int)
    BOOLEAN = auto()     # 布尔值 (True/False)
    SERIES = auto()      # 数值序列 (价格序列、指标值)
    BAR = auto()         # 单根K线数据
    ANY = auto()         # 任意类型
    EXEC = auto()        # 执行流 (控制流，无数据)


# 类型对应的颜色
TYPE_COLORS: Dict[DataType, str] = {
    DataType.NUMBER: "#58a6ff",      # 蓝色
    DataType.BOOLEAN: "#f85149",     # 红色
    DataType.SERIES: "#3fb950",      # 绿色
    DataType.BAR: "#d29922",         # 黄色
    DataType.ANY: "#8b949e",         # 灰色
    DataType.EXEC: "#ffffff",        # 白色
}

# 类型中文名称
TYPE_NAMES: Dict[DataType, str] = {
    DataType.NUMBER: "数值",
    DataType.BOOLEAN: "布尔",
    DataType.SERIES: "序列",
    DataType.BAR: "K线",
    DataType.ANY: "任意",
    DataType.EXEC: "执行",
}

# 类型兼容性矩阵
# key: 源类型, value: 可以连接到的目标类型列表
TYPE_COMPATIBILITY: Dict[DataType, List[DataType]] = {
    DataType.NUMBER: [DataType.NUMBER, DataType.ANY],
    DataType.BOOLEAN: [DataType.BOOLEAN, DataType.ANY],
    DataType.SERIES: [DataType.SERIES, DataType.ANY],
    DataType.BAR: [DataType.BAR, DataType.ANY],
    DataType.ANY: [DataType.NUMBER, DataType.BOOLEAN, DataType.SERIES,
                   DataType.BAR, DataType.ANY],
    DataType.EXEC: [DataType.EXEC],
}


def can_connect(source_type: DataType, target_type: DataType) -> bool:
    """
    检查两个类型是否可以连接

    Args:
        source_type: 源端口类型 (输出端口)
        target_type: 目标端口类型 (输入端口)

    Returns:
        是否可以连接
    """
    # ANY类型可以接受任何类型
    if target_type == DataType.ANY:
        return True

    # 检查兼容性矩阵
    compatible_types = TYPE_COMPATIBILITY.get(source_type, [])
    return target_type in compatible_types


def get_type_color(data_type: DataType) -> str:
    """获取类型对应的颜色"""
    return TYPE_COLORS.get(data_type, "#8b949e")


def get_type_name(data_type: DataType) -> str:
    """获取类型的中文名称"""
    return TYPE_NAMES.get(data_type, "未知")
