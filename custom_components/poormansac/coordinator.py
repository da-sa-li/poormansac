"""State tracking and computation for the Poor Man's AC integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPressure,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.unit_conversion import PressureConverter

from . import calc
from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_PRESSURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_THRESHOLD,
    DEFAULT_DX_DT,
    DEFAULT_PRESSURE_HPA,
    DEFAULT_THRESHOLD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PoorMansACData:
    """Computed values shared with the entities."""

    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None  # effective ambient pressure in Pa (SI)
    absolute_humidity: float | None = None
    mixing_ratio: float | None = None
    heat_index: float | None = None
    d_hi_dt: float | None = None
    d_hi_dx: float | None = None
    d_hi: float | None = None
    cooling_recommended: bool | None = None


class PoorMansACCoordinator(DataUpdateCoordinator[PoorMansACData]):
    """Recomputes derived values whenever a source sensor changes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self.entry = entry
        self._temperature_entity = entry.data[CONF_TEMPERATURE_ENTITY]
        self._humidity_entity = entry.data[CONF_HUMIDITY_ENTITY]
        # Optional: when set, the ambient pressure is read live from this
        # sensor; otherwise the static fallback below is used.
        self._pressure_entity = entry.data.get(CONF_PRESSURE_ENTITY)
        self._threshold = entry.options.get(CONF_THRESHOLD, DEFAULT_THRESHOLD)
        # Internal model constant already in SI (kg_water/(kg_air*K)); used directly.
        self._dx_dt = DEFAULT_DX_DT
        # Boundary conversion: the human-facing hPa fallback -> Pa for the math.
        self._pressure_fallback = DEFAULT_PRESSURE_HPA * 100.0

    @property
    def dx_dt(self) -> float:
        """Slope dx/dT of the isenthalpic cooling line, kg_water/(kg_air*K) (SI)."""
        return self._dx_dt

    async def async_initialize(self) -> None:
        """Subscribe to the source entities and compute the initial state."""
        tracked = [self._temperature_entity, self._humidity_entity]
        if self._pressure_entity is not None:
            tracked.append(self._pressure_entity)
        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                tracked,
                self._handle_source_change,
            )
        )
        await self.async_refresh()

    async def _async_update_data(self) -> PoorMansACData:
        return self._compute()

    @callback
    def _handle_source_change(self, event: Event[EventStateChangedData]) -> None:
        self.async_set_updated_data(self._compute())

    def _read(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            _LOGGER.debug("Cannot parse %s state '%s'", entity_id, state.state)
            return None

    def _read_pressure(self) -> float:
        """Ambient pressure in Pa.

        Priority:
        1. Configured sensor entity (live reading, unit-converted).
        2. HA's configured elevation via the ISA barometric formula.
        3. Static fallback value from the options (default 1013.25 hPa).
        """
        if self._pressure_entity is not None:
            value = self._read(self._pressure_entity)
            if value is not None:
                state = self.hass.states.get(self._pressure_entity)
                unit = (
                    state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state else None
                )
                try:
                    return PressureConverter.convert(value, unit, UnitOfPressure.PA)
                except (HomeAssistantError, ValueError):
                    _LOGGER.debug(
                        "Cannot convert pressure %s from unit '%s'; trying elevation",
                        value,
                        unit,
                    )

        elevation = self.hass.config.elevation
        if elevation is not None:
            return calc.pressure_from_elevation(elevation)

        return self._pressure_fallback

    def _compute(self) -> PoorMansACData:
        t = self._read(self._temperature_entity)
        rh = self._read(self._humidity_entity)
        if t is None or rh is None:
            return PoorMansACData(temperature=t, humidity=rh)

        pressure = self._read_pressure()
        x = calc.mixing_ratio(t, rh, pressure)
        d_hi = calc.d_hi_cooling(t, x, self._dx_dt)

        return PoorMansACData(
            temperature=t,
            humidity=rh,
            pressure=pressure,
            absolute_humidity=calc.absolute_humidity(t, rh) * 1000.0,  # kg/m^3 -> g/m^3
            mixing_ratio=x * 1000.0,  # expose in g_water/kg_air
            heat_index=calc.heat_index(t, x),
            d_hi_dt=calc.d_hi_d_t(t, x),
            d_hi_dx=calc.d_hi_d_x(t, x),
            d_hi=d_hi,
            cooling_recommended=d_hi < self._threshold,
        )
