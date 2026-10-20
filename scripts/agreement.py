"""Agreement between two human reviewers, and between each and the rubric.
usage: python3 scripts/agreement.py review_sheet_reviewerA.xlsx review_sheet_reviewerB.xlsx review_sample_key.json
Prints Cohen's kappa (A vs B), and kappa / accuracy of each reviewer and of the majority vs the rubric labels."""
import json, sys
from openpyxl import load_workbook

def col(path):
    ws = load_workbook(path)["Review"]
    return [str(r[6].value or "").strip().upper()[:1] for r in ws.iter_rows(min_row=2)]

def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in "YN")
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po

A, B = col(sys.argv[1]), col(sys.argv[2])
key = json.load(open(sys.argv[3])); R = ["Y" if k["rubric_label"] else "N" for k in key]
assert all(x in "YN" for x in A + B), "some rows are blank or not Y/N"
k, po = kappa(A, B); print(f"A vs B: kappa={k:.2f}  raw agreement={po:.0%}  (n={len(A)})")
for nm, X in (("A", A), ("B", B)):
    k, po = kappa(X, R); print(f"{nm} vs rubric: kappa={k:.2f}  agreement={po:.0%}")
agree = [x for x, y in zip(A, B) if x == y]
print("disagreements to resolve:", [i + 1 for i, (x, y) in enumerate(zip(A, B)) if x != y])
