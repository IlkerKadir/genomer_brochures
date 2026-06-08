"""engine.py — qPCR rapor PDF'lerini EN->TR çevirmek için saf çekirdek:
çıkar (extract) -> çevir (translate) -> render. UI ve CLI bunu kullanır.
"""
import os
import re
import sys
from dataclasses import dataclass
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


def _render_page_items(page, items, font_cache):
    """Tek bir sayfadaki değişen segmentleri yerinde render et (redaksiyon + geri yazma)."""
    if not items:
        return
    for a in items:
        for r in a.seg.rects:
            page.add_redact_annot(fitz.Rect(r), fill=None)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
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
            fitted = False
            while fs > 4.5:
                pad = fitz.Rect(left, box.y0 - 1, box.x1 + 2, box.y1 + 4 * s.size)
                rc = page.insert_textbox(pad, text, fontname=fontname, fontfile=fontfile,
                                         fontsize=fs, color=s.color, lineheight=1.15,
                                         align=fitz.TEXT_ALIGN_LEFT)
                if rc >= 0:
                    fitted = True
                    break
                fs -= 0.25
            if not fitted:
                sys.stderr.write("UYARI: segment sığmadı, atlandı: %r\n" % text)


def _changed_items(annotated):
    return [a for a in annotated
            if a.source not in ("passthrough", "unknown") and a.tr != a.en]


def render(doc, annotated):
    """Tüm belgeyi yerinde render et (kopya verin)."""
    by_page = {}
    for a in _changed_items(annotated):
        by_page.setdefault(a.seg.page, []).append(a)
    font_cache = {}
    for page_index, items in by_page.items():
        _render_page_items(doc[page_index], items, font_cache)
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
            _render_page_items(doc[page_index], items, {})
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
                    page_index, dpi=150, original=False, templates=None):
    """page_index'in render edilmiş PNG bayt'ı (override'lı veya orijinal)."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    try:
        if not original:
            ann = translate_segments(extract_segments(doc), table, passthrough, overrides, templates)
            items = [a for a in _changed_items(ann) if a.seg.page == page_index]
            _render_page_items(doc[page_index], items, {})
        png = doc[page_index].get_pixmap(dpi=dpi).tobytes("png")
    finally:
        doc.close()
    return png


def translate_document_bytes(pdf_path_or_bytes, table, passthrough, overrides, templates=None):
    """Orijinalden taze TR PDF bayt'ı üretir. pdf_path_or_bytes: yol (str) veya bytes."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    try:
        segs = extract_segments(doc)
        ann = translate_segments(segs, table, passthrough, overrides, templates)
        render(doc, ann)
        out = doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()
    return out
