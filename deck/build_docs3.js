// Builds the Review-3 research paper and the Phase I report from the shared content.
// usage: node build_docs3.js [tocPagesJson]
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle,
  Footer, PageNumber, ImageRun, PageBreak, TabStopType, LeaderType, SectionType,
} = require("docx");
const { blocks, ABSTRACT, REFS } = require("./content3");

const FONT = "Times New Roman";
const BLUE = "335295";
const tocPages = fs.existsSync("/tmp/claude-0/toc_pages.json") ? JSON.parse(fs.readFileSync("/tmp/claude-0/toc_pages.json")) : {};

function mk(mode) {
  const report = mode === "report";
  const SZ = report ? 24 : 22;                 // 12 pt report, 11 pt paper
  const LINE = report ? 360 : 276;             // 1.5 vs 1.15
  const W = report ? 8900 : 10100;             // text width in DXA (A4)
  let tN = 0, fN = 0, chN = 0;
  const toc = [];                              // {n, title}
  const tr = (text, o = {}) => new TextRun({ text, font: FONT, size: SZ, ...o });
  const runs = (t, o = {}) => t.split(/(\*[^*]+\*)/).filter(Boolean).map((x) =>
    x.startsWith("*") ? tr(x.slice(1, -1), { italics: true, ...o }) : tr(x, o));
  const P = (t) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: report ? 160 : 120, line: LINE }, children: runs(t) });
  const H1 = (t) => {
    chN += 1; const title = t; toc.push({ n: chN, title });
    if (report) return [
      new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [tr(`CHAPTER ${chN}`, { bold: true, size: 28 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [tr(title.toUpperCase(), { bold: true, size: 28 })] }),
    ];
    return [new Paragraph({ spacing: { before: 200, after: 100 }, keepNext: true, children: [tr(`${chN}. ${title}`, { bold: true, color: BLUE, size: 26 })] })];
  };
  let subN = 0;
  const H2 = (t) => { subN += 1; return new Paragraph({ spacing: { before: 140, after: 80 }, keepNext: true, children: [tr(`${chN}.${subN} ${t}`, { bold: true, size: SZ + (report ? 0 : 0) })] }); };
  const UL = (items) => items.map((t) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 80, line: LINE }, numbering: { reference: "bul", level: 0 }, children: runs(t) }));
  const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const LN = { style: BorderStyle.SINGLE, size: 4, color: "7F7F7F" };
  const cell = (text, w, hdr, keep) => new TableCell({
    width: { size: w, type: WidthType.DXA }, margins: { top: 50, bottom: 50, left: 80, right: 80 },
    shading: hdr ? { type: "clear", fill: BLUE, color: "auto" } : undefined,
    borders: { top: LN, bottom: LN, left: LN, right: LN },
    children: [new Paragraph({ keepNext: !!keep, children: [new TextRun({ text, font: FONT, size: report ? 20 : 18, bold: hdr, color: hdr ? "FFFFFF" : "000000" })] })],
  });
  const TBL = (b) => {
    tN += 1; const sc = W / b.w.reduce((a, c) => a + c, 0); const w = b.w.map((x) => Math.round(x * sc));
    return [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 80 }, keepNext: true, children: [tr(`Table ${tN}. ${b.cap}`, { bold: true, size: SZ - 2 })] }),
      new Table({ width: { size: w.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: w,
        rows: b.rows.map((r, i) => new TableRow({ cantSplit: true, tableHeader: i === 0, children: r.map((c, j) => cell(String(c), w[j], i === 0, i < b.rows.length - 1)) })) }),
      new Paragraph({ spacing: { after: 120 }, children: [] }),
    ];
  };
  const FIG = (b) => {
    fN += 1; const maxW = report ? 585 : 640; const k = Math.min(report ? 1.25 : 1.15, maxW / b.w);
    return [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true, children: [
        new ImageRun({ type: "png", data: fs.readFileSync(b.file), transformation: { width: Math.round(b.w * k), height: Math.round(b.h * k) },
          altText: { title: b.cap, description: b.cap, name: b.cap } })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [tr(`Figure ${fN}. ${b.cap}`, { bold: true, size: SZ - 2 })] }),
    ];
  };
  const CODE = (b) => b.lines.map((l) => new Paragraph({ spacing: { after: 20 }, indent: { left: 360 },
    shading: { type: "clear", fill: "F2F2F2", color: "auto" }, children: [new TextRun({ text: l, font: "Courier New", size: 18 })] }));
  const EQ = (b) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 120 }, children: [tr(b.x, { italics: true, size: SZ - 2 })] });

  function render(bs) {
    const out = [];
    for (const b of bs) {
      if (b.t === "h1") { subN = 0; out.push(...H1(b.x)); }
      else if (b.t === "h2") out.push(H2(b.x));
      else if (b.t === "p") out.push(P(b.x));
      else if (b.t === "ul") out.push(...UL(b.items));
      else if (b.t === "table") out.push(...TBL(b));
      else if (b.t === "fig") out.push(...FIG(b));
      else if (b.t === "code") out.push(...CODE(b));
      else if (b.t === "eq") out.push(EQ(b));
    }
    return out;
  }
  return { report, SZ, LINE, W, tr, P, render, toc, runs, counts: () => ({ tN, fN, chN }) };
}

const REFP = (n, t, SZ) => new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 90, line: 260 }, indent: { left: 480, hanging: 480 },
  tabStops: [{ type: TabStopType.LEFT, position: 480 }], children: [new TextRun({ text: `[${n}]\t${t}`, font: FONT, size: SZ })] });

const numbering = { config: [{ reference: "bul", levels: [{ level: 0, format: "bullet", text: "•", alignment: AlignmentType.LEFT,
  style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] };
const footer = (label) => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: label ? label + "   |   " : "", font: FONT, size: 18 }),
  new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })] })] });
const page = (w) => ({ page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: w.l, right: w.r } } });

// ------------------------------------------------------------------ research paper
function buildPaper() {
  const m = mk("paper");
  const body = m.render(blocks);
  const front = [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [m.tr("AI-Powered Intelligent API Testing Platform", { bold: true, size: 38, color: BLUE })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [m.tr("Hrithika S (3122235002047)", { size: 22 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [m.tr("Department of Information Technology, Sri Sivasubramaniya Nadar College of Engineering, Kalavakkam", { italics: true, size: 20 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [m.tr("Guide: Dr. Mahabub Hasan Mahalat   |   UG Project Work Phase I: Review 3   |   October 2026", { size: 20 })] }),
    new Paragraph({ spacing: { before: 60, after: 80 }, children: [m.tr("Abstract", { bold: true, color: BLUE, size: 26 })] }),
    m.P(ABSTRACT),
  ];
  const refs = [new Paragraph({ spacing: { before: 200, after: 100 }, keepNext: true, children: [m.tr("References", { bold: true, color: BLUE, size: 26 })] }),
    ...REFS.map((t, i) => REFP(i + 1, t, 19))];
  const doc = new Document({ numbering, styles: { default: { document: { run: { font: FONT, size: 22 } } } },
    sections: [{ properties: page({ l: 960, r: 960 }), footers: { default: footer("") }, children: [...front, ...body, ...refs] }] });
  return Packer.toBuffer(doc).then((b) => fs.writeFileSync("/mnt/user-data/outputs/Review3_Research_Paper.docx", b));
}

// ------------------------------------------------------------------ Phase I report
function buildReport() {
  const m = mk("report");
  const centre = (t, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 200 }, children: [m.tr(t, { bold: o.bold, size: o.size || 24, italics: o.italics })] });
  const cover = [
    centre("AI-POWERED INTELLIGENT API TESTING PLATFORM", { bold: true, size: 32, after: 400 }),
    centre("A PROJECT REPORT (PHASE I)", { bold: true, size: 26, after: 300 }),
    centre("Submitted by", { italics: true, after: 120 }),
    centre("HRITHIKA S", { bold: true, size: 28, after: 40 }),
    centre("(3122235002047)", { after: 360 }),
    centre("in partial fulfilment of the requirements for the award of the degree of", { italics: true, after: 120 }),
    centre("BACHELOR OF TECHNOLOGY", { bold: true, size: 28, after: 40 }),
    centre("in", { italics: true, after: 40 }),
    centre("INFORMATION TECHNOLOGY", { bold: true, size: 28, after: 400 }),
    centre("Department of Information Technology", { bold: true, after: 40 }),
    centre("SRI SIVASUBRAMANIYA NADAR COLLEGE OF ENGINEERING", { bold: true, after: 40 }),
    centre("(An Autonomous Institution, Affiliated to Anna University)", { after: 40 }),
    centre("Kalavakkam – 603 110", { after: 300 }),
    centre("October 2026", { bold: true }),
  ];
  const certificate = [
    new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [m.tr("BONAFIDE CERTIFICATE", { bold: true, size: 28 })] }),
    m.P("Certified that this project report titled “AI-Powered Intelligent API Testing Platform” is the bonafide work of HRITHIKA S (3122235002047), who carried out the Phase I project work under my supervision."),
    new Paragraph({ spacing: { before: 700 }, children: [m.tr("______________________________                    ______________________________")] }),
    new Paragraph({ children: [m.tr("Dr. Mahabub Hasan Mahalat                              Head of the Department")] }),
    new Paragraph({ children: [m.tr("Project Guide                                                         Department of Information Technology")] }),
    new Paragraph({ spacing: { before: 500 }, children: [m.tr("Submitted for the Project Viva-Voce examination held on ______________")] }),
    new Paragraph({ spacing: { before: 500 }, children: [m.tr("Internal Examiner                                                   External Examiner")] }),
  ];
  const ack = [
    new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [m.tr("ACKNOWLEDGEMENT", { bold: true, size: 28 })] }),
    m.P("I express my sincere gratitude to my project guide, Dr. Mahabub Hasan Mahalat, for his guidance and encouragement throughout this work, and to the project coordinators and panel members for their reviews and suggestions. I also thank the Head of the Department of Information Technology and the management of SSN College of Engineering for the facilities provided."),
    m.P("[Edit this paragraph to add any further acknowledgements.]"),
  ];
  const abs = [
    new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [m.tr("ABSTRACT", { bold: true, size: 28 })] }),
    m.P(ABSTRACT),
  ];
  // extra report-only material
  const extraIntro = [
    { t: "h2", x: "Problem statement" },
    { t: "p", x: "APIs are the primary integration surface of modern software, yet they are still tested by hand: slowly, shallowly and mostly for the happy path. Negative, boundary and security cases are rarely written, hand-written suites break silently when the contract changes, and most tools emit a raw pass or fail with no sense of what matters most." },
    { t: "h2", x: "Objectives" },
    { t: "ul", items: [
      "Generate positive, negative, boundary and security test cases automatically from an API's OpenAPI specification.",
      "Execute the tests and check each response against the declared schema and the meaning of its values.",
      "Separate genuine defects from expected behaviour and rank them by risk.",
      "Evaluate against a held-out ground truth and on real services, and report what does and does not hold up.",
      "Integrate with a CI pipeline so that a build fails only on new actionable findings.",
    ] },
    { t: "h2", x: "Scope and organisation of the report" },
    { t: "p", x: "The scope of Phase I is a working, evaluated pipeline and the evidence that it finds real defects. Chapter 2 surveys related work. Chapter 3 describes the methodology and Chapter 4 the algorithms. Chapter 5 describes the data sets, Chapter 6 the performance metrics and Chapter 7 the implementation. Chapter 8 presents the experiments and results, Chapter 9 the inferences and threats to validity, and Chapter 10 concludes with future work. Appendices give the drafted defect reports, the demo script and the review protocol." },
  ];
  const [intro, ...rest] = [blocks[0], ...blocks.slice(1)];
  // insert the extra intro material right after the Introduction chapter's own paragraphs (before Literature Survey)
  const iLit = blocks.findIndex((b) => b.t === "h1" && b.x === "Literature Survey");
  const merged = [...blocks.slice(0, iLit), ...extraIntro, ...blocks.slice(iLit)];
  const body = m.render(merged);
  const refs = [new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [m.tr("REFERENCES", { bold: true, size: 28 })] }),
    ...REFS.map((t, i) => REFP(i + 1, t, 22))];
  const read = (f) => fs.readFileSync(f, "utf8").split("\n");
  const app = (t) => new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [m.tr(t, { bold: true, size: 28 })] });
  const mono = (lines) => lines.map((l) => new Paragraph({ spacing: { after: 0 }, shading: { type: "clear", fill: "F2F2F2", color: "auto" }, children: [new TextRun({ text: l || " ", font: "Courier New", size: 16 })] }));
  const appendix = [
    app("APPENDIX A: DRAFTED DEFECT REPORTS"),
    m.P("These reports are drafted from the evaluation and have not been filed. Each project's issue tracker should be searched for duplicates first."),
    ...read("/home/claude/apitest/disclosure/DEFECT_REPORTS.md").slice(3).map((l) => new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: l.replace(/^#+\s*/, ""), font: /^\s{4}/.test(l) ? "Courier New" : FONT, size: /^\s{4}/.test(l) ? 18 : 22, bold: /^##/.test(l) })] })),
    app("APPENDIX B: DEMO SCRIPT"),
    ...mono(read("/home/claude/apitest/scripts/demo.sh")),
    app("APPENDIX C: CI WORKFLOW (GITHUB ACTIONS)"),
    ...mono(read("/home/claude/apitest/.github/workflows/api-quality-gate.yml")),
    app("APPENDIX D: LABEL REVIEW PROTOCOL"),
    m.P("Two reviewers each received a sheet of 79 findings sampled from the 934 real-service tests: all 33 actionable findings plus 23 findings the rubric marked as expected behaviour and 23 it marked as documentation gaps. The rubric label was hidden. Each reviewer answered Y or N to the question “Would a maintainer act on this?”. The script scripts/agreement.py reports Cohen's kappa between the reviewers and against the rubric."),
    m.P("Result: the two reviewers gave identical answers on all 79 rows (kappa 1.00, 22 Y and 57 N each). Each agreed with the rubric on 84% of rows (kappa 0.65). All 13 disagreements with the rubric are on 2xx responses: 12 that the rubric marks actionable because the body breaks the declared schema, and 1 that the reviewers marked actionable and the rubric did not. The sheet showed a truncated body and not the schema, so the 12 could not be judged from it. Future sheets should include the declared schema."),
  ];
  // TOC (page numbers filled from a previous render)
  const names = m.toc.length ? m.toc : [];
  const tocRows = m.toc.map((c) => new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: 8900, leader: LeaderType.DOT }], spacing: { after: 100 },
    children: [m.tr(`Chapter ${c.n}   ${c.title}`), m.tr(`\t${tocPages[c.title] || ""}`)] }));
  const toc = [new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [m.tr("TABLE OF CONTENTS", { bold: true, size: 28 })] }), ...tocRows,
    new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: 8900, leader: LeaderType.DOT }], spacing: { after: 100 }, children: [m.tr("References"), m.tr(`\t${tocPages["References"] || ""}`)] }),
    new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: 8900, leader: LeaderType.DOT }], spacing: { after: 100 }, children: [m.tr("Appendices A to D"), m.tr(`\t${tocPages["APPENDIX A"] || ""}`)] })];
  const doc = new Document({ numbering, styles: { default: { document: { run: { font: FONT, size: 24 } } } },
    sections: [
      { properties: page({ l: 1701, r: 1134 }), children: cover },
      { properties: { ...page({ l: 1701, r: 1134 }), type: SectionType.NEXT_PAGE }, footers: { default: footer("") }, children: [...certificate.slice(0, 1).map((p) => new Paragraph({ children: [] })).slice(0, 0), ...certificate, ...ack, ...abs, ...toc, ...body, ...refs, ...appendix] },
    ] });
  return Packer.toBuffer(doc).then((b) => fs.writeFileSync("/mnt/user-data/outputs/Phase_I_Report.docx", b));
}

Promise.all([buildPaper(), buildReport()]).then(() => console.log("docs written"));
