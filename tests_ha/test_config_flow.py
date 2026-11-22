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


if __name__ == "__main__":
    unittest.main()
