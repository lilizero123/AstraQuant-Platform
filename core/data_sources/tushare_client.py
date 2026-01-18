from __future__ import annotations

from typing import Any, Dict, List

try:
    import tushare as ts
except ImportError:  # pragma: no cover - 未安装
    ts = None


class TuShareClient:
    """TuShare 轻量封装."""

    def __init__(self, token: str):
        if ts is None:
            raise RuntimeError("未安装 tushare，请先运行 pip install tushare")
        if not token:
            raise ValueError("TuShare token 未配置")
        ts.set_token(token)
        self.pro = ts.pro_api()

    def daily(self, ts_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df.to_dict(orient="records") if df is not None else []

    def stock_basic(self, exchange: str = "") -> List[Dict[str, Any]]:
        df = self.pro.stock_basic(exchange=exchange)
        return df.to_dict(orient="records") if df is not None else []
