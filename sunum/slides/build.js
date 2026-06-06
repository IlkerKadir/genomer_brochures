const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/ilkerkadirozturk/.claude/plugins/cache/claude-scientific-skills/scientific-skills/497232fbc165/scientific-skills/document-skills/pptx/scripts/html2pptx.js');
const path = require('path');

const S = __dirname;
const hdr = (c, t) => ({ fill: { color: c }, color: "FFFFFF", bold: true, fontSize: 7, align: "center", valign: "middle" });
const cel = (t, opts = {}) => ({ text: t, options: { fontSize: 6.5, valign: "middle", ...opts } });
const cHdr = (t, c) => ({ text: t, options: { ...hdr(c), fontSize: 7 } });

async function build() {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'Genomer';
  pptx.title = 'Genomer Microbiome Testing Line \u2014 Clinical Product Portfolio';
  pptx.subject = 'FEMOBIOME II LINE, ENTEROBIOME KIDS, ANDROBIOME';

  // Slide 1: Title
  console.log('Slide 1: Title');
  await html2pptx(path.join(S, 'slide01-title.html'), pptx);

  // Slide 2: Portfolio
  console.log('Slide 2: Portfolio');
  await html2pptx(path.join(S, 'slide02-portfolio.html'), pptx);

  // Slide 3: FEMOBIOME Overview
  console.log('Slide 3: FEMOBIOME Overview');
  await html2pptx(path.join(S, 'slide03-femobiome.html'), pptx);

  // Slide 4: FEMOBIOME Detection Panel (with table)
  console.log('Slide 4: FEMOBIOME Panel');
  const { slide: s4, placeholders: ph4 } = await html2pptx(path.join(S, 'slide04-femobiome-panel.html'), pptx);
  const panelPh = ph4.find(p => p.id === 'panel-table');
  if (panelPh) {
    const purpleHdr = { fill: { color: "7B4B94" }, color: "FFFFFF", bold: true, fontSize: 6.5, align: "center", valign: "middle" };
    const chk = { text: "\u2713", options: { fontSize: 6.5, align: "center", color: "10B981" } };
    const dash = { text: "\u2014", options: { fontSize: 6.5, align: "center", color: "94A3B8" } };
    const catCell = (t) => ({ text: t, options: { fontSize: 6, bold: true, fill: { color: "F3E8FF" }, color: "5C3470" } });

    s4.addTable([
      [
        { text: "Category", options: purpleHdr },
        { text: "Organism / Marker", options: purpleHdr },
        { text: "FB II", options: purpleHdr },
        { text: "Prima", options: purpleHdr },
        { text: "Secunda", options: purpleHdr }
      ],
      [catCell("Control"), cel("Human DNA / Total bacterial load"), chk, chk, chk],
      [catCell("Normobiota"), cel("Lactobacillus spp., L. crispatus, L. jensenii, L. gasseri, L. iners, Bifidobacterium"), chk, { text: "Partial", options: { fontSize: 6, align: "center", color: "F59E0B" } }, { text: "Partial", options: { fontSize: 6, align: "center", color: "F59E0B" } }],
      [catCell("Aerobes"), cel("Staphylococcus, Streptococcus, S. agalactiae, Enterobacteriaceae, Enterococcus, Haemophilus"), chk, dash, chk],
      [catCell("Anaerobes"), cel("Gardnerella, Fannyhessea, Mobiluncus, Anaerococcus, Peptostreptococcus, Bacteroides/Prevotella, Sneathia, Megasphaera, BVAB1-3"), chk, { text: "Key only", options: { fontSize: 6, align: "center", color: "F59E0B" } }, chk],
      [catCell("Mycoplasmas"), cel("U. urealyticum, U. parvum, M. hominis"), chk, chk, chk],
      [catCell("Yeast"), cel("Candida spp., Candida albicans"), chk, chk, chk],
      [catCell("STIs"), cel("C. trachomatis, M. genitalium, N. gonorrhoeae, T. vaginalis"), chk, dash, chk],
      [catCell("Herpes"), cel("HSV-1, HSV-2, CMV"), chk, dash, chk],
      [catCell("HPV"), cel("HPV 16, 18, 45 + 11 high-risk types"), chk, dash, dash],
    ], {
      ...panelPh,
      border: { pt: 0.5, color: "D4C5DE" },
      colW: [0.9, 4.2, 0.7, 0.7, 0.7],
      rowH: [0.28, 0.24, 0.3, 0.3, 0.35, 0.24, 0.24, 0.28, 0.24, 0.24],
      valign: "middle"
    });
  }

  // Slide 5: FEMOBIOME Clinical
  console.log('Slide 5: FEMOBIOME Clinical');
  await html2pptx(path.join(S, 'slide05-femobiome-clinical.html'), pptx);

  // Slide 6: FEMOBIOME Report (with traffic light table)
  console.log('Slide 6: FEMOBIOME Report');
  const { slide: s6, placeholders: ph6 } = await html2pptx(path.join(S, 'slide06-femobiome-report.html'), pptx);
  const trafficPh = ph6.find(p => p.id === 'traffic-table');
  if (trafficPh) {
    const green = { fill: { color: "D1FAE5" }, color: "065F46", fontSize: 6.5, align: "center", valign: "middle" };
    const yellow = { fill: { color: "FEF3C7" }, color: "92400E", fontSize: 6.5, align: "center", valign: "middle" };
    const red = { fill: { color: "FEE2E2" }, color: "991B1B", fontSize: 6.5, align: "center", valign: "middle" };
    const hdrStyle = { fill: { color: "5C3470" }, color: "FFFFFF", bold: true, fontSize: 6.5, align: "center", valign: "middle" };
    const rowLabel = (t) => ({ text: t, options: { fontSize: 6.5, bold: true, fill: { color: "F3E8FF" }, color: "5C3470", valign: "middle" } });

    s6.addTable([
      [
        { text: "State", options: hdrStyle },
        { text: "Pathogens\nDetected", options: hdrStyle },
        { text: "No Pathogens\nViruses/Myco/Candida\n\u226510\u2074", options: hdrStyle },
        { text: "No Pathogens\nNo Significant\nFindings", options: hdrStyle }
      ],
      [rowLabel("Eubiosis"), { text: "RED", options: red }, { text: "YELLOW", options: yellow }, { text: "GREEN", options: green }],
      [rowLabel("Moderate\nDysbiosis"), { text: "RED", options: red }, { text: "YELLOW", options: yellow }, { text: "YELLOW", options: yellow }],
      [rowLabel("Severe\nDysbiosis"), { text: "RED", options: red }, { text: "RED", options: red }, { text: "RED", options: red }],
    ], {
      ...trafficPh,
      border: { pt: 0.5, color: "D4C5DE" },
      colW: [1.0, 1.1, 1.2, 1.2],
      rowH: [0.45, 0.35, 0.4, 0.4],
      valign: "middle"
    });
  }

  // Slide 7: FEMOBIOME Sample Report (with microbiota table)
  console.log('Slide 7: FEMOBIOME Sample Report');
  const { slide: s7, placeholders: ph7 } = await html2pptx(path.join(S, 'slide06b-femobiome-sample-report.html'), pptx);
  const microPh = ph7.find(p => p.id === 'micro-table');
  if (microPh) {
    const purpHdr = { fill: { color: "7B4B94" }, color: "FFFFFF", bold: true, fontSize: 5.5, align: "center", valign: "middle" };
    const catRow = (t) => [{ text: t, options: { colspan: 3, fontSize: 5.5, bold: true, fill: { color: "F3E8FF" }, color: "5C3470" } }];
    const mRow = (name, lg, pct) => [
      cel(name, { fontSize: 5.5, color: "334155" }),
      { text: lg, options: { fontSize: 5.5, align: "center", color: "334155" } },
      { text: pct, options: { fontSize: 5.5, align: "center", color: "334155" } }
    ];
    const ndC = { text: "\u2014", options: { fontSize: 5.5, align: "center", color: "94A3B8" } };
    const ndRow = (name) => [cel(name, { fontSize: 5.5, color: "334155" }), ndC, ndC];
    s7.addTable([
      [{ text: "Microorganism", options: purpHdr }, { text: "lg GE/ml", options: purpHdr }, { text: "%", options: purpHdr }],
      catRow("NORMOBIOTA"),
      mRow("  Lactobacillus spp.", "6.2", "99.8%"),
      mRow("  Bifidobacterium spp.", "1.7", "<1%"),
      catRow("AEROBES"),
      ndRow("  Staphylococcus spp."),
      ndRow("  Streptococcus spp."),
      ndRow("  Enterobacteriaceae"),
      mRow("  Enterococcus spp.", "2.4", "<1%"),
      ndRow("  Haemophilus spp."),
      catRow("ANAEROBES"),
      ndRow("  Gardnerella vaginalis"),
      ndRow("  Fannyhessea vaginae"),
      ndRow("  Mobiluncus spp."),
      mRow("  Anaerococcus spp.", "2.9", "<1%"),
      mRow("  Peptostreptococcus spp.", "2.6", "<1%"),
      mRow("  Bacteroides / Prevotella", "3.3", "<1%"),
      ndRow("  Sneathia / Leptotrichia / Fusobacterium"),
      mRow("  Megasphaera / Veillonella / Dialister", "2.4", "<1%"),
      ndRow("  BVAB1 / BVAB2 / BVAB3"),
      catRow("MYCOPLASMAS"),
      ndRow("  Ureaplasma urealyticum"),
      mRow("  Ureaplasma parvum", "<4.0", "<1%"),
      ndRow("  Mycoplasma hominis"),
      catRow("YEAST"),
      ndRow("  Candida spp."),
      ndRow("  Candida albicans"),
    ], {
      x: microPh.x, y: microPh.y, w: microPh.w,
      border: { pt: 0.3, color: "E2E8F0" },
      colW: [microPh.w * 0.55, microPh.w * 0.22, microPh.w * 0.23],
      rowH: new Array(27).fill(0.11),
      margin: 0.02,
      valign: "middle"
    });
  }

  // Slide 8: FEMOBIOME Tech
  console.log('Slide 8: FEMOBIOME Tech');
  await html2pptx(path.join(S, 'slide07-femobiome-tech.html'), pptx);

  // Slide 8: ENTEROBIOME Overview
  console.log('Slide 8: ENTEROBIOME Overview');
  await html2pptx(path.join(S, 'slide08-enterobiome.html'), pptx);

  // Slide 9: ENTEROBIOME Science
  console.log('Slide 9: ENTEROBIOME Science');
  await html2pptx(path.join(S, 'slide09-enterobiome-science.html'), pptx);

  // Slide 10: ENTEROBIOME Panel
  console.log('Slide 10: ENTEROBIOME Panel');
  await html2pptx(path.join(S, 'slide10-enterobiome-panel.html'), pptx);

  // Slide 11: ENTEROBIOME Clinical
  console.log('Slide 11: ENTEROBIOME Clinical');
  await html2pptx(path.join(S, 'slide11-enterobiome-clinical.html'), pptx);

  // Slide 13: ENTEROBIOME Report Output
  console.log('Slide 13: ENTEROBIOME Report');
  await html2pptx(path.join(S, 'slide11b-enterobiome-report.html'), pptx);

  // Slide 14: ANDROBIOME Overview
  console.log('Slide 14: ANDROBIOME Overview');
  await html2pptx(path.join(S, 'slide12-androbiome.html'), pptx);

  // Slide 13: ANDROBIOME Panel (with table)
  console.log('Slide 13: ANDROBIOME Panel');
  const { slide: s13, placeholders: ph13 } = await html2pptx(path.join(S, 'slide13-androbiome-panel.html'), pptx);
  const androPh = ph13.find(p => p.id === 'andro-panel-table');
  if (androPh) {
    const blueHdr = { fill: { color: "0EA5E9" }, color: "FFFFFF", bold: true, fontSize: 7, align: "center", valign: "middle" };
    const chk = { text: "\u2713", options: { fontSize: 7, align: "center", color: "10B981" } };
    const dash = { text: "\u2014", options: { fontSize: 7, align: "center", color: "94A3B8" } };
    const catCell = (t) => ({ text: t, options: { fontSize: 6.5, bold: true, fill: { color: "E0F2FE" }, color: "0284C7" } });

    s13.addTable([
      [
        { text: "Category", options: blueHdr },
        { text: "Organism", options: blueHdr },
        { text: "Full", options: blueHdr },
        { text: "Screen", options: blueHdr }
      ],
      [catCell("Normal"), cel("Staphylococcus spp., Streptococcus spp., Corynebacterium spp."), chk, chk],
      [catCell("Transit"), cel("Lactobacillus spp."), chk, chk],
      [catCell("BV-associated"), cel("Gardnerella, Megasphaera/Veillonella/Dialister, Sneathia/Leptotrichia/Fusobacterium, Atopobium cluster"), chk, dash],
      [catCell("Mycoplasmas"), cel("Ureaplasma urealyticum, U. parvum, Mycoplasma hominis"), chk, chk],
      [catCell("Anaerobes"), cel("Bacteroides/Porphyromonas/Prevotella, Anaerococcus, Peptostreptococcus/Parvimonas, Eubacterium"), chk, dash],
      [catCell("Other OM"), cel("Haemophilus spp., Pseudomonas/Ralstonia/Burkholderia, Enterobacteriaceae/Enterococcus"), chk, { text: "Partial", options: { fontSize: 6, align: "center", color: "F59E0B" } }],
      [catCell("Yeast"), cel("Candida spp."), chk, chk],
      [catCell("STIs"), cel("C. trachomatis, M. genitalium, N. gonorrhoeae, T. vaginalis"), chk, chk],
    ], {
      ...androPh,
      border: { pt: 0.5, color: "BAE6FD" },
      colW: [1.1, 4.8, 0.7, 0.7],
      rowH: [0.3, 0.28, 0.25, 0.38, 0.28, 0.35, 0.35, 0.25, 0.28],
      valign: "middle"
    });
  }

  // Slide 14: ANDROBIOME Clinical
  console.log('Slide 14: ANDROBIOME Clinical');
  await html2pptx(path.join(S, 'slide14-androbiome-clinical.html'), pptx);

  // Slide 15: ANDROBIOME Results
  console.log('Slide 15: ANDROBIOME Results');
  await html2pptx(path.join(S, 'slide15-androbiome-results.html'), pptx);

  // Slide 18: ANDROBIOME Sample Report (with result table)
  console.log('Slide 18: ANDROBIOME Sample Report');
  const { slide: s18, placeholders: ph18 } = await html2pptx(path.join(S, 'slide15b-androbiome-sample-report.html'), pptx);
  const resultPh = ph18.find(p => p.id === 'result-table');
  if (resultPh) {
    const blueH = { fill: { color: "0EA5E9" }, color: "FFFFFF", bold: true, fontSize: 5, align: "center", valign: "middle" };
    const grpR = (t) => [{ text: t, options: { colspan: 4, fontSize: 5, bold: true, fill: { color: "F0F9FF" }, color: "0284C7" } }];
    const val = (num, exp) => ({ text: [{ text: `${num} x 10`, options: { fontSize: 5.5 } }, { text: exp, options: { fontSize: 4.5, superscript: true } }], options: { align: "center", valign: "middle" } });
    const nd = { text: "Not detected", options: { fontSize: 5.5, align: "center", color: "94A3B8" } };
    const dash = { text: "\u2013", options: { fontSize: 5.5, align: "center", color: "94A3B8" } };
    const lg = (v) => ({ text: v, options: { fontSize: 5.5, align: "center", valign: "middle" } });
    const st = (label, color, fill) => ({ text: label, options: { fontSize: 5.5, align: "center", valign: "middle", bold: true, color, ...(fill ? { fill: { color: fill } } : {}) } });
    const dRow = (name, result, lgVal, status, opts) => [
      { text: name, options: { fontSize: 5.5, valign: "middle", ...(opts || {}) } },
      typeof result === 'string' ? { text: result, options: { fontSize: 5.5, align: "center", valign: "middle" } } : result,
      lgVal,
      status
    ];
    const detRow = (name, result, lgVal) => [
      { text: name, options: { fontSize: 5.5, valign: "middle", italic: true, bold: true, fill: { color: "FEE2E2" } } },
      { ...result, options: { ...result.options, fill: { color: "FEE2E2" } } },
      { ...lgVal, options: { ...lgVal.options, fill: { color: "FEE2E2" } } },
      { text: "DETECTED", options: { fontSize: 5.5, align: "center", valign: "middle", bold: true, color: "991B1B", fill: { color: "FEE2E2" } } }
    ];
    s18.addTable([
      [{ text: "Microorganism", options: blueH }, { text: "Result (GE)", options: blueH }, { text: "lg (GE)", options: blueH }, { text: "Status", options: blueH }],
      grpR("Control Parameters"),
      dRow("Human DNA", val("4.8", "5"), lg("5.7"), st("Adequate", "065F46", "D1FAE5")),
      dRow("Total Bacterial Mass (TBM)", val("8.5", "6"), lg("6.9"), st("High", "991B1B", "FEE2E2")),
      grpR("Transit Microorganisms"),
      dRow("Lactobacillus spp.", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("Commensals"),
      dRow("Staphylococcus spp.", val("1.2", "4"), lg("4.1"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Streptococcus spp.", val("5.8", "3"), lg("3.8"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Corynebacterium spp.", val("7.3", "3"), lg("3.9"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("Opportunistic Microorganisms"),
      dRow("Gardnerella vaginalis", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Enterobacteriaceae / Enterococcus", val("4.1", "3"), lg("3.6"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("Mycoplasmas"),
      dRow("Mycoplasma hominis", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Ureaplasma urealyticum", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Ureaplasma parvum", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("Candida"),
      dRow("Candida spp.", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("STIs"),
      dRow("Mycoplasma genitalium", nd, dash, st("Not detected", "991B1B", "FEE2E2"), { italic: true }),
      dRow("Trichomonas vaginalis", nd, dash, st("Not detected", "991B1B", "FEE2E2"), { italic: true }),
      detRow("Neisseria gonorrhoeae", val("7.2", "6"), lg("6.9")),
      dRow("Chlamydia trachomatis", nd, dash, st("Not detected", "991B1B", "FEE2E2"), { italic: true }),
    ], {
      x: resultPh.x, y: resultPh.y, w: resultPh.w,
      border: { pt: 0.3, color: "E0F2FE" },
      colW: [resultPh.w * 0.38, resultPh.w * 0.24, resultPh.w * 0.12, resultPh.w * 0.26],
      rowH: [0.15, 0.08,0.14,0.14, 0.08,0.14, 0.08,0.14,0.14,0.14, 0.08,0.14,0.14, 0.08,0.14,0.14,0.14, 0.08,0.14, 0.08,0.14,0.14,0.16,0.14],
      margin: 0.01,
      valign: "middle"
    });
  }

  // Slide 19: Technology
  console.log('Slide 19: Technology');
  await html2pptx(path.join(S, 'slide16-technology.html'), pptx);

  // Slide 17: Tech Specs
  console.log('Slide 17: Tech Specs');
  await html2pptx(path.join(S, 'slide17-tech-specs.html'), pptx);

  // Slide 18: Closing
  console.log('Slide 18: Closing');
  await html2pptx(path.join(S, 'slide18-closing.html'), pptx);

  const outputPath = path.join(S, '..', 'Genomer_Microbiome_Testing_Line.pptx');
  await pptx.writeFile({ fileName: outputPath });
  console.log(`Presentation saved: ${outputPath}`);
}

build().catch(err => { console.error('Build failed:', err.message); process.exit(1); });
