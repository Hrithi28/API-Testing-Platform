"""
Generates the system-architecture block diagram into artifacts/block_diagram.png.

Layout: two straight left-to-right rows (not a snake), so reading order can
never be ambiguous. Row 1 is parse -> generate -> execute. Row 2 continues
from where row 1 ends: detect -> prioritise -> report -> integrate.
This matches the exact module order run_pipeline.py itself executes in.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts")

NAVY = "#335295"; NAVY_D = "#1B2A4A"; TEAL = "#2E8B7C"
AMBER = "#D98E2B"; PLUM = "#8E5FA8"; RED = "#B5484D"; GREY = "#5A6472"


def build(out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(12.6, 5.9))
    ax.set_xlim(0, 12.6); ax.set_ylim(0, 5.9); ax.axis("off")

    def box(x, y, w, h, title, sub, color, fc, dashed=False):
        style = (0, (5, 3)) if dashed else "solid"
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.02,rounding_size=0.07",
                     linewidth=1.8, edgecolor=color, facecolor=fc, zorder=3,
                     linestyle=style))
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=10.2, weight="bold", color=NAVY_D, zorder=4, linespacing=1.25)
        ax.text(x + w / 2, y + h * 0.22, sub, ha="center", va="center",
                fontsize=8.0, color=GREY, zorder=4, style="italic")
        return (x, y, w, h)

    def arrow(b1, b2, color=GREY, side="rl", lw=1.9):
        x1, y1, w1, h1 = b1; x2, y2, w2, h2 = b2
        pts = {
            "rl": ((x1 + w1, y1 + h1 / 2), (x2, y2 + h2 / 2)),
            "lr": ((x1, y1 + h1 / 2), (x2 + w2, y2 + h2 / 2)),
            "bt": ((x1 + w1 / 2, y1), (x2 + w2 / 2, y2 + h2)),
            "tb": ((x1 + w1 / 2, y1 + h1), (x2 + w2 / 2, y2)),
        }[side]
        ax.add_patch(FancyArrowPatch(pts[0], pts[1], arrowstyle="->", mutation_scale=14,
                     color=color, linewidth=lw, connectionstyle="arc3,rad=0.0", zorder=2))

    gap = 0.24

    # ---------------- Row 1: parse -> generate -> execute --------------
    y1 = 3.75
    x = 0.25
    b_spec = box(x, y1, 2.35, 1.3, "API Specification", "OpenAPI 3.x / Swagger", NAVY, "#EDF1F8")
    x += 2.35 + gap
    b_m1 = box(x, y1, 2.75, 1.3, "M1  Spec Parser &\nEndpoint Extractor", "$ref resolution, dependency graph", NAVY, "#EDF1F8")
    x += 2.75 + gap
    b_m2 = box(x, y1, 2.55, 1.3, "M2  Test Case\nGenerator", "positive / negative /\nboundary / security", TEAL, "#E4F1ED")
    x += 2.55 + gap
    b_m3 = box(x, y1, 2.85, 1.3, "M3  Execution Engine &\nResponse Collector", "parallel, dependency-ordered", AMBER, "#FAF0E1")

    arrow(b_spec, b_m1, NAVY, side="rl")
    arrow(b_m1, b_m2, NAVY, side="rl")
    arrow(b_m2, b_m3, TEAL, side="rl")

    ax.text(6.35, y1 + 1.62, "1.  Parse   \u2192   2.  Generate   \u2192   3.  Execute",
            ha="center", fontsize=9.5, color="#8A94A3", style="italic")

    # ---------------- Row 2: detect -> prioritise -> report -> integrate
    y2 = 1.15
    x = 0.25
    b_m4 = box(x, y2, 2.55, 1.3, "M4  Anomaly\nDetector", "IsolationForest +\nRandomForest", RED, "#F7E7E8")
    x += 2.55 + gap
    b_m5 = box(x, y2, 2.75, 1.3, "M5  Risk-based\nPrioritisation", "P1\u2013P4 tiering", PLUM, "#F1E9F5")
    x += 2.75 + gap
    b_m6a = box(x, y2, 2.85, 1.3, "M6  Reporting\nDashboard", "risk-ranked findings,\ncoverage, defect register", NAVY, "#EDF1F8")
    x += 2.85 + gap
    b_m6b = box(x, y2, 2.35, 1.3, "CI/CD Integration", "planned \u2014 Review 3", GREY, "#F1F2F4", dashed=True)

    arrow(b_m4, b_m5, RED, side="rl")
    arrow(b_m5, b_m6a, PLUM, side="rl")
    ax.add_patch(FancyArrowPatch(
        (b_m6a[0] + b_m6a[2], y2 + b_m6a[3] / 2), (b_m6b[0], y2 + b_m6b[3] / 2),
        arrowstyle="->", mutation_scale=14, color=GREY, linewidth=1.6,
        linestyle=(0, (4, 3)), zorder=2))

    ax.text(6.35, y2 - 0.30, "4.  Detect   \u2192   5.  Prioritise   \u2192   6.  Report   \u2192   Integrate (planned)",
            ha="center", fontsize=9.5, color="#8A94A3", style="italic")

    # elbow connector: M3 (end of row 1) -> M4 (start of row 2), routed through
    # the empty corridor between the rows so it never crosses another box
    m3_bottom_x = b_m3[0] + b_m3[2] / 2
    m4_top_x = b_m4[0] + b_m4[2] / 2
    y_mid = y1 - 0.45
    ax.plot([m3_bottom_x, m3_bottom_x], [y1, y_mid], color=AMBER, linewidth=2.2, zorder=2, solid_capstyle="round")
    ax.plot([m3_bottom_x, m4_top_x], [y_mid, y_mid], color=AMBER, linewidth=2.2, zorder=2, solid_capstyle="round")
    ax.add_patch(FancyArrowPatch((m4_top_x, y_mid), (m4_top_x, y2 + b_m4[3]),
                 arrowstyle="->", mutation_scale=16, color=AMBER, linewidth=2.2, zorder=2))

    # feedback loop: M6 dashboard back to M2 (dashed, informational)
    ax.add_patch(FancyArrowPatch(
        (b_m6a[0] + 0.3, y2 + b_m6a[3]), (b_m2[0] + b_m2[2] * 0.7, y1),
        arrowstyle="->", mutation_scale=11, color="#B7C2D0", linewidth=1.3,
        linestyle=(0, (4, 3)), connectionstyle="arc3,rad=0.28", zorder=1))
    ax.text(0.25, 0.22, "Dashed: feedback loop \u2014 confirmed findings inform the next generation cycle",
            fontsize=8.4, color="#8A94A3", style="italic")

    # legend: solid = implemented, dashed = planned
    ax.add_patch(FancyBboxPatch((9.55, 5.35), 0.32, 0.18, boxstyle="round,pad=0.01",
                 linewidth=1.6, edgecolor=NAVY, facecolor="#EDF1F8", zorder=4))
    ax.text(9.98, 5.44, "implemented (M1\u2013M6)", fontsize=7.6, color="#5A6472", va="center")
    ax.add_patch(FancyBboxPatch((9.55, 5.08), 0.32, 0.18, boxstyle="round,pad=0.01",
                 linewidth=1.6, edgecolor=GREY, facecolor="#F1F2F4", zorder=4, linestyle=(0, (5, 3))))
    ax.text(9.98, 5.17, "planned (Review 3)", fontsize=7.6, color="#5A6472", va="center")

    plt.tight_layout()
    plt.savefig(out_path, dpi=210, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(ART, exist_ok=True)
    out = os.path.join(ART, "block_diagram.png")
    build(out)
    print(f"diagram written: {out} ({os.path.getsize(out)//1024} KB)")
