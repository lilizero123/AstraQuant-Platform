"""
统一代理池管理器
"""
from __future__ import annotations

import json
import logging
import time
from typing import Dict, Optional

import requests

from config.settings import config_manager

logger = logging.getLogger(__name__)


class ProxyManager:
    """为 requests 提供统一的代理池支持"""

    def __init__(self, config=None):
        self.config = config or config_manager
        self._cached_proxy: Optional[Dict[str, str]] = None
        self._last_fetch: float = 0.0

    def reload_config(self, config=None):
        if config:
            self.config = config
        self._cached_proxy = None
        self._last_fetch = 0.0

    def get_requests_proxies(self) -> Optional[Dict[str, str]]:
        """返回 requests 可用的 proxies 字典"""
        cfg = getattr(self.config, "get_all", lambda: {})()
        if not cfg.get("proxy_enabled"):
            self._cached_proxy = None
            return None

        rotate_interval = max(10, int(cfg.get("proxy_rotate_interval", 120)))
        now = time.time()
        if self._cached_proxy and now - self._last_fetch < rotate_interval:
            return self._cached_proxy

        proxy_entry = (
            self._fetch_from_pool(cfg.get("proxy_pool_url", "").strip(), cfg)
            or self._build_static_proxy(cfg.get("proxy_static", "").strip(), cfg)
        )
        if proxy_entry:
            self._cached_proxy = proxy_entry
            self._last_fetch = now
        return self._cached_proxy

    # --------------------------------------------------------------- internals
    def _fetch_from_pool(self, url: str, cfg: dict) -> Optional[Dict[str, str]]:
        if not url:
            return None
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                return None
            proxy = self._extract_proxy_value(text)
            if proxy:
                return self._build_proxy_dict(proxy, cfg)
        except requests.RequestException as exc:
            logger.warning("获取代理失败: %s", exc)
        return None

    @staticmethod
    def _extract_proxy_value(payload: str) -> Optional[str]:
        """兼容 JSON/纯文本返回"""
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                for key in ("proxy", "data", "ip"):
                    value = data.get(key)
                    if isinstance(value, dict):
                        nested = value.get("proxy") or value.get("ip")
                        if nested:
                            return str(nested).strip()
                    elif value:
                        return str(value).strip()
            elif isinstance(data, list) and data:
                return str(data[0]).strip()
        except json.JSONDecodeError:
            pass
        return payload.splitlines()[0].strip()

    def _build_static_proxy(self, proxy_str: str, cfg: dict) -> Optional[Dict[str, str]]:
        if not proxy_str:
            return None
        return self._build_proxy_dict(proxy_str, cfg)

    def _build_proxy_dict(self, proxy: str, cfg: dict) -> Dict[str, str]:
        if not proxy:
            return {}
        if not proxy.startswith("http://") and not proxy.startswith("https://"):
            proxy = f"http://{proxy}"
        username = cfg.get("proxy_username", "").strip()
        password = cfg.get("proxy_password", "").strip()
        if username and password:
            proxy = proxy.replace("://", f"://{username}:{password}@", 1)
        return {"http": proxy, "https": proxy}


proxy_manager = ProxyManager()

