@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 goto nopython

if not exist ".venv\Scripts\python.exe" goto setup
goto run

:setup
echo Ilk kurulum yapiliyor, lutfen bekleyin. Internet gerekir...
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip -q
.venv\Scripts\python -m pip install -q -r requirements.txt
if errorlevel 1 goto installfail
goto run

:run
if not exist "web\index.html" echo UYARI: web klasoru eksik - klasoru eksiksiz kopyalayin.
start "" http://127.0.0.1:8731
echo.
echo Genomer Rapor Cevirici calisiyor.
echo Tarayicida acilmazsa: http://127.0.0.1:8731
echo Durdurmak icin bu pencereyi kapatin.
echo.
.venv\Scripts\python -m uvicorn app:app --port 8731 --host 127.0.0.1
pause
exit /b 0

:nopython
echo.
echo HATA: Python bulunamadi.
echo python.org adresinden Python 3.13 kurun ve kurulumda
echo "Add Python to PATH" kutusunu isaretleyin, sonra tekrar calistirin.
echo.
pause
exit /b 1

:installfail
echo.
echo HATA: Bagimliliklar kurulamadi. Internet baglantisini kontrol edip tekrar deneyin.
echo.
pause
exit /b 1
