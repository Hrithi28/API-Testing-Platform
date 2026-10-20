"""
Module 1 extension -- real-world spec support.

The original SpecParser targets clean OpenAPI 3.0 documents. Real services
publish Swagger 2.0 (httpbin) or OpenAPI 3.1 (ChromaDB) documents, with
nullable unions, anyOf/oneOf/allOf, body parameters and top-level parameter
types. RealSpecParser normalises all of these into the same Endpoint model so
Modules 2-5 run unchanged.
"""
from __future__ import annotations
import copy
import json
from typing import Any, Dict, List

from m1_spec_parser import SpecParser, Endpoint, Parameter

HTTP = {"get", "post", "put", "patch", "delete", "head", "options"}
SCHEMA_KEYS = ("type", "format", "enum", "minimum", "maximum", "minLength", "maxLength",
               "pattern", "items", "default", "description", "properties", "required",
               "minItems", "maxItems", "uniqueItems", "exclusiveMinimum", "exclusiveMaximum")


def _first_non_null(options: List[Dict[str, Any]]) -> Dict[str, Any]:
    for o in options:
        if isinstance(o, dict) and o.get("type") != "null":
            return o
    return options[0] if options else {}


class RealSpecParser(SpecParser):
    def __init__(self, spec: Dict[str, Any]):
        spec = copy.deepcopy(spec)
        self.swagger2 = str(spec.get("swagger", "")).startswith("2")
        if self.swagger2:
            spec = self._upgrade_swagger2(spec)
        super().__init__(spec)

    # ------------------------------------------------------------ loading
    @classmethod
    def from_file(cls, path: str) -> "RealSpecParser":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))

    # ------------------------------------------------- swagger 2 -> oas 3
    @staticmethod
    def _param_to_oas3(raw: Dict[str, Any]) -> Dict[str, Any]:
        if "schema" in raw or raw.get("in") == "body":
            return raw
        p = {k: v for k, v in raw.items() if k not in SCHEMA_KEYS}
        p["schema"] = {k: raw[k] for k in SCHEMA_KEYS if k in raw and k != "description"}
        if "description" in raw:
            p["description"] = raw["description"]
        return p

    def _upgrade_swagger2(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        spec["components"] = {"schemas": spec.get("definitions", {}),
                              "parameters": spec.get("parameters", {})}
        host = spec.get("host", "")
        scheme = (spec.get("schemes") or ["http"])[0]
        spec["servers"] = [{"url": f"{scheme}://{host}{spec.get('basePath', '')}".rstrip("/")}]
        for path, item in spec.get("paths", {}).items():
            shared = [self._param_to_oas3(self._deref(p, spec)) for p in item.get("parameters", [])]
            if "parameters" in item:
                item["parameters"] = shared
            for method, op in item.items():
                if method.lower() not in HTTP or not isinstance(op, dict):
                    continue
                params, body_schema = [], None
                for raw in op.get("parameters", []):
                    raw = self._deref(raw, spec)
                    if raw.get("in") == "body":
                        body_schema = raw.get("schema", {})
                    elif raw.get("in") == "formData":
                        body_schema = body_schema or {"type": "object", "properties": {}}
                        body_schema.setdefault("properties", {})[raw["name"]] = \
                            self._param_to_oas3(raw)["schema"]
                        if raw.get("required"):
                            body_schema.setdefault("required", []).append(raw["name"])
                    else:
                        params.append(self._param_to_oas3(raw))
                op["parameters"] = params
                if body_schema is not None:
                    op["requestBody"] = {"content": {"application/json": {"schema": body_schema}}}
                for code, resp in (op.get("responses") or {}).items():
                    if isinstance(resp, dict) and "schema" in resp:
                        resp["content"] = {"application/json": {"schema": resp["schema"]}}
        return spec

    @staticmethod
    def _deref(node: Any, spec: Dict[str, Any]) -> Any:
        if isinstance(node, dict) and isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/"):
            tgt: Any = spec
            for part in node["$ref"][2:].split("/"):
                tgt = tgt.get(part, {}) if isinstance(tgt, dict) else {}
            return tgt
        return node

    # --------------------------------------------- schema simplification
    def resolve(self, node: Any, _depth: int = 0) -> Any:
        out = super().resolve(node, _depth)
        return self._simplify(out) if isinstance(out, dict) else out

    def _simplify(self, s: Dict[str, Any]) -> Dict[str, Any]:
        # OpenAPI 3.1: "type": ["string", "null"]
        t = s.get("type")
        if isinstance(t, list):
            non_null = [x for x in t if x != "null"]
            s = {**s, "type": non_null[0] if non_null else "string"}
            if "null" in t:
                s["nullable"] = True
        # allOf: merge
        if isinstance(s.get("allOf"), list):
            merged: Dict[str, Any] = {k: v for k, v in s.items() if k != "allOf"}
            for part in s["allOf"]:
                if isinstance(part, dict):
                    part = self._simplify(part)
                    props = {**merged.get("properties", {}), **part.get("properties", {})}
                    req = list(dict.fromkeys(merged.get("required", []) + part.get("required", [])))
                    merged.update({k: v for k, v in part.items() if k not in ("properties", "required")})
                    if props:
                        merged["properties"] = props
                    if req:
                        merged["required"] = req
            s = merged
        # anyOf / oneOf: choose the first non-null branch
        for key in ("anyOf", "oneOf"):
            if isinstance(s.get(key), list) and s[key]:
                has_null = any(isinstance(o, dict) and o.get("type") == "null" for o in s[key])
                chosen = _first_non_null(s[key])
                branch = self._simplify(chosen) if isinstance(chosen, dict) else {}
                s = {**{k: v for k, v in s.items() if k != key}, **branch}
                if has_null or s.get("nullable"):
                    s["nullable"] = True
        if "type" not in s:
            if "properties" in s:
                s = {**s, "type": "object"}
            elif "items" in s:
                s = {**s, "type": "array"}
        return s
