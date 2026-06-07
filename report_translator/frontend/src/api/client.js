async function jget(url) {
  const r = await fetch(url);
  if (!r.ok) throw await asError(r);
  return r.json();
}
async function jpost(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw await asError(r);
  return r.json();
}
async function asError(r) {
  try { const j = await r.json(); return new Error(j.error?.message || "İstek başarısız"); }
  catch { return new Error("İstek başarısız (" + r.status + ")"); }
}

export async function upload(fileList) {
  const fd = new FormData();
  [...fileList].forEach((f) => fd.append("files", f));
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  if (!r.ok) throw await asError(r);
  return r.json();
}
export const getStatus = (s) => jget(`/api/${s}/status`);
export const getSessions = () => jget(`/api/sessions`);
export const getManifest = (s, f) => jget(`/api/${s}/${f}/manifest`);
export const editSegment = (s, f, seg, tr, scope, force = false) =>
  jpost(`/api/${s}/${f}/segment/${seg}`, { tr, scope, force });
export const setKit = (s, f, kit) => jpost(`/api/${s}/${f}/kit`, { kit });
export const saveOne = (s, f) => jpost(`/api/${s}/${f}/save`);
export const saveAll = (s) => jpost(`/api/${s}/save_all`);
export const getOutDir = () => jget(`/api/out_dir`);
export const setOutDir = (path) => jpost(`/api/out_dir`, { path });
export const openOutDir = () => jpost(`/api/open_out_dir`);
export const deleteSession = (s) => fetch(`/api/${s}`, { method: "DELETE" });
export const deleteReport = (s, f) => fetch(`/api/${s}/${f}`, { method: "DELETE" });
export const pageUrl = (s, f, n) => `/api/${s}/${f}/page/${n}.png?t=${Date.now()}`;
export const originalUrl = (s, f, n) => `/api/${s}/${f}/original/${n}.png`;
export const reviewUrl = (s, f) => `/api/${s}/${f}/review.txt`;
export const downloadAllUrl = (s) => `/api/${s}/download_all`;
