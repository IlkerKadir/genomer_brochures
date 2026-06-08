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
