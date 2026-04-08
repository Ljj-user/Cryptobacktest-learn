# RSI Futures Project

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
