# Cetak Bulk Label (SumatraPDF)

Panduan lengkap fitur **cetak bulk label** (`cetak-label-spesial.bat` /
`cetak-label-urgent.bat` / `cetak-label-satuan.bat` / `cetak-label-kombinasi.bat`,
semuanya menjalankan `src/print_spesial.py --jenis <jenis>`): cara install
SumatraPDF (syarat wajib fitur ini) dan cara pakai fiturnya sehari-hari.

## 1. Apa fitur ini

Mencetak ulang semua label pengiriman yang sudah ada di subfolder tertentu folder
sesi `label-pengiriman/<tanggal>/<sesi>/`, secara **bulk dan berurut** (nomor PICK
terkecil/paling dulu dibuat, duluan dicetak), langsung ke printer pilihan, tanpa
perlu buka file PDF satu-satu secara manual. Ada 4 jenis, masing-masing `.bat`
sendiri:

| Jenis (`--jenis`) | `.bat` | Subfolder dicari | Dibuat alur |
|---|---|---|---|
| `spesial` | `cetak-label-spesial.bat` | `SPESIAL`, `JNT_SPESIAL`, `SPX_SPESIAL` — hanya file bertanda `_SPESIAL_` | `--label` (Alur 1, SKU spesial) |
| `urgent` | `cetak-label-urgent.bat` | `URGENT` (tanpa varian kurir) — semua PDF | `--urgent` (Alur 2, Lazada & GTL-SiCepat) |
| `satuan` | `cetak-label-satuan.bat` | `SATUAN`, `JNT_SATUAN`, `SPX_SATUAN` — semua PDF | `--reguler --bagian 1qty` (Alur 3) |
| `kombinasi` | `cetak-label-kombinasi.bat` | `KOMBINASI`, `JNT_KOMBINASI`, `SPX_KOMBINASI` — semua PDF | `--reguler --bagian kombinasi` (Alur 3) |

Untuk jenis `urgent`/`satuan`/`kombinasi`, nama file labelnya variatif (mis.
`Lazada`, `GTL-SiCepat-LANTAI1`, `1QTY-REGULER-2A`, `KOMBINASI-REGULER-LANTAI2`) dan
TIDAK punya tag unik seperti `_SPESIAL_` — karena subfolder-nya sendiri sudah
eksklusif per jenis (dibuat `proses_label.py` khusus alur itu), **semua PDF** di
subfolder itu ikut dicetak, tanpa filter nama tambahan.

Label **Lazada** sudah berukuran 100x150 mm (diperkecil ke skala 68% dari template A5 saat
diunduh, lihat `docs/analisa-alur-cetak-label.md` bagian 6) — jadi cetak bulk cukup memakai
kertas label 100x150 mm tanpa pengaturan skala tambahan di printer. File Lazada yang
diunduh SEBELUM perbaikan 2026-10-07 masih template umum/ukuran lama.

**Program ini TIDAK membuat picklist/label baru.** Fungsinya cuma mencetak ulang
PDF label yang sudah ada. Picklist & label itu sendiri dibuat lewat alur
`--label`/`--urgent`/`--reguler` (lihat README bagian 1-3).

## 2. Download & setup SumatraPDF (sekali saja per PC)

Fitur ini **wajib** menggunakan [SumatraPDF](https://www.sumatrapdfreader.org/) —
pembaca PDF gratis & ringan yang dipakai di sini untuk mencetak PDF langsung dari
command line (`-print-to -silent`) tanpa jendela PDF reader terbuka satu per satu
untuk tiap label. Setup ini berlaku untuk KEEMPAT jenis (`spesial`/`urgent`/
`satuan`/`kombinasi`) — sekali install, dipakai semua `.bat` cetak bulk.

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
tambahan. Cek dengan menjalankan salah satu `.bat` cetak bulk (mis.
`cetak-label-spesial.bat`) — kalau SumatraPDF **tidak** ditemukan, program berhenti
dengan pesan:

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

Buka terminal/PC baru (atau klik 2x ulang `.bat` cetak bulk setelah restart) supaya
environment variable baru terbaca.

## 3. Cara pakai

Pilih `.bat` sesuai jenis label yang mau dicetak (lihat tabel bagian 1):

```bash
cetak-label-spesial.bat
cetak-label-urgent.bat
cetak-label-satuan.bat
cetak-label-kombinasi.bat
```

Urutan kerja program (sama untuk keempat jenis):

1. Cari folder sesi `label-pengiriman/YYYY-MM-DD/N` **terbaru** secara otomatis
   (dibandingkan dari tanggal lalu nomor urut sesi di nama folder, bukan dari waktu
   modifikasi file).
2. Cari file PDF di subfolder jenis itu (lihat tabel bagian 1) di folder sesi itu.
3. Tampilkan daftar printer yang terhubung ke komputer (lewat `Get-Printer`
   PowerShell) — pilih nomor printer.
4. Konfirmasi (Y/N) sebelum mulai cetak.
5. Cetak satu per satu secara **berurut** (nomor PICK terkecil dulu).

### Pilihan tambahan

Berlaku sama untuk keempat `.bat` (contoh pakai `cetak-label-urgent.bat`, ganti
nama `.bat`-nya sesuai jenis yang mau dicetak):

| Perintah | Kegunaan |
|---|---|
| `cetak-label-urgent.bat --folder "label-pengiriman\2026-10-01\3"` | Pakai folder sesi tertentu, bukan yang terbaru (mis. mau cetak ulang sesi sebelumnya) |
| `cetak-label-urgent.bat --tanpa-konfirmasi` | Lewati tanya Y/N sebelum mulai cetak (tetap tanya pilih printer) |
| `cetak-label-urgent.bat --ulang "logs\gagal_cetak_2026-10-01_153000.txt"` | Cetak ULANG hanya file dari daftar gagal sebelumnya (lihat bagian 4), tanpa mencari ulang folder sesi |

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
  di `main.py`) sekaligus ditampilkan di layar — log ini DIBAGI bersama untuk
  keempat jenis (tidak dipisah per jenis).
- **Kalau ada yang gagal**: setelah semua file selesai diproses, daftar nama file
  yang gagal/dilewati disimpan ke `logs/gagal_cetak_<tanggal>_<jam>.txt` (satu path
  file per baris), dan program langsung menawarkan mencetak **ULANG hanya file yang
  gagal itu** (Y/N) — bisa langsung saat itu juga, atau belakangan lewat
  `--ulang "logs\gagal_cetak_....txt"` (lewat `.bat` jenis yang sama).
- Proses ulang (`--ulang` maupun tawaran langsung) bisa diulang berkali-kali kalau
  masih ada yang gagal lagi, sampai semua berhasil atau user memilih berhenti.

## 6. Troubleshooting

| Masalah | Penyebab umum | Solusi |
|---|---|---|
| `SumatraPDF.exe tidak ditemukan` | Belum install, atau terpasang di lokasi tidak standar | Install ulang (bagian 2.1) atau set `SUMATRA_PDF_PATH` (bagian 2.3) |
| `Tidak ada printer terhubung ke komputer ini` | Printer belum ditambahkan di Windows (Settings → Printers & scanners), atau driver belum terpasang | Pasang/hubungkan printer dulu di Windows sebelum menjalankan program |
| `Tidak ada folder sesi (YYYY-MM-DD/N)` | Belum ada label yang dibuat hari itu lewat alur terkait | Jalankan alur yang sesuai (`--label`/`--urgent`/`--reguler --jalankan`) dulu sampai label PDF terbentuk |
| `Tidak ada label <JENIS> di folder ini.` | Folder sesi ada, tapi tidak ada label jenis itu (mis. tidak ada pesanan urgent hari itu) | Normal, bukan error — cek jenis/folder sesi yang dimaksud sudah benar |
| Program tidak tahu kertas habis sampai dicek manual | Printer tidak melapor status ke Windows Print Spooler (lihat bagian 4) | Pantau fisik printer saat sesi cetak besar; andalkan daftar gagal (bagian 5) sebagai jaring pengaman |
