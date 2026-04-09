import unittest

from config import BacktestConfig


class ParamsValidationTest(unittest.TestCase):
    def test_invalid_cash(self):
        cfg = BacktestConfig()
        cfg.cash = -1
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_invalid_margin(self):
        cfg = BacktestConfig()
        cfg.margin = 0
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_invalid_walk_forward(self):
        cfg = BacktestConfig()
        cfg.validation.walk_forward = True
        cfg.validation.wf_test_bars = 0
        with self.assertRaises(ValueError):
            cfg.validate()


if __name__ == "__main__":
    unittest.main()
