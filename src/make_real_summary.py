"""Consolidate the real-target evaluation into artifacts_real/real_summary.json and one figure."""
import json, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "artifacts_real")
labels = json.load(open(f"{A}/labels.json"))
S = {"targets": {}}
for t in ("httpbin", "chroma"):
    rep = json.load(open(f"{A}/{t}/run_report.json"))
    rows = [x for x in labels if x["target"] == t and x["is_finding"]]
    def cls(x):
        if x["rule"] in ("R1", "R2"): return "actionable"
        if x["rule"] == "R3": return "doc_gap"
        if x["rule"] == "R1x": return "flaky"
        if x["status"] == 501: return "unimplemented"
        return "by_design"
    c = collections.Counter(cls(x) for x in rows)
    S["targets"][t] = {
        "description": rep["description"], "operations": rep["counts"]["operations"],
        "tests": rep["counts"]["test_cases"], "by_category": rep["counts"]["by_category"],
        "server_errors_5xx": rep["counts"]["server_errors"],
        "raw_findings_baseline": rep["baseline"]["counts"]["findings"],
        "raw_findings_with_oracle": rep["with_oracle"]["counts"]["findings"],
        "oracle_flagged_responses": rep["counts"]["oracle_flagged_responses"],
        "triage": {k: c.get(k, 0) for k in ("actionable", "doc_gap", "unimplemented", "by_design", "flaky")},
        "runtime_s": rep["timings"]["total_s"],
    }
tot = {k: sum(S["targets"][t]["triage"][k] for t in S["targets"]) for k in S["targets"]["httpbin"]["triage"]}
S["total_raw_findings"] = sum(tot.values()); S["total_triage"] = tot
S["oracle_mutation"] = json.load(open(f"{A}/oracle_mutation.json"))
S["retrain"] = json.load(open(f"{A}/retrain_results.json"))
json.dump(S, open(f"{A}/real_summary.json", "w"), indent=1)

# ---- figure: where the raw findings go
order = [("actionable", "Actionable defect", "#335295"), ("doc_gap", "Documentation gap (undeclared status)", "#7f7f7f"),
         ("unimplemented", "501 documented but unimplemented", "#b0b0b0"), ("by_design", "By design / expected", "#d9d9d9"),
         ("flaky", "Not reproducible", "#000000")]
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
names = ["httpbin", "ChromaDB"]
for i, t in enumerate(("httpbin", "chroma")):
    left = 0
    for key, lab, col in order:
        v = S["targets"][t]["triage"][key]
        ax.barh(i, v, left=left, color=col, edgecolor="white", label=lab if i == 0 else None)
        if v >= 6: ax.text(left + v / 2, i, str(v), ha="center", va="center", fontsize=9, color="white" if col in ("#335295", "#7f7f7f", "#000000") else "black")
        left += v
    ax.text(left + 4, i, f"{left} raw findings", va="center", fontsize=9)
ax.set_yticks([0, 1]); ax.set_yticklabels(names); ax.invert_yaxis()
ax.set_xlabel("Findings raised by the platform"); ax.set_xlim(0, 270)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
fig.tight_layout(); fig.savefig(f"{A}/fig_real_triage.png"); 
print(json.dumps({k: S[k] for k in ("total_raw_findings", "total_triage")}, indent=1))
for t, v in S["targets"].items(): print(t, v["operations"], "ops", v["tests"], "tests", v["triage"], "runtime", v["runtime_s"])
