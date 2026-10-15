"""Draw the charts of technical_report.md into docs/report/ (PNG, 200 dpi).

Run from track_2a/:  python3 scripts/report_figures.py
Needs matplotlib (development machine only; not in the image). The numbers are copied from the report's tables, which
cite the run folders they come from (tags in square brackets, e.g. [FIN]); change them here when the tables change.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("docs/report")

# Colours: task A blue, task B orange (the first two slots of a colour-blind-checked palette); grey for comparisons.
TASK_A = "#2a78d6"
TASK_B = "#eb6834"
GREY = "#b4b2a9"
INK = "#0b0b0b"
MUTED = "#52514e"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
})


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / name)


def ablation():
    """Section 4: what Apertus reads, against Macro-F1 and input tokens (task A dev)."""
    rows = [  # label, Macro-F1, input tokens per case, final?
        ("Claim and vote only", 0.435, 200, False),
        ("8 embedding-search chunks", 0.834, 1868, False),
        ("Whole booklet, 100 cases", 0.858, 37586, False),
        ("Apertus does all parsing", 0.960, 1655, False),
        ("Part the claim names (final)", 0.977, 1259, True),
    ]
    labels = [r[0] for r in rows]
    colours = [TASK_A if r[3] else GREY for r in rows]
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 2.4), sharey=True, gridspec_kw={"wspace": 0.18})

    left.barh(labels, [r[1] for r in rows], color=colours, height=0.6)
    left.axvline(0.60, color=MUTED, linestyle="--", linewidth=1)
    left.text(0.605, -0.75, "minimum 0.60", color=MUTED, fontsize=7.5, va="bottom")
    left.set_xlim(0, 1.12)
    left.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    left.set_title("Macro-F1", loc="left")
    for i, r in enumerate(rows):
        left.text(r[1] + 0.01, i, f"{r[1]:.3f}", va="center", fontsize=8, color=INK)

    right.barh(labels, [r[2] for r in rows], color=colours, height=0.6)
    right.set_xscale("log")
    right.set_xlim(100, 150000)
    right.set_title("Input tokens per case (log scale)", loc="left")
    for i, r in enumerate(rows):
        right.text(r[2] * 1.12, i, f"{r[2]:,}", va="center", fontsize=8, color=INK)

    left.invert_yaxis()
    save(fig, "ablation_task_a.png")


def generalisation():
    """Section 6: final defaults on dev, val and the probe (two unseen dates), both tasks."""
    sets = ["dev", "val", "probe"]
    a = [0.977, 0.981, 0.990]
    b = [0.987, 0.968, 0.977]
    fig, ax = plt.subplots(figsize=(4.2, 2.3))
    x = range(len(sets))
    # Dots, not bars: the axis starts at 0.9, and a bar's length would exaggerate the differences.
    ax.plot([i - 0.1 for i in x], a, "o", color=TASK_A, markersize=8, label="Task A (document)")
    ax.plot([i + 0.1 for i in x], b, "o", color=TASK_B, markersize=8, label="Task B (reference)")
    # Dev only: 95 % bootstrap intervals [STAB].
    ax.errorbar([-0.1], [0.977], yerr=[[0.977 - 0.958], [0.991 - 0.977]], color=TASK_A, capsize=3, linewidth=1)
    ax.errorbar([0.1], [0.987], yerr=[[0.987 - 0.973], [0.997 - 0.987]], color=TASK_B, capsize=3, linewidth=1)
    for i in x:
        ax.text(i - 0.16, a[i], f"{a[i]:.3f}", ha="right", va="center", fontsize=7.5, color=INK)
        ax.text(i + 0.16, b[i], f"{b[i]:.3f}", ha="left", va="center", fontsize=7.5, color=INK)
    ax.set_xlim(-0.6, 2.6)
    ax.grid(axis="y", color="#e5e4df", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xticks(list(x), ["dev (300)", "val (580 A / 300 B)", "probe (94)"])
    ax.set_ylim(0.95, 1.0)
    ax.set_title("Macro-F1 of the final system", loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "final_scores.png")


def fallbacks():
    """Section 6: forced fallbacks, dev Macro-F1: e5 chunks (before) against the adopted fallback."""
    situations = ["no part found", "contents unreadable"]
    before = [0.900, 0.896]  # e5's 8 chunks of the booklet
    after = [0.956, 0.946]   # BM25 + AP-translate; AP-structure
    after_labels = ["word search + translation", "Apertus reads the contents"]
    fig, ax = plt.subplots(figsize=(4.6, 1.9))
    y = range(len(situations))
    h = 0.36
    ax.barh([i - h / 2 for i in y], before, h, color=GREY, label="earlier fallback: embedding search")
    ax.barh([i + h / 2 for i in y], after, h, color=TASK_A, label="adopted fallback")
    for i in y:
        ax.text(before[i] + 0.003, i - h / 2, f"{before[i]:.3f}", va="center", fontsize=8)
        ax.text(after[i] + 0.003, i + h / 2, f"{after[i]:.3f}  ({after_labels[i]})", va="center", fontsize=8)
    ax.axvline(0.977, color=MUTED, linestyle="--", linewidth=1)
    ax.text(0.979, -0.45, "normal path: 0.977", color=MUTED, fontsize=7.5, ha="left", va="top")
    ax.set_yticks(list(y), situations)
    ax.set_xlim(0.85, 1.08)
    ax.set_xticks([0.85, 0.90, 0.95, 1.0])
    ax.invert_yaxis()
    ax.set_title("Task A dev Macro-F1 with every case forced into a fallback", loc="left")
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.45, -0.18), ncol=2)
    save(fig, "fallbacks.png")


def local_time():
    """Section 6: local time per case against the model's speed (dev, the organisers' measure)."""
    speeds = [1.0, 0.3, 0.1]
    series = [  # label, values, colour, style
        ("Task A, earlier (e5)", [0.017, 0.160, 0.364], GREY, "--"),
        ("Task A, static model (final)", [0.020, 0.027, 0.062], TASK_A, "-"),
        ("Task B (final)", [0.012, 0.021, 0.172], TASK_B, "-"),
    ]
    fig, ax = plt.subplots(figsize=(4.4, 2.4))
    for label, values, colour, style in series:
        ax.plot(speeds, values, style, color=colour, linewidth=2, marker="o", markersize=5, label=label)
        ax.text(0.1 * 0.85, values[-1], f"{values[-1]:.3f} s", ha="left", va="center", fontsize=7.5, color=INK)
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xticks(speeds, ["1.0 s", "0.3 s", "0.1 s"])
    ax.minorticks_off()
    ax.set_xlim(1.25, 0.045)
    ax.set_xlabel("Model latency per request (faster →)")
    ax.set_ylabel("Local time per case (s)")
    ax.set_title("Local time grows when the model is fast", loc="left")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    save(fig, "local_time.png")


if __name__ == "__main__":
    ablation()
    generalisation()
    fallbacks()
    local_time()
