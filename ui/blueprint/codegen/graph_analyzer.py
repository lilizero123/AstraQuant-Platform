"""
图分析器
分析蓝图节点图，进行拓扑排序和验证
"""
from typing import List, Dict, Set, Optional, Tuple
from collections import deque

from ..nodes.base_node import BaseNode
from ..connections.port import PortDirection


class GraphAnalyzer:
    """
    图分析器

    功能:
    - 拓扑排序: 确定节点执行顺序
    - 循环检测: 检测图中是否有循环
    - 依赖分析: 分析节点间的依赖关系
    """

    def __init__(self, nodes: List[BaseNode]):
        self.nodes = nodes
        self._node_map: Dict[str, BaseNode] = {n.node_id: n for n in nodes}

    def topological_sort(self) -> Tuple[List[BaseNode], bool]:
        """
        拓扑排序

        Returns:
            (排序后的节点列表, 是否有循环)
        """
        # 计算入度
        in_degree: Dict[str, int] = {n.node_id: 0 for n in self.nodes}
        adjacency: Dict[str, List[str]] = {n.node_id: [] for n in self.nodes}

        for node in self.nodes:
            for port in node.input_ports.values():
                for conn in port.connections:
                    if conn.source_port:
                        source_id = conn.source_port.parent_node.node_id
                        if source_id in adjacency:
                            adjacency[source_id].append(node.node_id)
                            in_degree[node.node_id] += 1

        # Kahn算法
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(self._node_map[node_id])

            for neighbor_id in adjacency[node_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        # 检查是否有循环
        has_cycle = len(result) != len(self.nodes)

        return result, has_cycle

    def detect_cycle(self) -> bool:
        """检测是否有循环"""
        _, has_cycle = self.topological_sort()
        return has_cycle

    def get_dependencies(self, node: BaseNode) -> List[BaseNode]:
        """
        获取节点的所有依赖节点

        Args:
            node: 目标节点

        Returns:
            依赖节点列表
        """
        dependencies = []
        visited = set()

        def dfs(n: BaseNode):
            for port in n.input_ports.values():
                for conn in port.connections:
                    if conn.source_port:
                        source_node = conn.source_port.parent_node
                        if source_node.node_id not in visited:
                            visited.add(source_node.node_id)
                            dependencies.append(source_node)
                            dfs(source_node)

        dfs(node)
        return dependencies

    def get_execution_order(self) -> List[BaseNode]:
        """
        获取执行顺序

        Returns:
            按执行顺序排列的节点列表
        """
        sorted_nodes, has_cycle = self.topological_sort()
        if has_cycle:
            raise ValueError("图中存在循环，无法确定执行顺序")
        return sorted_nodes

    def get_trade_nodes(self) -> List[BaseNode]:
        """获取所有交易节点"""
        return [n for n in self.nodes if n.CONFIG.category == "交易"]

    def get_data_nodes(self) -> List[BaseNode]:
        """获取所有数据节点"""
        return [n for n in self.nodes if n.CONFIG.category == "数据"]

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证图的有效性

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 检查循环
        if self.detect_cycle():
            errors.append("图中存在循环依赖")

        # 检查必需的输入端口是否已连接
        for node in self.nodes:
            for port_name, port in node.input_ports.items():
                if port.definition.required and not port.connections:
                    # 检查是否有默认值
                    if port.definition.default_value is None:
                        errors.append(
                            f"节点 '{node.CONFIG.title}' 的输入端口 '{port.definition.label}' 未连接"
                        )

        # 检查是否有交易节点
        trade_nodes = self.get_trade_nodes()
        if not trade_nodes:
            errors.append("没有交易节点，策略不会执行任何交易")

        return len(errors) == 0, errors

    def get_required_data_count(self) -> int:
        """
        计算策略需要的最小数据量

        Returns:
            需要的K线数量
        """
        max_count = 1

        for node in self.nodes:
            # 检查周期参数
            period = node.parameters.get('period')
            if period:
                max_count = max(max_count, int(period) + 1)

            count = node.parameters.get('count')
            if count:
                max_count = max(max_count, int(count))

            # MACD需要更多数据
            slow = node.parameters.get('slow')
            if slow:
                max_count = max(max_count, int(slow) + 10)

        return max_count
