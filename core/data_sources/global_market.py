from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import QuoteRecord, RequestManager

SINA_GLOBAL_RE = re.compile(r'var hq_str_(?P<code>int_[a-z0-9]+)="(?P<data>[^"]*)"')
SINA_US_RE = re.compile(r'var hq_str_gb_(?P<code>[a-z.]+)="(?P<data>[^"]*)"')


class GlobalMarketProvider:
    """港美股 / 全球指数数据源。"""

    def __init__(self, request_manager: RequestManager | None = None):
        self.rm = request_manager or RequestManager()

    def get_global_indices(self) -> Dict[str, QuoteRecord]:
        fetchers = [
            self._fetch_global_from_sina,
            self._fetch_global_from_tencent,
            self._fetch_global_from_eastmoney,
        ]
        result: Dict[str, QuoteRecord] = {}
        for fetch in fetchers:
            try:
                data = fetch()
                result.update(data)
            except Exception:  # pragma: no cover - 网络异常
                continue
        return result

    def get_us_stock_price(self, symbols: List[str]) -> Dict[str, QuoteRecord]:
        if not symbols:
            return {}
        codes = ",".join(f"gb_{s.lower()}" for s in symbols)
        resp = self.rm.request(
            "GET", f"https://hq.sinajs.cn/list={codes}", domain="sina.com.cn"
        )
        data: Dict[str, QuoteRecord] = {}
        for line in resp.text.splitlines():
            match = SINA_US_RE.search(line)
            if not match:
                continue
            code = match.group("code").upper()
            parts = match.group("data").split(",")
            if len(parts) < 20:
                continue
            record = QuoteRecord(
                code=code,
                name=parts[0],
                price=_to_float(parts[1]),
                open=_to_float(parts[5]),
                high=_to_float(parts[6]),
                low=_to_float(parts[7]),
                pre_close=_to_float(parts[26]),
                volume=_to_float(parts[10]),
                amount=_to_float(parts[11]),
            ).normalize()
            data[code] = record
        return data

    def get_hk_stock_price(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        if not codes:
            return {}
        hk_codes = [code if code.startswith("hk") else f"hk{code}" for code in codes]
        resp = self.rm.request(
            "GET",
            f"https://qt.gtimg.cn/q={','.join(hk_codes)}",
            domain="qq.com",
            encoding="gbk",
        )
        data: Dict[str, QuoteRecord] = {}
        pattern = re.compile(r'v_(?P<code>hk\d{5})="(?P<data>[^"]*)"')
        for line in resp.text.split(";"):
            match = pattern.search(line)
            if not match:
                continue
            code = match.group("code").upper()
            parts = match.group("data").split("~")
            if len(parts) < 40:
                continue
            record = QuoteRecord(
                code=code,
                name=parts[1],
                price=_to_float(parts[3]),
                pre_close=_to_float(parts[4]),
                open=_to_float(parts[5]),
                high=_to_float(parts[33]),
                low=_to_float(parts[34]),
                volume=_to_float(parts[6]),
                amount=_to_float(parts[37]),
            ).normalize()
            data[code] = record
        return data

    # --------------------- 内部抓取 ---------------------
    def _fetch_global_from_sina(self) -> Dict[str, QuoteRecord]:
        codes = "int_dji,int_nasdaq,int_sp500,int_hangseng,int_nikkei,b_FTSE,b_DAX,b_HSI"
        resp = self.rm.request(
            "GET", f"https://hq.sinajs.cn/list={codes}", domain="sina.com.cn", encoding="gbk"
        )
        data: Dict[str, QuoteRecord] = {}
        mapping = {
            "int_dji": "DJI",
            "int_nasdaq": "IXIC",
            "int_sp500": "SPX",
            "int_hangseng": "HSI",
            "int_nikkei": "N225",
            "b_FTSE": "FTSE",
            "b_DAX": "DAX",
            "b_HSI": "HSI",
        }
        for line in resp.text.splitlines():
            match = SINA_GLOBAL_RE.search(line)
            if not match:
                continue
            code = match.group("code")
            parts = match.group("data").split(",")
            if len(parts) < 4:
                continue
            mapped = mapping.get(code, code)
            record = QuoteRecord(
                code=mapped,
                name=parts[0],
                price=_to_float(parts[1]),
                change=_to_float(parts[2]),
                change_percent=_to_float(parts[3]),
            ).normalize()
            data[mapped] = record
        return data

    def _fetch_global_from_tencent(self) -> Dict[str, QuoteRecord]:
        codes = (
            "usDJI,usIXIC,usSPX,hkHSI,jpN225,ukFTSE,deDAX,frCAC,krKOSPI,twTWSE,"
            "sgSTI,inSENSEX,auASX"
        )
        resp = self.rm.request(
            "GET", f"https://qt.gtimg.cn/q={codes}", domain="qq.com", encoding="gbk"
        )
        data: Dict[str, QuoteRecord] = {}
        pattern = re.compile(r'v_(?P<code>[a-zA-Z]+)="(?P<data>[^"]*)"')
        mapping = {
            "usDJI": "DJI",
            "usIXIC": "IXIC",
            "usSPX": "SPX",
            "hkHSI": "HSI",
            "jpN225": "N225",
            "ukFTSE": "FTSE",
            "deDAX": "DAX",
            "frCAC": "FCHI",
        }
        for line in resp.text.split(";"):
            match = pattern.search(line)
            if not match:
                continue
            code = match.group("code")
            parts = match.group("data").split("~")
            if len(parts) < 10:
                continue
            mapped = mapping.get(code, code)
            price = _to_float(parts[3])
            prev = _to_float(parts[4])
            change = price - prev
            change_percent = (change / prev) * 100 if prev else 0
            data[mapped] = QuoteRecord(
                code=mapped,
                name=parts[1],
                price=price,
                change=change,
                change_percent=change_percent,
            ).normalize()
        return data

    def _fetch_global_from_eastmoney(self) -> Dict[str, QuoteRecord]:
        # 使用东方财富全球指数接口
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get"
            "?pn=1&pz=50&po=1&np=1&fs=i:1.000001,i:0.399001,i:2.1"
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


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
