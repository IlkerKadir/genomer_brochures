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
