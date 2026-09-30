@echo off
setlocal
cd /d "%~dp0"

:menu
cls
echo ==================================================================
echo   PROSES PESANAN OTOMATIS - MODE UJI (tidak ada perubahan di Jubelio)
echo ==================================================================
echo   1. Uji SESI PAGI
echo   2. Uji JAM 13.00
echo   3. Uji SESI SORE
echo   0. Keluar
echo ==================================================================
set "pilih="
set /p "pilih=Pilih menu: "
if "%pilih%"=="1" goto sesi_pagi
if "%pilih%"=="2" goto jam_1300
if "%pilih%"=="3" goto sesi_sore
if "%pilih%"=="0" goto :eof
goto menu

:sesi_pagi
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
echo Uji SESI PAGI selesai.
pause
goto menu

:jam_1300
echo.
echo === 1/9 Uji URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
echo.
echo === 2/9 Uji URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
echo.
echo === 3/9 Uji SPX PAGI (RESI SHOPEE ^<= 12.00) ===
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
echo Uji JAM 13.00 selesai.
pause
goto menu

:sesi_sore
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
echo Uji SESI SORE selesai.
pause
goto menu
