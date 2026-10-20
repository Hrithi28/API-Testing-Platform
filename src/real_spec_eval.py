"""Run Modules 1 and 2 over real-world OpenAPI specs (APIs.guru directory).

Generation-only evaluation: the real services are not called. For every spec we
record whether it parses, how many operations/parameters it has, how many tests
are generated, and how much of the spec those tests exercise.

usage: python3 real_spec_eval.py <APIs_dir> <out_json> [limit]
"""
import glob, json, os, sys, time, traceback
import multiprocessing as mp
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m1_spec_parser import SpecParser
from m2_test_generator import TestGenerator

HTTP = {"get", "post", "put", "patch", "delete", "head", "options"}
TIMEOUT = 90


def pick_specs(root):
    """One spec per API: the highest-sorted version directory."""
    by_api = {}
    for p in glob.glob(os.path.join(root, "**", "openapi.*"), recursive=True):
        ver_dir = os.path.dirname(p)
        api_dir = os.path.dirname(ver_dir)
        by_api.setdefault(api_dir, []).append(p)
    out = []
    for api_dir, ps in sorted(by_api.items()):
        out.append(sorted(ps)[-1])
    return out


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        txt = fh.read()
    return json.loads(txt) if path.endswith(".json") else yaml.load(txt, Loader=yaml.CSafeLoader)


def evaluate(path):
    name = "/".join(path.split("/APIs/")[1].split("/")[:-2]) if "/APIs/" in path else path
    rec = {"api": name, "file": path, "status": "ok"}
    try:
        spec = load(path)
        raw_ops = sum(1 for _, item in (spec.get("paths") or {}).items()
                      if isinstance(item, dict) for m in item if m.lower() in HTTP)
        rec["spec_operations"] = raw_ops
        rec["openapi"] = str(spec.get("openapi", ""))
        t0 = time.perf_counter()
        parser = SpecParser(spec)
        eps = parser.parse()
        rec["m1_s"] = round(time.perf_counter() - t0, 3)
        rec["endpoints"] = len(eps)
        rec["parameters"] = sum(len(e.parameters) for e in eps)
        rec["with_body"] = sum(1 for e in eps if e.request_schema)
        rec["dep_links"] = sum(len(v) for v in parser.dependency_graph(eps).values())
        t0 = time.perf_counter()
        cases = TestGenerator().generate_all(eps)
        rec["m2_s"] = round(time.perf_counter() - t0, 3)
        rec["tests"] = len(cases)
        cats = {}
        for c in cases:
            cats[c.category] = cats.get(c.category, 0) + 1
        rec["categories"] = cats
        covered = {c.endpoint for c in cases}
        rec["endpoints_covered"] = len(covered)
        # parameter coverage: declared params that appear in at least one test
        used, total = 0, 0
        by_ep = {}
        for c in cases:
            by_ep.setdefault(c.endpoint, []).append(c)
        for e in eps:
            key = f"{e.method} {e.path}"
            cs = by_ep.get(key, [])
            for p in e.parameters:
                total += 1
                if p.location == "query":
                    hit = any(p.name in c.query for c in cs)
                elif p.location == "header":
                    hit = any(p.name in c.headers for c in cs)
                else:  # path / cookie: exercised whenever the endpoint is
                    hit = bool(cs)
                used += hit
        rec["params_exercised"] = used
        rec["params_total"] = total
    except RecursionError:
        rec["status"] = "recursion_error"
    except Exception as ex:  # noqa
        rec["status"] = "error:" + type(ex).__name__ + ":" + str(ex)[:120]
    return rec


def _worker(path, q):
    q.put(evaluate(path))


def run_one(path):
    q = mp.Queue()
    p = mp.Process(target=_worker, args=(path, q))
    p.start()
    p.join(TIMEOUT)
    if p.is_alive():
        p.terminate(); p.join()
        name = "/".join(path.split("/APIs/")[1].split("/")[:-2])
        return {"api": name, "file": path, "status": "timeout"}
    try:
        return q.get(timeout=5)
    except Exception:
        name = "/".join(path.split("/APIs/")[1].split("/")[:-2])
        return {"api": name, "file": path, "status": "crashed"}


if __name__ == "__main__":
    root, out = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    specs = pick_specs(root)
    if limit:
        specs = specs[:limit]
    print(f"{len(specs)} specs", flush=True)
    results = []
    for i, sp in enumerate(specs, 1):
        results.append(run_one(sp))
        if i % 50 == 0:
            print(f"  {i}/{len(specs)}", flush=True)
            json.dump(results, open(out, "w"))
    json.dump(results, open(out, "w"), indent=1)
    print("done")
