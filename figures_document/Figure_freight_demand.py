"""Freight demand of the model (methodology figure): (a) the demand per period from the macroeconomic driver (90 PJ of
truck output in 2020, GDP with an elasticity of 0.6) and (b) the hourly profile of one week, with the two
time-restriction variants of the sensitivity analysis (Sunday ban, night ban). Read from the freight database.
Run from the package folder: python figures_document/Figure_freight_demand.py
"""
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.getcwd())
DB = os.path.join('input_databases', 'freight_nl', 'demand.xlsx')
INK, MUTED, GRID = '#1f2328', '#59636e', '#e6e8eb'
COL = {'freight_road': '#2a78d6', 'freight_sunday_ban': '#eb6834', 'freight_night_ban': '#6250d6'}
LAB = {'freight_road': 'base profile', 'freight_sunday_ban': 'Sunday ban (0–22 h)', 'freight_night_ban':
       'night ban (23–6 h)'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.edgecolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.labelcolor': INK})

dem = pd.read_excel(DB, 'demands').set_index('Demand').loc['freight_road']
drv = pd.read_excel(DB, 'drivers').set_index('driver').loc[dem['Driver']]
years = [2020, 2030, 2040, 2050]
twh = {y: dem['Start_value'] * (drv[y] / drv[2020]) ** dem['Exponent'] / 1e6 for y in years}
prof = pd.read_excel(DB, 'freight_profiles').set_index('time')

fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.6), gridspec_kw={'width_ratios': [0.8, 2.0]})
a1.bar(range(len(years)), [twh[y] for y in years], 0.62, color='#2a78d6', edgecolor='white')
for i, y in enumerate(years):
    a1.text(i, twh[y] + 0.6, f'{twh[y]:.1f}\n({twh[y] * 3.6:.0f} PJ)', ha='center', va='bottom', fontsize=5.8,
            color=MUTED, linespacing=1.1)
a1.set_xticks(range(len(years)), [str(y) for y in years], fontsize=6.5)
a1.set_ylim(0, 44)
a1.set_ylabel('Freight transport (TWh/yr,\ntruck output)')
a1.set_title(f'(a) Demand: GDP$^{{{dem["Exponent"]:g}}}$ driver', fontsize=7.5, loc='left', color=INK)
a1.grid(axis='y', color=GRID, lw=0.6)
a1.set_axisbelow(True)

week = prof.loc['2019-10-07':'2019-10-13 23:00']                  # an ordinary week (Monday to Sunday)
peak = week['freight_road'].max()
for c in ('freight_road', 'freight_sunday_ban', 'freight_night_ban'):
    a2.plot(range(len(week)), week[c] / peak, color=COL[c], lw=1.4 if c == 'freight_road' else 1.0,
            ls='-' if c == 'freight_road' else '--', label=LAB[c])
a2.set_xticks([12 + 24 * d for d in range(7)], ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], fontsize=6.5)
for d in range(1, 7):
    a2.axvline(24 * d, color=GRID, lw=0.6, zorder=0)
a2.set_xlim(0, len(week))
a2.set_ylim(0, 1.45)
a2.set_ylabel('Hourly demand\n(weekday peak = 1)')
a2.set_title('(b) Hourly profile of one week, and the time-restriction variants (energy per period unchanged)',
             fontsize=7.5, loc='left', color=INK)
a2.legend(frameon=False, fontsize=6.3, ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.02))
fig.tight_layout(w_pad=1.5)
for ext in ('png', 'svg'):
    fig.savefig(f'figures_document/Figure_freight_demand.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
print('saved figures_document/Figure_freight_demand.png')
