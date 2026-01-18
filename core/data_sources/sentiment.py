from __future__ import annotations

from typing import Dict

from .base import RequestManager


class SentimentDataProvider:
    """市场情绪与资金指标。"""

    def __init__(self, request_manager: RequestManager | None = None):
        self.rm = request_manager or RequestManager()
        self.base_url = (
            "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1"
            "&fltt=2&invt=2&fields=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        )

    def get_advances_declines(self) -> Dict[str, float]:
        result = {}
        # 涨幅 >= 0
        resp = self.rm.request(
            "GET",
            self.base_url + "&fid=f3",
            domain="eastmoney.com",
        )
        result["top_gainers"] = self._extract_percent(resp.json())
        # 跌幅 <= 0
        resp = self.rm.request(
            "GET",
            self.base_url + "&fid0=f3&fv0=-0.01&fid=f3",
            domain="eastmoney.com",
        )
        result["top_decliners"] = self._extract_percent(resp.json())
        return result

    def get_limit_stats(self) -> Dict[str, float]:
        result = {}
        up_resp = self.rm.request(
            "GET", self.base_url + "&fid0=f3&fv0=9.9", domain="eastmoney.com"
        )
        down_resp = self.rm.request(
            "GET",
            self.base_url + "&fid0=f3&fv0=-100&fid1=f3&fv1=-9.9",
            domain="eastmoney.com",
        )
        result["limit_up_ratio"] = self._extract_percent(up_resp.json())
        result["limit_down_ratio"] = self._extract_percent(down_resp.json())
        return result

    @staticmethod
    def _extract_percent(payload: dict) -> float:
        try:
            diff = payload["data"]["diff"][0]
            return diff.get("f3", 0.0)
        except Exception:  # pragma: no cover - 容错
            return 0.0
