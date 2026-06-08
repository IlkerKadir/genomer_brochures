"""dictionary.py — sözlüğü yükle ve düzenle (yedek + çakışma + paragraf heuristiği)."""
import os
import re
import json
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, "dictionary.json")
PARAGRAPH_WORD_THRESHOLD = 6  # >=6 kelime -> _paragraphs


def _safe_write(path, data):
    """Atomik yazım: önce .tmp'ye yaz, sonra os.replace ile taşı (yarım dosya riski yok)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


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
        atomic = {k: v for k, v in sec.items() if k not in ("_paragraphs", "_templates")}
        paras = sec.get("_paragraphs", {})
        merged = {}
        merged.update(common)
        merged.update(atomic)
        merged.update(paras)
        kits[kit] = merged
    return kits, common, passthrough, raw


def compile_templates(raw, kit):
    """Kit'in `_templates` listesini [(derlenmiş_regex, yerine_metni)] olarak döndür.
    _templates = [[regex_deseni, TR_metni], ...] — substring çevirisinden ÖNCE uygulanır."""
    pats = raw.get(kit, {}).get("_templates", [])
    return [(re.compile(p), r) for p, r in pats]


def detect_kit(doc):
    text = " ".join(doc[i].get_text() for i in range(min(2, len(doc)))).lower()
    if "androbiome" in text or "% of tmd" in text or "bv-associated" in text:
        return "androbiome"
    if "enterobiome" in text or "intestinal microbiota" in text or "ge/g" in text:
        return "enterobiome_kids"
    return "femobiome_ii"


def list_entries(path=None):
    """Tüm sözlük girişlerini düz liste olarak döndür.
    passthrough_patterns ve _meta hariç.
    Her giriş: {"scope": ..., "en": ..., "tr": ..., "paragraph": bool}
    """
    path = path or DICT_PATH
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    result = []
    # common girişleri
    for en, tr in data.get("common", {}).items():
        result.append({"scope": "common", "en": en, "tr": tr, "paragraph": False})

    # kit girişleri
    for kit in ("femobiome_ii", "androbiome", "enterobiome_kids"):
        sec = data.get(kit, {})
        paras = sec.get("_paragraphs", {})
        for en, tr in sec.items():
            if en == "_paragraphs":
                continue
            result.append({"scope": kit, "en": en, "tr": tr, "paragraph": False})
        for en, tr in paras.items():
            result.append({"scope": kit, "en": en, "tr": tr, "paragraph": True})

    return result


def set_entry(scope, en, tr, path=None, overwrite=False):
    """scope='common' ise common'a, kit ise add_entry mantığıyla yazar.
    Yedek .bak alır. Çakışmada {ok:False, conflict:True, existing}.
    Başarıda {ok:True}.
    """
    path = path or DICT_PATH
    en = re.sub(r"\s+", " ", en).strip()

    if scope == "common":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        common = data.setdefault("common", {})
        existing = common.get(en)
        if existing is not None and existing != tr and not overwrite:
            return {"ok": False, "conflict": True, "existing": existing}
        shutil.copy(path, path + ".bak")
        common[en] = tr
        _safe_write(path, data)
        return {"ok": True}

    # kit scope → mevcut add_entry mantığını kullan
    return add_entry(scope, en, tr, path=path, overwrite=overwrite)


def delete_entry(scope, en, path=None):
    """scope'a göre girişi siler. Yedek .bak alır.
    Başarıda {ok:True}. Bulunamazsa {ok:False, not_found:True}.
    """
    path = path or DICT_PATH
    en = re.sub(r"\s+", " ", en).strip()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    found = False
    if scope == "common":
        if en in data.get("common", {}):
            shutil.copy(path, path + ".bak")
            del data["common"][en]
            found = True
    else:
        sec = data.get(scope, {})
        paras = sec.get("_paragraphs", {})
        if en in sec:
            shutil.copy(path, path + ".bak")
            del sec[en]
            found = True
        elif en in paras:
            shutil.copy(path, path + ".bak")
            del paras[en]
            found = True

    if not found:
        return {"ok": False, "not_found": True}

    _safe_write(path, data)
    return {"ok": True}


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

    _safe_write(path, data)
    return {"ok": True, "conflict": False}
