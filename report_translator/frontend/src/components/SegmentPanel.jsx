import { SegmentItem } from "./SegmentItem.jsx";
import * as api from "../api/client.js";

export function SegmentPanel({ session, file, store, activeId, setActiveId, onChanged }) {
  const visible = store.visibleSegments.value;

  async function save(seg, tr, scope, force = false) {
    const r = await api.editSegment(session, file.file_id, seg.id, tr, scope, force);
    if (r.conflict) {
      if (confirm(`Bu metin sözlükte zaten "${r.existing}" olarak var. Üzerine yazılsın mı?`)) {
        await api.editSegment(session, file.file_id, seg.id, tr, "dict", true);
      } else {
        return; // iptal — yerel state değişmesin
      }
    }
    store.applyOverride(seg.id, tr);
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
