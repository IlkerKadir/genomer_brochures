"""translator.py — sağlayıcı-bağımsız harici çeviri arayüzü. İlk uygulama: DeepL."""
import json
import urllib.request
import urllib.parse


def _http_post_form(url, fields, headers, timeout=10):
    """form-encoded POST → JSON yanıt. (Testlerde monkeypatch'lenir.)"""
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


class DeepLProvider:
    def __init__(self, api_key):
        self.api_key = api_key

    def _endpoint(self):
        return ("https://api-free.deepl.com/v2/translate"
                if self.api_key.endswith(":fx")
                else "https://api.deepl.com/v2/translate")

    def translate(self, texts, target="TR"):
        fields = [("text", t) for t in texts]
        fields += [("target_lang", target), ("source_lang", "EN")]
        headers = {"Authorization": "DeepL-Auth-Key " + self.api_key}
        res = _http_post_form(self._endpoint(), fields, headers)
        return [t["text"] for t in res["translations"]]


def get_provider(config):
    """config'e göre Provider veya None (kapalı/anahtarsız/bilinmeyen)."""
    if not config.get("ai_summary_enabled"):
        return None
    provider = config.get("provider", "deepl")
    if provider == "deepl" and config.get("deepl_api_key"):
        return DeepLProvider(config["deepl_api_key"])
    return None
