@echo off
setlocal
cd /d "%~dp0.."

rem Proses MALAM (MODE UJI, kembaran proses-malam.bat tanpa --jalankan): Urgent Lazada, Urgent GTL & SiCepat, lalu SPX - J&T (J&T+SPX digabung).
rem Tanpa menu & tanpa subrutin/label (hindari bug lompat label cmd). IRESIS tidak ikut.
rem Sesi folder label dihitung SEKALI di sini.
for /f "delims=" %%i in ('.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from main import sesi_label_baru; print(sesi_label_baru())"') do set "LABEL_SESI_DIR=%%i"
echo Sesi label: %LABEL_SESI_DIR%
echo.
echo ==================================================================
echo   PROSES MALAM (MODE UJI - tidak mengubah data)
echo   1. Urgent Lazada  2. Urgent GTL ^& SiCepat  3. SPX - J^&T (spesial, 1 qty, kombinasi)
echo ==================================================================
echo MODE UJI: hanya menampilkan rencana, tidak mengubah data di Jubelio.
set "yakin="
set /p "yakin=Lanjutkan uji proses malam? (Y/N): "
if /i not "%yakin%"=="Y" exit /b 0
echo.
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T1_AWAL=%%t"
echo === 1/5 URGENT LAZADA ===
".venv\Scripts\python.exe" src\main.py --urgent --channel lazada
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T1_AKHIR=%%t"
echo.
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T2_AWAL=%%t"
echo === 2/5 URGENT GTL ^& SICEPAT ===
".venv\Scripts\python.exe" src\main.py --urgent --channel gtl-sicepat
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T2_AKHIR=%%t"
echo.
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T3_AWAL=%%t"
echo === 3/5 SPX - J^&T SPESIAL ===
".venv\Scripts\python.exe" src\main.py --label --tanpa-reguler
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T3_AKHIR=%%t"
echo.
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T4_AWAL=%%t"
echo === 4/5 SPX - J^&T 1 QTY REGULER ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian 1qty
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T4_AKHIR=%%t"
echo.
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T5_AWAL=%%t"
echo === 5/5 SPX - J^&T KOMBINASI ===
".venv\Scripts\python.exe" src\main.py --reguler --bagian kombinasi
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time; print(time.time())"') do set "T5_AKHIR=%%t"
echo.
echo Proses malam selesai.
".venv\Scripts\python.exe" src\rekap_waktu.py "MALAM" "URGENT LAZADA:%T1_AWAL%:%T1_AKHIR%" "URGENT GTL & SICEPAT:%T2_AWAL%:%T2_AKHIR%" "SPX - J&T SPESIAL:%T3_AWAL%:%T3_AKHIR%" "SPX - J&T 1 QTY REGULER:%T4_AWAL%:%T4_AKHIR%" "SPX - J&T KOMBINASI:%T5_AWAL%:%T5_AKHIR%"
pause
