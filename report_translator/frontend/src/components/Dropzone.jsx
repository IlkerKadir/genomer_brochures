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
      <p>PDF raporlarını buraya sürükleyin<br/><small>veya tıklayıp seçin (çoklu)</small></p>
      <input ref={input} type="file" accept="application/pdf" multiple hidden
        onChange={(e) => onFiles(e.target.files)} />
    </div>
  );
}
