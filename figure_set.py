"""Collect the figures of the paper and its appendix into numbered sets, with captions.

Usage:  python figure_set.py            (copies the figures that exist; run analysis_freight.py first)
        python figure_set.py --redraw   (first redraws the methodology figures in figures_document/)

Output: results/plots/paper/Fig01_...Fig06_ and results/plots/appendix/A01_...A18_ (png + svg) and
results/plots/FIGURES.md
(number, caption, source file and the script that draws it). A figure whose source is missing is listed as missing.
"""
import argparse
import os
import shutil
import subprocess
import sys

FD, FR = 'figures_document', os.path.join('results', 'plots', 'freight')
OUT = os.path.join('results', 'plots')

# (number, stem, source folder, source stem, script, caption)
# The paper template allows up to 2 visuals for the scenarios and up to 4 plots for the results: Fig01-Fig02 are the
# methodology figures, Fig03-Fig06 the result plots (paper outline: Figures 1-6). Everything else is in the appendix.
PAPER = [
    ('Fig01', 'freight_module', FD, 'Figure_freight_topology', 'figures_document/Figure_freight_topology.py',
     'The freight module: the carriers, the six truck technologies (colours as in the result figures), the freight '
     'demand, and the limits and price instruments of the realistic layer.'),
    ('Fig02', 'scenario_matrix', FD, 'Figure_freight_scenarios', 'figures_document/Figure_freight_scenarios.py',
     'Scenario matrix: BET costs (X: CAPEX and VOM constant or decreasing) and fuel price (Y: moderate or sharp), '
     'all with the moderate carbon price; what the core runs and the realistic runs contain.'),
    ('Fig03', 'fleet_transition', FR, 'R1_fleet_transition_real', 'analysis_freight.py',
     'Fleet transition with BETs by duty cycle and hydrogen trucks: assignment core, realistic layer without '
     'policies, and realistic layer under current truck and hydrogen policies.'),
    ('Fig04', 'emissions', FR, 'R2_emissions_real', 'analysis_freight.py',
     'Freight CO2 per period and cumulative CO2: core, realistic layer with and without current policies, ICE-only.'),
    ('Fig05', 'cost_of_switching', FR, 'R3_cost_of_switching_real', 'analysis_freight.py',
     'Cost of switching: system cost minus the ICE-only run per period, core (course prices) and realistic layer '
     '(real prices, current policies), with the abatement cost per tonne of CO2 (and without toll and subsidies).'),
    ('Fig06', 'tipping_point', FR, 'R4_tipping_point', 'analysis_freight.py (grids: sensitivity.py)',
     'Tipping point: who serves freight at each fuel price and BET charging penalty, for three truck sets.'),
]
APPENDIX = [
    ('A01', 'freight_demand', FD, 'Figure_freight_demand', 'figures_document/Figure_freight_demand.py',
     'Freight demand: the GDP driver (elasticity 0.6) and the hourly profile of one week, with the Sunday-ban and '
     'night-ban variants of the sensitivity analysis.'),
    ('A02', 'sankey_2030', FR, 'S1_sankey_2030', 'analysis_freight.py (figures/plots/freight_system.py)',
     'Energy flows of the whole system in 2030 with the freight trucks as a sector: F1 core and F1 realistic.'),
    ('A03', 'sankey_2050', FR, 'S1_sankey_2050', 'analysis_freight.py (figures/plots/freight_system.py)',
     'Energy flows of the whole system in 2050: F1 core and F1 realistic.'),
    ('A04', 'freight_final_energy', FR, 'S2_freight_final_energy', 'analysis_freight.py',
     'Final energy of the freight trucks by carrier (labels: freight delivered).'),
    ('A05', 'energy_balance', FR, 'S3_energy_balance_F1_real', 'analysis_freight.py',
     'Final energy by sector and carrier, F1 realistic under current policies.'),
    ('A06', 'hydrogen_supply', FR, 'S4_hydrogen_supply', 'analysis_freight.py',
     'Hydrogen supply by route and the hydrogen the trucks use (incl. the EU targets and renewable H2 at the pump).'),
    ('A07', 'electricity_supply', FR, 'S5_electricity_supply', 'analysis_freight.py (figures/plots/system_plots.py)',
     'Electricity generation by source: F1 core, F1 realistic, F1 realistic with ICE trucks only.'),
    ('A08', 'fleet_transition_core', FR, 'R1_freight_transition', 'analysis_freight.py',
     'Fleet transition in F1-F4 with the assignment\'s ICE trucks and BETs (top) and the change in grid generation '
     'against the ICE-only run (bottom).'),
    ('A09', 'fleet_transition_h2', FR, 'R1_freight_transition_h2', 'analysis_freight.py',
     'Hydrogen extension: fleet transition with FCETs and H2-ICE trucks and the change in grid generation.'),
    ('A10', 'emissions_h2', FR, 'R2_emissions_h2', 'analysis_freight.py',
     'Hydrogen extension: freight CO2 and cumulative CO2.'),
    ('A11', 'cost_of_switching_h2', FR, 'R3_cost_of_switching_h2', 'analysis_freight.py',
     'Hydrogen extension: cost of switching per period and abatement cost.'),
    ('A12', 'water_driver_path', FD, 'Figure_water_driver', 'figures_document/Figure_water_driver.py',
     'Water-scarcity driver: the verdringingsreeks categories, the model\'s water users in each, and the share of '
     'its drought-season reference water each category may use per period; desalination as the backstop.'),
    ('A13', 'water_driver_results', FR, 'A_water_driver', 'analysis_freight.py',
     'Water-scarcity driver, results: drought-season freshwater use under the verdringingsreeks, the desalinated or '
     'reused water above the quotas, and the cost against the same runs without water limits.'),
    ('A14', 'emissions_core', FR, 'R2_emissions', 'analysis_freight.py',
     'Freight truck CO2 per period and cumulative CO2 2020-2059 of trucks, cars and the rest of the system, core '
     'runs and the ICE-only counterfactual.'),
    ('A15', 'sensitivities', FR, 'R5_sensitivities', 'analysis_freight.py',
     'Sensitivities of the assignment for F1 and F4, core and realistic: carbon price (central, high) and time '
     'restrictions (Sunday ban, night ban); colour = change against the base run.'),
    ('A16', 'transition_speed', FR, 'R7_transition_speed', 'analysis_freight.py',
     'Speed of the transition: zero-emission share of freight per period (core, realistic without and with current '
     'policies) inside the corridor of the realistic layer, and the value of a faster ramp-up (shadow price).'),
    ('A17', 'policy_levers', FR, 'R6_policy_levers', 'analysis_freight.py',
     'Policy and market levers of the realistic layer for F1 and F4 (incl. the water-scarcity driver); colour = '
     'change against current policies.'),
    ('A18', 'model_overview', FD, 'Figure_model_overview_freight',
     'figures_document/Figure_model_overview_freight.py',
     'Model structure: the course model with the group\'s hydrogen module (teal) and heavy-duty road freight (blue). '
     'Pink boxes are outside drivers: hourly profiles, the water-scarcity driver and the macroeconomic drivers.'),
]
METHOD_SCRIPTS = ['figures_document/Figure_model_overview_freight.py', 'figures_document/Figure_freight_topology.py',
                  'figures_document/Figure_freight_scenarios.py', 'figures_document/Figure_freight_demand.py',
                  'figures_document/Figure_water_driver.py']


def collect(items, folder):
    """Copy each figure (png + svg) to folder under its number (old copies are removed first); returns the rows for
    FIGURES.md."""
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(folder):
        if f.endswith(('.png', '.svg')):
            os.remove(os.path.join(folder, f))
    rows = []
    for num, stem, src, src_stem, script, caption in items:
        found = False
        for ext in ('png', 'svg'):
            p = os.path.join(src, f'{src_stem}.{ext}')
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(folder, f'{num}_{stem}.{ext}'))
                found = True
        rows.append(f'| {num} | {caption} | `{src}/{src_stem}.png`{"" if found else " (missing)"} | `{script}` |')
    return rows


def main(redraw=False):
    if redraw:
        for s in METHOD_SCRIPTS:
            subprocess.run([sys.executable, s], check=True)
    head = ['| No. | Caption | Source | Drawn by |', '|---|---|---|---|']
    md = ['# Figures of the paper and the appendix', '',
          'Made by `python figure_set.py` from the methodology figures (`figures_document/`) and the result figures '
          '(`python analysis_freight.py`). Numbered copies: `results/plots/paper/` and `results/plots/appendix/` '
          '(png at 300-400 dpi and svg).', '', '## Paper', '', *head, *collect(PAPER, os.path.join(OUT, 'paper')),
          '', '## Appendix', '', *head, *collect(APPENDIX, os.path.join(OUT, 'appendix')), '']
    open(os.path.join(OUT, 'FIGURES.md'), 'w').write('\n'.join(md))
    print('\n'.join(md))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--redraw', action='store_true', help='redraw the methodology figures first')
    main(ap.parse_args().redraw)
