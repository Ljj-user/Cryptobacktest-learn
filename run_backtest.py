from strategies.ema_adx_strategy import EMA_ADX_Strategy as StrategyClass
# 切换策略时，只需改上面这一行，例如：
# from strategies.rsi_strategy import RSIFuturesStrategy as StrategyClass
# from strategies.supertrend_strategy import SuperTrendFuturesStrategy as StrategyClass
# from strategies.ema_adx_strategy import EMA_ADX_Strategy as StrategyClass
from backtesting.lib import FractionalBacktest
import pandas as pd
import os
from report_utils import write_stats_cards_to_html

def print_chinese_stats(stats):
    metric_map = {
        'Start': '开始时间',
        'End': '结束时间',
        'Duration': '回测周期',
        'Exposure Time [%]': '持仓时间占比[%]',
        'Equity Final [$]': '最终权益[$]',
        'Equity Peak [$]': '权益峰值[$]',
        'Commissions [$]': '总手续费[$]',
        'Return [%]': '策略收益率[%]',
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
              cash=10000,           
              commission=0.0002,    
              margin=0.2,           # 模拟5倍杠杆
              finalize_trades=True,  # 回测结束时强制平掉未平仓单并计入统计
              trade_on_close=True,
              exclusive_orders=True)

stats = bt.run()
print(f"当前策略: {StrategyClass.__name__}")
print(stats)
print_chinese_stats(stats)
os.makedirs('charts', exist_ok=True)
output_html = f"charts/{StrategyClass.__name__}.html"
bt.plot(resample='4h', filename=output_html)
write_stats_cards_to_html(output_html, stats)