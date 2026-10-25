"""Write docs/results_summary.md: the main numbers of THIS package (with or without additions), from its saved runs.

    The interface imports these functions to summarize saved runs.
"""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import presentation as pres
from .h2_results import summary, cumulative_co2, gas_use, _horizon
ADDITIONS = False
SET_NAME = 'without additions'
SET_LONG = 'without additions: SMR, SMR + CCS and the grid electrolyser; storage sensitivities included'

ROOT = Path(__file__).resolve().parents[2]


def _md(df, fmt=None, index=True):
    """A pandas DataFrame as a Markdown table (no extra packages)."""
    fmt = fmt or {}
    cols = list(df.columns)
    head = ([df.index.name or ''] if index else []) + [str(c) for c in cols]
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    for i, r in df.iterrows():
        cells = [str(i)] if index else []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                f = fmt.get(c, '{:,.1f}')
                txt = '–' if np.isnan(v) else f.format(v + 0.0)
                if txt.startswith('-') and not txt.strip('-0.,'):      # '-0.0' -> '0.0'
                    txt = txt[1:]
                cells.append(txt)
            else:
                cells.append(str(v))
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def scenario_table(period=2050):
    R = pres.scenarios()
    rows = {}
    for k, n in R.items():
        s = summary(n)
        rows[k] = {
            'System cost 2020-2059 (bn €, discounted)': pres._econ_cost(n),
            f'Electrolysis share {period} (%)': float(np.nan_to_num(s.at[period, 'Electrolysis share (%)'])),
            f'Electrolysers {period} (GW_el)': s.at[period, 'Electrolyser capacity (GW_el)'],
            f'Full-load hours {period}': s.at[period, 'Electrolyser full-load hours (h/yr)'],
            f'H2 storage {period} (TWh)': s.at[period, 'H2 storage (GWh)'] / 1e3,
            f'Gas for H2 {period} (TWh)': s.at[period, 'Gas for H2 (TWh/yr)'],
            'Gas imports 2020-2059 (TWh)': _horizon(n, gas_use(n)['Gas use, total (TWh/yr)']),
            'CO2 2020-2059 (Mt)': cumulative_co2(n),
            f'CO2 {period} (Mt/yr)': s.at[period, 'CO2 total (Mt/yr)'],
            f'Water for H2 {period} (Mm3)': s.at[period, 'Water for H2 (Mm3/yr)'],
            'Value of 1 kW more electrolyser (€/kW_H2)': pres._water_value(n) if k == 'Medium' else np.nan,
        }
    return pd.DataFrame(rows)


def variation_table(period=2050):
    rows = []
    for v in pres.OVERVIEW:
        for sc in pres.SCEN:
            n = pres.run(pres.SCEN[sc] + v)
            if n is None:
                continue
            c = pres.run(pres.SCEN[sc])
            s = summary(n).loc[period]
            rows.append({'variation': pres.VARIANT_NAMES[v].replace('$_2$', '₂'), 'scenario': sc,
                         f'Electrolysis share {period} (%)': float(np.nan_to_num(s['Electrolysis share (%)'])),
                         f'Electrolysers {period} (GW_el)': s['Electrolyser capacity (GW_el)'],
                         'System cost vs central (bn €)': pres._econ_cost(n) - pres._econ_cost(c),
                         'CO2 vs central (Mt)': cumulative_co2(n) - cumulative_co2(c)})
    return pd.DataFrame(rows)


def main():
    out = ROOT / 'docs' / 'results_summary.md'
    n_runs = len(list(pres.RUNS_DIR.glob('*.nc')))
    parts = [f'# Results of the package {SET_NAME}',
             '',
             f'*Written from the {n_runs} runs in `results/runs/` '
             f'({date.today():%d %B %Y}). Package: {SET_LONG}. System costs are discounted over 2020-2059 (the model '
             'objective, with subsidies added back because they are transfers); CO₂ and gas are summed over '
             '2020-2059; "vs central" = against the central run of the same scenario.*',
             '']
    st = scenario_table()
    parts += ['## The three scenarios', '', _md(st), '']
    sn = pres.scarcity_numbers()
    parts += ['## What water scarcity costs (against Base)', '',
              _md(sn, {c: '{:,.2f}' for c in sn.columns}), '']
    if ADDITIONS:
        rows = []
        for v in pres.ADDITION_ROWS:
            for sc in pres.SCEN:
                n, c = pres.run(pres.SCEN[sc] + v), pres.run(pres.SCEN[sc] + '_noadd')
                if n is None or c is None:
                    continue
                s = summary(n).loc[2050]
                rows.append({'run': {'': 'all additions (central)', '_noadd': 'without additions'}.get(
                    v, pres.VARIANT_NAMES[v].replace('$_2$', '₂')), 'scenario': sc,
                    'Electrolysis share 2050 (%)': float(np.nan_to_num(s['Electrolysis share (%)'])),
                    'Electrolysers 2050 (GW_el)': s['Electrolyser capacity (GW_el)'],
                    'of which pure green (GW_el)': s['of which pure green (GW_el)'],
                    'of which pink (GW_el)': s['of which pink (GW_el)'],
                    'H2 storage 2050 (TWh)': s['H2 storage (GWh)'] / 1e3,
                    'System cost vs without additions (bn €)': pres._econ_cost(n) - pres._econ_cost(c),
                    'CO2 vs without additions (Mt)': cumulative_co2(n) - cumulative_co2(c)})
        parts += ['## What the additions do', '', _md(pd.DataFrame(rows), index=False), '']
    vt = variation_table()
    parts += ['## Variations within the scenarios', '', _md(vt, index=False), '']
    lt = pres.lever_table()
    if lt is not None:
        lt = lt.drop(columns=['lever']).rename(columns={'label': 'lever'})
        parts += ['## Green levers within the water scenarios', '', _md(lt, index=False), '',
                  'The 60% mandate alone is infeasible in Medium (water allows electrolysis for at most 50% of the '
                  'hydrogen) and in Scarce (no electrolysers).', '']
    out.write_text('\n'.join(parts) + '\n')
    print('written', out)


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    main()

