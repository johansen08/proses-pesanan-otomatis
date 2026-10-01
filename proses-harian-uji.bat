@echo off
setlocal
cd /d "%~dp0"

:menu
cls
echo ==================================================================
echo   PROSES PESANAN OTOMATIS (NON EVENT) - MODE UJI (tidak ada perubahan di Jubelio)
echo ==================================================================
echo   1. Uji GABUNG JNT+SPX                           (07.00-12.00 / 16.00-07.00)
echo   2. Uji DIPISAH + SPX RESI ^<= 12.00              (TEPAT JAM 13.00)
echo   3. Uji DIPISAH, TANPA SPX RESI PAGI             (13.00-15.00)
echo   4. Uji GABUNG JNT+SPX LAGI + JNT RESI ^<= 15.00  (TEPAT JAM 15.00)
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

:tipe1
echo.
call :catat_waktu T1_AWAL
echo === 1/5 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 2/5 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 3/5 Uji SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 4/5 Uji SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 5/5 Uji SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi
call :catat_waktu T5_AKHIR
echo.
echo Uji TIPE 1 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 1" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "SPX - J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "SPX - J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "SPX - J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%"
pause
goto menu

:tipe2
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
echo === 3/9 Uji SPX ^<= 12.00 (SPX RESI PAGI) ===
".venv\Scripts\python.exe" src\main.py --shopee-pagi
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 4/9 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 5/9 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 6/9 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 7/9 Uji SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 8/9 Uji SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx
call :catat_waktu T8_AKHIR
echo.
call :catat_waktu T9_AWAL
echo === 9/9 Uji SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx
call :catat_waktu T9_AKHIR
echo.
echo Uji TIPE 2 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 2" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "SPX RESI PAGI:%T3_AWAL%:%T3_AKHIR%" "J&T SPESIAL:%T4_AWAL%:%T4_AKHIR%" "J&T 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "J&T KOMBINASI:%T6_AWAL%:%T6_AKHIR%" "SPX SPESIAL:%T7_AWAL%:%T7_AKHIR%" "SPX 1 QTY REGULER:%T8_AWAL%:%T8_AKHIR%" "SPX KOMBINASI:%T9_AWAL%:%T9_AKHIR%"
pause
goto menu

:tipe3
echo.
call :catat_waktu T1_AWAL
echo === 1/8 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 2/8 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 3/8 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 4/8 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 5/8 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 6/8 Uji SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler
call :catat_waktu T6_AKHIR
echo.
call :catat_waktu T7_AWAL
echo === 7/8 Uji SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx
call :catat_waktu T7_AKHIR
echo.
call :catat_waktu T8_AWAL
echo === 8/8 Uji SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx
call :catat_waktu T8_AKHIR
echo.
echo Uji TIPE 3 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 3" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%" "SPX SPESIAL:%T6_AWAL%:%T6_AKHIR%" "SPX 1 QTY REGULER:%T7_AWAL%:%T7_AKHIR%" "SPX KOMBINASI:%T8_AWAL%:%T8_AKHIR%"
pause
goto menu

:tipe4
echo.
call :catat_waktu T1_AWAL
echo === 1/6 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
call :catat_waktu T1_AKHIR
echo.
call :catat_waktu T2_AWAL
echo === 2/6 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
call :catat_waktu T2_AKHIR
echo.
call :catat_waktu T3_AWAL
echo === 3/6 Uji J^&T ^<= 15.00 (J^&T RESI SIANG) ===
".venv\Scripts\python.exe" src\main.py --jnt-siang
call :catat_waktu T3_AKHIR
echo.
call :catat_waktu T4_AWAL
echo === 4/6 Uji SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler
call :catat_waktu T4_AKHIR
echo.
call :catat_waktu T5_AWAL
echo === 5/6 Uji SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty
call :catat_waktu T5_AKHIR
echo.
call :catat_waktu T6_AWAL
echo === 6/6 Uji SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi
call :catat_waktu T6_AKHIR
echo.
echo Uji TIPE 4 selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "TIPE 4" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "J&T RESI SIANG:%T3_AWAL%:%T3_AKHIR%" "SPX - J&T SPESIAL:%T4_AWAL%:%T4_AKHIR%" "SPX - J&T 1 QTY REGULER:%T5_AWAL%:%T5_AKHIR%" "SPX - J&T KOMBINASI:%T6_AWAL%:%T6_AKHIR%"
pause
goto menu

rem ============================================================
rem Catat waktu sekarang (epoch, time.time()) ke variabel %1 - dipakai
rem sebelum & sesudah tiap langkah proses supaya durasinya bisa dihitung
rem src\rekap_waktu.py di akhir tiap TIPE.
rem ============================================================
:catat_waktu
for /f "delims=" %%t in ('".venv\Scripts\python.exe" -c "import time; print(time.time())"') do set "%~1=%%t"
exit /b 0
