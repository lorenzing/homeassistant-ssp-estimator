"""Local annual SSP estimates, reacting to changes of the two energy counters."""

from datetime import timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.util import dt as dt_util

from .calculation import number
from .const import DOMAIN, EXPORT, IMPORT, ESTIMATE_STATUSES, price_mode
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
        if key == "status":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(ESTIMATE_STATUSES)
            self._attr_translation_key = "estimate_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title, manufacturer="Community", model="SSP annual estimate")

    async def async_added_to_hass(self):
        self.async_on_remove(async_track_state_change_event(self.hass, [self.entry.data[IMPORT], self.entry.data[EXPORT]], self._changed))
        self.async_on_remove(async_track_time_change(self.hass, self._changed, hour=0, minute=0, second=1))
        self.async_on_remove(self.hass.data[DOMAIN][self.entry.entry_id].valuation.async_add_listener(self._changed))

    @callback
    def _changed(self, _event=None):
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
        result = {}
        invalid = False
        referenced = bool(str(config.get("rate_reference") or "").strip())
        mode = price_mode(config)
        coverage["energy_price_mode"] = mode
        priced_exchanged = min(energies)
        automatic_pending = False
        if mode == "automatic":
            market = getattr(self.hass, "data", {}).get(DOMAIN, {}).get(self.entry.entry_id)
            valuation = getattr(market, "valuation", None)
            data = valuation.data if valuation and valuation.last_update_success else None
            # A new reset must not reuse the previous period's cached valuation.
            if not data or data["priced_period_start"] != max(periods).astimezone(timezone.utc).isoformat():
                automatic_pending = True
            else:
                result.update(oe=data["oe"], cei=data["cei"])
                priced_exchanged = data["exchanged_kwh"]
                coverage.update({f"valuation_{key}": value for key, value in data.items()})
        elif referenced:
            for key, energy, output in (("pun_average", energies[0], "oe"), ("zonal_average", energies[1], "cei")):
                if key in config:
                    try:
                        result[output] = number(energy * number(config[key]))
                    except ValueError:
                        invalid = True
        if "oe" in result and "cei" in result:
            result["energy_component"] = min(result["oe"], result["cei"])
            result["economic_surplus"] = max(result["cei"] - result["oe"], 0.0)
        cusf_referenced = referenced or bool(str(config.get("cusf_reference") or "").strip())
        if "cusf" in config and cusf_referenced:
            try:
                cusf = number(config["cusf"])
                if cusf < 0:
                    raise ValueError
                result["services_component"] = number(priced_exchanged * cusf)
            except ValueError:
                invalid = True
        if "energy_component" in result and "services_component" in result:
            try:
                result["contribution"] = number(result["energy_component"] + result["services_component"])
            except ValueError:
                invalid = True
        if invalid:
            return "invalid_rates", result, coverage
        if automatic_pending:
            return "hourly_valuation_unavailable", result, coverage
        if "oe" not in result or "cei" not in result:
            return "rate_reference_required" if not referenced else "rates_required", result, coverage
        if "services_component" not in result:
            return "cusf_required", result, coverage
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        partial = any(value != year_start for value in periods)
        return "partial_year_estimate" if partial else "annual_estimate", result, coverage

    @property
    def available(self):
        _, result, coverage = self._result()
        return self.key == "status" or (self.key == "exchanged_kwh" and "exchanged_kwh" in coverage) or (result is not None and self.key in result)

    @property
    def native_value(self):
        status, result, coverage = self._result()
        if self.key == "exchanged_kwh":
            return coverage.get("exchanged_kwh")
        return status if self.key == "status" else round(result[self.key], 6) if result and self.key in result else None

    @property
    def extra_state_attributes(self):
        config = self.entry.options or self.entry.data
        status, _, coverage = self._result()
        return {"estimated": True, "method": "recorded_hourly_market_approximation" if price_mode(config) == "automatic" else "annual_weighted_average_scenario", "status": status,
                "reference_year": config.get("reference_year"), "zone": config.get("zone"),
                "province": config.get("province"),
                "rate_reference": config.get("rate_reference", ""),
                "cusf_reference": config.get("cusf_reference", ""),
                "not_an_official_gse_statement": True, **coverage}
