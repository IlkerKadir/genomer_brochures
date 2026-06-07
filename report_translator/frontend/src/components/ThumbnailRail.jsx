export function ThumbnailRail({ session, file, pageCount, manifest, onJump, refreshKey }) {
  const reviewPages = new Set(manifest.filter((s) => s.needs_review).map((s) => s.page));
  return (
    <div class="thumbs">
      {Array.from({ length: pageCount }).map((_, n) => {
        const hasReview = reviewPages.has(n);
        return (
          <button key={n} class={"thumb" + (hasReview ? " thumb-review" : "")}
            onClick={() => onJump(n)}
            title={"Sayfa " + (n + 1) + (hasReview ? " — gözden geçirilecek" : "")}
            aria-label={"Sayfa " + (n + 1)}>
            <img
              src={`/api/${session}/${file.file_id}/page/${n}.png?v=${refreshKey}`}
              alt={"Sayfa " + (n + 1)}
              loading="lazy"
            />
            <span class={"thumbNo" + (hasReview ? " thumbNo-warn" : "")}>
              {n + 1}{hasReview ? " ⚠" : ""}
            </span>
          </button>
        );
      })}
    </div>
  );
}
