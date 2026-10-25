# Figure 1 – Scenario matrix: three water scarcity scenarios.
# Made with Python + matplotlib. Run:  pip install matplotlib   then
#   python Figure1_scenario_matrix.py           APA, in colour (report): Figure1_scenario_matrix_APA.png / .pdf / .svg
#   python Figure1_scenario_matrix.py --bw      APA, black and white:    Figure1_scenario_matrix_APA_bw.png / .pdf / .svg
#   python Figure1_scenario_matrix.py --slide   the presentation (16:9 content box): Figure1_scenario_matrix_slide.png / .svg
# Colours: the scenario colours of the result charts (Base violet, Medium yellow, Scarce red; never blue or green, which
# are colours of hydrogen). APA: 6.5 inches wide, all text 8 pt or larger.
# Base = no water scarcity (group, 15 October). Parameter 1, the water limit on electrolysis, as a share of the
# cost-optimal electrolyser capacity of S1: S1 base 100% (no limit), S2 medium 50%, S3 high 0% (the rest of the
# hydrogen demand is met by grey or blue hydrogen).
import re
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"]

MODE = "slide" if "--slide" in sys.argv else ("bw" if "--bw" in sys.argv else "apa")


def _additions():
    """The package flag (energy_model/package.py), read as text so that this script needs only matplotlib."""
    f = Path(__file__).resolve().parents[1] / "energy_model" / "package.py"
    m = re.search(r"^ADDITIONS = (True|False)", f.read_text(), re.M) if f.exists() else None
    return bool(m and m.group(1) == "True")


ADDITIONS = _additions()       # the package with additions: H2 storage, pure green and pink in every run
W, H = 100, 57
WIDTH = 4.76 * W / H if MODE == "slide" else 6.5      # slide: as tall as the content box of the template (4.76 in)
FS = WIDTH / 6.5                                      # fonts scale with the width (APA: 8 pt or more)
fig = plt.figure(figsize=(WIDTH, WIDTH * H / W))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
BLACK, INK2, GRAY = "#000000", "#333333", "#E6E6E6"
COLOUR = MODE != "bw"


def rect(x, y, w, h, fill="white", dashed=False, lw=0.8, edge=BLACK):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge, linewidth=lw * (FS if COLOUR else 1.0),
                           linestyle=(0, (4, 2)) if dashed else "-"))


def text(x, y, s, size, **kw):
    ax.text(x, y, s, ha=kw.pop("ha", "center"), va="center", fontsize=size * FS, **kw)


def block(cx, cy, title, lines=(), ts=9.5, ss=8.0, step=2.25, code=None):
    """A title (and an optional code above it) with lines under it, centred on (cx, cy)."""
    total = 2.9 + step * len(lines) + (2.5 if code else 0)
    y = cy + total / 2
    if code:
        text(cx, y - 1.1, code, 8.4, fontweight="bold", color=INK2)
        y -= 2.5
    text(cx, y - 1.35, title, ts, fontweight="bold")
    for i, ln in enumerate(lines):
        text(cx, y - 2.9 - step * (i + 0.5), ln, ss)


# geometry: label column + three scenario columns in document order (S1, S2, S3)
LX, LWID = 1.0, 14.0
X0, GAP = 16.5, 1.2
CW = (99.0 - X0 - 2 * GAP) / 3
cols = [X0 + i * (CW + GAP) for i in range(3)]
NY, NH = 0.6, 9.6                     # note box
Y0, RH = 22.6, 22.0                   # scenario row
HY, HH = Y0 + RH + 1.5, 8.6           # header row (electrolyser capacity)

SCEN_EDGE = ["#6250d6", "#eda100", "#e34948"]
SCEN_TINT = ["#e9e6fa", "#fcefcf", "#fbe1e1"]
if COLOUR:
    styles = [(t, False, 1.6) for t in SCEN_TINT]
    edges = SCEN_EDGE
else:
    styles = [("white", False, 2.0), (GRAY, False, 0.8), (GRAY, True, 0.8)]   # S1 (base, bold), S2, S3
    edges = [BLACK] * 3

# header row: hydrogen from electrolysis (parameter 1)
text(LX + LWID / 2, HY + HH / 2 + 1.2, "Electrolyser", 8.6, fontweight="bold")
text(LX + LWID / 2, HY + HH / 2 - 1.2, "capacity (1)", 8.6, fontweight="bold")
heads = [("100%", ["no limit: cost-optimal"]),
         ("50%", ["of S1; rest grey or blue"]),
         ("0%", ["all grey or blue"])]
for x, (t, s), (fill, dashed, lw), edge in zip(cols, heads, styles, edges):
    rect(x, HY, CW, HH, fill=fill, dashed=dashed, lw=lw if COLOUR else 1.0, edge=edge)
    block(x + CW / 2, HY + HH / 2, t, s, ts=9.5, ss=8.0)

# row header: hydrogen demand (parameter 2), the same in every scenario
rect(LX, Y0, LWID, RH)
cx = LX + LWID / 2
rows = [("Hydrogen", True), ("demand", True), ("feedstock", False), ("industry,", False), ("1.3 Mt/yr, fixed", False),
        ("in all scenarios", False)]
for i, (s, bold) in enumerate(rows):
    text(cx, Y0 + RH / 2 + 5.9 - i * 2.4, s, 8.8 if bold else 8.0, fontweight="bold" if bold else "normal")

# scenario cells (the words of the scenario narratives; wrapped to the cell width)
cells = [
    ("S1 · BASE", "No water scarcity", ["heavy investment in", "seawater desalination;", "outside the verdringingsreeks"]),
    ("S2", "Medium water scarcity", ["competition with agriculture;", "little desalination or",
                                     "recycling; category 3,", "partly curtailed"]),
    ("S3", "High water scarcity", ["drought; other sectors", "prioritized; no desalination;",
                                   "category 4, curtailed first"]),
]
if COLOUR:      # the short names of the result charts
    cells = [(c, nm, ln) for (_, nm, ln), c in zip(cells, ["S1 · BASE", "S2 · MEDIUM", "S3 · SCARCE"])]
for x, (code, name, lines), (fill, dashed, lw), edge in zip(cols, cells, styles, edges):
    rect(x, Y0, CW, RH, fill=fill, dashed=dashed, lw=lw, edge=edge)
    block(x + CW / 2, Y0 + RH / 2, name, lines, ts=9.5, ss=8.0, code=code)

# comparisons with the base scenario: S1 -> S2 (medium scarcity) and S1 -> S3 (high scarcity)
c1, c2, c3 = (x + CW / 2 for x in cols)
yA, yB = Y0 - 4.4, Y0 - 9.4


def connector(points, label, lx, ly):
    for (x1, y1), (x2, y2) in zip(points[:-2], points[1:-1]):
        ax.plot([x1, x2], [y1, y2], color=BLACK, lw=0.8 * FS, solid_capstyle="butt")
    ax.annotate("", xy=points[-1], xytext=points[-2],
                arrowprops=dict(arrowstyle="-|>", color=BLACK, lw=0.8 * FS, mutation_scale=9 * FS, shrinkA=0,
                                shrinkB=0))
    text(lx, ly, label, 8.0, style="italic")


connector([(c1 + 3, Y0), (c1 + 3, yA), (c2, yA), (c2, Y0)], "medium scarcity: at most 50%", (c1 + 3 + c2) / 2, yA + 1.6)
connector([(c1 - 3, Y0), (c1 - 3, yB), (c3, yB), (c3, Y0)], "high scarcity: no electrolysers", (c2 + c3) / 2, yB + 1.6)
text(LX + LWID / 2, (yA + yB) / 2 + 1.2, "Compared with", 8.4, fontweight="bold")
text(LX + LWID / 2, (yA + yB) / 2 - 1.2, "the base (S1)", 8.4, fontweight="bold")

# note box
rect(LX, NY, cols[2] + CW - LX, NH, lw=1.2)
mid = (LX + cols[2] + CW) / 2
text(mid, NY + NH - 2.0, "Hydrogen demand is met in every scenario; S2 and S3 are compared with the base scenario S1",
     8.6, fontweight="bold")
if ADDITIONS:
    text(mid, NY + NH - 4.7, "In every run: H₂ storage, pure green and pink routes (additions). In each scenario:", 8.0)
    text(mid, NY + NH - 7.1, "electrolyser cost or subsidy, CO₂ price (2a–b), H₂ storage cost (2c); batteries (3a–c); green levers",
         8.0)
else:
    text(mid, NY + NH - 4.7, "In each scenario: electrolyser cost or subsidy, CO₂ price (2a–b); batteries (3a–c);", 8.0)
    text(mid, NY + NH - 7.1, "green levers (desalinated water, subsidy per kg of hydrogen, mandate)", 8.0)

stem, exts, dpi = {"apa": ("Figure1_scenario_matrix_APA", ("png", "pdf", "svg"), 400),
                   "bw": ("Figure1_scenario_matrix_APA_bw", ("png", "pdf", "svg"), 400),
                   "slide": ("Figure1_scenario_matrix_slide", ("png", "svg"), 400)}[MODE]
for ext in exts:
    fig.savefig(Path(__file__).with_name(f"{stem}.{ext}"), dpi=dpi, facecolor="white", bbox_inches="tight",
                pad_inches=0.05)
print("saved", stem)
