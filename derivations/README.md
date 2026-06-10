> [!CAUTION]
> This README is not up to date and contains errors.

# On the Advantageousness of Direct Adiabatic Cooling in Residential Spaces

## Introduction

The heat index $HI$ is a state variable and can be described as follows:

$$HI = c_1 + c_2 T + c_3 \varphi + c_4 T \varphi + c_5 T^2 + c_6 \varphi^2 + c_7 T^2\varphi + c_8 T \varphi^2 + c_9 T^2 \varphi^2$$

where $T$ is the ambient temperature in degrees Celsius and $\varphi$ is the relative humidity in percent.

The purpose of the heat index is to provide a measure that better represents the human perception of warmth than the dry-bulb temperature.

### Air Humidity

The relative humidity is given by:

$$\varphi = \frac{\rho_w}{\rho_{w, \max}}$$

The relationship between the saturation moisture content $\rho_{w, \max}$ in g/m³ and the temperature in degrees Celsius $T$ can be described by the following equation:

$$\rho_{w, \max} = 6.0495 \cdot e^{0.0533 \cdot T}$$

Substituting back into the relative humidity equation:

$$\varphi = \frac{\rho_w}{6.0495 \cdot e^{0.0533 \cdot T}} = 0.16530 \cdot \rho_w \cdot e^{-0.0533 \cdot T}$$

And substituting back into the heat index equation:

$$HI = -8.784695 + 1.61139411 \cdot T + 0.3865 \cdot \rho_w \cdot e^{-0.0533 \cdot T} - 0.024153 \cdot T \cdot \rho_w \cdot e^{-0.0533 \cdot T} - 0.01231 \cdot T^2 - 0.002715 \cdot \rho_w \cdot e^{-0.1066 \cdot T} + 0.0003656 \cdot T^2 \cdot \rho_w \cdot e^{-0.0533 \cdot T} + 0.0001199 \cdot T \cdot \rho_w \cdot e^{-0.1066 \cdot T} - 5.921 \cdot 10^{-7} \cdot T^2 \cdot \rho_w \cdot e^{-0.1066 \cdot T}$$

Taking the partial derivative with respect to temperature:

$$\frac{\partial HI}{\partial T} = 6.311786 \cdot 10^{-8}\, \rho_w\, e^{-0.1066\, T}\, T^2 - 1.94865 \cdot 10^{-5}\, \rho_w\, e^{-0.0533\, T}\, T^2 - 1.39655 \cdot 10^{-5}\, \rho_w\, e^{-0.1066\, T}\, T + 0.00201855\, \rho_w\, e^{-0.0533\, T}\, T + 0.000409319\, \rho_w\, e^{-0.1066\, T} - 0.0447535\, \rho_w\, e^{-0.0533\, T} - 0.02462\, T + 1.61139$$

And taking the partial derivative with respect to moisture content:

$$\frac{\partial HI}{\partial \rho_w} = -5.921 \cdot 10^{-7}\, e^{-0.1066\, T}\, T^2 + 0.0003656\, e^{-0.0533\, T}\, T^2 + 0.0001199\, e^{-0.1066\, T}\, T - 0.024153\, e^{-0.0533\, T}\, T - 0.002715\, e^{-0.1066\, T} + 0.3865\, e^{-0.0533\, T}$$

The total differential of the heat index is:

$$\mathrm{d} HI = \left( \frac{\partial HI}{\partial T} \right)_{\rho_w} \mathrm d T + \left( \frac{\partial HI}{\partial \rho_w} \right)_T \mathrm d \rho_w$$

### Thermodynamics

The enthalpy of vaporization of water is:

$$\Delta h_v = 2441 \, \text{kJ} \cdot \text{kg}^{-1}$$

The specific heat capacity of air at constant pressure is approximately:

$$c_p = 1.01 \, \text{kJ} \cdot \text{kg}^{-1} \cdot \text{K}^{-1}$$

The first law of thermodynamics for our adiabatic process yields:

$$\begin{align}
\mathrm d h &= 0 \\
0 &= c_p \mathrm d T + \Delta H_v \mathrm d x \\
\frac{\mathrm d x}{\mathrm d T} &= -\frac{c_p}{\Delta H_v} \\
\frac{\mathrm d x}{\mathrm d T} &= -0.41 \, \text{g}_w \cdot \text{kg}_L^{-1} \cdot \text{K}^{-1}
\end{align}$$

where $x$ is the mixing ratio and $\Delta H_v$ is the enthalpy of vaporization.

With air density $\varrho_L = 1.2041 \, \text{kg} \cdot \text{m}^{-3}$ (assumed constant), we obtain:

$$\frac{\mathrm d \rho_w}{\mathrm d T} = -4.94 \times 10^{-4} \, \text{kg} \cdot \text{m}^{-3} \cdot \text{K}^{-1} \approx -0.494 \, \text{g} \cdot \text{m}^{-3} \cdot \text{K}^{-1}$$

## Differential Equation

Combining the partial derivatives with the adiabatic constraint:

$$\frac{\mathrm d HI}{\mathrm{d T}} = \left( \frac{\partial HI}{\partial T} \right) + \left( \frac{\partial HI}{\partial \rho_w} \right) \frac{\mathrm d \rho_w}{\mathrm d T}$$

Substituting the expressions, we arrive at the governing equation for how the heat index changes along an adiabatic cooling path:

$$\mathrm d HI = \left( 6.311786 \cdot 10^{-8}\, \rho_w\, e^{-0.1066\, T}\, T^2 - 1.94865 \cdot 10^{-5}\, \rho_w\, e^{-0.0533\, T}\, T^2 - 1.39655 \cdot 10^{-5}\, \rho_w\, e^{-0.1066\, T}\, T + 0.00201855\, \rho_w\, e^{-0.0533\, T}\, T + 0.000409319\, \rho_w\, e^{-0.1066\, T} - 0.0447535\, \rho_w\, e^{-0.0533\, T} - 0.02462\, T + 1.61139 \right) + \left( 2.01 \cdot 10^{-7}\, e^{-0.1066\, T}\, T^2 - 0.00012\, e^{-0.0533\, T}\, T^2 - 0.000041\, e^{-0.1066\, T}\, T + 0.0082\, e^{-0.0533\, T}\, T + 0.00092\, e^{-0.1066\, T} - 0.13\, e^{-0.0533\, T} \right) \mathrm d T$$

This differential equation describes the rate of change of the heat index with respect to temperature during adiabatic cooling, allowing us to determine whether direct evaporative cooling is thermodynamically advantageous for a given set of ambient conditions.
