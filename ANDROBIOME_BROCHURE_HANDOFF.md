# Androbiome Broşür — Rapor Mockup Yenileme Handoff

## Proje Konumu
- **Çalışma dosyası:** `/Users/ilkerkadirozturk/Documents/genomer_brochures/androbiome-brochure-TR-new.html`
- **Görsel referans (Genomer'in kendi rapor PDF'i):** `reportsamples/tr/Androbiome_rapor.pdf`
- **İçerik denetimi referansı (sonraki faz):** `androflor.pdf`
- **Logo:** `genomerlogo.png`

## Ana Hedef
Broşür içindeki 20 adet "Örnek N. Androbiome testi" rapor mockup'ını, Genomer'in kendi rapor PDF'inin görsel diliyle eşleşecek şekilde yeniden çerçevelemek:
- Üstte koyu mavi başlık çubuğu ("Ürogenital Mikrobiyom Kompozisyon Testi" + "Androbiome")
- Tablo zaten mevcut — çerçeveye sarılacak
- Altta renk kodlu sonuç çubuğu (yeşil/sarı/kırmızı)

## TAMAMLANAN İŞLER

### 1. CSS Framework eklendi
`<style>` etiketinin sonuna (yaklaşık satır 387'den önce, `.conclusion-title` kuralından sonra) aşağıdaki sınıflar eklendi:

```css
.report-card { border: 1px solid var(--border-medium); border-radius: 4px; background: #fff; overflow: hidden; margin-bottom: 8px; }
.report-title-bar { background: var(--primary-dark); color: #fff; padding: 6px 12px; text-align: center; }
.report-title-bar .report-title { font-size: 0.92em; font-weight: 700; letter-spacing: 0.4px; }
.report-title-bar .report-subtitle { font-size: 0.78em; opacity: 0.9; font-style: italic; margin-top: 2px; }
.report-meta { display: flex; justify-content: space-between; padding: 4px 12px; background: var(--bg-light); border-bottom: 1px solid var(--border-light); font-size: 0.7em; color: var(--text-secondary); }
.report-meta .meta-label { font-weight: 600; color: var(--text-primary); margin-right: 4px; }

.report-card .result-table { margin: 0; border-radius: 0; }
.report-card .result-table th { background: var(--bg-muted); color: var(--text-primary); font-size: 0.72em; padding: 4px 6px; border-bottom: 1px solid var(--border-medium); font-weight: 600; }
.report-card .result-table .group-header td { background: #eef2f6; font-weight: 600; color: var(--primary-dark); font-style: italic; font-size: 0.85em; padding: 3px 6px; border-top: 1px solid var(--border-light); border-bottom: 1px solid var(--border-light); }
.report-card .result-table .sum-row td { background: rgba(10,90,138,0.05); font-weight: 600; font-style: italic; border-top: 1px dashed var(--border-medium); }
.report-card .result-table td { font-size: 0.92em; }
.report-card .result-table .not-detected { color: #888; font-style: italic; }
.report-card .result-table .detected-pathogen { color: var(--result-abnormal); font-weight: 700; text-transform: uppercase; }

.report-footnotes { padding: 4px 12px 6px; font-size: 0.68em; color: var(--text-muted); background: #fff; }
.report-conclusion-bar { background: var(--bg-primary-subtle); border-top: 2px solid var(--primary); padding: 8px 12px; font-size: 0.78em; line-height: 1.45; }
.report-conclusion-bar strong { color: var(--primary-dark); display: block; margin-bottom: 3px; font-size: 1.05em; }
.report-conclusion-bar.conclusion-normal { background: var(--result-normal-bg); border-top-color: var(--accent-green); }
.report-conclusion-bar.conclusion-moderate { background: var(--result-moderate-bg); border-top-color: var(--accent-yellow); }
.report-conclusion-bar.conclusion-abnormal { background: var(--result-abnormal-bg); border-top-color: var(--result-abnormal); }
.report-sig-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; padding: 6px 12px 8px; background: #fff; font-size: 0.62em; color: var(--text-muted); border-top: 1px solid var(--border-light); }
.report-sig-row .sig-cell { border-top: 1px dotted var(--border-medium); padding-top: 3px; text-align: center; }
```

### 2. Örnek 1 pilot olarak güncellendi (satır ~1862-1955)
Yeni yapıyla sarıldı:
- `<div class="report-card">` açıldı
- `<div class="report-title-bar">` eklendi: "Ürogenital Mikrobiyom Kompozisyon Testi" + "Androbiome • Sample ID: Örnek_1"
- Tablo değişmeden korundu
- `<p class="tiny-text">` → `<p class="report-footnotes">`
- `<div class="conclusion-box" style="background: var(--result-normal-bg); border-color: var(--accent-green);">` → `<div class="report-conclusion-bar conclusion-normal">` (içeriği tek paragrafa konsolide edildi)
- `<div class="report-sig-row">` eklendi (Çalışmayı yapan / Tarih / İmza)
- `</div><!-- /report-card -->` ile kapatıldı

### Test render bulgusu
Pilot render edildiğinde sayfa çok hafifçe taşıyor — sig row bazı mockup'larda alta sığmayabilir. İki seçenek:
- **A.** Sig row'u tamamen kaldır (mockup'lar broşürde, gerçek rapor değil)
- **B.** Sig row'u koru ama padding 6px → 3px, font 0.62em → 0.55em yap

Pilot şu an sig row dahil. Karar verince globalde uygulanmalı.

## KALAN İŞLER

### Faz 1: 19 mockup'a aynı patternin uygulanması
Mockup başlıkları ve dosyada bulundukları satırlar:

| Örnek No | Satır | Test Tipi |
|----------|-------|-----------|
| 2 | 1965 | Androbiome Screen |
| 3 | 2042 | Androbiome |
| 4 | 2124 | Androbiome |
| 5 | 2180 | Androbiome |
| 6 | 2244 | Androbiome Screen |
| 7 | 2315 | Androbiome Screen |
| 8 | 2388 | Androbiome |
| 9 | 2443 | Androbiome |
| 10 | 2499 | Androbiome |
| 11 | 2562 | Androbiome Screen |
| 12 | 2611 | Androbiome |
| 13 | 2669 | Androbiome |
| 14 | 2726 | Androbiome Screen |
| 15 | 2777 | Androbiome |
| 16 | 2831 | Androbiome |
| 17 | 2889 | Androbiome |
| 18 | 2942 | Androbiome Screen |
| 19 | 2993 | Androbiome |
| 20 | 3053 | Androbiome |

### Her mockup için uygulanacak değişim patterni

**Adım A — Tablonun ÖNÜNE wrapper aç:**
Her mockup'ta `<div class="example-header" ...><h3>Örnek N. Androbiome...</h3></div>` bloğundan SONRA, `<table class="result-table ...">` etiketinden ÖNCE ekle:

```html
<div class="report-card">
<div class="report-title-bar">
    <div class="report-title">Ürogenital Mikrobiyom Kompozisyon Testi</div>
    <div class="report-subtitle">Androbiome &nbsp;•&nbsp; Sample ID: Örnek_N</div>
</div>
```

(N yerine ilgili örnek numarası)

**Adım B — Footnotes class'ı:**
Tablodan sonraki `<p class="tiny-text">* Kantitatif Analiz Lg(X) ...</p>` ifadelerini `<p class="report-footnotes">...` olarak değiştir.

**Adım C — Conclusion box'ı conclusion-bar'a çevir:**
Her mockup'ta `<div class="conclusion-box" style="...">` ile başlayan blok, aşağıdaki formata dönüştürülmeli:

```html
<div class="report-conclusion-bar conclusion-X">
    <strong>Sonuç:</strong>
    [orijinal conclusion içeriği, paragraflar tek satıra konsolide edilebilir]
</div>
```

`conclusion-X` sınıfı seçimi (mevcut conclusion-box style'a göre):

| Örnek | Mevcut Style | Yeni Sınıf |
|-------|-------------|-----------|
| 2-6 | `result-normal-bg` + `accent-green` | `conclusion-normal` |
| 7-16 | `result-abnormal-bg` + `accent-red` | `conclusion-abnormal` |
| 17 | `#FEE2E2` + `#EF4444` | `conclusion-abnormal` |
| 18 | `#FEF3C7` + `#F59E0B` | `conclusion-moderate` |
| 19 | `#FEF3C7` + `#F59E0B` | `conclusion-moderate` |
| 20 | `result-abnormal-bg` + `accent-red` | `conclusion-abnormal` |

(Örnek 1 zaten yapıldı: `conclusion-normal`)

**Adım D — Sig row (opsiyonel) ve wrapper kapanışı:**
Conclusion-bar'dan SONRA, `<div class="page-footer">` etiketinden ÖNCE ekle:

```html
<div class="report-sig-row">
    <div class="sig-cell">Çalışmayı yapan</div>
    <div class="sig-cell">Tarih</div>
    <div class="sig-cell">İmza</div>
</div>
</div><!-- /report-card -->
```

(Eğer sig row kaldırılırsa, sadece `</div><!-- /report-card -->` ekle.)

### Doğrulama
Render komutu:
```bash
cd /Users/ilkerkadirozturk/Documents/genomer_brochures
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-pdf-header-footer --force-device-scale-factor=2 --virtual-time-budget=10000 --run-all-compositor-stages-before-draw --print-to-pdf=androbiome-brochure-TR.pdf "file://$(pwd)/androbiome-brochure-TR-new.html"
```

Her mockup tek brochure sayfasında kalmalı (taşma yok). Pilot olarak Örnek 1 sayfasını (yaklaşık PDF sayfa 20) kontrol et.

## Faz 2: İçerik Denetimi (Androbiome ↔ Androflor karşılaştırması)

20 Androbiome mockup'ın her birinin **sonuç değerleri** (TBM, organizma seviyeleri, conclusion metni) Androflor PDF'indeki karşılık gelen örnek vakayla **tutarlı mı** kontrol edilecek.

**Önemli not — bu faz tam metin reproduction değil tutarsızlık listesi olmalı.** Örneğin:
- "Androflor Örnek 8'de Candida pozitif (`below TH`), Androbiome Örnek 8'de Candida `saptanmadı` — uyumsuz, düzeltilmesi gerekir"
- "Androflor Örnek 12'de TBM 10^4.7, Androbiome Örnek 12'de 10^4.7 — uyumlu"

Format: tablo şeklinde, mockup başına 1 satır, "uyumlu / uyumsuz + neden" notuyla.

**Androflor PDF örnek vakaları için sayfa eşleştirmesi (yaklaşık):**
- Sayfa 20-21: Örnek 1-2
- Sayfa 24-27: Örnek 3-6
- Sayfa 29-31: Örnek 7-9 (moderate disbiyoz)
- Sayfa 33-36: Örnek 10-13 (severe disbiyoz)
- Sayfa 37-39: Örnek 14-17 (STI / patojen)
- Sayfa 40+: Örnek 18-20 (edge case'ler)

## Açık Notlar (geçmiş oturum kararları)
- DNA-Tech adı broşürde geçmemeli (Genomer marka olarak konumlanıyor)
- "Androbiome" + "Androbiome Screen" iki varyant — mockup başlıklarında zaten doğru yazılıyor
- Tüm conclusion metinleri tek paragrafa konsolide edilebilir (Genomer rapor PDF'i de tek bloktur)

## Bu Handoff Sonrası Önerilen Adımlar
1. Codex faz 1'i tamamlasın (20 mockup wrap)
2. PDF render, taşma var mı kontrol
3. Taşma varsa sig row'u kaldırma kararı
4. Faz 2 içerik denetimi
5. Tutarsızlık varsa kullanıcıya rapor — düzeltme onayı kullanıcıdan beklenir
