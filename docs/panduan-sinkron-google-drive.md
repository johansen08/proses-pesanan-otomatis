# Panduan sinkron Google Drive: PC kantor ↔ laptop malam

Untuk skenario: PC kantor dipakai 07.00-17.00, laptop dipakai malam (20.00, 22.00, 24.00), dan
data hasil kerja harus ikut berpindah. Gratis dengan akun Google biasa (15 GB).

**Prinsip pembagian:**

| Bagian | Cara sinkron |
|---|---|
| Kode (`src/`, `bat/`, `docs/`, `tests/`) | Git (`git pull` / `git push`) |
| Data kerja: `logs/`, `label-pengiriman/`, `data/riwayat_picklist.xlsx` | Google Drive |
| TIDAK disinkronkan | `.venv/`, `.env`, `data/operator.json`, `data/laporan-*` (unduhan sementara) |

Program tidak perlu diubah: folder `logs/` dan `label-pengiriman/` di project cukup menjadi
*junction* (pintasan folder) ke folder yang ada di dalam Google Drive.

Pakai **satu akun Google yang sama** di kedua perangkat.

---

## A. Di PC kantor (sekali saja)

1. Pasang **Google Drive for desktop** (drive.google.com/drive/download), login.
2. Pengaturan Drive → *Preferences* → *Google Drive* → pilih **Mirror files** (bukan Stream),
   supaya file benar-benar ada di disk. Catat lokasi folder Drive-nya, mis.
   `C:\Users\User\My Drive` (di bawah dipakai sebagai `$drive`; sesuaikan).
3. **Tutup semua program** (UI, `.bat`, Excel yang membuka `PICKLIST.xlsx`).
4. Buka PowerShell di folder project, lalu pindahkan data ke Drive dan buat pintasannya:

```powershell
$drive = "C:\Users\User\My Drive"          # sesuaikan
$tujuan = "$drive\proses-pesanan-data"
New-Item -ItemType Directory -Force $tujuan | Out-Null

foreach ($f in "logs", "label-pengiriman") {
    Move-Item ".\$f" "$tujuan\$f"           # pindah, bukan salin
    cmd /c mklink /J ".\$f" "$tujuan\$f"    # pintasan di project -> folder di Drive
}
# riwayat_picklist.xlsx adalah FILE: butuh symlink (aktifkan Developer Mode di
# Settings > System > For developers, atau jalankan PowerShell sebagai Administrator)
Move-Item .\data\riwayat_picklist.xlsx "$tujuan\riwayat_picklist.xlsx"
cmd /c mklink ".\data\riwayat_picklist.xlsx" "$tujuan\riwayat_picklist.xlsx"
```

5. Isi `.env` dengan nama perangkat (baris baru):

```
PERANGKAT=PC-KANTOR
```

6. Tunggu ikon Drive di tray selesai mengunggah (centang hijau / "Sync complete"). Folder
   `label-pengiriman` yang lama bisa besar, jadi upload pertama mungkin lama.
7. Cek: `bat\jalankan.bat --cek-sinkron` harus menampilkan status kunci dan "Tidak ada file konflik".

> Folder `$tujuan` yang berisi data harus **nyata di dalam Drive**; pintasan (junction) ada di
> sisi project. Jangan dibalik: Drive tidak mengikuti pintasan ke luar folder Drive.

---

## B. Di laptop (sekali saja)

1. Pasang Git & Python, lalu ikuti [instalasi.md](instalasi.md): clone repo, buat `.venv`,
   `pip install -r requirements.txt`, salin `.env` (isi Jubelio/IRESIS sama dengan PC).
2. Tambahkan di `.env` laptop: `PERANGKAT=LAPTOP-MALAM`.
3. Pasang Google Drive for desktop, login dengan akun yang sama, pilih **Mirror files**, dan
   **tunggu folder `proses-pesanan-data` selesai terunduh penuh**.
4. Kalau di project laptop sudah ada folder `logs` / `label-pengiriman` kosong, hapus dulu
   (pastikan memang kosong), lalu buat pintasan:

```powershell
$drive = "C:\Users\<nama-laptop>\My Drive"   # sesuaikan
$tujuan = "$drive\proses-pesanan-data"

foreach ($f in "logs", "label-pengiriman") {
    cmd /c mklink /J ".\$f" "$tujuan\$f"
}
cmd /c mklink ".\data\riwayat_picklist.xlsx" "$tujuan\riwayat_picklist.xlsx"
```

5. Atur laptop supaya tidak tidur saat dicolok listrik (Settings → Power → Screen and sleep →
   Sleep: Never) selama jam kerja malam.
6. Pilih operator malam: `bat\jalankan.bat --operator NAMA` (file `data/operator.json` per
   perangkat, tidak ikut sinkron).
7. Cek: `bat\jalankan.bat --cek-sinkron`.

---

## C. Rutinitas serah-terima harian

**PC kantor → laptop (±17.00 → 20.00)**
1. Pastikan proses terakhir selesai, tutup `PICKLIST.xlsx` kalau terbuka di Excel.
2. Tunggu ikon Drive di PC **selesai sinkron** (centang hijau), baru matikan PC.
3. Di laptop, buka Drive dan tunggu selesai sinkron **sebelum** menjalankan program.
4. Jalankan `bat\jalankan.bat --cek-sinkron`. Lanjut hanya kalau kunci BEBAS dan tidak ada konflik.

**Laptop → PC kantor (±24.00 → 07.00)**
1. Setelah proses terakhir, biarkan laptop menyala sampai Drive selesai mengunggah.
2. Pagi hari, di PC: tunggu Drive selesai mengunduh, jalankan `--cek-sinkron`, baru mulai.
3. Kalau kode berubah (kamu commit dari salah satu perangkat): `git pull` di perangkat lainnya.

Program memakai **kunci serah-terima** (`logs/serah_terima.json`): proses ditolak kalau perangkat
lain masih memegang kunci, dan memberi peringatan kalau perangkat lain baru selesai < 10 menit
lalu (sinkron mungkin belum tiba). Detail: bagian `serah_terima.py` di `CLAUDE.md`.

---

## D. Kalau ada masalah

| Gejala | Penyebab / tindakan |
|---|---|
| "KUNCI SERAH-TERIMA dipegang perangkat X" | Tunggu X selesai & sinkron. Kalau X pasti sudah berhenti (mati mendadak): tunggu 3 jam (kunci basi otomatis) atau tambah `--abaikan-kunci`. |
| Peringatan "file salinan KONFLIK" | Dua perangkat mengubah file yang sama. Buka kedua file, pertahankan yang benar (biasanya yang paling baru/terlengkap), hapus salinannya. Untuk `sudah_dicetak.txt` / `picklist_terakhir.txt`, gabungkan barisnya. |
| `PICKLIST.xlsx` tidak tersinkron | File masih terbuka di Excel (terkunci). Tutup Excel. |
| Peringatan nomor picklist terlompat di laptop | Biasanya picklist pertama laptop setelah serah-terima; kalau data sinkron sudah lengkap tidak muncul. |
| Drive penuh (15 GB) | Pindahkan folder sesi lama ke luar Drive (di bawah). |
| Drive menampilkan "Stream" / file tidak lengkap | Ubah ke **Mirror files**, tunggu unduhan selesai. |

**Arsipkan sesi lama** (pindah ke luar Drive, mis. > 14 hari; `-WhatIf` dulu untuk melihat
daftar tanpa memindahkan):

```powershell
$arsip = "D:\arsip-label"                    # di luar folder Drive
New-Item -ItemType Directory -Force $arsip | Out-Null
Get-ChildItem .\label-pengiriman -Directory |
    Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' -and [datetime]$_.Name -lt (Get-Date).AddDays(-14) } |
    Move-Item -Destination $arsip -WhatIf
```

Hapus `-WhatIf` setelah daftarnya benar. Cetak ulang dan `--semua-sesi` hanya membutuhkan sesi
beberapa hari terakhir, jadi arsip lama aman dipindah.

Cek ukuran data kapan saja:

```powershell
"{0:N0} MB" -f ((Get-ChildItem .\label-pengiriman -Recurse -File | Measure-Object Length -Sum).Sum / 1MB)
```

## E. Batasan yang perlu diingat

- Kunci hanya terlihat oleh perangkat lain **setelah tersinkron**. Selalu tunggu indikator Drive
  selesai di kedua sisi sebelum berganti perangkat.
- Jangan menjalankan program di dua perangkat bersamaan, apa pun yang ditampilkan Drive.
- Kalau internet mati di salah satu perangkat, perubahan baru tersinkron setelah online lagi:
  tunda serah-terima sampai ikon Drive hijau.
