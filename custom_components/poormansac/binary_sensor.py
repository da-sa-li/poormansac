"""Binary sensor exposing the adiabatic cooling recommendation."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PoorMansACConfigEntry
from .entity import PoorMansACEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PoorMansACConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor."""
    async_add_entities([CoolingRecommendedBinarySensor(entry.runtime_data, entry)])


class CoolingRecommendedBinarySensor(PoorMansACEntity, BinarySensorEntity):
    """True when direct adiabatic cooling is expected to lower the heat index."""

    _attr_translation_key = "cooling_recommended"
    _attr_icon = "mdi:air-humidifier"

    def __init__(self, coordinator, entry: PoorMansACConfigEntry) -> None:
        super().__init__(coordinator, entry, "cooling_recommended")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.cooling_recommended

    @property
    def extra_state_attributes(self) -> dict[str, float | None]:
        data = self.coordinator.data
        # Pressure is kept in Pa internally; expose hPa at this display boundary.
        pressure_hpa = data.pressure / 100.0 if data.pressure is not None else None
        return {
            "d_hi": data.d_hi,
            "heat_index": data.heat_index,
            "absolute_humidity": data.absolute_humidity,
            "temperature": data.temperature,  # °C
            "humidity": data.humidity,  # %
            "mixing_ratio": data.mixing_ratio,  # g_water/kg_air
            "pressure": pressure_hpa,  # hPa (effective pressure used for x)
            "dx_dt": self.coordinator.dx_dt,  # kg_water/(kg_air*K), SI slope
        }
