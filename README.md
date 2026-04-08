# RSI Futures Project

## 项目简介

这是一个面向加密货币永续合约的量化策略学习与实验项目，目标是将「策略开发 - 历史回测 - 指标评估 - 图表输出」串成一套可复用流程。项目当前聚焦于技术指标类策略（如 RSI、SuperTrend、EMA+ADX），并通过统一入口脚本进行策略切换和结果对比，便于快速迭代参数与验证思路。

数据与交易接口基于 `ccxt`，回测框架基于 `backtesting`，最终结果会输出为可交互的 HTML 报告并附带关键绩效卡片，方便从收益、风险、交易质量等维度做复盘分析。该仓库适合用于个人量化自学、策略原型验证和后续实盘化前的研究准备。

## 环境与依赖

本项目使用项目内虚拟环境（位于仓库根目录）：

- `.venv`

已安装核心依赖：

- `backtesting`
- `ccxt`
- `pandas`
- `numpy`
- `matplotlib`

---

## 常用命令（推荐）

### 方式 1：不激活环境，直接使用完整路径（最稳）

```cmd
.\.venv\Scripts\python.exe -m pip list
.\.venv\Scripts\python.exe run_backtest.py
```

---

## 项目结构（当前）

- `strategies/`：策略导入入口（方便统一切换策略）
- `charts/`：回测生成的 HTML 图表输出目录
- `run_backtest.py`：统一回测入口（推荐从这里切换策略）
- `report_utils.py`：HTML 回测结果卡片渲染工具

---

## 回测图表说明

- 所有策略导出的 HTML 会自动追加“回测结果卡片总览”
- 卡片分为四类：收益规模、风险波动、综合质量、交易统计
- 百分比字段自动带 `%`，并按统一规则保留 3 位小数
- 综合质量指标包含简短科普与经验阈值提示（如 Sharpe、Sortino、Calmar、SQN）

### 方式 2：CMD 中激活虚拟环境

```cmd
.\.venv\Scripts\activate.bat
python -m pip list
python run_backtest.py
```

### 方式 3：PowerShell 中激活虚拟环境

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip list
python run_backtest.py
```

---

## PowerShell 执行脚本被限制时

如果提示“系统不允许运行脚本”，可临时放开当前会话（仅当前窗口生效）：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

如果不想改执行策略，直接使用“方式 1”完整路径命令即可。

---

## 快速检查是否进入项目环境

激活后执行：

```cmd
where python
where pip
```

输出应优先指向当前项目目录下的虚拟环境，例如：

- `...\Rsi_futures_project\.venv\Scripts\python.exe`
- `...\Rsi_futures_project\.venv\Scripts\pip.exe`
