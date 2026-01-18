"""
数据导入导出模块
支持 CSV、Excel、JSON 格式的数据导入导出
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import pandas as pd

from core.logger import get_log_manager, LogCategory


class DataExporter:
    """数据导出器"""

    def __init__(self):
        self.logger = get_log_manager()

    def export_to_csv(self, data: Union[List[Dict], pd.DataFrame],
                      file_path: str, encoding: str = 'utf-8-sig') -> bool:
        """
        导出数据到CSV文件

        Args:
            data: 数据（字典列表或DataFrame）
            file_path: 文件路径
            encoding: 编码格式

        Returns:
            是否成功
        """
        try:
            if isinstance(data, pd.DataFrame):
                data.to_csv(file_path, index=False, encoding=encoding)
            else:
                if not data:
                    return False

                with open(file_path, 'w', newline='', encoding=encoding) as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)

            self.logger.info(f"数据导出成功: {file_path}", LogCategory.DATA)
            return True

        except Exception as e:
            self.logger.error(f"CSV导出失败: {str(e)}", LogCategory.DATA)
            return False

    def export_to_excel(self, data: Union[List[Dict], pd.DataFrame, Dict[str, Any]],
                        file_path: str, sheet_name: str = 'Sheet1') -> bool:
        """
        导出数据到Excel文件

        Args:
            data: 数据（字典列表、DataFrame或多个sheet的字典）
            file_path: 文件路径
            sheet_name: 工作表名称

        Returns:
            是否成功
        """
        try:
            if isinstance(data, dict) and all(isinstance(v, (list, pd.DataFrame)) for v in data.values()):
                # 多个sheet
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    for name, sheet_data in data.items():
                        if isinstance(sheet_data, list):
                            df = pd.DataFrame(sheet_data)
                        else:
                            df = sheet_data
                        df.to_excel(writer, sheet_name=name, index=False)
            else:
                # 单个sheet
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = data
                df.to_excel(file_path, sheet_name=sheet_name, index=False, engine='openpyxl')

            self.logger.info(f"Excel导出成功: {file_path}", LogCategory.DATA)
            return True

        except Exception as e:
            self.logger.error(f"Excel导出失败: {str(e)}", LogCategory.DATA)
            return False

    def export_to_json(self, data: Union[List[Dict], Dict, pd.DataFrame],
                       file_path: str, indent: int = 2) -> bool:
        """
        导出数据到JSON文件

        Args:
            data: 数据
            file_path: 文件路径
            indent: 缩进

        Returns:
            是否成功
        """
        try:
            if isinstance(data, pd.DataFrame):
                data = data.to_dict(orient='records')

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent, default=str)

            self.logger.info(f"JSON导出成功: {file_path}", LogCategory.DATA)
            return True

        except Exception as e:
            self.logger.error(f"JSON导出失败: {str(e)}", LogCategory.DATA)
            return False

    def export_kline_data(self, data: Union[List[Dict], pd.DataFrame],
                          file_path: str, format: str = 'csv') -> bool:
        """
        导出K线数据

        Args:
            data: K线数据
            file_path: 文件路径
            format: 格式 (csv, excel, json)

        Returns:
            是否成功
        """
        if format == 'csv':
            return self.export_to_csv(data, file_path)
        elif format == 'excel':
            return self.export_to_excel(data, file_path)
        elif format == 'json':
            return self.export_to_json(data, file_path)
        else:
            self.logger.error(f"不支持的格式: {format}", LogCategory.DATA)
            return False

    def export_trade_records(self, trades: List[Dict], file_path: str,
                             format: str = 'excel') -> bool:
        """
        导出交易记录

        Args:
            trades: 交易记录
            file_path: 文件路径
            format: 格式

        Returns:
            是否成功
        """
        # 格式化交易记录
        formatted_trades = []
        for trade in trades:
            formatted_trades.append({
                '交易ID': trade.get('trade_id', ''),
                '股票代码': trade.get('stock_code', ''),
                '股票名称': trade.get('stock_name', ''),
                '交易方向': '买入' if trade.get('side') == 'buy' else '卖出',
                '成交价格': trade.get('price', 0),
                '成交数量': trade.get('quantity', 0),
                '成交金额': trade.get('amount', 0),
                '手续费': trade.get('commission', 0),
                '盈亏': trade.get('profit', 0),
                '交易时间': trade.get('trade_time', '')
            })

        if format == 'csv':
            return self.export_to_csv(formatted_trades, file_path)
        elif format == 'excel':
            return self.export_to_excel(formatted_trades, file_path)
        elif format == 'json':
            return self.export_to_json(formatted_trades, file_path)
        else:
            return False

    def export_backtest_report(self, result: Dict, file_path: str) -> bool:
        """
        导出回测报告

        Args:
            result: 回测结果
            file_path: 文件路径

        Returns:
            是否成功
        """
        try:
            # 准备多个sheet的数据
            sheets = {}

            # 概览
            overview = [{
                '指标': '策略名称', '值': result.get('strategy_name', '')
            }, {
                '指标': '股票代码', '值': result.get('stock_code', '')
            }, {
                '指标': '回测区间', '值': f"{result.get('start_date', '')} ~ {result.get('end_date', '')}"
            }, {
                '指标': '初始资金', '值': result.get('initial_capital', 0)
            }, {
                '指标': '最终资金', '值': result.get('final_capital', 0)
            }, {
                '指标': '总收益率', '值': f"{result.get('total_return', 0):.2f}%"
            }, {
                '指标': '年化收益率', '值': f"{result.get('annual_return', 0):.2f}%"
            }, {
                '指标': '最大回撤', '值': f"{result.get('max_drawdown', 0):.2f}%"
            }, {
                '指标': '夏普比率', '值': f"{result.get('sharpe_ratio', 0):.2f}"
            }, {
                '指标': '胜率', '值': f"{result.get('win_rate', 0):.2f}%"
            }, {
                '指标': '盈亏比', '值': f"{result.get('profit_loss_ratio', 0):.2f}"
            }, {
                '指标': '总交易次数', '值': result.get('total_trades', 0)
            }]
            sheets['概览'] = overview

            # 资金曲线
            if result.get('equity_curve'):
                sheets['资金曲线'] = result['equity_curve']

            # 交易记录
            if result.get('trades'):
                sheets['交易记录'] = result['trades']

            return self.export_to_excel(sheets, file_path)

        except Exception as e:
            self.logger.error(f"回测报告导出失败: {str(e)}", LogCategory.DATA)
            return False


class DataImporter:
    """数据导入器"""

    def __init__(self):
        self.logger = get_log_manager()

    def import_from_csv(self, file_path: str, encoding: str = 'utf-8') -> Optional[pd.DataFrame]:
        """
        从CSV文件导入数据

        Args:
            file_path: 文件路径
            encoding: 编码格式

        Returns:
            DataFrame或None
        """
        try:
            # 尝试多种编码
            encodings = [encoding, 'utf-8-sig', 'gbk', 'gb2312']
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    self.logger.info(f"CSV导入成功: {file_path}", LogCategory.DATA)
                    return df
                except UnicodeDecodeError:
                    continue

            self.logger.error(f"CSV导入失败: 无法识别编码", LogCategory.DATA)
            return None

        except Exception as e:
            self.logger.error(f"CSV导入失败: {str(e)}", LogCategory.DATA)
            return None

    def import_from_excel(self, file_path: str, sheet_name: Union[str, int] = 0) -> Optional[pd.DataFrame]:
        """
        从Excel文件导入数据

        Args:
            file_path: 文件路径
            sheet_name: 工作表名称或索引

        Returns:
            DataFrame或None
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
            self.logger.info(f"Excel导入成功: {file_path}", LogCategory.DATA)
            return df

        except Exception as e:
            self.logger.error(f"Excel导入失败: {str(e)}", LogCategory.DATA)
            return None

    def import_from_json(self, file_path: str) -> Optional[Union[List, Dict]]:
        """
        从JSON文件导入数据

        Args:
            file_path: 文件路径

        Returns:
            数据或None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.logger.info(f"JSON导入成功: {file_path}", LogCategory.DATA)
            return data

        except Exception as e:
            self.logger.error(f"JSON导入失败: {str(e)}", LogCategory.DATA)
            return None

    def import_kline_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        导入K线数据

        Args:
            file_path: 文件路径

        Returns:
            DataFrame或None
        """
        ext = Path(file_path).suffix.lower()

        if ext == '.csv':
            df = self.import_from_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            df = self.import_from_excel(file_path)
        elif ext == '.json':
            data = self.import_from_json(file_path)
            df = pd.DataFrame(data) if data else None
        else:
            self.logger.error(f"不支持的文件格式: {ext}", LogCategory.DATA)
            return None

        if df is not None:
            # 标准化列名
            df = self._standardize_kline_columns(df)

        return df

    def _standardize_kline_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化K线数据列名"""
        column_mapping = {
            # 日期时间
            '日期': 'datetime', 'date': 'datetime', 'time': 'datetime',
            '时间': 'datetime', 'trade_date': 'datetime',
            # 开盘价
            '开盘': 'open', '开盘价': 'open',
            # 最高价
            '最高': 'high', '最高价': 'high',
            # 最低价
            '最低': 'low', '最低价': 'low',
            # 收盘价
            '收盘': 'close', '收盘价': 'close',
            # 成交量
            '成交量': 'volume', 'vol': 'volume',
            # 成交额
            '成交额': 'amount', 'turnover': 'amount'
        }

        # 转换列名为小写
        df.columns = df.columns.str.lower()

        # 应用映射
        df = df.rename(columns=column_mapping)

        return df

    def import_stock_list(self, file_path: str) -> Optional[List[Dict]]:
        """
        导入股票列表

        Args:
            file_path: 文件路径

        Returns:
            股票列表或None
        """
        ext = Path(file_path).suffix.lower()

        if ext == '.csv':
            df = self.import_from_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            df = self.import_from_excel(file_path)
        elif ext == '.json':
            return self.import_from_json(file_path)
        else:
            return None

        if df is not None:
            return df.to_dict(orient='records')
        return None


class DataManager:
    """数据管理器（整合导入导出功能）"""

    def __init__(self):
        self.exporter = DataExporter()
        self.importer = DataImporter()
        self.logger = get_log_manager()

    def export(self, data: Any, file_path: str, format: str = None) -> bool:
        """
        导出数据

        Args:
            data: 数据
            file_path: 文件路径
            format: 格式（如果不指定则根据扩展名判断）

        Returns:
            是否成功
        """
        if format is None:
            format = Path(file_path).suffix.lower().lstrip('.')

        if format == 'csv':
            return self.exporter.export_to_csv(data, file_path)
        elif format in ['xlsx', 'xls', 'excel']:
            return self.exporter.export_to_excel(data, file_path)
        elif format == 'json':
            return self.exporter.export_to_json(data, file_path)
        else:
            self.logger.error(f"不支持的导出格式: {format}", LogCategory.DATA)
            return False

    def import_data(self, file_path: str) -> Optional[Union[pd.DataFrame, List, Dict]]:
        """
        导入数据

        Args:
            file_path: 文件路径

        Returns:
            数据或None
        """
        ext = Path(file_path).suffix.lower()

        if ext == '.csv':
            return self.importer.import_from_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            return self.importer.import_from_excel(file_path)
        elif ext == '.json':
            return self.importer.import_from_json(file_path)
        else:
            self.logger.error(f"不支持的导入格式: {ext}", LogCategory.DATA)
            return None
