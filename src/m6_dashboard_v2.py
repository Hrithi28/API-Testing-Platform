"""
Module 6 v2 -- Interactive Reporting Dashboard.

Unlike m6_dashboard.py (a static HTML report with pre-rendered PNG charts),
this embeds the full run data as JSON and renders everything client-side with
vanilla JS: sortable/filterable findings and test-case tables, SVG charts
built from live data, and cross-tab drill-down (defect -> the exact finding
that caught it -> the exact request that produced it). No CDN, no server,
no build step -- one file, opens directly in a browser.
"""
from __future__ import annotations
import base64
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts")


def b64(path: str) -> str:
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def build() -> str:
    report = json.load(open(os.path.join(ART, "run_report.json")))
    ev = json.load(open(os.path.join(ART, "evaluation.json")))
    diagram_path = os.path.join(ART, "block_diagram.png")
    if os.path.exists(diagram_path):
        diagram_b64 = b64(diagram_path)
        diagram_html = f'<img class="diagram-img" src="data:image/png;base64,{diagram_b64}" alt="architecture">'
    else:
        diagram_html = (
            '<div style="padding:40px;text-align:center;background:#FBECDD;'
            'border:1px dashed #D98E2B;border-radius:8px;color:#8A5A1A;font-size:13px">'
            '<b>Diagram not found.</b> Run <code>python3 src/make_diagram.py</code> first, '
            'then rebuild this dashboard.</div>'
        )

    data_json = json.dumps(report, separators=(",", ":")).replace("</", "<\\/")
    eval_json = json.dumps(ev, separators=(",", ":")).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Testing Platform — Interactive Run Report</title>
<style>
{CSS}
</style></head>
<body>
{HTML_BODY.replace('__DIAGRAM_HTML__', diagram_html)}
<script id="report-data" type="application/json">{data_json}</script>
<script id="eval-data" type="application/json">{eval_json}</script>
<script>
{JS}
</script>
</body></html>"""


CSS = r"""
:root{
  --navy:#335295; --navy-d:#1B2A4A; --teal:#2E8B7C; --amber:#D98E2B;
  --plum:#8E5FA8; --red:#B5484D; --grey:#6B7280; --ink:#222;
  --line:#E1E6EE; --bg:#F5F7FA; --card:#fff;
}
*{box-sizing:border-box;}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     background:var(--bg);color:var(--ink);}
header{background:var(--navy);color:#fff;padding:22px 28px 60px;}
header h1{margin:0 0 4px;font-size:21px;font-weight:700;}
header p{margin:0;opacity:.85;font-size:12.5px;}
header .mono{font-family:ui-monospace,Menlo,monospace;}
.wrap{max-width:1360px;margin:0 auto;padding:0 24px 50px;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
      gap:12px;margin:-42px 0 18px;}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;
     padding:14px 16px;box-shadow:0 1px 3px rgba(20,40,80,.07);}
.kpi-label{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--grey);}
.kpi-value{font-size:24px;font-weight:700;color:var(--navy);margin:4px 0 1px;}
.kpi-sub{font-size:11px;color:var(--grey);}
nav.tabs{display:flex;gap:4px;margin-bottom:16px;border-bottom:2px solid var(--line);
         flex-wrap:wrap;}
nav.tabs button{background:none;border:none;padding:10px 16px;font-size:13px;font-weight:600;
     color:var(--grey);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;
     transition:color .15s;}
nav.tabs button:hover{color:var(--navy);}
nav.tabs button.active{color:var(--navy);border-bottom-color:var(--navy);}
nav.tabs button .count{background:var(--line);color:var(--grey);border-radius:20px;
     padding:1px 7px;font-size:10.5px;margin-left:6px;}
nav.tabs button.active .count{background:var(--navy);color:#fff;}
section.tab{display:none;}
section.tab.active{display:block;}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
      padding:20px 22px;margin-bottom:18px;}
.card h2{margin:0 0 3px;font-size:15px;color:var(--navy-d);}
.card .sub{margin:0 0 14px;font-size:12px;color:var(--grey);}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;}
@media(max-width:900px){.grid2,.grid4{grid-template-columns:1fr;}}

.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;}
.toolbar input[type=search]{flex:1;min-width:200px;padding:8px 12px;border:1px solid var(--line);
     border-radius:7px;font-size:12.5px;background:#FAFBFD;}
.toolbar input[type=search]:focus{outline:2px solid var(--navy);outline-offset:-1px;}
.chipgroup{display:flex;gap:5px;flex-wrap:wrap;}
.chip{border:1px solid var(--line);background:#fff;border-radius:20px;padding:4px 11px;
      font-size:11px;font-weight:600;cursor:pointer;color:var(--grey);user-select:none;
      transition:all .12s;}
.chip.on{color:#fff;border-color:transparent;}
.chip[data-p1].on{background:var(--red);} .chip[data-p2].on{background:var(--amber);}
.chip[data-p3].on{background:var(--navy);} .chip[data-p4].on{background:var(--grey);}
.chip[data-cat].on{background:var(--navy);} .chip[data-lab].on{background:var(--plum);}
.result-count{font-size:11.5px;color:var(--grey);margin-left:auto;}

table{width:100%;border-collapse:collapse;font-size:12px;}
thead th{text-align:left;background:var(--navy);color:#fff;padding:8px 9px;
     font-weight:600;font-size:10.8px;cursor:pointer;user-select:none;white-space:nowrap;}
thead th:hover{background:#2A4478;}
thead th .arrow{opacity:.6;font-size:9px;margin-left:3px;}
tbody td{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top;}
tbody tr.rowmain{cursor:pointer;}
tbody tr.rowmain:hover td{background:#FAFBFD;}
tbody tr.rowmain.flash td{background:#FFF3D6 !important;}
tbody tr.detail td{background:#F7F9FC;padding:14px 18px;border-bottom:2px solid var(--line);}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:11px;}
.pill{color:#fff;padding:2px 8px;border-radius:20px;font-size:10.5px;font-weight:700;
      display:inline-block;}
.tag{border:1px solid;padding:1px 7px;border-radius:20px;font-size:10.5px;font-weight:600;
     display:inline-block;}
.scroll{max-height:560px;overflow:auto;border:1px solid var(--line);border-radius:8px;}

.detailgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px;font-size:11.5px;}
.detailgrid h4{margin:0 0 6px;font-size:11px;color:var(--navy);text-transform:uppercase;
     letter-spacing:.04em;}
.kv{display:grid;grid-template-columns:110px 1fr;gap:4px 10px;margin-bottom:3px;}
.kv b{color:var(--grey);font-weight:600;}
pre.jsonblock{background:#0E1621;color:#CBD7E6;padding:10px 12px;border-radius:6px;
     font-size:10.8px;overflow:auto;max-height:160px;margin:4px 0 0;}
.evidence-box{background:#FBF3E5;border-left:3px solid var(--amber);padding:9px 12px;
     border-radius:0 6px 6px 0;margin-top:8px;}

.chart{width:100%;height:auto;}
.chart .bar-label{font-size:10.5px;fill:#444;}
.chart .bar-value{font-size:11px;font-weight:700;fill:#222;}
.chart .axis{stroke:#D7DEE9;stroke-width:1;}

.defect-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;}
.defect-card{border:1px solid var(--line);border-radius:9px;padding:14px 16px;position:relative;}
.defect-card.detected{border-left:4px solid var(--teal);}
.defect-card.missed{border-left:4px solid var(--red);}
.defect-card .id{font-family:ui-monospace,Menlo,monospace;font-weight:700;color:var(--navy);
     font-size:12.5px;}
.defect-card .status{float:right;font-size:10.5px;font-weight:700;}
.defect-card.detected .status{color:var(--teal);}
.defect-card.missed .status{color:var(--red);}
.defect-card .ep{font-family:ui-monospace,Menlo,monospace;font-size:10.8px;color:var(--grey);
     margin:5px 0 6px;}
.defect-card .desc{font-size:11.5px;color:#333;line-height:1.4;margin-bottom:9px;}
.defect-card button{background:var(--navy);color:#fff;border:none;border-radius:6px;
     padding:6px 12px;font-size:10.8px;font-weight:600;cursor:pointer;}
.defect-card button:hover{background:#2A4478;}
.defect-card .missnote{font-size:10.8px;color:var(--red);font-style:italic;}

.note{background:#EEF3FA;border-left:3px solid var(--navy);padding:12px 14px;
     border-radius:0 6px 6px 0;font-size:12px;color:#334;margin-top:14px;}
.methodtable td, .methodtable th{padding:9px;}
footer{text-align:center;color:var(--grey);font-size:11px;padding:14px 0 30px;}
.diagram-img{width:100%;border:1px solid var(--line);border-radius:8px;margin-top:6px;}
"""

HTML_BODY = r"""
<header>
  <h1>AI-Powered Intelligent API Testing Platform</h1>
  <p id="meta-line">Interactive run report</p>
</header>
<div class="wrap">
  <div class="kpis" id="kpis"></div>

  <nav class="tabs" id="tabs">
    <button data-tab="overview" class="active">Overview</button>
    <button data-tab="findings">Findings <span class="count" id="cnt-findings"></span></button>
    <button data-tab="tests">Test Suite <span class="count" id="cnt-tests"></span></button>
    <button data-tab="defects">Defect Register <span class="count" id="cnt-defects"></span></button>
    <button data-tab="arch">Architecture</button>
  </nav>

  <section class="tab active" id="tab-overview">
    <div class="card">
      <h2>Defect detection: happy-path baseline vs. full pipeline</h2>
      <p class="sub">Same 8 seeded defects, two suites evaluated against them.</p>
      <svg id="chart-baseline" class="chart"></svg>
    </div>
    <div class="grid2">
      <div class="card"><h2>Generated test cases by category</h2>
        <p class="sub">47 cases synthesised from the specification.</p>
        <svg id="chart-categories" class="chart"></svg></div>
      <div class="card"><h2>Findings by risk priority</h2>
        <p class="sub">P1 tier gates the CI/CD pipeline.</p>
        <svg id="chart-priority" class="chart"></svg></div>
    </div>
    <div class="grid2">
      <div class="card"><h2>Response latency distribution</h2>
        <p class="sub">Log-scale buckets, all 47 executed calls.</p>
        <svg id="chart-latency" class="chart"></svg></div>
      <div class="card"><h2>Most informative response features</h2>
        <p class="sub">Random Forest Gini importance.</p>
        <svg id="chart-features" class="chart"></svg></div>
    </div>
    <div class="card">
      <h2>Detector confusion matrix</h2>
      <p class="sub" id="cv-sub"></p>
      <div id="confusion" style="max-width:340px"></div>
      <div class="note">
        <b>Interpretation note.</b> Training labels are derived from contract violations the
        model also observes as features (5xx, schema breach, unexpected status, successful
        security probe). These scores measure internal consistency, not generalisation to
        unseen defect families — reported here as a limitation, not as accuracy on new data.
      </div>
    </div>
  </section>

  <section class="tab" id="tab-findings">
    <div class="card">
      <div class="toolbar">
        <input type="search" id="find-search" placeholder="Search endpoint, intent, evidence, test id…">
        <span class="result-count" id="find-count"></span>
      </div>
      <div class="toolbar">
        <div class="chipgroup" id="chips-priority"></div>
        <div class="chipgroup" id="chips-label"></div>
      </div>
      <div class="scroll">
        <table id="findings-table">
          <thead><tr>
            <th data-key="priority">Priority</th>
            <th data-key="risk_score">Risk</th>
            <th data-key="endpoint">Endpoint</th>
            <th data-key="label">Class</th>
            <th data-key="intent">Test intent</th>
            <th data-key="status_code">Status</th>
            <th data-key="latency_ms">ms</th>
          </tr></thead>
          <tbody id="findings-body"></tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="tab" id="tab-tests">
    <div class="card">
      <div class="toolbar">
        <input type="search" id="test-search" placeholder="Search test id, endpoint, intent…">
        <span class="result-count" id="test-count"></span>
      </div>
      <div class="toolbar">
        <div class="chipgroup" id="chips-category"></div>
      </div>
      <div class="scroll">
        <table id="tests-table">
          <thead><tr>
            <th data-key="test_id">Test ID</th>
            <th data-key="category">Category</th>
            <th data-key="endpoint">Endpoint</th>
            <th data-key="intent">Intent</th>
            <th data-key="status_code">Actual</th>
            <th data-key="status_as_expected">As expected?</th>
            <th data-key="latency_ms">ms</th>
            <th>Flagged</th>
          </tr></thead>
          <tbody id="tests-body"></tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="tab" id="tab-defects">
    <div class="card">
      <h2>Seeded-defect register</h2>
      <p class="sub">Ground truth held out of the pipeline; used only to score the run afterwards.</p>
      <div class="defect-grid" id="defect-grid"></div>
    </div>
  </section>

  <section class="tab" id="tab-arch">
    <div class="card">
      <h2>System architecture</h2>
      __DIAGRAM_HTML__
    </div>
    <div class="card">
      <h2>Algorithms and technologies per module</h2>
      <table class="methodtable">
        <thead><tr style="background:var(--navy)">
          <th style="color:#fff">Module</th><th style="color:#fff">Algorithm / technique</th>
          <th style="color:#fff">Technology</th></tr></thead>
        <tbody id="method-body"></tbody>
      </table>
    </div>
  </section>

  <footer>Department of Information Technology · SSN College of Engineering · UG Project Work Phase I</footer>
</div>
"""

JS = r"""
const R = JSON.parse(document.getElementById('report-data').textContent);
const E = JSON.parse(document.getElementById('eval-data').textContent);
const NAVY='#335295', TEAL='#2E8B7C', AMBER='#D98E2B', PLUM='#8E5FA8', RED='#B5484D', GREY='#6B7280';
const PCOLOR={P1:RED,P2:AMBER,P3:NAVY,P4:GREY};
const LCOLOR={security:RED,regression:AMBER,'schema-drift':PLUM,performance:TEAL};

// ---- merge test_cases + results + findings by test_id for drill-down -----
const byId = {};
R.test_cases.forEach(tc => byId[tc.test_id] = {request: tc});
R.results.forEach(r => { (byId[r.test_id] ||= {}).response = r; });
R.findings.forEach(f => { (byId[f.test_id] ||= {}).finding = f; });

// ================================================================ header
document.getElementById('meta-line').innerHTML =
  `target: <span class="mono">${R.base_url}</span> &middot; spec: <span class="mono">${R.spec_file}</span> &middot; generated ${R.generated_at}`;

// ================================================================ KPIs
const cv = E.cross_validation, de = R.defect_evaluation, c = R.counts;
const kpis = [
  ['Endpoints tested', c.endpoints, '100% of spec'],
  ['Test cases generated', c.test_cases, '4 categories'],
  ['Defects detected', `${de.detected_count}/${de.total_seeded}`, `${Math.round(de.detection_rate*100)}% of seeded`],
  ['Critical findings', c.priority_tiers.P1, 'P1 tier'],
  ['Detector F1', (cv.f1||0).toFixed(3), '5-fold CV'],
  ['Total runtime', R.timings.total_s.toFixed(1)+'s', 'end to end'],
];
document.getElementById('kpis').innerHTML = kpis.map(([l,v,s]) =>
  `<div class="kpi"><div class="kpi-label">${l}</div><div class="kpi-value">${v}</div><div class="kpi-sub">${s}</div></div>`).join('');
document.getElementById('cnt-findings').textContent = R.findings.length;
document.getElementById('cnt-tests').textContent = R.test_cases.length;
document.getElementById('cnt-defects').textContent = de.total_seeded;

// ================================================================ tabs
document.getElementById('tabs').addEventListener('click', e => {
  const btn = e.target.closest('button[data-tab]'); if (!btn) return;
  document.querySelectorAll('nav.tabs button').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('section.tab').forEach(s => s.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
});

// ================================================================ SVG bar chart helper
function barChart(svgEl, items, {horizontal=false, width=560, height=230, fmt=v=>v} = {}) {
  const pad = horizontal ? {l:130,r:44,t:10,b:10} : {l:40,r:16,t:26,b:54};
  const innerW = width - pad.l - pad.r, innerH = height - pad.t - pad.b;
  const max = Math.max(...items.map(d=>d.value), 1);
  svgEl.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svgEl.innerHTML = '';
  const ns = 'http://www.w3.org/2000/svg';
  const mk = (tag, attrs) => { const el = document.createElementNS(ns, tag);
    for (const k in attrs) el.setAttribute(k, attrs[k]); return el; };

  if (horizontal) {
    const bw = innerH / items.length * 0.62;
    items.forEach((d, i) => {
      const y = pad.t + i * (innerH/items.length) + (innerH/items.length - bw)/2;
      const w = innerW * d.value / max;
      svgEl.appendChild(mk('rect', {x:pad.l, y, width:Math.max(w,2), height:bw, fill:d.color||NAVY, rx:3}));
      const lab = mk('text', {x:pad.l-8, y:y+bw/2+4, 'text-anchor':'end', class:'bar-label'});
      lab.textContent = d.label; svgEl.appendChild(lab);
      const val = mk('text', {x:pad.l+w+6, y:y+bw/2+4, class:'bar-value'});
      val.textContent = fmt(d.value); svgEl.appendChild(val);
    });
  } else {
    const bw = innerW / items.length * 0.55;
    const gap = innerW / items.length;
    items.forEach((d, i) => {
      const h = innerH * d.value / max;
      const x = pad.l + i*gap + (gap-bw)/2;
      const y = pad.t + innerH - h;
      svgEl.appendChild(mk('rect', {x, y, width:bw, height:Math.max(h,1), fill:d.color||NAVY, rx:3}));
      const val = mk('text', {x:x+bw/2, y:y-6, 'text-anchor':'middle', class:'bar-value'});
      val.textContent = fmt(d.value); svgEl.appendChild(val);
      const lab = mk('text', {x:x+bw/2, y:pad.t+innerH+18, 'text-anchor':'middle', class:'bar-label'});
      lab.textContent = d.label; svgEl.appendChild(lab);
    });
    svgEl.appendChild(mk('line', {x1:pad.l, y1:pad.t+innerH, x2:pad.l+innerW, y2:pad.t+innerH, class:'axis'}));
  }
}

// ---- overview charts ----
barChart(document.getElementById('chart-baseline'),
  [{label:`Happy-path (${E.baseline_vs_full.baseline.tests})`, value:E.baseline_vs_full.baseline.detected, color:GREY},
   {label:`Full pipeline (${E.baseline_vs_full.full.tests})`, value:E.baseline_vs_full.full.detected, color:NAVY}],
  {width:900, height:230});

barChart(document.getElementById('chart-categories'),
  ['positive','negative','boundary','security'].map(k =>
    ({label:k[0].toUpperCase()+k.slice(1), value:c.by_category[k],
      color:{positive:TEAL,negative:AMBER,boundary:NAVY,security:RED}[k]})),
  {width:520, height:220});

barChart(document.getElementById('chart-priority'),
  ['P1','P2','P3','P4'].map(k => ({label:k, value:c.priority_tiers[k], color:PCOLOR[k]})),
  {width:520, height:220});

// latency histogram, log-spaced buckets
(() => {
  const lats = R.results.map(r=>r.latency_ms).filter(v=>v>0);
  const lo = Math.log10(Math.min(...lats)), hi = Math.log10(Math.max(...lats)*1.05);
  const n = 8, buckets = Array(n).fill(0), edges=[];
  for (let i=0;i<=n;i++) edges.push(Math.pow(10, lo + (hi-lo)*i/n));
  lats.forEach(v => { for (let i=0;i<n;i++) if (v>=edges[i] && v<edges[i+1]) { buckets[i]++; return;} buckets[n-1]++; });
  const items = buckets.map((v,i) => ({label: edges[i]<10?edges[i].toFixed(1):Math.round(edges[i])+'', value:v, color:NAVY}));
  barChart(document.getElementById('chart-latency'), items, {width:520, height:220});
})();

// feature importance
const feats = Object.entries(R.model_metrics.feature_importance || {}).slice(0,7)
  .map(([k,v]) => ({label:k.replace(/_/g,' '), value:v, color:NAVY}));
barChart(document.getElementById('chart-features'), feats, {horizontal:true, width:520, height:220, fmt:v=>v.toFixed(3)});

// confusion matrix
(() => {
  const cm = cv.confusion_matrix || {tn:0,fp:0,fn:0,tp:0};
  document.getElementById('cv-sub').textContent =
    `Stratified 5-fold CV over ${cv.n_samples} responses — P=${cv.precision} R=${cv.recall} F1=${cv.f1}`;
  const mx = Math.max(cm.tn,cm.fp,cm.fn,cm.tp,1);
  const cell = (v,label) => { const t = v/mx;
    const bg = `rgba(51,82,149,${0.12+0.75*t})`, fg = t>0.55 ? '#fff':'#1B2A4A';
    return `<div style="background:${bg};color:${fg};padding:18px 8px;text-align:center;border-radius:6px;font-weight:700;font-size:20px">${v}<div style="font-size:10px;font-weight:600;opacity:.85;margin-top:3px">${label}</div></div>`; };
  document.getElementById('confusion').innerHTML = `
    <div style="display:grid;grid-template-columns:80px 1fr 1fr;gap:6px;font-size:11px;align-items:center">
      <div></div><div style="text-align:center;color:#667;font-weight:600">Pred: normal</div><div style="text-align:center;color:#667;font-weight:600">Pred: faulty</div>
      <div style="color:#667;font-weight:600">Actual: normal</div>${cell(cm.tn,'TN')}${cell(cm.fp,'FP')}
      <div style="color:#667;font-weight:600">Actual: faulty</div>${cell(cm.fn,'FN')}${cell(cm.tp,'TP')}
    </div>`;
})();

// ================================================================ FINDINGS TAB
let findState = { search:'', priorities:new Set(['P1','P2','P3','P4']), labels:new Set(), sortKey:'risk_score', sortDir:-1 };
const allLabels = [...new Set(R.findings.map(f=>f.label))];

document.getElementById('chips-priority').innerHTML = ['P1','P2','P3','P4'].map(p =>
  `<span class="chip on" data-p${p.slice(1)} data-priority="${p}">${p}</span>`).join('');
document.getElementById('chips-label').innerHTML = allLabels.map(l =>
  `<span class="chip" data-lab data-label="${l}" style="border-color:${LCOLOR[l]||GREY}">${l}</span>`).join('');

document.getElementById('chips-priority').addEventListener('click', e => {
  const chip = e.target.closest('.chip'); if (!chip) return;
  const p = chip.dataset.priority;
  chip.classList.toggle('on');
  if (findState.priorities.has(p)) findState.priorities.delete(p); else findState.priorities.add(p);
  renderFindings();
});
document.getElementById('chips-label').addEventListener('click', e => {
  const chip = e.target.closest('.chip'); if (!chip) return;
  const l = chip.dataset.label;
  chip.classList.toggle('on');
  if (findState.labels.has(l)) findState.labels.delete(l); else findState.labels.add(l);
  renderFindings();
});
document.getElementById('find-search').addEventListener('input', e => {
  findState.search = e.target.value.toLowerCase(); renderFindings();
});
document.querySelector('#findings-table thead').addEventListener('click', e => {
  const th = e.target.closest('th[data-key]'); if (!th) return;
  const key = th.dataset.key;
  if (findState.sortKey === key) findState.sortDir *= -1;
  else { findState.sortKey = key; findState.sortDir = 1; }
  renderFindings();
});

function detailRowHTML(id) {
  const rec = byId[id] || {};
  const req = rec.request || {}, resp = rec.response || {}, find = rec.finding || {};
  const evidence = find.evidence ? `<div class="evidence-box"><b>Evidence:</b> ${escapeHtml(find.evidence)}</div>` : '';
  return `<tr class="detail"><td colspan="8"><div class="detailgrid">
    <div><h4>Request</h4>
      <div class="kv"><b>Method</b><span class="mono">${req.method||''}</span></div>
      <div class="kv"><b>Path</b><span class="mono">${req.path||''}</span></div>
      <div class="kv"><b>Expected</b><span class="mono">${(req.expected_status||[]).join(', ')}</span></div>
      <pre class="jsonblock">${escapeHtml(JSON.stringify({query:req.query,headers:req.headers,body:req.body}, null, 2))}</pre>
    </div>
    <div><h4>Response</h4>
      <div class="kv"><b>Status</b><span class="mono">${resp.status_code!=null?resp.status_code:''}</span></div>
      <div class="kv"><b>Latency</b><span class="mono">${resp.latency_ms!=null?resp.latency_ms+' ms':''}</span></div>
      <div class="kv"><b>As expected</b><span class="mono">${resp.status_as_expected}</span></div>
      <pre class="jsonblock">${escapeHtml(resp.body_preview||'')}</pre>
      ${evidence}
    </div>
  </div></td></tr>`;
}
function escapeHtml(s){ return String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

let expandedFinding = null;
function renderFindings(highlightId) {
  let rows = R.findings.filter(f => findState.priorities.has(f.priority));
  if (findState.labels.size) rows = rows.filter(f => findState.labels.has(f.label));
  if (findState.search) {
    const q = findState.search;
    rows = rows.filter(f => (f.endpoint+f.intent+f.evidence+f.test_id).toLowerCase().includes(q));
  }
  rows.sort((a,b) => {
    const k = findState.sortKey, d = findState.sortDir;
    return (a[k] > b[k] ? 1 : a[k] < b[k] ? -1 : 0) * d;
  });
  document.getElementById('find-count').textContent = rows.length + ' of ' + R.findings.length;
  const body = document.getElementById('findings-body');
  body.innerHTML = rows.map(f => `
    <tr class="rowmain${f.test_id===highlightId?' flash':''}" data-id="${f.test_id}">
      <td><span class="pill" style="background:${PCOLOR[f.priority]}">${f.priority}</span></td>
      <td class="mono">${f.risk_score.toFixed(2)}</td>
      <td class="mono">${f.endpoint}</td>
      <td><span class="tag" style="color:${LCOLOR[f.label]||GREY};border-color:${LCOLOR[f.label]||GREY}">${f.label}</span></td>
      <td>${escapeHtml(f.intent)}</td>
      <td class="mono">${f.status_code}</td>
      <td class="mono">${f.latency_ms.toFixed(0)}</td>
    </tr>`).join('');
  body.querySelectorAll('tr.rowmain').forEach(tr => tr.addEventListener('click', () => {
    const id = tr.dataset.id;
    const next = tr.nextElementSibling;
    if (next && next.classList.contains('detail')) { next.remove(); return; }
    document.querySelectorAll('#findings-body tr.detail').forEach(d=>d.remove());
    tr.insertAdjacentHTML('afterend', detailRowHTML(id));
  }));
  if (highlightId) {
    const tr = body.querySelector(`tr[data-id="${highlightId}"]`);
    if (tr) { tr.scrollIntoView({block:'center'}); tr.click(); setTimeout(()=>tr.classList.remove('flash'), 2200); }
  }
}
renderFindings();

// ================================================================ TEST SUITE TAB
let testState = { search:'', categories:new Set(['positive','negative','boundary','security']), sortKey:'test_id', sortDir:1 };
document.getElementById('chips-category').innerHTML = ['positive','negative','boundary','security'].map(cat =>
  `<span class="chip on" data-cat data-cat-val="${cat}">${cat}</span>`).join('');
document.getElementById('chips-category').addEventListener('click', e => {
  const chip = e.target.closest('.chip'); if (!chip) return;
  const cat = chip.dataset.catVal; chip.classList.toggle('on');
  if (testState.categories.has(cat)) testState.categories.delete(cat); else testState.categories.add(cat);
  renderTests();
});
document.getElementById('test-search').addEventListener('input', e => { testState.search = e.target.value.toLowerCase(); renderTests(); });
document.querySelector('#tests-table thead').addEventListener('click', e => {
  const th = e.target.closest('th[data-key]'); if (!th) return;
  const key = th.dataset.key;
  if (testState.sortKey === key) testState.sortDir *= -1; else { testState.sortKey = key; testState.sortDir = 1; }
  renderTests();
});
function renderTests() {
  let rows = R.results.filter(r => testState.categories.has(r.category));
  if (testState.search) { const q = testState.search;
    rows = rows.filter(r => (r.test_id+r.endpoint+r.intent).toLowerCase().includes(q)); }
  rows.sort((a,b) => { const k=testState.sortKey,d=testState.sortDir;
    return (a[k]>b[k]?1:a[k]<b[k]?-1:0)*d; });
  document.getElementById('test-count').textContent = rows.length + ' of ' + R.results.length;
  const body = document.getElementById('tests-body');
  body.innerHTML = rows.map(r => {
    const flagged = (byId[r.test_id]||{}).finding;
    return `<tr class="rowmain" data-id="${r.test_id}">
      <td class="mono">${r.test_id}</td>
      <td><span class="tag" style="border-color:${GREY};color:${GREY}">${r.category}</span></td>
      <td class="mono">${r.endpoint}</td>
      <td>${escapeHtml(r.intent)}</td>
      <td class="mono">${r.status_code}</td>
      <td>${r.status_as_expected ? '✓' : '✗'}</td>
      <td class="mono">${r.latency_ms.toFixed(0)}</td>
      <td>${flagged ? `<span class="pill" style="background:${PCOLOR[flagged.priority]}">${flagged.priority}</span>` : '—'}</td>
    </tr>`;
  }).join('');
  body.querySelectorAll('tr.rowmain').forEach(tr => tr.addEventListener('click', () => {
    const id = tr.dataset.id;
    const next = tr.nextElementSibling;
    if (next && next.classList.contains('detail')) { next.remove(); return; }
    document.querySelectorAll('#tests-body tr.detail').forEach(d=>d.remove());
    tr.insertAdjacentHTML('afterend', detailRowHTML(id));
  }));
}
renderTests();

// ================================================================ DEFECT REGISTER TAB
(() => {
  const grid = document.getElementById('defect-grid');
  const cards = [];
  for (const [id, d] of Object.entries(de.detected)) {
    cards.push(`<div class="defect-card detected"><span class="status">DETECTED</span>
      <div class="id">${id}</div><div class="ep">${d.endpoint}</div>
      <div class="desc">${escapeHtml(d.description)}</div>
      <button data-jump="${d.found_by}">View finding: ${d.found_by} →</button></div>`);
  }
  for (const [id, d] of Object.entries(de.missed)) {
    cards.push(`<div class="defect-card missed"><span class="status">MISSED</span>
      <div class="id">${id}</div><div class="ep">${d.endpoint}</div>
      <div class="desc">${escapeHtml(d.description)}</div>
      <div class="missnote">Not caught by the current generated suite.</div></div>`);
  }
  grid.innerHTML = cards.join('');
  grid.addEventListener('click', e => {
    const btn = e.target.closest('button[data-jump]'); if (!btn) return;
    document.querySelector('nav.tabs button[data-tab="findings"]').click();
    findState.priorities = new Set(['P1','P2','P3','P4']); findState.labels = new Set(); findState.search = '';
    document.getElementById('find-search').value = '';
    document.querySelectorAll('#chips-priority .chip').forEach(c=>c.classList.add('on'));
    document.querySelectorAll('#chips-label .chip').forEach(c=>c.classList.remove('on'));
    renderFindings(btn.dataset.jump);
  });
})();

// ================================================================ ARCHITECTURE TAB
document.getElementById('method-body').innerHTML = [
  ['M1 Spec Parser', 'Recursive $ref resolution; producer\u2013consumer dependency inference', 'Python 3, JSON/YAML'],
  ['M2 Test Generator', 'Schema-driven synthesis; boundary-value analysis; OWASP-style probes; pluggable LLM backend', 'Python 3'],
  ['M3 Execution Engine', 'Thread-pool parallel execution; JSON-Schema conformance checking', 'requests, concurrent.futures'],
  ['M4 Anomaly Detector', 'Isolation Forest (unsupervised) + Random Forest (supervised), 12 features', 'scikit-learn'],
  ['M5 Risk Engine', 'Weighted multi-factor scoring: class, criticality, anomaly, blast radius', 'Python 3'],
  ['M6 Reporting', 'Interactive client-side dashboard; CI/CD P1 gate', 'HTML / CSS / vanilla JS'],
].map(r => `<tr><td style="font-weight:700;color:${NAVY}">${r[0]}</td><td>${r[1]}</td><td class="mono">${r[2]}</td></tr>`).join('');
"""

if __name__ == "__main__":
    out = os.path.join(ART, "dashboard.html")
    html = build()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"interactive dashboard written: {out} ({os.path.getsize(out)//1024} KB)")
