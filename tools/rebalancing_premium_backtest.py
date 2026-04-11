"""
Rebalancing Premium in Cryptocurrencies (Quantpedia / QuantConnect) — research backtest.

Important:
- This project’s main backtest engine (backtesting.py) is single-instrument.
- The original strategy is a multi-crypto long/short portfolio.
  So we implement the same portfolio logic as a standalone vectorized backtest.

Logic (kept consistent with the original QC code):
- Universe: a list of crypto tickers.
- Long leg: daily rebalanced equal-weight portfolio across the universe (100% notional of current equity).
- Short leg: "buy-and-hold" equal-weight portfolio, shorted once at inception with 70% notional of initial equity.
  (No rebalancing on the short leg; weights drift.)

Data:
- Uses CCXT (Binance spot) daily OHLCV and caches to data/rebalancing_premium/.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import ccxt  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "ccxt is required to run this script. Install it in your venv (pip install ccxt) and retry."
    ) from e


UNIVERSE_USDT: List[str] = [
    "BTC/USDT",
    "BAT/USDT",
    "DAI/USDT",
    "DGB/USDT",
    "EOS/USDT",
    "ETH/USDT",
    "FUN/USDT",
    "LTC/USDT",
    "NEO/USDT",
    "OMG/USDT",
    "SNT/USDT",
    "TRX/USDT",
    "XLM/USDT",
    "XMR/USDT",
    "XRP/USDT",
    "XVG/USDT",
    "ZEC/USDT",
    "ZRX/USDT",
    "LRC/USDT",
    "REQ/USDT",
    "SAN/USDT",
    "WAXP/USDT",  # WAX on Binance is typically WAXP
    "ZIL/USDT",
    "IOTA/USDT",
    "MANA/USDT",
    "DATA/USDT",
]


@dataclass(frozen=True)
class BacktestSpec:
    start: str = "2022-01-01T00:00:00Z"
    end: str = "2023-01-01T00:00:00Z"
    initial_cash: float = 1.0
    short_side_percentage: float = 0.7
    timeframe: str = "1d"


def _parse8601_ms(ex, s: str) -> int:
    ms = ex.parse8601(s)
    if ms is None:
        raise ValueError(f"Invalid ISO8601 time: {s}")
    return int(ms)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _cache_path(cache_dir: Path, symbol: str, timeframe: str) -> Path:
    safe = symbol.replace("/", "_").replace(":", "_")
    return cache_dir / f"{safe}_{timeframe}.csv"


def fetch_ohlcv_cached(
    ex,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    cache_dir: Path,
    limit: int = 1000,
) -> pd.DataFrame:
    def _naive(ts: str) -> pd.Timestamp:
        t = pd.Timestamp(ts)
        # Make it comparable to our tz-naive index
        return t.tz_convert(None) if getattr(t, "tzinfo", None) is not None else t

    start_ts = _naive(start)
    end_ts = _naive(end)

    _ensure_dir(cache_dir)
    p = _cache_path(cache_dir, symbol, timeframe)
    if p.exists():
        df = pd.read_csv(p, parse_dates=["timestamp"])
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"])
        df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] < end_ts)]
        df = df.set_index("timestamp")
        return df

    start_ms = _parse8601_ms(ex, start)
    end_ms = _parse8601_ms(ex, end)
    tf_ms = ex.parse_timeframe(timeframe) * 1000

    all_rows: List[List[float]] = []
    since = start_ms
    while since < end_ms:
        rows = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not rows:
            break
        all_rows.extend(rows)
        last_ts = int(rows[-1][0])
        nxt = last_ts + tf_ms
        if nxt <= since:
            break
        since = nxt

    if not all_rows:
        raise RuntimeError(f"No OHLCV fetched for {symbol} {timeframe}")

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(None)
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"])
    df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] < end_ts)]
    df.to_csv(p, index=False)
    return df.set_index("timestamp")


def load_close_matrix(
    symbols: Iterable[str],
    spec: BacktestSpec,
    cache_dir: Path,
    proxy_url: str | None = None,
) -> Tuple[pd.DataFrame, List[str]]:
    ex = ccxt.binance(
        {
            "timeout": 30000,
            "enableRateLimit": True,
            "proxies": {"http": proxy_url, "https": proxy_url} if proxy_url else None,
        }
    )
    ex.load_markets()

    closes: Dict[str, pd.Series] = {}
    used: List[str] = []
    for sym in symbols:
        try:
            df = fetch_ohlcv_cached(
                ex, sym, spec.timeframe, spec.start, spec.end, cache_dir=cache_dir
            )
            s = df["close"].astype(float).rename(sym)
            closes[sym] = s
            used.append(sym)
        except Exception:
            # Skip missing / delisted / unsupported markets
            continue

    if len(used) < 3:
        raise RuntimeError(f"Too few symbols available ({len(used)}). Cannot backtest portfolio.")

    full = pd.concat([closes[s] for s in used], axis=1).sort_index()

    # QuantConnect has a unified dataset; in CCXT spot, listings are staggered and gaps exist.
    # We keep the portfolio logic intact, but adapt the data by pruning symbols until we have
    # a sufficiently long common panel (complete rows across remaining symbols).
    remaining = list(full.columns)
    while len(remaining) >= 3:
        mat = full[remaining]
        firsts = {c: mat[c].first_valid_index() for c in mat.columns}
        lasts = {c: mat[c].last_valid_index() for c in mat.columns}
        common_start = max([t for t in firsts.values() if t is not None])
        common_end = min([t for t in lasts.values() if t is not None])
        if common_start >= common_end:
            # Drop the symbol that starts the latest (most restrictive)
            drop_c = max(firsts.items(), key=lambda kv: kv[1] or pd.Timestamp.min)[0]
            remaining.remove(drop_c)
            continue

        panel = mat.loc[common_start:common_end]
        panel = panel.dropna(how="any")
        if len(panel) >= 200:
            return panel, remaining

        # Not enough complete rows: drop the symbol with the worst completeness in the overlap window
        overlap = mat.loc[common_start:common_end]
        na_counts = overlap.isna().sum().sort_values(ascending=False)
        drop_c = str(na_counts.index[0])
        remaining.remove(drop_c)

    raise RuntimeError(
        "Cannot form a usable common panel (need >=3 symbols with >=200 aligned days)."
    )


def perf_stats(equity: pd.Series) -> Dict[str, float]:
    eq = equity.astype(float)
    rets = eq.pct_change().dropna()
    if len(rets) == 0:
        return {"Return [%]": 0.0, "CAGR [%]": 0.0, "Sharpe": 0.0, "MaxDD [%]": 0.0}

    total_ret = (eq.iloc[-1] / eq.iloc[0] - 1.0) * 100.0
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0
    vol = rets.std(ddof=0) * np.sqrt(365.25)
    sharpe = (rets.mean() * 365.25) / vol if vol > 0 else 0.0
    peak = eq.cummax()
    dd = (eq / peak - 1.0) * 100.0
    maxdd = float(dd.min())
    return {
        "Return [%]": float(total_ret),
        "CAGR [%]": float(cagr * 100.0),
        "Sharpe": float(sharpe),
        "MaxDD [%]": float(maxdd),
    }


def run_rebalancing_premium(close_mat: pd.DataFrame, spec: BacktestSpec) -> pd.DataFrame:
    prices = close_mat.astype(float)
    n = prices.shape[1]

    # Daily individual returns
    asset_rets = prices.pct_change().fillna(0.0)

    # Long leg: daily rebalanced equal-weight => portfolio return is arithmetic mean of asset returns.
    long_ret = asset_rets.mean(axis=1)

    # Short leg: set fixed quantities at inception using 70% of initial equity (equal-weight notionals).
    p0 = prices.iloc[0]
    short_notional = spec.initial_cash * spec.short_side_percentage
    q = (short_notional / n) / p0  # quantity per asset (positive); position is -q

    # Daily short PnL in equity units (cash terms). Uses price differences.
    price_diff = prices.diff().fillna(0.0)
    short_pnl = -(price_diff.mul(q, axis=1)).sum(axis=1)  # negative because short

    equity = []
    eq = float(spec.initial_cash)
    for t in prices.index:
        # Long leg scales with current equity (100% notional)
        eq = eq * (1.0 + float(long_ret.loc[t])) + float(short_pnl.loc[t])
        # Liquidation guard: this portfolio can go bankrupt with a fixed short notional.
        # In a real brokerage / QC backtest, equity would not be allowed to go negative.
        if eq <= 0:
            equity.append(0.0)
            # Fill the remaining timestamps with 0 equity and stop.
            remaining = len(prices.index) - len(equity)
            if remaining > 0:
                equity.extend([0.0] * remaining)
            break
        equity.append(eq)

    out = pd.DataFrame(
        {
            "Equity": np.array(equity, dtype=float),
            "LongRet": long_ret.to_numpy(),
            "ShortPnL": short_pnl.to_numpy(),
        },
        index=prices.index,
    )
    peak = out["Equity"].cummax()
    out["DrawdownPct"] = (out["Equity"] / peak - 1.0) * 100.0
    return out


def save_charts(equity_df: pd.DataFrame, out_dir: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    axes[0].plot(equity_df.index, equity_df["Equity"], color="#2563eb", linewidth=1.8)
    axes[0].set_title("Rebalancing Premium - Equity Curve")
    axes[0].set_ylabel("Equity")
    axes[0].grid(alpha=0.25)

    axes[1].fill_between(
        equity_df.index,
        equity_df["DrawdownPct"].to_numpy(),
        0,
        color="#dc2626",
        alpha=0.35,
        linewidth=0,
    )
    axes[1].plot(equity_df.index, equity_df["DrawdownPct"], color="#991b1b", linewidth=1.2)
    axes[1].set_title("Drawdown (%)")
    axes[1].set_ylabel("Drawdown %")
    axes[1].set_xlabel("Date")
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(out_dir / "equity_drawdown.png", dpi=160)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebalancing premium portfolio backtest")
    parser.add_argument("--start", default="2022-01-01T00:00:00Z")
    parser.add_argument("--end", default="2023-01-01T00:00:00Z")
    parser.add_argument("--initial-cash", type=float, default=1.0)
    parser.add_argument("--short-side-percentage", type=float, default=0.7)
    parser.add_argument("--proxy-url", default="http://127.0.0.1:7897")
    return parser.parse_args()


def main():
    args = parse_args()
    spec = BacktestSpec(
        start=args.start,
        end=args.end,
        initial_cash=args.initial_cash,
        short_side_percentage=args.short_side_percentage,
    )
    root = Path(__file__).resolve().parents[1]
    cache_dir = root / "data" / "rebalancing_premium"

    proxy_url = args.proxy_url or None

    close_mat, used = load_close_matrix(
        UNIVERSE_USDT, spec, cache_dir=cache_dir, proxy_url=proxy_url
    )
    eq_df = run_rebalancing_premium(close_mat, spec)
    stats = perf_stats(eq_df["Equity"])

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_rebalancing_premium"
    out_dir = root / "experiments" / run_id
    _ensure_dir(out_dir)

    close_mat.to_csv(out_dir / "close_matrix.csv")
    eq_df.to_csv(out_dir / "equity.csv")
    save_charts(eq_df, out_dir)
    (out_dir / "universe.txt").write_text("\n".join(used) + "\n", encoding="utf-8")
    pd.Series(
        {
            **stats,
            "UniverseSize": len(used),
            "Start": str(eq_df.index[0]),
            "End": str(eq_df.index[-1]),
        }
    ).to_csv(out_dir / "stats.csv")

    print("Rebalancing Premium — portfolio backtest")
    print("Universe used:", len(used))
    print("Universe symbols:", ", ".join(used))
    print("Period:", eq_df.index[0], "->", eq_df.index[-1], "bars:", len(eq_df))
    for k, v in stats.items():
        print(f"{k}: {v:.4f}")
    print("Artifacts saved:", str(out_dir))


if __name__ == "__main__":  # pragma: no cover
    main()
