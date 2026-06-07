import { useEffect } from "preact/hooks";
import { Dropzone } from "./Dropzone.jsx";
import { FileCard } from "./FileCard.jsx";
import * as api from "../api/client.js";

export function UploadView({ session, files, setSession, setFiles, onOpen }) {
  async function handleFiles(fileList) {
    const res = await api.upload(fileList);
    setSession(res.session_id);
    setFiles(res.files.map((f) => ({ ...f, status: f.error ? "error" : "pending" })));
  }

  // ilerleme poll'ü: pending dosya kaldıkça durum çek
  useEffect(() => {
    if (!session) return;
    const pending = files.some((f) => f.status === "pending");
    if (!pending) return;
    const t = setInterval(async () => {
      const st = await api.getStatus(session);
      setFiles((prev) => prev.map((f) => {
        const s = st.files[f.file_id];
        return s ? { ...f, status: s.status, errorMsg: s.error } : f;
      }));
    }, 800);
    return () => clearInterval(t);
  }, [session, files]);

  return (
    <section class="upload">
      <Dropzone onFiles={handleFiles} />
      {files.length > 0 && (
        <div class="cards">
          {files.map((f) => <FileCard key={f.file_id || f.name} file={f} onOpen={onOpen} />)}
        </div>
      )}
      {files.length > 0 && (
        <div class="batch">
          <button onClick={() => api.saveAll(session)}>Tümünü kaydet</button>
          <button class="ghost" onClick={() => (location.href = api.downloadAllUrl(session))}>
            ZIP indir</button>
        </div>
      )}
    </section>
  );
}
