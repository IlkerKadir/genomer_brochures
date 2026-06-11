"""translator.py — sağlayıcı-bağımsız harici çeviri arayüzü. İlk uygulama: DeepL (glossary destekli)."""
import json
import ssl
import hashlib
import urllib.request
import urllib.parse

_SSL_CTX = None
_SSL_OPTS = {"ca_file": None, "insecure": False}


def configure_ssl(ca_file=None, insecure=False):
    """SSL davranışını ayarla (config'ten). ca_file: kurumsal kök CA (.pem) yolu;
    insecure: True ise doğrulama kapatılır (son çare, yalnız de-id özet gönderilir).
    Bağlamı yeniden kurar."""
    global _SSL_CTX, _SSL_OPTS
    _SSL_OPTS = {"ca_file": (ca_file or None), "insecure": bool(insecure)}
    _SSL_CTX = None


def _base_ctx():
    """Standart doğrulama bağlamı: truststore (OS deposu) -> certifi -> varsayılan."""
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    return ssl.create_default_context()


def _ssl_context():
    """HTTPS doğrulama bağlamı (bir kez kurulur, önbelleğe alınır).
    - insecure: doğrulama kapalı (kurumsal proxy/AV kökü hiçbir yerde güvenilir değilse son çare).
    - ca_file: standart CA'lara EK olarak kurumsal kök yüklenir (önerilen kurumsal çözüm).
    - aksi halde: OS deposu (truststore) / certifi / varsayılan."""
    global _SSL_CTX
    if _SSL_CTX is not None:
        return _SSL_CTX
    if _SSL_OPTS["insecure"]:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _SSL_CTX = ctx
        return ctx
    if _SSL_OPTS["ca_file"]:
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()
        try:
            ctx.load_verify_locations(cafile=_SSL_OPTS["ca_file"])
        except Exception:
            pass
        _SSL_CTX = ctx
        return ctx
    _SSL_CTX = _base_ctx()
    return _SSL_CTX


def _http_post_form(url, fields, headers, timeout=10):
    """form-encoded POST → JSON yanıt. (Testlerde monkeypatch'lenir.)"""
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        return json.load(resp)


def _base(api_key):
    return ("https://api-free.deepl.com/v2" if api_key.endswith(":fx")
            else "https://api.deepl.com/v2")


def _auth(api_key):
    return {"Authorization": "DeepL-Auth-Key " + api_key}


class DeepLProvider:
    def __init__(self, api_key, glossary_id=None, context=None):
        self.api_key = api_key
        self.glossary_id = glossary_id
        self.context = context

    def translate(self, texts, target="TR"):
        fields = [("text", t) for t in texts]
        fields += [("target_lang", target), ("source_lang", "EN")]
        if self.glossary_id:
            fields.append(("glossary_id", self.glossary_id))   # standart terimleri zorla
        if self.context:
            fields.append(("context", self.context))           # klinik domain bağlamı
        res = _http_post_form(_base(self.api_key) + "/translate", fields, _auth(self.api_key))
        return [t["text"] for t in res["translations"]]


def create_glossary(api_key, name, entries_tsv, source="EN", target="TR"):
    """DeepL'de glossary oluştur, glossary_id döndür."""
    fields = [("name", name), ("source_lang", source), ("target_lang", target),
              ("entries", entries_tsv), ("entries_format", "tsv")]
    res = _http_post_form(_base(api_key) + "/glossaries", fields, _auth(api_key))
    return res["glossary_id"]


def delete_glossary(api_key, glossary_id):
    """Bir glossary'yi sil (DeepL hesap limiti: ücretsiz katman tek glossary'ye izin verir;
    yeni oluşturmadan önce eskisini silmek gerekir, yoksa 'Too many glossaries')."""
    req = urllib.request.Request(_base(api_key) + "/glossaries/" + glossary_id,
                                 headers=_auth(api_key), method="DELETE")
    with urllib.request.urlopen(req, timeout=10, context=_ssl_context()):
        return True


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
    # Girişler değişti -> eski glossary'yi sil (DeepL ücretsiz katman tek glossary'ye izin verir;
    # silmeden yeni oluşturmak 'Too many glossaries' (456) hatası verir).
    old = state.get("glossary_id")
    if old:
        try:
            delete_glossary(api_key, old)
        except Exception:
            pass
    gid = create_glossary(api_key, "genomer-terms", entries_tsv)
    state["hash"] = h
    state["glossary_id"] = gid
    return gid


def get_provider(config):
    """config'e göre Provider veya None (kapalı/anahtarsız/bilinmeyen)."""
    if not config.get("ai_summary_enabled"):
        return None
    configure_ssl(config.get("deepl_ca_file"), config.get("deepl_insecure_ssl"))
    provider = config.get("provider", "deepl")
    if provider == "deepl" and config.get("deepl_api_key"):
        return DeepLProvider(config["deepl_api_key"])
    return None
