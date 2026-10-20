# AI-Powered Intelligent API Testing Platform: Review 3 package
- scripts/demo.sh                 live demo (about 40 s)
- scripts/run_all_real.sh         reproduce the whole real-service evaluation
- src/ci_gate.py                  CI quality gate; .github/workflows/api-quality-gate.yml; ci/accepted_findings.json
- src/apieval20_adapter.py        APIEval-20 suite generator; see apieval20_RUN.md
- artifacts_real/review_sheet_reviewer{A,B}.xlsx, review_sample_key.json, scripts/agreement.py   label review kit
- disclosure/DEFECT_REPORTS.md    five drafted defect reports (not filed)
- disclosure/results_explorer.html, disclosure/demo_transcript.txt   demo backups
Setup: python3 -m venv v && v/bin/pip install -r requirements-ci.txt
