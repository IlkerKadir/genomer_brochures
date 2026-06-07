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
