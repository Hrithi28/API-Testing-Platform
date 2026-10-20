// AI-Powered Intelligent API Testing Platform -- Review 2 deck
// Plain academic style matching the SSN template and the guide's own conference decks:
// white background, navy header/footer bars only, black bullet text, simple tables.
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const ART = "/home/claude/apitest/artifacts/";
const D = "/home/claude/apitest/deck/";

const R = JSON.parse(fs.readFileSync(ART + "run_report.json"));
const E = JSON.parse(fs.readFileSync(ART + "evaluation.json"));

const NAVY = "335295";
const BLACK = "000000";
const GREY = "4D4D4D";

const pptx = new pptxgen();
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";

const FOOTER_IMG = D + "assets/footer_graphic.png";

function footer(s, pageNo) {
  s.addImage({ path: FOOTER_IMG, x: 0, y: 7.08, w: 13.333, h: 0.42 });
  if (pageNo !== null) {
    s.addText(String(pageNo).padStart(2, "0"), {
      x: 12.75, y: 7.1, w: 0.5, h: 0.35, fontSize: 11, color: "FFFFFF",
      align: "center", fontFace: "Calibri", bold: true,
    });
  }
}
function kicker(s, text) {
  s.addText(text.toUpperCase(), {
    x: 0.55, y: 0.28, w: 10, h: 0.35, fontSize: 13, color: NAVY,
    bold: true, charSpacing: 2, fontFace: "Calibri",
  });
}
function title(s, text) {
  s.addText(text, {
    x: 0.55, y: 0.58, w: 12.2, h: 0.65, fontSize: 25, color: BLACK, bold: true, fontFace: "Calibri",
  });
}
function pg(s, n) { footer(s, n); }
function newSlide() {
  const s = pptx.addSlide();
  s.background = { color: "FFFFFF" };
  return s;
}
// Plain bullet list -- black text, big font, no color coding.
function bulletList(s, items, opts = {}) {
  const x = opts.x || 0.65, y = opts.y || 1.5, w = opts.w || 12.0, h = opts.h || 5.2;
  const fontSize = opts.fontSize || 18;
  const textItems = items.map((it, i) => ({
    text: it,
    options: {
      bullet: { code: "2022", indent: 24 },
      breakLine: true,
      paraSpaceAfter: opts.spaceAfter || 16,
      fontSize,
      color: BLACK,
      fontFace: "Calibri",
    },
  }));
  s.addText(textItems, { x, y, w, h, valign: "top", lineSpacingMultiple: 1.12 });
}
function plainTable(s, rows, colW, opts = {}) {
  const tableRows = rows.map((r, i) => r.map((c) => ({
    text: c,
    options: {
      bold: i === 0,
      fontSize: opts.fontSize || (i === 0 ? 13 : 12),
      color: i === 0 ? "FFFFFF" : BLACK,
      fill: i === 0 ? { color: NAVY } : { color: "FFFFFF" },
      align: "left", valign: "middle", fontFace: "Calibri",
    },
  })));
  s.addTable(tableRows, {
    x: opts.x || 0.55, y: opts.y || 1.55, w: opts.w || 12.2, h: opts.h || 5.0,
    colW,
    border: { type: "solid", color: "999999", pt: 0.75 },
    autoPage: false,
    rowH: opts.rowH,
  });
}

// ---------------------------------------------------------------------------
// Slide 1 -- Title (SSN template: navy header bar + plain white body + footer)
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  // top navy bar, same proportion as the SSN master (≈21% of slide height)
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 1.58, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("UG PROJECT WORK  ·  PHASE I  ·  REVIEW 2", {
    x: 0.7, y: 0.18, w: 12, h: 0.4, fontSize: 13, color: "DCE6F7", bold: true, charSpacing: 1.5, fontFace: "Calibri",
  });
  s.addText("AI-Powered Intelligent API Testing Platform", {
    x: 0.7, y: 0.52, w: 12, h: 1.0, fontSize: 30, color: "FFFFFF", bold: true, fontFace: "Calibri", valign: "middle",
  });

  s.addText("Working implementation, evaluation and literature positioning", {
    x: 0, y: 2.15, w: 13.333, h: 0.5, fontSize: 16, color: BLACK, italic: true, align: "center", fontFace: "Calibri",
  });
  s.addText("Hrithika S  (3122235002047)", {
    x: 0, y: 3.15, w: 13.333, h: 0.45, fontSize: 17, color: BLACK, bold: true, align: "center", fontFace: "Calibri",
  });
  s.addText("Department of Information Technology", {
    x: 0, y: 3.65, w: 13.333, h: 0.4, fontSize: 14, color: BLACK, align: "center", fontFace: "Calibri",
  });
  s.addText("Sri Sivasubramaniya Nadar College of Engineering, Kalavakkam", {
    x: 0, y: 4.02, w: 13.333, h: 0.4, fontSize: 14, color: BLACK, align: "center", fontFace: "Calibri",
  });
  s.addText("Guide: Dr. Radha N.  /  Dr. Mahabub Hasan Mahalat", {
    x: 0, y: 4.65, w: 13.333, h: 0.4, fontSize: 14, color: BLACK, align: "center", fontFace: "Calibri",
  });
  s.addText("Project Work Phase I — Review 2   |   September 2026", {
    x: 0, y: 5.02, w: 13.333, h: 0.4, fontSize: 13, color: GREY, align: "center", fontFace: "Calibri",
  });
  footer(s, null);
}

// ---------------------------------------------------------------------------
// Slide 2 -- Recap Problem Statement (plain bullets, black, big font)
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Recap");
  title(s, "Problem Statement");
  bulletList(s, [
    "APIs are the primary integration surface of modern software, yet they are still tested by hand — slowly, shallowly, and mostly only for the happy path.",
    "Coverage gap: negative, boundary and security cases are rarely hand-written.",
    "Maintenance gap: hand-written suites break silently when the API contract changes.",
    "Triage gap: most tools emit a raw pass/fail with no sense of what matters most.",
    "Security gap: authentication and injection testing is usually deferred to a separate, later effort.",
    "Our solution: a six-module pipeline that generates all four test categories from the API's own specification, executes them, and uses machine learning to flag and risk-rank genuine defects.",
  ], { fontSize: 19, y: 1.55, spaceAfter: 22 });
  pg(s, 2);
}

// ---------------------------------------------------------------------------
// Slide 3 -- Literature Survey: Existing Tools
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Literature Survey");
  title(s, "Existing Tools Used for API Testing");
  const rows = [
    ["Tool", "What it does", "Where it falls short"],
    ["Postman, SoapUI", "Manual, GUI-driven request authoring and collection running", "No automatic generation; effort grows with every endpoint"],
    ["RESTler", "Infers producer-consumer dependencies from an OpenAPI spec and fuzzes statefully", "Mostly syntactic; little modelling of business-logic intent"],
    ["EvoMaster", "Evolutionary, search-based generation aimed at maximising coverage", "Computationally expensive; weaker on semantic edge cases"],
    ["Schemathesis", "Property-based testing that checks responses against the declared schema", "No learning component; cannot rank findings by risk"],
    ["Dredd", "Validates API responses against the specification, similar to Schemathesis", "Same limitation — a schema check, not a risk assessment"],
  ];
  plainTable(s, rows, [2.3, 5.4, 4.5], { y: 1.75, h: 4.6, fontSize: 13.5, rowH: [0.6, 0.78, 0.78, 0.78, 0.78, 0.78] });
  pg(s, 3);
}

// ---------------------------------------------------------------------------
// Slide 4 -- Literature Survey: Existing Research Papers
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Literature Survey");
  title(s, "Existing Research Papers: Technique and Limitation");
  const rows = [
    ["Paper", "Technique", "Limitation"],
    ["SATORI (Alonso et al., 2025)", "LLM reads response-field text in an OpenAPI spec to infer semantic test oracles, without running the API", "Produces oracles only; does not generate or execute tests itself"],
    ["KAT (Le et al., ICST 2024)", "LLM-built operation-dependency graph and inter-parameter constraint detection", "Improves dependency inference only; no execution-time detection or risk ranking"],
    ["Kyaw et al. (JCSSE 2025)", "Four LLMs prompted to author path/parameter/response test cases from OpenAPI docs", "Generation quality only; no live execution or defect ground truth"],
    ["Garousi, Joy & Taibi (2025)", "Systematic review of 56 commercial AI-powered testing tools", "API testing rarely supported; false positives and opaque decisions reported"],
    ["Faraji & Pombo (2025)", "Systematic review of 76 AI-driven test-automation tools and papers", "Identifies open, field-wide gaps in CI/CD integration and explainability"],
    ["Wan et al., “Keeper” (ICSE 2022)", "Pseudo-inverse oracle functions for software that consumes ML APIs", "Different problem genre; illustrates the same oracle problem"],
  ];
  plainTable(s, rows, [2.6, 5.1, 4.5], { y: 1.75, h: 4.9, fontSize: 12.5, rowH: [0.55, 0.72, 0.72, 0.72, 0.72, 0.72, 0.72] });
  pg(s, 4);
}

// ---------------------------------------------------------------------------
// Slide 5 -- Gap Analysis and Motivation (plain bullets, no colors)
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Positioning");
  title(s, "Gap Analysis and Motivation");
  bulletList(s, [
    "Generation stops short of a verdict: prompting-based generators and dependency-graph builders improve test authoring, but neither executes against a live system nor ranks what matters.",
    "API-level testing is under-served by commercial tools: a 2025 review of 56 AI testing tools found most target UI or unit testing, not APIs.",
    "Explainability and standardised ground truth are open, field-wide challenges, named by two independent 2025 surveys — not just a limitation of this project.",
    "Dependency inference here is still heuristic: field-name matching, which the KAT paper shows can be outperformed by an LLM-built dependency graph.",
    "Motivation: build the piece this literature consistently leaves out — an end-to-end, honestly evaluated loop from specification to risk-ranked, evidenced findings.",
  ], { fontSize: 18.5, y: 1.55, spaceAfter: 24 });
  pg(s, 5);
}

// ---------------------------------------------------------------------------
// Slide 6 -- Novelty (plain bullets)
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Positioning");
  title(s, "Novelty — What This Adds");
  bulletList(s, [
    "An end-to-end loop, not another point tool: generation, execution, ML-based detection and risk-based prioritisation are unified in one pipeline.",
    "A falsifiable, held-out ground truth: an 8-defect register, authored and kept outside the pipeline, gives a measured 0/8-vs-8/8 result.",
    "Stated self-critique as a design choice: label circularity, benchmark scope and the dependency-inference heuristic are reported explicitly, not left implicit.",
    "A specific, attributable generation choice: the far-above-maximum boundary probe (10x the declared cap) is the one test that caught the performance defect, D4.",
  ], { fontSize: 19, y: 1.6, spaceAfter: 26 });
  pg(s, 6);
}

// ---------------------------------------------------------------------------
// Slide 7 -- System Architecture
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Proposed Work");
  title(s, "System Architecture — All Seven Modules Implemented");
  s.addImage({ path: "/home/claude/apitest/artifacts_real/fig_architecture_bw.png", x: 0.5, y: 1.55, w: 12.3, h: 5.35, sizing: { type: "contain", w: 12.3, h: 5.35 } });
  pg(s, 7);
}

// ---------------------------------------------------------------------------
// Slide 8 -- Algorithms & Techniques table
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Methodology");
  title(s, "Algorithms & Techniques Used");
  const rows = [
    ["Module", "Algorithm / Technique", "Purpose"],
    ["M1  Spec Parser", "Recursive $ref resolution; producer-consumer dependency inference", "Normalised endpoint model + execution ordering"],
    ["M2  Test Generator", "Schema-driven synthesis + boundary-value analysis; optional LLM backend", "Positive, negative, boundary & security cases"],
    ["M3  Execution Engine", "Thread-pool parallel execution; recursive JSON-Schema conformance check", "Structured response evidence per call"],
    ["M4  Anomaly Detector", "Isolation Forest (unsupervised) + Random Forest (supervised), 12 features", "Outlier + known-defect-signature detection"],
    ["M5  Risk Engine", "Weighted multi-criteria scoring", "P1–P4 prioritisation of findings"],
    ["M6  Reporting Dashboard", "Client-side interactive rendering (sort/filter/search)", "Human triage; automated CI gating planned for Review 3"],
  ];
  plainTable(s, rows, [2.6, 6.0, 3.6], { y: 1.55, h: 5.0, fontSize: 13, rowH: [0.5, 0.78, 0.9, 0.78, 0.78, 0.9, 0.9] });
  s.addText("M1's dependency inference uses field-name heuristics; see Limitations for the planned refinement.", {
    x: 0.55, y: 6.68, w: 12.2, h: 0.35, fontSize: 11, italic: true, color: GREY, fontFace: "Calibri",
  });
  pg(s, 8);
}

// ---------------------------------------------------------------------------
// Slide 9 -- Dataset & Evaluation Target
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Data");
  title(s, "Dataset & Evaluation Target");
  bulletList(s, [
    "Input: OpenAPI 3.0.3 specification — 7 endpoints, 5 schemas, bearer-auth scheme.",
    "Parsed into a normalised endpoint model with 2 inferred dependency links.",
    "System under test: a Flask service with 8 documented defects injected as ground truth.",
    "Classes: validation, schema drift, performance, auth, BOLA, injection.",
    "Register is held out — the pipeline never reads it; used only for scoring.",
  ], { x: 0.55, y: 1.5, w: 6.1, h: 3.5, fontSize: 15.5, spaceAfter: 16 });
  const rows = [
    ["ID", "Endpoint", "Class", "Seeded defect"],
    ["D1", "GET /pets/{petId}", "validation", "Non-integer id returns 500 instead of 400"],
    ["D2", "POST /pets", "validation", "Missing required field accepted with 201"],
    ["D3", "GET /orders/{orderId}", "BOLA", "Any user can read any other user's order"],
    ["D4", "GET /pets", "performance", "Latency degrades with large limit (no cap)"],
    ["D5", "POST /pets", "validation", "Oversized name causes unhandled 500"],
    ["D6", "GET /pets/search", "injection", "Injection payload echoed in error trace"],
    ["D7", "DELETE /pets/{petId}", "auth", "Missing auth token accepted"],
    ["D8", "GET /pets/{petId}", "schema", "Required 'status' field omitted for high ids"],
  ];
  plainTable(s, rows, [0.55, 2.0, 1.3, 2.0], { x: 6.85, y: 1.45, w: 5.95, h: 5.2, fontSize: 10 });
  pg(s, 9);
}

// ---------------------------------------------------------------------------
// Slide 10 -- Demo Live Run console
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Demo");
  title(s, "Live Pipeline Run — Console Output");
  s.addText("Command:  python3 src/run_pipeline.py", { x: 0.55, y: 1.3, w: 6, h: 0.35, fontSize: 12, color: GREY, fontFace: "Consolas" });
  s.addImage({ path: ART + "shot_terminal.png", x: 0.6, y: 1.7, w: 8.8, h: 4.9, sizing: { type: "contain", w: 8.8, h: 4.9 } });
  const steps = [
    "M1 — 7 endpoints parsed",
    "M2 — 47 test cases generated",
    "M3 — 47 executed in 3.01 s",
    "M4 — 21 findings detected",
    "M5 — 9 ranked P1 (critical)",
    "M6 — JSON + interactive dashboard",
  ];
  bulletList(s, steps, { x: 9.65, y: 1.8, w: 3.2, h: 4.2, fontSize: 13, spaceAfter: 18 });
  s.addText("End-to-end runtime: 3.88 s", { x: 9.65, y: 6.1, w: 3.2, h: 0.4, fontSize: 12.5, bold: true, color: NAVY, fontFace: "Calibri" });
  pg(s, 10);
}

// ---------------------------------------------------------------------------
// Slide 11 -- Demo Dashboard
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Demo");
  title(s, "Module 6 — Interactive Reporting Dashboard");
  s.addImage({ path: ART + "shot_findings.png", x: 3.75, y: 1.6, w: 9.1, h: 5.4, sizing: { type: "contain", w: 9.1, h: 5.4 } });
  bulletList(s, [
    "Findings sortable, filterable by priority/class, and searchable.",
    "Click a row to expand the exact request & response JSON.",
    "Defect register jumps straight to the finding that caught it.",
    "Fully client-side — opens with no server, no internet.",
    "Top finding: injection payload reflected in a 201 response on POST /pets — risk 0.89, tier P1.",
  ], { x: 0.55, y: 1.75, w: 3.05, h: 5.0, fontSize: 12.5, spaceAfter: 18 });
  pg(s, 11);
}

// ---------------------------------------------------------------------------
// Slide 12 -- Results Headline
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Results");
  title(s, "Headline Result — Against a Conventional Baseline");
  s.addImage({ path: ART + "fig_baseline.png", x: 0.6, y: 1.5, w: 7.6, h: 5.3, sizing: { type: "contain", w: 7.6, h: 5.3 } });
  bulletList(s, [
    "The baseline is the 8 happy-path tests our own generator produced — a fair stand-in for a hand-written suite.",
    "It found none of the 8 defects: every one lives in negative, boundary, or security territory.",
    "The full 47-test suite found all 8.",
  ], { x: 8.45, y: 2.0, w: 4.3, h: 4.0, fontSize: 15, spaceAfter: 20 });
  pg(s, 12);
}

// ---------------------------------------------------------------------------
// Slide 13 -- Defect Trace
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Results");
  title(s, "Every Seeded Defect Traced to the Test That Found It");
  s.addText("8/8 defects detected   •   100% endpoint coverage   •   100% parameter coverage   •   0.0 SD across 5 runs", {
    x: 0.55, y: 1.45, w: 12.2, h: 0.5, fontSize: 15, bold: true, color: NAVY, fontFace: "Calibri", align: "center",
  });
  const rows = [
    ["Defect", "Detected", "Found by", "Category that found it"],
    ["D1", "Yes", "getPet-002", "negative (invalid path type)"],
    ["D2", "Yes", "createPet-002", "negative (omitted required field)"],
    ["D3", "Yes", "getOrder-008", "security (BOLA probe)"],
    ["D4", "Yes", "listPets-007", "boundary (far-above-maximum)"],
    ["D5", "Yes", "createPet-003", "boundary (over-maxlength body)"],
    ["D6", "Yes", "searchPets-007", "security (injection)"],
    ["D7", "Yes", "deletePet-006", "security (auth-bypass)"],
    ["D8", "Yes", "getPet-005", "boundary + schema conformance"],
  ];
  plainTable(s, rows, [1.5, 1.8, 2.9, 6.0], { y: 2.15, h: 4.4, fontSize: 13 });
  pg(s, 13);
}

// ---------------------------------------------------------------------------
// Slide 14 -- Generation Profile & Latency
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Results");
  title(s, "Generation Profile & Latency Observations");
  s.addImage({ path: ART + "fig_categories.png", x: 0.4, y: 1.5, w: 7.9, h: 3.0, sizing: { type: "contain", w: 7.9, h: 3.0 } });
  s.addImage({ path: ART + "fig_latency.png", x: 0.4, y: 4.55, w: 7.9, h: 2.3, sizing: { type: "contain", w: 7.9, h: 2.3 } });
  bulletList(s, [
    "p50 latency: 5.1 ms",
    "p95 latency: 16.7 ms",
    "max latency: 3006 ms (defect D4)",
    "5xx responses: 11 of 47",
    "schema violations: 1 (defect D8)",
  ], { x: 8.55, y: 2.0, w: 4.2, h: 3.5, fontSize: 15.5, spaceAfter: 18 });
  pg(s, 14);
}

// ---------------------------------------------------------------------------
// Slide 15 -- Anomaly Detector Performance
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Results");
  title(s, "Anomaly Detector Performance");
  s.addImage({ path: ART + "fig_model.png", x: 0.5, y: 1.5, w: 12.3, h: 4.0, sizing: { type: "contain", w: 12.3, h: 4.0 } });
  s.addText([
    { text: "Stated limitation:  ", options: { bold: true, color: BLACK } },
    { text: "the supervised labels are derived from contract violations the model also sees as features. These scores measure internal consistency, not generalisation to unseen defect families.", options: { color: BLACK } },
  ], { x: 0.55, y: 5.75, w: 12.2, h: 1.0, fontSize: 13.5, fontFace: "Calibri", valign: "top" });
  pg(s, 15);
}

// ---------------------------------------------------------------------------
// Slide 16 -- Performance Metrics table
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Evaluation");
  title(s, "Performance Metrics — Measured Values");
  const rows = [
    ["Metric", "Definition", "Measured"],
    ["Endpoint coverage", "Spec endpoints exercised by generated tests", "100%  (7/7)"],
    ["Parameter coverage", "Declared parameters exercised at least once", "100%"],
    ["Defect detection rate", "Seeded defects found ÷ total seeded", "100%  (8/8)"],
    ["Baseline detection rate", "Same metric for a happy-path-only suite", "0%  (0/8)"],
    ["Precision / Recall / F1", "Detector, stratified 5-fold cross-validation", "1.00 / 0.90 / 0.947"],
    ["False-positive rate", "Normal responses wrongly flagged", "0.0  (0 of 27)"],
    ["Generation + execution time", "End-to-end wall-clock for the full suite", "3.88 s"],
    ["Run-to-run stability", "SD of defects detected over 5 repeat runs", "0.00"],
  ];
  plainTable(s, rows, [3.6, 5.4, 3.2], { y: 1.55, h: 5.0, fontSize: 13.5 });
  pg(s, 16);
}

const RA = "/home/claude/apitest/artifacts_real/";

// Slide 17 -- Real-service evaluation: setup
{
  const s = newSlide();
  kicker(s, "Real-World Evaluation");
  title(s, "Moving Beyond the Synthetic Benchmark: Two Real Services");
  plainTable(s, [
    ["Target", "Specification", "Operations", "Tests run", "Raw findings"],
    ["httpbin 0.10.4", "Swagger 2.0 (normalised to OpenAPI 3)", "68", "271", "142"],
    ["ChromaDB 1.5.9", "OpenAPI 3.1 (vector database REST API v2)", "34", "664", "220"],
    ["Total", "", "102", "935", "362"],
  ], [2.4, 4.9, 1.6, 1.6, 1.7], { y: 1.5, h: 2.2, fontSize: 14 });
  bulletList(s, [
    "Both are widely used open-source services, hosted locally so runs are repeatable and safe.",
    "The pipeline ran unchanged after one new parser step for Swagger 2.0 and OpenAPI 3.1 quirks.",
    "Every finding was verified: server errors were re-issued three times, and responses were checked against the declared schema.",
  ], { y: 4.0, h: 2.8, fontSize: 16, spaceAfter: 14 });
  pg(s, 17);
}

// Slide 18 -- Real results: triage
{
  const s = newSlide();
  kicker(s, "Real-World Evaluation");
  title(s, "362 Raw Findings Reduce to 33 Actionable Ones");
  s.addImage({ path: RA + "fig_real_triage.png", x: 0.5, y: 1.5, w: 7.4, h: 5.3, sizing: { type: "contain", w: 7.4, h: 5.3 } });
  bulletList(s, [
    "Actionable: 33 (9%) — a server error that reproduces, or a 2xx response that breaks its declared schema.",
    "Documentation gaps: 73 — undeclared status codes, not defects.",
    "Unimplemented (501): 72.  Expected behaviour: 183.  Non-reproducible: 1.",
    "Most generator output is noise unless it is triaged against evidence.",
  ], { x: 8.1, y: 1.8, w: 4.7, h: 4.8, fontSize: 15, spaceAfter: 16 });
  pg(s, 18);
}

// Slide 19 -- Root causes
{
  const s = newSlide();
  kicker(s, "Real-World Evaluation");
  title(s, "The 33 Actionable Findings Are Five Confirmed Root Causes");
  plainTable(s, [
    ["Service", "Operation", "Finding"],
    ["httpbin", "/delay/{n}, all methods", "Non-numeric n raises an unhandled ValueError: HTTP 500 and a stack trace"],
    ["ChromaDB", "GET .../indexing_status", "Returns 500 “not implemented”; other unsupported operations return 501"],
    ["ChromaDB", "GET /healthcheck", "Documented as a string; returns a JSON object"],
    ["ChromaDB", "GET .../databases", "Documented fields configuration_json, database, log_position are absent"],
    ["ChromaDB", "GET .../collections (2 routes)", "embedding_function.type is “unknown”; schema allows only “legacy”"],
  ], [1.9, 3.3, 7.0], { y: 1.55, h: 4.2, fontSize: 14 });
  s.addText("Each was reproduced on the running service. Not yet reported upstream, and not checked against known issues.", {
    x: 0.55, y: 6.0, w: 12.2, h: 0.6, fontSize: 14, color: BLACK, fontFace: "Calibri", valign: "top" });
  pg(s, 19);
}

// Slide 20 -- Semantic oracle
{
  const s = newSlide();
  kicker(s, "Semantic Oracle (SATORI-style)");
  title(s, "Module 3b — Checks What Values Mean, Not Just Their Type");
  plainTable(s, [
    ["Injected fault", "Mutants", "Original checker", "Semantic oracle"],
    ["Non-UUID in a UUID field", "12", "0", "12"],
    ["Empty identifier", "15", "0", "12"],
    ["Limit exceeded by list length", "2", "0", "2"],
    ["Negative number, implied non-negative", "26", "0", "16"],
    ["Negative number, other fields", "92", "0", "47"],
    ["Total", "147", "0 (0%)", "89 (61%)"],
  ], [5.0, 2.0, 2.6, 2.6], { y: 1.5, h: 3.4, fontSize: 14 });
  bulletList(s, [
    "Faults injected one at a time into 27 real ChromaDB responses; 3 false alarms on the 27 clean ones.",
    "Rule-based (declared constraints plus name, format and cross-field heuristics), not an LLM; an LLM version is future work.",
    "On the real runs it found no extra defect: real specifications say little about meaning.",
  ], { y: 5.1, h: 1.9, fontSize: 14.5, spaceAfter: 8 });
  pg(s, 20);
}

// Slide 21 -- Detector retraining
{
  const s = newSlide();
  kicker(s, "Detector Retraining");
  title(s, "Retraining on Verified Labels: An Honest Negative Result");
  plainTable(s, [
    ["Setting", "Result"],
    ["Pooled 5-fold cross-validation (both services)", "F1 0.978 — optimistic, near-duplicate requests leak across folds"],
    ["Train on httpbin, test on ChromaDB", "Learned model F1 0.19 (precision 0.13, recall 0.40)"],
    ["Train on ChromaDB, test on httpbin", "Learned model F1 0 — found none of the 8 defects"],
    ["Deterministic evidence rule", "Precision and recall 1.0 on both, but labels are a function of the same signals"],
  ], [5.2, 7.0], { y: 1.5, h: 3.0, fontSize: 14 });
  bulletList(s, [
    "With 33 positive examples from two services, the learned model adds nothing over a rule.",
    "So the CI gate uses the deterministic rule; the model stays a secondary signal.",
    "Labels were applied by our rubric, not independently by people. A review workbook (362 rows) is ready for hand-checking.",
  ], { y: 4.8, h: 2.1, fontSize: 15, spaceAfter: 10 });
  pg(s, 21);
}

// Slide 22 -- CI/CD
{
  const s = newSlide();
  kicker(s, "CI/CD Integration");
  title(s, "Module 7 — Quality Gate That Fails Only on New Findings");
  bulletList(s, [
    "Flow: start service, run pipeline, keep actionable findings, fingerprint each, compare with an accepted baseline.",
    "Exit code 0 = pass, 1 = new actionable finding, 2 = pipeline error. A JUnit XML report is written for the CI dashboard.",
    "httpbin: first run failed with 4 new findings (one root cause across 4 HTTP methods); after acceptance the run passed.",
    "Removing one accepted fingerprint made the gate fail again, as a regression would.",
    "ChromaDB: 5 distinct findings reported; the non-reproducible 5xx was ignored.",
    "A GitHub Actions workflow is included, but it has not yet run on a hosted runner.",
  ], { y: 1.55, fontSize: 16, spaceAfter: 14 });
  pg(s, 22);
}

// Slide 23 -- APIEval-20
{
  const s = newSlide();
  kicker(s, "APIEval-20 Benchmark");
  title(s, "APIEval-20: Adapter Built, Official Run Pending");
  bulletList(s, [
    "APIEval-20 (KushoAI): 20 hosted reference APIs; score = 0.7 bug detection + 0.2 coverage + 0.1 efficiency.",
    "The benchmark gives only the request schema and a sample payload; the tool returns a list of test payloads.",
    "Built an adapter that turns each scenario into a test suite: omitted fields, wrong types, boundaries, enums, injection, cross-field swaps.",
    "Self-tested on synthetic scenarios (100% local coverage). Not yet run on the real dataset files or scored.",
    "Next: download the dataset, generate suites, run the official harness on our machine, report the score.",
  ], { y: 1.55, fontSize: 16, spaceAfter: 14 });
  pg(s, 23);
}

// ---------------------------------------------------------------------------
// Slide 17 -- Limitations (plain, no colors)
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Discussion");
  title(s, "Honest Limitations of the Current Results");
  bulletList(s, [
    "Two real services — httpbin and ChromaDB. The five defects show the approach works, not how often.",
    "Labels came from our rubric, applied programmatically; independent human review is still needed.",
    "The learned detector did not generalise across services; the CI gate relies on a deterministic rule.",
    "The semantic oracle is rule-based; an LLM-based version and real (not injected) faults are untested.",
    "APIEval-20 not yet scored; CI workflow not yet run on a hosted runner; defects not yet reported upstream.",
  ], { fontSize: 15.5, y: 1.55, spaceAfter: 20 });
  pg(s, 24);
}

// ---------------------------------------------------------------------------
// Slide 18 -- Project Plan / Road to Review 3
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Project Plan");
  title(s, "Status and Road to Review 3");
  const rows = [
    ["Stage", "Status", "Details"],
    ["Review 1", "Done", "Problem framing, literature survey, architecture design"],
    ["Review 2", "Done", "All six modules implemented; end-to-end pipeline running with measured results; literature positioning added"],
    ["Review 3", "In progress", "Done: real-service evaluation, semantic oracle, CI gate, IEEE-style paper draft. Remaining: official APIEval-20 score, human-reviewed labels, LLM oracle and dependency graph, upstream defect reports, paper submission"],
  ];
  plainTable(s, rows, [1.8, 1.6, 8.8], { y: 1.65, h: 4.8, fontSize: 14, rowH: [0.55, 1.2, 1.4, 1.5] });
  pg(s, 25);
}

// ---------------------------------------------------------------------------
// Slide 19 -- References (paragraph style, annotated)
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "References");
  title(s, "References");
  const refs = [
  "[1] Atlidakis, Vaggelis, Patrice Godefroid, and Marina Polishchuk. “RESTler: Stateful REST API fuzzing.” In 2019 IEEE/ACM 41st International Conference on Software Engineering (ICSE), pp. 748-758. IEEE, 2019.",
  "[2] Arcuri, Andrea. “RESTful API automated test case generation with EvoMaster.” ACM Transactions on Software Engineering and Methodology (TOSEM) 28, no. 1 (2019): 1-37.",
  "[3] Liu, Fei Tony, Kai Ming Ting, and Zhi-Hua Zhou. “Isolation forest.” In 2008 Eighth IEEE International Conference on Data Mining, pp. 413-422. IEEE, 2008.",
  "[4] Breiman, Leo. “Random forests.” Machine Learning 45, no. 1 (2001): 5-32.",
  "[5] OWASP Foundation. “OWASP API Security Top 10.” OWASP Project documentation, owasp.org.",
  "[6] OWASP Foundation. “crAPI — Completely Ridiculous API.” OWASP Project documentation, github.com/OWASP/crAPI.",
  "[7] Pedregosa, Fabian, et al. “Scikit-learn: Machine learning in Python.” Journal of Machine Learning Research 12 (2011): 2825-2830.",
  "[8] Schemathesis Documentation. “Property-based testing for OpenAPI and GraphQL APIs.” schemathesis.readthedocs.io.",
  "[9] OpenAPI Initiative. “OpenAPI Specification v3.0.3.” spec.openapis.org."
];
  const refs2 = [
  "[10] Alonso, Juan C., Alberto Martin-Lopez, Sergio Segura, Gabriele Bavota, and Antonio Ruiz-Cortés. “SATORI: Static test oracle generation for REST APIs.” In 2025 40th IEEE/ACM International Conference on Automated Software Engineering (ASE), pp. 1364-1376. IEEE, 2025.",
  "[11] KushoAI. “APIEval-20: An open benchmark for AI agent API test generation.” KushoAI Resources, resources.kusho.ai, 2026.",
  "[12] Nguyen, Quoc Phong, Kar Wai Lim, Dinil Mon Divakaran, Kian Hsiang Low, and Mun Choon Chan. “GEE: A gradient-based explainable variational autoencoder for network anomaly detection.” In 2019 IEEE Conference on Communications and Network Security (CNS), pp. 91-99. IEEE, 2019.",
  "[13] Faraji, Aazaade, and Nuno Pombo. “AI-driven software test automation: An AI4SE-oriented survey of techniques, tools, and challenges.” IEEE Access (2025).",
  "[14] Garousi, Vahid, Nithin Joy, and Davide Taibi. “AI-powered software testing tools: Full autonomy remains a distant goal.” IEEE Software 42, no. 4 (2025): 98-111.",
  "[15] Kyaw, P. T. T., A. Luangsodsai, and P. Bhattarakosol. “Open API testing using large language models and prompt engineering.” In 2025 22nd International Joint Conference on Computer Science and Software Engineering (JCSSE), pp. 193-198. IEEE, 2025.",
  "[16] Le, Tri, Thien Tran, Duy Cao, Vy Le, Tien N. Nguyen, and Vu Nguyen. “KAT: Dependency-aware automated API testing with large language models.” In 2024 IEEE Conference on Software Testing, Verification and Validation (ICST), pp. 82-92. IEEE, 2024.",
  "[17] Wan, Chengcheng, Shicheng Liu, Sophie Xie, Yifan Liu, Henry Hoffmann, Michael Maire, and Shan Lu. “Automated testing of software that uses machine learning APIs.” In Proceedings of the 44th International Conference on Software Engineering (ICSE), pp. 212-224. 2022."
];
  const _all = refs.concat(refs2); const L = _all.slice(0,9), Rr = _all.slice(9);
  s.addText(L.join("\n\n"), { x: 0.55, y: 1.4, w: 6.0, h: 5.6, fontSize: 10.5, color: BLACK, fontFace: "Calibri", valign: "top", lineSpacingMultiple: 1.05 });
  s.addText(Rr.join("\n\n"), { x: 6.75, y: 1.4, w: 6.0, h: 5.6, fontSize: 10.5, color: BLACK, fontFace: "Calibri", valign: "top", lineSpacingMultiple: 1.05 });
  pg(s, 26);
}

// ---------------------------------------------------------------------------
// Slide 20 -- Conclusion / Thank you
// ---------------------------------------------------------------------------
{
  const s = newSlide();
  kicker(s, "Summary");
  title(s, "From Design to a Working, Measured System");
  bulletList(s, [
    "Seven modules implemented and validated on a seeded-defect benchmark and on two real services.",
    "8/8 seeded defects detected (baseline 0/8); on real services 362 raw findings reduced to 5 confirmed root causes.",
    "Semantic oracle caught 61% of injected faults the original checker missed; CI gate blocks new findings.",
    "Next: official APIEval-20 score, human-reviewed labels, LLM oracle, and paper submission.",
  ], { fontSize: 18, y: 1.7, spaceAfter: 24 });
  s.addText("Thank You — Questions & Feedback Welcome", {
    x: 0.55, y: 6.0, w: 12.2, h: 0.7, fontSize: 20, bold: true, color: NAVY, align: "center", fontFace: "Calibri",
  });
  pg(s, 27);
}

pptx.writeFile({ fileName: "/mnt/user-data/outputs/AI_API_Testing_Review2_SSN.pptx" }).then(() => {
  console.log("deck written");
});
