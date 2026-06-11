@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM --- Python kurulu mu? ---
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo HATA: Python bulunamadi.
  echo python.org/downloads adresinden Python 3.13 kurun ve kurulum sirasinda
  echo "Add Python to PATH" kutusunu mutlaka isaretleyin, sonra bu dosyayi tekrar calistirin.
  echo.
  pause
  exit /b 1
)

REM --- Ilk acilis: sanal ortam + bagimliliklar (internet gerekir) ---
if not exist ".venv\Scripts\python.exe" (
  echo Ilk kurulum yapiliyor, lutfen bekleyin (internet gerekir)...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip -q
  .venv\Scripts\pip install -q -r requirements.txt
  if errorlevel 1 (
    echo.
    echo HATA: Bagimliliklar kurulamadi. Internet baglantisini kontrol edip tekrar deneyin.
    echo.
    pause
    exit /b 1
  )
)

if not exist "web\index.html" echo UYARI: Arayuz dosyalari (web\) eksik - klasoru eksiksiz kopyaladiginizdan emin olun.

REM --- Sunucu hazir olunca tarayiciyi ac (ayri islem), sunucuyu bu pencerede calistir ---
start "" cmd /c "timeout /t 3 /nobreak >nul & start """" http://127.0.0.1:8731"
echo.
echo Genomer Rapor Cevirici baslatiliyor... Tarayicida birazdan acilacak.
echo (Bu pencereyi kapatirsaniz uygulama durur.)
echo.
.venv\Scripts\python -m uvicorn app:app --port 8731 --host 127.0.0.1
