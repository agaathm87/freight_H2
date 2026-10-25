# Trucks in transition: heavy-duty road freight in the course model

This package is the group's hydrogen model (`FinalModel_H2`) plus heavy-duty road freight (the individual assignment
"Trucks in transition"), hydrogen as a truck fuel, a realistic layer with the current truck and hydrogen policies, and
the sensitivity analysis as its own script. Nothing in the hydrogen study changes when the freight settings are left
at their defaults. Freight demand follows a macroeconomic driver (GDP, elasticity 0.6); water scarcity enters the
same way, as an outside driver (verdringingsreeks droughts that tighten over time, desalination as the backstop), not
as a scenario axis (section "Water: the water-scarcity driver").

## Run it on your computer
1. **Python 3.11, 3.12 or 3.13.** Open a terminal in this folder (`FinalModel_Freight`).
2. **A clean environment with the packages** (`requirements.txt`: the versions the runs were made with):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate      # macOS / Linux
   py -3.12 -m venv .venv && .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```
   With Anaconda: `conda create -n freight python=3.12`, `conda activate freight`, then the same `pip install`.
   If pip finds no wheel for a pinned version on your Python, install the unpinned set:
   `pip install -r requirements.txt` (includes `gurobipy`; a valid Gurobi licence is required).
3. **Check:** `python run_freight.py --list` prints the run groups and how many runs are on disk.
4. **Tables and figures from the saved runs** (no solving; the runs must be in `results/runs` and `results/runs_sens`):
   ```bash
   python analysis_freight.py      # results/outputs/*.csv and results/plots/freight/ (about 15 minutes)
   python paper_tables.py          # results/outputs/paper_tables/: Tables 1, 2, A2 and A3 (CSV, Markdown, Excel)
   python figure_set.py --redraw   # numbered paper and appendix figures (results/plots/FIGURES.md)
   ```
5. **Solve runs yourself** (Gurobi; runs on disk are skipped, `--rerun` solves them again):
   ```bash
   python run_freight.py F1_nofcet --rerun                      # one run, to try the solver
   python run_freight.py --group assignment                     # the 23 runs of the assignment
   python run_freight.py --group real --group real_sensitivity  # realistic layer
   python run_freight.py --group paper                          # all 72 runs
   python sensitivity.py --list                                 # the tipping-point grids (48 runs)
   ```
   Gurobi is the only supported solver and requires a valid licence.
6. **Rebuild the databases** only after changing a build setting:
   `python build_h2_database.py && python build_freight_database.py`.

The shell scripts in `results/logs` (`jobs.sh`, `queue.sh`) are for Linux and macOS; on Windows run the `python`
commands directly. `interface.ipynb` runs the same steps from a notebook (VS Code or Jupyter).

| Group | Runs | What for |
|---|---|---|
| `core` | `F1_nofcet` … `F4_nofcet`, `F1_ice` … `F4_ice` | assignment steps 1–5: the X/Y matrix with ICE trucks and BETs, ICE-only twins for the cost of switching |
| `core_sensitivity` | `F1/F4_co2central_nofcet`, `_co2high_nofcet`, `_sunday_ban_nofcet`, `_night_ban_nofcet` | assignment step 5: carbon price and time restrictions |
| `tests` | `F1/F4_fuel90_nofcet`, `F1_diesel_nofcet`, `F1_untaxed_nofcet`, `F1_vom3_nofcet`, `F1_tres6`, `F1_nostock_nofcet` | assignment step 5: calibration tests (section "Calibration and tests") |
| `assignment` | `core` + `core_sensitivity` + `tests` (23 runs) | everything the assignment asks for, within its specs |
| `h2` | `F1` … `F4`, `F1/F4_co2central`, `_co2high`, `_sunday_ban`, `_night_ban` | hydrogen extension (FCET and H2-ICE truck added) |
| `real` | `F*_real`, `F*_real_noh2`, `F*_real_ice`, `F*_real_nopolicy` | realistic layer and its twins (figures R1–R3 `_real`, S1–S5) |
| `real_sensitivity` | `F1/F4_real_co2central`, `_co2high`, `_sunday_ban`, `_night_ban` | the assignment's sensitivities in the realistic layer |
| `real_tests` | `F1/F3_real_h2green`, `F1_real_h2subsidy`, `F1/F4_real_netzero`, `F1/F4_real_h2eu`, `F1/F4_real_nolimit`, `F1_real_noheavy` | green hydrogen, net zero, EU hydrogen targets, limits |
| `water` | `F1/F4_real_water`, `F1_real_water_ely4` | the water-scarcity driver (realistic layer) |
| `paper` | all of the above: every run in `RUNS` (72) | every run behind the paper's figures and tables |

Every run is in one group (`run_freight.py` checks this), so there are no runs outside the paper. Removed on
23 October 2026: the earlier policy tests on the core (net-zero cap, EU truck mandate, RED III transport, SWiM-type
support, toll and AanZET with untaxed fuel), the slower fleet-turnover runs, the H2-ICE-only runs, the battery runs
and the group's fixed water levels. The realistic layer (current policies, market ramp-up, net zero, EU hydrogen
targets), the tipping-point grid (H2-ICE without fuel cells) and the water-scarcity driver replace them.

Or open `interface.ipynb`: section 7.1 (sensitivities, now `sensitivity.py`) and section 12 (freight; 12.2 the
water-scarcity driver, 12.5 the realistic layer).

## What was added
| File | Content |
|---|---|
| `build_freight_database.py` | Freight demand `freight_road` (90 PJ in 2020, GDP driver, exponent 0.6), hourly profile + Sunday-ban and night-ban profiles, ICE truck / BET / FCET / H2-ICE truck and the 2020 stock (`ICE truck - existing`, `BET - existing` 0.1 GW) |
| `energy_model/freight_presets.py` | Scenario axes (BET costs, gasoline prices), FCET and H2-ICE truck data, the policy presets and the realistic layer (BET duty cycles, mandates, subsidies, toll, ramp-up), the new settings (`FREIGHT_DEFAULTS`); sources next to the numbers |
| `energy_model/freight_water.py` | Applies the settings: BET costs, fuel prices, FCET / H2-ICE / ICE-only switches, freight profile, subsidies and toll; constraints: zero-emission share limits, BET duty cycles, hydrogen-truck and heavy-segment limits, RFNBO targets, renewable hydrogen at the pump, the net-zero cap, and the water constraints (verdringingsreeks quotas, as a path over the periods for the water-scarcity driver) |
| `figures/plots/freight_results.py` | Freight output, capacity, CO2 by sector, cost of switching, policy transfers, shadow prices |
| `figures/plots/freight_system.py` | System figures: Sankey with the trucks as a sector, energy balances, hydrogen supply and use |
| `run_freight.py` | Run registry (`RUNS`, 72 freight runs; `TESTS`), run groups (`GROUPS`) and batch runner |
| `analysis_freight.py` | Tables (`results/outputs/`) and figures (`results/plots/freight/`) from the runs on disk |
| `paper_tables.py` | The paper's tables (Table 1 settings, Table 2 sensitivities, Table A2 truck parameters, Table A3 calibration and tests) from the presets and the outputs: `results/outputs/paper_tables/` (CSV, `paper_tables.md`, `paper_tables.xlsx`) |
| `requirements.txt` | The Python packages and versions (run it on your computer, above) |
| `figure_set.py` | Numbered figure sets for the paper and the appendix with captions (`results/plots/paper/`, `appendix/`, `FIGURES.md`) |
| `figures_document/Figure_*` | Methodology figures: model overview with freight, freight module, scenario matrix, demand and profiles, water-scarcity driver |
| `sensitivity.py` | Sensitivity grids (the group's three from the notebook + three freight tipping-point grids); `--points a-b` for queues |
| Hooks marked `# [Freight]` | `h2_presets.py` (defaults, ETS2 for trucks), `h2_scenario.py`, `h2_constraints.py`, `model.py` (Gurobi options) |

## Scenario matrix
| Run | X: BET costs | Y: gasoline price (€/MWh 2020→2050) |
|---|---|---|
| F1 | constant: CAPEX 650 €/kW, VOM 0.10 €/kWh | moderate: 200→260 |
| F2 | decrease: CAPEX 650→290, VOM 0.10→0.02 | moderate |
| F3 | constant | sharp: 200→500 |
| F4 | decrease | sharp |

All with a moderately increasing CO2 price (`co2_price='low'`: ETS1 75/130/170, ETS2 55/55/170 €/t in 2030/40/50).
VOM values of the assignment table are entered in the database unit (€/kWh), so the BET charging penalty is
100 €/MWh of electricity (read literally as €/MWh it would be below 0.1% of the fuel cost).

## Truck sets: the assignment core and the hydrogen extension
| Runs | Trucks | Role |
|---|---|---|
| `F1_nofcet` … `F4_nofcet` and every `*_nofcet` | ICE truck, BET | the assignment's own set (the core of the paper) |
| `F1` … `F4` and every run without suffix | ICE truck, BET, FCET, H2-ICE truck | hydrogen extension: both hydrogen trucks |
| `F1_real` … `F4_real` and every `*_real*` | ICE truck, BET by duty cycle, FCET, H2-ICE truck | realistic layer (below): current policies and frictions, the mix of all four types |
| `*_ice` | ICE truck only | counterfactual for the cost of switching |

`fcet=False` switches both hydrogen trucks off unless `h2ice=True`; `h2ice=None` (default) follows `fcet`. The truck
set ICE + BET + H2-ICE (no fuel cells: what if fuel-cell trucks do not arrive) is in the tipping-point grid
`bet_vom_x_gasoline_h2ice` (figure R4).

**H2-ICE truck** (hydrogen combustion engine, added 23 October 2026; `H2ICE_PARAMS` in `freight_presets.py`): a
diesel truck with 700-bar hydrogen tanks (MAN hTGX: small series of 200 from 2025, 56 kg H2, 600 km).
CAPEX 215 / 180 / 160 / 150 €/kW (2020/30/40/50; ×1.8 → ×1.25 the ICE truck, ICCT 2023), FOM 2.5% of CAPEX,
efficiency 0.35 / 0.37 / 0.38 / 0.40 (about 10% more energy per km than diesel now, diesel level by 2050; ICCT
2023: 13–16%), VOM = the FCET's hydrogen delivery + station cost + 0.01 €/kWh for the engine, lifetime 12 years, no
tailpipe CO2. Zero-emission in the EU truck CO2 standards (below 3 g CO2/tkm), so it counts in `ze_min_share` /
`ze_max_share`, pays the zero-emission toll and must use RFNBO under `rfnbo_transport`. Settings:
`h2ice_capex_factor`; `fcet_vom_factor` also scales its hydrogen delivery part. CAPEX is anchored on the ICE truck,
not on the BET/FCET: this favours the H2-ICE (the assignment's zero-emission trucks cost 5–6× an ICE truck per kW).

All extension runs were solved again with the H2-ICE truck (23 October 2026). The core base runs (`F1`-`F4_nofcet`)
and the ICE-only runs were solved again too, so that every run carries its shadow prices; their results did not
change.

Key results (all numbers in `results/outputs/`, written by `python analysis_freight.py`):
- Core (ICE + BET): BETs take 96.5-98.6% of freight in 2030 and >= 99.8% in 2050 in F1-F4; switching saves
  EUR 315-687 bn over 2020-2059 against an ICE-only fleet (-540 to -1,190 EUR/t CO2).
- Extension: FCETs 2-6% and H2-ICE trucks 0.2-1.3% of freight in 2030, mostly as backup in scarce-power hours
  (H2-ICE 2-3 GW in 2050 at ~1% use); total cost -0.04 to -0.25% against the core.
- Tipping point (`R4_tipping_point`): FCETs take over from 0.20 EUR/kWh charging; H2-ICE trucks only without
  FCETs and from 0.30 EUR/kWh (58-100% of freight); ICE trucks stay with untaxed fuel or cheap fuel and
  expensive charging.
- H2-ICE vs FCET: an H2-ICE truck burns about a third more hydrogen per MWh of freight (EUR 120-160/MWh more at
  the model's hydrogen price); its lower purchase cost only pays for trucks that rarely drive.

## Realistic layer: current truck and hydrogen policies, real prices and frictions (23 October 2026)
The core keeps the course set-up. The realistic layer (`REAL` = `REAL_FRICTIONS` + `TRUCK_POLICIES` + `H2_POLICIES` in
`run_freight.py`; runs `F1_real` … `F4_real` on the same X/Y matrix with the moderate carbon price) runs the four
scenarios under the truck and hydrogen policies in force or planned in October 2026, with real prices and the frictions
the policies act on (values and sources in `freight_presets.py`, 'Realistic layer'):

| Policy | Setting |
|---|---|
| EU CO2 standards for new trucks (Reg. (EU) 2024/1610) | `ze_min_share='eu_hdv_fleet'`: zero-emission share of freight at least 30% / 65% / 75% (2030s / 2040s / 2050), the fleet shares of the sales the standards imply |
| ETS2 (from 2028) | in `co2_price='low'` (ETS2 55 €/t, 170 in 2050), as in the core |
| Truck toll (vrachtwagenheffing, since 1 July 2026) | `truck_toll='nl2026'` (€0.20/km diesel, €0.039/km zero-emission) |
| AanZET purchase subsidy (toll revenue) | `bet_capex_subsidy='aanzet'` (BET CAPEX −20% in the 2030s, all duty cycles) |
| RED III transport target (ERE system in NL) | `rfnbo_transport='red3'` (hydrogen trucks use ≥ 0.5% of road transport energy as renewable hydrogen) |
| Dutch RFNBO obligation for industry (jaarverplichting, bill 36 936; start postponed to 2028) | `green_mandate='nl_jaarverplichting'` (≥ 4% of industrial hydrogen from renewable electrolysis in 2030, 9.9% from 2035) |
| OWE electrolyser subsidies | `electrolyser_subsidy=OWE_SUBSIDY` (CAPEX −50% for the 2030 vintage) |
| SWiM hydrogen-mobility subsidy | `h2truck_capex_subsidy='swim'` (FCET and H2-ICE CAPEX −60% in the 2030s: 80% of the extra cost over diesel) |
| AFIR charging and hydrogen stations; zero-emission zones | behind the ramp-up and hydrogen limits; the urban duty cycle switches first |

| Friction | Setting |
|---|---|
| BETs by duty cycle | `bet_tiers='nl'`: `BET - urban` ≤ 25% of freight (depot, ~250 kWh, CAPEX ×0.8, VOM ×0.5), `BET` regional the next 35% (the assignment's BET), `BET - long haul` the rest (~800 kWh, half public charging at €0.399/kWh, CAPEX ×1.3, VOM ×2.5): a stepwise supply curve |
| Heavy special transport | `freight_heavy_share=0.05`: 5% that only ICE or H2-ICE trucks serve |
| Market ramp-up | `ze_max_share='market'`: zero-emission trucks at most 40% of freight in the 2030s and 90% in the 2040s |
| Hydrogen-truck availability | `h2_truck_max_share='market'`: FCET + H2-ICE at most 3% (2030s) and 25% (2040s) |
| Real prices | `truck_fuel_price`: diesel ex VAT, `diesel_nl` (moderate Y, 105/150/155/160 €/MWh) or `diesel_nl_sharp` (sharp Y, 105/205/258/308); `fcet_vom_factor=1.5` |

Runs: `F*_real` (all four types), `F*_real_noh2` (ICE + BET only), `F*_real_ice` (ICE-only counterfactual at the same
prices, toll and industry hydrogen policies, for the cost of switching), `F*_real_nopolicy` (the frictions and real
prices without any truck or hydrogen policy; the carbon price stays), `F1/F4_real_h2eu` (the EU hydrogen targets met in
full: 60% RFNBO in industry from 2040, transport path 'ambition'), and sensitivities `F1/F4_real_co2central/_co2high`,
`F1/F4_real_nolimit` (no ramp-up and no hydrogen limit), `F1_real_noheavy`, `F1/F4_real_sunday_ban/_night_ban`.

Green hydrogen for the trucks (policy test; `h2_trucks_rfnbo=True`: all hydrogen the trucks use comes from renewable
electrolysis, on top of the industry obligation, i.e. an RFNBO obligation on hydrogen sold to road transport):
`F1/F3_real_h2green` and the price-based alternative `F1_real_h2subsidy` (€1/kg production subsidy for electrolytic
hydrogen). Net zero in the realistic layer: `F1/F4_real_netzero` (the Klimaatwet / EU 2040 CO2 cap on the whole system,
with renewable hydrogen at the pump). Time restrictions for F1 and F4 (`_real_sunday_ban`, `_real_night_ban`).
Table `freight_green_hydrogen_tests.csv`. Water is unlimited in these runs; the water-scarcity driver is a separate set
(`_real_water`, section "Water"). The BET tiers are separate links in the database (`BET - urban`,
`BET - long haul`, from 2030); they are switched off unless `bet_tiers` is set, so the core and extension runs do not
change. Figures `R1_fleet_transition_real`, `R2_emissions_real`, `R3_cost_of_switching_real`, `R6_policy_levers`; tables
`freight_realistic.csv`, `freight_switching_cost_real.csv`, `freight_policy_transfers.csv` (toll paid and the AanZET,
SWiM and OWE subsidies: transfers next to the system cost), `freight_switching_cost_real_no_transfers.csv` and
`freight_policy_effect.csv`.

## Runs, analysis and results (October 2026)
- `RUNS` in `run_freight.py` holds 72 freight runs (groups above). Besides F1–F4: `_ice` (cost of switching),
  `_nofcet` (core), `_co2central/_co2high`, `_sunday_ban/_night_ban`, the tests (`TESTS`, below), the realistic layer
  (`_real*`) and the water-scarcity driver (`_real_water*`).
- Tipping-point grids (fuel price × BET charging penalty, 16 points each): `bet_vom_x_gasoline_nofcet` (core),
  `bet_vom_x_gasoline_h2ice` (+ H2-ICE truck) and `bet_vom_x_gasoline` (+ H2-ICE truck + FCET); figure R4.
- `python analysis_freight.py` — tables in `results/outputs/` and figures in `results/plots/freight/`: R1–R3 for the
  core (and `_h2` versions for the extension), R1–R3 `_real` for the realistic layer (core / no policies / current
  policies), R4 tipping point (three truck sets), R5 sensitivity heatmaps (carbon price, time restrictions; core and
  realistic), R6 policy-lever heatmap (realistic layer), R7 transition speed (zero-emission share in the corridor of the
  realistic layer, value of a faster ramp-up), S1–S5 system figures (Sankeys with the freight trucks, final energy of
  the trucks, energy balance, hydrogen supply and use, electricity generation; `figures/plots/freight_system.py`) and
  `A_water_driver`. Only runs of `RUNS` are loaded; missing runs are skipped, so the analysis works on any subset of
  the runs (missing cells read "not run").
- Methodology figures (`figures_document/`): `Figure_model_overview_freight` (the course model overview with the
  hydrogen module, freight and the outside drivers), `Figure_freight_topology` (the freight module),
  `Figure_freight_scenarios` (scenario matrix and policies), `Figure_freight_demand` (GDP driver and profiles),
  `Figure_water_driver` (verdringingsreeks path). `python figure_set.py --redraw` redraws them and writes the numbered
  sets `results/plots/paper/Fig01…Fig11` and `results/plots/appendix/A01…A13` with captions in
  `results/plots/FIGURES.md`.
- Hydrogen routes: pure green (own wind + solar) and pink (own nuclear) from 2030 (`pure_green`, `pink` switches).
- Bug fix in `energy_model/model.py: get_cap_constraints` (also in FinalModel_H2): with pandas ≥ 3 the base-year
  capacity constraints were silently dropped (all-NaN), so 2020 was not calibrated.
- Policy settings (all used by the realistic layer): `ze_min_share='eu_hdv_fleet'`, `truck_toll='nl2026'`,
  `bet_capex_subsidy='aanzet'`, `rfnbo_transport='red3'` (RED III: ≥1% RFNBO in road transport energy, counted ×2 via
  `rfnbo_multiplier`) or `'ambition'` (2/5/10%), `green_mandate='nl_jaarverplichting'` or `'red3'` (RFNBO only, pink
  excluded), `h2truck_capex_subsidy='swim'`, `co2_cap='netzero'`, `h2_trucks_rfnbo`, `h2_production_subsidy`.

## Calibration and tests (assignment step 5)
"Start with some tests and make sure the model is reasonably well calibrated in all scenarios": the base year is the
existing stock only (`ICE truck - existing`, size endogenous, and `BET - existing` 0.1 GW; new trucks are blocked in
2020), the same in all scenarios: 96.5% of freight from ICE trucks and 3.5% from BETs. The tests (`TESTS` in
`run_freight.py`, group `tests`; table `freight_calibration_tests.csv`) check this stock and the inputs behind it, in
the core set (F1 is the scenario least favourable to BETs):

| Run | Test | Result |
|---|---|---|
| `F1_nostock_nofcet` | no 2020 truck stock (`truck_stock=False`: the 'existing' trucks off, new ICE trucks and BETs allowed in 2020): the assignment's question whether 'existing' technologies are needed | yes: without them the model builds 4.8 GW of new BETs in 2020, which carry 99.95% of freight (observed: almost none); truck CO2 in 2020 is 0.01 Mt instead of 15.1 Mt, gas plants supply the extra 31 TWh, and the total cost looks €72 bn (5.5%) lower. From 2030 on the results are the same as `F1_nofcet` |
| `F1/F4_fuel90_nofcet` | the 90 PJ read as fuel input (×0.4) instead of truck output | as output, truck CO2 in 2020 is 15.1 Mt, three times the observed ~5 Mt (CE Delft, 2021); as fuel it is 5.7 Mt (BETs 8.8% in 2020: the 0.1 GW stock is a larger share), and BETs still take 95–98% of freight in 2030 |
| `F1_diesel_nofcet` | real diesel prices ex VAT (`truck_fuel_price='diesel_nl'`, 105 / 150 / 155 / 160 €/MWh) instead of the course gasoline price | BETs still take 92% of freight in 2030 (ICE 8%); the savings against ICE trucks shrink |
| `F1_untaxed_nofcet` | fuel without excise (`gasoline_price='untaxed'`, 70 → 85 €/MWh) | ICE trucks keep 55% of freight in 2030 and 24% in 2040: part of the saving is a tax effect |
| `F1_vom3_nofcet` | the course coordinator's high-VOM variant (BET charging penalty ×3, 0.30 €/kWh) | BETs keep 87% in 2030 (ICE 13%), at +15.5% total cost |
| `F1_tres6` | 6-hour instead of 15-hour time steps (`TRES`; extension run, longer than standard runs) | the freight shares do not change (93% BET in 2030); the power system does: batteries 4.0 GW in 2030 and 15 GW in 2050, system cost +4.2%, green hydrogen in 2050 26 → 8 TWh |

## Shadow prices (restored)
`store_shadow_prices(n, scenario)` (`energy_model/h2_constraints.py`, both packages) is called by `model_run` after
every solve. It was declared in the group package but its body was missing; it saves the scenario settings and the
shadow prices on `n.meta` (kept in the .nc file). Values are |dual| per year of the period (undiscounted) unless
marked PV (present value, discounted like the objective):

| Key on `n.meta` | Unit | Constraint |
|---|---|---|
| `co2_storage_cap_shadow_price` | €/t | CO2-storage cap |
| `build_cap_shadow_price_eur_per_kw_yr` | €/kW/yr | build limits (offshore wind, nuclear, electrolysers, H2 storage, battery) |
| `co2_cap_shadow_price` | €/t | net-zero CO2 cap (carbon price needed on top of the ETS) |
| `ze_share_shadow_price` | €/MWh of freight | zero-emission truck floor (`min`: EU CO2 standards, mandate) or the market ramp-up / diffusion limit (`max`) |
| `freight_segment_shadow_price` | €/MWh of freight | realistic layer: BET duty-cycle limits (`bet-tier-<type>`), hydrogen-truck availability (`h2-truck-max`), heavy special segment (`heavy-segment`) |
| `h2_trucks_rfnbo_shadow_price_eur_per_kg` | €/kg H2 | renewable hydrogen at the pump (`h2_trucks_rfnbo`) |
| `green_mandate_shadow_price_eur_per_kg` | €/kg H2 | RFNBO obligation for industry (Dutch jaarverplichting, RED III) |
| `rfnbo_transport_shadow_price` | €/MWh H2 | RED III transport target (`use`, `supply`) |
| `water_drought_shadow_price` | €/m³ | verdringingsreeks quota per category (`cat3`, `cat4`) or the cost-optimal pool: the value of one more m³ in the drought season (at most the desalination price) |

The group's other water limits store their own keys (`electrolyser_cap_…`, `water_cap_…`, `water_budget_…`).
A limit of 0 has no marginal value: its dual is not unique (degenerate) and is not stored; use the cost difference
between runs instead. Table: `freight_results.shadow_prices(n)`. Runs solved before this change have no shadow
prices: rerun them with `python run_freight.py --rerun <name>` (or `run_batch.py` in the group package).

## Water: the water-scarcity driver
Water is not a scenario axis of the freight study. It enters like the macroeconomic driver: an outside path over the
periods that the model has to live with (`water_scarcity='driver'`, `WATER_SCARCITY['driver']` in
`freight_presets.py`). In each period's dry season (June–September) every freshwater user gets a share of the water
its verdringingsreeks category used in the reference run F1 (`WATER_REFERENCE_DRY`, fixed in m³):

| Category (verdringingsreeks) | Model users | 2030 | 2040 | 2050 |
|---|---|---|---|---|
| 2 utilities | power plants | 100% | 100% | 100% |
| 3 small-scale high-value use | process water (SMR, CO2 capture), electrolysis (default) | 100% | 100% | 75% |
| 4 other interests | PV panel cleaning (electrolysis in `_ely4`) | 50% | 50% | 0% |

2030 and 2040 are the Deltaprogramma Zoetwater's 1-in-20 dry year (`dry_1in20`), 2050 a 2018-type drought
(`extreme_2018`, close to a normal summer under KNMI'23 Hd around 2050); river-cooled plants lose 10 / 15 / 25% of
their capacity in summer. Water above a quota is desalinated or reused water at `water_alt_cost` (€1.4/m³, the
group's desalination lever; `'low'` 0.6 … `'high'` 1.5), so the runs stay feasible and the quota's shadow price is
the value of water. `water_drought` and `thermal_summer_derate` take such a path `{year: …}` for any run. Runs:
`F1_real_water`, `F4_real_water`, `F1_real_water_ely4` (group `water`); figures `Figure_water_driver` (method) and
`A_water_driver` (results); table `freight_water_driver.csv`.

The group's earlier fixed water levels (electrolyser caps, a freshwater budget) remain available as settings
(`water_caps`, `water_budget`, `water_allocation='cost_optimal'`), but no freight run uses them.
