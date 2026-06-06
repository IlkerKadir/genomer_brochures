# Rapor Çevirici (EN → TR)

DNA-Technology (Femoflor®/Androflor®) qPCR rapor PDF'lerini **düzeni birebir koruyarak**
İngilizceden Türkçeye çevirir. Grafikler, tablolar, renkli çubuklar, çizgiler ve görüntüler
hiç ellenmez; yalnızca metin baytları değiştirilir.

## Nasıl çalışır

1. Her metin bloğu mantıksal birime toplanır (tek-satır etiket veya çok-satır paragraf).
2. `dictionary.json` ile çevrilir (önce tam eşleşme, sonra longest-match; `passthrough`
   desenleri — sayılar, birimler, Latin tür adları — asla çevrilmez).
3. `apply_redactions(text=REMOVE, graphics=NONE, images=NONE)` ile **yalnızca metin** silinir
   → arkadaki renkli hücreler / grafik çubukları / çizgiler / görüntüler korunur.
4. Türkçe metin, raporun **kendi fontuyla** (Roboto / Arial / Carlito / Montserrat — tümü tam
   Türkçe glyph içerir) aynı konum ve renkte yeniden yazılır. Paragraflar aynı kutuya sarılır.

## Kullanım

```bash
# Tek dosya
python3 translate_report.py "girdi.pdf" -o "cikti_TR.pdf"

# Klasördeki tüm PDF'ler ( *_TR.pdf üretir )
python3 translate_report.py "../reportsamples/en"

# Kit tipini elle zorla (otomatik tespit yerine)
python3 translate_report.py "girdi.pdf" --kit androbiome
```

Her çıktının yanında bir `*_review.txt` üretilir: sözlükte olmayan / kısmen çevrilen
birimleri listeler. `[PARAGRAF — sözlüğe tam ekleyin]` satırları, `_paragraphs` bölümüne
aynen yapıştırıp Türkçesini yazabileceğiniz tam metni içerir.

## Arayüz (yerel uygulama)

`baslat.command` (mac) / `baslat.bat` (win) çift tıklayın. Tarayıcıda Türkçe arayüz açılır:
çoklu PDF sürükle → çevir → segment düzelt → kaydet. Çıktılar `~/Genomer Ceviriler/`
klasörüne `*_TR.pdf` olarak yazılır. Veriler makineden çıkmaz (sunucu yalnız 127.0.0.1).

Segment düzeltme: her metni satır içi düzeltin; "Sözlüğe ekle" kalıcı (tüm raporlara),
"Sadece bu rapor" geçici. Sözlük çakışmasında onay sorulur; `dictionary.json.bak` yedeği alınır.

## Sözlüğü düzenleme — `dictionary.json`

- `common` : tüm kitlerde ortak etiketler.
- `femobiome_ii` / `androbiome` / `enterobiome_kids` : kite özgü etiketler.
- `_paragraphs` : akıcı cümleler (sonuç, not, terminoloji). **Anahtar, rapordaki tam metnin
  aynısı olmalı** (boşluklar normalize edilir ama kelimeler birebir). Tam metni `*_review.txt`'ten
  alabilirsiniz.
- `passthrough_patterns` : çevrilmeyecek desenler (regex).

Anahtar = TAM İngilizce kaynak metni. Çeviri uzunsa etiket sağdaki boşluğa uzar; paragraf
sığmazsa font hafifçe küçülür.

## Bilinen sınırlar (sonraki iyileştirmeler)

- **Paragraf içi italik Latin tür adları** düz yazılır (orijinalde italik). Etiket/tablo
  hücrelerinde italik korunur; yalnızca reflow edilen paragraflarda kaybolur.
- **Hastaya özel serbest metin** (örn. Enterobiome açıklama paragrafı) yalnızca sözlükte
  karşılığı varsa çevrilir; yoksa İngilizce kalır ve review'a düşer.
- Otomatik kit tespiti dosya/başlık metnine bakar; şüpheli durumda `--kit` ile zorlayın.

## Fontlar — `fonts/`

| Kit | Fontlar | Kaynak |
|-----|---------|--------|
| Femobiome II | Roboto-Regular/Italic, Montserrat-Bold | Google Fonts (variable→statik instance) |
| Androbiome | Arial-Regular/Bold | macOS sistem Arial (gerçek Arial) |
| Enterobiome Kids | Carlito (4 stil) | Calibri metrik-uyumlu açık muadili |

Hepsi tam Türkçe glyph kapsamına sahiptir (ş ğ ı İ ö ç ü).
