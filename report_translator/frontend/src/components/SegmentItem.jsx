import { useState, useEffect } from "preact/hooks";

export function SegmentItem({ seg, active, onFocus, onSave, onRevert }) {
  const [val, setVal] = useState(seg.tr);
  useEffect(() => setVal(seg.tr), [seg.tr]);
  return (
    <div
      class={"seg" + (seg.needs_review ? " review" : "") + (active ? " active" : "")}
      onClick={onFocus}>
      <div class="en">{seg.en}</div>
      <textarea
        value={val}
        onInput={(e) => setVal(e.target.value)}
        rows={2}
        onClick={(e) => e.stopPropagation()}
      />
      <div class="acts">
        <button onClick={(e) => { e.stopPropagation(); onSave(val, "dict"); }}>
          Sözlüğe ekle
        </button>
        <button class="ghost" onClick={(e) => { e.stopPropagation(); onSave(val, "report"); }}>
          Sadece bu rapor
        </button>
        {seg.source === "override" && (
          <button class="ghost" onClick={(e) => { e.stopPropagation(); onRevert(); }}>
            Sözlüğe döndür
          </button>
        )}
      </div>
    </div>
  );
}
