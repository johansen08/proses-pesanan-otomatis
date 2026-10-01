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
echo   PROSES PESANAN OTOMATIS (NON EVENT)
echo ==================================================================
echo   1. GABUNG JNT+SPX                           (07.00-12.00 / 16.00-07.00)
echo   2. DIPISAH + SPX RESI ^<= 12.00              (TEPAT JAM 13.00)
echo   3. DIPISAH, TANPA SPX RESI PAGI             (13.00-15.00)
echo   4. GABUNG JNT+SPX LAGI + JNT RESI ^<= 15.00  (TEPAT JAM 15.00)
echo   0. Keluar
echo ==================================================================
set "pilih="
set /p "pilih=Pilih menu (0-4): "
if "%pilih%"=="1" goto tipe1
if "%pilih%"=="2" goto tipe2
if "%pilih%"=="3" goto tipe3
if "%pilih%"=="4" goto tipe4
if "%pilih%"=="0" goto :eof
echo.
echo Pilihan "%pilih%" tidak dikenali, coba lagi.
pause
goto menu

rem ============================================================
rem TIPE 1: J&T dan SPX DIGABUNG (seperti semula). Dipakai siklus
rem pagi 07.00-11.xx DAN siklus sore/malam/dini hari 16.00-07.00
rem keesokan harinya (setelah TIPE 4 selesai sampai TIPE 1 besok
rem pagi) - lihat docs/jadwal-proses.md
rem ============================================================
:tipe1
call :cek_jam 1 "TIPE 1 (07.00-12.00 / 16.00-07.00)"
if errorlevel 1 goto menu
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio.
set "yakin="
set /p "yakin=Lanjutkan TIPE 1? (Y/N): "
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
echo TIPE 1 selesai.
pause
goto menu

rem ============================================================
rem TIPE 2: SPX Resi Pagi (resi Shopee <= 12.00, habiskan wajib
rem keluar Shopee) + J&T dan SPX DIPISAH saat pembuatan picklist.
rem Dipicu TEPAT jam 13.00 (lihat docs/jadwal-proses.md)
rem ============================================================
:tipe2
call :cek_jam 2 "TIPE 2 (TEPAT JAM 13.00)"
if errorlevel 1 goto menu
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio. SPX RESI PAGI cuma 1x sehari.
set "yakin="
set /p "yakin=Lanjutkan TIPE 2? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
echo === 1/9 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
echo.
echo === 2/9 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
echo.
echo === 3/9 SPX ^<= 12.00 (SPX RESI PAGI) ===
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
echo TIPE 2 selesai.
pause
goto menu

rem ============================================================
rem TIPE 3: sama seperti TIPE 2 tapi TANPA SPX Resi Pagi (sudah
rem dijalankan di TIPE 2, cukup 1x sehari). Dipakai SETELAH TIPE 2
rem selesai DAN SEBELUM TIPE 4 dimulai (13.00-15.00)
rem ============================================================
:tipe3
call :cek_jam 3 "TIPE 3 (13.00-15.00)"
if errorlevel 1 goto menu
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio.
set "yakin="
set /p "yakin=Lanjutkan TIPE 3? (Y/N): "
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
echo TIPE 3 selesai.
pause
goto menu

rem ============================================================
rem TIPE 4: J&T Resi Siang (wajib keluar TikTok Shop <= 15.00,
rem habiskan wajib keluar TikTok, cukup 1x sehari), lalu J&T dan
rem SPX DIGABUNG lagi seperti TIPE 1 (bukan dipisah lagi). Dipicu
rem TEPAT jam 15.00 (lihat docs/jadwal-proses.md)
rem ============================================================
:tipe4
call :cek_jam 4 "TIPE 4 (TEPAT JAM 15.00)"
if errorlevel 1 goto menu
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio. J^&T RESI SIANG cuma 1x sehari.
set "yakin="
set /p "yakin=Lanjutkan TIPE 4? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
echo === 1/6 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
echo.
echo === 2/6 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
echo.
echo === 3/6 J^&T ^<= 15.00 (J^&T RESI SIANG) ===
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
echo TIPE 4 selesai.
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
