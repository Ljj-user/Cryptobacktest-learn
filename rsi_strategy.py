# 策略代码（核心）

from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import pandas as pd
import numpy as np

def RSI(series, period=14):
    """手动实现 RSI（Backtesting.py 推荐方式）"""
    # Backtesting 传入的是内部数组类型，先转为 pandas.Series 再做 diff/rolling
    series = pd.Series(series)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

class RSIFuturesStrategy(Strategy):
    rsi_period = 14
    rsi_lower = 10   # 超卖阈值
    rsi_upper = 90   # 超买阈值
    risk_per_trade = 0.02  # 单笔风险 2% 本金（可调）
    
    def init(self):
        self.rsi = self.I(RSI, self.data.Close, self.rsi_period, name='RSI')
        self.equity_peak = self.equity  # 用于跟踪最大权益
    
    def next(self):
        price = self.data.Close[-1]
        # 仓位大小控制（模拟杠杆效果，实际回测中通过 risk_per_trade 控制）
        if not self.position:
            # 开仓
            if self.rsi[-1] < self.rsi_lower:   # 超卖 → 多单
                sl = price * 0.992  # 0.5% 止损
                tp = price * 1.015   # 1.5% 止盈（盈亏比约 2:1）
                self.buy(size=0.1, sl=sl, tp=tp)  # size 可动态调整
                
            elif self.rsi[-1] > self.rsi_upper:  # 超买 → 空单
                sl = price * 1.015
                tp = price * 0.97
                self.sell(size=0.1, sl=sl, tp=tp)
                
        else:
            # 已有仓位，反向信号平仓
            if (self.position.is_long and self.rsi[-1] > self.rsi_upper) or \
               (self.position.is_short and self.rsi[-1] < self.rsi_lower):
                self.position.close()

# 如果你想直接运行测试，可在这里加
if __name__ == "__main__":
    data = pd.read_csv('data/btc_futures_1h.csv', parse_dates=True, index_col='timestamp')
    bt = Backtest(data, RSIFuturesStrategy, cash=10000, commission=0.0004,  # 币安合约手续费约 0.04%
                  trade_on_close=True, exclusive_orders=True)
    stats = bt.run()
    print(stats)
    bt.plot()