from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class CostConfig:
    base_commission: float = 0.0002
    slippage_bps_per_side: float = 3.0
    est_funding_rate_8h: float = 0.0001
    realism_mode: bool = True

    def commission_rate(self) -> float:
        if not self.realism_mode:
            return self.base_commission
        return self.base_commission + (self.slippage_bps_per_side / 10000.0)

    def validate(self) -> None:
        if self.base_commission < 0:
            raise ValueError("base_commission 不能为负数")
        if self.slippage_bps_per_side < 0:
            raise ValueError("slippage_bps_per_side 不能为负数")
        if self.est_funding_rate_8h < 0:
            raise ValueError("est_funding_rate_8h 不能为负数")


@dataclass
class ValidationConfig:
    split_date: Optional[str] = None
    walk_forward: bool = False
    wf_train_bars: int = 24 * 120
    wf_test_bars: int = 24 * 30
    wf_step_bars: int = 24 * 30

    def validate(self) -> None:
        if self.split_date:
            datetime.fromisoformat(self.split_date.replace("Z", "+00:00"))
        if self.walk_forward:
            if self.wf_train_bars <= 0 or self.wf_test_bars <= 0 or self.wf_step_bars <= 0:
                raise ValueError("walk-forward bars 参数必须大于0")


@dataclass
class BacktestConfig:
    strategy: str = "low_drawdown_trend"
    data_path: str = "data/btc_futures_1h.csv"
    output_dir: str = "charts"
    experiments_dir: str = "experiments"
    cash: float = 10000.0
    margin: float = 0.2
    trade_on_close: Optional[bool] = None
    finalize_trades: bool = True
    exclusive_orders: bool = True
    resample: str = "4h"
    cost: CostConfig = field(default_factory=CostConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    strategy_overrides: Dict[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        if self.cash <= 0:
            raise ValueError("cash 必须大于0")
        if self.margin <= 0:
            raise ValueError("margin 必须大于0")
        self.cost.validate()
        self.validation.validate()

    def to_dict(self) -> Dict:
        payload = asdict(self)
        payload["effective_trade_on_close"] = (
            self.trade_on_close if self.trade_on_close is not None else (not self.cost.realism_mode)
        )
        payload["effective_commission"] = self.cost.commission_rate()
        return payload
