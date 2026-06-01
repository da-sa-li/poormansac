"""Thermodynamic calculations for the Poor Man's AC integration.

All functions are pure and unit-explicit:

* ``t``: temperature in degrees Celsius,
* ``rh``: relative humidity in percent (0-100),
* ``x``: water loading (mixing ratio) in kg_water / kg_dry_air,
* ``pressure``: ambient pressure in Pa.

The decision criterion is the total differential of the heat index along the
direct adiabatic (evaporative) cooling path, which uses the water loading
``x`` rather than the vapour density (``rho_w = x * rho_L`` with a variable
dry-air density ``rho_L``):

    dHI = (dHI/dT) * dT + (dHI/dx) * dx

``dx/dT`` along the isenthalpic process line is supplied as a configurable
constant.  A negative ``dHI`` means evaporative cooling lowers the heat index
and therefore improves comfort.
"""

from __future__ import annotations

import math

_R_V = 461.5  # specific gas constant of water vapour, J/(kg*K)
# Ratio of molar masses of water vapour and dry air used in the mixing ratio.
_EPSILON = 0.621945


def pressure_from_elevation(elevation: float) -> float:
    """Ambient pressure in Pa from elevation in metres (ISA standard atmosphere)."""
    return 101325.0 * (1.0 - 2.25577e-5 * elevation) ** 5.25588


def saturation_vapour_pressure(t: float) -> float:
    """Saturation vapour pressure over water in Pa (Magnus formula)."""
    return 611.2 * math.exp(17.62 * t / (243.12 + t))


def mixing_ratio(t: float, rh: float, pressure: float) -> float:
    """Water loading x in kg_water / kg_dry_air from T, rel. humidity and p."""
    vapour_pressure = saturation_vapour_pressure(t) * rh / 100.0
    return _EPSILON * vapour_pressure / (pressure - vapour_pressure)


def absolute_humidity(t: float, rh: float) -> float:
    """Water vapour density rho_w in kg/m^3 (SI) from T and rel. humidity."""
    vapour_pressure = saturation_vapour_pressure(t) * rh / 100.0
    return vapour_pressure / (_R_V * (t + 273.15))


def heat_index(t: float, x: float) -> float:
    """Heat index in degrees Celsius from temperature and water loading."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    tk = 273.15 + t
    tk2 = tk * tk
    x2 = x * x
    return (
        -8.7847
        + 1.61139 * t
        - 0.0123081 * t * t
        + 136.452 * e1 * tk * x
        - 8.5257 * e1 * t * tk * x
        + 0.129052 * e1 * t * t * tk * x
        - 55.9197 * e2 * tk2 * x2
        + 2.46989 * e2 * t * tk2 * x2
        - 0.0121952 * e2 * t * t * tk2 * x2
    )


def d_hi_d_t(t: float, x: float) -> float:
    """Partial derivative dHI/dT (Mathematica specification)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    tk = 273.15 + t
    tk2 = tk * tk
    x2 = x * x
    return (
        1.61139
        - 0.0246162 * t
        + 136.452 * e1 * x
        - 8.5257 * e1 * t * x
        + 0.129052 * e1 * t * t * x
        - 15.7986 * e1 * tk * x
        + 0.712523 * e1 * t * tk * x
        - 0.00687847 * e1 * t * t * tk * x
        - 111.839 * e2 * tk * x2
        + 4.93978 * e2 * t * tk * x2
        - 0.0243904 * e2 * t * t * tk * x2
        + 8.43093 * e2 * tk2 * x2
        - 0.287681 * e2 * t * tk2 * x2
        + 0.00130001 * e2 * t * t * tk2 * x2
    )


def d_hi_d_x(t: float, x: float) -> float:
    """Partial derivative dHI/dx (Mathematica specification)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    tk = 273.15 + t
    tk2 = tk * tk
    return (
        136.452 * e1 * tk
        - 8.5257 * e1 * t * tk
        + 0.129052 * e1 * t * t * tk
        - 111.839 * e2 * tk2 * x
        + 4.93978 * e2 * t * tk2 * x
        - 0.0243904 * e2 * t * t * tk2 * x
    )


def d_hi_cooling(
    t: float,
    x: float,
    dx_dt: float,
    delta_t: float = -1.0,
) -> float:
    """Change of the heat index for ``delta_t`` K of evaporative cooling.

    ``dx_dt`` is the slope of the isenthalpic process line as a pure ratio
    ``[kg_water/(kg_air*K)]`` (negative: as the air cools the water loading
    rises).  With the default ``delta_t = -1`` K the result is the heat-index
    change per 1 K of evaporative cooling; a negative value means cooling
    improves comfort.
    """
    dx = dx_dt * delta_t
    return d_hi_d_t(t, x) * delta_t + d_hi_d_x(t, x) * dx
