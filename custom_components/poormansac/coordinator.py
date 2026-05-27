"""State tracking and computation for the Poor Man's AC integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import calc
from .const import (
    CONF_AIR_DENSITY,
    CONF_HEAT_CAPACITY,
    CONF_HUMIDITY_ENTITY,
    CONF_HYSTERESIS,
    CONF_TEMPERATURE_ENTITY,
    CONF_THRESHOLD,
    DEFAULT_AIR_DENSITY,
    DEFAULT_HEAT_CAPACITY,
    DEFAULT_HYSTERESIS,
    DEFAULT_THRESHOLD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PoorMansACData:
    """Computed values shared with the entities."""

    temperature: float | None = None
    humidity: float | None = None
    absolute_humidity: float | None = None
    heat_index: float | None = None
    d_hi_dt: float | None = None
    d_hi_drho: float | None = None
    d_hi: float | None = None
    cooling_recommended: bool | None = None


class PoorMansACCoordinator(DataUpdateCoordinator[PoorMansACData]):
    """Recomputes derived values whenever a source sensor changes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entry = entry
        self._temperature_entity = entry.data[CONF_TEMPERATURE_ENTITY]
        self._humidity_entity = entry.data[CONF_HUMIDITY_ENTITY]
        options = entry.options
        self._threshold = options.get(CONF_THRESHOLD, DEFAULT_THRESHOLD)
        self._hysteresis = options.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
        self._air_density = options.get(CONF_AIR_DENSITY, DEFAULT_AIR_DENSITY)
        self._heat_capacity = options.get(CONF_HEAT_CAPACITY, DEFAULT_HEAT_CAPACITY)
        self._recommended = False

    async def async_initialize(self) -> None:
        """Subscribe to the source entities and compute the initial state."""
        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [self._temperature_entity, self._humidity_entity],
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

    def _compute(self) -> PoorMansACData:
        t = self._read(self._temperature_entity)
        rh = self._read(self._humidity_entity)
        if t is None or rh is None:
            return PoorMansACData(temperature=t, humidity=rh)

        rho_w = calc.absolute_humidity(t, rh)
        d_hi = calc.d_hi_cooling(t, rho_w, self._air_density, self._heat_capacity)

        # Cooling improves comfort when dHI is below the threshold. Apply a
        # symmetric hysteresis band so the binary recommendation does not flap.
        if self._recommended:
            self._recommended = d_hi < self._threshold + self._hysteresis
        else:
            self._recommended = d_hi < self._threshold - self._hysteresis

        return PoorMansACData(
            temperature=t,
            humidity=rh,
            absolute_humidity=rho_w,
            heat_index=calc.heat_index(t, rh),
            d_hi_dt=calc.d_hi_d_t(t, rho_w),
            d_hi_drho=calc.d_hi_d_rho(t),
            d_hi=d_hi,
            cooling_recommended=self._recommended,
        )
