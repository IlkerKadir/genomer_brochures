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
import aiconfig
import translator

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
    kits, common, passthrough, raw = dictionary.load()
    return kits[kit], passthrough, dictionary.compile_templates(raw, kit)


def _ai_for(kit):
    """(provider, markers, cache) veya None. Config kapalı/anahtarsız ise None."""
    cfg = aiconfig.load_config()
    provider = translator.get_provider(cfg)
    if provider is None:
        return None
    _, _, _, raw = dictionary.load()
    markers = dictionary.ai_markers(raw, kit)
    if not markers:
        return None
    # DeepL: klinik domain bağlamı (context) + standart terim glossary'si.
    context = cfg.get("deepl_context") or None
    if hasattr(provider, "context"):
        provider.context = context
    entries = aiconfig.glossary_entries_tsv()
    state = aiconfig.load_glossary_state()
    # Önbellek geçersizleştirme glossary API'sinden BAĞIMSIZ olmalı: glossary/context imzası
    # değişince eski çeviriler geçersizdir; glossary oluşturma (ağ/limit) başarısız olsa bile temizle.
    sig = translator.entries_hash((entries or "") + "\x00" + (context or ""))
    if state.get("cache_sig") != sig:
        aiconfig.clear_cache()
        state["cache_sig"] = sig
        aiconfig.save_glossary_state(state)
    try:
        if entries.strip() and hasattr(provider, "glossary_id"):
            gid = translator.ensure_glossary(cfg["deepl_api_key"], entries, state)
            if gid:
                provider.glossary_id = gid
                aiconfig.save_glossary_state(state)
    except Exception:
        pass    # glossary oluşturma başarısız (ağ/limit) -> glossary'siz devam (context yine etkin)
    return (provider, markers, aiconfig.load_cache())


def _file_or_404(sid, fid):
    try:
        return SESSIONS.get_file(sid, fid)
    except (KeyError, FileNotFoundError):
        raise AppError(404, "not_found", "Oturum veya dosya bulunamadı")


def _annotate(fs):
    table, passthrough, templates = _table_for(fs["kit"])
    doc = fitz.open(stream=fs["pdf_bytes"], filetype="pdf")
    try:
        ann = engine.translate_segments(engine.extract_segments(doc), table, passthrough,
                                        fs["overrides"], templates)
        ai = _ai_for(fs["kit"])
        if ai:
            engine.apply_ai_summary(ann, ai[0], ai[1], ai[2])
        return ann
    finally:
        doc.close()


def _counts(ann):
    translated = sum(1 for a in ann if a.source in ("dict-exact", "dict-partial", "override"))
    review = sum(1 for a in ann if a.needs_review)
    return {"translated": translated, "review": review, "total": len(ann)}


def _render_bytes(fs):
    table, passthrough, templates = _table_for(fs["kit"])
    return engine.translate_document_bytes(fs["pdf_bytes"], table, passthrough,
                                           fs["overrides"], templates, _ai_for(fs["kit"]))


def _process_file(sid, fid):
    """Arka planda: dosyayı çevir, otomatik kaydet, status=done."""
    try:
        fs = SESSIONS.get_file(sid, fid)
        _save_one(sid, fid, fs)
        SESSIONS.set_status(sid, fid, "done")
    except Exception as e:  # noqa
        SESSIONS.set_status(sid, fid, "error", str(e))


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    sid = SESSIONS.create_session()
    out = []
    for uf in files:
        data = await uf.read()
        if data[:4] != b"%PDF":
            out.append({"name": uf.filename, "error": "geçersiz PDF"})
            continue
        _doc = fitz.open(stream=data, filetype="pdf")
        try:
            kit = dictionary.detect_kit(_doc)
        finally:
            _doc.close()
        fid = SESSIONS.add_file(sid, uf.filename, data, kit)
        ann = _annotate(SESSIONS.get_file(sid, fid))
        counts = _counts(ann)
        SESSIONS.set_counts(sid, fid, counts)
        threading.Thread(target=_process_file, args=(sid, fid), daemon=True).start()
        out.append({"file_id": fid, "name": uf.filename, "kit": kit, "counts": counts})
    return {"session_id": sid, "files": out}


@app.get("/api/sessions")
def sessions():
    res = []
    for sid in SESSIONS.list_sessions():
        try:
            files = SESSIONS.list_files(sid)
        except (FileNotFoundError, KeyError):
            continue
        res.append({"session_id": sid,
                    "files": [{"file_id": k, "name": v["name"], "kit": v["kit"],
                               "counts": v.get("counts", {"translated": 0, "review": 0, "total": 0}),
                               "status": v.get("status", "done"),
                               "saved_path": v.get("saved_path")}
                              for k, v in files.items()]})
    return {"sessions": res}


@app.delete("/api/{sid}/{fid}")
def delete_file(sid: str, fid: str):
    try:
        SESSIONS.file_meta(sid, fid)
    except (KeyError, FileNotFoundError):
        raise AppError(404, "not_found", "Oturum veya dosya bulunamadı")
    CACHE.invalidate(fid)
    SESSIONS.delete_file(sid, fid)
    return {"ok": True}


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
    try:
        fids = list(SESSIONS.list_files(sid).keys())
    except (FileNotFoundError, KeyError):
        fids = []
    for fid in fids:
        CACHE.invalidate(fid)
    SESSIONS.delete_session(sid)
    return {"ok": True}


@app.get("/api/{sid}/{fid}/manifest")
def manifest(sid: str, fid: str):
    fs = _file_or_404(sid, fid)
    ann = _annotate(fs)
    return [{"id": a.id, "page": a.page, "bbox": a.seg.bbox, "en": a.en, "tr": a.tr,
             "source": a.source, "needs_review": a.needs_review} for a in ann]


def _check_page(pdf_bytes, n):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        count = doc.page_count
    finally:
        doc.close()
    if n < 0 or n >= count:
        raise AppError(404, "page_not_found", "Sayfa bulunamadı")


@app.get("/api/{sid}/{fid}/page/{n}.png")
def page_png(sid: str, fid: str, n: int):
    cached = CACHE.get(fid, n)
    if cached is not None:
        return Response(content=cached, media_type="image/png")
    fs = _file_or_404(sid, fid)
    _check_page(fs["pdf_bytes"], n)
    table, passthrough, templates = _table_for(fs["kit"])
    try:
        png = engine.render_page_png(fs["pdf_bytes"], table, passthrough, fs["overrides"], n,
                                     templates=templates, ai=_ai_for(fs["kit"]))
    except Exception:
        raise AppError(500, "render_failed", "Sayfa render edilemedi")
    CACHE.set(fid, n, png)
    return Response(content=png, media_type="image/png")


@app.get("/api/{sid}/{fid}/original/{n}.png")
def original_png(sid: str, fid: str, n: int):
    fs = _file_or_404(sid, fid)
    _check_page(fs["pdf_bytes"], n)
    table, passthrough, _tpl = _table_for(fs["kit"])
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
        ann_for_dict = _annotate(SESSIONS.get_file(sid, fid))
        en = next((a.en for a in ann_for_dict if a.id == seg), None)
        if en:
            res = dictionary.add_entry(fs["kit"], en, body.tr, overwrite=body.force)
            if res.get("conflict"):
                return {"ok": True, "conflict": True, "existing": res["existing"], "en": en}
            # Dict updated successfully — refresh persisted counts
            ann2 = _annotate(SESSIONS.get_file(sid, fid))
            SESSIONS.set_counts(sid, fid, _counts(ann2))
    return {"ok": True}


class KitBody(BaseModel):
    kit: Literal["femobiome_ii", "androbiome", "enterobiome_kids"]


@app.post("/api/{sid}/{fid}/kit")
def set_kit(sid: str, fid: str, body: KitBody):
    _file_or_404(sid, fid)
    SESSIONS.set_kit(sid, fid, body.kit)
    CACHE.invalidate(fid)
    ann = _annotate(SESSIONS.get_file(sid, fid))
    counts = _counts(ann)
    SESSIONS.set_counts(sid, fid, counts)
    return {"ok": True, "counts": counts}


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


@app.get("/api/config")
def get_config():
    return aiconfig.public_config()


class ConfigBody(BaseModel):
    ai_summary_enabled: bool | None = None
    deepl_api_key: str | None = None
    provider: str | None = None


@app.post("/api/config")
def set_config(body: ConfigBody):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    aiconfig.save_config(updates)
    return aiconfig.public_config()


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


# ── Sözlük yönetimi ──────────────────────────────────────────────────────────

DictScope = Literal["common", "femobiome_ii", "androbiome", "enterobiome_kids"]


@app.get("/api/dictionary")
def get_dictionary():
    """Tüm sözlük girişlerini listele."""
    return {"entries": dictionary.list_entries()}


class DictEntryBody(BaseModel):
    scope: DictScope
    en: str
    tr: str
    overwrite: bool = False


@app.post("/api/dictionary/entry")
def post_dict_entry(body: DictEntryBody):
    """Sözlüğe giriş ekle veya güncelle."""
    res = dictionary.set_entry(body.scope, body.en, body.tr, overwrite=body.overwrite)
    if res.get("conflict"):
        return {"ok": True, "conflict": True, "existing": res["existing"]}
    CACHE.clear()
    return {"ok": True}


class DictDeleteBody(BaseModel):
    scope: DictScope
    en: str


@app.post("/api/dictionary/delete")
def post_dict_delete(body: DictDeleteBody):
    """Sözlükten giriş sil."""
    res = dictionary.delete_entry(body.scope, body.en)
    if res.get("not_found"):
        return JSONResponse(status_code=404,
                            content={"ok": False, "error": {"code": "not_found",
                                                             "message": "Giriş bulunamadı"}})
    CACHE.clear()
    return {"ok": True}


if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
