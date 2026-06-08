import { useEffect, useState } from "preact/hooks";
import * as api from "../api/client.js";

export function SettingsView() {
  const [cfg, setCfg] = useState(null);
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState("");
  useEffect(() => { api.getConfig().then(setCfg); }, []);
  if (!cfg) return <div class="skeleton">Yükleniyor…</div>;

  async function toggle(e) {
    const c = await api.setConfig({ ai_summary_enabled: e.target.checked });
    setCfg(c); setMsg("Kaydedildi");
  }
  async function saveKey() {
    const c = await api.setConfig({ deepl_api_key: key, provider: "deepl" });
    setCfg(c); setKey(""); setMsg("Anahtar kaydedildi");
  }
  return (
    <section class="settings">
      <h2>Ayarlar — Sonuç özeti AI çevirisi</h2>
      <p class="settings-note">Yalnız hastaya-özel <b>sonuç özeti</b> harici servise (DeepL) gönderilir.
        Hasta adı, tarih, ID gibi veriler <b>asla</b> gönderilmez. Çıktı düzenlenebilir taslaktır.</p>
      <label class="settings-row">
        <input type="checkbox" checked={cfg.ai_summary_enabled} onChange={toggle} />
        Sonuç özetini AI (DeepL) ile çevir
      </label>
      <div class="settings-row">
        <span>DeepL API anahtarı {cfg.has_key ? "✓ (kayıtlı)" : "(tanımsız)"}</span>
        <input type="password" placeholder="DeepL-Auth-Key…" value={key}
          onInput={(e) => setKey(e.target.value)} />
        <button onClick={saveKey} disabled={!key}>Anahtarı kaydet</button>
      </div>
      {msg && <div class="settings-msg">{msg}</div>}
    </section>
  );
}
