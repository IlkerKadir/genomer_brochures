"""app.py — Rapor Çevirici yerel backend (FastAPI). Yalnız 127.0.0.1.
Orijinal PDF tek doğru kaynak; çıktı her zaman taze render edilir."""
import os
import io
import uuid
import zipfile
import fitz
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import engine
import dictionary

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")

app = FastAPI(title="Genomer Rapor Çevirici")

SESSIONS = {}  # session_id -> {"files": {file_id: FileState}}
_OUT_DIR = os.path.join(os.path.expanduser("~"), "Genomer Ceviriler")


def set_out_dir(path):
    global _OUT_DIR
    _OUT_DIR = path
    os.makedirs(_OUT_DIR, exist_ok=True)


def _table_for(kit):
    kits, common, passthrough, _ = dictionary.load()
    return kits[kit], passthrough


def _annotate(fs):
    table, passthrough = _table_for(fs["kit"])
    doc = fitz.open(stream=fs["pdf_bytes"], filetype="pdf")
    segs = engine.extract_segments(doc)
    return engine.translate_segments(segs, table, passthrough, fs["overrides"]), doc


def _counts(ann):
    translated = sum(1 for a in ann if a.source in ("dict-exact", "dict-partial", "override"))
    review = sum(1 for a in ann if a.needs_review)
    return {"translated": translated, "review": review, "total": len(ann)}


def _render_bytes(fs):
    table, passthrough = _table_for(fs["kit"])
    return engine.translate_document_bytes(fs["pdf_bytes"], table, passthrough, fs["overrides"])


def _get(session, file):
    sess = SESSIONS.get(session)
    if not sess or file not in sess["files"]:
        raise HTTPException(404, "oturum/dosya yok")
    return sess["files"][file]


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    set_out_dir(_OUT_DIR)
    session_id = uuid.uuid4().hex[:12]
    SESSIONS[session_id] = {"files": {}}
    out = []
    for uf in files:
        data = await uf.read()
        if not data[:4] == b"%PDF":
            out.append({"name": uf.filename, "error": "geçersiz PDF"})
            continue
        kit = dictionary.detect_kit(fitz.open(stream=data, filetype="pdf"))
        file_id = uuid.uuid4().hex[:8]
        fs = {"name": uf.filename, "pdf_bytes": data, "kit": kit,
              "overrides": {}, "saved_path": None}
        SESSIONS[session_id]["files"][file_id] = fs
        ann, _ = _annotate(fs)
        out.append({"file_id": file_id, "name": uf.filename, "kit": kit,
                    "counts": _counts(ann)})
    return {"session_id": session_id, "files": out}


@app.get("/api/{session}/{file}/manifest")
def manifest(session: str, file: str):
    fs = _get(session, file)
    ann, _ = _annotate(fs)
    return [{"id": a.id, "page": a.page, "bbox": a.seg.bbox, "en": a.en, "tr": a.tr,
             "source": a.source, "needs_review": a.needs_review} for a in ann]


@app.get("/api/{session}/{file}/page/{n}.png")
def page_png(session: str, file: str, n: int):
    fs = _get(session, file)
    out_bytes = _render_bytes(fs)
    doc = fitz.open(stream=out_bytes, filetype="pdf")
    if n < 0 or n >= len(doc):
        raise HTTPException(404, "sayfa yok")
    png = doc[n].get_pixmap(dpi=150).tobytes("png")
    return Response(content=png, media_type="image/png")


class SegmentEdit(BaseModel):
    tr: str
    scope: str  # "dict" | "report"


@app.post("/api/{session}/{file}/segment/{seg}")
def edit_segment(session: str, file: str, seg: str, body: SegmentEdit):
    fs = _get(session, file)
    fs["overrides"][seg] = body.tr
    result = {"ok": True}
    if body.scope == "dict":
        ann, _ = _annotate(fs)
        en = next((a.en for a in ann if a.id == seg), None)
        if en:
            res = dictionary.add_entry(fs["kit"], en, body.tr, overwrite=False)
            if res.get("conflict"):
                return {"ok": True, "conflict": True, "existing": res["existing"], "en": en}
    return result


class KitBody(BaseModel):
    kit: str


@app.post("/api/{session}/{file}/kit")
def set_kit(session: str, file: str, body: KitBody):
    fs = _get(session, file)
    fs["kit"] = body.kit
    fs["overrides"] = {}
    ann, _ = _annotate(fs)
    return {"ok": True, "counts": _counts(ann)}


def _save_one(fs):
    os.makedirs(_OUT_DIR, exist_ok=True)
    base = os.path.splitext(fs["name"])[0]
    path = os.path.join(_OUT_DIR, base + "_TR.pdf")
    with open(path, "wb") as f:
        f.write(_render_bytes(fs))
    fs["saved_path"] = path
    return path


@app.post("/api/{session}/{file}/save")
def save_one(session: str, file: str):
    fs = _get(session, file)
    return {"ok": True, "saved_path": _save_one(fs)}


@app.post("/api/{session}/save_all")
def save_all(session: str):
    sess = SESSIONS.get(session)
    if not sess:
        raise HTTPException(404, "oturum yok")
    return {"ok": True, "paths": [_save_one(fs) for fs in sess["files"].values()]}


@app.get("/api/{session}/{file}/download")
def download(session: str, file: str):
    fs = _get(session, file)
    base = os.path.splitext(fs["name"])[0]
    return Response(content=_render_bytes(fs), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{base}_TR.pdf"'})


@app.get("/api/{session}/download_all")
def download_all(session: str):
    sess = SESSIONS.get(session)
    if not sess:
        raise HTTPException(404, "oturum yok")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fs in sess["files"].values():
            base = os.path.splitext(fs["name"])[0]
            z.writestr(base + "_TR.pdf", _render_bytes(fs))
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="ceviriler.zip"'})


class OutDirBody(BaseModel):
    path: str


@app.post("/api/{session}/out_dir")
def change_out_dir(session: str, body: OutDirBody):
    set_out_dir(body.path)
    return {"ok": True, "out_dir": _OUT_DIR}


# statik frontend (en sonda mount edilir ki /api yolları gölgelenmesin)
if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
