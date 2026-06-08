# Vektör-Outline Raporlarda "Kapat + Yeniden Yaz" Tasarımı

**Tarih:** 2026-06-08
**Bileşen:** `report_translator/engine.py` (`_render_page_items`)

## Problem

Gerçek lab çıktısı Femobiome raporları (`Femo 07.05.2026.pdf`, DNA-Technology rapor yazılımı),
görünen gövde metnini **vektör outline (eğriye çevrilmiş)** olarak çizer ve bunun üstüne
ayrı bir **görünmez/çift metin katmanı** koyar (arama/seçim amaçlı).

Mevcut çeviri motoru metin katmanını redakte edip (`fill=None`, `text=REMOVE`) yerine Türkçe yazar.
Bu, gizli metin katmanını kaldırır ama **görünen vektör-outline İngilizce kalır** → tüm gövdede
İngilizce + Türkçe **çakışması** (banner alt-yazısı, sonuç kutusu, tablo başlıkları, lejant vb.).

Doğrulamalar:
- Tüm metin redakte edilse bile İngilizce ("Yeast fungi", "Candida spp.", "Reference"...) görünür
  → metin değil, vektör outline.
- Çıktının metin katmanı tamamen temiz Türkçe (hiç İngilizce yok), buna rağmen pixmap'te İngilizce var.
- Orijinal bölünmemiş PDF de birebir aynı (sayfa başına 421 vektör path) → split kaynaklı **değil**.

Önceki tip raporlar (`reportsamples/en/`) normal metin-katmanlıydı; bu lab çıktısı yapısal olarak farklı.

## Çözüm

Redaksiyonu `fill=None` yerine **`fill=<zemin rengi>`** ile yap. Bu, redakte edilen dikdörtgeni
zemin rengiyle boyar; böylece **hem gizli metni hem altındaki vektör-outline İngilizceyi örter.**
Üstüne Türkçe eskisi gibi yazılır.

Zemin rengi her segment için orijinal sayfadan **örneklenir** (gövdede beyaz, başlık satırlarında
açık gri). Bu sayede gri başlık satırlarında beyaz yama oluşmaz.

### Neden bu yaklaşım

- Alternatif "seçici grafik redaksiyonu" (sadece harf-vektörlerini sil): 421 path arasında
  harf-vektörünü tablo çizgisinden ayırmak kırılgan. Reddedildi.
- Alternatif "tüm sayfayı raster + overlay": vektör kalitesi kaybolur, dosya şişer. Reddedildi.

## Gözlem: zemin her zaman düz renk

Femo rapor_1'deki çevrilecek (changed, passthrough olmayan) **tüm** segmentlerin baskın zemin rengi
ya `(255,255,255)` beyaz ya `(240,240,240)` açık gridir. **Grafik/çok-renkli zemin üzerine binen
çevrilebilir etiket yoktur.** Dolayısıyla "düz olmayan zemin" durumu femo'da hiç oluşmaz; yine de
gelecekteki diğer kitler için güvenli fallback tasarıma dahildir (aşağıda).

## Mimari

Değişiklik tek dosyada: `report_translator/engine.py`. Yeni bir saf yardımcı fonksiyon + mevcut
`_render_page_items` akışının güncellenmesi.

### Yeni fonksiyon: `_sample_bg(pixmap, rect, scale, tol=12, min_frac=0.7)`

Segment dikdörtgeninin **kenar marjından** (harflerin dışındaki dolgu halkası) zemin rengini örnekler.

- **Girdi:** `pixmap` (orijinal sayfanın fitz.Pixmap'i), `rect` (PDF-koordinat fitz.Rect),
  `scale` (pixmap dpi / 72), `tol` (renk eşitlik toleransı), `min_frac` (düzlük eşiği).
- **Algoritma:**
  1. `rect`'i pixmap piksel koordinatlarına çevir (`scale` ile).
  2. Dikdörtgenin **çevresindeki ince halkadan** pikselleri topla: üst kenarın 1-2 px üstü,
     alt kenarın 1-2 px altı, sol/sağ kenarın 1-2 px dışı (bunlar harf değil, zemindir).
     Pixmap sınırları dışına taşan noktalar atlanır.
  3. Toplanan piksellerin baskın (mode) rengini bul. `tol` toleransıyla bu renge eşit piksel
     oranı `min_frac`'tan büyükse → o rengi `(r,g,b)` float (0-1) olarak döndür.
  4. Aksi halde (halka çok-renkli, ör. grafik üzeri) → `None`.
- **Çıktı:** `(r, g, b)` 0-1 float tuple veya `None`.
- **Saf fonksiyon:** dosya/IO yok; sadece pixmap okur. Birim-test edilebilir.

### Güncellenen: `_render_page_items(page, items, font_cache)`

Mevcut akış: tüm `items` rect'lerini `fill=None` ile redakte et → apply_redactions → Türkçe yaz.

Yeni akış:
1. `items` boşsa erken dön (mevcut davranış).
2. **Sayfayı bir kez pixmap'e render et** (redaksiyon öncesi, örnekleme için):
   `pm = page.get_pixmap(dpi=150)`. `scale = 150/72`.
3. Her segment / her rect için:
   - `bg = _sample_bg(pm, fitz.Rect(r), scale)`
   - `bg` `None` değilse: `fill = bg`, ve rect'i ~1px **genişleterek** redaksiyon ekle
     (vektör outline kenarları metin bbox'undan biraz taşabilir):
     `page.add_redact_annot(fitz.Rect(r) + (-1, -1, 1, 1), fill=bg)`
   - `bg` `None` ise (güvenli fallback): `page.add_redact_annot(fitz.Rect(r), fill=None)`
     → İngilizce vektör kalır, yama yok. (Femo'da tetiklenmez.)
4. `page.apply_redactions(images=NONE, graphics=LINE_ART_NONE, text=REMOVE)` (mevcut parametreler).
5. Türkçe metni eskisi gibi yaz (mevcut `insert_text` / `insert_textbox` kodu **değişmez**).

`graphics=PDF_REDACT_LINE_ART_NONE` korunur: tablo çizgileri, kutu kenarları, grafik barları
silinmez; sadece redaksiyon dolgusu üstlerine boyanır (yalnız metin bbox'u kadar dar alanda).

### Kapsam

Bu davranış render yolunda **evrensel** uygulanır (kit ayrımı yok). Normal metin-katmanlı raporlarda
zemin = beyaz örneklenir → beyaz dolgu = görsel olarak aynı sonuç (mevcut çıktı bozulmaz).

## Veri akışı

```
translate_document_bytes / render_page_png
  └─ render(doc, annotated)
       └─ _render_page_items(page, changed_items, font_cache)
            ├─ pm = page.get_pixmap(dpi=150)          # YENİ: zemin örneklemesi
            ├─ her rect: bg = _sample_bg(pm, rect, scale)   # YENİ
            ├─ add_redact_annot(rect, fill=bg veya None)    # DEĞİŞTİ: fill
            ├─ apply_redactions(...)                  # aynı
            └─ insert_text / insert_textbox(...)      # aynı
```

## Hata durumları

- **Pixmap render başarısız** (beklenmez): yakalanırsa `fill=None`'a düş (eski davranış), render devam eder.
- **Halka pixmap dışına taşar** (segment sayfa kenarında): sınır-dışı noktalar atlanır; kalan
  noktalarla örnekleme yapılır, hiç nokta yoksa `None`.
- **Çok-renkli zemin:** `_sample_bg` `None` → `fill=None` → İngilizce kalır (güvenli).

## Test stratejisi

Tümü `report_translator/tests/` altında, mevcut pytest yapısına uygun.

1. **`_sample_bg` birim testleri** (sentetik `fitz.Pixmap`):
   - Tamamen beyaz bölge → `(1,1,1)` (tolerans içinde).
   - Açık gri bölge → `(240/255, ...)`.
   - Yarı beyaz/yarı renkli halka (çok-renkli) → `None`.
   - Sayfa-kenarı rect (halka kısmen dışarıda) → kalan noktalardan renk veya `None`, çökmeden.

2. **Render birim testi** (sentetik PDF):
   - Bir sayfaya **vektör-outline** olarak "ENGLISH" çiz (`page.draw_*` / text-as-curves benzeri
     dolu dikdörtgenle taklit) + aynı yere bir **metin katmanı** koy.
   - `_render_page_items` ile çevir; çıktı pixmap'inde o bölgenin zemin-rengi olduğunu
     (vektörün örtüldüğünü) doğrula.

3. **Entegrasyon (gerçek lab örneği varsa, gitignore'da):**
   - `rapor_1.pdf` render edilir; gövdedeki bilinen eski-İngilizce noktalarda pixmap zemin-rengi
     (koyu harf yok) olduğu örneklenerek doğrulanır.
   - *Not:* `new_samples/` gerçek lab verisidir, git'e girmez; bu test örnek dosya varsa çalışır,
     yoksa `skip`.

4. **Gerileme:** mevcut **78 test** geçmeye devam etmeli (normal raporlar bozulmamalı).

5. **Görsel doğrulama:** rapor_1–4 elle gözden geçirilir (çakışma yok, yama yok).

## Performans

Sayfa başına +1 pixmap render (~150 dpi). PNG önizleme yolu zaten pixmap üretir; PDF çıktı yoluna
sayfa başına bir render eklenir. Tipik rapor 1–2 sayfa → ihmal edilebilir.

## Kapsam dışı (YAGNI)

- Çok-renkli zemin üzerine yazma (gradient eşleme) — femo'da yok; gerekirse sonra.
- Vektör-outline'ı gerçekten silme/parse etme — gerek yok, örtme yeterli.
- Diğer kitlere özel ayar — mekanizma evrensel; kit-özel davranış eklenmez.
