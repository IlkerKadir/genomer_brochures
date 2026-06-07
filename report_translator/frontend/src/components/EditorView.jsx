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
