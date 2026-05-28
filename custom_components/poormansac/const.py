"""Constants for the Poor Man's AC integration."""

from __future__ import annotations

DOMAIN = "poormansac"

CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_THRESHOLD = "threshold"
CONF_DX_DT = "dx_dt"
CONF_PRESSURE = "pressure"

DEFAULT_NAME = "Poor Man's AC"

# Cooling is recommended when dHI < threshold. The differential is the
# heat-index change per 1 K of evaporative cooling, so 0 is the natural
# break-even point (negative = comfort improves).
DEFAULT_THRESHOLD = 0.0

# Slope of the isenthalpic process line dx/dT in g_water/(kg_air*K). Negative:
# as the air cools (dT < 0) the water loading rises (dx > 0). Default is the
# first-order approximation from the project specification.
DEFAULT_DX_DT = -0.41

# Ambient pressure in hectopascals used when computing the mixing ratio x.
DEFAULT_PRESSURE_HPA = 1013.25
