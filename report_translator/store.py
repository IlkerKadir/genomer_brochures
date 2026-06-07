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
