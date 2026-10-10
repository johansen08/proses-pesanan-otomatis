@echo off
setlocal
cd /d "%~dp0.."

rem Sesi folder label dihitung SEKALI di sini (bertahan selama proses-harian.bat ini berjalan).
rem Ditutup lalu dijalankan ulang -> sesi baru (angka lanjut dari yang terbesar hari ini).
for /f "delims=" %%i in ('.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from main import sesi_label_baru; print(sesi_label_baru())"') do set "LABEL_SESI_DIR=%%i"
echo Sesi label: %LABEL_SESI_DIR%

:menu
cls
echo ==================================================================
echo   PROSES PESANAN OTOMATIS (NON EVENT)
echo ==================================================================
echo   1. GABUNG JNT+SPX                           (07.00-12.00 / 16.00-17.00)
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
rem Keluar pakai "exit" (bukan "goto :eof"/"exit /b"): kalau ada call :label yang belum
rem kembali, "goto :eof" cuma kembali ke baris setelah call itu dan proses LANJUT jalan.
if "%pilih%"=="0" exit
echo.
echo Pilihan "%pilih%" tidak dikenali, coba lagi.
pause
goto menu

rem ============================================================
rem TIPE 1: J&T dan SPX DIGABUNG (seperti semula). Dipakai siklus
rem pagi 07.00-11.xx DAN siklus sore 16.00-17.00 (malam/dini hari: proses-malam.bat)
rem (setelah TIPE 4 selesai, sampai jam 17.00)
rem - lihat docs/jadwal-proses.md
rem ============================================================
:tipe1
call :cek_jam 1 "TIPE 1 (07.00-12.00 / 16.00-17.00)"
if errorlevel 1 goto menu
echo.
echo PERHATIAN: proses SUNGGUHAN di Jubelio.
set "yakin="
set /p "yakin=Lanjutkan TIPE 1? (Y/N): "
if /i not "%yakin%"=="Y" goto menu
echo.
call :catat_waktu TR_AWAL
set "WAKTU_MENU_MULAI=%TR_AWAL%"
echo === 1/9 RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok --jalankan
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/9 SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel --jalankan
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/9 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan --lewati-malam
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/9 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan --lewati-malam
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu TJ_AWAL
echo === 5/9 URGENT JNE ^& LEX ===
".venv\Scripts\python.exe" src\main.py --urgent --channel jne-lex --jalankan --lewati-malam
call :catat_waktu TJ_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 6/9 SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler --jalankan --non-wajib-sore
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 7/9 SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --jalankan --non-wajib-sore
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 8/9 SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --jalankan --non-wajib-sore
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 9/9 UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis --jalankan
call :catat_waktu TF_AKHIR
echo.
echo TIPE 1 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 1" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "URGENT JNE & LEX:%TJ_AWAL%:%TJ_AKHIR%" "SPX - J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "SPX - J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "SPX - J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
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
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/13 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu TJ_AWAL
echo === 5/13 URGENT JNE ^& LEX ===
".venv\Scripts\python.exe" src\main.py --urgent --channel jne-lex --jalankan
call :catat_waktu TJ_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 6/13 SPX ^<= 12.00 (SPX RESI PAGI) ===
".venv\Scripts\python.exe" src\main.py --shopee-pagi --jalankan
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 7/13 J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler --jalankan
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 8/13 J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt --jalankan
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 9/13 J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt --jalankan
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 10/13 SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler --jalankan --non-wajib
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 11/13 SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx --jalankan --non-wajib
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 12/13 SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx --jalankan --non-wajib
call :catat_waktu T9_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 13/13 UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis --jalankan
call :catat_waktu TF_AKHIR
echo.
echo TIPE 2 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 2" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "URGENT JNE & LEX:%TJ_AWAL%:%TJ_AKHIR%" "SPX RESI PAGI:%T3_AWAL%:%T3_AKHIR%" "J&T SPESIAL:%T4_AWAL%:%T4_AKHIR%" "J&T 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "J&T KOMBINASI:%T6_AWAL%:%T6_AKHIR%" "SPX SPESIAL:%T7_AWAL%:%T7_AKHIR%" "SPX 1 QTY REGULER:%T8_AWAL%:%T8_AKHIR%" "SPX KOMBINASI:%T9_AWAL%:%T9_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
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
call :catat_waktu TR_AWAL
echo === 1/12 RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok --jalankan
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/12 SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel --jalankan
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/12 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/12 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu TJ_AWAL
echo === 5/12 URGENT JNE ^& LEX ===
".venv\Scripts\python.exe" src\main.py --urgent --channel jne-lex --jalankan
call :catat_waktu TJ_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 6/12 J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler --jalankan
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 7/12 J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt --jalankan
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 8/12 J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt --jalankan
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 9/12 SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler --jalankan --non-wajib
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 10/12 SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx --jalankan --non-wajib
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 11/12 SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx --jalankan --non-wajib
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 12/12 UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis --jalankan
call :catat_waktu TF_AKHIR
echo.
echo TIPE 3 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 3" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "URGENT JNE & LEX:%TJ_AWAL%:%TJ_AKHIR%" "J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%" "SPX SPESIAL:%T6_AWAL%:%T6_AKHIR%" "SPX 1 QTY REGULER:%T7_AWAL%:%T7_AKHIR%" "SPX KOMBINASI:%T8_AWAL%:%T8_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
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
call :catat_waktu TR_AWAL
echo === 1/10 RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok --jalankan
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/10 SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel --jalankan
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/10 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --jalankan
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/10 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --jalankan
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu TJ_AWAL
echo === 5/10 URGENT JNE ^& LEX ===
".venv\Scripts\python.exe" src\main.py --urgent --channel jne-lex --jalankan
call :catat_waktu TJ_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 6/10 J^&T ^<= 15.00 (J^&T RESI SIANG) ===
".venv\Scripts\python.exe" src\main.py --jnt-siang --jalankan
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 7/10 SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler --jalankan --non-wajib
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 8/10 SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --jalankan --non-wajib
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 9/10 SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --jalankan --non-wajib
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 10/10 UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis --jalankan
call :catat_waktu TF_AKHIR
echo.
echo TIPE 4 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 4" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "URGENT JNE & LEX:%TJ_AWAL%:%TJ_AKHIR%" "J&T RESI SIANG:%T3_AWAL%:%T3_AKHIR%" "SPX - J&T SPESIAL:%T4_AWAL%:%T4_AKHIR%" "SPX - J&T 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "SPX - J&T KOMBINASI:%T6_AWAL%:%T6_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
pause
goto menu

rem ============================================================
rem Catat waktu sekarang (epoch, time.time()) ke variabel %1 - dipakai
rem sebelum & sesudah tiap langkah proses supaya durasinya bisa dihitung
rem src\rekap_waktu.py di akhir tiap TIPE.
rem JANGAN beri kutip di sekitar .venv\Scripts\python.exe di dalam for /f
rem (lihat tests\test_bat.py) - cmd.exe akan salah potong command-nya.
rem ============================================================
:catat_waktu
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "%~1=%%t"
exit /b 0

rem ============================================================
rem Cek jam sekarang vs jendela jam menu yang dipilih (lihat
rem dalam_jam_menu() di src\main.py & docs\jadwal-proses.md).
rem %1 = kode menu ("1"/"2"/"3"/"4"), %2 = label jendela untuk pesan.
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
