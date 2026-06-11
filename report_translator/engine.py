"""engine.py — qPCR rapor PDF'lerini EN->TR çevirmek için saf çekirdek:
çıkar (extract) -> çevir (translate) -> render. UI ve CLI bunu kullanır.
"""
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
import fitz  # PyMuPDF
import aiconfig

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
    # Bold/italic'i hem İngilizce hem Türkçe font adlarından tespit et
    # (gerçek lab yazılımı "ArialKalın"/"Arialİtalik" kullanıyor; ı/İ encoding'i sorunlu olabilir)
    bold = "bold" in key or "kal" in key            # Kalın
    ital = "italic" in key or "talik" in key or "oblique" in key   # İtalik
    if "calibri" in key or "carlito" in key:
        return ("Carlito-BoldItalic.ttf" if bold and ital else
                "Carlito-Bold.ttf" if bold else
                "Carlito-Italic.ttf" if ital else "Carlito-Regular.ttf")
    if "montserrat" in key:
        return "Montserrat-Bold.ttf"
    if "roboto" in key:
        return "Roboto-Italic.ttf" if ital else "Roboto-Regular.ttf"
    return ("Arial-BoldItalic.ttf" if bold and ital else
            "Arial-Bold.ttf" if bold else
            "Arial-Italic.ttf" if ital else "Arial-Regular.ttf")


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
    return _merge_split_sentences(segments)


def _mergeable_continuation(a, b, page_segs):
    """a (cümle-sonu noktalamasız biten) ve b (küçük harfle başlayan) gerçek bir bölünmüş
    cümle mi? Çok-satırlı prose blokları doğrudan; tek-satır parçalar yalnız GENİŞ prose satırı
    olup iki tarafta da sağ-komşu YOKSA (tablo değer hücresi yok) birleşir. Böylece özet/sonuç
    kutusu parçaları birleşir ama tablo etiket/değer satırları korunur."""
    if not a.single_line and not b.single_line:
        return True
    return ((a.bbox[2] - a.bbox[0]) > 150
            and not _has_right_neighbor(a, page_segs)
            and not _has_right_neighbor(b, page_segs))


def _merge_split_sentences(segments):
    """Aynı sütunda dikey-bitişik, aynı font/boyut iki prose bloğu — birincisi cümle-sonu
    noktalaması OLMADAN bitip ikincisi küçük harfle başlıyorsa — tek segmente birleştir.

    Gerçek-lab özet/sonuç kutusu bazı raporlarda cümle ortasından iki parçaya bölünüyor
    (ör. '...The Bacteroidetes taxa' + 'agents are present...', '...The accuracy of bacterial' +
    'amount calculation may be low.'). Birleştirmeyince her parça ayrı çevrilir (DeepL yarım
    cümle alır → kötü çeviri) ve ayrı yazılır (cümle ortasında satır atlama). Tablo hücreleri
    `_mergeable_continuation` koruması ile etkilenmez."""
    by_page = {}
    for s in segments:
        by_page.setdefault(s.page, []).append(s)
    cand = sorted(segments, key=lambda s: (s.page, round(s.bbox[0]), s.bbox[1]))
    drop = set()
    i = 0
    while i < len(cand):
        a = cand[i]
        if id(a) in drop:
            i += 1
            continue
        j = i + 1
        while j < len(cand):
            b = cand[j]
            if id(b) in drop:
                j += 1
                continue
            same_col = (a.page == b.page and abs(a.bbox[0] - b.bbox[0]) <= 4
                        and a.fontfile == b.fontfile and abs(a.size - b.size) <= 0.6)
            adjacent = -2.0 <= (b.bbox[1] - a.bbox[3]) <= a.size * 0.8
            split_sentence = (a.en.rstrip()[-1:] not in ".!?:" and b.en.lstrip()[:1].islower())
            if (same_col and adjacent and split_sentence
                    and _mergeable_continuation(a, b, by_page[a.page])):
                a.en = a.en.rstrip() + " " + b.en.lstrip()
                a.bbox = [min(a.bbox[0], b.bbox[0]), a.bbox[1],
                          max(a.bbox[2], b.bbox[2]), b.bbox[3]]
                a.rects = a.rects + b.rects
                a.single_line = False              # birleşik metin çok satıra sarılmalı (küçülmesin)
                drop.add(id(b))
                j += 1
            else:
                break
        i += 1
    return [s for s in segments if id(s) not in drop]


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
    def __init__(self, table, passthrough, templates=None):
        self.table = table
        self.keys = sorted(table.keys(), key=len, reverse=True)
        self.passthrough = passthrough
        self.templates = templates or []   # [(derlenmiş_regex, yerine_metni), ...]

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
        for rx, rep in self.templates:        # regex ön-geçişi (yüzde biçimi vb.)
            result = rx.sub(rep, result)
        for k in self.keys:                   # parça-değişimi (longest-match)
            if k in result:
                result = result.replace(k, self.table[k])
        changed = norm_ws(result) != t
        return (result if changed else text), changed, False


def translate_segments(segments, table, passthrough, overrides, templates=None):
    matcher = _Matcher(table, passthrough, templates)
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


def _leading_indent(text, font, size):
    n = len(text) - len(text.lstrip(" "))
    return font.text_length(" " * n, size) if n else 0.0


# Render fontları (Arial vb.) bazı sembol gliflerini içermez → içi boş kutu çizilir.
# Bilinen eksikleri fontun sahip olduğu eşdeğerle değiştir (ör. ⯀ U+2BC0 -> ■ U+25A0).
_GLYPH_SUBS = {0x2BC0: "■"}


def _sub_glyphs(text):
    """Render fontunda olmayan bilinen glifleri eşdeğeriyle değiştir."""
    return text.translate(_GLYPH_SUBS)


def _bullet_breaks(text):
    """Çok-satırlı kutuda her madde-işaretini (■) yeni satıra al (ilki hariç).

    Çıkarma sırasında birden çok madde tek segmente birleşip aralarındaki satır
    sonu boşluğa dönüşebilir; bunu orijinaldeki gibi geri koyar. ■ yoksa değişmez."""
    return re.sub(r"\s*■\s*", "\n■ ", text).lstrip("\n")


def _fit_size(font, text, avail, size, floor=4.5):
    """text `avail` genişliğine sığana kadar font boyutunu küçült (floor'a kadar).

    Tek-satır segmentlerde çeviri orijinalden uzun olunca yatay taşmayı önler;
    sığıyorsa `size` aynen döner."""
    fs = size
    while fs > floor and font.text_length(text, fs) > avail + 0.5:
        fs -= 0.25
    return fs


def _sample_bg(pixmap, rect, scale, tol=12, min_frac=0.7):
    """Segment dikdörtgeninin kenar marjından (harf dışı dolgu) baskın zemin rengini örnekle.

    Halka yeterince tek-renk ise (r, g, b) 0-1 float tuple; çok-renkli/örneklenemezse None.
    None dönerse çağıran fill=None'a düşer (vektör İngilizce kalır, yama oluşmaz).
    tol sıkı (12): gradyan/yakın renkleri 'tek renk' saymamak için."""
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
               if all(abs(a - b) <= tol for a, b in zip(c[:3], col[:3])))
    if near / sum(cnt.values()) < min_frac:
        return None
    return (col[0] / 255.0, col[1] / 255.0, col[2] / 255.0)


def _sample_fg(pixmap, rect, scale, bg, tol=24):
    """rect içindeki baskın ön-plan (mürekkep) rengini örnekle: bg'den farklı baskın renk.

    Görünmez (beyaz) metin-katmanı rengi yerine gerçek mürekkep rengini verir.
    bg-dışı piksel yoksa (0,0,0) siyah döndürür (asla None).
    tol gevşek (24): anti-aliased harf kenar piksellerini de mürekkep saymak için.
    Not: RGB pixmap varsayar (page.get_pixmap() varsayılanı alfasızdır); ilk 3 kanalı kullanır."""
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


def _fontname_for(fontfile, font_cache):
    """fontfile için kalıcı, çakışmasız PDF font adı üret/önbellekle.

    Gerçek-lab PDF'leri gömülü fontlarını F0/F1/... olarak adlandırır. Kısa "F0"
    gibi adlar bu kaynak fontlarla ÇAKIŞIR: insert_text(box) çakışan adı görünce
    kaynak fontu (Türkçe glif'siz) yeniden kullanır → ı/ç/ş/ğ düşer, mojibake olur.
    Bu yüzden hiçbir kaynak PDF'te bulunmayacak ayırt edici bir önek kullanılır."""
    name = font_cache.get(fontfile)
    if name is None:
        name = "GnmrTR%d" % len(font_cache)
        font_cache[fontfile] = name
    return name


def _has_right_neighbor(seg, all_segs, gap=4):
    """seg'in sağında (y-bandı örtüşen) başka segment var mı?

    Tablo değer hücreleri (lg GE/mL, %, Reference) sağda olur; paragraf satırlarının
    sağı boştur. Bu, reflow'un yanlışlıkla tablo satırlarını birleştirmesini önler."""
    y0, y1 = seg.bbox[1], seg.bbox[3]
    for o in all_segs:
        if o is seg:
            continue
        if o.bbox[0] >= seg.bbox[2] + gap and min(y1, o.bbox[3]) - max(y0, o.bbox[1]) > 1:
            return True
    return False


def _avail_width(seg, all_segs, page_width, left):
    """Tek-satır segment için sağdaki en yakın komşuya (yoksa sayfa kenarına) kadar kullanılabilir
    genişlik. Çeviri orijinalden uzunsa (ör. 'SEX:' -> 'CİNSİYET:'), fontu küçültmek yerine
    sağdaki boşluğa taşımayı sağlar. Tablo hücrelerinde sağ komşu bulunur -> taşma yine engellenir."""
    right = page_width - 4.0
    if all_segs:
        y0, y1 = seg.bbox[1], seg.bbox[3]
        for o in all_segs:
            if o is seg or o.bbox[0] < seg.bbox[2] - 0.5:
                continue
            if min(y1, o.bbox[3]) - max(y0, o.bbox[1]) > 1.0:   # y-örtüşen sağ komşu
                right = min(right, o.bbox[0] - 2.0)
    return max(right - left, seg.bbox[2] - left)               # en az orijinal genişlik


def _paragraph_groups(all_items, changed_ids):
    """Ardışık tek-satır segmentleri paragraf bloklarına grupla (tablo/hasta-alanı hariç).

    `all_items`: sayfanın tüm segmentleri; `changed_ids`: çevrilen (değişen) segment id'leri.
    Tüm tek-satır segmentleri komşuluğa göre grupla; bir grup ancak şu üç koşulda reflow edilir:
    >=2 satır, en az biri değişmiş (saf-İngilizce blokları atla), ve hiçbir satırın sağında
    komşu yok (tablo değer hücreleri sağda olur -> tablolar/hasta-alanları korunur).
    Gruplar passthrough/unknown satırları da kapsar (aradaki Latin adı satırı gibi) ki blok
    bütünlüğü bozulmasın."""
    singles = sorted([it for it in all_items if it.seg.single_line],
                     key=lambda it: (round(it.seg.bbox[1]), it.seg.bbox[0]))
    all_segs = [it.seg for it in all_items]
    used = [False] * len(singles)
    groups = []
    for idx, it in enumerate(singles):
        if used[idx]:
            continue
        grp = [it]
        used[idx] = True
        cur = it                              # cur = gruba son eklenen üye (sıradaki değil)
        for j in range(idx + 1, len(singles)):
            if used[j]:
                continue
            nx = singles[j]
            same_x = abs(nx.seg.bbox[0] - cur.seg.bbox[0]) <= 3
            adjacent = 0 < nx.seg.bbox[1] - cur.seg.bbox[1] <= 1.9 * cur.seg.size
            same_size = abs(nx.seg.size - cur.seg.size) <= 0.6
            if same_x and adjacent and same_size:
                grp.append(nx)
                used[j] = True
                cur = nx
        groups.append(grp)
    return [grp for grp in groups
            if len(grp) >= 2
            and any(id(g) in changed_ids for g in grp)
            and not any(_has_right_neighbor(g.seg, all_segs) for g in grp)
            and _is_prose_block(grp)]


def _is_prose_block(grp):
    """Grup sarılmış prose mu, yoksa istiflenmiş kısa etiketler mi?

    Sarılmış prose'da son-olmayan satırlar kolonu DOLDURUR (bir sonraki kelime sığmadığı
    için sağ kenara yakın biter). Tablo etiket satırları (ör. değer hücresi '—' olduğu için
    sağ-komşusu görünmeyen 'HPV 16' / 'HPV 18' / 'HPV 45') kısadır ve kolonu doldurmaz.
    En az bir son-olmayan satır kolonu dolduruyorsa prose say (reflow et)."""
    gl = min(g.seg.bbox[0] for g in grp)
    gr = max(g.seg.bbox[2] for g in grp)
    width = gr - gl
    if width <= 0:
        return False
    return any(g.seg.bbox[2] >= gr - 0.25 * width for g in grp[:-1])


def _group_bottom(grp, all_segs):
    """Grubun altındaki (y-altında, x-örtüşen) en yakın segmentin üst kenarı; yoksa None.

    Sarılan metnin alttaki öğeye (ör. grafik) taşmaması için sınır olarak kullanılır."""
    gx0 = min(g.seg.bbox[0] for g in grp)
    gx1 = max(g.seg.bbox[2] for g in grp)
    gy1 = max(g.seg.bbox[3] for g in grp)
    grp_ids = {id(g.seg) for g in grp}
    bottom = None
    for s in all_segs:
        if id(s) in grp_ids:
            continue
        if s.bbox[1] >= gy1 - 1 and min(gx1, s.bbox[2]) - max(gx0, s.bbox[0]) > 1:
            if bottom is None or s.bbox[1] < bottom:
                bottom = s.bbox[1]
    return bottom


def _reflow_layout(page, grp, col_of, font_cache, sc, x0, right, baseline, pitch, do_render):
    """Grubu sc ölçeğinde sararak yerleştir; son satırın y'sini döndür (do_render=False ise sadece ölçer)."""
    cx, cy = x0, baseline
    for gi, g in enumerate(grp):
        s = g.seg
        fontfile = os.path.join(FONT_DIR, s.fontfile)
        fontname = _fontname_for(s.fontfile, font_cache)
        font = fitz.Font(fontfile=fontfile)
        col = col_of[id(g)]
        size = s.size * sc
        text = _sub_glyphs(g.tr.strip())
        if gi > 0 and text.startswith("■") and cx > x0 + 0.1:   # yeni madde -> yeni satır
            cx, cy = x0, cy + pitch * sc
        space_w = font.text_length(" ", size)
        for word in text.split():
            ww = font.text_length(word, size)
            if cx > x0 + 0.1 and cx + ww > right:               # satır sonu -> sar
                cx, cy = x0, cy + pitch * sc
            if do_render:
                page.insert_text((cx, cy), word, fontname=fontname,
                                 fontfile=fontfile, fontsize=size, color=col)
            cx += ww + space_w
    return cy


def _render_reflow_group(page, grp, col_of, font_cache, bottom=None):
    """Bir paragraf grubunu kutuya yeniden akıt (kelime-bazlı sarma, her segmentin kendi fontu).

    İngilizcedeki gibi alt satıra geçer; Latin tür adlarının italiği korunur. Madde işaretiyle
    (■) başlayan segmentler yeni satıra alınır. `bottom` verilirse ve sarılan metin taşacaksa
    blok orantılı olarak küçültülür (taşma yerine ölçek)."""
    x0 = min(g.seg.bbox[0] for g in grp)
    right = max(g.seg.bbox[2] for g in grp)
    pitches = sorted(grp[i + 1].seg.bbox[1] - grp[i].seg.bbox[1] for i in range(len(grp) - 1))
    pitch = pitches[len(pitches) // 2] if pitches else grp[0].seg.size * 1.2   # medyan aralık
    baseline = grp[0].seg.origin[1]
    sc = 1.0
    if bottom is not None:
        while sc > 0.5:
            if _reflow_layout(page, grp, col_of, font_cache, sc, x0, right,
                              baseline, pitch, False) <= bottom - 2:
                break
            sc -= 0.05
    _reflow_layout(page, grp, col_of, font_cache, sc, x0, right, baseline, pitch, True)


def _page_graphics(page):
    """Tek bir get_drawings çağrısından (ince_çizgiler, vektör_outline_mu) döndür.

    - ince çizgiler: tablo ızgara çizgileri (a, b, renk, kalınlık). Kapatma dolgusu bunları
      örtebilir; render sonunda örtülenler üste yeniden çizilir.
    - vektör_outline_mu: sayfa gövde metnini eğriye-çevrilmiş (glif-boyutlu dolgu yolları)
      olarak çiziyor mu? Öyleyse kapatma+yeniden-yaz gerekir; normal metin sayfalarında
      (ör. Enterobiome) kapatma dolgusu gereksiz/zararlıdır (gri kutu + soluk mürekkep)."""
    strokes = []
    glyph_fills = 0
    for d in page.get_drawings():
        typ = d["type"]
        w = d.get("width") or 0
        col = d.get("color")
        if "f" in typ:                         # dolgu: glif-boyutlu mu? (vektör-outline işareti)
            r = fitz.Rect(d["rect"])
            if 0 < r.width < 40 and 0 < r.height < 20:
                glyph_fills += 1
        if col is not None and "s" in typ and w <= 1.5:
            for it in d["items"]:
                if it[0] == "l":
                    strokes.append((fitz.Point(it[1]), fitz.Point(it[2]), tuple(col), w))
                elif it[0] == "re":
                    rr = fitz.Rect(it[1])
                    cs = [fitz.Point(rr.x0, rr.y0), fitz.Point(rr.x1, rr.y0),
                          fitz.Point(rr.x1, rr.y1), fitz.Point(rr.x0, rr.y1)]
                    for i in range(4):
                        strokes.append((cs[i], cs[(i + 1) % 4], tuple(col), w))
    return strokes, glyph_fills >= 5


def _redraw_covered_strokes(page, strokes, filled_rects):
    """Yalnız bir kapatma-dolgusuyla kesişen ince çizgileri orijinal renk/kalınlıkla üste çiz.
    Grafik/çizelge gibi dolgu uygulanmayan alanlara dokunulmaz (cerrahi onarım)."""
    if not filled_rects or not strokes:
        return
    from collections import defaultdict
    groups = defaultdict(list)
    for a, b, col, w in strokes:
        seg = fitz.Rect(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y))
        seg += (-0.5, -0.5, 0.5, 0.5)              # dejenere (sıfır en/boy) çizgi için tolerans
        if any(seg.intersects(fr) for fr in filled_rects):
            groups[(col, round(max(w, 0.3), 2))].append((a, b))
    for (col, w), lines in groups.items():
        shape = page.new_shape()
        for a, b in lines:
            shape.draw_line(a, b)
        shape.finish(color=col, width=w)
        shape.commit()


# Femo hasta-başlığı etiketleri metin katmanı OLMAYAN saf vektör (Patient name: vb.).
# Sabit şablon: sayfa-1'de 6 alan; devam sayfalarında 2 alan (Patient name, Sample ID).
# Etiket sayısına göre eşlenir (metin yok -> hangi etiket olduğu sıra/şablondan bilinir).
_FEMO_HEADER_LABELS = {
    6: ["Hasta adı:", "Doğum tarihi:", "Numune tarihi:", "Örnek türü:", "Örnek ID:", "Hekim:"],
    2: ["Hasta adı:", "Örnek ID:"],
}


def _overlay_femo_header(page):
    """Femo hasta-başlığı etiketlerini (metin katmanı yok, saf vektör) Türkçeye çevir.

    İmza: üst bölgede ~14.4pt düzenli aralıklı, üzerinde etiket-glifi olan ardışık ayraç
    çizgileri (hasta-alan satırları) + o satırlarda metin katmanı YOK (andro/entero başlıkları
    metin katmanlı → tetiklenmez). Etiket sayısı şablonu belirler (6=sayfa-1, 2=devam sayfası).
    Her satırda etiket glif-kümesi kapatılıp Türkçe yazılır; değer (hasta verisi) korunur."""
    draws = page.get_drawings()
    lines = sorted(set(
        round(it[1][1], 1)
        for d in draws if "s" in d["type"] and (d.get("width") or 0) < 2.0
        for it in d["items"]
        if it[0] == "l" and abs(it[1][1] - it[2][1]) < 0.5
        and min(it[1][0], it[2][0]) < 60 and max(it[1][0], it[2][0]) > 280
        and 60 < it[1][1] < 260))
    if len(lines) < 2:
        return
    black_fills = [fitz.Rect(d["rect"]) for d in draws
                   if "f" in d["type"] and d.get("fill") and max(d["fill"]) < 0.3]
    # üstten, ~14.4pt düzenli aralıklı, üzerinde etiket-glifi olan ardışık satırları topla
    rows = []          # (bottom, lab_top, lab_end, value_start)
    prev = None
    for y in lines:
        if rows and prev is not None and abs((y - prev) - 14.4) > 3:
            break                              # düzenli koşu bitti -> hasta-alanları bitti
        row = sorted((r for r in black_fills if y - 13 < r.y0 < y - 1 and 46 < r.x0 < 220),
                     key=lambda r: r.x0)
        if row:
            lab_top = min(r.y0 for r in row)
            lab_end = row[0].x1
            value_start = None
            for r in row[1:]:                  # etiket kümesi: soldan, >5pt boşluğa kadar
                if r.x0 - lab_end > 5:
                    value_start = r.x0
                    break
                lab_end = max(lab_end, r.x1)
            rows.append((y, lab_top, lab_end, value_start))
            prev = y
        elif rows:
            break                              # etiketsiz satır -> hasta-alanları bitti
        else:
            prev = y                           # henüz başlamadık (banner üstü vb.)
    labels = _FEMO_HEADER_LABELS.get(len(rows))
    if not labels:
        return                                 # bilinmeyen alan sayısı -> yanlış etiket yazma
    # Not: vektör glif-satır deseni femo'ya özgüdür (andro/entero başlıkları metin katmanlı,
    # bu desen oluşmaz) -> ayrı metin-yok kontrolü gerekmez; sadece bilinen alan sayılarında yaz.
    fontfile = os.path.join(FONT_DIR, "Arial-Bold.ttf")
    font = fitz.Font(fontfile=fontfile)
    plans = []
    for (bottom, lab_top, lab_end, value_start), label in zip(rows, labels):
        right = (value_start - 1.5) if value_start else (lab_end + 3)
        page.add_redact_annot(fitz.Rect(46, lab_top - 1, right, bottom - 1.5), fill=(1, 1, 1))
        size = _fit_size(font, label, right - 49, 9.0)
        plans.append((bottom - 4.0, label, size))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
    for baseline, label, size in plans:
        page.insert_text((49, baseline), label, fontname="GnmrTRhdr",
                         fontfile=fontfile, fontsize=size, color=(0, 0, 0))


def _render_page_items(page, items, font_cache, all_items=None):
    """Tek bir sayfadaki değişen segmentleri yerinde render et (redaksiyon + geri yazma).

    all_items verilirse (sayfanın tüm segmentleri), ardışık tek-satır paragraf blokları
    tespit edilip kutuya yeniden akıtılır (sarma); tablo satırları güvenlik kuralıyla hariç."""
    if not items:
        return
    strokes, vector_outline = _page_graphics(page)   # ızgara çizgileri + vektör-outline mu?
    filled_rects = []                          # kapatma-dolgusu (fill=bg) uygulanan dikdörtgenler
    try:
        pm = page.get_pixmap(dpi=150)
        scale = 150 / 72.0
    except Exception:                      # pragma: no cover - beklenmez
        pm = None
        scale = 1.0
    changed_ids = {id(a) for a in items}
    all_segs = [it.seg for it in all_items] if all_items is not None else None
    groups = _paragraph_groups(all_items, changed_ids) if all_items is not None else []
    grouped = {id(g) for grp in groups for g in grp}
    # redaksiyon kümesi: değişen segmentler + grup üyeleri (aradaki passthrough/unknown satırlar
    # da redakte edilip akış içinde yeniden yazılır; yoksa orijinal İngilizce yerinde kalırdı)
    render_set = list(items)
    seen = set(changed_ids)
    for grp in groups:
        for g in grp:
            if id(g) not in seen:
                render_set.append(g)
                seen.add(id(g))
    resolved = []                          # (annotation, yeniden-yazma rengi)
    for a in render_set:
        first_bg = None
        first_rect = None
        for r in a.seg.rects:
            rect = fitz.Rect(r)
            # kapatma yalnız vektör-outline sayfalarda; normal metin redaksiyonla temizce silinir
            bg = _sample_bg(pm, rect, scale) if (pm is not None and vector_outline) else None
            if bg is not None:
                if first_bg is None:
                    first_bg = bg
                    first_rect = rect
                # vektör kenarları metin bbox'unu yatayda taşabilir -> yatayda 1px genişlet;
                # dikeyde yalnız 0.3px (ince tablo ızgara çizgileri ~0.7px ötede; onları örtüp
                # soluklaştırmamak için). Yine de örtülen çizgi olursa _redraw_covered_strokes geri çizer.
                fr = rect + (-1, -0.3, 1, 0.3)
                page.add_redact_annot(fr, fill=bg)
                filled_rects.append(fr)
            else:
                page.add_redact_annot(rect, fill=None)   # güvenli: İngilizce kalır
        # kapatma yapıldıysa görünmez (beyaz) metin-katmanı yerine gerçek mürekkep rengi;
        # mürekkebi, zemini bulunan rect'ten örnekle
        if first_bg is not None and pm is not None:
            col = _sample_fg(pm, first_rect, scale, first_bg)
        else:
            col = a.seg.color
        resolved.append((a, col))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
    col_of = {id(a): col for a, col in resolved}
    for grp in groups:                     # paragraf blokları -> sararak akıt
        _render_reflow_group(page, grp, col_of, font_cache, _group_bottom(grp, all_segs))
    for a, col in resolved:
        if id(a) in grouped:               # grup içinde render edildi
            continue
        s = a.seg
        fontfile = os.path.join(FONT_DIR, s.fontfile)
        fontname = _fontname_for(s.fontfile, font_cache)
        font = fitz.Font(fontfile=fontfile)
        text = _sub_glyphs(a.tr.strip())
        indent = _leading_indent(s.raw_first, font, s.size)
        if s.single_line:
            ox, oy = s.origin
            # kullanılabilir genişlik = sağdaki komşuya/sayfa kenarına kadar (etiketler boşluğa taşar,
            # küçülmez); yine sığmazsa _fit_size fontu küçültür (tablo hücrelerinde taşma engellenir)
            avail = _avail_width(s, all_segs, page.rect.width, ox + indent)
            fs = _fit_size(font, text, avail, s.size)
            page.insert_text((ox + indent, oy), text, fontname=fontname,
                             fontfile=fontfile, fontsize=fs, color=col)
        else:
            text = _bullet_breaks(text)        # her madde-işareti yeni satırda
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
    # kapatma-dolgusunun örttüğü ızgara çizgilerini orijinal renk/kalınlıkla geri çiz
    _redraw_covered_strokes(page, strokes, filled_rects)
    # femo hasta-başlığı etiketleri (metin katmanı yok, saf vektör) -> Türkçe kaplama (femo imzalıysa)
    _overlay_femo_header(page)


def _changed_items(annotated):
    return [a for a in annotated
            if a.source not in ("passthrough", "unknown") and a.tr != a.en]


def render(doc, annotated):
    """Tüm belgeyi yerinde render et (kopya verin)."""
    by_page = {}
    for a in _changed_items(annotated):
        by_page.setdefault(a.seg.page, []).append(a)
    by_page_all = {}
    for a in annotated:
        by_page_all.setdefault(a.seg.page, []).append(a)
    font_cache = {}
    for page_index, items in by_page.items():
        _render_page_items(doc[page_index], items, font_cache, by_page_all.get(page_index))
    return doc


def translate_one_page_bytes(pdf_path_or_bytes, table, passthrough, overrides,
                             page_index, original=False, templates=None):
    """Yalnız page_index render edilmiş tek-sayfalık PDF bayt'ı döndür."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    try:
        if not original:
            ann = translate_segments(extract_segments(doc), table, passthrough, overrides, templates)
            items = [a for a in _changed_items(ann) if a.seg.page == page_index]
            all_items = [a for a in ann if a.seg.page == page_index]
            _render_page_items(doc[page_index], items, {}, all_items)
        # yalnız o sayfayı içeren yeni belge
        out = fitz.open()
        try:
            out.insert_pdf(doc, from_page=page_index, to_page=page_index)
            data = out.tobytes(garbage=4, deflate=True)
        finally:
            out.close()
    finally:
        doc.close()
    return data


def render_page_png(pdf_path_or_bytes, table, passthrough, overrides,
                    page_index, dpi=150, original=False, templates=None, ai=None):
    """page_index'in render edilmiş PNG bayt'ı."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    try:
        if not original:
            ann = translate_segments(extract_segments(doc), table, passthrough, overrides, templates)
            if ai:
                apply_ai_summary(ann, ai[0], ai[1], ai[2])
            items = [a for a in _changed_items(ann) if a.seg.page == page_index]
            all_items = [a for a in ann if a.seg.page == page_index]
            _render_page_items(doc[page_index], items, {}, all_items)
        png = doc[page_index].get_pixmap(dpi=dpi).tobytes("png")
    finally:
        doc.close()
    return png


def translate_document_bytes(pdf_path_or_bytes, table, passthrough, overrides,
                             templates=None, ai=None):
    """Orijinalden taze TR PDF bayt'ı üretir. ai = (provider, markers, cache) veya None."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    try:
        segs = extract_segments(doc)
        ann = translate_segments(segs, table, passthrough, overrides, templates)
        if ai:
            apply_ai_summary(ann, ai[0], ai[1], ai[2])
        render(doc, ann)
        out = doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()
    return out


def apply_ai_summary(annotated, provider, markers, cache, deid=None):
    """Saf çeviriden SONRA: yalnız 'özet' (beyaz-liste) + de-id temiz segmentleri AI ile çevir.
    Öncelik: dict-exact korunur > önbellek > AI çağrısı > (hata/yedek) yerel çeviri kalır.
    Ağ yalnız provider verilince ve önbellek ıskasında çalışır. annotated yerinde değişir."""
    if deid is None:
        deid = aiconfig.deid_ok
    corrections = aiconfig.postedit_corrections()   # DeepL Türkçe dilbilgisi düzeltmeleri
    todo = []   # (index, norm_en)
    for i, a in enumerate(annotated):
        if a.source == "dict-exact":          # hekim/sözlük onayı kazanır
            continue
        en = norm_ws(a.en)
        if not any(m.lower() in en.lower() for m in markers):
            continue
        if not deid(en):                        # hasta verisi -> asla gönderme
            continue
        cached = cache.get(en)
        if cached is not None:
            a.tr = aiconfig.apply_postedit(cached, corrections)   # önbellek ham DeepL tutar
            a.source = "ai"
            a.needs_review = False
            continue
        todo.append((i, en))
    if provider and todo:
        try:
            results = provider.translate([en for _, en in todo])
            for (i, en), tr in zip(todo, results):
                aiconfig.cache_set(cache, en, tr)                 # ham DeepL'i önbelleğe yaz
                annotated[i].tr = aiconfig.apply_postedit(tr, corrections)
                annotated[i].source = "ai"
                annotated[i].needs_review = False
        except Exception:
            pass    # yerel yedek: annotated[i].tr zaten sözlük+şablon çevirisini taşıyor
    return annotated
