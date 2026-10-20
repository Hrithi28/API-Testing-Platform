"""
End-to-end pipeline runner for the AI-Powered Intelligent API Testing Platform.

    Module 1  parse spec
    Module 2  generate test cases
    Module 3  execute + collect responses
    Module 4  detect anomalies (ML)
    Module 5  risk-score and prioritise
    Module 6  emit report artifacts

Also computes the evaluation metrics reported in the paper: endpoint coverage,
defect-detection rate against the seeded-defect register, classifier
precision/recall/F1, false-positive rate, and runtime.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from m1_spec_parser import SpecParser                     # noqa: E402
from m2_test_generator import TestGenerator, CATEGORIES    # noqa: E402
from m3_executor import ExecutionEngine                    # noqa: E402
from m4_anomaly_detector import AnomalyDetector, RiskEngine, heuristic_label  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "demo_api", "petstore_openapi.json")
ARTIFACTS = os.path.join(ROOT, "artifacts")


# ---------------------------------------------------------------------------
#  Evaluation against the seeded-defect ground truth
# ---------------------------------------------------------------------------
# Each seeded defect maps to a detection rule over the findings. The pipeline
# itself never sees this -- it is applied afterwards, purely for scoring.
DEFECT_MATCHERS = {
    "D1": lambda f: f.endpoint == "GET /pets/{petId}" and f.status_code >= 500,
    "D2": lambda f: f.endpoint == "POST /pets" and "required" in f.intent.lower()
                    and 200 <= f.status_code < 300,
    "D3": lambda f: f.endpoint == "GET /orders/{orderId}" and "bola" in f.intent.lower(),
    "D4": lambda f: f.endpoint == "GET /pets" and f.label == "performance",
    "D5": lambda f: f.endpoint == "POST /pets" and f.status_code >= 500,
    "D6": lambda f: f.endpoint == "GET /pets/search" and f.label == "security",
    "D7": lambda f: f.endpoint == "DELETE /pets/{petId}"
                    and "without an authentication" in f.intent.lower()
                    and 200 <= f.status_code < 300,
    "D8": lambda f: f.endpoint == "GET /pets/{petId}" and f.label == "schema-drift",
}


def evaluate_defect_detection(findings) -> Dict[str, Any]:
    sys.path.insert(0, os.path.join(ROOT, "demo_api"))
    from target_api import SEEDED_DEFECTS                 # noqa: E402

    detected, missed = {}, {}
    for did, meta in SEEDED_DEFECTS.items():
        matcher = DEFECT_MATCHERS.get(did)
        hits = [f for f in findings if matcher and matcher(f)] if matcher else []
        if hits:
            best = max(hits, key=lambda f: f.risk_score)
            detected[did] = {
                "description": meta["description"],
                "category": meta["category"],
                "endpoint": meta["endpoint"],
                "found_by": best.test_id,
                "priority": best.priority,
                "risk_score": best.risk_score,
            }
        else:
            missed[did] = meta
    total = len(SEEDED_DEFECTS)
    return {
        "total_seeded": total,
        "detected_count": len(detected),
        "detection_rate": round(len(detected) / total, 4) if total else 0.0,
        "detected": detected,
        "missed": missed,
    }


# ---------------------------------------------------------------------------
def main() -> Dict[str, Any]:
    os.makedirs(ARTIFACTS, exist_ok=True)
    wall_start = time.perf_counter()
    timings: Dict[str, float] = {}

    print("=" * 74)
    print("AI-POWERED INTELLIGENT API TESTING PLATFORM  --  pipeline run")
    print("=" * 74)

    # ---------------- Module 1 ----------------
    t0 = time.perf_counter()
    parser = SpecParser.from_file(SPEC)
    endpoints = parser.parse()
    dep_graph = parser.dependency_graph(endpoints)
    base_url = parser.base_url()
    timings["m1_parse_s"] = round(time.perf_counter() - t0, 3)
    print(f"\n[M1] Spec parsed        : {len(endpoints)} endpoints from {os.path.basename(SPEC)}")
    print(f"     base URL           : {base_url}")
    print(f"     dependency links   : {sum(1 for v in dep_graph.values() if v)}")

    # ---------------- Module 2 ----------------
    t0 = time.perf_counter()
    gen = TestGenerator()
    cases = gen.generate_all(endpoints)
    timings["m2_generate_s"] = round(time.perf_counter() - t0, 3)
    by_cat = {c: sum(1 for t in cases if t.category == c) for c in CATEGORIES}
    print(f"\n[M2] Test cases         : {len(cases)}  (backend: {gen.backend.name})")
    for c in CATEGORIES:
        print(f"     {c:9s}          : {by_cat[c]}")

    # ---------------- Module 3 ----------------
    engine = ExecutionEngine(base_url)
    if not engine.wait_until_ready():
        print("\n!! target API is not reachable at " + base_url)
        print("   start it first:  python3 demo_api/target_api.py")
        sys.exit(1)

    t0 = time.perf_counter()
    print(f"\n[M3] Executing {len(cases)} test cases against {base_url} ...")
    results = engine.run_all(cases)
    timings["m3_execute_s"] = round(time.perf_counter() - t0, 3)

    n_5xx = sum(1 for r in results if r.is_server_error)
    n_unexpected = sum(1 for r in results if not r.status_as_expected)
    n_schema = sum(1 for r in results if r.schema_violations)
    lat = sorted(r.latency_ms for r in results)
    p50 = lat[len(lat) // 2]
    p95 = lat[int(len(lat) * 0.95)]
    print(f"     completed          : {len(results)} calls in {timings['m3_execute_s']}s")
    print(f"     5xx responses      : {n_5xx}")
    print(f"     unexpected status  : {n_unexpected}")
    print(f"     schema violations  : {n_schema}")
    print(f"     latency p50 / p95  : {p50:.1f} ms / {p95:.1f} ms")

    # ---------------- Module 4 ----------------
    t0 = time.perf_counter()
    detector = AnomalyDetector()
    model_metrics = detector.fit(results)
    findings = detector.detect(results)
    timings["m4_detect_s"] = round(time.perf_counter() - t0, 3)
    print(f"\n[M4] Anomaly detection  : {len(findings)} findings from {len(results)} responses")
    if "precision" in model_metrics:
        print(f"     RF precision       : {model_metrics['precision']}")
        print(f"     RF recall          : {model_metrics['recall']}")
        print(f"     RF F1              : {model_metrics['f1']}")
        print(f"     false-positive rate: {model_metrics['false_positive_rate']}")
    top_feats = list(model_metrics.get("feature_importance", {}).items())[:4]
    print(f"     top features       : {', '.join(f'{k}={v}' for k, v in top_feats)}")

    # ---------------- Module 5 ----------------
    t0 = time.perf_counter()
    blast = {ep.signature: len([1 for deps in dep_graph.values()
                                if ep.signature in deps]) for ep in endpoints}
    risk = RiskEngine()
    findings = risk.score(findings, blast_radius=blast)
    timings["m5_prioritise_s"] = round(time.perf_counter() - t0, 3)
    tiers = {p: sum(1 for f in findings if f.priority == p) for p in ("P1", "P2", "P3", "P4")}
    print(f"\n[M5] Risk prioritisation: " +
          "  ".join(f"{k}={v}" for k, v in tiers.items()))
    print("     top 5 findings     :")
    for f in findings[:5]:
        print(f"       [{f.priority}] {f.risk_score:.2f}  {f.endpoint:24s} {f.label:13s} {f.test_id}")

    # ---------------- evaluation ----------------
    defect_eval = evaluate_defect_detection(findings)
    covered = {r.endpoint for r in results}
    coverage = len(covered) / len(endpoints) if endpoints else 0.0

    total_params = sum(len(e.parameters) for e in endpoints)
    exercised_params = set()
    for tc in cases:
        for k in tc.query:
            exercised_params.add((tc.endpoint, k))
        for p in (e for e in endpoints if e.signature == tc.endpoint):
            for prm in p.parameters:
                if prm.location == "path" and "{" not in tc.path:
                    exercised_params.add((tc.endpoint, prm.name))
    param_coverage = len(exercised_params) / total_params if total_params else 1.0

    wall = round(time.perf_counter() - wall_start, 3)
    timings["total_s"] = wall

    print(f"\n[EVAL] Endpoint coverage : {coverage:.1%}  ({len(covered)}/{len(endpoints)})")
    print(f"       Parameter coverage: {param_coverage:.1%}")
    print(f"       Defects detected  : {defect_eval['detected_count']}/{defect_eval['total_seeded']} "
          f"({defect_eval['detection_rate']:.1%})")
    if defect_eval["missed"]:
        for did, meta in defect_eval["missed"].items():
            print(f"         MISSED {did}: {meta['description']}")
    print(f"       Total runtime     : {wall}s")

    # ---------------- Module 6: artifacts ----------------
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "spec_file": os.path.basename(SPEC),
        "base_url": base_url,
        "generator_backend": gen.backend.name,
        "endpoints": [e.to_dict() for e in endpoints],
        "dependency_graph": dep_graph,
        "counts": {
            "endpoints": len(endpoints),
            "test_cases": len(cases),
            "by_category": by_cat,
            "executed": len(results),
            "server_errors": n_5xx,
            "unexpected_status": n_unexpected,
            "schema_violations": n_schema,
            "findings": len(findings),
            "priority_tiers": tiers,
        },
        "latency": {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2),
                    "max_ms": round(max(lat), 2), "mean_ms": round(sum(lat) / len(lat), 2)},
        "model_metrics": model_metrics,
        "coverage": {"endpoint_coverage": round(coverage, 4),
                     "parameter_coverage": round(param_coverage, 4),
                     "endpoints_covered": sorted(covered)},
        "defect_evaluation": defect_eval,
        "timings": timings,
        "findings": [f.to_dict() for f in findings],
        "results": [r.to_dict() for r in results],
        "test_cases": [c.to_dict() for c in cases],
    }
    out = os.path.join(ARTIFACTS, "run_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[M6] Report written     : {out}")
    print("=" * 74)
    return report


if __name__ == "__main__":
    main()
