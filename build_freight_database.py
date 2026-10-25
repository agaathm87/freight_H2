"""Build input_databases/freight_nl = input_databases/h2_nl + heavy-duty road freight (individual assignment).

Additions
  demand.xlsx      'freight_road' on the bus 'Freight transport': 90 PJ in 2020 in energy terms (the output of the truck
                   links), projected with GDP (exponent FREIGHT_GDP_EXPONENT); an hourly profile with weekday delivery
                   peaks, low weekends and seasonal dips (sheet normalized_profiles), and two alternative profiles for
                   time restrictions (sheet freight_profiles: a Sunday/holiday ban and a night ban).
  technologies     ICE truck (gasoline), BET (electricity), FCET and H2-ICE truck (hydrogen, from 2030), the realistic
                   layer's BETs by duty cycle ('BET - urban', 'BET - long haul', from 2030) and the 2020 stock as
                   'ICE truck - existing' (endogenous size, CAPEX 0) and 'BET - existing' (0.1 GW). New ICE trucks and
                   BETs cannot be built in the base year, so 2020 is calibrated on the existing stock only.
  supply.xlsx      gasoline is imported at its price (reserves 1e12 MWh, like gas), so the reserve never binds.
  hydrogen routes  the group's additions: pure green (an electrolyser on its own offshore wind, onshore wind and solar,
                   on the bus 'Electricity - pure green', no grid connection) and pink (an electrolyser on its own
                   nuclear plant, bus 'Electricity - pink'), both from 2030, with the costs of their grid counterparts.
                   Switch them off per run with pure_green=False / pink=False.
Run:  python build_freight_database.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

from build_h2_database import _copy_tech
from energy_model.freight_presets import (FREIGHT_PJ_2020, FREIGHT_GDP_EXPONENT, FCET_PARAMS, H2ICE_PARAMS, FREIGHT_BUS,
                                          FREIGHT_LOAD)

HERE = Path(__file__).parent
SRC, DST = HERE / 'input_databases' / 'h2_nl', HERE / 'input_databases' / 'freight_nl'
YEARS = [2020, 2030, 2040, 2050]
MWH_PER_PJ = 277777.78                     # 1 PJ = 277,777.8 MWh

# ---- temporal profile (stylised from Dutch traffic data; see report) ----------------------------------------------
# Weekday hour shape of truck traffic: low at night (long-haul keeps running), delivery peak 07-15 h.
WEEKDAY_HOURS = [0.30, 0.27, 0.27, 0.30, 0.45, 0.75, 0.95, 1.00, 1.00, 1.00, 1.00, 0.98,
                 0.97, 0.97, 0.95, 0.90, 0.82, 0.70, 0.58, 0.48, 0.42, 0.38, 0.35, 0.32]
# Sunday: little traffic until the evening, when trucks position for Monday (and the German ban ends at 22 h).
SUNDAY_HOURS = [0.15, 0.12, 0.10, 0.10, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.32, 0.33,
                0.33, 0.33, 0.35, 0.40, 0.50, 0.65, 0.80, 0.95, 1.00, 1.00, 0.95, 0.70]
# Day factors (Mon..Sun): workday-to-week-average ratio of truck traffic ~0.80 in the Netherlands (IPLO, 2021).
DAY_FACTOR = [0.97, 1.00, 1.00, 1.00, 0.95, 0.40, 0.20]
# Month factors: dips in the summer holidays (bouwvak) and around Christmas, peak in autumn (CBS road freight).
MONTH_FACTOR = [0.95, 0.98, 1.03, 1.00, 1.02, 1.03, 0.97, 0.92, 1.03, 1.05, 1.04, 0.95]
HOLIDAYS_2019 = ['2019-01-01', '2019-04-22', '2019-04-27', '2019-05-30', '2019-06-10', '2019-12-25', '2019-12-26']


def freight_profiles(index):
    """Hourly freight profiles over the course's year, each normalised to a sum of 1: 'base' (weekday peak
    07:00-15:00, night at 30% of the peak, Saturday 40% and Sunday 20% of a weekday, monthly factors),
    'sunday_ban' (Sundays and holidays 0-22 h at 2% of base) and 'night_ban' (no trucks 23-06 h)."""
    t = pd.DatetimeIndex(index)
    sunday = (t.dayofweek == 6) | t.normalize().isin(pd.to_datetime(HOLIDAYS_2019))
    hour_w = np.array(WEEKDAY_HOURS)[t.hour]
    hour_s = np.array(SUNDAY_HOURS)[t.hour] * np.mean(WEEKDAY_HOURS) / np.mean(SUNDAY_HOURS)   # same daily mean
    day = np.where(sunday, DAY_FACTOR[6], np.array(DAY_FACTOR)[t.dayofweek])
    base = np.where(sunday, hour_s, hour_w) * day * np.array(MONTH_FACTOR)[t.month - 1]
    sunday_ban = np.where(sunday & (t.hour < 22), 0.02 * base, base)          # Sunday/holiday ban 0-22 h (DE-style)
    night_ban = np.where((t.hour >= 23) | (t.hour < 6), 0.0, base)            # no trucks 23-06 h
    out = pd.DataFrame({'base': base, 'sunday_ban': sunday_ban, 'night_ban': night_ban}, index=index)
    return out / out.sum()


def main():
    """Write input_databases/freight_nl: h2_nl plus the freight demand and profiles and the truck technologies."""
    x = {f: pd.ExcelFile(SRC / f'{f}.xlsx') for f in ('technologies', 'demand', 'supply')}
    s = pd.read_excel(x['technologies'], 'static_parameters')
    d = pd.read_excel(x['technologies'], 'dynamic_parameters')
    c = pd.read_excel(x['technologies'], 'capacity_constraints')
    prof = pd.read_excel(x['demand'], 'normalized_profiles')
    dem = pd.read_excel(x['demand'], 'demands')
    drv = pd.read_excel(x['demand'], 'drivers')
    res = pd.read_excel(x['supply'], 'resources')
    par = pd.read_excel(x['supply'], 'resources_parameters')
    ren = pd.read_excel(x['supply'], 'ren_profiles')
    for df in (s, d):
        df['Technology'] = df['Technology'].ffill()
    trucks = ['ICE truck', 'ICE truck - existing', 'BET', 'BET - existing', 'FCET', 'H2-ICE truck', 'BET - urban',
              'BET - long haul']
    s, d = s[~s.Technology.isin(trucks)], d[~d.Technology.isin(trucks)]

    # demand: 90 PJ of useful freight transport energy in 2020, driver GDP
    dem = dem[dem.Demand != FREIGHT_LOAD]
    dem.loc[len(dem)] = {'Demand': FREIGHT_LOAD, 'Desrciption': 'Heavy-duty road freight transport (energy terms)',
                         'Bus': FREIGHT_BUS, 'Carrier': FREIGHT_BUS, 'Unit': 'MWh', 'Driver': 'gdp',
                         'Start_value': FREIGHT_PJ_2020 * MWH_PER_PJ, 'Exponent': FREIGHT_GDP_EXPONENT}
    p = freight_profiles(prof['time'])
    prof[FREIGHT_LOAD] = p['base'].values
    fp = pd.DataFrame({'time': prof['time'], 'freight_road': p['base'].values,
                       'freight_sunday_ban': p['sunday_ban'].values, 'freight_night_ban': p['night_ban'].values})

    # technologies: static topology
    def static(t, long, bus0, start=None, co2=True):
        """Static rows of a truck technology: a link from bus0 to the freight bus (and CO2 to the atmosphere)."""
        rows = [(t, 'Long name', None, None, long), (t, 'Sector', None, None, 'Transport'),
                (t, 'Type', None, None, 'Link'), (t, 'bus0', 'main input', None, bus0),
                (t, 'bus1', 'main output', 'Efficiency', FREIGHT_BUS)]
        if co2:
            rows.append((t, 'bus2', 'secondary output', 'Emissions', 'CO2 atmosphere'))
        if start:
            rows.append((t, 'Start year', None, None, start))
        return rows
    rows = (static('ICE truck', 'Internal combustion engine truck (gasoline)', 'Gasoline supply')
            + static('ICE truck - existing', 'ICE truck, 2020 stock', 'Gasoline supply')
            + static('BET', 'Battery electric truck', 'Electricity', co2=False)
            + static('BET - existing', 'Battery electric truck, 2020 stock', 'Electricity', co2=False)
            + static('FCET', 'Fuel cell electric truck (hydrogen)', 'Hydrogen', start=2030, co2=False)
            + static('H2-ICE truck', 'Hydrogen combustion engine truck', 'Hydrogen', start=2030, co2=False)
            # realistic layer: BETs by duty cycle (costs set per run from the BET's with factors; off unless bet_tiers)
            + static('BET - urban', 'Battery electric truck, urban and construction (depot charging)', 'Electricity',
                     start=2030, co2=False)
            + static('BET - long haul', 'Battery electric truck, long haul (large battery, public charging)',
                     'Electricity', start=2030, co2=False))
    cols = ['Technology', 'Parameter', 'Description', 'Efficiency_link', 'Value']
    s = pd.concat([s, pd.DataFrame(rows, columns=cols)], ignore_index=True)

    # technologies: dynamic parameters (assignment table; FCET and H2-ICE truck from freight_presets)
    def dyn(t, capex, fom, vom, eff, life, emis=None):
        """Dynamic rows (per period) of a truck technology: CAPEX €/kW, FOM €/kW/yr, VOM €/kWh, efficiency,
        lifetime and emissions (t CO2/MWh of fuel)."""
        out = [(t, 'CAPEX', '€/kW', *capex), (t, 'FOM', '€/kW', *fom), (t, 'VOM', '€/kWh', *vom),
               (t, 'Efficiency', None, *eff), (t, 'Lifetime', 'years', *life)]
        if emis is not None:
            out.append((t, 'Emissions', 'tCO2/MWh_th', *emis))
        return out
    k = lambda v: [v] * 4
    fc = lambda par_: [FCET_PARAMS[par_][y] for y in YEARS]
    hi = lambda par_: [H2ICE_PARAMS[par_][y] for y in YEARS]
    rows = (dyn('ICE truck', k(120), k(3), k(0.01), k(0.40), k(12), k(0.25))
            + dyn('ICE truck - existing', k(0), k(3), k(0.01), k(0.40), k(4), k(0.25))
            + dyn('BET', k(650), k(5), k(0.10), k(0.70), k(8))
            + dyn('BET - existing', k(0), k(5), k(0.10), k(0.70), k(4))
            + dyn('FCET', fc('CAPEX'), fc('FOM'), fc('VOM'), fc('Efficiency'), fc('Lifetime'))
            + dyn('H2-ICE truck', hi('CAPEX'), hi('FOM'), hi('VOM'), hi('Efficiency'), hi('Lifetime'))
            + dyn('BET - urban', k(650), k(5), k(0.10), k(0.70), k(8))
            + dyn('BET - long haul', k(650), k(5), k(0.10), k(0.70), k(8)))
    d = pd.concat([d, pd.DataFrame(rows, columns=['Technology', 'Parameter', 'Unit'] + YEARS)], ignore_index=True)

    # base-year calibration: BET stock 0.1 GW of output; no new ICE trucks or BETs in 2020
    c = c[~c.Technology.isin(trucks)]
    cal = [('BET - existing', 'min', 100.0), ('BET - existing', 'max', 100.0), ('BET', 'max', 0.0),
           ('ICE truck', 'max', 0.0)]
    c = pd.concat([c, pd.DataFrame([{'Technology': t, 'Type': ty, 'Unit': 'MW', 2020: v} for t, ty, v in cal])],
                  ignore_index=True)

    # hydrogen routes (additions): pure green and pink, each on its own electricity bus
    adds = {'Wind turbine - offshore - dedicated': ('Wind turbine - offshore', {'bus1': 'Electricity - pure green',
                                                    'Carrier': 'Wind offshore - dedicated'}),
            'Wind turbine - onshore - dedicated': ('Wind turbine - onshore', {'bus1': 'Electricity - pure green',
                                                   'Carrier': 'Wind onshore - dedicated'}),
            'Solar PV - dedicated': ('Solar PV', {'bus1': 'Electricity - pure green', 'Carrier': 'Solar - dedicated'}),
            'Electrolyser - pure green': ('Electrolyser', {'bus0': 'Electricity - pure green'}),
            'Nuclear plant - dedicated': ('Nuclear plant', {'bus1': 'Electricity - pink'}),
            'Electrolyser - pink': ('Electrolyser', {'bus0': 'Electricity - pink'})}
    s, d = s[~s.Technology.isin(adds)], d[~d.Technology.isin(adds)]
    for new, (src, changes) in adds.items():
        s, d = _copy_tech(s, d, src, new, {**changes, 'Start year': 2030,
                                           'Long name': f'{new} (hydrogen route addition)'})
    res = res[~res.Resource.isin(['Electricity - pure green', 'Electricity - pink'])]
    for b in ('Electricity - pure green', 'Electricity - pink'):
        res.loc[len(res)] = {'Resource': b, 'Carrier': b, 'Type': 'Secondary'}

    # gasoline is imported at its price: no binding reserve
    par.loc[(par.Resource == 'Gasoline supply') & (par.Parameter == 'Reserves'), 2020] = 1e12

    DST.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(DST / 'technologies.xlsx') as w:
        s.to_excel(w, sheet_name='static_parameters', index=False)
        d.to_excel(w, sheet_name='dynamic_parameters', index=False)
        c.to_excel(w, sheet_name='capacity_constraints', index=False)
    with pd.ExcelWriter(DST / 'demand.xlsx') as w:
        prof.to_excel(w, sheet_name='normalized_profiles', index=False)
        dem.to_excel(w, sheet_name='demands', index=False)
        drv.to_excel(w, sheet_name='drivers', index=False)
        fp.to_excel(w, sheet_name='freight_profiles', index=False)
    with pd.ExcelWriter(DST / 'supply.xlsx') as w:
        res.to_excel(w, sheet_name='resources', index=False)
        par.to_excel(w, sheet_name='resources_parameters', index=False)
        ren.to_excel(w, sheet_name='ren_profiles', index=False)
    print(f'Written {DST}: freight demand {FREIGHT_PJ_2020:.0f} PJ in 2020, {len(trucks)} truck technologies')


if __name__ == '__main__':
    main()
