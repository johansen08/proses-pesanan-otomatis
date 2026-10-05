@echo off
setlocal
cd /d "%~dp0"

echo ==================================================================
echo   CETAK LABEL URGENT (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   di subfolder URGENT (Lazada & GTL-SiCepat), lalu mencetaknya
echo   berurut (nomor PICK terkecil dulu) ke printer yang anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis urgent %*

echo.
pause
