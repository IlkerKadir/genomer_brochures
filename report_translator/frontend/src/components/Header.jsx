import { useEffect, useState } from "preact/hooks";
import * as api from "../api/client.js";

export function Header({ view, onNav }) {
  const [outDir, setOut] = useState("");
  useEffect(() => { api.getOutDir().then((r) => setOut(r.out_dir)); }, []);
  return (
    <header>
      <img src="./genomerlogo.png" alt="Genomer" class="logo" />
      <div class="header-divider" aria-hidden="true" />
      <h1>
        Rapor Çevirici
        <span>EN → TR</span>
      </h1>
      <nav class="nav-tabs" aria-label="Ana gezinti">
        <button
          class={`nav-tab${view === "reports" ? " active" : ""}`}
          onClick={() => onNav("reports")}
        >
          Raporlar
        </button>
        <button
          class={`nav-tab${view === "dictionary" ? " active" : ""}`}
          onClick={() => onNav("dictionary")}
        >
          Sözlük
        </button>
        <button
          class={`nav-tab${view === "settings" ? " active" : ""}`}
          onClick={() => onNav("settings")}
        >
          Ayarlar
        </button>
      </nav>
      <div class="out-dir">
        <span>Çıktı:</span>
        <code title={outDir}>{outDir || "—"}</code>
        <button class="mini" onClick={async () => {
          const p = prompt("Yeni çıktı klasörü:", outDir);
          if (p) { const r = await api.setOutDir(p); setOut(r.out_dir); }
        }}>Değiştir</button>
        <button class="mini" onClick={() => api.openOutDir()}>Klasörü aç</button>
      </div>
    </header>
  );
}
