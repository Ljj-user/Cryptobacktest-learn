import unittest

from strategy_registry import STRATEGY_REGISTRY, get_strategy_meta, list_strategy_keys


class StrategyRegistryTest(unittest.TestCase):
    def test_registry_not_empty(self):
        self.assertGreater(len(STRATEGY_REGISTRY), 0)

    def test_registry_roundtrip(self):
        for key in list_strategy_keys():
            meta = get_strategy_meta(key)
            self.assertEqual(meta.key, key)
            self.assertTrue(callable(meta.cls))

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            get_strategy_meta("not_exists")


if __name__ == "__main__":
    unittest.main()
