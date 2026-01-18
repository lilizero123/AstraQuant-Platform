"""
节点工厂
负责创建和注册所有节点类型
"""
from typing import Dict, List, Type, Optional

from PyQt5.QtCore import QPointF

from .base_node import BaseNode, NodeConfig
from .data_nodes import DATA_NODES
from .indicator_nodes import INDICATOR_NODES
from .logic_nodes import LOGIC_NODES
from .signal_nodes import SIGNAL_NODES
from .trade_nodes import TRADE_NODES
from .param_nodes import PARAM_NODES


class NodeFactory:
    """
    节点工厂

    负责:
    - 注册所有节点类型
    - 根据类型创建节点实例
    - 提供节点分类信息
    """

    def __init__(self):
        # 节点类型注册表: node_type -> node_class
        self._registry: Dict[str, Type[BaseNode]] = {}

        # 分类信息: category -> [node_types]
        self._categories: Dict[str, List[str]] = {}

        # 注册所有内置节点
        self._register_builtin_nodes()

    def _register_builtin_nodes(self):
        """注册所有内置节点"""
        all_nodes = (
            DATA_NODES +
            INDICATOR_NODES +
            LOGIC_NODES +
            SIGNAL_NODES +
            TRADE_NODES +
            PARAM_NODES
        )

        for node_class in all_nodes:
            self.register(node_class)

    def register(self, node_class: Type[BaseNode]):
        """
        注册节点类型

        Args:
            node_class: 节点类
        """
        config = node_class.CONFIG
        if not config:
            raise ValueError(f"Node class {node_class.__name__} has no CONFIG")

        node_type = config.node_type
        category = config.category

        # 注册到类型表
        self._registry[node_type] = node_class

        # 添加到分类
        if category not in self._categories:
            self._categories[category] = []
        if node_type not in self._categories[category]:
            self._categories[category].append(node_type)

    def create_node(self, node_type: str, pos: QPointF = None) -> Optional[BaseNode]:
        """
        创建节点实例

        Args:
            node_type: 节点类型标识
            pos: 初始位置

        Returns:
            节点实例，如果类型不存在返回None
        """
        node_class = self._registry.get(node_type)
        if not node_class:
            return None

        return node_class(pos)

    def get_node_class(self, node_type: str) -> Optional[Type[BaseNode]]:
        """获取节点类"""
        return self._registry.get(node_type)

    def get_node_config(self, node_type: str) -> Optional[NodeConfig]:
        """获取节点配置"""
        node_class = self._registry.get(node_type)
        if node_class:
            return node_class.CONFIG
        return None

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        # 按固定顺序返回
        order = ["数据", "指标", "信号", "逻辑", "交易", "参数"]
        result = []
        for cat in order:
            if cat in self._categories:
                result.append(cat)
        # 添加其他分类
        for cat in self._categories:
            if cat not in result:
                result.append(cat)
        return result

    def get_nodes_in_category(self, category: str) -> List[str]:
        """获取分类下的所有节点类型"""
        return self._categories.get(category, [])

    def get_all_node_types(self) -> List[str]:
        """获取所有节点类型"""
        return list(self._registry.keys())

    def get_node_info(self, node_type: str) -> Optional[Dict]:
        """
        获取节点信息

        Returns:
            {
                "type": "indicator.ma",
                "category": "指标",
                "title": "MA均线",
                "description": "简单移动平均线",
                "color": "#3fb950"
            }
        """
        config = self.get_node_config(node_type)
        if not config:
            return None

        return {
            "type": config.node_type,
            "category": config.category,
            "title": config.title,
            "description": config.description,
            "color": config.color,
        }

    def get_all_nodes_info(self) -> Dict[str, List[Dict]]:
        """
        获取所有节点信息，按分类组织

        Returns:
            {
                "数据": [{"type": "data.bar", "title": "K线数据", ...}, ...],
                "指标": [...],
                ...
            }
        """
        result = {}
        for category in self.get_categories():
            nodes = []
            for node_type in self.get_nodes_in_category(category):
                info = self.get_node_info(node_type)
                if info:
                    nodes.append(info)
            result[category] = nodes
        return result


# 全局节点工厂实例
_factory_instance: Optional[NodeFactory] = None


def get_node_factory() -> NodeFactory:
    """获取全局节点工厂实例"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = NodeFactory()
    return _factory_instance
