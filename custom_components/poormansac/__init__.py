"""The Poor Man's AC (adiabatic cooling advisor) integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import PoorMansACCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

PoorMansACConfigEntry = ConfigEntry[PoorMansACCoordinator]

# Lovelace card bundled with the integration and auto-registered as a resource.
_FRONTEND_URL_BASE = "/poormansac_frontend"
_CARD_FILENAME = "poormansac-psychrometric-card.js"
_CARD_URL = f"{_FRONTEND_URL_BASE}/{_CARD_FILENAME}"
_FRONTEND_REGISTERED_KEY = f"{DOMAIN}_frontend_registered"


async def async_setup_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> bool:
    """Set up Poor Man's AC from a config entry."""
    coordinator = PoorMansACCoordinator(hass, entry)
    await coordinator.async_initialize()
    entry.runtime_data = coordinator

    await _async_register_frontend(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and auto-load it as a JS module.

    Runs once per Home Assistant instance; the guard makes a second config
    entry safe, since registering the same static path twice would raise.
    """
    if hass.data.get(_FRONTEND_REGISTERED_KEY):
        return
    hass.data[_FRONTEND_REGISTERED_KEY] = True

    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_FRONTEND_URL_BASE, str(frontend_dir), False)]
    )
    frontend.add_extra_js_url(hass, _CARD_URL)


async def async_unload_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
