import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import requests

from core.network.proxy_manager import proxy_manager


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class RequestManager:
    """简易请求调度器，负责限流与统一 UA。"""

    def __init__(self):
        self.session = requests.Session()
        self._domain_lock = threading.Lock()
        self._last_call: Dict[str, float] = {}
        self.timeout = 8
        self.min_interval = 0.25  # 同一域名最小间隔

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        domain: Optional[str] = None,
        encoding: Optional[str] = None,
        retries: int = 2,
        **kwargs,
    ) -> requests.Response:
        domain = domain or self._extract_domain(url)
        headers = headers or {}
        headers.setdefault("User-Agent", random.choice(USER_AGENTS))

        for attempt in range(retries + 1):
            self._throttle(domain)
            try:
                proxies = proxy_manager.get_requests_proxies()
                resp = self.session.request(
                    method.upper(),
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    proxies=proxies,
                    **kwargs,
                )
                resp.raise_for_status()
                if encoding:
                    resp.encoding = encoding
                return resp
            except requests.RequestException:
                if attempt >= retries:
                    raise
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError("unreachable")

    def _throttle(self, domain: str):
        with self._domain_lock:
            last = self._last_call.get(domain, 0)
            now = time.monotonic()
            delta = now - last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last_call[domain] = time.monotonic()

    @staticmethod
    def _extract_domain(url: str) -> str:
        start = url.find("://")
        if start != -1:
            url = url[start + 3 :]
        return url.split("/", 1)[0]


@dataclass
class QuoteRecord:
    code: str
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    timestamp: Optional[datetime] = None

    def normalize(self) -> "QuoteRecord":
        self.price = float(self.price or 0.0)
        self.open = float(self.open or 0.0)
        self.high = float(self.high or self.price)
        self.low = float(self.low or self.price)
        self.pre_close = float(self.pre_close or 0.0)
        self.change = self.price - self.pre_close if not self.change else self.change
        if not self.change_percent and self.pre_close:
            self.change_percent = (self.change / self.pre_close) * 100
        if not self.timestamp:
            self.timestamp = datetime.now()
        return self

    def to_snapshot_dict(self) -> dict:
        data = self.normalize()
        return {
            "code": data.code,
            "name": data.name,
            "price": data.price,
            "open": data.open,
            "high": data.high,
            "low": data.low,
            "pre_close": data.pre_close,
            "volume": data.volume,
            "amount": data.amount,
            "change": data.change,
            "change_percent": data.change_percent,
            "timestamp": data.timestamp or datetime.now(),
        }
