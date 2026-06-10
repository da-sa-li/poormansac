"""Sensor entities for Poor Man's AC."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PoorMansACConfigEntry
from .coordinator import PoorMansACData
from .entity import PoorMansACEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PoorMansACSensorDescription(SensorEntityDescription):
    """Describes a Poor Man's AC sensor."""

    value_fn: Callable[[PoorMansACData], float | None]


SENSORS: tuple[PoorMansACSensorDescription, ...] = (
    PoorMansACSensorDescription(
        key="heat_index",
        translation_key="heat_index",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.heat_index,
    ),
    PoorMansACSensorDescription(
        key="absolute_humidity",
        translation_key="absolute_humidity",
        native_unit_of_measurement="g/m³",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:water",
        value_fn=lambda data: data.absolute_humidity,
    ),
    PoorMansACSensorDescription(
        key="mixing_ratio",
        translation_key="mixing_ratio",
        native_unit_of_measurement="g/kg",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:water-percent",
        value_fn=lambda data: data.mixing_ratio,
    ),
    PoorMansACSensorDescription(
        key="wet_bulb_temperature",
        translation_key="wet_bulb_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-water",
        value_fn=lambda data: data.wet_bulb_temperature,
    ),
    PoorMansACSensorDescription(
        key="wet_bulb_depression",
        translation_key="wet_bulb_depression",
        native_unit_of_measurement="K",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-chevron-down",
        value_fn=lambda data: data.wet_bulb_depression,
    ),
    PoorMansACSensorDescription(
        key="d_hi",
        translation_key="d_hi",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:delta",
        value_fn=lambda data: data.d_hi,
    ),
    PoorMansACSensorDescription(
        key="d_hi_dt",
        translation_key="d_hi_dt",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:function-variant",
        value_fn=lambda data: data.d_hi_dt,
    ),
    PoorMansACSensorDescription(
        key="d_hi_dx",
        translation_key="d_hi_dx",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:function-variant",
        value_fn=lambda data: data.d_hi_dx,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PoorMansACConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        PoorMansACSensor(coordinator, entry, description) for description in SENSORS
    )


class PoorMansACSensor(PoorMansACEntity, SensorEntity):
    """A computed sensor."""

    entity_description: PoorMansACSensorDescription

    def __init__(
        self,
        coordinator,
        entry: PoorMansACConfigEntry,
        description: PoorMansACSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)
