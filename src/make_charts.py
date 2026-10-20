"""Renders result figures from artifacts/run_report.json + evaluation.json."""
from __future__ import annotations
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts")

NAVY = "#335295"
TEAL = "#2E8B7C"
AMBER = "#D98E2B"
RED = "#B5484D"
PLUM = "#8E5FA8"
GREY = "#6B7280"
LIGHT = "#E8ECF5"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#C7CEDB",
    "axes.labelcolor": "#333333",
    "text.color": "#222222",
    "xtick.color": "#555555",
    "ytick.color": "#555555",
})

report = json.load(open(os.path.join(ART, "run_report.json")))
ev = json.load(open(os.path.join(ART, "evaluation.json")))


# --------------------------------------------------------------- figure 1
def fig_baseline():
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    b = ev["baseline_vs_full"]["baseline"]
    f = ev["baseline_vs_full"]["full"]
    labels = [f"Happy-path suite\n({b['tests']} tests)", f"Full pipeline\n({f['tests']} tests)"]
    vals = [b["detected"], f["detected"]]
    bars = ax.bar(labels, vals, color=[GREY, NAVY], width=0.5, zorder=3)
    ax.axhline(f["total"], ls="--", lw=1.4, color=RED, zorder=2)
    ax.text(1.46, f["total"] + 0.12, f"all {f['total']} seeded defects",
            color=RED, fontsize=9, ha="right")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.18, f"{v}/{f['total']}",
                ha="center", fontsize=13, fontweight="bold",
                color=NAVY if v else GREY)
    ax.set_ylabel("Seeded defects detected")
    ax.set_ylim(0, f["total"] + 1.1)
    ax.set_title("Defect detection: conventional happy-path testing vs. the platform",
                 fontsize=12, fontweight="bold", color=NAVY, pad=12)
    ax.grid(axis="y", color=LIGHT, zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_baseline.png"), dpi=200, facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------- figure 2
def fig_categories():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 3.9))

    cats = report["counts"]["by_category"]
    order = ["positive", "negative", "boundary", "security"]
    colors = [TEAL, AMBER, NAVY, RED]
    ax1.bar([c.capitalize() for c in order], [cats[c] for c in order],
            color=colors, width=0.6, zorder=3)
    for i, c in enumerate(order):
        ax1.text(i, cats[c] + 0.4, str(cats[c]), ha="center",
                 fontweight="bold", fontsize=11, color="#333333")
    ax1.set_ylabel("Test cases generated")
    ax1.set_title("Generated test cases by category", fontsize=11,
                  fontweight="bold", color=NAVY)
    ax1.grid(axis="y", color=LIGHT, zorder=0)
    ax1.set_ylim(0, max(cats.values()) * 1.2)

    tiers = report["counts"]["priority_tiers"]
    tnames = ["P1", "P2", "P3", "P4"]
    tcolors = [RED, AMBER, NAVY, GREY]
    ax2.bar(tnames, [tiers[t] for t in tnames], color=tcolors, width=0.6, zorder=3)
    for i, t in enumerate(tnames):
        ax2.text(i, tiers[t] + 0.2, str(tiers[t]), ha="center",
                 fontweight="bold", fontsize=11, color="#333333")
    ax2.set_ylabel("Findings")
    ax2.set_title("Findings by risk priority tier", fontsize=11,
                  fontweight="bold", color=NAVY)
    ax2.grid(axis="y", color=LIGHT, zorder=0)
    ax2.set_ylim(0, max(tiers.values()) * 1.25 + 0.5)

    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_categories.png"), dpi=200, facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------- figure 3
def fig_confusion_and_features():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 3.9),
                                   gridspec_kw={"width_ratios": [1, 1.45]})

    cv = ev["cross_validation"]
    cm = cv.get("confusion_matrix", {"tn": 0, "fp": 0, "fn": 0, "tp": 0})
    mat = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
    im = ax1.imshow(mat, cmap="Blues", vmin=0, vmax=mat.max() * 1.15)
    for i in range(2):
        for j in range(2):
            ax1.text(j, i, str(mat[i, j]), ha="center", va="center",
                     fontsize=15, fontweight="bold",
                     color="white" if mat[i, j] > mat.max() * 0.55 else "#1B2A4A")
    ax1.set_xticks([0, 1], ["Pred:\nnormal", "Pred:\nfaulty"], fontsize=9)
    ax1.set_yticks([0, 1], ["Actual:\nnormal", "Actual:\nfaulty"], fontsize=9)
    ax1.set_title(f"Confusion matrix (5-fold CV)\nP={cv.get('precision')}  "
                  f"R={cv.get('recall')}  F1={cv.get('f1')}",
                  fontsize=10.5, fontweight="bold", color=NAVY)
    for sp in ax1.spines.values():
        sp.set_visible(False)

    feats = report["model_metrics"]["feature_importance"]
    top = list(feats.items())[:7][::-1]
    names = [k.replace("_", " ") for k, _ in top]
    vals = [v for _, v in top]
    ax2.barh(names, vals, color=NAVY, height=0.6, zorder=3)
    for i, v in enumerate(vals):
        ax2.text(v + 0.006, i, f"{v:.3f}", va="center", fontsize=9, color="#444444")
    ax2.set_xlabel("Gini importance")
    ax2.set_title("Most informative response features", fontsize=10.5,
                  fontweight="bold", color=NAVY)
    ax2.grid(axis="x", color=LIGHT, zorder=0)
    ax2.set_xlim(0, max(vals) * 1.22)

    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_model.png"), dpi=200, facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------- figure 4
def fig_latency():
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    lats = [r["latency_ms"] for r in report["results"]]
    flagged = [r["latency_ms"] for r in report["results"]
               if r["latency_ms"] > 1000]
    bins = np.logspace(np.log10(max(min(lats), 0.5)),
                       np.log10(max(lats) * 1.15), 26)
    ax.hist(lats, bins=bins, color=NAVY, alpha=0.85, zorder=3, label="All responses")
    if flagged:
        ax.hist(flagged, bins=bins, color=RED, zorder=4,
                label=f"Flagged as slow (>1000 ms): {len(flagged)}")
    ax.axvline(1000, ls="--", lw=1.3, color=RED, zorder=5)
    ax.text(1080, ax.get_ylim()[1] * 0.82, "1000 ms\nthreshold",
            color=RED, fontsize=8.5)
    ax.set_xlabel("Response latency (ms, log scale)")
    ax.set_ylabel("Responses")
    ax.set_xscale("log")
    ax.set_title("Observed response-latency distribution",
                 fontsize=11.5, fontweight="bold", color=NAVY, pad=10)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", color=LIGHT, zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_latency.png"), dpi=200, facecolor="white")
    plt.close(fig)


for fn in (fig_baseline, fig_categories, fig_confusion_and_features, fig_latency):
    fn()
    print("rendered", fn.__name__)
