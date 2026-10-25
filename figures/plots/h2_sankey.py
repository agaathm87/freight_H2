"""Sankey diagrams of the hydrogen system, drawn from model results (one panel per run, one scale).

Based on the earlier illustrative script Extra_sankey_scenarios.py (matplotlib only, no extra packages),
now fed with model output: TWh per year of the representative year of a period.

    from figures.plots.h2_sankey import plot_sankeys, plot_sankeys_row
    fig = plot_sankeys({'Base': n1, 'Medium': n2, 'Scarce': n3}, period=2050)        # panels under each other
    fig = plot_sankeys_row({'Base': n1, 'Medium': n2, 'Scarce': n3}, period=2050)    # side by side (slides)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Rectangle

from .h2_results import _w, link_input, link_output
from energy_model.h2_presets import (ELECTROLYSIS_GRID, ELECTROLYSIS_SEAWATER, ELECTROLYSIS_GREEN, ELECTROLYSIS_PINK,
                                     GREY, BLUE)
from .h2_plots import ROUTE_COLORS, CARRIER_COLORS, INK, INK2
# [Freight] the pure green (dedicated wind + solar) and pink (own nuclear) electrolysers come from h2_presets; they
# were empty placeholders here, so these routes were missing from the Sankey when they were used

# the hydrogen technologies (end-use technologies: they feed the hydrogen demand directly):
# (label, technologies, input carrier node, colour of the hydrogen it makes). The options appear when they are used.
CONVERSIONS = [
    ('Electrolysis (grid)', ELECTROLYSIS_GRID + ELECTROLYSIS_SEAWATER, 'Grid electricity',
     ROUTE_COLORS['Green (grid electrolysis)']),
    ('Electrolysis (dedicated)', ELECTROLYSIS_GREEN, 'Dedicated wind + solar',
     ROUTE_COLORS['Pure green (dedicated wind + solar)']),
    ('Electrolysis (nuclear)', ELECTROLYSIS_PINK, 'Nuclear power', ROUTE_COLORS['Pink (nuclear electrolysis)']),
    ('SMR + CCS', BLUE, 'Natural gas', ROUTE_COLORS['Blue (SMR + CCS)']),
    ('SMR', GREY, 'Natural gas', ROUTE_COLORS['Grey (SMR)']),
]
SOURCE_COL = {'Grid electricity': CARRIER_COLORS['electricity'], 'Dedicated wind + solar': '#008300',
              'Nuclear power': '#6250d6', 'Natural gas': CARRIER_COLORS['gas']}
HUB = 'Hydrogen demand'          # the demand bus: refineries and ammonia, 1.3 Mt/yr
H2_COL = CARRIER_COLORS['hydrogen']
LOSS_COL = CARRIER_COLORS['loss']


def co2_notes(n, period, sep=', '):
    """CO2 emitted and stored by the SMR routes (Mt/yr), for labels under the conversion nodes."""
    from .h2_results import ts
    w = _w(n)
    notes = {}
    for label, techs in [('SMR', GREY), ('SMR + CCS', BLUE)]:
        links = n.links.index[n.links.carrier.isin(techs)]
        if not len(links):
            continue
        sl = n.snapshots.get_level_values(0) == period
        emit = float((-ts(n, 'links', 'p2').loc[sl, links]).mul(w[sl], axis=0).sum().sum()) / 1e6
        stored = float((-ts(n, 'links', 'p3').loc[sl, links]).mul(w[sl], axis=0).sum().sum()) / 1e6 \
            if 'p3' in n.links_t and label == 'SMR + CCS' else 0.0
        notes[label] = f'CO$_2$ {emit:.1f} Mt emitted' + (f'{sep}{stored:.1f} Mt stored' if stored > 0.05 else '')
    return notes


def sankey_flows(n, period):
    """Flows (source, target, TWh/yr, colour) for one network and period."""
    flows = []
    for label, techs, src, col in CONVERSIONS:
        inp = link_input(n, techs).get(period, 0.0) / 1e6
        out = link_output(n, techs).get(period, 0.0) / 1e6
        if inp <= 1e-3:
            continue
        flows.append((src, label, inp, SOURCE_COL[src]))
        flows.append((label, HUB, out, col))
        flows.append((label, 'loss', inp - out, LOSS_COL))
    return flows


def _ribbon(ax, x0, y0t, y0b, x1, y1t, y1b, color):
    xm = (x0 + x1) / 2
    verts = [(x0, y0t), (xm, y0t), (xm, y1t), (x1, y1t), (x1, y1b), (xm, y1b), (xm, y0b), (x0, y0b), (x0, y0t)]
    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor='white', lw=0.6, alpha=0.8))


XCOL = [16, 42, 66, 86]   # x of each column (axis units 0-100)
NW = 1.6                  # node width
GAP = 6.0                 # vertical gap between nodes (TWh units)


def panel_height(flows, scale):
    """Height needed by the tallest column of one panel."""
    src = {}
    for s_, t, v, _ in flows:
        if s_ in SOURCE_COL:
            src[s_] = src.get(s_, 0) + v
    conv = {}
    for s_, t, v, _ in flows:
        if t not in (HUB, 'loss') and s_ in SOURCE_COL:
            conv[t] = conv.get(t, 0) + v
    h = max(sum(src.values()) + GAP * max(len(src) - 1, 0), sum(conv.values()) + GAP * max(len(conv) - 1, 0), 1)
    return h * scale


SHORT = {'Grid electricity': 'Grid electricity', 'Dedicated wind + solar': 'Own wind + solar',
         'Nuclear power': 'Own nuclear', 'Natural gas': 'Natural gas', HUB: 'H$_2$ demand'}


def draw_sankey(ax, flows, title, top, scale, notes=None, xcol=None, fs=1.0, compact=False, title_dy=18):
    """One panel. xcol: x of the source, conversion and demand columns; fs: font scale; compact: labels on two
    lines (name, value) and short names, for narrow panels side by side."""
    XCOL_ = xcol or XCOL
    if not any(v > 1e-3 for _, _, v, _ in flows):          # a period without any hydrogen
        ax.text(0, top + title_dy, title, ha='left', va='center', fontsize=9 * fs, fontweight='bold', color=INK)
        ax.text(XCOL_[0], top - 4, 'No hydrogen is produced or used in this period.', ha='left', va='center',
                fontsize=7.5 * fs, style='italic', color=INK2)
        return
    cols = {0: [], 1: [], 2: [HUB], 3: []}
    for s_, t, v, _ in flows:
        if s_ in SOURCE_COL and s_ not in cols[0]:
            cols[0].append(s_)
    cols[1] = [c[0] for c in CONVERSIONS if any(f[1] == c[0] for f in flows)]
    val = {}
    for c in cols.values():
        for nme in c:
            val[nme] = max(sum(f[2] for f in flows if f[0] == nme), sum(f[2] for f in flows if f[1] == nme))
    pos = {}
    for ci, names in cols.items():
        y = top
        for nme in names:
            h = val[nme] * scale
            pos[nme] = (XCOL_[ci], y, y - h)
            y -= h + GAP * scale
    order = {nme: i for i, nme in enumerate(cols[0] + cols[1] + cols[2] + cols[3])}
    order['loss'] = 99
    out_off = {k: 0.0 for k in pos}
    in_off = {k: 0.0 for k in pos}
    loss_labels = []
    for s_, t, v, col in sorted(flows, key=lambda f: (order[f[0]], order[f[1]])):
        if v <= 1e-3:
            continue
        xs, ts, _ = pos[s_]
        h = v * scale
        y0t = ts - out_off[s_]
        out_off[s_] += h
        if t == 'loss':
            drop = 2.0
            _ribbon(ax, xs + NW, y0t, y0t - h, xs + NW + 4.0, y0t - drop, y0t - h - drop, col)
            loss_labels.append((xs + NW + 4.4, y0t - drop - h / 2, f'loss {v:.1f}' if compact else f'losses {v:.1f}'))
            continue
        xt, tt, _ = pos[t]
        y1t = tt - in_off[t]
        in_off[t] += h
        _ribbon(ax, xs + NW, y0t, y0t - h, xt, y1t, y1t - h, col)
    for ci, names in cols.items():
        for nme in names:
            x, t, b = pos[nme]
            fc = SOURCE_COL.get(nme) or next((c[3] for c in CONVERSIONS if c[0] == nme), H2_COL)
            ax.add_patch(Rectangle((x, b), NW, max(t - b, 0.3), facecolor=fc, edgecolor='none'))
            name = SHORT.get(nme, nme) if compact else nme
            txt = f'{name}\n{val[nme]:.1f}' if compact and (ci == 0 or nme == HUB) else f'{name}  {val[nme]:.1f}'
            ym = (t + b) / 2
            if ci == 0:
                ax.text(x - 1.0, ym, txt, ha='right', va='center', fontsize=7 * fs, color=INK, linespacing=1.15)
            elif ci == 3 or nme == HUB:
                ax.text(x + NW + 1.0, ym, txt, ha='left', va='center', fontsize=7 * fs, color=INK, linespacing=1.15)
            else:
                ax.text(x + NW / 2, t + 1.2, txt, ha='center', va='bottom', fontsize=6.8 * fs, color=INK,
                        bbox=dict(facecolor='white', edgecolor='none', pad=0.3))
                if notes and nme in notes:
                    ax.text(x - 1.0, b - 1.0, notes[nme], ha='right', va='top', fontsize=6.3 * fs, color=INK2,
                            style='italic', linespacing=1.15)
    for x, y, txt in loss_labels:   # drawn last, on a white label, so ribbons do not cover them
        ax.text(x, y, txt, ha='left', va='center', fontsize=6.3 * fs, color=INK2, zorder=5,
                bbox=dict(facecolor='white', edgecolor='none', pad=0.2, alpha=0.85))
    ax.text(0, top + title_dy, title, ha='left', va='center', fontsize=9 * fs, fontweight='bold', color=INK)


def fit_texts(ax, pad=0.6, rounds=6):
    """Widen the data limits of an axes (no ticks, e.g. a Sankey) so that every text lies inside the figure. The fonts
    keep their size; the drawing gets a little narrower. Iterates, because the limits move the texts."""
    fig = ax.figure
    for _ in range(rounds):
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        inv = ax.transData.inverted()
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        bx0, bx1, by0, by1 = x0, x1, y0, y1
        for t in ax.texts:
            if not t.get_visible() or not t.get_text().strip():
                continue
            bb = t.get_window_extent(renderer=r)
            (a, b), (c, d) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
            bx0, bx1 = min(bx0, a - pad), max(bx1, c + pad)
            by0, by1 = min(by0, b - pad), max(by1, d + pad)
        if max(abs(bx0 - x0), abs(bx1 - x1), abs(by0 - y0), abs(by1 - y1)) < 1e-6:
            break
        ax.set_xlim(bx0, bx1)
        ax.set_ylim(by0, by1)


def plot_sankeys(runs, period=2050, scale=None, note=True, width=7.5, fs=1.0, titles=None, fit=False):
    """One Sankey panel per run (same scale), TWh/yr in the given period, the panels under each other (report).
    width in inches; fs scales the fonts; titles: {run: panel title}."""
    all_flows = {k: sankey_flows(n, period) for k, n in runs.items()}
    all_notes = {k: co2_notes(n, period) for k, n in runs.items()}
    biggest = max(sum(f[2] for f in fl if f[1] != 'loss' and f[0] in SOURCE_COL) + 1 for fl in all_flows.values())
    if scale is None:
        scale = 120.0 / max(biggest, 1.0)
    heights = [panel_height(fl, scale) + 62 for fl in all_flows.values()]
    H = sum(heights) + 12
    fig = plt.figure(figsize=(width, H / 62 * width / 7.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, H)
    ax.axis('off')
    y0 = H
    for (k, fl), h in zip(all_flows.items(), heights):
        top = y0 - 30
        draw_sankey(ax, fl, (titles or {}).get(k, f'{k}: hydrogen system in {period} (TWh per year)'), top, scale,
                    all_notes[k], fs=fs)
        y0 -= h
    if note:
        ax.text(0, 4, 'Model results. Width = energy (TWh/yr, LHV); losses = conversion losses. '
                      'Colours: the colour of the hydrogen (green, pure green, pink, blue, grey).',
                fontsize=6.6, style='italic', color=INK2, va='center')
    if fit:                 # keep every label inside the figure (the report: a fixed width of 6.5 inches)
        fit_texts(ax)
    return fig


def plot_sankeys_row(runs, period=2050, figsize=(13.3, 5.4), fs=1.3, titles=None, note=True):
    """The panels side by side on one scale (for slides): one Sankey per run, TWh/yr in the given period.
    titles: {run: panel title}; by default the run name."""
    all_flows = {k: sankey_flows(n, period) for k, n in runs.items()}
    all_notes = {k: co2_notes(n, period, sep='\n') for k, n in runs.items()}
    biggest = max(sum(f[2] for f in fl if f[1] != 'loss' and f[0] in SOURCE_COL) + 1 for fl in all_flows.values())
    scale = 100.0 / max(biggest, 1.0)
    H = max(panel_height(fl, scale) for fl in all_flows.values()) + 36
    fig, axes = plt.subplots(1, len(runs), figsize=figsize)
    for ax, (k, fl) in zip(np.atleast_1d(axes), all_flows.items()):
        ax.set_xlim(0, 100)
        ax.set_ylim(0, H)
        ax.axis('off')
        draw_sankey(ax, fl, (titles or {}).get(k, k), H - 17, scale, all_notes[k], xcol=[30, 57, 84, 99], fs=fs,
                    compact=True, title_dy=11)
    if note:
        fig.text(0.01, 0.015, f'Model results, {period}. Width = energy (TWh/yr, LHV), the same scale in every panel; '
                              'loss = conversion losses. Colour of a ribbon into the demand = the colour of the hydrogen.',
                 fontsize=7.2 * fs, style='italic', color=INK2)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.06, wspace=0.04)
    return fig
