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
