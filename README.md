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

Struktur folder & aturan penamaan file di project ini: lihat
[docs/standar-struktur-proyek.md](docs/standar-struktur-proyek.md).

Di luar alur lengkap itu, ada **Picklist SPX Resi Pagi** (`--shopee-pagi`) — **bukan** bagian
`--label --jalankan`, dijalankan manual 1x sehari (mis. jam 13:00): channel Shopee saja,
pesanan yang jam pesannya (WIB) maksimal jam 12:00 siang hari ini. Lihat bagian 4 di bawah.
Sejajar dengan itu, ada **Picklist J&T Resi Siang** (`--jnt-siang`) — juga manual 1x sehari
(mis. jam 15:00): channel TikTok Shop saja, kurir J&T saja, pesanan yang jam pesannya (WIB)
maksimal jam 15:00 hari ini (aturan bisnis J&T: wajib keluar TikTok Shop paling lambat jam
15.00). Lihat bagian 5 di bawah.

**Pemisahan J&T/SPX (`--kurir`)**: `--label` dan `--reguler` menerima opsi `--kurir jnt` /
`--kurir spx` supaya J&T dan SPX jadi picklist **terpisah** saat pembuatan, bukan digabung.
Tanpa `--kurir` (default), J&T dan SPX tetap digabung seperti semula. Penentuan SKU mana yang
"spesial" (dari Excel, `hitung_sku_spesial`) **selalu** menggabung J&T+SPX — `--kurir` cuma
membatasi resi mana yang benar-benar dipicklist saat itu. Dipakai `proses-harian.bat` **TIPE 2**
dan **TIPE 3** (lihat `proses-harian.bat`/[docs/jadwal-proses.md](docs/jadwal-proses.md)); **TIPE 1**
dan **TIPE 4** tetap menggabung J&T+SPX.

Aturan SKU spesial dan data uji: lihat [docs/panduan-sku-spesial.md](docs/panduan-sku-spesial.md)
(kode di bagian 8 panduan adalah versi awal; kode yang dipakai adalah file `.py` di folder ini).

## File

| File | Isi |
|---|---|
| `src/main.py` | Alur CLI: login → download Excel → hitung → (SKU spesial + PDF) → (reguler). `--urgent`/`--reguler`/`--shopee-pagi`/`--jnt-siang` adalah alur terpisah (tidak lewat langkah ini). Lihat `--help` untuk semua opsi |
| `src/jubelio.py` | Login API Jubelio, download Excel laporan, ambil nilai pesanan (tanpa browser) |
| `src/sku_spesial.py` | Baca Excel, hitung SKU spesial, buat PDF |
| `src/proses_label.py` | Picklist → picking → resi → label PDF (SKU spesial per SKU, urgent/reguler/Shopee Pagi/J&T Resi Siang per channel), catat riwayat |
| `jalankan.bat` | Menjalankan `src/main.py` dengan Python di `.venv` |
| `proses-harian.bat` | Menu interaktif SUNGGUHAN (klik 2x), 4 TIPE + Keluar: TIPE 1-4 — tiap TIPE menjalankan urutan langkahnya sendiri (lihat [docs/jadwal-proses.md](docs/jadwal-proses.md)) dalam satu kali konfirmasi Y/N |
| `proses-harian-uji.bat` | Menu interaktif MODE UJI (klik 2x), struktur sama seperti `proses-harian.bat` - tidak ada perubahan di Jubelio |
| `.env` | Email & password Jubelio (`JUBELIO_EMAIL`, `JUBELIO_PASSWORD`) |
| `sniff/` | Perekam alur Jubelio (`run_sniff_jubel.bat`) untuk analisa jika Jubelio berubah |
| `docs/` | Dokumentasi tambahan (instalasi, jadwal, panduan SKU spesial, analisa alur label) |

Hasil: Excel di `laporan-siap-proses/`, PDF ringkasan SKU spesial di `laporan-sku-spesial/`,
label per picklist di `label-pengiriman/`, log di `logs/`, riwayat semua picklist (SKU spesial, urgent,
reguler) di `riwayat_picklist.xlsx`. Lihat [docs/standar-struktur-proyek.md](docs/standar-struktur-proyek.md)
untuk aturan penamaan folder/file.

## Instalasi (sekali saja)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Buat file `.env` berisi `JUBELIO_EMAIL` dan `JUBELIO_PASSWORD` (lihat contoh isi di
`.env` yang sudah ada, atau [docs/instalasi.md](docs/instalasi.md) bagian 5 kalau mulai dari nol —
tidak ada file `.env.example` di proyek ini).

Pindah ke PC lain? Lihat panduan lengkap di [docs/instalasi.md](docs/instalasi.md) (versi
Python, semua library yang perlu di-install, dan konfigurasi `.env`).

Jadwal operasional harian tim resi (jam berapa menu apa dijalankan, plus
rencana pengembangan ke depan): lihat [docs/jadwal-proses.md](docs/jadwal-proses.md).

## Menjalankan

```bash
jalankan.bat
```

Pilihan:

- `jalankan.bat --excel "C:\path\file.xlsx"` — lewati download, proses file yang sudah ada
  (nilai pesanan tetap dicek ke API).
- `jalankan.bat --excel "C:\path\file.xlsx" --tanpa-cek-nilai` — tanpa akses API sama sekali;
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
jalankan.bat --urgent                                      # mode uji (keduanya)
jalankan.bat --urgent --channel lazada --jalankan           # Lazada saja, sungguhan
jalankan.bat --urgent --channel gtl-sicepat --jalankan      # GTL/SiCepat saja, sungguhan
```

Dijalankan sebagai langkah pertama & kedua di setiap TIPE `proses-harian.bat` (TIPE 1-4)
= `jalankan.bat --urgent --channel lazada --jalankan` lalu
`jalankan.bat --urgent --channel gtl-sicepat --jalankan`. `proses-harian-uji.bat` = versi mode uji
(tanpa `--jalankan`) masing-masing channel.

- Label PDF urgent: nama file & kolom SKU di riwayat pakai nama skenario (huruf besar),
  bukan SKU — mis. `label-pengiriman/PICK-000155230_LAZADA_2026-09-29_150512.pdf`,
  `label-pengiriman/PICK-000155231_GTL-SICEPAT_2026-09-29_150612.pdf`. Tercatat juga di
  `riwayat_picklist.xlsx` dengan kolom SKU berisi `LAZADA` / `GTL-SICEPAT`.

## 2. Proses SKU spesial sampai label pengiriman (`--label`, `proses_label.py`)

**Langkah pertama** dari alur `--label --jalankan` (sebelum picklist sisa reguler — picklist
urgent **tidak** termasuk, lihat catatan di bagian 1): per SKU dibuat picklist, picking
diselesaikan, resi diminta, lalu label PDF diunduh. Detail alur:
[docs/analisa-alur-cetak-label.md](docs/analisa-alur-cetak-label.md).

**Tanpa `--jalankan` selalu mode uji**: hanya membaca data Jubelio dan menampilkan pesanan yang
akan diproses / dibuang beserta alasannya. Tidak ada yang berubah di Jubelio.

```bash
jalankan.bat --label
jalankan.bat --label --sku T01-BSBI-5
jalankan.bat --label --sku T01-BSBI-5 --jalankan
jalankan.bat --label --jalankan
jalankan.bat --label --tanpa-reguler --jalankan
jalankan.bat --label --kurir jnt --tanpa-reguler --jalankan    # J&T saja (TIPE 2/TIPE 3)
jalankan.bat --label --kurir spx --tanpa-reguler --jalankan    # SPX saja (TIPE 2/TIPE 3)
jalankan.bat --lanjut PICK-000154839 --jalankan
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

`proses-harian.bat` TIPE 1/TIPE 4, langkah "SPX - J&T SPESIAL" = `jalankan.bat --label --tanpa-reguler --jalankan`;
TIPE 2/TIPE 3, langkah "J&T SPESIAL"/"SPX SPESIAL" = `jalankan.bat --label --kurir jnt
--tanpa-reguler --jalankan` / `jalankan.bat --label --kurir spx --tanpa-reguler --jalankan`
(satu konfirmasi Y/N per TIPE). `proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`) yang sama.

- Label PDF: `label-pengiriman/<PICK-no>_<SKU>_<tanggal>_<jam>.pdf`, mis. `PICK-000155085_BM-AKS27-1_2026-09-29_090947.pdf`
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

`jalankan.bat --label --jalankan` otomatis menjalankan ini **SETELAH** SKU spesial selesai (kalau
tidak dibatasi `--sku`, karena daftar SKU spesial perlu lengkap dulu supaya pengecualiannya
benar). Bisa juga dijalankan terpisah, per bagian — ini tetap download & hitung Excel dulu
(read-only, tanpa proses SKU spesial) supaya tahu resi mana yang harus dikecualikan:

```bash
jalankan.bat --reguler                                # mode uji (keduanya, digabung)
jalankan.bat --reguler --bagian 1qty --jalankan        # 1 Qty Reguler saja, sungguhan (digabung)
jalankan.bat --reguler --bagian kombinasi --jalankan   # Kombinasi Reguler saja, sungguhan (digabung)
jalankan.bat --reguler --bagian 1qty --kurir jnt --jalankan       # J&T saja
jalankan.bat --reguler --bagian kombinasi --kurir spx --jalankan  # SPX saja
```

`proses-harian.bat` TIPE 1/TIPE 4, langkah "SPX - J&T 1 QTY REGULER"/"SPX - J&T KOMBINASI" =
`jalankan.bat --reguler --bagian 1qty --jalankan` / `jalankan.bat --reguler --bagian kombinasi --jalankan`
(digabung). TIPE 2/TIPE 3, langkah "J&T 1 QTY REGULER"/"J&T KOMBINASI"/"SPX 1 QTY
REGULER"/"SPX KOMBINASI" = perintah yang sama ditambah `--kurir jnt`/`--kurir spx`.
`proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`) yang sama. Kolom SKU di riwayat:
`1QTY-REGULER` / `KOMBINASI-REGULER` (digabung), atau `J&T-1QTY-REGULER` / `SPX-1QTY-REGULER`
/ `J&T-KOMBINASI-REGULER` / `SPX-KOMBINASI-REGULER` (dipisah lewat `--kurir`). Nama file PDF
tidak boleh memuat simbol `&` (dibuang otomatis), jadi khusus nama file J&T dituliskan `JNT`
tanpa simbol, mis. `label-pengiriman/PICK-000155300_1QTY-REGULER_...pdf` atau
`label-pengiriman/PICK-000155301_JNT-1QTY-REGULER_...pdf`.

Tiap TIPE `proses-harian.bat` (TIPE 1-4) menjalankan seluruh langkahnya secara berurut dalam
satu kali klik + satu konfirmasi Y/N — urutan lengkap tiap TIPE ada di
[docs/jadwal-proses.md](docs/jadwal-proses.md).

## 4. Picklist SPX Resi Pagi (`--shopee-pagi`)

**Dijalankan MANUAL 1x sehari** (mis. jam 13:00) — **bukan** bagian alur otomatis
`--label --jalankan`, dan **tidak** perlu download/hitung Excel. Semua pesanan Siap Proses
channel **Shopee** saja (`channel_id=64`, tanpa filter kurir) yang jam pesannya (WIB)
**maksimal jam 12:00 siang hari ini**, digabung jadi 1 picklist (dipecah kalau > 200),
diproses SAMPAI label PDF juga.

```bash
jalankan.bat --shopee-pagi               # mode uji
jalankan.bat --shopee-pagi --jalankan    # sungguhan
```

`proses-harian.bat` TIPE 2, langkah "SPX <= 12.00 (SPX RESI PAGI)" = `jalankan.bat --shopee-pagi
--jalankan` (dijalankan cukup 1x sehari, jangan diulang di TIPE 3). `proses-harian-uji.bat` = versi mode
uji (tanpa `--jalankan`). Nama file & kolom SKU di riwayat: `SHOPEE-PAGI`, mis.
`label-pengiriman/PICK-000155400_SHOPEE-PAGI_...pdf`.

## 5. Picklist J&T Resi Siang (`--jnt-siang`)

**Dijalankan MANUAL 1x sehari** (mis. jam 15:00) — **bukan** bagian alur otomatis
`--label --jalankan`, dan **tidak** perlu download/hitung Excel. Semua pesanan Siap Proses
channel **TikTok Shop** (`channel_id=131076`), kurir **J&T saja**, yang jam pesannya (WIB)
**maksimal jam 15:00 hari ini**, digabung jadi 1 picklist (dipecah kalau > 200), diproses
SAMPAI label PDF juga. Aturan bisnis J&T: pesanan TikTok Shop wajib keluar hari itu lewat J&T
harus digabung 1 picklist paling lambat jam 15.00 (sejajar dengan aturan SPX Resi Pagi di
atas, beda kurir dan beda jam cutoff — lihat [docs/jadwal-proses.md](docs/jadwal-proses.md)).

```bash
jalankan.bat --jnt-siang               # mode uji
jalankan.bat --jnt-siang --jalankan    # sungguhan
```

`proses-harian.bat` TIPE 4, langkah "J&T <= 15.00 (J&T RESI SIANG)" =
`jalankan.bat --jnt-siang --jalankan` (dijalankan cukup 1x sehari, jangan diulang di siklus
setelahnya). `proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`). Nama file & kolom
SKU di riwayat: `JNT-SIANG`, mis. `label-pengiriman/PICK-000155500_JNT-SIANG_...pdf`.

## Jadwal otomatis (Windows Task Scheduler)

*Create Basic Task* → pilih jadwal → *Start a program*:

- Program: `C:\proses-pesanan-otomatis\jalankan.bat`
- Start in: `C:\proses-pesanan-otomatis`
