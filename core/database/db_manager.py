"""
数据库管理模块
使用 SQLite 进行数据持久化
"""
import sqlite3
import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from contextlib import contextmanager

from config.settings import config_manager


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def _resolve_path(value: Optional[str], default_subdir: str) -> Path:
    base_dir = _runtime_base_dir()
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = base_dir / path
    else:
        path = base_dir / default_subdir
    return path


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为 ./data/trading.db
        """
        if db_path is None:
            data_root = None
            try:
                data_root = config_manager.get("data_path", None)
            except Exception:
                data_root = None
            resolved = _resolve_path(data_root, "data") / "trading.db"
        else:
            resolved = Path(db_path)
            if not resolved.is_absolute():
                resolved = _runtime_base_dir() / resolved

        self.db_path = resolved
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 策略表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    code TEXT NOT NULL,
                    parameters TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 回测结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    initial_capital REAL NOT NULL,
                    final_capital REAL NOT NULL,
                    total_return REAL,
                    annual_return REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    win_rate REAL,
                    profit_loss_ratio REAL,
                    total_trades INTEGER,
                    parameters TEXT,
                    equity_curve TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 交易记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL UNIQUE,
                    order_id TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    commission REAL DEFAULT 0,
                    profit REAL DEFAULT 0,
                    strategy_name TEXT,
                    trade_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 持仓记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    quantity INTEGER NOT NULL,
                    avg_cost REAL NOT NULL,
                    current_price REAL DEFAULT 0,
                    market_value REAL DEFAULT 0,
                    profit REAL DEFAULT 0,
                    profit_pct REAL DEFAULT 0,
                    strategy_name TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, strategy_name)
                )
            ''')

            # 订单记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL UNIQUE,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    filled_quantity INTEGER DEFAULT 0,
                    filled_price REAL DEFAULT 0,
                    status TEXT NOT NULL,
                    strategy_name TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP
                )
            ''')

            # K线数据缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kline_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    period TEXT NOT NULL,
                    datetime TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    amount REAL DEFAULT 0,
                    UNIQUE(stock_code, period, datetime)
                )
            ''')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_time ON trade_records(trade_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_code ON trade_records(stock_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_kline ON kline_data(stock_code, period, datetime)')

    # ==================== 策略管理 ====================

    def save_strategy(self, name: str, code: str, parameters: Dict = None, description: str = "") -> int:
        """
        保存策略

        Args:
            name: 策略名称
            code: 策略代码
            parameters: 策略参数
            description: 策略描述

        Returns:
            策略ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            params_json = json.dumps(parameters) if parameters else None

            cursor.execute('''
                INSERT INTO strategies (name, code, parameters, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    code = excluded.code,
                    parameters = excluded.parameters,
                    description = excluded.description,
                    updated_at = excluded.updated_at
            ''', (name, code, params_json, description, datetime.now()))

            return cursor.lastrowid

    def get_strategy(self, name: str) -> Optional[Dict]:
        """获取策略"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM strategies WHERE name = ?', (name,))
            row = cursor.fetchone()

            if row:
                result = dict(row)
                if result.get('parameters'):
                    result['parameters'] = json.loads(result['parameters'])
                return result
            return None

    def get_all_strategies(self) -> List[Dict]:
        """获取所有策略"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM strategies ORDER BY updated_at DESC')
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                if result.get('parameters'):
                    result['parameters'] = json.loads(result['parameters'])
                results.append(result)
            return results

    def delete_strategy(self, name: str) -> bool:
        """删除策略"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM strategies WHERE name = ?', (name,))
            return cursor.rowcount > 0

    # ==================== 回测结果管理 ====================

    def save_backtest_result(self, result: Dict) -> int:
        """
        保存回测结果

        Args:
            result: 回测结果字典，包含以下字段:
                - strategy_name: 策略名称
                - stock_code: 股票代码
                - start_date: 开始日期
                - end_date: 结束日期
                - initial_capital: 初始资金
                - final_capital: 最终资金
                - total_return: 总收益率
                - annual_return: 年化收益率
                - max_drawdown: 最大回撤
                - sharpe_ratio: 夏普比率
                - win_rate: 胜率
                - profit_loss_ratio: 盈亏比
                - total_trades: 总交易次数
                - parameters: 策略参数
                - equity_curve: 资金曲线
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            params_json = json.dumps(result.get('parameters')) if result.get('parameters') else None
            equity_json = json.dumps(result.get('equity_curve')) if result.get('equity_curve') else None

            cursor.execute('''
                INSERT INTO backtest_results (
                    strategy_name, stock_code, start_date, end_date,
                    initial_capital, final_capital, total_return, annual_return,
                    max_drawdown, sharpe_ratio, win_rate, profit_loss_ratio,
                    total_trades, parameters, equity_curve
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.get('strategy_name'),
                result.get('stock_code'),
                result.get('start_date'),
                result.get('end_date'),
                result.get('initial_capital'),
                result.get('final_capital'),
                result.get('total_return'),
                result.get('annual_return'),
                result.get('max_drawdown'),
                result.get('sharpe_ratio'),
                result.get('win_rate'),
                result.get('profit_loss_ratio'),
                result.get('total_trades'),
                params_json,
                equity_json
            ))

            return cursor.lastrowid

    def get_backtest_results(self, strategy_name: str = None, limit: int = 100) -> List[Dict]:
        """获取回测结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if strategy_name:
                cursor.execute('''
                    SELECT * FROM backtest_results
                    WHERE strategy_name = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (strategy_name, limit))
            else:
                cursor.execute('''
                    SELECT * FROM backtest_results
                    ORDER BY created_at DESC LIMIT ?
                ''', (limit,))

            rows = cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                if result.get('parameters'):
                    result['parameters'] = json.loads(result['parameters'])
                if result.get('equity_curve'):
                    result['equity_curve'] = json.loads(result['equity_curve'])
                results.append(result)
            return results

    # ==================== 交易记录管理 ====================

    def save_trade(self, trade: Dict) -> int:
        """保存交易记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO trade_records (
                    trade_id, order_id, stock_code, stock_name, side,
                    price, quantity, amount, commission, profit,
                    strategy_name, trade_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.get('trade_id'),
                trade.get('order_id'),
                trade.get('stock_code'),
                trade.get('stock_name'),
                trade.get('side'),
                trade.get('price'),
                trade.get('quantity'),
                trade.get('amount', trade.get('price', 0) * trade.get('quantity', 0)),
                trade.get('commission', 0),
                trade.get('profit', 0),
                trade.get('strategy_name'),
                trade.get('trade_time')
            ))

            return cursor.lastrowid

    def get_trades(self, stock_code: str = None, start_date: str = None,
                   end_date: str = None, limit: int = 1000) -> List[Dict]:
        """获取交易记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM trade_records WHERE 1=1'
            params = []

            if stock_code:
                query += ' AND stock_code = ?'
                params.append(stock_code)
            if start_date:
                query += ' AND trade_time >= ?'
                params.append(start_date)
            if end_date:
                query += ' AND trade_time <= ?'
                params.append(end_date)

            query += ' ORDER BY trade_time DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # ==================== 持仓管理 ====================

    def save_position(self, position: Dict) -> int:
        """保存或更新持仓"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO positions (
                    stock_code, stock_name, quantity, avg_cost,
                    current_price, market_value, profit, profit_pct,
                    strategy_name, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_code, strategy_name) DO UPDATE SET
                    quantity = excluded.quantity,
                    avg_cost = excluded.avg_cost,
                    current_price = excluded.current_price,
                    market_value = excluded.market_value,
                    profit = excluded.profit,
                    profit_pct = excluded.profit_pct,
                    updated_at = excluded.updated_at
            ''', (
                position.get('stock_code'),
                position.get('stock_name'),
                position.get('quantity'),
                position.get('avg_cost'),
                position.get('current_price', 0),
                position.get('market_value', 0),
                position.get('profit', 0),
                position.get('profit_pct', 0),
                position.get('strategy_name'),
                datetime.now()
            ))

            return cursor.lastrowid

    def get_positions(self, strategy_name: str = None) -> List[Dict]:
        """获取持仓"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if strategy_name:
                cursor.execute('''
                    SELECT * FROM positions
                    WHERE strategy_name = ? AND quantity > 0
                    ORDER BY updated_at DESC
                ''', (strategy_name,))
            else:
                cursor.execute('''
                    SELECT * FROM positions
                    WHERE quantity > 0
                    ORDER BY updated_at DESC
                ''')

            return [dict(row) for row in cursor.fetchall()]

    def delete_position(self, stock_code: str, strategy_name: str = None) -> bool:
        """删除持仓"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if strategy_name:
                cursor.execute('''
                    DELETE FROM positions
                    WHERE stock_code = ? AND strategy_name = ?
                ''', (stock_code, strategy_name))
            else:
                cursor.execute('DELETE FROM positions WHERE stock_code = ?', (stock_code,))

            return cursor.rowcount > 0

    # ==================== 订单管理 ====================

    def save_order(self, order: Dict) -> int:
        """保存订单"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO orders (
                    order_id, stock_code, stock_name, side, order_type,
                    price, quantity, filled_quantity, filled_price,
                    status, strategy_name, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.get('order_id'),
                order.get('stock_code'),
                order.get('stock_name'),
                order.get('side'),
                order.get('order_type'),
                order.get('price'),
                order.get('quantity'),
                order.get('filled_quantity', 0),
                order.get('filled_price', 0),
                order.get('status'),
                order.get('strategy_name'),
                order.get('created_at'),
                order.get('updated_at')
            ))

            return cursor.lastrowid

    def get_orders(self, status: str = None, limit: int = 100) -> List[Dict]:
        """获取订单"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute('''
                    SELECT * FROM orders
                    WHERE status = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT * FROM orders
                    ORDER BY created_at DESC LIMIT ?
                ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

    # ==================== K线数据缓存 ====================

    def save_kline_data(self, stock_code: str, period: str, data: List[Dict]) -> int:
        """
        保存K线数据

        Args:
            stock_code: 股票代码
            period: 周期 (daily, weekly, monthly, 1min, 5min, etc.)
            data: K线数据列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            count = 0
            for bar in data:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO kline_data (
                            stock_code, period, datetime, open, high, low, close, volume, amount
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stock_code,
                        period,
                        bar.get('datetime'),
                        bar.get('open'),
                        bar.get('high'),
                        bar.get('low'),
                        bar.get('close'),
                        bar.get('volume'),
                        bar.get('amount', 0)
                    ))
                    count += 1
                except Exception:
                    continue

            return count

    def get_kline_data(self, stock_code: str, period: str,
                       start_date: str = None, end_date: str = None) -> List[Dict]:
        """获取K线数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM kline_data WHERE stock_code = ? AND period = ?'
            params = [stock_code, period]

            if start_date:
                query += ' AND datetime >= ?'
                params.append(start_date)
            if end_date:
                query += ' AND datetime <= ?'
                params.append(end_date)

            query += ' ORDER BY datetime ASC'

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def clear_kline_data(self, stock_code: str = None, period: str = None) -> int:
        """清除K线数据缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if stock_code and period:
                cursor.execute('''
                    DELETE FROM kline_data
                    WHERE stock_code = ? AND period = ?
                ''', (stock_code, period))
            elif stock_code:
                cursor.execute('DELETE FROM kline_data WHERE stock_code = ?', (stock_code,))
            else:
                cursor.execute('DELETE FROM kline_data')

            return cursor.rowcount

    # ==================== 数据导出 ====================

    def export_to_csv(self, table_name: str, file_path: str) -> bool:
        """导出表数据到CSV"""
        import csv

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM {table_name}')
            rows = cursor.fetchall()

            if not rows:
                return False

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(rows[0].keys())
                for row in rows:
                    writer.writerow(row)

            return True

    def export_to_json(self, table_name: str, file_path: str) -> bool:
        """导出表数据到JSON"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM {table_name}')
            rows = cursor.fetchall()

            if not rows:
                return False

            data = [dict(row) for row in rows]

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            return True

    # ==================== 统计查询 ====================

    def get_trade_statistics(self, start_date: str = None, end_date: str = None) -> Dict:
        """获取交易统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = '''
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN side = 'buy' THEN 1 ELSE 0 END) as buy_count,
                    SUM(CASE WHEN side = 'sell' THEN 1 ELSE 0 END) as sell_count,
                    SUM(amount) as total_amount,
                    SUM(commission) as total_commission,
                    SUM(profit) as total_profit,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as win_count,
                    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as loss_count
                FROM trade_records WHERE 1=1
            '''
            params = []

            if start_date:
                query += ' AND trade_time >= ?'
                params.append(start_date)
            if end_date:
                query += ' AND trade_time <= ?'
                params.append(end_date)

            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                result = dict(row)
                sell_count = result.get('sell_count', 0) or 0
                win_count = result.get('win_count', 0) or 0
                if sell_count > 0:
                    result['win_rate'] = win_count / sell_count * 100
                else:
                    result['win_rate'] = 0
                return result

            return {}
