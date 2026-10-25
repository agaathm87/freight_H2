"""Tables for the paper, built from the model settings and the saved outputs.

    Table 1   scenario settings: Panel A the assignment's trucks, Panel B the scenario axes and the realistic layer
    Table 2   sensitivities in 2030 and 2050: Panel A the core (ICE + BET), Panel B the realistic layer
    Table A2  truck parameters by period (all truck types)
    Table A3  calibration and tests (assignment step 5)

Run it after analysis_freight.py, which writes the CSVs it reads:   python paper_tables.py
Output in results/outputs/paper_tables/: one CSV per table panel, paper_tables.md (all tables with APA titles and
notes, as in the paper outline) and paper_tables.xlsx (one sheet per panel, to paste into Word).
Settings come from energy_model/freight_presets.py, energy_model/h2_presets.py and run_freight.py, so the tables follow
any change there; results come from results/outputs/freight_summary.csv, freight_total_cost.csv and
freight_calibration_tests.csv.
"""
import os

import pandas as pd

from energy_model.freight_presets import (BET_COSTS, BET_SUBSIDIES, BET_TIERS, FCET_PARAMS, FREIGHT_SCENARIOS,
                                          GASOLINE_PRICES, GREEN_MANDATES, H2_TRUCK_SHARES, H2ICE_PARAMS,
                                          H2TRUCK_SUBSIDIES, KG_PER_MWH, RFNBO_TRANSPORT,
                                          TRUCK_FUEL_PRICES, TRUCK_TOLLS, ZE_MANDATES)
from energy_model.h2_presets import CO2_PRICES, CO2_PRICES_ETS2
from run_freight import BASE, RUNS

YEARS = [2020, 2030, 2040, 2050]
OUTPUTS = os.path.join('results', 'outputs')
OUT = os.path.join(OUTPUTS, 'paper_tables')
DB = os.path.join('input_databases', 'freight_nl', 'technologies.xlsx')
DASH = '–'
REAL = RUNS['F1_real'][1]                          # the realistic layer's settings (the same in F1-F4 but the fuel)
CO2 = BASE['co2_price']                            # the assignment's moderate carbon price ('low')
KWH_PER_KG = 1000.0 / KG_PER_MWH


# --------------------------------------------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------------------------------------------
def num(v, nd=0):
    """A number with nd decimals, a thousands separator and a true minus sign; '–' for None."""
    return DASH if v is None or pd.isna(v) else f'{v:,.{nd}f}'.replace('-', '\u2212')


def signed(v, nd=1):
    """A change with its sign: '+3.6', '\u221214.7'."""
    return f'{v:+.{nd}f}'.replace('-', '\u2212')


def fine(v, nd=1):
    """nd decimals, but two for small values (0.01) and for shares just below 100 (99.95)."""
    if v is None or pd.isna(v):
        return DASH
    return num(v, 2) if (0 < abs(v) < 0.1 or 99.9 < v < 100) else num(v, nd)


def pct(v):
    """A share (0.099) as a percentage ('9.9%'); whole numbers without decimals."""
    if v is None or pd.isna(v):
        return DASH
    p = 100.0 * float(v)
    return f'{p:.0f}%' if abs(p - round(p)) < 1e-9 else f'{p:.1f}%'


def by_year(values, fmt, skip_zero=False, years=YEARS):
    """One formatted value per period from {year: value}; '–' where the value is missing (or zero, if skip_zero)."""
    out = []
    for y in years:
        v = values.get(y, values.get(str(y))) if isinstance(values, dict) else values
        out.append(DASH if v is None or (skip_zero and float(v) == 0.0) else fmt(v))
    return out


def path_text(values, fmt, years=YEARS):
    """'650' when constant over the periods, else '650 / 420 / 325 / 290' (2020 / 2030 / 2040 / 2050)."""
    vals = [values[y] for y in years]
    return fmt(vals[0]) if all(v == vals[0] for v in vals) else ' / '.join(fmt(v) for v in vals)


def scenarios_with(axis, level):
    """The scenarios (F1-F4) with this level on an axis: 'bet' (X, BET costs) or 'fuel' (Y, gasoline price)."""
    i = 0 if axis == 'bet' else 1
    return ', '.join(f for f, v in FREIGHT_SCENARIOS.items() if v[i] == level)


def md_table(df):
    """A pipe table (markdown) of a DataFrame with string cells."""
    head = '| ' + ' | '.join(df.columns) + ' |'
    rule = '| ' + ' | '.join('---' for _ in df.columns) + ' |'
    rows = ['| ' + ' | '.join(str(c).replace('|', '/') for c in r) + ' |' for r in df.itertuples(index=False)]
    return '\n'.join([head, rule] + rows)


# --------------------------------------------------------------------------------------------------------------
# Table 1: scenario settings
# --------------------------------------------------------------------------------------------------------------
def table1_trucks():
    """Panel A: the assignment's ICE truck and BET, the 2020 stock (database values)."""
    d = pd.read_excel(DB, 'dynamic_parameters').set_index(['Technology', 'Parameter'])
    c = pd.read_excel(DB, 'capacity_constraints')
    v = lambda t, p: float(d.loc[(t, p), 2020])
    bet_stock = float(c[(c.Technology == 'BET - existing') & (c.Type == 'min')][2020].iloc[0]) / 1e3
    x_fall = scenarios_with('bet', 'decrease')
    rows = [
        ('CAPEX (€/kW of output)', num(v('ICE truck', 'CAPEX')),
         f"{num(v('BET', 'CAPEX'))} (falling in {x_fall}: Panel B)"),
        ('FOM (€/kW/yr)', num(v('ICE truck', 'FOM')), num(v('BET', 'FOM'))),
        ('VOM (€/kWh of input)', num(v('ICE truck', 'VOM'), 2),
         f"{num(v('BET', 'VOM'), 2)} (falling in {x_fall}: Panel B)"),
        ('Efficiency (%)', num(100 * v('ICE truck', 'Efficiency')), num(100 * v('BET', 'Efficiency'))),
        ('Lifetime (years)', num(v('ICE truck', 'Lifetime')), num(v('BET', 'Lifetime'))),
        ('CO2 (t/MWh of fuel)', num(v('ICE truck', 'Emissions'), 2), DASH),
        ('2020 stock (2020 only)', 'ICE truck – existing, size set by the model',
         f'BET – existing, {num(bet_stock, 1)} GW'),
    ]
    return pd.DataFrame(rows, columns=['Parameter', 'ICE truck', 'BET'])


def table1_settings():
    """Panel B: the scenario axes, the carbon price and the realistic layer, per period."""
    summary = pd.read_csv(os.path.join(OUTPUTS, 'freight_summary.csv')).set_index(['run', 'period'])
    demand = {y: summary.loc[('F1_nofcet', y), 'Freight demand (TWh/yr)'] for y in YEARS}
    cols = ['Setting', 'Scenarios'] + [str(y) for y in YEARS] + ['Source']
    x_c, x_d = scenarios_with('bet', 'constant'), scenarios_with('bet', 'decrease')
    y_m, y_s = scenarios_with('fuel', 'moderate'), scenarios_with('fuel', 'sharp')
    blank = [''] * (len(YEARS) + 2)
    rows = [['**Scenario axes and carbon price (all runs)**'] + blank,
            ['Freight demand (TWh/yr of truck output)', 'All', *by_year(demand, lambda v: num(v, 1)),
             'Assignment (90 PJ in 2020); GDP elasticity 0.6 (KiM, 2021: ~1.0 in the short run)'],
            ['BET CAPEX (€/kW)', x_c, *by_year(BET_COSTS['constant']['CAPEX'], num), 'Assignment'],
            ['', x_d, *by_year(BET_COSTS['decrease']['CAPEX'], num), 'Link et al. (2024)'],
            ['BET VOM, the charging penalty (€/kWh of electricity)', x_c,
             *by_year(BET_COSTS['constant']['VOM'], lambda v: num(v, 2)), 'Assignment'],
            ['', x_d, *by_year(BET_COSTS['decrease']['VOM'], lambda v: num(v, 2)),
             'Charging roll-out (Regulation (EU) 2023/1804)'],
            ['Gasoline price, with excise (€/MWh)', y_m, *by_year(GASOLINE_PRICES['moderate'], num), 'IISD (2025)'],
            ['', y_s, *by_year(GASOLINE_PRICES['sharp'], num), 'Course database'],
            ['Carbon price, ETS1 (€/t CO2)', 'All', *by_year(CO2_PRICES[CO2], num),
             'Group model (Učelniece et al., 2026)'],
            ['Carbon price, ETS2 on road fuels (€/t CO2)', 'All', *by_year(CO2_PRICES_ETS2[CO2], num, skip_zero=True),
             'van der Veen et al. (2026, p. 17)'],
            ['**Realistic layer (F1_real to F4_real)**'] + blank]
    ze_min, ze_max = ZE_MANDATES[REAL['ze_min_share']], ZE_MANDATES[REAL['ze_max_share']]
    h2_max = H2_TRUCK_SHARES[REAL['h2_truck_max_share']]
    rows += [['Zero-emission share of freight, minimum (CO2 standards)', 'All', *by_year(ze_min, pct),
              'Regulation (EU) 2024/1610; Transport & Environment (2024)'],
             ['Zero-emission share of freight, maximum (market ramp-up)', 'All', *by_year(ze_max, pct),
              'Mulholland & Benoit (2026)'],
             ['Hydrogen trucks (FCET + H2-ICE), maximum share of freight', 'All', *by_year(h2_max, pct),
              'Regulation (EU) 2023/1804; Electrive (2026)']]
    tiers = BET_TIERS[REAL['bet_tiers']]
    urban, regional = tiers['BET - urban'], tiers['BET']
    rows += [["BET duty cycles, share of freight: urban at most / regional (the assignment's BET) the next; "
              "long haul the rest (costs: Table A2)",
              'All', DASH, *[f"{pct(urban['share'])} / {pct(regional['share'])}"] * (len(YEARS) - 1),
              'TNO (2021); Sharpe & Basma (2022); Basma et al. (2022); Milence (2025)'],
             ['Heavy special segment, ICE or H2-ICE trucks only (share of freight)', 'All',
              *by_year({y: REAL['freight_heavy_share'] for y in YEARS}, pct),
              'Wang & Ahluwalia (2026); MAN Truck & Bus (2024)']]
    toll = TRUCK_TOLLS[REAL['truck_toll']]
    rows += [['Truck toll, ICE / zero-emission (€/km)', 'All',
              *[DASH if toll['ICE'][y] == 0 else f"{num(toll['ICE'][y], 2)} / {num(toll['ZE'][y], 3)}"
                for y in YEARS], 'Ministerie van Infrastructuur en Waterstaat (2026)'],
             ['Purchase subsidy for BETs, AanZET (share of CAPEX)', 'All',
              *by_year(BET_SUBSIDIES[REAL['bet_capex_subsidy']], pct, skip_zero=True), 'RVO (2026a)'],
             ['Purchase subsidy for hydrogen trucks, SWiM (share of CAPEX)', 'All',
              *by_year(H2TRUCK_SUBSIDIES[REAL['h2truck_capex_subsidy']], pct, skip_zero=True), 'RVO (2026b)'],
             ['Electrolyser subsidy, OWE (share of CAPEX)', 'All',
              *by_year(REAL['electrolyser_subsidy'], pct, skip_zero=True), 'RVO (n.d.); Rijksoverheid (2025)'],
             ['Renewable hydrogen in road transport (share of road-transport energy, counted double)', 'All',
              *by_year(RFNBO_TRANSPORT[REAL['rfnbo_transport']], pct), 'Directive (EU) 2023/2413'],
             ['Renewable hydrogen in industry, Dutch obligation (share of industrial hydrogen)', 'All',
              *by_year(GREEN_MANDATES[REAL['green_mandate']], pct),
              'Tweede Kamer der Staten-Generaal (2026); KGG (2026)']]
    fuel = {}
    for f in FREIGHT_SCENARIOS:
        fuel.setdefault(RUNS[f'{f}_real'][1]['truck_fuel_price'], []).append(f)
    for i, (key, fs) in enumerate(fuel.items()):
        rows.append(['Diesel price for trucks, without VAT (€/MWh)' if i == 0 else '', ', '.join(fs),
                     *by_year(TRUCK_FUEL_PRICES[key], num),
                     'Weekly Oil Bulletin (European Commission, n.d.)' if i == 0 else "The course's sharp-to-moderate ratio"])
    h2_cost = {y: FCET_PARAMS['VOM'][y] * REAL['fcet_vom_factor'] * KWH_PER_KG for y in YEARS}
    rows.append(['Hydrogen delivery and station cost (€/kg; ×1.5 of the extension)', 'All',
                 DASH, *by_year(h2_cost, lambda v: num(v, 2), years=YEARS[1:]), 'Chung & Wang (2024)'])
    t = pd.DataFrame(rows, columns=cols)
    return t, ze_max, h2_max


# --------------------------------------------------------------------------------------------------------------
# Table 2: sensitivities
# --------------------------------------------------------------------------------------------------------------
SENS_ROWS = [('', 'moderate carbon price (base)'), ('co2central', 'central carbon price'),
             ('co2high', 'high carbon price'), ('sunday_ban', 'Sunday ban'), ('night_ban', 'night ban')]


def table2(layer):
    """Panel A (layer 'core': the _nofcet runs) or B (layer 'real'): F1 and F4 with the assignment's sensitivities."""
    s = pd.read_csv(os.path.join(OUTPUTS, 'freight_summary.csv')).set_index(['run', 'period'])
    cost = pd.read_csv(os.path.join(OUTPUTS, 'freight_total_cost.csv'), index_col=0)['Total discounted cost (bn €)']
    rows = []
    for f in ('F1', 'F4'):
        base = f'{f}_nofcet' if layer == 'core' else f'{f}_real'
        for key, label in SENS_ROWS:
            run = base if not key else (f'{f}_{key}_nofcet' if layer == 'core' else f'{f}_real_{key}')
            dc = cost[run] - cost[base]
            rows.append([f'{f}, {label}',
                         num(s.loc[(run, 2030), 'ZE share of freight (%)'], 1),
                         num(s.loc[(run, 2030), 'BET capacity (GW)'], 1),
                         num(s.loc[(run, 2050), 'BET capacity (GW)'], 1),
                         num(s.loc[(run, 2030), 'CO2 total (Mt/yr)'], 1),
                         num(s.loc[(run, 2050), 'CO2 total (Mt/yr)'], 1),
                         DASH if run == base else signed(dc),
                         DASH if run == base else signed(100 * dc / cost[base])])
    cols = ['Scenario and sensitivity', 'Zero-emission share 2030 (%)', 'BET capacity 2030 (GW)',
            'BET capacity 2050 (GW)', 'System CO2 2030 (Mt/yr)', 'System CO2 2050 (Mt/yr)',
            'Cost change (bn €)', 'Cost change (%)']
    return pd.DataFrame(rows, columns=cols)


# --------------------------------------------------------------------------------------------------------------
# Table A2: truck parameters by period
# --------------------------------------------------------------------------------------------------------------
def table_a2():
    """All truck types, with paths 2020 / 2030 / 2040 / 2050 where a value changes."""
    d = pd.read_excel(DB, 'dynamic_parameters').set_index(['Technology', 'Parameter'])

    def series(tech, par, start=2020):
        return {y: (float(d.loc[(tech, par), y]) if y >= start else None) for y in YEARS}

    def path(values, fmt):
        vals = [values[y] for y in YEARS]
        known = [v for v in vals if v is not None]
        if all(v == known[0] for v in known):          # constant (from its first period on)
            return fmt(known[0])
        return ' / '.join(DASH if v is None else fmt(v) for v in vals)

    i0, i2 = (lambda v: num(v)), (lambda v: num(v, 2))
    i3 = lambda v: f'{v:.3f}'.rstrip('0').rstrip('.') if v < 0.1 else f'{v:.2f}'
    eff = lambda v: num(100 * v)
    tiers = BET_TIERS[REAL['bet_tiers']]
    rows = []
    for tech, label, runs, start in [('ICE truck', 'ICE truck', 'All', 2030),
                                     ('ICE truck - existing', 'ICE truck – existing (2020 stock)', 'All', 2020)]:
        rows.append([label, runs, path(series(tech, 'CAPEX'), i0), path(series(tech, 'FOM'), i0),
                     path(series(tech, 'VOM'), i2), path(series(tech, 'Efficiency'), eff),
                     path(series(tech, 'Lifetime'), i0), 'Assignment'])
    for lvl in ('constant', 'decrease'):
        rows.append([f"BET ({'constant' if lvl == 'constant' else 'falling'} costs)", scenarios_with('bet', lvl),
                     path_text(BET_COSTS[lvl]['CAPEX'], i0), path(series('BET', 'FOM'), i0),
                     path_text(BET_COSTS[lvl]['VOM'], i2), path(series('BET', 'Efficiency'), eff),
                     path(series('BET', 'Lifetime'), i0), 'Assignment' if lvl == 'constant' else 'Link et al. (2024)'])
    rows.append(['BET – existing (2020 stock)', 'All', path(series('BET - existing', 'CAPEX'), i0),
                 path(series('BET - existing', 'FOM'), i0), path(series('BET - existing', 'VOM'), i2),
                 path(series('BET - existing', 'Efficiency'), eff), path(series('BET - existing', 'Lifetime'), i0),
                 'Assignment'])
    for tech, label in [('BET - urban', 'BET – urban (from 2030)'), ('BET - long haul', 'BET – long haul (from 2030)')]:
        f = tiers[tech]
        rows.append([label, 'Realistic layer', f"×{f['capex']:g} of the BET", f"×{f['capex']:g} of the BET",
                     f"×{f['vom']:g} of the BET", path(series('BET', 'Efficiency'), eff),
                     path(series('BET', 'Lifetime'), i0), 'Sharpe & Basma (2022); Basma et al. (2022); Milence (2025)'])
    for params, label, src in [(FCET_PARAMS, 'FCET (from 2030)', 'Basma & Rodríguez (2023); Link et al. (2024)'),
                               (H2ICE_PARAMS, 'H2-ICE truck (from 2030)', 'Basma et al. (2023); MAN Truck & Bus (2024)')]:
        p = {k: {y: (v[y] if y >= 2030 else None) for y in YEARS} for k, v in params.items()}
        rows.append([label, 'Extension and realistic layer', path(p['CAPEX'], i0),
                     path(p['FOM'], lambda v, nd=int(any(x % 1 for x in params['FOM'].values())): num(v, nd)),
                     path(p['VOM'], i3),
                     path(p['Efficiency'], eff), path(p['Lifetime'], i0), src])
    cols = ['Truck', 'Runs', 'CAPEX (€/kW)', 'FOM (€/kW/yr)', 'VOM (€/kWh of input)', 'Efficiency (%)',
            'Lifetime (years)', 'Source']
    return pd.DataFrame(rows, columns=cols)


# --------------------------------------------------------------------------------------------------------------
# Table A3: calibration and tests
# --------------------------------------------------------------------------------------------------------------
TESTS = {'base year': 'Calibrated base year (the 2020 stock)', 'fuel90': '90 PJ read as fuel, not as truck output',
         'diesel': "Diesel without VAT instead of the course's gasoline price",
         'untaxed': 'Fuel without excise (70–85 €/MWh)', 'vom3': 'Charging penalty ×3 (0.30 €/kWh)',
         'tres6': '6-hour instead of 15-hour time steps', 'nostock': 'No 2020 truck stock'}


def table_a3():
    """The base year of F1-F4 and the seven tests (freight_calibration_tests.csv, written by analysis_freight.py)."""
    t = pd.read_csv(os.path.join(OUTPUTS, 'freight_calibration_tests.csv'))
    rows = []
    for _, r in t.iterrows():
        scen = r.run.split('_')[0] + ('' if 'nofcet' in r.run else ' (with hydrogen trucks)')
        rows.append([TESTS.get(r.test, r.test), scen, num(r['Truck fuel 2020 (PJ)'], 0),
                     fine(r['BET share 2020 (%)']), fine(r['CO2 freight trucks 2020 (Mt)']),
                     fine(r['ZE share 2030 (%)']), fine(r['CO2 freight trucks 2030 (Mt)']),
                     DASH if r.test == 'base year' else signed(r['Total cost vs base run (%)'])])
    cols = ['Test', 'Scenario', 'Truck energy input 2020 (PJ)', 'BET share of freight 2020 (%)',
            'Truck CO2 2020 (Mt)', 'Zero-emission share 2030 (%)', 'Truck CO2 2030 (Mt)', 'Cost change (%)']
    return pd.DataFrame(rows, columns=cols), t


# --------------------------------------------------------------------------------------------------------------
# titles and notes (APA 7), and the output files
# --------------------------------------------------------------------------------------------------------------
def main():
    os.makedirs(OUT, exist_ok=True)
    t1a = table1_trucks()
    t1b, ze_max, h2_max = table1_settings()
    t2a, t2b = table2('core'), table2('real')
    ta2 = table_a2()
    ta3, tests = table_a3()
    c, c2 = CO2_PRICES, CO2_PRICES_ETS2
    co2_text = '; '.join(f"{k}: ETS1 {' / '.join(num(c[k][y]) for y in YEARS[1:])}, "
                         f"ETS2 {' / '.join(num(c2[k][y]) for y in YEARS[1:])}" for k in ('central', 'high'))
    lh_share = 1 - BET_TIERS[REAL['bet_tiers']]['BET - urban']['share'] - BET_TIERS[REAL['bet_tiers']]['BET']['share'] \
        - REAL['freight_heavy_share']
    obs = 5.1                                     # Mt CO2 of heavy trucks in 2014 (CE Delft, 2021)
    first = tests[tests.test == 'base year'].iloc[0]
    base_co2 = first['CO2 freight trucks 2020 (Mt)']
    summary = pd.read_csv(os.path.join(OUTPUTS, 'freight_summary.csv')).set_index(['run', 'period'])
    base_fuel = summary.loc[(first.run, 2020), 'Gasoline for trucks (TWh/yr)'] * 3.6     # TWh -> PJ
    tables = [
        ('table1_panelA_trucks', '**Table 1**', '*Scenario Settings and Parameter Values*',
         "*Panel A. The assignment's trucks (all periods)*", t1a, None),
        ('table1_panelB_settings', None, None, '*Panel B. Scenario axes, carbon price and the realistic layer*', t1b,
         "*Note.* Money in 2024 euros. CAPEX and FOM per kW of truck output, VOM per kWh of input (the database "
         "units), so the BET's charging penalty is 100 €/MWh of electricity. The core runs (`_nofcet`) carry only "
         "the carbon price; the extension adds fuel-cell (FCET) and hydrogen combustion (H2-ICE) trucks from 2030 "
         "(Table A2). The realistic layer keeps the X/Y matrix and the carbon price and adds the policies in force "
         f"or planned in October 2026 and the frictions they act on. Long-haul BETs take the rest of freight "
         f"({pct(lh_share)} after the heavy segment), and the trucks pay the diesel price instead of the gasoline price "
         "(cars keep the gasoline price). – = not applied. Toll, AanZET, SWiM and OWE are transfers, "
         "reported next to the system cost. Settings: `energy_model/freight_presets.py` and `run_freight.py`."),
        ('table2_panelA_core', '**Table 2**', '*Sensitivities: Zero-Emission Share, BET Capacity, System CO2 and '
         'Cost in 2030 and 2050*', "*Panel A. Core: the assignment's ICE trucks and BETs (`_nofcet` runs)*", t2a,
         None),
        ('table2_panelB_realistic', None, None, '*Panel B. Realistic layer: current policies (`_real` runs)*', t2b,
         f"*Note.* Cost change: total discounted system cost 2020–2059 against the same scenario with the moderate "
         f"carbon price and the base demand profile. BET capacity: output capacity of all BETs (GW of truck output). "
         f"System CO2 covers all sectors. Carbon prices in 2030 / 2040 / "
         f"2050 (€/t CO2): moderate (base) ETS1 {' / '.join(num(c[CO2][y]) for y in YEARS[1:])}, ETS2 "
         f"{' / '.join(num(c2[CO2][y]) for y in YEARS[1:])}; {co2_text}. Sunday ban: trucks on Sundays and holidays "
         "until 22:00 at 2% of the base profile; night ban: no trucks from 23:00 to 06:00. In the realistic layer "
         f"the market ramp-up holds the zero-emission share at {pct(ze_max[2030])} in the 2030s in every "
         "sensitivity. The hydrogen trucks and the policy and green-hydrogen tests are in Figure A17 "
         "(`freight_policy_levers.csv`). Data: `freight_summary.csv`, `freight_total_cost.csv`."),
        ('tableA2_truck_parameters', '**Table A2**', '*Truck Parameters by Period*', None, ta2,
         "*Note.* Values with a slash are 2020 / 2030 / 2040 / 2050; – = not available in that period. Money in "
         "2024 euros; CAPEX and FOM per kW of truck output, VOM per kWh of input. The ICE trucks emit 0.25 t "
         "CO2 per MWh of fuel. The 2020 stock has no investment cost, a 4-year life (2020 only) and replaces new "
         "trucks in the base year; BET – existing is fixed at 0.1 GW. The VOM of the hydrogen trucks is the "
         f"hydrogen delivery and station cost ({' / '.join(num(FCET_PARAMS['VOM'][y] * KWH_PER_KG, 1) for y in YEARS[1:])}"
         " €/kg in 2030 / 2040 / 2050; ×1.5 in the realistic layer), plus 0.01 €/kWh for the H2-ICE engine. The BET "
         "duty cycles scale the BET of the scenario (FOM scales with CAPEX). Sources and derivations: "
         "`energy_model/freight_presets.py`."),
        ('tableA3_calibration_tests', '**Table A3**', '*Calibration and Tests (Assignment Step 5)*', None, ta3,
         f"*Note.* Cost change: total discounted system cost 2020–2059 against the same scenario without the test "
         f"(the 6-hour run against F1 with hydrogen trucks). Truck energy input is fuel plus electricity. The 90 PJ of "
         f"the assignment is truck output: at 40% efficiency the ICE trucks burn {num(base_fuel)} PJ of fuel and emit "
         f"{num(base_co2, 1)} Mt CO2 in 2020, against an observed {obs} Mt for heavy trucks (2014; CE Delft, 2021); "
         "the fuel test reads the 90 PJ as fuel. The 2020 values are the same in all four scenarios. Without the "
         "stock the model builds new BETs in 2020; from 2030 on nothing changes. Runs: group `tests` in "
         "`run_freight.py`; data: `freight_calibration_tests.csv`."),
    ]
    md = ['# Paper tables', '',
          'Written by `paper_tables.py` from the model settings and the saved outputs. Bold first-column rows are '
          'block headers.', '']
    with pd.ExcelWriter(os.path.join(OUT, 'paper_tables.xlsx')) as xl:
        for key, number, title, panel, df, note in tables:
            df.to_csv(os.path.join(OUT, f'{key}.csv'), index=False)
            df.replace({r'\*\*': '', '`': ''}, regex=True).to_excel(xl, sheet_name=key[:31], index=False)
            if number:
                md += [f'{number} {title}', '']
            if panel:
                md += [panel, '']
            md += [md_table(df), '']
            if note:
                md += [note, '']
    open(os.path.join(OUT, 'paper_tables.md'), 'w', encoding='utf-8').write('\n'.join(md))
    print(f'{len(tables)} table panels written to {OUT}')
    return tables


if __name__ == '__main__':
    main()
