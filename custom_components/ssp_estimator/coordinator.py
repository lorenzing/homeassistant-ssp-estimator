"""Fetch official public market files once an hour; no account credentials."""

from datetime import timedelta
import logging
from zipfile import BadZipFile
import xml.etree.ElementTree as ET

from aiohttp import ClientError, ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .market import DOWNLOAD_HEADERS, DOWNLOAD_URL, ROME, parse_prices


async def download_prices(hass, start, end, zone):
    """Fetch a bounded date range from GME, also used for historical valuation."""
    params = {"DataInizio": start.strftime("%Y%m%d"),
              "DataFine": end.strftime("%Y%m%d"), "Date": end.strftime("%Y%m%d"),
              "Mercato": "MGP", "Settore": "Prezzi", "FiltroDate": "InizioFine"}
    session = async_get_clientsession(hass)
    async with session.get(DOWNLOAD_URL, params=params, headers=DOWNLOAD_HEADERS,
                           timeout=ClientTimeout(total=30)) as response:
        response.raise_for_status()
        payload = bytearray()
        async for chunk in response.content.iter_chunked(65536):
            payload.extend(chunk)
            if len(payload) > 2_000_000:
                raise ValueError("Unexpected response size")
    return await hass.async_add_executor_job(parse_prices, payload, zone)


class MarketCoordinator(DataUpdateCoordinator):
    """Hourly network refresh; sensors select the current quarter locally."""

    def __init__(self, hass, entry):
        super().__init__(hass, logging.getLogger(__name__), name=f"{DOMAIN} market",
                         config_entry=entry, update_interval=timedelta(hours=1))
        self.zone = (entry.options or entry.data)["zone"]
        self.fetched_at = None

    async def _async_update_data(self):
        today = dt_util.now().astimezone(ROME).date()
        tomorrow = today + timedelta(days=1)
        try:
            slots = await download_prices(self.hass, today, tomorrow, self.zone)
        except (ClientError, TimeoutError, ValueError, BadZipFile, ET.ParseError, OSError) as err:
            raise UpdateFailed(f"GME prices unavailable: {err}") from err
        self.fetched_at = dt_util.utcnow()
        return slots
