#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
if [ ! -f "web/index.html" ]; then
  echo "Frontend derlenmemiş. 'cd frontend && npm install && npm run build' çalıştırın."
fi
PORT=8731
./.venv/bin/python -m uvicorn app:app --port $PORT --host 127.0.0.1 &
SRV=$!
sleep 2
open "http://127.0.0.1:$PORT"
echo "Genomer Rapor Çevirici çalışıyor. Kapatmak için bu pencereyi kapatın."
wait $SRV
