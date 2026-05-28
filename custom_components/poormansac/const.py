"""Constants for the Poor Man's AC integration."""

from __future__ import annotations

DOMAIN = "poormansac"

CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_THRESHOLD = "threshold"
CONF_HYSTERESIS = "hysteresis"
CONF_DRHO_W_DT = "drho_w_dt"

DEFAULT_NAME = "Poor Man's AC"

# Cooling is recommended when dHI < threshold. The differential is the
# heat-index change per 1 K of evaporative cooling, so 0 is the natural
# break-even point (negative = comfort improves).
DEFAULT_THRESHOLD = 0.0
# Symmetric hysteresis band [degC] around the threshold to avoid flapping.
DEFAULT_HYSTERESIS = 0.05

# Slope of the isenthalpic process line drho_w/dT [g/(m^3*K)]. Negative:
# as the air cools (dT < 0) the water vapour density rises (drho_w > 0).
# Default is the first-order approximation from the project specification.
DEFAULT_DRHO_W_DT = -0.34
