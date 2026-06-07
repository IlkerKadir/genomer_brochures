@echo off
cd /d "%~dp0"
if not exist ".venv" (
  python -m venv .venv
  .venv\Scripts\pip install -q -r requirements.txt
)
if not exist "web\index.html" echo Frontend derlenmemis. frontend klasorunde 'npm install && npm run build' calistirin.
start "" http://127.0.0.1:8731
.venv\Scripts\python -m uvicorn app:app --port 8731 --host 127.0.0.1
