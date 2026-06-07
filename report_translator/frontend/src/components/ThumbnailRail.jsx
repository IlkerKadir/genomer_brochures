export function ThumbnailRail({ session, file, pageCount, manifest, onJump, refreshKey }) {
  const reviewPages = new Set(manifest.filter((s) => s.needs_review).map((s) => s.page));
  return (
    <div class="thumbs">
      {Array.from({ length: pageCount }).map((_, n) => (
        <button key={n} class="thumb" onClick={() => onJump(n)}>
          <img src={`/api/${session}/${file.file_id}/page/${n}.png?v=${refreshKey}`} alt={"Sayfa " + (n + 1)} />
          <span class="thumbNo">{n + 1}{reviewPages.has(n) ? " ⚠" : ""}</span>
        </button>
      ))}
    </div>
  );
}
