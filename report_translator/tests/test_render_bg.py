import os
import re
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


def test_sample_bg_scale_factor():
    # scale=2.0: rect (10,10,30,15) pikselde (20,20,60,30)'a eşlenir; marj beyaz
    pm = _solid_pm(200, 100, (255, 255, 255))
    bg = engine._sample_bg(pm, fitz.Rect(10, 10, 30, 15), 2.0)
    assert bg is not None
    assert all(abs(c - 1.0) < 0.02 for c in bg)


def test_sample_bg_edge_does_not_crash():
    # rect sayfa kenarında: sol/üst marj sınır dışı -> kalan noktalardan örnekle, çökme
    pm = _solid_pm(100, 50, (255, 255, 255))
    bg = engine._sample_bg(pm, fitz.Rect(0, 0, 30, 20), 1.0)
    assert bg is None or all(abs(c - 1.0) < 0.02 for c in bg)


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
    red = total = 0
    for yy in range(int(red_rect.y0 * sc), int(red_rect.y1 * sc) + 1):
        for xx in range(int(red_rect.x0 * sc), int(red_rect.x1 * sc) + 1):
            if 0 <= xx < pm.width and 0 <= yy < pm.height:
                total += 1
                px = pm.pixel(xx, yy)
                if px[0] > 180 and px[1] < 80 and px[2] < 80:
                    red += 1
    # Solid kırmızı blok (vektör mürekkebi) kapatıldı: çoğunluk artık zemin.
    # Kalan az kırmızı yalnız yeniden-yazılan TR harf izleri olabilir (_sample_fg
    # mürekkep rengini -kırmızı- örnekleyip TR'yi o renkle yazar; beklenen davranış).
    assert red < 0.25 * total, f"kırmızı blok kapatılmadı: {red}/{total}"
    assert "Merhaba" in page.get_text()


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

    # 2) render çökmeden tamamlanmalı ve sayfa sayısı korunmalı
    assert doc.page_count == 2


def test_sub_glyphs_replaces_missing_bullet():
    # ⯀ (U+2BC0, Arial'da yok) -> ■ (U+25A0, dolu kare, Arial'da var)
    assert engine._sub_glyphs("⯀ Test") == "■ Test"
    assert engine._sub_glyphs("normal metin") == "normal metin"


def test_bullet_breaks_puts_each_bullet_on_new_line():
    t = "■ Birinci madde. ■ İkinci madde."
    assert engine._bullet_breaks(t) == "■ Birinci madde.\n■ İkinci madde."


def test_bullet_breaks_no_bullet_unchanged():
    assert engine._bullet_breaks("düz metin") == "düz metin"
