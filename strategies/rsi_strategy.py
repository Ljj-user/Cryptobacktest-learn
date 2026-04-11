import pandas as pd
from backtesting import Strategy


def RSI(series, period=14):
    """手动实现 RSI（Backtesting.py 推荐方式）"""
    series = pd.Series(series)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


class RSIFuturesStrategy(Strategy):
    rsi_period = 14
    rsi_lower = 10
    rsi_upper = 90
    risk_per_trade = 0.02

    def init(self):
        self.rsi = self.I(RSI, self.data.Close, self.rsi_period, name="RSI")
        self.equity_peak = self.equity

    def next(self):
        price = self.data.Close[-1]
        if not self.position:
            if self.rsi[-1] < self.rsi_lower:
                sl = price * 0.992
                tp = price * 1.015
                self.buy(size=0.18, sl=sl, tp=tp)
            elif self.rsi[-1] > self.rsi_upper:
                sl = price * 1.015
                tp = price * 0.97
                self.sell(size=0.18, sl=sl, tp=tp)
        else:
            if (self.position.is_long and self.rsi[-1] > self.rsi_upper) or (
                self.position.is_short and self.rsi[-1] < self.rsi_lower
            ):
                self.position.close()
