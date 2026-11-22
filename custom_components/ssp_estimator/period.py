"""Validate yearly Utility Meter sources before using their measurements."""

from datetime import datetime

from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .calculation import energy_kwh


class InvalidCounter(ValueError):
    """A source cannot safely contribute to the estimate."""


def read_counter(hass, entity_id, now):
    """Return kWh and timezone-aware period boundaries, or a status error."""
    registry_entry = er.async_get(hass).async_get(entity_id)
    source = hass.config_entries.async_get_entry(registry_entry.config_entry_id) if registry_entry else None
    if (source is None or source.domain != "utility_meter"
            or source.options.get("cycle") != "yearly"
            or source.options.get("tariffs")
            or source.options.get("net_consumption", False)):
        raise InvalidCounter("annual_counters_required")
    state = hass.states.get(entity_id)
    if state is None:
        raise InvalidCounter("energy_unavailable")
    try:
        energy = energy_kwh(state.state, state.attributes.get("unit_of_measurement"))
    except ValueError as err:
        raise InvalidCounter("energy_unavailable") from err
    if state.attributes.get("status") == "paused":
        raise InvalidCounter("counter_paused")
    try:
        boundaries = [datetime.fromisoformat(str(state.attributes[key]))
                      for key in ("last_reset", "next_reset")]
        if any(value.utcoffset() is None for value in boundaries):
            raise ValueError
        start, end = map(dt_util.as_local, boundaries)
    except (KeyError, ValueError, TypeError, OverflowError) as err:
        raise InvalidCounter("annual_counters_required") from err
    expected_end = now.replace(year=now.year + 1, month=1, day=1,
                               hour=0, minute=0, second=0, microsecond=0)
    if start.year != now.year or start > now or end != expected_end:
        raise InvalidCounter("annual_counters_required")
    return energy, start, end
