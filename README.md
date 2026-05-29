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

## What it computes

From temperature and relative humidity the integration derives the water vapour
density `ρ_w` (g/m³, Magnus formula) and evaluates the total differential of the
heat index along the isenthalpic evaporative-cooling path:

```
dHI = (∂HI/∂T)·dT + (∂HI/∂ρ_w)·dρ_w
```

`dT` and `dρ_w` follow from the energy balance of the adiabatic process
(sensible heat released = latent heat absorbed). `dHI` is reported as the
heat-index change per 1 K of evaporative cooling. **`dHI < 0` ⇒ cooling lowers
the heat index ⇒ recommended.**

## Entities

- **binary_sensor** – `Adiabatic cooling recommended`
- **sensor** – `Heat index`, `Absolute humidity`, `Heat index differential (dHI)`
- diagnostic sensors `dHI/dT` and `dHI/dρ_w` (disabled by default)

## Installation

Copy `custom_components/poormansac` into your Home Assistant `config` folder (or
add this repository to HACS as a custom repository), restart, then add the
integration via **Settings → Devices & Services → Add Integration → Poor Man's
AC** and pick the temperature and humidity sensors.

## Options

`Settings → … → Configure`: `dHI` threshold and the moist-air constants (air
density, specific heat capacity) used in the energy balance.
