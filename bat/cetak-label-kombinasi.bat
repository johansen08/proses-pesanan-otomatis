@echo off
setlocal
cd /d "%~dp0.."

echo ==================================================================
echo   CETAK LABEL KOMBINASI REGULER (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   di subfolder KOMBINASI (Kombinasi Reguler per lantai rak), lalu
echo   mencetaknya berurut (nomor PICK terkecil dulu) ke printer yang
echo   anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis kombinasi %*

echo.
pause
