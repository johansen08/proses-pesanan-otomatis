@echo off
setlocal
cd /d "%~dp0.."

rem Sesi folder label dihitung SEKALI di sini (bertahan selama proses-event.bat ini berjalan).
rem Ditutup lalu dijalankan ulang -> sesi baru (angka lanjut dari yang terbesar hari ini).
for /f "delims=" %%i in ('.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from main import sesi_label_baru; print(sesi_label_baru())"') do set "LABEL_SESI_DIR=%%i"
echo Sesi label: %LABEL_SESI_DIR%

:menu
cls
echo ==================================================================
echo   PROSES PESANAN OTOMATIS (EVENT: 10.10 / 11.11 / 12.12 DST)
echo ==================================================================
echo   1. EVENT - SESI BIASA          (J^&T / SPX HEMAT / SPX STANDARD dipisah)
echo   2. EVENT - TEPAT JAM 13.00     (SHOPEE PAGI ^<= 12.00, lalu sesi biasa)
echo   0. Keluar
echo ==================================================================
set "pilih="
set /p "pilih=Pilih menu (0-2): "
if "%pilih%"=="1" goto event1
if "%pilih%"=="2" goto event2
rem Keluar pakai "exit" (bukan "goto :eof"/"exit /b"): kalau ada call :label yang belum
rem kembali, "goto :eof" cuma kembali ke baris setelah call itu dan proses LANJUT jalan.
if "%pilih%"=="0" exit
echo.
echo Pilihan "%pilih%" tidak dikenali, coba lagi.
pause
goto menu

rem ============================================================
rem EVENT - SESI BIASA: J&T, SPX Hemat, dan SPX Standard DIPISAH
rem sepanjang hari. SPX Standard hanya per lantai; SPX Hemat dan J&T
rem spesial, 1 qty, kombinasi. J&T Resi Siang (s.d. 15.00) OPSIONAL,
rem ditanya di awal (bawaan tidak). Lihat docs/jadwal-proses.md
rem ============================================================
:event1
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio.
set "yakin="
set /p "yakin=Lanjutkan EVENT - SESI BIASA? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
set "JNT_SIANG="
set /p "JNT_SIANG=Jalankan J&T RESI SIANG (<= 15.00, cukup 1x sehari)? (Y/N, bawaan N): "
echo.
call :catat_waktu TR_AWAL
echo === 1/13 RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok --jalankan
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/13 SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel --jalankan
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/13 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --lewati-malam --jalankan
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/13 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --lewati-malam --jalankan
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 5/13 J^&T ^<= 15.00 (J^&T RESI SIANG, OPSIONAL) ===
if /i "%JNT_SIANG%"=="Y" ".venv\Scripts\python.exe" src\main.py --jnt-siang --jalankan
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 6/13 J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir jnt --tanpa-reguler --jalankan
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 7/13 J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian 1qty --jalankan
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 8/13 J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian kombinasi --jalankan
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 9/13 SPX HEMAT SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat --tanpa-reguler --jalankan
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 10/13 SPX HEMAT 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian 1qty --jalankan
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 11/13 SPX HEMAT KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian kombinasi --jalankan
call :catat_waktu T9_AKHIR
echo.
call :catat_waktu T10_AWAL
echo === 12/13 SPX STANDARD (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard --jalankan
call :catat_waktu T10_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 13/13 UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis --jalankan
call :catat_waktu TF_AKHIR
echo.
echo EVENT - SESI BIASA selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "EVENT - SESI BIASA" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "J&T RESI SIANG:%T3_AWAL%:%T3_AKHIR%" "J&T SPESIAL:%T4_AWAL%:%T4_AKHIR%" "J&T 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "J&T KOMBINASI:%T6_AWAL%:%T6_AKHIR%" "SPX HEMAT SPESIAL:%T7_AWAL%:%T7_AKHIR%" "SPX HEMAT 1 QTY REGULER:%T8_AWAL%:%T8_AKHIR%" "SPX HEMAT KOMBINASI:%T9_AWAL%:%T9_AKHIR%" "SPX STANDARD:%T10_AWAL%:%T10_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
pause
goto menu

rem ============================================================
rem EVENT - TEPAT JAM 13.00: Shopee Pagi dulu (pesanan Shopee s.d. 12.00:
rem SPX Standard per lantai, SPX Hemat spesial/1 qty/kombinasi, folder
rem hasil TERPISAH), cukup 1x sehari, lalu sesi biasa tanpa J&T Resi Siang.
rem Lihat docs/jadwal-proses.md
rem ============================================================
:event2
call :cek_jam E2 "EVENT TEPAT JAM 13.00 (12.00-15.59)"
if errorlevel 1 goto menu
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio. SHOPEE PAGI cuma 1x sehari.
set "yakin="
set /p "yakin=Lanjutkan EVENT - TEPAT JAM 13.00? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
call :catat_waktu TR_AWAL
echo === 1/16 RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok --jalankan
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/16 SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel --jalankan
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/16 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/16 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 5/16 SPX STANDARD PAGI ^<= 12.00 (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard --pagi --jalankan
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 6/16 SPX HEMAT PAGI SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat-pagi --tanpa-reguler --jalankan
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 7/16 SPX HEMAT PAGI 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat-pagi --bagian 1qty --jalankan
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 8/16 SPX HEMAT PAGI KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat-pagi --bagian kombinasi --jalankan
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 9/16 J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir jnt --tanpa-reguler --jalankan
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 10/16 J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian 1qty --jalankan
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 11/16 J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian kombinasi --jalankan
call :catat_waktu T9_AKHIR
echo.
call :catat_waktu T10_AWAL
echo === 12/16 SPX HEMAT SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat --tanpa-reguler --jalankan
call :catat_waktu T10_AKHIR
echo.
call :catat_waktu T11_AWAL
echo === 13/16 SPX HEMAT 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian 1qty --jalankan
call :catat_waktu T11_AKHIR
echo.
call :catat_waktu T12_AWAL
echo === 14/16 SPX HEMAT KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian kombinasi --jalankan
call :catat_waktu T12_AKHIR
echo.
call :catat_waktu T13_AWAL
echo === 15/16 SPX STANDARD (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard --jalankan
call :catat_waktu T13_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 16/16 UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis --jalankan
call :catat_waktu TF_AKHIR
echo.
echo EVENT - TEPAT JAM 13.00 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "EVENT - TEPAT JAM 13.00" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "SPX STANDARD PAGI:%T3_AWAL%:%T3_AKHIR%" "SPX HEMAT PAGI SPESIAL:%T4_AWAL%:%T4_AKHIR%" "SPX HEMAT PAGI 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "SPX HEMAT PAGI KOMBINASI:%T6_AWAL%:%T6_AKHIR%" "J&T SPESIAL:%T7_AWAL%:%T7_AKHIR%" "J&T 1 QTY REGULER:%T8_AWAL%:%T8_AKHIR%" "J&T KOMBINASI:%T9_AWAL%:%T9_AKHIR%" "SPX HEMAT SPESIAL:%T10_AWAL%:%T10_AKHIR%" "SPX HEMAT 1 QTY REGULER:%T11_AWAL%:%T11_AKHIR%" "SPX HEMAT KOMBINASI:%T12_AWAL%:%T12_AKHIR%" "SPX STANDARD:%T13_AWAL%:%T13_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
pause
goto menu

rem ============================================================
rem Catat waktu sekarang (epoch, time.time()) ke variabel %1 - dipakai
rem sebelum & sesudah tiap langkah proses supaya durasinya bisa dihitung
rem src\rekap_waktu.py di akhir tiap pilihan.
rem JANGAN beri kutip di sekitar .venv\Scripts\python.exe di dalam for /f
rem (lihat tests\test_bat.py) - cmd.exe akan salah potong command-nya.
rem ============================================================
:catat_waktu
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "%~1=%%t"
exit /b 0

rem ============================================================
rem Cek jam sekarang vs jendela jam menu yang dipilih (lihat
rem dalam_jam_menu() di src\main.py & docs\jadwal-proses.md).
rem %1 = kode menu ("E2"), %2 = label jendela untuk pesan.
rem errorlevel 1 -> user pilih batal (kembali ke menu).
rem ============================================================
:cek_jam
set "JAM_OK="
for /f "delims=" %%i in ('.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from main import dalam_jam_menu; print(1 if dalam_jam_menu('%~1') else 0)"') do set "JAM_OK=%%i"
if "%JAM_OK%"=="1" exit /b 0
echo.
echo PERINGATAN: sekarang di luar jam %~2.
set "lanjut_jam="
set /p "lanjut_jam=Apakah anda tidak salah memilih menu? (Y/N): "
if /i "%lanjut_jam%"=="Y" exit /b 0
exit /b 1
