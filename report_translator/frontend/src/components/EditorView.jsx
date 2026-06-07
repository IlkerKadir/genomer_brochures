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
        <button class="ghost" onClick={onBack}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 18-6-6 6-6"/>
          </svg>
          Geri
        </button>
        <strong>{file.name}</strong>
        <SaveBadge status={store.saveStatus.value} />
        <label class="cmp">
          <input type="checkbox" checked={compare}
            onChange={(e) => setCompare(e.target.checked)} />
          EN↔TR karşılaştır
        </label>
        <span class="zoom">
          <button class="mini" onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))} aria-label="Küçült">−</button>
          <span style="min-width:32px; text-align:center;">{Math.round(zoom * 100)}%</span>
          <button class="mini" onClick={() => setZoom((z) => Math.min(2, z + 0.1))} aria-label="Büyüt">+</button>
        </span>
        <a class="mini-link" href={api.reviewUrl(session, file.file_id)}>
          Gözden geçirme listesi ↗
        </a>
        <button onClick={async () => { await api.saveOne(session, file.file_id);
          store.saveStatus.value = "saved"; }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          Kaydet
        </button>
      </div>
      {loading ? (
        <div class="skeleton">
          <div class="skeleton-pulse"></div>
          <p>Sayfa verileri yükleniyor…</p>
        </div>
      ) : (
        <div class="editorBody">
          <ThumbnailRail session={session} file={file} pageCount={pageCount}
            manifest={store.manifest.value} onJump={jump} refreshKey={refreshKey} />
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
  const map = {
    saved:   ["kaydedildi ✓", "ok"],
    unsaved: ["kaydedilmedi ●", "warn"],
    saving:  ["kaydediliyor…", ""],
  };
  const [t, c] = map[status] || map.saved;
  return <span class={"saveBadge " + c}>{t}</span>;
}
