import os

from backtesting.lib import FractionalBacktest

from backtest_engine import load_ohlcv_data, run_backtest
from config import BacktestConfig
from experiment_tracker import append_run_index, create_run_dir, load_recent_runs, save_run_artifacts
from report_utils import write_stats_cards_to_html
from strategy_registry import get_strategy_meta

def print_chinese_stats(stats):
    metric_map = {
        'Start': '开始时间',
        'End': '结束时间',
        'Duration': '回测周期',
        'Exposure Time [%]': '持仓时间占比[%]',
        'Equity Final [$]': '最终权益[$]',
        'Equity Peak [$]': '权益峰值[$]',
        'Commissions [$]': '总手续费[$]',
        'Est. Slippage [$]': '估算滑点成本[$]',
        'Est. Funding [$]': '估算资金费率成本[$]',
        'Est. Extra Costs [$]': '估算额外成本[$]',
        'Capital Utilization [%]': '资金使用率[%]',
        'Margin Utilization [%]': '保证金占用率[%]',
        'Return [%]': '策略收益率[%]',
        'Realism-Adjusted Return [%]': '实盘修正收益率[%]',
        'Buy & Hold Return [%]': '买入持有收益率[%]',
        'Return (Ann.) [%]': '年化收益率[%]',
        'Volatility (Ann.) [%]': '年化波动率[%]',
        'CAGR [%]': '复合年增长率[%]',
        'Sharpe Ratio': '夏普比率',
        'Sortino Ratio': '索提诺比率',
        'Calmar Ratio': '卡玛比率',
        'Alpha [%]': 'Alpha[%]',
        'Beta': 'Beta',
        'Max. Drawdown [%]': '最大回撤[%]',
        'Avg. Drawdown [%]': '平均回撤[%]',
        'Max. Drawdown Duration': '最大回撤持续时间',
        'Avg. Drawdown Duration': '平均回撤持续时间',
        '# Trades': '交易次数',
        'Win Rate [%]': '胜率[%]',
        'Best Trade [%]': '单笔最大收益[%]',
        'Worst Trade [%]': '单笔最大亏损[%]',
        'Avg. Trade [%]': '单笔平均收益[%]',
        'Max. Trade Duration': '最长持仓时间',
        'Avg. Trade Duration': '平均持仓时间',
        'Profit Factor': '盈亏比(Profit Factor)',
        'Expectancy [%]': '期望收益[%]',
        'SQN': '系统质量指数(SQN)',
        'Kelly Criterion': '凯利公式值',
    }

    print("\n===== 中文回测指标 =====")
    for key, zh_key in metric_map.items():
        if key in stats:
            print(f"{zh_key}: {stats[key]}")

def main():
    config = BacktestConfig()
    strategy_meta = get_strategy_meta(config.strategy)
    data = load_ohlcv_data(config.data_path)
    print("修正后的列名：", data.columns.tolist())
    print(data.head(3))

    result = run_backtest(data, config)
    if result["mode"] != "single":
        print(f"当前模式: {result['mode']}")
        if result["mode"] == "split":
            print("\n===== 训练集指标 =====")
            print(result["train_stats"])
            print("\n===== 测试集指标 =====")
            print(result["test_stats"])
        else:
            print(result.get("walk_forward_summary", {}))
        return

    stats = result["stats"]
    trades = result["trades"]
    equity_curve = result["equity_curve"]

    print(f"当前策略: {strategy_meta.cls.__name__}")
    print(stats)
    print_chinese_stats(stats)

    os.makedirs(config.output_dir, exist_ok=True)
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

    output_html = f"{config.output_dir}/{strategy_meta.cls.__name__}.html"
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
    bt_plot.plot(resample=config.resample, filename=output_html)
    compare_rows = load_recent_runs(config.experiments_dir, config.strategy, limit=5)
    write_stats_cards_to_html(
        output_html,
        stats,
        strategy_name=strategy_meta.cls.__name__,
        compare_rows=compare_rows,
    )


if __name__ == "__main__":
    main()