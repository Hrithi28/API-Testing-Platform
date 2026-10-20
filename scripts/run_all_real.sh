#!/usr/bin/env bash
# Reproduce the whole real-target evaluation from a clean state.
set -e
cd "$(dirname "$0")/.."
PY=${PY:-/home/claude/venv_real/bin/python}
bash scripts/start_real_targets.sh "$(dirname "$PY")"
$PY src/real_target_run.py httpbin
$PY src/real_target_run.py chroma
$PY src/label_findings.py
$PY src/retrain_detector.py
$PY src/oracle_mutation_study.py
