@echo off
setlocal
cd /d "%~dp0"

rem Tombol BUKA APP: jalankan server UI desktop (menu Harian & Cetak) lalu buka di browser,
rem langsung di menu Harian. Jendela ini harus tetap terbuka selama app dipakai - menutupnya
rem menghentikan app (proses yang sedang berjalan di menu Harian ikut terhenti).
rem Klik dua kali lagi saat app sudah berjalan = hanya membuka tampilannya.
echo Membuka UI Proses Pesanan Otomatis ...
".venv\Scripts\python.exe" src\server_ui.py --buka --menu harian
if errorlevel 1 pause
