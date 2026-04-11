# 依赖升级检查清单

在升级核心库或放宽 `requirements.txt` 版本约束前，建议按顺序执行，避免 silent breakage。

## 1. 必跑（每次升级后）

```bash
# 使用项目 venv
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
python -m unittest discover -s tests -v
```

## 2. 按依赖类型的额外注意点

### `backtesting`

- 确认 `from backtesting.lib import FractionalBacktest` 仍可用（历史上 0.3.x 与 0.6.x 行为差异大）。
- 跑一次最小回测：`python cli.py --strategy low_drawdown_trend`（需本地有 `data/btc_futures_1h.csv`）。
- 检查 `charts/*.html` 是否仍能生成（依赖 bokeh 等传递依赖）。

### `pandas`

- 若放宽 `<3` 升级到 pandas 3.x：全量 unittest + 至少一次完整 CLI 回测。
- 关注 `read_csv(..., parse_dates=True)` 与时区索引行为。

### `ccxt`

- 升级大版本（如 4 → 5）后重跑 `data_fetch.py` 或等价拉取脚本，确认 Binance futures 接口无变更。
- 网络/代理环境需与生产一致时再验收。

### `numpy` / `matplotlib`

- 通常随 pandas/backtesting 约束即可；若单独升级，重跑 `tools/rebalancing_premium_backtest.py`（使用 matplotlib 作图）。

## 3. CI

推送前确保 [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) 在 GitHub Actions 上通过（含 Ruff + unittest）。
