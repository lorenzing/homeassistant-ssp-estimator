"""Automatic hourly valuation, with a local cache of historical GME prices."""

from datetime import datetime, timedelta, timezone
import logging
from zipfile import BadZipFile
import xml.etree.ElementTree as ET

from aiohttp import ClientError
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.helpers.recorder import get_instance
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EXPORT, IMPORT, price_mode
from .coordinator import download_prices
from .market import PriceSlot, ROME, daily_prices
from .period import read_counter
from .valuation import timestamp, value_hours


class ValuationCoordinator(DataUpdateCoordinator):
    """Value only recorded hours, independently of the optional CUSf."""

    def __init__(self, hass, entry, market):
        super().__init__(hass, logging.getLogger(__name__), config_entry=entry,
                         name=f"{DOMAIN} hourly valuation", update_interval=timedelta(minutes=15))
        self.entry = entry
        self.market = market
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.prices")
        self.loaded = False
        self.prices = {}

    async def _async_update_data(self):
        config = self.entry.options or self.entry.data
        if price_mode(config) == "manual":
            return None
        now = dt_util.now()
        try:
            starts = [read_counter(self.hass, self.entry.data[key], now)[1] for key in (IMPORT, EXPORT)]
            if abs((starts[0] - starts[1]).total_seconds()) > 300:
                raise ValueError("Counter periods do not match")
            start = max(starts).astimezone(timezone.utc)
            requested_end = now.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
            ids = {self.entry.data[IMPORT], self.entry.data[EXPORT]}
            recorder = get_instance(self.hass)
            rows = await recorder.async_add_executor_job(
                statistics_during_period, self.hass,
                start.replace(minute=0, second=0, microsecond=0), requested_end,
                ids, "hour", {"energy": "kWh"}, {"change"})
            imports = rows.get(self.entry.data[IMPORT], [])
            exports = rows.get(self.entry.data[EXPORT], [])
            if not imports or not exports:
                raise ValueError("Hourly energy statistics not available yet")
            end = min(requested_end, *(datetime.fromtimestamp(timestamp(group[-1]["end"]), timezone.utc)
                                       for group in (imports, exports)))
            if not self.loaded:
                saved = await self.store.async_load()
                if saved and saved.get("zone") == self.market.zone:
                    for raw in saved.get("prices", []):
                        when = datetime.fromtimestamp(raw[0], timezone.utc)
                        if when.year == now.year or when.astimezone(ROME).year == now.year:
                            self.prices[when.timestamp()] = PriceSlot(when, when + timedelta(minutes=15), raw[1], raw[2])
                self.loaded = True
            for slot in self.market.data or []:
                self.prices[slot.start.timestamp()] = slot
            day = start.astimezone(ROME).date()
            last_day = (end - timedelta(seconds=1)).astimezone(ROME).date()
            while day <= last_day:
                if daily_prices(list(self.prices.values()), day) is not None:
                    day += timedelta(days=1)
                    continue
                chunk_end = min(day + timedelta(days=6), last_day)
                slots = await download_prices(self.hass, day, chunk_end, self.market.zone)
                for slot in slots:
                    self.prices[slot.start.timestamp()] = slot
                day = chunk_end + timedelta(days=1)
            await self.store.async_save({"zone": self.market.zone, "prices": [
                [slot.start.timestamp(), slot.pun, slot.zonal] for slot in self.prices.values()
                if slot.start.astimezone(ROME).year == now.year]})
            return value_hours(imports, exports, list(self.prices.values()), start, end)
        except (ClientError, TimeoutError, ValueError, KeyError, TypeError, BadZipFile, ET.ParseError, OSError) as err:
            raise UpdateFailed(f"Hourly valuation unavailable: {err}") from err
