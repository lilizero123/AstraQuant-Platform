"""
策略管理模块
提供策略的保存、加载、验证等功能
"""
import os
import sys
import ast
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass

from config.settings import config_manager
from core.strategy.base import BaseStrategy
from core.database.db_manager import DatabaseManager
from core.logger import get_log_manager, LogCategory


@dataclass
class StrategyInfo:
    """策略信息"""
    name: str
    code: str
    parameters: Dict[str, Any]
    description: str
    created_at: str
    updated_at: str
    file_path: Optional[str] = None


class StrategyValidator:
    """策略代码验证器"""

    @staticmethod
    def validate_syntax(code: str) -> tuple:
        """
        验证Python语法

        Returns:
            (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"语法错误 (行 {e.lineno}): {e.msg}"

    @staticmethod
    def validate_structure(code: str) -> tuple:
        """
        验证策略结构

        Returns:
            (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)

            # 检查是否有类定义
            class_defs = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            if not class_defs:
                return False, "策略代码必须包含一个类定义"

            # 检查是否继承BaseStrategy
            has_base_strategy = False
            strategy_class = None
            for cls in class_defs:
                for base in cls.bases:
                    if isinstance(base, ast.Name) and base.id == 'BaseStrategy':
                        has_base_strategy = True
                        strategy_class = cls
                        break
                    elif isinstance(base, ast.Attribute) and base.attr == 'BaseStrategy':
                        has_base_strategy = True
                        strategy_class = cls
                        break

            if not has_base_strategy:
                return False, "策略类必须继承 BaseStrategy"

            # 检查是否实现on_bar方法
            if strategy_class:
                methods = [node.name for node in strategy_class.body if isinstance(node, ast.FunctionDef)]
                if 'on_bar' not in methods:
                    return False, "策略类必须实现 on_bar 方法"

            return True, ""

        except Exception as e:
            return False, f"验证失败: {str(e)}"

    @staticmethod
    def validate(code: str) -> tuple:
        """
        完整验证

        Returns:
            (is_valid, error_message)
        """
        # 语法验证
        is_valid, error = StrategyValidator.validate_syntax(code)
        if not is_valid:
            return False, error

        # 结构验证
        is_valid, error = StrategyValidator.validate_structure(code)
        if not is_valid:
            return False, error

        return True, "验证通过"


class StrategyManager:
    """策略管理器"""

    def __init__(self, strategy_dir: str = None, db_manager: DatabaseManager = None):
        """
        初始化策略管理器

        Args:
            strategy_dir: 策略文件目录
            db_manager: 数据库管理器
        """
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent.parent

        if strategy_dir is None:
            config_path = None
            try:
                config_path = config_manager.get("strategy_path", None)
            except Exception:
                config_path = None

            if config_path:
                candidate = Path(config_path)
                strategy_dir = candidate if candidate.is_absolute() else base_dir / candidate
            else:
                strategy_dir = base_dir / "strategies"
        else:
            strategy_dir = Path(strategy_dir)
            if not strategy_dir.is_absolute():
                strategy_dir = base_dir / strategy_dir

        self.strategy_dir = strategy_dir
        self.strategy_dir.mkdir(parents=True, exist_ok=True)

        self.db_manager = db_manager or DatabaseManager()
        self.logger = get_log_manager()

        # 已加载的策略类缓存
        self._strategy_classes: Dict[str, Type[BaseStrategy]] = {}

        # 内置策略模板
        self._templates = self._init_templates()

    def _init_templates(self) -> Dict[str, str]:
        """初始化策略模板"""
        return {
            "双均线策略": '''"""
双均线交叉策略
当快线上穿慢线时买入，下穿时卖出
"""
from core.strategy.base import BaseStrategy, Bar


class DualMAStrategy(BaseStrategy):
    """双均线策略"""

    # 策略参数
    fast_period = 5   # 快线周期
    slow_period = 20  # 慢线周期

    def on_bar(self, bar: Bar):
        # 获取历史收盘价
        closes = self.get_close_prices(self.slow_period + 1)
        if len(closes) < self.slow_period:
            return

        # 计算均线
        fast_ma = sum(closes[-self.fast_period:]) / self.fast_period
        slow_ma = sum(closes[-self.slow_period:]) / self.slow_period

        # 计算前一根K线的均线
        prev_closes = closes[:-1]
        prev_fast_ma = sum(prev_closes[-self.fast_period:]) / self.fast_period
        prev_slow_ma = sum(prev_closes[-self.slow_period:]) / self.slow_period

        # 金叉买入
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"金叉买入: 价格={bar.close:.2f}, 数量={quantity}")

        # 死叉卖出
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"死叉卖出: 价格={bar.close:.2f}, 数量={self.position}")
''',

            "MACD策略": '''"""
MACD策略
基于MACD指标的金叉死叉进行交易
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class MACDStrategy(BaseStrategy):
    """MACD策略"""

    # 策略参数
    fast_period = 12
    slow_period = 26
    signal_period = 9

    def on_bar(self, bar: Bar):
        # 获取足够的历史数据
        bars = self.get_bars(self.slow_period + self.signal_period + 10)
        if len(bars) < self.slow_period + self.signal_period:
            return

        # 计算MACD
        closes = [b.close for b in bars]
        macd_result = TechnicalIndicators.MACD(
            closes, self.fast_period, self.slow_period, self.signal_period
        )

        # 获取当前和前一个MACD值
        dif = macd_result.dif
        dea = macd_result.dea

        if len(dif) < 2:
            return

        # 金叉买入 (DIF上穿DEA)
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"MACD金叉买入: DIF={dif[-1]:.4f}, DEA={dea[-1]:.4f}")

        # 死叉卖出 (DIF下穿DEA)
        elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"MACD死叉卖出: DIF={dif[-1]:.4f}, DEA={dea[-1]:.4f}")
''',

            "KDJ策略": '''"""
KDJ策略
基于KDJ指标的超买超卖进行交易
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class KDJStrategy(BaseStrategy):
    """KDJ策略"""

    # 策略参数
    n = 9
    m1 = 3
    m2 = 3
    oversold = 20    # 超卖线
    overbought = 80  # 超买线

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.n + 10)
        if len(bars) < self.n + 2:
            return

        # 计算KDJ
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        closes = [b.close for b in bars]

        kdj = TechnicalIndicators.KDJ(highs, lows, closes, self.n, self.m1, self.m2)

        k, d, j = kdj.k[-1], kdj.d[-1], kdj.j[-1]
        prev_k, prev_d = kdj.k[-2], kdj.d[-2]

        # J值从超卖区上穿，买入
        if j < self.oversold and prev_k <= prev_d and k > d:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"KDJ超卖买入: K={k:.2f}, D={d:.2f}, J={j:.2f}")

        # J值从超买区下穿，卖出
        elif j > self.overbought and prev_k >= prev_d and k < d:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"KDJ超买卖出: K={k:.2f}, D={d:.2f}, J={j:.2f}")
''',

            "布林带策略": '''"""
布林带策略
价格触及下轨买入，触及上轨卖出
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class BollStrategy(BaseStrategy):
    """布林带策略"""

    # 策略参数
    period = 20
    std_dev = 2.0

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.period + 5)
        if len(bars) < self.period:
            return

        # 计算布林带
        closes = [b.close for b in bars]
        boll = TechnicalIndicators.BOLL(closes, self.period, self.std_dev)

        upper = boll.upper[-1]
        middle = boll.middle[-1]
        lower = boll.lower[-1]

        # 价格触及下轨，买入
        if bar.close <= lower:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"触及下轨买入: 价格={bar.close:.2f}, 下轨={lower:.2f}")

        # 价格触及上轨，卖出
        elif bar.close >= upper:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"触及上轨卖出: 价格={bar.close:.2f}, 上轨={upper:.2f}")

        # 价格回归中轨，可选择平仓
        elif self.position > 0 and bar.close >= middle:
            # 可以选择在中轨附近减仓
            pass
''',

            "RSI策略": '''"""
RSI策略
基于RSI指标的超买超卖进行交易
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class RSIStrategy(BaseStrategy):
    """RSI策略"""

    # 策略参数
    period = 14
    oversold = 30    # 超卖线
    overbought = 70  # 超买线

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.period + 5)
        if len(bars) < self.period + 2:
            return

        # 计算RSI
        closes = [b.close for b in bars]
        rsi = TechnicalIndicators.RSI(closes, self.period)

        current_rsi = rsi[-1]
        prev_rsi = rsi[-2]

        # RSI从超卖区回升，买入
        if prev_rsi < self.oversold and current_rsi >= self.oversold:
            if self.position == 0:
                quantity = int(self.cash * 0.9 / bar.close / 100) * 100
                if quantity >= 100:
                    self.buy(bar.close, quantity)
                    self.log(f"RSI超卖回升买入: RSI={current_rsi:.2f}")

        # RSI从超买区回落，卖出
        elif prev_rsi > self.overbought and current_rsi <= self.overbought:
            if self.position > 0:
                self.sell(bar.close, self.position)
                self.log(f"RSI超买回落卖出: RSI={current_rsi:.2f}")
'''
        }

    def get_templates(self) -> Dict[str, str]:
        """获取策略模板"""
        return self._templates.copy()

    def get_template(self, name: str) -> Optional[str]:
        """获取指定模板"""
        return self._templates.get(name)

    def validate_strategy(self, code: str) -> tuple:
        """验证策略代码"""
        return StrategyValidator.validate(code)

    def save_strategy(self, name: str, code: str, parameters: Dict = None,
                      description: str = "", save_to_file: bool = True) -> bool:
        """
        保存策略

        Args:
            name: 策略名称
            code: 策略代码
            parameters: 策略参数
            description: 策略描述
            save_to_file: 是否同时保存到文件

        Returns:
            是否成功
        """
        # 验证代码
        is_valid, error = self.validate_strategy(code)
        if not is_valid:
            self.logger.error(f"策略验证失败: {error}", LogCategory.STRATEGY)
            return False

        try:
            # 保存到数据库
            self.db_manager.save_strategy(name, code, parameters, description)

            # 保存到文件
            if save_to_file:
                file_path = self.strategy_dir / f"{name}.py"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)

            # 清除已缓存的旧策略类，确保后续加载使用最新代码
            if name in self._strategy_classes:
                del self._strategy_classes[name]

            self.logger.info(f"策略保存成功: {name}", LogCategory.STRATEGY)
            return True

        except Exception as e:
            self.logger.error(f"策略保存失败: {str(e)}", LogCategory.STRATEGY)
            return False

    def load_strategy(self, name: str) -> Optional[StrategyInfo]:
        """
        加载策略

        Args:
            name: 策略名称

        Returns:
            策略信息
        """
        # 先从数据库加载
        strategy_data = self.db_manager.get_strategy(name)
        if strategy_data:
            return StrategyInfo(
                name=strategy_data['name'],
                code=strategy_data['code'],
                parameters=strategy_data.get('parameters', {}),
                description=strategy_data.get('description', ''),
                created_at=strategy_data.get('created_at', ''),
                updated_at=strategy_data.get('updated_at', '')
            )

        # 从文件加载
        file_path = self.strategy_dir / f"{name}.py"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return StrategyInfo(
                name=name,
                code=code,
                parameters={},
                description='',
                created_at='',
                updated_at='',
                file_path=str(file_path)
            )

        # 使用内置模板兜底，保证默认策略可用
        if name in self._templates:
            return StrategyInfo(
                name=name,
                code=self._templates[name],
                parameters={},
                description='内置模板',
                created_at='',
                updated_at=''
            )

        return None

    def load_strategy_class(self, name: str) -> Optional[Type[BaseStrategy]]:
        """
        加载策略类

        Args:
            name: 策略名称

        Returns:
            策略类
        """
        # 检查缓存
        if name in self._strategy_classes:
            return self._strategy_classes[name]

        # 加载策略信息
        strategy_info = self.load_strategy(name)
        if not strategy_info:
            return None

        try:
            # 动态编译策略代码
            code = strategy_info.code

            # 创建模块
            spec = importlib.util.spec_from_loader(name, loader=None)
            module = importlib.util.module_from_spec(spec)

            # 执行代码
            exec(code, module.__dict__)

            # 查找策略类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseStrategy) and
                    attr is not BaseStrategy):
                    self._strategy_classes[name] = attr
                    return attr

        except Exception as e:
            self.logger.error(f"加载策略类失败: {str(e)}", LogCategory.STRATEGY)

        return None

    def create_strategy_instance(self, name: str, **kwargs) -> Optional[BaseStrategy]:
        """
        创建策略实例

        Args:
            name: 策略名称
            **kwargs: 策略参数

        Returns:
            策略实例
        """
        strategy_class = self.load_strategy_class(name)
        if not strategy_class:
            return None

        try:
            instance = strategy_class()

            params = {}
            info = self.load_strategy(name)
            if info and info.parameters:
                params.update(info.parameters)
            params.update(kwargs)

            # 设置参数
            for key, value in params.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            return instance

        except Exception as e:
            self.logger.error(f"创建策略实例失败: {str(e)}", LogCategory.STRATEGY)
            return None

    def get_all_strategies(self) -> List[StrategyInfo]:
        """获取所有策略"""
        strategies = []

        # 从数据库获取
        db_strategies = self.db_manager.get_all_strategies()
        for s in db_strategies:
            strategies.append(StrategyInfo(
                name=s['name'],
                code=s['code'],
                parameters=s.get('parameters', {}),
                description=s.get('description', ''),
                created_at=s.get('created_at', ''),
                updated_at=s.get('updated_at', '')
            ))

        # 从文件系统获取（排除已在数据库中的）
        db_names = {s.name for s in strategies}
        for file_path in self.strategy_dir.glob("*.py"):
            name = file_path.stem
            if name not in db_names and not name.startswith('_'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                strategies.append(StrategyInfo(
                    name=name,
                    code=code,
                    parameters={},
                    description='',
                    created_at='',
                    updated_at='',
                    file_path=str(file_path)
                ))

        return strategies

    def get_available_strategy_names(self) -> List[str]:
        """获取可供回测/实盘使用的策略名称列表"""
        names = list(self._templates.keys())
        names.extend(strategy.name for strategy in self.get_all_strategies())
        # dict.fromkeys 用于保持顺序同时去重
        return list(dict.fromkeys(names))

    def delete_strategy(self, name: str, delete_file: bool = True) -> bool:
        """
        删除策略

        Args:
            name: 策略名称
            delete_file: 是否同时删除文件

        Returns:
            是否成功
        """
        try:
            # 从数据库删除
            self.db_manager.delete_strategy(name)

            # 删除文件
            if delete_file:
                file_path = self.strategy_dir / f"{name}.py"
                if file_path.exists():
                    file_path.unlink()

            # 清除缓存
            if name in self._strategy_classes:
                del self._strategy_classes[name]

            self.logger.info(f"策略删除成功: {name}", LogCategory.STRATEGY)
            return True

        except Exception as e:
            self.logger.error(f"策略删除失败: {str(e)}", LogCategory.STRATEGY)
            return False

    def export_strategy(self, name: str, file_path: str) -> bool:
        """导出策略到文件"""
        strategy_info = self.load_strategy(name)
        if not strategy_info:
            return False

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(strategy_info.code)
            return True
        except Exception:
            return False

    def import_strategy(self, file_path: str, name: str = None) -> bool:
        """从文件导入策略"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            if name is None:
                name = Path(file_path).stem

            return self.save_strategy(name, code)

        except Exception as e:
            self.logger.error(f"导入策略失败: {str(e)}", LogCategory.STRATEGY)
            return False
