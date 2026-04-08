import itertools
import os
import sys
import pandas as pd
from backtesting.lib import FractionalBacktest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from strategies.low_drawdown_trend_strategy import LowDrawdownTrendStrategy

REALISM_MODE = True
BASE_COMMISSION = 0.0002
SLIPPAGE_BPS_PER_SIDE = 3.0


def run_once(data, params):
    for k, v in params.items():
        setattr(LowDrawdownTrendStrategy, k, v)
    bt = FractionalBacktest(
        data,
        LowDrawdownTrendStrategy,
        cash=10000,
        commission=BASE_COMMISSION + (SLIPPAGE_BPS_PER_SIDE / 10000.0 if REALISM_MODE else 0.0),
        margin=0.2,
        finalize_trades=True,
        trade_on_close=not REALISM_MODE,
        exclusive_orders=True,
    )
    stats = bt.run()
    return {
        **params,
        "Return [%]": float(stats["Return [%]"]),
        "Max. Drawdown [%]": float(stats["Max. Drawdown [%]"]),
        "Win Rate [%]": float(stats["Win Rate [%]"]),
        "Sharpe Ratio": float(stats["Sharpe Ratio"]),
        "Profit Factor": float(stats["Profit Factor"]),
        "# Trades": int(stats["# Trades"]),
    }


def score(row):
    # Prefer positive return, low drawdown, decent hit-rate and PF
    return (
        row["Return [%]"] * 1.5
        + row["Sharpe Ratio"] * 2.0
        + (row["Profit Factor"] - 1.0) * 8.0
        + (row["Win Rate [%]"] - 50.0) * 0.08
        - abs(row["Max. Drawdown [%]"]) * 1.2
    )


def main():
    data = pd.read_csv("data/btc_futures_1h.csv", parse_dates=True, index_col="timestamp")
    data = data.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )

    grid = {
        "rsi_entry": [30, 34, 38],
        "rsi_exit": [52, 56, 60],
        "base_allocation": [0.04, 0.06],
        "add_allocation": [0.02, 0.03],
        "max_total_allocation": [0.18, 0.24],
        "take_profit_pct": [2.2, 2.8],
        "stop_loss_pct": [-3.2, -4.2],
        "trail_atr_mult": [1.2, 1.6],
    }

    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    results = []
    total = 1
    for v in values:
        total *= len(v)

    for idx, combo in enumerate(itertools.product(*values), start=1):
        params = dict(zip(keys, combo))
        row = run_once(data, params)
        row["_score"] = score(row)
        results.append(row)
        if idx % 50 == 0 or idx == total:
            print(f"Progress: {idx}/{total}")

    # hard filters: prioritize low drawdown and better win-rate
    filtered = [
        r
        for r in results
        if r["Max. Drawdown [%]"] >= -3.5 and r["Win Rate [%]"] >= 50 and r["Return [%]"] > 0
    ]
    target = filtered if filtered else results
    target = sorted(target, key=lambda x: x["_score"], reverse=True)

    print("\nTop 5 candidates:")
    for i, r in enumerate(target[:5], start=1):
        print(
            f"{i}. score={r['_score']:.3f} | ret={r['Return [%]']:.3f}% | dd={r['Max. Drawdown [%]']:.3f}% | "
            f"win={r['Win Rate [%]']:.2f}% | pf={r['Profit Factor']:.3f} | sharpe={r['Sharpe Ratio']:.3f} | trades={r['# Trades']}"
        )
        print(
            "   params:",
            {k: r[k] for k in keys},
        )


if __name__ == "__main__":
    main()
