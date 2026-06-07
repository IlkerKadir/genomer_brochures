import { useEffect } from "preact/hooks";
import { Dropzone } from "./Dropzone.jsx";
import { FileCard } from "./FileCard.jsx";
import * as api from "../api/client.js";

export function UploadView({ session, files, setSession, setFiles, onOpen }) {
  async function handleFiles(fileList) {
    try {
      const res = await api.upload(fileList);
      setSession(res.session_id);
      setFiles(res.files.map((f) => ({ ...f, status: f.error ? "error" : "pending" })));
    } catch (e) {
      alert("Yükleme başarısız: " + e.message);
    }
  }

  // ilerleme poll'ü: pending dosya kaldıkça durum çek
  const hasPending = files.some((f) => f.status === "pending");
  useEffect(() => {
    if (!session || !hasPending) return;
    const t = setInterval(async () => {
      const st = await api.getStatus(session);
      setFiles((prev) => prev.map((f) => {
        const s = st.files[f.file_id];
        return s ? { ...f, status: s.status, errorMsg: s.error } : f;
      }));
    }, 800);
    return () => clearInterval(t);
  }, [session, hasPending]);

  return (
    <section class="upload">
      <Dropzone onFiles={handleFiles} />
      {files.length > 0 && (
        <>
          <div class="cards-header">
            <h2>Yüklenen Raporlar</h2>
            <span>{files.length} dosya</span>
          </div>
          <div class="cards">
            {files.map((f) => <FileCard key={f.file_id || f.name} file={f} onOpen={onOpen} />)}
          </div>
        </>
      )}
      {files.length > 0 && (
        <div class="batch">
          <button onClick={() => api.saveAll(session)}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            Tümünü kaydet
          </button>
          <button class="ghost" onClick={() => (location.href = api.downloadAllUrl(session))}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            ZIP indir
          </button>
        </div>
      )}
    </section>
  );
}
