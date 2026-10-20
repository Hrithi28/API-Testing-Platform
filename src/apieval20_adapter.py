"""
APIEval-20 adapter -- turns our Module-2 test-generation logic into APIEval-20 suites.

APIEval-20 (KushoAI, 2026) gives an agent, per scenario, ONLY a request schema and one
valid sample payload, and asks for a list of test cases {test_name, payload}. A hosted
harness runs them against a live reference API with planted bugs and scores
    0.7 * bug_detection + 0.2 * coverage + 0.1 * efficiency.

This adapter reads scenarios, generates a suite per scenario with the same
boundary-value / negative / security reasoning as Module 2 (it reuses
SchemaRuleBackend.boundary_values), and writes <scenario_id>_suite.json.

IMPORTANT -- written from the benchmark's published description; it has NOT been run
against the real dataset files. Check (1) the scenario file layout and (2) the suite
file shape against the dataset README, and pass --format / adjust load_scenarios()
if either differs. Scoring happens on KushoAI's hosted harness, not here.

usage:
  python3 src/apieval20_adapter.py --scenarios api-eval-20/scenarios --out suites
  python3 src/apieval20_adapter.py --selftest
"""
from __future__ import annotations
import argparse
import copy
import csv
import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m2_test_generator import SchemaRuleBackend, INJECTION_PAYLOADS   # noqa: E402

BACKEND = SchemaRuleBackend()


# --------------------------------------------------------------------- loading
def _maybe_json(v: Any) -> Any:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


def _record(d: Dict[str, Any], fallback_id: str) -> Optional[Dict[str, Any]]:
    d = {k.lower(): v for k, v in d.items()}
    schema = _maybe_json(d.get("schema") or d.get("request_schema"))
    sample = _maybe_json(d.get("sample_payload") or d.get("payload") or d.get("sample"))
    if not isinstance(schema, dict) or not isinstance(sample, dict):
        return None
    return {"scenario_id": str(d.get("scenario_id") or d.get("id") or fallback_id),
            "domain": d.get("domain", ""), "endpoint": d.get("endpoint", ""),
            "method": d.get("method", ""), "schema": schema, "sample": sample}


def load_scenarios(folder: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    files = sorted(glob.glob(os.path.join(folder, "**", "*"), recursive=True))
    for f in files:
        base = os.path.basename(f)
        try:
            if f.endswith(".jsonl"):
                for i, line in enumerate(open(f, encoding="utf-8")):
                    r = _record(json.loads(line), f"{base}:{i}")
                    out += [r] if r else []
            elif f.endswith(".json"):
                data = json.load(open(f, encoding="utf-8"))
                items = data if isinstance(data, list) else [data]
                for i, it in enumerate(items):
                    if isinstance(it, dict):
                        r = _record(it, os.path.splitext(base)[0])
                        out += [r] if r else []
            elif f.endswith(".csv"):
                for i, row in enumerate(csv.DictReader(open(f, encoding="utf-8"))):
                    r = _record(row, f"{base}:{i}")
                    out += [r] if r else []
            elif f.endswith(".parquet"):
                import pandas as pd
                for i, row in enumerate(pd.read_parquet(f).to_dict("records")):
                    r = _record(row, f"{base}:{i}")
                    out += [r] if r else []
        except Exception as ex:                                  # noqa: BLE001
            print(f"  skipped {base}: {type(ex).__name__}: {ex}")
    # layout B: separate <id>_schema.json and <id>_sample/_payload.json files
    if not out:
        for sf in sorted(glob.glob(os.path.join(folder, "**", "*schema*.json"), recursive=True)):
            sid = re.sub(r"[._-]?schema.*$", "", os.path.basename(sf))
            for cand in glob.glob(os.path.join(os.path.dirname(sf), f"{sid}*"), recursive=False):
                if cand != sf and re.search(r"sample|payload|example", cand) and cand.endswith(".json"):
                    schema, sample = json.load(open(sf)), json.load(open(cand))
                    if isinstance(schema, dict) and isinstance(sample, dict):
                        out.append({"scenario_id": sid, "domain": "", "endpoint": "", "method": "",
                                    "schema": schema, "sample": sample})
    return out


# ------------------------------------------------------------ schema handling
def field_map(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Accepts the benchmark's {field: {type, required, ...}} map OR standard JSON Schema."""
    if "properties" in schema and isinstance(schema["properties"], dict):
        req = set(schema.get("required", []))
        return {k: {**v, "required": v.get("required", k in req)} for k, v in schema["properties"].items()
                if isinstance(v, dict)}
    return {k: v for k, v in schema.items() if isinstance(v, dict)}


def enrich(fs: Dict[str, Any]) -> Dict[str, Any]:
    """Pull numeric/length constraints out of the natural-language description."""
    fs = dict(fs)
    d = str(fs.get("description", ""))
    t = fs.get("type", "string")
    num = r"(-?\d+(?:\.\d+)?)"
    m = re.search(rf"between\s+{num}\s+and\s+{num}", d, re.I) or re.search(rf"{num}\s*(?:-|to)\s*{num}", d)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        key = ("minLength", "maxLength") if t == "string" else ("minimum", "maximum")
        fs.setdefault(key[0], int(lo) if lo.is_integer() else lo)
        fs.setdefault(key[1], int(hi) if hi.is_integer() else hi)
    for rx, key in ((rf"(?:min(?:imum)?(?: of)?|at least)\s+{num}", "min"), (rf"(?:max(?:imum)?(?: of)?|at most|up to|no more than)\s+{num}", "max")):
        m = re.search(rx, d, re.I)
        if m:
            v = float(m.group(1)); v = int(v) if v.is_integer() else v
            if t == "string":
                fs.setdefault("minLength" if key == "min" else "maxLength", v)
            elif t in ("integer", "number"):
                fs.setdefault("minimum" if key == "min" else "maximum", v)
    if re.search(r"\bpositive\b|greater than (zero|0)", d, re.I) and t in ("integer", "number"):
        fs.setdefault("minimum", 1)
    return fs


def norm_type(t: Any) -> str:
    t = str(t or "string").lower()
    return {"int": "integer", "float": "number", "bool": "boolean", "str": "string", "list": "array", "dict": "object"}.get(t, t)


# --------------------------------------------------------------- mutation core
def get_path(d: Dict[str, Any], path: List[str]) -> Any:
    for p in path:
        d = d[p]
    return d


def set_path(d: Dict[str, Any], path: List[str], val: Any, delete: bool = False) -> Dict[str, Any]:
    """Copy of d with the value at path set (or removed). Missing intermediate objects are created for a set
    (an optional nested object the sample omits can still be filled in); for a delete they mean nothing to remove."""
    d = copy.deepcopy(d)
    cur = d
    for i, p in enumerate(path[:-1]):
        try:
            nxt = cur[p]
        except (KeyError, IndexError, TypeError):
            if delete:
                return d
            nxt = {}
            if isinstance(cur, dict):
                cur[p] = nxt
            else:
                return d
        cur = nxt
    if delete:
        if isinstance(cur, list):
            if isinstance(path[-1], int) and path[-1] < len(cur):
                del cur[path[-1]]
        elif isinstance(cur, dict):
            cur.pop(path[-1], None)
    elif isinstance(cur, dict) or (isinstance(cur, list) and isinstance(path[-1], int) and path[-1] < len(cur)):
        cur[path[-1]] = val
    return d


def walk_fields(fmap: Dict[str, Dict[str, Any]], sample: Dict[str, Any],
                prefix: Optional[List[str]] = None) -> List[Tuple[List[str], Dict[str, Any]]]:
    out = []
    for name, fs in fmap.items():
        path = (prefix or []) + [name]
        out.append((path, fs))
        sub = fs.get("properties")
        if norm_type(fs.get("type")) == "object" and isinstance(sub, dict):
            req_o = set(fs.get("required", [])) if isinstance(fs.get("required"), list) else set()
            out += walk_fields({k: {**v, "required": v.get("required", k in req_o) if not isinstance(v.get("required"), list) else k in req_o}
                                for k, v in sub.items() if isinstance(v, dict)}, sample, path)
        # arrays of objects: descend into element 0 of the sample (path element is the int index 0)
        elif norm_type(fs.get("type")) == "array" and isinstance(fs.get("items"), dict):
            it = fs["items"]
            try:
                cur = get_path(sample, path)
            except (KeyError, TypeError, IndexError):
                cur = None
            if isinstance(cur, list) and cur and norm_type(it.get("type")) == "object" and isinstance(it.get("properties"), dict):
                req = set(it.get("required", []))
                sub_map = {k: {**v, "required": v.get("required", k in req)} for k, v in it["properties"].items() if isinstance(v, dict)}
                out += walk_fields(sub_map, sample, path + [0])
    return out


def wrong_type(t: str) -> Any:
    return {"string": 12345, "integer": "not-a-number", "number": "not-a-number", "boolean": "maybe",
            "array": "not-an-array", "object": "not-an-object"}.get(t, 12345)


def generate_suite(sc: Dict[str, Any], budget: int = 80) -> List[Dict[str, Any]]:
    fmap, sample = field_map(sc["schema"]), sc["sample"]
    fields = walk_fields(fmap, sample)
    tests: List[Dict[str, Any]] = [{"test_name": "baseline_valid_sample", "payload": copy.deepcopy(sample)}]
    seen = {json.dumps(sample, sort_keys=True)}
    tiers: List[List[Dict[str, Any]]] = [[], [], [], [], [], []]

    def add(tier: int, name: str, payload: Dict[str, Any]) -> None:
        key = json.dumps(payload, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            tiers[tier].append({"test_name": name, "payload": payload})

    for path, raw in fields:
        try:
            cur = get_path(sample, path)
        except (KeyError, TypeError):
            cur = None
        fs = enrich(raw)
        t = norm_type(fs.get("type"))
        label = ".".join(str(x) for x in path)
        # tier 0: omit (every field counts toward coverage; required ones are the likely bugs)
        add(0, f"omit_{label}" + ("_required" if fs.get("required") else ""), set_path(sample, path, None, delete=True))
        # tier 1: wrong type + null
        add(1, f"wrong_type_{label}", set_path(sample, path, wrong_type(t)))
        add(1, f"null_{label}", set_path(sample, path, None))
        # tier 2: boundary values (reuse Module 2 logic)
        schema_like = {"type": t if t in ("integer", "string") else ("integer" if t == "number" else t), **{
            k: fs[k] for k in ("minimum", "maximum", "minLength", "maxLength") if k in fs}}
        bvs = BACKEND.boundary_values(schema_like) if t in ("integer", "number", "string") else []
        if t == "number":
            bvs = [(lbl, float(v)) for lbl, v in bvs]
        for lbl, val in bvs:
            add(2, f"boundary_{label}_{lbl}", set_path(sample, path, val))
        if t in ("integer", "number") and "minimum" not in fs:
            add(2, f"boundary_{label}_negative", set_path(sample, path, -1))
        # tier 3: enum / format
        if isinstance(fs.get("enum"), list) and fs["enum"]:
            add(3, f"invalid_enum_{label}", set_path(sample, path, "__not_in_enum__"))
        if re.search(r"email", label + str(fs.get("description", "")), re.I) and t == "string":
            add(3, f"invalid_email_{label}", set_path(sample, path, "not-an-email"))
        if re.search(r"date|time|_at$", label, re.I) and t == "string":
            add(3, f"invalid_date_{label}", set_path(sample, path, "31-31-2025"))
        # arrays
        if t == "array" and isinstance(cur, list):
            add(3, f"empty_array_{label}", set_path(sample, path, []))
            if cur:
                add(3, f"duplicate_items_{label}", set_path(sample, path, cur + [copy.deepcopy(cur[0])]))
        # tier 4: injection (strings only)
        if t == "string":
            add(4, f"injection_{label}", set_path(sample, path, INJECTION_PAYLOADS[0]))

    # tier 5: cross-field -- swap start/end style pairs
    names = {str(p[-1]).lower(): p for p, _ in fields}
    for a, b in (("start_date", "end_date"), ("start", "end"), ("from", "to"), ("check_in", "check_out"),
                 ("start_time", "end_time"), ("min", "max"), ("min_price", "max_price")):
        if a in names and b in names:
            try:
                va, vb = get_path(sample, names[a]), get_path(sample, names[b])
                add(5, f"swap_{a}_{b}", set_path(set_path(sample, names[a], vb), names[b], va))
            except (KeyError, TypeError):
                pass

    # tiers are consumed round-robin by field priority until the budget is met
    pool = [t for ti in (0, 1, 3, 5, 2, 4) for t in tiers[ti]]
    for t in pool:
        if len(tests) < budget:
            tests.append(t)
    # coverage guarantee: the benchmark counts a TOP-LEVEL field as exercised when some test changes or omits it,
    # so make sure no top-level field is left out by the budget cut (a few extra tests at most).
    top = list(fmap.keys())
    def touched(tc, f):
        pl = tc["payload"]
        if f in sample and f not in pl:
            return True
        if f in pl and f not in sample:
            return True
        return pl.get(f) != sample.get(f)
    for f in top:
        if not any(touched(tc, f) for tc in tests):
            cand = next((c for c in pool if c not in tests and touched(c, f)), None)
            if cand:
                tests.append(cand)
    return tests


def local_coverage(sc: Dict[str, Any], tests: List[Dict[str, Any]]) -> float:
    """Re-implements the published coverage rule: a field counts if some test changes/omits it."""
    sample = sc["sample"]
    fields = [p for p, _ in walk_fields(field_map(sc["schema"]), sample)]
    hit = 0
    for p in fields:
        for t in tests:
            try:
                cur = get_path(t["payload"], p)
            except (KeyError, TypeError):
                hit += 1
                break
            try:
                if cur != get_path(sample, p):
                    hit += 1
                    break
            except (KeyError, TypeError):
                hit += 1
                break
    return hit / len(fields) if fields else 1.0


# --------------------------------------------------------------------- selftest
SYNTHETIC = [
    {"scenario_id": "99_payment_demo", "domain": "payments", "endpoint": "/charge", "method": "POST",
     "schema": {"amount": {"type": "number", "required": True, "description": "Amount in USD, between 1 and 10000"},
                "currency": {"type": "string", "required": True, "enum": ["USD", "EUR", "INR"]},
                "card": {"type": "object", "required": True, "properties": {
                    "number": {"type": "string", "required": True, "description": "16 digit card number"},
                    "expiry": {"type": "string", "required": True, "description": "expiry date"}}},
                "email": {"type": "string", "required": False, "description": "Customer email address"},
                "items": {"type": "array", "required": False}},
     "sample": {"amount": 250.0, "currency": "USD", "card": {"number": "4111111111111111", "expiry": "2030-12-01"},
                "email": "a@b.com", "items": ["sku-1"]}},
    {"scenario_id": "98_booking_demo", "domain": "scheduling", "endpoint": "/book", "method": "POST",
     "schema": {"start_date": {"type": "string", "required": True}, "end_date": {"type": "string", "required": True},
                "guests": {"type": "integer", "required": True, "description": "Number of guests, maximum 8"}},
     "sample": {"start_date": "2026-01-01", "end_date": "2026-01-05", "guests": 2}},
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios")
    ap.add_argument("--out", default="suites")
    ap.add_argument("--budget", type=int, default=80, help="max tests per scenario (efficiency = bugs/tests)")
    ap.add_argument("--format", choices=["list", "object"], default="list",
                    help="suite file shape: bare JSON list, or {scenario_id, tests:[...]}")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        scs = SYNTHETIC
    else:
        if not a.scenarios:
            sys.exit("give --scenarios <folder> (the dataset's scenarios/ folder) or --selftest")
        scs = load_scenarios(a.scenarios)
        if not scs:
            print(f"No scenarios recognised in {a.scenarios}. Folder contains:")
            for f in sorted(glob.glob(os.path.join(a.scenarios, "**", "*"), recursive=True))[:30]:
                print("  ", f)
            sys.exit("Send me that listing and one file's first lines so I can adapt load_scenarios().")
    out_dir = a.out if not a.selftest else "/tmp/claude-0/apieval_selftest"
    os.makedirs(out_dir, exist_ok=True)
    print(f"{len(scs)} scenario(s)")
    for sc in scs:
        tests = generate_suite(sc, a.budget)
        cov = local_coverage(sc, tests)
        body = tests if a.format == "list" else {"scenario_id": sc["scenario_id"], "tests": tests}
        path = os.path.join(out_dir, f"{sc['scenario_id']}_suite.json")
        json.dump(body, open(path, "w"), indent=1)
        print(f"  {sc['scenario_id']:28s} {len(tests):3d} tests  local field coverage {cov:.0%}  -> {path}")


if __name__ == "__main__":
    main()
