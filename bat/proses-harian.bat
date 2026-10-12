@echo off
setlocal
cd /d "%~dp0.."

rem Menu TIPE 1-4 proses harian (non event). SUNGGUHAN, mengubah data di Jubelio.
rem Peluncur tipis: semua langkah/urutan/flag ada di src\alur.py (satu sumber, sama dengan UI),
rem menunya di src\menu_konsol.py. JANGAN menulis ulang daftar langkah di .bat ini.
".venv\Scripts\python.exe" src\menu_konsol.py harian
if errorlevel 1 pause
