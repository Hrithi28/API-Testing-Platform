# Defect reports drafted from the evaluation (not yet filed)

Check each project's open AND closed issues first so you don't file duplicates.
How: open the repo's Issues tab, clear the default "is:open" filter, paste the search terms below, and read the top results.
  httpbin issues:  https://github.com/postmanlabs/httpbin/issues   (confirm this is the repo you installed from: `pip show httpbin` shows its home page)
  ChromaDB issues: https://github.com/chroma-core/chroma/issues
If a matching issue exists, add a short comment with your version and reproduction command instead of filing a new one.
If none exists, click New issue and paste the matching section below (one issue per defect). httpbin is lightly maintained, so a reply may not come.
All findings were reproduced 3/3 against locally hosted httpbin 0.10.4 and ChromaDB 1.5.9 (Python 3, default configuration).

## 1. httpbin: /delay/{n} returns HTTP 500 on non-numeric n
Repo: https://github.com/postmanlabs/httpbin   Search: `delay ValueError`, `delay 500`
Steps:
    pip install httpbin gunicorn && gunicorn -b 127.0.0.1:8081 httpbin:app &
    curl -i http://127.0.0.1:8081/delay/abc
Expected: 4xx (or the spec's declared client error) because `delay` is declared as an integer path parameter.
Actual: HTTP 500 with a stack trace (unhandled ValueError). Also occurs for DELETE, PATCH, POST and PUT on the same route.
Impact: unhandled exception on malformed input; stack trace disclosed.

## 2. ChromaDB: GET .../collections/{collection_id}/indexing_status returns 500 "not implemented"
Repo: https://github.com/chroma-core/chroma   Search: `indexing_status`, `not implemented`
Steps (server 1.5.9, default tenant/database, with an existing collection id):
    curl -i http://127.0.0.1:8082/api/v2/tenants/default_tenant/databases/default_database/collections/<collection_id>/indexing_status
Expected: 501 (as other unsupported operations return) or a documented response.
Actual: HTTP 500.

## 3. ChromaDB: GET /api/v2/healthcheck response does not match the OpenAPI schema
Search: `healthcheck openapi`
Steps: `curl -i http://127.0.0.1:8082/api/v2/healthcheck`
Spec says: 200 response is a string. Actual: a JSON object.

## 4. ChromaDB: GET .../databases omits fields the schema marks required
Search: `list databases openapi required`
Steps: `curl -i http://127.0.0.1:8082/api/v2/tenants/default_tenant/databases`
Spec requires `configuration_json` (and `database`, `log_position` per our checker output); the response items lack them.

## 5. ChromaDB: collection responses return embedding_function.type "unknown"; schema allows only "legacy"
Search: `embedding_function unknown openapi`
Steps: `curl -i http://127.0.0.1:8082/api/v2/tenants/default_tenant/databases/default_database/collections`
Path: `$[0].schema.defaults.sparse_vector.sparse_vector_index.config.embedding_function.type` = "unknown".
Same on `.../collections/by-id/{collection_id}`.

Tool used: AI-Powered Intelligent API Testing Platform (SSN College of Engineering, UG project). Offer to share the test suite and run reports.
