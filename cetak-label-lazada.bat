@echo off
setlocal
cd /d "%~dp0"

echo ==================================================================
echo   CETAK LABEL LAZADA (BULK, SKALA CUSTOM 68%%)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   Lazada di subfolder URGENT, merender tiap label (A5) ke skala
echo   68%% di kertas 100x150 mm, lalu mencetaknya berurut (nomor PICK
echo   terkecil dulu) ke printer yang anda pilih. Tanpa SumatraPDF.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis lazada %*

echo.
pause
