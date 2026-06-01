"""Constants for the Poor Man's AC integration."""

from __future__ import annotations

DOMAIN = "poormansac"

CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_PRESSURE_ENTITY = "pressure_entity"
CONF_THRESHOLD = "threshold"

DEFAULT_NAME = "Poor Man's AC"

# Cooling is recommended when dHI < threshold. The differential is the
# heat-index change per 1 K of evaporative cooling, so 0 is the natural
# break-even point (negative = comfort improves).
DEFAULT_THRESHOLD = 0.0

# Slope of the isenthalpic process line dx/dT in kg_water/(kg_air*K) (SI unit,
# matching the mixing ratio x, so it feeds the calc functions directly without
# conversion). Negative: as the air cools (dT < 0) the water loading rises
# (dx > 0). First-order approximation -cp/L from the adiabatic energy balance.
DEFAULT_DX_DT = -0.00041

# Ambient pressure in hectopascals used when computing the mixing ratio x.
# Acts as the fallback whenever no pressure sensor is configured or the
# configured sensor is unavailable.
DEFAULT_PRESSURE_HPA = 1013.25
