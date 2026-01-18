from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import QuoteRecord, RequestManager


class FuturesDataProvider:
    """期货/大宗商品行情。"""

    def __init__(self, request_manager: RequestManager | None = None):
        self.rm = request_manager or RequestManager()

    def get_main_contracts(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        if not codes:
            return {}
        qq_codes = [code.lower() for code in codes]
        resp = self.rm.request(
            "GET", f"https://qt.gtimg.cn/q={','.join(qq_codes)}", domain="qq.com", encoding="gbk"
        )
        data: Dict[str, QuoteRecord] = {}
        pattern = re.compile(r'v_(?P<code>\w+)="(?P<data>[^"]*)"')
        for line in resp.text.split(";"):
            match = pattern.search(line)
            if not match:
                continue
            code = match.group("code").upper()
            parts = match.group("data").split("~")
            if len(parts) < 10:
                continue
            price = _to_float(parts[3])
            pre_close = _to_float(parts[4])
            record = QuoteRecord(
                code=code,
                name=parts[1],
                price=price,
                pre_close=pre_close,
                open=_to_float(parts[5]),
                high=_to_float(parts[33]),
                low=_to_float(parts[34]),
            ).normalize()
            data[code] = record
        return data

    def get_from_eastmoney(self) -> Dict[str, QuoteRecord]:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            "pn=1&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:113,m:114,m:115"
            "&fields=f2,f3,f4,f12,f14,f15,f16,f17,f18"
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
                high=(item.get("f15") or 0) / 100,
                low=(item.get("f16") or 0) / 100,
                open=(item.get("f17") or 0) / 100,
                pre_close=(item.get("f18") or 0) / 100,
            ).normalize()
            data[code] = record
        return data


def _to_float(value: str | float | int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
