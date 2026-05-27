"""Thermodynamic calculations for the Poor Man's AC integration.

All functions are pure and unit-explicit:

* temperature ``t`` in degrees Celsius,
* relative humidity ``rh`` in percent (0-100),
* water vapour density / absolute humidity ``rho_w`` in g/m^3.

The decision criterion is the total differential of the heat index along the
direct adiabatic (evaporative) cooling path:

    dHI = (dHI/dT) * dT + (dHI/drho_w) * drho_w

``dHI/dT`` (:func:`d_hi_d_t`) and ``dHI/drho_w`` (:func:`d_hi_d_rho`) are the two
partial derivatives supplied as the project specification. ``dT`` and
``drho_w`` follow from the energy balance of the isenthalpic process
(:func:`drho_w_dt`). A negative ``dHI`` means evaporative cooling lowers the
heat index and therefore improves comfort.
"""

from __future__ import annotations

import math

# Gas constant for water vapour [J/(kg*K)].
_R_V = 461.5


def saturation_vapour_pressure(t: float) -> float:
    """Saturation vapour pressure over water in Pa (Magnus formula)."""
    return 611.2 * math.exp(17.62 * t / (243.12 + t))


def absolute_humidity(t: float, rh: float) -> float:
    """Water vapour density rho_w in g/m^3 from temperature and rel. humidity."""
    vapour_pressure = saturation_vapour_pressure(t) * rh / 100.0  # Pa
    rho_kg = vapour_pressure / (_R_V * (t + 273.15))  # kg/m^3
    return rho_kg * 1000.0


def latent_heat_of_vaporisation(t: float) -> float:
    """Latent heat of vaporisation of water in J/kg (linear fit)."""
    return (2500.8 - 2.36 * t) * 1000.0


def heat_index(t: float, rh: float) -> float:
    """Heat index in degrees Celsius (NWS Rothfusz regression)."""
    t_f = t * 9.0 / 5.0 + 32.0

    # Simple form is accurate enough at low apparent temperatures.
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
    """Partial derivative dHI/dT (first bracket of the specification)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    return (
        6.311786e-8 * rho_w * e2 * t**2
        - 1.94865e-5 * rho_w * e1 * t**2
        - 1.39655e-5 * rho_w * e2 * t
        + 0.00201855 * rho_w * e1 * t
        + 0.000409319 * rho_w * e2
        - 0.0447535 * rho_w * e1
        - 0.02462 * t
        + 1.61139
    )


def d_hi_d_rho(t: float) -> float:
    """Partial derivative dHI/drho_w (second bracket of the specification)."""
    e1 = math.exp(-0.0533 * t)
    e2 = math.exp(-0.1066 * t)
    e3 = math.exp(0.036 * t)
    return (
        2.01e-7 * e3 * t**2
        - 0.00012 * e1 * t**2
        - 0.000041 * e2 * t
        + 0.0082 * e1 * t
        + 0.00092 * e2
        - 0.13 * e1
    )


def drho_w_dt(t: float, air_density: float, heat_capacity: float) -> float:
    """Slope drho_w/dT [g/(m^3*K)] of the adiabatic evaporative path.

    Energy balance: the sensible heat released by cooling the air equals the
    latent heat absorbed by the evaporating water, so
    ``air_density * c_p * dT = -L * drho_w``. The result is negative: as the
    air cools (dT < 0) the vapour density rises (drho_w > 0).
    """
    return -1000.0 * air_density * heat_capacity / latent_heat_of_vaporisation(t)


def d_hi_cooling(
    t: float,
    rho_w: float,
    air_density: float,
    heat_capacity: float,
    delta_t: float = -1.0,
) -> float:
    """Change of the heat index for ``delta_t`` K of evaporative cooling.

    Evaluated as the total differential along the adiabatic path. With the
    default ``delta_t = -1`` K it is the heat-index change per 1 K of
    evaporative cooling; a negative value means cooling improves comfort.
    """
    d_rho = drho_w_dt(t, air_density, heat_capacity) * delta_t
    return d_hi_d_t(t, rho_w) * delta_t + d_hi_d_rho(t) * d_rho
