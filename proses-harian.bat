@echo off
setlocal
cd /d "%~dp0"

rem Sesi folder label dihitung SEKALI di sini (bertahan selama proses-harian.bat ini berjalan).
rem Ditutup lalu dijalankan ulang -> sesi baru (angka lanjut dari yang terbesar hari ini).
for /f "delims=" %%i in ('".venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'src'); from main import sesi_label_baru; print(sesi_label_baru())"') do set "LABEL_SESI_DIR=%%i"
echo Sesi label: %LABEL_SESI_DIR%

:menu
cls
echo ==================================================================
echo   PROSES PESANAN OTOMATIS
echo ==================================================================
echo   1. SESI PAGI
echo   2. JAM 13.00
echo   3. SESI SORE
echo   0. Keluar
echo ==================================================================
set "pilih="
set /p "pilih=Pilih menu: "
if "%pilih%"=="1" goto sesi_pagi
if "%pilih%"=="2" goto jam_1300
if "%pilih%"=="3" goto sesi_sore
if "%pilih%"=="0" goto :eof
goto menu

rem ============================================================
rem SESI PAGI: J&T dan SPX digabung (seperti semula, dipakai jam
rem 07.00-11.xx & 18.00-23.00 - lihat JADWAL-PROSES.md)
rem ============================================================
:sesi_pagi
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio.
set "yakin="
set /p "yakin=Lanjutkan SESI PAGI? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
echo === 1/5 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
echo.
echo === 2/5 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
echo.
echo === 3/5 SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler --jalankan
echo.
echo === 4/5 SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --jalankan
echo.
echo === 5/5 SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --jalankan
echo.
echo SESI PAGI selesai.
pause
goto menu

rem ============================================================
rem JAM 13.00: SPX Resi Pagi (resi Shopee <= 12.00) + J&T dan SPX
rem DIPISAH saat pembuatan picklist (lihat JADWAL-PROSES.md)
rem ============================================================
:jam_1300
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio. SPX RESI PAGI cuma 1x sehari.
set "yakin="
set /p "yakin=Lanjutkan JAM 13.00? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
echo === 1/9 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
echo.
echo === 2/9 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
echo.
echo === 3/9 SPX PAGI (RESI SHOPEE ^<= 12.00) ===
".venv\Scripts\python.exe" src\main.py --shopee-pagi --jalankan
echo.
echo === 4/9 J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler --jalankan
echo.
echo === 5/9 J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt --jalankan
echo.
echo === 6/9 J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt --jalankan
echo.
echo === 7/9 SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler --jalankan
echo.
echo === 8/9 SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx --jalankan
echo.
echo === 9/9 SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx --jalankan
echo.
echo JAM 13.00 selesai.
pause
goto menu

rem ============================================================
rem SESI SORE: sama seperti JAM 13.00 tapi TANPA SPX Resi Pagi
rem (sudah dijalankan jam 13.00, cukup 1x sehari)
rem ============================================================
:sesi_sore
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio.
set "yakin="
set /p "yakin=Lanjutkan SESI SORE? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
echo === 1/8 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
echo.
echo === 2/8 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
echo.
echo === 3/8 J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler --jalankan
echo.
echo === 4/8 J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt --jalankan
echo.
echo === 5/8 J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt --jalankan
echo.
echo === 6/8 SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler --jalankan
echo.
echo === 7/8 SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx --jalankan
echo.
echo === 8/8 SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx --jalankan
echo.
echo SESI SORE selesai.
pause
goto menu
