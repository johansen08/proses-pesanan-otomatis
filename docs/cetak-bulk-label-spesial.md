# Cetak Bulk Label SPESIAL (SumatraPDF)

Panduan lengkap fitur **cetak bulk label SKU spesial** (`cetak-label-spesial.bat` /
`src/print_spesial.py`): cara install SumatraPDF (syarat wajib fitur ini) dan cara
pakai fiturnya sehari-hari.

## 1. Apa fitur ini

Mencetak ulang semua label SKU spesial — PDF yang namanya mengandung penanda
`_SPESIAL_` (dibuat `proses_label.py` di alur `--label`, lihat
[analisa-alur-cetak-label.md](analisa-alur-cetak-label.md)), mis.
`PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf` — secara **bulk dan berurut**
(nomor PICK terkecil/paling dulu dibuat, duluan dicetak), langsung ke printer
pilihan, tanpa perlu buka file PDF satu-satu secara manual.

**Program ini TIDAK membuat picklist/label baru.** Fungsinya cuma mencetak ulang
PDF label yang sudah ada di folder `label-pengiriman/`. Picklist & label itu
sendiri dibuat lewat alur `--label` (lihat README bagian 2).

## 2. Download & setup SumatraPDF (sekali saja per PC)

Fitur ini **wajib** menggunakan [SumatraPDF](https://www.sumatrapdfreader.org/) —
pembaca PDF gratis & ringan yang dipakai di sini untuk mencetak PDF langsung dari
command line (`-print-to -silent`) tanpa jendela PDF reader terbuka satu per satu
untuk tiap label.

### 2.1 Download & install

1. Buka https://www.sumatrapdfreader.org/download-free-pdf-viewer
2. Pilih installer **64-bit** (sesuai Windows 64-bit yang umum dipakai), bukan versi
   "portable" — supaya terpasang di lokasi standar dan mudah ditemukan otomatis oleh
   `print_spesial.py`.
3. Jalankan installer, ikuti langkah instalasi default (Next → Install → Finish).
   Tidak perlu set SumatraPDF sebagai pembaca PDF default di Windows — fitur ini
   hanya memanggil `SumatraPDF.exe` langsung, tidak lewat asosiasi file.

Lokasi hasil install biasanya salah satu dari:

```
C:\Program Files\SumatraPDF\SumatraPDF.exe
C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe
%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe
```

### 2.2 Verifikasi terdeteksi otomatis

`print_spesial.py` mencari `SumatraPDF.exe` otomatis, berurutan:

1. Environment variable `SUMATRA_PDF_PATH` (kalau diset).
2. PATH sistem (`SumatraPDF.exe`/`SumatraPDF`).
3. Tiga lokasi install umum di atas.

Kalau install lewat installer default, biasanya langsung ketemu tanpa setting
tambahan. Cek dengan menjalankan `cetak-label-spesial.bat` — kalau SumatraPDF
**tidak** ditemukan, program berhenti dengan pesan:

```
SumatraPDF.exe tidak ditemukan. Install dari https://www.sumatrapdfreader.org/
atau set environment variable SUMATRA_PDF_PATH ke lokasi SumatraPDF.exe.
```

### 2.3 Kalau terinstall di lokasi tidak standar

Set environment variable `SUMATRA_PDF_PATH` ke path lengkap `SumatraPDF.exe`.
Lewat PowerShell (permanen, berlaku untuk user Windows saat ini):

```powershell
[Environment]::SetEnvironmentVariable("SUMATRA_PDF_PATH", "D:\Apps\SumatraPDF\SumatraPDF.exe", "User")
```

Buka terminal/PC baru (atau klik 2x ulang `cetak-label-spesial.bat` setelah
restart) supaya environment variable baru terbaca.

## 3. Cara pakai

```bash
cetak-label-spesial.bat
```

Urutan kerja program:

1. Cari folder sesi `label-pengiriman/YYYY-MM-DD/N` **terbaru** secara otomatis
   (dibandingkan dari tanggal lalu nomor urut sesi di nama folder, bukan dari waktu
   modifikasi file).
2. Saring file yang namanya mengandung `_SPESIAL_`.
3. Tampilkan daftar printer yang terhubung ke komputer (lewat `Get-Printer`
   PowerShell) — pilih nomor printer.
4. Konfirmasi (Y/N) sebelum mulai cetak.
5. Cetak satu per satu secara **berurut** (nomor PICK terkecil dulu).

### Pilihan tambahan

| Perintah | Kegunaan |
|---|---|
| `cetak-label-spesial.bat --folder "label-pengiriman\2026-10-01\3"` | Pakai folder sesi tertentu, bukan yang terbaru (mis. mau cetak ulang sesi sebelumnya) |
| `cetak-label-spesial.bat --tanpa-konfirmasi` | Lewati tanya Y/N sebelum mulai cetak (tetap tanya pilih printer) |
| `cetak-label-spesial.bat --ulang "logs\gagal_cetak_2026-10-01_153000.txt"` | Cetak ULANG hanya file dari daftar gagal sebelumnya (lihat bagian 4), tanpa mencari ulang folder sesi |

## 4. Kertas habis / printer bermasalah di tengah cetak

Program memantau antrian cetak Windows (`Get-PrintJob`, modul PrintManagement)
setelah tiap file dikirim. Kalau job itu ditandai bermasalah (status salah satu
dari `PaperOut`, `Error`, `UserIntervention`, `Offline`, `Blocked_DevQ`), program:

1. **Berhenti di file itu** (tidak lanjut ke file berikutnya dulu).
2. Menampilkan pesan di layar untuk memperbaiki masalahnya (isi ulang kertas,
   buka yang macet, dst).
3. Tekan **ENTER** untuk melanjutkan — mencetak ulang **dari file yang sama**,
   bukan lanjut ke file berikutnya, supaya tidak ada label yang terlewat diam-diam
   dan file sebelumnya tidak ikut tercetak dobel.
4. Atau ketik `lewati` + ENTER untuk melewati **1 file itu saja** (dicatat sebagai
   gagal, lihat bagian 5).

**Keterbatasan**: deteksi ini bergantung pada driver printer melaporkan status ke
Windows Print Spooler. Printer label/thermal tertentu yang mencetak langsung tanpa
melapor balik mungkin **tidak** melaporkan status ini sama sekali — kalau begitu
program tetap jalan tanpa pemantauan otomatis (ada peringatan di log/layar saat
mulai), dan daftar berhasil/gagal (bagian 5) jadi jaring pengaman untuk kasus itu.

## 5. Log & daftar gagal

- **Log tiap file**: setiap file yang diproses (berhasil, gagal, atau dilewati)
  dicatat ke `logs/cetak_YYYY-MM.log` (format sama seperti `logs/run_YYYY-MM.log`
  di `main.py`) sekaligus ditampilkan di layar.
- **Kalau ada yang gagal**: setelah semua file selesai diproses, daftar nama file
  yang gagal/dilewati disimpan ke `logs/gagal_cetak_<tanggal>_<jam>.txt` (satu path
  file per baris), dan program langsung menawarkan mencetak **ULANG hanya file yang
  gagal itu** (Y/N) — bisa langsung saat itu juga, atau belakangan lewat
  `--ulang "logs\gagal_cetak_....txt"`.
- Proses ulang (`--ulang` maupun tawaran langsung) bisa diulang berkali-kali kalau
  masih ada yang gagal lagi, sampai semua berhasil atau user memilih berhenti.

## 6. Troubleshooting

| Masalah | Penyebab umum | Solusi |
|---|---|---|
| `SumatraPDF.exe tidak ditemukan` | Belum install, atau terpasang di lokasi tidak standar | Install ulang (bagian 2.1) atau set `SUMATRA_PDF_PATH` (bagian 2.3) |
| `Tidak ada printer terhubung ke komputer ini` | Printer belum ditambahkan di Windows (Settings → Printers & scanners), atau driver belum terpasang | Pasang/hubungkan printer dulu di Windows sebelum menjalankan program |
| `Tidak ada folder sesi (YYYY-MM-DD/N)` | Belum ada label yang dibuat lewat alur `--label` hari itu | Jalankan alur SKU spesial (`jalankan.bat --label --jalankan`) dulu sampai label PDF terbentuk |
| Program tidak tahu kertas habis sampai dicek manual | Printer tidak melapor status ke Windows Print Spooler (lihat bagian 4) | Pantau fisik printer saat sesi cetak besar; andalkan daftar gagal (bagian 5) sebagai jaring pengaman |
