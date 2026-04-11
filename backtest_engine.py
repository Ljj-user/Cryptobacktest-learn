from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import pandas as pd
from backtesting.lib import FractionalBacktest

from config import BacktestConfig
from strategy_registry import get_strategy_meta


def load_ohlcv_data(data_path: str) -> pd.DataFrame:
    data = pd.read_csv(data_path, parse_dates=True, index_col="timestamp")
    data = data.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    return data


def _apply_strategy_overrides(strategy_cls, overrides: Dict):
    original = {}
    for k, v in overrides.items():
        if not hasattr(strategy_cls, k):
            raise ValueError(f"策略参数不存在: {strategy_cls.__name__}.{k}")
        original[k] = getattr(strategy_cls, k)
        setattr(strategy_cls, k, v)
    return original


def _restore_strategy_overrides(strategy_cls, original: Dict):
    for k, v in original.items():
        setattr(strategy_cls, k, v)


def calculate_capital_utilization(stats, data, initial_cash=10000.0):
    trades = stats.get("_trades", None)
    if trades is None or len(trades) == 0 or initial_cash <= 0:
        return 0.0
    n = len(data)
    pos_diff = [0.0] * (n + 1)
    for _, tr in trades.iterrows():
        entry_bar = int(tr["EntryBar"])
        exit_bar = int(tr["ExitBar"])
        size = float(tr["Size"])
        if entry_bar < 0 or entry_bar >= n:
            continue
        exit_bar = max(entry_bar, min(exit_bar, n - 1))
        pos_diff[entry_bar] += size
        if exit_bar + 1 < len(pos_diff):
            pos_diff[exit_bar + 1] -= size
    running_size = 0.0
    max_notional = 0.0
    closes = data["Close"].to_numpy()
    for i in range(n):
        running_size += pos_diff[i]
        notional = abs(running_size) * float(closes[i])
        max_notional = max(max_notional, notional)
    return (max_notional / float(initial_cash)) * 100.0


def calculate_margin_utilization(stats, data, margin=0.2):
    trades = stats.get("_trades", None)
    equity_curve = stats.get("_equity_curve", None)
    if trades is None or len(trades) == 0 or equity_curve is None or len(equity_curve) == 0:
        return 0.0
    n = len(data)
    pos_diff = [0.0] * (n + 1)
    for _, tr in trades.iterrows():
        entry_bar = int(tr["EntryBar"])
        exit_bar = int(tr["ExitBar"])
        size = float(tr["Size"])
        if entry_bar < 0 or entry_bar >= n:
            continue
        exit_bar = max(entry_bar, min(exit_bar, n - 1))
        pos_diff[entry_bar] += size
        if exit_bar + 1 < len(pos_diff):
            pos_diff[exit_bar + 1] -= size

    closes = data["Close"].to_numpy()
    equities = equity_curve["Equity"].to_numpy()
    running_size = 0.0
    max_ratio = 0.0
    for i in range(min(n, len(equities))):
        running_size += pos_diff[i]
        equity_now = float(equities[i])
        if equity_now <= 0:
            continue
        notional = abs(running_size) * float(closes[i])
        ratio = (notional * margin) / equity_now
        max_ratio = max(max_ratio, ratio)
    return max_ratio * 100.0


def estimate_realism_costs(stats, data, slippage_bps_per_side: float, est_funding_rate_8h: float):
    trades = stats.get("_trades", None)
    if trades is None or len(trades) == 0:
        return 0.0, 0.0, 0.0
    slip_rate = slippage_bps_per_side / 10000.0
    total_slippage = 0.0
    total_funding = 0.0
    closes = data["Close"].to_numpy()
    n = len(closes)
    for _, tr in trades.iterrows():
        size = abs(float(tr["Size"]))
        entry_bar = max(0, min(int(tr["EntryBar"]), n - 1))
        exit_bar = max(entry_bar, min(int(tr["ExitBar"]), n - 1))
        entry_price = float(tr["EntryPrice"])
        exit_price = float(tr["ExitPrice"])
        total_slippage += (size * entry_price + size * exit_price) * slip_rate
        bars_held = max(1, exit_bar - entry_bar + 1)
        funding_periods = bars_held / 8.0
        avg_price = (
            float(closes[entry_bar : exit_bar + 1].mean()) if exit_bar >= entry_bar else entry_price
        )
        total_funding += (size * avg_price) * est_funding_rate_8h * funding_periods
    return total_slippage, total_funding, total_funding


def _run_single(
    data: pd.DataFrame, config: BacktestConfig
) -> Tuple[Dict, pd.DataFrame, pd.DataFrame]:
    strategy_meta = get_strategy_meta(config.strategy)
    strategy_cls = strategy_meta.cls
    overrides_original = _apply_strategy_overrides(strategy_cls, config.strategy_overrides)
    try:
        bt = FractionalBacktest(
            data,
            strategy_cls,
            cash=config.cash,
            commission=config.cost.commission_rate(),
            margin=config.margin,
            finalize_trades=config.finalize_trades,
            trade_on_close=config.trade_on_close
            if config.trade_on_close is not None
            else (not config.cost.realism_mode),
            exclusive_orders=config.exclusive_orders,
        )
        stats = bt.run()
    finally:
        _restore_strategy_overrides(strategy_cls, overrides_original)

    stats = deepcopy(stats)
    stats["Capital Utilization [%]"] = calculate_capital_utilization(
        stats, data, initial_cash=config.cash
    )
    stats["Margin Utilization [%]"] = calculate_margin_utilization(
        stats, data, margin=config.margin
    )
    if config.cost.realism_mode:
        est_slippage, est_funding, est_extra = estimate_realism_costs(
            stats,
            data,
            slippage_bps_per_side=config.cost.slippage_bps_per_side,
            est_funding_rate_8h=config.cost.est_funding_rate_8h,
        )
        stats["Est. Slippage [$]"] = est_slippage
        stats["Est. Funding [$]"] = est_funding
        stats["Est. Extra Costs [$]"] = est_extra
        adj_equity = float(stats["Equity Final [$]"]) - est_extra
        stats["Realism-Adjusted Return [%]"] = ((adj_equity / config.cash) - 1.0) * 100.0
    return stats, stats.get("_trades"), stats.get("_equity_curve")


def run_backtest(data: pd.DataFrame, config: BacktestConfig) -> Dict:
    config.validate()
    out: Dict = {
        "mode": "single",
        "strategy": config.strategy,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(),
    }

    if config.validation.walk_forward:
        runs: List[Dict] = []
        train = config.validation.wf_train_bars
        test = config.validation.wf_test_bars
        step = config.validation.wf_step_bars
        start = 0
        while True:
            train_end = start + train
            test_end = train_end + test
            if test_end > len(data):
                break
            test_slice = data.iloc[train_end:test_end]
            stats, trades, equity = _run_single(test_slice, config)
            runs.append(
                {
                    "start": str(test_slice.index[0]),
                    "end": str(test_slice.index[-1]),
                    "Return [%]": float(stats["Return [%]"]),
                    "Max. Drawdown [%]": float(stats["Max. Drawdown [%]"]),
                    "Win Rate [%]": float(stats["Win Rate [%]"]),
                    "# Trades": int(stats["# Trades"]),
                }
            )
            start += step
        out["mode"] = "walk_forward"
        out["walk_forward_runs"] = runs
        if runs:
            out["walk_forward_summary"] = {
                "runs": len(runs),
                "avg_return_pct": sum(r["Return [%]"] for r in runs) / len(runs),
                "avg_drawdown_pct": sum(r["Max. Drawdown [%]"] for r in runs) / len(runs),
                "avg_win_rate_pct": sum(r["Win Rate [%]"] for r in runs) / len(runs),
            }
        return out

    if config.validation.split_date:
        split_ts = pd.Timestamp(config.validation.split_date)
        train_data = data[data.index < split_ts]
        test_data = data[data.index >= split_ts]
        if len(train_data) == 0 or len(test_data) == 0:
            raise ValueError("split_date 切分后训练集或测试集为空")
        train_stats, _, _ = _run_single(train_data, config)
        test_stats, test_trades, test_equity = _run_single(test_data, config)
        out["mode"] = "split"
        out["split"] = {"split_date": config.validation.split_date}
        out["train_stats"] = train_stats
        out["test_stats"] = test_stats
        out["trades"] = test_trades
        out["equity_curve"] = test_equity
        return out

    stats, trades, equity = _run_single(data, config)
    out["stats"] = stats
    out["trades"] = trades
    out["equity_curve"] = equity
    return out
