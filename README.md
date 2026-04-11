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

## 安装与环境

需要 **Python 3.10+**（CI 在 3.10 / 3.12 上跑通）。

### 方式 A：venv + pip（推荐）

```bash
cd Crypto-futures-strategy-lab
python -m venv .venv
# Windows CMD:
.venv\Scripts\activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
```

### 方式 B：Conda（可选）

```bash
conda create -n crypto-lab python=3.12 -y
conda activate crypto-lab
pip install -r requirements.txt
```

依赖说明见 `requirements.txt`（核心：`backtesting`、`pandas`、`numpy`、`matplotlib`、`ccxt`）。

---

## 最小可复现示例

1. 确保仓库根目录存在示例数据 `data/btc_futures_1h.csv`（若无，可用 `python data_fetch.py` 从 Binance 拉取，需可访问交易所 API 与网络）。
2. 运行一次默认回测：

```bash
python cli.py --strategy low_drawdown_trend
```

终端会打印类似摘要（数值随数据与版本略有不同）：

```
Start                                           2024-01-01 00:00:00
End                                             2025-12-31 23:00:00
Return [%]                                      ...
Max. Drawdown [%]                               ...
# Trades                                        ...
_strategy                                       LowDrawdownTrendStrategy
...
Artifacts saved: experiments\<run_id>_low_drawdown_trend
```

同时在 `charts/` 下生成策略对应的 HTML 图表；实验产物在 `experiments/<run_id>_.../`。

---

## 快速开始（最常用）

### 0) 懒人一键脚本（推荐）

项目根目录已提供 4 个快捷脚本，减少重复输入：

- `start.cmd`：进入项目并激活 `.venv`
- `list-strategies.cmd`：显示可用策略列表
- `bt.cmd`：回测命令快捷入口（参数原样透传给 `cli.py`）
- `test.cmd`：运行测试

示例：

```cmd
start.cmd
list-strategies.cmd
bt.cmd --strategy low_drawdown_trend
bt.cmd --strategy dca_rsi --set long_entry_rsi=22 --set take_profit_pct=4
test.cmd
```

---

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
- 成本模型：支持 realism mode（有效佣金 = 手续费 + 滑点 bps；资金费为事后启发式估算）

**详细假设、与实盘的差异、指标是否重复计量** 见 [docs/backtest_assumptions.md](docs/backtest_assumptions.md)。
升级 `backtesting` / `pandas` / `ccxt` 时的检查步骤见 [docs/dependency_upgrade_checklist.md](docs/dependency_upgrade_checklist.md)。

---

## 已接入策略

- `ema_adx`：EMA + ADX 趋势过滤
- `rsi`：RSI 反转
- `supertrend`：SuperTrend 趋势跟随
- `dca_time`：按时间间隔 DCA
- `dca_rsi`：RSI 触发 DCA 变种
- `low_drawdown_trend`：低回撤趋势策略（EMA200 + ATR 风控）
- `donchian_long`：Donchian 突破 + ATR 追踪 + 金字塔加仓（仅做多）
- `intraday_seasonality_btc`：UTC 固定时段开平（日内季节性研究用）

用 `--list-strategies` 可以看到中文说明。

---

## 指标说明（新增重点）

- `资金使用率[%]`：历史最大名义仓位 / 初始资金 * 100
- `保证金占用率[%]`：历史最大（名义仓位 * margin / 当时权益）* 100
- `策略收益率 Return [%]`：引擎内已按 **有效佣金**（含滑点 bps）扣费后的收益
- `估算滑点成本 Est. Slippage [$]`：与滑点 bps **同口径**的美元展示，**未再从最终权益重复扣除**（避免与佣金重复）
- `估算资金费率成本 Est. Funding [$]`：按持仓时长与固定 8h 费率粗算
- `实盘修正收益率 Realism-Adjusted Return [%]`：在最终权益上 **减去估算资金费**；**不**再减 `Est. Slippage`（滑点已在仿真佣金中体现）

完整说明见 [docs/backtest_assumptions.md](docs/backtest_assumptions.md)。

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

或（已激活 venv 时）：

```bash
python -m unittest discover -s tests -v
```

测试覆盖：

- 策略注册有效性
- 参数校验
- 数据契约
- 各策略 smoke 跑通

推送至 `main` / `master` 或提交 PR 时，GitHub Actions 会安装 `requirements-dev.txt`（含运行时依赖），依次执行 **Ruff 检查**、**Ruff 格式化检查**、`unittest`（见 [`.github/workflows/ci.yml`](.github/workflows/ci.yml)）。fork 后可在自己仓库的 Actions 页查看运行结果。

### 开发：代码风格与 pre-commit

安装开发依赖（含 `ruff`、`pre-commit`）：

```bash
pip install -r requirements-dev.txt
```

在仓库根目录启用 Git 提交前检查（可选但推荐）：

```bash
pre-commit install
```

手动对全仓库跑一遍（与 CI 口径一致）：

```bash
ruff check .
ruff format --check .
pre-commit run --all-files
```

配置见根目录 [`pyproject.toml`](pyproject.toml)（Ruff）与 [`.pre-commit-config.yaml`](.pre-commit-config.yaml)。

---

## 贡献

欢迎 Issue / PR。提交前请：

1. 运行 `ruff check .` 与 `ruff format --check .`（或 `pre-commit run --all-files`）
2. 运行 `python -m unittest discover -s tests` 确保通过
3. 策略变更请在 `strategy_registry.py` 注册并补充 `strategies/__init__.py` 导出（如适用）
4. 保持改动聚焦、避免无关大改

---

## 许可

本项目采用 **MIT License**，见仓库根目录 `LICENSE`。

---

## 联系方式

通过 GitHub 仓库的 **Issues** 沟通即可（无单独邮件列表）。

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
