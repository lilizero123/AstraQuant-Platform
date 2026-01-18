"""
系统设置对话框
"""
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QDoubleSpinBox,
    QDialogButtonBox,
    QMessageBox,
    QCheckBox,
    QLabel,
    QGroupBox,
)
from PyQt5.QtCore import Qt

from config.settings import config_manager


class SettingsDialog(QDialog):
    """全局设置面板"""

    BROKERS = [
        ("模拟交易", "simulated"),
        ("华泰证券", "huatai"),
        ("中信证券", "zhongxin"),
        ("国泰君安", "guotai"),
        ("海通证券", "haitong"),
        ("广发证券", "guangfa"),
    ]

    AI_PROVIDERS = [
        ("本地助手", "local"),
        ("阿里百炼（DashScope）", "qwen"),
        ("腾讯混元", "hunyuan"),
        ("DeepSeek", "deepseek"),
        ("Kimi（月之暗面）", "kimi"),
        ("OpenAI", "openai"),
        ("Azure", "azure"),
        ("自定义", "custom"),
    ]

    AI_PROVIDER_DEFAULTS = {
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "hint": "阿里百炼 API Key 可在 dashscope 控制台获取",
        },
        "hunyuan": {
            "base_url": "https://hunyuan.tencentcloudapi.com",
            "model": "hunyuan-lite",
            "hint": "腾讯混元需要在腾讯云控制台创建 API 密钥",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "hint": "DeepSeek API Key 需在官网申请",
        },
        "kimi": {
            "base_url": "https://api.moonshot.cn/v1",
            "model": "moonshot-v1-8k",
            "hint": "Kimi API Key 可在月之暗面开放平台申请",
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setModal(True)
        self.resize(520, 420)
        self.config = config_manager
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_data_tab()
        self._build_trade_tab()
        self._build_ai_tab()

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _build_data_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setLabelAlignment(Qt.AlignRight)

        self.combo_data_source = QComboBox()
        self.combo_data_source.addItems(["akshare", "tushare", "csv", "multisource", "simulated"])
        self.combo_data_source.currentTextChanged.connect(self._sync_data_fields)

        self.edit_tushare_token = QLineEdit()
        self.edit_tushare_token.setPlaceholderText("Tushare Token")

        self.edit_csv_path = QLineEdit()
        self.checkbox_csv_loop = QCheckBox("循环回放")
        self.spin_csv_speed = QDoubleSpinBox()
        self.spin_csv_speed.setRange(0.1, 10.0)
        self.spin_csv_speed.setDecimals(2)
        self.spin_csv_speed.setSingleStep(0.1)

        self.spin_sim_interval = QDoubleSpinBox()
        self.spin_sim_interval.setRange(0.1, 10.0)
        self.spin_sim_interval.setDecimals(2)
        self.spin_sim_interval.setSingleStep(0.1)

        self.spin_sim_volatility = QDoubleSpinBox()
        self.spin_sim_volatility.setRange(0.0001, 0.2)
        self.spin_sim_volatility.setDecimals(4)
        self.spin_sim_volatility.setSingleStep(0.001)

        self.spin_http_interval = QDoubleSpinBox()
        self.spin_http_interval.setRange(0.5, 30.0)
        self.spin_http_interval.setDecimals(1)
        self.spin_http_interval.setSingleStep(0.5)

        self.edit_data_path = QLineEdit()
        self.edit_strategy_path = QLineEdit()
        self.edit_log_path = QLineEdit()

        form.addRow("数据源:", self.combo_data_source)
        form.addRow("Tushare Token:", self.edit_tushare_token)
        form.addRow("CSV 路径:", self.edit_csv_path)
        form.addRow("", self.checkbox_csv_loop)
        form.addRow("回放倍速:", self.spin_csv_speed)
        form.addRow("模拟间隔(秒):", self.spin_sim_interval)
        form.addRow("模拟波动率(%):", self.spin_sim_volatility)
        form.addRow("HTTP轮询(秒):", self.spin_http_interval)
        form.addRow("数据目录:", self.edit_data_path)
        form.addRow("策略目录:", self.edit_strategy_path)
        form.addRow("日志目录:", self.edit_log_path)

        proxy_group = QGroupBox("代理配置")
        proxy_layout = QFormLayout(proxy_group)
        proxy_layout.setLabelAlignment(Qt.AlignRight)
        self.checkbox_proxy_enabled = QCheckBox("启用代理池")
        self.checkbox_proxy_enabled.toggled.connect(self._sync_proxy_fields)
        self.edit_proxy_pool = QLineEdit()
        self.edit_proxy_pool.setPlaceholderText("例如：http://proxy-provider/api/get")
        self.edit_proxy_static = QLineEdit()
        self.edit_proxy_static.setPlaceholderText("备用代理，如 127.0.0.1:7890")
        self.edit_proxy_user = QLineEdit()
        self.edit_proxy_password = QLineEdit()
        self.edit_proxy_password.setEchoMode(QLineEdit.Password)
        self.spin_proxy_rotate = QDoubleSpinBox()
        self.spin_proxy_rotate.setRange(10, 600)
        self.spin_proxy_rotate.setDecimals(0)
        self.spin_proxy_rotate.setSuffix(" 秒")
        self.spin_proxy_rotate.setSingleStep(10)
        proxy_layout.addRow(self.checkbox_proxy_enabled)
        proxy_layout.addRow("代理池URL:", self.edit_proxy_pool)
        proxy_layout.addRow("固定代理:", self.edit_proxy_static)
        proxy_layout.addRow("用户名:", self.edit_proxy_user)
        proxy_layout.addRow("密码:", self.edit_proxy_password)
        proxy_layout.addRow("轮换间隔:", self.spin_proxy_rotate)
        form.addRow(proxy_group)
        self.tabs.addTab(widget, "数据")

    def _build_trade_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setLabelAlignment(Qt.AlignRight)

        self.combo_broker = QComboBox()
        for text, _value in self.BROKERS:
            self.combo_broker.addItem(text)

        self.edit_broker_account = QLineEdit()
        self.edit_broker_password = QLineEdit()
        self.edit_broker_password.setEchoMode(QLineEdit.Password)
        self.edit_broker_api = QLineEdit()
        self.edit_broker_api_key = QLineEdit()
        self.edit_broker_api_secret = QLineEdit()
        self.edit_broker_api_secret.setEchoMode(QLineEdit.Password)
        self.edit_broker_client_cert = QLineEdit()
        self.edit_broker_client_cert.setPlaceholderText("client_cert.pem")
        self.checkbox_broker_verify_ssl = QCheckBox("启用SSL验证")
        self.checkbox_broker_verify_ssl.setChecked(True)
        self.checkbox_auto_strategy = QCheckBox("策略自动下单")
        self.checkbox_auto_strategy.setChecked(True)

        self.spin_capital = QDoubleSpinBox()
        self.spin_capital.setRange(1000, 1_000_000_000)
        self.spin_capital.setDecimals(2)
        self.spin_capital.setSingleStep(10000)

        self.spin_commission = QDoubleSpinBox()
        self.spin_commission.setRange(0, 1)
        self.spin_commission.setDecimals(4)

        self.spin_slippage = QDoubleSpinBox()
        self.spin_slippage.setRange(0, 10)
        self.spin_slippage.setDecimals(4)

        form.addRow("默认券商:", self.combo_broker)
        form.addRow("券商账号:", self.edit_broker_account)
        form.addRow("券商密码:", self.edit_broker_password)
        form.addRow("券商API:", self.edit_broker_api)
        form.addRow("API Key:", self.edit_broker_api_key)
        form.addRow("API Secret:", self.edit_broker_api_secret)
        form.addRow("客户端证书:", self.edit_broker_client_cert)
        form.addRow("", self.checkbox_broker_verify_ssl)
        form.addRow("", self.checkbox_auto_strategy)
        form.addRow("初始资金:", self.spin_capital)
        form.addRow("手续费率:", self.spin_commission)
        form.addRow("滑点(%):", self.spin_slippage)
        self.tabs.addTab(widget, "交易")

    def _build_ai_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setLabelAlignment(Qt.AlignRight)

        self.checkbox_ai_remote = QCheckBox("启用自定义AI接口")
        self.checkbox_ai_remote.toggled.connect(self._sync_ai_fields)
        self.combo_ai_provider = QComboBox()
        for text, _value in self.AI_PROVIDERS:
            self.combo_ai_provider.addItem(text)
        self.combo_ai_provider.currentIndexChanged.connect(self._apply_ai_provider_defaults)

        self.edit_ai_base_url = QLineEdit()
        self.edit_ai_api_key = QLineEdit()
        self.edit_ai_api_key.setEchoMode(QLineEdit.Password)
        self.edit_ai_model = QLineEdit()

        form.addRow(self.checkbox_ai_remote)
        form.addRow("服务提供商:", self.combo_ai_provider)
        form.addRow("Base URL:", self.edit_ai_base_url)
        form.addRow("API Key:", self.edit_ai_api_key)
        form.addRow("模型名称:", self.edit_ai_model)
        self.label_ai_hint = QLabel("提示：AI API Key 仅保存在本地 config/settings.json")
        self.label_ai_hint.setWordWrap(True)
        self.label_ai_hint.setStyleSheet("color: #8b949e; font-size: 11px;")
        form.addRow(self.label_ai_hint)

        self.tabs.addTab(widget, "AI")

    def _load_values(self):
        cfg = self.config.get_all()
        self.combo_data_source.setCurrentText(cfg.get("data_source", "akshare"))
        self.edit_tushare_token.setText(cfg.get("tushare_token", ""))
        self.edit_csv_path.setText(cfg.get("csv_data_path", ""))
        self.checkbox_csv_loop.setChecked(cfg.get("csv_loop", False))
        self.spin_csv_speed.setValue(cfg.get("csv_speed", 1.0))
        self.spin_sim_interval.setValue(cfg.get("sim_interval", 1.0))
        self.spin_sim_volatility.setValue(cfg.get("sim_volatility", 0.01))
        self.spin_http_interval.setValue(cfg.get("http_data_interval", 2.0))
        self.edit_data_path.setText(cfg.get("data_path", "./data"))
        self.edit_strategy_path.setText(cfg.get("strategy_path", "./strategies"))
        self.edit_log_path.setText(cfg.get("log_path", "./logs"))

        broker_value = cfg.get("broker_type", "simulated")
        self.combo_broker.setCurrentIndex(
            max(0, self._index_from_lookup(self.BROKERS, broker_value))
        )
        self.edit_broker_account.setText(cfg.get("broker_account", ""))
        self.edit_broker_password.setText(cfg.get("broker_password", ""))
        self.edit_broker_api.setText(cfg.get("broker_api_url", ""))
        self.edit_broker_api_key.setText(cfg.get("broker_api_key", ""))
        self.edit_broker_api_secret.setText(cfg.get("broker_api_secret", ""))
        self.checkbox_broker_verify_ssl.setChecked(cfg.get("broker_api_verify_ssl", True))
        self.edit_broker_client_cert.setText(cfg.get("broker_api_client_cert", ""))
        self.spin_capital.setValue(cfg.get("initial_capital", 1000000.0))
        self.spin_commission.setValue(cfg.get("commission_rate", 0.0003))
        self.spin_slippage.setValue(cfg.get("slippage", 0.001))
        self.checkbox_auto_strategy.setChecked(cfg.get("strategy_auto_execute", True))
        self.checkbox_proxy_enabled.setChecked(cfg.get("proxy_enabled", False))
        self.edit_proxy_pool.setText(cfg.get("proxy_pool_url", ""))
        self.edit_proxy_static.setText(cfg.get("proxy_static", ""))
        self.edit_proxy_user.setText(cfg.get("proxy_username", ""))
        self.edit_proxy_password.setText(cfg.get("proxy_password", ""))
        self.spin_proxy_rotate.setValue(cfg.get("proxy_rotate_interval", 120))
        self._sync_proxy_fields()

        provider_value = cfg.get("ai_provider", "local")
        self.combo_ai_provider.blockSignals(True)
        self.combo_ai_provider.setCurrentIndex(
            max(0, self._index_from_lookup(self.AI_PROVIDERS, provider_value))
        )
        self.combo_ai_provider.blockSignals(False)
        self.checkbox_ai_remote.setChecked(cfg.get("ai_use_remote", False))
        self.edit_ai_base_url.setText(cfg.get("ai_base_url", ""))
        self.edit_ai_api_key.setText(cfg.get("ai_api_key", ""))
        self.edit_ai_model.setText(cfg.get("ai_model", ""))
        self._sync_ai_fields()
        self._set_ai_provider_defaults(force=False)
        self._sync_data_fields()

    def _index_from_lookup(self, options, target_value: str) -> int:
        for idx, (_, value) in enumerate(options):
            if value == target_value:
                return idx
        return 0

    def _collect_values(self) -> dict:
        broker_value = self.BROKERS[self.combo_broker.currentIndex()][1]
        ai_provider = self.AI_PROVIDERS[self.combo_ai_provider.currentIndex()][1]
        return {
            "data_source": self.combo_data_source.currentText(),
            "tushare_token": self.edit_tushare_token.text().strip(),
            "csv_data_path": self.edit_csv_path.text().strip(),
            "csv_loop": self.checkbox_csv_loop.isChecked(),
            "csv_speed": float(self.spin_csv_speed.value()),
            "sim_interval": float(self.spin_sim_interval.value()),
            "sim_volatility": float(self.spin_sim_volatility.value()),
            "http_data_interval": float(self.spin_http_interval.value()),
            "data_path": self.edit_data_path.text().strip() or "./data",
            "strategy_path": self.edit_strategy_path.text().strip() or "./strategies",
            "log_path": self.edit_log_path.text().strip() or "./logs",
            "broker_type": broker_value,
            "broker_account": self.edit_broker_account.text().strip(),
            "broker_password": self.edit_broker_password.text().strip(),
            "broker_api_url": self.edit_broker_api.text().strip(),
            "broker_api_key": self.edit_broker_api_key.text().strip(),
            "broker_api_secret": self.edit_broker_api_secret.text().strip(),
            "broker_api_client_cert": self.edit_broker_client_cert.text().strip(),
            "broker_api_verify_ssl": self.checkbox_broker_verify_ssl.isChecked(),
            "strategy_auto_execute": self.checkbox_auto_strategy.isChecked(),
            "initial_capital": float(self.spin_capital.value()),
            "commission_rate": float(self.spin_commission.value()),
            "slippage": float(self.spin_slippage.value()),
            "ai_use_remote": self.checkbox_ai_remote.isChecked(),
            "ai_provider": ai_provider,
            "ai_api_key": self.edit_ai_api_key.text().strip(),
            "ai_base_url": self.edit_ai_base_url.text().strip(),
            "ai_model": self.edit_ai_model.text().strip(),
            "proxy_enabled": self.checkbox_proxy_enabled.isChecked(),
            "proxy_pool_url": self.edit_proxy_pool.text().strip(),
            "proxy_static": self.edit_proxy_static.text().strip(),
            "proxy_username": self.edit_proxy_user.text().strip(),
            "proxy_password": self.edit_proxy_password.text().strip(),
            "proxy_rotate_interval": int(self.spin_proxy_rotate.value()),
        }

    def _on_save(self):
        try:
            payload = self._collect_values()
            self.config.update(payload)
            QMessageBox.information(self, "提示", "设置已保存")
            self.accept()
        except Exception as err:  # pragma: no cover - 防御
            QMessageBox.warning(self, "错误", f"保存失败: {err}")

    def _sync_ai_fields(self):
        enabled = self.checkbox_ai_remote.isChecked()
        for widget in (self.combo_ai_provider, self.edit_ai_base_url, self.edit_ai_api_key, self.edit_ai_model):
            widget.setEnabled(enabled)
        self._set_ai_provider_defaults(force=False)

    def _sync_data_fields(self):
        source = self.combo_data_source.currentText()
        is_csv = source == "csv"
        is_sim = source == "simulated"
        is_http = source in {"multisource", "tushare"}
        requires_token = source in {"tushare", "multisource"}

        for widget in (self.edit_csv_path, self.checkbox_csv_loop, self.spin_csv_speed):
            widget.setEnabled(is_csv)
        for widget in (self.spin_sim_interval, self.spin_sim_volatility):
            widget.setEnabled(is_sim)
        self.spin_http_interval.setEnabled(is_http)
        self.edit_tushare_token.setEnabled(requires_token)

    def _sync_proxy_fields(self):
        enabled = self.checkbox_proxy_enabled.isChecked()
        for widget in (
            self.edit_proxy_pool,
            self.edit_proxy_static,
            self.edit_proxy_user,
            self.edit_proxy_password,
            self.spin_proxy_rotate,
        ):
            widget.setEnabled(enabled)

    def _apply_ai_provider_defaults(self, *_args):
        self._set_ai_provider_defaults(force=True)

    def _set_ai_provider_defaults(self, force: bool):
        if not hasattr(self, "combo_ai_provider"):
            return
        index = self.combo_ai_provider.currentIndex()
        if index < 0 or index >= len(self.AI_PROVIDERS):
            return
        provider_key = self.AI_PROVIDERS[index][1]
        defaults = self.AI_PROVIDER_DEFAULTS.get(provider_key, {})
        hint = defaults.get("hint", "提示：AI API Key 仅保存在本地 config/settings.json")
        if hasattr(self, "label_ai_hint"):
            self.label_ai_hint.setText(hint)

        if provider_key == "custom" or provider_key == "local":
            return

        base_url = defaults.get("base_url", "")
        model_name = defaults.get("model", "")

        if base_url and (force or not self.edit_ai_base_url.text().strip()):
            self.edit_ai_base_url.setText(base_url)
        if model_name and (force or not self.edit_ai_model.text().strip()):
            self.edit_ai_model.setText(model_name)
