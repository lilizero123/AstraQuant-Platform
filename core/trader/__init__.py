"""
交易模块

提供统一的交易接口抽象和多券商支持
"""
from .trader import BaseTrader, SimulatedTrader, TradeManager, TraderStatus
from .broker import (
    BrokerTrader,
    BrokerConfig,
    BrokerType,
    BrokerFactory,
    AccountInfo,
    OrderResult,
    SimulatedBroker,
    TradingEngine,
)

# 注册 REST 券商
from . import huatai  # noqa: F401
from . import zhongxin  # noqa: F401
from . import guotaijunan  # noqa: F401
from . import haitong  # noqa: F401
from . import guangfa  # noqa: F401

__all__ = [
    # 基础交易接口
    'BaseTrader',
    'SimulatedTrader',
    'TradeManager',
    'TraderStatus',

    # 券商接口
    'BrokerTrader',
    'BrokerConfig',
    'BrokerType',
    'BrokerFactory',
    'AccountInfo',
    'OrderResult',
    'SimulatedBroker',
    'TradingEngine'
]
