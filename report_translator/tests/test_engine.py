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
