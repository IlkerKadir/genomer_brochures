# Genomer Rapor Çevirici — Yerel Masaüstü Arayüzü (Tasarım)

**Tarih:** 2026-06-06
**Durum:** Onaylandı (uygulama planı bekliyor)
**Bağlam:** `report_translator/` çekirdek motoru (EN→TR qPCR rapor PDF çevirici) zaten çalışıyor.
Bu spec, onun üzerine müşteriye sunulacak bir arayüz ekler.

## 1. Amaç ve kapsam

DNA-Technology (Femoflor®/Androflor®) qPCR rapor PDF'lerini düzeni birebir koruyarak
EN→TR çeviren mevcut motora, **laboratuvar personelinin** kullanabileceği güzel bir
**yerel masaüstü arayüzü** eklemek. Üç ana yetenek:

1. **Çoklu PDF** kabul et → toplu çevir → tek tek veya ZIP indir.
2. **Segment düzeyinde düzeltme**: çevrilen/işaretlenen her metni satır içi düzelt, anında
   yeniden render gör.
3. Düzeltmeyi **kalıcı (sözlüğe)** veya **geçici (sadece bu rapor)** olarak uygula.

**Kapsam dışı (YAGNI):** serbest WYSIWYG PDF editörü (tıkla-taşı-keyfi metin) — font/düzen
kırılganlığını geri getirir, yüksek efor. Yapılmayacak.

## 2. Kullanıcı ve dağıtım

- **Son kullanıcı:** laboratuvar personeli (teknik değil), Windows ağırlıklı, Türkçe arayüz.
- **Gizlilik:** klinik veri **yereldedir**; sunucu yalnızca `127.0.0.1`'e bağlanır, hiçbir veri
  internete gitmez. Çevrilen PDF'ler **diske kaydedilir** (hasta raporu olarak saklanır/verilir).
- **Dağıtım:** makineye **native**, PyInstaller ile tek-dosya çalıştırılabilir (.exe/.app).
  Python kurulumu/bağımlılık yönetimi gerekmez. Hedef ölçek: lab başına 1-3 iş istasyonu.
  Docker/VM **kapsam dışı** (altyapı/IT gerektirir, bu kullanım için aşırı).

## 3. Mimari ilke

**Orijinal PDF = tek doğru kaynak.** Çevrilmiş çıktı her zaman saf bir fonksiyon:

```
çıktı = render( orijinal_kopya, çevir( çıkar(orijinal), sözlük, override'lar ) )
```

Redaksiyon yıkıcıdır (orijinali siler), bu yüzden hiçbir zaman çıktıyı tekrar düzenlemeyiz;
her düzeltmede orijinalin taze kopyasından yeniden üretiriz. Çeviri hızlıdır (~1-2 sn/rapor),
bu nedenle tam yeniden render sorunsuzdur ve yıkıcı-edit problemini ortadan kaldırır.

## 4. Bileşenler

### 4.1 Motor refaktörü — `report_translator/engine.py`

Mevcut `translate_report.py` mantığı saf, test edilebilir fonksiyonlara ayrılır. CLI ince
sarmalayıcı olarak korunur (geriye uyumlu).

- `extract_segments(doc) -> list[Segment]`
  Mevcut blok→satır gruplama mantığı. Her **Segment**:
  ```
  Segment {
    id:        str        # kararlı: f"{page}:{seq}" (sayfadaki sıra)
    page:      int
    bbox:      [x0,y0,x1,y1]
    en:        str        # birleştirilmiş ham kaynak metin
    style:     {fontfile, size, color, single_line}
    is_paragraph: bool
  }
  ```
- `translate_segments(segments, table, passthrough, overrides) -> list[AnnotatedSegment]`
  Her segmente çeviri + kaynak-tipi ekler:
  ```
  AnnotatedSegment (Segment + {
    tr:     str
    source: "dict-exact" | "dict-partial" | "passthrough" | "unknown" | "override"
    needs_review: bool      # unknown VEYA dict-partial
  })
  ```
  `overrides` = bu render için segment-id → tr eşlemesi (geçici düzeltmeler). Override varsa
  o segmentin kaynak-tipi `override` olur ve sözlüğün üstüne yazar.
- `render(doc_copy, annotated) -> bytes`
  Mevcut render mantığı (redaksiyon yalnız-metin + eşleşen tam fontla geri yazma + paragraf
  reflow + madde imi girintisi). Orijinalin taze kopyası üzerinde çalışır, PDF bayt'ı döndürür.
- `detect_kit(doc)` — mevcut; korunur.

`translate_report.py` CLI bu fonksiyonları çağıran ince katman olur (mevcut davranış aynı).

### 4.2 Sözlük yazımı — `report_translator/dictionary.py`

- `load() -> (table_by_kit, common, passthrough, raw)`
- `add_entry(kit, en, tr)` — `dictionary.json`'ı **yazmadan önce** `dictionary.json.bak`
  yedeği alır; `common`'da değilse ilgili kit bölümüne ekler; çok kelimeli akıcı metni
  `_paragraphs`'a, kısa etiketi düz bölüme koyar (heuristik: ≥6 kelime → `_paragraphs`).
- Aynı `en` zaten farklı bir `tr`'ye eşliyse: çağırana "çakışma" bildirir (UI onay ister).

### 4.3 Backend — `report_translator/app.py` (FastAPI)

**Oturum modeli (bellekte):** `sessions[session_id] = { files: {file_id: FileState}, out_dir }`.
```
FileState {
  name: str
  pdf_bytes: bytes          # orijinal (doğru kaynak; düzenleme için bellekte)
  kit: str
  overrides: {seg_id: tr}   # geçici (sadece bu rapor)
  saved_path: str | None    # diske yazılan TR PDF'in yolu
}
```
Çalışma durumu (override'lar, ara render'lar) bellektedir. **Çevrilmiş TR PDF'ler diske
kaydedilir** — kullanıcı bunları hasta raporu olarak saklar/verir. "İndir" ve "Kaydet" güncel
override'larla taze render üretip `out_dir` altına `<ad>_TR.pdf` yazar. Çıktı klasörü:
varsayılan `~/Genomer Ceviriler/` (kullanıcı arayüzden değiştirebilir).

**Uç noktalar:**
| Metot & yol | Gövde / dönüş |
|---|---|
| `POST /api/upload` | multipart N PDF → `{session_id, files:[{file_id,name,kit,counts}]}` |
| `GET /api/{s}/{f}/manifest` | `[AnnotatedSegment...]` (bbox, en, tr, source, needs_review) |
| `GET /api/{s}/{f}/page/{n}.png` | güncel override'larla render edilmiş sayfa görüntüsü |
| `POST /api/{s}/{f}/segment/{seg}` | `{tr, scope:"dict"\|"report"}` → override güncelle; scope=dict ise `add_entry`; `{ok, conflict?}` |
| `POST /api/{s}/{f}/kit` | `{kit}` → yeniden çevir |
| `POST /api/{s}/{f}/save` | taze render → `out_dir/<ad>_TR.pdf` diske yaz → `{saved_path}` |
| `POST /api/{s}/save_all` | tüm dosyaları `out_dir`'e yaz → `{paths[]}` |
| `GET /api/{s}/{f}/download` | TR PDF (tarayıcıdan indirme; alternatif) |
| `POST /api/{s}/out_dir` | `{path}` → çıktı klasörünü değiştir |
| `GET /api/{s}/{f}/review.txt` | gözden geçirme dosyası |

Yükleme sonrası her dosya otomatik bir kez `out_dir`'e kaydedilir; sonraki düzeltmelerde
"Kaydet" güncel hâli üzerine yazar. UI'da "Çıktı klasörünü aç" düğmesi bulunur.

`counts = {translated, review, total}`. Statik dosyalar (frontend + Genomer logosu) `/`
altından servis edilir.

### 4.4 Frontend — `report_translator/web/` (statik: index.html, app.js, styles.css)

Tek sayfa, **Türkçe**, Genomer markası. `frontend-design` skill'i uygulama aşamasında
estetik için kullanılır.

- **Yükleme ekranı:** çoklu sürükle-bırak; her dosya için durum kartı
  (kit rozeti, "✓ N çevrildi / ⚠ M gözden geçir"); "Tümünü indir (ZIP)".
- **Görüntüle/Düzelt ekranı (iki panel):**
  - Sol: render edilmiş sayfa görüntüleri; manifest bbox'ları görüntü ölçeğine göre
    **tıklanabilir kutu** olarak bindirilir. Bir kutuya tıklayınca sağdaki ilgili segmente
    kaydırır (ve tersi).
  - Sağ: segment listesi; filtre **Tümü / Gözden geçirilecek**. Her segment: EN kaynak
    (salt-okunur) + TR düzenleme alanı + iki düğme: **"Sözlüğe ekle"** (kalıcı) /
    **"Sadece bu rapor"** (geçici). Kaydedince ilgili sayfa görüntüsü anında tazelenir.
  - Sözlük çakışması: küçük onay diyaloğu ("Bu metin zaten X'e eşli; üzerine yazılsın mı?").
- Kit yanlış tespit edilmişse karttan açılır menüyle düzeltme → yeniden çevir.

## 5. Veri akışı (düzeltme döngüsü)

1. Kullanıcı segmentin TR'sini düzenler, "Sadece bu rapor" veya "Sözlüğe ekle" der.
2. Backend: `overrides[seg]=tr` (+ scope=dict ise `add_entry` ve tablo yeniden yüklenir).
3. Backend: `render(copy(pdf_bytes), translate_segments(extract(doc), table, overrides))`.
4. İlgili sayfa PNG'si frontend'e döner; görüntü tazelenir.
5. "İndir" her zaman güncel override'larla taze render üretir.

## 6. Hata yönetimi

- **PDF olmayan/bozuk dosya:** dosya başına hata kartı, atla, diğerleri devam.
- **Bilinmeyen kit:** `femobiome_ii` varsayılan + kartta düzeltme menüsü.
- **Sözlük yazım çakışması:** UI onayı; onayda üzerine yaz, `dictionary.json.bak` zaten yedek.
- **Eksik/eşlenememiş font:** mevcut `map_font` Arial fallback'i.
- **Büyük parti:** dosyalar sırayla işlenir; UI ilerleme/iskelet gösterir.
- **Port meşgul:** başlatıcı boş port seçer ve tarayıcıyı ona yönlendirir.

## 7. Paketleme ve çalıştırma

- `report_translator/requirements.txt`: `fastapi`, `uvicorn`, `pymupdf`, `python-multipart`.
- **Geliştirme:** `baslat.command` (mac) / `baslat.bat` (win) → venv kur, bağımlılık yükle,
  uvicorn başlat, tarayıcıyı `127.0.0.1`'e aç.
- **Dağıtım:** PyInstaller ile tek-dosya çalıştırılabilir (gömülü uvicorn + statik frontend +
  `fonts/` + `dictionary.json`). Çift tıkla çalışır; Python gerektirmez.
- **v2 (sonra):** PyWebView ile gerçek pencere (tarayıcı sekmesi yok); ardından PyInstaller
  paketlemesi `.app`/`.exe` olarak.

## 8. Test

- **Motor birim testleri:** `extract_segments` kararlı id'ler; `translate_segments` override
  uygulaması ve kaynak-tipi; `render` determinizmi (aynı girdi → aynı bayt yapısı);
  `dictionary.add_entry` round-trip + yedek + çakışma tespiti.
- **API testleri:** upload → manifest → segment düzelt (her iki kapsam) → download; ZIP.
- **Görsel kontrol:** 3 kit örnek sayfası render edilip gözle/golden karşılaştırma.

## 9. Dosya yapısı (hedef)

```
report_translator/
  engine.py          # çıkar / çevir / render (saf)
  dictionary.py      # yükle / add_entry / çakışma
  translate_report.py# CLI (engine üstüne ince sarmalayıcı)
  app.py             # FastAPI backend
  web/               # index.html, app.js, styles.css, genomerlogo.png
  fonts/             # mevcut
  dictionary.json    # mevcut (+ .bak yedek)
  requirements.txt
  baslat.command / baslat.bat
  out/               # mevcut örnek çıktılar
  README.md          # güncellenecek
```

## 10. Bilinen sınırlar (değişmedi)

- Reflow edilen paragraflarda italik Latin tür adları düz yazılır.
- Hastaya özel serbest metin yalnızca sözlükte karşılığı varsa çevrilir; segment düzeltme +
  "sözlüğe ekle" bu boşluğu zamanla kapatır.
