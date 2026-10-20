"""
CI/CD quality gate for the API testing platform.

Runs the pipeline against a target, reduces the raw findings to ACTIONABLE ones
with the evidence rule, compares them with an accepted-findings baseline, writes
a JUnit report and exits non-zero when a NEW actionable finding appears.

Actionable = (R1) a 5xx other than 501 that reproduces when re-issued alone, or
             (R2) a 2xx response that breaks the operation's declared schema.
Everything else (undeclared status codes, 501, auth disabled by configuration,
heuristic-only hits) is reported as informational and never fails the build.

usage:
  python3 src/ci_gate.py --target targets/httpbin.json                 # gate a run
  python3 src/ci_gate.py --target targets/httpbin.json --update-baseline
exit codes: 0 pass, 1 new actionable findings, 2 pipeline/target error
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from label_findings import reproduce                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fingerprint(kind: str, endpoint: str, detail: str) -> str:
    detail = re.sub(r"\[\d+\]", "[]", detail)                       # ignore array positions
    detail = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27}", "<uuid>", detail)  # ignore generated ids
    return hashlib.sha1(f"{kind}|{endpoint}|{detail}".encode()).hexdigest()[:12]


def actionable_findings(report: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    cases = {c["test_id"]: c for c in report["test_cases"]}
    found: Dict[str, Dict[str, Any]] = {}
    flaky: List[str] = []
    for r in report["results"]:
        sc = r["status_code"]
        if 500 <= sc < 600 and sc != 501:
            rr = reproduce(base_url, cases[r["test_id"]])
            if sum(1 for x in rr if 500 <= x < 600 and x != 501) >= 2:
                fp = fingerprint("server-error", r["endpoint"], str(sc))
                f = found.setdefault(fp, {"fingerprint": fp, "kind": "server-error", "endpoint": r["endpoint"],
                                          "detail": f"HTTP {sc} on malformed/unsupported input (reproduces {sum(1 for x in rr if x == sc)}/3)",
                                          "example_test": r["test_id"], "example_url": r["url"], "count": 0})
                f["count"] += 1
            else:
                flaky.append(r["test_id"])
        elif 200 <= sc < 300:
            hard = [v for v in r["schema_violations"] if not v.startswith("semantic:")]
            if hard:
                fp = fingerprint("schema-mismatch", r["endpoint"], hard[0])
                f = found.setdefault(fp, {"fingerprint": fp, "kind": "schema-mismatch", "endpoint": r["endpoint"],
                                          "detail": hard[0][:200], "example_test": r["test_id"],
                                          "example_url": r["url"], "count": 0})
                f["count"] += 1
    return {"findings": sorted(found.values(), key=lambda f: (f["kind"], f["endpoint"])), "flaky": flaky}


def write_junit(path: str, target: str, act: List[Dict[str, Any]], new_fp: set, total: int, info: Dict[str, int]) -> None:
    suite = ET.Element("testsuite", name=f"api-gate:{target}", tests=str(len(act) + 1),
                       failures=str(len([a for a in act if a["fingerprint"] in new_fp])))
    ET.SubElement(suite, "testcase", classname="api-gate", name=f"pipeline executed {total} generated tests")
    for a in act:
        tc = ET.SubElement(suite, "testcase", classname=a["kind"], name=f"{a['endpoint']} [{a['fingerprint']}]")
        if a["fingerprint"] in new_fp:
            fl = ET.SubElement(tc, "failure", message=a["detail"])
            fl.text = f"{a['count']} generated test(s) hit this. Example: {a['example_test']} -> {a['example_url']}"
        else:
            ET.SubElement(tc, "system-out").text = "accepted in baseline"
    ET.SubElement(suite, "system-out").text = "informational (never fails build): " + json.dumps(info)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="path to a target config JSON")
    ap.add_argument("--baseline", default=os.path.join(ROOT, "ci", "accepted_findings.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "ci", "out"))
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--skip-run", action="store_true", help="reuse the last report in --out")
    args = ap.parse_args()
    cfg = json.load(open(args.target))
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.dirname(args.baseline), exist_ok=True)

    if not args.skip_run:
        p = subprocess.run([sys.executable, os.path.join(ROOT, "src", "real_target_run.py"),
                            os.path.abspath(args.target), "--out", args.out], capture_output=True, text=True)
        if p.returncode != 0:
            print(p.stdout[-800:], p.stderr[-800:])
            print("GATE ERROR: pipeline or target failed")
            sys.exit(2)
    report = json.load(open(os.path.join(args.out, "run_report.json")))
    act = actionable_findings(report, cfg["base_url"])

    baseline = json.load(open(args.baseline)) if os.path.exists(args.baseline) else {}
    base_fp = set(baseline.get(cfg["name"], []))
    cur_fp = {a["fingerprint"] for a in act["findings"]}
    new_fp = cur_fp - base_fp
    resolved = base_fp - cur_fp

    info = {"findings_total": report["with_oracle"]["counts"]["findings"],
            "actionable_distinct": len(act["findings"]),
            "non_reproducible_5xx": len(act["flaky"])}
    write_junit(os.path.join(args.out, "junit.xml"), cfg["name"], act["findings"], new_fp,
                report["counts"]["executed"], info)
    json.dump({"target": cfg["name"], "new": sorted(new_fp), "resolved": sorted(resolved),
               "actionable": act["findings"], "info": info},
              open(os.path.join(args.out, "gate_summary.json"), "w"), indent=1)

    print(f"[gate] {cfg['name']}: {report['counts']['executed']} tests, "
          f"{info['findings_total']} raw findings -> {info['actionable_distinct']} distinct actionable "
          f"({len(new_fp)} new, {len(resolved)} resolved, {info['non_reproducible_5xx']} non-reproducible 5xx ignored)")
    for a in act["findings"]:
        tag = "NEW " if a["fingerprint"] in new_fp else "known"
        print(f"  [{tag}] {a['kind']:15s} {a['endpoint'][:70]}  - {a['detail'][:90]}")

    if args.update_baseline:
        baseline[cfg["name"]] = sorted(cur_fp)
        json.dump(baseline, open(args.baseline, "w"), indent=1)
        print(f"[gate] baseline updated ({len(cur_fp)} accepted findings) -> {args.baseline}")
        sys.exit(0)
    if new_fp:
        print("[gate] FAIL: new actionable findings")
        sys.exit(1)
    print("[gate] PASS")


if __name__ == "__main__":
    main()
