"""Diagnostics support for Poor Man's AC."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from . import PoorMansACConfigEntry
from .const import CONF_HUMIDITY_ENTITY, CONF_PRESSURE_ENTITY, CONF_TEMPERATURE_ENTITY


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PoorMansACConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": {
            "dx_dt": coordinator.dx_dt,
            "last_update_success": coordinator.last_update_success,
            "data": asdict(coordinator.data) if coordinator.data else None,
        },
        "source_entities": {
            key: _state_dict(hass, entity_id)
            for key, entity_id in (
                ("temperature", entry.data.get(CONF_TEMPERATURE_ENTITY)),
                ("humidity", entry.data.get(CONF_HUMIDITY_ENTITY)),
                ("pressure", entry.data.get(CONF_PRESSURE_ENTITY)),
            )
        },
    }


def _state_dict(hass: HomeAssistant, entity_id: str | None) -> dict[str, Any] | None:
    """Return a JSON-serialisable snapshot of an entity's state, or None."""
    if entity_id is None:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return {
        "entity_id": entity_id,
        "state": state.state,
        "attributes": dict(state.attributes),
    }
