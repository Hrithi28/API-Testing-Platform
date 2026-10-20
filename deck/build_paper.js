// AI-Powered Intelligent API Testing Platform -- Review 2 research paper (literature-integrated, humanized prose)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, ShadingType, Footer, PageNumber, ImageRun,
} = require("docx");

const ART = "/home/claude/apitest/artifacts/";
const R = JSON.parse(fs.readFileSync(ART + "run_report.json"));
const E = JSON.parse(fs.readFileSync(ART + "evaluation.json"));

const NAVY = "335295";

// ---- small helpers ---------------------------------------------------------
function P(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 160, line: 276 },
    children: [new TextRun({ text, size: 22, ...opts })],
  });
}
function Body(text) {
  return new Paragraph({ spacing: { after: 160, line: 276 }, alignment: AlignmentType.JUSTIFIED, children: [new TextRun({ text, size: 22 })] });
}
function H1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 }, children: [new TextRun({ text, bold: true, size: 28, color: NAVY })] });
}
function H2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 }, children: [new TextRun({ text, bold: true, size: 24, color: "1C2B4A" })] });
}
function Caption(text) {
  return new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text, italics: true, size: 20, color: "444444" })] });
}
function Bullet(text) {
  return new Paragraph({ bullet: { level: 0 }, spacing: { after: 120, line: 276 }, alignment: AlignmentType.JUSTIFIED, children: [new TextRun({ text, size: 22 })] });
}
function RefPara(text) {
  // annotated-bibliography style paragraph: hanging indent, justified, slightly smaller
  return new Paragraph({
    spacing: { after: 220, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    indent: { left: 360, hanging: 360 },
    children: [new TextRun({ text, size: 21 })],
  });
}
function cell(text, opts = {}) {
  return new TableCell({
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.header ? { fill: NAVY, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: !!opts.header, color: opts.header ? "FFFFFF" : "000000", size: 19 })],
    })],
  });
}
function table(rows, widths) {
  return new Table({
    width: { size: 9350, type: WidthType.DXA },
    rows: rows.map((r, i) => new TableRow({
      children: r.map((c, j) => cell(c, { header: i === 0, width: widths[j] })),
    })),
  });
}

// ---- document ---------------------------------------------------------------
const doc = new Document({
  sections: [{
    properties: { page: { margin: { top: 1000, bottom: 1000, left: 1100, right: 1100 } } },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" })],
        })],
      }),
    },
    children: [
      // Title block
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 80 },
        children: [new TextRun({ text: "AI-Powered Intelligent API Testing Platform", bold: true, size: 34, color: NAVY })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 40 },
        children: [new TextRun({ text: "Hrithika S (3122235002047)", size: 21 })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 40 },
        children: [new TextRun({ text: "Department of Information Technology, Sri Sivasubramaniya Nadar College of Engineering, Kalavakkam", size: 20, italics: true })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 300 },
        children: [new TextRun({ text: "Guide: Dr. Radha N. / Dr. Mahabub Hasan Mahalat   |   Project Work Phase I — Review 2   |   September 2026", size: 19 })],
      }),

      H1("Abstract"),
      Body("Most APIs today are still checked by hand. An engineer looks at the endpoints, writes a handful of requests in Postman, and moves on once the obvious cases pass. That approach does not scale well, and it rarely goes beyond the happy path. In this project we built a small pipeline that takes an API's own OpenAPI specification and turns it into a test suite automatically, runs that suite against the API, and then uses a basic machine-learning model to separate genuine problems from expected behaviour. The system has six working parts: a parser that reads the specification and works out which endpoints depend on which; a generator that writes positive, negative, boundary and security test cases; an execution engine that runs everything in parallel and checks each response against the declared schema; an anomaly detector that combines an Isolation Forest with a Random Forest over twelve features of each response; a risk engine that sorts findings into four priority tiers; and a dashboard to look at the results. CI/CD integration is left for the next review. To test whether any of this actually works, we built a small Flask service with eight defects planted in it on purpose and kept a written record of what they were, separate from the pipeline. Given a 7-endpoint specification, the platform produced 47 test cases, covered every endpoint, and caught all eight defects in under four seconds. A plain happy-path suite, run as a baseline, caught none of them. The supervised detector scored precision 1, recall 0.90 and F1 0.9474 under five-fold cross-validation, though as Section 8 explains, its training labels come partly from the same signals it uses as features, so that number should be read carefully. This version of the report also places the work against ten points of comparison from recent literature, including two 2025 surveys of AI-driven testing tools, and is honest about where the project's own design still lags behind what that literature shows is possible."),

      H1("1. Introduction"),
      Body("Microservices have made the API the main contract between almost every part of a modern system, which also makes it one of the more consequential things to get wrong. As the number of endpoints grows and release cycles get shorter, writing tests by hand simply does not keep up. Most engineers still do this in Postman or SoapUI, and those suites take time to write, are expensive to maintain when the contract changes, and tend to reflect whatever inputs the author happened to think of rather than what could actually go wrong."),
      Body("There are automated alternatives, but they have their own gaps. Specification-driven fuzzers and search-based generators can improve structural coverage, yet mostly they vary values inside a schema without understanding what an endpoint is actually for, and they report a flat pass or fail with no indication of which failures matter. Machine learning is used a great deal for defect prediction in general, but it is rarely wired directly into an API test loop where the response evidence is already sitting there, unused. Two recent surveys make roughly the same point from different directions. A 2025 review of 76 AI-driven testing tools and papers found persistent gaps across the field in CI/CD integration, explainability and standard benchmarks [13]. Separately, a review of 56 commercial AI-powered testing tools concluded that genuine support for API-level testing is the exception rather than the rule, and that full autonomy in this space is, in their words, \"a distant goal\" [14]."),
      Body("This project tries to close part of that gap by putting generation, execution, detection and prioritisation into one pipeline instead of treating them as separate problems. The Review 1 submission was mostly a design; this paper reports on an implementation that actually runs, plus a proper evaluation of it. Compared with that earlier version, this revision adds an explicit comparison against existing tools and literature, a short gap analysis, a statement of what is actually novel here, and a longer discussion of limitations informed by the new literature. In short, the contributions are: a working six-module pipeline; a reproducible benchmark built around a fault-injection methodology with a defect register kept outside the pipeline; a controlled comparison against a happy-path baseline that shows where the detection capability actually comes from; a fairly blunt discussion of a limitation in the supervised detector; and an account, grounded in the literature, of where this design is and is not novel."),

      H1("2. Literature Survey and Positioning"),
      H2("2.1 Representative Approaches"),
      Body("Table 1 lists the established industry tools this work is implicitly compared against, and Table 2 lists the research papers that shaped the design or are discussed in the gap analysis below. Splitting them this way seemed more honest than lumping a GUI testing tool together with a 2025 arXiv paper under one heading."),
      Caption("Table 1. Existing tools used for API testing in practice."),
      table([
        ["Tool", "What it does", "Where it falls short"],
        ["Postman, SoapUI", "Manual, GUI-driven request authoring and collection running", "No automatic generation; effort grows linearly with the number of endpoints"],
        ["RESTler", "Infers producer-consumer dependencies from an OpenAPI spec and fuzzes statefully", "Mostly syntactic; does not really model business-logic intent"],
        ["EvoMaster", "Evolutionary, search-based test generation aimed at maximising coverage", "Computationally expensive; weaker on semantic edge cases"],
        ["Schemathesis", "Property-based testing that checks responses against the declared OpenAPI schema", "No learning component; cannot rank findings by how serious they are"],
        ["Dredd", "Validates API responses against the specification, similar in spirit to Schemathesis", "Same limitation — a schema check, not a risk assessment"],
      ], [2000, 4000, 3350]),
      Caption("Table 2. Research papers consulted for this project, their technique, and the limitation each leaves open."),
      table([
        ["Paper", "Technique", "Limitation"],
        ["SATORI (Alonso et al., 2025)", "Uses an LLM to read response-field descriptions in an OpenAPI spec and infer semantic test oracles, without running the API", "Only produces oracles; it does not generate or execute test cases on its own"],
        ["KAT (Le et al., ICST 2024)", "Builds an operation-dependency graph with an LLM and detects inter-parameter constraints for REST API testing", "Improves dependency inference and coverage, but has no execution-time anomaly detection or risk ranking"],
        ["Kyaw et al. (JCSSE 2025)", "Prompts four LLMs (GPT, Claude, Gemini, Grok) to write path/parameter/response-checking test cases directly from OpenAPI docs", "Evaluates generation quality only; nothing is executed and there is no ground truth or prioritisation"],
        ["Garousi, Joy & Taibi (IEEE Software, 2025)", "Systematic review of 56 commercial AI-powered testing tools on the market", "Finds that API/integration testing is rarely supported, and that tool users repeatedly report false positives and opaque decisions"],
        ["Faraji & Pombo (IEEE Access, 2025)", "Systematic review of 76 AI-driven test-automation tools and papers across the whole testing lifecycle", "Identifies ongoing, field-wide gaps in CI/CD integration, explainability and standardised benchmarks"],
        ["Wan et al., \"Keeper\" (ICSE 2022)", "Builds pseudo-inverse oracle functions to test software that consumes cognitive ML APIs (image/text/audio)", "A different problem altogether, but it illustrates the same oracle problem this project answers with a held-out defect register instead"],
      ], [2250, 3700, 3400]),
      Body("Industry tools in Table 1 remain largely manual, or close to it. RESTler infers producer-consumer dependencies from a specification and fuzzes statefully; EvoMaster applies evolutionary search instead. Both are good at generating structurally valid requests, but neither reasons much about semantics. Schemathesis and Dredd check responses against a declared schema without learning anything from previous runs. The research papers in Table 2 tend to attack narrower, deeper problems. SATORI infers oracles from an OpenAPI specification's response-field text using an LLM, and does this without ever calling the API [10]. KAT builds an LLM-guided dependency graph instead of relying on field-name matching, and reports a 15.7% improvement in overall status-code coverage (from 59.2% to 74.9%) over a RESTler-style baseline across 12 real RESTful services [16]. None of these, on their own, carries a specification all the way through to a risk-ranked, evidenced finding, which is roughly the gap this project tries to sit in."),

      H2("2.2 Gap Analysis"),
      Bullet("Generation on its own does not produce a verdict. Both the Kyaw et al. prompting study and KAT improve how test cases are authored, but neither one executes those cases against a running system or ranks the results — a person still has to go through the output."),
      Bullet("API-level testing is not well served by commercial tools. The Garousi et al. review of 56 AI-powered testing tools found that most of them target UI or unit testing; proper support for API or integration testing is uncommon."),
      Bullet("Explainability and a lack of standard ground truth come up in both 2025 surveys as problems for the whole field, not just for this project [13], [14]."),
      Bullet("This platform's own dependency inference is still a heuristic. KAT shows that an LLM-built dependency graph does better than the field-name matching this project's Module 1 currently uses."),
      Bullet("CI/CD integration is still unfinished business industry-wide, according to the AI4SE survey, which treats it as a near-term research priority rather than something already solved — which is one reason this project treats it as Review-3 work instead of claiming it now."),

      H2("2.3 Motivation and Positioning"),
      Body("The motivation here follows pretty directly from the gaps above. The literature has strong individual pieces — better generation, better dependency graphs, better oracles — but nothing that takes a specification all the way through generation, execution, detection and risk-based triage in one reproducible run, while being upfront about what the resulting numbers do and do not show. Commercial tools, per the 56-tool review, rarely target APIs specifically, and their own users complain about false positives and decisions they cannot explain. The academic work on generation and dependency inference (Kyaw et al.; KAT) moves one stage of the pipeline forward without closing the loop to an actual pass/fail verdict based on execution. So the aim here was never to beat any one of these approaches at its own narrow task. It was to connect the stages that the literature tends to treat separately, and to check the result against a ground truth that does not depend on a vendor's own claims about their product."),

      H2("2.4 Novelty"),
      Bullet("It is an end-to-end loop rather than a single-purpose tool: specification-driven generation across four categories, parallel execution with schema checking, ML-based anomaly detection, and risk-based prioritisation all sit in one pipeline, where most of the literature surveyed covers one or two of these stages at most."),
      Bullet("There is a genuine, held-out ground truth: eight defects were written into the target API ahead of time and kept outside the pipeline, which is what makes the 0-of-8-versus-8-of-8 result something that can actually be checked, rather than a tool vendor's claim taken on faith."),
      Bullet("The write-up says plainly where the detector's numbers are shaky — the label circularity discussed in Section 8, the synthetic benchmark, and the heuristic dependency inference relative to KAT are all stated outright rather than glossed over, which is more or less what the explainability complaints in both 2025 surveys are asking for."),
      Bullet("One specific generation choice is traceable to a result: the far-above-maximum boundary probe, set at ten times the declared cap, was the only test in the whole suite that caught the one performance defect (D4)."),

      H1("3. Proposed Methodology"),
      Body("At a high level this is a six-stage pipeline. A specification gets parsed into a normalised endpoint model. Test cases are generated across four categories. The resulting suite is ordered by dependency and executed. Responses are collected as structured evidence. An ensemble detector flags anything unusual. Findings are then risk-scored and written to a report. There is also a feedback path, in principle, where confirmed findings can inform later generation cycles, though this has not been exercised much yet given the scale of the current evaluation."),
      Caption("Figure 1. System architecture. All six modules run end to end; CI/CD integration is drawn separately as planned work for Review 3."),

      H1("4. Algorithms and Technologies Used"),
      Caption("Table 3. Algorithms and technologies used in each module."),
      table([
        ["Module", "Algorithm / technique", "Technology"],
        ["M1 Spec Parser", "Recursive $ref resolution; producer-consumer dependency inference by field-name matching", "Python 3, JSON/YAML"],
        ["M2 Test Generator", "Schema-driven synthesis; boundary-value analysis; OWASP-style probes; optional LLM-backed generation", "Python 3"],
        ["M3 Execution Engine", "Thread-pool parallel execution; recursive JSON-Schema conformance checking", "requests, concurrent.futures"],
        ["M4 Anomaly Detector", "Isolation Forest (unsupervised) plus Random Forest (supervised) over 12 features", "scikit-learn 1.8"],
        ["M5 Risk Engine", "Weighted multi-criteria scoring; P1-P4 tiering", "Python 3"],
        ["M6 Reporting", "Interactive client-side dashboard with sort, filter and drill-down", "HTML/CSS, vanilla JS"],
      ], [2600, 4900, 1850]),

      H2("4.1 Test-case generation strategy"),
      Body("For every endpoint the generator writes four kinds of cases. Positive cases send schema-conformant values. Negative cases break exactly one declared constraint at a time — a wrong parameter type, a missing required field, a wrong body field type — so that when something fails, it is usually obvious why. Boundary cases apply standard boundary-value analysis: at the minimum, just below it, at the maximum, just above it, and, more unusually, ten times the declared maximum, plus empty and oversized strings. Security cases inject OWASP-style payloads into every string field, call protected endpoints with missing or malformed tokens, and try re-requesting objects under a different identity to probe for broken object-level authorisation."),
      Body("That far-above-maximum probe is worth a short digression. A defect where the work done scales with an input value is often invisible to a test that only goes one step past the boundary, because the extra work is still small. Going an order of magnitude past the declared cap tends to expose that kind of problem, and in our evaluation it was, in fact, the only thing that caught defect D4."),
      Body("The generator can run on either of two backends. The default is deterministic and schema-driven, which keeps runs reproducible; there is also an LLM backend that writes cases from endpoint metadata, and it falls back to the deterministic one automatically if no API key is set. Everything reported in this paper used the deterministic backend. Module 1's dependency inference, separately, still relies on a simpler field-name-matching heuristic to connect producer and consumer operations — Section 8 says more about why that is a limitation relative to KAT's dependency graph [16]."),

      H2("4.2 Anomaly detection and risk scoring"),
      Body("Each response gets reduced to a twelve-element feature vector: status code and class, raw and log-scaled latency, response size, how many schema violations were found, whether the status code was one of the ones the spec declared, whether the request was a security probe, whether a probe payload showed up reflected in the response, and the content type. An Isolation Forest looks for statistical outliers without any supervision. Alongside it, a Random Forest is trained on weak labels built from observable contract violations — a 5xx response, a schema breach, a status code outside everything the spec declared, or a security probe that actually succeeded. The two signals are then combined into one anomaly score per response."),
      Body("The risk engine turns that detector output into something closer to a priority list. It combines a weight for the defect class (security ranked highest, then regression, schema-drift, and performance), how critical the endpoint is (auth, order and payment paths count for more than read-only ones), the anomaly score itself, and how far the dependency blast radius reaches. The result maps onto four tiers, P1 through P4; once CI/CD integration exists, the idea is for P1 findings to block a build."),
      P("risk = 0.45·w_class + 0.25·w_criticality + 0.20·anomaly_score + 0.10·w_blast_radius", { italics: true }),

      H1("5. Dataset Description"),
      Body("Because this platform works on live specifications and responses rather than a static dataset, evaluation needed a system to test against, with faults deliberately injected into it — a fairly standard fault-injection approach that at least gives an unambiguous ground truth. The target is a small Flask service with 7 endpoints, described by an OpenAPI 3.0.3 specification with five component schemas and a bearer-token security scheme. Eight defects were written into it and documented in a register that sits entirely outside the pipeline; the pipeline itself never reads it, and it only gets consulted afterwards, by the scoring script."),
      Caption("Table 4. Seeded-defect register used as ground truth, held out from the pipeline."),
      table([
        ["ID", "Endpoint", "Class", "Seeded defect"],
        ["D1", "GET /pets/{petId}", "validation", "Non-integer or negative id returns 500 rather than 400"],
        ["D2", "POST /pets", "validation", "Missing required 'name' accepted with 201"],
        ["D3", "GET /orders/{orderId}", "BOLA", "Any authenticated user can read any order"],
        ["D4", "GET /pets", "performance", "Latency degrades with large limit; no pagination cap"],
        ["D5", "POST /pets", "validation", "Oversized name causes unhandled 500"],
        ["D6", "GET /pets/search", "injection", "Injection payload echoed unsanitised in an error trace"],
        ["D7", "DELETE /pets/{petId}", "auth", "Missing authentication token accepted"],
        ["D8", "GET /pets/{petId}", "schema", "Required 'status' field omitted for high ids"],
      ], [1200, 3200, 1950, 3000]),
      Body("These eight were chosen to fail in different ways on purpose — a crash, something being silently accepted that shouldn't be, an authorisation bypass, a path with unbounded work, a reflected payload, and a missing field — so that no single heuristic could catch all of them by accident."),

      H1("6. Implementation"),
      Body("The whole thing comes to roughly 1,400 lines of Python 3 across the six modules, using scikit-learn 1.8 for the detector, requests for execution, and matplotlib for the figures. There is a single entry point, and beyond pointing it at a specification file there is no configuration to do."),
      P("$ python3 demo_api/target_api.py     # start system under test", { font: "Consolas", size: 20 }),
      P("$ python3 src/run_pipeline.py        # parse → generate → execute → detect → rank", { font: "Consolas", size: 20 }),
      P("$ python3 src/evaluate.py            # baseline comparison, repeats, cross-validation", { font: "Consolas", size: 20 }),
      Body(`Running it against the evaluation specification, the parser picked up 7 endpoints and worked out 2 producer-consumer dependency links, which the execution engine then uses to order stateful request sequences. After de-duplication the generator produced 47 distinct cases — 8 positive, 6 negative, 22 boundary, 11 security — and executing all of them took ${R.timings.m3_execute_s.toFixed(3)} seconds across a six-worker thread pool.`),
      Caption("Figure 2. Console output of a complete pipeline run."),
      Body("Module 6 writes out a single self-contained HTML dashboard that needs no server and no external assets, so it is easy to pass around and open offline. The data is embedded directly in the page and rendered on the client side — findings can be sorted, filtered by priority tier or defect class, and searched; clicking a row opens the exact request and response behind it; and the defect register links each seeded defect straight to the finding that caught it."),
      Caption("Figure 3. Interactive findings view, expanded to show the request/response evidence behind the top-ranked finding."),

      H1("7. Results"),
      H2("7.1 Defect detection and baseline comparison"),
      Body(`The platform detected ${R.defect_evaluation.detected_count} of the ${R.defect_evaluation.total_seeded} seeded defects. To work out where that was actually coming from, the same target was also tested with a baseline made up of just the 8 positive cases the generator produces — a reasonable stand-in for a conventional hand-written happy-path suite. That baseline caught none of the eight.`),
      Caption("Figure 4. Defect detection: happy-path baseline versus the full generated suite."),
      Body("The gap between the two is not a close call, and the reason for it is fairly mechanical: every one of the seeded defects is only reachable through an input a happy-path suite simply never sends. Valid requests to the target come back correct every time. So this result is not really evidence that the platform is highly accurate in some absolute sense — it is evidence that the negative, boundary and security generation is what is actually doing the detection work here, not the machine-learning layer. What the detector adds is triage: helping decide which of the resulting signals are worth looking at first."),
      Caption("Table 5. Each seeded defect and the specific generated test that exposed it."),
      table([
        ["Defect", "Detected", "Found by", "Category that found it"],
        ["D1", "Yes", "getPet-002", "negative (invalid path type)"],
        ["D2", "Yes", "createPet-002", "negative (omitted required field)"],
        ["D3", "Yes", "getOrder-008", "security (BOLA probe)"],
        ["D4", "Yes", "listPets-007", "boundary (far-above-maximum)"],
        ["D5", "Yes", "createPet-003", "boundary (over-maxlength body)"],
        ["D6", "Yes", "searchPets-007", "security (injection)"],
        ["D7", "Yes", "deletePet-006", "security (auth-bypass)"],
        ["D8", "Yes", "getPet-005", "boundary + schema conformance"],
      ], [1200, 1400, 2650, 4100]),

      H2("7.2 Execution and prioritisation profile"),
      Body(`Over the 47 executed calls the platform saw ${R.counts.server_errors} server errors, ${R.counts.unexpected_status} responses outside what the spec declared, and ${R.counts.schema_violations} schema violation, which together worked out to ${R.counts.findings} findings. Of those, risk scoring put ${R.counts.priority_tiers.P1} in P1, ${R.counts.priority_tiers.P2} in P2, ${R.counts.priority_tiers.P3} in P3 and ${R.counts.priority_tiers.P4} in P4. The single highest-ranked finding, with a risk score of 0.89, was an injection payload that showed up reflected in a 201 response on POST /pets. Latency stayed fairly tight overall (p50 ${R.latency.p50_ms} ms, p95 ${R.latency.p95_ms} ms), apart from one outlier at around ${Math.round(R.latency.max_ms)} ms that lines up with defect D4, which the detector picked up through its performance rule.`),
      Caption("Figure 5. Generated test cases by category, and findings by risk tier."),

      H2("7.3 Detector performance"),
      Body(`Under stratified five-fold cross-validation over ${E.cross_validation.n_samples} response records (positive rate ${E.cross_validation.positive_rate}), the Random Forest came out to precision ${E.cross_validation.precision}, recall ${E.cross_validation.recall}, F1 ${E.cross_validation.f1}, and a false-positive rate of ${E.cross_validation.false_positive_rate} (confusion matrix: TP ${E.cross_validation.confusion_matrix.tp}, FP ${E.cross_validation.confusion_matrix.fp}, FN ${E.cross_validation.confusion_matrix.fn}, TN ${E.cross_validation.confusion_matrix.tn}). Section 8 goes into more detail on how much weight these numbers can actually bear.`),
      Caption("Figure 6. Cross-validated confusion matrix and feature importances."),
      Body("The feature importances line up with how the labels were defined in the first place: status-expectation mismatch dominates at 0.346, followed by the raw status code (0.129), the security-probe indicator (0.107), and the server-error indicator (0.080). Latency barely registers, which makes sense since only one of the eight defects in this benchmark actually shows up as a timing anomaly."),

      H2("7.4 Reproducibility"),
      Body(`Running the pipeline five separate times caught all 8 defects every time (standard deviation ${E.repeat_summary.detected_sd}), with a mean wall-clock time of ${E.repeat_summary.wall_mean_s.toFixed(2)} seconds (SD ${E.repeat_summary.wall_sd_s.toFixed(2)} s). Generation itself is deterministic under the schema-driven backend, so whatever small variation there is comes only from network timing.`),
      Caption("Table 6. Measured performance metrics."),
      table([
        ["Metric", "Definition", "Measured"],
        ["Endpoint coverage", "Specification endpoints exercised", "100% (7/7)"],
        ["Parameter coverage", "Declared parameters exercised at least once", "100%"],
        ["Defect detection rate", "Seeded defects found ÷ total seeded", "100% (8/8)"],
        ["Baseline detection rate", "Same metric, happy-path suite only", "0% (0/8)"],
        ["Precision / Recall / F1", "Detector, stratified 5-fold CV", "1 / 0.90 / 0.9474"],
        ["False-positive rate", "Normal responses wrongly flagged", "0 (0 of 27)"],
        ["End-to-end runtime", "Parse, generate, execute, detect, rank", `${R.timings.total_s.toFixed(3)} s`],
        ["Run-to-run stability", "SD of defects detected over 5 runs", "0"],
      ], [2600, 4200, 2550]),

      H1("8. Limitations and Threats to Validity"),
      Body("There are five things worth being upfront about here, and the fifth was added in this revision after reading more of the dependency-inference literature."),
      Bullet("Synthetic benchmark. The eight defects were put into a service written specifically for this project. Fault injection is an accepted way to evaluate this kind of system, but catching 100% of defects on a target we built ourselves is not the same as evidence of how this would perform against a production API, where defects do not separate as cleanly and specifications are often out of date."),
      Bullet("Circularity in the supervised labels. The Random Forest is trained on weak labels that come from contract violations the model also sees as input features. So the precision and recall numbers mostly show that the model reproduces a rule the platform already encodes, not that it generalises to defect types it has not seen. The unsupervised Isolation Forest does not have this problem, and the defect-detection rate in Section 7.1 is unaffected by it too, since that figure is scored against the held-out register rather than against the model's own labels."),
      Bullet("Heuristic dependency inference. Module 1 currently links producer and consumer operations by matching field names between schemas. Le et al.'s KAT work (ICST 2024) shows this kind of heuristic can be beaten by an LLM-built dependency graph, which improved status-code coverage by 15.7% (from 59.2% to 74.9%) over a RESTler-style baseline on 12 real services [16]. A similar approach for this platform's Module 1 is listed as future work below."),
      Bullet("Scale. One specification, seven endpoints, forty-seven tests — that exercises the pipeline, but it does not say much about how generation cost, execution time or the sheer volume of findings would behave on a much larger specification. The same point applies to Module 4: a reconstruction-based detector like an autoencoder typically needs hundreds of training records to learn anything meaningful, and the current 47-record corpus is nowhere near that."),
      Bullet("LLM backend unexercised. Every result in this paper comes from the deterministic backend. Whether LLM-authored cases would actually improve semantic coverage over schema-driven generation is still an open question as far as this project is concerned."),
      Body("One more threat is worth naming separately. The happy-path baseline comes from the project's own generator rather than from tests an actual engineer wrote by hand, and real hand-written suites do sometimes include a negative case or two. So the comparison shows that positive-only testing cannot reach these particular defects; it does not establish a precise improvement factor over how a team would normally test. There is also a looser threat around the literature comparison in Section 2 — a couple of the papers discussed there (the 56-tool review, the AI4SE survey) describe the AI-driven-testing landscape broadly rather than API testing specifically, so they are used here mainly to motivate design choices and name open problems, not as a quantitative baseline this platform is actually measured against."),

      H1("9. Conclusion and Future Work"),
      Body(`To sum up: this paper reported a working implementation of a six-module AI-powered API testing platform, evaluated it against a fault-injection benchmark, and — new in this revision — placed it against ten points of comparison from recent literature, including two 2025 surveys of the AI-driven testing landscape. From a 7-endpoint specification the platform generated 47 test cases, reached full endpoint and parameter coverage, and caught all 8 seeded defects in ${R.timings.total_s.toFixed(3)} seconds, where a happy-path baseline caught none. The headline result says the platform's value sits mostly in specification-driven generation across the negative, boundary and security categories, with the learning layer doing triage rather than discovery. The literature review, separately, is where the novelty argument actually sits: in tying generation, execution, detection and triage into one evaluated loop, which none of the individual papers surveyed quite does on its own.`),
      Body("Six things follow from the limitations above and from the literature reviewed in Section 2. First, swap the synthetic target for APIEval-20, an open benchmark from KushoAI with 20 live API scenarios and 3-8 planted bugs each, scored by actually running generated tests against a reference implementation — a more standardised, third-party alternative to the benchmark used here. APIEval-20 only supplies a request schema and one example payload rather than a full OpenAPI document, so using it means extending Module 1 with a lighter parsing path for schema-only input, not just pointing the existing pipeline at it. Second, build a hand-labelled set of confirmed and dismissed findings to retrain the supervised detector without the circularity described in Section 8 — this really has to happen before its precision and recall can be read as generalisation rather than self-consistency. Third, replace Module 1's field-name heuristic with a KAT-style LLM-built dependency graph, since Le et al. show this materially helps on real services. Fourth, finish the CI/CD integration so the P1 gate actually runs inside a live pipeline, which lines up with the AI4SE survey calling CI/CD integration an open, field-wide problem rather than something already solved. Fifth, extend the oracle in Modules 2 and 3 past plain schema conformance with something closer to SATORI's static, LLM-inferred semantic oracle, to catch defects that pass type validation but are still semantically wrong. Sixth, once there is enough data for a reconstruction-based model to be trained without overfitting — plausibly once APIEval-20's larger response corpus is folded in — add an autoencoder- or VAE-based signal to Module 4 alongside the Isolation Forest, following Nguyen et al.'s gradient-based explainable VAE approach. This last one is deliberately left for later, not attempted now, because the 47-record corpus we currently have is too small to support it honestly."),

      H1("References"),
      RefPara("[1] V. Atlidakis, P. Godefroid, and M. Polishchuk, “RESTler: Stateful REST API Fuzzing,” in Proc. 41st Int. Conf. on Software Engineering (ICSE), Montreal, Canada, 2019, pp. 748–758. RESTler reads an OpenAPI specification, works out which operations likely produce values that other operations consume (for example, a POST that returns an id later used by a GET), and uses that inferred dependency graph to generate long, stateful sequences of requests through a custom fuzzing grammar. It was one of the first tools to treat REST API fuzzing as a dependency problem rather than a per-endpoint one, and it found real bugs, including server crashes, in several Microsoft Azure and OSS cloud services."),
      RefPara("[2] A. Arcuri, “RESTful API Automated Test Case Generation with EvoMaster,” ACM Transactions on Software Engineering and Methodology, vol. 28, no. 1, article 3, 2019. EvoMaster applies evolutionary search — essentially a genetic algorithm — to the problem of generating REST API test cases, using code coverage as the fitness signal it tries to maximise. It operates in both black-box and white-box modes and was evaluated against several open-source and industrial RESTful services, generally outperforming random and dependency-graph-based baselines on branch coverage, though at a noticeably higher computational cost."),
      RefPara("[3] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in Proc. 8th IEEE Int. Conf. on Data Mining (ICDM), Pisa, Italy, 2008, pp. 413–422. This is the original Isolation Forest paper. Instead of profiling what normal data looks like, it isolates individual observations through random recursive partitioning and treats points that are isolated in fewer splits as more likely to be anomalies. It needs no labelled training data, which is why it is used here as the unsupervised half of Module 4's detector, alongside the supervised Random Forest."),
      RefPara("[4] L. Breiman, “Random Forests,” Machine Learning, vol. 45, no. 1, pp. 5–32, 2001. Breiman's paper introduces the Random Forest algorithm: an ensemble of decision trees, each trained on a bootstrap sample of the data with a randomised subset of features considered at each split, with predictions combined by majority vote or averaging. It remains one of the more reliable off-the-shelf classifiers for tabular data, which is why it was chosen for the supervised side of the anomaly detector in this project."),
      RefPara("[5] OWASP Foundation, “OWASP API Security Top 10,” OWASP Project documentation, owasp.org. A community-maintained list of the ten most common and serious API security risks — broken object-level authorisation, broken authentication, excessive data exposure, injection, and so on — along with guidance on how each one typically manifests. The security test-case category in Module 2 (injection payloads, auth-bypass probes, BOLA checks) is modelled loosely on this list."),
      RefPara("[6] OWASP Foundation, “crAPI — Completely Ridiculous API,” OWASP Project documentation, github.com/OWASP/crAPI. crAPI is a deliberately vulnerable, full-featured REST API built by OWASP as a training and benchmarking target, with real-world-style business logic (a ride-booking and e-commerce app) layered over a set of intentionally planted security flaws. It was consulted as a reference design for how to structure a believable, documented, intentionally-flawed target API, which shaped the approach taken for this project's own seeded-defect target service."),
      RefPara("[7] F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011. The reference paper for scikit-learn, the Python machine-learning library this project uses directly for both the Isolation Forest and Random Forest implementations, as well as for the stratified k-fold cross-validation used to evaluate the detector in Section 7.3."),
      RefPara("[8] Schemathesis Documentation, “Property-based testing for OpenAPI and GraphQL APIs,” schemathesis.readthedocs.io. Schemathesis generates test inputs from an API's OpenAPI or GraphQL schema using property-based testing (built on Hypothesis) and checks that responses conform to what the schema promises. It is referenced here as one of the more mature existing schema-conformance tools, and its core idea — checking every response against the declared schema, not just the ones a test explicitly asserts on — is close in spirit to what Module 3's conformance checker does in this project."),
      RefPara("[9] OpenAPI Initiative, “OpenAPI Specification v3.0.3,” spec.openapis.org. The formal specification document that defines the OpenAPI 3.0.3 format this entire project is built around — how paths, parameters, request and response schemas, and security schemes are described in a machine-readable way. Module 1's parser implements reference resolution and dependency inference against this specification."),
      RefPara("[10] J. C. Alonso, A. Martin-Lopez, S. Segura, G. Bavota, and A. Ruiz-Cortés, “SATORI: Static Test Oracle Generation for REST APIs,” presented at the 40th IEEE/ACM Int. Conf. on Automated Software Engineering (ASE), Seoul, South Korea, Nov. 2025; preprint arXiv:2508.16318. SATORI is a black-box method that infers test oracles for REST APIs purely from the OpenAPI specification, without ever executing the API, by using an LLM to read response-field names and descriptions and work out what a “correct” value should plausibly look like. Evaluated on 17 operations across 12 industrial APIs, it reached an F1 of 74.3% on its own (versus 69.3% for a dynamic baseline, AGORA+), found 90% of the ground-truth oracles when combined with that dynamic approach, and surfaced 18 real bugs in production APIs that led maintainers to update their documentation."),
      RefPara("[11] KushoAI, “APIEval-20: An Open Benchmark for AI Agent API Test Generation,” KushoAI Resources, resources.kusho.ai, 2026. APIEval-20 is an open, third-party benchmark of 20 live API scenarios, each with between 3 and 8 deliberately planted bugs, designed to score AI agents on whether they can find real bugs in an API given only a request schema and a single example payload — deliberately less information than a full OpenAPI document provides. It is referenced here as a natural next evaluation target, mentioned in Section 9 as future work, precisely because it offers a standardised, third-party alternative to the self-authored benchmark used in this paper."),
      RefPara("[12] Q. P. Nguyen, K. W. Lim, D. M. Divakaran, K. H. Low, and M. C. Chan, “GEE: A Gradient-based Explainable Variational Autoencoder for Network Anomaly Detection,” in Proc. IEEE Conf. on Communications and Network Security (CNS), Washington, DC, 2019, pp. 91–99. This paper proposes GEE, a variational autoencoder for network anomaly detection that adds a gradient-based technique to explain which input features drove a particular anomaly score, addressing the usual black-box criticism of autoencoder-based detectors. It is referenced in Section 9 as the likely approach for a future reconstruction-based signal in Module 4, once the evaluation corpus is large enough to train one without overfitting."),
      RefPara("[13] A. Faraji and N. Pombo, “AI-Driven Software Test Automation: An AI4SE-Oriented Survey of Techniques, Tools, and Challenges,” IEEE Access, vol. 13, pp. 183296–183313, 2025. A systematic survey covering 76 industrial tools and peer-reviewed papers on AI-driven software test automation, organised around a lifecycle-based taxonomy of testing tasks, AI techniques and data modalities. Among its conclusions, it names explainability, scalability, and solid CI/CD integration as the field's main open research challenges, and notes an acute shortage of standardised, reproducible benchmarks — both points this paper leans on directly in Sections 1 and 2."),
      RefPara("[14] V. Garousi, N. Joy, and D. Taibi, “AI-Powered Software Testing Tools: Full Autonomy Remains a Distant Goal,” IEEE Software, 2025. A systematic review of 56 commercially available AI-powered software testing tools, classifying each by the AI features it offers (test generation, self-healing of UI tests, visual testing, failure analysis) and drawing on real user-reported experiences. The review's central finding, reflected in its title, is that none of the surveyed tools come close to full testing autonomy, and that genuine API/integration-level test support is comparatively rare among them — commercial attention skews heavily toward UI and unit-level testing instead."),
      RefPara("[15] P. T. T. Kyaw, A. Luangsodsai, and P. Bhattarakosol, “Open API Testing Using Large Language Models and Prompt Engineering,” in Proc. 22nd Int. Joint Conf. on Computer Science and Software Engineering (JCSSE), Bangkok, Thailand, 2025, pp. 193–198. This study prompts four large language models — GPT, Claude, Gemini and Grok — with four different prompting strategies to generate REST API test cases directly from an OpenAPI document, covering path, parameter and response-validation checks. It evaluates the resulting test cases for correctness and coverage, but does not execute them against a live system or compare findings to a known set of defects, which is the specific gap this paper's Section 2.2 points to."),
      RefPara("[16] T. Le, T. Tran, D. Cao, V. Le, T. N. Nguyen, and V. Nguyen, “KAT: Dependency-aware Automated API Testing with Large Language Models,” in Proc. IEEE Int. Conf. on Software Testing, Verification and Validation (ICST), Toronto, Canada, 2024, pp. 82–92. KAT uses GPT, guided by carefully designed prompts, to construct an operation-dependency graph directly from an OpenAPI specification and to detect inter-parameter constraints, replacing the field-name-matching heuristics earlier tools such as RESTler rely on. Evaluated against 12 real-world RESTful services, KAT improved overall status-code coverage from 59.2% to 74.9% (a 15.7% improvement) over a RESTler-style baseline, detected more undocumented status codes, and produced fewer false-positive test cases."),
      RefPara("[17] C. Wan, S. Liu, S. Xie, Y. Liu, H. Hoffmann, M. Maire, and S. Lu, “Automated Testing of Software that Uses Machine Learning APIs,” in Proc. 44th Int. Conf. on Software Engineering (ICSE), Pittsburgh, PA, 2022, pp. 212–224. This paper addresses a different but related problem: testing ordinary software that calls cognitive ML APIs (image, text or audio classification services) as a black box. Their tool, Keeper, builds a pseudo-inverse function for each ML API — for instance, reversing an image-classification task by generating an image expected to produce a particular label — and uses that to automatically construct inputs and judge whether the software's use of the API's output is correct. It is cited here as an example of the same underlying oracle problem this project answers differently, with a held-out, hand-written defect register rather than an automatically derived pseudo-inverse function."),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("/mnt/user-data/outputs/AI_API_Testing_ResearchPaper_Review2.docx", buf);
  console.log("paper written");
});
