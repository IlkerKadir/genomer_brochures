import os
import subprocess
import sys
import fitz

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
import app as app_mod


def _client():
    return TestClient(app_mod.app)


def test_upload_manifest_edit_save_flow(femobiome_pdf, tmp_path):
    c = _client()
    app_mod.set_out_dir(str(tmp_path))  # testte çıktı klasörünü izole et
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
