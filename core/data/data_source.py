"""
数据获取模块，封装 AkShare 与 Tushare 数据源
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import subprocess
import sys
from typing import List

import pandas as pd

from core.logger.logger import (
    log_error,
    log_info,
    log_warning,
    LogCategory,
)


class DataSource(ABC):
    """数据源基类"""

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""

    @abstractmethod
    def get_daily_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日 K 线"""

    @abstractmethod
    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""


class AkShareDataSource(DataSource):
    """AkShare 数据源"""

    def __init__(self):
        self.ak = None
        self.log_category = LogCategory.DATA
        self._init_akshare()

    def _init_akshare(self):
        """初始化 akshare"""
        log_info("正在初始化 AkShare 数据源", self.log_category)
        try:
            import akshare as ak

            self.ak = ak
            log_info("AkShare 导入成功", self.log_category)
            return
        except ImportError:
            log_warning("检测到未安装 AkShare，尝试自动安装", self.log_category)
            print("检测到未安装 akshare，尝试自动安装...")
            if self._install_akshare():
                try:
                    import akshare as ak

                    self.ak = ak
                    log_info("自动安装 AkShare 成功", self.log_category)
                    return
                except Exception as err:
                    log_error(f"自动安装 AkShare 后导入失败: {err}", self.log_category)
                    print(f"自动安装后导入 akshare 仍失败: {err}")
        except Exception as err:
            log_error(f"AkShare 初始化失败: {err}", self.log_category)
            print(f"AkShare 初始化失败: {err}")

        self.ak = None
        log_error("AkShare 初始化失败，行情/回测功能不可用", self.log_category)

    def _install_akshare(self) -> bool:
        """在未打包环境中尝试自动安装 AkShare"""
        if getattr(sys, "frozen", False):
            log_warning("当前为打包环境，无法自动安装 AkShare，请重新打包时包含依赖", self.log_category)
            return False

        log_info("开始自动安装 AkShare...", self.log_category)
        try:
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "akshare",
                    "-i",
                    "https://pypi.tuna.tsinghua.edu.cn/simple",
                ]
            )
            log_info("自动安装 AkShare 完成", self.log_category)
            return True
        except Exception as err:
            log_error(f"自动安装 AkShare 失败: {err}", self.log_category)
            print(f"自动安装 akshare 失败: {err}")
            return False

    def get_stock_list(self) -> pd.DataFrame:
        """获取 A 股股票列表"""
        if self.ak is None:
            log_error("AkShare 未就绪，无法获取股票列表", self.log_category)
            return pd.DataFrame()
        try:
            df = self.ak.stock_zh_a_spot_em()
            return df[["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额"]]
        except Exception as err:
            log_error(f"获取股票列表失败: {err}", self.log_category)
            print(f"获取股票列表失败: {err}")
            return pd.DataFrame()

    def get_daily_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日 K 线数据"""
        if self.ak is None:
            log_error(f"AkShare 未就绪，无法获取 {code} K 线数据", self.log_category)
            return pd.DataFrame()

        try:
            df = self.ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq",
            )

            if df.empty:
                log_warning(f"AkShare 返回空的 K 线数据: {code} [{start_date} - {end_date}]", self.log_category)
                return pd.DataFrame()

            df = df.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                    "涨跌幅": "pct_change",
                }
            )

            df["date"] = pd.to_datetime(df["date"])
            log_info(f"成功获取 {code} [{start_date} - {end_date}] 共 {len(df)} 条 K 线数据", self.log_category)
            return df
        except Exception as err:
            log_error(f"获取 {code} K 线数据失败: {err}", self.log_category)
            print(f"获取K线数据失败: {err}")
            return pd.DataFrame()

    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        if self.ak is None:
            log_error("AkShare 未就绪，无法获取实时行情", self.log_category)
            return pd.DataFrame()
        try:
            df = self.ak.stock_zh_a_spot_em()
            df = df[df["代码"].isin(codes)]
            return df
        except Exception as err:
            log_error(f"获取实时行情失败: {err}", self.log_category)
            print(f"获取实时行情失败: {err}")
            return pd.DataFrame()

    def get_minute_data(self, code: str, period: str = "5") -> pd.DataFrame:
        """获取分钟级别行情"""
        if self.ak is None:
            log_error(f"AkShare 未就绪，无法获取 {code} 分钟数据", self.log_category)
            return pd.DataFrame()
        try:
            df = self.ak.stock_zh_a_hist_min_em(symbol=code, period=period, adjust="qfq")
            return df
        except Exception as err:
            log_error(f"获取 {code} 分钟数据失败: {err}", self.log_category)
            print(f"获取分钟数据失败: {err}")
            return pd.DataFrame()


class TushareDataSource(DataSource):
    """Tushare 数据源"""

    def __init__(self, token: str = ""):
        self.token = token
        self.pro = None
        self._init_tushare()

    def _init_tushare(self):
        """初始化 tushare"""
        if not self.token:
            return
        try:
            import tushare as ts

            ts.set_token(self.token)
            self.pro = ts.pro_api()
        except ImportError:
            print("检测到未安装 tushare，尝试自动安装...")
            if self._install_tushare():
                try:
                    import tushare as ts
                    ts.set_token(self.token)
                    self.pro = ts.pro_api()
                    print("自动安装 tushare 成功")
                except Exception as err:
                    print(f"自动安装 tushare 后仍无法导入: {err}")
        except Exception as err:
            print(f"初始化 tushare 失败: {err}")

    def _install_tushare(self) -> bool:
        """在未打包环境中自动安装 tushare"""
        if getattr(sys, "frozen", False):
            print("当前为打包环境，无法自动安装 tushare，请在构建时包含该依赖")
            return False
        try:
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "tushare",
                    "-i",
                    "https://pypi.tuna.tsinghua.edu.cn/simple",
                ]
            )
            return True
        except Exception as err:
            print(f"自动安装 tushare 失败: {err}")
            return False

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        if self.pro is None:
            return pd.DataFrame()
        try:
            df = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,list_date",
            )
            return df
        except Exception as err:
            print(f"获取股票列表失败: {err}")
            return pd.DataFrame()

    def get_daily_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日 K 线数据"""
        if self.pro is None:
            return pd.DataFrame()
        try:
            ts_code = f"{code}.SH" if code.startswith("6") else f"{code}.SZ"

            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
            )

            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={"trade_date": "date", "vol": "volume"})
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            return df
        except Exception as err:
            print(f"获取K线数据失败: {err}")
            return pd.DataFrame()

    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情 - Tushare 不支持实时行情"""
        return pd.DataFrame()


class DataManager:
    """数据管理器"""

    def __init__(self, source: str = "akshare", token: str = ""):
        """
        Args:
            source: 数据源类型 ("akshare" or "tushare")
            token: Tushare token
        """
        if source == "akshare":
            self.data_source: DataSource = AkShareDataSource()
        elif source == "tushare":
            self.data_source = TushareDataSource(token)
        else:
            raise ValueError(f"不支持的数据源: {source}")

        self.cache = {}

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        return self.data_source.get_stock_list()

    def get_daily_data(self, code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取日 K 线数据"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        cache_key = f"{code}_{start_date}_{end_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        df = self.data_source.get_daily_data(code, start_date, end_date)
        if not df.empty:
            self.cache[cache_key] = df
        return df

    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        return self.data_source.get_realtime_quote(codes)

    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()
