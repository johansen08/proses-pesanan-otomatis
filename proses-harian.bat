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
echo   4. JAM 15.00
echo   0. Keluar
echo ==================================================================
set "pilih="
set /p "pilih=Pilih menu: "
if "%pilih%"=="1" goto sesi_pagi
if "%pilih%"=="2" goto jam_1300
if "%pilih%"=="3" goto sesi_sore
if "%pilih%"=="4" goto jam_1500
if "%pilih%"=="0" goto :eof
goto menu

rem ============================================================
rem SESI PAGI: J&T dan SPX digabung (seperti semula, dipakai jam
rem 07.00-11.xx, DAN lagi setelah JAM 15.00 selesai (kapan pun
rem itu, bukan jam pas - lihat JADWAL-PROSES.md) sampai jam 17.xx)
rem ============================================================
:sesi_pagi
call :cek_jam 1 "SESI PAGI (07.00-13.00 / 15.00-17.59, setelah JAM 15.00 selesai)"
if errorlevel 1 goto menu
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
call :cek_jam 2 "JAM 13.00 (13.01-14.00)"
if errorlevel 1 goto menu
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
rem (sudah dijalankan jam 13.00, cukup 1x sehari). Dipakai SETELAH
rem JAM 13.00 selesai (kapan pun itu) DAN SEBELUM JAM 15.00 mulai,
rem juga dipakai lagi untuk jadwal malam 18.00-23.00.
rem ============================================================
:sesi_sore
call :cek_jam 3 "SESI SORE (13.01-14.59, setelah JAM 13.00 selesai / 18.00-23.00)"
if errorlevel 1 goto menu
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

rem ============================================================
rem JAM 15.00: J&T Resi Siang (wajib keluar TikTok Shop <= 15.00,
rem cukup 1x sehari), lalu J&T dan SPX DIGABUNG lagi seperti SESI
rem PAGI (bukan dipisah lagi - lihat JADWAL-PROSES.md)
rem ============================================================
:jam_1500
call :cek_jam 4 "JAM 15.00 (15.00-15.59)"
if errorlevel 1 goto menu
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio. J^&T RESI SIANG cuma 1x sehari.
set "yakin="
set /p "yakin=Lanjutkan JAM 15.00? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
echo === 1/6 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
echo.
echo === 2/6 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
echo.
echo === 3/6 J^&T RESI SIANG (WAJIB KELUAR TIKTOK ^<= 15.00) ===
".venv\Scripts\python.exe" src\main.py --jnt-siang --jalankan
echo.
echo === 4/6 SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler --jalankan
echo.
echo === 5/6 SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --jalankan
echo.
echo === 6/6 SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --jalankan
echo.
echo JAM 15.00 selesai.
pause
goto menu

rem ============================================================
rem Cek jam sekarang vs jendela jam menu yang dipilih (lihat
rem dalam_jam_menu() di src\main.py & docs\jadwal-proses.md).
rem %1 = kode menu ("1"/"2"/"3"/"4"), %2 = label jendela untuk pesan.
rem errorlevel 1 -> user pilih batal (kembali ke menu).
rem ============================================================
:cek_jam
set "JAM_OK="
for /f "delims=" %%i in ('".venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'src'); from main import dalam_jam_menu; print(1 if dalam_jam_menu('%~1') else 0)"') do set "JAM_OK=%%i"
if "%JAM_OK%"=="1" exit /b 0
echo.
echo PERINGATAN: sekarang di luar jam %~2.
set "lanjut_jam="
set /p "lanjut_jam=Apakah anda tidak salah memilih menu? (Y/N): "
if /i "%lanjut_jam%"=="Y" exit /b 0
exit /b 1
