"""
Run the full pipeline (M1-M5 + semantic oracle) against a REAL, locally hosted
open-source service described by a JSON target config.

usage:  python3 src/real_target_run.py <target-name> [--out DIR]

One execution pass is made. The recorded responses are then analysed twice:
  baseline     -- the original Module 3 contract checks only
  with_oracle  -- plus the Module 3b specification-driven semantic oracle
so the oracle's contribution can be isolated.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
from typing import Any, Dict, List

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m1x_real_parser import RealSpecParser                        # noqa: E402
from m2_test_generator import TestGenerator, SchemaRuleBackend    # noqa: E402
from m3_executor import ExecutionEngine, ExecutionResult, schema_violations  # noqa: E402
from m3b_semantic_oracle import SemanticOracle                    # noqa: E402
from m4_anomaly_detector import AnomalyDetector, RiskEngine       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
class FixtureBackend(SchemaRuleBackend):
    """Schema-rule generator that fills path parameters with real fixture values."""

    def __init__(self, cfg: Dict[str, Any], fixtures: Dict[str, Any]):
        super().__init__()
        self.cfg = cfg
        self.fixtures = fixtures
        self._method = "GET"

    def _fill_path(self, ep, override=None):
        override = override or {}
        by_method = self.cfg.get("fixtures_by_method", {}).get(ep.method, {})
        path = ep.path
        for p in ep.parameters:
            if p.location == "path":
                if p.name in override:
                    val = override[p.name]
                elif p.name in by_method:
                    val = by_method[p.name]
                elif p.name in self.fixtures:
                    val = self.fixtures[p.name]
                else:
                    val = self.valid_value(p.schema)
                path = path.replace("{" + p.name + "}", str(val))
        return path

    def generate(self, ep, auth_token="Bearer user-100"):
        cases = super().generate(ep, auth_token)
        extra = self.cfg.get("extra_expected_by_method", {}).get(ep.method, [])
        for tc in cases:
            if extra:
                tc.expected_status = list(dict.fromkeys(tc.expected_status + extra))
            tc.headers = {**self.cfg.get("default_headers", {}), **tc.headers}
        return cases


def run_with_bodies(engine: ExecutionEngine, cases) -> (List[ExecutionResult], Dict[str, Any]):
    """Execute all cases once, capturing full parsed JSON bodies."""
    from urllib.parse import urlencode
    bodies: Dict[str, Any] = {}
    results: List[ExecutionResult] = []

    def one(tc):
        url = engine.base_url + tc.path
        if tc.query:
            url += "?" + urlencode({k: str(v) for k, v in tc.query.items()})
        kwargs: Dict[str, Any] = {"headers": {"Accept": "application/json", **tc.headers},
                                  "timeout": engine.timeout}
        if tc.body is not None and tc.method in ("POST", "PUT", "PATCH"):
            kwargs["json"] = tc.body
        t0 = time.perf_counter()
        try:
            resp = requests.request(tc.method, url, **kwargs)
            lat = (time.perf_counter() - t0) * 1000.0
            try:
                parsed = resp.json()
                preview = json.dumps(parsed)[:400]
            except ValueError:
                parsed, preview = None, resp.text[:400]
            exp_schema = tc.expect_schema if 200 <= resp.status_code < 300 else None
            viol = schema_violations(parsed, exp_schema) if parsed is not None else []
            r = ExecutionResult(
                test_id=tc.test_id, endpoint=tc.endpoint, method=tc.method, url=url,
                category=tc.category, intent=tc.intent, security_probe=tc.security_probe,
                status_code=resp.status_code, latency_ms=round(lat, 2),
                expected_status=tc.expected_status,
                status_as_expected=resp.status_code in tc.expected_status,
                schema_violations=viol, response_size=len(resp.content),
                content_type=resp.headers.get("Content-Type", ""), body_preview=preview)
            if parsed is not None and len(resp.content) < 200_000:
                bodies[tc.test_id] = parsed
            return r
        except Exception as exc:                                    # noqa: BLE001
            lat = (time.perf_counter() - t0) * 1000.0
            return ExecutionResult(
                test_id=tc.test_id, endpoint=tc.endpoint, method=tc.method, url=url,
                category=tc.category, intent=tc.intent, security_probe=tc.security_probe,
                status_code=0, latency_ms=round(lat, 2), expected_status=tc.expected_status,
                status_as_expected=False, error=f"{type(exc).__name__}: {exc}")

    with cf.ThreadPoolExecutor(max_workers=engine.workers) as pool:
        for r in pool.map(one, cases):
            results.append(r)
    results.sort(key=lambda r: r.test_id)
    return results, bodies


# ---------------------------------------------------------------------------
def setup_chroma(base: str) -> Dict[str, Any]:
    """Create one populated collection so path-parameterised endpoints have a real target."""
    t, d = "default_tenant", "default_database"
    url = f"{base}/api/v2/tenants/{t}/databases/{d}/collections"
    r = requests.post(url, json={"name": "qa_primary", "get_or_create": True}, timeout=15)
    r.raise_for_status()
    cid = r.json()["id"]
    requests.post(f"{url}/{cid}/add", timeout=15, json={
        "ids": ["a", "b", "c"], "embeddings": [[0.1, 0.2, 0.3], [0.2, 0.1, 0.4], [0.9, 0.8, 0.7]],
        "documents": ["alpha", "beta", "gamma"], "metadatas": [{"k": 1}, {"k": 2}, {"k": 3}]})
    return {"collection_id": cid}


SETUPS = {"chroma": setup_chroma}


def analyse(results: List[ExecutionResult], endpoints, dep_graph, label: str) -> Dict[str, Any]:
    detector = AnomalyDetector()
    metrics = detector.fit(results)
    findings = detector.detect(results)
    blast = {ep.signature: len([1 for deps in dep_graph.values() if ep.signature in deps])
             for ep in endpoints}
    findings = RiskEngine().score(findings, blast_radius=blast)
    tiers = {p: sum(1 for f in findings if f.priority == p) for p in ("P1", "P2", "P3", "P4")}
    by_label: Dict[str, int] = {}
    for f in findings:
        by_label[f.label] = by_label.get(f.label, 0) + 1
    return {"variant": label, "findings": [f.to_dict() for f in findings],
            "counts": {"findings": len(findings), "priority_tiers": tiers, "by_label": by_label},
            "model_metrics": metrics}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    cfg_path = args.target if args.target.endswith(".json") else os.path.join(ROOT, "targets", f"{args.target}.json")
    with open(cfg_path) as fh:
        cfg = json.load(fh)
    cfg.setdefault("_root", os.path.dirname(os.path.abspath(cfg_path)))
    out_dir = args.out or os.path.join(ROOT, "artifacts_real", cfg["name"])
    os.makedirs(out_dir, exist_ok=True)
    t_start = time.perf_counter()

    parser = RealSpecParser.from_file(cfg["spec"] if os.path.isabs(cfg["spec"]) else os.path.join(ROOT, cfg["spec"]))
    endpoints = [e for e in parser.parse()
                 if not any(re.search(rx, e.signature) for rx in cfg.get("exclude", []))]
    dep_graph = parser.dependency_graph(endpoints)
    print(f"[M1] {cfg['name']}: {len(endpoints)} operations "
          f"({'Swagger 2.0' if parser.swagger2 else 'OpenAPI ' + str(parser.spec.get('openapi'))})")

    engine = ExecutionEngine(cfg["base_url"], timeout=12.0, workers=args.workers)
    if not engine.wait_until_ready(cfg["health_path"]):
        sys.exit(f"target not reachable at {cfg['base_url']}")

    fixtures = dict(cfg.get("fixtures", {}))
    if cfg.get("setup"):
        fixtures.update(SETUPS[cfg["setup"]](cfg["base_url"]))
        print(f"[setup] fixtures: {fixtures}")

    gen = TestGenerator(backend=FixtureBackend(cfg, fixtures))
    cases = gen.generate_all(endpoints)
    by_cat = {}
    for c in cases:
        by_cat[c.category] = by_cat.get(c.category, 0) + 1
    print(f"[M2] {len(cases)} test cases  {by_cat}")

    t0 = time.perf_counter()
    results, bodies = run_with_bodies(engine, cases)
    exec_s = time.perf_counter() - t0
    print(f"[M3] executed {len(results)} calls in {exec_s:.1f}s; "
          f"5xx={sum(r.is_server_error for r in results)} "
          f"unexpected={sum(not r.status_as_expected for r in results)} "
          f"transport-errors={sum(1 for r in results if r.error)}")

    # ---- Module 3b: oracle over every recorded 2xx JSON response
    ep_by_sig = {e.signature: e for e in endpoints}
    case_by_id = {c.test_id: c for c in cases}
    oracle = SemanticOracle()
    oracle_hits: Dict[str, List[str]] = {}
    for r in results:
        if not (200 <= r.status_code < 300) or r.test_id not in bodies:
            continue
        ep = ep_by_sig[r.endpoint]
        schema = None
        for code in sorted(ep.response_schemas):
            if code.startswith("2"):
                schema = ep.response_schemas[code]
                break
        v = oracle.check(schema, bodies[r.test_id], case_by_id[r.test_id].query)
        if v:
            oracle_hits[r.test_id] = v
    n_con = sum(1 for vs in oracle_hits.values() for v in vs if v.startswith("constraint:"))
    n_sem = sum(1 for vs in oracle_hits.values() for v in vs if v.startswith("semantic:"))
    print(f"[M3b] oracle: {len(oracle_hits)} responses flagged "
          f"({n_con} constraint, {n_sem} semantic violations)")

    baseline = analyse(results, endpoints, dep_graph, "baseline")
    import copy
    enhanced_results = copy.deepcopy(results)
    for r in enhanced_results:
        r.schema_violations = list(r.schema_violations) + oracle_hits.get(r.test_id, [])
    with_oracle = analyse(enhanced_results, endpoints, dep_graph, "with_oracle")
    print(f"[M4/M5] findings: baseline={baseline['counts']['findings']}  "
          f"with_oracle={with_oracle['counts']['findings']}")

    covered = {r.endpoint for r in results}
    report = {
        "target": cfg["name"], "description": cfg["description"],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "counts": {
            "operations": len(endpoints), "test_cases": len(cases), "by_category": by_cat,
            "executed": len(results),
            "server_errors": sum(r.is_server_error for r in results),
            "unexpected_status": sum(not r.status_as_expected for r in results),
            "transport_errors": sum(1 for r in results if r.error),
            "endpoint_coverage": round(len(covered) / len(endpoints), 4),
            "oracle_flagged_responses": len(oracle_hits),
            "oracle_constraint_violations": n_con, "oracle_semantic_violations": n_sem,
        },
        "timings": {"execute_s": round(exec_s, 2), "total_s": round(time.perf_counter() - t_start, 2)},
        "baseline": baseline, "with_oracle": with_oracle,
        "oracle_hits": oracle_hits,
        "results": [r.to_dict() for r in results],
        "test_cases": [c.to_dict() for c in cases],
    }
    path = os.path.join(out_dir, "run_report.json")
    with open(path, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"[M6] report -> {path}")


if __name__ == "__main__":
    main()
