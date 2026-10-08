# Cetak Bulk Label (SumatraPDF)

Panduan lengkap fitur **cetak bulk label** (`cetak-label-spesial.bat` /
`cetak-label-gtl-sicepat.bat` / `cetak-label-satuan.bat` / `cetak-label-kombinasi.bat`,
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
| `gtl-sicepat` | `cetak-label-gtl-sicepat.bat` | `URGENT` (tanpa varian kurir) — hanya file `GTL-SICEPAT-*` | `--urgent --channel gtl-sicepat` (Alur 2) |
| `satuan` | `cetak-label-satuan.bat` | `SATUAN`, `JNT_SATUAN`, `SPX_SATUAN` — semua PDF | `--reguler --bagian 1qty` (Alur 3) |
| `spesial-jnt` / `spesial-spx` | `cetak-label-spesial-jnt.bat` / `-spx.bat` | `JNT_SPESIAL` / `SPX_SPESIAL` saja (TIPE 2 & 3) | `--label --kurir jnt/spx` |
| `satuan-jnt` / `satuan-spx` | `cetak-label-satuan-jnt.bat` / `-spx.bat` | `JNT_SATUAN` / `SPX_SATUAN` saja | `--reguler --bagian 1qty --kurir jnt/spx` |
| `kombinasi-jnt` / `kombinasi-spx` | `cetak-label-kombinasi-jnt.bat` / `-spx.bat` | `JNT_KOMBINASI` / `SPX_KOMBINASI` saja | `--reguler --bagian kombinasi --kurir jnt/spx` |
| `spx-pagi` | `cetak-label-spx-pagi.bat` | `SPX_PAGI` (Shopee Pagi, `SHOPEE-PAGI-LANTAI*`) — sesi lama (sebelum 2026-10-07) masih di root folder sesi, tidak ikut | `--shopee-pagi` |
| `jnt-siang` | `cetak-label-jnt-siang.bat` | `JNT_SIANG` (`JNT-SIANG-LANTAI*`) — sesi lama tidak ikut | `--jnt-siang` |
| `kombinasi` | `cetak-label-kombinasi.bat` | `KOMBINASI`, `JNT_KOMBINASI`, `SPX_KOMBINASI` — semua PDF | `--reguler --bagian kombinasi` (Alur 3) |

**Mode event** (`proses-event.bat`, hari 10.10 / 11.11 / 12.12 dst — lihat
[jadwal-proses.md](jadwal-proses.md)) punya jenis sendiri; jenis gabungan di atas (`spesial`,
`satuan`, `kombinasi`) **tidak** ikut mencetak folder event. J&T mode event memakai jenis
`*-jnt` yang sudah ada (foldernya sama dengan harian).

| Jenis (`--jenis`) | `.bat` | Subfolder dicari | Dibuat alur |
|---|---|---|---|
| `spesial-spx-hemat` / `satuan-spx-hemat` / `kombinasi-spx-hemat` | `cetak-label-spesial-spx-hemat.bat` dst | `SPXHEMAT_SPESIAL` / `SPXHEMAT_SATUAN` / `SPXHEMAT_KOMBINASI` | `--event --kurir spx-hemat` |
| `spesial-spx-hemat-pagi` / `satuan-spx-hemat-pagi` / `kombinasi-spx-hemat-pagi` | `cetak-label-spesial-spx-hemat-pagi.bat` dst | `SPXHEMATPAGI_SPESIAL` / `SPXHEMATPAGI_SATUAN` / `SPXHEMATPAGI_KOMBINASI` | `--event --kurir spx-hemat-pagi` (Shopee Pagi, s.d. 12:00) |
| `spx-standard` | `cetak-label-spx-standard.bat` | `SPX_STANDARD` (`SPX-STANDARD-LANTAI*`) — semua PDF | `--spx-standard` |
| `spx-pagi` (sudah ada) | `cetak-label-spx-pagi.bat` | `SPX_PAGI` — di mode event juga berisi `SHOPEE-PAGI-SPX-STANDARD-LANTAI*` | `--spx-standard --pagi` |

`tests/test_print_spesial.py` menjaga agar setiap jenis punya tepat satu `.bat` cetak dan agar
nama folder yang ditulis `proses_label.py` selalu sama dengan yang dicari `print_spesial.py`.

Untuk jenis `satuan`/`kombinasi`, nama file labelnya variatif (mis. `1QTY-REGULER-2A`,
`KOMBINASI-REGULER-LANTAI2`) dan TIDAK punya tag unik seperti `_SPESIAL_` — karena
subfolder-nya sendiri sudah eksklusif per jenis (dibuat `proses_label.py` khusus alur itu),
**semua PDF** di subfolder itu ikut dicetak, tanpa filter nama tambahan.

Jenis `gtl-sicepat` (dulu `urgent`) memakai subfolder `URGENT` yang dipakai bersama label
**Lazada**, jadi ada saringan nama: hanya `PICK-..._GTL-SICEPAT-...` (LANTAI1/2/3/LAINNYA) yang
dicetak. **Label Lazada TIDAK ikut cetak bulk** — dicetak manual (skala custom 68% di kertas
100x150 mm, lihat `docs/analisa-alur-cetak-label.md` bagian 6). Pengecekan "nomor PICK
terlompat" tetap dihitung dari SEMUA PDF di `URGENT` (termasuk Lazada), supaya picklist Lazada
di antara nomor GTL-SiCepat tidak salah dianggap hilang.

**Program ini TIDAK membuat picklist/label baru.** Fungsinya cuma mencetak ulang
PDF label yang sudah ada. Picklist & label itu sendiri dibuat lewat alur
`--label`/`--urgent`/`--reguler` (lihat README bagian 1-3).

## 2. Download & setup SumatraPDF (sekali saja per PC)

Fitur ini **wajib** menggunakan [SumatraPDF](https://www.sumatrapdfreader.org/) —
pembaca PDF gratis & ringan yang dipakai di sini untuk mencetak PDF langsung dari
command line (`-print-to -silent`) tanpa jendela PDF reader terbuka satu per satu
untuk tiap label. Setup ini berlaku untuk KEEMPAT jenis (`spesial`/`gtl-sicepat`/
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
cetak-label-gtl-sicepat.bat
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

Berlaku sama untuk keempat `.bat` (contoh pakai `cetak-label-gtl-sicepat.bat`, ganti
nama `.bat`-nya sesuai jenis yang mau dicetak):

| Perintah | Kegunaan |
|---|---|
| `cetak-label-gtl-sicepat.bat --folder "label-pengiriman\2026-10-01\3"` | Pakai folder sesi tertentu, bukan yang terbaru (mis. mau cetak ulang sesi sebelumnya) |
| `cetak-label-gtl-sicepat.bat --tanpa-konfirmasi` | Lewati tanya Y/N sebelum mulai cetak (tetap tanya pilih printer) |
| `cetak-label-gtl-sicepat.bat --ulang "logs\gagal_cetak_2026-10-01_153000.txt"` | Cetak ULANG hanya file dari daftar gagal sebelumnya (lihat bagian 4), tanpa mencari ulang folder sesi |

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

## Label yang sudah tercetak & nomor PICK terlompat (revisi 2026-10-07)

- **Tidak tercetak dobel**: tiap label yang berhasil dicetak dicatat di `logs/sudah_dicetak.txt`
  (path absolut). Cetak berikutnya (folder sesi sama dipakai banyak TIPE) melewatinya dan
  hanya mencetak yang baru. Tambahkan `--cetak-ulang-semua` untuk mencetak ulang semuanya,
  atau hapus baris/file catatannya untuk mencetak ulang sebagian.
- **Nomor PICK terlompat** kini hanya menghitung nomor yang tidak ada di MANA PUN di folder
  sesi (semua subfolder/jenis/kurir). Nomor yang "bolong" karena milik J&T/SPX/jenis lain
  tidak lagi memicu peringatan palsu.
- **Shopee Pagi** (`--shopee-pagi`) kini hanya mengambil kurir **SPX** (`KURIR_FILTER_SHOPEE_PAGI`).
