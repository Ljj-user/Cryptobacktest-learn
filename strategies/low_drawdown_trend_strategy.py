import numpy as np
import pandas as pd
from backtesting import Strategy


def EMA(series, period):
    return np.array(pd.Series(series).ewm(span=period, adjust=False).mean().to_numpy(), copy=True)


def RSI(series, period=14):
    s = pd.Series(series, dtype=float)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean().replace(0, np.nan)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return np.array(rsi.fillna(50).to_numpy(), copy=True)


def ATR(high, low, close, period=14):
    h = pd.Series(high, dtype=float)
    low_s = pd.Series(low, dtype=float)
    c = pd.Series(close, dtype=float)
    prev_close = c.shift(1)
    tr = pd.concat(
        [(h - low_s).abs(), (h - prev_close).abs(), (low_s - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return np.array(atr.bfill().to_numpy(), copy=True)


class LowDrawdownTrendStrategy(Strategy):
    # --- trend/pullback filters ---
    ema_fast_period = 50
    ema_slow_period = 200
    rsi_period = 14
    rsi_entry = 30
    rsi_exit = 60

    # --- position management ---
    base_allocation = 0.09
    max_total_allocation = 0.42

    # --- risk management ---
    atr_period = 14
    stop_atr_mult = 1.8
    trail_atr_mult = 1.6
    take_profit_pct = 2.8
    stop_loss_pct = -3.2
    cooldown_bars = 18
    equity_drawdown_pause_pct = 4.0
    pause_bars = 72

    def init(self):
        self.ema_fast = self.I(EMA, self.data.Close, self.ema_fast_period, name="EMA50")
        self.ema_slow = self.I(EMA, self.data.Close, self.ema_slow_period, name="EMA200")
        self.rsi = self.I(RSI, self.data.Close, self.rsi_period, name="RSI")
        self.atr = self.I(
            ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period, name="ATR"
        )

        self.dynamic_stop = np.nan
        self.last_exit_bar = -(10**9)
        self.pause_until_bar = -1
        self.equity_peak = self.equity

    def _reset_cycle(self, bar_idx):
        self.dynamic_stop = np.nan
        self.last_exit_bar = bar_idx

    def _current_notional(self, price):
        return abs(self.position.size) * price if self.position else 0.0

    def _can_trade(self, bar_idx):
        if bar_idx <= self.pause_until_bar:
            return False
        if bar_idx - self.last_exit_bar < self.cooldown_bars:
            return False
        return True

    def _update_equity_guard(self, bar_idx):
        self.equity_peak = max(self.equity_peak, self.equity)
        dd_pct = (1 - self.equity / self.equity_peak) * 100 if self.equity_peak > 0 else 0
        if dd_pct >= self.equity_drawdown_pause_pct:
            self.pause_until_bar = max(self.pause_until_bar, bar_idx + self.pause_bars)

    def next(self):
        bar_idx = len(self.data.Close) - 1
        price = float(self.data.Close[-1])
        atr_now = float(self.atr[-1]) if np.isfinite(self.atr[-1]) else 0.0
        if price <= 0 or self.equity <= 0 or atr_now <= 0:
            return

        self._update_equity_guard(bar_idx)

        trend_up = float(self.ema_fast[-1]) > float(self.ema_slow[-1]) and price > float(
            self.ema_slow[-1]
        )
        pullback_long = float(self.rsi[-1]) <= self.rsi_entry and price < float(self.ema_fast[-1])

        if self.position and self.position.is_long:
            hard_stop = price <= self.dynamic_stop if np.isfinite(self.dynamic_stop) else False
            take_profit = float(self.position.pl_pct) >= self.take_profit_pct
            mean_revert_exit = float(self.rsi[-1]) >= self.rsi_exit and price >= float(
                self.ema_fast[-1]
            )
            stop_loss = float(self.position.pl_pct) <= self.stop_loss_pct
            if hard_stop or stop_loss or take_profit or mean_revert_exit or (not trend_up):
                self.position.close()
                self._reset_cycle(bar_idx)
                return

            trail_candidate = price - atr_now * self.trail_atr_mult
            if not np.isfinite(self.dynamic_stop):
                self.dynamic_stop = trail_candidate
            else:
                self.dynamic_stop = max(self.dynamic_stop, trail_candidate)
            return

        if not self._can_trade(bar_idx):
            return

        if trend_up and pullback_long:
            current_alloc = self._current_notional(price) / self.equity
            remain = self.max_total_allocation - current_alloc
            init_size = min(self.base_allocation, remain)
            if init_size > 0:
                self.buy(size=init_size)
                self.dynamic_stop = price - atr_now * self.stop_atr_mult
