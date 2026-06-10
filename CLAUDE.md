# CLAUDE.md

Guidance for working in this repository.

## Project

Poor Man's AC is a Home Assistant integration that decides, on thermodynamic
grounds, whether direct adiabatic (evaporative) cooling improves indoor
comfort. It uses the heat index as the comfort measure and the total
differential of the heat index along the isenthalpic cooling path as the
decision criterion.

- Core math: `custom_components/poormansac/calc.py` (pure, depends only on
  `math`).
- State wiring / Home Assistant glue: `custom_components/poormansac/coordinator.py`.
- Entities: `sensor.py`, `binary_sensor.py`.

## Units / Conventions

**The background math runs in SI units. Unit conversions live only at the
boundary** (Home Assistant entity I/O, configuration, and display) — never
inside the math functions in `calc.py`.

- **Pressure**: Pa internally. Sensor readings are converted with
  `PressureConverter`, and the human-facing hPa fallback
  (`DEFAULT_PRESSURE_HPA`) is converted to Pa in the coordinator.
- **Mixing ratio `x`**: kg_water/kg_dry_air (dimensionless). Exposed to the
  `mixing_ratio` sensor as g/kg (×1000 at the boundary).
- **Absolute humidity** (`calc.absolute_humidity`): kg/m³ internally. Exposed
  to the `absolute_humidity` sensor as g/m³ (×1000 at the boundary in the
  coordinator).
- **`dx/dT`** (`DEFAULT_DX_DT`): kg_water/(kg_air·K) — the SI unit that matches
  `x`, so it is passed to `calc.d_hi_cooling` directly, without conversion.
  Physical first-order value ≈ −cp/L from the adiabatic energy balance.

### Internal model constants vs. boundary I/O values

Keep the distinction clear:

- A **model constant** that feeds the math directly (e.g. `DEFAULT_DX_DT`) is
  stored in its SI unit so no conversion is needed at the call site.
- A **boundary I/O value** that mirrors a human-facing unit (e.g. the pressure
  fallback in hPa, or sensor inputs) is converted to SI once, at the boundary.

### Documented exception: temperature

The heat-index polynomial in `calc.py` (`heat_index`, `d_hi_d_t`, `d_hi_d_x`)
is an **empirical fit in degrees Celsius**, mixed with the absolute temperature
`tk = t + 273.15` where the fit requires it. The calc functions therefore take
temperature in **°C**, not Kelvin. Note that `dHI/dT` has the same numeric
value in °C or K, because it is a per-kelvin *interval* derivative.

The same fit also carries the ambient **pressure** through the moisture term
(the vapour-pressure-like product `p * x`). The fit was produced with `p` in
**kPa**, but its *coefficients* are stored **per pascal** (linear-in-`p` ÷ 1e3,
quadratic-in-`p` ÷ 1e6) — these coefficients are the model constants kept in SI
— so the functions take pressure in **Pa** like the rest of the math. The
`pressure` value itself is still a **boundary I/O** input, not a model constant:
it is converted to SI once in the coordinator and then passed through unchanged
at the call site.

When adding a value: if it feeds the math directly, express it in SI; if it
crosses the entity/config boundary, convert it there, not inside `calc.py`.

## Priorities

**The Home Assistant integration is the primary deliverable.** Everything in
`custom_components/` takes precedence. When the integration and the website
are in tension, resolve it in favour of the integration — never the other way
around.

The GitHub Pages calculator (`docs/`) is a secondary artefact: a convenience
tool for testing extreme values and an explainer for interested readers. It has
no influence on HA behaviour and must never drive changes to the integration
code.

Consequence: the calculator runs `calc.py` and `const.py` **directly** in the
browser via Pyodide (CPython compiled to WebAssembly), so there is a single
source of truth and no JavaScript re-implementation to keep in sync. Changes to
the integration math reach the website automatically — there is nothing to port
and no parity test to satisfy.

## Website (`docs/`)

- `docs/index.html` — single-file static calculator. It loads Pyodide from a
  CDN, fetches the integration's own `calc.py` and `const.py`, and executes them
  in the browser. The page itself contains only UI logic (input validation,
  psychrometric chart, DOM rendering). No build step.
- **Source loading:** `index.html` tries the repo-relative path
  `../custom_components/poormansac/` first (works when a local server is started
  from the repository root) and falls back to
  `raw.githubusercontent.com/da-sa-li/poormansac/main/...` for the deployed
  GitHub Pages site, where `docs/` is the web root.
- **Constants:** `DX_DT` and `THRESHOLD` come from `const.py`
  (`DEFAULT_DX_DT` / `DEFAULT_THRESHOLD`); `DELTA_T` is read from the default of
  `calc.d_hi_cooling`. None are duplicated in the page.

**When changing the integration math or constants:** nothing extra is required —
the website executes `calc.py`/`const.py` as-is. Just keep the public function
names and the `DEFAULT_*` constant names stable, since `index.html` looks them
up by name.

## Dev

- Quick syntax check: `python3 -m py_compile custom_components/poormansac/*.py`.
- `calc.py` is pure and can be imported standalone to sanity-check numbers.
- CI (`.github/workflows/validate.yml`) runs Home Assistant **hassfest** on
  push and pull request.
- CI (`.github/workflows/test.yml`) runs Python unit tests (`pytest -m
  thermodynamics`).
