from dataclasses import dataclass
from typing import Dict, Type

from backtesting import Strategy

from strategies.dca_rsi_strategy import DCARsiStrategy
from strategies.dca_strategy import DCAStrategy
from strategies.donchian_trend_long_strategy import DonchianTrendLongStrategy
from strategies.ema_adx_strategy import EMA_ADX_Strategy
from strategies.intraday_seasonality_btc_strategy import IntradaySeasonalityBTCStrategy
from strategies.low_drawdown_trend_strategy import LowDrawdownTrendStrategy
from strategies.rsi_strategy import RSIFuturesStrategy
from strategies.supertrend_strategy import SuperTrendFuturesStrategy


@dataclass(frozen=True)
class StrategyMeta:
    key: str
    cls: Type[Strategy]
    display_name: str
    description: str


STRATEGY_REGISTRY: Dict[str, StrategyMeta] = {
    "ema_adx": StrategyMeta(
        key="ema_adx",
        cls=EMA_ADX_Strategy,
        display_name="EMA + ADX 趋势策略",
        description="EMA 金叉/死叉 + ADX 趋势强度过滤",
    ),
    "rsi": StrategyMeta(
        key="rsi",
        cls=RSIFuturesStrategy,
        display_name="RSI 策略",
        description="RSI 超买超卖反转",
    ),
    "intraday_seasonality_btc": StrategyMeta(
        key="intraday_seasonality_btc",
        cls=IntradaySeasonalityBTCStrategy,
        display_name="BTC 日内季节性（22:00 开多，00:00 平）",
        description="按 UTC 小时窗口做 2 小时隔夜多头",
    ),
    "supertrend": StrategyMeta(
        key="supertrend",
        cls=SuperTrendFuturesStrategy,
        display_name="SuperTrend 策略",
        description="SuperTrend 趋势跟随",
    ),
    "dca_time": StrategyMeta(
        key="dca_time",
        cls=DCAStrategy,
        display_name="定投策略（时间间隔）",
        description="按固定周期分批加仓",
    ),
    "dca_rsi": StrategyMeta(
        key="dca_rsi",
        cls=DCARsiStrategy,
        display_name="定投策略（RSI 触发变种）",
        description="RSI 极值触发分批加仓",
    ),
    "low_drawdown_trend": StrategyMeta(
        key="low_drawdown_trend",
        cls=LowDrawdownTrendStrategy,
        display_name="低回撤趋势策略（EMA200 + ATR 风控）",
        description="只做多 + 趋势过滤 + ATR 风控",
    ),
    "donchian_long": StrategyMeta(
        key="donchian_long",
        cls=DonchianTrendLongStrategy,
        display_name="Donchian 突破趋势（只做多，小亏大赚）",
        description="通道突破入场 + ATR 追踪止损 + 金字塔加仓",
    ),
}


def get_strategy_meta(strategy_key: str) -> StrategyMeta:
    if strategy_key not in STRATEGY_REGISTRY:
        valid = ", ".join(sorted(STRATEGY_REGISTRY))
        raise ValueError(f"未知策略: {strategy_key}. 可选: {valid}")
    return STRATEGY_REGISTRY[strategy_key]


def list_strategy_keys():
    return sorted(STRATEGY_REGISTRY.keys())
