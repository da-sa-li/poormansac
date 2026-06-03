#!/usr/bin/env python3
"""Emit JSON reference values from calc.py; consumed by test_calc_parity.js."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "custom_components" / "poormansac"))
import calc  # noqa: E402

_TEST_CASES = [
    # (T °C, RH %, p hPa)
    (25.0, 50.0, 1013.25),  # standard reference
    (35.0, 20.0, 1013.25),  # hot + dry  → cooling ON
    (40.0, 90.0, 1013.25),  # hot + humid → cooling OFF
    (30.0, 60.0,  950.0),   # lower pressure
    (15.0, 80.0, 1013.25),  # cool + humid
]

rows = []
for t, rh, p_hpa in _TEST_CASES:
    p = p_hpa * 100.0
    x = calc.mixing_ratio(t, rh, p)
    rows.append({
        "t": t,
        "rh": rh,
        "p_hpa": p_hpa,
        "mixing_ratio": x,
        "absolute_humidity": calc.absolute_humidity(t, rh),
        "heat_index": calc.heat_index(t, x, p),
        "d_hi_d_t": calc.d_hi_d_t(t, x, p),
        "d_hi_d_x": calc.d_hi_d_x(t, x, p),
    })

json.dump(rows, sys.stdout, indent=2)
sys.stdout.write("\n")
