@echo off
setlocal
cd /d "%~dp0"

rem --- pakai Python di .venv proyek (sudah berisi Playwright) ---
set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] %PY% tidak ditemukan.
    echo         Buat dulu di folder proyek: python -m venv .venv
    echo         lalu: .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)

"%PY%" -c "import playwright" >nul 2>nul
if errorlevel 1 (
    echo [setup] Playwright belum terpasang, menginstall...
    "%PY%" -m pip install playwright
    if errorlevel 1 (
        echo [ERROR] Gagal install Playwright.
        pause
        exit /b 1
    )
)

echo [run] Menjalankan sniff_jubel_v2.py ...
echo [run] Setelah aksi selesai, kembali ke jendela ini dan tekan ENTER (jangan Ctrl+C).
"%PY%" sniff_jubel_v2.py %*

echo.
echo [selesai] Program berhenti.
pause
endlocal
