"""Thermodynamic calculations for the Poor Man's AC integration.

All functions are pure and unit-explicit:

* ``t``: temperature in degrees Celsius,
* ``rh``: relative humidity in percent (0-100),
* ``x``: specific humidity (water mass fraction) in kg_water / kg_moist_air,
* ``pressure``: ambient pressure in Pa.

The decision criterion is the total differential of the heat index along the
direct adiabatic (evaporative) cooling path.  The composed heat index is the
Rothfusz fit evaluated at the relative humidity that ``(T, x, p)`` imply through
the moist-air density ``rho = p / (R(x) * T)``, where ``R(x)`` is the
mass-weighted specific gas constant of moist air.  Because ``R(x)`` depends on
the water loading, ``x`` enters both numerator and denominator of the moisture
terms, so the closed forms below carry ``R(x)`` explicitly.  Along the
isenthalpic path ``p`` is constant, so only ``T`` and ``x`` vary:

    dHI = (dHI/dT) * dT + (dHI/dx) * dx

``dx/dT`` along the isenthalpic process line follows from the first law,
``0 = cp(x) dT + L dx``, hence ``dx/dT = -cp(x) / L`` (``process_line_slope``).
A negative ``dHI`` means evaporative cooling lowers the heat index and therefore
improves comfort.

These closed forms are the expanded Mathematica results from
``derivations/Diffrechnung Hitzeindex.nb`` (``Out[9]/Out[10]/Out[11]``),
transcribed verbatim.  They take ``t`` in degrees Celsius and form the absolute
temperature ``tk = t + 273.15`` internally, with the relative-humidity fit's
exponential carried over Kelvin at rates ``-0.0524`` (and ``-0.1048`` for the
squared moisture term).  The pressure enters in pascals directly, matching the
units the notebook computed in.
"""

from __future__ import annotations

import math

_R_V = 461.5  # specific gas constant of water vapour, J/(kg*K)
# Ratio of molar masses of water vapour and dry air used in the mixing ratio.
_EPSILON = 0.621945

# Specific gas constants R = R_universal / molar_mass, J/(kg*K), of dry air and
# water vapour.  They build the mass-weighted moist-air gas constant R(x) and
# the moist-air heat capacity cp(x) that the composed heat index and the
# isenthalpic process line depend on.
_R_DRY = 8.314 / 0.028949  # 287.1947217520467
_R_VAP = 8.314 / 0.01802  # 461.37624861265255

# Latent heat of vaporisation of water near 25 degC, J/kg (process line -cp/L).
_DHV = 2441.0 * 1000.0


def pressure_from_elevation(elevation: float) -> float:
    """Ambient pressure in Pa from elevation in metres (ISA standard atmosphere)."""
    return 101325.0 * (1.0 - 2.25577e-5 * elevation) ** 5.25588


def saturation_vapour_pressure(t: float) -> float:
    """Saturation vapour pressure over water in Pa (Magnus formula)."""
    return 611.2 * math.exp(17.62 * t / (243.12 + t))


def mixing_ratio(t: float, rh: float, pressure: float) -> float:
    """Water loading in kg_water / kg_dry_air from T, rel. humidity and p."""
    vapour_pressure = saturation_vapour_pressure(t) * rh / 100.0
    return _EPSILON * vapour_pressure / (pressure - vapour_pressure)


def specific_humidity(t: float, rh: float, pressure: float) -> float:
    """Specific humidity x in kg_water / kg_moist_air from T, rel. humidity and p.

    The water mass fraction of moist air; this is the ``x`` the heat-index
    derivation is expressed in (it feeds the mass-weighted moist-air gas
    constant ``R(x)``).  Equivalent to ``r / (1 + r)`` for mixing ratio ``r``.
    """
    vapour_pressure = saturation_vapour_pressure(t) * rh / 100.0
    return _EPSILON * vapour_pressure / (pressure - vapour_pressure * (1.0 - _EPSILON))


def _r_moist(x: float) -> float:
    """Mass-weighted specific gas constant of moist air, J/(kg*K)."""
    return _R_DRY * (1.0 - x) + _R_VAP * x


def cp_moist(x: float) -> float:
    """Specific heat capacity of moist air at constant pressure, J/(kg*K)."""
    return (1.0 - x) * 3.5 * _R_DRY + x * 4.0 * _R_VAP


def process_line_slope(x: float) -> float:
    """Isenthalpic process-line slope dx/dT in kg_water/(kg_moist_air*K).

    From the first law along the adiabatic (evaporative) cooling path,
    ``0 = cp(x) dT + L dx`` gives ``dx/dT = -cp(x) / L``.  Negative: as the air
    cools (dT < 0) the water loading rises (dx > 0).
    """
    return -cp_moist(x) / _DHV


def absolute_humidity(t: float, rh: float) -> float:
    """Water vapour density rho_w in kg/m^3 (SI) from T and rel. humidity."""
    vapour_pressure = saturation_vapour_pressure(t) * rh / 100.0
    return vapour_pressure / (_R_V * (t + 273.15))


def heat_index(t: float, x: float, pressure: float) -> float:
    """Heat index in degrees Celsius from temperature, specific humidity and pressure.

    Expanded closed form of the Rothfusz fit composed with the relative humidity
    that ``(t, x, pressure)`` imply (notebook ``Out[9]``, shifted to degrees
    Celsius).  ``tk = t + 273.15`` carries the RH-fit exponential over Kelvin and
    ``r = R(x)`` is the mass-weighted moist-air gas constant; ``pressure`` is in
    pascals.
    """
    tk = 273.15 + t
    tk2 = tk * tk
    e1 = math.exp(-0.0524 * tk)
    e2 = math.exp(-0.1048 * tk)
    r = _r_moist(x)
    r2 = r * r
    p = pressure
    p2 = p * p
    x2 = x * x
    t2 = t * t
    return (
        -8.784695
        + 1.61139411 * t
        - 0.012308094 * t2
        - 9.770671924498799e18 * e2 * p2 * x2 / (tk2 * r2)
        + 4.31555913666e17 * e2 * p2 * t * x2 / (tk2 * r2)
        - 2.1308318622e15 * e2 * p2 * t2 * x2 / (tk2 * r2)
        + 5.703721011e10 * e1 * p * x / (tk * r)
        - 3.5637704595e9 * e1 * p * t * x / (tk * r)
        + 5.3944143480000004e7 * e1 * p * t2 * x / (tk * r)
    )


def d_hi_d_t(t: float, x: float, pressure: float) -> float:
    """Partial derivative dHI/dT (notebook ``Out[10]``; degrees Celsius, p in Pa)."""
    tk = 273.15 + t
    tk2 = tk * tk
    tk3 = tk2 * tk
    e1 = math.exp(-0.0524 * tk)
    e2 = math.exp(-0.1048 * tk)
    r = _r_moist(x)
    r2 = r * r
    p = pressure
    p2 = p * p
    x2 = x * x
    t2 = t * t
    return (
        1.61139411
        - 0.024616188 * t
        + 1.9541343848997597e19 * e2 * p2 * x2 / (tk3 * r2)
        - 8.63111827332e17 * e2 * p2 * t * x2 / (tk3 * r2)
        + 4.2616637244e15 * e2 * p2 * t2 * x2 / (tk3 * r2)
        + 1.455522331353474e18 * e2 * p2 * x2 / (tk2 * r2)
        - 4.94887234765968e16 * e2 * p2 * t * x2 / (tk2 * r2)
        + 2.2331117915856e14 * e2 * p2 * t2 * x2 / (tk2 * r2)
        - 5.703721011e10 * e1 * p * x / (tk2 * r)
        + 3.5637704595e9 * e1 * p * t * x / (tk2 * r)
        - 5.3944143480000004e7 * e1 * p * t2 * x / (tk2 * r)
        - 6.552520269264e9 * e1 * p * x / (tk * r)
        + 2.946298590378e8 * e1 * p * t * x / (tk * r)
        - 2.826673118352e6 * e1 * p * t2 * x / (tk * r)
    )


def d_hi_d_x(t: float, x: float, pressure: float) -> float:
    """Partial derivative dHI/dx (notebook ``Out[11]``; degrees Celsius, p in Pa)."""
    tk = 273.15 + t
    tk2 = tk * tk
    e1 = math.exp(-0.0524 * tk)
    e2 = math.exp(-0.1048 * tk)
    r = _r_moist(x)
    r2 = r * r
    r3 = r2 * r
    p = pressure
    p2 = p * p
    x2 = x * x
    t2 = t * t
    return (
        3.40374110852651e21 * e2 * p2 * x2 / (tk2 * r3)
        - 1.5033813593613536e20 * e2 * p2 * t * x2 / (tk2 * r3)
        + 7.423030944824483e17 * e2 * p2 * t2 * x2 / (tk2 * r3)
        - 1.9541343848997597e19 * e2 * p2 * x / (tk2 * r2)
        + 8.63111827332e17 * e2 * p2 * t * x / (tk2 * r2)
        - 4.2616637244e15 * e2 * p2 * t2 * x / (tk2 * r2)
        - 9.934828344828984e12 * e1 * p * x / (tk * r2)
        + 6.20742980016433e11 * e1 * p * t * x / (tk * r2)
        - 9.396073276533997e9 * e1 * p * t2 * x / (tk * r2)
        + 5.703721011e10 * e1 * p / (tk * r)
        - 3.5637704595e9 * e1 * p * t / (tk * r)
        + 5.3944143480000004e7 * e1 * p * t2 / (tk * r)
    )


def d_hi_cooling(
    t: float,
    x: float,
    pressure: float,
    delta_t: float = -1.0,
) -> float:
    """Change of the heat index for ``delta_t`` K of evaporative cooling.

    Moves along the isenthalpic process line, whose slope ``dx/dT`` is the
    local ``process_line_slope(x)`` (negative: as the air cools the water
    loading rises).  The ambient ``pressure`` is constant along the path and
    only feeds the two partials.  With the default ``delta_t = -1`` K the result
    is the heat-index change per 1 K of evaporative cooling; a negative value
    means cooling improves comfort.
    """
    dx = process_line_slope(x) * delta_t
    return d_hi_d_t(t, x, pressure) * delta_t + d_hi_d_x(t, x, pressure) * dx


def wet_bulb_temperature(t: float, x: float, pressure: float) -> float:
    """Cooling limit (thermodynamic wet-bulb) temperature in degrees Celsius.

    Intersection of the isenthalpic cooling line through ``(t, x)`` with the
    saturation curve ``specific_humidity(t_wb, 100, pressure)``.  The line uses
    the local process-line slope at the starting state (its variation over the
    descent is well below a percent).  This is the lowest temperature direct
    evaporative cooling can reach.  For already saturated (or supersaturated)
    air the result is ``t`` itself.
    """
    if x >= specific_humidity(t, 100.0, pressure):
        return t
    dx_dt = process_line_slope(x)

    def excess(t_path: float) -> float:
        """Water loading on the cooling line minus saturation, at ``t_path``."""
        return x + dx_dt * (t_path - t) - specific_humidity(t_path, 100.0, pressure)

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


def optimal_water_uptake(t: float, x: float, pressure: float) -> float:
    """Comfort-optimal water uptake along the isenthalpic path, kg_water/kg_moist_air.

    Walks the isenthalpic cooling line from ``(t, x)`` for as long as the heat
    index still falls (``d_hi_cooling < 0``) and stops at the first sign
    change — the local heat-index minimum — or at saturation (the wet-bulb
    point), whichever comes first.  The result is the water-loading increase up
    to that point: the largest amount of water evaporative cooling should add.
    Zero when cooling does not improve comfort at the current state.
    """
    if d_hi_cooling(t, x, pressure) >= 0.0:
        return 0.0
    t_wb = wet_bulb_temperature(t, x, pressure)
    dx_dt = process_line_slope(x)

    def hi_falling(t_path: float) -> bool:
        x_path = x + dx_dt * (t_path - t)
        return d_hi_cooling(t_path, x_path, pressure) < 0.0

    # Coarse march keeps the *first* sign change; bisection then refines it.
    step = 0.25
    hi_end = t
    lo_end = max(t - step, t_wb)
    while hi_falling(lo_end):
        if lo_end <= t_wb:
            # + 0.0 normalises the -0.0 of already saturated air.
            return dx_dt * (t_wb - t) + 0.0
        hi_end = lo_end
        lo_end = max(lo_end - step, t_wb)
    for _ in range(50):
        mid = 0.5 * (lo_end + hi_end)
        if hi_falling(mid):
            hi_end = mid
        else:
            lo_end = mid
    return dx_dt * (0.5 * (lo_end + hi_end) - t)
