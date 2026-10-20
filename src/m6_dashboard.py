"""
Module 6 -- Reporting Dashboard generator.

Renders artifacts/run_report.json into a single self-contained HTML file
(no external assets) that can be opened directly in a browser during the demo.
"""
from __future__ import annotations
import base64
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts")

PRIORITY_COLOR = {"P1": "#B5484D", "P2": "#D98E2B", "P3": "#335295", "P4": "#6B7280"}
LABEL_COLOR = {"security": "#B5484D", "regression": "#D98E2B",
               "schema-drift": "#8E5FA8", "performance": "#2E8B7C"}


def b64(path: str) -> str:
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def build() -> str:
    report = json.load(open(os.path.join(ART, "run_report.json")))
    ev = json.load(open(os.path.join(ART, "evaluation.json")))
    c = report["counts"]
    de = report["defect_evaluation"]
    cv = ev["cross_validation"]
    base = ev["baseline_vs_full"]

    kpis = [
        ("Endpoints tested", f"{c['endpoints']}", "100% of spec"),
        ("Test cases generated", f"{c['test_cases']}", "4 categories"),
        ("Defects detected", f"{de['detected_count']}/{de['total_seeded']}",
         f"{de['detection_rate']:.0%} of seeded"),
        ("Critical findings", f"{c['priority_tiers']['P1']}", "P1 tier"),
        ("Detector F1", f"{cv.get('f1', 0):.3f}", "5-fold CV"),
        ("Total runtime", f"{report['timings']['total_s']:.1f}s", "end to end"),
    ]

    kpi_html = "".join(
        f"""<div class="kpi"><div class="kpi-label">{html.escape(l)}</div>
        <div class="kpi-value">{html.escape(v)}</div>
        <div class="kpi-sub">{html.escape(s)}</div></div>""" for l, v, s in kpis)

    # findings table
    rows = []
    for f in report["findings"]:
        pc = PRIORITY_COLOR.get(f["priority"], "#6B7280")
        lc = LABEL_COLOR.get(f["label"], "#6B7280")
        rows.append(f"""
        <tr>
          <td><span class="pill" style="background:{pc}">{f['priority']}</span></td>
          <td class="mono">{f['risk_score']:.2f}</td>
          <td class="mono">{html.escape(f['endpoint'])}</td>
          <td><span class="tag" style="color:{lc};border-color:{lc}">{html.escape(f['label'])}</span></td>
          <td>{html.escape(f['intent'])}</td>
          <td class="mono">{f['status_code']}</td>
          <td class="mono">{f['latency_ms']:.0f}</td>
          <td class="evidence">{html.escape(f['evidence'])}</td>
        </tr>""")
    findings_html = "".join(rows)

    # defect register
    drows = []
    for did, d in de["detected"].items():
        drows.append(f"""<tr><td class="mono">{did}</td>
          <td><span class="ok">detected</span></td>
          <td class="mono">{html.escape(d['endpoint'])}</td>
          <td>{html.escape(d['description'])}</td>
          <td class="mono">{html.escape(d['found_by'])}</td></tr>""")
    for did, d in de["missed"].items():
        drows.append(f"""<tr><td class="mono">{did}</td>
          <td><span class="miss">missed</span></td>
          <td class="mono">{html.escape(d['endpoint'])}</td>
          <td>{html.escape(d['description'])}</td>
          <td class="mono">&mdash;</td></tr>""")
    defects_html = "".join(drows)

    figs = {n: b64(os.path.join(ART, f"fig_{n}.png"))
            for n in ("baseline", "categories", "model", "latency")
            if os.path.exists(os.path.join(ART, f"fig_{n}.png"))}

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Testing Platform &mdash; Run Report</title>
<style>
  :root {{
    --navy:#335295; --navy-deep:#1B2A4A; --ink:#222; --muted:#6B7280;
    --line:#E1E6EE; --bg:#F5F7FA; --card:#fff;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         background:var(--bg); color:var(--ink); }}
  header {{ background:var(--navy); color:#fff; padding:26px 32px; }}
  header h1 {{ margin:0 0 4px; font-size:22px; font-weight:700; }}
  header p {{ margin:0; opacity:.85; font-size:13px; }}
  .wrap {{ max-width:1280px; margin:0 auto; padding:24px 32px 56px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
           gap:14px; margin:-46px 0 26px; }}
  .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:16px 18px; box-shadow:0 1px 3px rgba(20,40,80,.06); }}
  .kpi-label {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
  .kpi-value {{ font-size:27px; font-weight:700; color:var(--navy); margin:6px 0 2px; }}
  .kpi-sub {{ font-size:11.5px; color:var(--muted); }}
  section {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
             padding:22px 24px; margin-bottom:20px; }}
  h2 {{ margin:0 0 4px; font-size:16px; color:var(--navy-deep); }}
  .sub {{ margin:0 0 16px; font-size:12.5px; color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th {{ text-align:left; background:var(--navy); color:#fff; padding:9px 10px;
        font-weight:600; font-size:11.5px; position:sticky; top:0; }}
  td {{ padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  tr:hover td {{ background:#FAFBFD; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px; }}
  .pill {{ color:#fff; padding:2px 9px; border-radius:20px; font-size:11px; font-weight:700; }}
  .tag {{ border:1px solid; padding:1px 8px; border-radius:20px; font-size:11px; font-weight:600; }}
  .evidence {{ color:var(--muted); max-width:340px; }}
  .ok {{ color:#2E8B7C; font-weight:700; }}
  .miss {{ color:#B5484D; font-weight:700; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
  .grid2 img, .full img {{ width:100%; border:1px solid var(--line); border-radius:8px; }}
  .scroll {{ max-height:480px; overflow:auto; border:1px solid var(--line); border-radius:8px; }}
  .note {{ background:#EEF3FA; border-left:3px solid var(--navy); padding:12px 14px;
           border-radius:0 6px 6px 0; font-size:12.5px; color:#334; margin-top:16px; }}
  footer {{ text-align:center; color:var(--muted); font-size:11.5px; padding:10px 0 30px; }}
  @media (max-width:820px) {{ .grid2 {{ grid-template-columns:1fr; }} .wrap {{ padding:20px 16px 40px; }} }}
</style></head><body>
<header>
  <h1>AI-Powered Intelligent API Testing Platform</h1>
  <p>Run report &middot; target: <span class="mono">{html.escape(report['base_url'])}</span>
     &middot; spec: <span class="mono">{html.escape(report['spec_file'])}</span>
     &middot; generated {html.escape(report['generated_at'])}</p>
</header>
<div class="wrap">
  <div class="kpis">{kpi_html}</div>

  <section>
    <h2>Headline result</h2>
    <p class="sub">A conventional happy-path suite ({base['baseline']['tests']} tests) versus the
       full generated suite ({base['full']['tests']} tests), evaluated against the same
       {base['full']['total']} seeded defects.</p>
    <div class="full"><img src="data:image/png;base64,{figs.get('baseline','')}" alt="baseline comparison"></div>
  </section>

  <section>
    <h2>Risk-ranked findings</h2>
    <p class="sub">{len(report['findings'])} findings, ordered by risk score. P1 issues gate the CI pipeline.</p>
    <div class="scroll"><table>
      <thead><tr><th>Priority</th><th>Risk</th><th>Endpoint</th><th>Class</th>
      <th>Test intent</th><th>Status</th><th>ms</th><th>Evidence</th></tr></thead>
      <tbody>{findings_html}</tbody>
    </table></div>
  </section>

  <section>
    <h2>Seeded-defect register</h2>
    <p class="sub">Ground truth held out of the pipeline; used only for scoring after the run.</p>
    <table>
      <thead><tr><th>ID</th><th>Outcome</th><th>Endpoint</th><th>Defect</th><th>Found by</th></tr></thead>
      <tbody>{defects_html}</tbody>
    </table>
  </section>

  <section>
    <h2>Generation and prioritisation profile</h2>
    <div class="grid2">
      <img src="data:image/png;base64,{figs.get('categories','')}" alt="categories">
      <img src="data:image/png;base64,{figs.get('latency','')}" alt="latency">
    </div>
  </section>

  <section>
    <h2>Detector performance</h2>
    <p class="sub">Stratified 5-fold cross-validation over {cv.get('n_samples','n/a')} response records.</p>
    <div class="full"><img src="data:image/png;base64,{figs.get('model','')}" alt="model metrics"></div>
    <div class="note"><strong>Interpretation note.</strong> Training labels are derived from
      contract violations the platform can observe directly (5xx responses, schema breaches,
      unexpected status codes, successful security probes). The classifier therefore learns a
      rule overlapping its own label definition, so these scores measure internal consistency
      rather than generalisation to unseen defect families. This is reported as a limitation,
      and supervised learning over human-confirmed labels is the planned next step.</div>
  </section>

  <footer>Department of Information Technology &middot; SSN College of Engineering
    &middot; UG Project Work Phase I</footer>
</div></body></html>"""


if __name__ == "__main__":
    out = os.path.join(ART, "dashboard.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build())
    print("dashboard written:", out, f"({os.path.getsize(out)//1024} KB)")
