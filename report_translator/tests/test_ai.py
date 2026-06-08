import os
import json
import aiconfig


def test_config_defaults_and_save_roundtrip(tmp_path, monkeypatch):
    cfgpath = str(tmp_path / "config.json")
    monkeypatch.setattr(aiconfig, "CONFIG_PATH", cfgpath)
    cfg = aiconfig.load_config()
    assert cfg["provider"] == "deepl"
    assert cfg["ai_summary_enabled"] is False
    assert cfg["deepl_api_key"] == ""
    assert cfg["target_lang"] == "TR"
    aiconfig.save_config({"ai_summary_enabled": True, "deepl_api_key": "k:fx"})
    cfg2 = aiconfig.load_config()
    assert cfg2["ai_summary_enabled"] is True
    assert cfg2["deepl_api_key"] == "k:fx"
    assert cfg2["provider"] == "deepl"   # diğer alanlar korunur


def test_public_config_hides_key(tmp_path, monkeypatch):
    monkeypatch.setattr(aiconfig, "CONFIG_PATH", str(tmp_path / "config.json"))
    aiconfig.save_config({"deepl_api_key": "secret:fx", "ai_summary_enabled": True})
    pub = aiconfig.public_config()
    assert "deepl_api_key" not in pub
    assert pub["has_key"] is True
    assert pub["ai_summary_enabled"] is True
    assert pub["provider"] == "deepl"


def test_is_summary_matches_markers():
    markers = ["Microbiota state", "Detected:", "NB!"]
    assert aiconfig.is_summary("Microbiota state – severe anaerobic dysbiosis: ...", markers)
    assert aiconfig.is_summary("Detected: HPV 16", markers)
    assert not aiconfig.is_summary("Yeast fungi", markers)
    assert not aiconfig.is_summary("Total Bacterial Load", markers)


def test_deid_blocks_patient_data():
    # tarih -> reddedilir
    assert not aiconfig.deid_ok("Microbiota state assessed on 25.09.2023")
    # hasta-alanı kelimesi -> reddedilir
    assert not aiconfig.deid_ok("Patient name: ... microbiota status")
    assert not aiconfig.deid_ok("Sample ID: Sample_1 conclusion")
    assert not aiconfig.deid_ok("Physician: Dr X. Microbiota state eubiosis")
    # uzun rakam dizisi (ID/barkod) -> reddedilir
    assert not aiconfig.deid_ok("Container 1234567 microbiota")
    # temiz klinik özet -> geçer
    assert aiconfig.deid_ok("Microbiota state – eubiosis: predominance of normal microbiota, "
                            "relative quantity of Lactobacillus spp. 100%, Bifidobacterium spp. <1%.")
    assert aiconfig.deid_ok("The bacterial microbiome composition is normal.")
    # yüzde/ondalık veri reddi TETİKLEMEZ
    assert aiconfig.deid_ok("Normal microbiota within the reference range – 99.9%, 8.5 GE/g.")


def test_ai_eligible_combines_both():
    markers = ["Microbiota state"]
    assert aiconfig.ai_eligible("Microbiota state – eubiosis: normal microbiota predominance.", markers)
    # marker eşleşir ama tarih var -> uygun değil
    assert not aiconfig.ai_eligible("Microbiota state on 01.02.2024", markers)


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(aiconfig, "CACHE_PATH", str(tmp_path / "ai_cache.json"))
    cache = aiconfig.load_cache()
    assert cache == {}
    aiconfig.cache_set(cache, "Microbiota state – eubiosis", "Mikrobiyota durumu – öbiyoz")
    cache2 = aiconfig.load_cache()
    assert cache2["Microbiota state – eubiosis"] == "Mikrobiyota durumu – öbiyoz"


def test_markers_loaded_from_dictionary():
    import dictionary
    kits, common, pt, raw = dictionary.load()
    markers = dictionary.ai_markers(raw, "femobiome_ii")
    assert any("Microbiota state" in m for m in markers)
    # _ai_markers, çeviri tablosuna sızmamalı (değer string olmalı)
    assert "_ai_markers" not in kits["femobiome_ii"]


import translator as tr_mod


def test_deepl_provider_request_and_parse(monkeypatch):
    captured = {}

    def fake_post(url, fields, headers, timeout=10):
        captured["url"] = url
        captured["fields"] = fields
        captured["headers"] = headers
        return {"translations": [{"text": "Mikrobiyota durumu"},
                                 {"text": "Patojen saptanmadı."}]}

    monkeypatch.setattr(tr_mod, "_http_post_form", fake_post)
    p = tr_mod.DeepLProvider("key:fx")
    out = p.translate(["Microbiota state", "No pathogens detected."])
    assert out == ["Mikrobiyota durumu", "Patojen saptanmadı."]
    # ücretsiz uç nokta (:fx)
    assert captured["url"] == "https://api-free.deepl.com/v2/translate"
    assert captured["headers"]["Authorization"] == "DeepL-Auth-Key key:fx"
    assert ("target_lang", "TR") in captured["fields"]
    assert ("text", "Microbiota state") in captured["fields"]


def test_deepl_pro_endpoint(monkeypatch):
    captured = {}
    monkeypatch.setattr(tr_mod, "_http_post_form",
                        lambda url, f, h, timeout=10: captured.update(url=url) or
                        {"translations": [{"text": "x"}]})
    tr_mod.DeepLProvider("prokey").translate(["a"])
    assert captured["url"] == "https://api.deepl.com/v2/translate"


def test_get_provider_disabled_or_no_key():
    assert tr_mod.get_provider({"ai_summary_enabled": False, "deepl_api_key": "k"}) is None
    assert tr_mod.get_provider({"ai_summary_enabled": True, "provider": "deepl",
                                "deepl_api_key": ""}) is None
    p = tr_mod.get_provider({"ai_summary_enabled": True, "provider": "deepl",
                             "deepl_api_key": "k:fx"})
    assert isinstance(p, tr_mod.DeepLProvider)


import engine


class FakeProvider:
    def __init__(self):
        self.received = []

    def translate(self, texts, target="TR"):
        self.received.append(list(texts))
        return ["[AI] " + t for t in texts]


def _seg(engine, sid, en, tr, source):
    s = engine.Segment(id=sid, page=0, bbox=[0, 0, 1, 1], en=en, fontfile="Arial-Regular.ttf",
                       size=8.0, color=(0, 0, 0), single_line=True, rects=[[0, 0, 1, 1]],
                       origin=(0, 0), raw_first=en, is_paragraph=False)
    return engine.AnnotatedSegment(s, tr, source, source == "unknown")


def test_apply_ai_summary_translates_only_eligible(tmp_path, monkeypatch):
    monkeypatch.setattr(aiconfig, "CACHE_PATH", str(tmp_path / "c.json"))
    markers = ["Microbiota state", "Detected:"]
    cache = {}
    prov = FakeProvider()
    ann = [
        _seg(engine, "0:1", "Microbiota state – severe dysbiosis: normobiota low.", "kısmi", "dict-partial"),
        _seg(engine, "0:2", "Yeast fungi", "Maya mantarları", "dict-exact"),          # özet değil
        _seg(engine, "0:3", "Detected: Sample ID: Sample_1", "...", "unknown"),         # de-id reddi
        _seg(engine, "0:4", "Detected: HPV 16", "Saptandı: HPV 16", "dict-partial"),
    ]
    engine.apply_ai_summary(ann, prov, markers, cache, deid=None)
    # yalnız 0:1 ve 0:4 AI'ya gitti (0:2 özet değil; 0:3 de-id reddi)
    sent = prov.received[0]
    assert "Microbiota state – severe dysbiosis: normobiota low." in sent
    assert "Detected: HPV 16" in sent
    assert all("Sample ID" not in s for s in sent)            # KRİTİK: hasta verisi gitmedi
    assert all("Yeast fungi" not in s for s in sent)
    assert ann[0].tr.startswith("[AI]") and ann[0].source == "ai"
    assert ann[3].tr.startswith("[AI]")
    assert ann[1].tr == "Maya mantarları"                     # dokunulmadı
    assert cache  # önbelleğe yazıldı


def test_apply_ai_summary_uses_cache_and_skips_provider():
    markers = ["Microbiota state"]
    cache = {"Microbiota state – eubiosis.": "ÖNBELLEK"}
    prov = FakeProvider()
    ann = [_seg(engine, "0:1", "Microbiota state – eubiosis.", "kısmi", "dict-partial")]
    engine.apply_ai_summary(ann, prov, markers, cache, deid=None)
    assert ann[0].tr == "ÖNBELLEK" and ann[0].source == "ai"
    assert prov.received == []                                # API çağrılmadı


def test_apply_ai_summary_fallback_on_error():
    markers = ["Microbiota state"]
    class Boom:
        def translate(self, texts, target="TR"): raise RuntimeError("offline")
    ann = [_seg(engine, "0:1", "Microbiota state – eubiosis.", "yerel-yedek", "dict-partial")]
    engine.apply_ai_summary(ann, Boom(), markers, {}, deid=None)
    assert ann[0].tr == "yerel-yedek"                         # yerel çeviri korundu


def test_config_endpoints_and_ai_in_flow(femobiome_dysbiosis_pdf, tmp_path, monkeypatch):
    import store
    monkeypatch.setattr(store, "DEFAULT_BASE", str(tmp_path / "sess"))
    monkeypatch.setattr(aiconfig, "CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setattr(aiconfig, "CACHE_PATH", str(tmp_path / "cache.json"))
    import importlib, app as app_mod
    importlib.reload(app_mod)
    app_mod.set_out_dir(str(tmp_path / "out"))
    # sahte sağlayıcı enjekte et
    import translator
    class Fake:
        def translate(self, texts, target="TR"): return ["[AI] " + t for t in texts]
    monkeypatch.setattr(translator, "get_provider", lambda cfg: Fake() if cfg.get("ai_summary_enabled") else None)

    from fastapi.testclient import TestClient
    c = TestClient(app_mod.app)

    # config: başta kapalı, anahtar yok
    assert c.get("/api/config").json()["ai_summary_enabled"] is False
    # config aç + anahtar gir
    c.post("/api/config", json={"ai_summary_enabled": True, "deepl_api_key": "k:fx"})
    pub = c.get("/api/config").json()
    assert pub["ai_summary_enabled"] is True and pub["has_key"] is True
    assert "deepl_api_key" not in pub

    # upload + manifest: özet segmenti AI ile çevrilmiş ("ai" source)
    # (eubiosis sonucu dict-exact olduğundan AI'ya gitmez; disbiyoz sonucu dict-partial -> uygun)
    with open(femobiome_dysbiosis_pdf, "rb") as fh:
        r = c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")}).json()
    s, f = r["session_id"], r["files"][0]["file_id"]
    man = c.get(f"/api/{s}/{f}/manifest").json()
    ai_segs = [m for m in man if m["source"] == "ai"]
    assert len(ai_segs) >= 1
    assert any(m["tr"].startswith("[AI]") for m in ai_segs)


def test_deepl_translate_with_glossary(monkeypatch):
    captured = {}
    monkeypatch.setattr(tr_mod, "_http_post_form",
                        lambda url, fields, headers, timeout=10: captured.update(url=url, fields=fields) or
                        {"translations": [{"text": "x"}]})
    p = tr_mod.DeepLProvider("k:fx", glossary_id="GID123")
    p.translate(["relative amount of X"])
    assert captured["url"] == "https://api-free.deepl.com/v2/translate"
    assert ("glossary_id", "GID123") in captured["fields"]
    assert ("source_lang", "EN") in captured["fields"]


def test_create_glossary_posts_and_parses(monkeypatch):
    captured = {}
    monkeypatch.setattr(tr_mod, "_http_post_form",
                        lambda url, fields, headers, timeout=10: captured.update(url=url, fields=dict(fields)) or
                        {"glossary_id": "G-NEW"})
    gid = tr_mod.create_glossary("k:fx", "genomer-terms", "relative amount\tgöreceli miktar")
    assert gid == "G-NEW"
    assert captured["url"] == "https://api-free.deepl.com/v2/glossaries"
    assert captured["fields"]["source_lang"] == "EN" and captured["fields"]["target_lang"] == "TR"
    assert captured["fields"]["entries_format"] == "tsv"
    assert "göreceli miktar" in captured["fields"]["entries"]


def test_ensure_glossary_caches_and_recreates(monkeypatch):
    calls = {"n": 0}
    def fake_create(api_key, name, entries, source="EN", target="TR"):
        calls["n"] += 1
        return "G-%d" % calls["n"]
    monkeypatch.setattr(tr_mod, "create_glossary", fake_create)
    state = {}
    g1 = tr_mod.ensure_glossary("k:fx", "a\tb", state)
    g2 = tr_mod.ensure_glossary("k:fx", "a\tb", state)   # aynı giriş -> tekrar oluşturmaz
    assert g1 == g2 and calls["n"] == 1
    g3 = tr_mod.ensure_glossary("k:fx", "a\tc", state)   # değişti -> yeniden oluştur
    assert g3 != g1 and calls["n"] == 2
    assert tr_mod.ensure_glossary("k:fx", "  ", state) is None  # boş giriş


def test_glossary_entries_from_file(tmp_path, monkeypatch):
    f = tmp_path / "glossary.tsv"
    f.write_text("# yorum\nrelative amount\tgöreceli miktar\n\neubiosis\töbiyoz\n", encoding="utf-8")
    monkeypatch.setattr(aiconfig, "GLOSSARY_PATH", str(f))
    tsv = aiconfig.glossary_entries_tsv()
    assert "relative amount\tgöreceli miktar" in tsv
    assert "eubiosis\töbiyoz" in tsv
    assert "# yorum" not in tsv


def test_deepl_translate_with_context(monkeypatch):
    captured = {}
    monkeypatch.setattr(tr_mod, "_http_post_form",
                        lambda url, fields, headers, timeout=10: captured.update(fields=fields) or
                        {"translations": [{"text": "x"}]})
    tr_mod.DeepLProvider("k:fx", context="clinical report").translate(["relative amount"])
    assert ("context", "clinical report") in captured["fields"]
    # context yokken gönderilmez
    captured.clear()
    monkeypatch.setattr(tr_mod, "_http_post_form",
                        lambda url, fields, headers, timeout=10: captured.update(fields=fields) or
                        {"translations": [{"text": "x"}]})
    tr_mod.DeepLProvider("k:fx").translate(["x"])
    assert not any(k == "context" for k, _ in captured["fields"])
