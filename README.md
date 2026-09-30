# Proses Pesanan Otomatis — SKU Spesial

Download **Laporan Siap Proses** dari Jubelio → hitung SKU spesial → PDF (tanggal, jam, tabel).

Dengan `--label --jalankan`, program membuat picklist sungguhan di Jubelio lewat 2 alur
berurutan (otomatis, satu kali jalan):

1. **Picklist SKU spesial** — per SKU, dari daftar kandidat di Excel. PDF SKU spesial dibuat
   di sini, setelah proses ini selesai (bukan sebelumnya), dari jumlah pesanan aktual.
2. **Picklist sisa reguler** (TikTok Shop & Shopee, bukan SKU spesial) — dibuat setelah SKU
   spesial selesai (perlu tahu SKU mana yang sudah spesial dulu), dipecah 1 Qty Reguler &
   Kombinasi Reguler.

**Picklist urgent** (channel Lazada, kurir GTL/SiCepat lintas channel) **BUKAN** bagian dari
`--label --jalankan` — harus dijalankan **terpisah**, lewat `--urgent`, sebelum atau sesudah
menu SKU spesial/reguler sesuai kebutuhan. Ketiganya (`--urgent`, `--label`, `--reguler`) juga
bisa dijalankan berdiri sendiri — lihat bagian masing-masing di bawah.

Di luar alur lengkap itu, ada **Picklist SPX Resi Pagi** (`--shopee-pagi`) — **bukan** bagian
`--label --jalankan`, dijalankan manual 1x sehari (mis. jam 13:00): channel Shopee saja,
pesanan yang jam pesannya (WIB) maksimal jam 12:00 siang hari ini. Lihat bagian 4 di bawah.

**Pemisahan J&T/SPX (`--kurir`)**: `--label` dan `--reguler` menerima opsi `--kurir jnt` /
`--kurir spx` supaya J&T dan SPX jadi picklist **terpisah** saat pembuatan, bukan digabung.
Tanpa `--kurir` (default), J&T dan SPX tetap digabung seperti semula. Penentuan SKU mana yang
"spesial" (dari Excel, `hitung_sku_spesial`) **selalu** menggabung J&T+SPX — `--kurir` cuma
membatasi resi mana yang benar-benar dipicklist saat itu. Dipakai `menu.bat` sesi **JAM 13.00**
dan **SESI SORE** (lihat `menu.bat`/[JADWAL-PROSES.md](JADWAL-PROSES.md)); sesi **SESI PAGI**
tetap menggabung J&T+SPX seperti sebelumnya.

Aturan SKU spesial dan data uji: lihat [panduan-sku-spesial.md](panduan-sku-spesial.md)
(kode di bagian 8 panduan adalah versi awal; kode yang dipakai adalah file `.py` di folder ini).

## File

| File | Isi |
|---|---|
| `main.py` | Alur CLI: login → download Excel → hitung → (SKU spesial + PDF) → (reguler). `--urgent`/`--reguler`/`--shopee-pagi` adalah alur terpisah (tidak lewat langkah ini). Lihat `--help` untuk semua opsi |
| `jubelio.py` | Login API Jubelio, download Excel laporan, ambil nilai pesanan (tanpa browser) |
| `sku_spesial.py` | Baca Excel, hitung SKU spesial, buat PDF |
| `proses_label.py` | Picklist → picking → resi → label PDF (SKU spesial per SKU, urgent/reguler/Shopee Pagi per channel), catat riwayat |
| `run.bat` | Menjalankan `main.py` dengan Python di `.venv` |
| `menu.bat` | Menu interaktif SUNGGUHAN (klik 2x), 3 sesi + Keluar: SESI PAGI, JAM 13.00, SESI SORE — tiap sesi menjalankan urutan langkahnya sendiri (lihat [JADWAL-PROSES.md](JADWAL-PROSES.md)) dalam satu kali konfirmasi Y/N |
| `uji.bat` | Menu interaktif MODE UJI (klik 2x), struktur sama seperti `menu.bat` - tidak ada perubahan di Jubelio |
| `.env` | Email & password Jubelio (`JUBELIO_EMAIL`, `JUBELIO_PASSWORD`) |
| `sniff/` | Perekam alur Jubelio (`run_sniff_jubel.bat`) untuk analisa jika Jubelio berubah |

Hasil: Excel di `excel/`, PDF di `laporan/`, label per picklist di `label/`, log di `logs/`,
riwayat semua picklist (SKU spesial, urgent, reguler) di `riwayat_picklist.xlsx`.

## Instalasi (sekali saja)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Buat file `.env` berisi `JUBELIO_EMAIL` dan `JUBELIO_PASSWORD` (lihat contoh isi di
`.env` yang sudah ada, atau [INSTALASI.md](INSTALASI.md) bagian 5 kalau mulai dari nol —
tidak ada file `.env.example` di proyek ini).

Pindah ke PC lain? Lihat panduan lengkap di [INSTALASI.md](INSTALASI.md) (versi
Python, semua library yang perlu di-install, dan konfigurasi `.env`).

Jadwal operasional harian tim resi (jam berapa menu apa dijalankan, plus
rencana pengembangan ke depan): lihat [JADWAL-PROSES.md](JADWAL-PROSES.md).

## Menjalankan

```bash
run.bat
```

Pilihan:

- `run.bat --excel "C:\path\file.xlsx"` — lewati download, proses file yang sudah ada
  (nilai pesanan tetap dicek ke API).
- `run.bat --excel "C:\path\file.xlsx" --tanpa-cek-nilai` — tanpa akses API sama sekali;
  pesanan kreator (nilai 0) **tidak** dikeluarkan.

Pesanan kreator (nilai pesanan 0) dikeluarkan dari hitungan spesial. Nilainya diambil dari
API daftar pesanan "Siap Proses" karena Excel tidak punya kolom nilai. Jumlah resi yang
dikeluarkan dicatat di log. Resi yang nilainya tidak ditemukan di API juga dikeluarkan.

Cara download (dari rekaman sniff): URL laporan dari API `ready-to-pick-list` diubah path-nya
dari `/` menjadi `/xlsx/`, lalu diunduh langsung dengan cookie `JB_OMNI_ACCESS_TOKEN` = token login.
Jika suatu saat Jubelio mengubah alurnya dan download gagal, rekam ulang dengan
`sniff\run_sniff_jubel.bat`.

## 1. Picklist urgent (`--urgent`)

**Alur berdiri sendiri, BUKAN bagian dari `--label --jalankan`** (lihat catatan di bawah).
Gabungkan pesanan Siap Proses lintas SKU jadi picklist sebanyak mungkin (maks
200 pesanan/picklist, dipecah kalau lebih), lalu diproses SAMPAI label PDF juga (picking
diselesaikan, resi diminta, label diunduh — sama seperti alur SKU spesial). 2 skenario:

**Resi terlama diambil duluan**: pesanan diurutkan `transaction_date` **ASC** (terlama dulu,
bukan terbaru dulu), jadi kalau totalnya > 200 dan dipecah beberapa picklist, resi yang lebih
lama (mis. sudah dipesan sejak sebelum jam 12 tapi baru diproses jam 1 siang) selalu masuk
picklist **pertama**, bukan tertahan di picklist belakangan. Berlaku juga di picklist sisa
reguler (bagian 3 di bawah), sama-sama lewat `ambil_pesanan_channel()`.

- **Lazada**: semua pesanan channel Lazada (`channel_id=4`).
- **GTL-SiCepat**: semua pesanan kurir **GTL** atau **SiCepat**, **lintas channel** (TIDAK
  difilter channel). Urgent-nya ditentukan kurir, bukan channel, jadi pesanan Tokopedia
  **asli** (`channel_id=128`) *dan* "Shop | Tokopedia" (`channel_id=131076`, nama lain TikTok
  Shop di Jubelio) dengan kurir itu sama-sama ikut.

**Tidak dijalankan otomatis oleh `--label --jalankan`.** Harus dipicu manual, terpisah, lewat
`--urgent` (mis. sebelum menjalankan menu SKU spesial/reguler, supaya pesanan yang sudah
"diambil" urgent tidak ikut terhitung sebagai kandidat SKU spesial — tapi ini tanggung jawab
tim/jadwal, bukan otomatis di kode). Jalankan salah satu atau kedua skenario:

```bash
run.bat --urgent                                      # mode uji (keduanya)
run.bat --urgent --channel lazada --jalankan           # Lazada saja, sungguhan
run.bat --urgent --channel gtl-sicepat --jalankan      # GTL/SiCepat saja, sungguhan
```

Dijalankan sebagai langkah pertama & kedua di setiap sesi `menu.bat` (SESI PAGI, JAM 13.00,
SESI SORE) = `run.bat --urgent --channel lazada --jalankan` lalu
`run.bat --urgent --channel gtl-sicepat --jalankan`. `uji.bat` = versi mode uji
(tanpa `--jalankan`) masing-masing channel.

- Label PDF urgent: nama file & kolom SKU di riwayat pakai nama skenario (huruf besar),
  bukan SKU — mis. `label/PICK-000155230_LAZADA_2026-09-29_150512.pdf`,
  `label/PICK-000155231_GTL-SICEPAT_2026-09-29_150612.pdf`. Tercatat juga di
  `riwayat_picklist.xlsx` dengan kolom SKU berisi `LAZADA` / `GTL-SICEPAT`.

## 2. Proses SKU spesial sampai label pengiriman (`--label`, `proses_label.py`)

**Langkah pertama** dari alur `--label --jalankan` (sebelum picklist sisa reguler — picklist
urgent **tidak** termasuk, lihat catatan di bagian 1): per SKU dibuat picklist, picking
diselesaikan, resi diminta, lalu label PDF diunduh. Detail alur:
[analisa-alur-cetak-label.md](analisa-alur-cetak-label.md).

**Tanpa `--jalankan` selalu mode uji**: hanya membaca data Jubelio dan menampilkan pesanan yang
akan diproses / dibuang beserta alasannya. Tidak ada yang berubah di Jubelio.

```bash
run.bat --label
run.bat --label --sku T01-BSBI-5
run.bat --label --sku T01-BSBI-5 --jalankan
run.bat --label --jalankan
run.bat --label --tanpa-reguler --jalankan
run.bat --label --kurir jnt --tanpa-reguler --jalankan    # J&T saja (JAM 13.00/SESI SORE)
run.bat --label --kurir spx --tanpa-reguler --jalankan    # SPX saja (JAM 13.00/SESI SORE)
run.bat --lanjut PICK-000154839 --jalankan
```

Urutan pakai: (1) mode uji semua SKU, (2) mode uji satu SKU, (3) jalankan sungguhan untuk
**satu SKU** dan cek hasilnya di web Jubelio, (4) baru semua SKU. `--lanjut` dipakai untuk
picklist yang prosesnya terhenti di tengah. **Catatan**: `--sku` melewatkan langkah picklist
reguler otomatis (lihat bagian 3) karena perlu daftar SKU spesial yang lengkap, bukan
sebagian (picklist urgent tidak terpengaruh — memang tidak pernah otomatis, lihat bagian 1).
`--tanpa-reguler` melewatkan langkah yang sama tapi tetap memproses SEMUA SKU spesial (dipakai
menu "SPX - J&T SPESIAL"/"J&T SPESIAL"/"SPX SPESIAL" supaya picklist sisa reguler diproses
terpisah lewat `--reguler`, lihat bagian 3). `--kurir jnt`/`--kurir spx` membatasi picklist ke
1 kurir saja (lihat catatan "Pemisahan J&T/SPX" di atas) — daftar SKU yang dianggap "spesial"
tidak berubah, cuma resi kurir lain yang tidak ikut dipicklist saat itu.

SKU selalu diproses berurutan per `No Rak` (sama dengan urutan di PDF daftar). Di akhir log
tampil ringkasan per SKU beserta durasinya, lama pembuatan daftar resi spesial, lama proses
semua SKU, rata-rata per SKU, dan total waktu.

**PDF baru dibuat SETELAH proses SKU spesial selesai** (bukan sebelumnya), dari jumlah
pesanan yang **benar-benar berhasil dipicklist** per SKU — bukan dari daftar kandidat awal.
Kalau ada SKU yang dilewati (pesanan tersisa < 3), gagal, atau sebagian pesanannya kena stok
kosong/invalidSO, PDF akan mencerminkan angka aktual itu, jadi total di PDF selalu sama
dengan yang benar-benar diproses. (Mode uji tetap memakai daftar kandidat, karena tidak ada
proses sungguhan yang bisa "aktual".)

`menu.bat` sesi SESI PAGI, langkah "SPX - J&T SPESIAL" = `run.bat --label --tanpa-reguler --jalankan`;
sesi JAM 13.00/SESI SORE, langkah "J&T SPESIAL"/"SPX SPESIAL" = `run.bat --label --kurir jnt
--tanpa-reguler --jalankan` / `run.bat --label --kurir spx --tanpa-reguler --jalankan`
(satu konfirmasi Y/N per sesi). `uji.bat` = versi mode uji (tanpa `--jalankan`) yang sama.

- Label PDF: `label/<PICK-no>_<SKU>_<tanggal>_<jam>.pdf`, mis. `PICK-000155085_BM-AKS27-1_2026-09-29_090947.pdf`
- Riwayat: `riwayat_picklist.xlsx` (Waktu, SKU, No Picklist, Total Pesanan, Resi Keluar,
  File Label, Catatan, Durasi). Jika file sedang dibuka di Excel, ditulis ke `riwayat_picklist.csv`.
- SKU dilewati jika pesanan tersisa < 3, stok kurang, pesanan dari lokasi berbeda,
  atau ada item selain SKU itu.
- Uji tanpa internet: `.venv\Scripts\python tests\test_proses_label.py`

## 3. Picklist sisa reguler (`--reguler`)

**Langkah kedua/terakhir** dari alur `--label --jalankan` — dibuat setelah SKU
spesial selesai diproses (picklist urgent tidak termasuk, lihat bagian 1). Sisa pesanan channel **TikTok Shop** ("Shop | Tokopedia"
di Jubelio, `channel_id=131076`) dan **Shopee** (`channel_id=64`) dengan kurir **J&T/SPX**
yang **bukan** bagian SKU spesial hari itu digabung jadi picklist, dipecah 2 bagian:

- **1 Qty Reguler**: 1 SKU, qty 1 (resi tunggal yang SKU-nya tidak mencapai syarat spesial).
- **Kombinasi Reguler**: sisanya — pesanan qty > 1 (multi-baris/multi-SKU atau 1 SKU qty > 1).

Resi yang sudah termasuk SKU spesial (dari `resi_per_sku` hasil `hitung_sku_spesial`)
dikeluarkan dari kedua bagian ini, supaya tidak dobel proses dengan picklist SKU spesial.
Sama seperti urgent: sebanyak mungkin per picklist (maks 200, dipecah kalau lebih), diproses
SAMPAI label PDF.

**Filter tipe pesanan**: kurir SPX dan channel Shopee sama-sama bisa menyertakan pesanan tipe
**pengiriman kilat**, yang tidak diproses lewat alur picklist ini. Karena skenario reguler di
atas selalu memakai kurir SPX (`KURIR_FILTER_REGULER`) dan channel Shopee (`CHANNEL_IDS_REGULER`),
`ambil_pesanan_channel()` otomatis menambahkan filter `order_type` (`TIPE_PESANAN_FILTER`,
mengeluarkan "kilat") begitu salah satu dari dua kondisi itu terpenuhi — berlaku juga kalau
nanti ada skenario lain yang memakai SPX atau Shopee.

`main.py --label --jalankan` otomatis menjalankan ini **SETELAH** SKU spesial selesai (kalau
tidak dibatasi `--sku`, karena daftar SKU spesial perlu lengkap dulu supaya pengecualiannya
benar). Bisa juga dijalankan terpisah, per bagian — ini tetap download & hitung Excel dulu
(read-only, tanpa proses SKU spesial) supaya tahu resi mana yang harus dikecualikan:

```bash
run.bat --reguler                                # mode uji (keduanya, digabung)
run.bat --reguler --bagian 1qty --jalankan        # 1 Qty Reguler saja, sungguhan (digabung)
run.bat --reguler --bagian kombinasi --jalankan   # Kombinasi Reguler saja, sungguhan (digabung)
run.bat --reguler --bagian 1qty --kurir jnt --jalankan       # J&T saja
run.bat --reguler --bagian kombinasi --kurir spx --jalankan  # SPX saja
```

`menu.bat` sesi SESI PAGI, langkah "SPX - J&T 1 QTY REGULER"/"SPX - J&T KOMBINASI" =
`run.bat --reguler --bagian 1qty --jalankan` / `run.bat --reguler --bagian kombinasi --jalankan`
(digabung). Sesi JAM 13.00/SESI SORE, langkah "J&T 1 QTY REGULER"/"J&T KOMBINASI"/"SPX 1 QTY
REGULER"/"SPX KOMBINASI" = perintah yang sama ditambah `--kurir jnt`/`--kurir spx`.
`uji.bat` = versi mode uji (tanpa `--jalankan`) yang sama. Kolom SKU di riwayat:
`1QTY-REGULER` / `KOMBINASI-REGULER` (digabung), atau `J&T-1QTY-REGULER` / `SPX-1QTY-REGULER`
/ `J&T-KOMBINASI-REGULER` / `SPX-KOMBINASI-REGULER` (dipisah lewat `--kurir`). Nama file PDF
tidak boleh memuat simbol `&` (dibuang otomatis), jadi khusus nama file J&T dituliskan `JNT`
tanpa simbol, mis. `label/PICK-000155300_1QTY-REGULER_...pdf` atau
`label/PICK-000155301_JNT-1QTY-REGULER_...pdf`.

Tiap sesi `menu.bat` (SESI PAGI, JAM 13.00, SESI SORE) menjalankan seluruh langkahnya secara
berurut dalam satu kali klik + satu konfirmasi Y/N — urutan lengkap tiap sesi ada di
[JADWAL-PROSES.md](JADWAL-PROSES.md).

## 4. Picklist SPX Resi Pagi (`--shopee-pagi`)

**Dijalankan MANUAL 1x sehari** (mis. jam 13:00) — **bukan** bagian alur otomatis
`--label --jalankan`, dan **tidak** perlu download/hitung Excel. Semua pesanan Siap Proses
channel **Shopee** saja (`channel_id=64`, tanpa filter kurir) yang jam pesannya (WIB)
**maksimal jam 12:00 siang hari ini**, digabung jadi 1 picklist (dipecah kalau > 200),
diproses SAMPAI label PDF juga.

```bash
run.bat --shopee-pagi               # mode uji
run.bat --shopee-pagi --jalankan    # sungguhan
```

`menu.bat` sesi JAM 13.00, langkah "SPX PAGI (RESI SHOPEE <= 12.00)" = `run.bat --shopee-pagi
--jalankan` (dijalankan cukup 1x sehari, jangan diulang di SESI SORE). `uji.bat` = versi mode
uji (tanpa `--jalankan`). Nama file & kolom SKU di riwayat: `SHOPEE-PAGI`, mis.
`label/PICK-000155400_SHOPEE-PAGI_...pdf`.

## Jadwal otomatis (Windows Task Scheduler)

*Create Basic Task* → pilih jadwal → *Start a program*:

- Program: `C:\proses-pesanan-otomatis\run.bat`
- Start in: `C:\proses-pesanan-otomatis`
