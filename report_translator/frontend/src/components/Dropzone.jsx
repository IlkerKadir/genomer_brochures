import { useRef, useState } from "preact/hooks";

export function Dropzone({ onFiles }) {
  const input = useRef(null);
  const [drag, setDrag] = useState(false);
  return (
    <div class={"dropzone" + (drag ? " drag" : "")}
      onClick={() => input.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); onFiles(e.dataTransfer.files); }}>
      <div class="dropzone-icon" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="12" y1="18" x2="12" y2="12"/>
          <line x1="9" y1="15" x2="15" y2="15"/>
        </svg>
      </div>
      <p class="dropzone-title">PDF raporlarını buraya sürükleyin</p>
      <p class="dropzone-sub">veya tıklayarak bilgisayarınızdan seçin</p>
      <span class="dropzone-hint">Birden fazla raporu aynı anda ekleyebilirsiniz · Yalnızca PDF</span>
      <input ref={input} type="file" accept="application/pdf" multiple hidden
        onChange={(e) => onFiles(e.target.files)} />
    </div>
  );
}
