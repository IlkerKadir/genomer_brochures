import * as api from "../api/client.js";

export function ThumbnailRail({ session, file, pageCount, manifest, onJump }) {
  const reviewPages = new Set(manifest.filter((s) => s.needs_review).map((s) => s.page));
  return (
    <div class="thumbs">
      {Array.from({ length: pageCount }).map((_, n) => (
        <button key={n} class="thumb" onClick={() => onJump(n)}>
          <img src={api.pageUrl(session, file.file_id, n)} alt={"Sayfa " + (n + 1)} />
          <span class="thumbNo">{n + 1}{reviewPages.has(n) ? " ⚠" : ""}</span>
        </button>
      ))}
    </div>
  );
}
