@echo off
setlocal
cd /d "%~dp0"

echo ==================================================================
echo   CETAK LABEL SATUAN / 1 QTY REGULER (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   di subfolder SATUAN (1 Qty Reguler per grup rak), lalu
echo   mencetaknya berurut (nomor PICK terkecil dulu) ke printer yang
echo   anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis satuan %*

echo.
pause
