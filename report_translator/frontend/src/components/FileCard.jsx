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
        <div class="stat ok">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
            style="flex-shrink:0">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          Çeviri tamamlandı
        </div>
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
