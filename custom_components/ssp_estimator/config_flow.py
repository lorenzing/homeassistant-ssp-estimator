"""Configure annual energy counters and explicit financial assumptions."""

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .calculation import energy_kwh
from .const import DOMAIN, EXPORT, IMPORT, RATES, ZONES


def _schema(defaults: dict, *, user: bool = False) -> vol.Schema:
    fields = {}
    if user:
        fields[vol.Required("name", default="Scambio sul Posto")] = selector.TextSelector()
        for key in (IMPORT, EXPORT):
            fields[vol.Required(key)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            )
    fields[vol.Required("zone", default=defaults.get("zone", "NORD"))] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=list(ZONES), mode="dropdown")
    )
    fields[vol.Required("reference_year", default=defaults.get("reference_year", dt_util.now().year))] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=2000, max=2100, step=1, mode="box")
    )
    for key in RATES:
        marker = vol.Optional(key, default=defaults[key]) if key in defaults else vol.Optional(key)
        fields[marker] = selector.NumberSelector(selector.NumberSelectorConfig(
            min=0 if key == "cusf" else -2, max=5, step=0.000001, mode="box", unit_of_measurement="EUR/kWh"
        ))
    fields[vol.Optional("rate_reference", default=defaults.get("rate_reference", ""))] = selector.TextSelector()
    return vol.Schema(fields)


class SSPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create an independent, local estimate."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            if user_input[IMPORT] == user_input[EXPORT]:
                errors["base"] = "same_sensor"
            for key in (IMPORT, EXPORT):
                state = self.hass.states.get(user_input[key])
                try:
                    if state is None:
                        raise ValueError
                    energy_kwh(state.state, state.attributes.get("unit_of_measurement"))
                except ValueError:
                    errors[key] = "invalid_energy"
            if not errors:
                return self.async_create_entry(title=user_input["name"], data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}, user=True), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return SSPOptionsFlow()


class SSPOptionsFlow(OptionsFlow):
    """Update yearly scenario assumptions without replacing energy counters."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        defaults = self.config_entry.options or self.config_entry.data
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
