const $ = (s, r = document) => r.querySelector(s);
const api = (p, o) => fetch("/api" + p, o).then(r => r.json());
let SESSION = null, FILES = [], CUR = null, MANIFEST = [], FILTER = "all";

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 2200);
}

// ---- yükleme ----
const dz = $("#dropzone"), fi = $("#fileInput");
dz.onclick = () => fi.click();
dz.ondragover = e => { e.preventDefault(); dz.classList.add("drag"); };
dz.ondragleave = () => dz.classList.remove("drag");
dz.ondrop = e => { e.preventDefault(); dz.classList.remove("drag"); upload(e.dataTransfer.files); };
fi.onchange = () => upload(fi.files);

async function upload(fileList) {
  const fd = new FormData();
  [...fileList].forEach(f => fd.append("files", f));
  toast("Çevriliyor…");
  const res = await fetch("/api/upload", { method: "POST", body: fd }).then(r => r.json());
  SESSION = res.session_id; FILES = res.files;
  renderCards();
  $("#batchActions").classList.toggle("hidden", FILES.length === 0);
}

function renderCards() {
  const wrap = $("#cards"); wrap.innerHTML = "";
  FILES.forEach(f => {
    const c = document.createElement("div"); c.className = "card";
    if (f.error) {
      c.innerHTML = `<div class="name">${escapeHtml(f.name)}</div><div class="err">${escapeHtml(f.error)}</div>`;
    } else {
      const rev = f.counts.review;
      c.innerHTML = `<span class="kit">${escapeHtml(f.kit)}</span>
        <div class="name">${escapeHtml(f.name)}</div>
        <div class="stat ok">✓ ${f.counts.translated} çevrildi</div>
        ${rev ? `<div class="stat warn">⚠ ${rev} gözden geçirilecek</div>` : ""}
        <button data-f="${escapeHtml(f.file_id)}">Görüntüle / Düzelt</button>`;
      c.querySelector("button").onclick = () => openEditor(f);
    }
    wrap.appendChild(c);
  });
}

$("#saveAllBtn").onclick = async () => {
  const r = await api(`/${SESSION}/save_all`, { method: "POST" });
  toast(`${r.paths.length} dosya kaydedildi`);
};
$("#zipBtn").onclick = () => { location.href = `/api/${SESSION}/download_all`; };

// ---- editör ----
$("#backBtn").onclick = () => {
  $("#editView").classList.add("hidden"); $("#uploadView").classList.remove("hidden");
};
document.querySelectorAll(".filter button").forEach(b =>
  b.onclick = () => {
    FILTER = b.dataset.filter;
    document.querySelectorAll(".filter button").forEach(x => x.classList.remove("active"));
    b.classList.add("active"); renderSegments();
  });

async function openEditor(f) {
  CUR = f;
  $("#uploadView").classList.add("hidden"); $("#editView").classList.remove("hidden");
  $("#editTitle").textContent = f.name;
  MANIFEST = await api(`/${SESSION}/${f.file_id}/manifest`);
  await renderPages();
  renderSegments();
}

async function renderPages() {
  const pages = $("#pages"); pages.innerHTML = "";
  const maxPage = Math.max(...MANIFEST.map(s => s.page), 0);
  for (let n = 0; n <= maxPage; n++) {
    const wrap = document.createElement("div"); wrap.className = "pageWrap";
    const img = new Image();
    img.src = `/api/${SESSION}/${CUR.file_id}/page/${n}.png?t=${Date.now()}`;
    wrap.appendChild(img);
    img.onload = () => overlayBoxes(wrap, img, n);
    pages.appendChild(wrap);
  }
}

function overlayBoxes(wrap, img, n) {
  // PDF noktası 150 dpi'da: ölçek = render genişliği(px) / PDF genişliği(pt)
  const scale = img.clientWidth / (img.naturalWidth / (150 / 72));
  MANIFEST.filter(s => s.page === n).forEach(s => {
    const [x0, y0, x1, y1] = s.bbox;
    const b = document.createElement("div");
    b.className = "box" + (s.needs_review ? " review" : "");
    b.style.left = x0 * scale + "px"; b.style.top = y0 * scale + "px";
    b.style.width = (x1 - x0) * scale + "px"; b.style.height = (y1 - y0) * scale + "px";
    b.dataset.id = s.id;
    b.onclick = () => focusSeg(s.id);
    wrap.appendChild(b);
  });
}

function renderSegments() {
  const list = $("#segList"); list.innerHTML = "";
  MANIFEST.filter(s => FILTER === "all" || s.needs_review).forEach(s => {
    const el = document.createElement("div");
    el.className = "seg" + (s.needs_review ? " review" : "");
    el.dataset.id = s.id;
    el.innerHTML = `<div class="en">${escapeHtml(s.en)}</div>
      <textarea></textarea>
      <div class="acts">
        <button data-scope="dict">Sözlüğe ekle</button>
        <button class="ghost" data-scope="report">Sadece bu rapor</button>
      </div>`;
    const ta = el.querySelector("textarea");
    ta.value = s.tr;
    el.querySelectorAll("button").forEach(btn =>
      btn.onclick = () => saveSeg(s, ta.value, btn.dataset.scope));
    list.appendChild(el);
  });
}

function focusSeg(id) {
  document.querySelectorAll(".seg,.box").forEach(e => e.classList.remove("active"));
  const seg = document.querySelector(`.seg[data-id="${id}"]`);
  document.querySelectorAll(`.box[data-id="${id}"]`).forEach(b => b.classList.add("active"));
  if (seg) { seg.classList.add("active"); seg.scrollIntoView({ block: "center", behavior: "smooth" }); }
}

async function saveSeg(s, tr, scope) {
  const r = await api(`/${SESSION}/${CUR.file_id}/segment/${s.id}`,
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tr, scope }) });
  if (r.conflict) {
    if (confirm(`Bu metin sözlükte zaten "${r.existing}" olarak var. Üzerine yazılsın mı?`)) {
      await api(`/${SESSION}/${CUR.file_id}/segment/${s.id}`,
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tr, scope: "dict", force: true }) });
    } else return;
  }
  s.tr = tr;
  await renderPages();  // override'lı taze render
  toast(scope === "dict" ? "Sözlüğe eklendi" : "Bu rapora uygulandı");
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
