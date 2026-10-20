const pptxgen = require("pptxgenjs");
const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
const s = pptx.addSlide();

const BW = 2.6, BH = 1.3, GAP = 0.55, X0 = 0.65, Y1 = 1.9, Y2 = 4.7;
const bx = (i) => X0 + i * (BW + GAP);

function box(i, y, title, sub, dashed) {
  s.addText(
    [
      { text: title, options: { bold: true, fontSize: 16, color: "000000", breakLine: true } },
      { text: sub, options: { italic: true, fontSize: 12, color: "000000" } },
    ],
    {
      shape: pptx.ShapeType.roundRect, rectRadius: 0.08,
      x: bx(i), y, w: BW, h: BH, align: "center", valign: "middle",
      fill: { color: "FFFFFF" },
      line: { color: "000000", width: 1.75, dashType: dashed ? "dash" : "solid" },
      fontFace: "Calibri", margin: 6,
    }
  );
}
function line(x, y, w, h, opts = {}) {
  s.addShape(pptx.ShapeType.line, {
    x, y, w, h, flipH: !!opts.flipH, flipV: !!opts.flipV,
    line: { color: "000000", width: 1.75, dashType: opts.dash ? "dash" : "solid",
            endArrowType: opts.arrow ? "triangle" : undefined },
  });
}
function label(text, x, y, w, align = "center") {
  s.addText(text, { x, y, w, h: 0.35, align, fontSize: 13, italic: true,
    color: "000000", fontFace: "Calibri", margin: 0 });
}

s.addText("System Architecture", { x: 0.65, y: 0.35, w: 12, h: 0.7, fontSize: 30,
  bold: true, color: "000000", fontFace: "Calibri", margin: 0 });

// step labels
label("1. Parse  →  2. Generate  →  3. Execute", bx(0), 1.45, 3 * BW + 2 * GAP + BW);
label("4. Detect  →  5. Prioritise  →  6. Report  →  7. Gate the build", bx(0), 6.2, 4 * BW + 3 * GAP);

// row 1
box(0, Y1, "API Specification", "OpenAPI 3.x / Swagger");
box(1, Y1, "M1  Spec Parser & Endpoint Extractor", "$ref resolution, dependency graph");
box(2, Y1, "M2  Test Case Generator", "positive / negative / boundary / security");
box(3, Y1, "M3  Execution Engine & Semantic Oracle", "parallel; schema, constraint and semantic checks");
// row 2
box(0, Y2, "M4  Anomaly Detector", "Isolation Forest + Random Forest");
box(1, Y2, "M5  Risk-based Prioritisation", "P1–P4 tiering");
box(2, Y2, "M6  Reporting Dashboard", "risk-ranked findings, coverage, defect register");
box(3, Y2, "M7  CI/CD Quality Gate", "new-finding gate, JUnit report, exit code");

// row 1 arrows
for (let i = 0; i < 3; i++) line(bx(i) + BW, Y1 + BH / 2, GAP, 0, { arrow: true });
// row 2 arrows
for (let i = 0; i < 2; i++) line(bx(i) + BW, Y2 + BH / 2, GAP, 0, { arrow: true });
line(bx(2) + BW, Y2 + BH / 2, GAP, 0, { arrow: true });

// M3 -> M4 elbow
const m3x = bx(3) + BW / 2, m4x = bx(0) + BW / 2, ymid = 4.05;
line(m3x, Y1 + BH, 0, ymid - (Y1 + BH));
line(m4x, ymid, m3x - m4x, 0);
line(m4x, ymid, 0, Y2 - ymid, { arrow: true });

// feedback loop M6 -> M2 (dashed)
const fx = bx(2) + BW / 2;
line(fx, Y1 + BH, 0, Y2 - (Y1 + BH), { dash: true, arrow: true, flipV: true });
s.addText("feedback loop (not yet automated)", { x: fx + 0.1, y: 3.35, w: 2.8, h: 0.3, fontSize: 12, italic: true,
  color: "000000", fontFace: "Calibri", margin: 0 });

// legend
s.addText("Solid box: implemented and evaluated     Dashed arrow: designed, not yet automated",
  { x: 0.65, y: 6.85, w: 12, h: 0.35, fontSize: 12, color: "000000", fontFace: "Calibri", margin: 0 });

pptx.writeFile({ fileName: "/mnt/user-data/outputs/Architecture_Diagram_Editable.pptx" })
  .then(() => console.log("diagram written"));
