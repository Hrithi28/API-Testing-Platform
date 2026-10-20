"""
Module 1 -- Spec Parser & Endpoint Extractor.

Reads an OpenAPI 3.x document, resolves $ref pointers, and emits a normalised
endpoint model that every downstream module consumes.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Parameter:
    name: str
    location: str              # path | query | header
    required: bool
    schema: Dict[str, Any]


@dataclass
class Endpoint:
    operation_id: str
    method: str                # GET, POST, ...
    path: str                  # /pets/{petId}
    summary: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    request_schema: Optional[Dict[str, Any]] = None
    response_schemas: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    requires_auth: bool = False

    @property
    def signature(self) -> str:
        return f"{self.method} {self.path}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["signature"] = self.signature
        return d


class SpecParser:
    """Parses an OpenAPI 3.x spec into a list of Endpoint objects."""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.components = spec.get("components", {})

    # ---------------------------------------------------------------- load
    @classmethod
    def from_file(cls, path: str) -> "SpecParser":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))

    # ------------------------------------------------------------- $ref
    def resolve(self, node: Any, _depth: int = 0) -> Any:
        """Recursively resolve local $ref pointers ( #/components/... )."""
        if _depth > 25:
            return node
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                ref = node["$ref"]
                if ref.startswith("#/"):
                    target: Any = self.spec
                    for part in ref[2:].split("/"):
                        target = target.get(part, {}) if isinstance(target, dict) else {}
                    merged = self.resolve(target, _depth + 1)
                    # allow sibling keys to override the referenced object
                    extra = {k: v for k, v in node.items() if k != "$ref"}
                    if isinstance(merged, dict) and extra:
                        merged = {**merged, **self.resolve(extra, _depth + 1)}
                    return merged
                return node
            return {k: self.resolve(v, _depth + 1) for k, v in node.items()}
        if isinstance(node, list):
            return [self.resolve(v, _depth + 1) for v in node]
        return node

    # ------------------------------------------------------------- parse
    def parse(self) -> List[Endpoint]:
        endpoints: List[Endpoint] = []
        global_security = bool(self.spec.get("security"))

        for path, path_item in self.spec.get("paths", {}).items():
            shared_params = path_item.get("parameters", [])
            for method, op in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue

                params: List[Parameter] = []
                for raw in list(shared_params) + list(op.get("parameters", [])):
                    raw = self.resolve(raw)
                    params.append(Parameter(
                        name=raw.get("name", ""),
                        location=raw.get("in", "query"),
                        required=bool(raw.get("required", raw.get("in") == "path")),
                        schema=self.resolve(raw.get("schema", {})),
                    ))

                req_schema = None
                rb = self.resolve(op.get("requestBody", {}))
                if rb:
                    content = rb.get("content", {})
                    for ct in ("application/json", *content.keys()):
                        if ct in content:
                            req_schema = self.resolve(content[ct].get("schema", {}))
                            break

                resp_schemas: Dict[str, Dict[str, Any]] = {}
                for code, resp in op.get("responses", {}).items():
                    resp = self.resolve(resp)
                    content = resp.get("content", {})
                    if "application/json" in content:
                        resp_schemas[str(code)] = self.resolve(
                            content["application/json"].get("schema", {})
                        )

                endpoints.append(Endpoint(
                    operation_id=op.get("operationId") or f"{method}_{path}",
                    method=method.upper(),
                    path=path,
                    summary=op.get("summary", ""),
                    parameters=params,
                    request_schema=req_schema,
                    response_schemas=resp_schemas,
                    requires_auth=bool(op.get("security")) or global_security,
                ))
        return endpoints

    # -------------------------------------------------- dependency graph
    @staticmethod
    def dependency_graph(endpoints: List[Endpoint]) -> Dict[str, List[str]]:
        """
        Infers producer->consumer links: an endpoint that takes {xId} in its path
        depends on the collection endpoint that creates/lists that resource.
        """
        producers: Dict[str, str] = {}
        for ep in endpoints:
            if ep.method == "POST" and "{" not in ep.path:
                producers[ep.path.rstrip("/")] = ep.signature

        graph: Dict[str, List[str]] = {}
        for ep in endpoints:
            deps: List[str] = []
            if "{" in ep.path:
                collection = ep.path.split("{")[0].rstrip("/")
                if collection in producers and producers[collection] != ep.signature:
                    deps.append(producers[collection])
            graph[ep.signature] = deps
        return graph

    # ------------------------------------------------------- base server
    def base_url(self) -> str:
        servers = self.spec.get("servers", [])
        return servers[0]["url"].rstrip("/") if servers else ""


if __name__ == "__main__":
    import sys
    p = SpecParser.from_file(sys.argv[1] if len(sys.argv) > 1
                             else "demo_api/petstore_openapi.json")
    eps = p.parse()
    print(f"base url      : {p.base_url()}")
    print(f"endpoints     : {len(eps)}")
    for e in eps:
        print(f"  {e.signature:28s} params={len(e.parameters)} auth={e.requires_auth}")
    print("dependencies  :")
    for k, v in p.dependency_graph(eps).items():
        if v:
            print(f"  {k}  <-  {v}")
