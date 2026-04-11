from backtesting import Strategy


class DCAStrategy(Strategy):
    # ================== 可调参数 ==================
    dca_interval_bars = 24  # 每隔多少根K线DCA一次（1H数据 -> 24=每天一次）
    dca_usdt = 300.0  # 每次DCA希望增加的名义仓位(USDT)
    max_dca_orders = 40  # 单个持仓周期最多加仓次数
    max_total_allocation = 0.92  # 总目标仓位上限（占权益比例）
    max_single_allocation = 0.17  # 单次下单上限（占权益比例）
    min_order_value = 10.0  # 过小订单忽略，避免无效交易
    take_profit_pct = 8  # 持仓浮盈达到8%平仓并重置DCA
    stop_loss_pct = -12  # 持仓浮亏达到-12%止损并重置DCA
    # ============================================

    def init(self):
        self.bar_count = 0
        self.last_dca_bar = -(10**9)  # 允许第一根就执行DCA
        self.dca_count = 0

    def _reset_cycle(self) -> None:
        """平仓后重置DCA计数，开始下一轮累积。"""
        self.dca_count = 0
        self.last_dca_bar = self.bar_count

    def next(self):
        self.bar_count += 1
        price = float(self.data.Close[-1])
        if price <= 0 or self.equity <= 0:
            return

        # 风控优先：浮盈/浮亏触发后平仓，重置下一轮DCA
        if self.position:
            if (
                self.position.pl_pct >= self.take_profit_pct
                or self.position.pl_pct <= self.stop_loss_pct
            ):
                self.position.close()
                self._reset_cycle()
                return

        # 未到DCA节奏，跳过
        if self.bar_count - self.last_dca_bar < self.dca_interval_bars:
            return

        # 限制单轮最大加仓次数，避免无限叠仓
        if self.dca_count >= self.max_dca_orders:
            return

        # 当前持仓名义价值（USDT）
        current_notional = abs(self.position.size) * price if self.position else 0.0

        # 下一档目标名义价值：每次+ dca_usdt，并受总仓位上限约束
        target_notional = min(
            (self.dca_count + 1) * self.dca_usdt,
            self.equity * self.max_total_allocation,
        )
        add_notional = target_notional - current_notional
        if add_notional < self.min_order_value:
            self.last_dca_bar = self.bar_count
            return

        # FractionalBacktest中 size<1 代表权益比例
        size = min(add_notional / self.equity, self.max_single_allocation)
        if size <= 0:
            self.last_dca_bar = self.bar_count
            return

        self.buy(size=size)
        self.dca_count += 1
        self.last_dca_bar = self.bar_count
