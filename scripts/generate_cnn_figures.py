#!/usr/bin/env python3
"""Regenerate the CNN dense-parallelism figures used by the website.

The measurements are preserved in the historical CNN article and match the
analytical latency model exactly:

    total_cycles = 403_000 fixed cycles + dense_cycles

The fixed component consists of convolution, ReLU, max-pool, argmax, and seven
cycles of control overhead.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRS = (ROOT / "static" / "figures", ROOT / "public" / "figures")

PARALLELISM = np.array([1, 2, 5, 10])
DENSE_CYCLES = np.array([62_732, 31_367, 12_548, 6_275])
CONV_CYCLES = np.full(4, 344_962)
RELU_CYCLES = np.full(4, 25_090)
MAXPOOL_CYCLES = np.full(4, 32_930)
OTHER_CYCLES = np.full(4, 18)  # Argmax (11) + control overhead (7)
REMAINING_CYCLES = RELU_CYCLES + MAXPOOL_CYCLES + OTHER_CYCLES
TOTAL_CYCLES = CONV_CYCLES + RELU_CYCLES + MAXPOOL_CYCLES + DENSE_CYCLES + OTHER_CYCLES
PREDICTED_CYCLES = 403_000 + DENSE_CYCLES

COLORS = {
    "ink": "#172B3A",
    "muted": "#5E6B76",
    "grid": "#DCE3E8",
    "background": "#FBFCFD",
    "conv": "#23638A",
    "relu": "#E59A3A",
    "pool": "#4B9B82",
    "dense": "#D65F5F",
    "other": "#A9B2BA",
    "model": "#D65F5F",
}


def thousands(value: float, _position: float | None = None) -> str:
    if value == 0:
        return "0"
    return f"{value / 1_000:.0f}k"


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": COLORS["background"],
            "axes.facecolor": COLORS["background"],
            "savefig.facecolor": COLORS["background"],
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.titlesize": 15,
            "axes.titleweight": "semibold",
            "axes.labelsize": 12,
            "axes.labelcolor": COLORS["ink"],
            "axes.edgecolor": COLORS["ink"],
            "axes.linewidth": 0.8,
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "text.color": COLORS["ink"],
            "grid.color": COLORS["grid"],
            "grid.linewidth": 0.8,
            "grid.alpha": 0.9,
            "legend.frameon": False,
        }
    )


def add_heading(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.suptitle(title, x=0.08, y=0.965, ha="left", fontsize=19, fontweight="semibold")
    fig.text(0.08, 0.875, subtitle, ha="left", color=COLORS["muted"], fontsize=11)


def save_figure(fig: plt.Figure, filename: str) -> None:
    for output_dir in OUTPUT_DIRS:
        output_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_dir / filename, dpi=180, bbox_inches="tight", pad_inches=0.24)
    plt.close(fig)


def stage_breakdown() -> None:
    fig, ax = plt.subplots(figsize=(10.4, 6.4))
    add_heading(
        fig,
        "Dense parallelism barely changes total latency",
        "Cycle breakdown for one CNN inference · lower is better",
    )
    fig.subplots_adjust(top=0.75, bottom=0.16, left=0.12, right=0.95)

    x = np.arange(len(PARALLELISM))
    bottom = np.zeros_like(PARALLELISM, dtype=float)
    stages = (
        ("Convolution", CONV_CYCLES, COLORS["conv"]),
        ("All other stages", REMAINING_CYCLES, COLORS["pool"]),
        ("Dense", DENSE_CYCLES, COLORS["dense"]),
    )
    for label, values, color in stages:
        ax.bar(
            x,
            values,
            width=0.56,
            bottom=bottom,
            color=color,
            label=label,
            linewidth=0,
        )
        bottom += values

    for index, total in enumerate(TOTAL_CYCLES):
        ax.text(
            index,
            total + 6_500,
            f"{total:,}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="semibold",
        )

    ax.set_ylabel("Cycles")
    ax.set_xlabel("Dense-output parallelism")
    ax.set_xticks(x, [f"{value}×" for value in PARALLELISM])
    ax.set_ylim(0, 500_000)
    ax.yaxis.set_major_formatter(FuncFormatter(thousands))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.10),
        ncol=3,
        columnspacing=2.0,
        handlelength=1.5,
        fontsize=10.5,
    )
    save_figure(fig, "stage_cycles_breakdown_vs_DENSE_OUT_PAR.png")


def latency_curve() -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    add_heading(
        fig,
        "Dense parallelism quickly reaches a system-level floor",
        "Measured end-to-end latency across the dense-output parallelism sweep",
    )
    fig.subplots_adjust(top=0.75, bottom=0.16, left=0.12, right=0.95)

    x = np.arange(len(PARALLELISM))
    fixed_floor = 403_000
    ax.axhline(fixed_floor, color=COLORS["muted"], linewidth=1.4, linestyle=(0, (4, 4)))
    ax.fill_between(x, fixed_floor, TOTAL_CYCLES, color=COLORS["dense"], alpha=0.12)
    ax.plot(
        x,
        TOTAL_CYCLES,
        color=COLORS["conv"],
        linewidth=2.6,
        marker="o",
        markersize=7,
        markerfacecolor=COLORS["background"],
        markeredgewidth=2.2,
    )
    for index, total in enumerate(TOTAL_CYCLES):
        ax.annotate(
            f"{total:,}",
            (index, total),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="semibold",
        )

    ax.text(
        2.96,
        fixed_floor + 1_100,
        "Fixed non-dense work: 403,000 cycles",
        ha="right",
        va="bottom",
        color=COLORS["muted"],
        fontsize=9.5,
    )
    ax.set_ylabel("End-to-end latency (cycles)")
    ax.set_xlabel("Dense-output parallelism")
    ax.set_xticks(x, [f"{value}×" for value in PARALLELISM])
    ax.set_xlim(-0.22, 3.22)
    ax.set_ylim(400_000, 478_000)
    ax.yaxis.set_major_formatter(FuncFormatter(thousands))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "latency_cycles_vs_DENSE_OUT_PAR.png")


def model_validation() -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    add_heading(
        fig,
        "Measured and predicted latency match exactly",
        "Analytical model validation across the dense-output parallelism sweep",
    )
    fig.subplots_adjust(top=0.69, bottom=0.16, left=0.12, right=0.95)

    x = np.arange(len(PARALLELISM))
    ax.plot(
        x,
        TOTAL_CYCLES,
        color=COLORS["conv"],
        linewidth=3.2,
        marker="o",
        markersize=10,
        markerfacecolor=COLORS["background"],
        markeredgewidth=2.5,
        label="Measured",
        zorder=2,
    )
    ax.plot(
        x,
        PREDICTED_CYCLES,
        color=COLORS["dense"],
        linewidth=2.0,
        linestyle=(0, (4, 3)),
        marker="s",
        markersize=5,
        markerfacecolor=COLORS["dense"],
        label="Predicted",
        zorder=3,
    )
    for index, total in enumerate(TOTAL_CYCLES):
        ax.annotate(
            f"{total:,}",
            (index, total),
            xytext=(0, 14),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="semibold",
        )

    ax.set_ylabel("Latency (cycles)")
    ax.set_xlabel("Dense-output parallelism")
    ax.set_xticks(x, [f"{value}×" for value in PARALLELISM])
    ax.set_xlim(-0.22, 3.22)
    ax.set_ylim(404_000, 478_000)
    ax.yaxis.set_major_formatter(FuncFormatter(thousands))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.09),
        ncol=2,
        columnspacing=2.0,
        handlelength=2.2,
        fontsize=10.5,
    )
    save_figure(fig, "measured_vs_predicted_latency_vs_DENSE_OUT_PAR.png")


def main() -> None:
    configure_style()
    stage_breakdown()
    latency_curve()
    model_validation()


if __name__ == "__main__":
    main()
