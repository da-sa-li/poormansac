"""Constants for the Poor Man's AC integration."""

from __future__ import annotations

DOMAIN = "poormansac"

CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_PRESSURE_ENTITY = "pressure_entity"
CONF_THRESHOLD = "threshold"
CONF_MIN_HOLD_TIME = "min_hold_time"

DEFAULT_NAME = "Poor Man's AC"

# Cooling is recommended when dHI < threshold. The differential is the
# heat-index change per 1 K of evaporative cooling, so 0 is the natural
# break-even point (negative = comfort improves).
DEFAULT_THRESHOLD = 0.0

# Minimum time (minutes) the cooling_recommended state must hold before it is
# allowed to flip again. 0 = disabled (immediate flips).
DEFAULT_MIN_HOLD_TIME = 0

# Note: the isenthalpic process-line slope dx/dT is no longer a fixed constant.
# It is the x-dependent value -cp(x)/L derived in calc.process_line_slope.

# Ambient pressure in hectopascals used when computing the specific humidity x.
# Acts as the fallback whenever no pressure sensor is configured or the
# configured sensor is unavailable.
DEFAULT_PRESSURE_HPA = 1013.25
