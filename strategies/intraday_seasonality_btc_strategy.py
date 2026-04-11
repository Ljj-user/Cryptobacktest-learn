from backtesting import Strategy


class IntradaySeasonalityBTCStrategy(Strategy):
    """
    Quantpedia intraday seasonality idea (adapted to this repo):
    - Open long at 22:00 UTC
    - Close at 00:00 UTC (hold ~2 hours on 1H bars)
    """

    open_trade_hour = 22
    close_trade_hour = 0
    # backtesting.py: size in (0,1) means fraction of available equity
    # Use ~100% allocation to match QC SetHoldings(symbol, 1).
    long_allocation = 0.99

    def init(self):
        pass

    def next(self):
        ts = self.data.index[-1]
        hour = int(ts.hour)
        minute = int(getattr(ts, "minute", 0))

        # Open long at 22:00
        if hour == self.open_trade_hour and minute == 0 and not self.position:
            if self.long_allocation > 0:
                self.buy(size=self.long_allocation)
            return

        # Close at 00:00
        if hour == self.close_trade_hour and minute == 0 and self.position:
            self.position.close()
