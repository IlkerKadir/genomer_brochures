import { useState, useEffect, useCallback } from "preact/hooks";
import * as api from "../api/client.js";

const SCOPES = ["common", "femobiome_ii", "androbiome", "enterobiome_kids"];

const SCOPE_LABEL = {
  common: "Ortak",
  femobiome_ii: "Femobiome II",
  androbiome: "Androbiome",
  enterobiome_kids: "Enterobiome Kids",
};

// ─── Row ───────────────────────────────────────────────────────────────────
function DictRow({ entry, onRefresh }) {
  const [localTr, setLocalTr] = useState(entry.tr);
  const [saved, setSaved] = useState(false);
  const dirty = localTr !== entry.tr;

  const handleSave = useCallback(async () => {
    try {
      await api.saveDictEntry(entry.scope, entry.en, localTr, true);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onRefresh();
    } catch (e) {
      alert(e.message);
    }
  }, [entry.scope, entry.en, localTr, onRefresh]);

  const handleDelete = useCallback(async () => {
    if (!confirm("Bu girişi silmek istediğinize emin misiniz?")) return;
    try {
      await api.deleteDictEntry(entry.scope, entry.en);
      onRefresh();
    } catch (e) {
      alert(e.message);
    }
  }, [entry.scope, entry.en, onRefresh]);

  return (
    <div class="dict-row">
      <span class="kit dict-scope">{SCOPE_LABEL[entry.scope] || entry.scope}</span>
      <span class="dict-en" title={entry.en}>{entry.en}</span>
      {entry.paragraph
        ? (
          <textarea
            class="dict-tr-input"
            value={localTr}
            onInput={(e) => setLocalTr(e.target.value)}
            rows={3}
          />
        )
        : (
          <input
            class="dict-tr-input"
            type="text"
            value={localTr}
            onInput={(e) => setLocalTr(e.target.value)}
          />
        )
      }
      <div class="dict-row-acts">
        <button
          class="mini"
          disabled={!dirty}
          onClick={handleSave}
          title="Değişikliği kaydet"
        >
          {saved ? "Kaydedildi" : "Kaydet"}
        </button>
        <button
          class="mini dict-del"
          onClick={handleDelete}
          title="Girişi sil"
        >
          Sil
        </button>
      </div>
    </div>
  );
}

// ─── Add Form ──────────────────────────────────────────────────────────────
function AddEntryForm({ onRefresh }) {
  const [scope, setScope] = useState(SCOPES[0]);
  const [en, setEn] = useState("");
  const [tr, setTr] = useState("");
  const [busy, setBusy] = useState(false);

  const handleAdd = useCallback(async () => {
    const enTrim = en.trim();
    const trTrim = tr.trim();
    if (!enTrim || !trTrim) { alert("EN ve TR alanları boş bırakılamaz."); return; }
    setBusy(true);
    try {
      const res = await api.saveDictEntry(scope, enTrim, trTrim, false);
      if (res.conflict) {
        const ok = confirm(
          `"${enTrim}" zaten "${res.existing}" olarak var. Üzerine yazılsın mı?`
        );
        if (ok) {
          await api.saveDictEntry(scope, enTrim, trTrim, true);
        } else {
          setBusy(false);
          return;
        }
      }
      setEn("");
      setTr("");
      onRefresh();
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }, [scope, en, tr, onRefresh]);

  return (
    <div class="dict-add card">
      <h3 class="dict-add-title">Yeni Giriş Ekle</h3>
      <div class="dict-add-fields">
        <select
          class="dict-select"
          value={scope}
          onChange={(e) => setScope(e.target.value)}
        >
          {SCOPES.map((s) => (
            <option key={s} value={s}>{SCOPE_LABEL[s]}</option>
          ))}
        </select>
        <input
          class="dict-input"
          type="text"
          placeholder="İngilizce (EN)"
          value={en}
          onInput={(e) => setEn(e.target.value)}
        />
        <input
          class="dict-input"
          type="text"
          placeholder="Türkçe (TR)"
          value={tr}
          onInput={(e) => setTr(e.target.value)}
        />
        <button onClick={handleAdd} disabled={busy}>
          {busy ? "Ekleniyor…" : "Ekle"}
        </button>
      </div>
    </div>
  );
}

// ─── Main View ─────────────────────────────────────────────────────────────
export function DictionaryView() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [scopeFilter, setScopeFilter] = useState("all");

  const refresh = useCallback(async () => {
    try {
      const data = await api.getDictionary();
      setEntries(data.entries || []);
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const filtered = entries.filter((e) => {
    if (scopeFilter !== "all" && e.scope !== scopeFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return e.en.toLowerCase().includes(q) || e.tr.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div class="dict">
      <AddEntryForm onRefresh={refresh} />

      <div class="dict-toolbar">
        <input
          class="dict-search searchBox"
          type="search"
          placeholder="EN veya TR içinde ara…"
          value={search}
          onInput={(e) => setSearch(e.target.value)}
        />
        <div class="filter">
          <button
            class={scopeFilter === "all" ? "active" : ""}
            onClick={() => setScopeFilter("all")}
          >
            Tümü
          </button>
          {SCOPES.map((s) => (
            <button
              key={s}
              class={scopeFilter === s ? "active" : ""}
              onClick={() => setScopeFilter(s)}
            >
              {SCOPE_LABEL[s]}
            </button>
          ))}
        </div>
        <span class="dict-count">
          {loading ? "Yükleniyor…" : `${filtered.length} giriş`}
        </span>
      </div>

      {loading
        ? (
          <div class="empty-state">
            <div class="skeleton-pulse" />
            <p>Sözlük yükleniyor…</p>
          </div>
        )
        : filtered.length === 0
          ? (
            <div class="empty-state">
              <p>Eşleşen giriş bulunamadı.</p>
            </div>
          )
          : (
            <div class="dict-list">
              {filtered.map((e) => (
                <DictRow
                  key={`${e.scope}::${e.en}`}
                  entry={e}
                  onRefresh={refresh}
                />
              ))}
            </div>
          )
      }
    </div>
  );
}
