"""Create the core freight-scenario matrix used in the paper.

Run from this directory with:
    python Figure_core_scenario_matrix.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


OUTPUT = Path(__file__).with_name("Figure_core_scenario_matrix.png")


def create_figure(output: Path = OUTPUT) -> Path:
    """Render the four core scenarios on their two economic uncertainty axes."""
    fig, ax = plt.subplots(figsize=(8.6, 5.6), dpi=300)
    cells = {
        (0, 0): ("F1", "Moderate fuel-price increase\n€200 → €260/MWh", "#DCEAF7"),
        (1, 0): ("F2", "Moderate fuel-price increase\n€200 → €260/MWh", "#D9EAD3"),
        (0, 1): ("F3", "Sharp fuel-price increase\n€200 → €500/MWh", "#FCE4D6"),
        (1, 1): ("F4", "Sharp fuel-price increase\n€200 → €500/MWh", "#FFF2CC"),
    }

    for (x, y), (scenario, description, colour) in cells.items():
        ax.add_patch(
            Rectangle(
                (x, y),
                1,
                1,
                facecolor=colour,
                edgecolor="white",
                linewidth=2.5,
            )
        )
        ax.text(
            x + 0.5,
            y + 0.62,
            scenario,
            ha="center",
            va="center",
            fontsize=20,
            fontweight="bold",
            color="#1F2937",
        )
        ax.text(
            x + 0.5,
            y + 0.30,
            description,
            ha="center",
            va="center",
            fontsize=9.5,
            color="#374151",
            linespacing=1.3,
        )

    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5], ["Constant BET costs", "Falling BET costs"], fontsize=11)
    ax.set_yticks(
        [0.5, 1.5],
        ["Moderate increase\n€200 → €260/MWh", "Sharp increase\n€200 → €500/MWh"],
        fontsize=10,
    )
    ax.set_xlabel("BET cost pathway", fontsize=12, fontweight="bold", labelpad=12)
    ax.set_ylabel("Gasoline-price pathway", fontsize=12, fontweight="bold", labelpad=12)
    ax.tick_params(length=0, pad=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Core scenario matrix", fontsize=15, fontweight="bold", pad=18)
    fig.text(
        0.5,
        0.015,
        "The realistic layer retains this economic matrix and adds duty-cycle, "
        "adoption, policy and hydrogen constraints.",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#4B5563",
    )
    fig.subplots_adjust(left=0.25, right=0.98, top=0.82, bottom=0.22)
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


if __name__ == "__main__":
    print("saved", create_figure())
