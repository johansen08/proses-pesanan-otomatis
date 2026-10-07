@echo off
setlocal
cd /d "%~dp0"

echo ==================================================================
echo   CETAK LABEL GTL-SICEPAT (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   GTL-SiCepat di subfolder URGENT (Lazada TIDAK ikut), lalu mencetaknya
echo   berurut (nomor PICK terkecil dulu) ke printer yang anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis gtl-sicepat %*

echo.
pause
