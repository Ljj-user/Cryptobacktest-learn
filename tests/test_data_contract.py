import os
import unittest

from backtest_engine import load_ohlcv_data


class DataContractTest(unittest.TestCase):
    def test_ohlcv_contract(self):
        path = "data/btc_futures_1h.csv"
        self.assertTrue(os.path.exists(path))
        data = load_ohlcv_data(path)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            self.assertIn(col, data.columns)
        self.assertTrue(data.index.is_monotonic_increasing)
        self.assertFalse(data.isna().any().any())


if __name__ == "__main__":
    unittest.main()
