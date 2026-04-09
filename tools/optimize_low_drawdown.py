import argparse
import itertools
import json
import os
import sys

import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backtest_engine import load_ohlcv_data, run_backtest
from config import BacktestConfig


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
    parser = argparse.ArgumentParser(description="Grid optimize low drawdown strategy")
    parser.add_argument("--data", default="data/btc_futures_1h.csv")
    parser.add_argument("--split-date", default=None)
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--wf-train-bars", type=int, default=24 * 120)
    parser.add_argument("--wf-test-bars", type=int, default=24 * 30)
    parser.add_argument("--wf-step-bars", type=int, default=24 * 30)
    parser.add_argument("--out", default="experiments/optimization_low_drawdown.csv")
    args = parser.parse_args()

    data = load_ohlcv_data(args.data)
    config = BacktestConfig(strategy="low_drawdown_trend")
    config.validation.split_date = args.split_date
    config.validation.walk_forward = args.walk_forward
    config.validation.wf_train_bars = args.wf_train_bars
    config.validation.wf_test_bars = args.wf_test_bars
    config.validation.wf_step_bars = args.wf_step_bars

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
        config.strategy_overrides = params
        result = run_backtest(data, config)
        if result["mode"] == "single":
            stats = result["stats"]
            row = {
                **params,
                "mode": "single",
                "Return [%]": float(stats["Return [%]"]),
                "Max. Drawdown [%]": float(stats["Max. Drawdown [%]"]),
                "Win Rate [%]": float(stats["Win Rate [%]"]),
                "Sharpe Ratio": float(stats["Sharpe Ratio"]),
                "Profit Factor": float(stats["Profit Factor"]),
                "# Trades": int(stats["# Trades"]),
            }
        elif result["mode"] == "split":
            stats = result["test_stats"]
            row = {
                **params,
                "mode": "split",
                "Return [%]": float(stats["Return [%]"]),
                "Max. Drawdown [%]": float(stats["Max. Drawdown [%]"]),
                "Win Rate [%]": float(stats["Win Rate [%]"]),
                "Sharpe Ratio": float(stats["Sharpe Ratio"]),
                "Profit Factor": float(stats["Profit Factor"]),
                "# Trades": int(stats["# Trades"]),
            }
        else:
            summary = result.get("walk_forward_summary", {})
            row = {
                **params,
                "mode": "walk_forward",
                "Return [%]": float(summary.get("avg_return_pct", 0.0)),
                "Max. Drawdown [%]": float(summary.get("avg_drawdown_pct", 0.0)),
                "Win Rate [%]": float(summary.get("avg_win_rate_pct", 0.0)),
                "Sharpe Ratio": 0.0,
                "Profit Factor": 0.0,
                "# Trades": 0,
            }
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

    out_df = pd.DataFrame(results).sort_values("_score", ascending=False)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out_df.to_csv(args.out, index=False)
    with open(args.out.replace(".csv", ".json"), "w", encoding="utf-8") as f:
        json.dump(out_df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

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
    print(f"\nFull results exported: {args.out}")


if __name__ == "__main__":
    main()
