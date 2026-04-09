# Crypto Futures Strategy Lab

## 这是一个什么项目

这是一个面向加密货币永续合约的策略研究仓库，目标是把一套完整流程跑通：

- 数据下载与质量检查
- 策略回测（支持单次/样本外/滚动验证）
- 成本与风险修正（realism mode）
- 图表与指标卡片输出
- 实验结果自动落盘，保证可复现

适合用于：个人量化学习、策略原型验证、参数迭代与对比。

---

## 核心能力（大改后）

### 1) 不用改源码切策略

通过 `cli.py` 直接选择策略，不再手改 `run_backtest.py` 的 import。

### 2) 统一配置与成本模型

在 `config.py` 统一管理：

- 资金与保证金参数
- 手续费/滑点/funding（realism mode）
- 验证模式（split-date / walk-forward）

### 3) 回测引擎统一入口

`backtest_engine.py` 统一处理：

- 数据加载
- 单次回测
- 样本内外切分验证
- 滚动窗口验证
- 扩展指标计算（资金使用率、保证金占用率等）

### 4) 实验追踪（可复现）

每次运行自动保存：

- `experiments/<run_id>/config.json`
- `experiments/<run_id>/stats.json`
- `experiments/<run_id>/trades.csv`
- `experiments/<run_id>/equity.csv`

并写入 `experiments/runs.jsonl` 作为运行索引。

### 5) 报告更可读

`report_utils.py` 输出的 HTML 卡片包含：

- 策略中文标题（变种带括号）
- 成本与仓位相关指标
- 证据强度提示（如样本数偏少、Sharpe为负）
- 最近多次同策略 run 对比表

---

## 项目结构（重点文件）

- `cli.py`：命令行入口（推荐使用）
- `backtest_engine.py`：回测执行与验证核心
- `config.py`：统一配置模型
- `strategy_registry.py`：策略注册表（新增策略从这里接入）
- `experiment_tracker.py`：实验落盘与索引
- `report_utils.py`：HTML 指标卡片渲染
- `run_backtest.py`：兼容入口（默认配置快速运行）
- `tools/optimize_low_drawdown.py`：参数网格优化脚本
- `strategies/`：策略实现
- `tests/`：自动化测试

---

## 环境与依赖

项目使用仓库内虚拟环境：

- `.venv`

核心依赖：

- `backtesting`
- `ccxt`
- `pandas`
- `numpy`
- `matplotlib`

---

## 快速开始（最常用）

### 1) 查看可用策略

```cmd
.\.venv\Scripts\python.exe cli.py --list-strategies
```

### 2) 单次回测（默认最推荐）

```cmd
.\.venv\Scripts\python.exe cli.py --strategy low_drawdown_trend
```

### 3) 单次回测 + 参数覆盖

```cmd
.\.venv\Scripts\python.exe cli.py --strategy dca_rsi --set long_entry_rsi=22 --set take_profit_pct=4
```

### 4) 样本内/样本外（OOS）验证

```cmd
.\.venv\Scripts\python.exe cli.py --strategy low_drawdown_trend --split-date 2025-01-01
```

### 5) 滚动窗口（Walk-Forward）验证

```cmd
.\.venv\Scripts\python.exe cli.py --strategy low_drawdown_trend --walk-forward --wf-train-bars 2880 --wf-test-bars 720 --wf-step-bars 720
```

---

## 回测口径（统一假设）

- 数据：`BTC/USDT:USDT` 永续，`1h` K线（`data/btc_futures_1h.csv`）
- 初始资金：`10000 USDT`
- 保证金参数：`margin=0.2`（约 5x）
- 订单处理：`finalize_trades=True`
- 成本模型：支持 realism mode（下一根开盘成交 + 滑点/资金费率估算）

---

## 已接入策略

- `ema_adx`：EMA + ADX 趋势过滤
- `rsi`：RSI 反转
- `supertrend`：SuperTrend 趋势跟随
- `dca_time`：按时间间隔 DCA
- `dca_rsi`：RSI 触发 DCA 变种
- `low_drawdown_trend`：低回撤趋势策略（EMA200 + ATR 风控）

用 `--list-strategies` 可以看到中文说明。

---

## 指标说明（新增重点）

- `资金使用率[%]`：历史最大名义仓位 / 初始资金 * 100
- `保证金占用率[%]`：历史最大（名义仓位 * margin / 当时权益）* 100
- `实盘修正收益率[%]`：回测收益基础上，额外扣除 funding 估算后的收益口径

---

## 科学回测建议流程

建议按这个顺序做，避免过拟合：

1. IS（样本内）调参，确保逻辑可跑通
2. OOS（样本外）验证，检查泛化
3. WFA（滚动窗口）验证，检查跨时期稳定性

经验阈值（可按风险偏好调整）：

- `Max. Drawdown [%] > -8`
- `Profit Factor > 1.1`
- `# Trades >= 50`

---

## 测试与稳定性

运行自动化测试：

```cmd
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

测试覆盖：

- 策略注册有效性
- 参数校验
- 数据契约
- 各策略 smoke 跑通

---

## 常见问题

### 新增策略怎么接入 CLI？

1. 在 `strategies/` 新建策略类  
2. 在 `strategy_registry.py` 注册一个新 key  
3. （建议）在 `strategies/__init__.py` 导出  
4. 之后直接 `--strategy <new_key>` 调用

### PowerShell 执行脚本受限怎么办？

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

或者直接用完整路径运行（无需激活）：

```cmd
.\.venv\Scripts\python.exe cli.py --strategy low_drawdown_trend
```
