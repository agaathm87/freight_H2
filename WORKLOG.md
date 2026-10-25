# Trucks in transition: work log and summary (as of 23 October 2026)

What was asked in the working sessions on the freight assignment, what was built, the main decisions and the results.
The package documentation is `README_freight.md`; the context for coding assistants is `../.github/copilot-instructions.md`.

## The assignment and where each step stands

| Step | Asked (FinalIndividualAssignment - Freight) | Done |
|---|---|---|
| 1 | Freight demand of 90 PJ with a macroeconomic driver and a temporal profile | `freight_road`: 90 PJ of truck output in 2020, GDP driver (elasticity 0.6: 25 → 28.6 → 31.7 → 34.6 TWh), hourly profile with weekday peak, night and weekend; Sunday-ban and night-ban variants |
| 2 | ICE truck and BET from the course table, with the base-year calibration capacity | Both, with the 2020 stock (`ICE truck - existing`, `BET - existing` 0.1 GW); VOM in the database unit €/kWh |
| 3 | Scenario matrix X: BET costs × Y: gasoline price | F1–F4 |
| 4 | Four scenarios from the literature (BET CAPEX and VOM constant vs decrease; gasoline moderate vs sharp); a moderate carbon price in all | `_nofcet` = the assignment's ICE + BET set; ETS1 75/130/170, ETS2 55/55/170 €/t |
| 5 | Tests and calibration in all scenarios; plots of the energy system; the fleet transition (speed, emissions vs transport and system, cost of switching); sensitivities (carbon price, time restrictions) | 2020 = existing stock only (96.5% ICE, 3.5% BET in all scenarios); tests (group `tests`): no existing stock, 90 PJ as fuel, real diesel, untaxed fuel, the coordinator's VOM ×3, 6-hour steps; figures R1–R3, R7, S1–S5; ICE-only twins; `_co2central`, `_co2high`, `_sunday_ban`, `_night_ban` for F1 and F4 (heatmap R5) |
| 6 | Paper: the policy landscape, the discussion in that context, more realism | the realistic layer (current policies, real prices, frictions; R1–R3 `_real`, R6), hydrogen trucks, the water-scarcity driver; paper outline and research notes (Claude Docs) |

## Requests in order and what came of them

1. **Freight in the model** (steps 1–4) and the scenario matrix F1–F4.
2. **Hydrogen trucks**: fuel-cell truck (FCET) and, as a third type, the hydrogen combustion truck (H2-ICE); tipping-point
   grids (fuel price × BET charging penalty) for three truck sets (R4).
3. **Realism and a mix of all trucks**: the realistic layer (`_real`): BETs by duty cycle (urban 25%, regional 35%,
   long haul), a heavy segment (5%, no BET), the market ramp-up (zero-emission ≤ 40% / 90%), hydrogen-truck
   availability (≤ 3% / 25%), diesel ex VAT, hydrogen delivery ×1.5.
4. **Scenarios based on policies**: current truck policies (EU CO2 standards as a floor 30/65/75%, truck toll since
   July 2026, AanZET) and hydrogen policies (RED III transport, the Dutch RFNBO obligation 4% → 9.9%, OWE, SWiM);
   twins without policies (`_real_nopolicy`) and ICE-only (`_real_ice`); policy transfers kept apart from the
   system cost.
5. **System figures**: Sankeys with the trucks as a sector, energy balance, hydrogen supply and use, electricity (S1–S5).
6. **Green hydrogen for trucks**: renewable hydrogen at the pump (`h2_trucks_rfnbo`), a €1/kg production subsidy, the
   EU hydrogen targets in full, and net zero with renewable hydrogen at the pump.
7. **Audit, clean-up, comments, Copilot context**: docstrings everywhere, lint-clean, lines ≤ 120, stale outputs
   removed, run groups (`--group`, `--list`), a shared run queue (`results/logs/queue.sh`), `.github/copilot-instructions.md`.
8. **Water**: first left out (not a scenario axis), then brought back as an **outside driver** like GDP: the
   verdringingsreeks drought quotas tighten over time (1-in-20 dry year in 2030 and 2040, a 2018-type drought in 2050),
   river-cooled plants are derated, desalinated or reused water at €1.4/m³ is the backstop (`water_scarcity='driver'`,
   runs `_real_water`).
9. **Figures redrawn and added**: model overview with freight and the drivers, the freight module, the scenario
   matrix, demand and profiles, the water driver; heatmaps of the sensitivities (R5) and the policy levers (R6); the
   speed of the transition (R7); numbered sets for the paper (Fig01–Fig06: the template's 2 + 4) and the appendix (A01–A18) with captions
   (`figure_set.py`, `results/plots/FIGURES.md`).
10. **Clean-up of the runs against the assignment**: every run is now in a group behind the paper (72 runs with
    the last test). Kept as
    the assignment's step-5 tests: 90 PJ read as fuel (`F1/F4_fuel90_nofcet`), real diesel (`F1_diesel_nofcet`),
    untaxed fuel (`F1_untaxed_nofcet`), the course coordinator's VOM ×3 (`F1_vom3_nofcet`) and 6-hour steps
    (`F1_tres6`). Removed (64 runs, their archives and database snapshots): the group's fixed water levels and
    drought runs, the earlier policy tests on the core (net-zero cap, EU truck mandate, RED III transport, SWiM-type
    support, toll and AanZET; replaced by the realistic layer), the slower-turnover runs (replaced by the market
    ramp-up), the battery runs, the H2-ICE-only runs (in the R4 grid) and duplicate test variants.
11. **The last test**: the base year without the 'existing' truck stock (`F1_nostock_nofcet`, setting
    `truck_stock=False`), the assignment's question whether 'existing' technologies are needed; then a final audit.
12. **Paper tables and running it locally** (25 October): `paper_tables.py` builds Table 1 (settings), Table 2
    (sensitivities), Table A2 (truck parameters) and Table A3 (calibration and tests) from the presets and the
    outputs (`results/outputs/paper_tables/`), also added to the paper outline; `requirements.txt` and the README
    section "Run it on your computer".

## Decisions worth knowing

- VOM of the course table is read in €/kWh (the database unit): a BET charging penalty of 100 €/MWh.
- Trucks can switch type hour by hour (one freight bus); segments are energy-share limits, not capacity.
- The realistic ICE-only twins drop the truck policies (a zero-emission floor cannot hold without zero-emission trucks).
- The toll is part of the system cost; subsidies lower CAPEX and are reported as transfers (cost with and without).
- Water is a driver, not a scenario axis; quotas are fixed in m³ from the reference run F1.
- Gurobi with one thread, 15-hour steps; 6-hour steps only in the test `F1_tres6`.
- No run outside the paper: `run_freight.py` asserts that every run is in the `paper` group.

## Main results (runs of 23 October 2026)

- **Core (ICE + BET)**: BETs take 96.5–98.6% of freight in 2030 and ≥ 99.8% in 2050; switching saves €315–687 bn
  over 2020–2059 against an ICE-only fleet (−540 to −1,190 €/t CO2).
- **Realistic layer, current policies**: the market ramp-up binds in every scenario (zero-emission 40% in the 2030s,
  90% in the 2040s); F1 and F3 add fuel-cell trucks (25% of freight in the 2040s, 35% in 2050), F2 and F4 electrify
  long haul instead. Switching saves €206–434 bn (−468 to −896 €/t; −292 to −738 €/t without toll and subsidies).
  A faster ramp-up would be worth 326–539 €/MWh of freight in the 2030s.
- **Policies** add €49.6 bn to the system cost in F1 (mostly transfers) and speed up F1 in the 2040s (zero-emission
  90% instead of 71%); in F2–F4 the ramp-up binds with or without policies.
- **Green hydrogen**: renewable hydrogen at the pump costs €1.9 bn and pushes long haul to BETs in the 2040s; a €1/kg
  production subsidy makes most hydrogen green from 2040; net zero costs €27 bn (F1) and €24 bn (F4).
- **Sensitivities**: a high carbon price costs €75–87 bn more and cuts cumulative system CO2 by about 0.8 Gt; the
  time restrictions cost €1–5 bn and need more BET capacity (night ban, core F1: 6.7 → 7.9 GW in 2050).
- **What binds**: removing the ramp-up and hydrogen-truck limits saves €25 bn (F1) and €70 bn (F4) and almost all
  freight CO2 of the 2030s (zero-emission 95–98% in 2030); the EU hydrogen targets in full cost €4.7–5.9 bn and make
  2050 hydrogen mostly green; without the heavy segment the H2-ICE trucks vanish.
- **Tests (step 5)**: without the 'existing' stock the base year is not calibrated: BETs carry 99.95% of freight in
  2020 (4.8 GW built in 2020), truck CO2 is 0.01 instead of 15.1 Mt and gas supplies the extra 31 TWh; from 2030 on
  nothing changes. Reading the 90 PJ as fuel brings 2020 truck CO2 from 15.1 to 5.7 Mt (observed ~5 Mt) and
  the switch stays (95–98% BET in 2030); with real diesel BETs take 92% in 2030; with untaxed fuel ICE trucks keep 55%
  (a tax effect); with the coordinator's VOM ×3 BETs keep 87% at +15.5% cost; 6-hour steps change the power system
  (batteries, +4.2% cost), not the freight shares.
- **Water-scarcity driver**: a small cost (+€0.14 bn F1, +€0.11 bn F4, +€0.20 bn with electrolysis in category 4);
  in the 2050 drought season the system buys 10–18 Mm³ of desalinated or reused water above the quotas (worth
  €1.4/m³ each); the truck mix does not change.

## Deliverables

- `FinalModel_Freight_model.zip` (code, databases, outputs, figures, docs), `FinalModel_Freight_runs.zip` (the 72
  solved runs), `FinalModel_Freight_grids.zip` (the 48 tipping-point grid points), `FinalModel_Freight_figures.zip` (paper and appendix sets with captions),
  `FinalModel_H2_updates.zip`.
- `README_freight.md`, `.github/copilot-instructions.md`, this work log.
- Claude Docs: the paper outline and the research notes.

## To reproduce

```bash
pip install -r requirements.txt
python build_h2_database.py && python build_freight_database.py
python run_freight.py --group paper            # 72 runs; --list shows the groups
python analysis_freight.py && python paper_tables.py && python figure_set.py --redraw
```
