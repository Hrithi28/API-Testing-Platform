"""
Evidence-based labelling of every recorded response from the real-target runs.

Why this exists
---------------
The original detector was trained on *weak* labels derived from the same signals
it receives as features (status, schema violations), so its precision/recall
only measured internal consistency. Here every response gets a label from a
written rubric whose rules rest on EXTERNAL evidence:

  R1  reproducible server error   a 5xx (not 501) that recurs when the request is
                                  re-issued alone, three times, in sequence
  R1x non-deterministic 5xx       a 5xx that does NOT recur sequentially
                                  -> excluded from training/evaluation
  R2  schema/constraint mismatch  a 2xx body that breaks the operation's own
                                  declared response schema (type, required, enum,
                                  min/max, pattern, format)
  R3  undeclared status code      a status the spec does not declare for that
                                  operation (and no 'default' response). This is a
                                  DOCUMENTATION GAP, reported separately and NOT
                                  counted as an actionable defect.
  R0  not a defect (with reason)  501 documented-but-unimplemented; auth disabled
                                  in the default configuration; echo-by-design;
                                  heuristic-only semantic hit reviewed by hand;
                                  status declared in the spec

A 'reviewer_override' column in the exported workbook (1 / 0 / blank) lets a
person overrule any rubric verdict; retrain_detector.py honours it.

usage: python3 src/label_findings.py        (targets must be running)
"""
from __future__ import annotations
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["httpbin", "chroma"]

# hand-reviewed groups of heuristic-only (semantic:) hits -> verdict + reason
SEMANTIC_REVIEWED = {
    ("chroma", "GET /api/v2/auth/identity", "user_id"):
        (0, "user_id is empty because authentication is not configured in a default local server (by design)"),
}


def declared_codes(spec: Dict[str, Any], endpoint: str) -> Optional[set]:
    method, path = endpoint.split(" ", 1)
    op = (spec.get("paths", {}).get(path, {}) or {}).get(method.lower(), {})
    codes = set(str(c) for c in (op.get("responses") or {}))
    return None if "default" in codes else codes


def reproduce(base: str, tc: Dict[str, Any], n: int = 3) -> List[int]:
    from urllib.parse import urlencode
    url = base.rstrip("/") + tc["path"]
    if tc.get("query"):
        url += "?" + urlencode({k: str(v) for k, v in tc["query"].items()})
    kw: Dict[str, Any] = {"headers": {"Accept": "application/json", **(tc.get("headers") or {})}, "timeout": 12}
    if tc.get("body") is not None and tc["method"] in ("POST", "PUT", "PATCH"):
        kw["json"] = tc["body"]
    out = []
    for _ in range(n):
        try:
            out.append(requests.request(tc["method"], url, **kw).status_code)
        except Exception:                                       # noqa: BLE001
            out.append(0)
    return out


def label_target(target: str) -> List[Dict[str, Any]]:
    cfg = json.load(open(os.path.join(ROOT, "targets", f"{target}.json")))
    spec = json.load(open(os.path.join(ROOT, cfg["spec"])))
    rep = json.load(open(os.path.join(ROOT, "artifacts_real", target, "run_report.json")))
    cases = {c["test_id"]: c for c in rep["test_cases"]}
    finding_ids = {f["test_id"]: f for f in rep["with_oracle"]["findings"]}
    rows: List[Dict[str, Any]] = []
    repro_cache: Dict[str, List[int]] = {}

    for r in rep["results"]:
        tid, sc = r["test_id"], r["status_code"]
        hits = rep["oracle_hits"].get(tid, [])
        viol = r["schema_violations"]
        declared = declared_codes(spec, r["endpoint"])
        label, rule, why, rr = 0, "R0", "consistent with the spec / by design", None

        if 500 <= sc < 600 and sc != 501:
            rr = reproduce(cfg["base_url"], cases[tid])
            repro_cache[tid] = rr
            if sum(1 for x in rr if 500 <= x < 600 and x != 501) >= 2:
                label, rule, why = 1, "R1", f"server error reproduced {sum(1 for x in rr if x == sc)}/3 times sequentially"
            else:
                label, rule, why = None, "R1x", f"5xx did not reproduce sequentially {rr} (concurrency-dependent)"
        elif sc == 501:
            label, rule, why = 0, "R0", "501: documented-but-unimplemented operation, not a robustness defect"
        elif viol and 200 <= sc < 300:
            hard = [v for v in viol if not v.startswith("semantic:")]
            if hard:
                label, rule, why = 1, "R2", "response breaks the declared schema: " + hard[0][:120]
            else:
                key = next(((t, r["endpoint"], k) for (t, e, k) in SEMANTIC_REVIEWED
                            if t == target and e == r["endpoint"] and k in viol[0]), None)
                if key:
                    label, why = SEMANTIC_REVIEWED[key]
                    rule = "R0-reviewed"
                else:
                    label, rule, why = None, "REVIEW", "heuristic-only semantic hit awaiting manual review"
        elif declared is not None and str(sc) not in declared and sc != 0 and not (200 <= sc < 300 and not declared):
            label, rule, why = 0, "R3", f"documentation gap: status {sc} is not declared for this operation (declared: {sorted(declared)})"
        elif r["security_probe"] in ("auth-bypass", "bola") and 200 <= sc < 300:
            label, rule, why = 0, "R0", "operation succeeds without credentials: authentication is not enabled in the default configuration"
        elif r["security_probe"] == "injection" and 200 <= sc < 300:
            ctype = (r.get("content_type") or "").lower()
            reflected = any(tok in r["body_preview"].lower() for tok in ("<script>", "or '1'='1", "drop table"))
            if reflected and "html" in ctype:
                label, rule, why = 1, "R2", "injection payload reflected unescaped in an HTML response"
            else:
                label, rule, why = 0, "R0", "payload echoed inside a JSON/plain response by design, not executable"

        rows.append({
            "target": target, "test_id": tid, "endpoint": r["endpoint"], "category": r["category"],
            "intent": r["intent"], "status": sc, "declared_codes": sorted(declared) if declared is not None else "default",
            "url": r["url"], "response_preview": r["body_preview"][:160].replace("\n", " "),
            "is_finding": tid in finding_ids,
            "finding_class": finding_ids[tid]["label"] if tid in finding_ids else "",
            "rubric_label": label, "rule": rule, "rationale": why,
            "repro_statuses": rr or "",
        })
    return rows


def main() -> None:
    allrows: List[Dict[str, Any]] = []
    for t in TARGETS:
        rows = label_target(t)
        allrows += rows
        c = {}
        for x in rows:
            c[x["rule"]] = c.get(x["rule"], 0) + 1
        print(f"{t}: {len(rows)} responses labelled  rules={c}  "
              f"defects={sum(1 for x in rows if x['rubric_label'] == 1)}")
    out = os.path.join(ROOT, "artifacts_real", "labels.json")
    json.dump(allrows, open(out, "w"), indent=1)
    print("->", out)


if __name__ == "__main__":
    main()
