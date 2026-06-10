"""State tracking and computation for the Poor Man's AC integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPressure,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import PressureConverter

from . import calc
from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_MIN_HOLD_TIME,
    CONF_PRESSURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_THRESHOLD,
    DEFAULT_DX_DT,
    DEFAULT_MIN_HOLD_TIME,
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
    wet_bulb_temperature: float | None = None
    # Wet-bulb depression t - t_wb in K: the maximum achievable evaporative cooling.
    wet_bulb_depression: float | None = None
    # Water uptake to the heat-index minimum along the isenthalpic path, g/kg.
    optimal_water_uptake: float | None = None
    d_hi_dt: float | None = None
    d_hi_dx: float | None = None
    d_hi: float | None = None
    cooling_recommended: bool | None = None


class PoorMansACCoordinator(DataUpdateCoordinator[PoorMansACData]):
    """Recomputes derived values whenever a source sensor changes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """
        Initialize the coordinator with entities, thresholds, model constants, and hysteresis state.
        
        Parameters:
            entry (ConfigEntry): Integration config entry used to read entity IDs (temperature, humidity, optional pressure) and options (threshold and minimum hold time).
        
        Initializes:
            - Reads and stores temperature, humidity, and optional pressure entity IDs from `entry.data`.
            - Loads threshold and model constant (`_dx_dt`) from `entry.options` / defaults.
            - Converts fallback pressure from hPa to Pa and computes `_min_hold_time`.
            - Sets up hysteresis state variables: `_cooling_recommended`, `_cooling_recommended_since`, and `_pending_flip_unsub`.
        """
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
        # Hysteresis: minimum time the cooling_recommended state must hold
        # before it is allowed to flip again.
        self._min_hold_time = timedelta(
            minutes=entry.options.get(CONF_MIN_HOLD_TIME, DEFAULT_MIN_HOLD_TIME)
        )
        self._cooling_recommended: bool | None = None
        self._cooling_recommended_since: datetime | None = None
        self._pending_flip_unsub: CALLBACK_TYPE | None = None

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
        self.entry.async_on_unload(self._cancel_pending_flip)
        await self.async_refresh()

    async def _async_update_data(self) -> PoorMansACData:
        """
        Produce the coordinator's current PoorMansACData snapshot.
        
        Returns:
            PoorMansACData: Computed AC-related values (temperature, humidity, effective pressure, absolute_humidity, mixing_ratio, heat_index, derivatives, and cooling_recommended). If temperature or humidity cannot be read, those fields (and derived values) may be None.
        """
        return self._compute()

    @callback
    def _handle_source_change(self, event: Event[EventStateChangedData]) -> None:
        """
        Recompute derived AC metrics and publish updated coordinator data when a tracked source entity changes.
        
        Parameters:
            event (Event[EventStateChangedData]): The state change event for one of the tracked source entities.
        """
        self.async_set_updated_data(self._compute())

    def _apply_hysteresis(self, raw: bool) -> bool:
        """
        Enforce a minimum hold time before changing the coordinator's cooling recommendation.
        
        If the stored recommendation is unset, initialize it to `raw`. If `raw` equals the current stored recommendation, any pending flip is cancelled and the stored value is returned. If the time since the stored recommendation was set is at least the configured minimum hold time, update the stored recommendation to `raw` and return it. Otherwise, schedule a delayed re-evaluation and return the current stored recommendation.
        
        Parameters:
            raw (bool): The freshly computed cooling recommendation before hysteresis.
        
        Returns:
            true if cooling is recommended after applying hysteresis, false otherwise.
        """
        now = dt_util.utcnow()

        if self._cooling_recommended is None:
            self._cooling_recommended = raw
            self._cooling_recommended_since = now
            return raw

        if raw == self._cooling_recommended:
            self._cancel_pending_flip()
            return self._cooling_recommended

        if now - self._cooling_recommended_since >= self._min_hold_time:
            self._cooling_recommended = raw
            self._cooling_recommended_since = now
            self._cancel_pending_flip()
            return raw

        self._schedule_flip()
        return self._cooling_recommended

    def _schedule_flip(self) -> None:
        """
        Schedule a delayed re-evaluation to occur when the current hold window ends.
        
        If a pending flip is already scheduled, this does nothing. The scheduled callback will trigger a recompute when `self._cooling_recommended_since + self._min_hold_time` is reached.
        """
        if self._pending_flip_unsub is not None:
            return
        when = self._cooling_recommended_since + self._min_hold_time
        self._pending_flip_unsub = async_track_point_in_time(
            self.hass, self._handle_pending_flip, when
        )

    @callback
    def _handle_pending_flip(self, _now: datetime) -> None:
        """
        Handle a scheduled pending flip by clearing the pending-unsubscribe handle and publishing a recomputed coordinator dataset.
        
        Parameters:
            _now (datetime): Scheduled callback time (unused).
        """
        self._pending_flip_unsub = None
        self.async_set_updated_data(self._compute())

    @callback
    def _cancel_pending_flip(self) -> None:
        """
        Cancel any scheduled pending flip for the cooling recommendation.
        
        If a point-in-time callback was previously scheduled, unsubscribe it and clear the internal unsubscribe handle.
        """
        if self._pending_flip_unsub is not None:
            self._pending_flip_unsub()
            self._pending_flip_unsub = None

    def _read(self, entity_id: str) -> float | None:
        """
        Read and parse a numeric state from Home Assistant, returning None for missing, unavailable, or non-numeric states.
        
        Parameters:
        	entity_id (str): Entity ID to read.
        
        Returns:
        	float | None: Parsed float value of the entity's state, or `None` if the state is absent, `unknown`, `unavailable`, or cannot be parsed as a number.
        """
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
        """
        Compute derived air-conditioning metrics from the configured temperature and humidity sensors.
        
        If either temperature or relative-humidity readings are unavailable, returns a PoorMansACData containing only those raw values. Otherwise returns a PoorMansACData populated with ambient pressure, absolute humidity (g/m³), mixing ratio (g_water/kg_air), heat index, partial derivatives of the heat index (d_hi/dt and d_hi/dx), the cooling-directed heat-index derivative (d_hi), and the debounced `cooling_recommended` boolean.
         
        Returns:
            PoorMansACData: Data object containing computed fields:
                - temperature: source temperature reading
                - humidity: source relative-humidity reading
                - pressure: estimated ambient pressure in Pa
                - absolute_humidity: absolute humidity in g/m³
                - mixing_ratio: mixing ratio exposed as g_water/kg_air
                - heat_index: computed heat index
                - d_hi_dt: partial derivative of heat index with respect to temperature
                - d_hi_dx: partial derivative of heat index with respect to mixing ratio
                - d_hi: heat-index cooling derivative used for decisioning
                - cooling_recommended: boolean indicating whether cooling is recommended after hysteresis
        """
        t = self._read(self._temperature_entity)
        rh = self._read(self._humidity_entity)
        if t is None or rh is None:
            return PoorMansACData(temperature=t, humidity=rh)

        pressure = self._read_pressure()
        x = calc.mixing_ratio(t, rh, pressure)
        d_hi = calc.d_hi_cooling(t, x, pressure, self._dx_dt)
        t_wb = calc.wet_bulb_temperature(t, x, pressure, self._dx_dt)

        return PoorMansACData(
            temperature=t,
            humidity=rh,
            pressure=pressure,
            absolute_humidity=calc.absolute_humidity(t, rh) * 1000.0,  # kg/m^3 -> g/m^3
            mixing_ratio=x * 1000.0,  # expose in g_water/kg_air
            heat_index=calc.heat_index(t, x, pressure),
            wet_bulb_temperature=t_wb,
            wet_bulb_depression=t - t_wb,
            optimal_water_uptake=calc.optimal_water_uptake(t, x, pressure, self._dx_dt)
            * 1000.0,  # expose in g_water/kg_air
            d_hi_dt=calc.d_hi_d_t(t, x, pressure),
            d_hi_dx=calc.d_hi_d_x(t, x, pressure),
            d_hi=d_hi,
            cooling_recommended=self._apply_hysteresis(d_hi < self._threshold),
        )
