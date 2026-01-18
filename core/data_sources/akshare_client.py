from __future__ import annotations

from typing import Any, Dict, List

from .base import RequestManager

try:
    import akshare as ak
except ImportError:  # pragma: no cover - 环境未安装
    ak = None


class AKShareClient:
    """AKShare 本地调用封装。"""

    def __init__(self):
        if ak is None:
            raise RuntimeError("未安装 akshare，请先运行 pip install akshare")

    def get_financial_report(self, stock_code: str) -> Dict[str, Any]:
        df = ak.stock_financial_analysis_indicator(symbol=stock_code)
        return df.to_dict(orient="records") if df is not None else {}

    def get_income_statement(self, stock_code: str) -> List[dict]:
        df = ak.stock_financial_report_sina(stock=stock_code, symbol="利润表")
        return df.to_dict(orient="records") if df is not None else []

    def get_balance_sheet(self, stock_code: str) -> List[dict]:
        df = ak.stock_financial_report_sina(stock=stock_code, symbol="资产负债表")
        return df.to_dict(orient="records") if df is not None else []

    def get_cashflow(self, stock_code: str) -> List[dict]:
        df = ak.stock_financial_report_sina(stock=stock_code, symbol="现金流量表")
        return df.to_dict(orient="records") if df is not None else []
