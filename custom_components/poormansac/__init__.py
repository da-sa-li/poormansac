"""The Poor Man's AC (adiabatic cooling advisor) integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .coordinator import PoorMansACCoordinator

try:  # ``LOVELACE_DATA`` is the documented key; fall back for older cores.
    from homeassistant.components.lovelace.const import LOVELACE_DATA
except ImportError:  # pragma: no cover - depends on Home Assistant version
    LOVELACE_DATA = "lovelace"

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

PoorMansACConfigEntry = ConfigEntry[PoorMansACCoordinator]

# Lovelace card bundled with the integration and auto-registered as a resource.
_FRONTEND_URL_BASE = "/poormansac_frontend"
_CARD_FILENAME = "poormansac-psychrometric-card.js"
_CARD_URL = f"{_FRONTEND_URL_BASE}/{_CARD_FILENAME}"
_FRONTEND_REGISTERED_KEY = f"{DOMAIN}_frontend_registered"
_FRONTEND_SCHEDULED_KEY = f"{DOMAIN}_frontend_scheduled"
_FRONTEND_LOCK_KEY = f"{DOMAIN}_frontend_lock"


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
    """Serve the bundled Lovelace card and make it loadable without manual setup.

    Serving the file is not enough on its own: a dashboard only loads a custom
    card if its JS module is registered, otherwise the card shows a
    "custom element doesn't exist" configuration error. So we register it the
    way the user otherwise would by hand under
    *Settings → Dashboard → Resources*:

    - **Storage mode** (the default): add a Lovelace *module* resource, so the
      card appears in the dashboard's resource list and card picker
      automatically.
    - **YAML mode**: resources live in the user's YAML and cannot be edited from
      code, so we fall back to loading the module globally via the frontend.

    Registration happens once per Home Assistant instance. A lock serialises
    concurrent config-entry setups, and the success flag is only set after the
    card is actually registered, so a failed attempt is retried by the next
    setup instead of leaving the card unregistered.
    """
    if hass.data.get(_FRONTEND_REGISTERED_KEY):
        return
    lock = hass.data.setdefault(_FRONTEND_LOCK_KEY, asyncio.Lock())
    async with lock:
        if hass.data.get(_FRONTEND_REGISTERED_KEY):
            return

        frontend_dir = Path(__file__).parent / "frontend"
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(_FRONTEND_URL_BASE, str(frontend_dir), cache_headers=False)]
            )
        except RuntimeError:
            # Path was already registered by an earlier setup; harmless.
            pass

        version = await _async_card_version(hass)

        async def _register(*_: object) -> None:
            # Mark as done only after the card is actually registered, so a
            # failure here leaves the flag unset and the next config-entry
            # setup retries instead of silently skipping registration.
            await _async_register_card_resource(hass, version)
            hass.data[_FRONTEND_REGISTERED_KEY] = True

        # Lovelace resources are reliable only once Home Assistant has finished
        # starting; defer until then if setup runs during the boot sequence.
        if hass.is_running:
            await _register()
        elif not hass.data.get(_FRONTEND_SCHEDULED_KEY):
            # Guard against queuing one startup listener per config entry.
            hass.data[_FRONTEND_SCHEDULED_KEY] = True
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register)


async def _async_card_version(hass: HomeAssistant) -> str:
    """Return the integration version, used as a cache-busting query string."""
    integration = await async_get_integration(hass, DOMAIN)
    return str(integration.version) if integration.version else "0"


async def _async_register_card_resource(hass: HomeAssistant, version: str) -> None:
    """Register the bundled card as a Lovelace module resource (storage mode).

    Falls back to loading the module globally when resources cannot be managed
    from code (YAML mode, or before Lovelace is available).
    """
    lovelace = hass.data.get(LOVELACE_DATA)
    resources = getattr(lovelace, "resources", None)
    if lovelace is None or getattr(lovelace, "resource_mode", None) != "storage" or resources is None:
        # No editable storage-mode resource list: load the module directly so
        # the card is still defined for the dashboard.
        frontend.add_extra_js_url(hass, _CARD_URL)
        return

    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    url = f"{_CARD_URL}?v={version}"
    for item in resources.async_items():
        # Match on the path only, so an existing entry (ours or a manually added
        # one) is updated in place instead of duplicated.
        if item["url"].split("?")[0] == _CARD_URL:
            if item["url"] != url:
                await resources.async_update_item(
                    item["id"], {"res_type": "module", "url": url}
                )
            return

    await resources.async_create_item({"res_type": "module", "url": url})
    _LOGGER.debug("Registered Lovelace card resource %s", url)


async def async_unload_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: PoorMansACConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
