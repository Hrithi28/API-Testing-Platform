"""
Mutation study for the Module 3b semantic oracle.

On the real services the oracle found no extra defects (their specs say little about
what values mean), which says nothing about its sensitivity. This study measures
sensitivity directly: take REAL 2xx responses from the ChromaDB server, inject one
semantic fault at a time, and record which checker notices.

  baseline = Module 3 checker (type / required / enum only)
  oracle   = Module 3b (declared constraints + name/description/format/cross-field rules)

Mutation operators
  NEG_NUM     any numeric field made negative
  BAD_TS      a timestamp-named field replaced by a non-date string
  EMPTY_ID    an identifier-named field emptied
  BAD_UUID    a UUID-valued field replaced by a non-UUID string
  COUNT_OFF   a count/size field no longer equals its sibling list length
  LIMIT_EXC   a list longer than the requested limit

A clean control (unmutated responses) measures false alarms.
usage: python3 src/oracle_mutation_study.py   (chroma must be running)
"""
from __future__ import annotations
import copy
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple
from urllib.parse import urlencode

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m1x_real_parser import RealSpecParser                      # noqa: E402
from m3_executor import schema_violations                        # noqa: E402
from m3b_semantic_oracle import (SemanticOracle, NONNEG_NAME, TIME_NAME, ID_NAME,   # noqa: E402
                                 UUID_RE)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def leaves(d: Any, path: Tuple = ()):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from leaves(v, path + (k,))
    elif isinstance(d, list):
        for i, v in enumerate(d[:3]):
            yield from leaves(v, path + (i,))
    else:
        yield path, d


def setp(d: Any, path: Tuple, val: Any) -> Any:
    if not path:
        return val
    d = copy.deepcopy(d)
    cur = d
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = val
    return d


def msgs(v: List[str]) -> set:
    """Distinct violation messages, ignoring array positions (so repeats of one violation count once)."""
    return {re.sub(r"\[\d+\]", "[]", m) for m in v}


def collect(report_path: str = "") -> List[Dict[str, Any]]:
    rep = json.load(open(report_path or os.path.join(ROOT, "artifacts_real", "chroma", "run_report.json")))
    parser = RealSpecParser.from_file(os.path.join(ROOT, "targets", "chroma_openapi.json"))
    eps = {e.signature: e for e in parser.parse()}
    okids = {r["test_id"] for r in rep["results"] if 200 <= r["status_code"] < 300}
    per_ep: Dict[str, int] = {}
    samples = []
    for tc in rep["test_cases"]:
        if tc["method"] != "GET" or tc["test_id"] not in okids or per_ep.get(tc["endpoint"], 0) >= 3:
            continue
        ep = eps[tc["endpoint"]]
        schema = next((ep.response_schemas[c] for c in sorted(ep.response_schemas) if c.startswith("2")), None)
        if not schema:
            continue
        url = "http://127.0.0.1:8082" + tc["path"] + ("?" + urlencode(tc["query"]) if tc["query"] else "")
        try:
            body = requests.get(url, timeout=10).json()
        except Exception:                                        # noqa: BLE001
            continue
        per_ep[tc["endpoint"]] = per_ep.get(tc["endpoint"], 0) + 1
        samples.append({"endpoint": tc["endpoint"], "schema": schema, "body": body, "query": tc["query"]})
    return samples


def mutants(sample: Dict[str, Any]):
    body = sample["body"]
    for path, v in leaves(body):
        name = str(path[-1]) if path and isinstance(path[-1], str) else ""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            yield "NEG_NUM", ("implied" if NONNEG_NAME.search(name) else "other"), setp(body, path, -abs(v) - 1)
        if isinstance(v, str) and TIME_NAME.search(name):
            yield "BAD_TS", "implied", setp(body, path, "last tuesday")
        if isinstance(v, str) and ID_NAME.search(name):
            yield "EMPTY_ID", "implied", setp(body, path, "")
        if isinstance(v, str) and UUID_RE.match(v):
            yield "BAD_UUID", "implied", setp(body, path, "not-a-uuid")
    if isinstance(body, dict):
        lists = [k for k, v in body.items() if isinstance(v, list)]
        if len(lists) == 1:
            for k, v in body.items():
                if k.lower() in ("count", "size", "length") and isinstance(v, int):
                    yield "COUNT_OFF", "implied", setp(body, (k,), v + 1)
    lim = sample["query"].get("limit")
    if lim is not None and isinstance(body, list) and body:
        grown = body + [copy.deepcopy(body[0]) for _ in range(int(lim) + 1)]
        yield "LIMIT_EXC", "implied", grown


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="", help="run_report.json of a chroma run made against the CURRENT live server")
    ap.add_argument("--out", default=os.path.join(ROOT, "artifacts_real", "oracle_mutation.json"))
    args = ap.parse_args()
    samples = collect(args.report)
    oracle = SemanticOracle()
    print(f"{len(samples)} real responses from {len({s['endpoint'] for s in samples})} endpoints")
    clean_flag_base = sum(1 for s in samples if schema_violations(s["body"], s["schema"]))
    clean_flag_orc = sum(1 for s in samples if oracle.check(s["schema"], s["body"], s["query"]))
    print(f"clean control: baseline flags {clean_flag_base}, oracle flags {clean_flag_orc} of {len(samples)}")

    table: Dict[Tuple[str, str], Dict[str, int]] = {}
    for s in samples:
        for op, kind, mb in mutants(s):
            row = table.setdefault((op, kind), {"n": 0, "baseline": 0, "oracle": 0, "either": 0})
            row["n"] += 1
            b = bool(msgs(schema_violations(mb, s["schema"])) - msgs(schema_violations(s["body"], s["schema"])))
            o = bool(msgs(oracle.check(s["schema"], mb, s["query"])) - msgs(oracle.check(s["schema"], s["body"], s["query"])))
            row["baseline"] += int(b); row["oracle"] += int(o); row["either"] += int(b or o)

    out = {"samples": len(samples), "endpoints": len({s["endpoint"] for s in samples}),
           "clean_control": {"baseline_flags": clean_flag_base, "oracle_flags": clean_flag_orc, "n": len(samples)},
           "operators": {f"{op}/{kind}": r for (op, kind), r in sorted(table.items())}}
    tot = {k: sum(r[k] for r in table.values()) for k in ("n", "baseline", "oracle", "either")}
    out["total"] = tot
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"\n{'operator/kind':22s} {'mutants':>7s} {'baseline':>9s} {'oracle':>7s}")
    for k, r in out["operators"].items():
        print(f"{k:22s} {r['n']:7d} {r['baseline']:6d} ({r['baseline']/r['n']:.0%}) {r['oracle']:4d} ({r['oracle']/r['n']:.0%})")
    print(f"{'TOTAL':22s} {tot['n']:7d} {tot['baseline']:6d} ({tot['baseline']/tot['n']:.0%}) {tot['oracle']:4d} ({tot['oracle']/tot['n']:.0%})")


if __name__ == "__main__":
    main()
