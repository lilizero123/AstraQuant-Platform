"""
日志管理模块
提供统一的日志记录功能
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from enum import Enum

try:
    from config.settings import config_manager
except Exception:  # pragma: no cover - fallback when config import fails
    config_manager = None


class LogLevel(Enum):
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogCategory(Enum):
    """日志分类"""
    SYSTEM = "system"       # 系统日志
    TRADE = "trade"         # 交易日志
    STRATEGY = "strategy"   # 策略日志
    DATA = "data"           # 数据日志
    RISK = "risk"           # 风控日志
    UI = "ui"               # 界面日志


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器（用于控制台输出）"""

    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """更健壮的定时滚动文件处理器，避免日志文件被占用时崩溃"""

    def doRollover(self):
        try:
            super().doRollover()
            return
        except PermissionError:
            fallback_name = f"{self.baseFilename}.{datetime.now():%Y%m%d%H%M%S}.fallback"
            try:
                if self.stream:
                    self.stream.close()
                self.stream = self._open(fallback_name)
                return
            except Exception:
                try:
                    self.stream = self._open(self.baseFilename)
                except Exception:
                    pass


class LogManager:
    """日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = None, app_name: str = "星衡量化平台"):
        """
        初始化日志管理器

        Args:
            log_dir: 日志目录，默认为 ./logs
            app_name: 应用名称
        """
        if LogManager._initialized:
            return

        self.app_name = app_name

        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent.parent

        if log_dir is None:
            log_path = base_dir / "logs"
        else:
            log_path = Path(log_dir)
            if not log_path.is_absolute():
                log_path = base_dir / log_path

        self.log_dir = log_path
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 日志记录器字典
        self._loggers = {}

        # UI回调函数列表
        self._ui_callbacks: List[Callable] = []

        # 日志缓存（用于UI显示）
        self._log_cache: List[dict] = []
        self._max_cache_size = 10000

        # 初始化主日志记录器
        self._init_main_logger()

        # 初始化分类日志记录器
        for category in LogCategory:
            self._init_category_logger(category)

        LogManager._initialized = True

    def _init_main_logger(self):
        """初始化主日志记录器"""
        logger = logging.getLogger(self.app_name)
        logger.setLevel(logging.DEBUG)

        # 清除已有的处理器
        logger.handlers.clear()

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # 文件处理器（按大小轮转）
        file_handler = RotatingFileHandler(
            self.log_dir / f"{self.app_name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

        self._loggers['main'] = logger

    def _init_category_logger(self, category: LogCategory):
        """初始化分类日志记录器"""
        logger_name = f"{self.app_name}.{category.value}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        # 清除已有的处理器
        logger.handlers.clear()

        # 按日期轮转的文件处理器
        file_handler = SafeTimedRotatingFileHandler(
            self.log_dir / f"{category.value}.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

        self._loggers[category.value] = logger

    def get_logger(self, category: LogCategory = None) -> logging.Logger:
        """获取日志记录器"""
        if category is None:
            return self._loggers['main']
        return self._loggers.get(category.value, self._loggers['main'])

    def add_ui_callback(self, callback: Callable):
        """添加UI回调函数"""
        if callback not in self._ui_callbacks:
            self._ui_callbacks.append(callback)

    def remove_ui_callback(self, callback: Callable):
        """移除UI回调函数"""
        if callback in self._ui_callbacks:
            self._ui_callbacks.remove(callback)

    def _notify_ui(self, log_entry: dict):
        """通知UI更新"""
        for callback in self._ui_callbacks:
            try:
                callback(log_entry)
            except Exception:
                pass

    def _add_to_cache(self, log_entry: dict):
        """添加到缓存"""
        self._log_cache.append(log_entry)
        if len(self._log_cache) > self._max_cache_size:
            self._log_cache = self._log_cache[-self._max_cache_size // 2:]

    def _log(self, level: LogLevel, message: str, category: LogCategory = None,
             extra: dict = None):
        """内部日志记录方法"""
        logger = self.get_logger(category)

        # 创建日志条目
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': level.name,
            'category': category.value if category else 'main',
            'message': message,
            'extra': extra or {}
        }

        # 记录到日志文件
        logger.log(level.value, message)

        # 添加到缓存
        self._add_to_cache(log_entry)

        # 通知UI
        self._notify_ui(log_entry)

    def debug(self, message: str, category: LogCategory = None, **kwargs):
        """调试日志"""
        self._log(LogLevel.DEBUG, message, category, kwargs)

    def info(self, message: str, category: LogCategory = None, **kwargs):
        """信息日志"""
        self._log(LogLevel.INFO, message, category, kwargs)

    def warning(self, message: str, category: LogCategory = None, **kwargs):
        """警告日志"""
        self._log(LogLevel.WARNING, message, category, kwargs)

    def error(self, message: str, category: LogCategory = None, **kwargs):
        """错误日志"""
        self._log(LogLevel.ERROR, message, category, kwargs)

    def critical(self, message: str, category: LogCategory = None, **kwargs):
        """严重错误日志"""
        self._log(LogLevel.CRITICAL, message, category, kwargs)

    # ==================== 便捷方法 ====================

    def trade(self, message: str, **kwargs):
        """交易日志"""
        self._log(LogLevel.INFO, message, LogCategory.TRADE, kwargs)

    def strategy(self, message: str, **kwargs):
        """策略日志"""
        self._log(LogLevel.INFO, message, LogCategory.STRATEGY, kwargs)

    def data(self, message: str, **kwargs):
        """数据日志"""
        self._log(LogLevel.INFO, message, LogCategory.DATA, kwargs)

    def risk(self, message: str, level: LogLevel = LogLevel.WARNING, **kwargs):
        """风控日志"""
        self._log(level, message, LogCategory.RISK, kwargs)

    def system(self, message: str, **kwargs):
        """系统日志"""
        self._log(LogLevel.INFO, message, LogCategory.SYSTEM, kwargs)

    # ==================== 日志查询 ====================

    def get_logs(self, category: LogCategory = None, level: LogLevel = None,
                 start_time: str = None, end_time: str = None,
                 keyword: str = None, limit: int = 100) -> List[dict]:
        """
        查询日志

        Args:
            category: 日志分类
            level: 日志级别
            start_time: 开始时间
            end_time: 结束时间
            keyword: 关键词
            limit: 返回数量限制

        Returns:
            日志条目列表
        """
        results = []

        for entry in reversed(self._log_cache):
            # 分类过滤
            if category and entry['category'] != category.value:
                continue

            # 级别过滤
            if level and entry['level'] != level.name:
                continue

            # 时间过滤
            if start_time and entry['timestamp'] < start_time:
                continue
            if end_time and entry['timestamp'] > end_time:
                continue

            # 关键词过滤
            if keyword and keyword.lower() not in entry['message'].lower():
                continue

            results.append(entry)

            if len(results) >= limit:
                break

        return results

    def get_recent_logs(self, count: int = 100) -> List[dict]:
        """获取最近的日志"""
        return list(reversed(self._log_cache[-count:]))

    def clear_cache(self):
        """清除日志缓存"""
        self._log_cache.clear()

    def export_logs(self, file_path: str, category: LogCategory = None,
                    start_time: str = None, end_time: str = None) -> bool:
        """
        导出日志到文件

        Args:
            file_path: 导出文件路径
            category: 日志分类
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            是否成功
        """
        try:
            logs = self.get_logs(
                category=category,
                start_time=start_time,
                end_time=end_time,
                limit=100000
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                for entry in logs:
                    line = f"[{entry['timestamp']}] [{entry['level']}] [{entry['category']}] {entry['message']}\n"
                    f.write(line)

            return True
        except Exception:
            return False


# 全局日志管理器实例
_log_manager: Optional[LogManager] = None


def get_logger(category: LogCategory = None) -> logging.Logger:
    """获取日志记录器"""
    return get_log_manager().get_logger(category)


def get_log_manager() -> LogManager:
    """获取日志管理器实例"""
    global _log_manager
    if _log_manager is None:
        log_dir = None
        if config_manager is not None:
            try:
                log_dir = config_manager.get("log_path", None)
            except Exception:  # pragma: no cover - defensive
                log_dir = None
        _log_manager = LogManager(log_dir=log_dir)
    return _log_manager


# 便捷函数
def log_debug(message: str, category: LogCategory = None, **kwargs):
    get_log_manager().debug(message, category, **kwargs)


def log_info(message: str, category: LogCategory = None, **kwargs):
    get_log_manager().info(message, category, **kwargs)


def log_warning(message: str, category: LogCategory = None, **kwargs):
    get_log_manager().warning(message, category, **kwargs)


def log_error(message: str, category: LogCategory = None, **kwargs):
    get_log_manager().error(message, category, **kwargs)


def log_critical(message: str, category: LogCategory = None, **kwargs):
    get_log_manager().critical(message, category, **kwargs)


def log_trade(message: str, **kwargs):
    get_log_manager().trade(message, **kwargs)


def log_strategy(message: str, **kwargs):
    get_log_manager().strategy(message, **kwargs)


def log_risk(message: str, level: LogLevel = LogLevel.WARNING, **kwargs):
    get_log_manager().risk(message, level, **kwargs)
