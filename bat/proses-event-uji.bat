@echo off
setlocal
cd /d "%~dp0.."

:menu
cls
echo ==================================================================
echo   PROSES PESANAN OTOMATIS (EVENT: 10.10 / 11.11 / 12.12 DST) - MODE UJI (tidak ada perubahan di Jubelio)
echo ==================================================================
echo   1. Uji EVENT - TIPE 1 (07.00-12.00 / 16.00-17.00)
echo   2. Uji EVENT - TIPE 2 (TEPAT JAM 13.00, + SHOPEE PAGI ^<= 12.00)
echo   3. Uji EVENT - TIPE 3 (13.00-15.00)
echo   4. Uji EVENT - TIPE 4 (TEPAT JAM 15.00, + J^&T RESI SIANG ^<= 15.00)
echo   5. Uji EVENT - MALAM  (URGENT + J^&T / SPX HEMAT / SPX STANDARD dipisah)
echo   0. Keluar
echo ==================================================================
set "pilih="
set /p "pilih=Pilih menu (0-5): "
if "%pilih%"=="1" goto event1
if "%pilih%"=="2" goto event2
if "%pilih%"=="3" goto event3
if "%pilih%"=="4" goto event4
if "%pilih%"=="5" goto event5
rem Keluar pakai "exit" (bukan "goto :eof"/"exit /b"): kalau ada call :label yang belum
rem kembali, "goto :eof" cuma kembali ke baris setelah call itu dan proses LANJUT jalan.
if "%pilih%"=="0" exit
echo.
echo Pilihan "%pilih%" tidak dikenali, coba lagi.
pause
goto menu

rem ============================================================
rem EVENT - TIPE 1 (07.00-12.00 dan 16.00-17.00): J&T, SPX Hemat, dan SPX Standard
rem DIPISAH sepanjang hari. SPX Standard hanya per lantai; J&T dan SPX Hemat spesial,
rem 1 qty, kombinasi. Urgent dengan --lewati-malam. Lihat docs/jadwal-proses.md
rem ============================================================
:event1
echo.
call :catat_waktu TR_AWAL
echo === 1/12 Uji RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/12 Uji SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/12 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --lewati-malam
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/12 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --lewati-malam
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 5/12 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir jnt --tanpa-reguler
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 6/12 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian 1qty
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 7/12 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian kombinasi
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 8/12 Uji SPX HEMAT SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat --tanpa-reguler
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 9/12 Uji SPX HEMAT 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian 1qty
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 10/12 Uji SPX HEMAT KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian kombinasi
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 11/12 Uji SPX STANDARD (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard
call :catat_waktu T9_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 12/12 Uji UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis
call :catat_waktu TF_AKHIR
echo.
echo Uji EVENT - TIPE 1 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "EVENT - TIPE 1" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%" "SPX HEMAT SPESIAL:%T6_AWAL%:%T6_AKHIR%" "SPX HEMAT 1 QTY REGULER:%T7_AWAL%:%T7_AKHIR%" "SPX HEMAT KOMBINASI:%T8_AWAL%:%T8_AKHIR%" "SPX STANDARD:%T9_AWAL%:%T9_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
pause
goto menu

rem ============================================================
rem EVENT - TIPE 2 (TEPAT JAM 13.00): Shopee Pagi dulu (pesanan Shopee s.d. 12.00:
rem SPX Standard per lantai, SPX Hemat spesial/1 qty/kombinasi, folder hasil TERPISAH),
rem cukup 1x sehari, lalu J&T/SPX Hemat/SPX Standard seharian. Urgent tanpa
rem --lewati-malam. Lihat docs/jadwal-proses.md
rem ============================================================
:event2
echo.
call :catat_waktu TR_AWAL
echo === 1/16 Uji RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/16 Uji SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/16 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/16 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 5/16 Uji SPX STANDARD PAGI ^<= 12.00 (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard --pagi
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 6/16 Uji SPX HEMAT PAGI SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat-pagi --tanpa-reguler
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 7/16 Uji SPX HEMAT PAGI 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat-pagi --bagian 1qty
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 8/16 Uji SPX HEMAT PAGI KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat-pagi --bagian kombinasi
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 9/16 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir jnt --tanpa-reguler
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 10/16 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian 1qty
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 11/16 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian kombinasi
call :catat_waktu T9_AKHIR
echo.
call :catat_waktu T10_AWAL
echo === 12/16 Uji SPX HEMAT SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat --tanpa-reguler
call :catat_waktu T10_AKHIR
echo.
call :catat_waktu T11_AWAL
echo === 13/16 Uji SPX HEMAT 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian 1qty
call :catat_waktu T11_AKHIR
echo.
call :catat_waktu T12_AWAL
echo === 14/16 Uji SPX HEMAT KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian kombinasi
call :catat_waktu T12_AKHIR
echo.
call :catat_waktu T13_AWAL
echo === 15/16 Uji SPX STANDARD (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard
call :catat_waktu T13_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 16/16 Uji UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis
call :catat_waktu TF_AKHIR
echo.
echo Uji EVENT - TIPE 2 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "EVENT - TIPE 2" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "SPX STANDARD PAGI:%T3_AWAL%:%T3_AKHIR%" "SPX HEMAT PAGI SPESIAL:%T4_AWAL%:%T4_AKHIR%" "SPX HEMAT PAGI 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "SPX HEMAT PAGI KOMBINASI:%T6_AWAL%:%T6_AKHIR%" "J&T SPESIAL:%T7_AWAL%:%T7_AKHIR%" "J&T 1 QTY REGULER:%T8_AWAL%:%T8_AKHIR%" "J&T KOMBINASI:%T9_AWAL%:%T9_AKHIR%" "SPX HEMAT SPESIAL:%T10_AWAL%:%T10_AKHIR%" "SPX HEMAT 1 QTY REGULER:%T11_AWAL%:%T11_AKHIR%" "SPX HEMAT KOMBINASI:%T12_AWAL%:%T12_AKHIR%" "SPX STANDARD:%T13_AWAL%:%T13_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
pause
goto menu

rem ============================================================
rem EVENT - TIPE 3 (13.00-15.00): J&T, SPX Hemat, dan SPX Standard dipisah seharian,
rem tanpa Shopee Pagi. Urgent dengan --lewati-malam. Lihat docs/jadwal-proses.md
rem ============================================================
:event3
echo.
call :catat_waktu TR_AWAL
echo === 1/12 Uji RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/12 Uji SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/12 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --lewati-malam
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/12 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --lewati-malam
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 5/12 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir jnt --tanpa-reguler
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 6/12 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian 1qty
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 7/12 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian kombinasi
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 8/12 Uji SPX HEMAT SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat --tanpa-reguler
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 9/12 Uji SPX HEMAT 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian 1qty
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 10/12 Uji SPX HEMAT KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian kombinasi
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 11/12 Uji SPX STANDARD (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard
call :catat_waktu T9_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 12/12 Uji UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis
call :catat_waktu TF_AKHIR
echo.
echo Uji EVENT - TIPE 3 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "EVENT - TIPE 3" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%" "SPX HEMAT SPESIAL:%T6_AWAL%:%T6_AKHIR%" "SPX HEMAT 1 QTY REGULER:%T7_AWAL%:%T7_AKHIR%" "SPX HEMAT KOMBINASI:%T8_AWAL%:%T8_AKHIR%" "SPX STANDARD:%T9_AWAL%:%T9_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
pause
goto menu

rem ============================================================
rem EVENT - TIPE 4 (TEPAT JAM 15.00): J&T Resi Siang (pesanan J&T s.d. 15.00, cukup 1x
rem sehari) dulu, lalu J&T/SPX Hemat/SPX Standard dipisah seharian. Urgent dengan
rem --lewati-malam. Lihat docs/jadwal-proses.md
rem ============================================================
:event4
echo.
call :catat_waktu TR_AWAL
echo === 1/13 Uji RECHECK STOK ===
".venv\Scripts\python.exe" src\main.py --recheck-stok
call :catat_waktu TR_AKHIR
echo.
call :catat_waktu T0_AWAL
echo === 2/13 Uji SAMPEL TIKTOK (NILAI 0) ===
".venv\Scripts\python.exe" src\main.py --sampel
call :catat_waktu T0_AKHIR
echo.
call :catat_waktu T1_AWAL
echo === 3/13 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada --lewati-malam
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 4/13 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat --lewati-malam
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 5/13 Uji J^&T ^<= 15.00 (J^&T RESI SIANG) ===
".venv\Scripts\python.exe" src\main.py --jnt-siang
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 6/13 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir jnt --tanpa-reguler
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 7/13 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian 1qty
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 8/13 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian kombinasi
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 9/13 Uji SPX HEMAT SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat --tanpa-reguler
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 10/13 Uji SPX HEMAT 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian 1qty
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 11/13 Uji SPX HEMAT KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian kombinasi
call :catat_waktu T9_AKHIR
echo.
call :catat_waktu T10_AWAL
echo === 12/13 Uji SPX STANDARD (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard
call :catat_waktu T10_AKHIR
echo.
call :catat_waktu TF_AWAL
echo === 13/13 Uji UPLOAD FAKTUR ^& PESANAN KE IRESIS ===
".venv\Scripts\python.exe" src\main.py --upload-iresis
call :catat_waktu TF_AKHIR
echo.
echo Uji EVENT - TIPE 4 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "EVENT - TIPE 4" "RECHECK STOK:%TR_AWAL%:%TR_AKHIR%" "SAMPEL TIKTOK:%T0_AWAL%:%T0_AKHIR%" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "J&T RESI SIANG:%T3_AWAL%:%T3_AKHIR%" "J&T SPESIAL:%T4_AWAL%:%T4_AKHIR%" "J&T 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "J&T KOMBINASI:%T6_AWAL%:%T6_AKHIR%" "SPX HEMAT SPESIAL:%T7_AWAL%:%T7_AKHIR%" "SPX HEMAT 1 QTY REGULER:%T8_AWAL%:%T8_AKHIR%" "SPX HEMAT KOMBINASI:%T9_AWAL%:%T9_AKHIR%" "SPX STANDARD:%T10_AWAL%:%T10_AKHIR%" "UPLOAD IRESIS:%TF_AWAL%:%TF_AKHIR%"
pause
goto menu

rem ============================================================
rem EVENT - MALAM: Urgent Lazada, Urgent GTL & SiCepat, lalu J&T/SPX Hemat/SPX Standard
rem dipisah. Tanpa recheck/sampel dan TANPA IRESIS (IRESIS hanya di jaringan lokal
rem kantor). Urgent tanpa --lewati-malam. Lihat docs/jadwal-proses.md
rem ============================================================
:event5
echo.
call :catat_waktu T1_AWAL
echo === 1/9 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 2/9 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 3/9 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir jnt --tanpa-reguler
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 4/9 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian 1qty
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 5/9 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir jnt --bagian kombinasi
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 6/9 Uji SPX HEMAT SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --event --kurir spx-hemat --tanpa-reguler
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 7/9 Uji SPX HEMAT 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian 1qty
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 8/9 Uji SPX HEMAT KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --event --kurir spx-hemat --bagian kombinasi
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 9/9 Uji SPX STANDARD (PER LANTAI) ===
".venv\Scripts\python.exe" src\main.py --spx-standard
call :catat_waktu T9_AKHIR
echo.
echo Uji EVENT - MALAM selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "EVENT - MALAM" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%" "SPX HEMAT SPESIAL:%T6_AWAL%:%T6_AKHIR%" "SPX HEMAT 1 QTY REGULER:%T7_AWAL%:%T7_AKHIR%" "SPX HEMAT KOMBINASI:%T8_AWAL%:%T8_AKHIR%" "SPX STANDARD:%T9_AWAL%:%T9_AKHIR%"
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
