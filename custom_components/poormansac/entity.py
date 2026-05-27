"""Shared entity base for Poor Man's AC."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PoorMansACCoordinator


class PoorMansACEntity(CoordinatorEntity[PoorMansACCoordinator]):
    """Base entity that ties all sensors to one device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PoorMansACCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="poormansac",
            model="Adiabatic cooling advisor",
            entry_type=DeviceEntryType.SERVICE,
        )
