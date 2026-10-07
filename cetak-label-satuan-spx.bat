@echo off
setlocal
cd /d "%~dp0"

echo ==================================================================
echo   CETAK LABEL SATUAN / 1 QTY REGULER SPX (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   di subfolder SPX_SATUAN, lalu mencetaknya berurut
echo   (nomor PICK terkecil dulu) ke printer yang anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis satuan-spx %*

echo.
pause
