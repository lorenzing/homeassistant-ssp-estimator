"""Match recorded hourly energy changes to real prices of the same hours."""

from datetime import datetime, timedelta, timezone

from .calculation import number


def timestamp(value):
    """Accept Recorder timestamps in seconds (or WS exports in milliseconds)."""
    value = number(value)
    return value / 1000 if value > 100_000_000_000 else value


def value_hours(import_rows, export_rows, slots, start, end):
    """Price completed hours with their four-quarter arithmetic price mean.

    Hourly statistics do not reveal within-hour energy profiles. This is an
    hourly approximation, never a claim of quarter-hour GSE settlement accuracy.
    No missing energy or price interval is replaced with zero or today's price.
    """
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("Timezone-aware coverage required")
    first_hour = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = end.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    if end <= start:
        raise ValueError("No completed energy interval")
    prices = {slot.start.timestamp(): slot for slot in slots}
    imports = {timestamp(row["start"]): row for row in import_rows}
    exports = {timestamp(row["start"]): row for row in export_rows}
    if len(imports) != len(import_rows) or len(exports) != len(export_rows):
        raise ValueError("Duplicate energy intervals")
    imported = exported = oe = cei = 0.0
    hour = first_hour
    count = 0
    while hour < end:
        key = hour.timestamp()
        rows = (imports.get(key), exports.get(key))
        if any(row is None for row in rows):
            raise ValueError("Missing energy interval")
        changes = [number(row.get("change")) for row in rows]
        if min(changes) < 0:
            raise ValueError("Negative energy correction requires review")
        quarters = [prices.get(key + index * 900) for index in range(4)]
        if any(slot is None for slot in quarters):
            raise ValueError("Missing market interval")
        imported += changes[0]
        exported += changes[1]
        oe += changes[0] * sum(slot.pun for slot in quarters) / 4
        cei += changes[1] * sum(slot.zonal for slot in quarters) / 4
        count += 1
        hour += timedelta(hours=1)
    return {"oe": number(oe), "cei": number(cei), "imported_kwh": imported,
            "exported_kwh": exported, "exchanged_kwh": min(imported, exported),
            "priced_hours": count, "priced_period_start": start.isoformat(),
            "priced_period_end": end.isoformat(),
            "method": "recorded_hourly_energy_times_hourly_market_mean",
            "within_hour_profile_unknown": True, "export_loss_factor": 1.0}
