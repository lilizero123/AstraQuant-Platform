"""
REST 交易接口基类
用于对接券商 HTTP 网关
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Tuple

import requests

from core.logger import LogCategory
from core.network.proxy_manager import proxy_manager
from core.strategy.base import Order, OrderSide, OrderStatus, OrderType, Position, Trade
from core.trader.broker import AccountInfo, BrokerConfig, BrokerTrader, OrderResult


@dataclass
class RestEndpoints:
    """REST 接口路径配置"""

    ping: str = "/api/ping"
    login: str = "/api/auth/login"
    logout: str = "/api/auth/logout"
    order: str = "/api/orders"
    cancel: str = "/api/orders/{order_id}/cancel"
    modify: str = "/api/orders/{order_id}"
    account: str = "/api/account"
    positions: str = "/api/positions"
    orders: str = "/api/orders"
    trades: str = "/api/trades"


class RestBrokerBase(BrokerTrader):
    """
    REST 券商接口基类

    子类只需提供不同的 RestEndpoints 配置和默认 base_url
    """

    endpoints = RestEndpoints()

    def __init__(self, config: BrokerConfig):
        super().__init__(config)
        self.base_url = config.extra.get("base_url", "").rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "QuantTrader/1.0"})
        self._timeout = config.extra.get("timeout", 5)
        self._token: Optional[str] = None
        self._request_adapter: Optional[Callable[..., Any]] = config.extra.get("request_adapter")
        self._mock_responses: Dict[Tuple[str, str], Any] = config.extra.get("mock_responses", {})
        self._api_key = config.extra.get("api_key")
        self._api_secret = config.extra.get("api_secret")
        self._sign_method = config.extra.get("sign_method", "hmac_sha256")
        self._custom_signer = config.extra.get("signer")
        self._verify_ssl = config.extra.get("verify_ssl", True)
        self._session.verify = self._verify_ssl
        self._client_cert = config.extra.get("client_cert")
        if self._client_cert:
            self._session.cert = self._client_cert
        self._clock: Callable[[], datetime] = config.extra.get("clock", datetime.utcnow)

        # 自动同步线程
        self._poll_interval = config.extra.get("poll_interval", 3)
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_event = threading.Event()

    # ==================== 工具方法 ====================

    def _get_endpoint(self, name: str, **kwargs) -> str:
        overrides = self.config.extra.get("endpoints", {})
        path = overrides.get(name) or getattr(self.endpoints, name)
        return path.format(**kwargs)

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def set_request_adapter(self, adapter: Callable[..., Any]):
        """设置自定义请求适配器（用于测试或模拟）"""
        self._request_adapter = adapter

    def set_mock_response(self, method: str, path: str, response: Any):
        """注册静态响应（测试用）"""
        self._mock_responses[(method.upper(), path)] = response

    def _request(self, method: str, path: str, require_auth: bool = True, **kwargs) -> Any:
        if not self.base_url:
            raise ValueError("未配置 base_url")

        mock_key = (method.upper(), path)
        if self._mock_responses and mock_key in self._mock_responses:
            return self._mock_responses[mock_key]

        headers = kwargs.pop("headers", {})
        if require_auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._apply_security_headers(method, path, headers, kwargs)

        if self._request_adapter:
            return self._request_adapter(
                method.upper(),
                path,
                headers=headers,
                require_auth=require_auth,
                **kwargs,
            )

        try:
            proxies = proxy_manager.get_requests_proxies()
            resp = self._session.request(
                method=method.upper(),
                url=self._build_url(path),
                timeout=self._timeout,
                headers=headers,
                proxies=proxies,
                **kwargs,
            )
            resp.raise_for_status()
            if resp.content:
                data = resp.json()
                return self._unwrap_response(data)
            return {}
        except requests.RequestException as exc:
            raise RuntimeError(f"HTTP请求失败: {exc}") from exc

    @staticmethod
    def _unwrap_response(response: Any) -> Any:
        """兼容不同 REST 响应格式"""
        if isinstance(response, dict):
            if "data" in response:
                data = response["data"]
                if isinstance(data, dict):
                    merged = dict(data)
                    for key, value in response.items():
                        if key == "data":
                            continue
                        merged.setdefault(key, value)
                    return merged
                return data
        return response

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if value is None:
            return datetime.now()
        if isinstance(value, (int, float)):
            # 秒级或毫秒级时间戳
            if value > 1e12:
                value = value / 1000
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value[: len(fmt)], fmt)
                except ValueError:
                    continue
        return datetime.now()

    @staticmethod
    def _parse_side(value: Any) -> OrderSide:
        if isinstance(value, OrderSide):
            return value
        mapping = {
            "buy": OrderSide.BUY,
            "1": OrderSide.BUY,
            1: OrderSide.BUY,
            "sell": OrderSide.SELL,
            "2": OrderSide.SELL,
            2: OrderSide.SELL,
        }
        return mapping.get(str(value).lower(), OrderSide.BUY)

    @staticmethod
    def _parse_status(value: Any) -> OrderStatus:
        if isinstance(value, OrderStatus):
            return value
        mapping = {
            "pending": OrderStatus.PENDING,
            "submitted": OrderStatus.SUBMITTED,
            "new": OrderStatus.SUBMITTED,
            "accepted": OrderStatus.SUBMITTED,
            "filled": OrderStatus.FILLED,
            "done": OrderStatus.FILLED,
            "partial": OrderStatus.SUBMITTED,
            "cancelled": OrderStatus.CANCELLED,
            "canceled": OrderStatus.CANCELLED,
            "reject": OrderStatus.REJECTED,
            "rejected": OrderStatus.REJECTED,
        }
        return mapping.get(str(value).lower(), OrderStatus.SUBMITTED)

    @staticmethod
    def _parse_order_type(value: Any) -> OrderType:
        if isinstance(value, OrderType):
            return value
        mapping = {
            "market": OrderType.MARKET,
            "1": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "0": OrderType.LIMIT,
        }
        return mapping.get(str(value).lower(), OrderType.LIMIT)

    # ==================== 安全辅助 ====================

    def _apply_security_headers(self, method: str, path: str, headers: Dict[str, str], kwargs: Dict[str, Any]):
        if not self._api_key:
            return
        timestamp = self._clock().isoformat()
        payload = self._canonical_payload(kwargs)
        if self._custom_signer:
            signature = self._custom_signer(method, path, payload, timestamp, kwargs)
        else:
            signature = self._build_signature(method, path, payload, timestamp)
        headers.setdefault("X-API-Key", self._api_key)
        headers["X-Timestamp"] = timestamp
        headers["X-Signature"] = signature

    def _canonical_payload(self, kwargs: Dict[str, Any]) -> str:
        params_repr = ""
        if "params" in kwargs and kwargs["params"]:
            params_items = sorted(kwargs["params"].items())
            params_repr = "&".join(f"{k}={v}" for k, v in params_items)

        body = ""
        if "json" in kwargs and kwargs["json"] is not None:
            body = json.dumps(kwargs["json"], sort_keys=True, separators=(",", ":"))
        elif "data" in kwargs and isinstance(kwargs["data"], (dict, list)):
            body = json.dumps(kwargs["data"], sort_keys=True, separators=(",", ":"))
        elif "data" in kwargs and isinstance(kwargs["data"], (str, bytes)):
            body = kwargs["data"] if isinstance(kwargs["data"], str) else kwargs["data"].decode("utf-8")
        return f"{params_repr}|{body}"

    def _build_signature(self, method: str, path: str, payload: str, timestamp: str) -> str:
        if not self._api_secret:
            return ""
        message = f"{method.upper()}|{path}|{payload}|{timestamp}"
        if self._sign_method.lower() == "hmac_sha512":
            digest = hmac.new(self._api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha512)
        else:
            digest = hmac.new(self._api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
        return digest.hexdigest()

    # ==================== 生命周期 ====================

    def connect(self) -> bool:
        """连接 REST 服务"""
        try:
            self._log_info("正在连接交易网关...")
            self._request("GET", self._get_endpoint("ping"), require_auth=False)
            self._connected = True
            self._log_info("连接成功")
            if self.on_connected:
                self.on_connected()
            return True
        except Exception as exc:
            self._log_error(f"连接失败: {exc}")
            return False

    def disconnect(self):
        self._stop_polling()
        self._connected = False
        self._logged_in = False
        if self.on_disconnected:
            self.on_disconnected()
        self._log_info("已断开REST网关")

    def login(self) -> bool:
        if not self._connected:
            self._log_error("请先连接交易网关")
            return False

        payload = {
            "account": self.config.account,
            "password": self.config.password,
            "server": self.config.server,
            "port": self.config.port,
        }
        try:
            response = self._request("POST", self._get_endpoint("login"), require_auth=False, json=payload)
            self._token = self._extract_token(response)
            if not self._token:
                raise RuntimeError("登录响应中没有令牌信息")

            self._logged_in = True
            self._log_info(f"账户 {self.config.account} 登录成功")
            if self.on_login:
                self.on_login()

            # 登录后立即同步一次
            self.query_account()
            self.query_positions()
            self.query_orders()

            self._start_polling()
            return True
        except Exception as exc:
            self._log_error(f"登录失败: {exc}")
            return False

    def logout(self):
        if not self._logged_in:
            return
        try:
            self._request("POST", self._get_endpoint("logout"), json={"account": self.config.account})
        except Exception as exc:
            self._log_error(f"登出异常: {exc}")
        finally:
            self._stop_polling()
            self._logged_in = False
            self._token = None
            if self.on_logout:
                self.on_logout()
            self._log_info("已从交易网关登出")

    def _extract_token(self, response: Any) -> Optional[str]:
        if isinstance(response, dict):
            if "token" in response:
                return response["token"]
            if "access_token" in response:
                return response["access_token"]
        return None

    def _start_polling(self):
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._poll_event.clear()

        def _loop():
            while not self._poll_event.wait(self._poll_interval):
                if not self._logged_in:
                    continue
                try:
                    self.query_account()
                    self.query_positions()
                    self.query_orders()
                    self.query_trades()
                except Exception as exc:  # pragma: no cover - 仅日志
                    self._log_error(f"自动同步失败: {exc}")

        self._poll_thread = threading.Thread(target=_loop, daemon=True)
        self._poll_thread.start()

    def _stop_polling(self):
        self._poll_event.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
            self._poll_thread = None

    # ==================== 交易操作 ====================

    def send_order(
        self,
        code: str,
        side: OrderSide,
        price: float,
        quantity: int,
        order_type: OrderType = OrderType.LIMIT,
    ) -> OrderResult:
        if not self._logged_in:
            return OrderResult(success=False, message="尚未登录")

        payload = {
            "code": code,
            "side": side.value,
            "price": price,
            "quantity": quantity,
            "order_type": order_type.value,
        }
        try:
            response = self._request("POST", self._get_endpoint("order"), json=payload)
            order_data = self._unwrap_order_response(response)
            order = self._parse_order(order_data, fallback_code=code, fallback_side=side, fallback_price=price, fallback_qty=quantity)
            self._notify_order_update(order)
            return OrderResult(success=True, order_id=order.order_id, order=order, message="下单成功")
        except Exception as exc:
            self._log_error(f"下单失败: {exc}")
            return OrderResult(success=False, message=str(exc))

    def cancel_order(self, order_id: str) -> bool:
        if not self._logged_in:
            return False
        try:
            self._request("POST", self._get_endpoint("cancel", order_id=order_id))
            with self._lock:
                order = self._orders.get(order_id)
                if order:
                    order.status = OrderStatus.CANCELLED
                    order.update_time = datetime.now()
            if order:
                self._notify_order_update(order)
            return True
        except Exception as exc:
            self._log_error(f"撤单失败: {exc}")
            return False

    def modify_order(self, order_id: str, price: float = None, quantity: int = None) -> bool:
        if not self._logged_in:
            return False
        payload: Dict[str, Any] = {}
        if price is not None:
            payload["price"] = price
        if quantity is not None:
            payload["quantity"] = quantity
        if not payload:
            return False
        try:
            self._request("PUT", self._get_endpoint("modify", order_id=order_id), json=payload)
            return True
        except Exception as exc:
            self._log_error(f"改单失败: {exc}")
            return False

    # ==================== 查询维护 ====================

    def query_account(self) -> Optional[AccountInfo]:
        if not self._logged_in:
            return None
        try:
            data = self._request("GET", self._get_endpoint("account"))
            account = self._parse_account(data)
            self._account = account
            if self.on_account_update:
                self.on_account_update(account)
            return account
        except Exception as exc:
            self._log_error(f"查询账户失败: {exc}")
            return None

    def query_positions(self) -> List[Position]:
        if not self._logged_in:
            return []
        try:
            data = self._request("GET", self._get_endpoint("positions"))
            positions = [self._parse_position(item) for item in self._ensure_list(data, "positions")]
            with self._lock:
                self._positions = {pos.code: pos for pos in positions}
            for pos in positions:
                self._notify_position_update(pos)
            return positions
        except Exception as exc:
            self._log_error(f"查询持仓失败: {exc}")
            return []

    def query_orders(self, status: OrderStatus = None) -> List[Order]:
        if not self._logged_in:
            return []
        try:
            params = {"status": status.value} if status else None
            data = self._request("GET", self._get_endpoint("orders"), params=params)
            orders = [self._parse_order(item) for item in self._ensure_list(data, "orders")]
            with self._lock:
                for order in orders:
                    self._orders[order.order_id] = order
            for order in orders:
                self._notify_order_update(order)
            return orders
        except Exception as exc:
            self._log_error(f"查询订单失败: {exc}")
            return []

    def query_trades(self) -> List[Trade]:
        if not self._logged_in:
            return []
        try:
            data = self._request("GET", self._get_endpoint("trades"))
            # 拷贝一份，避免后续 _notify_trade_update 中 append 导致迭代列表被修改
            raw_trades = list(self._ensure_list(data, "trades"))
            trades = [self._parse_trade(item) for item in raw_trades]
            with self._lock:
                self._trades = list(trades)
            for trade in trades:
                self._notify_trade_update(trade)
            return trades
        except Exception as exc:
            self._log_error(f"查询成交失败: {exc}")
            return []

    # ==================== 数据解析 ====================

    @staticmethod
    def _ensure_list(data: Any, key_hint: str) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if key_hint in data and isinstance(data[key_hint], list):
                return data[key_hint]
            if "items" in data and isinstance(data["items"], list):
                return data["items"]
        return []

    def _unwrap_order_response(self, response: Any) -> Dict[str, Any]:
        if isinstance(response, dict):
            if "order" in response and isinstance(response["order"], dict):
                return response["order"]
            return response
        raise ValueError("无效的订单响应格式")

    def _parse_account(self, data: Dict[str, Any]) -> AccountInfo:
        return AccountInfo(
            account_id=str(data.get("account_id") or self.config.account),
            broker=self.config.broker_type.value,
            cash=float(data.get("cash", 0.0)),
            frozen=float(data.get("frozen", 0.0)),
            market_value=float(data.get("market_value", 0.0)),
            total_value=float(data.get("total_value", data.get("cash", 0.0) + data.get("market_value", 0.0))),
            profit=float(data.get("profit", 0.0)),
            profit_pct=float(data.get("profit_pct", 0.0)),
        )

    def _parse_position(self, data: Dict[str, Any]) -> Position:
        code = str(data.get("code") or data.get("stock_code") or "")
        quantity = int(data.get("quantity") or data.get("volume") or 0)
        avg_cost = float(data.get("avg_cost") or data.get("cost_price") or 0.0)
        current_price = float(data.get("current_price") or data.get("price") or avg_cost)
        return Position(code=code, quantity=quantity, avg_cost=avg_cost, current_price=current_price)

    def _parse_order(
        self,
        data: Dict[str, Any],
        fallback_code: str = "",
        fallback_side: OrderSide = OrderSide.BUY,
        fallback_price: float = 0.0,
        fallback_qty: int = 0,
    ) -> Order:
        order_id = str(data.get("order_id") or data.get("id") or data.get("cl_ord_id") or "")
        price = float(data.get("price", fallback_price))
        quantity = int(data.get("quantity") or data.get("volume") or fallback_qty)

        order = Order(
            order_id=order_id,
            code=str(data.get("code") or fallback_code),
            side=self._parse_side(data.get("side") or fallback_side),
            price=price,
            quantity=quantity,
            order_type=self._parse_order_type(data.get("order_type", OrderType.LIMIT)),
            status=self._parse_status(data.get("status", OrderStatus.SUBMITTED)),
            filled_quantity=int(data.get("filled_quantity") or data.get("dealt") or 0),
            filled_price=float(data.get("filled_price") or data.get("avg_price") or price),
            create_time=self._parse_datetime(data.get("create_time") or data.get("ctime")),
            update_time=self._parse_datetime(data.get("update_time") or data.get("mtime")),
        )
        return order

    def _parse_trade(self, data: Dict[str, Any]) -> Trade:
        return Trade(
            trade_id=str(data.get("trade_id") or data.get("id") or ""),
            order_id=str(data.get("order_id") or data.get("cl_ord_id") or ""),
            code=str(data.get("code") or data.get("stock_code") or ""),
            side=self._parse_side(data.get("side", OrderSide.BUY)),
            price=float(data.get("price", 0.0)),
            quantity=int(data.get("quantity") or data.get("volume") or 0),
            commission=float(data.get("commission", 0.0)),
            trade_time=self._parse_datetime(data.get("trade_time") or data.get("time")),
        )

    # ==================== 日志助手 ====================

    def _log_info(self, message: str):
        self.logger.info(f"[REST-{self.config.broker_type.value}] {message}", LogCategory.TRADE)

    def _log_error(self, message: str):
        super()._log_error(message)
