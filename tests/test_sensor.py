"""Adapter checks with API substitutes, not a full Home Assistant integration test."""

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest


def load_adapter():
    modules = {}
    for name in ("homeassistant", "homeassistant.components", "homeassistant.components.sensor",
                 "homeassistant.config_entries", "homeassistant.core", "homeassistant.helpers",
                 "homeassistant.helpers.entity", "homeassistant.helpers.entity_platform", "homeassistant.helpers.entity_registry",
                 "homeassistant.helpers.event", "homeassistant.util", "homeassistant.util.dt"):
        modules[name] = ModuleType(name)
    modules["homeassistant.components.sensor"].SensorEntity = type("SensorEntity", (), {})
    modules["homeassistant.components.sensor"].SensorDeviceClass = SimpleNamespace(ENERGY="energy", MONETARY="monetary")
    modules["homeassistant.config_entries"].ConfigEntry = object
    modules["homeassistant.core"].HomeAssistant = object
    modules["homeassistant.core"].callback = lambda function: function
    modules["homeassistant.helpers.entity"].DeviceInfo = dict
    modules["homeassistant.helpers.entity_registry"].async_get = lambda hass: SimpleNamespace(async_get=lambda entity_id: SimpleNamespace(config_entry_id="source"))
    modules["homeassistant.helpers.entity_platform"].AddConfigEntryEntitiesCallback = object
    modules["homeassistant.helpers.event"].async_track_state_change_event = lambda *args: lambda: None
    modules["homeassistant.helpers.event"].async_track_time_change = lambda *args, **kwargs: lambda: None
    modules["homeassistant.util.dt"].now = lambda: datetime(2026, 11, 10, tzinfo=timezone(timedelta(hours=1)))
    modules["homeassistant.util.dt"].as_local = lambda value: value
    previous = {name: sys.modules.get(name) for name in modules}
    sys.modules.update(modules)
    package = ModuleType("ssp_adapter_tests")
    package.__path__ = [str(Path(__file__).parents[1] / "custom_components/ssp_estimator")]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location("ssp_adapter_tests.sensor", Path(package.__path__[0]) / "sensor.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    for name, value in previous.items():
        if value is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = value
    return adapter


adapter = load_adapter()


class SensorTests(unittest.TestCase):
    def setUp(self):
        self.options = dict(zone="NORD", reference_year=2026, pun_average=0.12,
                            zonal_average=0.10, cusf=0.06, rate_reference="Synthetic test assumptions")
        self.states = {}
        for key, value in (("sensor.import", "3000"), ("sensor.export", "2000")):
            self.states[key] = SimpleNamespace(state=value, attributes=dict(
                unit_of_measurement="kWh", last_reset="2026-01-01T00:00:00+01:00",
                next_reset="2027-01-01T00:00:00+01:00"))
        entry = SimpleNamespace(entry_id="test", title="Test", options=self.options,
                                data={"import_energy": "sensor.import", "export_energy": "sensor.export"})
        self.sensor = adapter.SSPSensor(entry, "contribution", "Test", "EUR")
        self.source_options = {"cycle": "yearly"}
        self.sensor.hass = SimpleNamespace(states=SimpleNamespace(get=self.states.get), config_entries=SimpleNamespace(async_get_entry=lambda entry_id: SimpleNamespace(domain="utility_meter", options=self.source_options)))

    def test_annual_valid(self):
        self.assertTrue(self.sensor.available)
        self.assertEqual(self.sensor.native_value, 320)
        self.assertEqual(self.sensor.extra_state_attributes["status"], "annual_estimate")
        self.assertIsNone(getattr(self.sensor, "_attr_state_class", None))

    def test_missing_rates_are_not_zero_euros(self):
        del self.options["cusf"]
        self.assertFalse(self.sensor.available)
        self.assertIsNone(self.sensor.native_value)
        self.assertEqual(self.sensor._result()[0], "rates_required")

    def test_year_rollover_requires_new_assumptions(self):
        self.options["reference_year"] = 2025
        self.assertEqual(self.sensor._result()[0], "reference_year_outdated")

    def test_monthly_meter_rejected(self):
        self.states["sensor.import"].attributes["next_reset"] = "2026-12-01T00:00:00+01:00"
        self.assertEqual(self.sensor._result()[0], "annual_counters_required")

    def test_december_monthly_meter_is_not_an_annual_meter(self):
        self.source_options["cycle"] = "monthly"
        for state in self.states.values():
            state.attributes["last_reset"] = "2026-12-01T00:00:00+01:00"
        self.assertEqual(self.sensor._result()[0], "annual_counters_required")

    def test_exchanged_energy_available_without_financial_assumptions(self):
        self.options.pop("cusf")
        self.sensor.key = "exchanged_kwh"
        self.assertTrue(self.sensor.available)
        self.assertEqual(self.sensor.native_value, 2000)

    def test_lifetime_counter_rejected(self):
        self.states["sensor.import"].attributes.clear()
        self.states["sensor.import"].attributes["unit_of_measurement"] = "kWh"
        self.assertEqual(self.sensor._result()[0], "annual_counters_required")

    def test_partial_year_label(self):
        for state in self.states.values():
            state.attributes["last_reset"] = "2026-11-10T09:00:00+01:00"
        self.assertEqual(self.sensor._result()[0], "partial_year_estimate")

    def test_mismatched_periods_rejected(self):
        self.states["sensor.export"].attributes["last_reset"] = "2026-11-10T09:00:00+01:00"
        self.assertEqual(self.sensor._result()[0], "periods_do_not_match")

    def test_reference_required(self):
        self.options["rate_reference"] = " "
        self.assertEqual(self.sensor._result()[0], "rate_reference_required")

    def test_unavailable_source_does_not_erase_data(self):
        self.states["sensor.export"].state = "unavailable"
        self.assertFalse(self.sensor.available)
        self.states["sensor.export"].state = "2000"
        self.assertEqual(self.sensor.native_value, 320)

    def test_mixed_units(self):
        self.states["sensor.export"].state = "2000000"
        self.states["sensor.export"].attributes["unit_of_measurement"] = "Wh"
        self.assertEqual(self.sensor.native_value, 320)


if __name__ == "__main__":
    unittest.main()
