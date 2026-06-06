const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/ilkerkadirozturk/.claude/plugins/cache/claude-scientific-skills/scientific-skills/497232fbc165/scientific-skills/document-skills/pptx/scripts/html2pptx.js');
const path = require('path');

const S = __dirname;
const cel = (t, opts = {}) => ({ text: t, options: { fontSize: 6.5, valign: "middle", ...opts } });

async function build() {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'Genomer';
  pptx.title = 'Genomer Mikrobiyom Test Hatt\u0131 \u2014 Klinik \u00dcr\u00fcn Portf\u00f6y\u00fc';
  pptx.subject = 'FEMOBIOME II HATTI, ENTEROBIOME KIDS, ANDROBIOME';

  // Slayt 1: Kapak
  console.log('Slayt 1: Kapak');
  await html2pptx(path.join(S, 'slide01-title_TR.html'), pptx);

  // Slayt 2: Portf\u00f6y
  console.log('Slayt 2: Portf\u00f6y');
  await html2pptx(path.join(S, 'slide02-portfolio_TR.html'), pptx);

  // Slayt 3: FEMOBIOME Genel
  console.log('Slayt 3: FEMOBIOME Genel');
  await html2pptx(path.join(S, 'slide03-femobiome_TR.html'), pptx);

  // Slayt 4: FEMOBIOME Tespit Paneli (tablo ile)
  console.log('Slayt 4: FEMOBIOME Panel');
  const { slide: s4, placeholders: ph4 } = await html2pptx(path.join(S, 'slide04-femobiome-panel_TR.html'), pptx);
  const panelPh = ph4.find(p => p.id === 'panel-table');
  if (panelPh) {
    const purpleHdr = { fill: { color: "7B4B94" }, color: "FFFFFF", bold: true, fontSize: 6.5, align: "center", valign: "middle" };
    const chk = { text: "\u2713", options: { fontSize: 6.5, align: "center", color: "10B981" } };
    const dash = { text: "\u2014", options: { fontSize: 6.5, align: "center", color: "94A3B8" } };
    const catCell = (t) => ({ text: t, options: { fontSize: 6, bold: true, fill: { color: "F3E8FF" }, color: "5C3470" } });

    s4.addTable([
      [
        { text: "Kategori", options: purpleHdr },
        { text: "Organizma / Belirte\u00e7", options: purpleHdr },
        { text: "FB II", options: purpleHdr },
        { text: "Prima", options: purpleHdr },
        { text: "Secunda", options: purpleHdr }
      ],
      [catCell("Kontrol"), cel("Human DNA / Toplam bakteri y\u00fck\u00fc"), chk, chk, chk],
      [catCell("Normobiyota"), cel("Lactobacillus spp., L. crispatus, L. jensenii, L. gasseri, L. iners, Bifidobacterium"), chk, { text: "K\u0131smi", options: { fontSize: 6, align: "center", color: "F59E0B" } }, { text: "K\u0131smi", options: { fontSize: 6, align: "center", color: "F59E0B" } }],
      [catCell("Aeroblar"), cel("Staphylococcus, Streptococcus, S. agalactiae, Enterobacteriaceae, Enterococcus, Haemophilus"), chk, dash, chk],
      [catCell("Anaeroblar"), cel("Gardnerella, Fannyhessea, Mobiluncus, Anaerococcus, Peptostreptococcus, Bacteroides/Prevotella, Sneathia, Megasphaera, BVAB1-3"), chk, { text: "Temel", options: { fontSize: 6, align: "center", color: "F59E0B" } }, chk],
      [catCell("Mikoplazmalar"), cel("U. urealyticum, U. parvum, M. hominis"), chk, chk, chk],
      [catCell("Maya"), cel("Candida spp., Candida albicans"), chk, chk, chk],
      [catCell("CYBH"), cel("C. trachomatis, M. genitalium, N. gonorrhoeae, T. vaginalis"), chk, dash, chk],
      [catCell("Herpes"), cel("HSV-1, HSV-2, CMV"), chk, dash, chk],
      [catCell("HPV"), cel("HPV 16, 18, 45 + 11 y\u00fcksek riskli tip"), chk, dash, dash],
    ], {
      ...panelPh,
      border: { pt: 0.5, color: "D4C5DE" },
      colW: [0.9, 4.2, 0.7, 0.7, 0.7],
      rowH: [0.28, 0.24, 0.3, 0.3, 0.35, 0.24, 0.24, 0.28, 0.24, 0.24],
      valign: "middle"
    });
  }

  // Slayt 5: FEMOBIOME Klinik
  console.log('Slayt 5: FEMOBIOME Klinik');
  await html2pptx(path.join(S, 'slide05-femobiome-clinical_TR.html'), pptx);

  // Slayt 6: FEMOBIOME Rapor (trafik \u0131\u015f\u0131\u011f\u0131 tablosu)
  console.log('Slayt 6: FEMOBIOME Rapor');
  const { slide: s6, placeholders: ph6 } = await html2pptx(path.join(S, 'slide06-femobiome-report_TR.html'), pptx);
  const trafficPh = ph6.find(p => p.id === 'traffic-table');
  if (trafficPh) {
    const green = { fill: { color: "D1FAE5" }, color: "065F46", fontSize: 6.5, align: "center", valign: "middle" };
    const yellow = { fill: { color: "FEF3C7" }, color: "92400E", fontSize: 6.5, align: "center", valign: "middle" };
    const red = { fill: { color: "FEE2E2" }, color: "991B1B", fontSize: 6.5, align: "center", valign: "middle" };
    const hdrStyle = { fill: { color: "5C3470" }, color: "FFFFFF", bold: true, fontSize: 6.5, align: "center", valign: "middle" };
    const rowLabel = (t) => ({ text: t, options: { fontSize: 6.5, bold: true, fill: { color: "F3E8FF" }, color: "5C3470", valign: "middle" } });

    s6.addTable([
      [
        { text: "Durum", options: hdrStyle },
        { text: "Patojen\nSaptand\u0131", options: hdrStyle },
        { text: "Patojen Yok\nVir\u00fcs/Miko/Candida\n\u226510\u2074", options: hdrStyle },
        { text: "Patojen Yok\n\u00d6nemli Bulgu\nYok", options: hdrStyle }
      ],
      [rowLabel("\u00d6biyoz"), { text: "KIRMIZI", options: red }, { text: "SARI", options: yellow }, { text: "YE\u015e\u0130L", options: green }],
      [rowLabel("Orta D\u00fczey\nDisbiyoz"), { text: "KIRMIZI", options: red }, { text: "SARI", options: yellow }, { text: "SARI", options: yellow }],
      [rowLabel("A\u011f\u0131r\nDisbiyoz"), { text: "KIRMIZI", options: red }, { text: "KIRMIZI", options: red }, { text: "KIRMIZI", options: red }],
    ], {
      ...trafficPh,
      border: { pt: 0.5, color: "D4C5DE" },
      colW: [1.0, 1.1, 1.2, 1.2],
      rowH: [0.45, 0.35, 0.4, 0.4],
      valign: "middle"
    });
  }

  // Slayt 7: FEMOBIOME \u00d6rnek Rapor (tablo ile)
  console.log('Slayt 7: FEMOBIOME \u00d6rnek Rapor');
  const { slide: s7, placeholders: ph7 } = await html2pptx(path.join(S, 'slide06b-femobiome-sample-report_TR.html'), pptx);
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
      [{ text: "Mikroorganizma", options: purpHdr }, { text: "lg GE/ml", options: purpHdr }, { text: "%", options: purpHdr }],
      catRow("NORMOB\u0130YOTA"),
      mRow("  Lactobacillus spp.", "6,2", "%99,8"),
      mRow("  Bifidobacterium spp.", "1,7", "<%1"),
      catRow("AEROBLAR"),
      ndRow("  Staphylococcus spp."),
      ndRow("  Streptococcus spp."),
      ndRow("  Enterobacteriaceae"),
      mRow("  Enterococcus spp.", "2,4", "<%1"),
      ndRow("  Haemophilus spp."),
      catRow("ANAEROBLAR"),
      ndRow("  Gardnerella vaginalis"),
      ndRow("  Fannyhessea vaginae"),
      ndRow("  Mobiluncus spp."),
      mRow("  Anaerococcus spp.", "2,9", "<%1"),
      mRow("  Peptostreptococcus spp.", "2,6", "<%1"),
      mRow("  Bacteroides / Prevotella", "3,3", "<%1"),
      ndRow("  Sneathia / Leptotrichia / Fusobacterium"),
      mRow("  Megasphaera / Veillonella / Dialister", "2,4", "<%1"),
      ndRow("  BVAB1 / BVAB2 / BVAB3"),
      catRow("M\u0130KOPLAZMALAR"),
      ndRow("  Ureaplasma urealyticum"),
      mRow("  Ureaplasma parvum", "<4,0", "<%1"),
      ndRow("  Mycoplasma hominis"),
      catRow("MAYA"),
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

  // Slayt 8: FEMOBIOME Teknik
  console.log('Slayt 8: FEMOBIOME Teknik');
  await html2pptx(path.join(S, 'slide07-femobiome-tech_TR.html'), pptx);

  // Slayt 8: ENTEROBIOME Genel
  console.log('Slayt 8: ENTEROBIOME Genel');
  await html2pptx(path.join(S, 'slide08-enterobiome_TR.html'), pptx);

  // Slayt 9: ENTEROBIOME Bilim
  console.log('Slayt 9: ENTEROBIOME Bilim');
  await html2pptx(path.join(S, 'slide09-enterobiome-science_TR.html'), pptx);

  // Slayt 10: ENTEROBIOME Panel
  console.log('Slayt 10: ENTEROBIOME Panel');
  await html2pptx(path.join(S, 'slide10-enterobiome-panel_TR.html'), pptx);

  // Slayt 11: ENTEROBIOME Klinik
  console.log('Slayt 11: ENTEROBIOME Klinik');
  await html2pptx(path.join(S, 'slide11-enterobiome-clinical_TR.html'), pptx);

  // Slayt 13: ENTEROBIOME Rapor \u00c7\u0131kt\u0131s\u0131
  console.log('Slayt 13: ENTEROBIOME Rapor');
  await html2pptx(path.join(S, 'slide11b-enterobiome-report_TR.html'), pptx);

  // Slayt 14: ANDROBIOME Genel
  console.log('Slayt 14: ANDROBIOME Genel');
  await html2pptx(path.join(S, 'slide12-androbiome_TR.html'), pptx);

  // Slayt 13: ANDROBIOME Panel (tablo ile)
  console.log('Slayt 13: ANDROBIOME Panel');
  const { slide: s13, placeholders: ph13 } = await html2pptx(path.join(S, 'slide13-androbiome-panel_TR.html'), pptx);
  const androPh = ph13.find(p => p.id === 'andro-panel-table');
  if (androPh) {
    const blueHdr = { fill: { color: "0EA5E9" }, color: "FFFFFF", bold: true, fontSize: 7, align: "center", valign: "middle" };
    const chk = { text: "\u2713", options: { fontSize: 7, align: "center", color: "10B981" } };
    const dash = { text: "\u2014", options: { fontSize: 7, align: "center", color: "94A3B8" } };
    const catCell = (t) => ({ text: t, options: { fontSize: 6.5, bold: true, fill: { color: "E0F2FE" }, color: "0284C7" } });

    s13.addTable([
      [
        { text: "Kategori", options: blueHdr },
        { text: "Organizma", options: blueHdr },
        { text: "Tam", options: blueHdr },
        { text: "Screen", options: blueHdr }
      ],
      [catCell("Normal"), cel("Staphylococcus spp., Streptococcus spp., Corynebacterium spp."), chk, chk],
      [catCell("Ge\u00e7ici"), cel("Lactobacillus spp."), chk, chk],
      [catCell("BV-ili\u015fkili"), cel("Gardnerella, Megasphaera/Veillonella/Dialister, Sneathia/Leptotrichia/Fusobacterium, Atopobium k\u00fcmesi"), chk, dash],
      [catCell("Mikoplazmalar"), cel("Ureaplasma urealyticum, U. parvum, Mycoplasma hominis"), chk, chk],
      [catCell("Anaeroblar"), cel("Bacteroides/Porphyromonas/Prevotella, Anaerococcus, Peptostreptococcus/Parvimonas, Eubacterium"), chk, dash],
      [catCell("Di\u011fer FM"), cel("Haemophilus spp., Pseudomonas/Ralstonia/Burkholderia, Enterobacteriaceae/Enterococcus"), chk, { text: "K\u0131smi", options: { fontSize: 6, align: "center", color: "F59E0B" } }],
      [catCell("Maya"), cel("Candida spp."), chk, chk],
      [catCell("CYBH"), cel("C. trachomatis, M. genitalium, N. gonorrhoeae, T. vaginalis"), chk, chk],
    ], {
      ...androPh,
      border: { pt: 0.5, color: "BAE6FD" },
      colW: [1.1, 4.8, 0.7, 0.7],
      rowH: [0.3, 0.28, 0.25, 0.38, 0.28, 0.35, 0.35, 0.25, 0.28],
      valign: "middle"
    });
  }

  // Slayt 14: ANDROBIOME Klinik
  console.log('Slayt 14: ANDROBIOME Klinik');
  await html2pptx(path.join(S, 'slide14-androbiome-clinical_TR.html'), pptx);

  // Slayt 15: ANDROBIOME Sonu\u00e7lar
  console.log('Slayt 15: ANDROBIOME Sonu\u00e7lar');
  await html2pptx(path.join(S, 'slide15-androbiome-results_TR.html'), pptx);

  // Slayt 18: ANDROBIOME \u00d6rnek Sonu\u00e7 Formu (tablo ile)
  console.log('Slayt 18: ANDROBIOME \u00d6rnek Rapor');
  const { slide: s18, placeholders: ph18 } = await html2pptx(path.join(S, 'slide15b-androbiome-sample-report_TR.html'), pptx);
  const resultPh = ph18.find(p => p.id === 'result-table');
  if (resultPh) {
    const blueH = { fill: { color: "0EA5E9" }, color: "FFFFFF", bold: true, fontSize: 5, align: "center", valign: "middle" };
    const grpR = (t) => [{ text: t, options: { colspan: 4, fontSize: 5, bold: true, fill: { color: "F0F9FF" }, color: "0284C7" } }];
    const val = (num, exp) => ({ text: [{ text: `${num} x 10`, options: { fontSize: 5.5 } }, { text: exp, options: { fontSize: 4.5, superscript: true } }], options: { align: "center", valign: "middle" } });
    const nd = { text: "Saptanmad\u0131", options: { fontSize: 5.5, align: "center", color: "94A3B8" } };
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
      { text: "SAPTANDI", options: { fontSize: 5.5, align: "center", valign: "middle", bold: true, color: "991B1B", fill: { color: "FEE2E2" } } }
    ];
    s18.addTable([
      [{ text: "Mikroorganizma", options: blueH }, { text: "Sonu\u00e7 (GE)", options: blueH }, { text: "lg (GE)", options: blueH }, { text: "Durum", options: blueH }],
      grpR("Kontrol Parametreleri"),
      dRow("\u0130nsan DNA", val("4,8", "5"), lg("5,7"), st("Yeterli", "065F46", "D1FAE5")),
      dRow("Toplam Bakteriyel K\u00fctle (TBK)", val("8,5", "6"), lg("6,9"), st("Y\u00fcksek", "991B1B", "FEE2E2")),
      grpR("Ge\u00e7ici Mikroorganizmalar"),
      dRow("Lactobacillus spp.", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("Komensaller"),
      dRow("Staphylococcus spp.", val("1,2", "4"), lg("4,1"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Streptococcus spp.", val("5,8", "3"), lg("3,8"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Corynebacterium spp.", val("7,3", "3"), lg("3,9"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("F\u0131rsat\u00e7\u0131 Mikroorganizmalar"),
      dRow("Gardnerella vaginalis", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Enterobacteriaceae / Enterococcus", val("4,1", "3"), lg("3,6"), st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("Mikoplazmalar"),
      dRow("Mycoplasma hominis", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Ureaplasma urealyticum", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      dRow("Ureaplasma parvum", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("Candida"),
      dRow("Candida spp.", nd, dash, st("Normal", "065F46", "D1FAE5"), { italic: true }),
      grpR("CYBH"),
      dRow("Mycoplasma genitalium", nd, dash, st("Saptanmad\u0131", "991B1B", "FEE2E2"), { italic: true }),
      dRow("Trichomonas vaginalis", nd, dash, st("Saptanmad\u0131", "991B1B", "FEE2E2"), { italic: true }),
      detRow("Neisseria gonorrhoeae", val("7,2", "6"), lg("6,9")),
      dRow("Chlamydia trachomatis", nd, dash, st("Saptanmad\u0131", "991B1B", "FEE2E2"), { italic: true }),
    ], {
      x: resultPh.x, y: resultPh.y, w: resultPh.w,
      border: { pt: 0.3, color: "E0F2FE" },
      colW: [resultPh.w * 0.38, resultPh.w * 0.24, resultPh.w * 0.12, resultPh.w * 0.26],
      rowH: [0.15, 0.08,0.14,0.14, 0.08,0.14, 0.08,0.14,0.14,0.14, 0.08,0.14,0.14, 0.08,0.14,0.14,0.14, 0.08,0.14, 0.08,0.14,0.14,0.16,0.14],
      margin: 0.01,
      valign: "middle"
    });
  }

  // Slayt 19: Teknoloji
  console.log('Slayt 19: Teknoloji');
  await html2pptx(path.join(S, 'slide16-technology_TR.html'), pptx);

  // Slayt 17: Teknik \u00d6zellikler
  console.log('Slayt 17: Teknik \u00d6zellikler');
  await html2pptx(path.join(S, 'slide17-tech-specs_TR.html'), pptx);

  // Slayt 18: Kapan\u0131\u015f
  console.log('Slayt 18: Kapan\u0131\u015f');
  await html2pptx(path.join(S, 'slide18-closing_TR.html'), pptx);

  const outputPath = path.join(S, '..', 'Genomer_Mikrobiyom_Test_Hatti_TR.pptx');
  await pptx.writeFile({ fileName: outputPath });
  console.log(`Sunum kaydedildi: ${outputPath}`);
}

build().catch(err => { console.error('Derleme hatas\u0131:', err.message); process.exit(1); });
