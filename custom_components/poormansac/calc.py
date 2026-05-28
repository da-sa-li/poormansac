"""Thermodynamic calculations for the Poor Man's AC integration.

All functions are pure and unit-explicit:

* temperature ``t`` in degrees Celsius,
* relative humidity ``rh`` in percent (0-100),
* water vapour density / absolute humidity ``rho_w`` in g/m^3.

The decision criterion is the total differential of the heat index along the
direct adiabatic (evaporative) cooling path:

    dHI = (dHI/dT) * dT + (dHI/drho_w) * drho_w

``dHI/dT`` (:func:`d_hi_d_t`) and ``dHI/drho_w`` (:func:`d_hi_d_rho`) are the
two partial derivatives supplied as the project specification (Mathematica).
``drho_w/dT`` along the isenthalpic process is supplied as a configurable
constant.  A negative ``dHI`` means evaporative cooling lowers the heat index
and therefore improves comfort.
"""

from __future__ import annotations

import math

_R_V = 461.5  # specific gas constant of water vapour, J/(kg*K)


def saturation_vapour_pressure(t: float) -> float:
    """Saturation vapour pressure over water in Pa (Magnus formula)."""
    return 611.2 * math.exp(17.62 * t / (243.12 + t))


def absolute_humidity(t: float, rh: float) -> float:
    """Water vapour density rho_w in g/m^3 from temperature and rel. humidity."""
    vapour_pressure = saturation_vapour_pressure(t) * rh / 100.0  # Pa
    rho_kg = vapour_pressure / (_R_V * (t + 273.15))  # kg/m^3
    return rho_kg * 1000.0


def heat_index(t: float, rh: float) -> float:
    """Heat index in degrees Celsius (NWS Rothfusz regression)."""
    t_f = t * 9.0 / 5.0 + 32.0
    simple = 0.5 * (t_f + 61.0 + (t_f - 68.0) * 1.2 + rh * 0.094)
    if (simple + t_f) / 2.0 < 80.0:
        return (simple - 32.0) * 5.0 / 9.0

    hi_f = (
        -42.379
        + 2.04901523 * t_f
        + 10.14333127 * rh
        - 0.22475541 * t_f * rh
        - 6.83783e-3 * t_f**2
        - 5.481717e-2 * rh**2
        + 1.22874e-3 * t_f**2 * rh
        + 8.5282e-4 * t_f * rh**2
        - 1.99e-6 * t_f**2 * rh**2
    )

    if rh < 13.0 and 80.0 <= t_f <= 112.0:
        hi_f -= ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
    elif rh > 85.0 and 80.0 <= t_f <= 87.0:
        hi_f += ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)

    return (hi_f - 32.0) * 5.0 / 9.0


def d_hi_d_t(t: float, rho_w: float) -> float:
    """Partial derivative dHI/dT (Mathematica specification)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    rho2 = rho_w * rho_w
    return (
        1.61139
        - 0.0246162 * t
        - 0.0447567 * e1 * rho_w
        + 0.00201855 * e1 * t * rho_w
        - 0.0000194864 * e1 * t * t * rho_w
        + 0.0000676639 * e2 * rho2
        - 2.30883e-6 * e2 * t * rho2
        + 1.04335e-8 * e2 * t * t * rho2
    )


def d_hi_d_rho(t: float, rho_w: float) -> float:
    """Partial derivative dHI/drho_w (Mathematica specification)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    return (
        0.386562 * e1
        - 0.024153 * e1 * t
        + 0.000365599 * e1 * t * t
        - 0.000897587 * e2 * rho_w
        + 0.0000396451 * e2 * t * rho_w
        - 1.9575e-7 * e2 * t * t * rho_w
    )


def d_hi_cooling(
    t: float,
    rho_w: float,
    drho_w_dt: float,
    delta_t: float = -1.0,
) -> float:
    """Change of the heat index for ``delta_t`` K of evaporative cooling.

    ``drho_w_dt`` is the slope of the isenthalpic process line in
    ``g/(m^3*K)`` (negative: as the air cools the vapour density rises).
    With the default ``delta_t = -1`` K the result is the heat-index change
    per 1 K of evaporative cooling; a negative value means cooling improves
    comfort.
    """
    d_rho = drho_w_dt * delta_t
    return d_hi_d_t(t, rho_w) * delta_t + d_hi_d_rho(t, rho_w) * d_rho
