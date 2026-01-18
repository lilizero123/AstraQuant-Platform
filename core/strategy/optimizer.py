"""
策略参数优化模块
提供网格搜索、参数敏感性分析等功能
"""
import itertools
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Type, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from core.strategy.base import BaseStrategy
from core.backtest.engine import BacktestEngine, BacktestResult
from core.logger import get_log_manager, LogCategory


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict[str, Any]
    best_score: float
    best_result: BacktestResult
    all_results: List[Dict] = field(default_factory=list)
    optimization_time: float = 0.0


@dataclass
class ParameterRange:
    """参数范围定义"""
    name: str
    start: float
    end: float
    step: float

    def get_values(self) -> List[float]:
        """获取参数值列表"""
        values = []
        current = self.start
        while current <= self.end:
            values.append(current)
            current += self.step
        return values


class StrategyOptimizer:
    """策略优化器"""

    def __init__(self, strategy_class: Type[BaseStrategy], data: Dict[str, pd.DataFrame]):
        """
        初始化优化器

        Args:
            strategy_class: 策略类
            data: 回测数据 {股票代码: DataFrame}
        """
        self.strategy_class = strategy_class
        self.data = data
        self.logger = get_log_manager()

        # 回测配置
        self.initial_capital = 1000000.0
        self.commission_rate = 0.0003
        self.slippage = 0.001

        # 优化配置
        self.score_func: Callable[[BacktestResult], float] = self._default_score
        self.max_workers = 4  # 并行线程数

    def set_backtest_config(self, initial_capital: float = None,
                            commission_rate: float = None,
                            slippage: float = None):
        """设置回测配置"""
        if initial_capital is not None:
            self.initial_capital = initial_capital
        if commission_rate is not None:
            self.commission_rate = commission_rate
        if slippage is not None:
            self.slippage = slippage

    def set_score_function(self, func: Callable[[BacktestResult], float]):
        """
        设置评分函数

        Args:
            func: 评分函数，接收BacktestResult，返回分数（越高越好）
        """
        self.score_func = func

    def _default_score(self, result: BacktestResult) -> float:
        """默认评分函数：夏普比率"""
        return result.sharpe_ratio

    def _run_backtest(self, params: Dict[str, Any]) -> Tuple[Dict[str, Any], BacktestResult, float]:
        """运行单次回测"""
        try:
            # 创建策略实例
            strategy = self.strategy_class()

            # 设置参数
            for key, value in params.items():
                if hasattr(strategy, key):
                    setattr(strategy, key, value)

            # 创建回测引擎
            engine = BacktestEngine()
            engine.set_strategy(strategy)
            engine.set_capital(self.initial_capital)
            engine.set_commission(self.commission_rate)
            engine.set_slippage(self.slippage)

            # 添加数据
            for code, df in self.data.items():
                engine.add_data(code, df.copy())

            # 运行回测
            result = engine.run()

            # 计算分数
            score = self.score_func(result)

            return params, result, score

        except Exception as e:
            self.logger.error(f"回测失败: {params}, 错误: {e}", LogCategory.STRATEGY)
            return params, None, float('-inf')

    def grid_search(self, param_ranges: List[ParameterRange],
                    parallel: bool = True) -> OptimizationResult:
        """
        网格搜索优化

        Args:
            param_ranges: 参数范围列表
            parallel: 是否并行执行

        Returns:
            优化结果
        """
        start_time = datetime.now()

        # 生成所有参数组合
        param_names = [p.name for p in param_ranges]
        param_values = [p.get_values() for p in param_ranges]
        all_combinations = list(itertools.product(*param_values))

        total = len(all_combinations)
        self.logger.info(f"开始网格搜索，共 {total} 个参数组合", LogCategory.STRATEGY)

        all_results = []
        best_params = None
        best_score = float('-inf')
        best_result = None

        if parallel and total > 1:
            # 并行执行
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for combo in all_combinations:
                    params = dict(zip(param_names, combo))
                    future = executor.submit(self._run_backtest, params)
                    futures[future] = params

                completed = 0
                for future in as_completed(futures):
                    params, result, score = future.result()
                    completed += 1

                    if result is not None:
                        all_results.append({
                            'params': params,
                            'score': score,
                            'total_return': result.total_return,
                            'max_drawdown': result.max_drawdown,
                            'sharpe_ratio': result.sharpe_ratio,
                            'win_rate': result.win_rate
                        })

                        if score > best_score:
                            best_score = score
                            best_params = params
                            best_result = result

                    if completed % 10 == 0:
                        self.logger.info(f"进度: {completed}/{total}", LogCategory.STRATEGY)
        else:
            # 串行执行
            for i, combo in enumerate(all_combinations):
                params = dict(zip(param_names, combo))
                params, result, score = self._run_backtest(params)

                if result is not None:
                    all_results.append({
                        'params': params,
                        'score': score,
                        'total_return': result.total_return,
                        'max_drawdown': result.max_drawdown,
                        'sharpe_ratio': result.sharpe_ratio,
                        'win_rate': result.win_rate
                    })

                    if score > best_score:
                        best_score = score
                        best_params = params
                        best_result = result

                if (i + 1) % 10 == 0:
                    self.logger.info(f"进度: {i + 1}/{total}", LogCategory.STRATEGY)

        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"网格搜索完成，耗时 {elapsed:.2f} 秒", LogCategory.STRATEGY)

        return OptimizationResult(
            best_params=best_params or {},
            best_score=best_score,
            best_result=best_result,
            all_results=all_results,
            optimization_time=elapsed
        )

    def random_search(self, param_ranges: List[ParameterRange],
                      n_iterations: int = 100) -> OptimizationResult:
        """
        随机搜索优化

        Args:
            param_ranges: 参数范围列表
            n_iterations: 迭代次数

        Returns:
            优化结果
        """
        start_time = datetime.now()

        self.logger.info(f"开始随机搜索，共 {n_iterations} 次迭代", LogCategory.STRATEGY)

        all_results = []
        best_params = None
        best_score = float('-inf')
        best_result = None

        for i in range(n_iterations):
            # 随机生成参数
            params = {}
            for p in param_ranges:
                if isinstance(p.step, int) or p.step == int(p.step):
                    # 整数参数
                    params[p.name] = np.random.randint(int(p.start), int(p.end) + 1)
                else:
                    # 浮点参数
                    params[p.name] = np.random.uniform(p.start, p.end)

            params_result, result, score = self._run_backtest(params)

            if result is not None:
                all_results.append({
                    'params': params_result,
                    'score': score,
                    'total_return': result.total_return,
                    'max_drawdown': result.max_drawdown,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate
                })

                if score > best_score:
                    best_score = score
                    best_params = params_result
                    best_result = result

            if (i + 1) % 20 == 0:
                self.logger.info(f"进度: {i + 1}/{n_iterations}", LogCategory.STRATEGY)

        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"随机搜索完成，耗时 {elapsed:.2f} 秒", LogCategory.STRATEGY)

        return OptimizationResult(
            best_params=best_params or {},
            best_score=best_score,
            best_result=best_result,
            all_results=all_results,
            optimization_time=elapsed
        )

    def sensitivity_analysis(self, base_params: Dict[str, Any],
                             param_name: str,
                             param_range: ParameterRange) -> pd.DataFrame:
        """
        参数敏感性分析

        Args:
            base_params: 基准参数
            param_name: 要分析的参数名
            param_range: 参数范围

        Returns:
            分析结果DataFrame
        """
        self.logger.info(f"开始参数敏感性分析: {param_name}", LogCategory.STRATEGY)

        results = []
        values = param_range.get_values()

        for value in values:
            params = base_params.copy()
            params[param_name] = value

            _, result, score = self._run_backtest(params)

            if result is not None:
                results.append({
                    param_name: value,
                    'score': score,
                    'total_return': result.total_return,
                    'annual_return': result.annual_return,
                    'max_drawdown': result.max_drawdown,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades
                })

        df = pd.DataFrame(results)
        self.logger.info(f"敏感性分析完成: {param_name}", LogCategory.STRATEGY)

        return df

    def walk_forward_optimization(self, param_ranges: List[ParameterRange],
                                  train_ratio: float = 0.7,
                                  n_splits: int = 5) -> List[OptimizationResult]:
        """
        滚动优化（Walk-Forward Optimization）

        Args:
            param_ranges: 参数范围列表
            train_ratio: 训练集比例
            n_splits: 分割数量

        Returns:
            每个分割的优化结果列表
        """
        self.logger.info(f"开始滚动优化，{n_splits} 个分割", LogCategory.STRATEGY)

        results = []

        # 获取数据长度
        first_code = list(self.data.keys())[0]
        total_len = len(self.data[first_code])
        split_size = total_len // n_splits

        for i in range(n_splits):
            start_idx = i * split_size
            end_idx = min((i + 2) * split_size, total_len)  # 包含下一个周期

            if end_idx - start_idx < split_size:
                break

            train_end = start_idx + int((end_idx - start_idx) * train_ratio)

            # 分割数据
            train_data = {}
            test_data = {}
            for code, df in self.data.items():
                train_data[code] = df.iloc[start_idx:train_end].reset_index(drop=True)
                test_data[code] = df.iloc[train_end:end_idx].reset_index(drop=True)

            # 在训练集上优化
            optimizer = StrategyOptimizer(self.strategy_class, train_data)
            optimizer.set_backtest_config(
                self.initial_capital, self.commission_rate, self.slippage
            )
            optimizer.set_score_function(self.score_func)

            train_result = optimizer.grid_search(param_ranges, parallel=False)

            # 在测试集上验证
            if train_result.best_params:
                test_optimizer = StrategyOptimizer(self.strategy_class, test_data)
                test_optimizer.set_backtest_config(
                    self.initial_capital, self.commission_rate, self.slippage
                )

                _, test_backtest_result, test_score = test_optimizer._run_backtest(
                    train_result.best_params
                )

                train_result.best_result = test_backtest_result
                train_result.best_score = test_score

            results.append(train_result)
            self.logger.info(f"分割 {i + 1}/{n_splits} 完成", LogCategory.STRATEGY)

        return results


class ScoreFunctions:
    """常用评分函数"""

    @staticmethod
    def sharpe_ratio(result: BacktestResult) -> float:
        """夏普比率"""
        return result.sharpe_ratio

    @staticmethod
    def total_return(result: BacktestResult) -> float:
        """总收益率"""
        return result.total_return

    @staticmethod
    def calmar_ratio(result: BacktestResult) -> float:
        """卡玛比率"""
        return result.calmar_ratio

    @staticmethod
    def risk_adjusted_return(result: BacktestResult) -> float:
        """风险调整收益（收益/回撤）"""
        if result.max_drawdown > 0:
            return result.total_return / result.max_drawdown
        return result.total_return

    @staticmethod
    def profit_factor(result: BacktestResult) -> float:
        """盈利因子"""
        if result.avg_loss != 0:
            return abs(result.avg_profit * result.win_trades /
                       (result.avg_loss * result.loss_trades)) if result.loss_trades > 0 else float('inf')
        return float('inf') if result.avg_profit > 0 else 0

    @staticmethod
    def combined_score(result: BacktestResult) -> float:
        """综合评分"""
        # 综合考虑收益、风险、胜率
        score = 0

        # 收益贡献 (40%)
        score += result.total_return * 0.4

        # 夏普比率贡献 (30%)
        score += result.sharpe_ratio * 10 * 0.3

        # 胜率贡献 (15%)
        score += result.win_rate * 0.15

        # 回撤惩罚 (15%)
        score -= result.max_drawdown * 0.15

        return score
