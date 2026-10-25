# Figure 2 – Verdringingsreeks and the classification of electrolysis.
# Made with Python + matplotlib. Run:  pip install matplotlib   then
#   python Figure2_verdringingsreeks.py           APA, in colour (report): Figure2_verdringingsreeks_APA.png / .pdf / .svg
#   python Figure2_verdringingsreeks.py --bw      APA, black and white:    Figure2_verdringingsreeks_APA_bw.png / .pdf / .svg
#   python Figure2_verdringingsreeks.py --slide   the presentation (16:9 content box, categories side by side):
#                                                 Figure2_verdringingsreeks_slide.png / .svg
# Colours: the scenario colours of the result charts (S1 Base violet, S2 Medium yellow, S3 Scarce red). APA: 6.5 inches
# wide, all text 8 pt or larger.
# Parameter 1, the water limit on electrolysis (base = no water scarcity, group 15 October): S1 base 100% (desalination,
# outside the verdringingsreeks), S2 medium 50% (category 3), S3 high 0% (category 4); grey or blue hydrogen fills the rest.
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"]

MODE = "slide" if "--slide" in sys.argv else ("bw" if "--bw" in sys.argv else "apa")
COLOUR = MODE != "bw"
BLACK, INK2, GRAY = "#000000", "#333333", "#E6E6E6"
SCEN = {"S1": ("#6250d6", "#e9e6fa"), "S2": ("#eda100", "#fcefcf"), "S3": ("#e34948", "#fbe1e1")}   # (edge, tint)
NEUTRAL = "#f4f3f0"


def setup(width, height_units, width_units=100):
    fig = plt.figure(figsize=(width, width * height_units / width_units))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width_units)
    ax.set_ylim(0, height_units)
    ax.axis("off")
    return fig, ax


def rect(ax, x, y, w, h, fill="white", edge=BLACK, dashed=False, lw=0.8):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge, linewidth=lw,
                           linestyle=(0, (4, 2)) if dashed else "-"))


def arrow(ax, x1, y1, x2, y2, lw=0.8, ms=9):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=BLACK, lw=lw, mutation_scale=ms, shrinkA=0, shrinkB=0))


def line(ax, xs, ys, dashed=False, lw=0.8):
    ax.plot(xs, ys, color=BLACK, lw=lw, linestyle=(0, (2, 2)) if dashed else "-", solid_capstyle="butt")


def outcome_items(ax, cx, y, size, items, gap=2.0, sq=1.6):
    """One centred line of items, each with a coloured square in front (colour) or a separator dot (bw)."""
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    widths = []
    for txt, _ in items:
        t = ax.text(0, 0, txt, fontsize=size)
        bb = t.get_window_extent(renderer=r)
        widths.append(inv.transform((bb.x1, 0))[0] - inv.transform((bb.x0, 0))[0])
        t.remove()
    total = sum(widths) + (len(items) - 1) * gap * 2 + (len(items) * (sq + 0.8) if COLOUR else 0)
    x = cx - total / 2
    for (txt, key), w in zip(items, widths):
        if COLOUR:
            ax.add_patch(Rectangle((x, y - sq / 2), sq, sq, facecolor=SCEN[key][0], edgecolor="none"))
            x += sq + 0.8
        ax.text(x, y, txt, fontsize=size, va="center", ha="left")
        x += w + gap * 2
        if not COLOUR and key != items[-1][1]:
            ax.text(x - gap, y, "·", fontsize=size, va="center", ha="center")


# --------------------------------------------------------------------------------------------------------------------
# APA (report): categories under each other, the classification of electrolysis next to categories 2-4
# --------------------------------------------------------------------------------------------------------------------

def apa():
    W, H = 100, 82
    fig, ax = setup(6.5, H, W)
    TS, SS = 9.2, 8.0

    def box(x, y, w, h, title, sub=None, fill="white", edge=BLACK, dashed=False, lw=0.8):
        rect(ax, x, y, w, h, fill, edge, dashed, lw)
        cx = x + w / 2
        if sub:
            ax.text(cx, y + h * 0.64, title, ha="center", va="center", fontsize=TS, fontweight="bold")
            ax.text(cx, y + h * 0.30, sub, ha="center", va="center", fontsize=SS)
        else:
            ax.text(cx, y + h / 2, title, ha="center", va="center", fontsize=TS, fontweight="bold")

    LX, LW = 2, 46          # left column
    RX, RW = 55, 39.5       # right column
    BH = 8.4                # box height
    grey_fill = NEUTRAL if COLOUR else GRAY

    # Header row
    box(LX, 71, LW, BH, "Drought in rivers and lakes", "Verdringingsreeks applies (S2, S3)")
    box(RX, 71, RW, BH, "Classification of electrolysis", "Scenario assumption", fill=grey_fill, dashed=True)

    # Verdringingsreeks categories
    cats = [
        (59.5, "1. Safety and irreversible damage", "Dikes, subsidence, vulnerable nature"),
        (48.5, "2. Utilities (supply at risk)", "Drinking water, then energy supply"),
        (37.5, "3. Small-scale high-value use", "Process water, capital-intensive crops"),
        (26.5, "4. Other interests", "Agriculture, shipping, industry, nature"),
    ]
    for y, t, s in cats:
        box(LX, y, LW, BH, t, s)
    arrow(ax, LX + LW / 2, 71, LX + LW / 2, 59.5 + BH)

    # Electrolysis options aligned with categories 2-4 (colour: the scenario that follows from it)
    opts = [
        (48.5, "As energy supply", "Category 2: protected (not used)", None),
        (37.5, "As process water", "Category 3: partly curtailed  →  S2 (50%)", "S2"),
        (26.5, "As ordinary industry", "Category 4: curtailed first  →  S3 (0%)", "S3"),
    ]
    for y, t, s, sc in opts:
        if COLOUR and sc:
            box(RX, y, RW, BH, t, s, fill=SCEN[sc][1], edge=SCEN[sc][0], dashed=True, lw=1.3)
        else:
            box(RX, y, RW, BH, t, s, fill=grey_fill, dashed=True)
        line(ax, [LX + LW, RX], [y + BH / 2, y + BH / 2], dashed=True)  # correspondence

    # Right-hand bus from header into each option
    bus = RX + RW + 3
    line(ax, [RX + RW, bus], [71 + BH / 2, 71 + BH / 2])
    line(ax, [bus, bus], [71 + BH / 2, 26.5 + BH / 2])
    for y, *_ in opts:
        arrow(ax, bus, y + BH / 2, RX + RW, y + BH / 2)

    # Outcome box
    arrow(ax, LX + LW / 2, 26.5, LX + LW / 2, 19.4)
    arrow(ax, RX + RW / 2, 26.5, RX + RW / 2, 19.4)
    rect(ax, LX, 11, RX + RW - LX, BH, lw=1.2)
    cx = (LX + RX + RW) / 2
    ax.text(cx, 11 + BH * 0.66, "Electrolyser capacity, share of the cost-optimal (parameter 1)", ha="center",
            va="center", fontsize=TS, fontweight="bold")
    outcome_items(ax, cx, 11 + BH * 0.29, SS, [("100% (S1 base, desalination)", "S1"), ("50% (S2, category 3)", "S2"),
                                               ("0% (S3, category 4)", "S3")], gap=1.6, sq=1.7)

    # Legend
    ly = 3.2
    rect(ax, LX + 4, ly, 3.2, 2.6)
    ax.text(LX + 8.4, ly + 1.3, "Verdringingsreeks category", va="center", fontsize=SS)
    rect(ax, 49, ly, 3.2, 2.6, fill=grey_fill, dashed=True)
    ax.text(53.4, ly + 1.3, "Electrolysis classification", va="center", fontsize=SS)
    if COLOUR:
        ax.text(81, ly + 1.3, "colour: scenario", va="center", fontsize=SS, style="italic", color=INK2)
    return fig


# --------------------------------------------------------------------------------------------------------------------
# Slide: the categories side by side (16:9 content box of the template, 11.5 x 4.76 in), text 10.5 pt or larger
# --------------------------------------------------------------------------------------------------------------------

def slide():
    W, H = 115, 47.6
    fig, ax = setup(11.5, H, W)
    TS, SS = 12.0, 10.5
    STEP_T, STEP_S = 1.9, 1.75          # line height of a title / subtitle line (units of 0.1 in)

    def box(x, y, w, h, title_lines, sub_lines, fill="white", edge=BLACK, dashed=False, lw=1.0):
        rect(ax, x, y, w, h, fill, edge, dashed, lw)
        total = STEP_T * len(title_lines) + 0.5 + STEP_S * len(sub_lines)
        yy = y + h / 2 + total / 2
        for t in title_lines:
            ax.text(x + w / 2, yy - STEP_T / 2, t, ha="center", va="center", fontsize=TS, fontweight="bold")
            yy -= STEP_T
        yy -= 0.5
        for s in sub_lines:
            ax.text(x + w / 2, yy - STEP_S / 2, s, ha="center", va="center", fontsize=SS, color=INK2 if COLOUR else BLACK)
            yy -= STEP_S
        return dict(cx=x + w / 2, t=y + h, b=y)

    X0, BW, GAP = 22.0, 21.6, 1.5
    xs = [X0 + i * (BW + GAP) for i in range(4)]
    TY, TH = 27.0, 10.6                  # verdringingsreeks row
    BY, BHH = 12.2, 10.6                 # classification row

    # heading over the categories: the order of the verdringingsreeks
    ax.text(X0, 45.6, "Drought in rivers and lakes: the verdringingsreeks applies (S2, S3)", ha="left", va="center",
            fontsize=TS, fontweight="bold")
    arrow(ax, X0, 41.4, xs[3] + BW, 41.4, lw=1.0, ms=11)
    ax.text(X0, 42.6, "served first", ha="left", va="bottom", fontsize=SS, color=INK2, style="italic")
    ax.text(xs[3] + BW, 42.6, "curtailed first", ha="right", va="bottom", fontsize=SS, color=INK2, style="italic")

    # row labels
    ax.text(0.8, TY + TH / 2 + 1.6, "Verdringingsreeks", ha="left", va="center", fontsize=TS, fontweight="bold")
    ax.text(0.8, TY + TH / 2 - 0.6, "priority of water use", ha="left", va="center", fontsize=SS, color=INK2)
    ax.text(0.8, TY + TH / 2 - 2.2, "in a drought", ha="left", va="center", fontsize=SS, color=INK2)
    ax.text(0.8, BY + BHH / 2 + 1.6, "Electrolysis", ha="left", va="center", fontsize=TS, fontweight="bold")
    ax.text(0.8, BY + BHH / 2 - 0.6, "classified as", ha="left", va="center", fontsize=SS, color=INK2)
    ax.text(0.8, BY + BHH / 2 - 2.2, "(scenario assumption)", ha="left", va="center", fontsize=SS, color=INK2)

    cats = [(["1. Safety and", "irreversible damage"], ["Dikes, subsidence,", "vulnerable nature"]),
            (["2. Utilities", "(supply at risk)"], ["Drinking water, then", "energy supply"]),
            (["3. Small-scale", "high-value use"], ["Process water,", "capital-intensive crops"]),
            (["4. Other interests"], ["Agriculture, shipping,", "industry, nature"])]
    tops = [box(x, TY, BW, TH, t, s) for x, (t, s) in zip(xs, cats)]

    grey_fill = NEUTRAL if COLOUR else GRAY
    opts = [(xs[0], ["Desalinated water"], ["outside the verdringingsreeks", "→ S1 Base: 100%"], "S1", False),
            (xs[1], ["As energy supply"], ["Category 2: protected", "(not used)"], None, True),
            (xs[2], ["As process water"], ["Category 3: partly curtailed", "→ S2 Medium: 50%"], "S2", True),
            (xs[3], ["As ordinary industry"], ["Category 4: curtailed first", "→ S3 Scarce: 0%"], "S3", True)]
    for i, (x, t, s, sc, inside) in enumerate(opts):
        if COLOUR and sc:
            box(x, BY, BW, BHH, t, s, fill=SCEN[sc][1], edge=SCEN[sc][0], dashed=inside, lw=1.8)
        else:
            box(x, BY, BW, BHH, t, s, fill=grey_fill if inside else "white", dashed=inside, lw=1.0 if inside else 1.8)
        if inside:            # correspondence with the category above
            line(ax, [tops[i]["cx"], tops[i]["cx"]], [TY, BY + BHH], dashed=True, lw=1.0)

    # outcome strip
    rect(ax, 0.8, 1.0, xs[3] + BW - 0.8, 7.6, lw=1.4)
    ax.text(2.4, 6.4, "Electrolyser capacity (parameter 1), share of the cost-optimal capacity of S1:", ha="left",
            va="center", fontsize=TS, fontweight="bold")
    outcome_items(ax, (0.8 + xs[3] + BW) / 2, 3.0, SS + 0.5,
                  [("100%  S1 Base (desalination)", "S1"), ("50%  S2 Medium (category 3)", "S2"),
                   ("0%  S3 Scarce (category 4); grey or blue hydrogen fills the rest", "S3")], gap=1.8, sq=1.5)
    return fig


fig = slide() if MODE == "slide" else apa()
stem, exts, dpi = {"apa": ("Figure2_verdringingsreeks_APA", ("png", "pdf", "svg"), 400),
                   "bw": ("Figure2_verdringingsreeks_APA_bw", ("png", "pdf", "svg"), 400),
                   "slide": ("Figure2_verdringingsreeks_slide", ("png", "svg"), 400)}[MODE]
for ext in exts:
    fig.savefig(Path(__file__).with_name(f"{stem}.{ext}"), dpi=dpi, facecolor="white", bbox_inches="tight",
                pad_inches=0.05)
print("saved", stem)
