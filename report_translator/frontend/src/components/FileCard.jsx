export function FileCard({ file, onOpen, onRemove }) {
  const c = file.counts || {};
  const isPending = file.status === "pending";
  const isError   = file.status === "error";

  return (
    <div class="card">
      <div class="card-top-row">
        {file.kit && <span class="kit">{file.kit}</span>}
        {onRemove && (
          <button class="card-remove" onClick={() => onRemove(file)} title="Kaldır">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
            Kaldır
          </button>
        )}
      </div>
      <div class="name">{file.name}</div>

      {isPending ? (
        <div class="stat">
          <span class="spinner" />
          çevriliyor…
        </div>
      ) : isError ? (
        <div class="err">
          {file.errorMsg || "Render hatası"}
        </div>
      ) : (
        <>
          <div class="stat ok">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
              style="flex-shrink:0">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            {c.translated} segment çevrildi
          </div>
          {c.review ? (
            <div class="stat warn">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
                style="flex-shrink:0">
                <path d="m10.29 3.86-8.63 14.9A1 1 0 0 0 2.5 20.5h19a1 1 0 0 0 .84-1.54l-9.5-14.9a1 1 0 0 0-1.55 0Z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              {c.review} gözden geçirilecek
            </div>
          ) : null}
        </>
      )}

      <button
        style="margin-top: auto;"
        disabled={isPending}
        onClick={() => onOpen(file)}>
        Görüntüle / Düzelt
      </button>
    </div>
  );
}
