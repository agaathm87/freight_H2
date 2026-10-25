# Figures of the paper and the appendix

Made by `python figure_set.py` from the methodology figures (`figures_document/`) and the result figures (`python analysis_freight.py`). Numbered copies: `results/plots/paper/` and `results/plots/appendix/` (png at 300-400 dpi and svg).

## Paper

| No. | Caption | Source | Drawn by |
|---|---|---|---|
| Fig01 | The freight module: the carriers, the six truck technologies (colours as in the result figures), the freight demand, and the limits and price instruments of the realistic layer. | `figures_document/Figure_freight_topology.png` | `figures_document/Figure_freight_topology.py` |
| Fig02 | Scenario matrix: BET costs (X: CAPEX and VOM constant or decreasing) and fuel price (Y: moderate or sharp), all with the moderate carbon price; what the core runs and the realistic runs contain. | `figures_document/Figure_freight_scenarios.png` | `figures_document/Figure_freight_scenarios.py` |
| Fig03 | Fleet transition with BETs by duty cycle and hydrogen trucks: assignment core, realistic layer without policies, and realistic layer under current truck and hydrogen policies. | `results/plots/freight/R1_fleet_transition_real.png` | `analysis_freight.py` |
| Fig04 | Freight CO2 per period and cumulative CO2: core, realistic layer with and without current policies, ICE-only. | `results/plots/freight/R2_emissions_real.png` | `analysis_freight.py` |
| Fig05 | Cost of switching: system cost minus the ICE-only run per period, core (course prices) and realistic layer (real prices, current policies), with the abatement cost per tonne of CO2 (and without toll and subsidies). | `results/plots/freight/R3_cost_of_switching_real.png` | `analysis_freight.py` |
| Fig06 | Tipping point: who serves freight at each fuel price and BET charging penalty, for three truck sets. | `results/plots/freight/R4_tipping_point.png` | `analysis_freight.py (grids: sensitivity.py)` |

## Appendix

| No. | Caption | Source | Drawn by |
|---|---|---|---|
| A01 | Freight demand: the GDP driver (elasticity 0.6) and the hourly profile of one week, with the Sunday-ban and night-ban variants of the sensitivity analysis. | `figures_document/Figure_freight_demand.png` | `figures_document/Figure_freight_demand.py` |
| A02 | Energy flows of the whole system in 2030 with the freight trucks as a sector: F1 core and F1 realistic. | `results/plots/freight/S1_sankey_2030.png` | `analysis_freight.py (figures/plots/freight_system.py)` |
| A03 | Energy flows of the whole system in 2050: F1 core and F1 realistic. | `results/plots/freight/S1_sankey_2050.png` | `analysis_freight.py (figures/plots/freight_system.py)` |
| A04 | Final energy of the freight trucks by carrier (labels: freight delivered). | `results/plots/freight/S2_freight_final_energy.png` | `analysis_freight.py` |
| A05 | Final energy by sector and carrier, F1 realistic under current policies. | `results/plots/freight/S3_energy_balance_F1_real.png` | `analysis_freight.py` |
| A06 | Hydrogen supply by route and the hydrogen the trucks use (incl. the EU targets and renewable H2 at the pump). | `results/plots/freight/S4_hydrogen_supply.png` | `analysis_freight.py` |
| A07 | Electricity generation by source: F1 core, F1 realistic, F1 realistic with ICE trucks only. | `results/plots/freight/S5_electricity_supply.png` | `analysis_freight.py (figures/plots/system_plots.py)` |
| A08 | Fleet transition in F1-F4 with the assignment's ICE trucks and BETs (top) and the change in grid generation against the ICE-only run (bottom). | `results/plots/freight/R1_freight_transition.png` | `analysis_freight.py` |
| A09 | Hydrogen extension: fleet transition with FCETs and H2-ICE trucks and the change in grid generation. | `results/plots/freight/R1_freight_transition_h2.png` | `analysis_freight.py` |
| A10 | Hydrogen extension: freight CO2 and cumulative CO2. | `results/plots/freight/R2_emissions_h2.png` | `analysis_freight.py` |
| A11 | Hydrogen extension: cost of switching per period and abatement cost. | `results/plots/freight/R3_cost_of_switching_h2.png` | `analysis_freight.py` |
| A12 | Water-scarcity driver: the verdringingsreeks categories, the model's water users in each, and the share of its drought-season reference water each category may use per period; desalination as the backstop. | `figures_document/Figure_water_driver.png` | `figures_document/Figure_water_driver.py` |
| A13 | Water-scarcity driver, results: drought-season freshwater use under the verdringingsreeks, the desalinated or reused water above the quotas, and the cost against the same runs without water limits. | `results/plots/freight/A_water_driver.png` | `analysis_freight.py` |
| A14 | Freight truck CO2 per period and cumulative CO2 2020-2059 of trucks, cars and the rest of the system, core runs and the ICE-only counterfactual. | `results/plots/freight/R2_emissions.png` | `analysis_freight.py` |
| A15 | Sensitivities of the assignment for F1 and F4, core and realistic: carbon price (central, high) and time restrictions (Sunday ban, night ban); colour = change against the base run. | `results/plots/freight/R5_sensitivities.png` | `analysis_freight.py` |
| A16 | Speed of the transition: zero-emission share of freight per period (core, realistic without and with current policies) inside the corridor of the realistic layer, and the value of a faster ramp-up (shadow price). | `results/plots/freight/R7_transition_speed.png` | `analysis_freight.py` |
| A17 | Policy and market levers of the realistic layer for F1 and F4 (incl. the water-scarcity driver); colour = change against current policies. | `results/plots/freight/R6_policy_levers.png` | `analysis_freight.py` |
| A18 | Model structure: the course model with the group's hydrogen module (teal) and heavy-duty road freight (blue). Pink boxes are outside drivers: hourly profiles, the water-scarcity driver and the macroeconomic drivers. | `figures_document/Figure_model_overview_freight.png` | `figures_document/Figure_model_overview_freight.py` |
