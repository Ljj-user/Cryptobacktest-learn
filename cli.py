import argparse
import os

from backtesting.lib import FractionalBacktest

from backtest_engine import load_ohlcv_data, run_backtest
from config import BacktestConfig
from experiment_tracker import append_run_index, create_run_dir, load_recent_runs, save_run_artifacts
from report_utils import write_stats_cards_to_html
from strategy_registry import STRATEGY_REGISTRY, get_strategy_meta, list_strategy_keys


def parse_overrides(override_items):
    overrides = {}
    for item in override_items:
        if "=" not in item:
            raise ValueError(f"--set 参数格式错误: {item}，应为 key=value")
        key, value = item.split("=", 1)
        try:
            cast_value = float(value)
            if cast_value.is_integer():
                cast_value = int(cast_value)
        except ValueError:
            cast_value = value
        overrides[key] = cast_value
    return overrides


def build_config(args):
    cfg = BacktestConfig()
    cfg.strategy = args.strategy
    cfg.data_path = args.data
    cfg.output_dir = args.out_dir
    cfg.experiments_dir = args.experiments_dir
    cfg.cash = args.cash
    cfg.margin = args.margin
    cfg.cost.realism_mode = args.realism_mode
    cfg.cost.base_commission = args.base_commission
    cfg.cost.slippage_bps_per_side = args.slippage_bps
    cfg.cost.est_funding_rate_8h = args.funding_rate_8h
    cfg.validation.split_date = args.split_date
    cfg.validation.walk_forward = args.walk_forward
    cfg.validation.wf_train_bars = args.wf_train_bars
    cfg.validation.wf_test_bars = args.wf_test_bars
    cfg.validation.wf_step_bars = args.wf_step_bars
    cfg.strategy_overrides = parse_overrides(args.set)
    cfg.validate()
    return cfg


def main():
    parser = argparse.ArgumentParser(description="Crypto futures backtest CLI")
    parser.add_argument("--list-strategies", action="store_true", help="列出可用策略并退出")
    parser.add_argument("--strategy", default="low_drawdown_trend", choices=list_strategy_keys())
    parser.add_argument("--data", default="data/btc_futures_1h.csv")
    parser.add_argument("--cash", type=float, default=10000.0)
    parser.add_argument("--margin", type=float, default=0.2)
    parser.add_argument("--realism-mode", action="store_true", default=True)
    parser.add_argument("--base-commission", type=float, default=0.0002)
    parser.add_argument("--slippage-bps", type=float, default=3.0)
    parser.add_argument("--funding-rate-8h", type=float, default=0.0001)
    parser.add_argument("--out-dir", default="charts")
    parser.add_argument("--experiments-dir", default="experiments")
    parser.add_argument("--split-date", default=None)
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--wf-train-bars", type=int, default=24 * 120)
    parser.add_argument("--wf-test-bars", type=int, default=24 * 30)
    parser.add_argument("--wf-step-bars", type=int, default=24 * 30)
    parser.add_argument("--set", action="append", default=[], help="策略参数覆盖，例如 --set rsi_entry=30")
    args = parser.parse_args()

    if args.list_strategies:
        print("可用策略：")
        for key in list_strategy_keys():
            meta = STRATEGY_REGISTRY[key]
            print(f"- {key}: {meta.display_name} | {meta.description}")
        return

    config = build_config(args)
    strategy_meta = get_strategy_meta(config.strategy)
    data = load_ohlcv_data(config.data_path)
    result = run_backtest(data, config)

    if result["mode"] == "single":
        stats = result["stats"]
        trades = result["trades"]
        equity_curve = result["equity_curve"]
        run_dir = create_run_dir(config.experiments_dir, config.strategy)
        save_run_artifacts(run_dir, config.to_dict(), dict(stats), trades, equity_curve)
        append_run_index(
            config.experiments_dir,
            {
                "run_dir": run_dir,
                "strategy": config.strategy,
                "Return [%]": float(stats["Return [%]"]),
                "Max. Drawdown [%]": float(stats["Max. Drawdown [%]"]),
                "Win Rate [%]": float(stats["Win Rate [%]"]),
                "Sharpe Ratio": float(stats["Sharpe Ratio"]),
                "# Trades": int(stats["# Trades"]),
            },
        )
        os.makedirs(config.output_dir, exist_ok=True)
        html_path = f"{config.output_dir}/{strategy_meta.cls.__name__}.html"
        bt_plot = FractionalBacktest(
            data,
            strategy_meta.cls,
            cash=config.cash,
            commission=config.cost.commission_rate(),
            margin=config.margin,
            finalize_trades=config.finalize_trades,
            trade_on_close=config.trade_on_close if config.trade_on_close is not None else (not config.cost.realism_mode),
            exclusive_orders=config.exclusive_orders,
        )
        bt_plot.run()
        bt_plot.plot(resample=config.resample, filename=html_path)
        compare_rows = load_recent_runs(config.experiments_dir, config.strategy, limit=5)
        write_stats_cards_to_html(
            html_path,
            stats,
            strategy_name=strategy_meta.cls.__name__,
            compare_rows=compare_rows,
        )
        print(stats)
        print(f"Artifacts saved: {run_dir}")
    else:
        print(result)


if __name__ == "__main__":
    main()
