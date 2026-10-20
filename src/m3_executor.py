"""
Module 3 -- Automated Test Execution Engine & Response Collector.

Executes generated test cases against the target API and records structured
evidence for every call: status, latency, headers, body, and schema conformance.
"""
from __future__ import annotations
import concurrent.futures as cf
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from m2_test_generator import TestCase


# ---------------------------------------------------------------------------
#  Lightweight JSON-Schema conformance checker
# ---------------------------------------------------------------------------
def schema_violations(data: Any, schema: Optional[Dict[str, Any]], path: str = "$") -> List[str]:
    """Returns a list of human-readable schema violations (empty == conformant)."""
    if not schema:
        return []
    if data is None and (schema.get("nullable") or schema.get("x-nullable")):
        return []
    alts = schema.get("x-alternatives")
    if alts:                                   # oneOf / anyOf: conformant if ANY branch accepts the value
        first: Optional[List[str]] = None
        for a in alts:
            v = schema_violations(data, a, path)
            if not v:
                return []
            first = v if first is None else first
        return first or []
    out: List[str] = []
    t = schema.get("type")

    if t == "object":
        if not isinstance(data, dict):
            return [f"{path}: expected object, got {type(data).__name__}"]
        for req in schema.get("required", []):
            if req not in data:
                out.append(f"{path}.{req}: required field missing")
        for k, sub in (schema.get("properties") or {}).items():
            if k in data:
                out.extend(schema_violations(data[k], sub, f"{path}.{k}"))
    elif t == "array":
        if not isinstance(data, list):
            return [f"{path}: expected array, got {type(data).__name__}"]
        for i, item in enumerate(data[:10]):
            out.extend(schema_violations(item, schema.get("items"), f"{path}[{i}]"))
    elif t == "integer":
        if isinstance(data, bool) or not isinstance(data, int):
            out.append(f"{path}: expected integer, got {type(data).__name__}")
    elif t == "number":
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            out.append(f"{path}: expected number, got {type(data).__name__}")
    elif t == "string":
        if not isinstance(data, str):
            out.append(f"{path}: expected string, got {type(data).__name__}")
        elif "enum" in schema and data not in schema["enum"]:
            out.append(f"{path}: value '{data}' not in enum {schema['enum']}")
    elif t == "boolean":
        if not isinstance(data, bool):
            out.append(f"{path}: expected boolean, got {type(data).__name__}")
    return out


@dataclass
class ExecutionResult:
    test_id: str
    endpoint: str
    method: str
    url: str
    category: str
    intent: str
    security_probe: Optional[str]
    status_code: int
    latency_ms: float
    expected_status: List[int]
    status_as_expected: bool
    schema_violations: List[str] = field(default_factory=list)
    response_size: int = 0
    content_type: str = ""
    body_preview: str = ""
    error: Optional[str] = None

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_server_error"] = self.is_server_error
        return d


class ExecutionEngine:
    def __init__(self, base_url: str, timeout: float = 10.0, workers: int = 6):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.workers = workers

    # ------------------------------------------------------------------ run
    def run_one(self, tc: TestCase) -> ExecutionResult:
        url = self.base_url + tc.path
        if tc.query:
            url += "?" + urlencode({k: str(v) for k, v in tc.query.items()})

        headers = {"Accept": "application/json", **tc.headers}
        kwargs: Dict[str, Any] = {"headers": headers, "timeout": self.timeout}
        if tc.body is not None and tc.method in ("POST", "PUT", "PATCH"):
            kwargs["json"] = tc.body

        t0 = time.perf_counter()
        try:
            resp = requests.request(tc.method, url, **kwargs)
            latency = (time.perf_counter() - t0) * 1000.0
            try:
                parsed = resp.json()
                preview = json.dumps(parsed)[:400]
            except ValueError:
                parsed, preview = None, resp.text[:400]

            # A declared success schema is a contract for EVERY 2xx response,
            # not only for the happy-path test that declared it. Checking all
            # 2xx responses is what surfaces schema drift on edge-case inputs.
            expected_schema = tc.expect_schema if 200 <= resp.status_code < 300 else None
            violations = schema_violations(parsed, expected_schema) if parsed is not None else []

            return ExecutionResult(
                test_id=tc.test_id, endpoint=tc.endpoint, method=tc.method, url=url,
                category=tc.category, intent=tc.intent, security_probe=tc.security_probe,
                status_code=resp.status_code, latency_ms=round(latency, 2),
                expected_status=tc.expected_status,
                status_as_expected=resp.status_code in tc.expected_status,
                schema_violations=violations,
                response_size=len(resp.content),
                content_type=resp.headers.get("Content-Type", ""),
                body_preview=preview,
            )
        except Exception as exc:                                    # noqa: BLE001
            latency = (time.perf_counter() - t0) * 1000.0
            return ExecutionResult(
                test_id=tc.test_id, endpoint=tc.endpoint, method=tc.method, url=url,
                category=tc.category, intent=tc.intent, security_probe=tc.security_probe,
                status_code=0, latency_ms=round(latency, 2),
                expected_status=tc.expected_status, status_as_expected=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def run_all(self, cases: List[TestCase], progress: bool = True) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        with cf.ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self.run_one, tc): tc for tc in cases}
            for i, fut in enumerate(cf.as_completed(futures), 1):
                results.append(fut.result())
                if progress and i % 10 == 0:
                    print(f"    executed {i}/{len(cases)}")
        # stable ordering for reproducible reports
        results.sort(key=lambda r: r.test_id)
        return results

    # ------------------------------------------------------- health probe
    def wait_until_ready(self, path: str = "/health", attempts: int = 25) -> bool:
        for _ in range(attempts):
            try:
                if requests.get(self.base_url + path, timeout=2).status_code == 200:
                    return True
            except Exception:                                        # noqa: BLE001
                pass
            time.sleep(0.4)
        return False
