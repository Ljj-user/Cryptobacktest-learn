import numpy as np
import pandas as pd
from backtesting import Strategy


def DonchianHigh(series, period: int):
    s = pd.Series(series, dtype=float)
    return np.array(
        s.rolling(window=period, min_periods=period).max().shift(1).bfill().to_numpy(), copy=True
    )


def DonchianLow(series, period: int):
    s = pd.Series(series, dtype=float)
    return np.array(
        s.rolling(window=period, min_periods=period).min().shift(1).bfill().to_numpy(), copy=True
    )


def ATR(high, low, close, period: int = 14):
    h = pd.Series(high, dtype=float)
    low_s = pd.Series(low, dtype=float)
    c = pd.Series(close, dtype=float)
    prev_close = c.shift(1)
    tr = pd.concat(
        [(h - low_s).abs(), (h - prev_close).abs(), (low_s - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return np.array(atr.bfill().to_numpy(), copy=True)


class DonchianTrendLongStrategy(Strategy):
    """
    低胜率/高盈亏比的经典趋势突破模型（只做多）：
    - 入场：突破过去 N 根K线最高价（Donchian 上轨）
    - 止损：ATR * k（随 ATR 动态更新为追踪止损）
    - 出场：跌破 Donchian 下轨 或 追踪止损触发
    """

    entry_period = 55
    exit_period = 20
    atr_period = 14
    stop_atr_mult = 2.5
    trail_atr_mult = 2.0

    base_allocation = 0.20
    max_total_allocation = 0.58
    pyramid_add_allocation = 0.12
    pyramid_add_every_atr = 1.0
    max_adds = 4

    def init(self):
        self.dc_high = self.I(DonchianHigh, self.data.High, self.entry_period, name="DonchianHigh")
        self.dc_low = self.I(DonchianLow, self.data.Low, self.exit_period, name="DonchianLow")
        self.atr = self.I(
            ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period, name="ATR"
        )
        self.dynamic_stop = np.nan
        self.last_add_price = np.nan
        self.add_count = 0

    def _reset_cycle(self):
        self.dynamic_stop = np.nan
        self.last_add_price = np.nan
        self.add_count = 0

    def next(self):
        price = float(self.data.Close[-1])
        atr_now = float(self.atr[-1]) if np.isfinite(self.atr[-1]) else 0.0
        if price <= 0 or self.equity <= 0 or atr_now <= 0:
            return

        # 出场逻辑：下轨止损 或 ATR 追踪止损
        if self.position and self.position.is_long:
            # 更新追踪止损：只上移不下移
            trail_candidate = price - atr_now * self.trail_atr_mult
            if not np.isfinite(self.dynamic_stop):
                self.dynamic_stop = trail_candidate
            else:
                self.dynamic_stop = max(self.dynamic_stop, trail_candidate)

            exit_break = price < float(self.dc_low[-1])
            exit_stop = np.isfinite(self.dynamic_stop) and price <= self.dynamic_stop
            if exit_break or exit_stop:
                self.position.close()
                self._reset_cycle()
                return

            # 趋势加仓（金字塔）：每上涨 1 ATR 加一次
            if self.add_count < self.max_adds:
                if not np.isfinite(self.last_add_price):
                    self.last_add_price = self.position.entry_price
                if price >= self.last_add_price + atr_now * self.pyramid_add_every_atr:
                    current_alloc = (abs(self.position.size) * price) / self.equity
                    remain = self.max_total_allocation - current_alloc
                    add_size = min(self.pyramid_add_allocation, remain)
                    if add_size > 0:
                        self.buy(size=add_size)
                        self.add_count += 1
                        self.last_add_price = price
            return

        # 入场逻辑：突破上轨开多
        breakout = price > float(self.dc_high[-1])
        if breakout:
            size = min(self.base_allocation, self.max_total_allocation)
            if size <= 0:
                return
            self.buy(size=size)
            # 初始止损
            self.dynamic_stop = price - atr_now * self.stop_atr_mult
            self.last_add_price = price
            self.add_count = 0
