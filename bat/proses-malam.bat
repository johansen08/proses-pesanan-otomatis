@echo off
setlocal
cd /d "%~dp0.."

rem Proses MALAM harian: urgent + SPX-J&T, tanpa menu, tanpa IRESIS. SUNGGUHAN, mengubah data di Jubelio.
rem Peluncur tipis: semua langkah/urutan/flag ada di src\alur.py (satu sumber, sama dengan UI),
rem menunya di src\menu_konsol.py. JANGAN menulis ulang daftar langkah di .bat ini.
".venv\Scripts\python.exe" src\menu_konsol.py malam
if errorlevel 1 pause
