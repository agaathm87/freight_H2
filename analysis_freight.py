"""Analysis of the freight runs: tables (results/outputs) and the result figures of the paper (results/plots/freight).

Usage:  python analysis_freight.py          (uses the runs on disk in results/runs; missing runs are skipped)

Figures (png + svg, 300 dpi):
  R1-R3                core (ICE + BET) results: fleet transition and power system, emissions, cost of switching;
                       R1_h2-R3_h2 the same for the hydrogen extension
  R1-R3 ..._real       realistic layer against the core: fleet transition (core / no policies / current policies),
                       emissions, cost of switching (with and without the toll and subsidy transfers)
  R4_tipping_point     fuel price x BET charging penalty for three truck sets (the sensitivity grids)
  R5_sensitivities     heatmaps of the assignment's sensitivities (carbon price, time restrictions), core and realistic
  R6_policy_levers     heatmap of the policy and market levers of the realistic layer (F1, F4)
  R7_transition_speed  zero-emission share per period inside the realistic corridor, and the value of a faster ramp-up
  S1-S5                system figures: Sankeys with the freight trucks (2030, 2050), final energy of the trucks by
                       carrier, the energy balance of F1_real, hydrogen supply and use, electricity generation
  A_water_driver       the water-scarcity driver: drought-season water under the verdringingsreeks and its cost
Tables: freight_key_numbers.md (all tables in one file) and one csv per table (freight_*.csv), among them the
calibration and tests of assignment step 5 (freight_calibration_tests.csv). Only the runs of run_freight.RUNS are
loaded; the water-scarcity driver runs ('*_real_water*') are in A_water_driver and freight_water_driver.csv.
"""
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pypsa

warnings.filterwarnings('ignore')
from figures.plots import freight_results as fr  # noqa: E402

RUNS = os.path.join('results', 'runs')
OUT, FIG = os.path.join('results', 'outputs'), os.path.join('results', 'plots', 'freight')
SCEN = ['F1', 'F2', 'F3', 'F4']                       # with hydrogen trucks, FCET and H2-ICE (the extension)
SCEN_CORE = [f'{f}_nofcet' for f in SCEN]             # the assignment's own set: ICE trucks and BETs only
LABEL = {'F1': 'F1 BET costs flat, fuel moderate', 'F2': 'F2 BET costs fall, fuel moderate',
         'F3': 'F3 BET costs flat, fuel sharp', 'F4': 'F4 BET costs fall, fuel sharp'}
# validated categorical palette (dataviz reference, light mode); ICE trucks = neutral grey (the incumbent)
C = {'BET': '#2a78d6', 'FCET': '#1baf7a', 'H2-ICE truck': '#6250d6', 'ICE truck': '#8a8f98',
     'F1': '#2a78d6', 'F2': '#eb6834', 'F3': '#1baf7a', 'F4': '#eda100',
     'Freight trucks': '#eb6834', 'Passenger cars': '#6250d6', 'Rest of system': '#8a8f98'}
INK, MUTED = '#1f2328', '#59636e'
plt.rcParams.update({'font.size': 8, 'axes.titlesize': 9, 'axes.labelsize': 8, 'legend.fontsize': 8,
                     'xtick.labelsize': 8, 'ytick.labelsize': 8, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'font.family': 'DejaVu Sans'})


def load(name):
    """The solved network results/runs/<name>.nc (with n.name set), or None when the run is not on disk."""
    path = os.path.join(RUNS, f'{name}.nc')
    if not os.path.exists(path):
        return None
    n = pypsa.Network(path)
    n.name = name
    return n


def save(fig, stem):
    """Save a figure as results/plots/freight/<stem>.png and .svg (300 dpi, white background) and close it."""
    os.makedirs(FIG, exist_ok=True)
    for ext in ('png', 'svg'):
        fig.savefig(os.path.join(FIG, f'{stem}.{ext}'), dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)


GEN_GROUPS = {'Solar': ['Solar'], 'Wind onshore': ['Wind onshore'], 'Wind offshore': ['Wind offshore'],
              'Gas': ['CCGT', 'CCGT - existing'], 'Gas + CCS': ['CCGT CCS'], 'Nuclear': ['Nuclear plant'],
              'Biomass': ['Biomass plant', 'Biomass plant CCS']}
GEN_COLORS = {'Solar': '#eda100', 'Wind onshore': '#008300', 'Wind offshore': '#2a78d6', 'Gas': '#8a8f98',
              'Gas + CCS': '#59636e', 'Nuclear': '#6250d6', 'Biomass': '#e87ba4'}


def grid_generation(n):
    """Electricity generated for the grid per technology group (TWh/yr), per period (dedicated plants excluded)."""
    w = n.snapshot_weightings.generators
    g = n.generators[n.generators.bus == 'Electricity']
    gen = n.generators_t.p.reindex(columns=g.index, fill_value=0).mul(w, axis=0).groupby(level=0).sum()
    gen = gen.T.groupby(g.carrier).sum().T
    lk = n.links[n.links.bus1 == 'Electricity']
    lo = (-n.links_t.p1.reindex(columns=lk.index, fill_value=0)).mul(w, axis=0).groupby(level=0).sum()
    lo = lo.T.groupby(lk.carrier).sum().T
    both = pd.concat([gen, lo], axis=1)
    return pd.DataFrame({k: both.reindex(columns=v, fill_value=0).sum(axis=1) for k, v in GEN_GROUPS.items()}) / 1e6


def cumulative(series, n):
    """Sum over the horizon of a per-period yearly value (each period counts its number of years)."""
    return float((series * n.investment_period_weightings['years']).sum())


def result_figures(runs, main_runs, sw, suffix=''):
    """Figures R1-R3 for one scenario set: the assignment core (ICE + BET, suffix '') or the hydrogen extension
    (with fuel-cell and hydrogen combustion trucks, suffix '_h2')."""
    periods = list(next(iter(main_runs.values())).investment_periods)

    # ---- R1: the fleet transition (top) and what it does to the power system (bottom) ----
    fig, axes = plt.subplots(2, len(main_runs), figsize=(6.5, 5.0), sharey='row')
    for col, (k, n) in enumerate(main_runs.items()):
        ax = axes[0, col]
        out = fr.freight_output(n)
        bottom = 0
        for g in ['ICE truck', 'BET', 'FCET', 'H2-ICE truck'][:2 if suffix == '' else 4]:
            ax.bar(range(len(periods)), out[g].values, bottom=bottom, color=C[g], width=0.7,
                   edgecolor='white', linewidth=1, label=g)
            bottom = bottom + out[g].values
        ax.set_xticks(range(len(periods)), [str(p) for p in periods], fontsize=7)
        ax.set_title(LABEL[k.split('_')[0]].replace(', ', ',\n'), fontsize=8, color=INK)
        ax.grid(axis='y', color='#e6e8eb', linewidth=0.6)
        ax.set_axisbelow(True)
        ax = axes[1, col]
        ice = runs.get(f"{k.split('_')[0]}_ice")
        if ice is not None:
            d = grid_generation(n) - grid_generation(ice)
            pos, neg = 0, 0
            for gname in GEN_GROUPS:
                v = d[gname].values
                ax.bar(range(len(periods)), v.clip(min=0), bottom=pos, color=GEN_COLORS[gname], width=0.7,
                       edgecolor='white', linewidth=1, label=gname)
                ax.bar(range(len(periods)), v.clip(max=0), bottom=neg, color=GEN_COLORS[gname], width=0.7,
                       edgecolor='white', linewidth=1)
                pos, neg = pos + v.clip(min=0), neg + v.clip(max=0)
            ax.axhline(0, color=INK, lw=0.8)
        ax.set_xticks(range(len(periods)), [str(p) for p in periods], fontsize=7)
        ax.grid(axis='y', color='#e6e8eb', linewidth=0.6)
        ax.set_axisbelow(True)
    axes[0, 0].set_ylabel('Freight transport energy\n(TWh/yr)')
    axes[1, 0].set_ylabel('Grid generation vs\nICE-only run (TWh/yr)')
    h0, l0 = axes[0, 0].get_legend_handles_labels()
    fig.legend(h0, l0, frameon=False, loc='upper center', ncol=4, fontsize=7, bbox_to_anchor=(0.5, 1.03))
    h, l = axes[1, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc='lower center', ncol=7, fontsize=7, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    save(fig, f'R1_freight_transition{suffix}')

    # ---- R2: emissions, freight vs cars vs rest; annual (left) and cumulative (right) ----
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.8), gridspec_kw={'width_ratios': [1.15, 1]})
    for k, n in main_runs.items():
        c = fr.co2_by_sector(n)
        a1.plot(periods, c['Freight trucks'], marker='o', ms=4, lw=1.6, color=C[k.split('_')[0]], label=k.split('_')[0])
    ice = runs.get('F1_ice')
    if ice is not None:
        a1.plot(periods, fr.co2_by_sector(ice)['Freight trucks'], ls='--', lw=1.2, color=MUTED,
                label='F1, ICE only')
    a1.text(periods[1] + 1, 1.8, 'F1–F4 overlap', fontsize=7, color=MUTED)
    a1.set_ylabel('Freight truck CO$_2$ (Mt/yr)')
    a1.set_xticks(periods)
    a1.legend(frameon=False)
    a1.grid(axis='y', color='#e6e8eb', linewidth=0.6)
    cum = {}
    labelled = {k.split('_')[0]: n for k, n in main_runs.items()}
    for k, n in {**labelled, **({'F1 ICE only': ice} if ice is not None else {})}.items():
        c = fr.co2_by_sector(n)
        rest = c.sum(axis=1) - c['Freight trucks'] - c.get('Passenger cars', 0)
        cum[k] = {'Freight trucks': cumulative(c['Freight trucks'], n),
                  'Passenger cars': cumulative(c.get('Passenger cars', 0 * rest), n),
                  'Rest of system': cumulative(rest, n)}
    cum = pd.DataFrame(cum).T / 1e3
    bottom = 0
    for s in ['Freight trucks', 'Passenger cars', 'Rest of system']:
        a2.bar(range(len(cum)), cum[s], bottom=bottom, color=C[s], width=0.65, edgecolor='white',
               linewidth=1, label=s)
        bottom = bottom + cum[s].values
    a2.set_xticks(range(len(cum)), [x.replace(' ICE only', '\nICE only') for x in cum.index])
    a2.set_ylabel('Cumulative CO$_2$ 2020–2059 (Gt)')
    a2.legend(frameon=False, fontsize=7, loc='upper left')
    fig.tight_layout()
    save(fig, f'R2_emissions{suffix}')
    cum.round(3).to_csv(os.path.join(OUT, f'freight_cumulative_co2_Gt{suffix}.csv'))

    # ---- R3: cost of switching per period ----
    if sw:
        fig, ax = plt.subplots(figsize=(6.5, 2.6))
        w = 0.8 / len(sw)
        for i, (k, d) in enumerate(sw.items()):
            ax.bar([j + (i - (len(sw) - 1) / 2) * w for j in range(len(periods))],
                   d['Extra system cost (bn €/yr)'].values, width=w * 0.92, color=C[k],
                   label=f"{k}: {d['Abatement cost, horizon (€/t)'].iloc[0]:,.0f} €/t CO$_2$ over the horizon")
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_xticks(range(len(periods)), [str(p) for p in periods])
        ax.set_ylabel('System cost minus ICE-only (bn €/yr)')
        ax.legend(frameon=False, fontsize=7)
        ax.grid(axis='y', color='#e6e8eb', linewidth=0.6)
        ax.set_axisbelow(True)
        fig.tight_layout()
        save(fig, f'R3_cost_of_switching{suffix}')


def grid_shares(grid, xs, ys, sc='F1', xk='gasoline_price', yk='bet_vom_factor'):
    """Truck shares of every point of a sensitivity grid (results/runs_sens), per period."""
    tag = lambda v: str(v).replace('.', 'p').replace(' ', '')
    rows = []
    for xv in xs:
        for yv in ys:
            path = os.path.join('results', 'runs_sens', f'sens_{grid}_{sc}_{xk}{tag(xv)}_{yk}{tag(yv)}.nc')
            if not os.path.exists(path):
                continue
            s = fr.summary(pypsa.Network(path))
            for per in (2030, 2050):
                bet, fc = float(s.at[per, 'BET share of freight (%)']), float(s.at[per, 'FCET share of freight (%)'])
                hi = float(s.at[per, 'H2-ICE share of freight (%)']) if 'H2-ICE share of freight (%)' in s else 0.0
                rows.append(dict(fuel=xv, vom=yv, period=per, BET=bet, FCET=fc, **{'H2-ICE': hi},
                                 ICE=max(0.0, 100 - bet - fc - hi)))
    return pd.DataFrame(rows)


def tipping_figure():
    """R4: who serves freight at each fuel price and BET charging penalty, for three truck sets: the assignment's
    ICE trucks and BETs, plus hydrogen combustion trucks, plus fuel-cell trucks as well (the assignment's X/Y axes
    and the coordinator's higher-VOM variant). Cell colour = the largest truck type, darker = larger share."""
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch, Rectangle
    xs, ys = [70, 120, 200, 300], [1.0, 2.0, 3.0, 4.0]
    grids = [('bet_vom_x_gasoline_nofcet', 'ICE + BET\n(assignment)'),
             ('bet_vom_x_gasoline_h2ice', '+ H2-ICE truck'),
             ('bet_vom_x_gasoline', '+ H2-ICE + FCET\n(extension)')]
    kinds = ('BET', 'FCET', 'H2-ICE', 'ICE')
    colour = {'BET': C['BET'], 'FCET': C['FCET'], 'H2-ICE': C['H2-ICE truck'], 'ICE': C['ICE truck']}
    data = {g: grid_shares(g, xs, ys) for g, _ in grids}
    if all(d.empty for d in data.values()):
        return
    pd.concat(data, names=['grid', 'row']).round(1).to_csv(os.path.join(OUT, 'freight_tipping_point.csv'))
    fig, axes = plt.subplots(2, len(grids), figsize=(6.5, 4.9), sharex=True, sharey=True)
    for j, (g, title) in enumerate(grids):
        d = data[g]
        for i, per in enumerate((2030, 2050)):
            ax = axes[i, j]
            for yi, yv in enumerate(ys):
                for xi, xv in enumerate(xs):
                    r = d[(d.fuel == xv) & (d.vom == yv) & (d.period == per)] if not d.empty else d
                    if r.empty:
                        ax.add_patch(Rectangle((xi - 0.5, yi - 0.5), 1, 1, facecolor='#f4f5f6', edgecolor='white'))
                        ax.text(xi, yi, 'not run', ha='center', va='center', fontsize=6, color=MUTED)
                        continue
                    r = r.iloc[0]
                    win = max(kinds, key=lambda t: r.get(t, 0.0))
                    base = np.array(to_rgb(colour[win]))
                    a = 0.25 + 0.75 * r[win] / 100
                    ax.add_patch(Rectangle((xi - 0.5, yi - 0.5), 1, 1, facecolor=(1 - a) + a * base,
                                           edgecolor='white', linewidth=1.5))
                    txt = f"{win}\n{r[win]:.0f}%"
                    second = sorted(((r.get(t, 0.0), t) for t in kinds if t != win), reverse=True)[0]
                    if second[0] >= 5:
                        txt += f"\n{second[1]} {second[0]:.0f}%"
                    ax.text(xi, yi, txt, ha='center', va='center', fontsize=5.4, linespacing=1.15,
                            color='white' if a > 0.6 else INK)
            ax.add_patch(Rectangle((2 - 0.5, 0 - 0.5), 1, 1, fill=False, edgecolor=INK, linewidth=1.4))
            ax.set_xlim(-0.5, len(xs) - 0.5)
            ax.set_ylim(-0.5, len(ys) - 0.5)
            ax.set_xticks(range(len(xs)), [str(x) for x in xs])
            ax.set_yticks(range(len(ys)), [f'{0.1 * y:.2f}' for y in ys])
            ax.set_title(f'{title}, {per}' if i == 0 else f'{per}', fontsize=7.5, color=INK)
            for sp in ax.spines.values():
                sp.set_visible(False)
            ax.tick_params(length=0)
    for ax in axes[1, :]:
        ax.set_xlabel('Fuel price (€/MWh)')
    for ax in axes[:, 0]:
        ax.set_ylabel('BET charging penalty (€/kWh)')
    fig.legend(handles=[Patch(color=colour[k], label={'ICE': 'ICE truck', 'H2-ICE': 'H2-ICE truck'}.get(k, k))
                        for k in kinds] +
               [Patch(facecolor='white', edgecolor=INK, label='assignment values (0.10 €/kWh, ~200 €/MWh)')],
               frameon=False, loc='lower center', ncol=5, fontsize=6.5, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.05, 1, 1), w_pad=0.3)
    save(fig, 'R4_tipping_point')


# realistic layer: truck types with the BETs by duty cycle (ordinal blue ramp, validated: steps 650 / 450 / 250)
REAL_TYPES = [('ICE truck', '#8a8f98'), ('BET, long haul', '#104281'), ('BET, regional', '#2a78d6'),
              ('BET, urban', '#86b6ef'), ('FCET', '#1baf7a'), ('H2-ICE truck', '#6250d6')]


def fleet_by_type(n):
    """Freight transport energy per truck type, the BETs split by duty cycle (TWh/yr), per period."""
    out, bet = fr.freight_output(n), fr.bet_by_duty(n)
    return pd.DataFrame({'ICE truck': out['ICE truck'], 'BET, long haul': bet['long-haul'],
                         'BET, regional': bet['regional'], 'BET, urban': bet['urban'], 'FCET': out['FCET'],
                         'H2-ICE truck': out['H2-ICE truck']})


def real_name(k):
    """Base run of a realistic-layer run: 'F1_real_co2high' -> 'F1_real'; None for other runs."""
    f = k.split('_')[0]
    return f'{f}_real' if k.startswith(f'{f}_real') else None


def realistic_figures(runs):
    """R1-R3 for the realistic layer against the assignment core: fleet transition (core; realistic without policies;
    realistic under current truck and hydrogen policies), freight and cumulative CO2, and the cost of switching (with
    and without the toll and subsidy transfers)."""
    core = {f: runs.get(f'{f}_nofcet') for f in SCEN}
    nopol = {f: runs.get(f'{f}_real_nopolicy') for f in SCEN}
    real = {f: runs.get(f'{f}_real') for f in SCEN}
    if not any(v is not None for v in real.values()):
        return
    periods = list(next(v for v in real.values() if v is not None).investment_periods)

    # ---- R1: fleet transition: core (top), realistic without policies (middle), current policies (bottom) ----
    rows_ = [('Assignment core\n(ICE + BET)', core), ('Realistic,\nno policies', nopol),
             ('Realistic,\ncurrent policies', real)]
    rows_ = [r for r in rows_ if any(v is not None for v in r[1].values())]
    fig, axes = plt.subplots(len(rows_), len(SCEN), figsize=(6.5, 1.0 + 2.05 * len(rows_)), sharey=True, squeeze=False)
    for row, (lab, rset) in enumerate(rows_):
        for col, f in enumerate(SCEN):
            ax = axes[row, col]
            n = rset.get(f)
            if row == 0:
                ax.set_title(LABEL[f].replace(', ', ',\n'), fontsize=8, color=INK)
            if n is None:
                ax.text(0.5, 0.5, 'not run', ha='center', va='center', color=MUTED, fontsize=7, transform=ax.transAxes)
                ax.set_xticks([])
                continue
            d = fleet_by_type(n)
            bottom = np.zeros(len(periods))
            for t, colr in REAL_TYPES:
                v = d[t].reindex(periods).fillna(0).values
                ax.bar(range(len(periods)), v, bottom=bottom, color=colr, width=0.7, edgecolor='white', linewidth=1,
                       label=t)
                bottom = bottom + v
            ze = 100 * (1 - d['ICE truck'].reindex(periods).fillna(0).values / np.maximum(bottom, 1e-9))
            for j, (top, z) in enumerate(zip(bottom, ze)):     # zero-emission share above each bar (text ink)
                ax.text(j, top + 0.6, f'{z:.0f}%', ha='center', va='bottom', fontsize=6, color=MUTED)
            ax.set_xticks(range(len(periods)), [str(p) for p in periods], fontsize=7)
            ax.grid(axis='y', color='#e6e8eb', linewidth=0.6)
            ax.set_axisbelow(True)
        axes[row, 0].set_ylabel(f'{lab}\nfreight (TWh/yr)', fontsize=7.5)
        axes[row, 0].set_ylim(0, 40)
    h, l = axes[-1, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc='lower center', ncol=6, fontsize=6.5, bbox_to_anchor=(0.5, -0.005))
    fig.text(0.995, 0.045, 'Labels: zero-emission share of freight', ha='right', va='bottom', fontsize=6, color=MUTED)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, 'R1_fleet_transition_real')

    # ---- R2: freight CO2 per period (core, no policies, current policies, ICE only) and cumulative ----
    # Realistic paths that coincide (within 0.25 Mt/yr, less than a line width here) are drawn once with a combined
    # label: where the market ramp-up binds, the scenarios share one path with and without policies. One scenario keeps
    # its colour, a shared path is ink.
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 3.2), gridspec_kw={'width_ratios': [1.0, 1.15]})
    fco2 = lambda n: fr.co2_by_sector(n)['Freight trucks'].reindex(periods)

    def span(fs):
        """Scenario list as a label: ['F1', 'F2', 'F3', 'F4'] -> 'F1–F4', ['F1', 'F3'] -> 'F1, F3'."""
        i = [SCEN.index(f) for f in fs]
        return f'{fs[0]}–{fs[-1]}' if len(fs) > 2 and i == list(range(i[0], i[-1] + 1)) else ', '.join(fs)

    for f in ('F1', 'F4'):
        if core.get(f) is not None:
            a1.plot(periods, fco2(core[f]), ls='--', lw=1.0, marker='o', ms=3, color=C[f],
                    label=f'{f}, core (ICE + BET)')
    paths = []                                        # [path, scenarios with policies, scenarios without]
    for k, rset in ((1, real), (2, nopol)):
        for f, n in rset.items():
            if n is None:
                continue
            v = fco2(n)
            p = next((p for p in paths if float((p[0] - v).abs().max()) < 0.25), None)
            if p is None:
                p = [v, [], []]
                paths.append(p)
            p[k].append(f)
    for v, wp, wo in paths:
        col = C[(wp + wo)[0]] if len(wp + wo) == 1 else INK
        if wp:
            a1.plot(periods, v, ls='-', lw=1.8, marker='o', ms=3, color=col, label=f'{span(wp)}, current policies'
                    + (f'\n(≈ {span(wo)} without policies)' if wo else ''))
        else:
            a1.plot(periods, v, ls=':', lw=1.6, marker='o', ms=3, color=col, label=f'{span(wo)}, no policies')
    ice = runs.get('F1_real_ice')
    if ice is not None:
        a1.plot(periods, fco2(ice), ls='-.', lw=1.2, color=MUTED, label='F1, ICE trucks only')
    a1.set_ylabel('Freight truck CO$_2$ (Mt/yr)')
    a1.set_xticks(periods)
    a1.legend(frameon=False, fontsize=6, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)
    a1.grid(axis='y', color='#e6e8eb', linewidth=0.6)
    bars = {'F1\ncore': runs.get('F1_nofcet'), 'F1 no\npolicies': nopol.get('F1'),
            **{f'{f}\npolicies': real.get(f) for f in SCEN}, 'F1 ICE\nonly': ice}
    cum = {}
    for k, n in bars.items():
        if n is None:
            continue
        c = fr.co2_by_sector(n)
        rest = c.sum(axis=1) - c['Freight trucks'] - c.get('Passenger cars', 0)
        cum[k] = {'Freight trucks': cumulative(c['Freight trucks'], n),
                  'Passenger cars': cumulative(c.get('Passenger cars', 0 * rest), n),
                  'Rest of system': cumulative(rest, n)}
    cum = pd.DataFrame(cum).T / 1e3
    bottom = 0
    for sct in ['Freight trucks', 'Passenger cars', 'Rest of system']:
        a2.bar(range(len(cum)), cum[sct], bottom=bottom, color=C[sct], width=0.65, edgecolor='white', linewidth=1,
               label=sct)
        bottom = bottom + cum[sct].values
    a2.set_xticks(range(len(cum)), list(cum.index), fontsize=6)
    a2.set_ylabel('Cumulative CO$_2$ 2020–2059 (Gt)')
    a2.set_ylim(0, 1.22 * float(cum.sum(axis=1).max()))          # headroom for the legend above the bars
    a2.legend(frameon=False, fontsize=6.5, loc='upper left')
    fig.tight_layout()
    save(fig, 'R2_emissions_real')
    cum.round(3).to_csv(os.path.join(OUT, 'freight_cumulative_co2_Gt_real.csv'))

    # ---- R3: cost of switching per period, core (left) and current policies (right; system cost incl. the toll) ----
    def no_transfer_eur_t(a, b):
        """Abatement cost over the horizon (€/t) of run a against its ICE-only twin b, without toll and subsidies."""
        ta, tb = fr.policy_transfers(a), fr.policy_transfers(b)
        d = ta['System cost without transfers (bn €/yr)'] - tb['System cost without transfers (bn €/yr)']
        dco2 = fr.co2_by_sector(b).sum(axis=1) - fr.co2_by_sector(a).sum(axis=1)
        wobj, wyrs = a.investment_period_weightings['objective'], a.investment_period_weightings['years']
        return float((d * wobj).sum()) * 1e9 / (float((dco2 * wyrs).sum()) * 1e6)

    fig, axs = plt.subplots(1, 2, figsize=(6.5, 2.8), sharey=True)
    for ax, (title, rset, ice_of, real_) in zip(axs, (
            ('Assignment core (course prices)', core, lambda f: f'{f}_ice', False),
            ('Realistic, current policies (real prices)', real, lambda f: f'{f}_real_ice', True))):
        sw = {f: fr.switching_cost(rset[f], runs[ice_of(f)]) for f in SCEN
              if rset.get(f) is not None and runs.get(ice_of(f)) is not None}
        w = 0.8 / max(len(sw), 1)
        for i, (f, d) in enumerate(sw.items()):
            lab = f"{f}: {d['Abatement cost, horizon (€/t)'].iloc[0]:,.0f} €/t"
            if real_:
                lab += f" ({no_transfer_eur_t(rset[f], runs[ice_of(f)]):,.0f} without toll and subsidies)"
            ax.bar([j + (i - (len(sw) - 1) / 2) * w for j in range(len(periods))],
                   d['Extra system cost (bn €/yr)'].values, width=w * 0.92, color=C[f], label=lab)
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_xticks(range(len(periods)), [str(p) for p in periods])
        ax.set_title(title, fontsize=8, color=INK)
        ax.legend(frameon=False, fontsize=6, loc='lower left')
        ax.grid(axis='y', color='#e6e8eb', linewidth=0.6)
        ax.set_axisbelow(True)
    axs[0].set_ylabel('System cost minus ICE-only\n(bn €/yr)')
    fig.tight_layout()
    save(fig, 'R3_cost_of_switching_real')


def system_figures(runs):
    """System figures (S1-S5) for the freight study, built on the group's system plots (figures/plots/freight_system.py
    and system_plots.py): whole-system Sankeys with the freight trucks, final energy of the trucks by carrier, the
    energy balance of one run, hydrogen supply and use, and electricity generation."""
    from figures.plots import freight_system as fs
    from figures.plots import system_plots as sp
    pick = lambda pairs: {lab: runs[k] for lab, k in pairs if runs.get(k) is not None}
    sank = pick([('F1, course core (ICE + BET)', 'F1_nofcet'), ('F1, realistic under current policies', 'F1_real')])
    if len(sank) == 2:
        for per in (2030, 2050):
            save(fs.plot_sankey(sank, per, titles={k: f'{k}: energy system in {per} (TWh/yr, final energy)'
                                                   for k in sank}), f'S1_sankey_{per}')
    fe = pick([('F1 core', 'F1_nofcet'), ('F1 realistic,\nno policies', 'F1_real_nopolicy'),
               ('F1 realistic,\ncurrent policies', 'F1_real'), ('F4 realistic,\ncurrent policies', 'F4_real')])
    if fe:
        save(fs.plot_freight_energy(fe), 'S2_freight_final_energy')
    if runs.get('F1_real') is not None:
        save(fs.plot_energy_balance(runs['F1_real'], 'F1 realistic under current policies: final energy by sector '
                                                     'and carrier'), 'S3_energy_balance_F1_real')
    h2 = pick([('F1 core', 'F1_nofcet'), ('F1 realistic,\nno policies', 'F1_real_nopolicy'),
               ('F1 realistic,\ncurrent policies', 'F1_real'), ('F1 realistic,\nEU hydrogen targets', 'F1_real_h2eu'),
               ('F1 realistic, green\nH2 at the pump', 'F1_real_h2green')])
    if h2:
        save(fs.plot_hydrogen(h2), 'S4_hydrogen_supply')
    el = pick([('F1 core', 'F1_nofcet'), ('F1 realistic, current policies', 'F1_real'),
               ('F1 realistic, ICE trucks only', 'F1_real_ice')])
    if el:
        with plt.rc_context(fs.STYLE):
            save(sp.plot_electricity_supply(el), 'S5_electricity_supply')
    # tables behind the figures
    rows = []
    for lab, n in {**fe, **h2}.items():
        f_ = fs.final_energy(n)
        if 'Freight trucks' in f_.columns.get_level_values(0):
            t = f_['Freight trucks'].copy()
            t.columns = [f'Freight final energy, {c} (TWh/yr)' for c in t.columns]
            hu = fs.hydrogen_supply_use(n)
            t = t.join(hu.add_suffix(' (TWh H2/yr)'))
            t.insert(0, 'run', lab.replace('\n', ' '))
            rows.append(t)
    if rows:
        pd.concat(rows).round(2).to_csv(os.path.join(OUT, 'freight_system_energy.csv'))


# ---------------------------------------------------------------- heatmaps: sensitivities and policy levers
DIV = ('#2a78d6', '#f2f3f5', '#eb6834')     # diverging: below the base (blue), as the base (light grey), above (orange)


def _div_color(x):
    """Fill for a scaled change x in [-1, 1] against the base: blue below, orange above, light grey at 0."""
    from matplotlib.colors import to_rgb
    lo, mid, hi = (np.array(to_rgb(c)) for c in DIV)
    x = float(np.clip(x, -1.0, 1.0))
    return tuple(mid + (hi - mid) * x) if x >= 0 else tuple(mid + (lo - mid) * (-x))


def _heat(ax, vals, ref, fmt, scale, row_labels=None, col_labels=None, bold_rows=()):
    """Annotated heatmap. vals and ref: arrays rows x cols (NaN = not run); the fill shows (vals - ref) / scale
    (scale per column: an array, or one number), the text the value itself."""
    nr, nc = vals.shape
    scale = np.broadcast_to(np.asarray(scale, dtype=float), (nc,))
    for i in range(nr):
        for j in range(nc):
            v, r = vals[i, j], ref[i, j]
            if np.isnan(v):
                ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor='white', edgecolor='white', lw=1.5))
                ax.text(j + 0.5, i + 0.5, 'not run', ha='center', va='center', fontsize=5.2, color='#a0a6ad')
                continue
            x = 0.0 if np.isnan(r) or scale[j] <= 0 else (v - r) / scale[j]
            ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=_div_color(x), edgecolor='white', lw=1.5))
            ax.text(j + 0.5, i + 0.5, fmt[j](v) if callable(fmt[j]) else format(v, fmt[j]), ha='center',
                    va='center', fontsize=6.2, color='white' if abs(x) > 0.62 else INK)
    ax.set_xlim(0, nc), ax.set_ylim(nr, 0)
    ax.tick_params(length=0)
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
    ax.set_yticks(np.arange(nr) + 0.5, row_labels if row_labels is not None else [''] * nr, fontsize=6.5)
    for i in bold_rows:
        ax.get_yticklabels()[i].set_fontweight('bold')
    ax.xaxis.tick_top()
    ax.set_xticks(np.arange(nc) + 0.5, col_labels if col_labels is not None else [''] * nc, fontsize=6.3)


def _metrics(n, fsys):
    """Indicators of one run for the heatmaps (dict)."""
    s = fr.summary(n)
    c = fr.co2_by_sector(n)
    hu = fsys.hydrogen_supply_use(n)
    routes = [r for r in hu.columns if not r.startswith('Use')]
    green = hu[[r for r in routes if r.startswith(('Green', 'Pure green'))]].sum(axis=1)
    tot = hu[routes].sum(axis=1)
    g = lambda col, y: float(s.at[y, col]) if col in s.columns else 0.0
    return {'ze2030': g('ZE share of freight (%)', 2030), 'ze2040': g('ZE share of freight (%)', 2040),
            'h2trucks2050': g('FCET share of freight (%)', 2050) + g('H2-ICE share of freight (%)', 2050),
            'bet2050': g('BET capacity (GW)', 2050),
            'green2050': 100 * float(green[2050] / tot[2050]) if tot[2050] > 0 else 0.0,
            'co2fr': cumulative(c['Freight trucks'], n), 'co2sys': cumulative(c.sum(axis=1), n) / 1e3,
            'cost': n.objective / 1e9}


def sensitivity_figure(runs):
    """R5: the assignment's sensitivities (carbon price, time restrictions) for F1 and F4, in the core (ICE + BET)
    and in the realistic layer, as heatmaps: one panel per indicator, colour = change against the base run."""
    from figures.plots import freight_system as fsys
    rows = [('Base run', ''), ('CO$_2$ price central', '_co2central'), ('CO$_2$ price high', '_co2high'),
            ('Sunday ban', '_sunday_ban'), ('Night ban', '_night_ban')]
    cols = [('F1\ncore', lambda t: f'F1{t}_nofcet'), ('F4\ncore', lambda t: f'F4{t}_nofcet'),
            ('F1\nrealistic', lambda t: f'F1_real{t}'), ('F4\nrealistic', lambda t: f'F4_real{t}')]
    if all(runs.get(name('')) is None for _, name in cols):
        return
    m = {}
    for j, (_, name) in enumerate(cols):
        for i, (_, tag) in enumerate(rows):
            n = runs.get(name(tag))
            if n is not None:
                m[i, j] = _metrics(n, fsys)
    panels = [('ze2030', 'Zero-emission share 2030 (%)', '.1f'), ('ze2040', 'Zero-emission share 2040 (%)', '.1f'),
              ('bet2050', 'BET capacity 2050 (GW)', '.1f'), ('co2fr', 'Freight CO$_2$ 2020–2059 (Mt)', '.0f'),
              ('co2sys', 'System CO$_2$ 2020–2059 (Gt)', '.2f'),
              ('cost', 'System cost vs base run\n(bn €, discounted 2020–2059)', '+.1f')]
    fig, axes = plt.subplots(2, 3, figsize=(6.5, 4.3))
    table = []
    for k, (key, title, fmt) in enumerate(panels):
        ax = axes.flat[k]
        vals = np.full((len(rows), len(cols)), np.nan)
        ref = np.full_like(vals, np.nan)
        for (i, j), d in m.items():
            vals[i, j] = d[key]
            table.append({'indicator': title.replace('\n', ' ').replace('$_2$', '2'),
                          'set': cols[j][0].replace('\n', ' '), 'run': cols[j][1](rows[i][1]), 'value': d[key]})
        for j in range(len(cols)):
            ref[:, j] = vals[0, j]
        base_mag = np.nanmax(np.abs(ref)) if np.isfinite(ref).any() else 1.0
        if key == 'cost':                                           # show the change against the base run
            vals, ref = vals - ref, np.zeros_like(vals)
        d = np.abs(vals - ref)
        # colour scale: the largest change in the panel, at least 5% of the base value (small changes stay pale)
        scale = max(np.nanmax(d) if np.isfinite(d).any() else 0.0, 0.05 * base_mag, 1e-9)
        _heat(ax, vals, ref, [fmt] * len(cols), scale, [r[0] for r in rows] if k % 3 == 0 else None,
              [c[0] for c in cols], bold_rows=(0,) if k % 3 == 0 else ())
        ax.set_title(title, fontsize=7, color=INK, pad=16, loc='left')
    fig.text(0.01, 0.005, 'Colour: change against the base run of the same column (blue lower, orange higher; '
             'scaled per panel).', fontsize=6, color=MUTED)
    fig.tight_layout(rect=(0, 0.025, 1, 1), h_pad=1.2, w_pad=0.6)
    save(fig, 'R5_sensitivities')
    pd.DataFrame(table).round(3).to_csv(os.path.join(OUT, 'freight_sensitivity_heatmap.csv'), index=False)


LEVERS = {'F1': [('Current policies (F1_real)', 'F1_real'), ('No truck or hydrogen policies', 'F1_real_nopolicy'),
                 ('ICE + BET only (no H$_2$ trucks)', 'F1_real_noh2'), ('EU hydrogen targets in full', 'F1_real_h2eu'),
                 ('Renewable H$_2$ at the pump', 'F1_real_h2green'),
                 ('H$_2$ production subsidy €1/kg', 'F1_real_h2subsidy'),
                 ('Net zero + renewable H$_2$ at the pump', 'F1_real_netzero'),
                 ('No ramp-up or H$_2$-truck limits', 'F1_real_nolimit'),
                 ('No heavy special segment', 'F1_real_noheavy'),
                 ('Water-scarcity driver', 'F1_real_water')],
          'F4': [('Current policies (F4_real)', 'F4_real'), ('No truck or hydrogen policies', 'F4_real_nopolicy'),
                 ('ICE + BET only (no H$_2$ trucks)', 'F4_real_noh2'), ('EU hydrogen targets in full', 'F4_real_h2eu'),
                 ('Net zero + renewable H$_2$ at the pump', 'F4_real_netzero'),
                 ('No ramp-up or H$_2$-truck limits', 'F4_real_nolimit'), ('Water-scarcity driver', 'F4_real_water')]}


def lever_figure(runs):
    """R6: policy and market levers in the realistic layer (F1 and F4), one row per lever and one column per
    indicator; colour = change against current policies (scaled per indicator)."""
    from figures.plots import freight_system as fsys
    if runs.get('F1_real') is None and runs.get('F4_real') is None:
        return
    cols = [('ze2030', 'Zero-\nemission\n2030 (%)', '.0f'), ('ze2040', 'Zero-\nemission\n2040 (%)', '.0f'),
            ('h2trucks2050', 'H$_2$ trucks\n2050 (%)', '.0f'), ('green2050', 'Green H$_2$\nshare\n2050 (%)', '.0f'),
            ('co2fr', 'Freight\nCO$_2$ 2020–\n2059 (Mt)', '.0f'),
            ('co2sys', 'System\nCO$_2$ 2020–\n2059 (Gt)', '.2f'),
            ('cost', 'Cost vs\ncurrent\npolicies\n(bn €)', '+.1f')]
    blocks = {f: rows for f, rows in LEVERS.items() if runs.get(rows[0][1]) is not None}
    fig, axes = plt.subplots(len(blocks), 1, figsize=(6.5, 0.9 + 0.235 * sum(len(r) for r in blocks.values())),
                             gridspec_kw={'height_ratios': [len(r) for r in blocks.values()]}, squeeze=False)
    table = []
    vals_all = {}
    for f, rows in blocks.items():
        v = np.full((len(rows), len(cols)), np.nan)
        for i, (lab, k) in enumerate(rows):
            n = runs.get(k)
            if n is None:
                continue
            d = _metrics(n, fsys)
            for j, (key, _, _) in enumerate(cols):
                v[i, j] = d[key]
            table.append({'scenario': f, 'lever': lab.replace('$_2$', '2'), 'run': k,
                          **{c[1].replace('\n', ' ').replace('$_2$', '2'): d[c[0]] for c in cols}})
        v[:, -1] = v[:, -1] - v[0, -1]                              # cost: change against current policies
        vals_all[f] = v
    # one colour scale per indicator over both blocks
    dev = np.vstack([np.abs(v - np.where(np.arange(len(cols)) == len(cols) - 1, 0.0, v[0])) for v in vals_all.values()])
    # colour scale per indicator: the largest change, at least 5% of the base value (small changes stay pale)
    floor = 0.05 * np.nanmax(np.vstack([np.abs(v[0]) for v in vals_all.values()]), axis=0)
    floor[-1] = 0.05 * max(runs[rows[0][1]].objective for rows in blocks.values()) / 1e9
    scale = np.maximum(np.nan_to_num(np.nanmax(dev, axis=0)), np.maximum(floor, 1e-9))
    for ax, (f, rows) in zip(axes[:, 0], blocks.items()):
        v = vals_all[f]
        ref = np.tile(v[0], (len(rows), 1))
        ref[:, -1] = 0.0
        _heat(ax, v, ref, [c[2] for c in cols], scale, [r[0] for r in rows],
              [c[1] for c in cols] if ax is axes[0, 0] else None, bold_rows=(0,))
        ax.set_ylabel(LABEL[f].replace(', ', ',\n'), fontsize=7, color=INK, labelpad=6)
    fig.text(0.01, 0.003, 'Colour: change against current policies (blue lower, orange higher; scaled per column). '
             'Not run = not on disk.', fontsize=6, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1), h_pad=0.8)
    save(fig, 'R6_policy_levers')
    pd.DataFrame(table).round(3).to_csv(os.path.join(OUT, 'freight_policy_levers.csv'), index=False)


def transition_speed_figure(runs):
    """R7: the speed of the transition. Left: zero-emission share of freight per period in the core, the realistic
    layer without policies and under current policies, inside the corridor of the realistic layer (EU CO2-standards
    floor, market ramp-up ceiling). Right: what a faster ramp-up would be worth (shadow price of the ceiling)."""
    from energy_model.freight_presets import ZE_MANDATES
    core = {f: runs.get(f'{f}_nofcet') for f in SCEN}
    real = {f: runs.get(f'{f}_real') for f in SCEN}
    nopol = {f: runs.get(f'{f}_real_nopolicy') for f in SCEN}
    if not any(v is not None for v in real.values()):
        return
    n0 = next(v for v in real.values() if v is not None)
    periods = list(n0.investment_periods)
    ze = lambda n: fr.summary(n)['ZE share of freight (%)'].reindex(periods)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9), gridspec_kw={'width_ratios': [1.25, 1]})
    floor, ceil = ZE_MANDATES['eu_hdv_fleet'], ZE_MANDATES['market']
    yrs = [y for y in periods if y >= 2030]
    a1.fill_between(yrs, [100 * floor.get(y, 0) for y in yrs], [100 * ceil.get(y, 1.0) for y in yrs], color='#e3effa',
                    lw=0, label='corridor of the realistic layer:\nCO$_2$-standards floor to ramp-up ceiling')
    for f in ('F1', 'F4'):                         # the core runs lie close together: F2 and F3 lie in between
        if core.get(f) is not None:
            a1.plot(periods, ze(core[f]), ls='--', lw=1.0, marker='o', ms=2.5, color=C[f],
                    label=f'{f}, core' + (' (F2, F3 in between)' if f == 'F4' else ''))
    paths = []                                     # realistic paths, merged where they coincide (as in R2_real)
    for k, rset in ((1, real), (2, nopol)):
        for f, n in rset.items():
            if n is None:
                continue
            v = ze(n)
            p = next((p for p in paths if float((p[0] - v).abs().max()) < 0.5), None)
            if p is None:
                p = [v, [], []]
                paths.append(p)
            p[k].append(f)
    span = lambda fs: f'{fs[0]}–{fs[-1]}' if len(fs) > 2 else ', '.join(fs)
    for v, wp, wo in paths:
        col = C[(wp + wo)[0]] if len(wp + wo) == 1 else INK
        if wp:
            a1.plot(periods, v, ls='-', lw=1.8, marker='o', ms=3, color=col, label=f'{span(wp)}, current policies'
                    + (f'\n(≈ {span(wo)} without policies)' if wo else ''))
        else:
            a1.plot(periods, v, ls=':', lw=1.6, marker='o', ms=3, color=col, label=f'{span(wo)}, no policies')
    a1.set_xticks(periods)
    a1.set_ylim(0, 105)
    a1.set_ylabel('Zero-emission share of freight (%)')
    a1.grid(axis='y', color='#e6e8eb', linewidth=0.6)
    a1.set_axisbelow(True)
    a1.legend(frameon=False, fontsize=5.8, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)
    # right: shadow price of the ramp-up ceiling (per year of the period), current policies vs no policies
    col_sp = 'ZE diffusion limit / market ramp-up (€/MWh)'
    rows = {}
    for tag, rset in (('current policies', real), ('no policies', nopol)):
        for f, n in rset.items():
            if n is None:
                continue
            sp_ = fr.shadow_prices(n)
            if col_sp in sp_.columns:
                rows[(f, tag)] = sp_[col_sp].reindex([2030, 2040]).fillna(0.0)
    if rows:
        t = pd.DataFrame(rows).T
        x = np.arange(len(SCEN))
        w = 0.2
        shades = {('current policies', 2030): '#104281', ('current policies', 2040): '#2a78d6',
                  ('no policies', 2030): '#86b6ef', ('no policies', 2040): '#c9ddf6'}
        for i, (tag, y) in enumerate(shades):
            vals = [float(t.loc[(f, tag), y]) if (f, tag) in t.index else np.nan for f in SCEN]
            a2.bar(x + (i - 1.5) * w, vals, w * 0.92, color=shades[(tag, y)], edgecolor='white', lw=0.6,
                   label=f'{y}s, {tag}')
        a2.set_xticks(x, SCEN)
        a2.set_ylabel('Value of a faster ramp-up\n(shadow price, €/MWh of freight)')
        a2.grid(axis='y', color='#e6e8eb', linewidth=0.6)
        a2.set_axisbelow(True)
        a2.legend(frameon=False, fontsize=5.8, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)
        t.round(1).to_csv(os.path.join(OUT, 'freight_rampup_shadow_price.csv'))
    a1.set_title('Speed of the transition', fontsize=7.5, color=INK, loc='left')
    a2.set_title('What binds: the market ramp-up', fontsize=7.5, color=INK, loc='left')
    fig.tight_layout(w_pad=1.6)
    save(fig, 'R7_transition_speed')


def water_driver_figure(runs):
    """A_water_driver: the water-scarcity driver (verdringingsreeks droughts that tighten over time, desalination as
    the backstop): freshwater use in the drought season against the quotas, and what it costs; table
    freight_water_driver.csv."""
    pairs = [(k, base) for k, base in (('F1_real_water', 'F1_real'), ('F4_real_water', 'F4_real'),
                                       ('F1_real_water_ely4', 'F1_real')) if runs.get(k) is not None]
    if not pairs:
        return
    rows = []
    for k, base in pairs:
        n, b = runs[k], runs.get(base)
        dt = fr.drought_table(n)
        s = fr.summary(n)
        sb = fr.summary(b) if b is not None else None
        for y in (2030, 2040, 2050):
            r = {'run': k, 'period': y}
            if dt is not None and y in dt.index:
                r.update({c: float(dt.at[y, c]) for c in dt.columns})
            alt_cost = float((n.meta.get('water') or {}).get('alt_cost') or 0.0)          # €/m3
            r['Alternative water bill (M€/yr)'] = alt_cost * float(r.get('Alternative water (Mm3)', 0.0) or 0.0)
            dsys = (1e3 * (float(s.at[y, 'System cost (bn €/yr)']) - float(sb.at[y, 'System cost (bn €/yr)']))
                    if sb is not None else np.nan)
            r['System cost vs no water limit (M€/yr)'] = dsys + r['Alternative water bill (M€/yr)']
            for col in ('FCET share of freight (%)', 'ZE share of freight (%)', 'Freshwater use (Mm3/yr)'):
                r[col] = float(s.at[y, col])
            rows.append(r)
    t = pd.DataFrame(rows).set_index(['run', 'period'])
    t.round(3).to_csv(os.path.join(OUT, 'freight_water_driver.csv'))
    horizon = {k: (runs[k].objective - runs[b].objective) / 1e9 for k, b in pairs if runs.get(b) is not None}
    lab = {'F1_real_water': 'F1', 'F4_real_water': 'F4', 'F1_real_water_ely4': 'F1, electrolysis last'}
    lab = {k: v + (f' (+€{horizon[k]:.2f} bn)' if k in horizon else '') for k, v in lab.items()}
    colr = {'F1_real_water': C['F1'], 'F4_real_water': C['F4'], 'F1_real_water_ely4': '#86b6ef'}
    periods = [2030, 2040, 2050]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.8), gridspec_kw={'width_ratios': [1.35, 1]})
    w = 0.8 / len(pairs)
    for i, (k, _) in enumerate(pairs):
        x = np.arange(len(periods)) + (i - (len(pairs) - 1) / 2) * w
        use = np.array([sum(t.loc[(k, y)].get(f'Use cat {c} (Mm3)', 0.0) for c in (2, 3, 4)) for y in periods])
        alt = np.array([t.loc[(k, y)].get('Alternative water (Mm3)', 0.0) for y in periods])
        alt = np.nan_to_num(alt)
        a1.bar(x, use - alt, w * 0.9, color=colr[k], edgecolor='white', lw=0.8, label=lab[k])
        a1.bar(x, alt, w * 0.9, bottom=use - alt, color='white', edgecolor=colr[k], hatch='////', lw=0.8)
        a2.bar(x, t.loc[[(k, y) for y in periods], 'System cost vs no water limit (M€/yr)'].values, w * 0.9,
               color=colr[k], edgecolor='white', lw=0.8, label=lab[k])
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=colr[k], edgecolor='white', label=lab[k]) for k, _ in pairs]
    handles.append(Patch(facecolor='white', edgecolor=MUTED, hatch='////',
                         label='above the quota:\ndesalinated or reused'))
    for ax in (a1, a2):
        ax.set_xticks(range(len(periods)), [str(p) for p in periods])
        ax.grid(axis='y', color='#e6e8eb', linewidth=0.6)
        ax.set_axisbelow(True)
    a1.set_ylabel('Freshwater use, June–September (Mm$^3$)')
    a1.legend(handles=handles, frameon=False, fontsize=6.0, loc='upper left')
    a2.axhline(0, color=INK, lw=0.8)
    a2.set_ylabel('System cost incl. the water bill,\nvs no water limits (M€/yr)')
    a1.set_title('Drought season under the verdringingsreeks', fontsize=7.5, color=INK, loc='left')
    a2.set_title('Cost of the water-scarcity driver\n(legend: discounted total 2020–2059)', fontsize=7.5, color=INK,
                 loc='left')
    fig.tight_layout()
    save(fig, 'A_water_driver')


def main():
    """Load every freight run on disk, draw all figures and write all tables (see the module docstring)."""
    from run_freight import RUNS as REGISTRY
    runs = {k: load(k) for k in REGISTRY if os.path.exists(os.path.join(RUNS, f'{k}.nc'))}
    os.makedirs(OUT, exist_ok=True)
    allsum = fr.compare(runs)
    allsum.to_csv(os.path.join(OUT, 'freight_summary.csv'))
    main_runs = {k: runs[k] for k in SCEN if k in runs}
    lines = ['# Freight study: key numbers (from the saved runs)\n']

    # ---- calibration and tests (assignment step 5): the base year in all four scenarios (core) and the tests of
    #      run_freight.TESTS against their base run ----
    from run_freight import TESTS
    rows = []
    for k in SCEN_CORE + list(TESTS):
        n = runs.get(k)
        if n is None:
            continue
        base = k.split('_')[0] + ('_nofcet' if k.endswith('_nofcet') else '')
        s = fr.summary(n)
        b = runs.get(base)
        rows.append({'run': k, 'test': 'base year' if k in SCEN_CORE else k.split('_', 1)[1].replace('_nofcet', ''),
                     'Freight 2020 (PJ, truck output)': s.at[2020, 'Freight demand (TWh/yr)'] * 3.6,
                     'Truck fuel 2020 (PJ)': (s.at[2020, 'Gasoline for trucks (TWh/yr)']
                                              + s.at[2020, 'Electricity for trucks (TWh/yr)']) * 3.6,
                     'BET share 2020 (%)': s.at[2020, 'BET share of freight (%)'],
                     'CO2 freight trucks 2020 (Mt)': s.at[2020, 'CO2 freight trucks (Mt/yr)'],
                     'ZE share 2030 (%)': s.at[2030, 'ZE share of freight (%)'],
                     'ZE share 2050 (%)': s.at[2050, 'ZE share of freight (%)'],
                     'CO2 freight trucks 2030 (Mt)': s.at[2030, 'CO2 freight trucks (Mt/yr)'],
                     'Total cost vs base run (%)': 0.0 if k == base or b is None
                     else 100 * (n.objective / b.objective - 1)})
    if rows:
        ct = pd.DataFrame(rows).set_index(['run', 'test']).round(2)
        ct.to_csv(os.path.join(OUT, 'freight_calibration_tests.csv'))
        lines += ['## Calibration and tests (assignment step 5)\n',
                  'Observed CO2 of heavy trucks: 5.1 Mt (2014; CE Delft, 2021). Base run of a test: the same scenario '
                  'without the test (F1_tres6: F1).\n', ct.round(1).to_markdown(), '']

    # ---- main scenarios per period ----
    cols = ['ZE share of freight (%)', 'BET share of freight (%)', 'FCET share of freight (%)',
            'H2-ICE share of freight (%)', 'CO2 freight trucks (Mt/yr)', 'CO2 passenger cars (Mt/yr)',
            'CO2 total (Mt/yr)',
            'Electricity for trucks (TWh/yr)', 'Electricity price, mean (€/MWh)', 'System cost (bn €/yr)']
    core_runs = {k: runs[k] for k in SCEN_CORE if k in runs}
    if core_runs:
        t = allsum.loc[list(core_runs)][[c for c in cols if c in allsum.columns and 'FCET' not in c
                                         and 'H2-ICE' not in c]].round(1)
        lines += ['## Assignment core: ICE trucks and BETs only (F1-F4_nofcet)\n', t.to_markdown(), '']
    if main_runs:
        t = allsum.loc[list(main_runs)][[c for c in cols if c in allsum.columns]].round(1)
        lines += ['## Hydrogen extension: F1-F4 with fuel-cell and hydrogen combustion trucks\n', t.to_markdown(), '']

    # ---- realistic layer: F1-F4 with all four truck types (and ICE + BET only), BETs by duty cycle ----
    rrows = []
    for f in SCEN:
        for tag, k in (('core (ICE + BET, course set-up)', f'{f}_nofcet'), ('realistic, ICE + BET', f'{f}_real_noh2'),
                       ('realistic, all four types', f'{f}_real')):
            n = runs.get(k)
            if n is None:
                continue
            s = fr.summary(n)
            d = fleet_by_type(n)
            tot = d.sum(axis=1)
            for y in (2030, 2040, 2050):
                rr = {'scenario': f, 'set': tag, 'period': y}
                rr.update({f'{t} (%)': 100 * float(d.at[y, t] / tot[y]) for t, _ in REAL_TYPES})
                rr['CO2 freight (Mt/yr)'] = float(s.at[y, 'CO2 freight trucks (Mt/yr)'])
                rr['CO2 total (Mt/yr)'] = float(s.at[y, 'CO2 total (Mt/yr)'])
                rr['Total cost 2020-2059 (bn €)'] = n.objective / 1e9
                rrows.append(rr)
    if rrows:
        rt = pd.DataFrame(rrows).set_index(['scenario', 'set', 'period'])
        rt.round(2).to_csv(os.path.join(OUT, 'freight_realistic.csv'))
        lines += ['## Realistic layer: truck mix per period (shares of freight energy)\n',
                  rt.round(1).to_markdown(), '']
        swr = {f: fr.switching_cost(runs[f'{f}_real'], runs[f'{f}_real_ice']) for f in SCEN
               if runs.get(f'{f}_real') is not None and runs.get(f'{f}_real_ice') is not None}
        if swr:
            swrt = pd.concat(swr).round(2)
            swrt.to_csv(os.path.join(OUT, 'freight_switching_cost_real.csv'))
            lines += ['## Cost of switching, realistic layer (run minus ICE-only at the same prices)\n',
                      swrt.to_markdown(), '']
        # policy transfers (toll paid, AanZET subsidy) and the cost without them, per run and period; horizon totals
        # discounted like the objective (bn €)
        trs, tot = {}, {}
        for f in SCEN:
            for tag in ('_real', '_real_noh2', '_real_ice', '_real_nopolicy'):
                n = runs.get(f + tag)
                if n is None:
                    continue
                t = fr.policy_transfers(n)
                trs[f + tag] = t
                wobj = n.investment_period_weightings['objective']
                tot[f + tag] = (t.mul(wobj, axis=0)).sum()
        if trs:
            trt = pd.concat(trs, names=['run', 'period']).round(2)
            trt.to_csv(os.path.join(OUT, 'freight_policy_transfers.csv'))
            tott = pd.DataFrame(tot).T.round(1)
            tott.columns = [c.replace('(bn €/yr)', '(bn €, discounted 2020-2059)') for c in tott.columns]
            tott.to_csv(os.path.join(OUT, 'freight_policy_transfers_horizon.csv'))
            lines += ['## Policy transfers, realistic layer (toll in the system cost, subsidies left out)\n',
                      trt.to_markdown(), '', '### Horizon totals, discounted like the objective\n',
                      tott.to_markdown(), '']
            rows = []
            for f in SCEN:
                a_, b_ = f + '_real', f + '_real_ice'
                if a_ in trs and b_ in trs:
                    d = (trs[a_]['System cost without transfers (bn €/yr)']
                         - trs[b_]['System cost without transfers (bn €/yr)'])
                    dco2 = fr.co2_by_sector(runs[b_]).sum(axis=1) - fr.co2_by_sector(runs[a_]).sum(axis=1)
                    n = runs[a_]
                    wobj, wyrs = n.investment_period_weightings['objective'], n.investment_period_weightings['years']
                    rows.append({'scenario': f, 'Saving without transfers, horizon (bn €)': -float((d * wobj).sum()),
                                 'Abatement cost without transfers (€/t)': float((d * wobj).sum()) * 1e9
                                 / (float((dco2 * wyrs).sum()) * 1e6)})
            if rows:
                swx = pd.DataFrame(rows).set_index('scenario').round(1)
                swx.to_csv(os.path.join(OUT, 'freight_switching_cost_real_no_transfers.csv'))
                lines += ['## Cost of switching without the toll and subsidy transfers (realistic layer)\n',
                          swx.to_markdown(), '']
        # green hydrogen for the trucks: renewable hydrogen at the pump, a production subsidy and net zero, against the
        # realistic run of the same scenario under current policies
        gtests = [('current policies', 'F1_real'), ('EU hydrogen targets', 'F1_real_h2eu'),
                  ('green H2 at the pump', 'F1_real_h2green'), ('H2 production subsidy €1/kg', 'F1_real_h2subsidy'),
                  ('net zero + green H2 at the pump', 'F1_real_netzero'), ('F3 current policies', 'F3_real'),
                  ('F3 green H2 at the pump', 'F3_real_h2green'), ('F4 current policies', 'F4_real'),
                  ('F4 net zero + green H2 at the pump', 'F4_real_netzero')]
        from figures.plots import freight_system as fsys
        rows = []
        for lab, k in gtests:
            n = runs.get(k)
            if n is None:
                continue
            d = fleet_by_type(n)
            tot = d.sum(axis=1)
            hu = fsys.hydrogen_supply_use(n)
            c = fr.co2_by_sector(n)
            sp_ = fr.shadow_prices(n)
            base = runs.get(k.split('_')[0] + '_real')
            for y in (2030, 2040, 2050):
                green = float(hu.loc[y, [r for r in hu.columns if r.startswith(('Green', 'Pure green'))]].sum())
                rows.append({'run': k, 'test': lab, 'period': y,
                             'FCET (%)': 100 * float(d.at[y, 'FCET'] / tot[y]),
                             'H2-ICE (%)': 100 * float(d.at[y, 'H2-ICE truck'] / tot[y]),
                             'BET long haul (%)': 100 * float(d.at[y, 'BET, long haul'] / tot[y]),
                             'H2 used by trucks (TWh/yr)': float(hu.at[y, 'Use: freight trucks']),
                             'Green H2 (TWh/yr)': green,
                             'Blue H2 (TWh/yr)': float(hu.at[y, 'Blue (SMR + CCS)']),
                             'Grey H2 (TWh/yr)': float(hu.at[y, 'Grey (SMR)']),
                             'CO2 total (Mt/yr)': float(c.sum(axis=1)[y]),
                             'Green H2 at the pump, shadow price (€/kg)':
                                 float(sp_['Renewable hydrogen for trucks (€/kg)'].get(y, np.nan))
                                 if 'Renewable hydrogen for trucks (€/kg)' in sp_ else np.nan,
                             'Total cost vs base (bn €, 2020-2059)': (n.objective - base.objective) / 1e9
                             if base is not None else np.nan})
        if rows:
            gt = pd.DataFrame(rows).set_index(['run', 'test', 'period']).round(2)
            gt.to_csv(os.path.join(OUT, 'freight_green_hydrogen_tests.csv'))
            lines += ['## Green hydrogen for the trucks (realistic layer)\n', gt.to_markdown(), '']

        # policy effect: current truck and hydrogen policies vs the frictions and real prices alone
        rows = []
        for f in SCEN:
            for tag, k in (('no policies', f'{f}_real_nopolicy'), ('current policies', f'{f}_real')):
                n = runs.get(k)
                if n is None or runs.get(f'{f}_real_nopolicy') is None:
                    continue
                d = fleet_by_type(n)
                tot = d.sum(axis=1)
                c = fr.co2_by_sector(n)
                t = trs.get(k) if trs else None
                wobj = n.investment_period_weightings['objective']
                bets = [x for x in d.columns if x.startswith('BET')]
                no_tr = float((t['System cost without transfers (bn €/yr)'] * wobj).sum()) if t is not None else None
                for y in (2030, 2040, 2050):
                    rows.append({'scenario': f, 'policies': tag, 'period': y,
                                 'ICE (%)': 100 * float(d.at[y, 'ICE truck'] / tot[y]),
                                 'BET (%)': 100 * float(d.loc[y, bets].sum() / tot[y]),
                                 'FCET (%)': 100 * float(d.at[y, 'FCET'] / tot[y]),
                                 'H2-ICE (%)': 100 * float(d.at[y, 'H2-ICE truck'] / tot[y]),
                                 'CO2 freight (Mt/yr)': float(c.at[y, 'Freight trucks']),
                                 'CO2 total (Mt/yr)': float(c.sum(axis=1)[y]),
                                 'Cumulative CO2 freight 2020-2059 (Mt)': cumulative(c['Freight trucks'], n),
                                 'Toll paid (bn €/yr)':
                                     float(t.loc[y].filter(like='Toll').sum()) if t is not None else None,
                                 'Subsidies: AanZET, SWiM, OWE (bn €/yr)':
                                     float(t.loc[y].filter(like='subsidy').sum()) if t is not None else None,
                                 'Cost without transfers, horizon (bn €)': no_tr})
        if rows:
            pe = pd.DataFrame(rows).set_index(['scenario', 'policies', 'period']).round(2)
            pe.to_csv(os.path.join(OUT, 'freight_policy_effect.csv'))
            lines += ['## Policy effect, realistic layer (frictions and real prices alone vs current policies)\n',
                      pe.to_markdown(), '']

    # ---- truck sets: the core (ICE + BET) and the extension (+ H2-ICE + FCET); H2-ICE alone is in the R4 grid ----
    rows = []
    for base in SCEN:
        core = runs.get(f'{base}_nofcet')
        for tag, k in (('ICE + BET', f'{base}_nofcet'), ('+ H2-ICE + FCET', base)):
            n = runs.get(k)
            if n is None:
                continue
            s = fr.summary(n)
            cap = fr.freight_capacity(n)
            row = {'scenario': base, 'trucks': tag, 'run': k,
                   'cost vs core (bn €, horizon)': None if core is None else (n.objective - core.objective) / 1e9}
            for y in (2030, 2050):
                for col, lab in (('BET share of freight (%)', 'BET'), ('FCET share of freight (%)', 'FCET'),
                                 ('H2-ICE share of freight (%)', 'H2-ICE'), ('ICE share of freight (%)', 'ICE')):
                    row[f'{lab} {y} (%)'] = float(s.at[y, col]) if col in s.columns else 0.0
                row[f'H2-ICE capacity {y} (GW)'] = float(cap.at[y, 'H2-ICE truck']) if 'H2-ICE truck' in cap else 0.0
                row[f'CO2 total {y} (Mt)'] = float(s.at[y, 'CO2 total (Mt/yr)'])
            rows.append(row)
    if rows:
        ts = pd.DataFrame(rows).set_index(['scenario', 'trucks'])
        ts.round(3).to_csv(os.path.join(OUT, 'freight_truck_sets.csv'))
        lines += ['## Truck sets: ICE + BET (core) and + H2-ICE + FCET (extension); H2-ICE without FCETs: grid R4\n',
                  ts.drop(columns='run').round(2).to_markdown(), '']

    # ---- relative change in total discounted system cost (objective) vs F1 ----
    if 'F1' in runs:
        obj = pd.Series({k: n.objective / 1e9 for k, n in runs.items()}, name='Total discounted cost (bn €)')
        rel = pd.DataFrame({'Total discounted cost (bn €)': obj, 'Change vs F1 (%)': 100 * (obj / obj['F1'] - 1)})
        if 'F1_nofcet' in obj:     # the core's own reference (ICE + BET only)
            rel['Change vs F1_nofcet (%)'] = 100 * (obj / obj['F1_nofcet'] - 1)
        rel.round(2).to_csv(os.path.join(OUT, 'freight_total_cost.csv'))
        lines += ['## Total discounted system cost 2020-2059\n', rel.round(2).to_markdown(), '']

    # ---- cost of switching (vs ICE-only counterfactual) ----
    sw, sw_core = {}, {}
    for f in SCEN:
        if f in runs and runs.get(f'{f}_ice') is not None:
            d = fr.switching_cost(runs[f], runs[f'{f}_ice'])
            sw[f] = d
        if f'{f}_nofcet' in runs and runs.get(f'{f}_ice') is not None:
            sw_core[f] = fr.switching_cost(runs[f'{f}_nofcet'], runs[f'{f}_ice'])
    if sw_core:
        swc = pd.concat(sw_core).round(2)
        swc.to_csv(os.path.join(OUT, 'freight_switching_cost_core.csv'))
        lines += ['## Cost of switching, assignment core (ICE + BET only, minus ICE-only)\n', swc.to_markdown(), '']
    if sw:
        swt = pd.concat(sw).round(2)
        swt.to_csv(os.path.join(OUT, 'freight_switching_cost.csv'))
        lines += ['## Cost of switching to zero-emission freight (run minus ICE-only)\n', swt.to_markdown(), '']

    # ---- sensitivities (2030 and 2050) ----
    sens = [k for k in runs if k not in SCEN and k not in SCEN_CORE and not k.endswith('_ice')
            and k not in [f'{f}_real' for f in SCEN]]
    if sens:
        rows = []
        for k in sens:
            base = real_name(k) or (k.split('_')[0] + ('_nofcet' if k.endswith('_nofcet') else ''))
            for y in (2030, 2050):
                a, b = allsum.loc[(k, y)], allsum.loc[(base, y)] if (base, y) in allsum.index else None
                rows.append({'run': k, 'period': y, 'ZE share (%)': a['ZE share of freight (%)'],
                             'FCET share (%)': a['FCET share of freight (%)'],
                             'H2-ICE share (%)': a.get('H2-ICE share of freight (%)', 0.0),
                             'CO2 freight (Mt/yr)': a['CO2 freight trucks (Mt/yr)'],
                             'CO2 total (Mt/yr)': a['CO2 total (Mt/yr)'],
                             'Δ system cost vs base (bn €/yr)': None if b is None else
                             a['System cost (bn €/yr)'] - b['System cost (bn €/yr)'],
                             'BET capacity (GW)': a['BET capacity (GW)']})
        st = pd.DataFrame(rows).round(2)
        st.to_csv(os.path.join(OUT, 'freight_sensitivities.csv'), index=False)
        lines += ['## Sensitivities\n', st.to_markdown(index=False), '']

    # ---- shadow prices (runs solved with store_shadow_prices) ----
    sp = {k: fr.shadow_prices(n) for k, n in runs.items() if n is not None and isinstance(n.meta, dict)
          and any('shadow' in key for key in n.meta)}
    if sp:
        spt = pd.concat(sp, names=['run', 'period']).drop(index=2020, level='period', errors='ignore')
        spt = spt.loc[:, spt.abs().max() > 1e-3]                     # drop constraints that never bind
        spt.round(2).to_csv(os.path.join(OUT, 'freight_shadow_prices.csv'))
        lines += ['## Shadow prices (per year of the period; 0 = limit does not bind)\n',
                  spt.round(2).to_markdown(), '']

    # ---- grid batteries and hydrogen storage ----
    stor = {k: fr.storage(n) for k, n in runs.items() if n is not None}
    if stor:
        stt = pd.concat(stor, names=['run', 'period'])
        stt.round(3).to_csv(os.path.join(OUT, 'freight_storage.csv'))
        keep = [k for k in ('F1_nofcet', 'F1', 'F1_tres6', 'F4') if k in stor]
        if keep:
            lines += ['## Batteries and hydrogen storage\n', stt.loc[keep].round(2).to_markdown(), '']
    open(os.path.join(OUT, 'freight_key_numbers.md'), 'w').write('\n'.join(lines))

    if not main_runs and not core_runs:
        return
    pd.concat({k: grid_generation(n) for k, n in runs.items()}).round(2).to_csv(
        os.path.join(OUT, 'freight_grid_generation_TWh.csv'))
    if core_runs:
        result_figures(runs, core_runs, sw_core, suffix='')         # within the assignment's specs
    if main_runs:
        result_figures(runs, main_runs, sw, suffix='_h2')         # hydrogen extension
    realistic_figures(runs)
    system_figures(runs)
    sensitivity_figure(runs)
    lever_figure(runs)
    transition_speed_figure(runs)
    water_driver_figure(runs)
    tipping_figure()
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
