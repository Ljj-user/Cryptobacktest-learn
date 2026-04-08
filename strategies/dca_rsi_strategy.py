from backtesting import Strategy
import pandas as pd
import numpy as np


def RSI(series, period=14):
    series = pd.Series(series)
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return np.array(rsi.fillna(50).to_numpy(), copy=True)


def EMA(series, period):
    return np.array(pd.Series(series).ewm(span=period, adjust=False).mean().to_numpy(), copy=True)


class DCARsiStrategy(Strategy):
    # ================== 可调参数 ==================
    rsi_period = 14
    long_entry_rsi = 22           # 放宽后区间: 20~25（默认22）
    short_entry_rsi = 82          # 放宽后区间: 80~85（仅保留参数，当前禁用空头DCA）
    rsi_exit_long = 55            # 多头均值回归退出阈值
    rsi_exit_short = 45           # 空头均值回归退出阈值
    dca_usdt = 200.0              # 首次DCA名义仓位(USDT)
    dca_scale = 1.2               # 每次加仓按1.2x递增
    max_dca_orders = 20           # 单个持仓周期最多加仓次数
    max_total_allocation = 0.8    # 总目标仓位上限（占权益比例）
    max_single_allocation = 0.10  # 单次下单上限（占权益比例）
    min_order_value = 10.0        # 过小订单忽略，避免无效交易
    take_profit_pct = 4           # 更激进：浮盈4%就止盈
    stop_loss_pct = -5            # 更激进：浮亏5%就止损
    trailing_stop_pct = 3         # 更激进：从峰值回撤3%则离场
    cooldown_bars = 12            # 平仓后冷却，降低重复打脸
    ema_fast_period = 50          # 趋势过滤快线
    ema_slow_period = 200         # 趋势过滤慢线（EMA200）
    adx_period = 14               # 趋势强度过滤
    adx_min = 18                  # ADX过低时不做反转DCA
    # ============================================

    def init(self):
        self.rsi = self.I(RSI, self.data.Close, self.rsi_period, name="RSI")
        self.ema_fast = self.I(EMA, self.data.Close, self.ema_fast_period, name="EMA Fast")
        self.ema_slow = self.I(EMA, self.data.Close, self.ema_slow_period, name="EMA Slow")
        self.dca_count = 0
        self.cycle_side = 0  # 1=long cycle, -1=short cycle, 0=idle
        self.last_exit_bar = -10**9
        self.peak_pl_pct = -np.inf

    def _reset_cycle(self) -> None:
        self.dca_count = 0
        self.cycle_side = 0
        self.peak_pl_pct = -np.inf
        self.last_exit_bar = len(self.data.Close) - 1

    def _adx(self) -> float:
        i = len(self.data.Close) - 1
        if i < self.adx_period + 1:
            return 0.0
        high = pd.Series(self.data.High[: i + 1], dtype=float)
        low = pd.Series(self.data.Low[: i + 1], dtype=float)
        close = pd.Series(self.data.Close[: i + 1], dtype=float)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0))
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0))
        tr = pd.concat(
            [(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.adx_period, min_periods=self.adx_period).mean()
        plus_di = 100 * (plus_dm.rolling(self.adx_period, min_periods=self.adx_period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(self.adx_period, min_periods=self.adx_period).mean() / atr)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.rolling(self.adx_period, min_periods=self.adx_period).mean().fillna(0)
        return float(adx.iloc[-1]) if len(adx) else 0.0

    def _add_position(self, side: int, price: float) -> None:
        current_notional = abs(self.position.size) * price if self.position else 0.0
        max_notional = self.equity * self.max_total_allocation
        next_add = self.dca_usdt * (self.dca_scale ** self.dca_count)
        remaining_capacity = max_notional - current_notional
        add_notional = min(next_add, remaining_capacity)
        if add_notional < self.min_order_value:
            return

        size = min(add_notional / self.equity, self.max_single_allocation)
        if size <= 0:
            return

        if side == 1:
            self.buy(size=size)
        else:
            self.sell(size=size)
        self.dca_count += 1
        self.cycle_side = side

    def next(self):
        price = float(self.data.Close[-1])
        if price <= 0 or self.equity <= 0:
            return

        rsi_now = float(self.rsi[-1])
        long_signal = rsi_now < self.long_entry_rsi
        long_trend_ok = float(self.ema_fast[-1]) > float(self.ema_slow[-1])
        price_above_ema200 = price > float(self.ema_slow[-1])
        strong_trend = self._adx() >= self.adx_min
        bar_idx = len(self.data.Close) - 1

        # 风控优先：浮盈/浮亏触发后平仓，重置下一轮DCA
        if self.position:
            self.peak_pl_pct = max(self.peak_pl_pct, float(self.position.pl_pct))
            trailing_triggered = (self.peak_pl_pct - float(self.position.pl_pct)) >= self.trailing_stop_pct
            if self.position.pl_pct >= self.take_profit_pct or self.position.pl_pct <= self.stop_loss_pct:
                self.position.close()
                self._reset_cycle()
                return
            if trailing_triggered:
                self.position.close()
                self._reset_cycle()
                return

            # 均值回归式退出：到达中性区就落袋
            if self.position.is_long and rsi_now >= self.rsi_exit_long:
                self.position.close()
                self._reset_cycle()
                return
            if self.position.is_short and rsi_now <= self.rsi_exit_short:
                self.position.close()
                self._reset_cycle()
                return

        # 信号反向时平仓并切换周期方向
        if self.position:
            if self.position.is_short and long_signal:
                self.position.close()
                self._reset_cycle()

        if self.dca_count >= self.max_dca_orders:
            return
        if bar_idx - self.last_exit_bar < self.cooldown_bars:
            return

        # 过滤弱趋势与逆势方向，减少“抄底抄顶被趋势碾压”
        if long_signal and self.cycle_side in (0, 1) and long_trend_ok and price_above_ema200 and strong_trend:
            self._add_position(side=1, price=price)
        # 按要求禁用空头DCA：不再执行 short_signal 开仓
