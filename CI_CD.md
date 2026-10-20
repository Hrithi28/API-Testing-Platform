# CI/CD integration (Module 7)

`src/ci_gate.py` turns the pipeline into a build gate.

1. Runs Modules 1-5 and the Module 3b oracle against the target in `targets/<name>.json`.
2. Reduces raw findings to **actionable** ones: a 5xx (not 501) that reproduces three times
   when re-issued alone, or a 2xx response that breaks the operation's declared schema.
3. Compares them with `ci/accepted_findings.json` by stable fingerprint.
4. Writes `junit.xml` + `gate_summary.json`; exit code 0 = pass, 1 = new actionable finding, 2 = error.

Accept today's known findings (do this once, review the list first):

    python3 src/ci_gate.py --target targets/httpbin.json --update-baseline

Gate a change:

    python3 src/ci_gate.py --target targets/httpbin.json

Add your own service by copying `targets/httpbin.json`: set `spec`, `base_url`, `health_path`,
path-parameter `fixtures`, and any `exclude` patterns for destructive endpoints.

The workflow `.github/workflows/api-quality-gate.yml` runs this on every pull request.
