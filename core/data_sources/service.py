from __future__ import annotations

from typing import Dict, List, Optional

from .base import QuoteRecord, RequestManager
from .china import ChinaStockProvider
from .forex_crypto import ForexCryptoProvider
from .futures import FuturesDataProvider
from .funds import FundDataProvider
from .global_market import GlobalMarketProvider
from .sentiment import SentimentDataProvider

try:  # 可选依赖
    from .akshare_client import AKShareClient  # type: ignore
except Exception:  # pragma: no cover - 环境缺失
    AKShareClient = None  # type: ignore

try:
    from .tushare_client import TuShareClient  # type: ignore
except Exception:  # pragma: no cover
    TuShareClient = None  # type: ignore


class MarketDataService:
    """
    对 stock-ai 中的多数据源进行统一封装，提供给 Quant 系统调用。
    """

    def __init__(self, tushare_token: str = ""):
        self.rm = RequestManager()
        self.china = ChinaStockProvider(self.rm)
        self.global_market = GlobalMarketProvider(self.rm)
        self.futures = FuturesDataProvider(self.rm)
        self.forex = ForexCryptoProvider(self.rm)
        self.fund = FundDataProvider(self.rm)
        self.sentiment = SentimentDataProvider(self.rm)
        self._akshare: Optional[AKShareClient] = None
        if tushare_token and TuShareClient:
            self._tushare: Optional[TuShareClient] = TuShareClient(tushare_token)
        else:
            self._tushare = None

    # --------------------------- 行情接口 ---------------------------
    def get_realtime_quotes(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        return self.china.get_realtime_quotes(codes)

    def get_global_indices(self) -> Dict[str, QuoteRecord]:
        return self.global_market.get_global_indices()

    def get_us_stock_price(self, symbols: List[str]) -> Dict[str, QuoteRecord]:
        return self.global_market.get_us_stock_price(symbols)

    def get_hk_stock_price(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        return self.global_market.get_hk_stock_price(codes)

    def get_futures_snapshot(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        data = self.futures.get_main_contracts(codes)
        data.update(self.futures.get_from_eastmoney())
        return data

    def get_forex(self, pairs: Optional[List[str]] = None) -> Dict[str, QuoteRecord]:
        return self.forex.get_forex_from_sina(pairs or [])

    def get_crypto(self, symbols: Optional[List[str]] = None) -> Dict[str, QuoteRecord]:
        return self.forex.get_crypto_from_xueqiu(symbols or [])

    def get_fund_nav(self, code: str) -> Dict[str, float]:
        return self.fund.get_nav(code)

    def get_market_sentiment(self) -> Dict[str, float]:
        data = self.sentiment.get_advances_declines()
        data.update(self.sentiment.get_limit_stats())
        return data

    # --------------------------- 财务接口 ---------------------------
    @property
    def akshare(self) -> AKShareClient:
        if self._akshare is None:
            if AKShareClient is None:
                raise RuntimeError("AKShare 未安装，或运行环境缺少依赖")
            self._akshare = AKShareClient()
        return self._akshare

    @property
    def tushare(self) -> TuShareClient:
        if self._tushare is None:
            raise RuntimeError("未配置 TuShare token 或未安装 tushare")
        return self._tushare
