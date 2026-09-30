# Panduan Instalasi di PC Baru

Panduan ini untuk memindahkan proyek **proses-pesanan-otomatis** ke PC/laptop lain
(Windows) agar `proses-harian.bat` bisa langsung jalan.

> Jika Claude Code yang membaca file ini di PC baru: jalankan langkah-langkah di
> bagian **"Langkah instalasi"** secara berurutan lewat terminal (PowerShell/CMD),
> lalu verifikasi dengan bagian **"Cek hasil instalasi"** di paling bawah.

## 1. Yang harus dipindahkan dari PC lama

Salin folder proyek ini (`C:\proses-pesanan-otomatis` atau lokasi lain terserah),
**termasuk** file-file berikut yang biasanya di-ignore git (`.gitignore`) tapi
tetap perlu ikut dipindahkan supaya konfigurasi & riwayat tidak hilang:

- `.env` — isi kredensial Jubelio (lihat langkah 5 kalau mau isi baru saja)
- `riwayat_picklist.xlsx` — riwayat semua picklist yang pernah dibuat

Folder **`.venv`** dan **`__pycache__`** TIDAK perlu disalin — akan dibuat ulang
di PC baru (langkah 3). Folder `laporan-siap-proses/`, `laporan-sku-spesial/`, `label-pengiriman/`,
`logs/` boleh disalin kalau mau menyimpan histori file lama, tapi tidak wajib (dibuat
otomatis saat program pertama kali jalan).

## 2. Prasyarat: Install Python

Proyek ini dites dengan **Python 3.13** (versi persis di PC sumber: 3.13.7).
Gunakan Python **3.11 atau lebih baru** kalau 3.13 tidak tersedia — semua
library yang dipakai (`pandas`, `openpyxl`, `reportlab`, `requests`, `tzdata`,
`playwright`) kompatibel dengan versi-versi itu.

1. Unduh installer dari https://www.python.org/downloads/windows/
   (pilih "Windows installer (64-bit)" versi 3.13.x terbaru).
2. Jalankan installer, **wajib centang "Add python.exe to PATH"** di layar
   pertama, lalu klik "Install Now".
3. Verifikasi di terminal baru:

```bash
python --version
```

Harus muncul `Python 3.13.x` (atau minimal 3.11.x).

## 3. Buat virtual environment & install library

Buka terminal (PowerShell/CMD), masuk ke folder proyek, lalu jalankan:

```bash
cd C:\proses-pesanan-otomatis
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
```

Ini akan menginstall 5 library dari `requirements.txt`:

| Library | Kegunaan |
|---|---|
| `pandas` | Baca/olah data Excel laporan pesanan |
| `openpyxl` | Baca/tulis file `.xlsx` (Excel) |
| `reportlab` | Membuat PDF (label & laporan SKU spesial) |
| `requests` | Panggil API Jubelio |
| `tzdata` | Data zona waktu WIB (Windows tidak punya bawaan) — dipakai fitur Shopee Pagi |
| `playwright` | Hanya dipakai skrip perekam di folder `sniff/` (opsional, lihat langkah 4) |

## 4. (Opsional) Setup Playwright untuk folder `sniff/`

Hanya diperlukan jika Anda akan menjalankan `sniff\run_sniff_jubel.bat` (alat
perekam ulang alur Jubelio, dipakai kalau Jubelio mengubah tampilan/API-nya).
**Tidak diperlukan** untuk pemakaian normal lewat `proses-harian.bat`.

```bash
.venv\Scripts\python -m playwright install chromium
```

## 5. Buat file `.env` (kredensial Jubelio)

Buat file bernama `.env` di root folder proyek (kalau belum ikut disalin dari
langkah 1) dengan isi:

```
JUBELIO_EMAIL=email_akun_jubelio_anda
JUBELIO_PASSWORD=password_akun_jubelio_anda
```

Ganti dengan email & password akun Jubelio yang sebenarnya. Baris
`JUBELIO_FID` dan `JUBELIO_CLIENT_KEY` opsional, boleh dikosongkan/dihapus
(default sudah diambil dari rekaman sniff di kode).

**Jangan bagikan file `.env` ini ke siapa pun** — isinya kredensial login.

## 6. Jalankan program

Klik dua kali `proses-harian.bat`, atau dari terminal:

```bash
proses-harian.bat
```

Program akan menampilkan menu 3 sesi (SESI PAGI, JAM 13.00, SESI SORE) +
Keluar seperti di [README.md](../README.md)/[jadwal-proses.md](jadwal-proses.md).
Folder `laporan-siap-proses/`, `laporan-sku-spesial/`, `label-pengiriman/`, `logs/` akan dibuat
otomatis saat dibutuhkan.

**Disarankan**: coba dulu `proses-harian-uji.bat` (mode uji, struktur menu sama seperti
`proses-harian.bat` — tidak mengubah apa pun di Jubelio) untuk memastikan login &
koneksi API berhasil, sebelum menjalankan sesi di `proses-harian.bat` yang membuat
picklist sungguhan.

## 7. (Opsional) Jadwal otomatis via Windows Task Scheduler

Kalau di PC lama ada jadwal otomatis (Task Scheduler) yang menjalankan
`jalankan.bat`, buat ulang di PC baru:

*Create Basic Task* → pilih jadwal → *Start a program*:
- Program: `C:\proses-pesanan-otomatis\jalankan.bat` (sesuaikan path)
- Start in: `C:\proses-pesanan-otomatis` (sesuaikan path)

---

## Cek hasil instalasi

Jalankan urutan berikut untuk memastikan semua terpasang benar:

```bash
python --version
.venv\Scripts\python -m pip list
.venv\Scripts\python -c "import pandas, openpyxl, reportlab, requests, tzdata; print('OK: semua library utama terbaca')"
```

Lalu pastikan file `.env` ada dan berisi `JUBELIO_EMAIL` + `JUBELIO_PASSWORD`
yang benar, baru jalankan `proses-harian-uji.bat` (mode uji) sebagai tes akhir koneksi ke
Jubelio.
