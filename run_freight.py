"""Freight study: run registry and batch runner (individual assignment 'Trucks in transition').

Usage:  python run_freight.py --list                     (the run groups and their runs; also when nothing is given)
        python run_freight.py --group assignment          (a group of runs, see GROUPS; --group can be repeated)
        python run_freight.py F1_nofcet F1_ice            (runs by name)
        python run_freight.py --solver gurobi F1_real
Runs already in results/runs are skipped (--rerun solves them again). A run typically takes several minutes.

Scenario matrix (assignment): X = BET costs ('constant' / 'decrease'), Y = gasoline price ('moderate' / 'sharp');
all with a moderately increasing carbon price (co2_price='low': ETS1 75/130/170 €/t, ETS2 55/55/170 €/t).
Every run also has the group's hydrogen module (1.3 Mt industrial demand, SMR / SMR + CCS / electrolysis).
Truck sets: '_nofcet' = the assignment's ICE trucks and BETs only (the core); no suffix = the hydrogen extension with
the two hydrogen trucks, fuel cell (FCET) and hydrogen combustion engine (H2-ICE truck); '_ice' = ICE trucks only
(counterfactual for the cost of switching).
Tests (assignment step 5, 'start with some tests and make sure the model is reasonably well calibrated'): the 90 PJ
read as fuel input, real diesel prices, fuel without excise, the course coordinator's high charging penalty, 6-hour
time steps and the base year without the 'existing' truck stock (group 'tests'; see TESTS).
Realistic layer: '_real' = the same four scenarios under the current truck and hydrogen policies, with real prices and
market frictions and all four truck types (twins '_real_noh2', '_real_ice', '_real_nopolicy'; see REAL below).
Water scarcity is not a scenario axis: water is unlimited in every run except the water-scarcity driver runs
('_real_water': the verdringingsreeks in droughts that tighten over time, desalination as the backstop; group 'water').
Every run is in a group and every group is behind the paper (group 'paper' = all runs).
Each run is (base scenario, settings); `run(name)` solves it into results/runs/<name>.nc.
"""
import argparse
import os
import time
import warnings

warnings.filterwarnings('ignore')
from energy_model import model_run, make_scenario
from energy_model.freight_presets import FREIGHT_SCENARIOS, FREIGHT_LABELS, OWE_SUBSIDY

try:
    from scenario_database import snapshot
except ImportError:
    snapshot = None

SOLVER = 'gurobi'
YEARS, T_RES, CARS_CF, RT, RS = [2020, 2030, 2040, 2050], 15, 40 * 0.1, 0.07, 0.01
DB = 'input_databases//freight_nl'
RUN_DIR = os.path.join('results', 'runs')
BASE = dict(co2_price='low')                 # 'constant or moderately increasing' carbon price (assignment)


def freight(f, **extra):
    """(base, settings) of scenario f (F1-F4) of the assignment matrix: BET costs (X) and gasoline price (Y) on the
    group's S1 (no water limit) with the moderate carbon price, plus any extra settings."""
    bet, gas = FREIGHT_SCENARIOS[f]
    return ('S1', {**BASE, 'bet_costs': bet, 'gasoline_price': gas, 'label': FREIGHT_LABELS[f], **extra})


# The four scenarios. '_nofcet': the assignment's own technology set (ICE trucks + BETs; fcet=False switches both
# hydrogen trucks off), the core of the paper. No suffix: the hydrogen extension (+ FCET + H2-ICE truck). '_ice': no
# zero-emission trucks, the counterfactual for the cost of switching.
RUNS = {}
for f in FREIGHT_SCENARIOS:
    RUNS[f] = freight(f)
    RUNS[f'{f}_ice'] = freight(f, ice_only=True)
    RUNS[f'{f}_nofcet'] = freight(f, fcet=False)
# The assignment's sensitivities (step 5): carbon price and time restrictions, for the corners F1 and F4, in the core
# and in the extension
SENS = {'co2central': dict(co2_price='central'), 'co2high': dict(co2_price='high'),
        'sunday_ban': dict(freight_profile='sunday_ban'), 'night_ban': dict(freight_profile='night_ban')}
for f in ('F1', 'F4'):
    for k, s in SENS.items():
        RUNS[f'{f}_{k}'] = freight(f, **s)
        RUNS[f'{f}_{k}_nofcet'] = freight(f, fcet=False, **s)
# Tests (step 5: 'start with some tests and make sure the model is reasonably well calibrated in all scenarios'). The
# 2020 calibration itself (existing stock only) is in every run; these test the inputs behind it (core set, F1 = the
# scenario least favourable to BETs):
#   _fuel90   the 90 PJ read as fuel input instead of truck output (x0.4 at 40%): as output it triples truck CO2
#   _diesel   real diesel prices for the trucks (ex VAT, 105 -> 160 €/MWh) instead of the course gasoline price
#   _untaxed  fuel without excise (70 -> 85 €/MWh): how much of the switch is a tax effect
#   _vom3     the course coordinator's high-VOM variant: BET charging penalty x3 (0.30 €/kWh)
#   _tres6    6-hour instead of 15-hour time steps (TRES; hydrogen extension, 40-65 min): does the resolution matter?
#   _nostock  no 2020 truck stock (truck_stock=False): the assignment's question 'do you need a series of existing
#             technologies for a well-calibrated base year?'
TESTS = {'F1_fuel90_nofcet': freight('F1', freight_scale=0.4, fcet=False),
         'F4_fuel90_nofcet': freight('F4', freight_scale=0.4, fcet=False),
         'F1_diesel_nofcet': freight('F1', truck_fuel_price='diesel_nl', fcet=False),
         'F1_untaxed_nofcet': freight('F1', gasoline_price='untaxed', fcet=False),
         'F1_vom3_nofcet': freight('F1', bet_vom_factor=3.0, fcet=False),
         'F1_tres6': freight('F1'),
         'F1_nostock_nofcet': freight('F1', truck_stock=False, fcet=False)}
TRES = {'F1_tres6': 6}                       # time step (hours) of runs that do not use T_RES
RUNS.update(TESTS)
# Realistic layer: the four scenarios on the same X/Y axes (BET costs x fuel price, moderate CO2 price) under the
# policies in force or planned in October 2026, with realistic prices and the real-world frictions the policies act on
# (freight_presets.py, 'Realistic layer').
#   Truck policies: EU CO2 standards for new trucks -> a floor on the zero-emission share of freight ('eu_hdv_fleet');
#   the Dutch truck toll and the AanZET purchase subsidy it funds.
#   Hydrogen policies: RED III's RFNBO target for transport (ERE system); the Dutch annual RFNBO obligation for industry
#   (4% in 2030, 9.9% from 2035); OWE electrolyser subsidies; SWiM support for hydrogen trucks; AFIR's hydrogen
#   stations behind the hydrogen-truck availability.
#   ETS1 and ETS2 stay in the carbon price (co2_price 'low', the moderate path the assignment asks for).
#   Frictions and prices: BETs by duty cycle (urban / regional / long haul), a heavy special segment for ICE or H2-ICE
#   trucks only, the market ramp-up, hydrogen-truck availability, diesel ex VAT (scaled by the Y axis), mid-range
#   hydrogen delivery.
# '_real' has all four truck types; '_real_noh2' the assignment's set (ICE + BET, by duty cycle; RED III transport is
# then met outside road freight, which the model does not contain); '_real_ice' the ICE-only counterfactual at the
# same prices, toll and hydrogen policies (cost of switching); '_real_nopolicy' the frictions and prices without any
# truck or hydrogen policy (the carbon price stays); '_real_h2eu' the EU hydrogen targets met in full (RED III:
# 60% RFNBO in industry from 2040, the stronger transport path).
REAL_FRICTIONS = dict(bet_tiers='nl', ze_max_share='market', h2_truck_max_share='market', freight_heavy_share=0.05,
                      fcet_vom_factor=1.5)
TRUCK_POLICIES = dict(ze_min_share='eu_hdv_fleet', truck_toll='nl2026', bet_capex_subsidy='aanzet')
H2_POLICIES = dict(rfnbo_transport='red3', green_mandate='nl_jaarverplichting', electrolyser_subsidy=OWE_SUBSIDY,
                   h2truck_capex_subsidy='swim')
REAL_POLICIES = {**TRUCK_POLICIES, **H2_POLICIES}
REAL = {**REAL_FRICTIONS, **REAL_POLICIES}
NO_POLICY = dict(ze_min_share=None, truck_toll=None, bet_capex_subsidy=None, rfnbo_transport=None, green_mandate=None,
                 electrolyser_subsidy=0.0, h2truck_capex_subsidy=None)
ZE_TRUCK_ONLY = dict(ze_min_share=None, rfnbo_transport=None, bet_capex_subsidy=None, h2truck_capex_subsidy=None)
REAL_FUEL = {'moderate': 'diesel_nl', 'sharp': 'diesel_nl_sharp'}


def real(f, **extra):
    """(base, settings) of scenario f in the realistic layer: freight(f) plus the frictions, the current truck and
    hydrogen policies and the trucks' diesel price on the scenario's Y path, plus any extra settings."""
    return freight(f, **{**REAL, 'truck_fuel_price': REAL_FUEL[FREIGHT_SCENARIOS[f][1]], **extra})


for f in FREIGHT_SCENARIOS:
    RUNS[f'{f}_real'] = real(f)
    RUNS[f'{f}_real_noh2'] = real(f, fcet=False)
    RUNS[f'{f}_real_ice'] = real(f, ice_only=True, **ZE_TRUCK_ONLY)    # keeps the toll and the industry H2 policies
    RUNS[f'{f}_real_nopolicy'] = real(f, **NO_POLICY)                  # frictions and prices without the policies
for f in ('F1', 'F4'):
    for k, s in SENS.items():
        RUNS[f'{f}_real_{k}'] = real(f, **s)                              # carbon price, time restrictions
    RUNS[f'{f}_real_nolimit'] = real(f, ze_max_share=None, h2_truck_max_share=None)   # no ramp-up or H2 limits
    RUNS[f'{f}_real_h2eu'] = real(f, green_mandate='red3', rfnbo_transport='ambition')  # EU hydrogen targets in full
RUNS['F1_real_noheavy'] = real('F1', freight_heavy_share=None)             # no heavy-duty special segment
# Green hydrogen for the trucks: under current policies the hydrogen trucks run mostly on blue hydrogen. Tests:
# renewable hydrogen at the pump (an RFNBO obligation on all hydrogen sold to road transport) and a price-based
# alternative (an H2Global / CfD-type production subsidy of €1/kg for electrolytic hydrogen). Water stays unlimited.
for f in ('F1', 'F3'):
    RUNS[f'{f}_real_h2green'] = real(f, h2_trucks_rfnbo=True)
RUNS['F1_real_h2subsidy'] = real('F1', h2_production_subsidy=1.0)
# Net zero in the realistic layer: the Klimaatwet / EU 2040 path as a cap on the CO2 of the whole system, with
# renewable hydrogen at the pump (a net-zero system cannot fuel its trucks with fossil-based hydrogen)
for f in ('F1', 'F4'):
    RUNS[f'{f}_real_netzero'] = real(f, co2_cap='netzero', h2_trucks_rfnbo=True)
# Water scarcity as an outside driver (like GDP for the demands), not a scenario axis: the drought-season water of the
# verdringingsreeks tightens over time (water_scarcity='driver': a 1-in-20 dry year in 2030 and 2040, a 2018-type
# drought in 2050, more summer derating of river-cooled plants), with desalinated or reused water at €1.4/m3 as the
# backstop. '_ely4': electrolysis in the lowest priority category of the verdringingsreeks (4) instead of 3.
for f in ('F1', 'F4'):
    RUNS[f'{f}_real_water'] = real(f, water_scarcity='driver')
RUNS['F1_real_water_ely4'] = real('F1', water_scarcity='driver', electrolysis_category=4)

# Run groups for the command line (--group). 'assignment' is what the assignment asks for within its specs (the four
# scenarios with ICE trucks and BETs, the ICE-only twins for the cost of switching, the carbon-price and
# time-restriction sensitivities and the calibration tests); 'paper' adds the hydrogen extension, the realistic layer
# and the water-scarcity driver: every run in RUNS.
GROUPS = {
    'core': [f'{f}_nofcet' for f in FREIGHT_SCENARIOS] + [f'{f}_ice' for f in FREIGHT_SCENARIOS],
    'core_sensitivity': [f'{f}_{k}_nofcet' for f in ('F1', 'F4') for k in SENS],
    'tests': list(TESTS),
    'h2': list(FREIGHT_SCENARIOS) + [f'{f}_{k}' for f in ('F1', 'F4') for k in SENS],
    'real': [f'{f}{t}' for f in FREIGHT_SCENARIOS for t in ('_real', '_real_noh2', '_real_ice', '_real_nopolicy')],
    'real_sensitivity': [f'{f}_real_{k}' for f in ('F1', 'F4') for k in SENS],
    'real_tests': ['F1_real_h2green', 'F3_real_h2green', 'F1_real_h2subsidy', 'F1_real_netzero', 'F4_real_netzero',
                   'F1_real_h2eu', 'F4_real_h2eu', 'F1_real_nolimit', 'F4_real_nolimit', 'F1_real_noheavy'],
    'water': ['F1_real_water', 'F4_real_water', 'F1_real_water_ely4'],      # the water-scarcity driver
}
GROUPS['assignment'] = GROUPS['core'] + GROUPS['core_sensitivity'] + GROUPS['tests']
GROUPS['paper'] = (GROUPS['assignment'] + GROUPS['h2'] + GROUPS['real'] + GROUPS['real_sensitivity']
                   + GROUPS['real_tests'] + GROUPS['water'])
assert all(r in RUNS for g in GROUPS.values() for r in g), 'a run group names a run that is not in RUNS'
assert sorted(GROUPS['paper']) == sorted(RUNS), 'every run must be in exactly one group behind the paper'

def solver_options(solver):
    """Return the Gurobi options used for every model run."""
    if solver != 'gurobi':
        raise ValueError(f"Unsupported solver {solver!r}; this project requires 'gurobi'.")
    return {'Threads': 1, 'TimeLimit': 7200}


def run(name, solver=SOLVER, rerun=False, t_res=T_RES, settings=None, base='S1', run_dir=RUN_DIR, db=DB):
    """Solve one run (from RUNS, or any name with explicit base and settings) and save it as <run_dir>/<name>.nc.
    Returns the path, or None when the model is infeasible; a run on disk is not solved again unless rerun=True."""
    path = os.path.join(run_dir, f'{name}.nc')
    if settings is None:
        base, settings = RUNS[name]
        t_res = TRES.get(name, t_res)
    if os.path.exists(path) and not rerun:
        return path
    db = snapshot(db, name, settings) if snapshot is not None else db
    t = time.time()
    n = model_run(db, YEARS, t_res, CARS_CF, RT, RS, solver_name=solver, solver_options=solver_options(solver),
                  scenario=make_scenario(base, **dict(settings, label=settings.get('label', name))),
                  results_dir=os.path.join('results', 'logs'))
    if n.loads_t.p.empty:
        print(f'{name}: NOT solved (infeasible?) - nothing saved')
        return None
    os.makedirs(run_dir, exist_ok=True)
    n.export_to_netcdf(path)
    print(f'{name}: solved in {time.time() - t:.0f} s')
    return path


def list_groups():
    """Print every run group with its runs and how many of them are on disk."""
    for g, rs in GROUPS.items():
        done = sum(os.path.exists(os.path.join(RUN_DIR, f'{r}.nc')) for r in rs)
        names = ' '.join(rs) if g != 'paper' else 'every run in RUNS'
        print(f'{g:17s} {len(rs):3d} runs, {done:3d} on disk: {names}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('names', nargs='*', help='run names (keys of RUNS)')
    ap.add_argument('--group', action='append', default=[], choices=list(GROUPS), help='a run group (repeatable)')
    ap.add_argument('--list', action='store_true', help='show the run groups and their runs, then stop')
    ap.add_argument('--solver', choices=['gurobi'], default=SOLVER)
    ap.add_argument('--rerun', action='store_true', help='solve runs again that are already on disk')
    a = ap.parse_args()
    todo = list(dict.fromkeys([r for g in a.group for r in GROUPS[g]] + a.names))   # in order, without duplicates
    unknown = [r for r in todo if r not in RUNS]
    if unknown:
        ap.error('unknown run(s): ' + ', '.join(unknown) + ' (see --list)')
    if a.list or not todo:
        list_groups()
        if not todo:
            print('\nNothing to run: give run names or --group <name>.')
    else:
        for nm in todo:
            run(nm, a.solver, a.rerun)
