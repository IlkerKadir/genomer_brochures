import { useEffect, useRef } from "preact/hooks";
import { Dropzone } from "./Dropzone.jsx";
import { FileCard } from "./FileCard.jsx";
import * as api from "../api/client.js";

export function UploadView({ reports, setReports, onOpen }) {
  // pending olan distinct session_id'lerini izle
  const pendingSessionsRef = useRef(new Set());

  async function handleFiles(fileList) {
    try {
      const res = await api.upload(fileList);
      const newReports = res.files.map((f) => ({
        session_id: res.session_id,
        file_id: f.file_id,
        name: f.name || f.error,
        kit: f.kit,
        counts: f.counts || { translated: 0, review: 0, total: 0 },
        status: f.error ? "error" : "pending",
        errorMsg: f.error,
        saved_path: null,
      }));
      // Mevcut reports listesine EKLE (replace etme)
      setReports((prev) => [...prev, ...newReports]);
      // Yeni session'ı poll kuyruğuna ekle
      pendingSessionsRef.current.add(res.session_id);
    } catch (e) {
      alert("Yükleme başarısız: " + e.message);
    }
  }

  async function handleRemove(report) {
    try {
      await api.deleteReport(report.session_id, report.file_id);
      setReports((prev) => prev.filter((r) => r.file_id !== report.file_id));
    } catch (e) {
      alert("Kaldırma başarısız: " + e.message);
    }
  }

  async function handleSaveAll() {
    for (const r of reports) {
      if (r.status === "done") {
        try { await api.saveOne(r.session_id, r.file_id); } catch {}
      }
    }
  }

  // Pending raporları olan session'ları poll'le
  const hasPending = reports.some((r) => r.status === "pending");
  useEffect(() => {
    if (!hasPending) return;

    // pending olan session'ların distinct listesi
    const pendingSids = [...new Set(
      reports.filter((r) => r.status === "pending").map((r) => r.session_id)
    )];

    const t = setInterval(async () => {
      for (const sid of pendingSids) {
        try {
          const st = await api.getStatus(sid);
          setReports((prev) => prev.map((r) => {
            if (r.session_id !== sid) return r;
            const s = st.files[r.file_id];
            return s ? { ...r, status: s.status, saved_path: s.saved_path, errorMsg: s.error } : r;
          }));
        } catch {}
      }
    }, 800);
    return () => clearInterval(t);
  }, [hasPending, reports.map((r) => r.session_id + r.status).join(",")]);

  return (
    <section class="upload">
      <Dropzone onFiles={handleFiles} />
      {reports.length > 0 && (
        <>
          <div class="cards-header">
            <h2>Rapor Kütüphanesi</h2>
            <span>{reports.length} dosya</span>
          </div>
          <div class="cards">
            {reports.map((r) => (
              <FileCard
                key={r.file_id}
                file={r}
                onOpen={onOpen}
                onRemove={handleRemove}
              />
            ))}
          </div>
        </>
      )}
      {reports.length > 0 && (
        <div class="batch">
          <button onClick={handleSaveAll}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            Tümünü kaydet
          </button>
        </div>
      )}
    </section>
  );
}
