# Poor Man's AC

Home Assistant integration that decides, on thermodynamic grounds, whether
**direct adiabatic (evaporative) cooling** improves the indoor climate of a
room. Evaporating water lowers the temperature but raises humidity, so it is
not obvious whether it makes the room more or less comfortable. The integration
uses the **heat index** as the comfort measure and its **total differential**
along the adiabatic cooling path as the decision criterion.

## Inputs

- a temperature sensor (°C)
- a relative humidity sensor (%)
- optionally an ambient pressure sensor; without one (or while it is
  unavailable) the fallback pressure from the options is used

## What it computes

From temperature, relative humidity and ambient pressure the integration
derives the **water loading** `x` (mixing ratio, kg_water / kg_dry_air, using
the Magnus formula for the saturation vapour pressure) and evaluates the total
differential of the heat index along the isenthalpic evaporative-cooling path:

```
dHI = (∂HI/∂T)·dT + (∂HI/∂x)·dx
```

`dT` and `dx` follow from the energy balance of the adiabatic process
(sensible heat released = latent heat absorbed), which fixes the slope
`dx/dT ≈ −cp/L`. `dHI` is reported as the heat-index change per 1 K of
evaporative cooling. **`dHI < 0` ⇒ cooling lowers the heat index ⇒
recommended.**

The water vapour density `ρ_w` (absolute humidity, g/m³) is also computed and
exposed as a sensor, but it is not part of the decision criterion.

## Entities

- **binary_sensor** – `Adiabatic cooling recommended`
- **sensor** – `Heat index`, `Absolute humidity`, `Water loading`, `Heat index differential (dHI)`
- diagnostic sensors `dHI/dT` and `dHI/dx` (disabled by default)

## Installation

Copy `custom_components/poormansac` into your Home Assistant `config` folder (or
add this repository to HACS as a custom repository), restart, then add the
integration via **Settings → Devices & Services → Add Integration → Poor Man's
AC** and pick the temperature and humidity sensors, plus an optional ambient
pressure sensor.

## Options

`Settings → … → Configure`: the `dHI` threshold below which cooling is
recommended.

## Lovelace card

The integration bundles an experimental **psychrometric (Carrier) chart** card
and registers it automatically as a Lovelace JavaScript-module resource — for
the default *storage-mode* dashboards no manual setup under *Settings →
Dashboard → Resources* is needed. Once the integration is loaded the card
appears in the dashboard's *Add card* picker as **"Poor Man's AC Psychrometric
Chart"** (a browser refresh may be required the first time).

If you run your dashboards in **YAML mode**, Home Assistant manages resources
from your own YAML and the integration cannot edit it; the module is still
loaded globally so the card works, but if you maintain a `resources:` list
yourself add `/poormansac_frontend/poormansac-psychrometric-card.js` as a
`module` there.

It plots the **current air state** as a point on a dry-bulb-temperature (x-axis)
vs. water-loading `x` (right y-axis, g/kg) chart, draws **constant
relative-humidity curves** (including the **100 % saturation curve**), and shows
the **isenthalpic cooling line** — the path along which evaporative cooling
would move the air (up and to the left, toward saturation).

```yaml
type: custom:poormansac-psychrometric-card
entity: binary_sensor.poor_man_s_ac_adiabatic_cooling_recommended
# optional (defaults shown):
# title: Psychrometric chart
# t_min: 0
# t_max: 40
# x_min: 0
# x_max: 50
# rh_lines: 5   # number of equally spaced rel.-humidity curves;
#              # the top one is the 100 % saturation curve, 0 % is never drawn,
#              # and 0 hides them entirely
# point_label: [t, x, hi]   # which values to show next to the state point;
#                           # any of t (temperature), x (mixing ratio),
#                           # hi (heat index), rh (rel. humidity); [] hides it
```

The card reads everything it needs from the binary sensor's attributes
(`temperature`, `mixing_ratio`, `pressure`, `dx_dt`) and recomputes only the
relative-humidity curves, using the same effective pressure the integration used
for `x`.
