# Rapor Çevirici — Production'a Geçiş (Tasarım)

**Tarih:** 2026-06-07
**Durum:** Onay bekliyor
**Bağlam:** `report_translator/` çalışan ama "demo seviyesi" bir yerel uygulama (FastAPI backend + ~150 satır vanilla JS frontend). Bu spec onu production-ready hâle getirir: profesyonel UX, zengin editör, güvenilirlik/performans, native paketleme.

## 1. Amaç ve kapsam

Dört boyutu birlikte ele almak:
1. **Görsel tasarım & UX cilası** — profesyonel arayüz, ilerleme/yükleme durumları, hata/boş durumlar, kaydetme geri bildirimi.
2. **Editör güç-özellikleri** — sayfa küçük-resimleri/gezinme, zoom, EN↔TR karşılaştırma, segment arama, override geri al, undo.
3. **Güvenilirlik & performans** — tek-sayfa render, oturum kalıcılığı, sağlam hata kurtarma, çok/büyük PDF.
4. **Gerçek paketleme** — PyInstaller .exe/.app, PyWebView penceresi, çevrimdışı, ikon.

**Değişmeyen ilke:** Orijinal PDF tek doğru kaynak; çıktı = `f(orijinal, sözlük, override'lar)`. Veri yereldedir, internet yok.

**Kapsam dışı (YAGNI):** Sonuç/özet (free-text) şablon çevirisi — ayrı bir iş olarak ertelendi. Çok-kullanıcı/sunucu dağıtımı. Kimlik doğrulama.

## 2. Mimari genel görünüm

```
report_translator/
  engine.py, dictionary.py        # MEVCUT — küçük eklemelerle (tek-sayfa render, revert)
  app.py                          # GENİŞLET — yeni uçlar, kalıcılık, async işleme, hata
  store.py                        # YENİ — oturum kalıcılığı (disk) + render önbelleği
  frontend/                       # YENİ — Vite + Preact kaynak (geliştirme)
    src/{components,state,api,styles}/
    index.html, vite.config.js, package.json
  web/                            # frontend build çıktısı (web/ = dist; FastAPI servis eder)
  launcher.py                     # YENİ — PyWebView penceresi + uvicorn
  build_app.md                    # GÜNCELLE — PyInstaller + frontend build
  fonts/, dictionary.json         # MEVCUT
```

**Geliştirme akışı:** Vite dev sunucusu (`npm run dev`, :5173) `/api`'yi FastAPI'ye (:8731) proxy'ler.
**Üretim akışı:** `npm run build` → `web/` (statik) → FastAPI servis eder → PyWebView penceresi → PyInstaller tek dosya. **CDN yok**; tüm varlıklar yerelde (çevrimdışı).

## 3. Backend (FastAPI) değişiklikleri

### 3.1 Tek-sayfa render + önbellek (performans)
Şu an `page/{n}.png` her çağrıda TÜM belgeyi render ediyor. Çözüm:
- `engine.render_page(doc, annotated, page_index)` — yalnızca bir sayfayı render eder (yalnız o sayfanın redaksiyon+yerleştirmesi).
- Dosya başına **render önbelleği** (`store.py`): `{file_id: {page_index: png_bytes}}`. Override değişince ilgili dosyanın önbelleği geçersiz kılınır (tüm sayfalar — basitlik; istenirse sadece etkilenen sayfa).
- `GET .../page/{n}.png` önbellekten servis eder; yoksa tek sayfa render edip önbelleğe koyar.

### 3.2 Orijinal (EN) sayfa render (karşılaştırma için)
- `GET /api/{s}/{f}/original/{n}.png` — orijinal PDF'in çevrilmemiş sayfa görüntüsü (EN↔TR yan yana için).

### 3.3 Oturum kalıcılığı (güvenilirlik)
- `store.py`: oturum durumu diske yazılır → `~/.genomer_cevirici/sessions/<session_id>/`:
  - her dosya için orijinal PDF (`<file_id>.pdf`) + `state.json` (name, kit, overrides, saved_path).
- Uygulama açılışında mevcut oturumlar listelenir; `GET /api/sessions` son oturumu döndürür → frontend yenileme/yeniden açılışta işe kaldığı yerden devam eder.
- Klinik veri yerelde; kullanıcı "Oturumu temizle" ile silebilir (`DELETE /api/{s}`).

### 3.4 Async yükleme + ilerleme (UX)
- `POST /api/upload` dosyaları **hemen** `pending` durumla kaydeder, file_id'leri döner; çeviriyi arka planda (FastAPI BackgroundTasks/thread) işler.
- `GET /api/{s}/status` → her dosyanın `{status: pending|done|error, counts?, error?}` durumu. Frontend bunu poll'ler ve ilerleme/iskelet gösterir.

### 3.5 Override yönetimi (editör)
- `POST .../segment/{seg}` — mevcut (tr, scope, force). `scope` değerleri `dict|report` + yeni `revert`.
- `revert`: o segmentin override'ını siler → render önbelleğini geçersiz kılar (sözlük değerine döner).

### 3.6 Sağlam hata yönetimi
- Tüm uçlarda yapısal hata gövdesi: `{error: {code, message}}`, uygun HTTP kodu. Bozuk PDF, render hatası, eksik oturum/dosya → kullanıcı-dostu mesaj (frontend bildirim sistemi gösterir). 500 yerine yakalanmış hata.

### 3.7 Klasör uçları (mevcut, korunur)
`GET/POST /api/out_dir`, `POST /api/open_out_dir`, `save`, `save_all`, `download`, `download_all`, `review.txt`.

## 4. Frontend (Vite + Preact)

### 4.1 Teknoloji
- **Vite + Preact** (JSX, düz JS), **@preact/signals** ile reaktif durum. Build → `web/`.
- Stil: yerel CSS (CSS değişkenleri + bileşen CSS modülleri). **Tailwind/CDN yok** (çevrimdışı). Görsel dil için `frontend-design` skill'i.
- İkonlar: satır içi SVG (yerel).

### 4.2 Bileşen mimarisi
```
App
 ├─ Header            (logo, çıktı klasörü göster/değiştir/aç, oturumu temizle)
 ├─ UploadView
 │   ├─ Dropzone      (çoklu sürükle-bırak)
 │   └─ FileCard[]    (kit rozeti, durum: pending spinner / ✓ N çevrildi / ⚠ M / hata+tekrar dene, "Düzelt", "Kaydet")
 │   └─ BatchBar      (Tümünü kaydet, ZIP indir)
 ├─ EditorView
 │   ├─ Toolbar       (geri, dosya adı, kaydetme durumu rozeti, EN↔TR karşılaştırma anahtarı, zoom −/+, "Gözden geçirme listesi")
 │   ├─ ThumbnailRail (sayfa küçük-resimleri; tıkla→atla; gözden-geçir işareti)
 │   ├─ PageCanvas    (render edilmiş sayfa; zoom/pan; tıklanabilir segment kutuları; karşılaştırma açıkken sol EN sağ TR)
 │   └─ SegmentPanel
 │       ├─ SearchFilter (arama kutusu + Tümü/Gözden geçirilecek)
 │       └─ SegmentItem[] (EN salt-okunur, TR textarea, "Sözlüğe ekle"/"Sadece bu rapor"/"Sözlüğe döndür", undo)
 ├─ Toasts            (bildirim yığını)
 └─ ConfirmDialog     (kaydedilmemiş değişiklik / sözlük çakışması)
```

### 4.3 Durum (signals)
- `session`, `files[]` (durum+counts), `currentFile`, `manifest[]`, `overrides` (yereldeki düzenlemeler), `saveStatus` (saved|unsaved|saving), `undoStack[]`, `compareMode`, `zoom`, `filter`, `search`.
- Düzenleme akışı: segment kaydet → API → ilgili sayfa görüntüsü cache-bust ile tazelenir → `saveStatus`/rozet güncellenir. Otomatik kayıt (mevcut) korunur; ayrıca açık "Kaydet".

### 4.4 UX davranışları
- **İlerleme:** yükleme sonrası kartlar `pending` spinner; `/status` poll → tamamlandıkça ✓/⚠/hata.
- **Yükleniyor durumları:** sayfa görüntüleri iskelet; editör açılışında manifest yüklenirken iskelet.
- **Kaydetme durumu:** düzenleme yapılınca "kaydedilmedi" noktası; kaydedilince "kaydedildi ✓".
- **Kaydedilmemiş değişiklik koruması:** editörden çıkış/pencere kapanışında uyarı.
- **Çakışma:** modal onay (mevcut force akışı).
- **Hata:** bildirim + dosya kartında "tekrar dene".
- **Boş durum:** dropzone yönlendirme metni + örnek.
- **Erişilebilirlik:** klavye ile segmentler arası gezinme, odak halkaları, yeterli kontrast.

### 4.5 Karşılaştırma görünümü
Toolbar anahtarı → PageCanvas iki sütun: sol `original/{n}.png` (EN), sağ `page/{n}.png` (TR), senkron kaydırma. Segment kutuları yalnız TR tarafında.

## 5. Paketleme

- `launcher.py`: uvicorn'u arka planda başlatır (boş port), **PyWebView** ile gerçek pencere açar (`webview.create_window("Genomer Rapor Çevirici", "http://127.0.0.1:<port>")`). Tarayıcı sekmesi yok.
- `requirements.txt` += `pywebview`.
- `build_app.md`: önce `cd frontend && npm install && npm run build` (→ `web/`), sonra PyInstaller `--add-data "web;web" --add-data "fonts;fonts" --add-data "dictionary.json;." --collect-all ... launcher.py`. Mac/Win ayrı notlar + ikon (`--icon`).
- `baslat.command`/`baslat.bat`: geliştirme/Python'lu çalıştırma için korunur (build edilmiş `web/`'i sunar).
- **Çevrimdışı:** tüm JS/CSS/font yerel; ağ çağrısı yok.

## 6. Veri akışı (özet)

1. Sürükle → `POST /upload` (pending döner) → kartlar spinner.
2. `/status` poll → done → counts; otomatik `out_dir`'e kaydedilir.
3. "Düzelt" → manifest + sayfa görüntüleri (önbellekli, tek-sayfa) → editör.
4. Segment düzenle → `POST segment` (report/dict/force/revert) → render önbelleği geçersiz → sayfa tazelenir → kaydetme durumu.
5. "Kaydet"/"Tümünü kaydet"/ZIP → `out_dir`'e taze yazım.
6. Yenileme/yeniden açılış → `GET /sessions` → kaldığı yerden devam (kalıcılık).

## 7. Hata yönetimi (uçtan uca)
- Bozuk/PDF-olmayan dosya → kart hatası + "tekrar dene"; parti devam eder.
- Render hatası (tek sayfa) → o sayfa için hata yer tutucusu + bildirim; diğer sayfalar etkilenmez.
- Backend istisnası → yapısal `{error}` + bildirim.
- Disk dolu/izin (kaydet) → bildirim, iş kaybolmaz (bellekte/oturum diskinde durur).
- Port meşgul → launcher boş port seçer.

## 8. Test
- **Backend (pytest):** tek-sayfa render eşdeğerliği (tam belge render'ı ile aynı sayfa içeriği); original render uç; oturum kalıcılığı round-trip (kaydet→yükle→aynı overrides); async upload status akışı; revert override; hata gövdeleri; mevcut 19 test yeşil kalır.
- **Frontend:** bileşen birim testleri (Vitest) — state reducer'ları/signals (override uygula/undo/revert, filtre/arama), API istemci (mock fetch). Editör render mantığı (bbox→ekran ölçek) birim testi.
- **E2E duman:** uvicorn + (geliştirmede) Vite; build sonrası `web/` üzerinden upload→manifest→segment edit→save curl/Playwright duman testi.
- **Görsel:** 3 kit sayfa render'ı + editör ekran görüntüsü (gözle).

## 9. Geriye uyumluluk
- CLI (`translate_report.py`) ve mevcut motor API'si korunur.
- Mevcut FastAPI uçları korunur; yenileri eklenir.
- `dictionary.json`, `fonts/` değişmez.

## 10. Riskler
- **Build adımı + Node bağımlılığı:** yalnızca geliştirmede; dağıtım statik. Node yoksa geliştirici kurar.
- **PyInstaller + PyWebView platform farkları:** mac/win ayrı test/ikon; v2'de imzalama.
- **Render performansı:** tek-sayfa + önbellek ile çözülür; çok büyük PDF'lerde yine de izlenir.
