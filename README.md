# AI-Powered Intelligent API Testing Platform

UG Project Work Phase I — Review 2
Department of Information Technology, SSN College of Engineering

## What this is

A six-module pipeline that generates an API test suite from an OpenAPI
specification, executes it, detects anomalies with machine learning, and
ranks findings by risk.

| Module | File | Role |
|---|---|---|
| M1 | `src/m1_spec_parser.py` | OpenAPI parsing, `$ref` resolution, dependency inference |
| M2 | `src/m2_test_generator.py` | Positive / negative / boundary / security case generation |
| M3 | `src/m3_executor.py` | Parallel execution + JSON-Schema conformance checking |
| M4 | `src/m4_anomaly_detector.py` | Isolation Forest + Random Forest detection |
| M5 | `src/m4_anomaly_detector.py` | Risk scoring and P1–P4 tiering (`RiskEngine`) |
| M6 | `src/m6_dashboard_v2.py` | Interactive HTML dashboard (sortable/filterable tables, client-side charts, drill-down) |

## Requirements

    pip install flask requests scikit-learn numpy matplotlib

## Running the demo

Open two terminals.

Terminal 1 — start the system under test:

    python3 demo_api/target_api.py

Terminal 2 — run the pipeline, in this order:

    python3 src/run_pipeline.py      # full pipeline, writes artifacts/run_report.json
    python3 src/evaluate.py          # baseline comparison, repeat runs, cross-validation
    python3 src/make_diagram.py      # renders artifacts/block_diagram.png (no API needed)
    python3 src/make_charts.py       # renders the other result figures
    python3 src/m6_dashboard_v2.py   # builds the interactive artifacts/dashboard.html

Then open `artifacts/dashboard.html` in a browser — no server needed, it's a
single self-contained file. `make_diagram.py` and `make_charts.py` must run
before `m6_dashboard_v2.py`, since the dashboard embeds their PNG output.

## The benchmark

`demo_api/target_api.py` contains 8 deliberately seeded defects, documented in
its `SEEDED_DEFECTS` dictionary. The pipeline never reads that register; it is
used only afterwards by the scoring code in `src/run_pipeline.py` to compute
the defect-detection rate.

## Results obtained

| Metric | Value |
|---|---|
| Endpoint / parameter coverage | 100% (7/7) |
| Test cases generated | 47 (8 positive, 6 negative, 22 boundary, 11 security) |
| Seeded defects detected | 8 / 8 |
| Happy-path baseline detection | 0 / 8 |
| Detector precision / recall / F1 (5-fold CV) | 1.00 / 0.90 / 0.947 |
| False-positive rate | 0.0 |
| End-to-end runtime | 3.88 s |
| Run-to-run stability (5 runs) | SD 0.00 |

## Known limitations

1. **Synthetic benchmark.** The defects were injected into a service authored
   for this project, not observed in production software.
2. **Circular supervised labels.** The Random Forest trains on contract
   violations that are also among its input features, so its precision/recall
   measure internal consistency, not generalisation. The defect-detection rate
   above is independent of this, since it scores against the held-out register.
3. **Heuristic dependency inference.** `M1` links operations by field-name
   matching. KAT (Le et al., ICST 2024) shows an LLM-built operation-dependency
   graph improves status-code coverage by 15.7% over this class of heuristic on
   real services — a candidate upgrade for Review 3.
4. **Small scale.** One specification, 7 endpoints, 47 tests.
5. **LLM backend unexercised.** `LLMBackend` in `m2_test_generator.py` is
   implemented but requires `ANTHROPIC_API_KEY`; all reported results use the
   deterministic schema-driven backend.

## Optional: enabling the LLM backend

    export ANTHROPIC_API_KEY=...
    # then in run_pipeline.py:
    #   from m2_test_generator import TestGenerator, LLMBackend
    #   gen = TestGenerator(backend=LLMBackend())
