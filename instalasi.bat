@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==================================================================
echo   SETUP PROSES PESANAN OTOMATIS
echo ==================================================================
echo.

rem --- 1. Cek Python sudah terinstall & ada di PATH ---
where python >nul 2>nul
if errorlevel 1 (
    echo [GAGAL] Python tidak ditemukan di PATH.
    echo.
    echo Install dulu Python 3.11+ dari https://www.python.org/downloads/windows/
    echo Saat instalasi, WAJIB centang "Add python.exe to PATH".
    echo Setelah install, tutup lalu buka ulang terminal ini, lalu jalankan instalasi.bat lagi.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo [OK] Ditemukan: %PYVER%
echo.

rem --- 2. Buat virtual environment kalau belum ada ---
if exist ".venv\Scripts\python.exe" (
    echo [OK] Virtual environment ".venv" sudah ada, lewati pembuatan.
) else (
    echo Membuat virtual environment ".venv"...
    python -m venv .venv
    if errorlevel 1 (
        echo [GAGAL] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment dibuat.
)
echo.

rem --- 3. Upgrade pip & install requirements ---
echo Upgrade pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [GAGAL] Gagal upgrade pip.
    pause
    exit /b 1
)
echo.

echo Install library dari requirements.txt (pandas, openpyxl, reportlab, requests, tzdata, playwright)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [GAGAL] Gagal install library dari requirements.txt.
    pause
    exit /b 1
)
echo [OK] Semua library terinstall.
echo.

rem --- 4. Verifikasi import library utama ---
echo Verifikasi library utama...
".venv\Scripts\python.exe" -c "import pandas, openpyxl, reportlab, requests, tzdata; print('[OK] semua library utama terbaca')"
if errorlevel 1 (
    echo [GAGAL] Ada library yang gagal diimport. Cek pesan error di atas.
    pause
    exit /b 1
)
echo.

rem --- 5. Cek file .env ---
if exist ".env" (
    echo [OK] File .env sudah ada.
) else (
    echo [PERHATIAN] File .env belum ada. Membuat template .env kosong...
    (
        echo JUBELIO_EMAIL=
        echo JUBELIO_PASSWORD=
    ) > ".env"
    echo [PERHATIAN] Isi dulu JUBELIO_EMAIL dan JUBELIO_PASSWORD di file .env sebelum menjalankan proses-harian.bat.
)
echo.

echo ==================================================================
echo   SETUP SELESAI
echo ==================================================================
echo Langkah selanjutnya:
echo   1. Pastikan file .env sudah berisi JUBELIO_EMAIL dan JUBELIO_PASSWORD yang benar.
echo   2. Jalankan bat\proses-harian-uji.bat dulu untuk tes login/koneksi (tidak mengubah apa pun di Jubelio).
echo   3. Kalau bat\proses-harian-uji.bat berhasil, jalankan proses-harian.bat untuk proses sungguhan.
echo.
pause
