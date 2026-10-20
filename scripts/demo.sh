#!/usr/bin/env bash
# Live demo for the review. ~40 seconds. Run from the project root:  bash scripts/demo.sh
# Needs the venv with httpbin, gunicorn, chromadb, scikit-learn, requests, pyyaml installed.
set -u
V=${1:-$(dirname "$(which python)")}
say(){ printf "\n\033[1;34m== %s\033[0m\n" "$1"; }
say "1. Start two real open-source services (httpbin, ChromaDB)"
bash scripts/start_real_targets.sh "$V"
say "2. Run the pipeline on httpbin: parse spec -> generate tests -> execute -> semantic oracle -> detect -> rank"
python src/real_target_run.py targets/httpbin.json --out /tmp/demo_gate | tail -6
rm -f /tmp/demo_empty.json /tmp/demo_base.json; echo "{}" > /tmp/demo_empty.json
say "3. CI quality gate with an EMPTY baseline: new actionable findings should FAIL the build"
python src/ci_gate.py --target targets/httpbin.json --baseline /tmp/demo_empty.json --out /tmp/demo_gate --skip-run | tail -8
echo "exit code: ${PIPESTATUS[0]}"
say "4. Accept them into the baseline, then run again: the gate should PASS"
python src/ci_gate.py --target targets/httpbin.json --baseline /tmp/demo_base.json --out /tmp/demo_gate --skip-run --update-baseline | tail -1
python src/ci_gate.py --target targets/httpbin.json --baseline /tmp/demo_base.json --out /tmp/demo_gate --skip-run | tail -1
say "5. The defect itself, reproduced with one command"
curl -s -o /dev/null -w "GET /delay/abc -> HTTP %{http_code}\n" http://127.0.0.1:8081/delay/abc
say "6. Semantic oracle sensitivity on real ChromaDB responses (147 injected faults)"
python src/real_target_run.py chroma --out /tmp/demo_chroma | tail -1
python src/oracle_mutation_study.py --report /tmp/demo_chroma/run_report.json --out /tmp/demo_mutation.json | tail -9
