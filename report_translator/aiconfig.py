"""aiconfig.py — AI sonuç-özeti çevirisi için yapılandırma, önbellek, de-id ve işaretçiler.
config.json ve ai_cache.json yereldedir (git'e girmez); API anahtarı koda yazılmaz."""
import os
import re
import json

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
CACHE_PATH = os.path.join(HERE, "ai_cache.json")

DEFAULT_CONFIG = {
    "provider": "deepl",
    "deepl_api_key": "",
    "ai_summary_enabled": False,
    "target_lang": "TR",
    "deepl_context": ("Formal Turkish translation of a clinical conclusion from a urogenital or "
                      "intestinal microbiota qPCR diagnostic report. Keep all Latin taxonomic names "
                      "and abbreviations (spp., gr, subsp.) exactly as written; do not translate them. "
                      "Relative amounts are reported as percentages; do not infer any increase or "
                      "decrease that is not explicitly stated. Use a formal medical register."),
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def save_config(updates):
    cfg = load_config()
    cfg.update(updates)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)
    return cfg


def public_config():
    """API'ye dönecek gizli-olmayan durum (anahtar DÖNMEZ)."""
    cfg = load_config()
    return {"provider": cfg["provider"],
            "ai_summary_enabled": bool(cfg["ai_summary_enabled"]),
            "target_lang": cfg["target_lang"],
            "has_key": bool(cfg.get("deepl_api_key"))}


# Hasta-verisi kara-listesi (de-id emniyet ağı)
_DATE_RX = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
_DIGIT_RUN_RX = re.compile(r"\d{6,}")
_PATIENT_TERMS = [
    "name", "ad soyad", "patient", "date of birth", "doğum", "sampling",
    "numune alma", "container id", "konteyner", "sample id", "örnek id",
    "physician", "hekim", "doctor", "organization", "kuruluş", "medical record",
    "full name", "tüp numarası", "number of tube",
]


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def is_summary(en, markers):
    """EN metni kit işaretçilerinden birini içeriyorsa 'özet' say (beyaz-liste)."""
    low = _norm(en).lower()
    return any(m.lower() in low for m in markers)


def deid_ok(en):
    """Hasta verisi içeriyorsa False (gönderilmez). Saf klinik özet ise True."""
    low = _norm(en).lower()
    if _DATE_RX.search(low):
        return False
    if _DIGIT_RUN_RX.search(low):
        return False
    if any(term in low for term in _PATIENT_TERMS):
        return False
    return True


def ai_eligible(en, markers):
    """Yalnız özet (beyaz-liste) VE de-id temiz ise AI'ya uygundur."""
    return is_summary(en, markers) and deid_ok(en)


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CACHE_PATH)


def cache_get(cache, en):
    return cache.get(_norm(en))


def cache_set(cache, en, tr):
    cache[_norm(en)] = tr
    _save_cache(cache)


GLOSSARY_PATH = os.path.join(HERE, "glossary.tsv")
GLOSSARY_STATE_PATH = os.path.join(HERE, "glossary_state.json")
POSTEDIT_PATH = os.path.join(HERE, "postedit.tsv")


def postedit_corrections():
    """postedit.tsv'den derlenmiş (regex, yerine) düzeltme çiftlerini döndür.
    Yalnız AI (DeepL) çıktısına uygulanır; DeepL'in Türkçe tampon-ünsüz hatalarını düzeltir.
    Hatalı satır (geçersiz regex) atlanır."""
    if not os.path.exists(POSTEDIT_PATH):
        return []
    out = []
    with open(POSTEDIT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#") or "\t" not in line:
                continue
            wrong, right = line.split("\t", 1)
            try:
                out.append((re.compile(wrong), right))
            except re.error:
                continue
    return out


def apply_postedit(text, corrections=None):
    """AI çevirisine çeviri-sonrası düzeltmeleri uygula (regex sırayla)."""
    if corrections is None:
        corrections = postedit_corrections()
    for rx, rep in corrections:
        text = rx.sub(rep, text)
    return text


def glossary_entries_tsv():
    """glossary.tsv'den 'EN\\tTR' satırlarını döndür (yorum/boş satır atlanır)."""
    if not os.path.exists(GLOSSARY_PATH):
        return ""
    out = []
    with open(GLOSSARY_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "\t" in line:
                out.append(line)
    return "\n".join(out)


def load_glossary_state():
    if os.path.exists(GLOSSARY_STATE_PATH):
        with open(GLOSSARY_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_glossary_state(state):
    tmp = GLOSSARY_STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, GLOSSARY_STATE_PATH)


def clear_cache():
    """AI önbelleğini sil (örn. glossary/terimler değişince eski çeviriler geçersiz)."""
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
