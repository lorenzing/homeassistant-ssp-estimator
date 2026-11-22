"""Smoke checks using genuine HA selectors instead of API substitutes."""

import unittest

from custom_components.ssp_estimator.config_flow import _schema


class ConfigurationSchemaTests(unittest.TestCase):
    def test_initial_form_accepts_province_and_precise_prices(self):
        schema = _schema({}, user=True)
        result = schema({"name": "Synthetic installation", "import_energy": "sensor.import",
                         "export_energy": "sensor.export", "province": "Ferrara",
                         "reference_year": 2026, "pun_average": 0.123456,
                         "zonal_average": 0.098765, "cusf": 0.061234})
        self.assertEqual(result["province"], "Ferrara")
        self.assertEqual(result["pun_average"], 0.123456)

    def test_options_form_preserves_precise_values(self):
        defaults = {"province": "Palermo", "reference_year": 2026,
                    "pun_average": 0.123456, "rate_reference": "Synthetic assumptions"}
        self.assertEqual(_schema(defaults)({})["pun_average"], 0.123456)

    def test_automatic_options_need_no_manual_energy_prices(self):
        result = _schema({"province": "Ferrara", "reference_year": 2026})({})
        self.assertEqual(result["energy_price_mode"], "automatic")
        self.assertNotIn("pun_average", result)
        self.assertNotIn("cusf", result)

    def test_existing_manual_configuration_remains_manual(self):
        result = _schema({"province": "Roma", "pun_average": 0.123456})({})
        self.assertEqual(result["energy_price_mode"], "manual")


if __name__ == "__main__":
    unittest.main()
