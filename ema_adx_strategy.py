from backtesting import Strategy, Backtest
from backtesting.lib import FractionalBacktest
import pandas as pd
import numpy as np
import os
from report_utils import write_stats_cards_to_html

def EMA(series, period):
    values = pd.Series(series).ewm(span=period, adjust=False).mean().to_numpy()
    return np.array(values, copy=True)

def ADX(high, low, close, period=14):
    """标准化 ADX（Wilder 方向性指标）"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0))
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0))

    tr = pd.concat(
        [(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1
    ).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()

    plus_di = 100 * (plus_dm.rolling(period, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period, min_periods=period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(period, min_periods=period).mean().fillna(0)
    return np.array(adx.to_numpy(), copy=True)

class EMA_ADX_Strategy(Strategy):
    fast_ema = 9
    slow_ema = 21
    adx_threshold = 25     # ADX > 25 才认为趋势够强
    size_percent = 0.10    # 每笔使用10%资金
    
    def init(self):
        self.ema_fast = self.I(EMA, self.data.Close, self.fast_ema, name='EMA Fast')
        self.ema_slow = self.I(EMA, self.data.Close, self.slow_ema, name='EMA Slow')
        self.adx = self.I(ADX, self.data.High, self.data.Low, self.data.Close, name='ADX')
    
    def next(self):
        price = self.data.Close[-1]
        
        if not self.position:
            # 趋势够强 + 金叉 → 开多
            if self.adx[-1] > self.adx_threshold and self.ema_fast[-1] > self.ema_slow[-1]:
                self.buy(size=self.size_percent, sl=price * 0.99)   # 1%止损
            
            # 趋势够强 + 死叉 → 开空
            elif self.adx[-1] > self.adx_threshold and self.ema_fast[-1] < self.ema_slow[-1]:
                self.sell(size=self.size_percent, sl=price * 1.01)
                
        else:
            # 反向信号平仓（可改成趋势反转再平）
            if (self.position.is_long and self.ema_fast[-1] < self.ema_slow[-1]) or \
               (self.position.is_short and self.ema_fast[-1] > self.ema_slow[-1]):
                self.position.close()

# ====================== 运行部分 ======================
if __name__ == "__main__":
    data = pd.read_csv('data/btc_futures_1h.csv', parse_dates=True, index_col='timestamp')
    data = data.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'})
    
    bt = FractionalBacktest(data, EMA_ADX_Strategy,
                  cash=10000,
                  commission=0.0002,
                  margin=0.2,           # 5倍杠杆
                  finalize_trades=True,
                  trade_on_close=True,
                  exclusive_orders=True)
    
    stats = bt.run()
    print(stats)
    os.makedirs('charts', exist_ok=True)
    output_html = 'charts/EMA_ADX_Strategy.html'
    bt.plot(resample='4h', filename=output_html)
    write_stats_cards_to_html(output_html, stats)