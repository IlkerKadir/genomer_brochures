# Rapor Çevirici Production'a Geçiş — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Çalışan ama demo-seviyesi rapor çevirici web uygulamasını production-ready hâle getirmek: tek-sayfa render + önbellek, oturum kalıcılığı, async ilerleme, sağlam hatalar (backend); Vite+Preact SPA ile profesyonel UX ve zengin editör (frontend); PyWebView + PyInstaller paketleme.

**Architecture:** FastAPI backend `store.py` ile disk-kalıcı oturum + render önbelleği kazanır; `engine.py` tek-sayfa render alır. Frontend `frontend/` altında Vite+Preact (signals) olarak yeniden inşa edilir, `web/`'e build edilip FastAPI tarafından servis edilir. Orijinal PDF tek doğru kaynak ilkesi korunur. `launcher.py` PyWebView penceresi açar; PyInstaller tek dosya üretir.

**Tech Stack:** Python 3, PyMuPDF, FastAPI, uvicorn, pytest, httpx; Vite, Preact, @preact/signals, Vitest; PyWebView, PyInstaller.

---

## Dosya yapısı

```
report_translator/
  engine.py            # MODIFY: render'ı _render_page_items'a böl + render_page_png ekle
  store.py             # CREATE: RenderCache + disk oturum kalıcılığı
  app.py               # MODIFY: store entegrasyonu, async upload+status, original png, revert, sessions, yapısal hata
  dictionary.py        # değişmez
  translate_report.py  # değişmez (CLI)
  tests/
    test_engine.py     # MODIFY: render_page testleri
    test_store.py      # CREATE
    test_app.py        # MODIFY: yeni uç testleri
  frontend/            # CREATE: Vite+Preact kaynak
    package.json, vite.config.js, index.html, vitest.config.js
    src/main.jsx, src/app.jsx
    src/api/client.js
    src/state/store.js
    src/components/*.jsx
    src/styles/*.css
    src/state/store.test.js, src/api/client.test.js
  web/                 # frontend build çıktısı (FastAPI servis eder)
  launcher.py          # CREATE: PyWebView + uvicorn
  requirements.txt     # MODIFY: pywebview ekle
  build_app.md         # MODIFY: frontend build + PyInstaller
  baslat.command/.bat  # MODIFY: web/ build edilmiş varsa sunar
```

> **Yürütme sırası:** Faz 1 (Task 1-3 backend) → Faz 2 (Task 4-10 frontend) → Faz 3 (Task 11-13 paketleme/doğrulama).

---

# FAZ 1 — Backend sertleştirme

## Task 1: engine.py — tek-sayfa render

**Files:**
- Modify: `report_translator/engine.py`
- Test: `report_translator/tests/test_engine.py`

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/tests/test_engine.py` sonuna ekle:
```python
def test_render_page_png_matches_full_render(femobiome_pdf):
    table, passthrough = _table()
    with open(femobiome_pdf, "rb") as fh:
        pdf_bytes = fh.read()
    # tek-sayfa render PNG üretir
    png0 = engine.render_page_png(pdf_bytes, table, passthrough, {}, 0)
    assert png0[:8] == b"\x89PNG\r\n\x1a\n"
    # tek-sayfa render'daki metin, tam-belge render'daki sayfa 0 metniyle aynı olmalı
    full = engine.translate_document_bytes(pdf_bytes, table, passthrough, {})
    full_doc = fitz.open(stream=full, filetype="pdf")
    page0_png_via_full = full_doc[0].get_pixmap(dpi=150).tobytes("png")
    # bayt-bayt eşitlik kırılgan; bunun yerine metin eşitliğini doğrula
    import fitz as _f
    doc_single = _f.open(stream=engine.translate_one_page_bytes(pdf_bytes, table, passthrough, {}, 0), filetype="pdf")
    assert "Maya mantarları" in doc_single[0].get_text()


def test_render_page_original(femobiome_pdf):
    table, passthrough = _table()
    with open(femobiome_pdf, "rb") as fh:
        pdf_bytes = fh.read()
    png = engine.render_page_png(pdf_bytes, table, passthrough, {}, 0, original=True)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    # orijinal: İngilizce metin korunur (çeviri uygulanmaz) -> "Yeast fungi"
    doc = fitz.open(stream=engine.translate_one_page_bytes(pdf_bytes, table, passthrough, {}, 0, original=True), filetype="pdf")
    assert "Yeast fungi" in doc[0].get_text()
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py::test_render_page_png_matches_full_render -v`
Expected: FAIL — `AttributeError: ... 'render_page_png'`

- [ ] **Step 3: engine.py'de render'ı böl ve tek-sayfa fonksiyonları ekle**

`report_translator/engine.py` içinde mevcut `render` fonksiyonunu bul. Onu, sayfa-başına gövdeyi ayrı bir yardımcıya taşıyacak şekilde değiştir ve yeni fonksiyonları ekle. Mevcut `render`'ı şununla DEĞİŞTİR:
```python
def _render_page_items(page, items, font_cache):
    """Tek bir sayfadaki değişen segmentleri yerinde render et (redaksiyon + geri yazma)."""
    if not items:
        return
    for a in items:
        for r in a.seg.rects:
            page.add_redact_annot(fitz.Rect(r), fill=None)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
    for a in items:
        s = a.seg
        fontfile = os.path.join(FONT_DIR, s.fontfile)
        fontname = font_cache.get(s.fontfile)
        if fontname is None:
            fontname = "F%d" % len(font_cache)
            font_cache[s.fontfile] = fontname
        font = fitz.Font(fontfile=fontfile)
        text = a.tr.strip()
        indent = _leading_indent(s.raw_first, font, s.size)
        if s.single_line:
            ox, oy = s.origin
            page.insert_text((ox + indent, oy), text, fontname=fontname,
                             fontfile=fontfile, fontsize=s.size, color=s.color)
        else:
            box = fitz.Rect(s.bbox)
            left = box.x0 + indent
            fs = s.size
            fitted = False
            while fs > 4.5:
                pad = fitz.Rect(left, box.y0 - 1, box.x1 + 2, box.y1 + 4 * s.size)
                rc = page.insert_textbox(pad, text, fontname=fontname, fontfile=fontfile,
                                         fontsize=fs, color=s.color, lineheight=1.15,
                                         align=fitz.TEXT_ALIGN_LEFT)
                if rc >= 0:
                    fitted = True
                    break
                fs -= 0.25
            if not fitted:
                sys.stderr.write("UYARI: segment sığmadı, atlandı: %r\n" % text)


def _changed_items(annotated):
    return [a for a in annotated
            if a.source not in ("passthrough", "unknown") and a.tr != a.en]


def render(doc, annotated):
    """Tüm belgeyi yerinde render et (kopya verin)."""
    by_page = {}
    for a in _changed_items(annotated):
        by_page.setdefault(a.seg.page, []).append(a)
    font_cache = {}
    for page_index, items in by_page.items():
        _render_page_items(doc[page_index], items, font_cache)
    return doc


def translate_one_page_bytes(pdf_path_or_bytes, table, passthrough, overrides,
                             page_index, original=False):
    """Yalnız page_index render edilmiş tek-sayfalık PDF bayt'ı döndür."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    if not original:
        ann = translate_segments(extract_segments(doc), table, passthrough, overrides)
        items = [a for a in _changed_items(ann) if a.seg.page == page_index]
        _render_page_items(doc[page_index], items, {})
    # yalnız o sayfayı içeren yeni belge
    out = fitz.open()
    out.insert_pdf(doc, from_page=page_index, to_page=page_index)
    data = out.tobytes(garbage=4, deflate=True)
    out.close(); doc.close()
    return data


def render_page_png(pdf_path_or_bytes, table, passthrough, overrides,
                    page_index, dpi=150, original=False):
    """page_index'in render edilmiş PNG bayt'ı (override'lı veya orijinal)."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    if not original:
        ann = translate_segments(extract_segments(doc), table, passthrough, overrides)
        items = [a for a in _changed_items(ann) if a.seg.page == page_index]
        _render_page_items(doc[page_index], items, {})
    png = doc[page_index].get_pixmap(dpi=dpi).tobytes("png")
    doc.close()
    return png
```
> Not: `translate_document_bytes` mevcut hâliyle kalır (artık `render` üzerinden çalışır).

- [ ] **Step 4: Testleri çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_engine.py -v`
Expected: PASS (tümü; eski testler dahil)

- [ ] **Step 5: Commit**

```bash
git add report_translator/engine.py report_translator/tests/test_engine.py
git commit -m "feat(engine): tek-sayfa render (render_page_png, translate_one_page_bytes)"
```

---

## Task 2: store.py — render önbelleği + oturum kalıcılığı

**Files:**
- Create: `report_translator/store.py`
- Test: `report_translator/tests/test_store.py`

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/tests/test_store.py`:
```python
import os
import store


def test_render_cache_set_get_invalidate():
    c = store.RenderCache()
    assert c.get("f1", 0) is None
    c.set("f1", 0, b"PNGDATA")
    assert c.get("f1", 0) == b"PNGDATA"
    c.invalidate("f1")
    assert c.get("f1", 0) is None


def test_session_persistence_roundtrip(tmp_path, femobiome_pdf):
    base = str(tmp_path / "sessions")
    st = store.SessionStore(base_dir=base)
    with open(femobiome_pdf, "rb") as fh:
        pdf = fh.read()
    sid = st.create_session()
    fid = st.add_file(sid, "rapor.pdf", pdf, kit="femobiome_ii")
    st.set_override(sid, fid, "0:5", "DENEME")
    # yeni store örneği diskten yükler
    st2 = store.SessionStore(base_dir=base)
    sessions = st2.list_sessions()
    assert sid in sessions
    f = st2.get_file(sid, fid)
    assert f["name"] == "rapor.pdf" and f["kit"] == "femobiome_ii"
    assert f["overrides"]["0:5"] == "DENEME"
    assert f["pdf_bytes"][:4] == b"%PDF"


def test_session_delete(tmp_path, femobiome_pdf):
    base = str(tmp_path / "sessions")
    st = store.SessionStore(base_dir=base)
    sid = st.create_session()
    st.add_file(sid, "r.pdf", open(femobiome_pdf, "rb").read(), "femobiome_ii")
    st.delete_session(sid)
    assert sid not in st.list_sessions()
    assert not os.path.exists(os.path.join(base, sid))
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'store'`

- [ ] **Step 3: store.py yaz**

`report_translator/store.py`:
```python
"""store.py — render önbelleği (bellek) + oturum kalıcılığı (disk).
Klinik veri yereldedir; oturumlar ~/.genomer_cevirici/sessions altında saklanır."""
import os
import json
import uuid
import shutil

DEFAULT_BASE = os.path.join(os.path.expanduser("~"), ".genomer_cevirici", "sessions")


class RenderCache:
    """file_id -> {page_index: png_bytes}. Override değişince invalidate edilir."""
    def __init__(self):
        self._c = {}

    def get(self, file_id, page):
        return self._c.get(file_id, {}).get(page)

    def set(self, file_id, page, png):
        self._c.setdefault(file_id, {})[page] = png

    def invalidate(self, file_id):
        self._c.pop(file_id, None)


class SessionStore:
    """Oturumları diske yazar/okur. Her oturum bir klasör; her dosya <fid>.pdf + state.json."""
    def __init__(self, base_dir=DEFAULT_BASE):
        self.base = base_dir
        os.makedirs(self.base, exist_ok=True)

    def _sdir(self, sid):
        return os.path.join(self.base, sid)

    def _state_path(self, sid):
        return os.path.join(self._sdir(sid), "state.json")

    def _read_state(self, sid):
        with open(self._state_path(sid), encoding="utf-8") as f:
            return json.load(f)

    def _write_state(self, sid, state):
        with open(self._state_path(sid), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def create_session(self):
        sid = uuid.uuid4().hex[:12]
        os.makedirs(self._sdir(sid), exist_ok=True)
        self._write_state(sid, {"files": {}})
        return sid

    def add_file(self, sid, name, pdf_bytes, kit):
        fid = uuid.uuid4().hex[:8]
        with open(os.path.join(self._sdir(sid), fid + ".pdf"), "wb") as f:
            f.write(pdf_bytes)
        state = self._read_state(sid)
        state["files"][fid] = {"name": name, "kit": kit, "overrides": {},
                               "saved_path": None, "status": "done"}
        self._write_state(sid, state)
        return fid

    def list_sessions(self):
        if not os.path.isdir(self.base):
            return []
        return [d for d in os.listdir(self.base)
                if os.path.isfile(self._state_path(d))]

    def get_file(self, sid, fid):
        state = self._read_state(sid)
        meta = dict(state["files"][fid])
        with open(os.path.join(self._sdir(sid), fid + ".pdf"), "rb") as f:
            meta["pdf_bytes"] = f.read()
        return meta

    def file_meta(self, sid, fid):
        return self._read_state(sid)["files"][fid]

    def list_files(self, sid):
        return self._read_state(sid)["files"]

    def set_override(self, sid, fid, seg_id, tr):
        state = self._read_state(sid)
        state["files"][fid]["overrides"][seg_id] = tr
        self._write_state(sid, state)

    def remove_override(self, sid, fid, seg_id):
        state = self._read_state(sid)
        state["files"][fid]["overrides"].pop(seg_id, None)
        self._write_state(sid, state)

    def set_kit(self, sid, fid, kit):
        state = self._read_state(sid)
        state["files"][fid]["kit"] = kit
        state["files"][fid]["overrides"] = {}
        self._write_state(sid, state)

    def set_saved_path(self, sid, fid, path):
        state = self._read_state(sid)
        state["files"][fid]["saved_path"] = path
        self._write_state(sid, state)

    def delete_session(self, sid):
        d = self._sdir(sid)
        if os.path.isdir(d):
            shutil.rmtree(d)
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_store.py -v`
Expected: PASS (3 test)

- [ ] **Step 5: Commit**

```bash
git add report_translator/store.py report_translator/tests/test_store.py
git commit -m "feat(store): render önbelleği + disk oturum kalıcılığı"
```

---

## Task 3: app.py — store entegrasyonu, async upload+status, original png, revert, sessions, yapısal hata

**Files:**
- Modify: `report_translator/app.py`
- Test: `report_translator/tests/test_app.py`

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/tests/test_app.py` sonuna ekle:
```python
def test_upload_async_status_and_persistence(femobiome_pdf, tmp_path, monkeypatch):
    import store
    monkeypatch.setattr(store, "DEFAULT_BASE", str(tmp_path / "sess"))
    import importlib, app as app_mod
    importlib.reload(app_mod)
    app_mod.set_out_dir(str(tmp_path / "out"))
    c = TestClient(app_mod.app)
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
    import store
    monkeypatch.setattr(store, "DEFAULT_BASE", str(tmp_path / "sess2"))
    import importlib, app as app_mod
    importlib.reload(app_mod)
    c = TestClient(app_mod.app)
    with open(femobiome_pdf, "rb") as fh:
        c.post("/api/upload", files={"files": ("rep.pdf", fh.read(), "application/pdf")})
    sess = c.get("/api/sessions").json()
    assert len(sess["sessions"]) >= 1
    # bilinmeyen oturum -> yapısal hata
    r = c.get("/api/yok/zzz/manifest")
    assert r.status_code == 404
    assert "error" in r.json()
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_app.py::test_upload_async_status_and_persistence -v`
Expected: FAIL (yeni uçlar/yapı yok)

- [ ] **Step 3: app.py'yi store tabanlı yeniden yaz**

`report_translator/app.py` (tüm içerik):
```python
"""app.py — Rapor Çevirici yerel backend (FastAPI). Yalnız 127.0.0.1.
Orijinal PDF tek doğru kaynak; çıktı her zaman taze render. Oturumlar diske kalıcı."""
import os
import io
import sys
import zipfile
import subprocess
import threading
import fitz
from typing import Literal
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import engine
import dictionary
import store

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")

app = FastAPI(title="Genomer Rapor Çevirici")

SESSIONS = store.SessionStore()
CACHE = store.RenderCache()
_OUT_DIR = os.path.join(os.path.expanduser("~"), "Genomer Ceviriler")


def set_out_dir(path):
    global _OUT_DIR
    _OUT_DIR = path
    os.makedirs(_OUT_DIR, exist_ok=True)


class AppError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


@app.exception_handler(AppError)
def _app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status,
                        content={"error": {"code": exc.code, "message": exc.message}})


def _table_for(kit):
    kits, common, passthrough, _ = dictionary.load()
    return kits[kit], passthrough


def _file_or_404(sid, fid):
    try:
        return SESSIONS.get_file(sid, fid)
    except (KeyError, FileNotFoundError):
        raise AppError(404, "not_found", "Oturum veya dosya bulunamadı")


def _annotate(fs):
    table, passthrough = _table_for(fs["kit"])
    doc = fitz.open(stream=fs["pdf_bytes"], filetype="pdf")
    try:
        return engine.translate_segments(engine.extract_segments(doc), table, passthrough,
                                         fs["overrides"])
    finally:
        doc.close()


def _counts(ann):
    translated = sum(1 for a in ann if a.source in ("dict-exact", "dict-partial", "override"))
    review = sum(1 for a in ann if a.needs_review)
    return {"translated": translated, "review": review, "total": len(ann)}


def _render_bytes(fs):
    table, passthrough = _table_for(fs["kit"])
    return engine.translate_document_bytes(fs["pdf_bytes"], table, passthrough, fs["overrides"])


def _process_file(sid, fid):
    """Arka planda: dosyayı çevir, otomatik kaydet, status=done."""
    try:
        fs = SESSIONS.get_file(sid, fid)
        path = _save_one(sid, fid, fs)
        SESSIONS.set_saved_path(sid, fid, path)
    except Exception as e:  # noqa
        st = SESSIONS._read_state(sid)
        st["files"][fid]["status"] = "error"
        st["files"][fid]["error"] = str(e)
        SESSIONS._write_state(sid, st)


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    set_out_dir(_OUT_DIR)
    sid = SESSIONS.create_session()
    out = []
    for uf in files:
        data = await uf.read()
        if data[:4] != b"%PDF":
            out.append({"name": uf.filename, "error": "geçersiz PDF"})
            continue
        kit = dictionary.detect_kit(fitz.open(stream=data, filetype="pdf"))
        fid = SESSIONS.add_file(sid, uf.filename, data, kit)
        ann = _annotate(SESSIONS.get_file(sid, fid))
        threading.Thread(target=_process_file, args=(sid, fid), daemon=True).start()
        out.append({"file_id": fid, "name": uf.filename, "kit": kit, "counts": _counts(ann)})
    return {"session_id": sid, "files": out}


@app.get("/api/sessions")
def sessions():
    res = []
    for sid in SESSIONS.list_sessions():
        files = SESSIONS.list_files(sid)
        res.append({"session_id": sid,
                    "files": [{"file_id": k, "name": v["name"], "kit": v["kit"]}
                              for k, v in files.items()]})
    return {"sessions": res}


@app.get("/api/{sid}/status")
def status(sid: str):
    try:
        files = SESSIONS.list_files(sid)
    except FileNotFoundError:
        raise AppError(404, "not_found", "Oturum bulunamadı")
    return {"files": {k: {"status": v.get("status", "done"),
                          "saved_path": v.get("saved_path"),
                          "error": v.get("error")} for k, v in files.items()}}


@app.delete("/api/{sid}")
def delete_session(sid: str):
    SESSIONS.delete_session(sid)
    return {"ok": True}


@app.get("/api/{sid}/{fid}/manifest")
def manifest(sid: str, fid: str):
    fs = _file_or_404(sid, fid)
    ann = _annotate(fs)
    return [{"id": a.id, "page": a.page, "bbox": a.seg.bbox, "en": a.en, "tr": a.tr,
             "source": a.source, "needs_review": a.needs_review} for a in ann]


@app.get("/api/{sid}/{fid}/page/{n}.png")
def page_png(sid: str, fid: str, n: int):
    cached = CACHE.get(fid, n)
    if cached is not None:
        return Response(content=cached, media_type="image/png")
    fs = _file_or_404(sid, fid)
    table, passthrough = _table_for(fs["kit"])
    try:
        png = engine.render_page_png(fs["pdf_bytes"], table, passthrough, fs["overrides"], n)
    except Exception:
        raise AppError(500, "render_failed", "Sayfa render edilemedi")
    CACHE.set(fid, n, png)
    return Response(content=png, media_type="image/png")


@app.get("/api/{sid}/{fid}/original/{n}.png")
def original_png(sid: str, fid: str, n: int):
    fs = _file_or_404(sid, fid)
    table, passthrough = _table_for(fs["kit"])
    png = engine.render_page_png(fs["pdf_bytes"], table, passthrough, {}, n, original=True)
    return Response(content=png, media_type="image/png")


class SegmentEdit(BaseModel):
    tr: str
    scope: Literal["dict", "report", "revert"]
    force: bool = False


@app.post("/api/{sid}/{fid}/segment/{seg}")
def edit_segment(sid: str, fid: str, seg: str, body: SegmentEdit):
    fs = _file_or_404(sid, fid)
    if body.scope == "revert":
        SESSIONS.remove_override(sid, fid, seg)
        CACHE.invalidate(fid)
        return {"ok": True}
    SESSIONS.set_override(sid, fid, seg, body.tr)
    CACHE.invalidate(fid)
    if body.scope == "dict":
        en = next((a.en for a in _annotate(SESSIONS.get_file(sid, fid)) if a.id == seg), None)
        if en:
            res = dictionary.add_entry(fs["kit"], en, body.tr, overwrite=body.force)
            if res.get("conflict"):
                return {"ok": True, "conflict": True, "existing": res["existing"], "en": en}
    return {"ok": True}


class KitBody(BaseModel):
    kit: Literal["femobiome_ii", "androbiome", "enterobiome_kids"]


@app.post("/api/{sid}/{fid}/kit")
def set_kit(sid: str, fid: str, body: KitBody):
    _file_or_404(sid, fid)
    SESSIONS.set_kit(sid, fid, body.kit)
    CACHE.invalidate(fid)
    ann = _annotate(SESSIONS.get_file(sid, fid))
    return {"ok": True, "counts": _counts(ann)}


def _save_one(sid, fid, fs=None):
    fs = fs or SESSIONS.get_file(sid, fid)
    os.makedirs(_OUT_DIR, exist_ok=True)
    base = os.path.splitext(fs["name"])[0]
    path = os.path.join(_OUT_DIR, base + "_TR.pdf")
    with open(path, "wb") as f:
        f.write(_render_bytes(fs))
    SESSIONS.set_saved_path(sid, fid, path)
    return path


@app.post("/api/{sid}/{fid}/save")
def save_one(sid: str, fid: str):
    _file_or_404(sid, fid)
    return {"ok": True, "saved_path": _save_one(sid, fid)}


@app.post("/api/{sid}/save_all")
def save_all(sid: str):
    try:
        files = SESSIONS.list_files(sid)
    except FileNotFoundError:
        raise AppError(404, "not_found", "Oturum bulunamadı")
    return {"ok": True, "paths": [_save_one(sid, fid) for fid in files]}


@app.get("/api/{sid}/{fid}/download")
def download(sid: str, fid: str):
    fs = _file_or_404(sid, fid)
    base = os.path.splitext(fs["name"])[0]
    return Response(content=_render_bytes(fs), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{base}_TR.pdf"'})


@app.get("/api/{sid}/download_all")
def download_all(sid: str):
    try:
        files = SESSIONS.list_files(sid)
    except FileNotFoundError:
        raise AppError(404, "not_found", "Oturum bulunamadı")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fid in files:
            fs = SESSIONS.get_file(sid, fid)
            base = os.path.splitext(fs["name"])[0]
            z.writestr(base + "_TR.pdf", _render_bytes(fs))
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="ceviriler.zip"'})


@app.get("/api/{sid}/{fid}/review.txt")
def review_txt(sid: str, fid: str):
    fs = _file_or_404(sid, fid)
    ann = _annotate(fs)
    lines = sorted({a.en for a in ann if a.needs_review})
    body = "# Gözden geçirilecek / sözlüğe eklenecek birimler\n\n" + "\n".join(lines)
    base = os.path.splitext(fs["name"])[0]
    return Response(content=body, media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{base}_review.txt"'})


@app.get("/api/out_dir")
def get_out_dir():
    return {"out_dir": _OUT_DIR}


class OutDirBody(BaseModel):
    path: str


@app.post("/api/out_dir")
def set_out_dir_endpoint(body: OutDirBody):
    set_out_dir(body.path)
    return {"ok": True, "out_dir": _OUT_DIR}


@app.post("/api/open_out_dir")
def open_out_dir():
    os.makedirs(_OUT_DIR, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.run(["open", _OUT_DIR])
    elif sys.platform == "win32":
        os.startfile(_OUT_DIR)  # type: ignore
    else:
        subprocess.run(["xdg-open", _OUT_DIR])
    return {"ok": True}


if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini doğrula**

Run: `cd report_translator && python3 -m pytest tests/test_app.py -v`
Expected: PASS. Eski testler `set_out_dir` ve uç sözleşmelerini hâlâ kullanıyor; gerekiyorsa eski `test_upload_manifest_edit_save_flow`'u yeni store tabanlı akışla uyumlu olacak şekilde güncelle (monkeypatch ile `store.DEFAULT_BASE`'i tmp'ye al). Tüm paket: `python3 -m pytest -q`.

- [ ] **Step 5: Commit**

```bash
git add report_translator/app.py report_translator/tests/test_app.py
git commit -m "feat(app): store kalıcılığı, async upload+status, original png, revert, sessions, yapısal hata"
```

---

# FAZ 2 — Frontend (Vite + Preact SPA)

## Task 4: frontend iskele (Vite + Preact + Vitest)

**Files:**
- Create: `report_translator/frontend/package.json`, `vite.config.js`, `vitest.config.js`, `index.html`, `src/main.jsx`, `src/app.jsx`, `src/styles/global.css`

- [ ] **Step 1: package.json yaz**

`report_translator/frontend/package.json`:
```json
{
  "name": "genomer-rapor-cevirici",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "preact": "^10.23.0",
    "@preact/signals": "^1.3.0"
  },
  "devDependencies": {
    "@preact/preset-vite": "^2.9.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0",
    "jsdom": "^25.0.0"
  }
}
```

- [ ] **Step 2: vite/vitest config + index.html yaz**

`report_translator/frontend/vite.config.js`:
```javascript
import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

export default defineConfig({
  plugins: [preact()],
  base: "./",
  build: { outDir: "../web", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8731" } },
});
```

`report_translator/frontend/vitest.config.js`:
```javascript
import { defineConfig } from "vitest/config";
import preact from "@preact/preset-vite";

export default defineConfig({
  plugins: [preact()],
  test: { environment: "jsdom", globals: true },
});
```

`report_translator/frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Genomer · Rapor Çevirici</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
```

- [ ] **Step 3: main/app/global.css yaz**

`report_translator/frontend/src/main.jsx`:
```javascript
import { render } from "preact";
import { App } from "./app.jsx";
import "./styles/global.css";

render(<App />, document.getElementById("app"));
```

`report_translator/frontend/src/app.jsx`:
```javascript
export function App() {
  return <div class="app"><h1>Genomer Rapor Çevirici</h1></div>;
}
```

`report_translator/frontend/src/styles/global.css`:
```css
:root{--mor:#6c3a8e;--mavi:#2b6cb0;--bg:#f6f7fb;--kart:#fff;--cizgi:#e3e6ef;
  --uyari:#b7791f;--ok:#2f855a;--hata:#c53030;--metin:#1a202c;--gri:#667;}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;
  background:var(--bg);color:var(--metin)}
.app{min-height:100vh}
```

- [ ] **Step 4: Bağımlılıkları kur ve build'i doğrula**

Run:
```bash
cd report_translator/frontend && npm install && npm run build
```
Expected: `../web/index.html` ve `../web/assets/*` üretilir, hata yok. `ls ../web` çıktısı `index.html` ve `assets/` içermeli.

- [ ] **Step 5: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/frontend report_translator/web
git commit -m "feat(frontend): Vite+Preact iskele + build çıktısı"
```

---

## Task 5: API istemcisi (+ Vitest)

**Files:**
- Create: `report_translator/frontend/src/api/client.js`, `src/api/client.test.js`

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/frontend/src/api/client.test.js`:
```javascript
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as api from "./client.js";

beforeEach(() => { global.fetch = vi.fn(); });

function mockJson(obj) {
  global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(obj) });
}

describe("api client", () => {
  it("uploads files via FormData", async () => {
    mockJson({ session_id: "s1", files: [] });
    const res = await api.upload([new File(["x"], "a.pdf")]);
    expect(res.session_id).toBe("s1");
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/upload");
    expect(opts.method).toBe("POST");
    expect(opts.body instanceof FormData).toBe(true);
  });

  it("edits a segment with scope and force", async () => {
    mockJson({ ok: true });
    await api.editSegment("s1", "f1", "0:5", "Çeviri", "dict", true);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/s1/f1/segment/0:5");
    expect(JSON.parse(opts.body)).toEqual({ tr: "Çeviri", scope: "dict", force: true });
  });

  it("builds page url with cache-bust", () => {
    const u = api.pageUrl("s1", "f1", 2);
    expect(u).toMatch(/^\/api\/s1\/f1\/page\/2\.png\?t=\d+/);
  });
});
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator/frontend && npx vitest run src/api/client.test.js`
Expected: FAIL — modül yok

- [ ] **Step 3: client.js yaz**

`report_translator/frontend/src/api/client.js`:
```javascript
async function jget(url) {
  const r = await fetch(url);
  if (!r.ok) throw await asError(r);
  return r.json();
}
async function jpost(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw await asError(r);
  return r.json();
}
async function asError(r) {
  try { const j = await r.json(); return new Error(j.error?.message || "İstek başarısız"); }
  catch { return new Error("İstek başarısız (" + r.status + ")"); }
}

export async function upload(fileList) {
  const fd = new FormData();
  [...fileList].forEach((f) => fd.append("files", f));
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  if (!r.ok) throw await asError(r);
  return r.json();
}
export const getStatus = (s) => jget(`/api/${s}/status`);
export const getSessions = () => jget(`/api/sessions`);
export const getManifest = (s, f) => jget(`/api/${s}/${f}/manifest`);
export const editSegment = (s, f, seg, tr, scope, force = false) =>
  jpost(`/api/${s}/${f}/segment/${seg}`, { tr, scope, force });
export const setKit = (s, f, kit) => jpost(`/api/${s}/${f}/kit`, { kit });
export const saveOne = (s, f) => jpost(`/api/${s}/${f}/save`);
export const saveAll = (s) => jpost(`/api/${s}/save_all`);
export const getOutDir = () => jget(`/api/out_dir`);
export const setOutDir = (path) => jpost(`/api/out_dir`, { path });
export const openOutDir = () => jpost(`/api/open_out_dir`);
export const deleteSession = (s) => fetch(`/api/${s}`, { method: "DELETE" });
export const pageUrl = (s, f, n) => `/api/${s}/${f}/page/${n}.png?t=${Date.now()}`;
export const originalUrl = (s, f, n) => `/api/${s}/${f}/original/${n}.png`;
export const reviewUrl = (s, f) => `/api/${s}/${f}/review.txt`;
export const downloadAllUrl = (s) => `/api/${s}/download_all`;
```

- [ ] **Step 4: Testi çalıştır, geçtiğini doğrula**

Run: `cd report_translator/frontend && npx vitest run src/api/client.test.js`
Expected: PASS (3 test)

- [ ] **Step 5: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/frontend/src/api
git commit -m "feat(frontend): API istemcisi + testler"
```

---

## Task 6: Durum yönetimi (signals store) + undo/revert mantığı (+ Vitest)

**Files:**
- Create: `report_translator/frontend/src/state/store.js`, `src/state/store.test.js`

- [ ] **Step 1: Başarısız testi yaz**

`report_translator/frontend/src/state/store.test.js`:
```javascript
import { describe, it, expect } from "vitest";
import { createStore } from "./store.js";

describe("editor store", () => {
  it("applies an override and marks unsaved", () => {
    const s = createStore();
    s.setManifest([{ id: "0:1", en: "Yeast fungi", tr: "Maya mantarları", needs_review: false, page: 0, bbox: [0,0,1,1] }]);
    s.applyOverride("0:1", "Yeni");
    expect(s.segmentById("0:1").tr).toBe("Yeni");
    expect(s.saveStatus.value).toBe("unsaved");
  });

  it("undo restores previous tr", () => {
    const s = createStore();
    s.setManifest([{ id: "0:1", en: "X", tr: "A", needs_review: false, page: 0, bbox: [0,0,1,1] }]);
    s.applyOverride("0:1", "B");
    s.undo();
    expect(s.segmentById("0:1").tr).toBe("A");
  });

  it("filters review and searches", () => {
    const s = createStore();
    s.setManifest([
      { id: "0:1", en: "Yeast fungi", tr: "Maya", needs_review: false, page: 0, bbox: [0,0,1,1] },
      { id: "0:2", en: "Foo", tr: "Bar", needs_review: true, page: 0, bbox: [0,0,1,1] },
    ]);
    s.filter.value = "review";
    expect(s.visibleSegments.value.map((x) => x.id)).toEqual(["0:2"]);
    s.filter.value = "all";
    s.search.value = "yeast";
    expect(s.visibleSegments.value.map((x) => x.id)).toEqual(["0:1"]);
  });
});
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu doğrula**

Run: `cd report_translator/frontend && npx vitest run src/state/store.test.js`
Expected: FAIL — modül yok

- [ ] **Step 3: store.js yaz**

`report_translator/frontend/src/state/store.js`:
```javascript
import { signal, computed } from "@preact/signals";

export function createStore() {
  const manifest = signal([]);       // [{id,en,tr,source,needs_review,page,bbox}]
  const saveStatus = signal("saved"); // saved | unsaved | saving
  const filter = signal("all");       // all | review
  const search = signal("");
  const undoStack = [];

  const segMap = computed(() => {
    const m = new Map();
    manifest.value.forEach((s) => m.set(s.id, s));
    return m;
  });
  const segmentById = (id) => segMap.value.get(id);

  const visibleSegments = computed(() => {
    const q = search.value.trim().toLowerCase();
    return manifest.value.filter((s) => {
      if (filter.value === "review" && !s.needs_review) return false;
      if (q && !(s.en.toLowerCase().includes(q) || (s.tr || "").toLowerCase().includes(q)))
        return false;
      return true;
    });
  });

  function setManifest(list) {
    manifest.value = list.map((s) => ({ ...s }));
    saveStatus.value = "saved";
    undoStack.length = 0;
  }

  function applyOverride(id, tr, record = true) {
    const cur = segmentById(id);
    if (!cur) return;
    if (record) undoStack.push({ id, prev: cur.tr });
    manifest.value = manifest.value.map((s) => (s.id === id ? { ...s, tr } : s));
    saveStatus.value = "unsaved";
  }

  function undo() {
    const last = undoStack.pop();
    if (last) applyOverride(last.id, last.prev, false);
  }

  return { manifest, saveStatus, filter, search, visibleSegments,
           segmentById, setManifest, applyOverride, undo };
}
```

- [ ] **Step 4: Testi çalıştır, geçtiğini doğrula**

Run: `cd report_translator/frontend && npx vitest run src/state/store.test.js`
Expected: PASS (3 test)

- [ ] **Step 5: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/frontend/src/state
git commit -m "feat(frontend): signals store (override/undo/filtre/arama) + testler"
```

---

## Task 7: Header + UploadView + FileCard (durum/ilerleme)

**Files:**
- Create: `report_translator/frontend/src/components/Header.jsx`, `UploadView.jsx`, `FileCard.jsx`, `Dropzone.jsx`
- Modify: `report_translator/frontend/src/app.jsx`
- Create: `report_translator/frontend/src/styles/components.css`

- [ ] **Step 1: Bileşenleri yaz**

`report_translator/frontend/src/components/Dropzone.jsx`:
```javascript
import { useRef, useState } from "preact/hooks";

export function Dropzone({ onFiles }) {
  const input = useRef(null);
  const [drag, setDrag] = useState(false);
  return (
    <div class={"dropzone" + (drag ? " drag" : "")}
      onClick={() => input.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); onFiles(e.dataTransfer.files); }}>
      <p>PDF raporlarını buraya sürükleyin<br/><small>veya tıklayıp seçin (çoklu)</small></p>
      <input ref={input} type="file" accept="application/pdf" multiple hidden
        onChange={(e) => onFiles(e.target.files)} />
    </div>
  );
}
```

`report_translator/frontend/src/components/FileCard.jsx`:
```javascript
export function FileCard({ file, onOpen }) {
  if (file.error)
    return <div class="card"><div class="name">{file.name}</div>
      <div class="err">{file.error}</div></div>;
  const c = file.counts || {};
  return (
    <div class="card">
      <span class="kit">{file.kit}</span>
      <div class="name">{file.name}</div>
      {file.status === "pending"
        ? <div class="stat"><span class="spinner" /> çevriliyor…</div>
        : file.status === "error"
        ? <div class="err">hata: {file.errorMsg || "render"}</div>
        : <>
            <div class="stat ok">✓ {c.translated} çevrildi</div>
            {c.review ? <div class="stat warn">⚠ {c.review} gözden geçirilecek</div> : null}
          </>}
      <button disabled={file.status === "pending"} onClick={() => onOpen(file)}>
        Görüntüle / Düzelt</button>
    </div>
  );
}
```

`report_translator/frontend/src/components/Header.jsx`:
```javascript
import { useEffect, useState } from "preact/hooks";
import * as api from "../api/client.js";

export function Header() {
  const [outDir, setOut] = useState("");
  useEffect(() => { api.getOutDir().then((r) => setOut(r.out_dir)); }, []);
  return (
    <header>
      <img src="./genomerlogo.png" alt="Genomer" class="logo" />
      <h1>Rapor Çevirici <span>EN → TR</span></h1>
      <div class="out-dir">
        Çıktı: <code>{outDir}</code>
        <button class="mini" onClick={async () => {
          const p = prompt("Yeni çıktı klasörü:", outDir);
          if (p) { const r = await api.setOutDir(p); setOut(r.out_dir); }
        }}>Değiştir</button>
        <button class="mini" onClick={() => api.openOutDir()}>Klasörü aç</button>
      </div>
    </header>
  );
}
```

`report_translator/frontend/src/components/UploadView.jsx`:
```javascript
import { useEffect } from "preact/hooks";
import { Dropzone } from "./Dropzone.jsx";
import { FileCard } from "./FileCard.jsx";
import * as api from "../api/client.js";

export function UploadView({ session, files, setSession, setFiles, onOpen }) {
  async function handleFiles(fileList) {
    const res = await api.upload(fileList);
    setSession(res.session_id);
    setFiles(res.files.map((f) => ({ ...f, status: f.error ? "error" : "pending" })));
  }

  // ilerleme poll'ü: pending dosya kaldıkça durum çek
  useEffect(() => {
    if (!session) return;
    const pending = files.some((f) => f.status === "pending");
    if (!pending) return;
    const t = setInterval(async () => {
      const st = await api.getStatus(session);
      setFiles((prev) => prev.map((f) => {
        const s = st.files[f.file_id];
        return s ? { ...f, status: s.status, errorMsg: s.error } : f;
      }));
    }, 800);
    return () => clearInterval(t);
  }, [session, files]);

  return (
    <section class="upload">
      <Dropzone onFiles={handleFiles} />
      {files.length > 0 && (
        <div class="cards">
          {files.map((f) => <FileCard key={f.file_id || f.name} file={f} onOpen={onOpen} />)}
        </div>
      )}
      {files.length > 0 && (
        <div class="batch">
          <button onClick={() => api.saveAll(session)}>Tümünü kaydet</button>
          <button class="ghost" onClick={() => (location.href = api.downloadAllUrl(session))}>
            ZIP indir</button>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: app.jsx'i UploadView'a bağla**

`report_translator/frontend/src/app.jsx` (tüm içerik):
```javascript
import { useState } from "preact/hooks";
import { Header } from "./components/Header.jsx";
import { UploadView } from "./components/UploadView.jsx";
import { EditorView } from "./components/EditorView.jsx";
import "./styles/components.css";

export function App() {
  const [session, setSession] = useState(null);
  const [files, setFiles] = useState([]);
  const [editing, setEditing] = useState(null);
  return (
    <div class="app">
      <Header />
      {editing
        ? <EditorView session={session} file={editing} onBack={() => setEditing(null)} />
        : <UploadView session={session} files={files} setSession={setSession}
            setFiles={setFiles} onOpen={setEditing} />}
    </div>
  );
}
```

- [ ] **Step 3: components.css yaz**

`report_translator/frontend/src/styles/components.css`:
```css
header{display:flex;align-items:center;gap:16px;padding:14px 22px;background:var(--kart);
  border-bottom:1px solid var(--cizgi)}
.logo{height:34px}
header h1{font-size:18px;margin:0}header h1 span{color:var(--mor);font-size:14px;font-weight:500}
.out-dir{margin-left:auto;font-size:13px;color:var(--gri);display:flex;align-items:center;gap:8px}
button{background:var(--mor);color:#fff;border:0;border-radius:8px;padding:8px 14px;
  font-size:13px;cursor:pointer}
button.ghost{background:#fff;color:var(--mor);border:1px solid var(--mor)}
button.mini{padding:4px 8px;font-size:12px}
button:disabled{opacity:.5;cursor:default}
.upload{max-width:1100px;margin:24px auto;padding:0 22px}
.dropzone{border:2px dashed var(--mavi);border-radius:14px;padding:54px;text-align:center;
  background:var(--kart);cursor:pointer}
.dropzone.drag{background:#eef3fb;border-color:var(--mor)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin-top:20px}
.card{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:14px}
.kit{display:inline-block;font-size:11px;padding:2px 8px;border-radius:20px;background:#efe7f5;
  color:var(--mor);margin-bottom:8px}
.name{font-weight:600;font-size:13px;word-break:break-word}
.stat{font-size:13px;margin-top:8px}.ok{color:var(--ok)}.warn{color:var(--uyari)}
.err{color:var(--hata);font-size:13px;margin-top:8px}
.batch{margin-top:18px;display:flex;gap:10px}
.spinner{display:inline-block;width:12px;height:12px;border:2px solid #ccc;border-top-color:var(--mor);
  border-radius:50%;animation:spin .7s linear infinite;vertical-align:-1px}
@keyframes spin{to{transform:rotate(360deg)}}
```

- [ ] **Step 4: Logoyu web'e koy ve build doğrula**

Run:
```bash
cp /Users/ilkerkadirozturk/Documents/genomer_brochures/genomerlogo.png report_translator/frontend/public/genomerlogo.png 2>/dev/null || (mkdir -p report_translator/frontend/public && cp /Users/ilkerkadirozturk/Documents/genomer_brochures/genomerlogo.png report_translator/frontend/public/genomerlogo.png)
cd report_translator/frontend && npm run build && ls ../web
```
Expected: build başarılı; `../web/genomerlogo.png` mevcut (Vite `public/` köke kopyalar).

- [ ] **Step 5: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/frontend report_translator/web
git commit -m "feat(frontend): Header + UploadView + FileCard (ilerleme/durum)"
```

---

## Task 8: EditorView — sayfa tuvali, küçük resimler, zoom, karşılaştırma, segment kutuları

**Files:**
- Create: `report_translator/frontend/src/components/EditorView.jsx`, `PageCanvas.jsx`, `ThumbnailRail.jsx`
- Modify: `report_translator/frontend/src/styles/components.css` (ekle)

- [ ] **Step 1: PageCanvas + ThumbnailRail + EditorView yaz**

`report_translator/frontend/src/components/PageCanvas.jsx`:
```javascript
import { useRef, useState } from "preact/hooks";
import * as api from "../api/client.js";

const DPI = 150;

export function PageCanvas({ session, file, pageCount, manifest, zoom, compare,
                            activeId, onPickSegment, refreshKey }) {
  return (
    <div class="pages" style={{ "--zoom": zoom }}>
      {Array.from({ length: pageCount }).map((_, n) => (
        <PageImage key={n + "_" + refreshKey} session={session} file={file} n={n}
          manifest={manifest.filter((s) => s.page === n)} compare={compare}
          activeId={activeId} onPickSegment={onPickSegment} />
      ))}
    </div>
  );
}

function PageImage({ session, file, n, manifest, compare, activeId, onPickSegment }) {
  const wrap = useRef(null);
  const [dims, setDims] = useState(null);
  function onLoad(e) {
    const img = e.target;
    setDims({ w: img.clientWidth, nat: img.naturalWidth });
  }
  const scale = dims ? dims.w / (dims.nat / (DPI / 72)) : 0;
  return (
    <div class="pageRow">
      {compare && (
        <div class="pageWrap">
          <img src={api.originalUrl(session, file.file_id, n)} alt={"EN sayfa " + (n + 1)} />
          <div class="pageTag">EN</div>
        </div>
      )}
      <div class="pageWrap" ref={wrap}>
        <img src={api.pageUrl(session, file.file_id, n)} onLoad={onLoad} alt={"TR sayfa " + (n + 1)} />
        {compare && <div class="pageTag">TR</div>}
        {dims && manifest.map((s) => {
          const [x0, y0, x1, y1] = s.bbox;
          return <div key={s.id}
            class={"box" + (s.needs_review ? " review" : "") + (s.id === activeId ? " active" : "")}
            style={{ left: x0 * scale, top: y0 * scale,
                     width: (x1 - x0) * scale, height: (y1 - y0) * scale }}
            onClick={() => onPickSegment(s.id)} />;
        })}
      </div>
    </div>
  );
}
```

`report_translator/frontend/src/components/ThumbnailRail.jsx`:
```javascript
import * as api from "../api/client.js";

export function ThumbnailRail({ session, file, pageCount, manifest, onJump }) {
  const reviewPages = new Set(manifest.filter((s) => s.needs_review).map((s) => s.page));
  return (
    <div class="thumbs">
      {Array.from({ length: pageCount }).map((_, n) => (
        <button key={n} class="thumb" onClick={() => onJump(n)}>
          <img src={api.pageUrl(session, file.file_id, n)} alt={"Sayfa " + (n + 1)} />
          <span class="thumbNo">{n + 1}{reviewPages.has(n) ? " ⚠" : ""}</span>
        </button>
      ))}
    </div>
  );
}
```

`report_translator/frontend/src/components/EditorView.jsx`:
```javascript
import { useEffect, useMemo, useState } from "preact/hooks";
import { createStore } from "../state/store.js";
import { PageCanvas } from "./PageCanvas.jsx";
import { ThumbnailRail } from "./ThumbnailRail.jsx";
import { SegmentPanel } from "./SegmentPanel.jsx";
import * as api from "../api/client.js";

export function EditorView({ session, file, onBack }) {
  const store = useMemo(createStore, []);
  const [zoom, setZoom] = useState(1);
  const [compare, setCompare] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getManifest(session, file.file_id).then((m) => { store.setManifest(m); setLoading(false); });
  }, [session, file.file_id]);

  // kaydedilmemiş değişiklik koruması
  useEffect(() => {
    const h = (e) => { if (store.saveStatus.value === "unsaved") { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, []);

  const pageCount = useMemo(
    () => (store.manifest.value.length ? Math.max(...store.manifest.value.map((s) => s.page)) + 1 : 1),
    [store.manifest.value]);

  function jump(n) {
    document.querySelectorAll(".pageRow")[n]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <section class="editor">
      <div class="toolbar">
        <button class="ghost" onClick={onBack}>← Geri</button>
        <strong>{file.name}</strong>
        <SaveBadge status={store.saveStatus.value} />
        <label class="cmp"><input type="checkbox" checked={compare}
          onChange={(e) => setCompare(e.target.checked)} /> EN↔TR karşılaştır</label>
        <span class="zoom">
          <button class="mini" onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}>−</button>
          {Math.round(zoom * 100)}%
          <button class="mini" onClick={() => setZoom((z) => Math.min(2, z + 0.1))}>+</button>
        </span>
        <a class="mini-link" href={api.reviewUrl(session, file.file_id)}>Gözden geçirme listesi</a>
        <button onClick={async () => { await api.saveOne(session, file.file_id);
          store.saveStatus.value = "saved"; }}>Kaydet</button>
      </div>
      {loading ? <div class="skeleton">Yükleniyor…</div> : (
        <div class="editorBody">
          <ThumbnailRail session={session} file={file} pageCount={pageCount}
            manifest={store.manifest.value} onJump={jump} />
          <PageCanvas session={session} file={file} pageCount={pageCount}
            manifest={store.manifest.value} zoom={zoom} compare={compare}
            activeId={activeId} onPickSegment={setActiveId} refreshKey={refreshKey} />
          <SegmentPanel session={session} file={file} store={store}
            activeId={activeId} setActiveId={setActiveId}
            onChanged={() => setRefreshKey((k) => k + 1)} />
        </div>
      )}
    </section>
  );
}

function SaveBadge({ status }) {
  const map = { saved: ["kaydedildi ✓", "ok"], unsaved: ["kaydedilmedi ●", "warn"], saving: ["kaydediliyor…", ""] };
  const [t, c] = map[status] || map.saved;
  return <span class={"saveBadge " + c}>{t}</span>;
}
```

- [ ] **Step 2: components.css'e editör stilleri ekle**

`report_translator/frontend/src/styles/components.css` sonuna ekle:
```css
.editor{max-width:1400px;margin:14px auto;padding:0 18px}
.toolbar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:10px}
.saveBadge{font-size:12px}.saveBadge.ok{color:var(--ok)}.saveBadge.warn{color:var(--uyari)}
.cmp{font-size:13px;color:var(--gri)} .zoom{font-size:13px;color:var(--gri)}
.mini-link{font-size:12px;color:var(--mavi)}
.editorBody{display:grid;grid-template-columns:84px 1fr 400px;gap:14px}
.thumbs{display:flex;flex-direction:column;gap:8px;max-height:80vh;overflow:auto}
.thumb{background:none;border:1px solid var(--cizgi);border-radius:6px;padding:2px;cursor:pointer}
.thumb img{width:100%;display:block}.thumbNo{font-size:10px;color:var(--gri)}
.pages{max-height:80vh;overflow:auto;background:var(--kart);border:1px solid var(--cizgi);
  border-radius:12px;padding:10px}
.pageRow{display:flex;gap:10px;margin-bottom:12px;justify-content:center}
.pageWrap{position:relative;width:calc(100% * var(--zoom,1));max-width:760px}
.pageWrap img{width:100%;display:block;border:1px solid var(--cizgi)}
.pageTag{position:absolute;top:4px;left:4px;background:#0008;color:#fff;font-size:10px;padding:1px 5px;border-radius:4px}
.box{position:absolute;border:1.5px solid transparent;border-radius:3px;cursor:pointer}
.box:hover,.box.active{border-color:var(--mavi);background:rgba(43,108,176,.14)}
.box.review{border-color:var(--uyari);background:rgba(183,121,31,.10)}
.skeleton{padding:40px;text-align:center;color:var(--gri)}
```

- [ ] **Step 3: Geçici SegmentPanel taslağı (Task 9'da tamamlanır) ekle ki build geçsin**

`report_translator/frontend/src/components/SegmentPanel.jsx`:
```javascript
export function SegmentPanel() { return <aside class="segments">…</aside>; }
```

- [ ] **Step 4: Build doğrula**

Run: `cd report_translator/frontend && npm run build`
Expected: hata yok; `../web` güncellenir.

- [ ] **Step 5: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/frontend report_translator/web
git commit -m "feat(frontend): EditorView + PageCanvas (zoom/karşılaştırma/kutular) + ThumbnailRail"
```

---

## Task 9: SegmentPanel — arama/filtre, düzenleme, kapsam, revert, undo, çakışma

**Files:**
- Modify: `report_translator/frontend/src/components/SegmentPanel.jsx` (tamamla)
- Create: `report_translator/frontend/src/components/SegmentItem.jsx`
- Modify: `report_translator/frontend/src/styles/components.css` (ekle)

- [ ] **Step 1: SegmentItem yaz**

`report_translator/frontend/src/components/SegmentItem.jsx`:
```javascript
import { useState, useEffect } from "preact/hooks";

export function SegmentItem({ seg, active, onFocus, onSave, onRevert }) {
  const [val, setVal] = useState(seg.tr);
  useEffect(() => setVal(seg.tr), [seg.tr]);
  return (
    <div class={"seg" + (seg.needs_review ? " review" : "") + (active ? " active" : "")}
      onClick={onFocus}>
      <div class="en">{seg.en}</div>
      <textarea value={val} onInput={(e) => setVal(e.target.value)} />
      <div class="acts">
        <button onClick={() => onSave(val, "dict")}>Sözlüğe ekle</button>
        <button class="ghost" onClick={() => onSave(val, "report")}>Sadece bu rapor</button>
        {seg.source === "override" &&
          <button class="ghost" onClick={onRevert}>Sözlüğe döndür</button>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: SegmentPanel'i tamamla**

`report_translator/frontend/src/components/SegmentPanel.jsx` (tüm içerik):
```javascript
import { SegmentItem } from "./SegmentItem.jsx";
import * as api from "../api/client.js";

export function SegmentPanel({ session, file, store, activeId, setActiveId, onChanged }) {
  const visible = store.visibleSegments.value;

  async function save(seg, tr, scope, force = false) {
    store.applyOverride(seg.id, tr);
    const r = await api.editSegment(session, file.file_id, seg.id, tr, scope, force);
    if (r.conflict) {
      if (confirm(`Bu metin sözlükte zaten "${r.existing}" olarak var. Üzerine yazılsın mı?`)) {
        await api.editSegment(session, file.file_id, seg.id, tr, "dict", true);
      }
    }
    onChanged();
  }

  async function revert(seg) {
    await api.editSegment(session, file.file_id, seg.id, "", "revert");
    // sözlük değerini almak için manifest tazele
    const m = await api.getManifest(session, file.file_id);
    store.setManifest(m);
    onChanged();
  }

  return (
    <aside class="segments">
      <div class="segHead">
        <input class="searchBox" placeholder="Segment ara…" value={store.search.value}
          onInput={(e) => (store.search.value = e.target.value)} />
        <div class="filter">
          <button class={store.filter.value === "all" ? "active" : ""}
            onClick={() => (store.filter.value = "all")}>Tümü</button>
          <button class={store.filter.value === "review" ? "active" : ""}
            onClick={() => (store.filter.value = "review")}>Gözden geçirilecek</button>
          <button class="mini" onClick={store.undo}>↶ Geri al</button>
        </div>
      </div>
      <div class="segList">
        {visible.map((s) => (
          <SegmentItem key={s.id} seg={s} active={s.id === activeId}
            onFocus={() => setActiveId(s.id)}
            onSave={(tr, scope) => save(s, tr, scope)}
            onRevert={() => revert(s)} />
        ))}
      </div>
    </aside>
  );
}
```

- [ ] **Step 3: components.css'e segment stilleri ekle**

`report_translator/frontend/src/styles/components.css` sonuna ekle:
```css
.segments{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:12px;
  max-height:80vh;overflow:auto}
.segHead{position:sticky;top:0;background:var(--kart);padding-bottom:8px}
.searchBox{width:100%;border:1px solid var(--cizgi);border-radius:7px;padding:7px;font:inherit;margin-bottom:8px}
.filter{display:flex;gap:8px}
.filter button{background:#eef;color:#334;font-size:12px;padding:5px 10px}
.filter button.active{background:var(--mor);color:#fff}
.seg{border:1px solid var(--cizgi);border-radius:9px;padding:10px;margin-bottom:9px;cursor:pointer}
.seg.review{border-color:var(--uyari)}.seg.active{box-shadow:0 0 0 2px var(--mavi)}
.seg .en{font-size:12px;color:var(--gri);margin-bottom:5px}
.seg textarea{width:100%;border:1px solid var(--cizgi);border-radius:6px;padding:6px;font:inherit;
  resize:vertical;min-height:34px}
.seg .acts{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}
.seg .acts button{font-size:12px;padding:5px 9px}
```

- [ ] **Step 4: Build doğrula**

Run: `cd report_translator/frontend && npm run build && npx vitest run`
Expected: build başarılı; tüm Vitest testleri (api + store) PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/frontend report_translator/web
git commit -m "feat(frontend): SegmentPanel (arama/filtre/düzenle/kapsam/revert/undo/çakışma)"
```

---

## Task 10: Görsel cila (frontend-design skill) + e2e duman testi

**Files:**
- Modify: `report_translator/frontend/src/styles/*.css` (ve gerekiyorsa bileşen ince ayarları)

- [ ] **Step 1: frontend-design skill ile görsel dili yükselt**

`frontend-design` skill'ini çağır ve şu kapsamda uygula: Genomer mor/mavi marka, tutarlı tipografi ölçeği, boşluk ritmi, kart/buton/odak durumları, yumuşak gölgeler, erişilebilir kontrast, hover/transition mikro-etkileşimleri. **Yalnız CSS ve sınıf düzeyinde** çalış; bileşen davranışını/değiştirme akışını DEĞİŞTİRME. CDN ekleme (çevrimdışı). Sonuç hâlâ `npm run build` ile `web/`'e derlenmeli.

- [ ] **Step 2: Build + duman testi (sunucu + curl)**

Run:
```bash
cd report_translator/frontend && npm run build
cd .. && nohup python3 -m uvicorn app:app --port 8731 --host 127.0.0.1 >/tmp/uv.log 2>&1 &
sleep 3
curl -s -o /dev/null -w "anasayfa:%{http_code}\n" http://127.0.0.1:8731/
curl -s -o /dev/null -w "logo:%{http_code}\n" http://127.0.0.1:8731/genomerlogo.png
SID=$(curl -s -F "files=@../reportsamples/en/Femobiome_II report_eubiosis_eng.pdf;type=application/pdf" http://127.0.0.1:8731/api/upload | python3 -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
echo "session:$SID"
pkill -f "uvicorn app:app"
```
Expected: anasayfa:200, logo:200, session boş değil.

- [ ] **Step 3: Commit**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add report_translator/frontend report_translator/web
git commit -m "style(frontend): frontend-design ile görsel cila + e2e duman"
```

---

# FAZ 3 — Paketleme ve doğrulama

## Task 11: launcher.py (PyWebView) + requirements

**Files:**
- Create: `report_translator/launcher.py`
- Modify: `report_translator/requirements.txt`

- [ ] **Step 1: requirements.txt'e pywebview ekle**

`report_translator/requirements.txt` sonuna ekle:
```
pywebview==5.2
```

- [ ] **Step 2: launcher.py yaz**

`report_translator/launcher.py`:
```python
"""launcher.py — uvicorn'u arka planda başlatır, PyWebView ile gerçek pencere açar."""
import threading
import socket
import time
import uvicorn
import webview
import app as app_module


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    port = _free_port()
    t = threading.Thread(
        target=lambda: uvicorn.run(app_module.app, host="127.0.0.1", port=port, log_level="warning"),
        daemon=True)
    t.start()
    time.sleep(1.0)
    webview.create_window("Genomer Rapor Çevirici", f"http://127.0.0.1:{port}",
                          width=1280, height=820)
    webview.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: İçe-aktarma sözdizimini doğrula (pencere açmadan)**

Run: `cd report_translator && python3 -c "import ast; ast.parse(open('launcher.py').read()); print('syntax ok')"`
Expected: `syntax ok` (pywebview kurulu değilse GERÇEKTEN çalıştırma; yalnız sözdizimi.)

- [ ] **Step 4: Commit**

```bash
git add report_translator/launcher.py report_translator/requirements.txt
git commit -m "feat(packaging): PyWebView launcher + pywebview bağımlılığı"
```

---

## Task 12: build_app.md + başlatıcı güncellemesi

**Files:**
- Modify: `report_translator/build_app.md`
- Modify: `report_translator/baslat.command`, `report_translator/baslat.bat`

- [ ] **Step 1: build_app.md'yi frontend build + PyInstaller ile güncelle**

`report_translator/build_app.md` (tüm içerik):
```markdown
# Native paketleme

## 1. Frontend'i derle
```bash
cd report_translator/frontend
npm install
npm run build      # -> ../web (statik, çevrimdışı)
```

## 2. PyInstaller ile tek dosya
```bash
cd report_translator
.venv/bin/pip install -r requirements.txt pyinstaller
.venv/bin/pyinstaller --onefile --windowed --name "GenomerRaporCevirici" \
  --add-data "web:web" --add-data "fonts:fonts" --add-data "dictionary.json:." \
  --collect-all fastapi --collect-all uvicorn --collect-all pymupdf --collect-all webview \
  launcher.py
```
- macOS: `--icon genomer.icns`; Windows: `--icon genomer.ico` (ayrı hazırlanır). Windows'ta `--add-data` ayıracı `;` kullanın (`"web;web"`).
- Çıktı `dist/GenomerRaporCevirici` tek dosyadır; Python gerektirmez, çevrimdışı çalışır.
- macOS imzalama/notarizasyon ve Windows kod imzalama dağıtım için ayrıca yapılır.
```

- [ ] **Step 2: baslat betiklerine frontend build kontrolü ekle**

`report_translator/baslat.command` (tüm içerik):
```bash
#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
if [ ! -f "web/index.html" ]; then
  echo "Frontend derlenmemiş. 'cd frontend && npm install && npm run build' çalıştırın." 
fi
PORT=8731
./.venv/bin/python -m uvicorn app:app --port $PORT --host 127.0.0.1 &
SRV=$!
sleep 2
open "http://127.0.0.1:$PORT"
echo "Genomer Rapor Çevirici çalışıyor. Kapatmak için bu pencereyi kapatın."
wait $SRV
```

`report_translator/baslat.bat` (tüm içerik):
```bat
@echo off
cd /d "%~dp0"
if not exist ".venv" (
  python -m venv .venv
  .venv\Scripts\pip install -q -r requirements.txt
)
if not exist "web\index.html" echo Frontend derlenmemis. frontend klasorunde 'npm install && npm run build' calistirin.
start "" http://127.0.0.1:8731
.venv\Scripts\python -m uvicorn app:app --port 8731 --host 127.0.0.1
```

- [ ] **Step 3: Sözdizimi doğrula**

Run: `bash -n report_translator/baslat.command && echo "ok"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add report_translator/build_app.md report_translator/baslat.command report_translator/baslat.bat
git commit -m "docs(packaging): frontend build + PyInstaller (PyWebView) + başlatıcı güncel"
```

---

## Task 13: Tam doğrulama (backend testleri + frontend testleri + 3 kit + editör)

**Files:** yalnız çalıştırma

- [ ] **Step 1: Tüm backend testleri**

Run: `cd report_translator && python3 -m pytest -q`
Expected: tümü PASS (engine + store + app).

- [ ] **Step 2: Frontend testleri + build**

Run: `cd report_translator/frontend && npx vitest run && npm run build`
Expected: tüm Vitest testleri PASS; `../web` üretilir.

- [ ] **Step 3: Canlı duman + editör akışı (sunucu)**

Run:
```bash
cd report_translator && nohup python3 -m uvicorn app:app --port 8731 --host 127.0.0.1 >/tmp/uv.log 2>&1 &
sleep 3
# upload, status, manifest, page png, original png, segment edit, save
python3 - <<'PY'
import requests, time, json
B="http://127.0.0.1:8731"
f=open("../reportsamples/en/Androbiome.pdf","rb")
r=requests.post(B+"/api/upload", files={"files":("Androbiome.pdf", f, "application/pdf")}).json()
s=r["session_id"]; fid=r["files"][0]["file_id"]
time.sleep(2)
st=requests.get(f"{B}/api/{s}/status").json(); print("status", st["files"][fid]["status"])
m=requests.get(f"{B}/api/{s}/{fid}/manifest").json(); print("segments", len(m))
assert requests.get(f"{B}/api/{s}/{fid}/page/0.png").content[:4]==b"\x89PNG"
assert requests.get(f"{B}/api/{s}/{fid}/original/0.png").content[:4]==b"\x89PNG"
seg=[x for x in m if x["en"]=="Yeast-like fungi"][0]
requests.post(f"{B}/api/{s}/{fid}/segment/{seg['id']}", json={"tr":"DENEME","scope":"report"})
sv=requests.post(f"{B}/api/{s}/{fid}/save").json(); print("saved", sv["saved_path"])
PY
pkill -f "uvicorn app:app"
```
Expected: status done, segments>0, PNG'ler geçerli, saved_path yazıldı.
(Not: `requests` yoksa `pip3 install requests` veya `httpx` ile uyarlayın.)

- [ ] **Step 4: Görsel doğrulama (controller yapar)**

Controller (sen): sunucuyu başlat, tarayıcı/PyWebView ile arayüzü aç, bir örnek PDF yükle, editörde sayfa önizlemesi + kutular + segment düzenleme + karşılaştırma + zoom + kaydet akışını ekran görüntüsüyle doğrula. Sorun varsa ilgili task'a dön.

- [ ] **Step 5: Commit (varsa düzeltmeler) + temizlik**

```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
git add -A && git commit -m "test: production paketi uçtan uca doğrulandı (backend+frontend+e2e)" || echo "değişiklik yok"
```

---

## Self-review notları (planı yazanın kontrolü)

- **Spec kapsamı:** tek-sayfa render+önbellek (Task 1,3) ✓; oturum kalıcılığı (Task 2,3) ✓; async upload+ilerleme (Task 3,7) ✓; original png/karşılaştırma (Task 3,8) ✓; revert/undo (Task 3,6,9) ✓; arama/filtre (Task 6,9) ✓; zoom/thumbnail (Task 8) ✓; kaydetme durumu/unsaved guard (Task 8) ✓; yapısal hata (Task 3,5) ✓; görsel cila (Task 10) ✓; PyWebView+PyInstaller (Task 11,12) ✓; çevrimdışı/CDN-yok (Task 4 base, public assets) ✓.
- **Tip/sözleşme tutarlılığı:** segment alanları `{id,page,bbox,en,tr,source,needs_review}` engine/app/manifest/store.js/bileşenler boyunca aynı; `scope` değerleri `dict|report|revert`; `editSegment(s,f,seg,tr,scope,force)` imzası client+SegmentPanel+app uyumlu; `pageUrl/originalUrl/reviewUrl/downloadAllUrl` client'ta tanımlı ve bileşenlerde kullanılıyor.
- **Sıra bağımlılığı:** Task 8 geçici SegmentPanel taslağı koyar, Task 9 tamamlar (build her iki adımda da geçer). Backend (Faz 1) frontend'den önce.
- **Bilinen sınır:** karşılaştırma görünümünde senkron kaydırma basit (ayrı kaydırma); gerekirse sonra senkronlanır. Render önbelleği dosya-bazında geçersiz kılınır (sayfa-bazlı ince ayar sonraya bırakıldı).
```
