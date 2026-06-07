export function FileCard({ file, onOpen }) {
  if (file.error)
    return <div class="card"><div class="name">{file.name}</div>
      <div class="err">{file.error}</div></div>;
  const c = file.counts || {};
  return (
    <div class="card">
      <span class="kit">{file.kit}</span>
      <div class="name">{file.name}</div>
      {file.status === "pending"
        ? <div class="stat"><span class="spinner" /> çevriliyor…</div>
        : file.status === "error"
        ? <div class="err">hata: {file.errorMsg || "render"}</div>
        : <>
            <div class="stat ok">✓ {c.translated} çevrildi</div>
            {c.review ? <div class="stat warn">⚠ {c.review} gözden geçirilecek</div> : null}
          </>}
      <button disabled={file.status === "pending"} onClick={() => onOpen(file)}>
        Görüntüle / Düzelt</button>
    </div>
  );
}
