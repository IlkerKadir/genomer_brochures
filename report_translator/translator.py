"""translator.py — sağlayıcı-bağımsız harici çeviri arayüzü. İlk uygulama: DeepL (glossary destekli)."""
import json
import hashlib
import urllib.request
import urllib.parse


def _http_post_form(url, fields, headers, timeout=10):
    """form-encoded POST → JSON yanıt. (Testlerde monkeypatch'lenir.)"""
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _base(api_key):
    return ("https://api-free.deepl.com/v2" if api_key.endswith(":fx")
            else "https://api.deepl.com/v2")


def _auth(api_key):
    return {"Authorization": "DeepL-Auth-Key " + api_key}


class DeepLProvider:
    def __init__(self, api_key, glossary_id=None):
        self.api_key = api_key
        self.glossary_id = glossary_id

    def translate(self, texts, target="TR"):
        fields = [("text", t) for t in texts]
        fields += [("target_lang", target), ("source_lang", "EN")]
        if self.glossary_id:
            fields.append(("glossary_id", self.glossary_id))   # standart terimleri zorla
        res = _http_post_form(_base(self.api_key) + "/translate", fields, _auth(self.api_key))
        return [t["text"] for t in res["translations"]]


def create_glossary(api_key, name, entries_tsv, source="EN", target="TR"):
    """DeepL'de glossary oluştur, glossary_id döndür."""
    fields = [("name", name), ("source_lang", source), ("target_lang", target),
              ("entries", entries_tsv), ("entries_format", "tsv")]
    res = _http_post_form(_base(api_key) + "/glossaries", fields, _auth(api_key))
    return res["glossary_id"]


def entries_hash(entries_tsv):
    return hashlib.sha256(entries_tsv.encode("utf-8")).hexdigest()[:16]


def ensure_glossary(api_key, entries_tsv, state):
    """Girişler değişmediyse mevcut glossary_id'yi kullan; değiştiyse yeniden oluştur.
    state = {"hash":..., "glossary_id":...} (yerinde güncellenir). Hata/boş giriş -> None."""
    if not entries_tsv.strip():
        return None
    h = entries_hash(entries_tsv)
    if state.get("hash") == h and state.get("glossary_id"):
        return state["glossary_id"]
    gid = create_glossary(api_key, "genomer-terms", entries_tsv)
    state["hash"] = h
    state["glossary_id"] = gid
    return gid


def get_provider(config):
    """config'e göre Provider veya None (kapalı/anahtarsız/bilinmeyen)."""
    if not config.get("ai_summary_enabled"):
        return None
    provider = config.get("provider", "deepl")
    if provider == "deepl" and config.get("deepl_api_key"):
        return DeepLProvider(config["deepl_api_key"])
    return None
