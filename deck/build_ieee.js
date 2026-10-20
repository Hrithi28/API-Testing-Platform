// IEEE conference-format paper (two columns, US Letter). All numbers come from the result files.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  BorderStyle, Footer, PageNumber, ImageRun, SectionType,
} = require("docx");

const ART = "/home/claude/apitest/artifacts/";
const RA = "/home/claude/apitest/artifacts_real/";
const R = JSON.parse(fs.readFileSync(ART + "run_report.json"));
const S = JSON.parse(fs.readFileSync(RA + "real_summary.json"));
const H = S.targets.httpbin, C = S.targets.chroma, T = S.total_triage;
const RT = S.retrain.cross_target, OM = S.oracle_mutation;
const pct = (x) => Math.round(x * 100) + "%";
const f2 = (x) => x.toFixed(2);

const FONT = "Times New Roman";
const COLW = 4860; // one column, DXA

// ---- helpers -------------------------------------------------------------------
function runs(text, base = {}) {
  // *italic* markup
  return text.split(/(\*[^*]+\*)/).filter(Boolean).map((t) =>
    t.startsWith("*") ? new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, size: 20, ...base })
                      : new TextRun({ text: t, font: FONT, size: 20, ...base }));
}
const Body = (t) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 240 },
  indent: { firstLine: 200 }, children: runs(t) });
const BodyNI = (t) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 240 }, children: runs(t) });
const H1 = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 80 }, keepNext: true,
  children: [new TextRun({ text: t.toUpperCase(), font: FONT, size: 18, smallCaps: false })] });
const H2 = (t) => new Paragraph({ spacing: { before: 100, after: 60 }, keepNext: true,
  children: [new TextRun({ text: t, font: FONT, size: 20, italics: true })] });
const Item = (t) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 240 },
  indent: { left: 400, hanging: 400 }, tabStops: [{ type: "left", position: 400 }], children: runs(t) });
const Cap = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
  new TextRun({ text: t, font: FONT, size: 16 })] });
const TCap = (n, t) => [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 20 }, keepNext: true,
    children: [new TextRun({ text: "TABLE " + n, font: FONT, size: 16 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, keepNext: true,
    children: [new TextRun({ text: t.toUpperCase(), font: FONT, size: 16 })] }),
];
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const RULE = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
function tcell(text, w, header, last) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    margins: { top: 30, bottom: 30, left: 50, right: 50 },
    borders: { top: header ? RULE : NONE, bottom: header || last ? RULE : { style: BorderStyle.SINGLE, size: 2, color: "BBBBBB" }, left: NONE, right: NONE },
    children: [new Paragraph({ children: [new TextRun({ text, font: FONT, size: 15, bold: !!header })] })],
  });
}
function Tbl(rows, widths) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({ cantSplit: true, tableHeader: i === 0,
      children: r.map((c, j) => tcell(String(c), widths[j], i === 0, i === rows.length - 1)) })),
  });
}
const Gap = () => new Paragraph({ spacing: { after: 80 }, children: [] });
function Img(file, wpx, hpx, alt) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 40 }, keepNext: true, children: [
    new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: wpx, height: hpx },
      altText: { title: alt, description: alt, name: alt } })] });
}
const Ref = (n, t) => new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 50, line: 220 },
  indent: { left: 360, hanging: 360 }, children: [new TextRun({ text: `[${n}]\t${t}`, font: FONT, size: 16 })],
  tabStops: [{ type: "left", position: 360 }] });

// ---- front matter ----------------------------------------------------------------
const front = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [
    new TextRun({ text: "An Evidence-Driven Pipeline for Automated REST API Testing: Evaluation on Real Open-Source Services", font: FONT, size: 44 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [
    new TextRun({ text: "Hrithika S, Mahabub Hasan Mahalat", font: FONT, size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [
    new TextRun({ text: "Department of Information Technology, Sri Sivasubramaniya Nadar College of Engineering, Chennai, India", font: FONT, size: 18, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [
    new TextRun({ text: "[corresponding author e-mail]", font: FONT, size: 18 })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 80, line: 240 }, children: [
    new TextRun({ text: "Abstract—", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ font: FONT, size: 18, bold: true, text:
      `Writing API tests by hand does not scale, and most automated tools stop at generating requests. We describe a pipeline that reads an OpenAPI specification, generates positive, negative, boundary and security tests, executes them, applies schema, constraint and semantic checks to the responses, triages the results, and gates a CI build on new findings. We evaluated it twice. On a small service with eight planted defects it found all eight, where a happy-path baseline found none. On two real open-source services, httpbin 0.10.4 and ChromaDB 1.5.9, it ran ${S.targets.httpbin.tests + S.targets.chroma.tests} tests and raised ${S.total_raw_findings} findings, of which only ${T.actionable} (${pct(T.actionable / S.total_raw_findings)}) were actionable. Those reduce to five root causes: an unhandled exception in httpbin and four mismatches between ChromaDB's specification and its behaviour. The rest were documentation gaps, unimplemented operations or expected behaviour. A specification-driven semantic oracle caught ${pct(OM.total.oracle / OM.total.n)} of injected semantic faults that the original checker missed entirely. A supervised detector retrained on verified labels did not carry over from one service to the other, so the CI gate rests on a deterministic evidence rule instead. We report that negative result because it limits what the learning layer can honestly claim.` })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 }, children: [
    new TextRun({ text: "Index Terms—", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ text: "API testing, OpenAPI, test generation, test oracle, anomaly detection, continuous integration", font: FONT, size: 18, bold: true })] }),
];

// ---- body part 1 (two columns) ------------------------------------------------------
const part1 = [
  H1("I. Introduction"),
  Body("An API is the contract between most parts of a modern system, which makes it costly to get wrong and tedious to test by hand. Suites written in Postman or SoapUI reflect the inputs their author happened to think of, and they age quickly once the contract changes."),
  Body("Automated tools help with generation. RESTler infers producer–consumer dependencies from a specification and fuzzes statefully [1]. EvoMaster searches for inputs that raise code coverage [2]. Schemathesis checks every response against the declared schema [3]. Recent work brings in language models for parts of the problem: SATORI infers test oracles from field descriptions without running the API [4], and KAT builds an operation-dependency graph [5]. Two 2025 surveys agree that CI/CD integration, explainability and shared benchmarks are still open [6], [7]."),
  Body("What we found missing is a measured account of what such a pipeline does on real services. Evaluating on a service you wrote, with defects you planted, says little about how many of a tool's findings a maintainer would act on. This paper reports both: a controlled benchmark, and two real services. Our contributions are:"),
  Item("1)\tA seven-module pipeline from specification to CI gate, with a specification-driven semantic oracle."),
  Item("2)\tA fault-injection benchmark whose defect register is held out from the pipeline."),
  Item("3)\tAn evaluation on httpbin and ChromaDB with an explicit triage taxonomy, and the root causes it confirmed."),
  Item("4)\tA mutation study measuring what the semantic oracle can and cannot detect."),
  Item("5)\tA negative result for the supervised detector, and the design change it led to."),

  H1("II. Related Work"),
  Body("Table I summarises the work closest to ours. The tools in the upper rows generate or check requests but do not rank what they find. The research papers in the lower rows each improve one stage, and the surveys name the gaps this paper addresses. Kyaw et al. prompt four language models to write test cases from OpenAPI documents, but do not execute them [8]. Wan et al. face a related oracle problem when testing software that calls machine-learning APIs [9]."),
  ...TCap("I", "Closest related work"),
  Tbl([
    ["Work", "Technique", "Open gap"],
    ["RESTler [1]", "Stateful fuzzing from dependencies", "Syntactic; no ranking"],
    ["EvoMaster [2]", "Evolutionary test search", "Costly; weak semantics"],
    ["Schemathesis [3]", "Schema conformance checks", "No triage of findings"],
    ["SATORI [4]", "LLM-inferred oracles from spec text", "Oracles only; no tests run"],
    ["KAT [5]", "LLM dependency graph", "No execution-time detection"],
    ["Kyaw et al. [8]", "LLM-written tests from OpenAPI", "Generation only"],
    ["Surveys [6], [7]", "Reviews of 76 and 56 tools", "CI/CD, explainability, benchmarks open"],
  ], [1250, 1950, 1660]),
  Gap(),

  H1("III. System Design"),
  Body("Fig. 1 shows the seven modules. Modules 1 to 6 existed at our second project review; Module 3b and Module 7, and the real-service extensions to Modules 1 and 4, are new in this paper."),
  H2("A. Parsing and test generation"),
  Body("Module 1 resolves $ref pointers and normalises Swagger 2.0 and OpenAPI 3.0/3.1 documents [10] into one endpoint model. Real specifications forced several extensions: nullable unions, anyOf and allOf, body parameters and top-level parameter types. Module 2 writes four kinds of test. Positive tests send schema-conformant values. Negative tests break exactly one constraint at a time, so a failure is easy to attribute. Boundary tests apply standard boundary-value analysis, including a probe at ten times the declared maximum. Security tests inject OWASP-style payloads [11], omit or corrupt credentials, and request objects under a different identity. Path parameters take fixture values so stateful operations reach real objects."),
  H2("B. Execution and oracles"),
  Body("Module 3 runs the tests in parallel and checks each 2xx body against the declared schema, covering type, required fields and enumerations. Module 3b adds what that check ignores. It verifies declared constraints (bounds, lengths, patterns, formats, item counts) and rules inferred from field names, descriptions and cross-field relations: a count must not be negative, an identifier must not be empty, a timestamp must parse, a page may not exceed the requested limit, and a count field must equal the length of its sibling list. This follows the idea behind SATORI [4], but uses deterministic rules instead of a language model."),
];

// ---- figure 1 (single column section) ---------------------------------------------------
const fig1 = [
  Img(RA + "fig_architecture_bw.png", 660, 324, "System architecture"),
  Cap("Fig. 1.  System architecture. Solid boxes are implemented and evaluated; the dashed arrow is designed but not yet automated."),
];

// ---- body part 2 -------------------------------------------------------------------------
const part2 = [
  H2("C. Detection, prioritisation and triage"),
  Body("Module 4 combines an Isolation Forest [12] with a Random Forest [13], both from scikit-learn [14], over per-response features. Module 5 scores risk as 0.45 w_class + 0.25 w_criticality + 0.20 anomaly + 0.10 w_blast and maps it to tiers P1 to P4. Running on real services showed that raw findings are mostly not actionable, so we added a triage taxonomy (Section IV-C). It also made us treat HTTP 501 as its own class, since a documented but unimplemented operation is not a crash."),
  H2("D. CI/CD quality gate"),
  Body("Module 7 reduces raw findings to actionable ones, fingerprints them, and compares the fingerprints with an accepted baseline. It writes a JUnit report and exits non-zero only when a new actionable finding appears. A GitHub Actions workflow is provided to run it on every pull request."),

  H1("IV. Experimental Setup"),
  H2("A. Seeded benchmark"),
  Body("We wrote a Flask service with seven endpoints, described by an OpenAPI 3.0.3 specification, and planted eight defects: three validation faults, a broken object-level authorisation, an unbounded-work performance fault, an injection reflection, a missing-authentication fault and a schema violation. They are recorded in a register the pipeline never reads; a scoring script uses it afterwards."),
  H2("B. Real services"),
  Body(`We chose two widely used open-source services that run locally. httpbin 0.10.4 [15] publishes Swagger 2.0 and has ${H.operations} operations in our run, after excluding endpoints that block by design (delay, drip, stream, range). ChromaDB 1.5.9 [16] is a vector database with a REST API v2 specified in OpenAPI 3.1; we tested ${C.operations} operations and excluded only the destructive reset endpoint. Both ran in their default configuration, with authentication off, from a clean state, using eight parallel workers. For ChromaDB we created one populated collection as a fixture, and sent DELETE requests to non-existent identifiers so the fixture survived.`),
  H2("C. Verification protocol"),
  Body("The original detector was trained on weak labels built from the same signals it receives as features, so its scores could only show internal consistency. We therefore labelled every one of the 935 responses by a written rule set that rests on outside evidence:"),
  Item("R1\tA 5xx other than 501 that recurs three times when the request is re-issued alone. This is a robustness defect."),
  Item("R1x\tA 5xx that does not recur sequentially. It is excluded, as it depends on concurrency."),
  Item("R2\tA 2xx body that breaks the operation's own declared response schema. This is a contract defect."),
  Item("R3\tA status code the specification does not declare. This is a documentation gap, not counted as a defect."),
  Item("R0\tEverything else: 501 responses, authentication disabled by configuration, echo-by-design behaviour, declared statuses."),
  Body("The rules were applied programmatically; the three heuristic-only oracle hits were reviewed by hand. The labelled workbook is released with the code so that anyone can audit or override a verdict."),
];

// ---- body part 3 -----------------------------------------------------------------------------
const part3 = [
  H1("V. Results"),
  H2("A. Seeded benchmark"),
  Body(`From the seven-endpoint specification the pipeline produced ${R.counts.test_cases} tests (8 positive, 6 negative, 22 boundary, 11 security), covered every endpoint and parameter, and detected all ${R.defect_evaluation.detected_count} planted defects in ${R.timings.total_s} s. A baseline made of just the eight positive tests detected none. Each defect sits behind an input a happy-path suite never sends, so the detection comes from the generated negative, boundary and security cases, not from the learning layer.`),
  H2("B. Real services"),
  Body(`Table II and Fig. 2 show where the findings went. Of ${S.total_raw_findings} raw findings, ${T.actionable} were actionable. Another ${T.doc_gap} were documentation gaps, ${T.unimplemented} were 501 responses, and ${T.by_design} were expected behaviour. One server error did not reproduce sequentially and was excluded. Taken at face value, the platform's findings were therefore about ${pct(T.actionable / S.total_raw_findings)} precise on these services, before triage.`),
  ...TCap("II", "Findings on the real services"),
  Tbl([
    ["Service", "Ops", "Tests", "Raw", "Action.", "Doc gap", "501", "Expect."],
    ["httpbin", H.operations, H.tests, H.raw_findings_with_oracle, H.triage.actionable, H.triage.doc_gap, H.triage.unimplemented, H.triage.by_design],
    ["ChromaDB", C.operations, C.tests, C.raw_findings_with_oracle, C.triage.actionable, C.triage.doc_gap, C.triage.unimplemented, C.triage.by_design],
  ], [880, 440, 560, 560, 640, 640, 480, 660]),
  Gap(),
  Img(RA + "fig_real_triage.png", 320, 168, "Where raw findings went"),
  Cap("Fig. 2.  Raw findings by outcome after verification."),
  Body("The actionable findings reduce to five root causes (Table III). Each was reproduced against the running service. We have not yet reported them upstream, and we did not check whether they are already known."),
  ...TCap("III", "Confirmed root causes"),
  Tbl([
    ["Service", "Operation", "Finding"],
    ["httpbin", "/delay/{n}, all methods", "Non-numeric n raises an unhandled ValueError: HTTP 500 and a stack trace"],
    ["ChromaDB", "GET .../indexing_status", "Returns 500 \"not implemented\"; other unsupported operations return 501"],
    ["ChromaDB", "GET /healthcheck", "Documented as a string; returns a JSON object"],
    ["ChromaDB", "GET .../databases", "Documented fields configuration_json, database and log_position are absent"],
    ["ChromaDB", "GET .../collections (two routes)", "embedding_function.type is \"unknown\"; the schema allows only \"legacy\""],
  ], [900, 1450, 2510]),
  Gap(),
  H2("C. Semantic oracle"),
  Body(`On the real runs the oracle flagged ${C.oracle_flagged_responses} responses and found no additional defect: all three were an empty user_id returned because authentication is off by default. Real specifications say little about what values mean, and httpbin's declares no response schemas at all. To measure sensitivity directly we injected one semantic fault at a time into ${OM.samples} real ChromaDB responses. The original checker detected ${OM.total.baseline} of ${OM.total.n} mutants; the oracle detected ${OM.total.oracle} (${pct(OM.total.oracle / OM.total.n)}), at a cost of 3 false alarms on ${OM.clean_control.n} unmutated responses (Table IV). The timestamp and count-mismatch operators found no applicable field in the sampled responses, so they were not exercised.`),
  ...TCap("IV", "Injected semantic faults detected"),
  Tbl([
    ["Fault injected", "Mutants", "Original", "Oracle"],
    ...Object.entries(OM.operators).map(([k, v]) => [
      { "BAD_UUID/implied": "Malformed UUID", "EMPTY_ID/implied": "Emptied identifier", "LIMIT_EXC/implied": "List exceeds limit",
        "NEG_NUM/implied": "Negative count-like field", "NEG_NUM/other": "Negative other number" }[k] || k,
      v.n, `${v.baseline} (${pct(v.baseline / v.n)})`, `${v.oracle} (${pct(v.oracle / v.n)})`]),
    ["All", OM.total.n, `${OM.total.baseline} (0%)`, `${OM.total.oracle} (${pct(OM.total.oracle / OM.total.n)})`],
  ], [1900, 700, 1100, 1160]),
  Gap(),
  H2("D. Retraining the supervised detector"),
  Body(`We retrained the Random Forest on the verified labels and tested it across services: train on one, test on the other. Table V compares it with the original rule-based flagging and with the original weak-label forest. The verified-label forest reached only ${f2(RT.train_httpbin__test_chroma.C_verified_rf.recall)} recall at ${f2(RT.train_httpbin__test_chroma.C_verified_rf.precision)} precision on ChromaDB, and found nothing on httpbin. A feature set without raw status code, latency or size, chosen after seeing this failure, did no better. Pooled cross-validation gave an F1 of ${f2(S.retrain.pooled_cv.mean_f1)}, but that figure is optimistic because near-duplicate responses fall on both sides of the split, and we do not rely on it.`),
  ...TCap("V", "Cross-service detector results (P / R / F1)"),
  Tbl([
    ["Method", "Train httpbin, test ChromaDB", "Train ChromaDB, test httpbin"],
    ...[["A_rule_flag", "Rule-based flagging"], ["B_weak_label_rf", "Weak-label forest"], ["C_verified_rf", "Verified-label forest"], ["C2_portable_rf", "Portable features"]].map(([k, n]) => [
      n,
      `${f2(RT.train_httpbin__test_chroma[k].precision)} / ${f2(RT.train_httpbin__test_chroma[k].recall)} / ${f2(RT.train_httpbin__test_chroma[k].f1)}`,
      `${f2(RT.train_chroma__test_httpbin[k].precision)} / ${f2(RT.train_chroma__test_httpbin[k].recall)} / ${f2(RT.train_chroma__test_httpbin[k].f1)}`]),
  ], [1400, 1750, 1710]),
  Gap(),
  Body("The labelling rule itself scores perfectly when used as a classifier, which is expected: the labels are a function of signals the rule can see. The honest reading is that, with 33 positive examples from two services, the learned model adds nothing over a deterministic rule. We therefore based the CI gate on the rule, and kept the learned model as a secondary signal."),
  H2("E. CI gate behaviour"),
  Body("We exercised the gate locally on both services. On httpbin, a first run against an empty baseline failed with four distinct new findings (one root cause across four HTTP methods). After the findings were accepted into the baseline, the same run passed. Removing one accepted fingerprint made it fail again, as a regression would. On ChromaDB the gate reported five distinct findings and ignored the non-reproducible server error. We have not yet run the workflow on a hosted CI runner."),

  H1("VI. Discussion and Threats to Validity"),
  Item("•\tThe seeded benchmark is synthetic, and the real-service study covers only two services. The five confirmed defects show the approach works in practice, not how often."),
  Item("•\tLabels come from a rule set that we wrote, applied programmatically. They are independent of the detector's features, but they are not independent of us. The released workbook allows external review."),
  Item("•\tWe cannot measure recall on defects no one has found. Recall against our labels is one by construction."),
  Item("•\tOur generator produces many requests that a service rightly rejects, so raw precision is low. Treating undeclared status codes as documentation gaps, not defects, is a judgement that lowers the defect count."),
  Item("•\tThe semantic oracle is rule-based. A language-model version, closer to SATORI, was not evaluated, and the mutation study used injected faults rather than real ones."),
  Item("•\tOne server error on ChromaDB occurred only under concurrent load (a locked database). We excluded it, but it may be a real concurrency defect."),

  H1("VII. Conclusion and Future Work"),
  Body("A specification is enough to generate tests that find real defects, but most of what a generator reports is noise unless it is triaged against outside evidence. On two real services, 9% of raw findings were actionable and they reduced to five root causes. A specification-driven oracle detects semantic faults the schema check cannot, though real specifications rarely give it much to work with. The learned detector did not generalise, which is why the CI gate uses a deterministic rule."),
  Body("Next, we will evaluate on APIEval-20 [17], whose 20 reference services are hosted by its authors and scored by their harness. We will also compare an LLM-based oracle with the rule-based one, add a language-model dependency graph in the style of KAT [5], collect a larger labelled corpus from more services, and report the confirmed defects to their maintainers."),

  H1("References"),
  Ref(1, "V. Atlidakis, P. Godefroid, and M. Polishchuk, “RESTler: Stateful REST API fuzzing,” in Proc. 41st Int. Conf. Software Engineering (ICSE), Montreal, Canada, 2019, pp. 748–758."),
  Ref(2, "A. Arcuri, “RESTful API automated test case generation with EvoMaster,” ACM Trans. Softw. Eng. Methodol., vol. 28, no. 1, art. 3, 2019."),
  Ref(3, "Schemathesis documentation, “Property-based testing for OpenAPI and GraphQL APIs,” schemathesis.readthedocs.io."),
  Ref(4, "J. C. Alonso, A. Martin-Lopez, S. Segura, G. Bavota, and A. Ruiz-Cortés, “SATORI: Static test oracle generation for REST APIs,” in Proc. 40th IEEE/ACM Int. Conf. Automated Software Engineering (ASE), Seoul, South Korea, 2025, arXiv:2508.16318."),
  Ref(5, "T. Le, T. Tran, D. Cao, V. Le, T. N. Nguyen, and V. Nguyen, “KAT: Dependency-aware automated API testing with large language models,” in Proc. IEEE Int. Conf. Software Testing, Verification and Validation (ICST), Toronto, Canada, 2024, pp. 82–92."),
  Ref(6, "A. Faraji and N. Pombo, “AI-driven software test automation: An AI4SE-oriented survey of techniques, tools, and challenges,” IEEE Access, vol. 13, pp. 183296–183313, 2025."),
  Ref(7, "V. Garousi, N. Joy, and D. Taibi, “AI-powered software testing tools: Full autonomy remains a distant goal,” IEEE Software, 2025."),
  Ref(8, "P. T. T. Kyaw, A. Luangsodsai, and P. Bhattarakosol, “Open API testing using large language models and prompt engineering,” in Proc. 22nd Int. Joint Conf. Computer Science and Software Engineering (JCSSE), Bangkok, Thailand, 2025, pp. 193–198."),
  Ref(9, "C. Wan, S. Liu, S. Xie, Y. Liu, H. Hoffmann, M. Maire, and S. Lu, “Automated testing of software that uses machine learning APIs,” in Proc. 44th Int. Conf. Software Engineering (ICSE), Pittsburgh, PA, USA, 2022, pp. 212–224."),
  Ref(10, "OpenAPI Initiative, “OpenAPI Specification v3.0.3,” spec.openapis.org."),
  Ref(11, "OWASP Foundation, “OWASP API Security Top 10,” owasp.org."),
  Ref(12, "F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation forest,” in Proc. 8th IEEE Int. Conf. Data Mining (ICDM), Pisa, Italy, 2008, pp. 413–422."),
  Ref(13, "L. Breiman, “Random forests,” Mach. Learn., vol. 45, no. 1, pp. 5–32, 2001."),
  Ref(14, "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” J. Mach. Learn. Res., vol. 12, pp. 2825–2830, 2011."),
  Ref(15, "K. Reitz, “httpbin: HTTP request and response service,” version 0.10.4, Python Package Index."),
  Ref(16, "Chroma, “Chroma: the open-source embedding database,” version 1.5.9, github.com/chroma-core/chroma."),
  Ref(17, "KushoAI, “APIEval-20: An open benchmark for AI agent API test generation,” resources.kusho.ai/api-eval-20, 2026."),
];

// ---- assemble -----------------------------------------------------------------------------------
const page = { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } };
const footer = { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 })] })] }) };
const two = { count: 2, space: 360, equalWidth: true };
const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [
    { properties: { page }, footers: footer, children: front },
    { properties: { type: SectionType.CONTINUOUS, page, column: two }, footers: footer, children: part1 },
    { properties: { type: SectionType.CONTINUOUS, page }, footers: footer, children: fig1 },
    { properties: { type: SectionType.CONTINUOUS, page, column: two }, footers: footer, children: [...part2, ...part3] },
  ],
});
Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync("/mnt/user-data/outputs/IEEE_Conference_Paper.docx", b);
  console.log("ieee paper written");
});
