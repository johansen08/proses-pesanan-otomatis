@echo off
setlocal
cd /d "%~dp0"

echo ==================================================================
echo   CETAK LABEL KOMBINASI JNT (BULK)
echo ==================================================================
echo   Mencari folder sesi label-pengiriman TERBARU, menyaring label
echo   di subfolder JNT_KOMBINASI, lalu mencetaknya berurut
echo   (nomor PICK terkecil dulu) ke printer yang anda pilih.
echo ==================================================================
echo.

".venv\Scripts\python.exe" src\print_spesial.py --jenis kombinasi-jnt %*

echo.
pause
