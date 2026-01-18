from __future__ import annotations

import json
import re
import time
from typing import Dict, List

from .base import QuoteRecord, RequestManager


class FundDataProvider:
    """基金净值 / 搜索接口。"""

    def __init__(self, request_manager: RequestManager | None = None):
        self.rm = request_manager or RequestManager()

    def get_nav(self, code: str) -> Dict[str, float]:
        ts = int(time.time() * 1000)
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
        headers = {"Referer": "https://fund.eastmoney.com/"}
        resp = self.rm.request("GET", url, headers=headers, domain="1234567.com.cn")
        text = resp.text.strip()
        if not text.startswith("jsonpgz("):
            raise RuntimeError("unexpected fund response")
        payload = json.loads(text[8:-2])
        return {
            "code": payload.get("fundcode"),
            "name": payload.get("name"),
            "nav": float(payload.get("dwjz") or 0),
            "nav_estimate": float(payload.get("gsz") or 0),
            "nav_change": float(payload.get("gszzl") or 0),
            "update_time": payload.get("gztime"),
        }

    def search(self, keyword: str) -> List[dict]:
        url = (
            "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
            f"?m=1&key={keyword}"
        )
        resp = self.rm.request("GET", url, domain="eastmoney.com")
        payload = resp.text.strip().lstrip("(").rstrip(")")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []
        return data.get("Datas", [])
