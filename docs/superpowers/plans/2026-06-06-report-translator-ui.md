# Rapor Çevirici Arayüzü — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mevcut EN→TR qPCR rapor çevirici motorunun üzerine, çoklu PDF kabul eden, segment düzeyinde düzeltme yapılabilen, çıktıları diske kaydeden, Türkçe yerel masaüstü arayüzü inşa etmek.

**Architecture:** Çekirdek mantık saf bir `engine.py`'ye (çıkar/çevir/render) ve `dictionary.py`'ye taşınır. FastAPI backend (`app.py`) oturum yönetir; orijinal PDF tek doğru kaynaktır, çıktı her zaman `render(çevir(çıkar(orijinal), sözlük, override'lar))` ile taze üretilir. Statik Türkçe frontend segment editörünü sunar. PyInstaller ile native paketlenir.

**Tech Stack:** Python 3, PyMuPDF (fitz), FastAPI, uvicorn, pytest, vanilla JS/HTML/CSS, PyInstaller.

---

## Dosya yapısı

```
report_translator/
  engine.py            # YENİ: Segment, extract_segments, translate_segments, render, translate_document
  dictionary.py        # YENİ: load, add_entry (yedek+çakışma+paragraf heuristiği), detect_kit
  translate_report.py  # DEĞİŞTİR: engine+dictionary üstüne ince CLI
  app.py               # YENİ: FastAPI backend
  web/
    index.html         # YENİ
    app.js             # YENİ
    styles.css         # YENİ
    genomerlogo.png    # KOPYALA (proje kökündeki logodan)
  fonts/               # MEVCUT
  dictionary.json      # MEVCUT
  requirements.txt     # YENİ
  baslat.command       # YENİ (mac)
  baslat.bat           # YENİ (win)
  tests/
    conftest.py        # YENİ
    test_engine.py     # YENİ
    test_dictionary.py # YENİ
    test_app.py        # YENİ
  README.md            # GÜNCELLE
```

Test örnekleri için sabit yol: `../reportsamples/en/` (mevcut örnek PDF'ler).

---

## Task 0: Proje kurulumu

**Files:**
- Create: `report_translator/requirements.txt`
- Create: `report_translator/tests/conftest.py`
- Create: `report_translator/.gitignore`

- [ ] **Step 1: requirements.txt yaz**

`report_translator/requirements.txt`:
```
pymupdf==1.26.7
fastapi==0.115.0
uvicorn==0.30.6
python-multipart==0.0.9
pytest==8.3.2
httpx==0.27.2
```

- [ ] **Step 2: .gitignore yaz**

`report_translator/.gitignore`:
```
__pycache__/
*.pyc
out/
dictionary.json.bak
.venv/
build/
dist/
*.spec
```

- [ ] **Step 3: conftest.py yaz (paylaşılan fixture'lar)**

`report_translator/tests/conftest.py`:
```python
import os
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.normpath(os.path.join(HERE, "..", "..", "reportsamples", "en"))


@pytest.fixture
def femobiome_pdf():
    p = os.path.join(SAMPLES, "Femobiome_II report_eubiosis_eng.pdf")
    assert os.path.exists(p), f"örnek bulunamadı: {p}"
    return p


@pytest.fixture
def androbiome_pdf():
    p = os.path.join(SAMPLES, "Androbiome.pdf")
    assert os.path.exists(p), f"örnek bulunamadı: {p}"
    return p


@pytest.fixture
def enterobiome_pdf():
    p = os.path.join(SAMPLES, "Enterobiome Kids.pdf")
    assert os.path.exists(p), f"örnek bulunamadı: {p}"
    return p
```

- [ ] **Step 4: git deposu başlat (yoksa) ve commit**

Run:
```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git rev-parse --is-inside-work-tree 2>/dev/null || git init
git add report_translator/requirements.txt report_translator/.gitignore report_translator/tests/conftest.py
git commit -m "chore: report_translator UI proje kurulumu (requirements, gitignore, test fixtures)"
```
Expected: commit oluşur. (Not: depo yeni başlatıldıysa mevcut dosyalar untracked kalır; sadece eklenenler commit'lenir.)

---

## Task 1: engine.py — Segment modeli ve extract_segments

**Files:**
- Create: `report_translator/engine.py`
- Test: `report_translator/tests/test_engine.py`

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/tests/test_engine.py`:
```python
import fitz
import engine


def test_extract_segments_stable_ids_and_fields(femobiome_pdf):
    doc = fitz.open(femobiome_pdf)
    segs = engine.extract_segments(doc)
    assert len(segs) > 30
    # kararlı id biçimi "sayfa:sıra"
    for s in segs:
        assert ":" in s.id
        assert s.page >= 0
        assert len(s.bbox) == 4
        assert isinstance(s.en, str) and s.en.strip()
        assert s.fontfile.endswith(".ttf")
        assert s.size > 0
    # iki kez çıkarınca aynı id'ler (determinizm)
    segs2 = engine.extract_segments(fitz.open(femobiome_pdf))
    assert [s.id for s in segs] == [s.id for s in segs2]


def test_extract_finds_conclusion_paragraph(femobiome_pdf):
    doc = fitz.open(femobiome_pdf)
    segs = engine.extract_segments(doc)
    concl = [s for s in segs if "predominance of normal" in s.en]
    assert len(concl) == 1
    assert concl[0].is_paragraph is True
    assert "Bifidobacterium spp. <1%." in concl[0].en
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine'`

- [ ] **Step 3: engine.py'nin çıkarma kısmını yaz**

`report_translator/engine.py`:
```python
"""engine.py — qPCR rapor PDF'lerini EN->TR çevirmek için saf çekirdek:
çıkar (extract) -> çevir (translate) -> render. UI ve CLI bunu kullanır.
"""
import os
import re
from dataclasses import dataclass, field
import fitz  # PyMuPDF

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

FONT_MAP = {
    "roboto-regular": "Roboto-Regular.ttf",
    "roboto-italic": "Roboto-Italic.ttf",
    "montserrat-bold": "Montserrat-Bold.ttf",
    "arial": "Arial-Regular.ttf",
    "arial,bold": "Arial-Bold.ttf",
    "arial-bold": "Arial-Bold.ttf",
    "calibri": "Carlito-Regular.ttf",
    "calibri,bold": "Carlito-Bold.ttf",
    "calibri,italic": "Carlito-Italic.ttf",
    "calibri,bolditalic": "Carlito-BoldItalic.ttf",
}


def map_font(orig_font):
    key = orig_font.lower().lstrip("+")
    if "+" in orig_font:
        key = orig_font.split("+", 1)[1].lower()
    if key in FONT_MAP:
        return FONT_MAP[key]
    bold = "bold" in key
    ital = "italic" in key or "oblique" in key
    if "calibri" in key or "carlito" in key:
        return ("Carlito-BoldItalic.ttf" if bold and ital else
                "Carlito-Bold.ttf" if bold else
                "Carlito-Italic.ttf" if ital else "Carlito-Regular.ttf")
    if "montserrat" in key:
        return "Montserrat-Bold.ttf"
    if "roboto" in key:
        return "Roboto-Italic.ttf" if ital else "Roboto-Regular.ttf"
    return "Arial-Bold.ttf" if bold else "Arial-Regular.ttf"


def norm_ws(s):
    return re.sub(r"\s+", " ", s).strip()


def _int_to_rgb(c):
    return (((c >> 16) & 255) / 255.0, ((c >> 8) & 255) / 255.0, (c & 255) / 255.0)


def _line_text(line):
    return "".join(s["text"] for s in line["spans"])


def _dominant_span(lines):
    best, best_len = None, -1
    for line in lines:
        for s in line["spans"]:
            if len(s["text"]) > best_len:
                best_len, best = len(s["text"]), s
    return best


def _group_units(block):
    """Blok satırlarını birimlere ayır: x0 paylaşan + sıkı dikey pitch'li satırlar bir birim."""
    units, cur = [], []
    for ln in block["lines"]:
        if not ln["spans"]:
            continue
        lx0, ly0 = ln["bbox"][0], ln["bbox"][1]
        size = ln["spans"][0]["size"]
        if cur:
            px0, py1 = cur[-1]["bbox"][0], cur[-1]["bbox"][3]
            if abs(lx0 - px0) <= 3 and -0.5 * size <= (ly0 - py1) <= 0.7 * size:
                cur.append(ln)
                continue
            units.append(cur)
            cur = [ln]
        else:
            cur = [ln]
    if cur:
        units.append(cur)
    return units


def _is_flowing_paragraph(unit):
    """Çok-satırlı birim gerçek sarılmış paragraf mı (conclusion) yoksa istiflenmiş ayrı
    etiketler mi (Age/Organization)? Geometri: sarılmış prozada son-olmayan satırlar geniştir."""
    if len(unit) < 2:
        return False
    widths = [l["bbox"][2] - l["bbox"][0] for l in unit]
    maxw = max(widths)
    non_last = widths[:-1]
    return maxw > 80 and all(w >= 0.6 * maxw for w in non_last)


@dataclass
class Segment:
    id: str
    page: int
    bbox: list            # [x0,y0,x1,y1] birim sınırı
    en: str               # birleştirilmiş ham kaynak metin
    fontfile: str
    size: float
    color: tuple
    single_line: bool
    rects: list           # render için satır bbox'ları
    origin: tuple         # ilk satır ilk span taban noktası (x,y)
    raw_first: str        # ilk satırın ham metni (girinti hesabı için)
    is_paragraph: bool


def _segment_from_unit(unit, page, seq):
    dom = _dominant_span(unit)
    xs0 = min(l["bbox"][0] for l in unit)
    ys0 = min(l["bbox"][1] for l in unit)
    xs1 = max(l["bbox"][2] for l in unit)
    ys1 = max(l["bbox"][3] for l in unit)
    return Segment(
        id="%d:%d" % (page, seq),
        page=page,
        bbox=[xs0, ys0, xs1, ys1],
        en=" ".join(_line_text(l) for l in unit),
        fontfile=map_font(dom["font"]),
        size=dom["size"],
        color=_int_to_rgb(dom["color"]),
        single_line=len(unit) == 1,
        rects=[list(l["bbox"]) for l in unit],
        origin=tuple(unit[0]["spans"][0]["origin"]),
        raw_first=_line_text(unit[0]),
        is_paragraph=_is_flowing_paragraph(unit),
    )


def extract_segments(doc):
    """Belgedeki tüm çevrilebilir birimleri kararlı id'lerle döndür.
    Çok-satırlı birim gerçek paragrafsa tek segment; değilse satır başına segment."""
    segments = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        data = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
        seq = 0
        for block in data["blocks"]:
            if "lines" not in block:
                continue
            for unit in _group_units(block):
                if len(unit) > 1 and not _is_flowing_paragraph(unit):
                    for line in unit:  # istiflenmiş ayrı etiketler -> satır başına segment
                        segments.append(_segment_from_unit([line], page_index, seq))
                        seq += 1
                else:
                    segments.append(_segment_from_unit(unit, page_index, seq))
                    seq += 1
    return segments
```

- [ ] **Step 4: Testi çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py -v`
Expected: PASS (2 test)

- [ ] **Step 5: Commit**

```bash
git add report_translator/engine.py report_translator/tests/test_engine.py
git commit -m "feat(engine): Segment modeli ve extract_segments (geometri-tabanlı paragraf tespiti)"
```

---

## Task 2: engine.py — translate_segments (override + kaynak-tipi)

**Files:**
- Modify: `report_translator/engine.py` (sona ekle)
- Test: `report_translator/tests/test_engine.py` (ekle)

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/tests/test_engine.py` sonuna ekle:
```python
import dictionary as dict_mod


def _table():
    kits, common, passthrough, _ = dict_mod.load()
    return kits["femobiome_ii"], passthrough


def test_translate_exact_and_passthrough(femobiome_pdf):
    table, passthrough = _table()
    doc = fitz.open(femobiome_pdf)
    segs = engine.extract_segments(doc)
    ann = engine.translate_segments(segs, table, passthrough, overrides={})
    by_en = {a.en: a for a in ann}
    # tam eşleşen etiket
    yeast = by_en.get("Yeast fungi")
    assert yeast and yeast.tr == "Maya mantarları" and yeast.source == "dict-exact"
    # Latin tür adı -> passthrough (değişmez)
    cand = [a for a in ann if a.en.strip() == "Candida albicans"]
    assert cand and cand[0].source == "passthrough" and cand[0].tr == cand[0].en


def test_translate_override_wins(femobiome_pdf):
    table, passthrough = _table()
    doc = fitz.open(femobiome_pdf)
    segs = engine.extract_segments(doc)
    target = next(s for s in segs if s.en == "Yeast fungi")
    ann = engine.translate_segments(segs, table, passthrough,
                                    overrides={target.id: "ÖZEL ÇEVİRİ"})
    a = next(x for x in ann if x.id == target.id)
    assert a.tr == "ÖZEL ÇEVİRİ" and a.source == "override"


def test_translate_unknown_flagged(femobiome_pdf):
    table, passthrough = _table()
    doc = fitz.open(femobiome_pdf)
    ann = engine.translate_segments(engine.extract_segments(doc), table, passthrough, {})
    # bilinmeyen ya da kısmi paragraf -> needs_review True olan en az bir öğe
    assert any(a.needs_review for a in ann)
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py::test_translate_exact_and_passthrough -v`
Expected: FAIL — `AttributeError: module 'engine' has no attribute 'translate_segments'` (veya dictionary modülü yok)

- [ ] **Step 3: translate_segments'i engine.py'ye ekle**

`report_translator/engine.py` sonuna ekle:
```python
@dataclass
class AnnotatedSegment:
    seg: Segment
    tr: str
    source: str           # dict-exact | dict-partial | passthrough | unknown | override
    needs_review: bool

    # render kolaylığı için pass-through alanlar
    @property
    def id(self): return self.seg.id
    @property
    def en(self): return self.seg.en
    @property
    def page(self): return self.seg.page


class _Matcher:
    def __init__(self, table, passthrough):
        self.table = table
        self.keys = sorted(table.keys(), key=len, reverse=True)
        self.passthrough = passthrough

    def is_passthrough_full(self, t):
        return any(p.fullmatch(t) for p in self.passthrough)

    def translate(self, text):
        """(çeviri, değişti_mi, tam_eşleşme_mi)"""
        t = norm_ws(text)
        if not t:
            return text, False, False
        if t in self.table:
            return self.table[t], True, True
        if self.is_passthrough_full(t):
            return text, False, False
        result = t
        for k in self.keys:
            if k in result:
                result = result.replace(k, self.table[k])
        changed = norm_ws(result) != t
        return (result if changed else text), changed, False


def translate_segments(segments, table, passthrough, overrides):
    matcher = _Matcher(table, passthrough)
    out = []
    for s in segments:
        if s.id in overrides:
            out.append(AnnotatedSegment(s, overrides[s.id], "override", False))
            continue
        tr, changed, exact = matcher.translate(s.en)
        if not changed:
            has_alpha = bool(re.search(r"[A-Za-z]{3,}", norm_ws(s.en)))
            is_pass = matcher.is_passthrough_full(norm_ws(s.en))
            source = "passthrough" if (is_pass or not has_alpha) else "unknown"
            needs = source == "unknown"
        elif exact:
            source, needs = "dict-exact", False
        else:
            source, needs = "dict-partial", True
        out.append(AnnotatedSegment(s, tr, source, needs))
    return out
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py -v`
Expected: PASS (test_dictionary henüz yoksa Task 5'te eklenir; bu testler `dictionary.load()` gerektirir — Task 5'i bu task'tan ÖNCE yapın VEYA `dictionary.py`'yi Task 5 Step 3'teki haliyle önce ekleyin.)

> **Sıra notu:** `engine.translate_segments` testleri `dictionary.load()`'a bağlıdır. Bu nedenle **Task 5 (dictionary.py) bu adımdan önce tamamlanmalı.** Yürütücü: Task 1 → Task 5 → Task 2 → Task 3 sırasını izleyin.

- [ ] **Step 5: Commit**

```bash
git add report_translator/engine.py report_translator/tests/test_engine.py
git commit -m "feat(engine): translate_segments (override, passthrough, kaynak-tipi)"
```

---

## Task 3: engine.py — render ve translate_document

**Files:**
- Modify: `report_translator/engine.py` (sona ekle)
- Test: `report_translator/tests/test_engine.py` (ekle)

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/tests/test_engine.py` sonuna ekle:
```python
def test_render_produces_turkish_pdf(femobiome_pdf):
    table, passthrough = _table()
    out_bytes = engine.translate_document_bytes(femobiome_pdf, table, passthrough, overrides={})
    assert out_bytes[:4] == b"%PDF"
    rendered = fitz.open(stream=out_bytes, filetype="pdf")
    text = rendered[0].get_text()
    assert "Maya mantarları" in text          # çeviri uygulanmış
    assert "Mikrobiyota durumu" in text       # paragraf/başlık çevrilmiş
    assert len(rendered) == 2                  # sayfa sayısı korunmuş


def test_render_applies_override(femobiome_pdf):
    table, passthrough = _table()
    doc = fitz.open(femobiome_pdf)
    target = next(s for s in engine.extract_segments(doc) if s.en == "Yeast fungi")
    out_bytes = engine.translate_document_bytes(
        femobiome_pdf, table, passthrough, overrides={target.id: "ÖZELMAYA"})
    text = fitz.open(stream=out_bytes, filetype="pdf")[0].get_text()
    assert "ÖZELMAYA" in text
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py::test_render_produces_turkish_pdf -v`
Expected: FAIL — `AttributeError: ... 'translate_document_bytes'`

- [ ] **Step 3: render ve translate_document_bytes'ı ekle**

`report_translator/engine.py` sonuna ekle:
```python
def _leading_indent(text, font, size):
    n = len(text) - len(text.lstrip(" "))
    return font.text_length(" " * n, size) if n else 0.0


def render(doc, annotated):
    """annotated: AnnotatedSegment listesi. doc üzerinde yerinde render (kopya verin).
    Yalnızca değişen (override/dict ile çevrilen) segmentler işlenir."""
    by_page = {}
    for a in annotated:
        if a.source in ("passthrough",) or a.tr == a.en:
            continue
        if a.source == "unknown":
            continue
        by_page.setdefault(a.seg.page, []).append(a)

    font_cache = {}
    for page_index, items in by_page.items():
        page = doc[page_index]
        # 1) yalnızca metni sil
        for a in items:
            for r in a.seg.rects:
                page.add_redact_annot(fitz.Rect(r), fill=None)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_REMOVE)
        # 2) Türkçe metni yerleştir
        for a in items:
            s = a.seg
            fontfile = os.path.join(FONT_DIR, s.fontfile)
            fontname = font_cache.get(s.fontfile)
            if fontname is None:
                fontname = "F%d" % len(font_cache)
                font_cache[s.fontfile] = fontname
            font = fitz.Font(fontfile=fontfile)
            text = a.tr.strip()
            indent = _leading_indent(s.raw_first, font, s.size)
            if s.single_line:
                ox, oy = s.origin
                page.insert_text((ox + indent, oy), text, fontname=fontname,
                                 fontfile=fontfile, fontsize=s.size, color=s.color)
            else:
                box = fitz.Rect(s.bbox)
                left = box.x0 + indent
                fs = s.size
                while fs > 4.5:
                    pad = fitz.Rect(left, box.y0 - 1, box.x1 + 2, box.y1 + 4 * s.size)
                    rc = page.insert_textbox(pad, text, fontname=fontname, fontfile=fontfile,
                                             fontsize=fs, color=s.color, lineheight=1.15,
                                             align=fitz.TEXT_ALIGN_LEFT)
                    if rc >= 0:
                        break
                    fs -= 0.25
    return doc


def translate_document_bytes(pdf_path_or_bytes, table, passthrough, overrides):
    """Orijinalden taze TR PDF bayt'ı üretir. pdf_path_or_bytes: yol (str) veya bytes."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    segs = extract_segments(doc)
    ann = translate_segments(segs, table, passthrough, overrides)
    render(doc, ann)
    out = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py -v`
Expected: PASS (tümü)

- [ ] **Step 5: Commit**

```bash
git add report_translator/engine.py report_translator/tests/test_engine.py
git commit -m "feat(engine): render + translate_document_bytes (taze, override'lı)"
```

---

## Task 5: dictionary.py — yükleme, ekleme, çakışma

> **Bu task, Task 2'den ÖNCE tamamlanmalı** (engine testleri buna bağlı).

**Files:**
- Create: `report_translator/dictionary.py`
- Test: `report_translator/tests/test_dictionary.py`

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/tests/test_dictionary.py`:
```python
import json
import shutil
import dictionary


def test_load_returns_kits_and_passthrough():
    kits, common, passthrough, raw = dictionary.load()
    assert "femobiome_ii" in kits and "androbiome" in kits
    assert kits["femobiome_ii"]["Yeast fungi"] == "Maya mantarları"
    assert passthrough  # derlenmiş regex listesi
    assert hasattr(passthrough[0], "fullmatch")


def test_detect_kit(femobiome_pdf, androbiome_pdf):
    import fitz
    assert dictionary.detect_kit(fitz.open(femobiome_pdf)) == "femobiome_ii"
    assert dictionary.detect_kit(fitz.open(androbiome_pdf)) == "androbiome"


def test_add_entry_short_label_and_backup(tmp_path):
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)
    res = dictionary.add_entry("femobiome_ii", "Brand New Label", "Yepyeni Etiket",
                               path=str(work))
    assert res["ok"] and not res.get("conflict")
    data = json.load(open(work, encoding="utf-8"))
    assert data["femobiome_ii"]["Brand New Label"] == "Yepyeni Etiket"
    assert (tmp_path / "dictionary.json.bak").exists()  # yedek alındı


def test_add_entry_long_goes_to_paragraphs(tmp_path):
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)
    long_en = "This is a long sentence with clearly more than six words total here."
    dictionary.add_entry("femobiome_ii", long_en, "Bu uzun bir cümledir.", path=str(work))
    data = json.load(open(work, encoding="utf-8"))
    assert long_en in data["femobiome_ii"]["_paragraphs"]


def test_add_entry_conflict_detected(tmp_path):
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)
    res = dictionary.add_entry("femobiome_ii", "Yeast fungi", "Farklı Çeviri",
                               path=str(work), overwrite=False)
    assert res["conflict"] and res["existing"] == "Maya mantarları"
    # overwrite=True ile üzerine yazılır
    res2 = dictionary.add_entry("femobiome_ii", "Yeast fungi", "Farklı Çeviri",
                                path=str(work), overwrite=True)
    assert res2["ok"]
    data = json.load(open(work, encoding="utf-8"))
    assert data["femobiome_ii"]["Yeast fungi"] == "Farklı Çeviri"
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_dictionary.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dictionary'`

- [ ] **Step 3: dictionary.py yaz**

`report_translator/dictionary.py`:
```python
"""dictionary.py — sözlüğü yükle ve düzenle (yedek + çakışma + paragraf heuristiği)."""
import os
import re
import json
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, "dictionary.json")
PARAGRAPH_WORD_THRESHOLD = 6  # >=6 kelime -> _paragraphs


def load(path=None):
    """(kits_by_kit, common, compiled_passthrough, raw) döndür."""
    path = path or DICT_PATH
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    passthrough = [re.compile(p) for p in raw.get("passthrough_patterns", [])]
    common = dict(raw.get("common", {}))
    kits = {}
    for kit in ("femobiome_ii", "androbiome", "enterobiome_kids"):
        sec = raw.get(kit, {})
        atomic = {k: v for k, v in sec.items() if k != "_paragraphs"}
        paras = sec.get("_paragraphs", {})
        merged = {}
        merged.update(common)
        merged.update(atomic)
        merged.update(paras)
        kits[kit] = merged
    return kits, common, passthrough, raw


def detect_kit(doc):
    text = " ".join(doc[i].get_text() for i in range(min(2, len(doc)))).lower()
    if "androbiome" in text or "% of tmd" in text or "bv-associated" in text:
        return "androbiome"
    if "enterobiome" in text or "intestinal microbiota" in text or "ge/g" in text:
        return "enterobiome_kids"
    return "femobiome_ii"


def add_entry(kit, en, tr, path=None, overwrite=False):
    """Sözlüğe EN->TR ekle. Yedek alır, çakışmayı bildirir, uzun metni _paragraphs'a koyar.
    Döner: {ok, conflict?, existing?}"""
    path = path or DICT_PATH
    en = re.sub(r"\s+", " ", en).strip()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    sec = data.setdefault(kit, {})
    paras = sec.setdefault("_paragraphs", {})

    existing = None
    if en in data.get("common", {}):
        existing = data["common"][en]
    elif en in sec and en != "_paragraphs":
        existing = sec[en]
    elif en in paras:
        existing = paras[en]
    if existing is not None and existing != tr and not overwrite:
        return {"ok": False, "conflict": True, "existing": existing}

    # yedek
    shutil.copy(path, path + ".bak")

    is_long = len(en.split()) >= PARAGRAPH_WORD_THRESHOLD
    # önce eski konumdan temizle (taşıma olabilir)
    sec.pop(en, None)
    paras.pop(en, None)
    if is_long:
        paras[en] = tr
    else:
        sec[en] = tr

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"ok": True, "conflict": False}
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_dictionary.py -v`
Expected: PASS (5 test)

- [ ] **Step 5: Commit**

```bash
git add report_translator/dictionary.py report_translator/tests/test_dictionary.py
git commit -m "feat(dictionary): load/detect_kit/add_entry (yedek, çakışma, paragraf heuristiği)"
```

---

## Task 4: translate_report.py CLI'yi engine üstüne taşı

**Files:**
- Modify: `report_translator/translate_report.py` (tamamen değiştir)
- Test: `report_translator/tests/test_app.py` (CLI smoke testi — geçici, burada)

- [ ] **Step 1: CLI smoke testini yaz**

`report_translator/tests/test_app.py` (şimdilik yalnız CLI):
```python
import os
import subprocess
import sys
import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.normpath(os.path.join(HERE, ".."))


def test_cli_translates_to_file(femobiome_pdf, tmp_path):
    out = tmp_path / "cikti_TR.pdf"
    r = subprocess.run([sys.executable, "translate_report.py", femobiome_pdf,
                        "-o", str(out)], cwd=RT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.exists()
    assert "Maya mantarları" in fitz.open(str(out))[0].get_text()
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_app.py::test_cli_translates_to_file -v`
Expected: FAIL (mevcut CLI hâlâ eski; ama büyük olasılıkla PASS olabilir — eski CLI de "Maya mantarları" üretir. Eğer PASS ise yine de Step 3'te refaktör edip determinizmi engine'e bağlayın.)

- [ ] **Step 3: translate_report.py'yi engine+dictionary kullanacak şekilde değiştir**

`report_translator/translate_report.py` (tüm içerik):
```python
#!/usr/bin/env python3
"""translate_report.py — qPCR rapor PDF'lerini EN->TR çeviren CLI (engine üstüne ince katman)."""
import os
import argparse
import fitz
import engine
import dictionary


def translate_pdf(in_path, out_path, kit=None):
    kits, common, passthrough, _ = dictionary.load()
    doc = fitz.open(in_path)
    kit = kit or dictionary.detect_kit(doc)
    table = kits[kit]
    segs = engine.extract_segments(doc)
    ann = engine.translate_segments(segs, table, passthrough, overrides={})
    engine.render(doc, ann)
    doc.save(out_path, garbage=4, deflate=True)
    doc.close()

    review = sorted({a.en for a in ann if a.needs_review})
    with open(os.path.splitext(out_path)[0] + "_review.txt", "w", encoding="utf-8") as f:
        f.write("# Sözlüğe eklenecek / gözden geçirilecek birimler\n")
        f.write("# kit: %s | kaynak: %s\n\n" % (kit, os.path.basename(in_path)))
        for line in review:
            f.write(line + "\n")
    translated = sum(1 for a in ann if a.source in ("dict-exact", "dict-partial", "override"))
    print("✓ %-50s [%s] %d çevrildi, %d gözden geçir"
          % (os.path.basename(out_path), kit, translated, len(review)))


def main():
    ap = argparse.ArgumentParser(description="EN->TR qPCR rapor PDF çevirici")
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--kit", choices=["femobiome_ii", "androbiome", "enterobiome_kids"])
    args = ap.parse_args()
    if os.path.isdir(args.input):
        for f in sorted(os.listdir(args.input)):
            if f.lower().endswith(".pdf"):
                p = os.path.join(args.input, f)
                translate_pdf(p, os.path.splitext(p)[0] + "_TR.pdf", args.kit)
    else:
        out = args.output or (os.path.splitext(args.input)[0] + "_TR.pdf")
        translate_pdf(args.input, out, args.kit)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testi çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_app.py::test_cli_translates_to_file -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add report_translator/translate_report.py report_translator/tests/test_app.py
git commit -m "refactor(cli): translate_report engine+dictionary üstüne ince katman"
```

---

## Task 6: app.py — FastAPI backend

**Files:**
- Create: `report_translator/app.py`
- Test: `report_translator/tests/test_app.py` (ekle)

- [ ] **Step 1: Başarısız API testini yaz**

`report_translator/tests/test_app.py` sonuna ekle:
```python
from fastapi.testclient import TestClient
import app as app_mod


def _client():
    return TestClient(app_mod.app)


def test_upload_manifest_edit_save_flow(femobiome_pdf, tmp_path):
    c = _client()
    app_mod.set_out_dir(str(tmp_path))  # testte çıktı klasörünü izole et
    with open(femobiome_pdf, "rb") as fh:
        r = c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    s = body["session_id"]
    f = body["files"][0]["file_id"]
    assert body["files"][0]["kit"] == "femobiome_ii"
    assert body["files"][0]["counts"]["translated"] > 0

    # manifest
    m = c.get(f"/api/{s}/{f}/manifest").json()
    seg = next(x for x in m if x["en"] == "Yeast fungi")
    assert seg["tr"] == "Maya mantarları"

    # sayfa görüntüsü
    png = c.get(f"/api/{s}/{f}/page/0.png")
    assert png.status_code == 200 and png.content[:8] == b"\x89PNG\r\n\x1a\n"

    # segment düzelt (sadece bu rapor)
    e = c.post(f"/api/{s}/{f}/segment/{seg['id']}",
               json={"tr": "ÖZELMAYA", "scope": "report"})
    assert e.status_code == 200 and e.json()["ok"]

    # kaydet -> diske yazılır ve override yansır
    sv = c.post(f"/api/{s}/{f}/save").json()
    assert os.path.exists(sv["saved_path"])
    assert "ÖZELMAYA" in fitz.open(sv["saved_path"])[0].get_text()
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_app.py::test_upload_manifest_edit_save_flow -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: app.py yaz**

`report_translator/app.py`:
```python
"""app.py — Rapor Çevirici yerel backend (FastAPI). Yalnız 127.0.0.1.
Orijinal PDF tek doğru kaynak; çıktı her zaman taze render edilir."""
import os
import io
import uuid
import zipfile
import fitz
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import engine
import dictionary

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")

app = FastAPI(title="Genomer Rapor Çevirici")

SESSIONS = {}  # session_id -> {"files": {file_id: FileState}}
_OUT_DIR = os.path.join(os.path.expanduser("~"), "Genomer Ceviriler")


def set_out_dir(path):
    global _OUT_DIR
    _OUT_DIR = path
    os.makedirs(_OUT_DIR, exist_ok=True)


def _table_for(kit):
    kits, common, passthrough, _ = dictionary.load()
    return kits[kit], passthrough


def _annotate(fs):
    table, passthrough = _table_for(fs["kit"])
    doc = fitz.open(stream=fs["pdf_bytes"], filetype="pdf")
    segs = engine.extract_segments(doc)
    return engine.translate_segments(segs, table, passthrough, fs["overrides"]), doc


def _counts(ann):
    translated = sum(1 for a in ann if a.source in ("dict-exact", "dict-partial", "override"))
    review = sum(1 for a in ann if a.needs_review)
    return {"translated": translated, "review": review, "total": len(ann)}


def _render_bytes(fs):
    table, passthrough = _table_for(fs["kit"])
    return engine.translate_document_bytes(fs["pdf_bytes"], table, passthrough, fs["overrides"])


def _get(session, file):
    sess = SESSIONS.get(session)
    if not sess or file not in sess["files"]:
        raise HTTPException(404, "oturum/dosya yok")
    return sess["files"][file]


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    set_out_dir(_OUT_DIR)
    session_id = uuid.uuid4().hex[:12]
    SESSIONS[session_id] = {"files": {}}
    out = []
    for uf in files:
        data = await uf.read()
        if not data[:4] == b"%PDF":
            out.append({"name": uf.filename, "error": "geçersiz PDF"})
            continue
        kit = dictionary.detect_kit(fitz.open(stream=data, filetype="pdf"))
        file_id = uuid.uuid4().hex[:8]
        fs = {"name": uf.filename, "pdf_bytes": data, "kit": kit,
              "overrides": {}, "saved_path": None}
        SESSIONS[session_id]["files"][file_id] = fs
        ann, _ = _annotate(fs)
        out.append({"file_id": file_id, "name": uf.filename, "kit": kit,
                    "counts": _counts(ann)})
    return {"session_id": session_id, "files": out}


@app.get("/api/{session}/{file}/manifest")
def manifest(session: str, file: str):
    fs = _get(session, file)
    ann, _ = _annotate(fs)
    return [{"id": a.id, "page": a.page, "bbox": a.seg.bbox, "en": a.en, "tr": a.tr,
             "source": a.source, "needs_review": a.needs_review} for a in ann]


@app.get("/api/{session}/{file}/page/{n}.png")
def page_png(session: str, file: str, n: int):
    fs = _get(session, file)
    out_bytes = _render_bytes(fs)
    doc = fitz.open(stream=out_bytes, filetype="pdf")
    if n < 0 or n >= len(doc):
        raise HTTPException(404, "sayfa yok")
    png = doc[n].get_pixmap(dpi=150).tobytes("png")
    return Response(content=png, media_type="image/png")


class SegmentEdit(BaseModel):
    tr: str
    scope: str  # "dict" | "report"


@app.post("/api/{session}/{file}/segment/{seg}")
def edit_segment(session: str, file: str, seg: str, body: SegmentEdit):
    fs = _get(session, file)
    fs["overrides"][seg] = body.tr
    result = {"ok": True}
    if body.scope == "dict":
        ann, _ = _annotate(fs)
        en = next((a.en for a in ann if a.id == seg), None)
        if en:
            res = dictionary.add_entry(fs["kit"], en, body.tr, overwrite=False)
            if res.get("conflict"):
                return {"ok": True, "conflict": True, "existing": res["existing"], "en": en}
    return result


class KitBody(BaseModel):
    kit: str


@app.post("/api/{session}/{file}/kit")
def set_kit(session: str, file: str, body: KitBody):
    fs = _get(session, file)
    fs["kit"] = body.kit
    fs["overrides"] = {}
    ann, _ = _annotate(fs)
    return {"ok": True, "counts": _counts(ann)}


def _save_one(fs):
    os.makedirs(_OUT_DIR, exist_ok=True)
    base = os.path.splitext(fs["name"])[0]
    path = os.path.join(_OUT_DIR, base + "_TR.pdf")
    with open(path, "wb") as f:
        f.write(_render_bytes(fs))
    fs["saved_path"] = path
    return path


@app.post("/api/{session}/{file}/save")
def save_one(session: str, file: str):
    fs = _get(session, file)
    return {"ok": True, "saved_path": _save_one(fs)}


@app.post("/api/{session}/save_all")
def save_all(session: str):
    sess = SESSIONS.get(session)
    if not sess:
        raise HTTPException(404, "oturum yok")
    return {"ok": True, "paths": [_save_one(fs) for fs in sess["files"].values()]}


@app.get("/api/{session}/{file}/download")
def download(session: str, file: str):
    fs = _get(session, file)
    base = os.path.splitext(fs["name"])[0]
    return Response(content=_render_bytes(fs), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{base}_TR.pdf"'})


@app.get("/api/{session}/download_all")
def download_all(session: str):
    sess = SESSIONS.get(session)
    if not sess:
        raise HTTPException(404, "oturum yok")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fs in sess["files"].values():
            base = os.path.splitext(fs["name"])[0]
            z.writestr(base + "_TR.pdf", _render_bytes(fs))
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="ceviriler.zip"'})


class OutDirBody(BaseModel):
    path: str


@app.post("/api/{session}/out_dir")
def change_out_dir(session: str, body: OutDirBody):
    set_out_dir(body.path)
    return {"ok": True, "out_dir": _OUT_DIR}


# statik frontend (en sonda mount edilir ki /api yolları gölgelenmesin)
if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_app.py -v`
Expected: PASS (`web/` henüz yoksa StaticFiles mount edilmez; sorun değil.)

- [ ] **Step 5: Commit**

```bash
git add report_translator/app.py report_translator/tests/test_app.py
git commit -m "feat(app): FastAPI backend (upload/manifest/page/segment/save/zip)"
```

---

## Task 7: web/ frontend (statik, Türkçe)

**Files:**
- Create: `report_translator/web/index.html`
- Create: `report_translator/web/styles.css`
- Create: `report_translator/web/app.js`
- Copy: `report_translator/web/genomerlogo.png` ← `genomerlogo.png` (proje kökü)

> **Not:** Estetik için uygulama sırasında `frontend-design` skill'i kullanılabilir; aşağıdaki
> dosyalar çalışan, temiz bir taban sağlar. Genomer mor/mavi paleti, Inter/sistem fontu.

- [ ] **Step 1: Logoyu kopyala**

Run:
```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
cp genomerlogo.png report_translator/web/genomerlogo.png
```

- [ ] **Step 2: index.html yaz**

`report_translator/web/index.html`:
```html
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Genomer · Rapor Çevirici</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header>
    <img src="genomerlogo.png" alt="Genomer" class="logo">
    <h1>Rapor Çevirici <span>EN → TR</span></h1>
    <div class="out-dir">Çıktı: <code id="outDir">~/Genomer Ceviriler</code></div>
  </header>

  <main>
    <section id="uploadView">
      <div id="dropzone" class="dropzone">
        <p>PDF raporlarını buraya sürükleyin <br><small>veya tıklayıp seçin (çoklu)</small></p>
        <input type="file" id="fileInput" accept="application/pdf" multiple hidden>
      </div>
      <div id="cards" class="cards"></div>
      <div id="batchActions" class="batch hidden">
        <button id="saveAllBtn">Tümünü kaydet</button>
        <button id="zipBtn" class="ghost">ZIP indir</button>
      </div>
    </section>

    <section id="editView" class="hidden">
      <button id="backBtn" class="ghost">← Geri</button>
      <h2 id="editTitle"></h2>
      <div class="editor">
        <div id="pages" class="pages"></div>
        <aside class="segments">
          <div class="filter">
            <button data-filter="all" class="active">Tümü</button>
            <button data-filter="review">Gözden geçirilecek</button>
          </div>
          <div id="segList"></div>
        </aside>
      </div>
    </section>
  </main>

  <div id="toast" class="toast hidden"></div>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: styles.css yaz**

`report_translator/web/styles.css`:
```css
:root{--mor:#6c3a8e;--mavi:#2b6cb0;--bg:#f6f7fb;--kart:#fff;--cizgi:#e3e6ef;
  --uyari:#b7791f;--ok:#2f855a;--metin:#1a202c;}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;
  background:var(--bg);color:var(--metin)}
header{display:flex;align-items:center;gap:16px;padding:14px 22px;background:var(--kart);
  border-bottom:1px solid var(--cizgi)}
.logo{height:34px}
header h1{font-size:18px;margin:0;font-weight:700}
header h1 span{color:var(--mor);font-weight:500;font-size:14px;margin-left:6px}
.out-dir{margin-left:auto;font-size:13px;color:#667}
main{max-width:1200px;margin:24px auto;padding:0 22px}
.hidden{display:none!important}
.dropzone{border:2px dashed var(--mavi);border-radius:14px;padding:54px;text-align:center;
  background:var(--kart);cursor:pointer;transition:.15s}
.dropzone.drag{background:#eef3fb;border-color:var(--mor)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;
  margin-top:20px}
.card{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:14px}
.card .kit{display:inline-block;font-size:11px;padding:2px 8px;border-radius:20px;
  background:#efe7f5;color:var(--mor);margin-bottom:8px}
.card .name{font-weight:600;font-size:13px;word-break:break-word}
.card .stat{font-size:13px;margin-top:8px}
.card .ok{color:var(--ok)} .card .warn{color:var(--uyari)}
.card .err{color:#c53030;font-size:13px}
.card button{margin-top:10px}
button{background:var(--mor);color:#fff;border:0;border-radius:8px;padding:8px 14px;
  font-size:13px;cursor:pointer}
button.ghost{background:#fff;color:var(--mor);border:1px solid var(--mor)}
button:hover{filter:brightness(1.05)}
.batch{margin-top:18px;display:flex;gap:10px}
.editor{display:grid;grid-template-columns:1fr 420px;gap:18px;margin-top:12px}
.pages{max-height:78vh;overflow:auto;background:var(--kart);border:1px solid var(--cizgi);
  border-radius:12px;padding:10px}
.pageWrap{position:relative;margin-bottom:10px}
.pageWrap img{width:100%;display:block;border:1px solid var(--cizgi)}
.box{position:absolute;border:1.5px solid transparent;border-radius:3px;cursor:pointer}
.box:hover,.box.active{border-color:var(--mavi);background:rgba(43,108,176,.12)}
.box.review{border-color:var(--uyari);background:rgba(183,121,31,.10)}
.segments{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;
  padding:12px;max-height:78vh;overflow:auto}
.filter{display:flex;gap:8px;margin-bottom:10px}
.filter button{background:#eef;color:#334;font-size:12px;padding:5px 10px}
.filter button.active{background:var(--mor);color:#fff}
.seg{border:1px solid var(--cizgi);border-radius:9px;padding:10px;margin-bottom:9px}
.seg.review{border-color:var(--uyari)}
.seg.active{box-shadow:0 0 0 2px var(--mavi)}
.seg .en{font-size:12px;color:#667;margin-bottom:5px}
.seg textarea{width:100%;border:1px solid var(--cizgi);border-radius:6px;padding:6px;
  font:inherit;resize:vertical;min-height:34px}
.seg .acts{display:flex;gap:6px;margin-top:6px}
.seg .acts button{font-size:12px;padding:5px 9px}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#222;
  color:#fff;padding:10px 16px;border-radius:8px;font-size:13px}
```

- [ ] **Step 4: app.js yaz**

`report_translator/web/app.js`:
```javascript
const $ = (s, r = document) => r.querySelector(s);
const api = (p, o) => fetch("/api" + p, o).then(r => r.json());
let SESSION = null, FILES = [], CUR = null, MANIFEST = [], FILTER = "all";

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 2200);
}

// ---- yükleme ----
const dz = $("#dropzone"), fi = $("#fileInput");
dz.onclick = () => fi.click();
dz.ondragover = e => { e.preventDefault(); dz.classList.add("drag"); };
dz.ondragleave = () => dz.classList.remove("drag");
dz.ondrop = e => { e.preventDefault(); dz.classList.remove("drag"); upload(e.dataTransfer.files); };
fi.onchange = () => upload(fi.files);

async function upload(fileList) {
  const fd = new FormData();
  [...fileList].forEach(f => fd.append("files", f));
  toast("Çevriliyor…");
  const res = await fetch("/api/upload", { method: "POST", body: fd }).then(r => r.json());
  SESSION = res.session_id; FILES = res.files;
  renderCards();
  $("#batchActions").classList.toggle("hidden", FILES.length === 0);
}

function renderCards() {
  const wrap = $("#cards"); wrap.innerHTML = "";
  FILES.forEach(f => {
    const c = document.createElement("div"); c.className = "card";
    if (f.error) {
      c.innerHTML = `<div class="name">${f.name}</div><div class="err">${f.error}</div>`;
    } else {
      const rev = f.counts.review;
      c.innerHTML = `<span class="kit">${f.kit}</span>
        <div class="name">${f.name}</div>
        <div class="stat ok">✓ ${f.counts.translated} çevrildi</div>
        ${rev ? `<div class="stat warn">⚠ ${rev} gözden geçirilecek</div>` : ""}
        <button data-f="${f.file_id}">Görüntüle / Düzelt</button>`;
      c.querySelector("button").onclick = () => openEditor(f);
    }
    wrap.appendChild(c);
  });
}

$("#saveAllBtn").onclick = async () => {
  const r = await api(`/${SESSION}/save_all`, { method: "POST" });
  toast(`${r.paths.length} dosya kaydedildi`);
};
$("#zipBtn").onclick = () => { location.href = `/api/${SESSION}/download_all`; };

// ---- editör ----
$("#backBtn").onclick = () => {
  $("#editView").classList.add("hidden"); $("#uploadView").classList.remove("hidden");
};
document.querySelectorAll(".filter button").forEach(b =>
  b.onclick = () => {
    FILTER = b.dataset.filter;
    document.querySelectorAll(".filter button").forEach(x => x.classList.remove("active"));
    b.classList.add("active"); renderSegments();
  });

async function openEditor(f) {
  CUR = f;
  $("#uploadView").classList.add("hidden"); $("#editView").classList.remove("hidden");
  $("#editTitle").textContent = f.name;
  MANIFEST = await api(`/${SESSION}/${f.file_id}/manifest`);
  await renderPages();
  renderSegments();
}

async function renderPages() {
  const pages = $("#pages"); pages.innerHTML = "";
  const maxPage = Math.max(...MANIFEST.map(s => s.page), 0);
  for (let n = 0; n <= maxPage; n++) {
    const wrap = document.createElement("div"); wrap.className = "pageWrap";
    const img = new Image();
    img.src = `/api/${SESSION}/${CUR.file_id}/page/${n}.png?t=${Date.now()}`;
    wrap.appendChild(img);
    img.onload = () => overlayBoxes(wrap, img, n);
    pages.appendChild(wrap);
  }
}

function overlayBoxes(wrap, img, n) {
  // PDF noktası 150 dpi'da: ölçek = render genişliği(px) / PDF genişliği(pt)
  const scale = img.clientWidth / (img.naturalWidth / (150 / 72));
  MANIFEST.filter(s => s.page === n).forEach(s => {
    const [x0, y0, x1, y1] = s.bbox;
    const b = document.createElement("div");
    b.className = "box" + (s.needs_review ? " review" : "");
    b.style.left = x0 * scale + "px"; b.style.top = y0 * scale + "px";
    b.style.width = (x1 - x0) * scale + "px"; b.style.height = (y1 - y0) * scale + "px";
    b.dataset.id = s.id;
    b.onclick = () => focusSeg(s.id);
    wrap.appendChild(b);
  });
}

function renderSegments() {
  const list = $("#segList"); list.innerHTML = "";
  MANIFEST.filter(s => FILTER === "all" || s.needs_review).forEach(s => {
    const el = document.createElement("div");
    el.className = "seg" + (s.needs_review ? " review" : "");
    el.dataset.id = s.id;
    el.innerHTML = `<div class="en">${escapeHtml(s.en)}</div>
      <textarea>${escapeHtml(s.tr)}</textarea>
      <div class="acts">
        <button data-scope="dict">Sözlüğe ekle</button>
        <button class="ghost" data-scope="report">Sadece bu rapor</button>
      </div>`;
    const ta = el.querySelector("textarea");
    el.querySelectorAll("button").forEach(btn =>
      btn.onclick = () => saveSeg(s, ta.value, btn.dataset.scope));
    list.appendChild(el);
  });
}

function focusSeg(id) {
  document.querySelectorAll(".seg,.box").forEach(e => e.classList.remove("active"));
  const seg = document.querySelector(`.seg[data-id="${id}"]`);
  document.querySelectorAll(`.box[data-id="${id}"]`).forEach(b => b.classList.add("active"));
  if (seg) { seg.classList.add("active"); seg.scrollIntoView({ block: "center", behavior: "smooth" }); }
}

async function saveSeg(s, tr, scope) {
  const r = await api(`/${SESSION}/${CUR.file_id}/segment/${s.id}`,
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tr, scope }) });
  if (r.conflict) {
    if (confirm(`Bu metin sözlükte zaten "${r.existing}" olarak var. Üzerine yazılsın mı?`)) {
      await api(`/${SESSION}/${CUR.file_id}/segment/${s.id}`,
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tr, scope: "report" }) });
      // sözlüğe zorla yazmak için ayrı çağrı gerekmez; report kapsamı render'ı günceller
    } else return;
  }
  s.tr = tr;
  toast(scope === "dict" ? "Sözlüğe eklendi" : "Bu rapora uygulandı");
  await renderPages();  // override'lı taze render
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
```

- [ ] **Step 5: Frontend'i elle doğrula**

Run:
```bash
cd report_translator && python3 -m uvicorn app:app --port 8731 &
sleep 2 && open http://127.0.0.1:8731
```
Beklenen: arayüz açılır; bir örnek PDF (`reportsamples/en/...`) sürükle-bırak → kart görünür →
"Görüntüle/Düzelt" → sol sayfa önizlemesi + tıklanabilir kutular, sağ segment listesi → bir
TR düzelt → "Sadece bu rapor" → önizleme tazelenir. Sunucuyu durdur: `kill %1`.

- [ ] **Step 6: Commit**

```bash
git add report_translator/web
git commit -m "feat(web): Türkçe statik frontend (yükleme + segment editörü)"
```

---

## Task 8: Başlatıcı betikleri ve README

**Files:**
- Create: `report_translator/baslat.command`
- Create: `report_translator/baslat.bat`
- Modify: `report_translator/README.md`

- [ ] **Step 1: baslat.command (mac) yaz**

`report_translator/baslat.command`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
PORT=8731
./.venv/bin/python -m uvicorn app:app --port $PORT --host 127.0.0.1 &
SRV=$!
sleep 2
open "http://127.0.0.1:$PORT"
echo "Genomer Rapor Çevirici çalışıyor. Kapatmak için bu pencereyi kapatın."
wait $SRV
```

- [ ] **Step 2: baslat.bat (win) yaz**

`report_translator/baslat.bat`:
```bat
@echo off
cd /d "%~dp0"
if not exist ".venv" (
  python -m venv .venv
  .venv\Scripts\pip install -q -r requirements.txt
)
start "" http://127.0.0.1:8731
.venv\Scripts\python -m uvicorn app:app --port 8731 --host 127.0.0.1
```

- [ ] **Step 3: Çalıştırılabilir yap ve elle doğrula (mac)**

Run:
```bash
chmod +x report_translator/baslat.command
```
Beklenen: çift tıklanınca venv kurulur, tarayıcı açılır, arayüz gelir.

- [ ] **Step 4: README'yi güncelle (arayüz bölümü ekle)**

`report_translator/README.md` içine "## Arayüz (yerel uygulama)" başlığı ekle:
```markdown
## Arayüz (yerel uygulama)

`baslat.command` (mac) / `baslat.bat` (win) çift tıklayın. Tarayıcıda Türkçe arayüz açılır:
çoklu PDF sürükle → çevir → segment düzelt → kaydet. Çıktılar `~/Genomer Ceviriler/`
klasörüne `*_TR.pdf` olarak yazılır. Veriler makineden çıkmaz (sunucu yalnız 127.0.0.1).

Segment düzeltme: her metni satır içi düzeltin; "Sözlüğe ekle" kalıcı (tüm raporlara),
"Sadece bu rapor" geçici. Sözlük çakışmasında onay sorulur; `dictionary.json.bak` yedeği alınır.
```

- [ ] **Step 5: Commit**

```bash
git add report_translator/baslat.command report_translator/baslat.bat report_translator/README.md
git commit -m "feat: başlatıcı betikleri (mac/win) + README arayüz bölümü"
```

---

## Task 9: Tüm test paketi + 3 kit görsel doğrulama

**Files:**
- Test: yalnız çalıştırma (yeni dosya yok)

- [ ] **Step 1: Tüm testleri çalıştır**

Run: `cd report_translator && python3 -m pytest -v`
Expected: tüm testler PASS.

- [ ] **Step 2: 3 kiti uçtan uca render edip gözle doğrula**

Run:
```bash
cd report_translator && python3 - <<'PY'
import engine, dictionary, fitz, os
kits, common, pt, _ = dictionary.load()
for name in ["Femobiome_II report_eubiosis_eng.pdf", "Androbiome.pdf", "Enterobiome Kids.pdf"]:
    p = os.path.join("..", "reportsamples", "en", name)
    doc = fitz.open(p); kit = dictionary.detect_kit(doc)
    out = engine.translate_document_bytes(p, kits[kit], pt, {})
    fitz.open(stream=out, filetype="pdf")[0].get_pixmap(dpi=130).save("_chk_%s.png" % kit)
    print(kit, "ok")
PY
```
Beklenen: `_chk_femobiome_ii.png`, `_chk_androbiome.png`, `_chk_enterobiome_kids.png` üretilir.
Her birini aç; düzen korunmuş, Türkçe metin doğru, "Yaş Kuruluş" gibi birleşme yok, conclusion
paragrafı düzgün sarılmış olmalı. Sorun varsa `_is_flowing_paragraph` eşiklerini (0.6 / 80)
ayarla ve test_engine'i tekrar çalıştır.

- [ ] **Step 3: Geçici görselleri temizle ve commit**

```bash
cd report_translator && rm -f _chk_*.png
git add -A
git commit -m "test: tam paket yeşil + 3 kit görsel doğrulama"
```

---

## Task 10 (v2, opsiyonel): PyInstaller paketleme

**Files:**
- Create: `report_translator/build_app.md` (paketleme notları)

- [ ] **Step 1: Paketleme notlarını yaz**

`report_translator/build_app.md`:
```markdown
# Native paketleme (PyInstaller)

```bash
cd report_translator
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --onefile --name "GenomerRaporCevirici" \
  --add-data "web:web" --add-data "fonts:fonts" --add-data "dictionary.json:." \
  --collect-all fastapi --collect-all uvicorn --collect-all pymupdf \
  launcher.py
```

`launcher.py` (uvicorn'u programatik başlatır + tarayıcı açar):
```python
import uvicorn, webbrowser, threading, app
def open_browser(): webbrowser.open("http://127.0.0.1:8731")
threading.Timer(1.5, open_browser).start()
uvicorn.run(app.app, host="127.0.0.1", port=8731)
```

Çıktı `dist/GenomerRaporCevirici` tek dosyadır; Python gerektirmez. macOS imzalama/notarizasyon
ve Windows kod imzalama dağıtım için ayrıca yapılmalı.
```

- [ ] **Step 2: Commit**

```bash
git add report_translator/build_app.md
git commit -m "docs: PyInstaller native paketleme notları (v2)"
```

---

## Self-review notları (planı yazanın kontrolü)

- **Spec kapsamı:** çoklu PDF (Task 6 upload + Task 7 cards) ✓; segment düzeltme (Task 7 + app segment) ✓; iki kapsam dict/report (app edit_segment + add_entry) ✓; disk kaydı (app save + Task 8) ✓; native paketleme (Task 10) ✓; Türkçe UI (Task 7) ✓; hata yönetimi (upload geçersiz PDF, kit override, çakışma) ✓.
- **Sıra bağımlılığı:** engine.translate_segments testleri dictionary'ye bağlı → **Task 1 → Task 5 → Task 2 → Task 3 → Task 4 → Task 6 → Task 7 → Task 8 → Task 9** sırası izlenmeli (Task 2 ve Task 5 içinde not düşüldü).
- **Tip tutarlılığı:** `AnnotatedSegment.source` değerleri (`dict-exact/dict-partial/passthrough/unknown/override`) engine, app, frontend boyunca tutarlı; `_counts` ve manifest aynı alanları kullanır.
- **Bilinen sınır:** segment düzeltmede "Sözlüğe ekle" çakışma onayı sonrası şu an yalnız rapor-kapsamı render'ı günceller; kalıcı yazma için kullanıcı tekrar "Sözlüğe ekle"ye basar (basitlik için kabul; gerekirse forced-overwrite ucu eklenebilir).
