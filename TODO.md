# 星衡量化平台 - 待完善功能清单

## 概述
本文档记录星衡量化平台需要完善的功能模块，按优先级排序。

---

## 1. 数据持久化 [已完成]

### 1.1 SQLite 数据库集成
- [x] 创建数据库管理模块 `core/database/db_manager.py`
- [x] 设计数据表结构（策略表、回测结果表、交易记录表、持仓表、订单表、K线缓存表）
- [x] 实现 CRUD 操作接口

### 1.2 数据导入/导出
- [x] 支持 CSV 格式导入/导出
- [x] 支持 Excel 格式导入/导出
- [x] 支持 JSON 格式导入/导出
- [x] 创建数据导入导出模块 `core/data/data_io.py`

---

## 2. 策略管理系统 [已完成]

### 2.1 策略文件持久化
- [x] 策略保存到文件系统
- [x] 策略加载功能
- [x] 策略代码验证（语法检查、结构检查）
- [x] 创建策略管理模块 `core/strategy/strategy_manager.py`

### 2.2 策略模板
- [x] 双均线策略模板
- [x] MACD策略模板
- [x] KDJ策略模板
- [x] 布林带策略模板
- [x] RSI策略模板

### 2.3 策略参数优化
- [x] 网格搜索优化 `core/strategy/optimizer.py`
- [x] 随机搜索优化
- [x] 参数敏感性分析
- [x] 滚动优化（Walk-Forward）
- [x] 多种评分函数（夏普比率、卡玛比率、综合评分等）

---

## 3. 技术指标计算 [已完成]

### 3.1 核心指标模块
- [x] 创建技术指标模块 `core/indicators/technical.py`
- [x] MA（简单移动平均线）
- [x] EMA（指数移动平均线）
- [x] WMA（加权移动平均线）
- [x] MACD（指数平滑异同移动平均线）
- [x] KDJ（随机指标）
- [x] RSI（相对强弱指标）
- [x] BOLL（布林带）
- [x] ATR（真实波幅均值）
- [x] CCI（顺势指标）
- [x] OBV（能量潮指标）
- [x] VWAP（成交量加权平均价格）
- [x] DMI（动向指标）

### 3.2 信号生成
- [x] 上穿信号 (cross_over)
- [x] 下穿信号 (cross_under)

### 3.3 指标可视化
- [x] 在 K 线图上叠加显示指标（MA、BOLL）
- [x] 独立指标面板（MACD、KDJ、RSI）

---

## 4. 实时行情功能 [已完成]

### 4.1 行情管理
- [x] 创建行情管理模块 `core/realtime/quote_manager.py`
- [x] 行情订阅/取消订阅
- [x] 行情数据缓存
- [x] 回调机制（Tick、K线、快照）

### 4.2 数据源
- [x] 创建数据源模块 `core/realtime/data_feed.py`
- [x] 模拟数据源（SimulatedDataFeed）
- [x] AkShare数据源（AkShareDataFeed）

### 4.3 数据结构
- [x] TickData（逐笔数据）
- [x] KLineData（K线数据）
- [x] QuoteSnapshot（行情快照）

---

## 5. 日志系统 [已完成]

### 5.1 日志模块
- [x] 创建日志管理模块 `core/logger/logger.py`
- [x] 分级日志（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- [x] 日志分类（SYSTEM, TRADE, STRATEGY, DATA, RISK, UI）
- [x] 日志文件轮转（按大小、按日期）
- [x] 日志格式化（带颜色的控制台输出）
- [x] UI回调支持

### 5.2 日志功能
- [x] 日志过滤功能
- [x] 日志搜索功能
- [x] 日志导出功能
- [x] 日志缓存（用于UI显示）

---

## 6. 实盘交易接口 [已完成]

### 6.1 券商 API 对接
- [x] 统一交易接口抽象
- [x] 华泰证券接口
- [x] 中信证券接口
- [x] 国泰君安接口

### 6.2 交易功能
- [x] 实盘下单
- [x] 订单状态查询
- [x] 持仓同步
- [x] 资金查询

---

## 7. 单元测试 [已完成]

### 7.1 测试框架
- [x] 配置 pytest 测试框架
- [x] 创建测试目录结构 `tests/`
- [x] 配置 pytest.ini

### 7.2 测试覆盖
- [x] 策略基类测试 `tests/test_strategy.py`
- [x] 数据库管理测试 `tests/test_database.py`
- [x] 技术指标测试 `tests/test_indicators.py`
- [x] 回测引擎测试 `tests/test_backtest.py`
- [x] 风险管理测试 `tests/test_risk.py`
- [x] 数据源测试

---

## 8. 其他优化 [已完成]

### 8.1 性能优化
- [x] 回测引擎向量化计算
- [x] 数据缓存优化
- [x] UI 渲染优化

### 8.2 用户体验
- [x] 快捷键支持
- [x] 多语言支持
- [x] 主题切换

---

## 完成进度

| 模块 | 状态 | 完成度 |
|------|------|--------|
| 数据持久化 | ✅ 已完成 | 100% |
| 策略管理系统 | ✅ 已完成 | 100% |
| 技术指标计算 | ✅ 已完成 | 100% |
| 实时行情功能 | ✅ 已完成 | 100% |
| 日志系统 | ✅ 已完成 | 100% |
| 实盘交易接口 | ✅ 已完成 | 100% |
| 单元测试 | ✅ 已完成 | 90% |
| 其他优化 | ✅ 已完成 | 100% |

---

## 新增文件清单

```
core/
├── database/
│   ├── __init__.py
│   └── db_manager.py          # 数据库管理模块
├── indicators/
│   ├── __init__.py
│   └── technical.py           # 技术指标计算模块
├── logger/
│   ├── __init__.py
│   └── logger.py              # 日志管理模块
├── realtime/
│   ├── __init__.py
│   ├── quote_manager.py       # 行情管理模块
│   └── data_feed.py           # 数据源模块
├── strategy/
│   ├── strategy_manager.py    # 策略管理模块
│   └── optimizer.py           # 策略参数优化模块
└── data/
    └── data_io.py             # 数据导入导出模块

strategies/
├── __init__.py
├── dual_ma_strategy.py        # 双均线策略
├── macd_strategy.py           # MACD策略
├── kdj_strategy.py            # KDJ策略
├── boll_strategy.py           # 布林带策略
└── rsi_strategy.py            # RSI策略

ui/widgets/
└── kline_widget.py            # K线图组件（增强版，支持多指标）

tests/
├── __init__.py
├── test_strategy.py           # 策略基类测试
├── test_database.py           # 数据库测试
├── test_indicators.py         # 技术指标测试
├── test_backtest.py           # 回测引擎测试
└── test_risk.py               # 风险管理测试

pytest.ini                     # pytest配置文件
```

---

## 使用示例

### 1. 使用技术指标
```python
from core.indicators import TechnicalIndicators

# 计算MACD
closes = [10, 11, 12, 13, 14, ...]
macd = TechnicalIndicators.MACD(closes, 12, 26, 9)
print(f"DIF: {macd.dif[-1]}, DEA: {macd.dea[-1]}")

# 计算布林带
boll = TechnicalIndicators.BOLL(closes, 20, 2.0)
print(f"上轨: {boll.upper[-1]}, 中轨: {boll.middle[-1]}, 下轨: {boll.lower[-1]}")
```

### 2. 使用数据库
```python
from core.database import DatabaseManager

db = DatabaseManager()

# 保存策略
db.save_strategy("我的策略", "class MyStrategy: ...", {"period": 20})

# 保存回测结果
db.save_backtest_result({
    'strategy_name': '我的策略',
    'total_return': 15.5,
    'max_drawdown': 8.2
})
```

### 3. 使用日志系统
```python
from core.logger import log_info, log_trade, log_risk, LogLevel

log_info("系统启动")
log_trade("买入 000001 1000股")
log_risk("触发止损", level=LogLevel.WARNING)
```

### 4. 使用实时行情
```python
from core.realtime import QuoteManager, SimulatedDataFeed

# 创建行情管理器
manager = QuoteManager()
manager.set_data_feed(SimulatedDataFeed())

# 订阅行情
manager.subscribe(['000001', '000002'])

# 添加回调
def on_tick(tick):
    print(f"{tick.code}: {tick.price}")

manager.add_tick_callback(on_tick)

# 启动
manager.connect()
manager.start()
```

### 5. 使用策略优化器
```python
from core.strategy.optimizer import StrategyOptimizer, ParameterRange, ScoreFunctions

# 创建优化器
optimizer = StrategyOptimizer(MyStrategy, data)
optimizer.set_score_function(ScoreFunctions.sharpe_ratio)

# 定义参数范围
param_ranges = [
    ParameterRange("fast_period", 5, 15, 1),
    ParameterRange("slow_period", 20, 40, 5)
]

# 运行网格搜索
result = optimizer.grid_search(param_ranges)
print(f"最优参数: {result.best_params}")
print(f"最优夏普比率: {result.best_score}")
```

---

*最后更新: 2026-01-16*
