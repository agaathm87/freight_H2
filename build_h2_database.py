"""Build THE hydrogen database from the database of the FINAL course model (input_databases/default).

  input_databases/h2_nl  = default (final course model, its 2020 calibration unchanged)
                           + a hydrogen DEMAND and three hydrogen technologies (set-up agreed with Francesco, 14 Oct)
                           + Dutch hydrogen input data based on the group's documented assumptions (Oct 2026)

The set-up (meeting with Francesco, 14 October):
  * Hydrogen is a demand, not a secondary resource. demand.xlsx gets one new demand, 'industrial_h2' on the bus
    'Hydrogen': 1.3 Mt/yr (Elzenga et al., 2025), the same in every period and scenario (exponent 0), with a flat
    hourly profile (industrial demand is flat).
  * Three new technologies feed that demand directly, so they are END-USE technologies (like a heat pump feeding
    residential heat), all links:
        SMR            grey   bus0 Gas supply   bus1 Hydrogen   bus2 CO2 atmosphere
        SMR CCS        blue   bus0 Gas supply   bus1 Hydrogen   bus2 CO2 atmosphere (not captured)   bus3 CO2 storage
        Electrolyser   green  bus0 Electricity  bus1 Hydrogen
    plus 'SMR - existing', the reformers that exist in 2020 (the course's "- existing" convention: CAPEX 0,
    base year only), so the 2020 hydrogen is not built from scratch.
  * H2 storage (group, 15 October), retained as an optional model feature:
        H2 storage                 salt caverns, a Store on the hydrogen bus                (h2_storage)
    Dedicated renewable and nuclear routes are not included.
  * The green lever 'Electrolyser - seawater' (desalinated water, outside the water limit) is off
    unless a run switches it on (desal=True).
  * Not in the model: hydrogen as a secondary resource, the hydrogen furnace (option A) and hydrogen imports.
  * Water is not a resource in the model. The scenarios limit the electrolyser capacity instead (capacity
    constraints, set per scenario by energy_model/model.py).

Run:  python build_h2_database.py
Edit the numbers in the HYDROGEN EXTENSION and DUTCH DATA sections below and run again to regenerate the database.
The HYDROGEN EXTENSION gives the structure and first values; the DUTCH DATA replace them with the selected Dutch
input values. input_databases/default stays untouched (the course model itself).

Units follow the course database:
  CAPEX, FOM  in €/kW of OUTPUT (the model multiplies by the efficiency for links)
  VOM         in €/kWh of INPUT (preprocessing multiplies every '/kW...' unit by 1000)
  Emissions / Captured CO2 in tCO2 per MWh of input
  Efficiency  output / input (lower heating value for hydrogen)

Cost sources (converted to these units): PyPSA technology-data, outputs/costs_<year>.csv
(https://github.com/PyPSA/technology-data), which takes the electrolyser and SMR data from the
Danish Energy Agency technology catalogues and the IEA. Per kW of H2 output = per kW of input / efficiency.
"""

from pathlib import Path
import pandas as pd

from energy_model.h2_presets import STORAGE

HERE = Path(__file__).parent
SRC = HERE / 'input_databases' / 'default'      # final course model (calibrated)
DST_NL = HERE / 'input_databases' / 'h2_nl'
YEARS = [2020, 2030, 2040, 2050]

H2_DEMAND_MT = 1.3          # Mt H2 per year (Elzenga et al., 2025), fixed in all periods and scenarios
MWH_PER_T = 33.33           # lower heating value of hydrogen
H2_DEMAND_MWH = H2_DEMAND_MT * 1e6 * MWH_PER_T

# ============================================================
# HYDROGEN EXTENSION
# ============================================================

# Static parameters: (Technology, Parameter, Description, Efficiency_link, Value)
# Sector 'Industry': the three routes are end-use technologies that serve the industrial hydrogen demand.
STATIC = [
    # Electrolyser: Electricity -> Hydrogen demand (green)
    ('Electrolyser', 'Long name', None, None, 'Water electrolysis (green hydrogen)'),
    ('Electrolyser', 'Sector', None, None, 'Industry'),
    ('Electrolyser', 'Type', None, None, 'Link'),
    ('Electrolyser', 'bus0', 'main input', None, 'Electricity'),
    ('Electrolyser', 'bus1', 'main output', 'Efficiency', 'Hydrogen'),
    ('Electrolyser', 'Start year', None, None, 2030),
    # SMR: Gas -> Hydrogen demand + CO2 to the atmosphere (grey)
    ('SMR', 'Long name', None, None, 'Steam methane reforming (grey hydrogen)'),
    ('SMR', 'Sector', None, None, 'Industry'),
    ('SMR', 'Type', None, None, 'Link'),
    ('SMR', 'bus0', 'main input', None, 'Gas supply'),
    ('SMR', 'bus1', 'main output', 'Efficiency', 'Hydrogen'),
    ('SMR', 'bus2', 'secondary output', 'Emissions', 'CO2 atmosphere'),
    # SMR - existing: the 2020 stock of grey SMR (course convention: CAPEX 0, base year only)
    ('SMR - existing', 'Long name', None, None, 'Steam methane reforming, existing stock'),
    ('SMR - existing', 'Sector', None, None, 'Industry'),
    ('SMR - existing', 'Type', None, None, 'Link'),
    ('SMR - existing', 'bus0', 'main input', None, 'Gas supply'),
    ('SMR - existing', 'bus1', 'main output', 'Efficiency', 'Hydrogen'),
    ('SMR - existing', 'bus2', 'secondary output', 'Emissions', 'CO2 atmosphere'),
    # SMR CCS: Gas -> Hydrogen demand + CO2 atmosphere + CO2 storage (blue), 4-bus link like the course's CCS links
    ('SMR CCS', 'Long name', None, None, 'Steam methane reforming with CCS (blue hydrogen)'),
    ('SMR CCS', 'Sector', None, None, 'Industry'),
    ('SMR CCS', 'Type', None, None, 'Link'),
    ('SMR CCS', 'bus0', 'main input', None, 'Gas supply'),
    ('SMR CCS', 'bus1', 'main output', 'Efficiency', 'Hydrogen'),
    ('SMR CCS', 'bus2', 'secondary output', 'Emissions', 'CO2 atmosphere'),
    ('SMR CCS', 'bus3', 'tertiary output', 'Captured CO2', 'CO2 storage'),
    ('SMR CCS', 'Start year', None, None, 2030),
]

# Dynamic parameters: (Technology, Parameter, Unit, [2020, 2030, 2040, 2050])
# Electrolysis: technology-data 'electrolysis': 2515/1886/1509/1257 €/kW_e, efficiency 0.577/0.622/0.653/0.699,
#               FOM 4 %/yr, lifetime 25 -> divided by efficiency to get €/kW_H2 (replaced by the Dutch data below).
# SMR:          technology-data 'SMR': 659 €/kW_CH4, efficiency 0.76, FOM 5 %/yr, lifetime 30.
# SMR CCS:      technology-data 'SMR CC': 765 €/kW_CH4, efficiency 0.69, capture rate 0.9, FOM 5 %/yr, lifetime 30.
#               Gas emission factor 0.2 tCO2/MWh as in the course database -> 0.02 emitted, 0.18 captured
#               (90% capture; Francesco: 80-90%, may rise over time; the course's CCS links capture 85-95%).
ely_capex_e = [2514.67, 1886.00, 1508.80, 1257.33]
ely_eff = [0.577, 0.622, 0.653, 0.699]
ely_capex = [round(c / e, 1) for c, e in zip(ely_capex_e, ely_eff)]
smr_capex = round(659.18 / 0.76, 1)
ccs_capex = round(764.65 / 0.69, 1)

DYNAMIC = [
    ('Electrolyser', 'CAPEX', '€/kW', ely_capex),
    ('Electrolyser', 'FOM', '€/kW', [round(0.04 * c, 1) for c in ely_capex]),
    ('Electrolyser', 'VOM', '€/kWh', [0.0, 0.0, 0.0, 0.0]),
    ('Electrolyser', 'Efficiency', None, ely_eff),
    ('Electrolyser', 'Lifetime', 'years', [25, 25, 25, 25]),

    ('SMR', 'CAPEX', '€/kW', [smr_capex] * 4),
    ('SMR', 'FOM', '€/kW', [round(0.05 * smr_capex, 1)] * 4),
    ('SMR', 'VOM', '€/kWh', [0.0] * 4),
    ('SMR', 'Efficiency', None, [0.76] * 4),
    ('SMR', 'Lifetime', 'years', [30] * 4),
    ('SMR', 'Emissions', 'tCO2/MWh_th', [0.2] * 4),

    ('SMR - existing', 'CAPEX', '€/kW', [0.0] * 4),
    ('SMR - existing', 'FOM', '€/kW', [round(0.05 * smr_capex, 1)] * 4),
    ('SMR - existing', 'VOM', '€/kWh', [0.0] * 4),
    ('SMR - existing', 'Efficiency', None, [0.76] * 4),
    ('SMR - existing', 'Lifetime', 'years', [4] * 4),
    ('SMR - existing', 'Emissions', 'tCO2/MWh_th', [0.2] * 4),

    ('SMR CCS', 'CAPEX', '€/kW', [ccs_capex] * 4),
    ('SMR CCS', 'FOM', '€/kW', [round(0.05 * ccs_capex, 1)] * 4),
    ('SMR CCS', 'VOM', '€/kWh', [0.0] * 4),
    ('SMR CCS', 'Efficiency', None, [0.69] * 4),
    ('SMR CCS', 'Lifetime', 'years', [30] * 4),
    ('SMR CCS', 'Emissions', 'tCO2/MWh_th', [0.02] * 4),
    ('SMR CCS', 'Captured CO2', 'tCO2/MWh_th', [0.18] * 4),
]

# Capacity constraints (in MW of output, per vintage as in the course model):
# no NEW SMR in the base year, only the existing stock. The electrolyser rows that make the scenarios
# (Medium, Scarce) are written per scenario by energy_model/model.py (Medium depends on the Base run).
CAPACITY = [
    ('SMR', 'max', 'MW', None, [0, None, None, None]),
    ('SMR', 'min', 'MW', None, [0, None, None, None]),
]

# ============================================================
# Optional hydrogen storage
# ============================================================
# H2 storage in salt caverns: a Store on the hydrogen bus. CAPEX/FOM per kWh of storage capacity.
STATIC_OPTIONS = [
    ('H2 storage', 'Long name', None, None, 'Underground hydrogen storage (salt cavern), addition'),
    ('H2 storage', 'Sector', None, None, 'Industry'),
    ('H2 storage', 'Type', None, None, 'Store'),
    ('H2 storage', 'bus0', 'storage bus', None, 'Hydrogen'),
    ('H2 storage', 'Start year', None, None, 2030),
]
DYNAMIC_OPTIONS = [
    ('H2 storage', 'CAPEX', '€/kWh', [4.01, 2.67, 2.01, 1.60]),     # technology-data; replaced by the Dutch data
    ('H2 storage', 'FOM', '€/kWh', [0.0] * 4),
    ('H2 storage', 'VOM', '€/kWh', [0.0] * 4),
    ('H2 storage', 'Efficiency', None, [1.0] * 4),
    ('H2 storage', 'Lifetime', 'years', [100] * 4),
]
OPTION_RESOURCES = []

# Technologies and buses of the earlier set-ups that are removed from the database
REMOVED_TECHS = ['Industrial HTP - hydrogen']
REMOVED_RESOURCES = ['Hydrogen']


# ============================================================
# DUTCH DATA (input_databases/h2_nl) - selected central values, in 2024 euros
# Price bases converted with the Dutch HICP (Eurostat/CBS): nominal 2020 x 1.2325, €2025 / 1.030 (see model.py)
# ============================================================
E2020, E2025 = 1.028 * 1.116 * 1.041 * 1.032, 1 / 1.030   # -> €2024
NL_VOM_FACTOR = 0.01        # course VOMs are read as ct/kWh: CCGT 2 €/MWh, wind 1, PV 0.5 (PyPSA technology-data/DEA)
NL_GAS_PRICE = [round(9.7 * 1.11 * E2020, 1), 26.6, 28.9, 27.8]  # TTF €/MWh LHV (HHV x 1.11): ACER 2020 (9.7 HHV
                                                                 # nominal = 13.3 LHV €2024); KEV 2025; WLO 2025
NL_GAS_RESERVE = 1e12                       # MWh: gas is imported at the TTF price, no depleting stock
NL_CO2_PRICE = [round(24.61 * E2020, 1), 110, 180, 250]  # EU ETS €/t: Umweltbundesamt 2020 (24.61 nominal = 30.3
                                                         # €2024); KEV 2025; Enerdata/TYNDP
NL_CO2_TS_PRICE = [55, 55, 45, 40]          # CO2 transport + storage €/t: Porthos 47.10, Aramis 67-72
NL_ELY_CAPEX_E = [2200, 1650, 1250, 1000]   # electrolyser €/kW_e: IEA GHR 2025, EHO 2025, TNO 2024
NL_ELY_EFF = [0.60, 0.62, 0.65, 0.70]       # LHV: TNO 2024 (56 kWh/kg today), 48 kWh/kg KPI in 2050
NL_SMR_CCS_CAPEX = 1330.0                   # €/kW_H2, full capture: IEAGHG 2017, BEIS 2021
NL_SMR_EXISTING_LIFETIME = 15               # existing reformers run through the 2030 period
NL_H2_STORAGE = [0.9, 0.9, 0.85, 0.8]       # €/kWh salt cavern (option): Clean Hydrogen Partnership KPI; Talukdar 2023
NL_NUCLEAR_CAPEX = [6000] + [round(9000 * E2025)] * 3   # €/kW_e new build, €2025 -> €2024 (2020 = course, fixed)
NL_OFFSHORE_CAPEX = [round(c * E2025) for c in (2500, 2400, 2150, 2100)]  # €/kW excl. grid (€2025): PBL 2026, DEA
NL_OFFSHORE_FOM = [round(47 * E2025, 1)] * 4  # €/kW/yr: PBL 2026 (€2025)
NL_BATTERY_HOURS = 4
NL_BATTERY_CAPEX = [round(c * E2025) for c in (800, 600, 480, 360)]  # €/kW for 4 h (200/150/120/90 €2025/kWh): BNEF,
                                                                     # Ember, NREL 2025
NL_BATTERY_LIFETIME = 20                    # years: 15-20 for 4-h systems; course 25


def _dyn_set(d, tech, par, values, unit=None):
    row = (d.Technology == tech) & (d.Parameter == par)
    if row.any():
        d.loc[row, YEARS] = values
    else:
        d.loc[len(d)] = {'Technology': tech, 'Parameter': par, 'Unit': unit, **dict(zip(YEARS, values))}


def _copy_tech(s, d, src, dst, static_changes):
    """Copy a technology (static and dynamic parameters) under a new name, with some static parameters changed."""
    s_new = s[s.Technology == src].copy()
    s_new['Technology'] = dst
    for par, val in static_changes.items():
        if (s_new.Parameter == par).any():
            s_new.loc[s_new.Parameter == par, 'Value'] = val
        else:
            s_new.loc[len(s_new) + 10_000] = {'Technology': dst, 'Parameter': par, 'Value': val}
    d_new = d[d.Technology == src].copy()
    d_new['Technology'] = dst
    return pd.concat([s, s_new], ignore_index=True), pd.concat([d, d_new], ignore_index=True)


def nl_updates(s, d, c, res, par):
    """Apply the Dutch data and add the optional storage and green-lever routes."""
    d = d.copy()
    # VOM: read the course values as ct/kWh
    vom = d.Parameter == 'VOM'
    d.loc[vom, YEARS] = d.loc[vom, YEARS].astype(float) * NL_VOM_FACTOR
    # electrolyser: €/kW_e -> €/kW_H2 output
    ely = [round(c_ / e, 1) for c_, e in zip(NL_ELY_CAPEX_E, NL_ELY_EFF)]
    _dyn_set(d, 'Electrolyser', 'CAPEX', ely)
    _dyn_set(d, 'Electrolyser', 'FOM', [round(0.03 * x, 1) for x in ely])
    _dyn_set(d, 'Electrolyser', 'Efficiency', NL_ELY_EFF)
    _dyn_set(d, 'SMR CCS', 'CAPEX', [NL_SMR_CCS_CAPEX] * 4)
    _dyn_set(d, 'SMR CCS', 'FOM', [round(0.05 * NL_SMR_CCS_CAPEX, 1)] * 4)
    _dyn_set(d, 'SMR - existing', 'Lifetime', [NL_SMR_EXISTING_LIFETIME] * 4)
    if STORAGE:
        _dyn_set(d, 'H2 storage', 'CAPEX', NL_H2_STORAGE)
        _dyn_set(d, 'H2 storage', 'FOM', [round(0.02 * x, 4) for x in NL_H2_STORAGE])
        _dyn_set(d, 'H2 storage', 'Lifetime', [45] * 4)
    _dyn_set(d, 'Nuclear plant', 'CAPEX', NL_NUCLEAR_CAPEX)
    _dyn_set(d, 'Wind turbine - offshore', 'CAPEX', NL_OFFSHORE_CAPEX)
    _dyn_set(d, 'Wind turbine - offshore', 'FOM', NL_OFFSHORE_FOM)
    _dyn_set(d, 'Battery', 'CAPEX', NL_BATTERY_CAPEX)
    _dyn_set(d, 'Battery', 'Lifetime', [NL_BATTERY_LIFETIME] * 4)
    s = s.copy()
    if ((s.Technology == 'Battery') & (s.Parameter == 'Max hours')).any():
        s.loc[(s.Technology == 'Battery') & (s.Parameter == 'Max hours'), 'Value'] = NL_BATTERY_HOURS
    else:
        s.loc[len(s)] = {'Technology': 'Battery', 'Parameter': 'Max hours', 'Value': NL_BATTERY_HOURS}

    # LEVER alternative water: an electrolyser on desalinated seawater (grid electricity), outside the verdringingsreeks,
    # so the water scenario does not limit it; the cost of the water is added per scenario (desal_cost_eur_per_kg)
    s, d = _copy_tech(s, d, 'Electrolyser', 'Electrolyser - seawater',
                      {'Long name': 'Electrolyser on desalinated seawater (alternative water, outside the '
                                    'verdringingsreeks), lever'})
    res = res[~res.Resource.isin([r['Resource'] for r in OPTION_RESOURCES])]
    res = res.reset_index(drop=True)

    par = par.copy()
    yrs = [y for y in YEARS if y in par.columns]

    def setp(resource, parameter, values):
        row = (par.Resource == resource) & (par.Parameter == parameter)
        par.loc[row, [c for c in par.columns if str(c).isnumeric()]] = float('nan')
        par.loc[row, yrs] = values

    setp('Gas supply', 'Price', NL_GAS_PRICE)
    setp('Gas supply', 'Reserves', [NL_GAS_RESERVE] * 4)
    setp('CO2 atmosphere', 'Price', NL_CO2_PRICE)
    setp('CO2 storage', 'Price', NL_CO2_TS_PRICE)
    return s, d, c, res, par


def write_database(dst, s, d, c, dem, drv, prof, res, par, ren):
    dst.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(dst / 'technologies.xlsx') as w:
        s.to_excel(w, sheet_name='static_parameters', index=False)
        d.to_excel(w, sheet_name='dynamic_parameters', index=False)
        c.to_excel(w, sheet_name='capacity_constraints', index=False)
    with pd.ExcelWriter(dst / 'demand.xlsx') as w:
        prof.to_excel(w, sheet_name='normalized_profiles', index=False)
        dem.to_excel(w, sheet_name='demands', index=False)
        drv.to_excel(w, sheet_name='drivers', index=False)
    with pd.ExcelWriter(dst / 'supply.xlsx') as w:
        res.to_excel(w, sheet_name='resources', index=False)
        par.to_excel(w, sheet_name='resources_parameters', index=False)
        ren.to_excel(w, sheet_name='ren_profiles', index=False)
    print(f'Written {dst.relative_to(HERE)}')


def main():
    # ---- technologies.xlsx: three hydrogen routes (+ the existing SMR stock) ----
    s = pd.read_excel(SRC / 'technologies.xlsx', sheet_name='static_parameters')
    d = pd.read_excel(SRC / 'technologies.xlsx', sheet_name='dynamic_parameters')
    c = pd.read_excel(SRC / 'technologies.xlsx', sheet_name='capacity_constraints')
    for df in (s, d, c):     # the final database uses merged cells: fill the technology name down
        df['Technology'] = df['Technology'].ffill()
    s_new = pd.DataFrame(STATIC + (STATIC_OPTIONS if STORAGE else []),
                         columns=['Technology', 'Parameter', 'Description', 'Efficiency_link', 'Value'])
    s_new['Unit'] = None
    d_new = pd.DataFrame([(t, p, u, *v) for t, p, u, v in DYNAMIC + (DYNAMIC_OPTIONS if STORAGE else [])],
                         columns=['Technology', 'Parameter', 'Unit'] + YEARS)
    c_new = pd.DataFrame([(t, ty, u, f, *v) for t, ty, u, f, v in CAPACITY],
                         columns=['Technology', 'Type', 'Unit', 'adjustment factor'] + YEARS)
    drop = set(s_new.Technology) | set(REMOVED_TECHS) | {'Solar PV - dedicated', 'Wind turbine - offshore - dedicated',
                                                          'Electrolyser - dedicated', 'Nuclear plant - dedicated',
                                                          'Electrolyser - nuclear', 'Electrolyser - seawater',
                                                          'H2 storage'}
    s = pd.concat([s[~s.Technology.isin(drop)], s_new], ignore_index=True)
    d = pd.concat([d[~d.Technology.isin(drop)], d_new], ignore_index=True)
    c = pd.concat([c[~c.Technology.isin(drop)], c_new], ignore_index=True)

    # ---- demand.xlsx: the hydrogen demand (bus 'Hydrogen'), constant over time, flat profile ----
    dem = pd.read_excel(SRC / 'demand.xlsx', sheet_name='demands')
    drv = pd.read_excel(SRC / 'demand.xlsx', sheet_name='drivers')
    prof = pd.read_excel(SRC / 'demand.xlsx', sheet_name='normalized_profiles')
    dem = dem[dem.Demand != 'industrial_h2']
    dem = pd.concat([dem, pd.DataFrame([{
        'Demand': 'industrial_h2',
        'Desrciption': f'Industrial hydrogen demand: feedstock for refineries and ammonia, {H2_DEMAND_MT} Mt/yr '
                       f'(Elzenga et al., 2025), LHV {MWH_PER_T} MWh/t; exponent 0 = constant over time. '
                       f'Served directly by the end-use technologies SMR, SMR CCS and Electrolyser.',
        'Bus': 'Hydrogen', 'Carrier': 'Hydrogen', 'Unit': 'MWh', 'Driver': 'gdp',
        'Start_value': H2_DEMAND_MWH, 'Exponent': 0.0}])], ignore_index=True)
    prof['industrial_h2'] = 1.0 / len(prof)          # flat: the same demand in every hour

    # ---- supply.xlsx: no hydrogen resource (hydrogen is a demand); the option buses are added in nl_updates ----
    res = pd.read_excel(SRC / 'supply.xlsx', sheet_name='resources')
    par = pd.read_excel(SRC / 'supply.xlsx', sheet_name='resources_parameters')
    ren = pd.read_excel(SRC / 'supply.xlsx', sheet_name='ren_profiles')
    res = res[~res.Resource.isin(REMOVED_RESOURCES)].reset_index(drop=True)
    # the CO2 price is used per tonne (tCO2/MWh x price), so the unit label is corrected here
    par.loc[(par.Resource.isin(['CO2 atmosphere', 'CO2 storage'])) & (par.Parameter == 'Price'), 'Unit'] = '€/tCO2'

    s_nl, d_nl, c_nl, res_nl, par_nl = nl_updates(s, d, c, res, par)      # the real (Dutch) numbers
    write_database(DST_NL, s_nl, d_nl, c_nl, dem, drv, prof, res_nl, par_nl, ren)
    print(f'Model rebuilt. Hydrogen demand: {H2_DEMAND_MWH:,.0f} MWh/yr = {H2_DEMAND_MWH / 8760:,.0f} MW flat')


if __name__ == '__main__':
    main()
