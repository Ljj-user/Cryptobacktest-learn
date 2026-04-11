import unittest

from backtest_engine import load_ohlcv_data, run_backtest
from config import BacktestConfig
from strategy_registry import list_strategy_keys


class StrategySmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = load_ohlcv_data("data/btc_futures_1h.csv")
        cls.data = data.iloc[: 24 * 20].copy()

    def test_all_strategies_run(self):
        for key in list_strategy_keys():
            cfg = BacktestConfig(strategy=key)
            cfg.cost.realism_mode = False
            cfg.trade_on_close = True
            result = run_backtest(self.data, cfg)
            self.assertEqual(result["mode"], "single")
            self.assertIn("stats", result)
            self.assertIn("Return [%]", result["stats"])


if __name__ == "__main__":
    unittest.main()
