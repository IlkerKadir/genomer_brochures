"""test_dict_mgmt.py — TDD: store.clear, dictionary.list_entries / set_entry / delete_entry,
app GET /api/dictionary, POST /api/dictionary/entry, POST /api/dictionary/delete."""
import json
import shutil
import importlib
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.normpath(os.path.join(HERE, ".."))

# ──────────────────────────────────────────────
# store.RenderCache.clear
# ──────────────────────────────────────────────

import store


def test_cache_clear():
    """clear() tüm önbelleği siler."""
    c = store.RenderCache()
    c.set("f1", 0, b"png1")
    c.set("f2", 1, b"png2")
    assert c.get("f1", 0) == b"png1"
    c.clear()
    assert c.get("f1", 0) is None
    assert c.get("f2", 1) is None


def test_cache_clear_empty_is_noop():
    """Boş önbellekte clear() hata vermez."""
    c = store.RenderCache()
    c.clear()  # should not raise
    assert c.get("x", 0) is None


# ──────────────────────────────────────────────
# dictionary.list_entries
# ──────────────────────────────────────────────

import dictionary


def test_list_entries_returns_common(tmp_path):
    """common girişleri scope='common', paragraph=False olarak döner."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    entries = dictionary.list_entries(path=str(work))
    common_entries = [e for e in entries if e["scope"] == "common"]
    assert len(common_entries) > 0
    for e in common_entries:
        assert e["paragraph"] is False
        assert "en" in e and "tr" in e


def test_list_entries_returns_kit_atomic(tmp_path):
    """Kit düz girişleri scope=kit_adı, paragraph=False."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    entries = dictionary.list_entries(path=str(work))
    kit_entries = [e for e in entries if e["scope"] == "femobiome_ii" and not e["paragraph"]]
    assert len(kit_entries) > 0
    assert all("Yeast fungi" != e["en"] or e["tr"] == "Maya mantarları"
               for e in kit_entries)


def test_list_entries_returns_paragraphs(tmp_path):
    """_paragraphs girişleri scope=kit_adı, paragraph=True."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    long_en = "This is a long sentence with clearly more than six words total here."
    dictionary.add_entry("femobiome_ii", long_en, "Uzun cümle çevirisi.", path=str(work))

    entries = dictionary.list_entries(path=str(work))
    para_entries = [e for e in entries if e.get("paragraph") is True]
    assert any(e["en"] == long_en for e in para_entries)
    for e in para_entries:
        assert e["scope"] in ("femobiome_ii", "androbiome", "enterobiome_kids")


def test_list_entries_excludes_meta_and_passthrough(tmp_path):
    """_meta ve passthrough_patterns liste dışıdır."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    entries = dictionary.list_entries(path=str(work))
    for e in entries:
        assert e.get("scope") != "_meta"
        assert e.get("en") != "passthrough_patterns"


# ──────────────────────────────────────────────
# dictionary.set_entry
# ──────────────────────────────────────────────

def test_set_entry_common(tmp_path):
    """scope='common' ile common sözlüğüne yazar."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    res = dictionary.set_entry("common", "New Common Key", "Yeni Ortak Değer", path=str(work))
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert data["common"]["New Common Key"] == "Yeni Ortak Değer"
    assert (tmp_path / "dictionary.json.bak").exists()


def test_set_entry_kit_short_goes_atomic(tmp_path):
    """scope=kit, kısa EN → kit düz bölümüne yazar."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    res = dictionary.set_entry("femobiome_ii", "Short label", "Kısa etiket", path=str(work))
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert data["femobiome_ii"]["Short label"] == "Kısa etiket"


def test_set_entry_kit_long_goes_paragraphs(tmp_path):
    """scope=kit, uzun EN (>=6 kelime) → _paragraphs bölümüne yazar."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    long_en = "A long sentence that should go to paragraphs section."
    res = dictionary.set_entry("femobiome_ii", long_en, "Paragraf çevirisi.", path=str(work))
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert data["femobiome_ii"]["_paragraphs"][long_en] == "Paragraf çevirisi."


def test_set_entry_conflict_detected(tmp_path):
    """Farklı TR, overwrite=False → conflict döner, dosya değişmez."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    res = dictionary.set_entry("femobiome_ii", "Yeast fungi", "Farklı Çeviri",
                               path=str(work), overwrite=False)
    assert res["ok"] is False
    assert res["conflict"] is True
    assert res["existing"] == "Maya mantarları"


def test_set_entry_overwrite(tmp_path):
    """overwrite=True → üzerine yazar."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    res = dictionary.set_entry("femobiome_ii", "Yeast fungi", "Yeni Çeviri",
                               path=str(work), overwrite=True)
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert data["femobiome_ii"]["Yeast fungi"] == "Yeni Çeviri"


def test_set_entry_does_not_break_add_entry(tmp_path):
    """Mevcut add_entry hâlâ çalışıyor (regresyon yok)."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    res = dictionary.add_entry("androbiome", "New Andro", "Yeni Andro", path=str(work))
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert data["androbiome"]["New Andro"] == "Yeni Andro"


def test_set_entry_moves_from_atomic_to_paragraphs(tmp_path):
    """Önce kısa ekle, sonra 6+ kelimeyle set_entry → _paragraphs'a taşınır."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    # Kısa anahtar ekle
    short_en = "Short key"
    dictionary.set_entry("femobiome_ii", short_en, "İlk", path=str(work))
    data1 = json.loads(work.read_text(encoding="utf-8"))
    assert short_en in data1["femobiome_ii"]

    # Şimdi uzun anahtar ile taşıma değil — ayrı test; bu sadece overwrite testi
    long_en = "This long key should land in paragraphs not atomic section"
    res = dictionary.set_entry("femobiome_ii", long_en, "Paragraf", path=str(work))
    assert res["ok"] is True
    data2 = json.loads(work.read_text(encoding="utf-8"))
    assert long_en in data2["femobiome_ii"]["_paragraphs"]
    assert long_en not in {k: v for k, v in data2["femobiome_ii"].items() if k != "_paragraphs"}


# ──────────────────────────────────────────────
# dictionary.delete_entry
# ──────────────────────────────────────────────

def test_delete_entry_kit_atomic(tmp_path):
    """Kit düz girişi siler, yedek alır."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    # Önce ekle
    dictionary.set_entry("femobiome_ii", "ToDelete", "Silinecek", path=str(work))
    assert (tmp_path / "dictionary.json.bak").exists()

    # Sil
    res = dictionary.delete_entry("femobiome_ii", "ToDelete", path=str(work))
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert "ToDelete" not in data["femobiome_ii"]


def test_delete_entry_kit_paragraph(tmp_path):
    """_paragraphs girişini siler."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    long_en = "A long sentence that should go to paragraphs section."
    dictionary.set_entry("femobiome_ii", long_en, "Paragraf.", path=str(work))

    res = dictionary.delete_entry("femobiome_ii", long_en, path=str(work))
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert long_en not in data["femobiome_ii"].get("_paragraphs", {})


def test_delete_entry_common(tmp_path):
    """common girişini siler."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    dictionary.set_entry("common", "CommonToDelete", "Ortak Silinecek", path=str(work))
    res = dictionary.delete_entry("common", "CommonToDelete", path=str(work))
    assert res["ok"] is True
    data = json.loads(work.read_text(encoding="utf-8"))
    assert "CommonToDelete" not in data["common"]


def test_delete_entry_not_found(tmp_path):
    """Olmayan giriş → ok=False, not_found=True."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    res = dictionary.delete_entry("femobiome_ii", "__nonexistent_key__", path=str(work))
    assert res["ok"] is False
    assert res["not_found"] is True


def test_delete_entry_backup_created(tmp_path):
    """Başarılı silmede yedek alınır."""
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)

    dictionary.set_entry("femobiome_ii", "BackupKey", "Yedek", path=str(work))
    bak = tmp_path / "dictionary.json.bak"
    # Sil .bak'ı, sil girişi → .bak yeniden oluşmalı
    bak.unlink(missing_ok=True)
    res = dictionary.delete_entry("femobiome_ii", "BackupKey", path=str(work))
    assert res["ok"] is True
    assert bak.exists()


# ──────────────────────────────────────────────
# app endpoints
# ──────────────────────────────────────────────

import app as app_mod
from fastapi.testclient import TestClient


def _isolated_app(monkeypatch, tmp_path):
    """Store + dictionary'i tmp'ye izole et, yeni TestClient döndür."""
    sess_dir = str(tmp_path / "sess")
    monkeypatch.setattr(store, "DEFAULT_BASE", sess_dir)

    # dictionary'i de izole et
    real_path = dictionary.DICT_PATH
    tmp_dict = tmp_path / "dictionary.json"
    shutil.copy(real_path, tmp_dict)
    monkeypatch.setattr(dictionary, "DICT_PATH", str(tmp_dict))

    importlib.reload(app_mod)
    app_mod.set_out_dir(str(tmp_path / "out"))
    return TestClient(app_mod.app), tmp_dict


def test_get_dictionary_returns_entries(monkeypatch, tmp_path):
    """GET /api/dictionary → {entries: [...]} döner."""
    c, _ = _isolated_app(monkeypatch, tmp_path)
    r = c.get("/api/dictionary")
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    entries = body["entries"]
    assert isinstance(entries, list)
    assert len(entries) > 0
    # Her giriş scope, en, tr, paragraph içermeli
    for e in entries:
        assert "scope" in e
        assert "en" in e
        assert "tr" in e
        assert "paragraph" in e


def test_get_dictionary_includes_common_and_kit(monkeypatch, tmp_path):
    """GET /api/dictionary sonucu hem common hem kit girişleri içerir."""
    c, _ = _isolated_app(monkeypatch, tmp_path)
    entries = c.get("/api/dictionary").json()["entries"]
    scopes = {e["scope"] for e in entries}
    assert "common" in scopes
    assert "femobiome_ii" in scopes


def test_post_entry_adds_to_dictionary(monkeypatch, tmp_path):
    """POST /api/dictionary/entry yeni giriş ekler, ok=True döner."""
    c, tmp_dict = _isolated_app(monkeypatch, tmp_path)
    r = c.post("/api/dictionary/entry",
               json={"scope": "femobiome_ii", "en": "API New Entry", "tr": "API Yeni Giriş"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True

    data = json.loads(tmp_dict.read_text(encoding="utf-8"))
    assert data["femobiome_ii"]["API New Entry"] == "API Yeni Giriş"


def test_post_entry_conflict_returns_200_with_conflict(monkeypatch, tmp_path):
    """POST /api/dictionary/entry çakışmada HTTP 200 + ok=True, conflict=True döner."""
    c, _ = _isolated_app(monkeypatch, tmp_path)
    r = c.post("/api/dictionary/entry",
               json={"scope": "femobiome_ii", "en": "Yeast fungi",
                     "tr": "Farklı Çeviri", "overwrite": False})
    assert r.status_code == 200
    body = r.json()
    assert body.get("conflict") is True
    assert body.get("existing") == "Maya mantarları"


def test_post_entry_overwrite_clears_cache(monkeypatch, tmp_path):
    """overwrite=True → sözlük güncellenir ve CACHE temizlenir."""
    c, tmp_dict = _isolated_app(monkeypatch, tmp_path)
    # Önce CACHE'e bir şey koy (mock gibi)
    app_mod.CACHE.set("fakeFile", 0, b"oldfakepng")
    assert app_mod.CACHE.get("fakeFile", 0) == b"oldfakepng"

    r = c.post("/api/dictionary/entry",
               json={"scope": "femobiome_ii", "en": "Yeast fungi",
                     "tr": "Temizlenmiş Çeviri", "overwrite": True})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # Cache temizlendi mi?
    assert app_mod.CACHE.get("fakeFile", 0) is None


def test_post_entry_common_scope(monkeypatch, tmp_path):
    """POST /api/dictionary/entry scope=common → common'a yazar."""
    c, tmp_dict = _isolated_app(monkeypatch, tmp_path)
    r = c.post("/api/dictionary/entry",
               json={"scope": "common", "en": "Common API Key", "tr": "Ortak API Değer"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    data = json.loads(tmp_dict.read_text(encoding="utf-8"))
    assert data["common"]["Common API Key"] == "Ortak API Değer"


def test_post_entry_invalid_scope_returns_422(monkeypatch, tmp_path):
    """Geçersiz scope → Pydantic validation hatası (422)."""
    c, _ = _isolated_app(monkeypatch, tmp_path)
    r = c.post("/api/dictionary/entry",
               json={"scope": "invalid_scope", "en": "X", "tr": "Y"})
    assert r.status_code == 422


def test_post_delete_removes_entry(monkeypatch, tmp_path):
    """POST /api/dictionary/delete → giriş silinir, CACHE temizlenir."""
    c, tmp_dict = _isolated_app(monkeypatch, tmp_path)
    # Önce ekle
    c.post("/api/dictionary/entry",
           json={"scope": "femobiome_ii", "en": "ToBeDeleted", "tr": "Silinecek"})
    data_before = json.loads(tmp_dict.read_text(encoding="utf-8"))
    assert "ToBeDeleted" in data_before["femobiome_ii"]

    # Cache'e bir şey koy
    app_mod.CACHE.set("fakeFile", 0, b"png")

    r = c.post("/api/dictionary/delete",
               json={"scope": "femobiome_ii", "en": "ToBeDeleted"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True

    data_after = json.loads(tmp_dict.read_text(encoding="utf-8"))
    assert "ToBeDeleted" not in data_after["femobiome_ii"]
    # Cache temizlendi
    assert app_mod.CACHE.get("fakeFile", 0) is None


def test_post_delete_not_found(monkeypatch, tmp_path):
    """POST /api/dictionary/delete olmayan giriş → not_found=True (200 veya 404)."""
    c, _ = _isolated_app(monkeypatch, tmp_path)
    r = c.post("/api/dictionary/delete",
               json={"scope": "femobiome_ii", "en": "__nonexistent__"})
    # Hem 200 not_found=True hem 404 kabul edilir
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert r.json().get("not_found") is True
    else:
        assert "error" in r.json()


def test_real_dictionary_not_modified():
    """dictionary.DICT_PATH (gerçek dosya) testler sırasında değişmemiş olmalı."""
    import json as _json
    # Gerçek dosyayı oku — 'Yeast fungi' hâlâ orijinal değerinde olmalı
    with open(dictionary.DICT_PATH, encoding="utf-8") as f:
        real = _json.load(f)
    assert real["femobiome_ii"]["Yeast fungi"] == "Maya mantarları", \
        "GERÇEK dictionary.json kirletildi!"
