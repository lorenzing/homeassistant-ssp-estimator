"""Synthetic market files cover missing values, units and DST boundaries."""

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from zipfile import ZipFile

package = ModuleType("ssp_market_tests")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components/ssp_estimator")]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location("ssp_market_tests.market", Path(package.__path__[0]) / "market.py")
market = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = market
spec.loader.exec_module(market)
from ssp_market_tests.provinces import PROVINCE_ZONES, province_options, with_province_zone
from ssp_market_tests.valuation import value_hours


def archive(day="20261122", count=96, pun="200,000000", zonal="180,000000"):
    xml = "<NewDataSet>" + "".join(
        f"<Prezzi15><Data>{day}</Data><Mercato>MGP</Mercato><Granularity>PT15</Granularity>"
        f"<Periodo>{period}</Periodo><PUN>{pun}</PUN><NORD>{zonal}</NORD></Prezzi15>"
        for period in range(1, count + 1)) + "</NewDataSet>"
    output = BytesIO()
    with ZipFile(output, "w") as value:
        value.writestr("prices.xml", xml)
    return output.getvalue()


class MarketTests(unittest.TestCase):
    def test_prices_are_converted_to_eur_kwh(self):
        slots = market.parse_prices(archive(), "NORD")
        self.assertEqual(len(slots), 96)
        self.assertEqual((slots[0].pun, slots[0].zonal), (0.2, 0.18))
        self.assertAlmostEqual(market.daily_prices(slots, date(2026, 11, 22))["pun_daily"], 0.2)

    def test_current_slot_boundaries_and_stale_data(self):
        slots = market.parse_prices(archive(), "NORD")
        self.assertIs(market.current_slot(slots, slots[0].start), slots[0])
        self.assertIs(market.current_slot(slots, slots[0].end), slots[1])
        self.assertIsNone(market.current_slot(slots, slots[-1].end))
        self.assertIsNone(market.current_slot(slots, slots[0].start - timedelta(seconds=1)))

    def test_missing_period_does_not_create_daily_average(self):
        slots = market.parse_prices(archive(count=95), "NORD")
        self.assertIsNone(market.daily_prices(slots, date(2026, 11, 22)))

    def test_negative_and_zero_prices_are_valid(self):
        slot = market.parse_prices(archive(pun="-10,000000", zonal="0,000000"), "NORD")[0]
        self.assertEqual((slot.pun, slot.zonal), (-0.01, 0))

    def test_missing_or_nonfinite_price_rejected(self):
        for price in ("", "NaN", "Infinity"):
            with self.subTest(price=price), self.assertRaises(ValueError):
                market.parse_prices(archive(pun=price), "NORD")

    def test_dst_spring_and_autumn_market_days(self):
        for day, count in (("20260329", 92), ("20261025", 100)):
            with self.subTest(day=day):
                slots = market.parse_prices(archive(day=day, count=count), "NORD")
                self.assertEqual(len(slots), count)
                self.assertEqual(len({slot.start for slot in slots}), count)
                self.assertIsNotNone(market.daily_prices(slots, datetime.strptime(day, "%Y%m%d").date()))

    def test_extra_period_on_spring_day_rejected(self):
        with self.assertRaises(ValueError):
            market.parse_prices(archive(day="20260329", count=93), "NORD")

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            market.parse_prices(archive(), "UNKNOWN")


class ProvinceTests(unittest.TestCase):
    def test_territorial_coverage(self):
        self.assertEqual(len(PROVINCE_ZONES), 110)
        self.assertEqual(set(PROVINCE_ZONES.values()), set(market.ZONES))
        self.assertEqual(len(province_options()), 110)

    def test_examples_across_all_market_zones(self):
        for province, zone in {"Ferrara": "NORD", "Firenze": "CNOR", "Napoli": "CSUD",
                               "Bari": "SUD", "Cosenza": "CALA", "Palermo": "SICI",
                               "Gallura Nord-Est Sardegna": "SARD"}.items():
            with self.subTest(province=province):
                self.assertEqual(with_province_zone({"province": province, "zone": "wrong"})["zone"], zone)


class HourlyValuationTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 10, 8, tzinfo=timezone.utc)
        self.end = self.start + timedelta(hours=2)
        self.slots = [market.PriceSlot(self.start + timedelta(minutes=15 * index),
                                      self.start + timedelta(minutes=15 * (index + 1)),
                                      0.1 if index < 4 else 0.3,
                                      0.05 if index < 4 else 0.15) for index in range(8)]
        self.imports = [{"start": self.start.timestamp(), "change": 10},
                        {"start": (self.start + timedelta(hours=1)).timestamp(), "change": 30}]
        self.exports = [{"start": row["start"], "change": row["change"] / 10} for row in self.imports]

    def test_weights_each_flow_with_the_price_of_the_same_hour(self):
        result = value_hours(self.imports, self.exports, self.slots, self.start, self.end)
        self.assertEqual(result["oe"], 10)
        self.assertAlmostEqual(result["cei"], 0.5)
        self.assertEqual(result["imported_kwh"], 40)
        self.assertEqual(result["exchanged_kwh"], 4)
        self.assertTrue(result["within_hour_profile_unknown"])

    def test_missing_price_is_not_replaced_with_zero(self):
        with self.assertRaises(ValueError):
            value_hours(self.imports, self.exports, self.slots[:-1], self.start, self.end)

    def test_missing_energy_is_not_replaced_with_zero(self):
        with self.assertRaises(ValueError):
            value_hours(self.imports[:-1], self.exports, self.slots, self.start, self.end)

    def test_negative_correction_is_not_counted_as_income(self):
        self.imports[0]["change"] = -1
        with self.assertRaises(ValueError):
            value_hours(self.imports, self.exports, self.slots, self.start, self.end)

    def test_duplicate_intervals_are_rejected(self):
        with self.assertRaises(ValueError):
            value_hours(self.imports + self.imports[:1], self.exports, self.slots, self.start, self.end)

    def test_first_hour_can_start_at_meter_creation(self):
        result = value_hours(self.imports, self.exports, self.slots,
                             self.start + timedelta(minutes=12), self.end)
        self.assertEqual(result["oe"], 10)
        self.assertEqual(result["priced_period_start"], (self.start + timedelta(minutes=12)).isoformat())


if __name__ == "__main__":
    unittest.main()
