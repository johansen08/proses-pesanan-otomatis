@echo off
setlocal
cd /d "%~dp0"

rem Menu cetak bulk label (HARIAN / EVENT / PER KURIR / satu jenis) - lihat menu_pilih_jenis()
rem di src\print_spesial.py. Argumen apa pun diteruskan apa adanya, mis.:
rem   cetak-label.bat --ulang "logs\gagal_cetak_xxx.txt"   (cetak ulang yang gagal, tanpa menu)
rem   cetak-label.bat --paket event-semua                 (langsung cetak paket, tanpa menu)
rem   cetak-label.bat --folder label-pengiriman\2026-10-10\3

".venv\Scripts\python.exe" src\print_spesial.py %*

echo.
pause
