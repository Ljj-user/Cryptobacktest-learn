from backtesting import Strategy, Backtest
from backtesting.lib import FractionalBacktest
import pandas as pd
import numpy as np

def SuperTrend(high, low, close, atr_period=10, multiplier=3.0):
    """计算 SuperTrend 指标"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    hl2 = (high + low) / 2
    atr = high.rolling(atr_period).max() - low.rolling(atr_period).min()  # 简化 ATR
    atr = atr.rolling(atr_period).mean()  # 更平滑
    
    upper = hl2 + (multiplier * atr)
    lower = hl2 - (multiplier * atr)
    
    # 趋势方向
    trend = pd.Series(1, index=close.index)  # 1 = up, -1 = down
    supertrend = pd.Series(index=close.index, dtype=float)
    
    for i in range(1, len(close)):
        if close.iloc[i - 1] > upper.iloc[i - 1]:
            trend.iloc[i] = 1
        elif close.iloc[i - 1] < lower.iloc[i - 1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]
            
        if trend.iloc[i] == 1:
            supertrend.iloc[i] = max(lower.iloc[i], supertrend.iloc[i - 1] if i > 0 and not pd.isna(supertrend.iloc[i - 1]) else lower.iloc[i])
        else:
            supertrend.iloc[i] = min(upper.iloc[i], supertrend.iloc[i - 1] if i > 0 and not pd.isna(supertrend.iloc[i - 1]) else upper.iloc[i])
    
    return supertrend.to_numpy(), trend.to_numpy()

class SuperTrendFuturesStrategy(Strategy):
    atr_period = 10
    multiplier = 3.0
    risk_per_trade = 0.02  # 单笔风险控制
    
    def init(self):
        self.supertrend, self.trend = self.I(SuperTrend, 
                                             self.data.High, self.data.Low, self.data.Close,
                                             self.atr_period, self.multiplier, 
                                             name='SuperTrend')
    
    def next(self):
        price = self.data.Close[-1]
        
        if not self.position:
            # 开仓
            if self.trend[-1] == 1:   # 上涨趋势 → 多
                self.buy(size=0.08, sl=price * 0.96)   # 约 4% 止损
            elif self.trend[-1] == -1:  # 下跌趋势 → 空
                self.sell(size=0.08, sl=price * 1.04)
                
        else:
            # 趋势反转平仓并反手
            if (self.position.is_long and self.trend[-1] == -1) or \
               (self.position.is_short and self.trend[-1] == 1):
                self.position.close()

# 测试运行
if __name__ == "__main__":
    data = pd.read_csv('data/btc_futures_1h.csv', parse_dates=True, index_col='timestamp')
    data = data.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'})
    
    bt = FractionalBacktest(data, SuperTrendFuturesStrategy,
                  cash=10000, 
                  commission=0.0004, 
                  margin=0.1,          # 10x 杠杆
                  trade_on_close=True,
                  exclusive_orders=True)
    
    stats = bt.run()
    print(stats)
    bt.plot(resample='4h')