"""
Evaluation harness.

Produces the numbers reported in the paper:
  1. Full pipeline vs. a conventional "happy-path only" baseline suite
  2. Repeat runs to report variance in detection and runtime
  3. Stratified k-fold cross-validation of the supervised detector
     (more honest than a single hold-out split)
"""
from __future__ import annotations
import json
import os
import sys
import time
from typing import Any, Dict, List

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from m1_spec_parser import SpecParser                       # noqa: E402
from m2_test_generator import TestGenerator                  # noqa: E402
from m3_executor import ExecutionEngine                      # noqa: E402
from m4_anomaly_detector import (AnomalyDetector, RiskEngine,  # noqa: E402
                                 featurize, heuristic_label, FEATURE_NAMES)
from run_pipeline import evaluate_defect_detection           # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "demo_api", "petstore_openapi.json")
ARTIFACTS = os.path.join(ROOT, "artifacts")


def run_suite(cases, base_url) -> List:
    engine = ExecutionEngine(base_url)
    return engine.run_all(cases, progress=False)


def detect_and_rank(results, dep_graph, endpoints):
    det = AnomalyDetector()
    det.fit(results)
    findings = det.detect(results)
    blast = {ep.signature: len([1 for deps in dep_graph.values()
                                if ep.signature in deps]) for ep in endpoints}
    return RiskEngine().score(findings, blast_radius=blast), det


def main() -> Dict[str, Any]:
    parser = SpecParser.from_file(SPEC)
    endpoints = parser.parse()
    dep_graph = parser.dependency_graph(endpoints)
    base_url = parser.base_url()

    engine = ExecutionEngine(base_url)
    if not engine.wait_until_ready():
        print("target API not reachable; start demo_api/target_api.py first")
        sys.exit(1)

    gen = TestGenerator()
    all_cases = gen.generate_all(endpoints)

    print("=" * 74)
    print("EVALUATION HARNESS")
    print("=" * 74)

    # ---------------------------------------------------------------- 1
    print("\n[1] Baseline comparison -- conventional happy-path suite vs. full pipeline")
    baseline_cases = [c for c in all_cases if c.category == "positive"]
    base_results = run_suite(baseline_cases, base_url)
    base_findings, _ = detect_and_rank(base_results, dep_graph, endpoints)
    base_eval = evaluate_defect_detection(base_findings)

    full_results = run_suite(all_cases, base_url)
    full_findings, full_det = detect_and_rank(full_results, dep_graph, endpoints)
    full_eval = evaluate_defect_detection(full_findings)

    print(f"    happy-path only : {len(baseline_cases):3d} tests -> "
          f"{base_eval['detected_count']}/{base_eval['total_seeded']} defects "
          f"({base_eval['detection_rate']:.1%})")
    print(f"    full pipeline   : {len(all_cases):3d} tests -> "
          f"{full_eval['detected_count']}/{full_eval['total_seeded']} defects "
          f"({full_eval['detection_rate']:.1%})")

    # ---------------------------------------------------------------- 2
    print("\n[2] Repeat runs (n=5) -- stability of detection and runtime")
    runs = []
    for i in range(5):
        t0 = time.perf_counter()
        res = run_suite(all_cases, base_url)
        find, _ = detect_and_rank(res, dep_graph, endpoints)
        ev = evaluate_defect_detection(find)
        dt = time.perf_counter() - t0
        lat = sorted(r.latency_ms for r in res)
        runs.append({
            "run": i + 1,
            "detected": ev["detected_count"],
            "detection_rate": ev["detection_rate"],
            "findings": len(find),
            "wall_s": round(dt, 3),
            "p50_ms": round(lat[len(lat) // 2], 2),
            "p95_ms": round(lat[int(len(lat) * 0.95)], 2),
        })
        print(f"    run {i+1}: {ev['detected_count']}/{ev['total_seeded']} defects, "
              f"{len(find)} findings, {dt:.2f}s, p95={runs[-1]['p95_ms']}ms")

    det_counts = [r["detected"] for r in runs]
    wall_times = [r["wall_s"] for r in runs]
    print(f"    detection : mean={np.mean(det_counts):.1f} sd={np.std(det_counts):.2f}")
    print(f"    runtime   : mean={np.mean(wall_times):.2f}s sd={np.std(wall_times):.2f}s")

    # ---------------------------------------------------------------- 3
    print("\n[3] Stratified 5-fold cross-validation of the supervised detector")
    X = np.array([featurize(r) for r in full_results], dtype=float)
    y = np.array([heuristic_label(r) for r in full_results], dtype=int)
    cv_block: Dict[str, Any] = {"n_samples": int(len(y)), "positive_rate": round(float(y.mean()), 4)}

    if len(set(y)) > 1 and min(np.bincount(y)) >= 5:
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        clf = RandomForestClassifier(n_estimators=200, random_state=42,
                                     class_weight="balanced")
        y_pred = cross_val_predict(clf, X, y, cv=skf)
        p, r_, f1, _ = precision_recall_fscore_support(y, y_pred, average="binary",
                                                       zero_division=0)
        tn, fp, fn, tp = confusion_matrix(y, y_pred, labels=[0, 1]).ravel()
        cv_block.update({
            "precision": round(float(p), 4), "recall": round(float(r_), 4),
            "f1": round(float(f1), 4),
            "false_positive_rate": round(float(fp / (fp + tn)) if (fp + tn) else 0.0, 4),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        })
        print(f"    precision={cv_block['precision']}  recall={cv_block['recall']}  "
              f"F1={cv_block['f1']}  FPR={cv_block['false_positive_rate']}")
        print(f"    confusion: TP={tp} FP={fp} FN={fn} TN={tn}")
    else:
        cv_block["note"] = "class support too small for 5-fold CV"
        print("    " + cv_block["note"])

    print("\n    NOTE: the supervised labels are derived from contract violations")
    print("    (5xx, schema breach, unexpected status, successful security probe).")
    print("    The classifier therefore learns a decision rule that overlaps its own")
    print("    label definition, so these scores measure internal consistency, not")
    print("    generalisation to unseen defect types. Reported as a limitation.")

    # ---------------------------------------------------------------- save
    out = {
        "baseline_vs_full": {
            "baseline": {"tests": len(baseline_cases),
                         "detected": base_eval["detected_count"],
                         "total": base_eval["total_seeded"],
                         "detection_rate": base_eval["detection_rate"],
                         "missed": {k: v["description"] for k, v in base_eval["missed"].items()}},
            "full": {"tests": len(all_cases),
                     "detected": full_eval["detected_count"],
                     "total": full_eval["total_seeded"],
                     "detection_rate": full_eval["detection_rate"],
                     "missed": {k: v["description"] for k, v in full_eval["missed"].items()}},
        },
        "repeat_runs": runs,
        "repeat_summary": {
            "detected_mean": float(np.mean(det_counts)),
            "detected_sd": float(np.std(det_counts)),
            "wall_mean_s": float(np.mean(wall_times)),
            "wall_sd_s": float(np.std(wall_times)),
        },
        "cross_validation": cv_block,
        "defects_by_category_found": {
            did: meta["category"] for did, meta in full_eval["detected"].items()
        },
    }
    path = os.path.join(ARTIFACTS, "evaluation.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n    written: {path}")
    print("=" * 74)
    return out


if __name__ == "__main__":
    main()
