"""Real GME prices, kept separate from annual SSP scenario assumptions."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .market import ROME, SOURCE_URL, current_slot, daily_prices

MARKET_SENSORS = (
    ("pun_current", "PUN puntuale"),
    ("zonal_current", "Prezzo zonale puntuale"),
    ("pun_daily", "PUN medio giornaliero"),
    ("zonal_daily", "Prezzo zonale medio giornaliero"),
)


class MarketSensor(CoordinatorEntity, SensorEntity):
    """Re-evaluate the price at every quarter boundary without downloading."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "EUR/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 6
    _attr_icon = "mdi:currency-eur"

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator)
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)},
                                           name=entry.title, manufacturer="Community",
                                           model="SSP annual estimate")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_track_time_change(
            self.hass, self._period_changed, minute=[0, 15, 30, 45], second=0))

    @callback
    def _period_changed(self, _event):
        self.async_write_ha_state()

    @property
    def native_value(self):
        slots = self.coordinator.data or []
        now = dt_util.now().astimezone(ROME)
        if self.key.endswith("_daily"):
            daily = daily_prices(slots, now.date())
            return round(daily[self.key], 6) if daily else None
        slot = current_slot(slots, now)
        if slot is None:
            return None
        return slot.pun if self.key == "pun_current" else slot.zonal

    @property
    def available(self):
        return self.coordinator.last_update_success and self.native_value is not None

    @property
    def extra_state_attributes(self):
        now = dt_util.now().astimezone(ROME)
        slot = current_slot(self.coordinator.data or [], now)
        return {"source": "GME — Mercato del Giorno Prima", "source_url": SOURCE_URL,
                "zone": self.coordinator.zone, "market_date": now.date().isoformat(),
                "fetched_at": self.coordinator.fetched_at,
                "period_start": slot.start.astimezone(ROME).isoformat() if slot else None,
                "period_end": slot.end.astimezone(ROME).isoformat() if slot else None,
                "method": "daily_arithmetic_mean" if self.key.endswith("_daily") else "quarter_hour_market_price",
                "used_in_annual_estimate": False}
