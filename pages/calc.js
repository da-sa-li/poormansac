// Port of custom_components/poormansac/calc.py and the model constants from
// const.py.  Keep in sync: any change to those files must be reflected here.
// The CI job "Rechner-Parität" (test.yml) enforces agreement automatically.

// ── model constants (from const.py) ──────────────────────────────────────
const DX_DT     = -0.00041;  // kg_water/(kg_air·K), isenthalpic line slope
const DELTA_T   = -1.0;      // K, cooling step for the differential
const THRESHOLD = 0.0;       // dHI < threshold → cooling recommended

// ── calc.py port (1:1 translation, same coefficient values) ───────────────
const _R_V     = 461.5;
const _EPSILON = 0.621945;

function saturation_vapour_pressure(t) {
    return 611.2 * Math.exp(17.62 * t / (243.12 + t));
}

function mixing_ratio(t, rh, pressure) {
    const vp = saturation_vapour_pressure(t) * rh / 100.0;
    return _EPSILON * vp / (pressure - vp);
}

function absolute_humidity(t, rh) {
    const vp = saturation_vapour_pressure(t) * rh / 100.0;
    return vp / (_R_V * (t + 273.15));
}

function heat_index(t, x, pressure) {
    const e1 = Math.exp(-0.0533 * t);
    const e2 = Math.exp(-0.1066 * t);
    const tk = 273.15 + t, tk2 = tk * tk;
    const p = pressure, p2 = p * p, x2 = x * x;
    return (
        -8.7847
        + 1.61139 * t
        - 0.0123081 * t * t
        + 134.599 * e1 * p * x / tk
        - 8.40997 * e1 * t * p * x / tk
        + 0.1273   * e1 * t * t * p * x / tk
        - 54.4119  * e2 * p2 * x2 / tk2
        + 2.40329  * e2 * t  * p2 * x2 / tk2
        - 0.0118664 * e2 * t * t * p2 * x2 / tk2
    );
}

function d_hi_d_t(t, x, pressure) {
    const e1 = Math.exp(-0.0533 * t);
    const e2 = Math.exp(-0.1066 * t);
    const tk = 273.15 + t, tk2 = tk * tk, tk3 = tk2 * tk;
    const p = pressure, p2 = p * p, x2 = x * x;
    return (
        1.61139
        - 0.0246162 * t
        - 134.599   * e1 * p  * x  / tk2
        + 8.40997   * e1 * t  * p  * x  / tk2
        - 0.1273    * e1 * t  * t  * p  * x  / tk2
        - 15.58410  * e1 * p  * x  / tk
        + 0.7028514 * e1 * t  * p  * x  / tk
        - 0.0067851 * e1 * t  * t  * p  * x  / tk
        + 108.8238  * e2 * p2 * x2 / tk3
        - 4.80658   * e2 * t  * p2 * x2 / tk3
        + 0.0237328 * e2 * t  * t  * p2 * x2 / tk3
        + 8.203599  * e2 * p2 * x2 / tk2
        - 0.2799235 * e2 * t  * p2 * x2 / tk2
        + 0.00126496 * e2 * t * t  * p2 * x2 / tk2
    );
}

function d_hi_d_x(t, x, pressure) {
    const e1 = Math.exp(-0.0533 * t);
    const e2 = Math.exp(-0.1066 * t);
    const tk = 273.15 + t, tk2 = tk * tk;
    const p = pressure, p2 = p * p;
    return (
        134.599   * e1 * p  / tk
        - 8.40997  * e1 * t  * p  / tk
        + 0.1273   * e1 * t  * t  * p  / tk
        - 108.8238 * e2 * p2 * x  / tk2
        + 4.80658  * e2 * t  * p2 * x  / tk2
        - 0.0237328 * e2 * t * t  * p2 * x  / tk2
    );
}

// Node.js export — conditional so browser execution is unaffected.
if (typeof module !== 'undefined') {
    module.exports = {
        DX_DT, DELTA_T, THRESHOLD,
        saturation_vapour_pressure,
        mixing_ratio,
        absolute_humidity,
        heat_index,
        d_hi_d_t,
        d_hi_d_x,
    };
}
