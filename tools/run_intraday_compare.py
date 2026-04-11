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


def run_case(allocation: float):
    data = load_ohlcv_data("data/btc_futures_1h.csv")
    data = data[(data.index >= "2024-01-01") & (data.index < "2025-01-01")].copy()

    cfg = BacktestConfig(strategy="intraday_seasonality_btc")
    cfg.resample = "1h"
    cfg.strategy_overrides = {
        "long_allocation": allocation,
        "open_trade_hour": 22,
        "close_trade_hour": 0,
    }

    result = run_backtest(data, cfg)
    stats = result["stats"]
    trades = result["trades"]
    equity = result["equity_curve"]

    run_dir = create_run_dir(cfg.experiments_dir, cfg.strategy)
    save_run_artifacts(run_dir, cfg.to_dict(), dict(stats), trades, equity)

    os.makedirs(cfg.output_dir, exist_ok=True)
    html_path = (
        f"{cfg.output_dir}/IntradaySeasonalityBTCStrategy_2024_1h_alloc_{allocation:.2f}.html"
    )
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

    return {
        "allocation": allocation,
        "return": float(stats["Return [%]"]),
        "maxdd": float(stats["Max. Drawdown [%]"]),
        "winrate": float(stats["Win Rate [%]"]),
        "trades": int(stats["# Trades"]),
        "run_dir": run_dir,
        "chart": html_path,
    }


def main():
    cases = [0.15, 0.50]
    rows = [run_case(a) for a in cases]
    for r in rows:
        print(
            f"alloc={r['allocation']:.2f} | Return={r['return']:.4f}% | "
            f"MaxDD={r['maxdd']:.4f}% | WinRate={r['winrate']:.2f}% | Trades={r['trades']}"
        )
        print("  Artifacts:", r["run_dir"])
        print("  Chart:", r["chart"])


if __name__ == "__main__":
    main()
