@echo off
setlocal
cd /d "%~dp0.."

rem Menu EVENT (10.10 / 11.11 / 12.12 dst): TIPE 1-4 + MALAM. MODE UJI: tanpa --jalankan, tidak mengubah data di Jubelio.
rem Peluncur tipis: semua langkah/urutan/flag ada di src\alur.py (satu sumber, sama dengan UI),
rem menunya di src\menu_konsol.py. JANGAN menulis ulang daftar langkah di .bat ini.
".venv\Scripts\python.exe" src\menu_konsol.py event --uji
if errorlevel 1 pause
