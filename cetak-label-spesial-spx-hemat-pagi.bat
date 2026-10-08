@echo off
setlocal
cd /d "%~dp0"

echo ==================================================================
echo   CETAK LABEL SPESIAL SPX HEMAT PAGI (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   di subfolder SPXHEMATPAGI_SPESIAL, lalu mencetaknya berurut
echo   (nomor PICK terkecil dulu) ke printer yang anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis spesial-spx-hemat-pagi %*

echo.
pause
