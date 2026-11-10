"""Local annual SSP estimates, reacting to changes of the two energy counters."""

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .calculation import energy_kwh, estimate
from .const import DOMAIN, EXPORT, IMPORT, RATES

DESCRIPTIONS = (
    ("exchanged_kwh", "Energia scambiata nel periodo", "kWh"),
    ("oe", "OE stimato", "EUR"),
    ("cei", "CEI stimato", "EUR"),
    ("energy_component", "Quota energia stimata", "EUR"),
    ("services_component", "Quota servizi stimata", "EUR"),
    ("contribution", "Contributo SSP stimato", "EUR"),
    ("economic_surplus", "Eccedenza economica stimata", "EUR"),
    ("status", "Stato della stima", None),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(SSPSensor(entry, key, name, unit) for key, name, unit in DESCRIPTIONS)


class SSPSensor(SensorEntity):
    """Scenario estimates deliberately have no cumulative statistics class.

    Updating an annual average revises the whole scenario. Do not feed these
    money sensors to the Energy dashboard as if they were settled payments.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry, key, name, unit):
        self.entry = entry
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_display_precision = 3 if unit == "kWh" else 2 if unit else None
        self._attr_device_class = SensorDeviceClass.ENERGY if unit == "kWh" else SensorDeviceClass.MONETARY if unit else None
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title, manufacturer="Community", model="SSP annual estimate")

    async def async_added_to_hass(self):
        self.async_on_remove(async_track_state_change_event(self.hass, [self.entry.data[IMPORT], self.entry.data[EXPORT]], self._changed))
        self.async_on_remove(async_track_time_change(self.hass, self._changed, hour=0, minute=0, second=1))

    @callback
    def _changed(self, _event):
        self.async_write_ha_state()

    def _result(self):
        config = self.entry.options or self.entry.data
        if int(config.get("reference_year", 0)) != dt_util.now().year:
            return "reference_year_outdated", None, {}
        energies = []
        coverage = {}
        periods = []
        for key in (IMPORT, EXPORT):
            state = self.hass.states.get(self.entry.data[key])
            try:
                registry_entry = er.async_get(self.hass).async_get(self.entry.data[key])
                source_entry = self.hass.config_entries.async_get_entry(registry_entry.config_entry_id) if registry_entry else None
                if source_entry is None or source_entry.domain != "utility_meter" or source_entry.options.get("cycle") != "yearly":
                    return "annual_counters_required", None, coverage
                if state is None:
                    raise ValueError
                energies.append(energy_kwh(state.state, state.attributes.get("unit_of_measurement")))
                # Yearly Utility Meter exposes next_reset on January 1.
                # Reject known monthly/day counters and stale previous-year data.
                for attribute in ("last_reset", "next_reset"):
                    raw = state.attributes.get(attribute)
                    coverage[f"{key}_{attribute}"] = raw
                start_raw = state.attributes.get("last_reset")
                end_raw = state.attributes.get("next_reset")
                if not start_raw or not end_raw:
                    return "annual_counters_required", None, coverage
                start = dt_util.as_local(datetime.fromisoformat(str(start_raw)))
                end = dt_util.as_local(datetime.fromisoformat(str(end_raw)))
                year = dt_util.now().year
                if start.year != year or (end.year, end.month, end.day) != (year + 1, 1, 1):
                    return "annual_counters_required", None, coverage
                periods.append(start)
            except (ValueError, TypeError, OverflowError):
                return "energy_unavailable", None, coverage
        # Creation timestamps can differ slightly; reject material mismatches.
        if abs((periods[0] - periods[1]).total_seconds()) > 300:
            return "periods_do_not_match", None, coverage
        coverage["exchanged_kwh"] = min(energies)
        if any(key not in config for key in RATES):
            return "rates_required", None, coverage
        if not config.get("rate_reference", "").strip():
            return "rate_reference_required", None, coverage
        try:
            result = estimate(*energies, *(config[key] for key in RATES))
        except ValueError:
            return "invalid_rates", None, coverage
        partial = any((value.month, value.day) != (1, 1) or value.hour != 0 for value in periods)
        return "partial_year_estimate" if partial else "annual_estimate", result, coverage

    @property
    def available(self):
        _, result, coverage = self._result()
        return self.key == "status" or (self.key == "exchanged_kwh" and "exchanged_kwh" in coverage) or result is not None

    @property
    def native_value(self):
        status, result, coverage = self._result()
        if self.key == "exchanged_kwh":
            return coverage.get("exchanged_kwh")
        return status if self.key == "status" else round(getattr(result, self.key), 6) if result else None

    @property
    def extra_state_attributes(self):
        config = self.entry.options or self.entry.data
        status, _, coverage = self._result()
        return {"estimated": True, "method": "annual_weighted_average_scenario", "status": status,
                "reference_year": config.get("reference_year"), "zone": config.get("zone"),
                "rate_reference": config.get("rate_reference", ""),
                "not_an_official_gse_statement": True, **coverage}
