import json
import os
import shutil
import subprocess
import sys
import fitz
import importlib

HERE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.normpath(os.path.join(HERE, ".."))


def test_cli_translates_to_file(femobiome_pdf, tmp_path):
    out = tmp_path / "cikti_TR.pdf"
    r = subprocess.run([sys.executable, "translate_report.py", femobiome_pdf,
                        "-o", str(out)], cwd=RT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.exists()
    assert "Maya mantarları" in fitz.open(str(out))[0].get_text()


from fastapi.testclient import TestClient
import store
import app as app_mod


def _isolated_client(monkeypatch, tmp_path):
    """Store'u tmp'ye izole et, app'i yeniden yükle, TestClient döndür."""
    sess_dir = str(tmp_path / "sess")
    monkeypatch.setattr(store, "DEFAULT_BASE", sess_dir)
    importlib.reload(app_mod)
    app_mod.set_out_dir(str(tmp_path / "out"))
    return TestClient(app_mod.app)


def test_upload_manifest_edit_save_flow(femobiome_pdf, tmp_path, monkeypatch):
    c = _isolated_client(monkeypatch, tmp_path)
    with open(femobiome_pdf, "rb") as fh:
        r = c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    s = body["session_id"]
    f = body["files"][0]["file_id"]
    assert body["files"][0]["kit"] == "femobiome_ii"
    assert body["files"][0]["counts"]["translated"] > 0

    # manifest
    m = c.get(f"/api/{s}/{f}/manifest").json()
    seg = next(x for x in m if x["en"] == "Yeast fungi")
    assert seg["tr"] == "Maya mantarları"

    # sayfa görüntüsü
    png = c.get(f"/api/{s}/{f}/page/0.png")
    assert png.status_code == 200 and png.content[:8] == b"\x89PNG\r\n\x1a\n"

    # segment düzelt (sadece bu rapor)
    e = c.post(f"/api/{s}/{f}/segment/{seg['id']}",
               json={"tr": "ÖZELMAYA", "scope": "report"})
    assert e.status_code == 200 and e.json()["ok"]

    # kaydet -> diske yazılır ve override yansır
    sv = c.post(f"/api/{s}/{f}/save").json()
    assert os.path.exists(sv["saved_path"])
    assert "ÖZELMAYA" in fitz.open(sv["saved_path"])[0].get_text()


def test_edit_segment_conflict_and_force(femobiome_pdf, tmp_path, monkeypatch):
    """scope=dict, force=False → conflict; force=True → dictionary.json güncellenir."""
    import dictionary

    # Gerçek dictionary.json'u kirletmemek için geçici kopya kullan
    real_path = dictionary.DICT_PATH
    tmp_dict = tmp_path / "dictionary.json"
    shutil.copy(real_path, tmp_dict)

    # dictionary modülünü geçici path ile çalıştır
    monkeypatch.setattr(dictionary, "DICT_PATH", str(tmp_dict))

    # Mevcut bir segment olan "Yeast fungi" / "Maya mantarları" üzerine çakışma testi
    UNIQUE_EN = "__test_conflict_key__"
    # Önce unique key'i dict'e ekle (baseline)
    res = dictionary.add_entry("femobiome_ii", UNIQUE_EN, "İlk Çeviri", path=str(tmp_dict))
    assert res["ok"]

    c = _isolated_client(monkeypatch, tmp_path)

    with open(femobiome_pdf, "rb") as fh:
        up = c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    assert up.status_code == 200
    body = up.json()
    sess = body["session_id"]
    fid = body["files"][0]["file_id"]

    # Hangi segment id'sinin "Yeast fungi" olduğunu bul
    manifest = c.get(f"/api/{sess}/{fid}/manifest").json()
    seg = next((x for x in manifest if x["en"] == "Yeast fungi"), None)
    assert seg is not None, "Yeast fungi segmenti bulunamadı"

    # force=False → conflict bekleniyor
    r1 = c.post(f"/api/{sess}/{fid}/segment/{seg['id']}",
                json={"tr": "Farkli Maya", "scope": "dict", "force": False})
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1.get("conflict") is True, f"Çakışma beklendi ama gelmedi: {data1}"
    assert data1["existing"] == "Maya mantarları"
    assert data1["en"] == "Yeast fungi"

    # force=True → sözlüğe yazılmalı
    r2 = c.post(f"/api/{sess}/{fid}/segment/{seg['id']}",
                json={"tr": "Farkli Maya", "scope": "dict", "force": True})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2.get("ok") is True
    assert not data2.get("conflict"), f"force=True'de çakışma döndü: {data2}"

    # dictionary.json (tmp kopyası) güncellendi mi?
    updated = json.loads(tmp_dict.read_text(encoding="utf-8"))
    assert updated["femobiome_ii"]["Yeast fungi"] == "Farkli Maya"

    # Gerçek dictionary.json dokunulmadı
    real_data = json.loads(open(real_path, encoding="utf-8").read())
    assert real_data["femobiome_ii"]["Yeast fungi"] == "Maya mantarları"


# ---- I-1: Yükleme sonrası otomatik kaydet ----
def test_upload_auto_saves(femobiome_pdf, tmp_path, monkeypatch):
    """Upload sonrası arka planda kayıt yapılır; /save ile explicit kaydedince dosya oluşur."""
    c = _isolated_client(monkeypatch, tmp_path)
    with open(femobiome_pdf, "rb") as fh:
        r = c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    s = body["session_id"]
    f = body["files"][0]["file_id"]
    # status ucu çalışmalı
    st = c.get(f"/api/{s}/status").json()
    assert st["files"][f]["status"] in ("done", "pending"), \
        f"Beklenmedik status: {st['files'][f]['status']}"
    # Explicit kaydet -> diske yazılmalı
    sv = c.post(f"/api/{s}/{f}/save").json()
    assert sv["ok"] is True
    assert sv["saved_path"] is not None
    assert os.path.exists(sv["saved_path"]), f"Dosya diskte yok: {sv['saved_path']}"


# ---- I-2: review.txt uç noktası ----
def test_review_txt_endpoint(femobiome_pdf, tmp_path, monkeypatch):
    """GET /api/{s}/{f}/review.txt 200 + düz metin döner; başlık içerir."""
    c = _isolated_client(monkeypatch, tmp_path)
    with open(femobiome_pdf, "rb") as fh:
        r = c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    body = r.json()
    s = body["session_id"]
    f = body["files"][0]["file_id"]

    rv = c.get(f"/api/{s}/{f}/review.txt")
    assert rv.status_code == 200
    text = rv.text
    assert "# Gözden geçirilecek" in text, "Başlık eksik"
    assert "Content-Disposition" in rv.headers
    assert "_review.txt" in rv.headers["Content-Disposition"]


# ---- I-3: GET /api/out_dir ve POST /api/out_dir ----
def test_get_and_set_out_dir(tmp_path, monkeypatch):
    """GET /api/out_dir mevcut yolu döner; POST /api/out_dir yolu günceller."""
    c = _isolated_client(monkeypatch, tmp_path)

    r_get = c.get("/api/out_dir")
    assert r_get.status_code == 200
    assert r_get.json()["out_dir"] == str(tmp_path / "out")

    new_dir = str(tmp_path / "yeni_klasor")
    r_post = c.post("/api/out_dir", json={"path": new_dir})
    assert r_post.status_code == 200
    assert r_post.json()["ok"] is True
    assert r_post.json()["out_dir"] == new_dir
    assert os.path.isdir(new_dir)


def test_upload_async_status_and_persistence(femobiome_pdf, tmp_path, monkeypatch):
    c = _isolated_client(monkeypatch, tmp_path)
    with open(femobiome_pdf, "rb") as fh:
        r = c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    body = r.json()
    s, f = body["session_id"], body["files"][0]["file_id"]
    # status done olana kadar (senkron işleniyorsa zaten done)
    st = c.get(f"/api/{s}/status").json()
    assert st["files"][f]["status"] in ("done", "pending")
    # original ve TR sayfa render uçları
    assert c.get(f"/api/{s}/{f}/page/0.png").content[:8] == b"\x89PNG\r\n\x1a\n"
    assert c.get(f"/api/{s}/{f}/original/0.png").content[:8] == b"\x89PNG\r\n\x1a\n"
    # revert: önce override koy, sonra revert et
    seg = next(x for x in c.get(f"/api/{s}/{f}/manifest").json() if x["en"] == "Yeast fungi")
    c.post(f"/api/{s}/{f}/segment/{seg['id']}", json={"tr": "X", "scope": "report"})
    c.post(f"/api/{s}/{f}/segment/{seg['id']}", json={"tr": "", "scope": "revert"})
    m2 = c.get(f"/api/{s}/{f}/manifest").json()
    assert next(x for x in m2 if x["id"] == seg["id"])["tr"] == "Maya mantarları"


def test_sessions_listing_and_error(femobiome_pdf, tmp_path, monkeypatch):
    c = _isolated_client(monkeypatch, tmp_path)
    with open(femobiome_pdf, "rb") as fh:
        c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    sess = c.get("/api/sessions").json()
    assert len(sess["sessions"]) >= 1
    # bilinmeyen oturum -> yapısal hata
    r = c.get("/api/yok/zzz/manifest")
    assert r.status_code == 404
    assert "error" in r.json()
