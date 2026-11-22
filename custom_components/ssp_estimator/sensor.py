"""Local annual SSP estimates, reacting to changes of the two energy counters."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.util import dt as dt_util

from .calculation import estimate, number
from .const import DOMAIN, EXPORT, IMPORT, RATES
from .period import InvalidCounter, read_counter

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
    from .market_sensor import MARKET_SENSORS, MarketSensor

    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        *(SSPSensor(entry, key, name, unit) for key, name, unit in DESCRIPTIONS),
        *(MarketSensor(coordinator, entry, key, name) for key, name in MARKET_SENSORS),
    ])


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
        now = dt_util.now()
        try:
            year = number(config.get("reference_year"))
        except ValueError:
            year = None
        if year != now.year:
            return "reference_year_outdated", None, {}
        energies = []
        coverage = {}
        periods = []
        for key in (IMPORT, EXPORT):
            try:
                energy, start, end = read_counter(self.hass, self.entry.data[key], now)
                energies.append(energy)
                coverage[f"{key}_last_reset"] = start.isoformat()
                coverage[f"{key}_next_reset"] = end.isoformat()
                periods.append(start)
            except InvalidCounter as err:
                return str(err), None, coverage
        # Creation timestamps can differ slightly; reject material mismatches.
        if abs((periods[0] - periods[1]).total_seconds()) > 300:
            return "periods_do_not_match", None, coverage
        coverage["exchanged_kwh"] = min(energies)
        if any(key not in config for key in RATES):
            return "rates_required", None, coverage
        if not str(config.get("rate_reference") or "").strip():
            return "rate_reference_required", None, coverage
        try:
            result = estimate(*energies, *(config[key] for key in RATES))
        except ValueError:
            return "invalid_rates", None, coverage
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        partial = any(value != year_start for value in periods)
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
                "province": config.get("province"),
                "rate_reference": config.get("rate_reference", ""),
                "not_an_official_gse_statement": True, **coverage}
