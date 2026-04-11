# 回测假设与结果可信度说明

本文说明本仓库默认引擎（`backtesting.py` 的 `FractionalBacktest` + [`backtest_engine.py`](../backtest_engine.py)）的假设、成本口径与**不宜**直接当作实盘收益预期的情形。

## 1. 数据与成交

- **输入**：OHLCV K 线（常用 `1h`）。无订单簿、无逐笔成交。
- **成交时点**：未显式指定 `trade_on_close` 时，在 `realism_mode=True` 下默认为 **不在当前 K 收盘价瞬时成交**（`trade_on_close=False`），具体撮合顺序以 `backtesting.py` 文档为准。请勿与「信号在同一根 K 的收盘价成交」混为一谈。
- **策略侧**：策略在 `next()` 中通常使用当前已闭合或可访问的价位；与真实交易所的延迟、拒单、部分成交无关。

## 2. 手续费与「滑点」

- **有效佣金**：在 `realism_mode` 下，`commission = base_commission + slippage_bps_per_side / 10000`（见 [`config.py`](../config.py) `CostConfig.commission_rate()`）。该费率在仿真中随成交从权益中扣除，**已把固定 bps 的滑点假设合并进佣金**。
- **报表中的「估算滑点成本」**（`Est. Slippage [$]`）：按同一 `slippage_bps` 对每笔交易做的 **美元换算展示**，用于直观感受量级；**并未在「实盘修正收益率」中再次扣除**，否则与引擎内已含滑点的佣金重复。
- 因此：**主回测收益 `Return [%]` 已反映「手续费 + bps 滑点」的合并费率**；`Est. Slippage [$]` 与 `Commissions [$]` 不要简单相加后再与 `Return` 对比，避免重复计量。

## 3. 资金费（Funding）

- **仿真内**：`backtesting.py` 默认不在逐根 K 线中按交易所规则扣除永续资金费。
- **事后修正**：`estimate_realism_costs()` 用 **启发式** 估算：持仓跨越的 K 线数量换算为「8h 结算周期」的近似次数，再乘以固定的 `est_funding_rate_8h` 与名义规模。真实资金费随时间、品种、多空方向变化，**该指标仅作粗算**。
- **「实盘修正收益率」**（`Realism-Adjusted Return [%]`）：在最终权益上 **减去上述估算资金费**（见引擎实现）。**不再次减去** `Est. Slippage [$]`。

## 4. 保证金与强平

- `margin` 传入 `FractionalBacktest`，为库内 **简化** 的杠杆/保证金逻辑，**不等于** 某交易所的逐仓/全仓、维持保证金率与强平价格路径。高杠杆、极端行情下，回测可能 **显著乐观或悲观**，需单独验证。

## 5. Walk-forward / 样本外

- 引擎仅按时间切分数据并分别跑回测；**若在训练段调参再于测试段展示收益**，仍可能产生过拟合；防泄漏需在使用流程上自控（文档与代码无法替你完成）。

## 6. 结论怎么用才靠谱

- **适合**：策略逻辑调试、相对排序、参数敏感度、成本假设对比。
- **不适合**：在未补充订单簿级成交、真实资金费序列、强平规则的情况下，将 `Return [%]` 或 `Realism-Adjusted Return [%]` **直接等同** 实盘净收益。

更多依赖与升级注意事项见 [dependency_upgrade_checklist.md](dependency_upgrade_checklist.md)。
