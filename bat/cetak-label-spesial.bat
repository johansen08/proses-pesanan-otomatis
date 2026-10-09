@echo off
setlocal
cd /d "%~dp0.."

echo ==================================================================
echo   CETAK LABEL SPESIAL (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   bertanda SPESIAL, lalu mencetaknya berurut (nomor PICK terkecil
echo   dulu) ke printer yang anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis spesial %*

echo.
pause
