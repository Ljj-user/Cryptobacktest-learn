import os
import sys
from pathlib import Path

from backtesting.lib import FractionalBacktest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_engine import load_ohlcv_data, run_backtest
from config import BacktestConfig
from experiment_tracker import create_run_dir, save_run_artifacts
from strategy_registry import get_strategy_meta


def main():
    data = load_ohlcv_data("data/btc_futures_1h.csv")
    data = data[(data.index >= "2025-01-01") & (data.index < "2026-01-01")].copy()

    cfg = BacktestConfig(strategy="intraday_seasonality_btc")
    cfg.resample = "1h"
    cfg.strategy_overrides = {
        "long_allocation": 0.30,
        "open_trade_hour": 5,
        "close_trade_hour": 12,
    }

    result = run_backtest(data, cfg)
    stats = result["stats"]
    trades = result["trades"]
    equity = result["equity_curve"]

    run_dir = create_run_dir(cfg.experiments_dir, cfg.strategy)
    save_run_artifacts(run_dir, cfg.to_dict(), dict(stats), trades, equity)

    os.makedirs(cfg.output_dir, exist_ok=True)
    html_path = f"{cfg.output_dir}/IntradaySeasonalityBTCStrategy_2025_1h_05_12.html"
    meta = get_strategy_meta(cfg.strategy)
    bt = FractionalBacktest(
        data,
        meta.cls,
        cash=cfg.cash,
        commission=cfg.cost.commission_rate(),
        margin=cfg.margin,
        finalize_trades=cfg.finalize_trades,
        trade_on_close=cfg.trade_on_close
        if cfg.trade_on_close is not None
        else (not cfg.cost.realism_mode),
        exclusive_orders=cfg.exclusive_orders,
    )
    bt.run(**cfg.strategy_overrides)
    bt.plot(resample="1h", filename=html_path)

    print("Window: 05:00 -> 12:00")
    print("Return [%]:", float(stats["Return [%]"]))
    print("Max. Drawdown [%]:", float(stats["Max. Drawdown [%]"]))
    print("Win Rate [%]:", float(stats["Win Rate [%]"]))
    print("# Trades:", int(stats["# Trades"]))
    print("Artifacts saved:", run_dir)
    print("Chart saved:", html_path)


if __name__ == "__main__":
    main()
