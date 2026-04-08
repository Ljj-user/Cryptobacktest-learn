from strategies.low_drawdown_trend_strategy import LowDrawdownTrendStrategy as StrategyClass
# 切换策略时，只需改上面这一行，例如：
# from strategies.rsi_strategy import RSIFuturesStrategy as StrategyClass
# from strategies.supertrend_strategy import SuperTrendFuturesStrategy as StrategyClass
# from strategies.ema_adx_strategy import EMA_ADX_Strategy as StrategyClass
# from strategies.dca_strategy import DCAStrategy as StrategyClass
# from strategies.dca_rsi_strategy import DCARsiStrategy as StrategyClass
# from strategies.low_drawdown_trend_strategy import LowDrawdownTrendStrategy as StrategyClass
from backtesting.lib import FractionalBacktest
import pandas as pd
import os
from report_utils import write_stats_cards_to_html

REALISM_MODE = True
INITIAL_CASH = 10000.0
BASE_COMMISSION = 0.0002
SLIPPAGE_BPS_PER_SIDE = 3.0        # 单边滑点(bps)
EST_FUNDING_RATE_8H = 0.0001       # 8小时资金费率估计（0.01%）


def calculate_capital_utilization(stats, data, initial_cash=10000.0):
    """
    资金使用率 = 历史最大持仓名义价值 / 初始资金 * 100
    """
    trades = stats.get('_trades', None)
    if trades is None or len(trades) == 0 or initial_cash <= 0:
        return 0.0

    n = len(data)
    pos_diff = [0.0] * (n + 1)
    for _, tr in trades.iterrows():
        entry_bar = int(tr['EntryBar'])
        exit_bar = int(tr['ExitBar'])
        size = float(tr['Size'])
        if entry_bar < 0 or entry_bar >= n:
            continue
        exit_bar = max(entry_bar, min(exit_bar, n - 1))
        pos_diff[entry_bar] += size
        if exit_bar + 1 < len(pos_diff):
            pos_diff[exit_bar + 1] -= size

    running_size = 0.0
    max_notional = 0.0
    closes = data['Close'].to_numpy()
    for i in range(n):
        running_size += pos_diff[i]
        notional = abs(running_size) * float(closes[i])
        if notional > max_notional:
            max_notional = notional

    return (max_notional / float(initial_cash)) * 100.0


def calculate_margin_utilization(stats, data, margin=0.2):
    """
    保证金占用率[%] = 历史最大(名义仓位 * margin / 当时权益) * 100
    """
    trades = stats.get('_trades', None)
    equity_curve = stats.get('_equity_curve', None)
    if trades is None or len(trades) == 0 or equity_curve is None or len(equity_curve) == 0:
        return 0.0

    n = len(data)
    pos_diff = [0.0] * (n + 1)
    for _, tr in trades.iterrows():
        entry_bar = int(tr['EntryBar'])
        exit_bar = int(tr['ExitBar'])
        size = float(tr['Size'])
        if entry_bar < 0 or entry_bar >= n:
            continue
        exit_bar = max(entry_bar, min(exit_bar, n - 1))
        pos_diff[entry_bar] += size
        if exit_bar + 1 < len(pos_diff):
            pos_diff[exit_bar + 1] -= size

    closes = data['Close'].to_numpy()
    equities = equity_curve['Equity'].to_numpy()
    running_size = 0.0
    max_ratio = 0.0
    for i in range(min(n, len(equities))):
        running_size += pos_diff[i]
        equity_now = float(equities[i])
        if equity_now <= 0:
            continue
        notional = abs(running_size) * float(closes[i])
        ratio = (notional * margin) / equity_now
        if ratio > max_ratio:
            max_ratio = ratio

    return max_ratio * 100.0


def estimate_realism_costs(stats, data):
    """
    估算更贴近实盘的成本拆分：
    - 滑点成本：用于展示（已通过commission并入回测）
    - Funding成本：回测引擎未原生扣减，作为额外成本单独扣减
    """
    trades = stats.get('_trades', None)
    if trades is None or len(trades) == 0:
        return 0.0, 0.0, 0.0

    slip_rate = SLIPPAGE_BPS_PER_SIDE / 10000.0
    total_slippage = 0.0
    total_funding = 0.0
    closes = data['Close'].to_numpy()
    n = len(closes)

    for _, tr in trades.iterrows():
        size = abs(float(tr['Size']))
        entry_bar = max(0, min(int(tr['EntryBar']), n - 1))
        exit_bar = max(entry_bar, min(int(tr['ExitBar']), n - 1))
        entry_price = float(tr['EntryPrice'])
        exit_price = float(tr['ExitPrice'])

        # 双边滑点（入场 + 出场）
        entry_notional = size * entry_price
        exit_notional = size * exit_price
        total_slippage += (entry_notional + exit_notional) * slip_rate

        # funding（按持仓bar数折算）
        bars_held = max(1, exit_bar - entry_bar + 1)
        funding_periods = bars_held / 8.0  # 1h K线 => 8小时一档
        avg_price = float(closes[entry_bar:exit_bar + 1].mean()) if exit_bar >= entry_bar else entry_price
        avg_notional = size * avg_price
        total_funding += avg_notional * EST_FUNDING_RATE_8H * funding_periods

    # 注意：slippage 已并入 commission，这里额外成本只扣 funding，避免重复扣减
    total_extra = total_funding
    return total_slippage, total_funding, total_extra


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

# 加载数据并修正列名
data = pd.read_csv('data/btc_futures_1h.csv', parse_dates=True, index_col='timestamp')

# 关键修复：列名改成 Backtesting.py 要求的格式
data = data.rename(columns={
    'open': 'Open',
    'high': 'High',
    'low': 'Low',
    'close': 'Close',
    'volume': 'Volume'
})

print("修正后的列名：", data.columns.tolist())   # 确认一下
print(data.head(3))

# 运行回测（支持小数仓位，更适合 BTC 等高价标的）
bt = FractionalBacktest(data, StrategyClass,
              cash=INITIAL_CASH,
              commission=BASE_COMMISSION + (SLIPPAGE_BPS_PER_SIDE / 10000.0 if REALISM_MODE else 0.0),
              margin=0.2,           # 模拟5倍杠杆
              finalize_trades=True,  # 回测结束时强制平掉未平仓单并计入统计
              trade_on_close=not REALISM_MODE,
              exclusive_orders=True)

stats = bt.run()
stats['Capital Utilization [%]'] = calculate_capital_utilization(stats, data, initial_cash=INITIAL_CASH)
stats['Margin Utilization [%]'] = calculate_margin_utilization(stats, data, margin=0.2)
if REALISM_MODE:
    est_slippage, est_funding, est_extra = estimate_realism_costs(stats, data)
    stats['Est. Slippage [$]'] = est_slippage
    stats['Est. Funding [$]'] = est_funding
    stats['Est. Extra Costs [$]'] = est_extra
    adj_equity = float(stats['Equity Final [$]']) - est_extra
    stats['Realism-Adjusted Return [%]'] = ((adj_equity / INITIAL_CASH) - 1.0) * 100.0
print(f"当前策略: {StrategyClass.__name__}")
print(stats)
print_chinese_stats(stats)
os.makedirs('charts', exist_ok=True)
output_html = f"charts/{StrategyClass.__name__}.html"
bt.plot(resample='4h', filename=output_html)
write_stats_cards_to_html(output_html, stats, strategy_name=StrategyClass.__name__)