"""Parse public GME MGP quarter-hour prices without estimating missing values."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from zipfile import ZipFile
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

from .calculation import number
from .const import ZONES

ROME = ZoneInfo("Europe/Rome")
SOURCE_URL = "https://gme.mercatoelettrico.org/en-us/Home/Results/Electricity/MGP/Download?valore=Prezzi"
DOWNLOAD_URL = "https://gme.mercatoelettrico.org/DesktopModules/GmeDownload/API/ExcelDownload/downloadzipfile"
DOWNLOAD_HEADERS = {"moduleid": "12103", "tabid": "1749", "userid": "-1", "Referer": SOURCE_URL}


@dataclass(frozen=True)
class PriceSlot:
    """UTC boundaries avoid ambiguity during the autumn clock change."""

    start: datetime
    end: datetime
    pun: float
    zonal: float


def parse_prices(payload: bytes, zone: str) -> list[PriceSlot]:
    """Read Prezzi15, in Italian EUR/MWh, and convert to EUR/kWh."""
    if zone not in ZONES:
        raise ValueError("Unsupported market zone")
    slots = {}
    with ZipFile(BytesIO(payload)) as archive:
        files = archive.infolist()
        if len(files) > 8 or sum(item.file_size for item in files) > 4_000_000:
            raise ValueError("Unexpected archive size")
        for item in files:
            if not item.filename.lower().endswith(".xml"):
                continue
            xml = archive.read(item)
            if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                raise ValueError("XML declarations are not supported")
            root = ET.fromstring(xml)
            for row in root.findall("Prezzi15"):
                if row.findtext("Mercato") != "MGP" or row.findtext("Granularity") != "PT15":
                    continue
                day = datetime.strptime(row.findtext("Data", ""), "%Y%m%d").replace(tzinfo=ROME)
                midnight = day.astimezone(timezone.utc)
                next_midnight = (day + timedelta(days=1)).astimezone(timezone.utc)
                period = int(row.findtext("Periodo", "0"))
                if not 1 <= period <= int((next_midnight - midnight).total_seconds() / 900):
                    raise ValueError("Invalid quarter-hour period")
                start = midnight + timedelta(minutes=15 * (period - 1))
                values = []
                for key in ("PUN", zone):
                    raw = row.findtext(key)
                    if raw is None or not raw.strip():
                        raise ValueError("Missing price")
                    values.append(number(raw.strip().replace(".", "").replace(",", ".")) / 1000)
                slot = PriceSlot(start, start + timedelta(minutes=15), *values)
                if start in slots and slots[start] != slot:
                    raise ValueError("Conflicting prices")
                slots[start] = slot
    if not slots:
        raise ValueError("No MGP quarter-hour prices")
    return sorted(slots.values(), key=lambda slot: slot.start)


def current_slot(slots, now):
    """Never substitute yesterday's or the next period's price."""
    utc_now = now.astimezone(timezone.utc)
    return next((slot for slot in slots if slot.start <= utc_now < slot.end), None)


def daily_prices(slots, day):
    """Return arithmetic daily means only when the whole market day exists."""
    start = datetime(day.year, day.month, day.day, tzinfo=ROME).astimezone(timezone.utc)
    end = (datetime(day.year, day.month, day.day, tzinfo=ROME) + timedelta(days=1)).astimezone(timezone.utc)
    selected = [slot for slot in slots if start <= slot.start < end]
    expected = int((end - start).total_seconds() / 900)
    if len(selected) != expected or any(slot.start != start + timedelta(minutes=15 * index)
                                         for index, slot in enumerate(selected)):
        return None
    return {"pun_daily": sum(slot.pun for slot in selected) / expected,
            "zonal_daily": sum(slot.zonal for slot in selected) / expected}
