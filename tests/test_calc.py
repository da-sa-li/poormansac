"""Unit tests for the pure thermodynamic calculations in ``calc.py``.

``calc.py`` depends only on the standard library, so these tests run under plain
``pytest`` without a Home Assistant test harness (see ``conftest.py`` for the
import-path setup).
"""

from __future__ import annotations

import pytest

import calc
import const

# Every test in this module exercises the pure thermodynamic calculations in
# ``calc.py``; the ``thermodynamics`` marker lets the CI job of the same name
# select exactly these tests (see ``pytest.ini`` and ``.github/workflows/test.yml``).
pytestmark = pytest.mark.thermodynamics

# Standard sea-level pressure used across several tests.
P0 = 101325.0  # Pa


# --- 1. Reference values (physical anchor points) ------------------------


def test_saturation_vapour_pressure_reference():
    """Magnus formula reproduces known anchor values at 0 C and 25 C."""
    # Magnus prefactor at the reference temperature (Pa).
    assert calc.saturation_vapour_pressure(0.0) == pytest.approx(611.2)
    # ~3.16 kPa at 25 C.
    assert calc.saturation_vapour_pressure(25.0) == pytest.approx(3160.0, rel=1e-3)


def test_pressure_from_elevation_sea_level():
    """ISA pressure at sea level is the standard 101325 Pa."""
    assert calc.pressure_from_elevation(0.0) == pytest.approx(101325.0)


def test_mixing_ratio_reference():
    """Mixing ratio at 25 C / 50 % / 1013 hPa matches the textbook ~9.85 g/kg."""
    # ~9.85 g/kg at 25 C / 50 % / 1013.25 hPa, expressed in kg/kg.
    assert calc.mixing_ratio(25.0, 50.0, P0) == pytest.approx(0.009852, rel=1e-3)


def test_heat_index_reference():
    """Heat index at 25 C / 50 % stays close to the dry-bulb temperature."""
    x = calc.mixing_ratio(25.0, 50.0, P0)
    assert calc.heat_index(25.0, x, P0) == pytest.approx(25.9, abs=0.1)


# --- 2. Unit guards (SI) -------------------------------------------------


def test_absolute_humidity_is_si_kg_per_m3():
    """absolute_humidity returns kg/m^3 (SI), guarding an accidental *1000."""
    # ~0.0115 kg/m^3, NOT ~11.5 g/m^3 -- guards an accidental *1000.
    ah = calc.absolute_humidity(25.0, 50.0)
    assert ah == pytest.approx(0.01148, rel=1e-3)
    assert ah < 1.0


def test_default_dx_dt_is_si_and_matches_physics():
    """DEFAULT_DX_DT is the SI ~-cp/L value, guarding a g- vs kg-unit mixup."""
    # dx/dT ~ -cp/L, of order 1e-4 kg/(kg*K) -- guards a g- vs kg-unit mixup.
    assert const.DEFAULT_DX_DT == pytest.approx(-1005.0 / 2.45e6, rel=0.05)
    assert abs(const.DEFAULT_DX_DT) < 1e-3


# --- 3. Derivative consistency (finite differences) ----------------------
#
# heat_index, d_hi_d_t and d_hi_d_x are hand-derived from a Mathematica
# specification; these tests verify the analytic partials really are the
# derivatives of heat_index, without duplicating the coefficients.

DERIV_POINTS = [
    (20.0, 0.005, 101325.0),
    (25.0, 0.010, 95000.0),
    (30.0, 0.015, 101325.0),
    (35.0, 0.020, 90000.0),
]


@pytest.mark.parametrize("t, x, p", DERIV_POINTS)
def test_d_hi_d_t_matches_finite_difference(t, x, p):
    """Analytic d_hi_d_t equals the numeric d(heat_index)/dt at each point."""
    h = 1e-6
    fd = (calc.heat_index(t + h, x, p) - calc.heat_index(t - h, x, p)) / (2.0 * h)
    assert calc.d_hi_d_t(t, x, p) == pytest.approx(fd, rel=1e-4)


@pytest.mark.parametrize("t, x, p", DERIV_POINTS)
def test_d_hi_d_x_matches_finite_difference(t, x, p):
    """Analytic d_hi_d_x equals the numeric d(heat_index)/dx at each point."""
    h = 1e-6
    fd = (calc.heat_index(t, x + h, p) - calc.heat_index(t, x - h, p)) / (2.0 * h)
    assert calc.d_hi_d_x(t, x, p) == pytest.approx(fd, rel=1e-4)


# --- 4. Invariants / properties (value-free) -----------------------------


def test_dry_air_has_zero_water():
    """At 0 % relative humidity the air holds no water."""
    assert calc.mixing_ratio(25.0, 0.0, P0) == 0.0
    assert calc.absolute_humidity(25.0, 0.0) == 0.0


def test_absolute_humidity_linear_in_rh():
    """absolute_humidity is exactly linear in relative humidity."""
    # rho_w = e_sat * (rh/100) / (R_v * T) is exactly linear in rh.
    assert calc.absolute_humidity(25.0, 100.0) == pytest.approx(
        2.0 * calc.absolute_humidity(25.0, 50.0)
    )


def test_saturation_vapour_pressure_monotonic():
    """Saturation vapour pressure increases with temperature."""
    assert (
        calc.saturation_vapour_pressure(10.0)
        < calc.saturation_vapour_pressure(20.0)
        < calc.saturation_vapour_pressure(30.0)
    )


def test_mixing_ratio_increases_with_humidity():
    """Mixing ratio increases with relative humidity at fixed T and P."""
    assert calc.mixing_ratio(25.0, 40.0, P0) < calc.mixing_ratio(25.0, 80.0, P0)


def test_pressure_decreases_with_elevation():
    """ISA pressure decreases with elevation."""
    assert calc.pressure_from_elevation(0.0) > calc.pressure_from_elevation(1000.0)


# --- 5. d_hi_cooling: composition, default, regression -------------------


def test_d_hi_cooling_composition():
    """d_hi_cooling is the total differential built from the two partials."""
    t, x, p, dx_dt, delta_t = 28.0, 0.012, P0, -0.00041, -1.0
    expected = (
        calc.d_hi_d_t(t, x, p) * delta_t + calc.d_hi_d_x(t, x, p) * dx_dt * delta_t
    )
    assert calc.d_hi_cooling(t, x, p, dx_dt, delta_t) == pytest.approx(expected)


def test_d_hi_cooling_default_delta_t_is_minus_one():
    """d_hi_cooling defaults to a 1 K cooling step (delta_t = -1.0)."""
    t, x, dx_dt = 25.0, 0.009852, -0.00041
    assert calc.d_hi_cooling(t, x, P0, dx_dt) == pytest.approx(
        calc.d_hi_cooling(t, x, P0, dx_dt, -1.0)
    )


def test_d_hi_cooling_regression():
    """d_hi_cooling at 25 C / 50 % stays at its known reference value."""
    x = calc.mixing_ratio(25.0, 50.0, P0)
    assert calc.d_hi_cooling(25.0, x, P0, const.DEFAULT_DX_DT) == pytest.approx(
        -0.5300, rel=1e-3
    )


# --- 6. Cooling recommendation: sign-based scenarios ---------------------
#
# The binary "cool or not" decision is: d_hi_cooling < 0  →  cooling helps.
# Two physically contrasting scenarios anchor the sign:
#   * Hot + dry: evaporative cooling reduces the heat index  → recommend ON.
#   * Hot + saturated: air is already near-saturated, adding moisture raises
#     the heat index further                                 → recommend OFF.


def test_d_hi_cooling_recommends_on_when_hot_and_dry():
    """Hot, dry air (35 C / 20 % rF): evaporative cooling lowers heat index."""
    x = calc.mixing_ratio(35.0, 20.0, P0)
    assert calc.d_hi_cooling(35.0, x, P0, const.DEFAULT_DX_DT) < 0


def test_d_hi_cooling_recommends_off_when_already_saturated():
    """Very hot, near-saturated air (40 C / 90 % rF): cooling raises heat index."""
    x = calc.mixing_ratio(40.0, 90.0, P0)
    assert calc.d_hi_cooling(40.0, x, P0, const.DEFAULT_DX_DT) > 0


# --- 7. Wet-bulb temperature (cooling limit) ------------------------------


def test_wet_bulb_temperature_reference():
    """Model wet bulb at 30 C / 50 % matches the psychrometric ~22 C."""
    x = calc.mixing_ratio(30.0, 50.0, P0)
    t_wb = calc.wet_bulb_temperature(30.0, x, P0, const.DEFAULT_DX_DT)
    assert t_wb == pytest.approx(22.0, abs=0.3)


def test_wet_bulb_temperature_lies_on_saturation_curve():
    """The result is the root: the cooling line meets the saturation curve."""
    t, rh = 35.0, 40.0
    x = calc.mixing_ratio(t, rh, P0)
    t_wb = calc.wet_bulb_temperature(t, x, P0, const.DEFAULT_DX_DT)
    x_path = x + const.DEFAULT_DX_DT * (t_wb - t)
    assert x_path == pytest.approx(calc.mixing_ratio(t_wb, 100.0, P0), rel=1e-9)


def test_wet_bulb_temperature_saturated_air_equals_dry_bulb():
    """At 100 % relative humidity no evaporative cooling is possible."""
    x = calc.mixing_ratio(30.0, 100.0, P0)
    assert calc.wet_bulb_temperature(30.0, x, P0, const.DEFAULT_DX_DT) == 30.0


def test_wet_bulb_depression_shrinks_with_humidity():
    """Drier air allows more evaporative cooling (larger depression)."""
    depressions = []
    for rh in (20.0, 50.0, 80.0, 95.0):
        x = calc.mixing_ratio(30.0, rh, P0)
        t_wb = calc.wet_bulb_temperature(30.0, x, P0, const.DEFAULT_DX_DT)
        assert t_wb < 30.0
        depressions.append(30.0 - t_wb)
    assert depressions == sorted(depressions, reverse=True)
