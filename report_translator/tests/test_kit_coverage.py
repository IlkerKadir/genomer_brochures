"""Enterobiome Kids + Androbiome gerçek-lab rapor kapsama testleri.

Femobiome II için kanıtlanmış 'kapat+yeniden-yaz' tasarımının aynısını iki kite
genişletir. Buradaki kontroller veri-katmanı (dictionary.json) içindir:
- passthrough desenleri Latin/marker/ID dizgilerini olduğu gibi geçirir (hasta-arası dayanıklı),
- yeni etiket girişleri doğrulanmış TR ile çevrilir,
- sonuç-özeti cümleleri AI'ya (DeepL) yönlendirilir (özet kutusu femo ile aynı yol).

Gerçek-lab örnekleri new_samples/ altında (gitignore, hasta verisi) — yoksa skip.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import dictionary
import engine
import aiconfig


# --- Saf veri testleri (PDF gerektirmez, CI'da daima çalışır) ---

def _passthrough():
    _kits, _common, passthrough, _raw = dictionary.load()
    return passthrough


def _passes(passthrough, t):
    return any(p.fullmatch(t) for p in passthrough)


# Latin tür / direnç-belirteci / örnek-ID dizgileri OLDUĞU GİBİ geçmeli
PASSTHROUGH_YES = [
    "Enterobiome Kids", "Androbiome",
    "Sample_1", "Sample_4",
    "PCS",
    "E.coli", "C.albicans",
    "Dialister+Allisonella+Megasphaera+Veillonella",
    "tcdA, tcdB", "tcdA tcdB", "mecA", "srr2",
    "Bifidobacterium longum subsp. infantis",
    "Bifidobacterium animalis subsp. lactis",
    "Bifidobacterium catenulatum subsp",
    "Clostridium leptum gr", "Clostridium difficile gr",
    "10 Ureaplasma parvum*", "20 Candida spp.*",
    "13 Bacteroides spp. / Porphyromonas spp. / Prevotella spp.",
    "14 Anaerococcus spp.",
    "Ureaplasma urealyticum*",
    # filum-sınıflandırma satırları (Filum (EskiAd) Cins spp/gr)
    "Actinomycetota (Actinobacteria) Bifidobacterium spp",
    "Bacillota (Firmicutes) Clostridium leptum gr",
    "Bacteroidota (Bacteroidetes) Alistipes spp",
    # femobiome Latin/marker: dipnot rakamlı tür, kısaltılmış tür/eğik liste, BVAB/HPV markerları
    "Lactobacillus spp.1", "Lactobacillus spp.¹", "Streptococcus spp.²",
    "L.gasseri/L.paragasseri", "L.gasseri/L. paragasseri", "L.jensenii/L.mulieris",
    "(L.crispatus, L.iners, L.jensenii/L.mulieris),",
    "BVAB1/BVAB2/BVAB3", "BVAB1 / BVAB2 / BVAB3", "HPV 16", "HSV-1",
]

# Gerçek etiketler / cümleler passthrough OLMAMALI (sözlük/AI ile çevrilirler)
PASSTHROUGH_NO = [
    "Total bacterial load (TBL)",
    "Total bacterial load",
    "metabolically active infant-type, diversity",
    "Bacteroidota (Bacteroidetes), presence",
    "Bacillota/Bacteroidota (Firmicutes/Bacteroidetes), ratio:",
    "Patient:", "Comment:", "Sample marking:",
    "Candida spp. DNA is below threshold.",
    "Proportion of opportunistic microbiota is within normal limits",
    "Opportunistic pathogens, proportion",
]


@pytest.mark.parametrize("t", PASSTHROUGH_YES)
def test_passthrough_accepts_organism_and_marker_strings(t):
    assert _passes(_passthrough(), t), f"passthrough kaçırdı: {t!r}"


@pytest.mark.parametrize("t", PASSTHROUGH_NO)
def test_passthrough_rejects_real_labels(t):
    # Not: sözlükte olan etiketler için dict-exact zaten passthrough'tan önce gelir;
    # yine de desen kendi başına bu dizgileri yakalamamalı (gelecekteki kapsama açıkları).
    assert not _passes(_passthrough(), t), f"passthrough yanlışlıkla yuttu: {t!r}"


def test_new_label_entries_present_and_verified():
    kits, _common, _pt, _raw = dictionary.load()
    entero = kits["enterobiome_kids"]
    andro = kits["androbiome"]
    # entero: gerçek-lab 'load (TBL)' -> kitin kendi doğrulanmış TR'si 'kütlesi (TBK)'
    assert entero.get("Total bacterial load (TBL)") == "Toplam bakteri kütlesi (TBK)"
    assert entero.get("Bacteroidota (Bacteroidetes), presence") == "Bacteroidota (Bacteroidetes), varlık"
    assert entero.get("Bacillota/Bacteroidota (Firmicutes/Bacteroidetes), ratio:") \
        == "Bacillota/Bacteroidota (Firmicutes/Bacteroidetes), oran:"
    # andro: gerçek-lab başlık alanları
    assert andro.get("Patient:") == "Hasta:"
    assert andro.get("Comment:") == "Açıklama:"
    assert andro.get("Sample marking:") == "Örnek işareti:"


def test_ai_markers_route_real_lab_summary_sentences():
    _kits, _common, _pt, raw = dictionary.load()
    entero_m = dictionary.ai_markers(raw, "enterobiome_kids")
    andro_m = dictionary.ai_markers(raw, "androbiome")
    # entero üst-sol kutu cümleleri AI'ya uygun (özet + de-id temiz)
    assert aiconfig.ai_eligible(
        "agents are present. Proportion of opportunistic microbiota is within normal limits – 0.2%.",
        entero_m)
    assert aiconfig.ai_eligible(
        "The amount of yeast fungi is within the normal range – 4.4 GE/g.", entero_m)
    # andro sonuç-altı özet cümlesi
    assert aiconfig.ai_eligible("Candida spp. DNA is below threshold.", andro_m)


def test_ai_markers_do_not_route_patient_fields():
    _kits, _common, _pt, raw = dictionary.load()
    entero_m = dictionary.ai_markers(raw, "enterobiome_kids")
    # hasta alanları asla AI'ya gitmez (de-id kara-liste)
    assert not aiconfig.ai_eligible("FULL NAME: John Doe", entero_m)
    assert not aiconfig.ai_eligible("DATE OF BIRTH: 1.01.2023", entero_m)


# --- Gerçek-lab entegrasyon testleri (örnek varsa) ---

_ENTERO = os.path.join(os.path.dirname(__file__), "..", "new_samples", "entero_split", "entero_1.pdf")
_ANDRO = os.path.join(os.path.dirname(__file__), "..", "new_samples", "andro_split", "andro_1.pdf")
_FEMO = os.path.join(os.path.dirname(__file__), "..", "new_samples", "split", "rapor_3.pdf")


def _unknown_strings(path, kit):
    import fitz
    kits, common, pt, raw = dictionary.load()
    tpl = dictionary.compile_templates(raw, kit)
    doc = fitz.open(path)
    segs = engine.extract_segments(doc)
    ann = engine.translate_segments(segs, kits[kit], pt, {}, tpl)
    doc.close()
    seen = []
    for a in ann:
        if a.source == "unknown":
            t = a.en.strip()
            if t and t not in seen:
                seen.append(t)
    return seen


@pytest.mark.skipif(not os.path.exists(_ENTERO), reason="gerçek lab örneği yok (gitignore)")
def test_enterobiome_no_unknown_after_coverage():
    # AI-uygun (özet) cümleler unknown kalır AMA render'da DeepL'e gider; onları hariç tut.
    _kits, _common, _pt, raw = dictionary.load()
    markers = dictionary.ai_markers(raw, "enterobiome_kids")
    leftover = [t for t in _unknown_strings(_ENTERO, "enterobiome_kids")
                if not aiconfig.ai_eligible(t, markers)]
    assert leftover == [], f"çevrilemeyen (özet-dışı) dizgiler kaldı: {leftover}"


@pytest.mark.skipif(not os.path.exists(_ANDRO), reason="gerçek lab örneği yok (gitignore)")
def test_androbiome_no_unknown_after_coverage():
    _kits, _common, _pt, raw = dictionary.load()
    markers = dictionary.ai_markers(raw, "androbiome")
    leftover = [t for t in _unknown_strings(_ANDRO, "androbiome")
                if not aiconfig.ai_eligible(t, markers)]
    assert leftover == [], f"çevrilemeyen (özet-dışı) dizgiler kaldı: {leftover}"


@pytest.mark.skipif(not os.path.exists(_FEMO), reason="gerçek lab örneği yok (gitignore)")
def test_femobiome_no_unknown_after_coverage():
    _kits, _common, _pt, raw = dictionary.load()
    markers = dictionary.ai_markers(raw, "femobiome_ii")
    leftover = [t for t in _unknown_strings(_FEMO, "femobiome_ii")
                if not aiconfig.ai_eligible(t, markers)]
    assert leftover == [], f"çevrilemeyen (özet-dışı) dizgiler kaldı: {leftover}"
