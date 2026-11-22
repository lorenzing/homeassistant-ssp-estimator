"""Configure annual energy counters and explicit financial assumptions."""

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EXPORT, IMPORT, RATES, price_mode
from .period import InvalidCounter, read_counter
from .provinces import PROVINCE_ZONES, province_options, with_province_zone


def _schema(defaults: dict, *, user: bool = False) -> vol.Schema:
    fields = {}
    if user:
        fields[vol.Required("name", default="Scambio sul Posto")] = selector.TextSelector()
        for key in (IMPORT, EXPORT):
            fields[vol.Required(key)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            )
    province = defaults.get("province")
    marker = vol.Required("province", default=province) if province in PROVINCE_ZONES else vol.Required("province")
    fields[marker] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=province_options(), mode="dropdown")
    )
    fields[vol.Required("reference_year", default=defaults.get("reference_year", dt_util.now().year))] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=2000, max=2100, step=1, mode="box")
    )
    fields[vol.Required("energy_price_mode", default=price_mode(defaults))] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=["automatic", "manual"], mode="dropdown", translation_key="energy_price_mode")
    )
    for key in RATES:
        marker = vol.Optional(key, default=defaults[key]) if key in defaults else vol.Optional(key)
        fields[marker] = selector.NumberSelector(selector.NumberSelectorConfig(
            min=0 if key == "cusf" else -2, max=5, step="any", mode="box", unit_of_measurement="EUR/kWh"
        ))
    fields[vol.Optional("rate_reference", default=defaults.get("rate_reference", ""))] = selector.TextSelector()
    fields[vol.Optional("cusf_reference", default=defaults.get("cusf_reference", ""))] = selector.TextSelector()
    return vol.Schema(fields)


class SSPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create an independent, local estimate."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            if user_input.get("province") not in PROVINCE_ZONES:
                errors["province"] = "invalid_province"
            if user_input[IMPORT] == user_input[EXPORT]:
                errors["base"] = "same_sensor"
            periods = []
            now = dt_util.now()
            for key in (IMPORT, EXPORT):
                try:
                    _, start, _ = read_counter(self.hass, user_input[key], now)
                    periods.append(start)
                except InvalidCounter as err:
                    errors[key] = "invalid_energy" if str(err) == "energy_unavailable" else str(err)
            if len(periods) == 2 and abs((periods[0] - periods[1]).total_seconds()) > 300:
                errors["base"] = "periods_do_not_match"
            if not errors:
                return self.async_create_entry(title=user_input["name"], data=with_province_zone(user_input))
        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}, user=True), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return SSPOptionsFlow()


class SSPOptionsFlow(OptionsFlow):
    """Update yearly scenario assumptions without replacing energy counters."""

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input.get("province") in PROVINCE_ZONES:
                return self.async_create_entry(data=with_province_zone(user_input))
            errors["province"] = "invalid_province"
        defaults = self.config_entry.options or self.config_entry.data
        return self.async_show_form(step_id="init", data_schema=_schema(user_input or defaults), errors=errors)
