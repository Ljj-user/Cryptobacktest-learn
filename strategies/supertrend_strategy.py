from backtesting import Strategy, Backtest
from backtesting.lib import FractionalBacktest
import pandas as pd
import numpy as np
from html import escape
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
import os
from report_utils import write_stats_cards_to_html


def SuperTrend(high, low, close, atr_period=10, multiplier=3.0):
    """标准 SuperTrend（TR/ATR + Final Bands）"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(atr_period, min_periods=atr_period).mean()

    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend = pd.Series(1, index=close.index, dtype=int)
    supertrend = pd.Series(np.nan, index=close.index, dtype=float)

    for i in range(1, len(close)):
        if pd.isna(atr.iloc[i]):
            trend.iloc[i] = trend.iloc[i - 1]
            continue

        if (basic_upper.iloc[i] < final_upper.iloc[i - 1]) or (close.iloc[i - 1] > final_upper.iloc[i - 1]):
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if (basic_lower.iloc[i] > final_lower.iloc[i - 1]) or (close.iloc[i - 1] < final_lower.iloc[i - 1]):
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if trend.iloc[i - 1] == -1 and close.iloc[i] > final_upper.iloc[i]:
            trend.iloc[i] = 1
        elif trend.iloc[i - 1] == 1 and close.iloc[i] < final_lower.iloc[i]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]

        supertrend.iloc[i] = final_lower.iloc[i] if trend.iloc[i] == 1 else final_upper.iloc[i]

    supertrend = supertrend.ffill().bfill()
    return np.array(supertrend, copy=True), np.array(trend, copy=True)


def SuperTrendLine(high, low, close, atr_period=10, multiplier=3.0):
    supertrend, _ = SuperTrend(high, low, close, atr_period, multiplier)
    return np.array(supertrend, copy=True)


def TrendDirection(high, low, close, atr_period=10, multiplier=3.0):
    _, trend = SuperTrend(high, low, close, atr_period, multiplier)
    return np.array(trend, copy=True)


class SuperTrendFuturesStrategy(Strategy):
    atr_period = 10
    multiplier = 3.0
    risk_per_trade = 0.02

    def init(self):
        self.supertrend = self.I(
            SuperTrendLine,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.atr_period,
            self.multiplier,
            name='SuperTrend',
            overlay=True,
            color='#FFB000',
        )
        self.trend = self.I(
            TrendDirection,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.atr_period,
            self.multiplier,
            name='Trend',
            plot=False,
        )

    def next(self):
        price = self.data.Close[-1]
        if not self.position:
            if self.trend[-1] == 1:
                self.buy(size=0.08, sl=price * 0.96)
            elif self.trend[-1] == -1:
                self.sell(size=0.08, sl=price * 1.04)
        else:
            if (self.position.is_long and self.trend[-1] == -1) or \
               (self.position.is_short and self.trend[-1] == 1):
                self.position.close()

