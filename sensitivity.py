"""Sensitivity analysis as its own script (moved out of interface.ipynb, section 7.1).

A sensitivity is a grid of two settings (x, y) around a base run, for one or more scenarios. Every grid point is
solved once and saved in results/runs_sens/<name>.nc; the metric goes to results/outputs/sens_<grid>.csv and a
heatmap per scenario and period to results/plots/sens_<grid>_<scenario>.png.

Command line:   python sensitivity.py --list
                python sensitivity.py bet_vom_x_gasoline                 (one grid, Gurobi)
                python sensitivity.py bet_vom_x_gasoline --points 0-7    (only points 0-7, e.g. for a queue)
                python sensitivity.py co2_x_subsidy --solver gurobi      (the group's hydrogen grids)
From the notebook:
                import sensitivity as sa
                df = sa.run_grid('bet_vom_x_gasoline_nofcet', solver='gurobi')  # solves what is not on disk
                sa.plot_grid(df, 'bet_vom_x_gasoline_nofcet')

Add a grid by adding an entry to GRIDS. Any setting of make_scenario can be an axis. The assignment's own
sensitivities (carbon price, time restrictions) are single runs in run_freight.py (groups 'core_sensitivity' and
'real_sensitivity'); the grids here map the tipping point behind them.
"""
import argparse
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

YEARS, T_RES, CARS_CF, RT, RS = [2020, 2030, 2040, 2050], 15, 40 * 0.1, 0.07, 0.01
RUN_DIR = os.path.join('results', 'runs_sens')
DBS = {'h2': 'input_databases//h2_nl', 'freight': 'input_databases//freight_nl'}

# The grids. 'scenarios': base runs (h2: S1/S2/S3; freight: names in run_freight.RUNS). 'fixed': extra settings.
GRIDS = {
    # --- the group's hydrogen study (from interface.ipynb 7.1); 'from:S1' = the electrolyser capacity of run S1 ---
    'co2_x_subsidy': dict(package='h2', scenarios=['S1', 'S2', 'S3'],
                          x=('electrolyser_subsidy', [0.0, 0.10, 0.20, 0.30, 0.40]),
                          y=('co2_price', [100, 170, 250, 350, 500]),
                          fixed=dict(electrolyser_reference='from:S1'),
                          metric='Electrolysis share (%)', periods=[2030, 2050]),
    'cap_x_co2': dict(package='h2', scenarios=['S1', 'S2', 'S3'],
                      x=('co2_price', [100, 170, 250, 350, 500]),
                      y=('electrolyser_cap_share', [0.0, 0.25, 0.50, 0.75, 1.0]),
                      fixed=dict(electrolyser_reference='from:S1'),
                      metric='CO2 total (Mt/yr)', periods=[2030, 2050]),
    'battery_x_co2': dict(package='h2', scenarios=['S1', 'S2', 'S3'],
                          x=('co2_price', [100, 250, 500]), y=('battery_cost_factor', [0.5, 0.75, 1.0, 1.25]),
                          fixed=dict(electrolyser_reference='from:S1'),
                          metric='Electrolysis share (%)', periods=[2030, 2050]),
    # --- the freight study ---
    # tipping point: how high must the charging penalty be, or how low the fuel price, for ICE trucks to stay?
    # Three truck sets on the same axes: the hydrogen extension (BET, FCET, H2-ICE truck), ICE + BET + H2-ICE truck
    # (no fuel cells) and the assignment's ICE trucks and BETs only
    'bet_vom_x_gasoline': dict(package='freight', scenarios=['F1'],
                               x=('gasoline_price', [70, 120, 200, 300]),
                               y=('bet_vom_factor', [1.0, 2.0, 3.0, 4.0]),
                               metric='ZE share of freight (%)', periods=[2030, 2050]),
    'bet_vom_x_gasoline_h2ice': dict(package='freight', scenarios=['F1'],
                                     x=('gasoline_price', [70, 120, 200, 300]),
                                     y=('bet_vom_factor', [1.0, 2.0, 3.0, 4.0]),
                                     fixed=dict(fcet=False, h2ice=True),
                                     metric='H2-ICE share of freight (%)', periods=[2030, 2050]),
    # the same tipping point within the assignment's specs: ICE trucks and BETs only (no hydrogen trucks)
    'bet_vom_x_gasoline_nofcet': dict(package='freight', scenarios=['F1'],
                                      x=('gasoline_price', [70, 120, 200, 300]),
                                      y=('bet_vom_factor', [1.0, 2.0, 3.0, 4.0]),
                                      fixed=dict(fcet=False),
                                      metric='ZE share of freight (%)', periods=[2030, 2050]),
}


def _tag(v):
    """A grid value as part of a file name: 0.25 -> '0p25'."""
    return str(v).replace('.', 'p').replace(' ', '')


def _base_settings(package, scenario, solver):
    """(base scenario, settings) of a base run."""
    if package == 'freight':
        import run_freight
        base, settings = run_freight.RUNS[scenario]
        return base, dict(settings)
    return scenario, {}


def _resolve_refs(settings, solver):
    """'from:<run>' -> the electrolyser capacity per vintage of that run of run_batch (solved if missing)."""
    if any(isinstance(v, str) and v.startswith('from:') for v in settings.values()):
        import run_batch
        settings = run_batch._reference(dict(settings), solver)
    return settings


def solve(name, base, settings, package, solver='gurobi', rerun=False):
    """Solve one grid point (or load it) and return the network."""
    import pypsa
    from energy_model import model_run, make_scenario
    path = os.path.join(RUN_DIR, f'{name}.nc')
    if os.path.exists(path) and not rerun:
        n = pypsa.Network(path)
    else:
        if solver != 'gurobi':
            raise ValueError(f"Unsupported solver {solver!r}; this project requires 'gurobi'.")
        opts = {'Threads': 1, 'TimeLimit': 7200}
        n = model_run(DBS[package], YEARS, T_RES, CARS_CF, RT, RS, solver_name=solver, solver_options=opts,
                      scenario=make_scenario(base, **dict(settings, label=name)),
                      results_dir=os.path.join('results', 'logs'))
        if n.loads_t.p.empty:
            print(f'{name}: infeasible, skipped')
            return None
        os.makedirs(RUN_DIR, exist_ok=True)
        n.export_to_netcdf(path)
        print(f'{name}: solved and saved')
    n.name = name
    return n


def metric(n, name, period, package):
    """The value of the grid's metric for one run and period."""
    if package == 'freight':
        from figures.plots.freight_results import summary
        s = summary(n)
        if name in s.columns:
            return float(s.at[period, name])
    from figures.plots.h2_results import compare
    return float(compare({n.name: n}, period=period)[name].iloc[0])


def run_grid(grid, solver='gurobi', rerun=False, scenarios=None, part=None):
    """Solve (or load) every point of a grid; returns a long table scenario, x, y, period, value.
    part=(i, k): solve only every k-th point starting at i (to split a grid over k processes); the other points
    are loaded if they are on disk."""
    g = GRIDS[grid]
    (xk, xs), (yk, ys) = g['x'], g['y']
    rows, count = [], -1
    for sc in scenarios or g['scenarios']:
        base, settings = _base_settings(g['package'], sc, solver)
        for xv in xs:
            for yv in ys:
                s = _resolve_refs({**settings, **g.get('fixed', {}), xk: xv, yk: yv}, solver)
                name = f'sens_{grid}_{sc}_{xk}{_tag(xv)}_{yk}{_tag(yv)}'
                count += 1
                if part is not None and count % part[1] != part[0]:
                    if not os.path.exists(os.path.join(RUN_DIR, f'{name}.nc')):
                        continue
                n = solve(name, base, s, g['package'], solver, rerun)
                for p in g['periods']:
                    val = np.nan if n is None else metric(n, g['metric'], p, g['package'])
                    rows.append(dict(scenario=sc, x=xv, y=yv, period=p, value=val))
    df = pd.DataFrame(rows)
    os.makedirs(os.path.join('results', 'outputs'), exist_ok=True)
    df.to_csv(os.path.join('results', 'outputs', f'sens_{grid}.csv'), index=False)
    return df


def solve_points(grid, points, solver='gurobi', rerun=False):
    """Solve only the grid points with these indices (order: scenario, x, y), e.g. for a queue; no table."""
    g = GRIDS[grid]
    (xk, xs), (yk, ys) = g['x'], g['y']
    count = -1
    for sc in g['scenarios']:
        base, settings = _base_settings(g['package'], sc, solver)
        for xv in xs:
            for yv in ys:
                count += 1
                if count in points:
                    s = _resolve_refs({**settings, **g.get('fixed', {}), xk: xv, yk: yv}, solver)
                    solve(f'sens_{grid}_{sc}_{xk}{_tag(xv)}_{yk}{_tag(yv)}', base, s, g['package'], solver, rerun)


def plot_grid(df, grid, save=True, cmap='YlGn'):
    """One heatmap per scenario and period (rows = y setting, columns = x setting)."""
    g = GRIDS[grid]
    figs = []
    for sc, d in df.groupby('scenario', sort=False):
        periods = list(d.period.unique())
        fig, axes = plt.subplots(1, len(periods), figsize=(3.4 * len(periods) + 1, 3.2), squeeze=False)
        for ax, p in zip(axes[0], periods):
            m = d[d.period == p].pivot(index='y', columns='x', values='value')
            m = m.reindex(index=g['y'][1], columns=g['x'][1])
            im = ax.imshow(m.values.astype(float), cmap=cmap, aspect='auto', origin='lower')
            for (i, j), v in np.ndenumerate(m.values.astype(float)):
                ax.text(j, i, '–' if np.isnan(v) else f'{v:.1f}', ha='center', va='center', fontsize=8)
            ax.set_xticks(range(len(m.columns)), [str(c) for c in m.columns], fontsize=8)
            ax.set_yticks(range(len(m.index)), [str(i) for i in m.index], fontsize=8)
            ax.set_xlabel(g['x'][0], fontsize=8)
            ax.set_ylabel(g['y'][0], fontsize=8)
            ax.set_title(f'{sc}, {p}', fontsize=9)
            fig.colorbar(im, ax=ax, shrink=0.8).ax.tick_params(labelsize=8)
        fig.suptitle(f"{g['metric']}", fontsize=9)
        fig.tight_layout()
        if save:
            os.makedirs(os.path.join('results', 'plots'), exist_ok=True)
            fig.savefig(os.path.join('results', 'plots', f'sens_{grid}_{sc}.png'), dpi=300, bbox_inches='tight')
        figs.append(fig)
    return figs


def main(grid, solver='gurobi', rerun=False):
    """Solve every point of a grid that is not on disk, draw its heatmaps and return the metric table."""
    df = run_grid(grid, solver, rerun)
    plot_grid(df, grid)
    return df


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('grids', nargs='*')
    ap.add_argument('--solver', choices=['gurobi'], default='gurobi')
    ap.add_argument('--rerun', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--part', default=None, help='i/k: solve every k-th grid point from i (parallel processes)')
    ap.add_argument('--points', default=None, help='a-b: solve only grid points a to b (0-based), no table')
    a = ap.parse_args()
    if a.list or not a.grids:
        for k, v in GRIDS.items():
            print(f"{k:22s} {v['package']:8s} x={v['x'][0]} y={v['y'][0]} metric={v['metric']}")
    for gname in a.grids:
        if a.points:
            lo, hi = (int(v) for v in (a.points.split('-') + [a.points])[:2])
            solve_points(gname, set(range(lo, hi + 1)), a.solver, a.rerun)
        elif a.part:
            run_grid(gname, a.solver, a.rerun, part=tuple(int(v) for v in a.part.split('/')))
        else:
            main(gname, a.solver, a.rerun)
