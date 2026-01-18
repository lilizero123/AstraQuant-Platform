"""
简单多语言支持
"""
from typing import Dict, List

AVAILABLE_LANGUAGES = {
    "zh": "中文",
    "en": "English",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "app.title": {"zh": "星衡量化平台", "en": "AstraQuant Platform"},
    "tab.market": {"zh": "  行情  ", "en": "  Market  "},
    "tab.strategy": {"zh": "  策略  ", "en": "  Strategy  "},
    "tab.backtest": {"zh": "  回测  ", "en": "  Backtest  "},
    "tab.trade": {"zh": "  交易  ", "en": "  Trading  "},
    "menu.file": {"zh": "文件", "en": "File"},
    "menu.strategy": {"zh": "策略", "en": "Strategy"},
    "menu.trade": {"zh": "交易", "en": "Trading"},
    "menu.help": {"zh": "帮助", "en": "Help"},
    "menu.settings": {"zh": "设置", "en": "Settings"},
    "menu.view": {"zh": "视图", "en": "View"},
    "menu.theme": {"zh": "主题", "en": "Theme"},
    "menu.language": {"zh": "语言", "en": "Language"},
    "action.import_data": {"zh": "导入数据", "en": "Import Data"},
    "action.export_data": {"zh": "导出数据", "en": "Export Data"},
    "action.exit": {"zh": "退出", "en": "Exit"},
    "action.new_strategy": {"zh": "新建策略", "en": "New Strategy"},
    "action.load_strategy": {"zh": "加载策略", "en": "Load Strategy"},
    "action.save_strategy": {"zh": "保存策略", "en": "Save Strategy"},
    "action.connect_trade": {"zh": "连接交易", "en": "Connect Broker"},
    "action.disconnect_trade": {"zh": "断开连接", "en": "Disconnect"},
    "action.settings": {"zh": "系统设置", "en": "Preferences"},
    "action.help": {"zh": "使用说明", "en": "User Guide"},
    "action.about": {"zh": "关于", "en": "About"},
    "action.ai_log_summary": {"zh": "AI日志摘要", "en": "AI Log Summary"},
    "toolbar.refresh": {"zh": "刷新行情", "en": "Refresh Quotes"},
    "toolbar.backtest": {"zh": "开始回测", "en": "Start Backtest"},
    "toolbar.trade.start": {"zh": "启动交易", "en": "Start Trading"},
    "toolbar.trade.stop": {"zh": "停止交易", "en": "Stop Trading"},
    "left.favorites": {"zh": "自选股", "en": "Watchlist"},
    "button.add_stock": {"zh": "+ 添加股票", "en": "+ Add Stock"},
    "button.clear_logs": {"zh": "清空", "en": "Clear"},
    "log.system": {"zh": "系统日志", "en": "System Logs"},
    "status.market.disconnected": {"zh": "行情: 未连接", "en": "Market: Disconnected"},
    "status.market.connected": {"zh": "行情: 已连接", "en": "Market: Connected"},
    "status.trade.disconnected": {"zh": "交易: 未连接", "en": "Trading: Disconnected"},
    "status.trade.connecting": {"zh": "交易: 连接中...", "en": "Trading: Connecting..."},
    "status.trade.running": {"zh": "交易: 运行中", "en": "Trading: Running"},
    "status.trade.stopped": {"zh": "交易: 已停止", "en": "Trading: Stopped"},
    "log.stock_selected": {"zh": "选中股票: {code}", "en": "Selected stock: {code}"},
    "log.stock_exists": {"zh": "股票 {code} 已在自选列表中", "en": "Stock {code} already exists"},
    "log.stock_added": {"zh": "已添加股票: {code} {name}", "en": "Added stock: {code} {name}"},
    "log.stock_removed": {"zh": "已删除股票: {code}", "en": "Removed stock: {code}"},
    "log.connecting_trade": {"zh": "正在连接交易服务器...", "en": "Connecting to broker..."},
    "log.trade_disconnected": {"zh": "已断开交易连接", "en": "Trading disconnected"},
    "log.refreshing": {"zh": "正在刷新行情数据...", "en": "Refreshing quotes..."},
    "log.trade_start": {"zh": "启动自动交易", "en": "Trading started"},
    "log.trade_stop": {"zh": "停止自动交易", "en": "Trading stopped"},
    "log.import_success": {"zh": "成功导入数据: {path}", "en": "Imported data: {path}"},
    "log.import_fail": {"zh": "导入数据失败: {error}", "en": "Import failed: {error}"},
    "log.export_success": {"zh": "成功导出数据到: {path}", "en": "Exported data to: {path}"},
    "log.export_fail": {"zh": "导出数据失败: {error}", "en": "Export failed: {error}"},
    "log.load_success": {"zh": "成功加载策略: {name}", "en": "Loaded strategy: {name}"},
    "log.load_fail": {"zh": "加载策略失败: {error}", "en": "Load strategy failed: {error}"},
    "log.save_success": {"zh": "成功保存策略: {name}", "en": "Saved strategy: {name}"},
    "log.save_fail": {"zh": "保存策略失败: {error}", "en": "Save strategy failed: {error}"},
    "dialog.add_stock.title": {"zh": "添加股票", "en": "Add Stock"},
    "dialog.add_stock.code": {"zh": "股票代码:", "en": "Code:"},
    "dialog.add_stock.name": {"zh": "股票名称:", "en": "Name:"},
    "dialog.add_stock.placeholder_code": {
        "zh": "输入6位股票代码，如 600000",
        "en": "Enter 6-digit code, e.g. 600000",
    },
    "dialog.add_stock.placeholder_name": {"zh": "股票名称", "en": "Stock name"},
    "dialog.add_stock.hint_auto": {"zh": "已自动识别股票名称", "en": "Name detected automatically"},
    "dialog.add_stock.hint_manual": {"zh": "未找到股票，请手动输入名称", "en": "Not found, please enter manually"},
    "dialog.add_stock.hint_remote_success": {
        "zh": "已通过实时数据源匹配股票名称",
        "en": "Matched from realtime data source",
    },
    "dialog.add_stock.hint_remote_fail": {
        "zh": "实时数据源暂不可用，请手动输入名称",
        "en": "Realtime data source unavailable, please enter manually",
    },
    "dialog.add_stock.hint_local_success": {
        "zh": "已通过内置接口匹配股票名称",
        "en": "Matched via built-in interface",
    },
    "message.help": {
        "zh": "星衡量化平台使用说明\n\n1. 添加自选股\n2. 编写交易策略\n3. 进行历史回测\n4. 连接券商进行实盘交易",
        "en": "Usage Guide\n\n1. Add symbols to the watchlist\n2. Create a strategy\n3. Run backtests\n4. Connect to a broker for live trading",
    },
    "message.about": {
        "zh": "星衡量化平台 v1.0\n\n基于 Python + PyQt5 开发\n现代化界面",
        "en": "AstraQuant Platform v1.0\n\nBuilt with Python + PyQt5\nModern interface",
    },
    "theme.dark": {"zh": "深色", "en": "Dark"},
    "theme.light": {"zh": "浅色", "en": "Light"},
    "lang.zh": {"zh": "中文", "en": "Chinese"},
    "lang.en": {"zh": "英文", "en": "English"},
    "kline.select_stock": {"zh": "选择股票查看行情", "en": "Select a stock to view quotes"},
    "kline.select_prompt": {"zh": "请选择股票查看K线图", "en": "Select a stock to display the chart"},
    "kline.period_label": {"zh": "周期", "en": "Period"},
    "kline.indicator_label": {"zh": "指标", "en": "Indicator"},
}

TRANSLATION_LISTS: Dict[str, Dict[str, List[str]]] = {
    "kline.periods": {
        "zh": ["日K", "周K", "月K", "60分", "30分", "15分", "5分", "1分"],
        "en": ["1D", "1W", "1M", "60m", "30m", "15m", "5m", "1m"],
    }
}


class Translator:
    """简单的翻译器"""

    def __init__(self, language: str = "zh"):
        self.language = language if language in AVAILABLE_LANGUAGES else "zh"

    def set_language(self, language: str):
        if language in AVAILABLE_LANGUAGES:
            self.language = language

    def translate(self, key: str, fallback: str = "") -> str:
        entry = TRANSLATIONS.get(key)
        if entry and self.language in entry:
            return entry[self.language]
        if entry and "zh" in entry:
            return entry["zh"]
        return fallback or key

    def translate_list(self, key: str, fallback: List[str]) -> List[str]:
        entry = TRANSLATION_LISTS.get(key)
        if entry and self.language in entry:
            return entry[self.language]
        if entry and "zh" in entry:
            return entry["zh"]
        return fallback
