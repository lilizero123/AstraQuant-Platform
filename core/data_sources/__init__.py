"""
多数据源行情接口集合。

该包整合了 `stock-ai` 项目中的公开数据抓取思路，
在 Python 环境下提供统一的服务封装，方便 Quant 系统调用。
"""

from .service import MarketDataService

__all__ = ["MarketDataService"]
