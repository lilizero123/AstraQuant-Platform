from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import QuoteRecord, RequestManager

SINA_FOREX_RE = re.compile(r'var hq_str_(?P<code>fx_[a-z]+)="(?P<data>[^"]*)"')


class ForexCryptoProvider:
    """外汇 / 数字货币行情。"""

    def __init__(self, request_manager: RequestManager | None = None):
        self.rm = request_manager or RequestManager()

    def get_forex_from_sina(self, pairs: List[str]) -> Dict[str, QuoteRecord]:
        if not pairs:
            pairs = ["USDCNY", "EURUSD", "GBPUSD", "USDJPY"]
        sina_pairs = ",".join(f"fx_{p.lower()}" for p in pairs)
        resp = self.rm.request(
            "GET", f"https://hq.sinajs.cn/list={sina_pairs}", domain="sina.com.cn", encoding="gbk"
        )
        data: Dict[str, QuoteRecord] = {}
        for line in resp.text.splitlines():
            match = SINA_FOREX_RE.search(line)
            if not match:
                continue
            code = match.group("code")[3:].upper()
            parts = match.group("data").split(",")
            if len(parts) < 8:
                continue
            record = QuoteRecord(
                code=code,
                name=parts[0],
                price=_to_float(parts[1]),
                open=_to_float(parts[5]),
                high=_to_float(parts[6]),
                low=_to_float(parts[7]),
                pre_close=_to_float(parts[3]),
            ).normalize()
            data[code] = record
        return data

    def get_forex_from_eastmoney(self) -> Dict[str, QuoteRecord]:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            "pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:119,m:120"
            "&fields=f2,f3,f4,f12,f14"
        )
        resp = self.rm.request("GET", url, domain="eastmoney.com")
        payload = resp.json()
        data: Dict[str, QuoteRecord] = {}
        for item in payload.get("data", {}).get("diff", []) or []:
            code = item.get("f12")
            if not code:
                continue
            record = QuoteRecord(
                code=code,
                name=item.get("f14", ""),
                price=(item.get("f2") or 0) / 100,
                change=(item.get("f4") or 0) / 100,
                change_percent=(item.get("f3") or 0) / 100,
            ).normalize()
            data[code] = record
        return data

    def get_crypto_from_xueqiu(self, symbols: List[str]) -> Dict[str, QuoteRecord]:
        if not symbols:
            symbols = ["BTCUSD", "ETHUSD"]
        url = (
            "https://stock.xueqiu.com/v5/stock/batch/quote.json?symbol="
            + ",".join(symbols)
        )
        headers = {"Referer": "https://xueqiu.com/"}
        resp = self.rm.request("GET", url, domain="xueqiu.com", headers=headers)
        payload = resp.json()
        data: Dict[str, QuoteRecord] = {}
        for item in payload.get("data", {}).get("items", []):
            quote = item.get("quote", {})
            code = quote.get("symbol")
            if not code:
                continue
            record = QuoteRecord(
                code=code,
                name=quote.get("name", ""),
                price=quote.get("current") or 0,
                change=quote.get("chg") or 0,
                change_percent=quote.get("percent") or 0,
                high=quote.get("high") or 0,
                low=quote.get("low") or 0,
                open=quote.get("open") or 0,
                pre_close=quote.get("last_close") or 0,
            ).normalize()
            data[code] = record
        return data


def _to_float(value: str | float | int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
