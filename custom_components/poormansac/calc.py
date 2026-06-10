"""Thermodynamic calculations for the Poor Man's AC integration.

All functions are pure and unit-explicit:

* ``t``: temperature in degrees Celsius,
* ``rh``: relative humidity in percent (0-100),
* ``x``: water loading (mixing ratio) in kg_water / kg_dry_air,
* ``pressure``: ambient pressure in Pa.

The decision criterion is the total differential of the heat index along the
direct adiabatic (evaporative) cooling path.  The heat index is a fit in the
water loading ``x`` (rather than the vapour density ``rho_w = x * rho_L`` with a
variable dry-air density ``rho_L``) and now carries the ambient pressure ``p``
explicitly.  Along the isenthalpic path ``p`` is constant, so only ``T`` and
``x`` vary:

    dHI = (dHI/dT) * dT + (dHI/dx) * dx

``dx/dT`` along the isenthalpic process line is supplied as a fixed model
constant (``const.DEFAULT_DX_DT``).  A negative ``dHI`` means evaporative
cooling lowers the heat index and therefore improves comfort.
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


def heat_index(t: float, x: float, pressure: float) -> float:
    """Heat index in degrees Celsius from temperature, water loading and pressure.

    The moisture dependence enters through the (vapour-pressure-like) product
    ``p * x``.  The pressure coefficients are the kPa-based Mathematica fit
    constants re-expressed per pascal, so the math stays in SI: the
    linear-in-``p`` constants are the fit values / 1e3 (e.g. 134599 -> 134.599)
    and the quadratic-in-``p`` ones / 1e6 (e.g. 5.44119e7 -> 54.4119).  The
    fit itself remains the documented exception that takes ``t`` in degrees
    Celsius and forms the absolute temperature ``tk = t + 273.15`` internally.
    """
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    tk = 273.15 + t
    tk2 = tk * tk
    p = pressure
    p2 = p * p
    x2 = x * x
    return (
        -8.7847
        + 1.61139 * t
        - 0.0123081 * t * t
        + 134.599 * e1 * p * x / tk
        - 8.40997 * e1 * t * p * x / tk
        + 0.1273 * e1 * t * t * p * x / tk
        - 54.4119 * e2 * p2 * x2 / tk2
        + 2.40329 * e2 * t * p2 * x2 / tk2
        - 0.0118664 * e2 * t * t * p2 * x2 / tk2
    )


def d_hi_d_t(t: float, x: float, pressure: float) -> float:
    """Partial derivative dHI/dT (analytic derivative of ``heat_index``, SI p)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    tk = 273.15 + t
    tk2 = tk * tk
    tk3 = tk2 * tk
    p = pressure
    p2 = p * p
    x2 = x * x
    return (
        1.61139
        - 0.0246162 * t
        - 134.599 * e1 * p * x / tk2
        + 8.40997 * e1 * t * p * x / tk2
        - 0.1273 * e1 * t * t * p * x / tk2
        - 15.58410 * e1 * p * x / tk
        + 0.7028514 * e1 * t * p * x / tk
        - 0.0067851 * e1 * t * t * p * x / tk
        + 108.8238 * e2 * p2 * x2 / tk3
        - 4.80658 * e2 * t * p2 * x2 / tk3
        + 0.0237328 * e2 * t * t * p2 * x2 / tk3
        + 8.203599 * e2 * p2 * x2 / tk2
        - 0.2799235 * e2 * t * p2 * x2 / tk2
        + 0.00126496 * e2 * t * t * p2 * x2 / tk2
    )


def d_hi_d_x(t: float, x: float, pressure: float) -> float:
    """Partial derivative dHI/dx (analytic derivative of ``heat_index``, SI p)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    tk = 273.15 + t
    tk2 = tk * tk
    p = pressure
    p2 = p * p
    return (
        134.599 * e1 * p / tk
        - 8.40997 * e1 * t * p / tk
        + 0.1273 * e1 * t * t * p / tk
        - 108.8238 * e2 * p2 * x / tk2
        + 4.80658 * e2 * t * p2 * x / tk2
        - 0.0237328 * e2 * t * t * p2 * x / tk2
    )


def d_hi_cooling(
    t: float,
    x: float,
    pressure: float,
    dx_dt: float,
    delta_t: float = -1.0,
) -> float:
    """Change of the heat index for ``delta_t`` K of evaporative cooling.

    ``dx_dt`` is the slope of the isenthalpic process line as a pure ratio
    ``[kg_water/(kg_air*K)]`` (negative: as the air cools the water loading
    rises).  The ambient ``pressure`` is constant along the path and only feeds
    the two partials.  With the default ``delta_t = -1`` K the result is the
    heat-index change per 1 K of evaporative cooling; a negative value means
    cooling improves comfort.
    """
    dx = dx_dt * delta_t
    return d_hi_d_t(t, x, pressure) * delta_t + d_hi_d_x(t, x, pressure) * dx


def wet_bulb_temperature(t: float, x: float, pressure: float, dx_dt: float) -> float:
    """Cooling limit (thermodynamic wet-bulb) temperature in degrees Celsius.

    Intersection of the isenthalpic cooling line through ``(t, x)`` — the same
    straight line with slope ``dx_dt`` that ``d_hi_cooling`` differentiates
    along — with the saturation curve ``mixing_ratio(t_wb, 100, pressure)``.
    This is the lowest temperature direct evaporative cooling can reach.  For
    already saturated (or supersaturated) air the result is ``t`` itself.
    """
    if x >= mixing_ratio(t, 100.0, pressure):
        return t

    def excess(t_path: float) -> float:
        """Water loading on the cooling line minus saturation, at ``t_path``."""
        return x + dx_dt * (t_path - t) - mixing_ratio(t_path, 100.0, pressure)

    lo = t - 60.0
    while excess(lo) < 0.0:
        lo -= 60.0
    hi = t
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if excess(mid) >= 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
