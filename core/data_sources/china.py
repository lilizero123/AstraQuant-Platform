from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

from .base import QuoteRecord, RequestManager
from .utils import SINA_STOCK_RE, TENCENT_RE, ensure_sina_codes, parse_sina_datetime


class ChinaStockProvider:
    """A 股多数据源行情抓取。"""

    def __init__(self, request_manager: RequestManager | None = None):
        self.rm = request_manager or RequestManager()

    # ------------------------- public API -------------------------
    def get_realtime_quotes(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        """依次尝试东方财富 / 腾讯 / 新浪，返回尽可能多的行情。"""
        codes = [c.lower() for c in codes if c]
        if not codes:
            return {}

        fetchers = [
            self._fetch_from_eastmoney,
            self._fetch_from_tencent,
            self._fetch_from_sina,
        ]
        errors: List[str] = []
        result: Dict[str, QuoteRecord] = {}
        for fetch in fetchers:
            try:
                data = fetch(codes)
                result.update(data)
            except Exception as exc:  # pragma: no cover - 网络异常
                errors.append(str(exc))
            if len(result) >= len(codes):
                break

        if not result and errors:
            raise RuntimeError("all china stock sources failed: " + "; ".join(errors))
        return result

    # ------------------------- 单个源实现 -------------------------
    def _fetch_from_sina(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        sina_codes = ensure_sina_codes(codes)
        url = f"https://hq.sinajs.cn/list={','.join(sina_codes)}"
        resp = self.rm.request("GET", url, domain="sina.com.cn", encoding="gbk")
        data: Dict[str, QuoteRecord] = {}
        for line in resp.text.splitlines():
            if not line:
                continue
            match = SINA_STOCK_RE.search(line)
            if not match:
                continue
            code = match.group("code")
            parts = match.group("data").split(",")
            if len(parts) < 32:
                continue
            record = QuoteRecord(
                code=code,
                name=parts[0],
                open=_to_float(parts[1]),
                pre_close=_to_float(parts[2]),
                price=_to_float(parts[3]),
                high=_to_float(parts[4]),
                low=_to_float(parts[5]),
                volume=_to_float(parts[8]),
                amount=_to_float(parts[9]),
                timestamp=parse_sina_datetime(parts[30], parts[31]),
            ).normalize()
            data[code] = record
        return data

    def _fetch_from_tencent(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        qq_codes = ensure_sina_codes(codes)
        url = f"https://qt.gtimg.cn/q={','.join(qq_codes)}"
        resp = self.rm.request("GET", url, domain="qq.com", encoding="gbk")
        data: Dict[str, QuoteRecord] = {}
        for line in resp.text.split(";"):
            if not line:
                continue
            match = TENCENT_RE.search(line)
            if not match:
                continue
            code = match.group("code")
            parts = match.group("data").split("~")
            if len(parts) < 40:
                continue
            pre_close = _to_float(parts[4])
            price = _to_float(parts[3])
            record = QuoteRecord(
                code=code,
                name=parts[1],
                price=price,
                open=_to_float(parts[5]),
                pre_close=pre_close,
                high=_to_float(parts[33]),
                low=_to_float(parts[34]),
                volume=_to_float(parts[6]),
                amount=_to_float(parts[37]),
                timestamp=_parse_time_str(parts[30]),
            )
            data[code] = record.normalize()
        return data

    def _fetch_from_eastmoney(self, codes: List[str]) -> Dict[str, QuoteRecord]:
        secids, mapping = _build_eastmoney_secids(codes)
        if not secids:
            return {}
        url = (
            "https://push2.eastmoney.com/api/qt/ulist.np/get?secids="
            + ",".join(secids)
            + "&fields=f2,f3,f4,f5,f6,f12,f13,f14,f15,f16,f17,f18"
        )
        resp = self.rm.request("GET", url, domain="eastmoney.com")
        payload = resp.json()
        data: Dict[str, QuoteRecord] = {}
        for item in payload.get("data", {}).get("diff", []) or []:
            code = item.get("f12")
            if not code:
                continue
            original = mapping.get(code, code)
            price = (item.get("f2") or 0) / 100
            record = QuoteRecord(
                code=original,
                name=item.get("f14", ""),
                price=price,
                change=(item.get("f4") or 0) / 100,
                change_percent=(item.get("f3") or 0) / 100,
                volume=item.get("f5") or 0,
                amount=item.get("f6") or 0,
                high=(item.get("f15") or 0) / 100,
                low=(item.get("f16") or 0) / 100,
                open=(item.get("f17") or 0) / 100,
                pre_close=(item.get("f18") or 0) / 100,
                timestamp=datetime.now(),
            )
            data[original] = record.normalize()
        return data


# ------------------------- helpers -------------------------
def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_time_str(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S")
    except Exception:
        try:
            return datetime.strptime(value, "%H%M%S")
        except Exception:
            return datetime.now()


def _build_eastmoney_secids(codes: List[str]) -> Tuple[List[str], Dict[str, str]]:
    secids: List[str] = []
    mapping: Dict[str, str] = {}
    for code in codes:
        if code.startswith("sh"):
            pure = code[2:]
            secids.append(f"1.{pure}")
            mapping[pure] = code
        elif code.startswith("sz"):
            pure = code[2:]
            secids.append(f"0.{pure}")
            mapping[pure] = code
        elif code.startswith("6"):
            secids.append(f"1.{code}")
            mapping[code] = f"sh{code}"
        else:
            secids.append(f"0.{code}")
            mapping[code] = f"sz{code}"
    return secids, mapping
