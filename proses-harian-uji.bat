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
echo === 1/5 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
echo.
echo === 2/5 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
echo.
echo === 3/5 Uji SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler
echo.
echo === 4/5 Uji SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty
echo.
echo === 5/5 Uji SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi
echo.
echo Uji TIPE 1 selesai.
pause
goto menu

:tipe2
echo.
echo === 1/9 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
echo.
echo === 2/9 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
echo.
echo === 3/9 Uji SPX ^<= 12.00 (SPX RESI PAGI) ===
".venv\Scripts\python.exe" src\main.py --shopee-pagi
echo.
echo === 4/9 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler
echo.
echo === 5/9 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt
echo.
echo === 6/9 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt
echo.
echo === 7/9 Uji SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler
echo.
echo === 8/9 Uji SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx
echo.
echo === 9/9 Uji SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx
echo.
echo Uji TIPE 2 selesai.
pause
goto menu

:tipe3
echo.
echo === 1/8 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
echo.
echo === 2/8 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
echo.
echo === 3/8 Uji J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir jnt --tanpa-reguler
echo.
echo === 4/8 Uji J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir jnt
echo.
echo === 5/8 Uji J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir jnt
echo.
echo === 6/8 Uji SPX SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --kurir spx --tanpa-reguler
echo.
echo === 7/8 Uji SPX 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty --kurir spx
echo.
echo === 8/8 Uji SPX KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi --kurir spx
echo.
echo Uji TIPE 3 selesai.
pause
goto menu

:tipe4
echo.
echo === 1/6 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
echo.
echo === 2/6 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
echo.
echo === 3/6 Uji J^&T ^<= 15.00 (J^&T RESI SIANG) ===
".venv\Scripts\python.exe" src\main.py --jnt-siang
echo.
echo === 4/6 Uji SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler
echo.
echo === 5/6 Uji SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty
echo.
echo === 6/6 Uji SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi
echo.
echo Uji TIPE 4 selesai.
pause
goto menu
