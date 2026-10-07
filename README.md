# Proses Pesanan Otomatis — SKU Spesial

Otomatisasi proses pesanan (picklist → resi → label pengiriman) untuk toko online yang
memakai **Jubelio** sebagai sistem manajemen pesanan (order management system). Dibuat untuk
tim operasional gudang/pengiriman yang setiap hari harus membuat picklist, meminta nomor
resi, dan mencetak label pengiriman secara manual di Jubelio untuk ratusan pesanan dari
beberapa marketplace (TikTok Shop, Shopee, Lazada, Tokopedia) sekaligus — pekerjaan yang
tadinya berulang-ulang lewat antarmuka web Jubelio, sekarang dijalankan lewat satu perintah.

**Tidak ada UI web.** Semuanya berupa CLI Python yang dijalankan lewat file `.bat` di
Windows (klik dua kali, atau dipicu otomatis via Windows Task Scheduler), dipakai langsung
oleh tim operasional tanpa perlu paham Python. Jubelio diakses lewat **API HTTP langsung**
(bukan browser automation) menggunakan cookie token dari hasil login — lebih cepat dan lebih
stabil dibanding men-drive browser, dengan `sniff/` (perekam traffic berbasis Playwright)
sebagai alat bantu untuk merekam ulang alur API Jubelio kalau suatu saat mereka mengubahnya.

Alur bisnis yang dicakup, sesuai aturan toko ini:

- **SKU spesial** — SKU tertentu (lihat [docs/panduan-sku-spesial.md](docs/panduan-sku-spesial.md))
  dipicklist terpisah per SKU supaya proses packing lebih cepat, alih-alih tercampur dengan
  pesanan reguler.
- **Urgent** (Lazada, serta kurir GTL/SiCepat lintas channel) — diproses lebih dulu/terpisah
  karena punya tenggat pengiriman lebih ketat.
- **Reguler** (sisa TikTok Shop & Shopee yang bukan SKU spesial) — dipecah 1 Qty vs Kombinasi
  supaya packing lebih efisien.
- **Shopee Pagi** dan **J&T Resi Siang** — dua batch manual 1x/hari yang mengejar jam cutoff
  pengiriman kurir tertentu.
- **Sampel/kreator** (pesanan TikTok Shop nilai 0) — tetap dipicklist & diberi label sendiri
  alih-alih dibuang diam-diam, supaya tim tahu ke mana pesanan itu harus dikirim.

Setiap langkah mencatat riwayat ke `riwayat_picklist.xlsx` dan mendeteksi anomali (nomor
picklist yang terlompat karena Jubelio gagal buat picklist, atau pesanan yang sudah "Picking
> Selesai" tapi tidak kunjung dapat resi) supaya tim admin/CS bisa ditindaklanjuti lebih awal.
Hampir semua alur defaultnya **mode uji** (read-only, hanya menampilkan rencana) dan baru
benar-benar mengubah data di Jubelio kalau diberi flag `--jalankan` secara eksplisit.

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
(kode yang dipakai adalah file `.py` di folder `src/`; versi awal/kerangka ada di
[docs/referensi-implementasi-sku-spesial-awal.md](docs/referensi-implementasi-sku-spesial-awal.md)).

## File

| File | Isi |
|---|---|
| `src/main.py` | Alur CLI: login → download Excel → hitung → (SKU spesial + PDF) → (reguler). `--urgent`/`--reguler`/`--shopee-pagi`/`--jnt-siang` adalah alur terpisah (tidak lewat langkah ini). Lihat `--help` untuk semua opsi |
| `src/jubelio.py` | Login API Jubelio, download Excel laporan, ambil nilai pesanan (tanpa browser) |
| `src/sku_spesial.py` | Baca Excel, hitung SKU spesial, buat PDF |
| `src/proses_label.py` | Picklist → picking → resi → label PDF (SKU spesial per SKU, urgent/reguler/Shopee Pagi/J&T Resi Siang per channel), catat riwayat |
| `src/print_spesial.py` | Cetak bulk label (SPESIAL/URGENT/SATUAN/KOMBINASI) dari folder sesi `label-pengiriman/` terbaru lewat SumatraPDF, lihat `--jenis` |
| `src/peringatan_picklist.py` | Deteksi nomor picklist yang terlompat (picklist batal/gagal dibuat karena Jubelio error) |
| `src/peringatan_resi.py` | Deteksi pesanan yang sudah Picking > Selesai tapi tidak kunjung dapat nomor resi (kemungkinan request cancel yang masih diproses) |
| `src/peringatan_gagal.py` | Simpan picklist/proses yang terhenti/gagal supaya tercetak ulang di rekap akhir tiap TIPE |
| `src/rekap_waktu.py` | Cetak rekap waktu & semua peringatan (picklist terlompat, tanpa resi, gagal) di akhir tiap TIPE `proses-harian.bat` |
| `src/rekap_master_excel.py` | Catat tiap picklist ke salinan kerja `PICKLIST.xlsx` (dari file master "PICK LIST - EXCEL ... MASTER - TERBARU NEW.xlsx" yang tetap diverifikasi & disalin manual oleh tim) — lewat antrean, ditulis sekaligus 1x per TIPE (`--tulis-excel`, lihat bagian "Rekap PICKLIST.xlsx") |
| `jalankan.bat` | Menjalankan `src/main.py` dengan Python di `.venv` |
| `cetak-label-spesial.bat` | Menjalankan `src/print_spesial.py --jenis spesial` (klik 2x) — lihat bagian "Cetak bulk label" |
| `cetak-label-urgent.bat` | Menjalankan `src/print_spesial.py --jenis urgent` (klik 2x) — lihat bagian "Cetak bulk label" |
| `cetak-label-satuan.bat` | Menjalankan `src/print_spesial.py --jenis satuan` (klik 2x) — lihat bagian "Cetak bulk label" |
| `cetak-label-kombinasi.bat` | Menjalankan `src/print_spesial.py --jenis kombinasi` (klik 2x) — lihat bagian "Cetak bulk label" |
| `proses-harian.bat` | Menu interaktif SUNGGUHAN (klik 2x), 4 TIPE + Keluar: TIPE 1-4 — tiap TIPE menjalankan urutan langkahnya sendiri (lihat [docs/jadwal-proses.md](docs/jadwal-proses.md)) dalam satu kali konfirmasi Y/N |
| `proses-harian-uji.bat` | Menu interaktif MODE UJI (klik 2x), struktur sama seperti `proses-harian.bat` - tidak ada perubahan di Jubelio |
| `.env` | Email & password Jubelio (`JUBELIO_EMAIL`, `JUBELIO_PASSWORD`) + akun IRESIS (`IRESIS_USERNAME`, `IRESIS_PASSWORD`) |
| `sniff/` | Perekam alur Jubelio (`run_sniff_jubel.bat`) untuk analisa jika Jubelio berubah |
| `docs/` | Dokumentasi tambahan (instalasi, jadwal, panduan SKU spesial, analisa alur label, cetak bulk label) |

Hasil: Excel di `laporan-siap-proses/`, PDF ringkasan SKU spesial di `laporan-sku-spesial/`,
label per picklist di `label-pengiriman/`, log di `logs/`, riwayat semua picklist (SKU spesial, urgent,
reguler) di `riwayat_picklist.xlsx`, salinan kerja rekap picklist di `PICKLIST.xlsx` (kalau file
master-nya ada — lihat [docs/instalasi.md](docs/instalasi.md)). Lihat
[docs/standar-struktur-proyek.md](docs/standar-struktur-proyek.md) untuk aturan penamaan folder/file.

## Instalasi (sekali saja)

```bash
git clone https://github.com/johansen08/proses-pesanan-otomatis.git
cd proses-pesanan-otomatis
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Buat file `.env` berisi `JUBELIO_EMAIL` dan `JUBELIO_PASSWORD` (lihat
[docs/instalasi.md](docs/instalasi.md) bagian 5) — file ini **tidak ikut ter-clone** dari
GitHub karena sengaja di-gitignore (berisi kredensial login), jadi wajib dibuat manual
sendiri; tidak ada file `.env.example` di proyek ini.

Pindah dari PC lama ke PC baru (atau sudah pernah pakai `riwayat_picklist.xlsx` sebelumnya)?
Lihat panduan lengkap di [docs/instalasi.md](docs/instalasi.md) (versi Python, semua library
yang perlu di-install, konfigurasi `.env`, dan file lain yang perlu disalin manual).

Jadwal operasional harian tim resi (jam berapa menu apa dijalankan): lihat
[docs/jadwal-proses.md](docs/jadwal-proses.md). Rencana pengembangan ke depan
(belum diimplementasikan): [docs/rencana-pengembangan.md](docs/rencana-pengembangan.md).

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

## 0. Picklist sampel (`--sampel`)

**Alur berdiri sendiri, dijalankan PALING PERTAMA di tiap TIPE `proses-harian.bat`** (sebelum
picklist urgent). Pesanan channel TikTok Shop ("Shop | Tokopedia", `channel_id=131076`) yang
nilainya **0 atau kosong** adalah pesanan sampel/kreator (lihat catatan
`TT-586350230929114342-67824`, 01-10-2026) — sebelumnya dibuang diam-diam oleh
`ambil_pesanan_channel()` di semua alur channel (urgent/reguler/Shopee Pagi/J&T Resi Siang)
tanpa pernah masuk picklist apa pun. Sekarang pesanan itu dikumpulkan jadi **1 picklist
tersendiri** (dipecah kalau > 200 pesanan), diproses SAMPAI label PDF juga — kalau tidak ada
pesanan sampel saat itu, langkah ini otomatis dilewati tanpa membuat picklist, lalu lanjut ke
langkah berikutnya seperti biasa.

```bash
jalankan.bat --sampel                 # mode uji
jalankan.bat --sampel --jalankan      # sungguhan
```

Dijalankan sebagai langkah PERTAMA di setiap TIPE `proses-harian.bat` (TIPE 1-4), sebelum
urgent Lazada/GTL-SiCepat. `proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`).

**Format penamaan**: nomor picklist (`PICK-000xxxxxx`) dibuat otomatis oleh Jubelio sendiri,
sama seperti alur lain — bukan sesuatu yang kita tentukan. Yang kita tentukan cuma "nama SKU
pengganti" dipakai sebagai pengganti nama SKU asli (karena lintas SKU, sama polanya dengan
`LAZADA`/`GTL-SICEPAT`/`1QTY-REGULER`/`SHOPEE-PAGI`/`JNT-SIANG` di bagian 1/3/4/5):
`LABEL_SAMPEL = "SAMPEL-TIKTOK"` (`src/proses_label.py`). Nama ini dipakai di 2 tempat:

- **Nama file PDF label**: `{No Picklist}_SAMPEL-TIKTOK_{tanggal YYYY-MM-DD}_{jam HHMMSS}.pdf`,
  mis. `label-pengiriman/PICK-000155229_SAMPEL-TIKTOK_2026-10-01_070512.pdf`. Tidak memakai
  penanda `SPESIAL` (itu khusus Alur 1 - SKU spesial, lihat bagian "Cetak bulk label"
  di bawah).
- **Kolom SKU di `riwayat_picklist.xlsx`**: berisi `SAMPEL-TIKTOK` juga.

`ambil_pesanan_channel()` (dipakai urgent/reguler/Shopee Pagi/J&T Resi Siang) TETAP
mengeluarkan pesanan sampel ini dari hasilnya supaya tidak dobel diproses.

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

- **Lazada**: semua pesanan channel Lazada (`channel_id=4`), digabung jadi 1 picklist
  (dipecah kalau > 200, lihat di atas). Label PDF-nya memakai template khusus **"Label
  Pengiriman Lazada"** (program mengirim `isFromLz=true` ke `reports/shipping-label/`, sama
  seperti web) yang berukuran A5; PDF otomatis **diperkecil ke skala 68%** di kertas label
  100x150 mm segera setelah diunduh (`skala_label_lazada()`, pakai `pypdf`), sama dengan cetak
  manual di web dengan skala custom 68%. Detailnya di `docs/analisa-alur-cetak-label.md`
  bagian 6.
- **GTL-SiCepat**: semua pesanan kurir **GTL** atau **SiCepat**, **lintas channel** (TIDAK
  difilter channel). Urgent-nya ditentukan kurir, bukan channel, jadi pesanan Tokopedia
  **asli** (`channel_id=128`) *dan* "Shop | Tokopedia" (`channel_id=131076`, nama lain TikTok
  Shop di Jubelio) dengan kurir itu sama-sama ikut. Volumenya besar, jadi dipecah per
  **LANTAI** rak gudang (1/2/3/LAINNYA) — pola yang sama dengan bagian "kombinasi" picklist
  sisa reguler (bagian 3 di bawah) lewat `_kelompok_kombinasi_per_lantai()`, tapi query rak
  live-nya dibatasi kurir GTL/SiCepat (bukan J&T/SPX reguler). Label/nama file jadi
  `GTL-SICEPAT-LANTAI1`/`GTL-SICEPAT-LANTAI2`/`GTL-SICEPAT-LANTAI3`/`GTL-SICEPAT-LAINNYA`,
  masing-masing dipecah lagi kalau > 200 pesanan.

**Jam tunda**: pesanan yang jam pesannya (WIB) masih di atas jam tunda hari itu belum
dipicklist dulu — Lazada ditahan di atas jam 14.00, GTL/SiCepat di atas jam 15.00 — baru
dilanjutkan otomatis begitu `--urgent` dijalankan lagi setelah jam 16.00 (batas jam ini
diabaikan sepenuhnya setelah jam 16.00). Lihat `docs/jadwal-proses.md` bagian "Jam tunda
Urgent Lazada & GTL/SiCepat" untuk jadwal lengkapnya.

**Tidak dijalankan otomatis oleh `--label --jalankan`.** Harus dipicu manual, terpisah, lewat
`--urgent` (mis. sebelum menjalankan menu SKU spesial/reguler, supaya pesanan yang sudah
"diambil" urgent tidak ikut terhitung sebagai kandidat SKU spesial — tapi ini tanggung jawab
tim/jadwal, bukan otomatis di kode). Jalankan salah satu atau kedua skenario:

```bash
jalankan.bat --urgent                                      # mode uji (keduanya)
jalankan.bat --urgent --channel lazada --jalankan           # Lazada saja, sungguhan
jalankan.bat --urgent --channel gtl-sicepat --jalankan      # GTL/SiCepat saja, sungguhan
```

Dijalankan sebagai langkah kedua & ketiga di setiap TIPE `proses-harian.bat` (TIPE 1-4,
setelah picklist sampel di bagian 0 di atas) = `jalankan.bat --urgent --channel lazada --jalankan`
lalu `jalankan.bat --urgent --channel gtl-sicepat --jalankan`. `proses-harian-uji.bat` = versi
mode uji (tanpa `--jalankan`) masing-masing channel.

- Label PDF urgent: nama file & kolom SKU di riwayat pakai nama skenario (huruf besar),
  bukan SKU, DAN disimpan di subfolder `URGENT` folder sesi (Lazada maupun GTL/SiCepat
  sama-sama di subfolder yang sama) — mis.
  `label-pengiriman/<tanggal>/<sesi>/URGENT/PICK-000155230_LAZADA_2026-09-29_150512.pdf`,
  `label-pengiriman/<tanggal>/<sesi>/URGENT/PICK-000155231_GTL-SICEPAT-LANTAI1_2026-09-29_150612.pdf`.
  Beda dengan subfolder `SPESIAL` (bagian 2 di bawah): nama filenya TIDAK disisipi penanda
  `URGENT`, cuma lokasi penyimpanannya yang pindah ke subfolder itu (lihat parameter
  `subfolder` di `lanjutkan_picklist()`, `src/proses_label.py`). Tercatat juga di
  `riwayat_picklist.xlsx` dengan kolom SKU berisi `LAZADA` /
  `GTL-SICEPAT-LANTAI1`/`LANTAI2`/`LANTAI3`/`LAINNYA`.

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
jalankan.bat --lanjut PICK-000157269 --nama KOMBINASI-REGULER-LANTAI2 --subfolder KOMBINASI --sesi 2026-10-06/11 --jalankan
```

Urutan pakai: (1) mode uji semua SKU, (2) mode uji satu SKU, (3) jalankan sungguhan untuk
**satu SKU** dan cek hasilnya di web Jubelio, (4) baru semua SKU. `--lanjut` dipakai untuk
picklist yang prosesnya terhenti di tengah — **salin perintah lengkapnya dari Catatan
`TERHENTI`** (blok PERHATIAN di akhir proses / `riwayat_picklist.xlsx`): perintah itu sudah
membawa `--nama` (label, mis. `KOMBINASI-REGULER-LANTAI2` atau SKU-nya), `--subfolder`
(`URGENT`/`SATUAN`/`KOMBINASI`/...) atau `--tag` (SKU spesial: `SPESIAL`/`JNT_SPESIAL`/
`SPX_SPESIAL`), dan `--sesi` (folder sesi asal), sehingga PDF hasil lanjutan bernama & tersimpan
persis seperti alur aslinya dan ikut tercetak lewat .bat cetak bulk per jenis. Tanpa opsi-opsi
itu, PDF disimpan langsung di folder sesi BARU dengan nama `PICK-..._<SKU>_...` (1 SKU) atau
`PICK-..._LANJUTAN_...` (lintas SKU) — tidak terbaca .bat cetak bulk. **Catatan**: `--sku` melewatkan langkah picklist
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

- Label PDF: disimpan di subfolder `SPESIAL` folder sesi, `label-pengiriman/<tanggal>/<sesi>/SPESIAL/<PICK-no>_SPESIAL_<SKU>_<tanggal>_<jam>.pdf`, mis. `label-pengiriman/2026-10-02/1/SPESIAL/PICK-000155085_SPESIAL_BM-AKS27-1_2026-09-29_090947.pdf` (dipisah dari label alur lain supaya folder sesi tidak penuh puluhan file SPESIAL). Kalau `--kurir jnt`/`--kurir spx` dipakai, tag & subfoldernya jadi `JNT_SPESIAL`/`SPX_SPESIAL` (mis. `.../JNT_SPESIAL/PICK-000155085_JNT_SPESIAL_BM-AKS27-1_..._....pdf`) supaya label J&T dan SPX tidak bercampur/tertukar — `cetak-label-spesial.bat` tetap mencari ketiga kemungkinan subfolder (lihat bagian "Cetak bulk label").
- Riwayat: `riwayat_picklist.xlsx` (Waktu, SKU, No Picklist, Total Pesanan, Resi Keluar,
  File Label, Catatan, Durasi). Jika file sedang dibuka di Excel, ditulis ke `riwayat_picklist.csv`.
- Detail resi (1 file per sesi, langsung di folder sesi `label-pengiriman/<tanggal>/<sesi>/`,
  BUKAN di subfolder SPESIAL): 1 baris per pesanan yang resinya benar-benar keluar & labelnya
  berhasil diunduh (kolom No Picklist, SKU, No Pesanan, No Resi). Kalau dari 1 picklist jumlah
  baris itu masih >= 3 (MIN_RESI), SKU-nya tetap sah spesial → masuk `detail-resi-spesial.xlsx`.
  Kalau sebagian resinya ternyata batal/request-cancel saat proses sehingga yang benar-benar
  tercetak jadi < 3 → SKU-nya gugur jadi tidak spesial lagi, tapi baris yang sudah tercetak
  tetap dicatat, ke `detail-resi-bukan-spesial.xlsx` (file berbeda) supaya bisa dipisah saat
  memilah resi fisik.
- SKU dilewati jika pesanan tersisa < 3, stok kurang, pesanan dari lokasi berbeda,
  atau ada item selain SKU itu.
- Uji tanpa internet: `.venv\Scripts\python tests\test_proses_label.py`

## 3. Picklist sisa reguler (`--reguler`)

**Langkah kedua/terakhir** dari alur `--label --jalankan` — dibuat setelah SKU
spesial selesai diproses (picklist urgent tidak termasuk, lihat bagian 1). Sisa pesanan channel **TikTok Shop** ("Shop | Tokopedia"
di Jubelio, `channel_id=131076`) dan **Shopee** (`channel_id=64`) dengan kurir **J&T/SPX**
yang **bukan** bagian SKU spesial hari itu digabung jadi picklist, dipecah 2 bagian:

- **1 Qty Reguler**: 1 SKU, qty 1 (resi tunggal yang SKU-nya tidak mencapai syarat spesial) -
  dipecah LAGI jadi beberapa picklist berdasarkan grup rak gudang (`GRUP_RAK` di
  `src/proses_label.py`: `2A`, `3A`, `1B`, `2B`, `3B`, berurutan - grup `1A` tidak ada di
  gudang ini), supaya picker tidak bolak-balik antar zona. Pesanan yang rak-nya di luar 5
  grup itu digabung jadi 1 picklist `LAINNYA`. Grup yang tidak ada pesanannya dilewati (tidak
  bikin picklist kosong). Lihat
  [docs/superpowers/specs/2026-10-02-pecah-1qty-per-rak-design.md](docs/superpowers/specs/2026-10-02-pecah-1qty-per-rak-design.md)
  untuk detail mekanismenya (endpoint `zones-racks-combination` + filter `combination[]`).
- **Kombinasi Reguler**: sisanya — pesanan qty > 1 (multi-baris/multi-SKU atau 1 SKU qty > 1),
  TIDAK dipecah per rak (tetap 1 picklist gabungan seperti sebelumnya).

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
`proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`) yang sama. Kolom SKU di riwayat
untuk bagian 1 Qty Reguler kini per grup rak: `1QTY-REGULER-2A` / `1QTY-REGULER-3A` /
`1QTY-REGULER-1B` / `1QTY-REGULER-2B` / `1QTY-REGULER-3B` / `1QTY-REGULER-LAINNYA` (digabung),
atau diawali `J&T-`/`SPX-` kalau dipisah lewat `--kurir` (mis. `J&T-1QTY-REGULER-2A`). Bagian
Kombinasi Reguler kini per lantai rak: `KOMBINASI-REGULER-LANTAI1` / `KOMBINASI-REGULER-LANTAI2`
/ `KOMBINASI-REGULER-LANTAI3` / `KOMBINASI-REGULER-LAINNYA` (digabung), atau diawali `J&T-`/
`SPX-` kalau dipisah lewat `--kurir` (mis. `J&T-KOMBINASI-REGULER-LANTAI1`). Nama file PDF tidak boleh memuat simbol `&` (dibuang
otomatis), jadi khusus nama file J&T dituliskan `JNT` tanpa simbol, mis.
`label-pengiriman/<tanggal>/<sesi>/SATUAN/PICK-000155300_1QTY-REGULER-2A_...pdf` atau
`label-pengiriman/<tanggal>/<sesi>/SATUAN/PICK-000155301_JNT-1QTY-REGULER-2A_...pdf`.

Label PDF bagian "1 Qty Reguler" disimpan di subfolder `SATUAN` folder sesi, bagian
"Kombinasi Reguler" di subfolder `KOMBINASI` — sama pola dengan subfolder `URGENT` di
bagian 1 (nama file TIDAK disisipi penanda, cuma lokasinya yang pindah). Kalau `--kurir
jnt`/`--kurir spx` dipakai, subfoldernya ikut disisipi awalan jadi `JNT_SATUAN`/`SPX_SATUAN`
atau `JNT_KOMBINASI`/`SPX_KOMBINASI` (lihat `SUBFOLDER_SATUAN`/`SUBFOLDER_KOMBINASI` &
`_gabung_kurir()` di `src/proses_label.py`), supaya label J&T dan SPX tidak bercampur.

Tiap TIPE `proses-harian.bat` (TIPE 1-4) menjalankan seluruh langkahnya secara berurut dalam
satu kali klik + satu konfirmasi Y/N — urutan lengkap tiap TIPE ada di
[docs/jadwal-proses.md](docs/jadwal-proses.md).

### Rekap PICKLIST.xlsx (`--tulis-excel`)

Selama langkah-langkah TIPE berjalan, tiap picklist cuma masuk **antrean**
(`logs/antrian_picklist_excel.jsonl`) — `PICKLIST.xlsx` baru dibuka & disimpan **sekali** di
langkah terakhir tiap TIPE ("TULIS PICKLIST.XLSX"), karena membuka+menyimpan file sebesar itu
makan ±2 menit (dulu terulang di tiap langkah, insiden 2026-10-06). Picklist dari `--lanjut`
juga masuk antrean dan ikut tertulis di akhir TIPE berikutnya — atau tulis sekarang juga:

```bash
jalankan.bat --tulis-excel              # mode uji: hanya tampilkan jumlah antrean
jalankan.bat --tulis-excel --jalankan   # tulis semua antrean ke PICKLIST.xlsx
```

Kalau `PICKLIST.xlsx` sedang dibuka di Excel (atau rusak), antrean **tidak dibuang** — muncul
peringatan di rekap akhir TIPE, dan otomatis dicoba lagi di TIPE berikutnya. File lama tidak
pernah setengah tertulis: penyimpanan lewat file sementara `PICKLIST.xlsx.menulis` dulu.

## 4. Picklist SPX Resi Pagi (`--shopee-pagi`)

**Dijalankan MANUAL 1x sehari** (mis. jam 13:00) — **bukan** bagian alur otomatis
`--label --jalankan`, dan **tidak** perlu download/hitung Excel. Semua pesanan Siap Proses
channel **Shopee** saja (`channel_id=64`, tanpa filter kurir) yang jam pesannya (WIB)
**maksimal jam 12:00 siang hari ini**, dipecah per **LANTAI** rak gudang (1/2/3/LAINNYA) —
pola yang sama dengan bagian "kombinasi" picklist sisa reguler/urgent GTL-SiCepat lewat
`_kelompok_kombinasi_per_lantai()` — masing-masing dipecah lagi kalau > 200 pesanan, diproses
SAMPAI label PDF juga.

```bash
jalankan.bat --shopee-pagi               # mode uji
jalankan.bat --shopee-pagi --jalankan    # sungguhan
```

`proses-harian.bat` TIPE 2, langkah "SPX <= 12.00 (SPX RESI PAGI)" = `jalankan.bat --shopee-pagi
--jalankan` (dijalankan cukup 1x sehari, jangan diulang di TIPE 3). `proses-harian-uji.bat` = versi mode
uji (tanpa `--jalankan`). Nama file & kolom SKU di riwayat:
`SHOPEE-PAGI-LANTAI1`/`LANTAI2`/`LANTAI3`/`LAINNYA`, mis.
`label-pengiriman/PICK-000155400_SHOPEE-PAGI-LANTAI1_...pdf`.

## 5. Picklist J&T Resi Siang (`--jnt-siang`)

**Dijalankan MANUAL 1x sehari** (mis. jam 15:00) — **bukan** bagian alur otomatis
`--label --jalankan`, dan **tidak** perlu download/hitung Excel. Semua pesanan Siap Proses
channel **TikTok Shop** (`channel_id=131076`), kurir **J&T saja**, yang jam pesannya (WIB)
**maksimal jam 15:00 hari ini**, dipecah per **LANTAI** rak gudang (1/2/3/LAINNYA, sama pola
dengan SPX Resi Pagi di atas), masing-masing dipecah lagi kalau > 200 pesanan, diproses
SAMPAI label PDF juga. Aturan bisnis J&T: pesanan TikTok Shop wajib keluar hari itu lewat J&T
paling lambat jam 15.00 (sejajar dengan aturan SPX Resi Pagi di atas, beda kurir dan beda jam
cutoff — lihat [docs/jadwal-proses.md](docs/jadwal-proses.md)).

```bash
jalankan.bat --jnt-siang               # mode uji
jalankan.bat --jnt-siang --jalankan    # sungguhan
```

`proses-harian.bat` TIPE 4, langkah "J&T <= 15.00 (J&T RESI SIANG)" =
`jalankan.bat --jnt-siang --jalankan` (dijalankan cukup 1x sehari, jangan diulang di siklus
setelahnya). `proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`). Nama file & kolom
SKU di riwayat: `JNT-SIANG-LANTAI1`/`LANTAI2`/`LANTAI3`/`LAINNYA`, mis.
`label-pengiriman/PICK-000155500_JNT-SIANG-LANTAI1_...pdf`.

## 6. Recheck stok (`--recheck-stok`)

**Alur berdiri sendiri, dijalankan PALING PERTAMA di tiap TIPE `proses-harian.bat`** (sebelum
picklist sampel) — cek ulang stok untuk SEMUA pesanan yang berstatus stok kosong
(`EMPTY_STOCK`, biasanya bekas picklist sebelumnya yang gagal karena stok tidak ada
sekaligus, bukan per-pesanan/per-SKU). Pesanan yang stoknya sudah tersedia lagi otomatis
kembali diproses normal, sehingga ikut terhitung di langkah-langkah berikutnya TIPE yang sama
(sampel/urgent/spesial/reguler). Kalau tidak ada pesanan stok kosong saat itu, langkah ini
otomatis dilewati tanpa memanggil Jubelio lagi — tidak membuat picklist/label apa pun, cuma
memicu Jubelio mengecek ulang stok.

```bash
jalankan.bat --recheck-stok                 # mode uji: tampilkan daftar pesanan stok kosong
jalankan.bat --recheck-stok --jalankan      # sungguhan
```

Dijalankan sebagai langkah PERTAMA di setiap TIPE `proses-harian.bat` (TIPE 1-4), sebelum
picklist sampel. `proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`).

Alur (berdasarkan rekaman sniff, lihat `jubelio.ambil_stok_kosong()`/`jubelio.recheck_stok()`):

1. `GET wms/sales/v2/orders/empty-stock/` — daftar pesanan berstatus stok kosong saat ini.
2. `GET wms/sales/orders/recheck-stock/` — picu Jubelio mengecek ulang stok SEMUA pesanan di
   atas sekaligus (tombol "Recheck Stok" di web, GET tanpa body/parameter).
3. Daftar diambil ulang untuk tahu berapa pesanan yang kembali normal vs masih stok kosong.

## Cetak bulk label (`cetak-label-*.bat`, `src/print_spesial.py`)

Panduan lengkap (termasuk download & setup SumatraPDF): [docs/cetak-bulk-label.md](docs/cetak-bulk-label.md).

Mencetak ulang label pengiriman yang sudah ada secara **bulk dan berurut** (nomor
PICK terkecil/paling dulu dibuat, duluan dicetak), tanpa perlu buka file PDF
satu-satu secara manual. Program ini **tidak** membuat picklist/label baru — cuma
mencetak ulang PDF yang sudah ada. Ada 4 jenis, masing-masing `.bat` sendiri:

```bash
cetak-label-spesial.bat      # subfolder SPESIAL/JNT_SPESIAL/SPX_SPESIAL (Alur 1)
cetak-label-urgent.bat       # subfolder URGENT (Alur 2, Lazada & GTL-SiCepat)
cetak-label-satuan.bat       # subfolder SATUAN/JNT_SATUAN/SPX_SATUAN (Alur 3, 1qty)
cetak-label-kombinasi.bat    # subfolder KOMBINASI/JNT_KOMBINASI/SPX_KOMBINASI (Alur 3, kombinasi)
```

Urutan kerja (sama untuk keempat jenis): cari folder sesi `label-pengiriman/YYYY-MM-DD/N`
yang **terbaru** secara otomatis → cari file PDF di subfolder jenis itu (untuk
`spesial`, hanya yang namanya mengandung `_SPESIAL_`; untuk jenis lain, semua PDF di
subfolder itu, karena nama filenya variatif dan subfoldernya sudah eksklusif per
jenis) → tampilkan daftar printer yang terhubung ke komputer → pilih nomor printer →
konfirmasi (Y/N) → cetak satu per satu secara berurut.

Pilihan (berlaku sama untuk keempat `.bat`, contoh pakai `cetak-label-urgent.bat`):

- `cetak-label-urgent.bat --folder "label-pengiriman\2026-10-01\3"` — pakai folder
  sesi tertentu, bukan yang terbaru.
- `cetak-label-urgent.bat --tanpa-konfirmasi` — lewati tanya Y/N sebelum mulai cetak
  (tetap tanya pilih printer).
- `cetak-label-urgent.bat --ulang "logs\gagal_cetak_2026-10-01_153000.txt"` — cetak
  ULANG hanya file dari daftar gagal sebelumnya (lihat bagian "Kertas habis" &
  "Kalau ada yang gagal" di [docs/cetak-bulk-label.md](docs/cetak-bulk-label.md)),
  tanpa mencari ulang folder sesi.

**Kertas habis / printer bermasalah di tengah cetak**: program memantau antrian cetak
Windows (PrintManagement) setelah tiap file dikirim. Kalau job itu ditandai bermasalah
(kertas habis, offline, dll), program **berhenti di file itu** dan menampilkan pesan untuk
memperbaikinya (isi ulang kertas, dst) lalu tekan ENTER untuk **melanjutkan dari file yang
sama** — tidak ada file yang terlewat diam-diam, dan file sebelumnya tidak dicetak ulang.
Bisa juga ketik `lewati` untuk melewati 1 file itu saja (dicatat sebagai gagal). Catatan:
deteksi ini bergantung pada driver printer melapor ke Windows — kalau printer tidak
mendukungnya, program tetap jalan tanpa pemantauan otomatis (ada peringatan di log/layar).

**Log jelas tiap file**: setiap file yang diproses (berhasil, gagal, atau dilewati)
dicatat ke `logs/cetak_YYYY-MM.log` (format sama seperti `logs/run_YYYY-MM.log` di
`main.py`, dibagi bersama keempat jenis) sekaligus ditampilkan di layar.

## Jadwal otomatis (Windows Task Scheduler)

*Create Basic Task* → pilih jadwal → *Start a program*:

- Program: `C:\proses-pesanan-otomatis\jalankan.bat`
- Start in: `C:\proses-pesanan-otomatis`
