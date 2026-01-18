"""
配置管理模块
"""
import json
import os
from typing import Any, Dict
from dataclasses import dataclass, asdict

from core.security import secret_store


@dataclass
class AppConfig:
    """应用配置"""
    # 数据源配置
    data_source: str = "akshare"      # 数据源: akshare, tushare, csv
    tushare_token: str = ""           # Tushare token
    data_path: str = "./data"           # 数据存储路径
    strategy_path: str = "./strategies" # 策略存储路径
    log_path: str = "./logs"            # 日志存储路径
    csv_data_path: str = ""             # CSV 行情路径
    csv_loop: bool = False
    csv_speed: float = 1.0             # 回放倍速
    sim_interval: float = 1.0          # 模拟行情推送间隔
    sim_volatility: float = 0.01       # 模拟波动率（百分比）
    http_data_interval: float = 2.0    # 多数据源行情轮询间隔

    # 交易配置
    initial_capital: float = 1000000.0  # 初始资金
    commission_rate: float = 0.0003     # 手续费率
    slippage: float = 0.001             # 滑点
    broker_type: str = "simulated"      # 券商类型
    broker_account: str = ""            # 账号
    broker_password: str = ""           # 密码
    broker_api_url: str = ""            # API 地址
    broker_api_key: str = ""            # API Key
    broker_api_secret: str = ""         # API Secret
    api_poll_interval: int = 3          # 券商轮询间隔
    api_timeout: int = 8                # HTTP 超时时间（秒）
    broker_api_verify_ssl: bool = True  # 是否校验证书
    broker_api_client_cert: str = ""    # 客户端证书路径
    strategy_auto_execute: bool = True  # 自动执行策略订单

    # 风控配置
    max_position_pct: float = 30.0      # 单只股票最大仓位
    max_total_position_pct: float = 80.0  # 总仓位最大比例
    stop_loss_pct: float = 5.0          # 止损比例
    take_profit_pct: float = 10.0       # 止盈比例
    max_drawdown_pct: float = 20.0      # 最大回撤
    risk_journal_path: str = "./logs/risk_journal.csv"

    # AI 配置
    ai_use_remote: bool = False
    ai_provider: str = "local"
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = ""
    ai_prompt_file: str = ""

    # 界面配置
    theme: str = "dark"                 # 主题: dark, light
    language: str = "zh"                # 语言

    # 代理配置
    proxy_enabled: bool = False
    proxy_pool_url: str = ""
    proxy_static: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
    proxy_rotate_interval: int = 120

    # 法务相关
    disclaimer_accepted_version: int = 0


class ConfigManager:
    """配置管理器"""

    SENSITIVE_FIELDS = {
        "broker_password": "broker_password",
        "tushare_token": "tushare_token",
        "ai_api_key": "ai_api_key",
        "broker_api_secret": "broker_api_secret",
        "broker_api_key": "broker_api_key",
        "proxy_password": "proxy_password",
    }

    def __init__(self, config_file: str = "config/settings.json"):
        self.config_file = config_file
        self.config = AppConfig()
        self.load()

    def load(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if not hasattr(self.config, key):
                            continue
                        if key in self.SENSITIVE_FIELDS:
                            setattr(self.config, key, self._read_sensitive(key, value))
                        else:
                            setattr(self.config, key, self._normalize_value(key, value))
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save(self):
        """保存配置"""
        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            data = asdict(self.config)
            for field, alias in self.SENSITIVE_FIELDS.items():
                raw_value = data.get(field)
                if raw_value:
                    secret_store.store_secret(alias, raw_value)
                    data[field] = {"keyring": alias}
                else:
                    secret_store.delete_secret(alias)
                    data[field] = ""
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def update(self, data: Dict[str, Any]):
        """批量更新配置"""
        for key, value in data.items():
            if hasattr(self.config, key):
                setattr(self.config, key, self._normalize_value(key, value))
        self.save()

    @staticmethod
    def _normalize_value(key: str, value: Any) -> Any:
        """针对特殊字段做兼容处理"""
        if key == "language" and isinstance(value, str):
            if value.startswith("zh"):
                return "zh"
            if value.startswith("en"):
                return "en"
        return value

    def _read_sensitive(self, key: str, value: Any) -> str:
        alias = self.SENSITIVE_FIELDS[key]
        if isinstance(value, dict) and value.get("keyring"):
            secret = secret_store.get_secret(alias)
            return secret or ""
        if isinstance(value, str):
            # 兼容旧版本: 明文写入
            secret_store.store_secret(alias, value)
            return value
        return ""

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any):
        """设置配置项"""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self.save()

    def get_all(self) -> Dict:
        """获取所有配置"""
        return asdict(self.config)

    def reset(self):
        """重置为默认配置"""
        self.config = AppConfig()
        self.save()


# 全局配置实例
config_manager = ConfigManager()
