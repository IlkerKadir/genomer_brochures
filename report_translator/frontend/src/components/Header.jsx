import { useEffect, useState } from "preact/hooks";
import * as api from "../api/client.js";

export function Header() {
  const [outDir, setOut] = useState("");
  useEffect(() => { api.getOutDir().then((r) => setOut(r.out_dir)); }, []);
  return (
    <header>
      <img src="./genomerlogo.png" alt="Genomer" class="logo" />
      <h1>Rapor Çevirici <span>EN → TR</span></h1>
      <div class="out-dir">
        Çıktı: <code>{outDir}</code>
        <button class="mini" onClick={async () => {
          const p = prompt("Yeni çıktı klasörü:", outDir);
          if (p) { const r = await api.setOutDir(p); setOut(r.out_dir); }
        }}>Değiştir</button>
        <button class="mini" onClick={() => api.openOutDir()}>Klasörü aç</button>
      </div>
    </header>
  );
}
