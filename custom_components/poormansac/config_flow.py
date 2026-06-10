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
    CONF_HUMIDITY_ENTITY,
    CONF_MIN_HOLD_TIME,
    CONF_PRESSURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_THRESHOLD,
    DEFAULT_MIN_HOLD_TIME,
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
_PRESSURE_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="sensor", device_class=["atmospheric_pressure", "pressure"]
    )
)


class PoorMansACConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            data = {
                CONF_TEMPERATURE_ENTITY: user_input[CONF_TEMPERATURE_ENTITY],
                CONF_HUMIDITY_ENTITY: user_input[CONF_HUMIDITY_ENTITY],
            }
            # The pressure sensor is optional; only store it when supplied.
            if user_input.get(CONF_PRESSURE_ENTITY):
                data[CONF_PRESSURE_ENTITY] = user_input[CONF_PRESSURE_ENTITY]
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data=data,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_TEMPERATURE_ENTITY): _TEMPERATURE_SELECTOR,
                vol.Required(CONF_HUMIDITY_ENTITY): _HUMIDITY_SELECTOR,
                vol.Optional(CONF_PRESSURE_ENTITY): _PRESSURE_SELECTOR,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PoorMansACOptionsFlow()


class PoorMansACOptionsFlow(OptionsFlow):
    """Tune the dHI threshold."""

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
                    CONF_MIN_HOLD_TIME,
                    default=options.get(CONF_MIN_HOLD_TIME, DEFAULT_MIN_HOLD_TIME),
                ): vol.All(vol.Coerce(float), vol.Range(min=0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
