# Native paketleme (PyInstaller)

```bash
cd report_translator
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --onefile --name "GenomerRaporCevirici" \
  --add-data "web:web" --add-data "fonts:fonts" --add-data "dictionary.json:." \
  --collect-all fastapi --collect-all uvicorn --collect-all pymupdf \
  launcher.py
```

`launcher.py` (uvicorn'u programatik başlatır + tarayıcı açar):
```python
import uvicorn, webbrowser, threading, app
def open_browser(): webbrowser.open("http://127.0.0.1:8731")
threading.Timer(1.5, open_browser).start()
uvicorn.run(app.app, host="127.0.0.1", port=8731)
```

Çıktı `dist/GenomerRaporCevirici` tek dosyadır; Python gerektirmez. macOS imzalama/notarizasyon
ve Windows kod imzalama dağıtım için ayrıca yapılmalı.
