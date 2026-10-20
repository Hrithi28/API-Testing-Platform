"""
Module 2 -- Test Case Generator.

Produces four categories of test case per endpoint:
  positive  -- valid request, expect a declared success code
  negative  -- invalid types / missing required fields, expect 4xx
  boundary  -- min / max / empty / oversized values, expect graceful handling
  security  -- injection, auth-bypass, BOLA probes, expect no leak / no 5xx

Design note
-----------
The generator has two back-ends behind one interface:

  * LLMBackend        -- calls an LLM to author cases (set OPENAI/ANTHROPIC key)
  * SchemaRuleBackend -- deterministic, schema-driven generation (default)

The schema-driven backend is the default so the pipeline is reproducible and
runs offline. Both emit the identical TestCase structure, so the rest of the
pipeline is unchanged when the LLM back-end is enabled.
"""
from __future__ import annotations
import json
import os
import random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from m1_spec_parser import Endpoint

CATEGORIES = ["positive", "negative", "boundary", "security"]

# Security probe payloads (standard OWASP API Top-10 style probes)
INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "1; DROP TABLE pets--",
    "<script>alert(1)</script>",
    "../../etc/passwd",
    "%00",
]


@dataclass
class TestCase:
    test_id: str
    endpoint: str              # "GET /pets/{petId}"
    method: str
    path: str                  # concrete path, placeholders substituted
    category: str              # positive | negative | boundary | security
    intent: str                # human-readable description
    query: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    expected_status: List[int] = field(default_factory=list)
    expect_schema: Optional[Dict[str, Any]] = None
    security_probe: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
#  Schema-driven (deterministic) backend
# ---------------------------------------------------------------------------
class SchemaRuleBackend:
    """Generates test cases directly from JSON Schema constraints."""

    name = "schema-rule"

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    # ---- value synthesis -------------------------------------------------
    def valid_value(self, schema: Dict[str, Any]) -> Any:
        t = schema.get("type", "string")
        if "enum" in schema:
            return schema["enum"][0]
        if t == "integer":
            lo = schema.get("minimum", 1)
            hi = schema.get("maximum", lo + 20)
            return self.rng.randint(int(lo), int(max(lo, hi)))
        if t == "number":
            return float(schema.get("minimum", 1.0))
        if t == "boolean":
            return True
        if t == "array":
            return [self.valid_value(schema.get("items", {"type": "string"}))]
        if t == "object":
            return {k: self.valid_value(v) for k, v in schema.get("properties", {}).items()}
        lo = int(schema.get("minLength", 3))
        return "abc"[:max(lo, 3)] if lo <= 3 else "a" * lo

    def invalid_value(self, schema: Dict[str, Any]) -> Any:
        """A value of deliberately the wrong type."""
        t = schema.get("type", "string")
        return "not-an-int" if t in ("integer", "number") else {"unexpected": "object"}

    def boundary_values(self, schema: Dict[str, Any]) -> List[tuple]:
        """Returns a list of (label, value) boundary probes."""
        out: List[tuple] = []
        t = schema.get("type", "string")
        if t == "integer":
            if "minimum" in schema:
                out.append(("at-minimum", schema["minimum"]))
                out.append(("below-minimum", schema["minimum"] - 1))
            else:
                out.append(("zero", 0))
                out.append(("negative", -1))
            if "maximum" in schema:
                out.append(("at-maximum", schema["maximum"]))
                out.append(("above-maximum", schema["maximum"] + 1))
                # far beyond the declared cap: surfaces unbounded-work defects
                # that a +1 probe cannot reach (classic boundary-value analysis)
                out.append(("far-above-maximum", int(schema["maximum"]) * 10))
            else:
                out.append(("very-large", 100000))
        elif t == "string":
            out.append(("empty-string", ""))
            mx = schema.get("maxLength")
            if mx:
                out.append(("at-maxlength", "a" * int(mx)))
                out.append(("over-maxlength", "a" * (int(mx) + 64)))
            else:
                out.append(("very-long", "a" * 512))
        return out

    # ---- helpers ---------------------------------------------------------
    @staticmethod
    def _success_codes(ep: Endpoint) -> List[int]:
        codes = [int(c) for c in ep.response_schemas if c.isdigit() and c.startswith("2")]
        if not codes:
            codes = [200, 201]
        return codes

    def _fill_path(self, ep: Endpoint, override: Dict[str, Any] | None = None) -> str:
        override = override or {}
        path = ep.path
        for p in ep.parameters:
            if p.location == "path":
                val = override.get(p.name, self.valid_value(p.schema))
                path = path.replace("{" + p.name + "}", str(val))
        return path

    # ---- generation ------------------------------------------------------
    def generate(self, ep: Endpoint, auth_token: str = "Bearer user-100") -> List[TestCase]:
        cases: List[TestCase] = []
        n = 0

        def nid() -> str:
            nonlocal n
            n += 1
            return f"{ep.operation_id}-{n:03d}"

        auth_header = {"Authorization": auth_token} if ep.requires_auth else {}
        ok_codes = self._success_codes(ep)
        ok_schema = ep.response_schemas.get(str(ok_codes[0]))

        # ---------------- positive ----------------
        q = {p.name: self.valid_value(p.schema)
             for p in ep.parameters if p.location == "query" and p.required}
        body = self.valid_value(ep.request_schema) if ep.request_schema else None
        cases.append(TestCase(
            test_id=nid(), endpoint=ep.signature, method=ep.method,
            path=self._fill_path(ep), category="positive",
            intent="Valid request with schema-conformant values",
            query=q, headers=dict(auth_header), body=body,
            expected_status=ok_codes, expect_schema=ok_schema,
        ))

        # add an optional-parameter variant
        opt = [p for p in ep.parameters if p.location == "query" and not p.required]
        if opt:
            q2 = dict(q)
            q2[opt[0].name] = self.valid_value(opt[0].schema)
            cases.append(TestCase(
                test_id=nid(), endpoint=ep.signature, method=ep.method,
                path=self._fill_path(ep), category="positive",
                intent=f"Valid request exercising optional parameter '{opt[0].name}'",
                query=q2, headers=dict(auth_header), body=body,
                expected_status=ok_codes, expect_schema=ok_schema,
            ))

        # ---------------- negative ----------------
        for p in ep.parameters:
            if p.location == "path":
                cases.append(TestCase(
                    test_id=nid(), endpoint=ep.signature, method=ep.method,
                    path=self._fill_path(ep, {p.name: self.invalid_value(p.schema)}),
                    category="negative",
                    intent=f"Path parameter '{p.name}' has an invalid type",
                    headers=dict(auth_header), body=body, expected_status=[400, 404, 422],
                ))
            elif p.location == "query" and p.required:
                cases.append(TestCase(
                    test_id=nid(), endpoint=ep.signature, method=ep.method,
                    path=self._fill_path(ep), category="negative",
                    intent=f"Required query parameter '{p.name}' omitted",
                    query={}, headers=dict(auth_header), body=body,
                    expected_status=[400, 422],
                ))

        if ep.request_schema and ep.request_schema.get("required"):
            for req_field in ep.request_schema["required"]:
                partial = dict(body or {})
                partial.pop(req_field, None)
                cases.append(TestCase(
                    test_id=nid(), endpoint=ep.signature, method=ep.method,
                    path=self._fill_path(ep), category="negative",
                    intent=f"Required body field '{req_field}' omitted",
                    headers=dict(auth_header), body=partial,
                    expected_status=[400, 422],
                ))
            cases.append(TestCase(
                test_id=nid(), endpoint=ep.signature, method=ep.method,
                path=self._fill_path(ep), category="negative",
                intent="Request body has wrong type for a required field",
                headers=dict(auth_header),
                body={**(body or {}), ep.request_schema["required"][0]: 12345},
                expected_status=[400, 422],
            ))

        # ---------------- boundary ----------------
        for p in ep.parameters:
            for label, val in self.boundary_values(p.schema):
                if p.location == "path":
                    tc = TestCase(
                        test_id=nid(), endpoint=ep.signature, method=ep.method,
                        path=self._fill_path(ep, {p.name: val}), category="boundary",
                        intent=f"Path parameter '{p.name}' at boundary: {label}",
                        headers=dict(auth_header), body=body,
                        expected_status=ok_codes + [400, 404, 422],
                        expect_schema=ok_schema,
                    )
                else:
                    tc = TestCase(
                        test_id=nid(), endpoint=ep.signature, method=ep.method,
                        path=self._fill_path(ep), category="boundary",
                        intent=f"Query parameter '{p.name}' at boundary: {label}",
                        query={**q, p.name: val}, headers=dict(auth_header), body=body,
                        expected_status=ok_codes + [400, 422],
                        expect_schema=ok_schema,
                    )
                cases.append(tc)

        if ep.request_schema:
            for fname, fschema in (ep.request_schema.get("properties") or {}).items():
                for label, val in self.boundary_values(fschema):
                    cases.append(TestCase(
                        test_id=nid(), endpoint=ep.signature, method=ep.method,
                        path=self._fill_path(ep), category="boundary",
                        intent=f"Body field '{fname}' at boundary: {label}",
                        headers=dict(auth_header), body={**(body or {}), fname: val},
                        expected_status=ok_codes + [400, 413, 422],
                        expect_schema=ok_schema,
                    ))

        # ---------------- security ----------------
        # (a) injection probes into string-typed inputs
        str_params = [p for p in ep.parameters if p.schema.get("type", "string") == "string"]
        for p in str_params:
            for payload in INJECTION_PAYLOADS[:3]:
                if p.location == "path":
                    tc = TestCase(
                        test_id=nid(), endpoint=ep.signature, method=ep.method,
                        path=self._fill_path(ep, {p.name: payload}), category="security",
                        intent=f"Injection payload in path parameter '{p.name}'",
                        headers=dict(auth_header), body=body,
                        expected_status=[400, 404, 422], security_probe="injection",
                    )
                else:
                    tc = TestCase(
                        test_id=nid(), endpoint=ep.signature, method=ep.method,
                        path=self._fill_path(ep), category="security",
                        intent=f"Injection payload in query parameter '{p.name}'",
                        query={**q, p.name: payload}, headers=dict(auth_header), body=body,
                        expected_status=[200, 400, 422], security_probe="injection",
                    )
                cases.append(tc)

        # (b) auth-bypass: call a protected endpoint with no token
        if ep.requires_auth:
            cases.append(TestCase(
                test_id=nid(), endpoint=ep.signature, method=ep.method,
                path=self._fill_path(ep), category="security",
                intent="Protected endpoint called without an authentication token",
                query=dict(q), headers={}, body=body,
                expected_status=[401, 403], security_probe="auth-bypass",
            ))
            cases.append(TestCase(
                test_id=nid(), endpoint=ep.signature, method=ep.method,
                path=self._fill_path(ep), category="security",
                intent="Protected endpoint called with a malformed token",
                query=dict(q), headers={"Authorization": "Bearer not-a-real-token"},
                body=body, expected_status=[401, 403], security_probe="auth-bypass",
            ))

            # (c) BOLA: same object requested by a different user identity
            if any(p.location == "path" for p in ep.parameters):
                cases.append(TestCase(
                    test_id=nid(), endpoint=ep.signature, method=ep.method,
                    path=self._fill_path(ep), category="security",
                    intent="Object requested while authenticated as a different user (BOLA probe)",
                    query=dict(q), headers={"Authorization": "Bearer user-999"},
                    body=body, expected_status=[403, 404], security_probe="bola",
                ))

        # (d) injection into string body fields
        if ep.request_schema:
            for fname, fschema in (ep.request_schema.get("properties") or {}).items():
                if fschema.get("type", "string") == "string":
                    cases.append(TestCase(
                        test_id=nid(), endpoint=ep.signature, method=ep.method,
                        path=self._fill_path(ep), category="security",
                        intent=f"Injection payload in body field '{fname}'",
                        headers=dict(auth_header),
                        body={**(body or {}), fname: INJECTION_PAYLOADS[0]},
                        expected_status=ok_codes + [400, 422], security_probe="injection",
                    ))
        return cases


# ---------------------------------------------------------------------------
#  LLM backend (optional -- requires an API key)
# ---------------------------------------------------------------------------
class LLMBackend:
    """
    Calls an LLM to author test cases. Enabled when an API key is present.
    Falls back to SchemaRuleBackend on any error so the pipeline never stalls.
    """
    name = "llm"

    PROMPT = """You are an API test engineer. Given this endpoint specification, \
produce test cases as a JSON array. Each object must have exactly these keys: \
category (one of positive/negative/boundary/security), intent (short string), \
query (object), headers (object), body (object or null), expected_status (array of ints).
Return ONLY the JSON array, no prose, no markdown fences.

Endpoint specification:
{spec}
"""

    def __init__(self, model: str = "claude-sonnet-4-6", fallback: SchemaRuleBackend | None = None):
        self.model = model
        self.fallback = fallback or SchemaRuleBackend()
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")

    def generate(self, ep: Endpoint, auth_token: str = "Bearer user-100") -> List[TestCase]:
        if not self.api_key:
            return self.fallback.generate(ep, auth_token)
        try:
            import urllib.request
            spec_json = json.dumps(ep.to_dict(), indent=2)[:4000]
            payload = json.dumps({
                "model": self.model,
                "max_tokens": 2000,
                "messages": [{"role": "user",
                              "content": self.PROMPT.format(spec=spec_json)}],
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages", data=payload,
                headers={"content-type": "application/json",
                         "x-api-key": self.api_key,
                         "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            text = "".join(b.get("text", "") for b in data.get("content", []))
            raw = json.loads(text.strip().strip("`").replace("json\n", "", 1))
            out: List[TestCase] = []
            for i, item in enumerate(raw, 1):
                out.append(TestCase(
                    test_id=f"{ep.operation_id}-llm-{i:03d}",
                    endpoint=ep.signature, method=ep.method,
                    path=self.fallback._fill_path(ep),
                    category=item.get("category", "positive"),
                    intent=item.get("intent", ""),
                    query=item.get("query") or {},
                    headers=item.get("headers") or {},
                    body=item.get("body"),
                    expected_status=item.get("expected_status") or [200],
                ))
            return out or self.fallback.generate(ep, auth_token)
        except Exception as exc:                       # noqa: BLE001
            print(f"  [llm backend unavailable: {exc}; using schema-rule fallback]")
            return self.fallback.generate(ep, auth_token)


# ---------------------------------------------------------------------------
class TestGenerator:
    """Front door: generates, validates, and de-duplicates test cases."""

    def __init__(self, backend=None):
        self.backend = backend or SchemaRuleBackend()

    def generate_all(self, endpoints: List[Endpoint]) -> List[TestCase]:
        cases: List[TestCase] = []
        for ep in endpoints:
            cases.extend(self.backend.generate(ep))
        return self.deduplicate(cases)

    @staticmethod
    def deduplicate(cases: List[TestCase]) -> List[TestCase]:
        seen = set()
        out = []
        for c in cases:
            key = (c.method, c.path, json.dumps(c.query, sort_keys=True),
                   json.dumps(c.body, sort_keys=True), c.category,
                   json.dumps(c.headers, sort_keys=True))
            if key not in seen:
                seen.add(key)
                out.append(c)
        return out


if __name__ == "__main__":
    from m1_spec_parser import SpecParser
    parser = SpecParser.from_file("demo_api/petstore_openapi.json")
    eps = parser.parse()
    gen = TestGenerator()
    tcs = gen.generate_all(eps)
    print(f"backend        : {gen.backend.name}")
    print(f"generated cases: {len(tcs)}")
    for cat in CATEGORIES:
        print(f"  {cat:10s}: {sum(1 for t in tcs if t.category == cat)}")
