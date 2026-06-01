"""Unit tests for the pure thermodynamic calculations in ``calc.py``.

``calc.py`` depends only on the standard library, so these tests run under plain
``pytest`` without a Home Assistant test harness (see ``conftest.py`` for the
import-path setup).
"""

from __future__ import annotations

import pytest

import calc
import const

# Standard sea-level pressure used across several tests.
P0 = 101325.0  # Pa


# --- 1. Reference values (physical anchor points) ------------------------


def test_saturation_vapour_pressure_reference():
    # Magnus prefactor at the reference temperature (Pa).
    assert calc.saturation_vapour_pressure(0.0) == pytest.approx(611.2)
    # ~3.16 kPa at 25 C.
    assert calc.saturation_vapour_pressure(25.0) == pytest.approx(3160.0, rel=1e-3)


def test_pressure_from_elevation_sea_level():
    assert calc.pressure_from_elevation(0.0) == pytest.approx(101325.0)


def test_mixing_ratio_reference():
    # ~9.85 g/kg at 25 C / 50 % / 1013.25 hPa, expressed in kg/kg.
    assert calc.mixing_ratio(25.0, 50.0, P0) == pytest.approx(0.009852, rel=1e-3)


def test_heat_index_reference():
    x = calc.mixing_ratio(25.0, 50.0, P0)
    assert calc.heat_index(25.0, x) == pytest.approx(25.8, abs=0.1)


# --- 2. Unit guards (SI) -------------------------------------------------


def test_absolute_humidity_is_si_kg_per_m3():
    # ~0.0115 kg/m^3, NOT ~11.5 g/m^3 -- guards an accidental *1000.
    ah = calc.absolute_humidity(25.0, 50.0)
    assert ah == pytest.approx(0.01148, rel=1e-3)
    assert ah < 1.0


def test_default_dx_dt_is_si_and_matches_physics():
    # dx/dT ~ -cp/L, of order 1e-4 kg/(kg*K) -- guards a g- vs kg-unit mixup.
    assert const.DEFAULT_DX_DT == pytest.approx(-1005.0 / 2.45e6, rel=0.05)
    assert abs(const.DEFAULT_DX_DT) < 1e-3


# --- 3. Derivative consistency (finite differences) ----------------------
#
# heat_index, d_hi_d_t and d_hi_d_x are hand-derived from a Mathematica
# specification; these tests verify the analytic partials really are the
# derivatives of heat_index, without duplicating the coefficients.

DERIV_POINTS = [
    (20.0, 0.005),
    (25.0, 0.010),
    (30.0, 0.015),
    (35.0, 0.020),
]


@pytest.mark.parametrize("t, x", DERIV_POINTS)
def test_d_hi_d_t_matches_finite_difference(t, x):
    h = 1e-6
    fd = (calc.heat_index(t + h, x) - calc.heat_index(t - h, x)) / (2.0 * h)
    assert calc.d_hi_d_t(t, x) == pytest.approx(fd, rel=1e-4)


@pytest.mark.parametrize("t, x", DERIV_POINTS)
def test_d_hi_d_x_matches_finite_difference(t, x):
    h = 1e-6
    fd = (calc.heat_index(t, x + h) - calc.heat_index(t, x - h)) / (2.0 * h)
    assert calc.d_hi_d_x(t, x) == pytest.approx(fd, rel=1e-4)


# --- 4. Invariants / properties (value-free) -----------------------------


def test_dry_air_has_zero_water():
    assert calc.mixing_ratio(25.0, 0.0, P0) == 0.0
    assert calc.absolute_humidity(25.0, 0.0) == 0.0


def test_absolute_humidity_linear_in_rh():
    # rho_w = e_sat * (rh/100) / (R_v * T) is exactly linear in rh.
    assert calc.absolute_humidity(25.0, 100.0) == pytest.approx(
        2.0 * calc.absolute_humidity(25.0, 50.0)
    )


def test_saturation_vapour_pressure_monotonic():
    assert (
        calc.saturation_vapour_pressure(10.0)
        < calc.saturation_vapour_pressure(20.0)
        < calc.saturation_vapour_pressure(30.0)
    )


def test_mixing_ratio_increases_with_humidity():
    assert calc.mixing_ratio(25.0, 40.0, P0) < calc.mixing_ratio(25.0, 80.0, P0)


def test_pressure_decreases_with_elevation():
    assert calc.pressure_from_elevation(0.0) > calc.pressure_from_elevation(1000.0)


# --- 5. d_hi_cooling: composition, default, regression -------------------


def test_d_hi_cooling_composition():
    t, x, dx_dt, delta_t = 28.0, 0.012, -0.00041, -1.0
    expected = calc.d_hi_d_t(t, x) * delta_t + calc.d_hi_d_x(t, x) * dx_dt * delta_t
    assert calc.d_hi_cooling(t, x, dx_dt, delta_t) == pytest.approx(expected)


def test_d_hi_cooling_default_delta_t_is_minus_one():
    t, x, dx_dt = 25.0, 0.009852, -0.00041
    assert calc.d_hi_cooling(t, x, dx_dt) == pytest.approx(
        calc.d_hi_cooling(t, x, dx_dt, -1.0)
    )


def test_d_hi_cooling_regression():
    x = calc.mixing_ratio(25.0, 50.0, P0)
    assert calc.d_hi_cooling(25.0, x, const.DEFAULT_DX_DT) == pytest.approx(
        -0.4223, rel=1e-3
    )
