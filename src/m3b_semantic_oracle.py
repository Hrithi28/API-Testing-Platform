"""
Module 3b -- Specification-driven semantic oracle (SATORI-style).

SATORI (Alonso et al., ASE 2025) shows that an API's OpenAPI document already
says a good deal about what a *correct* response looks like, and uses an LLM to
read response-field names and descriptions to infer oracles statically.

This module follows the same idea without needing an LLM: it reads the same
signals -- field names, descriptions, formats and declared constraints -- with
deterministic rules, and checks every 2xx response against them. It goes beyond
Module 3's checker, which only verifies type / required / enum.

Violations are tagged so reports can separate them:
    constraint:  an explicit schema keyword was broken (minimum, maxLength, ...)
    semantic:    an inferred, meaning-based rule was broken
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URI_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://\S+$")
IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

NONNEG_NAME = re.compile(
    r"(^|_)(count|total|size|length|len|num|number|limit|offset|age|duration|latency|bytes|"
    r"quantity|qty|page|dimension|n_results)($|_)|(count|total|size|length)$", re.I)
TIME_NAME = re.compile(r"(_at|_time|timestamp|datetime)$|^(created|updated|expires|date)$", re.I)
ID_NAME = re.compile(r"(^|_)(id|uuid)$|Id$")

DESC_RULES = [
    (re.compile(r"non-?negative|zero or (more|greater)|>=\s*0", re.I), ("min", 0, False)),
    (re.compile(r"\bpositive\b|greater than (zero|0)", re.I), ("min", 0, True)),
]
DESC_FORMAT = [
    (re.compile(r"iso[ -]?8601|rfc[ -]?3339", re.I), "date-time"),
    (re.compile(r"\buuid\b", re.I), "uuid"),
    (re.compile(r"e-?mail", re.I), "email"),
    (re.compile(r"\bvalid (url|uri)\b|\bfull url\b", re.I), "uri"),
]
BETWEEN = re.compile(r"between\s+(-?\d+)\s+and\s+(-?\d+)", re.I)
AT_MOST = re.compile(r"(at most|no more than|maximum of|up to)\s+(\d+)", re.I)


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_format(value: str, fmt: str) -> bool:
    if fmt == "uuid":
        return bool(UUID_RE.match(value))
    if fmt == "email":
        return bool(EMAIL_RE.match(value))
    if fmt in ("uri", "url"):
        return bool(URI_RE.match(value))
    if fmt == "ipv4":
        return bool(IPV4_RE.match(value)) and all(int(p) <= 255 for p in value.split("."))
    if fmt in ("date-time", "date"):
        v = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(v)
            return True
        except ValueError:
            return False
    return True


class SemanticOracle:
    def __init__(self, enable_semantic: bool = True, enable_constraints: bool = True):
        self.enable_semantic = enable_semantic
        self.enable_constraints = enable_constraints

    # ------------------------------------------------------------ public
    def check(self, schema: Optional[Dict[str, Any]], data: Any,
              request_query: Optional[Dict[str, Any]] = None) -> List[str]:
        if not schema or data is None:
            return []
        out: List[str] = []
        self._walk(schema, data, "$", None, out)
        if self.enable_semantic:
            self._cross_field(schema, data, request_query or {}, out)
        return out

    # ------------------------------------------------------------ walker
    def _walk(self, schema: Dict[str, Any], data: Any, path: str,
              name: Optional[str], out: List[str]) -> None:
        if not isinstance(schema, dict):
            return
        t = schema.get("type")
        desc = schema.get("description", "") or ""

        if self.enable_constraints:
            self._constraints(schema, data, path, out)

        if isinstance(data, dict) and (t == "object" or "properties" in schema):
            for k, sub in (schema.get("properties") or {}).items():
                if k in data:
                    self._walk(sub, data[k], f"{path}.{k}", k, out)
        elif isinstance(data, list) and (t == "array" or "items" in schema):
            for i, item in enumerate(data[:10]):
                self._walk(schema.get("items") or {}, item, f"{path}[{i}]", name, out)
        elif self.enable_semantic:
            self._semantic_scalar(schema, data, path, name, desc, out)

    def _constraints(self, s: Dict[str, Any], data: Any, path: str, out: List[str]) -> None:
        if _is_num(data):
            if "minimum" in s and data < s["minimum"]:
                out.append(f"constraint: {path}: {data} < minimum {s['minimum']}")
            if "maximum" in s and data > s["maximum"]:
                out.append(f"constraint: {path}: {data} > maximum {s['maximum']}")
            if _is_num(s.get("exclusiveMinimum")) and data <= s["exclusiveMinimum"]:
                out.append(f"constraint: {path}: {data} <= exclusiveMinimum {s['exclusiveMinimum']}")
        if isinstance(data, str):
            if "minLength" in s and len(data) < s["minLength"]:
                out.append(f"constraint: {path}: length {len(data)} < minLength {s['minLength']}")
            if "maxLength" in s and len(data) > s["maxLength"]:
                out.append(f"constraint: {path}: length {len(data)} > maxLength {s['maxLength']}")
            if s.get("pattern"):
                try:
                    if not re.search(s["pattern"], data):
                        out.append(f"constraint: {path}: does not match pattern {s['pattern']}")
                except re.error:
                    pass
            if s.get("format") and not _check_format(data, s["format"]):
                out.append(f"constraint: {path}: not a valid {s['format']}")
        if isinstance(data, list):
            if "minItems" in s and len(data) < s["minItems"]:
                out.append(f"constraint: {path}: {len(data)} items < minItems {s['minItems']}")
            if "maxItems" in s and len(data) > s["maxItems"]:
                out.append(f"constraint: {path}: {len(data)} items > maxItems {s['maxItems']}")
            if s.get("uniqueItems"):
                try:
                    if len({repr(x) for x in data}) != len(data):
                        out.append(f"constraint: {path}: items are not unique")
                except Exception:               # noqa: BLE001
                    pass

    def _semantic_scalar(self, s: Dict[str, Any], data: Any, path: str,
                         name: Optional[str], desc: str, out: List[str]) -> None:
        # 1. names that imply a non-negative quantity
        if name and _is_num(data) and NONNEG_NAME.search(name) and data < 0:
            out.append(f"semantic: {path}: field name '{name}' implies a non-negative value, got {data}")
        # 2. identifiers must not be empty
        if name and isinstance(data, str) and ID_NAME.search(name) and data.strip() == "":
            out.append(f"semantic: {path}: identifier '{name}' is empty")
        # 3. timestamps must parse
        if name and TIME_NAME.search(name):
            if isinstance(data, str) and not _check_format(data, "date-time"):
                out.append(f"semantic: {path}: '{name}' looks like a timestamp but '{data[:30]}' is not ISO 8601")
        # 4. rules stated in the field's description
        for rx, (kind, bound, strict) in DESC_RULES:
            if rx.search(desc) and _is_num(data):
                if (strict and data <= bound) or (not strict and data < bound):
                    out.append(f"semantic: {path}: description says '{rx.pattern.split('|')[0]}', got {data}")
        for rx, fmt in DESC_FORMAT:
            if rx.search(desc) and isinstance(data, str) and not _check_format(data, fmt):
                out.append(f"semantic: {path}: description mentions {fmt}, value '{data[:30]}' is not")
        m = BETWEEN.search(desc)
        if m and _is_num(data) and not (int(m.group(1)) <= data <= int(m.group(2))):
            out.append(f"semantic: {path}: description says between {m.group(1)} and {m.group(2)}, got {data}")
        m = AT_MOST.search(desc)
        if m and _is_num(data) and data > int(m.group(2)):
            out.append(f"semantic: {path}: description says at most {m.group(2)}, got {data}")

    # -------------------------------------------------- cross-field rules
    def _cross_field(self, schema: Dict[str, Any], data: Any,
                     query: Dict[str, Any], out: List[str]) -> None:
        # (a) a page can never hold more items than the requested limit
        limit = query.get("limit")
        if limit is not None:
            try:
                limit_i = int(limit)
            except (TypeError, ValueError):
                limit_i = None
            if limit_i is not None and limit_i >= 0:
                lists = [data] if isinstance(data, list) else \
                    [v for v in data.values() if isinstance(v, list)] if isinstance(data, dict) else []
                for lst in lists:
                    if len(lst) > limit_i:
                        out.append(f"semantic: $: {len(lst)} items returned but limit={limit_i} was requested")
        # (b) a 'count'-style field must equal the length of its sole sibling list
        if isinstance(data, dict):
            lists = [v for v in data.values() if isinstance(v, list)]
            if len(lists) == 1:
                for k, v in data.items():
                    if k.lower() in ("count", "size", "length", "num_items") and _is_num(v) and v != len(lists[0]):
                        out.append(f"semantic: $.{k}: reports {v} but sibling list has {len(lists[0])} items")
