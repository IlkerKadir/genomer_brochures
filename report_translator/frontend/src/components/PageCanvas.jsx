import { useRef, useState } from "preact/hooks";
import * as api from "../api/client.js";

const DPI = 150;

export function PageCanvas({ session, file, pageCount, manifest, zoom, compare,
                            activeId, onPickSegment, refreshKey }) {
  return (
    <div class="pages" style={{ "--zoom": zoom }}>
      {Array.from({ length: pageCount }).map((_, n) => (
        <PageImage key={n + "_" + refreshKey} session={session} file={file} n={n}
          manifest={manifest.filter((s) => s.page === n)} compare={compare}
          activeId={activeId} onPickSegment={onPickSegment} />
      ))}
    </div>
  );
}

function PageImage({ session, file, n, manifest, compare, activeId, onPickSegment }) {
  const wrap = useRef(null);
  const [dims, setDims] = useState(null);
  function onLoad(e) {
    const img = e.target;
    setDims({ w: img.clientWidth, nat: img.naturalWidth });
  }
  const scale = dims ? dims.w / (dims.nat / (DPI / 72)) : 0;
  return (
    <div class="pageRow">
      {compare && (
        <div class="pageWrap">
          <img src={api.originalUrl(session, file.file_id, n)} alt={"EN sayfa " + (n + 1)} />
          <div class="pageTag">EN</div>
        </div>
      )}
      <div class="pageWrap" ref={wrap}>
        <img src={api.pageUrl(session, file.file_id, n)} onLoad={onLoad} alt={"TR sayfa " + (n + 1)} />
        {compare && <div class="pageTag">TR</div>}
        {dims && manifest.map((s) => {
          const [x0, y0, x1, y1] = s.bbox;
          return <div key={s.id}
            class={"box" + (s.needs_review ? " review" : "") + (s.id === activeId ? " active" : "")}
            style={{ left: x0 * scale, top: y0 * scale,
                     width: (x1 - x0) * scale, height: (y1 - y0) * scale }}
            onClick={() => onPickSegment(s.id)} />;
        })}
      </div>
    </div>
  );
}
