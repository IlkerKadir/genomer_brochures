import { useState, useEffect } from "preact/hooks";
import { Header } from "./components/Header.jsx";
import { UploadView } from "./components/UploadView.jsx";
import { EditorView } from "./components/EditorView.jsx";
import { DictionaryView } from "./components/DictionaryView.jsx";
import { SettingsView } from "./components/SettingsView.jsx";
import * as api from "./api/client.js";
import "./styles/components.css";

export function App() {
  // reports: düz liste; her öğe {session_id, file_id, name, kit, counts, status, saved_path, errorMsg?}
  const [reports, setReports] = useState([]);
  // editing: tıklanan report nesnesi (session_id + file_id dahil) — klinik güvenlik
  const [editing, setEditing] = useState(null);
  // view: "reports" | "dictionary" | "settings"
  const [view, setView] = useState("reports");

  // Açılışta kalıcı oturumlardan kütüphane yükle
  useEffect(() => {
    api.getSessions().then((data) => {
      const flat = [];
      for (const sess of data.sessions) {
        for (const f of sess.files) {
          flat.push({
            session_id: sess.session_id,
            file_id: f.file_id,
            name: f.name,
            kit: f.kit,
            counts: f.counts,
            status: f.status,
            saved_path: f.saved_path,
          });
        }
      }
      setReports(flat);
    }).catch(() => {/* backend henüz hazır değilse sessizce geç */});
  }, []);

  return (
    <div class="app">
      <Header view={view} onNav={setView} />
      {view === "settings"
        ? <SettingsView />
        : view === "dictionary"
          ? <DictionaryView />
          : editing
            ? <EditorView file={editing} onBack={() => setEditing(null)} />
            : <UploadView reports={reports} setReports={setReports} onOpen={setEditing} />}
    </div>
  );
}
