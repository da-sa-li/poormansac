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
- **Specific humidity `x`**: kg_water/kg_moist_air (water mass fraction,
  dimensionless). This is the variable the heat-index derivation is expressed
  in (it feeds the mass-weighted moist-air gas constant `R(x)`). Computed at the
  boundary by `calc.specific_humidity` and exposed to the `specific_humidity`
  sensor as g/kg (×1000 at the boundary). `calc.mixing_ratio`
  (kg_water/kg_dry_air) still exists as a utility but is not used by the
  integration.
- **Absolute humidity** (`calc.absolute_humidity`): kg/m³ internally. Exposed
  to the `absolute_humidity` sensor as g/m³ (×1000 at the boundary in the
  coordinator).
- **`dx/dT`** (`calc.process_line_slope`): kg_water/(kg_air·K). No longer a
  fixed constant — it is the x-dependent isenthalpic slope `−cp(x)/L` from the
  first law (`cp_moist(x)`, `_DHV`). The coordinator computes it from the
  current `x` and exposes it (per-state) as the `dx_dt` attribute.

### Internal model constants vs. boundary I/O values

Keep the distinction clear:

- A **model constant** that feeds the math directly (e.g. `_R_DRY`, `_R_VAP`,
  `_DHV` in `calc.py`) is stored in its SI unit so no conversion is needed at
  the call site.
- A **boundary I/O value** that mirrors a human-facing unit (e.g. the pressure
  fallback in hPa, or sensor inputs) is converted to SI once, at the boundary.

### Documented exception: temperature

The heat index in `calc.py` (`heat_index`, `d_hi_d_t`, `d_hi_d_x`) is the
expanded closed form of the Rothfusz fit composed with the relative humidity
that `(t, x, p)` imply (see `derivations/Diffrechnung Hitzeindex.nb`,
`Out[9]/Out[10]/Out[11]`). It is an **empirical fit**: the calc functions take
temperature in **°C** and form the absolute temperature `tk = t + 273.15`
internally, with the relative-humidity fit's exponential carried over **Kelvin**
at rates `−0.0524` (and `−0.1048` for the squared moisture term). `heat_index`
returns °C. Note that `dHI/dT` has the same numeric value in °C or K, because it
is a per-kelvin *interval* derivative.

The moisture terms also carry the moist-air gas constant
`R(x) = 287.1947…·(1−x) + 461.3762…·x` in their denominators (the air density
`rho = p / (R(x) T)` depends on `x`), so `x` appears in both numerator and
denominator. The ambient **pressure** enters in **pascals directly** — the
notebook computed everything in Pa, so the expanded coefficients already assume
Pa (no kPa rescaling). The `pressure` value is still a **boundary I/O** input:
converted to SI once in the coordinator and passed through unchanged.

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
- **Constants & functions:** `THRESHOLD` comes from `const.py`
  (`DEFAULT_THRESHOLD`); `DELTA_T` is read from the default of
  `calc.d_hi_cooling`. The isenthalpic slope is no longer a constant — the page
  calls `calc.process_line_slope(x)` directly. None are duplicated in the page.
- **Pyodide version:** pinned as an exact version in the CDN `<script>` URL in
  `index.html`. Because it is CDN-based with no JS/Python manifest, Dependabot
  cannot track or bump it — update the version string manually against the
  latest stable Pyodide release from time to time. (Dependabot here only covers
  `github-actions`.)

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
