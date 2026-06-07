# Native paketleme

## 1. Frontend'i derle
```bash
cd report_translator/frontend
npm install
npm run build      # -> ../web (statik, çevrimdışı)
```

## 2. PyInstaller ile tek dosya
```bash
cd report_translator
.venv/bin/pip install -r requirements.txt pyinstaller
.venv/bin/pyinstaller --onefile --windowed --name "GenomerRaporCevirici" \
  --add-data "web:web" --add-data "fonts:fonts" --add-data "dictionary.json:." \
  --collect-all fastapi --collect-all uvicorn --collect-all pymupdf --collect-all webview \
  launcher.py
```
- macOS: `--icon genomer.icns`; Windows: `--icon genomer.ico` (ayrı hazırlanır). Windows'ta `--add-data` ayıracı `;` kullanın (`"web;web"`).
- Çıktı `dist/GenomerRaporCevirici` tek dosyadır; Python gerektirmez, çevrimdışı çalışır.
- macOS imzalama/notarizasyon ve Windows kod imzalama dağıtım için ayrıca yapılır.
