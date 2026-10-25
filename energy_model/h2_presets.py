# h2_presets.py      
#    ← all constants: 
# CO2_PRICES, GAS_PRICES, SCENARIOS, DEFAULTS, etc.


import numpy as np
import pandas as pd

__all__ = [
    'SCENARIOS', 'SHORT_NAMES', 'REFERENCE_SCENARIO', 'DEFAULTS', 'PRESETS',
    'CO2_PRICES', 'CO2_PRICES_ETS2', 'GAS_PRICES', 'ELY_CAPEX',
    'CO2_TS_PRICES', 'CO2_STORAGE_CAPS', 'H2_STORAGE_CAPS',
    'CAPACITY_CAPS', 'H2_DEMAND', 'WATER_L_PER_KG',
    'ELECTROLYSIS', 'ELECTROLYSIS_GRID', 'ELECTROLYSIS_SEAWATER', 'ELECTROLYSIS_GREEN', 'ELECTROLYSIS_PINK',
    'DEDICATED_RES', 'DEDICATED_RES_CARRIERS', 'DEDICATED_NUCLEAR',
    'GREY', 'BLUE', 'H2_PRODUCTION', 'H2_STORAGE', 'BATTERY',
    'H2_BUS', 'H2_LOAD', 'KG_PER_MWH_H2', 'MWH_PER_T_H2',
    'ETS2_TECHS', 'OPTION_TECHS', 'STORAGE',
]


# Set this switch to False to exclude hydrogen storage from rebuilt databases and
# from the default scenario settings. Individual runs can still override it with
# h2_storage=True or h2_storage=False.
STORAGE = True

# Names of the hydrogen technologies in the database (technologies.xlsx)
ELECTROLYSIS_GRID = ['Electrolyser']                   # green: grid electricity
ELECTROLYSIS_SEAWATER = ['Electrolyser - seawater']    # green on desalinated seawater: OUTSIDE the water limit (lever)
ELECTROLYSIS_GREEN = ['Electrolyser - pure green']    # [Freight] addition: own wind + solar, no grid connection
ELECTROLYSIS_PINK = ['Electrolyser - pink']            # [Freight] addition: own nuclear plant
DEDICATED_RES = ['Wind turbine - offshore - dedicated', 'Wind turbine - onshore - dedicated', 'Solar PV - dedicated']
DEDICATED_RES_CARRIERS = ['Wind offshore - dedicated', 'Wind onshore - dedicated', 'Solar - dedicated']
DEDICATED_NUCLEAR = ['Nuclear plant - dedicated']
ELECTROLYSIS = ELECTROLYSIS_GRID + ELECTROLYSIS_SEAWATER + ELECTROLYSIS_GREEN + ELECTROLYSIS_PINK
GREY = ['SMR', 'SMR - existing']                       # grey (new and the 2020 stock)
BLUE = ['SMR CCS']                                     # blue
H2_PRODUCTION = ELECTROLYSIS + GREY + BLUE
H2_STORAGE = ['H2 storage']                            # salt caverns (option)
OPTION_TECHS = {'h2_storage': H2_STORAGE, 'desal': ELECTROLYSIS_SEAWATER,
                'pure_green': ELECTROLYSIS_GREEN + DEDICATED_RES, 'pink': ELECTROLYSIS_PINK + DEDICATED_NUCLEAR}
KG_PER_MWH_H2 = 1000 / 33.33                           # kg of hydrogen per MWh (LHV)
BATTERY = ['Battery']
H2_BUS = 'Hydrogen'                                    # the demand bus of 'industrial_h2'
H2_LOAD = 'industrial_h2'
MWH_PER_T_H2 = 33.33                                   # lower heating value
MWH_PER_KG = MWH_PER_T_H2 / 1000

# --------------------------------------------------------------------------
# Scenario parameter (1): water availability for electrolysis
#   electrolyser_cap_share = largest electrolyser capacity, as a share of what the cost-optimal run (S1) builds.
#   None = no limit. 0 = no electrolysers. The base is the scenario without water scarcity (group, 15 Oct).
# --------------------------------------------------------------------------
SCENARIOS = {
    'S1': dict(label='S1 Base (no water scarcity)', electrolyser_cap_share=None),
    'S2': dict(label='S2 Medium (medium water scarcity)', electrolyser_cap_share=0.5),
    'S3': dict(label='S3 Scarce (high water scarcity)', electrolyser_cap_share=0.0),
}
SHORT_NAMES = {'S1': 'Base', 'S2': 'Medium', 'S3': 'Scarce'}     # short names for plots and tables (feedback)
REFERENCE_SCENARIO = 'S1'                                         # the cost-optimal run the caps refer to

# --------------------------------------------------------------------------
# Presets based on Dutch input data and cited sources (October 2026).
# All money values in 2024 euros (the report's convention). Price bases are converted with the Dutch HICP
# (Eurostat HICP, annual averages as published by CBS): 2021 +2.8%, 2022 +11.6%, 2023 +4.1%, 2024 +3.2%, 2025 +3.0%.
#   nominal 2020 -> €2024: x 1.2325          €2025 -> €2024: / 1.030
# 2020 = the observed value of 2020, expressed in 2024 euros.
# --------------------------------------------------------------------------
EUR2024_PER_EUR2020 = 1.028 * 1.116 * 1.041 * 1.032      # = 1.2325
EUR2024_PER_EUR2025 = 1 / 1.030
# EU ETS1 CO2 price (€/tCO2). 2020: auction average 24.61 nominal (Umweltbundesamt) = 30.3 €2024.
# 2030 band = PBL KEV 2025 (75-138, central 111, €2024); 2040-2050 = synthesis of Enerdata (2025, 2026),
# TYNDP 2024 and WLO 2025 (see report).
CO2_PRICES = {
    'zero':    {2020: 0,    2030: 0,   2040: 0,   2050: 0},
    'low':     {2020: 30.3, 2030: 75,  2040: 130, 2050: 170},
    'central': {2020: 30.3, 2030: 110, 2040: 180, 2050: 250},
    'high':    {2020: 30.3, 2030: 140, 2040: 270, 2050: 500},
    'stress':  {2020: 30.3, 2030: 140, 2040: 450, 2050: 630},
}
# EU ETS2 CO2 price (€/tCO2) for fuel burnt in buildings and road transport: here the household gas boilers and
# the petrol cars (ETS2_TECHS). ETS2 starts with the emissions of 2028, so 2020 = 0 (no EU carbon price on household
# gas and petrol). PBL (2026c, p. 17; 2025 prices): low 57 €/t = the price-stability trigger, kept flat ("loopt niet
# op in de tijd"); middle 86 in 2030 (futures price Dec-2028 of 71, +10%/yr); high 135 in 2030, +10%/yr.
# 2040 = 2030 x 1.1^10 for middle and high (223, 350). 2050: converges with ETS1.
# Stress = the ETS1 stress values from 2040. Converted to €2024 (/1.030). Industry, power and hydrogen stay in ETS1.
CO2_PRICES_ETS2 = {
    'zero':    {2020: 0, 2030: 0,   2040: 0,   2050: 0},
    'low':     {2020: 0, 2030: 55,  2040: 55,  2050: 170},
    'central': {2020: 0, 2030: 83,  2040: 217, 2050: 250},
    'high':    {2020: 0, 2030: 131, 2040: 340, 2050: 500},
    'stress':  {2020: 0, 2030: 131, 2040: 450, 2050: 630},
}
ETS2_TECHS = ['Residential gas boiler', 'Residential gas boiler - existing', 'ICE car', 'ICE car - existing',
              'ICE truck', 'ICE truck - existing']          # [Freight] trucks are road transport: ETS2
# Natural gas (TTF) in €/MWh LHV (= €/MWh HHV x 1.11). 2020: ACER annual average 9.7 HHV nominal = 13.3 LHV €2024.
# 2030 band = PBL KEV 2025 (15-47 HHV, central 24, €2024); 2040-2050 from WLO 2025, REF2020, IEA (see report).
GAS_PRICES = {
    'low':       {2020: 13.3, 2030: 16.7, 2040: 15.5, 2050: 14.4},
    'central':   {2020: 13.3, 2030: 26.6, 2040: 28.9, 2050: 27.8},
    'high':      {2020: 13.3, 2030: 52.2, 2040: 44.4, 2050: 42.2},
    'shock2030': {2020: 13.3, 2030: 80.0, 2040: 44.4, 2050: 42.2},   # Sept-Oct 2026 level (~72 HHV)
}
# Electrolyser system CAPEX (€/kW_e, installed, excluding grid). IEA GHR 2025, EHO 2025, TNO 2024.
ELY_CAPEX = {
    'low':     {2020: 1800, 2030: 1250, 2040: 800,  2050: 500},
    'central': {2020: 2200, 2030: 1650, 2040: 1250, 2050: 1000},
    'high':    {2020: 3100, 2030: 2500, 2040: 1800, 2050: 1400},
}
# CO2 transport and storage tariff (€/tCO2). Porthos max 47.10; Aramis 67-72 (Algemene Rekenkamer 2024).
CO2_TS_PRICES = {
    'zero':    {2020: 0,  2030: 0,  2040: 0,  2050: 0},
    'low':     {2020: 45, 2030: 45, 2040: 30, 2050: 25},
    'central': {2020: 55, 2030: 55, 2040: 45, 2050: 40},
    'high':    {2020: 75, 2030: 75, 2040: 70, 2050: 65},
}
# CO2 storage capacity (MtCO2/yr): Porthos 2.5 from 2027, Aramis 5-7.5 at launch, up to 22.
CO2_STORAGE_CAPS = {
    'low':     {2030: 2.5,  2040: 10, 2050: 10},
    'central': {2030: 10,   2040: 22, 2050: 25},
    'high':    {2030: 10,   2040: 25, 2050: 25},
}
# H2 storage option: salt-cavern storage that can exist (MWh): first HyStock cavern ~2031 (0.22 TWh),
# 4 caverns 0.67-0.9 TWh mid-2030s, 1.5-10 TWh in 2050 (Gasunie; KGG 2025; TNO 2020).
H2_STORAGE_CAPS = {
    'low':     {2030: 0.0,    2040: 0.67e6, 2050: 1.5e6},
    'central': {2030: 0.22e6, 2040: 0.9e6,  2050: 5e6},
    'high':    {2030: 0.9e6,  2040: 3e6,    2050: 10e6},
}
# Build limits per period (MW of p_nom: input power for links, output for generators), summed over all active vintages.
# Each period stands for 10 years (2030 = 2030-2039). These are limits on how fast things can be built in the
# Netherlands; they are not the water limit of the scenarios.
#   Electrolysers: 1.2 GW funded for 2030, 3-4 GW by 2035, NPE 15-20 GW in 2040, up to 40 GW 2050.
#   Offshore wind: 21 GW roadmap (~2032), 30-40 GW in 2040, up to 70 GW in 2050.
#   Nuclear: Borssele (512 MW_e) only until the late 2030s; up to 7 GW_e by 2050 (input = output / 0.4).
CAPACITY_CAPS = {
    'central': [
        dict(name='Electrolysers', component='Link', carriers=ELECTROLYSIS,
             cap={2030: 3000, 2040: 20000, 2050: 40000}),
        dict(name='Offshore wind', component='Generator', carriers=['Wind offshore', 'Wind offshore - dedicated'],
             cap={2030: 21000, 2040: 40000, 2050: 70000}),
        dict(name='Nuclear', component='Link', carriers=['Nuclear plant', 'Nuclear plant - dedicated'],
             cap={2030: 512 / 0.4, 2040: 2712 / 0.4, 2050: 7000 / 0.4}),
    ],
}
CAPACITY_CAPS['low'] = [
    {**CAPACITY_CAPS['central'][0], 'cap': {2030: 1200, 2040: 15000, 2050: 14000}},
    {**CAPACITY_CAPS['central'][1], 'cap': {2030: 10200, 2040: 21000, 2050: 40000}},
    {**CAPACITY_CAPS['central'][2], 'cap': {2030: 512 / 0.4, 2040: 512 / 0.4, 2050: 512 / 0.4}},
]
# Hydrogen demand (Mt/yr). Fixed 1.3 Mt in the scenarios (Elzenga et al., 2025); 'high' is a variation
# (Francesco: "of course you can do a variation where the demand is different", after the three scenarios run).
H2_DEMAND = {
    'fixed':  {2020: 1.3, 2030: 1.3, 2040: 1.3, 2050: 1.3},
    'low':    {2020: 1.3, 2030: 0.8, 2040: 1.3, 2050: 1.3},
    'high':   {2020: 1.3, 2030: 1.3, 2040: 2.5, 2050: 3.3},
}
# Water use by route, litres per kg H2 (consumption incl. treatment and cooling; report Table "water"):
# electrolysis 17.5-22.3 (IRENA 2023), SMR 8-12.5, SMR + CCS 24-32. Output only.
WATER_L_PER_KG = {'electrolysis': 22.0, 'SMR': 10.0, 'SMR CCS': 28.0}

PRESETS = {
    'co2_price': CO2_PRICES, 'co2_price_ets2': CO2_PRICES_ETS2, 'gas_price': GAS_PRICES, 'electrolyser_capex': ELY_CAPEX,
    'co2_storage_price': CO2_TS_PRICES, 'co2_storage_cap': CO2_STORAGE_CAPS, 'h2_storage_cap': H2_STORAGE_CAPS,
    'capacity_caps': CAPACITY_CAPS, 'h2_demand_mt': H2_DEMAND,
}

DEFAULTS = dict(
    label=None,
    # --- scenario parameter (1): water availability -> electrolyser capacity ---
    electrolyser_cap_share=None,   # None = no limit (cost-optimal, S1); 0.5 = half of the reference capacity; 0 = none
    electrolyser_reference=None,   # {technology: {year: MW of H2 output}} built per vintage in the reference run (the
                                   #   central S1), from electrolyser_reference(n_S1); needed when 0 < electrolyser_cap_share
    cap_from=2030,                 # first vintage that the scenario limits (electrolysers start in 2030)
    electrolyser_limit_scope='total',  # 'total': the limit is on all electrolysers together (MW of hydrogen output per
                                   #   vintage), share x the total of the reference run: the same water whatever the
                                   #   power source; 'per_technology': each electrolyser <= share x its own reference
    electrolyser_limit_on='capacity',  # 'capacity': water limits how big the electrolyser can be (the scenarios);
                                   # 'output': the plant is built as big as in the reference run (S1), but water lets
                                   #   it run at no more than electrolyser_cap_share of its capacity in any hour (the
                                   #   "over-dimensioned plant" story of Francesco: build for abundant water, then a drought)
    electrolyser_plant_reference=None,  # with 'output': the plant to build ({technology: {year: MW of H2}}, e.g. of
                                   #   the Base run); the water then caps the hourly output of all
                                   #   electrolysers together at share x electrolyser_reference (the same water in MW)
    # --- optional hydrogen storage ---
    h2_storage=STORAGE,            # H2 storage in salt caverns (a Store on the hydrogen bus)
    pure_green=True,               # [Freight] pure green route: electrolyser on its own wind + solar, no grid
    pink=True,                     # [Freight] pink route: electrolyser on its own nuclear plant
    h2_storage_cap='central',      # MWh of H2 storage that can exist (key of H2_STORAGE_CAPS or {year: MWh}); None = no cap
    h2_storage_cost_factor=1.0,    # (2c) multiplier on H2 storage CAPEX and FOM
    grid_electrolysis=True,        # False = no grid electrolyser: green hydrogen only from the pure green route
                                   #   (a strict reading of the EU rules for renewable hydrogen, RFNBO)
    # --- green levers within the water scenarios (16 Oct) ---
    desal=False,                   # alternative water: an electrolyser on desalinated seawater (or treated waste
                                   #   water), outside the verdringingsreeks, so NOT limited by the water scenario
    desal_cost_eur_per_kg=0.03,    # levelised cost of alternative water per kg H2
    h2_production_subsidy=0.0,     # €/kg of hydrogen from electrolysis (all electrolysers): an operating subsidy,
                                   #   CfD / H2Global / SDE++-type; a transfer, added back in the economic cost
    green_mandate=None,            # {year: minimum share of the hydrogen made by electrolysis}, e.g. {2040: 0.6,
                                   #   2050: 0.6} (RED III: 42% RFNBO in industry by 2030, 60% by 2035)
    # --- the hydrogen demand (Francesco: decide what this hydrogen is used for) ---
    h2_demand_use='feedstock',     # 'feedstock': refineries and ammonia, a separate demand ON TOP of the course demands
                                   # 'htp_fuel':  hydrogen burnt for high-temperature heat; the industrial HTP demand is
                                   #              reduced by the heat this hydrogen delivers (H2 x furnace efficiency)
    h2_demand_mt=None,             # key of H2_DEMAND or {year: Mt}; None = database (1.3 Mt every period)
    # --- sensitivities: cost variations within the scenarios ---
    electrolyser_subsidy=0.0,      # (2a) share of electrolyser CAPEX paid by subsidy, 0-0.8 (OWE)
    infrastructure_subsidy=0.0,    # share of electrolyser infrastructure CAPEX paid by subsidy, 0-0.8
    electrolyser_capex=None,       # (2a) 'low'/'central'/'high' or {year: €/kW_e}; None = database
    co2_price='central',           # (2b) key of CO2_PRICES, number, {year: price}, or None (= database)
    co2_price_scope='all',         # 'all': every emission pays (ETS-like); 'h2': only the SMR routes pay
    co2_price_ets2='auto',         # price for household gas boilers and petrol cars (ETS2_TECHS): key of
                                   #   CO2_PRICES_ETS2, number or {year: price}; 'auto' = the ETS2 path with the same
                                   #   name as co2_price (or the ETS1 price if co2_price is not a preset name);
                                   #   None = they pay ETS1
    capex_factors=None,            # {technology: multiplier on CAPEX}, e.g. {'SMR CCS': 1.2}
    battery=True,                  # (3) include batteries at all (course model; not used for hydrogen)
    battery_cost_factor=1.0,       # (3a) multiplier on battery CAPEX
    battery_max_mw=None,           # (3b) maximum total battery power in any period (MW)
    battery_max_hours=None,        # (3c) hours of storage per MW (None = database: 4 h in h2_nl)
    # --- data and model settings ---
    gas_price='central',           # key of GAS_PRICES or {year: €/MWh}; None = database
    gas_reserve=None,              # MWh of gas for ALL periods together; None = database
    co2_storage_price='central',   # €/tCO2 transport + storage (key, number or dict); None = database
    co2_storage_cap='central',     # MtCO2/yr captured (key or {year: Mt}); None = no cap
    capacity_caps='central',       # build limits: key of CAPACITY_CAPS or a list of dicts; None = no caps
    period_prices=True,            # True: fuel and CO2 prices of each PERIOD (not of the build year)
    storage_cyclic_per_period=True,  # batteries return to their start level within EACH period
    skip_early_vintages=True,      # do not add copies of a technology before its start year (see model.py)
    vom_scale=1.0,                 # multiplier on ALL variable O&M costs (1 = database as is)
)

# [Freight] settings of the freight extension and the water module (energy_model/freight_presets.py)
from .freight_presets import FREIGHT_DEFAULTS  # noqa: E402
DEFAULTS.update(FREIGHT_DEFAULTS)
