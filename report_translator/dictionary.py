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
