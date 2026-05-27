"""Constants for the Poor Man's AC integration."""

from __future__ import annotations

DOMAIN = "poormansac"

CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_THRESHOLD = "threshold"
CONF_HYSTERESIS = "hysteresis"
CONF_AIR_DENSITY = "air_density"
CONF_HEAT_CAPACITY = "heat_capacity"

DEFAULT_NAME = "Poor Man's AC"

# Cooling is recommended when dHI < threshold. The differential is the
# heat-index change per 1 K of evaporative cooling, so 0 is the natural
# break-even point (negative = comfort improves).
DEFAULT_THRESHOLD = 0.0
# Symmetric hysteresis band [degC] around the threshold to avoid flapping.
DEFAULT_HYSTERESIS = 0.05

# Moist-air properties used in the adiabatic energy balance.
DEFAULT_AIR_DENSITY = 1.2  # kg/m^3
DEFAULT_HEAT_CAPACITY = 1006.0  # J/(kg*K)
