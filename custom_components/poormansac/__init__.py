"""The Poor Man's AC (adiabatic cooling advisor) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import PoorMansACCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

PoorMansACConfigEntry = ConfigEntry[PoorMansACCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> bool:
    """Set up Poor Man's AC from a config entry."""
    coordinator = PoorMansACCoordinator(hass, entry)
    await coordinator.async_initialize()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
