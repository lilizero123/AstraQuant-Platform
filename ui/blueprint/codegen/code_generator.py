"""
代码生成器
将蓝图转换为Python策略代码
"""
from typing import List, Set
from ..nodes.base_node import BaseNode, CodeGenContext
from .graph_analyzer import GraphAnalyzer


class CodeGenerator:
    """
    代码生成器

    将蓝图节点图转换为可执行的Python策略代码
    """

    def __init__(self, nodes: List[BaseNode]):
        self.nodes = nodes
        self.analyzer = GraphAnalyzer(nodes)

    def generate(self, strategy_name: str = "BlueprintStrategy") -> str:
        """
        生成策略代码

        Args:
            strategy_name: 策略类名

        Returns:
            生成的Python代码
        """
        # 验证图
        is_valid, errors = self.analyzer.validate()
        if not is_valid:
            error_msg = "\n".join(f"# 错误: {e}" for e in errors)
            return f'"""\n蓝图验证失败:\n{error_msg}\n"""'

        # 获取执行顺序
        try:
            ordered_nodes = self.analyzer.get_execution_order()
        except ValueError as e:
            return f'"""\n{str(e)}\n"""'

        # 创建代码生成上下文
        context = CodeGenContext()

        # 生成节点代码
        self._generate_nodes_code(ordered_nodes, context)

        # 组装最终代码
        return self._assemble_code(strategy_name, context)

    def _generate_nodes_code(self, nodes: List[BaseNode], context: CodeGenContext):
        """生成所有节点的代码"""
        for node in nodes:
            if not context.is_generated(node):
                # 先生成依赖节点
                self._generate_dependencies(node, context)
                # 生成当前节点 (代码通过context.add_code添加，忽略返回值)
                node.generate_code(context)

    def _generate_dependencies(self, node: BaseNode, context: CodeGenContext):
        """递归生成依赖节点的代码"""
        for port in node.input_ports.values():
            for conn in port.connections:
                if conn.source_port:
                    source_node = conn.source_port.parent_node
                    if not context.is_generated(source_node):
                        self._generate_dependencies(source_node, context)
                        source_node.generate_code(context)

    def _assemble_code(self, strategy_name: str, context: CodeGenContext) -> str:
        """组装最终代码"""
        lines = []

        # 文档字符串
        lines.append('"""')
        lines.append(f'{strategy_name}')
        lines.append('由蓝图可视化编辑器自动生成')
        lines.append('"""')

        # 导入语句
        lines.append('from core.strategy.base import BaseStrategy')
        for imp in sorted(context.imports):
            lines.append(imp)
        lines.append('')
        lines.append('')

        # 类定义
        lines.append(f'class {strategy_name}(BaseStrategy):')
        lines.append(f'    """{strategy_name}"""')
        lines.append('')

        # 策略参数
        params = self._collect_parameters()
        if params:
            lines.append('    # 策略参数')
            for name, value in params.items():
                lines.append(f'    {name} = {repr(value)}')
            lines.append('')

        # on_bar方法
        lines.append('    def on_bar(self, bar):')
        lines.append('        """K线数据回调"""')

        # 数据检查
        min_data = self.analyzer.get_required_data_count()
        if min_data > 1:
            lines.append(f'        # 确保有足够的数据')
            lines.append(f'        if len(self.get_close_prices({min_data})) < {min_data}:')
            lines.append('            return')
            lines.append('')

        # 节点生成的代码
        if context.code_lines:
            for code_line in context.code_lines:
                # 处理多行代码
                for line in code_line.split('\n'):
                    lines.append(f'        {line}')
        else:
            lines.append('        pass')

        lines.append('')

        return '\n'.join(lines)

    def _collect_parameters(self) -> dict:
        """收集所有节点的参数"""
        params = {}
        for node in self.nodes:
            for name, value in node.parameters.items():
                # 使用节点ID前缀避免冲突
                param_name = f"{node.CONFIG.node_type.split('.')[-1]}_{name}"
                params[param_name] = value
        return params

    def generate_preview(self) -> str:
        """
        生成预览代码 (简化版)

        Returns:
            预览代码
        """
        if not self.nodes:
            return "# 在画布上创建节点并连接，代码将自动生成"

        return self.generate()
