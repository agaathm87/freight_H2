"""The water-scarcity driver (methodology figure): the verdringingsreeks (Dutch priority order for water in a
drought), the model's water users in each category, and the share of its drought-season reference water each
category may use per period on the driver path (water_scarcity='driver'). Water above a quota is desalinated or
reused water at water_alt_cost. Values are read from the presets.
Run from the package folder: python figures_document/Figure_water_driver.py
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.getcwd())
from energy_model.freight_presets import DROUGHTS, WATER_REFERENCE_DRY, WATER_SCARCITY  # noqa: E402

INK, MUTED, GRID = '#1f2328', '#59636e', '#e6e8eb'
LO, HI = np.array(to_rgb('#eb6834')), np.array(to_rgb('#f2f3f5'))       # 0% (curtailed) ... 100% (served)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5})
path = WATER_SCARCITY['driver']['drought']
derate = WATER_SCARCITY['driver']['derate']
years = sorted(path)
CATS = [(1, 'Safety and irreversible damage', 'dikes, subsidence, vulnerable nature', None),
        (2, 'Utilities', 'drinking water, then energy supply: power plants', 'power'),
        (3, 'Small-scale high-value use', 'process water (SMR, CO$_2$ capture); electrolysis*', 'process'),
        (4, 'Other interests', 'agriculture, nature; PV panel cleaning', 'pv')]

fig, ax = plt.subplots(figsize=(6.5, 3.6))
ax.set_xlim(0, 100), ax.set_ylim(-3, 52), ax.axis('off')
ax.annotate('', xy=(2.2, 7.5), xytext=(2.2, 44.0), arrowprops=dict(arrowstyle='-|>', color=INK, lw=0.9))
ax.text(0.6, 25.7, 'served first  →  curtailed first', fontsize=6.0, color=MUTED, style='italic', va='center',
        ha='center', rotation=270)
ax.text(5, 48.6, 'Verdringingsreeks', fontsize=7.6, weight='bold', color=INK, va='center')
ax.text(5, 46.3, 'priority of water use in a drought', fontsize=5.8, color=MUTED, va='center')
X0, CW, RH = 5, 44, 8.5                                     # category column; one row per category
for k, (c, name, users, grp) in enumerate(CATS):
    y = 36 - k * (RH + 1.2)
    ax.add_patch(FancyBboxPatch((X0, y), CW, RH, boxstyle='round,pad=0,rounding_size=0.8', facecolor='white',
                                edgecolor=MUTED, lw=0.8))
    ax.text(X0 + 1.5, y + RH - 2.2, f'{c}. {name}', fontsize=7.2, weight='bold', color=INK, va='center')
    ax.text(X0 + 1.5, y + 2.5, users, fontsize=6.0, color=MUTED, va='center')
    for j, yr in enumerate(years):
        x = 52 + j * 12.5
        share = DROUGHTS[path[yr]].get(c, 1.0) if c > 1 else 1.0
        ref = sum(v.get(yr, 0.0) for g, v in WATER_REFERENCE_DRY.items()
                  if (grp == g) or (c == 3 and g == 'electrolysis'))
        col = LO + (HI - LO) * share
        ax.add_patch(FancyBboxPatch((x, y), 11.5, RH, boxstyle='round,pad=0,rounding_size=0.8', facecolor=col,
                                    edgecolor='white', lw=1.0))
        ax.text(x + 5.75, y + RH / 2 + (1.3 if c > 1 else 0), f'{share:.0%}', ha='center', va='center', fontsize=7.5,
                weight='bold', color='white' if share < 0.4 else INK)
        if c > 1:
            ax.text(x + 5.75, y + 1.9, f'of {ref:.1f} Mm$^3$', ha='center', va='center', fontsize=5.5,
                    color='white' if share < 0.4 else MUTED)
for j, yr in enumerate(years):
    x = 52 + j * 12.5 + 5.75
    ax.text(x, 48.6, str(yr), ha='center', va='center', fontsize=7.2, weight='bold', color=INK)
    ax.text(x, 46.3, {'dry_1in20': '1-in-20 dry', 'extreme_2018': '2018-type'}[path[yr]], ha='center',
            va='center', fontsize=5.8, color=MUTED)
ax.text(90.5, 44.0, 'summer derating\nof river-cooled\nplants:\n'
        + ' / '.join(f'{100 * derate[y]:.0f}%' for y in years),
        fontsize=5.8, color=MUTED, va='top', linespacing=1.3)
ax.text(1, 5.0, 'Share of the June–September freshwater each category used in the reference run (F1, no limits) '
        'that it '
        'may use on the driver path.\nAbove a quota: desalinated or reused water at €1.4/m$^3$ (the backstop). '
        '* Electrolysis is in category 3 by default and in category 4 in the run F1_real_water_ely4.',
        fontsize=5.9, color=MUTED, va='top', linespacing=1.35)
for ext in ('png', 'svg'):
    fig.savefig(f'figures_document/Figure_water_driver.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
print('saved figures_document/Figure_water_driver.png')
