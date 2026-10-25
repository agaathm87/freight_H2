# h2_constraints.py  
#    ← make_extra_functionality(), store_shadow_prices(), _annual_flow()

import numpy as np
import pandas as pd
import xarray as xr

from .h2_presets import (
    H2_STORAGE, ELECTROLYSIS, ELECTROLYSIS_GRID, ELECTROLYSIS_PINK, H2_LOAD, BATTERY
)
from .h2_scenario import resolve, water_limited_electrolyser_techs, electrolyser_techs
from . import freight_water   # [Freight] water caps and budget, zero-emission freight shares

__all__ = ['make_extra_functionality', 'store_shadow_prices'] 

# --------------------------------------------------------------------------
# 4. Extra constraints (added to the optimisation problem)
# --------------------------------------------------------------------------

def _annual_flow(n, links, period, sns, eff_attr='efficiency'):
    """Linear expression: weighted annual flow of `links` in `period` at the port of eff_attr (per year)."""
    m = n.model
    p = m['Link-p']
    name_dim = [d for d in p.dims if d != 'snapshot'][0]
    pos = np.where(sns.get_level_values(0) == period)[0]
    w = n.snapshot_weightings.generators.iloc[pos].values            # hours per snapshot
    eff = n.links.loc[links, eff_attr].values
    coeff = np.outer(w, eff)                                          # (snapshot, link)
    sel = p.isel(snapshot=pos).sel({name_dim: list(links)})
    return (sel * coeff).sum()


def _capacity_cap(n, component, carriers, period, cap, name):
    """Sum of capacity of all active, extendable assets of these carriers <= cap (MW or MWh)."""
    c = {'Link': n.links, 'Generator': n.generators, 'Store': n.stores, 'StorageUnit': n.storage_units}[component]
    attr = 'e_nom' if component == 'Store' else 'p_nom'
    act = n.get_active_assets(component, period)
    names = [i for i in c.index[c.carrier.isin(carriers) & c[f'{attr}_extendable']] if act.get(i, False)]
    if not names:
        return
    var = n.model[f'{component}-{attr}']
    fixed = float(c.loc[c.carrier.isin(carriers) & ~c[f'{attr}_extendable'] & act.reindex(c.index, fill_value=False),
                        attr].sum())
    n.model.add_constraints(var.sel({var.dims[0]: names}).sum() <= cap - fixed, name=name)


def make_extra_functionality(scen):
    """Return a function for n.optimize(extra_functionality=...).

    The scenario limit itself is NOT here: it is a capacity constraint of the technology table (see above).
    """

    def extra_functionality(n, sns):
        periods = sns.get_level_values(0).unique()

        # CO2 storage capacity (MtCO2/yr captured, all CCS technologies together)
        cap = resolve('co2_storage_cap', scen.get('co2_storage_cap'))
        if cap is not None:
            ccs = n.links.index[n.links.get('bus3', pd.Series('', index=n.links.index)) == 'CO2 storage']
            for y in periods:
                if y in cap and len(ccs):
                    n.model.add_constraints(_annual_flow(n, ccs, y, sns, 'efficiency3') <= cap[y] * 1e6,
                                            name=f'CO2-storage_cap-{y}')

        # Build limits per period (electrolysers, offshore wind, nuclear) and the H2 storage that can exist (option)
        caps = list(resolve('capacity_caps', scen.get('capacity_caps')) or [])
        hcap = resolve('h2_storage_cap', scen.get('h2_storage_cap'))
        if scen.get('h2_storage') and hcap is not None:
            caps.append(dict(name='H2 storage', component='Store', carriers=H2_STORAGE, cap=hcap))
        for c in caps:
            for y in periods:
                if y in c['cap']:
                    _capacity_cap(n, c['component'], c['carriers'], y, c['cap'][y],
                                  name=f"Cap-{c['name'].replace(' ', '_')}-{y}")

        # Green lever: a minimum share of the hydrogen made by electrolysis (all electrolysers), per period
        mandate = scen.get('green_mandate') or {}
        if isinstance(mandate, str):                      # [Freight] preset name, e.g. 'red3'
            from .freight_presets import GREEN_MANDATES
            mandate = GREEN_MANDATES[mandate]
        if mandate:
            # [Freight] renewable electrolysis only (RFNBO): pink hydrogen from nuclear power does not count
            ely = n.links.index[n.links.carrier.isin([e for e in ELECTROLYSIS if e not in ELECTROLYSIS_PINK])]
            w_all = n.snapshot_weightings.generators
            for y in periods:
                share = mandate.get(y, mandate.get(str(y)))
                if not share:
                    continue
                sl = sns.get_level_values(0) == y
                p_set = n.get_switchable_as_dense('Load', 'p_set')[H2_LOAD]
                demand = float((p_set[sl] * w_all[sl]).sum())                             # MWh/yr in period y
                n.model.add_constraints(_annual_flow(n, ely, y, sns, 'efficiency') >= float(share) * demand,
                                        name=f'Green-mandate-{y}')

        # (1) Freshwater: the joint limit on grid electrolysers per vintage.
        total = scen.get('_electrolyser_cap_total_mw_h2') or {}
        techs = water_limited_electrolyser_techs(scen)
        if total and len(techs) > 1 and scen.get('electrolyser_limit_on', 'capacity') == 'capacity':
            var = n.model['Link-p_nom']
            ext = set(n.links.index[n.links.p_nom_extendable])
            for y, cap in total.items():
                names = [f'{t}_{y}' for t in techs if f'{t}_{y}' in ext]
                if not names:
                    continue
                eff = xr.DataArray([float(n.links.at[l, 'efficiency']) for l in names], coords={var.dims[0]: names})
                n.model.add_constraints((var.sel({var.dims[0]: names}) * eff).sum() <= cap,
                                        name=f'Electrolyser-total-cap-{y}')

        # Over-dimensioned plant with its own plant reference: water caps the hourly hydrogen output of all
        # electrolysers together at the MW that the water reference allows (the vintages still in use)
        water = scen.get('_electrolyser_water_mw_h2') or {}
        if water:
            p = n.model['Link-p']
            name_dim = [d for d in p.dims if d != 'snapshot'][0]
            ely_all = list(n.links.index[n.links.carrier.isin(electrolyser_techs(scen))])
            life = {int(v): float(n.links.at[f'{ELECTROLYSIS_GRID[0]}_{v}', 'lifetime'])
                    if f'{ELECTROLYSIS_GRID[0]}_{v}' in n.links.index else 25.0 for v in water}
            for y in periods:
                act = n.get_active_assets('Link', y)
                names = [l for l in ely_all if act.get(l, False)]
                if not names:
                    continue
                cap = sum(v for vy, v in water.items() if int(vy) <= y < int(vy) + life[int(vy)])
                pos = np.where(sns.get_level_values(0) == y)[0]
                eff = xr.DataArray(n.links.loc[names, 'efficiency'].values.astype(float), coords={name_dim: names})
                n.model.add_constraints((p.isel(snapshot=pos).sel({name_dim: names}) * eff).sum(name_dim) <= cap,
                                        name=f'Electrolyser-water-output-{y}')

        # (3b) Maximum battery power in each period (MW, summed over all active vintages)
        if scen['battery'] and scen['battery_max_mw'] is not None:
            for y in periods:
                _capacity_cap(n, 'StorageUnit', BATTERY, y, scen['battery_max_mw'], name=f'Battery-max_power-{y}')

        # [Freight] water-scarce capacity caps, the freshwater budget, zero-emission freight shares
        freight_water.add_constraints(n, sns, scen)

    return extra_functionality


def _jsonable(obj):
    """Scenario dict -> JSON-safe (str keys, plain floats) so it can be saved on n.meta in the netCDF file."""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def store_shadow_prices(n, scen=None):
    """Save the scenario settings and the shadow prices of the extra constraints on n.meta (restored group function,
    extended for the freight and water modules). Shadow price = |dual|; per YEAR of the period (dual / objective
    weighting of the period, undiscounted) unless marked present value (PV, discounted like the objective).

      co2_storage_cap_shadow_price   {year: €/t}                       CO2-storage cap (group)
      electrolyser_cap_shadow_price_eur_per_kw_h2  {tech | 'total': {year: €/kW_H2, PV}}   group water limit on
                                     electrolyser capacity: what 1 kW more electrolyser (H2 output) is worth over
                                     its life
      electrolyser_water_output_shadow_price  {year: {...}}            group water limit on hourly electrolyser output:
                                     €/kW_H2/yr, and the water shadow price in €/m3 (mean, summer mean, per month)
      build_cap_shadow_price_eur_per_kw_yr   {cap: {year: €/kW/yr}}    build limits (offshore wind, nuclear, ...)
      co2_cap_shadow_price           {year: €/t}                       net-zero cap: carbon price needed on top of ETS
      water_cap_shadow_price         {group: {year: €/kW/yr}}          water-scarce capacity caps (MW of p_nom basis)
      water_budget_shadow_price      {'year'|'summer': {year: €/m3}}   freshwater budget (= alt. water cost if used)
      water_drought_shadow_price     {'cat3'|'cat4'|'pool': {year: €/m3}}  verdringingsreeks quota per category in the
                                     drought season, or the cost-optimal pool (= alt. water cost when it is bought)
      ze_share_shadow_price          {'max'|'min': {year: €/MWh of freight}}
      h2_trucks_rfnbo_shadow_price_eur_per_kg  {year: €/kg}   renewable hydrogen for the trucks (h2_trucks_rfnbo)
      freight_segment_shadow_price   {'bet-tier-<type>'|'h2-truck-max'|'heavy-segment': {year: €/MWh of freight}}
                                     realistic layer: value of 1 MWh/yr more freight from that group of trucks
      green_mandate_shadow_price_eur_per_kg  {year: €/kg}
      rfnbo_transport_shadow_price   {'use'|'supply': {year: €/MWh_H2}}
    """
    if getattr(n, 'model', None) is None:
        return {}
    from .h2_presets import KG_PER_MWH_H2, WATER_L_PER_KG
    m = n.model
    w = n.investment_period_weightings['objective']
    meta = dict(n.meta or {})
    if scen is not None:
        meta['scenario'] = _jsonable({k: v for k, v in scen.items() if not k.startswith('_db')})
    m3_per_mwh_h2 = WATER_L_PER_KG['electrolysis'] * KG_PER_MWH_H2 / 1e3     # 0.66 m3 of water per MWh of H2
    sp = {}

    def put(key, sub, y, val):
        sp.setdefault(key, {}).setdefault(sub, {})[str(y)] = val

    for name in list(m.constraints):
        parts = name.rsplit('-', 1)
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        try:
            dual = m.constraints[name].dual
            vals = np.abs(np.nan_to_num(np.asarray(dual.values, dtype=float).ravel()))
        except Exception:
            continue
        d = float(vals.sum())
        y = int(parts[1])
        wy = float(w.get(y, np.nan))
        if name.startswith(('Water-cap-', 'Cap-', 'Battery-max_power-', 'Electrolyser-total-cap-')):
            try:
                rhs = np.asarray(m.constraints[name].rhs.values, dtype=float).ravel()
            except Exception:
                rhs = np.array([np.nan])
            if rhs.size and np.all(np.abs(rhs) < 1e-6):
                continue        # a limit of 0: the dual is not unique (degenerate), so no marginal value is defined
        if name.startswith('CO2-storage_cap-'):
            sp.setdefault('co2_storage_cap_shadow_price', {})[str(y)] = d / wy
        elif name.startswith('CO2-cap-'):
            sp.setdefault('co2_cap_shadow_price', {})[str(y)] = d / wy
        elif name.startswith('Electrolyser-total-cap-'):
            put('electrolyser_cap_shadow_price_eur_per_kw_h2', 'total', y, d / 1e3)
        elif name.startswith('Electrolyser-water-output-'):
            # one dual per snapshot: €/MW_H2 of allowed output in that hour (PV) -> €/MWh_H2 -> €/m3 of water
            pos = np.where(n.snapshots.get_level_values(0) == y)[0]
            hrs = n.snapshot_weightings.generators.iloc[pos].values
            if len(vals) != len(pos):
                continue
            eur_m3 = vals / (wy * hrs) / m3_per_mwh_h2
            month = n.snapshots[pos].get_level_values(1).month
            summer = np.isin(month, [6, 7, 8, 9])
            wmean = lambda mask: float((eur_m3[mask] * hrs[mask]).sum() / hrs[mask].sum()) if mask.any() else np.nan
            sp.setdefault('electrolyser_water_output_shadow_price', {})[str(y)] = {
                'eur_per_kw_h2_yr': d / wy / 1e3,
                'eur_per_m3_mean': wmean(np.ones(len(pos), bool)),
                'eur_per_m3_summer': wmean(summer),
                'eur_per_m3_by_month': {str(k): wmean(month == k) for k in range(1, 13)},
                'hours_binding': float(hrs[vals > 1e-9].sum())}
        elif name.startswith('Cap-') or name.startswith('Battery-max_power-'):
            put('build_cap_shadow_price_eur_per_kw_yr', parts[0].replace('Cap-', ''), y, d / wy / 1e3)
        elif name.startswith('Water-cap-'):
            put('water_cap_shadow_price', name[len('Water-cap-'):].rsplit('-', 1)[0], y, d / wy / 1e3)
        elif name.startswith('Water-drought-'):
            put('water_drought_shadow_price', name.split('-')[2], y, d / wy)
        elif name.startswith('Water-budget-'):
            put('water_budget_shadow_price', name.split('-')[2], y, d / wy)
        elif name.startswith('Freight-ze_'):
            put('ze_share_shadow_price', 'max' if 'max' in name else 'min', y, d / wy)
        elif name.startswith('H2-trucks-rfnbo-'):
            # renewable hydrogen at the pump: what 1 kg more renewable hydrogen for the trucks costs the system
            sp.setdefault('h2_trucks_rfnbo_shadow_price_eur_per_kg', {})[str(y)] = d / wy / KG_PER_MWH_H2
        elif name.startswith(('Freight-bet-tier-', 'Freight-h2-truck-max', 'Freight-heavy-segment')):
            # realistic layer: segment caps on BET duty cycles, hydrogen trucks and the heavy segment (€/MWh freight)
            put('freight_segment_shadow_price', parts[0][len('Freight-'):], y, d / wy)
        elif name.startswith('Green-mandate-'):
            sp.setdefault('green_mandate_shadow_price_eur_per_kg', {})[str(y)] = d / wy / KG_PER_MWH_H2
        elif name.startswith('RFNBO-transport-'):
            put('rfnbo_transport_shadow_price', name.split('-')[2], y, d / wy)

    # Group water limit on the capacity of each electrolyser (a max in the technology table -> bound on p_nom of the
    # vintage): the value of 1 kW more electrolyser (H2 output) over its lifetime, present value (€/kW_H2)
    caps = (scen or {}).get('_electrolyser_caps_mw_h2') or {}
    if caps and 'Link-ext-p_nom-upper' in m.constraints:
        dual = m.constraints['Link-ext-p_nom-upper'].dual.to_series()
        for tech, c in caps.items():
            for y in c:
                link = f'{tech}_{y}'
                if float(c[y] or 0.0) <= 1e-6:
                    continue    # limit 0 (e.g. S3): degenerate dual, no marginal value
                if link in dual.index and link in n.links.index:
                    put('electrolyser_cap_shadow_price_eur_per_kw_h2', tech, y,
                        abs(float(dual[link])) / float(n.links.at[link, 'efficiency']) / 1e3)
    sp = _clean(_jsonable(sp))
    meta.update(sp)
    n.meta = meta
    return sp


def _clean(obj, tol=1e-4):
    """Interior-point noise (duals of ~1e-9 on constraints that do not bind) -> 0 (below 1e-4 €)."""
    if isinstance(obj, dict):
        return {k: _clean(v, tol) for k, v in obj.items()}
    if isinstance(obj, float) and abs(obj) < tol:
        return 0.0
    return obj
