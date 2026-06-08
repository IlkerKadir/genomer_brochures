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
