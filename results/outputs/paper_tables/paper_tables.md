# Paper tables

Written by `paper_tables.py` from the model settings and the saved outputs. Bold first-column rows are block headers.

**Table 1** *Scenario Settings and Parameter Values*

*Panel A. The assignment's trucks (all periods)*

| Parameter | ICE truck | BET |
| --- | --- | --- |
| CAPEX (€/kW of output) | 120 | 650 (falling in F2, F4: Panel B) |
| FOM (€/kW/yr) | 3 | 5 |
| VOM (€/kWh of input) | 0.01 | 0.10 (falling in F2, F4: Panel B) |
| Efficiency (%) | 40 | 70 |
| Lifetime (years) | 12 | 8 |
| CO2 (t/MWh of fuel) | 0.25 | – |
| 2020 stock (2020 only) | ICE truck – existing, size set by the model | BET – existing, 0.1 GW |

*Panel B. Scenario axes, carbon price and the realistic layer*

| Setting | Scenarios | 2020 | 2030 | 2040 | 2050 | Source |
| --- | --- | --- | --- | --- | --- | --- |
| **Scenario axes and carbon price (all runs)** |  |  |  |  |  |  |
| Freight demand (TWh/yr of truck output) | All | 25.0 | 28.6 | 31.7 | 34.6 | Assignment (90 PJ in 2020); GDP elasticity 0.6 (KiM, 2021: ~1.0 in the short run) |
| BET CAPEX (€/kW) | F1, F3 | 650 | 650 | 650 | 650 | Assignment |
|  | F2, F4 | 650 | 420 | 325 | 290 | Link et al. (2024) |
| BET VOM, the charging penalty (€/kWh of electricity) | F1, F3 | 0.10 | 0.10 | 0.10 | 0.10 | Assignment |
|  | F2, F4 | 0.10 | 0.05 | 0.03 | 0.02 | Charging roll-out (Regulation (EU) 2023/1804) |
| Gasoline price, with excise (€/MWh) | F1, F2 | 200 | 220 | 240 | 260 | IISD (2025) |
|  | F3, F4 | 200 | 300 | 400 | 500 | Course database |
| Carbon price, ETS1 (€/t CO2) | All | 30 | 75 | 130 | 170 | Group model (Učelniece et al., 2026) |
| Carbon price, ETS2 on road fuels (€/t CO2) | All | – | 55 | 55 | 170 | van der Veen et al. (2026, p. 17) |
| **Realistic layer (F1_real to F4_real)** |  |  |  |  |  |  |
| Zero-emission share of freight, minimum (CO2 standards) | All | – | 30% | 65% | 75% | Regulation (EU) 2024/1610; Transport & Environment (2024) |
| Zero-emission share of freight, maximum (market ramp-up) | All | – | 40% | 90% | – | Mulholland & Benoit (2026) |
| Hydrogen trucks (FCET + H2-ICE), maximum share of freight | All | – | 3% | 25% | – | Regulation (EU) 2023/1804; Electrive (2026) |
| BET duty cycles, share of freight: urban at most / regional (the assignment's BET) the next; long haul the rest (costs: Table A2) | All | – | 25% / 35% | 25% / 35% | 25% / 35% | TNO (2021); Sharpe & Basma (2022); Basma et al. (2022); Milence (2025) |
| Heavy special segment, ICE or H2-ICE trucks only (share of freight) | All | 5% | 5% | 5% | 5% | Wang & Ahluwalia (2026); MAN Truck & Bus (2024) |
| Truck toll, ICE / zero-emission (€/km) | All | – | 0.20 / 0.039 | 0.20 / 0.039 | 0.20 / 0.039 | Ministerie van Infrastructuur en Waterstaat (2026) |
| Purchase subsidy for BETs, AanZET (share of CAPEX) | All | – | 20% | – | – | RVO (2026a) |
| Purchase subsidy for hydrogen trucks, SWiM (share of CAPEX) | All | – | 60% | – | – | RVO (2026b) |
| Electrolyser subsidy, OWE (share of CAPEX) | All | – | 50% | – | – | RVO (n.d.); Rijksoverheid (2025) |
| Renewable hydrogen in road transport (share of road-transport energy, counted double) | All | – | 1% | 1% | 1% | Directive (EU) 2023/2413 |
| Renewable hydrogen in industry, Dutch obligation (share of industrial hydrogen) | All | – | 4% | 9.9% | 9.9% | Tweede Kamer der Staten-Generaal (2026); KGG (2026) |
| Diesel price for trucks, without VAT (€/MWh) | F1, F2 | 105 | 150 | 155 | 160 | Weekly Oil Bulletin (European Commission, n.d.) |
|  | F3, F4 | 105 | 205 | 258 | 308 | The course's sharp-to-moderate ratio |
| Hydrogen delivery and station cost (€/kg; ×1.5 of the extension) | All | – | 6.00 | 4.50 | 3.75 | Chung & Wang (2024) |

*Note.* Money in 2024 euros. CAPEX and FOM per kW of truck output, VOM per kWh of input (the database units), so the BET's charging penalty is 100 €/MWh of electricity. The core runs (`_nofcet`) carry only the carbon price; the extension adds fuel-cell (FCET) and hydrogen combustion (H2-ICE) trucks from 2030 (Table A2). The realistic layer keeps the X/Y matrix and the carbon price and adds the policies in force or planned in October 2026 and the frictions they act on. Long-haul BETs take the rest of freight (35% after the heavy segment), and the trucks pay the diesel price instead of the gasoline price (cars keep the gasoline price). – = not applied. Toll, AanZET, SWiM and OWE are transfers, reported next to the system cost. Settings: `energy_model/freight_presets.py` and `run_freight.py`.

**Table 2** *Sensitivities: Zero-Emission Share, BET Capacity, System CO2 and Cost in 2030 and 2050*

*Panel A. Core: the assignment's ICE trucks and BETs (`_nofcet` runs)*

| Scenario and sensitivity | Zero-emission share 2030 (%) | BET capacity 2030 (GW) | BET capacity 2050 (GW) | System CO2 2030 (Mt/yr) | System CO2 2050 (Mt/yr) | Cost change (bn €) | Cost change (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1, moderate carbon price (base) | 96.5 | 5.4 | 6.7 | 74.2 | 8.6 | – | – |
| F1, central carbon price | 97.0 | 5.4 | 6.7 | 56.9 | 2.5 | +47.4 | +3.6 |
| F1, high carbon price | 96.1 | 5.5 | 6.7 | 51.6 | −4.9 | +77.9 | +5.9 |
| F1, Sunday ban | 96.5 | 5.6 | 6.9 | 74.0 | 8.7 | +2.1 | +0.2 |
| F1, night ban | 96.0 | 6.2 | 7.9 | 73.5 | 7.9 | +4.8 | +0.4 |
| F4, moderate carbon price (base) | 98.6 | 5.5 | 6.8 | 74.7 | 8.0 | – | – |
| F4, central carbon price | 98.9 | 5.5 | 6.8 | 56.1 | 2.2 | +46.0 | +3.7 |
| F4, high carbon price | 98.3 | 5.5 | 6.8 | 50.2 | −5.1 | +75.4 | +6.0 |
| F4, Sunday ban | 98.5 | 5.7 | 7.0 | 74.6 | 7.8 | +1.9 | +0.2 |
| F4, night ban | 98.1 | 6.6 | 8.1 | 74.8 | 7.7 | +4.3 | +0.3 |

*Panel B. Realistic layer: current policies (`_real` runs)*

| Scenario and sensitivity | Zero-emission share 2030 (%) | BET capacity 2030 (GW) | BET capacity 2050 (GW) | System CO2 2030 (Mt/yr) | System CO2 2050 (Mt/yr) | Cost change (bn €) | Cost change (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1, moderate carbon price (base) | 40.0 | 2.6 | 4.3 | 82.9 | 11.7 | – | – |
| F1, central carbon price | 40.0 | 2.2 | 4.1 | 66.8 | 0.4 | +50.6 | +3.8 |
| F1, high carbon price | 40.0 | 1.9 | 4.5 | 60.7 | −6.2 | +86.5 | +6.4 |
| F1, Sunday ban | 40.0 | 2.7 | 4.4 | 82.6 | 11.9 | +1.0 | +0.1 |
| F1, night ban | 40.0 | 2.4 | 4.4 | 83.1 | 11.4 | +1.0 | +0.1 |
| F4, moderate carbon price (base) | 40.0 | 3.2 | 6.3 | 82.6 | 7.1 | – | – |
| F4, central carbon price | 40.0 | 2.4 | 6.5 | 66.6 | 1.0 | +49.5 | +3.8 |
| F4, high carbon price | 40.0 | 2.7 | 6.6 | 59.3 | −5.7 | +84.9 | +6.5 |
| F4, Sunday ban | 40.0 | 3.3 | 6.5 | 82.3 | 7.1 | +1.0 | +0.1 |
| F4, night ban | 40.0 | 3.0 | 7.1 | 82.6 | 6.8 | +1.2 | +0.1 |

*Note.* Cost change: total discounted system cost 2020–2059 against the same scenario with the moderate carbon price and the base demand profile. BET capacity: output capacity of all BETs (GW of truck output). System CO2 covers all sectors. Carbon prices in 2030 / 2040 / 2050 (€/t CO2): moderate (base) ETS1 75 / 130 / 170, ETS2 55 / 55 / 170; central: ETS1 110 / 180 / 250, ETS2 83 / 217 / 250; high: ETS1 140 / 270 / 500, ETS2 131 / 340 / 500. Sunday ban: trucks on Sundays and holidays until 22:00 at 2% of the base profile; night ban: no trucks from 23:00 to 06:00. In the realistic layer the market ramp-up holds the zero-emission share at 40% in the 2030s in every sensitivity. The hydrogen trucks and the policy and green-hydrogen tests are in Figure A17 (`freight_policy_levers.csv`). Data: `freight_summary.csv`, `freight_total_cost.csv`.

**Table A2** *Truck Parameters by Period*

| Truck | Runs | CAPEX (€/kW) | FOM (€/kW/yr) | VOM (€/kWh of input) | Efficiency (%) | Lifetime (years) | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ICE truck | All | 120 | 3 | 0.01 | 40 | 12 | Assignment |
| ICE truck – existing (2020 stock) | All | 0 | 3 | 0.01 | 40 | 4 | Assignment |
| BET (constant costs) | F1, F3 | 650 | 5 | 0.10 | 70 | 8 | Assignment |
| BET (falling costs) | F2, F4 | 650 / 420 / 325 / 290 | 5 | 0.10 / 0.05 / 0.03 / 0.02 | 70 | 8 | Link et al. (2024) |
| BET – existing (2020 stock) | All | 0 | 5 | 0.10 | 70 | 4 | Assignment |
| BET – urban (from 2030) | Realistic layer | ×0.8 of the BET | ×0.8 of the BET | ×0.5 of the BET | 70 | 8 | Sharpe & Basma (2022); Basma et al. (2022); Milence (2025) |
| BET – long haul (from 2030) | Realistic layer | ×1.3 of the BET | ×1.3 of the BET | ×2.5 of the BET | 70 | 8 | Sharpe & Basma (2022); Basma et al. (2022); Milence (2025) |
| FCET (from 2030) | Extension and realistic layer | – / 750 / 550 / 450 | – / 6 / 5 / 5 | – / 0.12 / 0.09 / 0.075 | – / 50 / 52 / 55 | 10 | Basma & Rodríguez (2023); Link et al. (2024) |
| H2-ICE truck (from 2030) | Extension and realistic layer | – / 180 / 160 / 150 | – / 4.5 / 4.0 / 3.8 | – / 0.13 / 0.10 / 0.085 | – / 37 / 38 / 40 | 12 | Basma et al. (2023); MAN Truck & Bus (2024) |

*Note.* Values with a slash are 2020 / 2030 / 2040 / 2050; – = not available in that period. Money in 2024 euros; CAPEX and FOM per kW of truck output, VOM per kWh of input. The ICE trucks emit 0.25 t CO2 per MWh of fuel. The 2020 stock has no investment cost, a 4-year life (2020 only) and replaces new trucks in the base year; BET – existing is fixed at 0.1 GW. The VOM of the hydrogen trucks is the hydrogen delivery and station cost (4.0 / 3.0 / 2.5 €/kg in 2030 / 2040 / 2050; ×1.5 in the realistic layer), plus 0.01 €/kWh for the H2-ICE engine. The BET duty cycles scale the BET of the scenario (FOM scales with CAPEX). Sources and derivations: `energy_model/freight_presets.py`.

**Table A3** *Calibration and Tests (Assignment Step 5)*

| Test | Scenario | Truck energy input 2020 (PJ) | BET share of freight 2020 (%) | Truck CO2 2020 (Mt) | Zero-emission share 2030 (%) | Truck CO2 2030 (Mt) | Cost change (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Calibrated base year (the 2020 stock) | F1 | 222 | 3.5 | 15.1 | 96.5 | 0.6 | – |
| Calibrated base year (the 2020 stock) | F2 | 222 | 3.5 | 15.1 | 97.5 | 0.4 | – |
| Calibrated base year (the 2020 stock) | F3 | 222 | 3.5 | 15.1 | 98.2 | 0.3 | – |
| Calibrated base year (the 2020 stock) | F4 | 222 | 3.5 | 15.1 | 98.6 | 0.3 | – |
| 90 PJ read as fuel, not as truck output | F1 | 87 | 8.8 | 5.7 | 95.3 | 0.3 | −14.7 |
| 90 PJ read as fuel, not as truck output | F4 | 87 | 8.8 | 5.7 | 97.5 | 0.2 | −11.8 |
| Diesel without VAT instead of the course's gasoline price | F1 | 222 | 3.5 | 15.1 | 91.9 | 1.4 | −4.4 |
| Fuel without excise (70–85 €/MWh) | F1 | 222 | 3.5 | 15.1 | 45.2 | 9.8 | −16.0 |
| Charging penalty ×3 (0.30 €/kWh) | F1 | 222 | 3.5 | 15.1 | 87.4 | 2.2 | +15.5 |
| 6-hour instead of 15-hour time steps | F1 (with hydrogen trucks) | 222 | 3.5 | 15.1 | 99.0 | 0.2 | +4.2 |
| No 2020 truck stock | F1 | 129 | 99.95 | 0.01 | 96.5 | 0.6 | −5.5 |

*Note.* Cost change: total discounted system cost 2020–2059 against the same scenario without the test (the 6-hour run against F1 with hydrogen trucks). Truck energy input is fuel plus electricity. The 90 PJ of the assignment is truck output: at 40% efficiency the ICE trucks burn 217 PJ of fuel and emit 15.1 Mt CO2 in 2020, against an observed 5.1 Mt for heavy trucks (2014; CE Delft, 2021); the fuel test reads the 90 PJ as fuel. The 2020 values are the same in all four scenarios. Without the stock the model builds new BETs in 2020; from 2030 on nothing changes. Runs: group `tests` in `run_freight.py`; data: `freight_calibration_tests.csv`.
