"""
AI helper utilities used by the UI.

The helper provides deterministic, heuristic based fallbacks so the product can
showcase AI assisted workflows even when an actual LLM endpoint is not
configured.  To integrate with a real model simply replace the logic inside the
public methods with network calls and keep the return signatures identical.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests

from config.settings import config_manager
from core.backtest.engine import BacktestResult
from core.network.proxy_manager import proxy_manager


@dataclass
class StrategySuggestion:
    """Represents a strategy that was proposed by the AI helper."""

    code: str
    summary: str
    title: str


class AIHelper:
    """
    Lightweight strategy/backtest assistant.

    The class exposes synchronous helper functions so the UI layer can call it
    directly without threading.  The implementation looks at the user prompt or
    the backtest metrics and generates high level insights.
    """

    def __init__(self, config=None):
        self._templates = self._load_templates()
        self._config = config or config_manager
        self._system_prompt = ""
        self.reload_config(self._config)

    def reload_config(self, config=None):
        """重新读取配置，支持外部更新"""
        if config is not None:
            self._config = config
        cfg = {}
        if self._config:
            cfg = getattr(self._config, "get_all", lambda: {})()
        self.ai_use_remote = cfg.get("ai_use_remote", False)
        self.ai_provider = cfg.get("ai_provider", "local")
        self.ai_api_key = cfg.get("ai_api_key", "")
        self.ai_base_url = (cfg.get("ai_base_url") or "").rstrip("/")
        self.ai_model = cfg.get("ai_model", "")
        prompt_override = cfg.get("ai_prompt_file") if isinstance(cfg, dict) else None
        self._system_prompt = self._load_system_prompt(prompt_override)

    # ------------------------------------------------------------------ public
    def generate_strategy(self, prompt: str) -> StrategySuggestion:
        """
        Create a new strategy suggestion based on a free-form prompt.

        Args:
            prompt: User instructions collected from the UI.
        """
        remote = self._remote_action(
            "strategy_generate",
            {"prompt": prompt},
        )
        if remote:
            return StrategySuggestion(code=remote.get("code", ""), summary=remote.get("summary", ""), title=remote.get("title", "AI Strategy"))

        prompt_lower = prompt.lower()
        template_key = "momentum"
        for keyword, key in [
            ("macd", "macd"),
            ("boll", "boll"),
            ("band", "boll"),
            ("rsi", "rsi"),
            ("break", "breakout"),
            ("trend", "momentum"),
            ("mean", "mean_reversion"),
        ]:
            if keyword in prompt_lower:
                template_key = key
                break

        template = self._templates.get(template_key, self._templates["momentum"])
        summary = self._build_strategy_summary(template_key, template["idea"], prompt)

        code = template["code"].format(prompt=prompt)
        return StrategySuggestion(
            code=code,
            summary=summary,
            title=template["title"],
        )

    def review_strategy(self, code: str) -> str:
        """
        Provide a textual review of an existing piece of strategy code.

        The implementation evaluates the presence of basic components and emits
        guidance that mimics what an AI reviewer would say.
        """
        remote = self._remote_action(
            "strategy_review",
            {"code": code},
        )
        if remote:
            return remote.get("result") or remote.get("text", "")

        findings = []
        lower_code = code.lower()

        if "sell" not in lower_code:
            findings.append("• 未检测到 `sell()` 调用，策略可能没有明确的退出路径。")
        if "buy" not in lower_code:
            findings.append("• 未检测到 `buy()` 调用，需要补充买入条件。")
        if "stop" not in lower_code:
            findings.append("• 建议补充止损/止盈逻辑以降低尾部风险。")
        if "position" in lower_code:
            findings.append("• 代码已引用 `position`，请确保仓位管理逻辑与资金规模匹配。")
        if "self.log" not in lower_code:
            findings.append("• 可以在关键逻辑中加入 `self.log(...)` 便于回测排查。")

        if not findings:
            findings.append("• 代码结构完整，建议直接回测验证参数稳定性。")

        return "AI 策略诊断:\n" + "\n".join(findings)

    def summarize_backtest(
        self,
        result: BacktestResult,
        context: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Convert a BacktestResult into an analyst-style paragraph.
        """
        remote = self._remote_action(
            "backtest_summary",
            {
                "result": {
                    "start_date": result.start_date,
                    "end_date": result.end_date,
                    "total_return": result.total_return,
                    "annual_return": result.annual_return,
                    "max_drawdown": result.max_drawdown,
                    "win_rate": result.win_rate,
                    "profit_loss_ratio": result.profit_loss_ratio,
                    "sharpe_ratio": result.sharpe_ratio,
                },
                "context": context or {},
            },
        )
        if remote:
            return remote.get("result") or remote.get("summary", "")

        context = context or {}
        lines = []

        strategy_name = context.get("strategy", "策略")
        lines.append(
            f"{strategy_name} 在 {result.start_date} ~ {result.end_date} 的回测表现："
        )
        lines.append(
            f"- 总收益 {result.total_return:.2f}%、年化 {result.annual_return:.2f}%，"
            f"胜率 {result.win_rate:.2f}%"
        )
        lines.append(
            f"- 最大回撤 {result.max_drawdown:.2f}%、夏普 {result.sharpe_ratio:.2f}、盈亏比 {result.profit_loss_ratio:.2f}"
        )

        if result.total_return < 0:
            lines.append("收益为负，建议检查信号方向是否与市场环境相符。")
        elif result.annual_return < 5:
            lines.append("收益偏保守，可调高仓位或延长持有期提升期望。")
        else:
            lines.append("收益质量良好，可进一步做参数走查验证稳定性。")

        if result.max_drawdown > 15:
            lines.append("回撤较大，建议在策略中增加动态止损或仓位上限。")
        elif result.max_drawdown < 5:
            lines.append("回撤控制优秀，可以评估是否还有加杠杆空间。")

        if result.win_rate < 40:
            lines.append("胜率偏低，可考虑提高信号确认阈值或过滤震荡区间。")
        elif result.win_rate > 70:
            lines.append("胜率较高，重点关注是否存在盈亏不对称导致的尾部风险。")

        if result.profit_loss_ratio < 1:
            lines.append("盈亏比小于 1，需检查止盈止损设置是否合理。")

        lines.append(
            "AI 建议：结合最近的市场波动，先在小资金上进行滚动复盘，确认交易成本与滑点。"
        )
        suggestions = self._build_backtest_suggestions(result, context)
        if suggestions:
            lines.append("数据与参数优化提示：")
            lines.extend(f"- {hint}" for hint in suggestions)

        return "\n".join(lines)

    def suggest_parameters(self, hint: str = "") -> Dict[str, float]:
        """
        根据用户偏好生成默认的策略参数建议。
        """
        remote = self._remote_action("parameter_hint", {"hint": hint})
        if remote and isinstance(remote, dict):
            return remote

        hint = hint.lower()
        params = {
            "fast_period": 5,
            "slow_period": 20,
            "stop_loss": 5.0,
            "take_profit": 10.0,
        }

        if "macd" in hint:
            params.update({"fast_period": 12, "slow_period": 26})
        elif "short" in hint or "scalp" in hint or "短线" in hint:
            params.update({"fast_period": 3, "slow_period": 9, "stop_loss": 2.5})
        elif "long" in hint or "position" in hint or "波段" in hint:
            params.update({"fast_period": 10, "slow_period": 40, "take_profit": 15})
        elif "reversion" in hint or "回归" in hint:
            params.update({"fast_period": 7, "slow_period": 14, "take_profit": 6})

        params["comment"] = (
            "AI 参数建议：根据关键词"
            f"『{hint or '默认'}』设置快慢线、止损止盈，可在保存前微调。"
        )
        return params

    def analyze_quote(
        self,
        code: str,
        last_price: float,
        change_pct: float,
        volume: float,
    ) -> str:
        """
        根据最新行情给出文本点评。
        """
        remote = self._remote_action(
            "quote_analyze",
            {
                "code": code,
                "last_price": last_price,
                "change_pct": change_pct,
                "volume": volume,
            },
        )
        if remote:
            return remote.get("result") or remote.get("text", "")

        sentiment = "震荡"
        if change_pct > 2:
            sentiment = "强势上攻"
        elif change_pct < -2:
            sentiment = "显著回调"

        volume_hint = "成交量平稳"
        if volume > 1e7:
            volume_hint = "成交放大，资金介入明显"
        elif volume < 1e6:
            volume_hint = "量能偏弱，需谨慎"

        return (
            f"{code} 最新价 {last_price:.2f}，涨跌幅 {change_pct:.2f}% ({sentiment})。\n"
            f"{volume_hint}。若后续能守住关键支撑位，可继续观察；"
            "若跌破则考虑止损或减仓。"
        )

    def advise_order(
        self,
        *,
        code: str,
        direction: str,
        price: float,
        quantity: int,
        cash_available: Optional[float] = None,
        position_size: Optional[int] = None,
    ) -> str:
        """
        对下单参数进行快速风控点评。
        """
        remote = self._remote_action(
            "order_advise",
            {
                "code": code,
                "direction": direction,
                "price": price,
                "quantity": quantity,
                "cash_available": cash_available,
                "position_size": position_size,
            },
        )
        if remote:
            return remote.get("result") or remote.get("text", "")

        notes: List[str] = [f"下单标的 {code}，方向 {direction}，价格 {price:.2f}，数量 {quantity}。"]

        if cash_available is not None and direction == "买入":
            required = price * quantity
            if required > cash_available * 0.9:
                notes.append("• 此次下单接近可用资金上限，留意流动性和后续补仓空间。")
            else:
                notes.append("• 资金占比适中，可按计划执行。")

        if position_size is not None and direction == "卖出":
            if quantity >= position_size:
                notes.append("• 拟清仓操作，请确认是否需要分批减仓。")
            elif quantity > position_size * 0.5:
                notes.append("• 卖出超过一半仓位，建议同步回顾止盈/止损依据。")

        if direction == "买入" and quantity < 100:
            notes.append("• 委托数量小于 100，可能无法成交，A 股需整数手。")

        if direction == "卖出" and position_size and quantity > position_size:
            notes.append("• 卖出数量超出现有持仓，请检查输入。")

        return "\n".join(notes)

    def summarize_logs(self, logs: List[dict]) -> str:
        """
        对近期日志做简要汇总。
        """
        remote = self._remote_action("log_summary", {"logs": logs})
        if remote:
            return remote.get("result") or remote.get("summary", "")

        if not logs:
            return "暂无日志可供总结。"

        category_count: Dict[str, int] = {}
        level_count: Dict[str, int] = {}
        latest_messages = []
        for entry in logs[-50:]:
            category_count[entry["category"]] = category_count.get(entry["category"], 0) + 1
            level_count[entry["level"]] = level_count.get(entry["level"], 0) + 1
            latest_messages.append(f"[{entry['category']}] {entry['message']}")

        top_category = max(category_count, key=category_count.get)
        top_level = max(level_count, key=level_count.get)
        summary = [
            f"近{len(logs)}条日志：以 {top_category} 类为主，"
            f"告警级别以 {top_level} 为主。",
            "最近事件：",
        ]
        summary.extend(latest_messages[-5:])
        summary.append("AI 建议按类别逐一复盘，确认告警是否已处理。")
        return "\n".join(summary)

    @staticmethod
    def _build_backtest_suggestions(result: BacktestResult, context: Optional[Dict[str, str]]) -> List[str]:
        """根据绩效指标给出可执行的数据与参数优化提示。"""
        suggestions: List[str] = []
        strategy_name = context.get("strategy", "策略") if context else "策略"

        if result.total_return < 0 or result.annual_return < 5:
            suggestions.append(f"{strategy_name} 在当前样本上收益偏低，建议扩充历史区间或补充行业/指数数据做对比，确认信号是否只适用于特定行情。")

        if result.max_drawdown > 12:
            suggestions.append("回撤较大，可在数据集中加入成交量或波动率指标作为过滤条件，并缩短持仓周期，避免在高波动段全仓暴露。")

        if result.win_rate < 45:
            suggestions.append("胜率不足 45%，可增加多周期确认数据（如周线趋势或资金流向）作为入场条件，减少噪声信号。")

        if result.profit_loss_ratio < 1:
            suggestions.append("盈亏比低于 1，考虑调整止盈/止损参数，或引入更细粒度的分钟数据以提高出场精度。")

        if result.sharpe_ratio < 0.8:
            suggestions.append("夏普低于 0.8，建议在特征中增加宏观或因子数据，或对收益序列做去极值处理以提升稳定性。")

        if result.total_trades < 5:
            suggestions.append("交易次数过少，可以使用更短的回测周期或拓展股票池，避免样本过窄导致结论失真。")

        return suggestions

    # ----------------------------------------------------------------- remote
    def _remote_action(self, action: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.ai_use_remote or not self.ai_base_url:
            return None
        url = f"{self.ai_base_url}/api/assistant"
        body = {
            "action": action,
            "model": self.ai_model or "default",
            "provider": self.ai_provider,
            "payload": payload,
        }
        if self._system_prompt:
            body["system_prompt"] = self._system_prompt
        headers = {"Content-Type": "application/json"}
        if self.ai_api_key:
            headers["Authorization"] = f"Bearer {self.ai_api_key}"
        try:
            proxies = proxy_manager.get_requests_proxies()
            resp = requests.post(url, json=body, timeout=15, headers=headers, proxies=proxies)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            return {"result": str(data)}
        except requests.RequestException:
            return None

    # ----------------------------------------------------------------- helpers
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Prepare canned templates that act as AI strategy outputs.
        """
        return {
            "momentum": {
                "title": "均线动量策略",
                "idea": "使用双均线交叉捕捉趋势，并附带仓位控制建议。",
                "code": self._dual_ma_template(),
            },
            "macd": {
                "title": "MACD 趋势策略",
                "idea": "依赖 DIF 与 DEA 金叉/死叉控制进出场。",
                "code": self._macd_template(),
            },
            "boll": {
                "title": "布林带反转策略",
                "idea": "利用布林上下轨寻找极值，附带仓位分批。",
                "code": self._boll_template(),
            },
            "rsi": {
                "title": "RSI 超买超卖策略",
                "idea": "默认 14 周期 RSI，通过阈值判断回调。",
                "code": self._rsi_template(),
            },
            "breakout": {
                "title": "通道突破策略",
                "idea": "根据最高最低通道判断突破加仓。",
                "code": self._breakout_template(),
            },
            "mean_reversion": {
                "title": "均值回归策略",
                "idea": "结合 rolling mean 与标准差控制反转。",
                "code": self._mean_reversion_template(),
            },
        }

    @staticmethod
    def _build_strategy_summary(key: str, idea: str, prompt: str) -> str:
        return (
            f"AI 解析: 根据输入『{prompt or '未提供偏好'}』，推荐 {key} 方向。\n"
            f"策略思路：{idea}\n"
            "可直接回填代码或调整参数后回测验证。"
        )

    @staticmethod
    def _load_system_prompt(override: Optional[str]) -> str:
        candidates = []
        if override:
            candidates.append(Path(override))
        base_dir = Path(__file__).resolve().parents[2]
        candidates.append(base_dir / "resources" / "prompts" / "system_prompt.md")
        candidates.append(Path.cwd() / "resources" / "prompts" / "system_prompt.md")
        for path in candidates:
            try:
                if path and path.exists():
                    return path.read_text(encoding="utf-8").strip()
            except OSError:
                continue
        return ""

    # The following helpers keep template definitions separate to avoid clutter.
    @staticmethod
    def _dual_ma_template() -> str:
        return '''"""
AI 生成 - 均线动量策略
{prompt}
"""
from core.strategy.base import BaseStrategy, Bar


class AIMomentumStrategy(BaseStrategy):
    fast_period = 5
    slow_period = 20
    risk_pct = 0.9

    def on_bar(self, bar: Bar):
        closes = self.get_close_prices(self.slow_period + 2)
        if len(closes) < self.slow_period + 1:
            return

        fast = sum(closes[-self.fast_period:]) / self.fast_period
        slow = sum(closes[-self.slow_period:]) / self.slow_period
        prev_fast = sum(closes[-self.fast_period-1:-1]) / self.fast_period
        prev_slow = sum(closes[-self.slow_period-1:-1]) / self.slow_period

        qty = int(self.cash * self.risk_pct / bar.close / 100) * 100

        if prev_fast <= prev_slow and fast > slow and qty >= 100 and self.position == 0:
            self.buy(bar.close, qty)
            self.log(f"AI 动量买入 {qty} 股 @ {bar.close:.2f}")
        elif prev_fast >= prev_slow and fast < slow and self.position > 0:
            self.sell(bar.close, self.position)
            self.log(f"AI 动量卖出 全部仓位 @ {bar.close:.2f}")
'''

    @staticmethod
    def _macd_template() -> str:
        return '''"""
AI 生成 - MACD 趋势策略
{prompt}
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class AIMACDStrategy(BaseStrategy):
    fast_period = 12
    slow_period = 26
    signal_period = 9

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.slow_period + self.signal_period + 5)
        if len(bars) < self.slow_period + self.signal_period:
            return

        closes = [b.close for b in bars]
        macd = TechnicalIndicators.MACD(
            closes, self.fast_period, self.slow_period, self.signal_period
        )
        dif, dea = macd.dif, macd.dea
        if len(dif) < 2:
            return

        if dif[-2] <= dea[-2] and dif[-1] > dea[-1] and self.position == 0:
            qty = int(self.cash * 0.8 / bar.close / 100) * 100
            if qty >= 100:
                self.buy(bar.close, qty)
                self.log(f"AI MACD 金叉买入 {qty}")
        elif dif[-2] >= dea[-2] and dif[-1] < dea[-1] and self.position > 0:
            self.sell(bar.close, self.position)
            self.log("AI MACD 死叉卖出全部仓位")
'''

    @staticmethod
    def _boll_template() -> str:
        return '''"""
AI 生成 - 布林带反转策略
{prompt}
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class AIBollStrategy(BaseStrategy):
    period = 20
    sigma = 2.0

    def on_bar(self, bar: Bar):
        closes = [b.close for b in self.get_bars(self.period + 2)]
        if len(closes) < self.period:
            return

        boll = TechnicalIndicators.BOLL(closes, self.period, self.sigma)
        upper, middle, lower = boll.upper[-1], boll.middle[-1], boll.lower[-1]

        if bar.close <= lower and self.position == 0:
            qty = int(self.cash * 0.5 / bar.close / 100) * 100
            if qty >= 100:
                self.buy(bar.close, qty)
                self.log("AI 布林带低吸")
        elif bar.close >= middle and self.position > 0:
            self.sell(bar.close, self.position // 2)
            self.log("AI 布林带减仓锁定利润")
        if bar.close >= upper and self.position > 0:
            self.sell(bar.close, self.position)
            self.log("AI 布林带高抛出清")
'''

    @staticmethod
    def _rsi_template() -> str:
        return '''"""
AI 生成 - RSI 策略
{prompt}
"""
from core.strategy.base import BaseStrategy, Bar
from core.indicators import TechnicalIndicators


class AIRSIStrategy(BaseStrategy):
    period = 14
    oversold = 30
    overbought = 70

    def on_bar(self, bar: Bar):
        closes = [b.close for b in self.get_bars(self.period + 3)]
        if len(closes) < self.period + 1:
            return

        rsi = TechnicalIndicators.RSI(closes, self.period)
        if rsi[-2] < self.oversold <= rsi[-1] and self.position == 0:
            qty = int(self.cash * 0.6 / bar.close / 100) * 100
            if qty >= 100:
                self.buy(bar.close, qty)
                self.log("AI RSI 低位买入")
        elif rsi[-2] > self.overbought >= rsi[-1] and self.position > 0:
            self.sell(bar.close, self.position)
            self.log("AI RSI 高位卖出")
'''

    @staticmethod
    def _breakout_template() -> str:
        return '''"""
AI 生成 - 通道突破策略
{prompt}
"""
from core.strategy.base import BaseStrategy, Bar


class AIBreakoutStrategy(BaseStrategy):
    window = 20

    def on_bar(self, bar: Bar):
        bars = self.get_bars(self.window + 1)
        if len(bars) < self.window:
            return

        highs = [b.high for b in bars[:-1]]
        lows = [b.low for b in bars[:-1]]
        recent_high = max(highs)
        recent_low = min(lows)

        qty = int(self.cash * 0.7 / bar.close / 100) * 100
        if bar.close > recent_high and self.position == 0 and qty >= 100:
            self.buy(bar.close, qty)
            self.log("AI 突破买入")
        elif bar.close < recent_low and self.position > 0:
            self.sell(bar.close, self.position)
            self.log("AI 跌破通道清仓")
'''

    @staticmethod
    def _mean_reversion_template() -> str:
        return '''"""
AI 生成 - 均值回归策略
{prompt}
"""
from core.strategy.base import BaseStrategy, Bar


class AIMeanReversionStrategy(BaseStrategy):
    window = 15
    band = 1.5

    def on_bar(self, bar: Bar):
        closes = self.get_close_prices(self.window + 2)
        if len(closes) < self.window + 1:
            return

        mean = sum(closes[-self.window:]) / self.window
        std = (sum((c - mean) ** 2 for c in closes[-self.window:]) / self.window) ** 0.5
        upper = mean + std * self.band
        lower = mean - std * self.band

        qty = int(self.cash * 0.4 / bar.close / 100) * 100
        if bar.close < lower and self.position == 0 and qty >= 100:
            self.buy(bar.close, qty)
            self.log("AI 均值回归买入")
        elif bar.close > upper and self.position > 0:
            self.sell(bar.close, self.position)
            self.log("AI 均值回归卖出")
'''
