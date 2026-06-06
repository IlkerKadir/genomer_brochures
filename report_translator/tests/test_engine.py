import fitz
import engine
import dictionary as dict_mod


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


def test_detect_kit(femobiome_pdf, androbiome_pdf, enterobiome_pdf):
    import dictionary
    assert dictionary.detect_kit(fitz.open(femobiome_pdf)) == "femobiome_ii"
    assert dictionary.detect_kit(fitz.open(androbiome_pdf)) == "androbiome"
    assert dictionary.detect_kit(fitz.open(enterobiome_pdf)) == "enterobiome_kids"


def test_render_produces_turkish_pdf(femobiome_pdf):
    table, passthrough = _table()
    out_bytes = engine.translate_document_bytes(femobiome_pdf, table, passthrough, overrides={})
    assert out_bytes[:4] == b"%PDF"
    rendered = fitz.open(stream=out_bytes, filetype="pdf")
    text = rendered[0].get_text()
    assert "Maya mantarları" in text          # çeviri uygulanmış
    assert "Mikrobiyota durumu" in text       # paragraf/başlık çevrilmiş
    assert len(rendered) >= 1                  # sayfa sayısı korunmuş


def test_render_applies_override(femobiome_pdf):
    table, passthrough = _table()
    doc = fitz.open(femobiome_pdf)
    target = next(s for s in engine.extract_segments(doc) if s.en == "Yeast fungi")
    out_bytes = engine.translate_document_bytes(
        femobiome_pdf, table, passthrough, overrides={target.id: "ÖZELMAYA"})
    text = fitz.open(stream=out_bytes, filetype="pdf")[0].get_text()
    assert "ÖZELMAYA" in text
