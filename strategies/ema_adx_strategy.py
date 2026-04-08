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
    adx_threshold = 25
    size_percent = 0.10

    def init(self):
        self.ema_fast = self.I(EMA, self.data.Close, self.fast_ema, name='EMA Fast')
        self.ema_slow = self.I(EMA, self.data.Close, self.slow_ema, name='EMA Slow')
        self.adx = self.I(ADX, self.data.High, self.data.Low, self.data.Close, name='ADX')

    def next(self):
        price = self.data.Close[-1]

        if not self.position:
            if self.adx[-1] > self.adx_threshold and self.ema_fast[-1] > self.ema_slow[-1]:
                self.buy(size=self.size_percent, sl=price * 0.99)
            elif self.adx[-1] > self.adx_threshold and self.ema_fast[-1] < self.ema_slow[-1]:
                self.sell(size=self.size_percent, sl=price * 1.01)
        else:
            if (self.position.is_long and self.ema_fast[-1] < self.ema_slow[-1]) or \
               (self.position.is_short and self.ema_fast[-1] > self.ema_slow[-1]):
                self.position.close()

