# Scoring OUR adapter's suites on APIEval-20 (about 5 minutes)

Your earlier run (results.json, 0.6559) used the heuristic generator in your api-eval-20 folder, not our adapter.
To score ours, from inside your api-eval-20 folder:

    export APIEVAL_BASE_URL="https://eval.kusho.ai"
    export APIEVAL_GRADE_URL="https://eval.kusho.ai"      # use whatever URLs you used last time
    unzip -o apieval20_suites_ours.zip -d suites_ours
    python3 eval/evaluate.py --all --suite-dir ./suites_ours/ --output results_ours.json

Scenario 19 returned no grading result last time (total_bugs 0). Re-run it alone, for both suite sets:

    python3 eval/evaluate.py --suite suites/19_search_query_suite.json --scenario 19_search_query
    python3 eval/evaluate.py --suite suites_ours/19_search_query_suite.json --scenario 19_search_query

Send me results_ours.json (and the scenario-19 output) and I will put the numbers in the deck, paper and report.
Locally verified with the benchmark's own coverage functions: our suites reach parameter coverage 1.00 and edge coverage 1.00 on all 20 scenarios.
