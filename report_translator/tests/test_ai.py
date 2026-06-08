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
