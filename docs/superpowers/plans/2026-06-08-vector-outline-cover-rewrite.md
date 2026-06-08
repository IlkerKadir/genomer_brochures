# Vektör-Outline "Kapat + Yeniden Yaz" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerçek lab (vektör-outline) raporlarını temiz çevirmek için, redaksiyonu zemin rengiyle doldurarak görünen İngilizce vektör-outline'ı örtmek.

**Architecture:** `engine.py`'ye saf `_sample_bg` yardımcı fonksiyonu eklenir (segment dikdörtgeninin kenar marjından baskın zemin rengini örnekler). `_render_page_items` bu rengi kullanarak `add_redact_annot(rect, fill=bg)` yapar; düz-olmayan zeminde `fill=None`'a düşer (güvenli). Türkçe yazma kodu değişmez.

**Tech Stack:** Python 3, PyMuPDF (fitz), pytest.

**Spec:** `docs/superpowers/specs/2026-06-08-vector-outline-cover-rewrite-design.md`

---

## Dosya Yapısı

- **Modify:** `report_translator/engine.py`
  - Ekle: `_sample_bg(pixmap, rect, scale, tol=12, min_frac=0.7)` saf fonksiyon (mevcut `_render_page_items`'in hemen üstüne, ~satır 235).
  - Değiştir: `_render_page_items(page, items, font_cache)` (mevcut satır 236-275) — redaksiyon dolgusunu zemin rengiyle yap.
- **Create:** `report_translator/tests/test_render_bg.py` — `_sample_bg` birim testleri + sentetik-PDF render testi + (varsa) gerçek-örnek entegrasyon testi.

Mevcut `import` satırları yeterli (`os`, `re`, `sys`, `fitz`, `dataclass`). `_sample_bg` içinde `collections.Counter` kullanılacağından dosya başına `from collections import Counter` eklenir.

---

## Task 1: `_sample_bg` zemin örnekleme fonksiyonu

**Files:**
- Modify: `report_translator/engine.py` (import ekle ~satır 4-9; fonksiyon ekle ~satır 235)
- Test: `report_translator/tests/test_render_bg.py`

- [ ] **Step 1: Failing test'leri yaz**

`report_translator/tests/test_render_bg.py` oluştur:

```python
import os
import sys
import fitz
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import engine


def _solid_pm(w, h, color):
    """w x h düz renkli RGB pixmap. color = (r,g,b) 0-255 int."""
    pm = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, h), False)
    pm.set_rect(pm.irect, color)
    return pm


def test_sample_bg_white():
    pm = _solid_pm(100, 50, (255, 255, 255))
    bg = engine._sample_bg(pm, fitz.Rect(20, 20, 60, 30), 1.0)
    assert bg is not None
    assert all(abs(c - 1.0) < 0.02 for c in bg)


def test_sample_bg_gray():
    pm = _solid_pm(100, 50, (240, 240, 240))
    bg = engine._sample_bg(pm, fitz.Rect(20, 20, 60, 30), 1.0)
    assert bg is not None
    assert all(abs(c - 240 / 255) < 0.02 for c in bg)


def test_sample_bg_multicolor_returns_none():
    # sol yarı beyaz, sağ yarı mavi; rect tam sınırda -> marj çok-renkli
    pm = _solid_pm(100, 50, (255, 255, 255))
    pm.set_rect(fitz.IRect(50, 0, 100, 50), (0, 0, 255))
    bg = engine._sample_bg(pm, fitz.Rect(40, 20, 60, 30), 1.0)
    assert bg is None


def test_sample_bg_edge_does_not_crash():
    # rect sayfa kenarında: sol/üst marj sınır dışı -> kalan noktalardan örnekle, çökme
    pm = _solid_pm(100, 50, (255, 255, 255))
    bg = engine._sample_bg(pm, fitz.Rect(0, 0, 30, 20), 1.0)
    assert bg is None or all(abs(c - 1.0) < 0.02 for c in bg)
```

- [ ] **Step 2: Test'in başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_render_bg.py -v`
Expected: FAIL — `AttributeError: module 'engine' has no attribute '_sample_bg'`

- [ ] **Step 3: `Counter` import'unu ekle**

`report_translator/engine.py` başındaki import bloğunu (satır 4-9) şu hale getir:

```python
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
import fitz  # PyMuPDF
import aiconfig
```

- [ ] **Step 4: `_sample_bg`'yi ekle**

`report_translator/engine.py` içinde `def _render_page_items(` satırının **hemen üstüne** ekle:

```python
def _sample_bg(pixmap, rect, scale, tol=12, min_frac=0.7):
    """Segment dikdörtgeninin kenar marjından (harf dışı dolgu) baskın zemin rengini örnekle.

    Halka yeterince tek-renk ise (r, g, b) 0-1 float tuple; çok-renkli/örneklenemezse None.
    None dönerse çağıran fill=None'a düşer (vektör İngilizce kalır, yama oluşmaz)."""
    x0 = int(rect.x0 * scale); y0 = int(rect.y0 * scale)
    x1 = int(rect.x1 * scale); y1 = int(rect.y1 * scale)
    cnt = Counter()
    for d in (1, 2):
        for xx in range(x0, x1 + 1):
            for yy in (y0 - d, y1 + d):           # üst ve alt marj
                if 0 <= xx < pixmap.width and 0 <= yy < pixmap.height:
                    cnt[pixmap.pixel(xx, yy)] += 1
        for yy in range(y0, y1 + 1):
            for xx in (x0 - d, x1 + d):           # sol ve sağ marj
                if 0 <= xx < pixmap.width and 0 <= yy < pixmap.height:
                    cnt[pixmap.pixel(xx, yy)] += 1
    if not cnt:
        return None
    (col, _), = cnt.most_common(1)
    near = sum(v for c, v in cnt.items()
               if all(abs(a - b) <= tol for a, b in zip(c[:3], col[:3])))   # alfa kanalını hariç tut
    if near / sum(cnt.values()) < min_frac:
        return None
    return (col[0] / 255.0, col[1] / 255.0, col[2] / 255.0)
```

- [ ] **Step 5: Test'in geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_render_bg.py -v`
Expected: 4 test PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/engine.py report_translator/tests/test_render_bg.py
git commit -m "feat(engine): _sample_bg — segment zemin rengini kenar marjından örnekle"
```

---

## Task 2: `_render_page_items`'i dolgulu redaksiyona geçir

**Files:**
- Modify: `report_translator/engine.py` (`_render_page_items`, mevcut satır 236-245 — redaksiyon bloğu)
- Test: `report_translator/tests/test_render_bg.py` (sentetik render testi eklenir)

- [ ] **Step 1: Failing test'i ekle**

`report_translator/tests/test_render_bg.py` sonuna ekle:

```python
def test_fill_covers_vector_ink():
    """Metin-dışı vektör mürekkebi (kırmızı blok) redaksiyon dolgusuyla örtülmeli."""
    doc = fitz.open()
    page = doc.new_page(width=300, height=120)
    # 1) gerçek metin katmanı koy (extract bunu bulur, redaksiyon siler)
    page.insert_text((50, 66), "Hello", fontsize=12, color=(0, 0, 0))
    # 2) segmentin TAM dikdörtgeni üzerine ayırt edici kırmızı blok çiz
    #    ("vektör-outline İngilizce" simülasyonu; metin bbox'u ile birebir hizalı)
    segs = engine.extract_segments(doc)
    assert segs, "metin segmenti bulunamadı"
    red_rect = fitz.Rect(segs[0].rects[0])
    page.draw_rect(red_rect, color=None, fill=(1, 0, 0))

    ann = engine.translate_segments(segs, {"Hello": "Merhaba"}, [], {})
    items = [a for a in engine._changed_items(ann) if a.seg.page == 0]
    assert items, "çevrilecek segment bulunamadı"
    engine._render_page_items(page, items, {})

    pm = page.get_pixmap(dpi=150)
    sc = 150 / 72
    red = 0
    for yy in range(int(red_rect.y0 * sc), int(red_rect.y1 * sc) + 1):
        for xx in range(int(red_rect.x0 * sc), int(red_rect.x1 * sc) + 1):
            if 0 <= xx < pm.width and 0 <= yy < pm.height:
                px = pm.pixel(xx, yy)
                if px[0] > 180 and px[1] < 80 and px[2] < 80:
                    red += 1
    assert red == 0, f"kırmızı vektör mürekkebi örtülmedi: {red} piksel kaldı"
```

- [ ] **Step 2: Test'in başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_render_bg.py::test_fill_covers_vector_ink -v`
Expected: FAIL — mevcut `fill=None` kırmızıyı örtmez; `red > 0`.

- [ ] **Step 3: `_render_page_items`'in redaksiyon bloğunu değiştir**

`report_translator/engine.py` içinde mevcut redaksiyon bloğunu:

```python
    if not items:
        return
    for a in items:
        for r in a.seg.rects:
            page.add_redact_annot(fitz.Rect(r), fill=None)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
```

şununla değiştir:

```python
    if not items:
        return
    try:
        pm = page.get_pixmap(dpi=150)
        scale = 150 / 72.0
    except Exception:                      # pragma: no cover - beklenmez
        pm = None
        scale = 1.0
    for a in items:
        for r in a.seg.rects:
            rect = fitz.Rect(r)
            bg = _sample_bg(pm, rect, scale) if pm is not None else None
            if bg is not None:
                # vektör-outline kenarları metin bbox'undan taşabilir -> ~1px genişlet
                page.add_redact_annot(rect + (-1, -1, 1, 1), fill=bg)
            else:
                page.add_redact_annot(rect, fill=None)   # güvenli: İngilizce kalır
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
```

`_render_page_items`'in geri kalanı (Türkçe `insert_text`/`insert_textbox` döngüsü) **değişmez.**

- [ ] **Step 4: Test'in geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_render_bg.py -v`
Expected: 5 test PASS (4 + `test_fill_covers_vector_ink`)

- [ ] **Step 5: Tüm paketin geçtiğini doğrula (gerileme)**

Run: `cd report_translator && python3 -m pytest -q`
Expected: `83 passed` (mevcut 78 + yeni 5). Hiçbir mevcut test bozulmamalı.

- [ ] **Step 6: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/engine.py report_translator/tests/test_render_bg.py
git commit -m "feat(engine): redaksiyonu zemin rengiyle doldur (vektör-outline İngilizceyi ört)"
```

---

## Task 3: Gerçek lab örneğiyle entegrasyon doğrulaması

**Files:**
- Test: `report_translator/tests/test_render_bg.py` (gerçek-örnek testi eklenir; örnek yoksa skip)

**Bağlam:** `report_translator/new_samples/split/rapor_1.pdf` gerçek lab çıktısıdır ve `.gitignore`'dadır (hasta verisi). Bu test, dosya **mevcutsa** çalışır, yoksa `skip`. Femobiome kit tablosu `dictionary.load()` ile yüklenir; femo'da daha önce çakışan bir gövde etiketi (`Control parameters`) render sonrası örtülmüş olmalı.

- [ ] **Step 1: Entegrasyon testini ekle**

`report_translator/tests/test_render_bg.py` sonuna ekle:

```python
import re

_SAMPLE = os.path.join(os.path.dirname(__file__), "..", "new_samples", "split", "rapor_1.pdf")


@pytest.mark.skipif(not os.path.exists(_SAMPLE), reason="gerçek lab örneği yok (gitignore)")
def test_real_lab_body_label_translated_and_covered():
    import dictionary
    kits, _c, pt, raw = dictionary.load()
    tpl = dictionary.compile_templates(raw, "femobiome_ii")
    out = engine.translate_document_bytes(_SAMPLE, kits["femobiome_ii"], pt, {}, tpl, None)
    doc = fitz.open(stream=out, filetype="pdf")
    p0 = doc[0]

    # 1) metin katmanında İngilizce 'Control parameters' kalmamalı, TR gelmiş olmalı
    txt = p0.get_text()
    assert "Control parameters" not in txt
    assert "Kontrol parametreleri" in re.sub(r"\s+", " ", txt.replace("\xa0", " "))

    # 2) eski 'Control parameters' bölgesinde görünen (vektör) İngilizce örtülmüş olmalı:
    #    o satırda koyu-metin yoğunluğu, kapatma sonrası düşük olmalı (yalnız TR yazısı kalır).
    #    Burada sadece render'ın çökmeden tamamlandığını ve sayfa sayısını doğrularız.
    assert doc.page_count == 2
```

- [ ] **Step 2: Test'i çalıştır (örnek mevcutsa geçer, değilse skip)**

Run: `cd report_translator && python3 -m pytest tests/test_render_bg.py::test_real_lab_body_label_translated_and_covered -v`
Expected: PASS (örnek varsa) veya SKIPPED (yoksa). FAIL olmamalı.

- [ ] **Step 3: Görsel doğrulama (elle)**

Run:
```bash
cd report_translator && python3 - <<'PY'
import dictionary, engine, fitz
kits,c,pt,raw=dictionary.load()
tpl=dictionary.compile_templates(raw,"femobiome_ii")
for n in (1,2,3,4):
    f=f"new_samples/split/rapor_{n}.pdf"
    import os
    if not os.path.exists(f): continue
    out=engine.translate_document_bytes(f,kits["femobiome_ii"],pt,{},tpl,None)
    d=fitz.open(stream=out,filetype="pdf")
    for pi in range(d.page_count):
        d[pi].get_pixmap(dpi=150).save(f"/tmp/fixed_r{n}_p{pi}.png")
print("PNG'ler /tmp/fixed_r*_p*.png")
PY
```
Expected: `/tmp/fixed_r*_p*.png` üretilir. Görsel kontrol: gövdede İngilizce+Türkçe çakışması YOK, gri başlık satırlarında beyaz yama YOK, banner temiz.

- [ ] **Step 4: Tüm paket + commit**

Run: `cd report_translator && python3 -m pytest -q`
Expected: `84 passed` (veya örnek yoksa `83 passed, 1 skipped`).

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/tests/test_render_bg.py
git commit -m "test(engine): gerçek lab örneğiyle kapat+yeniden-yaz entegrasyon testi"
```

---

## Task 4: Görünmez (beyaz) metin-katmanı rengini gerçek mürekkep rengiyle değiştir

**Bağlam:** Görsel doğrulamada keşfedildi — vektör-outline etiketlerin görünmez metin katmanı **beyaz** (`s.color == (1,1,1)`). Kapatma sonrası `color=s.color` ile yazınca beyaz-üstüne-beyaz → görünmez. Çözüm: kapatma yapıldığında yeniden-yazma rengini orijinal pixmap'ten örneklenen gerçek mürekkep rengiyle (`_sample_fg`) belirle. Bu, "Kontrol parametreleri" morunu ve siyah veri etiketlerini doğru korur; sonuç kutusu teal'i de korunur.

**Files:**
- Modify: `report_translator/engine.py` (ekle: `_sample_fg`; değiştir: `_render_page_items` — renk belirleme + yeniden-yazmada `col` kullan)
- Test: `report_translator/tests/test_render_bg.py` (3 test ekle)

- [ ] **Step 1: Failing test'leri ekle** — `report_translator/tests/test_render_bg.py` sonuna:

```python
def test_sample_fg_returns_ink_over_background():
    # beyaz zemin + küçük siyah mürekkep bloğu -> baskın ön-plan siyah
    pm = _solid_pm(100, 50, (255, 255, 255))
    pm.set_rect(fitz.IRect(25, 22, 45, 28), (0, 0, 0))
    fg = engine._sample_fg(pm, fitz.Rect(20, 20, 60, 30), 1.0, (1.0, 1.0, 1.0))
    assert all(c < 0.1 for c in fg)


def test_sample_fg_no_ink_returns_black():
    # tamamen zemin (bg-dışı piksel yok) -> siyah fallback
    pm = _solid_pm(100, 50, (255, 255, 255))
    fg = engine._sample_fg(pm, fitz.Rect(20, 20, 60, 30), 1.0, (1.0, 1.0, 1.0))
    assert fg == (0.0, 0.0, 0.0)


def test_reinsert_uses_ink_color_not_invisible_textlayer():
    """Görünmez (beyaz) metin-katmanı + siyah vektör mürekkebi: TR görünür yazılmalı."""
    doc = fitz.open()
    page = doc.new_page(width=300, height=120)
    # beyaz (görünmez) metin katmanı
    page.insert_text((50, 66), "Hello", fontsize=12, color=(1, 1, 1))
    segs = engine.extract_segments(doc)
    assert segs
    rect = fitz.Rect(segs[0].rects[0])
    # görünen SİYAH vektör mürekkebi (blok)
    page.draw_rect(rect, color=None, fill=(0, 0, 0))

    ann = engine.translate_segments(segs, {"Hello": "Merhaba"}, [], {})
    items = [a for a in engine._changed_items(ann) if a.seg.page == 0]
    assert items
    engine._render_page_items(page, items, {})

    pm = page.get_pixmap(dpi=150)
    sc = 150 / 72
    dark = 0
    for yy in range(int(rect.y0 * sc), int(rect.y1 * sc) + 1):
        for xx in range(int(rect.x0 * sc), int(rect.x1 * sc) + 1):
            if 0 <= xx < pm.width and 0 <= yy < pm.height:
                px = pm.pixel(xx, yy)
                if px[0] < 80 and px[1] < 80 and px[2] < 80:
                    dark += 1
    assert dark > 0, "TR görünür mürekkep rengiyle yazılmadı (beyaz/görünmez kaldı)"
    assert "Merhaba" in page.get_text()
```

- [ ] **Step 2: Test'in başarısız olduğunu doğrula**

Run: `cd /Users/ilkerkadirozturk/Documents/genomer_brochures/report_translator && python3 -m pytest tests/test_render_bg.py -v`
Expected: yeni 3 testten en az `test_sample_fg_*` ikisi FAIL (`_sample_fg` yok → AttributeError); `test_reinsert_uses_ink_color...` da FAIL (beyaz yazılıyor → `dark == 0`).

- [ ] **Step 3: `_sample_fg`'yi ekle** — `engine.py` içinde `def _sample_bg(`'nin hemen ALTINA (yani `_render_page_items`'in üstüne) ekle:

```python
def _sample_fg(pixmap, rect, scale, bg, tol=24):
    """rect içindeki baskın ön-plan (mürekkep) rengini örnekle: bg'den farklı baskın renk.

    Görünmez (beyaz) metin-katmanı rengi yerine gerçek mürekkep rengini verir.
    bg-dışı piksel yoksa (0,0,0) siyah döndürür (asla None)."""
    x0 = int(rect.x0 * scale); y0 = int(rect.y0 * scale)
    x1 = int(rect.x1 * scale); y1 = int(rect.y1 * scale)
    bg255 = tuple(int(round(v * 255)) for v in bg)
    cnt = Counter()
    for yy in range(y0, y1 + 1):
        for xx in range(x0, x1 + 1):
            if 0 <= xx < pixmap.width and 0 <= yy < pixmap.height:
                px = pixmap.pixel(xx, yy)
                if not all(abs(a - b) <= tol for a, b in zip(px[:3], bg255[:3])):
                    cnt[px] += 1
    if not cnt:
        return (0.0, 0.0, 0.0)
    (col, _), = cnt.most_common(1)
    return (col[0] / 255.0, col[1] / 255.0, col[2] / 255.0)
```

- [ ] **Step 4: `_render_page_items`'i renk-belirlemeyle güncelle.** Mevcut fonksiyonun TAMAMINI şu sürümle değiştir:

```python
def _render_page_items(page, items, font_cache):
    """Tek bir sayfadaki değişen segmentleri yerinde render et (redaksiyon + geri yazma)."""
    if not items:
        return
    try:
        pm = page.get_pixmap(dpi=150)
        scale = 150 / 72.0
    except Exception:                      # pragma: no cover - beklenmez
        pm = None
        scale = 1.0
    colors = {}                            # id(a) -> yeniden-yazma rengi
    for a in items:
        first_bg = None
        for r in a.seg.rects:
            rect = fitz.Rect(r)
            bg = _sample_bg(pm, rect, scale) if pm is not None else None
            if bg is not None:
                if first_bg is None:
                    first_bg = bg
                # vektör-outline kenarları metin bbox'undan taşabilir -> ~1px genişlet
                page.add_redact_annot(rect + (-1, -1, 1, 1), fill=bg)
            else:
                page.add_redact_annot(rect, fill=None)   # güvenli: İngilizce kalır
        # kapatma yapıldıysa görünmez (beyaz) metin-katmanı yerine gerçek mürekkep rengi
        if first_bg is not None and pm is not None:
            colors[id(a)] = _sample_fg(pm, fitz.Rect(a.seg.rects[0]), scale, first_bg)
        else:
            colors[id(a)] = a.seg.color
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
    for a in items:
        s = a.seg
        col = colors[id(a)]
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
                             fontfile=fontfile, fontsize=s.size, color=col)
        else:
            box = fitz.Rect(s.bbox)
            left = box.x0 + indent
            fs = s.size
            fitted = False
            while fs > 4.5:
                pad = fitz.Rect(left, box.y0 - 1, box.x1 + 2, box.y1 + 4 * s.size)
                rc = page.insert_textbox(pad, text, fontname=fontname, fontfile=fontfile,
                                         fontsize=fs, color=col, lineheight=1.15,
                                         align=fitz.TEXT_ALIGN_LEFT)
                if rc >= 0:
                    fitted = True
                    break
                fs -= 0.25
            if not fitted:
                sys.stderr.write("UYARI: segment sığmadı, atlandı: %r\n" % text)
```

Değişiklikler: (a) `colors` sözlüğü + her segment için `first_bg` izleme + `_sample_fg` çağrısı; (b) yeniden-yazma döngüsünde `col = colors[id(a)]` ve iki `color=s.color` → `color=col`. Geri kalan mantık aynı.

- [ ] **Step 5: Test'lerin geçtiğini doğrula**

Run: `cd /Users/ilkerkadirozturk/Documents/genomer_brochures/report_translator && python3 -m pytest tests/test_render_bg.py -v`
Expected: test_render_bg.py'deki tüm testler PASS (önceki + 3 yeni).

- [ ] **Step 6: Tüm paket (gerileme)**

Run: `cd /Users/ilkerkadirozturk/Documents/genomer_brochures/report_translator && python3 -m pytest -q`
Expected: `88 passed` (gerçek örnek varsa) veya `87 passed, 1 skipped` (yoksa). Mevcut testlerden hiçbiri bozulmamalı.

- [ ] **Step 7: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/engine.py report_translator/tests/test_render_bg.py
git commit -m "feat(engine): kapatmada gerçek mürekkep rengini örnekle (görünmez beyaz metin-katmanı düzeltmesi)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Self-Review Notları

- **Spec kapsamı:** `_sample_bg` (örnekleme + uniformity guard) → Task 1. Dolgulu redaksiyon + 1px genişletme + fallback → Task 2. Evrensel kapsam + 78-test gerilemesi → Task 2 Step 5. Gerçek örnek + görsel → Task 3. Hepsi karşılandı.
- **Performans:** sayfa başına +1 pixmap (`get_pixmap(dpi=150)`) — Task 2'de eklendi, spec ile uyumlu.
- **Hata durumu:** pixmap render başarısız → `fill=None` (Task 2 try/except); marj sınır-dışı → atlanır (Task 1, sınır kontrolü); çok-renkli → None (Task 1).
- **Tip tutarlılığı:** `_sample_bg` her yerde `(r,g,b)` 0-1 float veya `None` döndürür; `add_redact_annot(..., fill=bg)` bu formatı bekler. `scale = 150/72.0`.
