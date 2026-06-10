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
    # 2) segmentin dikdörtgeni üzerine glif-boyutlu kırmızı dolgular çiz
    #    ("vektör-outline İngilizce" simülasyonu: eğriye-çevrilmiş harfler = çok sayıda küçük dolgu;
    #     ≥5 glif-boyutlu dolgu sayfayı vektör-outline olarak işaretler -> kapatma devreye girer)
    segs = engine.extract_segments(doc)
    assert segs, "metin segmenti bulunamadı"
    red_rect = fitz.Rect(segs[0].rects[0])
    n = 6
    step = red_rect.width / n
    for i in range(n):                          # 6 glif-boyutlu kırmızı dolgu (harf taklidi)
        gx = red_rect.x0 + i * step
        page.draw_rect(fitz.Rect(gx, red_rect.y0, gx + step * 0.9, red_rect.y1),
                       color=None, fill=(1, 0, 0))

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


def test_fontname_for_avoids_source_pdf_name_collision():
    # Gerçek-lab PDF'leri fontlarını F0/F1/... olarak adlandırır. Üretilen ad bunlarla
    # ÇAKIŞMAMALI; yoksa insert_textbox kaynak fontu (Türkçe glif'siz) yeniden kullanır.
    cache = {}
    names = [engine._fontname_for("Carlito-Regular.ttf", cache),
             engine._fontname_for("Arial-Regular.ttf", cache),
             engine._fontname_for("Carlito-Regular.ttf", cache)]  # tekrar -> aynı
    assert names[0] == names[2]                       # önbellek tutarlı
    assert names[0] != names[1]                       # farklı font farklı ad
    for n in names:
        assert not re.fullmatch(r"F\d+", n), f"çakışmaya açık ad: {n}"
        for clash in ("F0", "F1", "F2", "F3", "C0", "T1", "TT0", "C2_0"):
            assert n != clash


def _ascii_only_font(tmp_path):
    """Türkçe glif'i OLMAYAN bir kaynak font üret (gerçek-lab subset fontunu taklit).
    Mevcutsa fonttools ile Arial'ı ASCII'ye indir; yoksa testi atla."""
    fonttools = pytest.importorskip("fontTools")
    from fontTools.subset import Subsetter, Options
    from fontTools.ttLib import TTFont
    f = TTFont(os.path.join(engine.FONT_DIR, "Arial-Regular.ttf"))
    opt = Options()
    opt.glyph_names = True
    ss = Subsetter(options=opt)
    ss.populate(text="".join(chr(c) for c in range(32, 127)))   # yalnız ASCII
    ss.subset(f)
    out = str(tmp_path / "ascii_only.ttf")
    f.save(out)
    return out


def test_multiline_turkish_survives_source_font_collision(tmp_path):
    """Kaynak sayfada 'F0' adlı (Türkçe glif'siz) bir font varken Türkçe çok-satırlı segment
    render edilince ı/ç/ş/ğ düşmemeli. Çakışan kısa ad ('F0') insert_textbox'ı kaynak
    glif'siz fontu yeniden kullanmaya iter → mojibake; bu test o regresyonu yakalar."""
    src = _ascii_only_font(tmp_path)               # Türkçe glif YOK
    doc = fitz.open()
    page = doc.new_page(width=360, height=200)
    # kaynak PDF'i taklit: sayfaya 'F0' adlı glif'siz font + İngilizce metin yerleştir
    page.insert_text((20, 30), "English only text", fontname="F0",
                     fontfile=src, fontsize=10)
    page.insert_text((20, 90), "placeholder line", fontsize=10, color=(0, 0, 0))
    segs = engine.extract_segments(doc)
    seg = [s for s in segs if "placeholder" in s.en][0]
    seg.single_line = False                       # çok-satırlı insert_textbox yolunu zorla
    seg.bbox = [20, 80, 340, 100]
    ann = engine.translate_segments(
        segs, {"placeholder line": "oranı aralık içindedir Fırsatçı çeşitliliği"}, [], {})
    items = [a for a in ann if a.tr != a.en and a.seg.page == 0]
    assert items, "çevrilecek segment yok"
    engine._render_page_items(page, items, {})
    txt = page.get_text()
    assert "oranı" in txt and "içindedir" in txt and "çeşitliliği" in txt, repr(txt)


def test_page_graphics_detects_vector_outline():
    # glif-boyutlu dolgu yok -> normal metin (vektör-outline DEĞİL)
    doc = fitz.open()
    p1 = doc.new_page(width=200, height=60)
    p1.draw_rect(fitz.Rect(0, 20, 200, 35), color=None, fill=(0.89, 0.89, 0.89))  # büyük şerit
    p1.insert_text((10, 32), "Normal text row", fontsize=10)
    _strokes, vec = engine._page_graphics(p1)
    assert vec is False
    # ≥5 glif-boyutlu dolgu -> vektör-outline
    p2 = doc.new_page(width=200, height=60)
    for i in range(6):
        p2.draw_rect(fitz.Rect(10 + i * 12, 20, 18 + i * 12, 34), color=None, fill=(0, 0, 0))
    _s2, vec2 = engine._page_graphics(p2)
    assert vec2 is True


def test_normal_text_row_keeps_black_ink_no_coverfill():
    """Normal-metin sayfasında (gri şeritli satır) çeviri SİYAH mürekkeple yazılmalı;
    kapatma-dolgusu/ink-örnekleme devreye girip metni soluk (beyaz/gri) yapMAMALI."""
    import numpy as np
    doc = fitz.open()
    page = doc.new_page(width=300, height=70)
    page.draw_rect(fitz.Rect(0, 28, 300, 44), color=None, fill=(0.89, 0.89, 0.89))  # gri zebra şeridi
    page.insert_text((20, 40), "Label", fontsize=10, color=(0, 0, 0))
    segs = engine.extract_segments(doc)
    ann = engine.translate_segments(segs, {"Label": "Etiket"}, [], {})
    items = [a for a in ann if a.tr != a.en and a.seg.page == 0]
    engine._render_page_items(page, items, {})
    assert "Etiket" in page.get_text()
    pm = page.get_pixmap(dpi=150)
    arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
    sc = 150 / 72.0
    band = arr[int(31 * sc):int(43 * sc), int(20 * sc):int(60 * sc)]
    dark = int((band < 90).all(axis=2).sum())
    assert dark > 40, f"çeviri siyah yazılmadı (soluk mürekkep?), koyu px={dark}"


def test_grid_line_survives_cover_fill():
    """Kapatma-dolgusu (fill=bg) bir ızgara çizgisini örttüğünde, çizgi render sonunda
    orijinal renk/kalınlıkla geri çizilmeli (gerçek-lab tablolarında kırık/beyaz-taşma onarımı)."""
    import numpy as np
    doc = fitz.open()
    page = doc.new_page(width=160, height=80)
    # yatay siyah ızgara çizgisi (x10-150)
    page.draw_line(fitz.Point(10, 40), fitz.Point(150, 40), color=(0, 0, 0), width=1)
    # GENİŞ İngilizce metin -> geniş kapatma-dolgusu çizgiyi örter; KISA çeviri ("Et") sola yazılır
    page.insert_text((20, 42), "Wide English Label Here", fontsize=9, color=(0, 0, 0))
    segs = engine.extract_segments(doc)
    ann = engine.translate_segments(segs, {"Wide English Label Here": "Et"}, [], {})
    items = [a for a in ann if a.tr != a.en and a.seg.page == 0]
    assert items
    engine._render_page_items(page, items, {})
    pm = page.get_pixmap(dpi=150)
    arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
    sc = 150 / 72.0
    # dolgunun örttüğü ama metin yazılmayan bölge (x70-110): geri-çizim olmazsa çizgi silinir
    yb = int(40 * sc)
    band = arr[yb - 1:yb + 2, int(70 * sc):int(110 * sc)]
    dark = int((band < 100).all(axis=2).sum())
    assert dark > 40, f"ızgara çizgisi geri çizilmedi (koyu px={dark})"


def test_sub_glyphs_replaces_missing_bullet():
    # ⯀ (U+2BC0, Arial'da yok) -> ■ (U+25A0, dolu kare, Arial'da var)
    assert engine._sub_glyphs("⯀ Test") == "■ Test"
    assert engine._sub_glyphs("normal metin") == "normal metin"


def test_bullet_breaks_puts_each_bullet_on_new_line():
    t = "■ Birinci madde. ■ İkinci madde."
    assert engine._bullet_breaks(t) == "■ Birinci madde.\n■ İkinci madde."


def test_bullet_breaks_no_bullet_unchanged():
    assert engine._bullet_breaks("düz metin") == "düz metin"


def test_fit_size_shrinks_long_text_only():
    f = fitz.Font(fontfile=os.path.join(engine.FONT_DIR, "Arial-Regular.ttf"))
    short, long = "ab", "abcdefghijklmnopqrstuvwxyz"
    w = f.text_length(short, 10)            # 'ab' genişliği
    assert engine._fit_size(f, short, w, 10) == 10        # sığan -> küçülmez
    assert engine._fit_size(f, long, w, 10) < 10          # uzun -> küçülür
    fs = engine._fit_size(f, long, w, 10)
    assert f.text_length(long, fs) <= w + 0.5 or fs <= 4.5  # sığar ya da floor


import types as _types


def _seg(x0, y0, x1, y1, size=9, single=True):
    return _types.SimpleNamespace(bbox=(x0, y0, x1, y1), size=size, single_line=single)


def _item(seg):
    return _types.SimpleNamespace(seg=seg)


def test_has_right_neighbor_detects_table_value():
    label = _seg(46, 280, 133, 289)
    value = _seg(180, 280, 210, 289)
    assert engine._has_right_neighbor(label, [label, value])
    assert not engine._has_right_neighbor(label, [label])


def test_avail_width_extends_to_neighbor_or_margin():
    # kısa, dar etiket ('SEX:' gibi): sağı boşsa kullanılabilir genişlik sayfa kenarına uzar
    label = _seg(40, 30, 57, 39)            # ~17pt geniş
    free = engine._avail_width(label, [label], 400, 40)
    assert free > 300, free                 # küçülme yok -> 'CİNSİYET:' tam boyutta sığar
    # sağda değer hücresi olunca (tablo) kullanılabilir genişlik komşuya kadar kısıtlanır
    value = _seg(200, 30, 260, 39)
    tbl = engine._avail_width(label, [label, value], 400, 40)
    assert 150 < tbl < 162, tbl             # ~ (200-2) - 40 ; taşma yine engellenir


def test_paragraph_groups_groups_prose_lines():
    a = _item(_seg(322, 124, 552, 133))
    b = _item(_seg(322, 134, 539, 143))
    c = _item(_seg(322, 145, 490, 154))
    groups = engine._paragraph_groups([a, b, c], {id(a), id(b), id(c)})
    assert len(groups) == 1 and len(groups[0]) == 3


def test_paragraph_groups_includes_passthrough_middle_line():
    # ortadaki satır değişmemiş (passthrough Latin adı) olsa da blok bütünlüğü için DAHİL edilir
    a = _item(_seg(322, 124, 552, 133))
    b = _item(_seg(322, 134, 490, 143))      # passthrough/unknown (changed değil)
    c = _item(_seg(322, 145, 500, 154))
    groups = engine._paragraph_groups([a, b, c], {id(a), id(c)})
    assert len(groups) == 1 and len(groups[0]) == 3 and groups[0][1] is b


def test_paragraph_groups_skips_all_unknown_block():
    # hiçbir satır değişmemişse (saf İngilizce) reflow edilmez
    a = _item(_seg(322, 124, 552, 133))
    b = _item(_seg(322, 134, 539, 143))
    assert engine._paragraph_groups([a, b], set()) == []


def test_paragraph_groups_skips_table_rows_with_right_neighbor():
    # tablo: her etiket satırının sağında değer hücresi -> reflow EDİLMEZ (tablo korunur)
    r1 = _item(_seg(46, 280, 133, 289))
    r2 = _item(_seg(46, 295, 121, 304))
    v1 = _item(_seg(180, 280, 210, 289))
    v2 = _item(_seg(180, 295, 210, 304))
    groups = engine._paragraph_groups([r1, r2, v1, v2], {id(r1), id(r2)})
    assert groups == []


def test_paragraph_groups_single_line_not_grouped():
    a = _item(_seg(322, 124, 552, 133))
    assert engine._paragraph_groups([a], {id(a)}) == []


def test_group_bottom_finds_nearest_below():
    a = _item(_seg(322, 124, 552, 133))
    b = _item(_seg(322, 134, 539, 143))
    chart = _seg(322, 230, 500, 240)         # altta, x-örtüşen
    assert engine._group_bottom([a, b], [a.seg, b.seg, chart]) == 230
    assert engine._group_bottom([a, b], [a.seg, b.seg]) is None
