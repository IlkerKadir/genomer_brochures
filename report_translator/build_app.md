# Native paketleme (.exe / .app)

> Not: Çoğu dağıtım için `KURULUM.md`'deki **`baslat.bat` (Python'lu)** yolu daha basittir.
> Bu doküman, Python gerektirmeyen tek dosyalık paket içindir.

Yazılabilir veri (config.json, ai_cache.json, glossary_state.json ve kullanıcı tarafından
düzenlenen dictionary.json / glossary.tsv / postedit.tsv) `paths.py` sayesinde paketli modda
**%APPDATA%\Genomer** (Windows) altına yazılır; salt-okunur varlıklar (fonts, web ve taban
dictionary.json/glossary.tsv/postedit.tsv) bundle'dan gelir ve ilk açılışta %APPDATA%'ya
kopyalanır (seed). Böylece tek dosyalık `.exe`'de bile DeepL anahtarı ve sözlük düzenlemeleri
kalıcı olur.

## 1. Frontend'i derle (zaten derlenmişse atla — `web/index.html` var)
```bash
cd report_translator/frontend
npm install
npm run build      # -> ../web (statik, çevrimdışı)
```

## 2. PyInstaller ile tek dosya

**Windows** (PowerShell/CMD — `--add-data` ayıracı `;`):
```bat
cd report_translator
python -m venv .venv
.venv\Scripts\pip install -r requirements-desktop.txt pyinstaller
.venv\Scripts\pyinstaller --onefile --windowed --name "GenomerRaporCevirici" ^
  --add-data "web;web" --add-data "fonts;fonts" ^
  --add-data "dictionary.json;." --add-data "glossary.tsv;." --add-data "postedit.tsv;." ^
  --collect-all fastapi --collect-all uvicorn --collect-all pymupdf --collect-all webview ^
  launcher.py
```

**macOS/Linux** (ayıraç `:`):
```bash
cd report_translator
.venv/bin/pip install -r requirements-desktop.txt pyinstaller
.venv/bin/pyinstaller --onefile --windowed --name "GenomerRaporCevirici" \
  --add-data "web:web" --add-data "fonts:fonts" \
  --add-data "dictionary.json:." --add-data "glossary.tsv:." --add-data "postedit.tsv:." \
  --collect-all fastapi --collect-all uvicorn --collect-all pymupdf --collect-all webview \
  launcher.py
```

- İkon: macOS `--icon genomer.icns`, Windows `--icon genomer.ico` (ayrı hazırlanır).
- Çıktı `dist/GenomerRaporCevirici(.exe)` tek dosyadır; Python gerektirmez, çevrimdışı çalışır
  (DeepL özet çevirisi hariç — o internet ister).
- İlk açılışta taban sözlük/glossary/postedit `%APPDATA%\Genomer`'a kopyalanır; sonraki
  güncellemede yeni taban terimleri istemciye gitmesi için o dosyaları elle yenileyin
  (veya silin → `.exe` yeniden seed eder; kullanıcı eklemeleri kaybolur).
- macOS imzalama/notarizasyon ve Windows kod imzalama dağıtım için ayrıca yapılır.
