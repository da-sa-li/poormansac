> [!NOTE]
> For the full derivations, check the other files in this directory. Use this file as a commentary only.

# Derivations

## Introduction

Evaporating water reduces dry-bulb temperatures, but increase humidity. This is called direct adiabatic cooling. It is not obvious whether evaporative coolers increases physiological well-being, because they produce sultry air.

Steadman [^steadman1979] delivers a more holistic view on the human perception of warmth than the dry-bulb temperature by taking into account that sweating does not yield as much cooling when the air is moist.

The goal of this project is to help assess in which circumstances direct adiabatic cooling is helpful or not.

## Thermodynamic considerations
The specific gas constant of air with the specific humidity $x$ equals:

$$ R_s = \frac{R}{M_{air}} (1-x) + \frac{R}{M_{water}}  x $$

The ideal gas law for this case is:

$$ p V = m R_s T $$
$$ p = \varrho R_s T $$
$$ \varrho = \frac{p}{R_s T} $$

The specific heat capacity of air is:
$$ c_p = (1-x) \frac{7}{2} \frac{R}{M_{air}} + x \cdot 4 \frac{R}{M_{water}} $$

The evaporation of water is an isenthalpic process. The first law of thermodynamics yields the following equations:

$$ 0 = c_p \mathrm{d} T + \mathrm{d} H_v \mathrm{d} x $$
$$ \frac{\mathrm{d} x}{\mathrm{d} T} = - \frac{c_p}{\mathrm{d} H_v} $$

This equation is the process line of the evaporation process of water.

## Physiological considerations

The heat index $HI$ is a state variable and can be approximated with an equation by Lans P. Rothfusz [^rothfusz1990]:

$$HI = c_1 + c_2 T + c_3 \varphi + c_4 T \varphi + c_5 T^2 + c_6 \varphi^2 + c_7 T^2\varphi + c_8 T \varphi^2 + c_9 T^2 \varphi^2$$

where $T$ is the ambient temperature in degrees Celsius and $\varphi$ is the relative humidity in percent.

The temperature and heat index are converted to Kelvin, and the relative humidity is expressed as specific humidity.

## Total derivation

To assess whether the evaporation of water is helpful, we have to find the slope of the heat index function. Since the heat index is a function of $T$ and $x$, we have to use the total differential.

$$ \mathrm{d} HI = \frac{\partial HI}{\partial T} \mathrm{d} T + \frac{\partial HI}{\partial x} \mathrm{d} x $$

But we can not move free on this surface, we are constrained by the first law of thermodynamics. Including the process line from above:

$$ \frac{\mathrm{d} HI}{\mathrm{d} T} = \frac{\partial HI}{\partial T} - \frac{\partial HI}{\partial x} \frac{c_p}{\mathrm{d} H_v} $$

Computing this expression yields the total differential of the heat index function. A negative result indicates that evaporating water moves the climate towards more comfortable conditions.

## Literature
[^steadman1979]: Steadman, R. G. (1979). *The Assessment of Sultriness. Part I: A Temperature-Humidity Index Based on Human Physiology and Clothing Science.* Journal of Applied Meteorology, 18(7), 861–873. DOI: 10.1175/1520-0450(1979)018<0861:TAOSPI>2.0.CO;2
[^rothfusz1990]: Rothfusz, L. P. (1990-07-01). *The Heat Index "Equation" (or, More Than You Ever Wanted to Know About Heat Index).* Technical Attachment SR 90-23, Scientific Services Division, NWS Southern Region Headquarters, Fort Worth, TX.
