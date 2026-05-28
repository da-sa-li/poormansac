"""Config and options flow for Poor Man's AC."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DRHO_W_DT,
    CONF_HUMIDITY_ENTITY,
    CONF_HYSTERESIS,
    CONF_TEMPERATURE_ENTITY,
    CONF_THRESHOLD,
    DEFAULT_DRHO_W_DT,
    DEFAULT_HYSTERESIS,
    DEFAULT_NAME,
    DEFAULT_THRESHOLD,
    DOMAIN,
)

_TEMPERATURE_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
)
_HUMIDITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
)


class PoorMansACConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data={
                    CONF_TEMPERATURE_ENTITY: user_input[CONF_TEMPERATURE_ENTITY],
                    CONF_HUMIDITY_ENTITY: user_input[CONF_HUMIDITY_ENTITY],
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_TEMPERATURE_ENTITY): _TEMPERATURE_SELECTOR,
                vol.Required(CONF_HUMIDITY_ENTITY): _HUMIDITY_SELECTOR,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PoorMansACOptionsFlow()


class PoorMansACOptionsFlow(OptionsFlow):
    """Tune thresholds and the isenthalpic slope."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_THRESHOLD,
                    default=options.get(CONF_THRESHOLD, DEFAULT_THRESHOLD),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_HYSTERESIS,
                    default=options.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
                vol.Optional(
                    CONF_DRHO_W_DT,
                    default=options.get(CONF_DRHO_W_DT, DEFAULT_DRHO_W_DT),
                ): vol.All(vol.Coerce(float), vol.Range(max=0.0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
