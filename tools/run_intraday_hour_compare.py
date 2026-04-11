import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_engine import load_ohlcv_data, run_backtest
from config import BacktestConfig


def run_case(open_h: int, close_h: int, alloc: float = 0.30):
    data = load_ohlcv_data("data/btc_futures_1h.csv")
    data = data[(data.index >= "2024-01-01") & (data.index < "2025-01-01")].copy()
    cfg = BacktestConfig(strategy="intraday_seasonality_btc")
    cfg.strategy_overrides = {
        "long_allocation": alloc,
        "open_trade_hour": open_h,
        "close_trade_hour": close_h,
    }
    result = run_backtest(data, cfg)
    s = result["stats"]
    return (
        float(s["Return [%]"]),
        float(s["Max. Drawdown [%]"]),
        float(s["Win Rate [%]"]),
        int(s["# Trades"]),
    )


def main():
    cases = [(22, 0), (23, 1)]
    for op, cl in cases:
        ret, dd, wr, n = run_case(op, cl, alloc=0.30)
        print(
            f"window={op:02d}:00->{cl:02d}:00 | Return={ret:.4f}% | "
            f"MaxDD={dd:.4f}% | WinRate={wr:.2f}% | Trades={n}"
        )


if __name__ == "__main__":
    main()
