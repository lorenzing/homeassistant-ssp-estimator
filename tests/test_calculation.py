"""Financial invariants and invalid-input tests without Home Assistant installed."""

import importlib.util
from pathlib import Path
import sys
import unittest

path = Path(__file__).parents[1] / "custom_components/ssp_estimator/calculation.py"
spec = importlib.util.spec_from_file_location("ssp_calculation", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class CalculationTests(unittest.TestCase):
    def test_import_more_than_export(self):
        value = module.estimate(3000, 2000, 0.12, 0.10, 0.06)
        self.assertEqual((value.oe, value.cei, value.exchanged_kwh), (360, 200, 2000))
        self.assertEqual(value.contribution, 320)
        self.assertEqual(value.economic_surplus, 0)

    def test_export_more_than_import_and_no_double_counting_surplus(self):
        value = module.estimate(1000, 3000, 0.12, 0.10, 0.06)
        self.assertEqual(value.contribution, 180)
        self.assertEqual(value.economic_surplus, 180)
        self.assertEqual(value.contribution + value.economic_surplus, 360)

    def test_economic_surplus_is_not_physical_surplus(self):
        value = module.estimate(2000, 1000, 0.05, 0.20, 0.06)
        self.assertEqual(value.economic_surplus, 100)

    def test_zero_flows(self):
        self.assertEqual(module.estimate(0, 0, 0.12, 0.10, 0.06).contribution, 0)
        self.assertEqual(module.estimate(0, 1000, 0.12, 0.10, 0.06).economic_surplus, 100)

    def test_negative_market_price_not_silently_clipped(self):
        self.assertEqual(module.estimate(100, 100, 0.1, -0.01, 0).cei, -1)

    def test_missing_nonfinite_boolean_and_negative_energy(self):
        for invalid in (None, "unknown", "unavailable", float("nan"), float("inf"), True, -1):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                module.estimate(invalid, 1, 0.1, 0.1, 0.06)
        with self.assertRaises(ValueError):
            module.estimate(1, 1, 0.1, 0.1, -0.1)

    def test_unit_conversion(self):
        self.assertEqual(module.energy_kwh("1000", "Wh"), 1)
        self.assertEqual(module.energy_kwh("1", "MWh"), 1000)
        for unit in ("W", "EUR", None):
            with self.assertRaises(ValueError):
                module.energy_kwh(100, unit)

    def test_overflow(self):
        with self.assertRaises(ValueError):
            module.estimate(1e308, 1e308, 1e308, 1e308, 1e308)


if __name__ == "__main__":
    unittest.main()
