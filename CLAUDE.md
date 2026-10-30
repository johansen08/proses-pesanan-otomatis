# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Bahasa

Codebase ini (kode, dokumentasi, nama variabel/fungsi, commit, log) sebagian besar ditulis
dalam Bahasa Indonesia secara sengaja — ikuti konvensi yang sudah ada saat menambah/mengubah
kode atau dokumentasi, jangan terjemahkan ke Inggris.

## Apa project ini

Otomatisasi proses pesanan (picklist → resi → label pengiriman) untuk toko online yang pakai
Jubelio sebagai sistem manajemen pesanan. Tidak ada UI web — semuanya CLI Python dijalankan
lewat `.bat` di Windows, dipicu manual oleh tim operasional atau Windows Task Scheduler.
Jubelio diakses lewat API HTTP langsung (bukan browser automation) menggunakan cookie token
dari login; `sniff/` berisi perekam traffic (Playwright) untuk re-reverse-engineer alur kalau
Jubelio berubah.

## Menjalankan & menguji

```bash
# Install sekali di awal
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# Jalankan alur utama (lihat --help untuk semua opsi; lihat juga README.md per-alur)
bat\jalankan.bat
bat\jalankan.bat --label --sku <SKU> --jalankan

# Uji tanpa akses internet (server Jubelio / requests ditiru di dalam test)
.venv\Scripts\python tests\test_proses_label.py
.venv\Scripts\python tests\test_print_spesial.py
.venv\Scripts\python tests\test_sku_spesial.py
.venv\Scripts\python tests\test_jubelio.py
.venv\Scripts\python tests\test_main.py
.venv\Scripts\python tests\test_rekap_master_excel.py
.venv\Scripts\python tests\test_server_ui.py
.venv\Scripts\python tests\test_operator_aktif.py
.venv\Scripts\python tests\test_pilah_satuan.py
.venv\Scripts\python tests\test_peringatan_sisa.py
.venv\Scripts\python tests\test_jalankan_harian.py
.venv\Scripts\python tests\test_alur.py     # definisi langkah/TIPE + menu konsol (WAJIB setelah mengubah langkah/flag)
.venv\Scripts\python tests\test_bat.py      # WAJIB setelah mengubah file .bat apa pun
```

Tidak ada test runner (pytest dsb) terpasang sebagai framework — tiap file test adalah skrip
mandiri yang dijalankan langsung dengan `python`, memakai server Jubelio tiruan
(`JubelioPalsu`/mock di `test_proses_label.py`, berbasis fixture kecil `tests/fixtures/rekaman_report_jubelio.har` hasil ringkasan rekaman HAR sniff 2026-09-26)
atau `requests.get`/`post`/`Session` yang ditiru langsung (`test_jubelio.py`), bukan
`unittest`/`pytest` assertions berjalan via CLI test discovery. Jalankan satu file sekaligus
seperti di atas untuk "menjalankan satu test". `test_sku_spesial.py` dan `test_main.py` murni
logika data/filesystem (tanpa API sama sekali) — cocok dijalankan paling sering karena paling
cepat dan jadi yang pertama dicek kalau mengubah aturan bisnis SKU spesial atau penomoran
sesi label.

**Mode uji vs sungguhan**: hampir semua alur CLI defaultnya adalah mode uji (read-only, hanya
menampilkan rencana) kecuali diberi flag `--jalankan`, yang baru benar-benar mengubah data di
Jubelio. `bat\proses-harian-uji.bat` adalah kembaran `bat\proses-harian.bat` yang selalu memakai mode
uji — pakai ini untuk mencoba perubahan sebelum menjalankan `bat\proses-harian.bat` sungguhan.

## Arsitektur

Lima modul di `src/` (snake_case wajib — lihat
[docs/standar-struktur-proyek.md](docs/standar-struktur-proyek.md) untuk aturan penamaan
project secara umum, root tidak boleh berisi file `.py`):

- `src/jubelio.py` — login API Jubelio & download Excel laporan (HTTP langsung dengan cookie
  `JB_OMNI_ACCESS_TOKEN`, bukan browser). Kalau Jubelio mengubah alurnya dan download gagal,
  rekam ulang lewat `sniff/run_sniff_jubel.bat` untuk menemukan endpoint baru.
- `src/sku_spesial.py` — baca Excel hasil download, hitung mana SKU yang "spesial"
  (lihat [docs/panduan-sku-spesial.md](docs/panduan-sku-spesial.md) untuk aturan bisnisnya),
  buat PDF ringkasan.
- `src/proses_label.py` — modul terbesar (~1000 baris): semua alur picklist → picking → resi →
  label PDF, untuk SEMUA skenario (SKU spesial per-SKU, urgent per-channel/kurir, reguler,
  Shopee Pagi, J&T Resi Siang), plus pencatatan riwayat ke `data/riwayat_picklist.xlsx`. Label
  Lazada diminta dengan `isFromLz=true` (template "Label Pengiriman Lazada", A5) lalu
  disimpan apa adanya (A5) — tanpa `isFromLz` PDF-nya beda dari unduhan manual (sniff
  2026-10-07). Di kertas 100x150 mm label Lazada harus dicetak skala 68% - dilakukan otomatis
  oleh `print_spesial.py` (lihat di bawah).
  **GTL-SiCepat spesial** (2026-10-23): langkah TERSENDIRI "Spesial GTL & SiCepat" (`main.py --urgent --channel gtl-sicepat-spesial`, ada di SEMUA TIPE/EVENT/MALAM, tepat SEBELUM "Urgent GTL & SiCepat") mengecek SKU yang punya
  >= `MIN_RESI` (3) pesanan (1 item, qty 1, bukan bundle, bukan `C225-UB`, nilai != 0; `pisah_spesial_per_sku()` via `items-to-pick`,
  read-only, gagal = semua ke lantai) -> picklist `GTL-SICEPAT-SPESIAL-<SKU>` di subfolder SENDIRI `GTL_SICEPAT_SPESIAL`
  (bukan URGENT; jenis cetak `gtl-spesial`, tampil "GTL-SiCepat Spesial" di UI Cetak & menu `cetak-label.bat`) dibuat DULU, sisanya baru
  dipecah LANTAI1/2/3/LAINNYA (tetap URGENT, jenis `gtl-sicepat`; pemulihan sesi mengenali keduanya lewat `kelas_jenis()`). Detail resi: `detail-resi-spesial-gtl-sicepat.xlsx` di folder sesi
  (`detail_spesial_terpisah()`, ikut ditulis jalur `--lanjut`/pemulihan selama nama label dipertahankan). Tes: `tests/test_proses_label.py`.
  **SPX Pagi spesial** (TIPE 2; langkah TERSENDIRI "Spesial SPX <= 12.00 (Resi Pagi)" = `main.py --shopee-pagi --spesial-saja`, tepat sebelum langkah "SPX <= 12.00 (Resi Pagi)" = `--shopee-pagi` yang kini hanya per lantai; `proses_shopee_pagi(spesial_saja=)`): SKU dengan >= `MIN_RESI` pesanan (aturan sama, `pisah_spesial_per_sku()`) dibuat picklist `SHOPEE-PAGI-SPESIAL-<SKU>` di folder `SPX-PAGI-SPESIAL` (PDF per SKU + `detail-resi-spesial-spx-pagi.xlsx` DI DALAM folder itu; sisa tetap `SHOPEE-PAGI-LANTAI*` di `SPX_PAGI`); jenis cetak `spx-pagi-spesial` (UI: "Shopee Pagi Spesial", menu `cetak-label.bat`). Peta awalan label -> subfolder/detail ada di `SPESIAL_TERPISAH` (`proses_label.py`), dipakai juga GTL-SiCepat.
  **J&T Resi Siang 3 langkah** (TIPE 4 & EVENT - TIPE 4, `main.py --jnt-siang [--spesial-saja|--satuan-saja]`, urut: "Spesial J&T <= 15.00 (Resi Siang)" -> "Satuan J&T <= 15.00 (Resi Siang)" -> "J&T <= 15.00 (Resi Siang)" per lantai; `_subkelompok_jnt_siang()`): spesial = picklist `JNT-SIANG-SPESIAL-<SKU>` di folder `JNT-SIANG-SPESIAL` (+ `detail-resi-spesial-jnt-siang.xlsx` di dalamnya, jenis cetak `jnt-siang-spesial`); satuan = pesanan 1 qty per grup rak, label `JNTSIANG-1QTY-REGULER-<rak>` di folder `JNTSIANG_SATUAN` (jenis cetak `satuan-jnt-siang`; folder satuan per kurir, jadi ikut `pilah_satuan` bebas jam bersama satuan jam sebelumnya - `cari_pdf_satuan(jendela=True)` membuang HANYA satuan gabungan sesi di luar jendela jam); sisanya per lantai di `JNT_SIANG`.
  **Optimasi P1 (2026-10-30)**: (1) `snapshot_siap_proses.py` - Excel Siap Proses + nilai pesanan diunduh SEKALI per TIPE/job (env `SNAPSHOT_SIAP_PROSES` diisi `menu_konsol.py` & `jalankan_harian.py`; `main.muat_data_excel()` memakainya, umur maks 30 menit, tanpa env = unduh baru seperti dulu; resi kandidat yang belum ada dicari terpisah `ambil_nilai_pesanan(semua_halaman=False)`); (2) pra-cek `main.pracek_lewati()` - `--label --tanpa-reguler` dilewati kalau pesanan Siap Proses kurir itu < `MIN_RESI`, `--reguler` kalau 0 (1 request `proses_label.jumlah_siap_proses()`, batas atas, gagal = lanjut); (3) `--jnt-siang --event` membuang J&T NDD (langkah event J&T Siang di `KATALOG_EVENT` membawa `--event`); (4) `pulihkan_sesi.kelas_jenis()` mengenali label per kurir (`satuan-JNT`, `kombinasi-SPXHEMAT`, `spx-standard`, `bawaan_jenis()`).
  **Optimasi P2 (2026-10-30)**: (1) spesial berbasis `items-to-pick` (GTL/SPX Pagi/J&T Siang) diurutkan menurut rak master (`_rak_per_sku()`, `rack_no` kartu item, SKU tanpa rak di akhir) seperti spesial Excel; (2) `buat_picklist()` memakai `_saring_item()` (bukan `_cek_item()` ketat): hanya PESANAN janggal (item lain, qty != 1, bundle bukan PTAA, hilang, lokasi di luar lokasi terbanyak) yang dikeluarkan, SKU tetap jadi selama >= `MIN_RESI`; pesanan SKU spesial yang tidak jadi picklist spesial (SKU dilewati/gagal atau dikeluarkan) dilaporkan `proses(dilepas=)` dan `main.proses_label_sku()` mengeluarkannya dari `resi_spesial_semua` supaya diproses picklist REGULER (dulu hilang sampai peringatan 'pesanan tak tersentuh'); (3) paket cetak `event-urgent-siang` (gtl-spesial, gtl-sicepat, jnt-siang-spesial, satuan-jnt-siang, jnt-siang) di grup EVENT menu cetak; (4) log durasi per fase (`_log_fase()`: picking | resi | pdf, dan fase buat picklist) untuk optimasi berbasis data.
  **Prefetch spesial (B3, 2026-10-30)**: `proses()` mencari pesanan (`cari_pesanan`, hanya BACA) `JENDELA_PREFETCH_SKU` (4) SKU ke depan di thread lain selagi picklist SKU sebelumnya dibuat; hasilnya dipakai `buat_picklist(pesanan_awal=)` HANYA percobaan pertama; pembuatan picklist tetap SERIAL berurutan (nomor PICK/deteksi terlompat); prefetch gagal = cari sendiri.
- `src/print_spesial.py` — program terpisah untuk mencetak ulang (bulk, lewat SumatraPDF,
  parameter `--jenis`) label SPESIAL/GTL-SICEPAT/SATUAN/KOMBINASI yang sudah ada; tidak
  membuat picklist/label baru. Punya 27 jenis (termasuk `spesial-satuan`/`sisa-satuan` = hasil `pilah_satuan.py`, folder tingkat tanggal dilampirkan ke sesi TERAKHIR tanggal itu; paket `pilah-satuan`); `bat\cetak-label.bat` = MENU (grup HARIAN/EVENT/
  PER KURIR/satu jenis; `PAKET` = beberapa jenis berurutan dalam 1 sesi, printer dipilih sekali).
  Default hanya mengambil folder sesi TERBARU; `--semua-sesi [--hari N]` (dan pertanyaan di menu)
  mencetak semua sesi N hari terakhir terlama→terbaru, dedupe lewat `logs/sudah_dicetak.txt`,
  nomor terlompat dicek per sesi. `--file PDF` (diulang) / `--file-dari DAFTAR.txt` mencetak file
  PDF TERTENTU saja (untuk UI pilih-per-file): path harus ada, `.pdf`, dan di dalam
  `label-pengiriman` (kalau tidak, error sebelum cetak apa pun); dedupe sama; tidak bisa digabung
  `--jenis`/`--paket`/`--folder`/`--semua-sesi`/`--ulang`.
  Hanya `bat\cetak-label.bat` + 4 pintasan harian yang boleh ada sebagai `.bat` cetak (dikunci
  `tests/test_print_spesial.py`) — jenis baru cukup ditambah di `JENIS_LABEL` + `MENU`/`PAKET`,
  JANGAN membuat `.bat` per jenis lagi.
  **Cetak terputus & lanjut per halaman** (insiden 2026-10-10: file LANTAI1/2 gagal beruntun): file yang
  tidak selesai ("lewati" saat printer bermasalah, job hilang dari antrean, atau batas tunggu habis)
  dicatat beserta `PagesPrinted`/`TotalPages` (Get-PrintJob) di `logs/cetak_sebagian.json`. Lanjut lewat
  menu "LANJUTKAN cetak yang terputus" / `--lanjut-sebagian [--mulai-dari PDF=HALAMAN ...]` — hanya halaman
  sisa (SumatraPDF `-print-settings "N-total"`), sisa job lama dibuang dulu (`Remove-PrintJob`) supaya tidak
  dobel. Tanpa konsol (stdin=DEVNULL, dari UI) status printer bermasalah ditunggu `TUNGGU_PRINTER_PULIH_S`
  (180 dtk) sebelum file dilewati, dan file gagal dicoba ulang otomatis `PERCOBAAN_ULANG_CETAK`x. Akurasi
  halaman bergantung driver melapor ke spooler (printer thermal tertentu tidak) — makanya halaman mulai
  bisa diganti user. Tes: `tests/test_print_spesial.py`.
  **Dokumen panjang dipotong** (2026-10-15; cetak berhenti ~halaman 103 pada file 100+ halaman, timeout SumatraPDF 120 dtk
  memotong job di spooler): `cetak()` mengirim dokumen > `POTONG_HALAMAN` (50) halaman sebagai beberapa job berurutan
  (`-print-settings "1-50"`, `"51-100"`, ...), tiap potongan dipantau & diulang sendiri (`PERCOBAAN_ULANG_CETAK`) sehingga potongan
  yang sudah tercetak tidak dobel; potongan gagal/dilewati dicatat ke `cetak_sebagian.json` relatif seluruh dokumen (lanjut sebagian
  ikut dipotong). Tes: `uji_cetak_dokumen_panjang_dipotong_per_50_halaman`.
  **Cetak banyak printer** (2026-10-15): UI Cetak tombol "Banyak printer" -> `POST /api/cetak {"files", "printers": [...]}`
  (`server_ui.mulai_cetak_banyak()`): file terpilih dibagi jadi blok BERURUTAN dengan bobot halaman terberat sekecil mungkin
  (`print_spesial.bagi_ke_printer()`, DP), tiap printer = satu job `mulai_cetak` biasa (proses terpisah); semua printer harus
  bebas sebelum satu pun dimulai; printer berlebih (file < printer) tidak dipakai; printer virtual (OneNote/PDF/XPS/Fax) ditandai
  di `/api/printer` ("virtual"). Catatan `cetak_sebagian.json` dikunci (`_kunci_catatan`) karena 5 proses bisa menulis bersamaan.
  **Label Lazada skala 68%** (2026-10-13): PDF Lazada A5, kertas 100x150 mm. `cetak()` mengirim SALINAN
  sementara (`buat_salinan_skala()`, `pypdf`: halaman > 100x150 diperkecil `SKALA_LAZADA` di tengah halaman
  100x150) + `-print-settings noscale` untuk SEMUA file `PICK-..._LAZADA_...` (jenis `lazada`, `--file` dari UI
  kelompok "Urgent Lazada · skala 68%", `--ulang`, lanjut sebagian). Jumlah halaman sama; `sudah_dicetak` tetap
  path asli. SumatraPDF tidak punya opsi skala persen - jangan diganti `-print-settings fit/shrink`.
- `src/pilah_satuan.py` — pilah ulang label SATUAN yang sudah dicetak (`python src/pilah_satuan.py --tanggal YYYY-MM-DD`):
  READ-ONLY ke Jubelio (GET `sales/picklists/{id}`), SEMUA jenis satuan (2026-10-23: gabungan `SATUAN` + per kurir `JNT_/SPX_/SPXHEMAT_/SPXHEMATPAGI_/JNTNDD_SATUAN`, `pdf_satuan_sesi()`) DIGABUNG lintas kurir; TANPA batas jam (2026-10-24: syarat 07.00-12.00 / 20.00-07.00 dihapus, sesi jam berapa pun boleh; `periksa_sesi()` hanya menolak sesi tanpa label satuan atau yang PDF-nya baru diubah); resi kurir selain J&T/SPX tidak dihitung; memetakan tiap halaman PDF SATUAN semua sesi ke SKU lewat "No Resi"
  di teks label, lalu SKU dengan >= `MIN_RESI` resi (gabungan lintas sesi) dibuatkan PDF per SKU + `ringkasan-pilah-satuan.xlsx`
  di `label-pengiriman/<tanggal>/pilah-satuan/`. Tidak membuat picklist/resi baru. Halaman tak cocok = umumnya pesanan batal
  setelah dicetak. Hasil: `SPESIAL-SATUAN-<sesi>/` (PDF per SKU + `detail-resi-spesial-satuan-<sesi>.xlsx`) dan
  `SISA-SATUAN-<sesi>/` (sisa per kelompok rak 2A/3A/1B/2B/3B/LAINNYA); `--sesi 1-2-3`, `--analisis-saja`, `--cache`, `--json`.
  Syarat spesial SAMA dengan spesial biasa (15-10-2026): awalan `C225-UB` dikecualikan, bundle (`bundle_item_id`; BD dst,
  PTAA ikut ditolak), pesanan multi-item & qty bukan 1 ditolak (`item_picklist()` -> `boleh_spesial`, `kelompokkan()`); cache lama tanpa kunci itu diabaikan.
  Pengaman: sesi yang PDF-nya diubah <2 menit lalu ditolak (proses harian masih menulis), server 409 selama job harian/download ulang berjalan;
  pilah ulang di atas PDF yang sudah dikurasi ke folder hasil LAIN ditolak (`KurasiBentrok`, resi dobel); cache analisis maks 15 menit;
  nomor PICK terlompat di antara picklist satuan = peringatan. `--tanpa-pdf` / UI "Hanya Excel" = daftar resi saja (label fisik sudah dicetak,
  tidak menandai dikurasi). PDF SPESIAL-SATUAN bernama `SPESIAL-SATUAN_<rak>_<SKU>_<n>resi.pdf` -> urut cetak rak (1B,2A,2B,3A,3B,LAINNYA) lalu SKU.
  Penanda "dikurasi" (`src/kurasi_satuan.py`, `logs/satuan_dikurasi.json`): PDF satuan asal yang halamannya sudah dipindah ke folder hasil
  dianggap sudah tercetak oleh cetak bulk (`print_spesial.sudah_atau_dikurasi()`) & ditandai pill "dikurasi" di UI Cetak (disembunyikan bersama
  yang tercetak); berlaku selama folder hasilnya ada. Status "tercetak" file hasil dijaga bila dibuat ulang dengan isi identik (sidik SHA-256),
  dilupakan bila isinya berubah/hilang (`lupakan_sudah_dicetak()`).
  **Pilah LANJUTAN** (2026-10-22; `--sesi 3 --lanjutan-dari 1-2`, API `lanjutan_dari`): sesi baru digabung dengan satuan sesi lama TANPA resi yang
  sudah jadi `SPESIAL-SATUAN-1-2` (dibaca dari `detail-resi-spesial-satuan-*.xlsx`/PDF-nya, yang mungkin sudah tercetak) -> `SPESIAL/SISA-SATUAN-1-2+3`
  (bertingkat: `--lanjutan-dari 1-2+3`). Folder spesial lama tidak disentuh; PDF `SISA-SATUAN-1-2` dipindah ke subfolder `sudah-dipilah-lagi`
  (folder tetap ada supaya penanda dikurasi sesi lama berlaku). Ditolak bila SISA lama sudah (sebagian) tercetak (label dobel), sesi baru tumpang
  tindih, atau hasil lama tak ada. Tombol/pilihan di UI web belum ada (baru CLI + API).
  UI: tab "Pilah" (`/api/pilah/sesi|analisis|buat|job` di `server_ui.py`, proses terpisah + cache `logs/pilah_analisis.json`
  supaya "Buat folder" tidak memanggil Jubelio lagi); folder hasil ikut tampil di menu Cetak. Tes: `tests/test_pilah_satuan.py`, `tests/test_server_ui.py`.
- `src/server_ui.py` — server lokal (stdlib, hanya 127.0.0.1) untuk UI desktop di
  `data/prototype-desktop/index.html` (`python src/server_ui.py --buka`). Baru menu Cetak yang sungguhan:
  API `/api/sesi` (3 hari, jenis spesial/satuan/kombinasi/gtl-sicepat, file PDF + status tercetak),
  `/api/printer`, `/api/cetak`, `/api/job`. Cetak terputus: `/api/sebagian` + `/api/sebagian/lanjut` (tombol "Terputus" di UI, lewat `--lanjut-sebagian --mulai-dari`). Cetak SELALU lewat proses terpisah
  `print_spesial.py --file-dari ... --printer ... --tanpa-konfirmasi` (jangan mencetak langsung dari
  server). Penjagaan: Host harus localhost, POST wajib JSON, path divalidasi `pilih_file_spesifik()`,
  satu job sekaligus. Menu Harian di UI SUNGGUHAN lewat `src/jalankan_harian.py` (lihat di bawah).
  **Cetak ulang dari UI** (2026-10-20): saat filter "sembunyikan yang sudah dicetak" dimatikan, file bertanda tercetak boleh dipilih dan
  UI mengirim `ulang:true` (-> `--cetak-ulang-semua`, hanya untuk file terpilih); satuan yang sudah dikurasi tetap tidak dikirim.
  Peluncurnya `proses-pesanan.bat` (`--buka --menu harian`; `--menu cetak` membuka Cetak dulu); server kedua
  dicegah (`Server.allow_reuse_address = False` — di Windows SO_REUSEADDR membolehkan bind ganda ke
  port yang sama), klik kedua hanya membuka tampilan. Job cetak dikunci PER PRINTER (`_jobs[printer]`):
  printer berbeda boleh mencetak bersamaan, printer sama/file sama yang sedang dicetak -> 409. Supaya
  aman paralel, `print_spesial.py` TIDAK boleh memakai `taskkill /IM SumatraPDF.exe` (mematikan cetak
  printer lain; `_matikan_sumatra()` hanya mematikan proses yang command line-nya memuat path file
  itu), `catat_sudah_dicetak()` memakai kunci file (`_kunci_catatan`), dan nama file daftar
  gagal/pilihan unik per proses (PID/uuid). Tes: `tests/test_server_ui.py`.
- `src/alur.py` — SATU-SATUNYA sumber definisi alur menu: `KATALOG`/`KATALOG_EVENT` (nama langkah -> flag
  `main.py`), `PRESET` (isi tiap TIPE 1-4/MALAM, harian & `EVENT - ...`), `susun_argumen()` (menambah
  `--jalankan`, `--lewati-malam` hanya judul TIPE 1/KUSTOM/EVENT 1,3,4, `--non-wajib*`), teks menu konsol.
  Ubah langkah/urutan/flag HANYA di sini (dulu disalin di 6 `.bat` + KATALOG UI). Preset di
  `data/prototype-desktop/index.html` (JS) masih salinan terpisah: `tests/test_alur.py` hanya memastikan
  semua nama langkah ada di sana — kalau mengubah isi TIPE, ubah JS-nya juga. Tes: `tests/test_alur.py`
  (tiap langkah diterima argparse `main.py` sungguhan, aturan bisnis tiap TIPE, menu konsol dengan ketikan palsu).
- `src/menu_konsol.py` — menu konsol (`menu_konsol.py harian|event|malam [--uji]`) yang dipanggil SEMUA
  `bat\proses-harian/event/malam[-uji].bat` (kini peluncur tipis 1 baris, tanpa label/goto/daftar langkah).
  Tiap langkah = SATU proses `main.py` berurutan, langkah gagal tidak menghentikan berikutnya, rekap waktu di
  akhir TIPE, `LABEL_SESI_DIR` dihitung per TIPE yang dijalankan (TIPE pertama memakai sesi saat peluncuran, TIPE berikutnya di cmd yang sama sesi BARU). Nama langkah memakai `<=` (bukan `≤`) di konsol.
  Cek jam memakai `MENU_JAM` (EVENT - TIPE 2 memakai kunci "2", bukan "E2" — perilaku .bat lama dipertahankan).
- `src/coba_ulang.py` — percobaan ulang OTOMATIS di akhir tiap TIPE (konsol `menu_konsol.py` & UI
  `jalankan_harian.py`): setelah semua langkah, SEBELUM `rekap_waktu.py`, tiap picklist TERHENTI/gagal unduh PDF
  selama TIPE itu (`peringatan_gagal.daftar_terhenti()` op "tambah", bukan yatim) dilanjutkan SEKALI lewat
  `main.py --lanjut ... --jalankan` (perintah sama dengan tombol "Download ulang" UI). Mode uji tidak mencoba.
  Yang berhasil hilang dari rekap (`peringatan_gagal.baca_belum_pulih`). Tes: `tests/test_coba_ulang.py`.
- `src/jalankan_harian.py` — menjalankan langkah menu Harian dari UI (SUNGGUHAN, mengubah data di
  Jubelio): tiap langkah di `KATALOG` (dari `alur.py`) = satu proses `main.py <flag> --jalankan` berurutan
  (BUKAN memanggil fungsi langsung), lalu `rekap_waktu.py`. Perilaku sama dengan `menu_konsol.py` (satu
  `susun_argumen()`): `LABEL_SESI_DIR` dihitung sekali per job (job berikutnya selalu sesi baru), langkah gagal tidak menghentikan berikutnya.
  Jangan pernah menjalankan job ini di tes tanpa meniru `_luncurkan` (akan menyentuh Jubelio sungguhan).
  Menu Event di UI memakai judul `EVENT - TIPE 1..4`/`EVENT - MALAM`/`EVENT - KUSTOM` dan `KATALOG_EVENT`
  (flag `--event`; MALAM menolak IRESIS).
- `src/peringatan_picklist.py` — deteksi nomor picklist yang terlompat (picklist batal/gagal
  dibuat karena Jubelio error). Nomor terakhir disimpan di `logs/picklist_terakhir.txt`,
  peringatan di `logs/picklist_terlompat.jsonl`; dicetak paling akhir oleh `main.py` dan juga
  di bawah rekap waktu `src/rekap_waktu.py` (akhir tiap TIPE `bat\proses-harian.bat`).
  Nomor di gap DIVERIFIKASI ke Jubelio (`periksa_nomor(no, k.ada_picklist)`, GET `sales/picklists/{id}`,
  404 = tidak ada; 10 pekerja paralel, batas 30 dtk, sisa = "belum pasti" tetap dilaporkan): nomor yang
  ADA (dibuat PC lain semalam) tidak lagi jadi peringatan/baris "PICKLIST CANCEL". Tidak ada endpoint
  daftar picklist di Jubelio (sudah dicoba 2026-10-14), jadi cek per-ID.
- `src/peringatan_resi.py` — pola yang sama dengan `peringatan_picklist.py`, tapi untuk
  pesanan yang sudah Picking > Selesai namun tidak kunjung dapat nomor resi sampai batas
  tunggu `minta_resi()` di `proses_label.py` habis (dan bukan berstatus batal) — biasanya
  tanda ada request cancel dari customer/channel yang masih diproses Jubelio, sehingga tim
  resi perlu tahu nomor pesanannya untuk diinformasikan ke tim admin/CS. Peringatan di
  `logs/pesanan_tanpa_resi.jsonl`; dicetak di tempat yang sama (akhir `main.py` & rekap
  waktu tiap TIPE). **Resi susulan** (insiden 2026-10-19: 715 pesanan Shopee SPX Hemat tidak dapat resi dalam 180 dtk sejak
  ±15.30, Jubelio menjawab `marketplace_status` "The order is not valid to ship.", resi baru keluar belakangan sehingga tidak ikut
  label PDF): `main.py --resi-susulan [--hari N] [--jalankan]` membaca peringatan di atas, cek ulang tiap pesanan
  (`proses_label.resi_susulan()`), dan yang kini punya resi diunduh ke `label-pengiriman/<hari ini>/SUSULAN/PICK-..._SUSULAN_*.pdf`
  (dicatat di `logs/resi_susulan.jsonl` agar tidak dobel). Tanpa `--jalankan` hanya membaca. `minta_resi()` kini mencatat alasan
  `channel_status/marketplace_status` pesanan yang tak kunjung dapat resi ke log.
- `src/pulihkan_sesi.py` — **pemulihan satu sesi** (`main.py --pulihkan-sesi YYYY-MM-DD/N [--jalankan]`):
  TIDAK membuat picklist baru; untuk semua picklist yang sudah dibuat di sesi itu (daftar dari `logs/picklist_terhenti.jsonl`
  per `sesi` + nama PDF di folder sesi + `PICKLIST.xlsx` sesi — Excel menangkap picklist tanpa PDF/jurnal, mis. spesial yang resinya 0: insiden 2026-10-20, 93 dari 103 terdeteksi;
  tag/subfolder ditebak dari jenis di kolom T dengan contoh picklist sejenis di sesi itu) mengulang tahap sesudahnya lewat `proses_label.pulihkan_picklist()`: selesaikan picking, minta resi
  untuk SEMUA pesanan picklist (bukan hanya yang belum-dicetak seperti `--lanjut`), unduh ulang PDF, `detail-resi-*.xlsx`, `PICKLIST.xlsx`
  dan riwayat — untuk SEMUA picklist sesi itu (yang tidak bermasalah ikut, jadi folder hasilnya satu sesi LENGKAP dengan Excel utuh; tidak ada pilihan sebagian). Semua keluaran ke folder BARU `label-pengiriman/<tanggal>/N-PEMULIHAN` (N = nomor sesi terbesar hari itu + 1); sesi asal
  tidak disentuh. `src/nama_sesi.py` = satu-satunya pola nama folder sesi (`N` atau `N-PEMULIHAN`): cetak bulk, menu Cetak UI
  (judul "N-PEMULIHAN"), `--sesi`, dan penomoran sesi baru memperlakukannya sebagai sesi (pilah_satuan/kurasi tetap hanya sesi `N` biasa).
  **Pilah satuan bisa memakai `N-PEMULIHAN`** (kode sesi `11P`, mis. `--sesi 1-2-11P`; UI mengirim kode itu): berguna kalau satuan sesi N tidak lengkap. Jam tampil
  di UI dari sesi ASAL (penanda `pulihan.json` di folder pemulihan), sesi N dan `NP` tidak boleh dipilih bersamaan (resi sama), tanpa `--sesi`
  pemulihan menggantikan sesi asalnya. Folder hasil: `SPESIAL-SATUAN-<kode>` (mis. `-11P`).
  **UI tab Pulih (tersambung ke data nyata)**: `GET /api/pulih/sesi` (status tiap picklist dari data LOKAL: jurnal terhenti, `PICKLIST.xlsx`, PDF, peringatan tanpa resi),
  `POST /api/pulih/cek|jalankan` (= `main.py --pulihkan-sesi` mode uji / sungguhan, proses terpisah, satu job sekaligus, 409 bila harian/download ulang/pilah berjalan),
  `GET /api/pulih/job` (kemajuan, hasil per picklist `OK/CEK/GAGAL`, folder tujuan). Mode uji membaca Jubelio lewat `proses_label.cek_picklist()` (perkiraan resi sekarang).
  **Paralel** (`--paralel N`, bawaan 5, maks 10): picklist dipulihkan bersamaan; Excel/riwayat ditulis berurutan nomor picklist lewat `proses_label.tulis_hasil_pulihan()` (hasil
  `pulihkan_picklist(tulis=False)`). Progress UI dibaca dari log main.py (`=== Pulihkan`, `[3|5|6] PICK-..`, `OK/GAGAL PICK-..`) — parser WAJIB menoleransi awalan log `YYYY-MM-DD HH:MM LEVEL`.
  Tanpa `--jalankan` hanya melapor (folder tidak dibuat). Satu picklist gagal tidak menghentikan yang lain (exit 1 di akhir).
- `src/peringatan_sisa.py` — penjaga "pesanan tak tersentuh" (insiden 2026-10-09: 2 resi wajib keluar,
  channel Tokopedia asli `TP-...` id 128 & kurir JNE, tidak pernah masuk picklist apa pun TANPA peringatan).
  Dipanggil `main.py --upload-iresis` (langkah terakhir tiap TIPE; tetap jalan walau upload IRESIS dilewati
  di jendela malam): mengambil SEMUA pesanan Siap Proses tanpa filter channel/kurir, memperingatkan yang
  jam pesannya sebelum hari ini 00:00 WIB beserta tebakan alasan (kurir/channel di luar alur, atau sebab
  lain). Peringatan di `logs/pesanan_tak_tersentuh.jsonl`, dicetak ulang di rekap waktu; kegagalan API/login
  hanya jadi warning. Channel `TP-` (128) sekarang ikut alur reguler/J&T Siang lewat
  `CHANNEL_IDS_TIKTOK_TOKOPEDIA`; kurir JNE/LEX punya skenario urgent `JNE-LEX` sendiri (langkah "Urgent JNE
  & LEX" di semua .bat/KATALOG/UI, setelah Lazada & GTL-SiCepat, tanpa jam tunda, channel Lazada dikecualikan lewat
  `KECUALI_CHANNEL_URGENT` karena Lazada juga berkurir JNE/LEX, label `JNE-LEX` di subfolder URGENT, dicetak manual). Tes: `tests/test_peringatan_sisa.py`.
- `src/peringatan_gagal.py` — persistensi lintas-proses (pola sama, `logs/picklist_bermasalah.
  jsonl`) untuk picklist/proses yang TERHENTI/GAGAL (lihat `main.cetak_bermasalah()`, dipicu
  mis. timeout unduh label PDF di `proses_label.py`). `main.cetak_bermasalah()` sendiri sudah
  mencetak peringatan ini LANGSUNG saat terjadi; modul ini cuma menyimpannya ke file supaya
  `src/rekap_waktu.py` bisa mencetaknya ULANG di rekap akhir tiap TIPE — kalau langkah yang
  bermasalah bukan langkah terakhir TIPE itu, peringatannya tenggelam di tengah log dan luput
  dibaca kalau cuma scroll ke rekap paling bawah (insiden 2026-10-06).
- `src/rekap_master_excel.py` — catat tiap picklist ke `PICKLIST.xlsx` PER SESI, langsung di
  folder sesi (`label-pengiriman/YYYY-MM-DD/N/PICKLIST.xlsx`), dibuat dari
  `data/template/picklist-form-kosong.xlsx` (sheet "HARI IN - FORM KOSONG" milik tim: rumus B/E/O/Q/W
  & format sama, supaya baris-barisnya mudah di-copy-paste manual ke file master). Program TIDAK
  PERNAH membuka/menulis file master (dulu salinan ~51 ribu baris: buka ~48 detik + simpan ~67
  detik per proses, insiden 2026-10-06 -> antrean + `--tulis-excel`; sekarang dibuang). Kolom
  F/G/H/L/M/N/T/U diisi, rumus disalin ke tiap baris baru; sel O (MINUS) kuning kalau
  Total Pesanan - Resi Keluar > 0; baris GAGAL/TERHENTI kuning. "PICKLIST CANCEL" (baris kuning)
  HANYA untuk nomor yang terlompat SELAMA proses python berjalan: gap sebelum picklist PERTAMA
  proses cuma diperingatkan di layar (`peringatan_picklist.ambil_nomor_hilang()` mengembalikan
  kosong untuk gap itu — bisa dibuat orang lain di PC lain). `catat(folder_sesi, baris,
  nomor_terlompat)` langsung menambah baris & menyimpan atomik (file sementara lalu
  `os.replace`; file kecil ±60 ms); workbook ditahan di memori per proses, jadi kalau simpan
  gagal (file dibuka di Excel) isinya ikut tersimpan di `catat()` berikutnya / `selesai()`
  (dipanggil `main.py` di akhir proses; peringatan lewat `peringatan_gagal` kalau tetap gagal).
  Template dibuat ulang lewat `python src/buat_template_picklist.py` (butuh `PICKLIST.xlsx`
  salinan master, ±2 menit) — hanya kalau tim mengubah format form; template sengaja disalin ke
  workbook BARU (menghapus baris saja tidak cukup: stylesheet 22 ribu fill membuat tiap save ~1
  detik).
- `src/operator_aktif.py` — daftar operator & operator aktif di `data/operator.json` (tidak dikomit,
  per PC; bawaan PUTRI/ALFIANA/SAHRUL/DENADA/SELVI kalau file belum ada). Dibaca ULANG tiap
  `rekap_master_excel` menulis baris (kolom F), jadi ganti operator langsung berlaku di proses
  berikutnya. Diatur lewat dropdown "Operator" di header UI (`/api/operator`; ganti operator DITOLAK 409
  selama proses harian/download ulang berjalan) atau CLI `main.py --operator [NAMA]` /
  `--tambah-operator NAMA`. Tes: `tests/test_operator_aktif.py`.
- `src/serah_terima.py` — untuk 2 perangkat bergantian memakai folder project yang disinkronkan
  (PC kantor siang, laptop malam; OneDrive/Google Drive/Syncthing). Kunci `logs/serah_terima.json`:
  `main.py --jalankan/--lanjut` dan `print_spesial.py` mengambilnya di awal & melepasnya di akhir;
  ditolak (exit 1) kalau dipegang PERANGKAT LAIN yang masih segar (TTL 3 jam; basi = diambil alih),
  `--abaikan-kunci` untuk memaksa. Proses di perangkat sama boleh paralel (daftar PID). Perangkat lain
  yang selesai <10 menit lalu = peringatan "tunggu sinkron". Nama perangkat = `PERANGKAT` di `.env`
  (kalau kosong: nama komputer). Juga memeriksa file salinan konflik sinkron (`.sync-conflict-`,
  `conflicted copy`, `nama (1).ext`, `nama-NAMAPC.ext`) di logs/, data/, sesi 3 hari terakhir:
  peringatan di awal proses, atau `main.py --cek-sinkron` (exit 1 kalau ada konflik/kunci dipegang
  lain). `.venv/`, `.env`, `data/operator.json` jangan disinkronkan. Tes: `tests/test_serah_terima.py`.
- `src/transfer_stok.py` — jendela Transfer Stok (07.50-08.00, 09.00-09.10, 11.00-11.10, 13.00-13.10,
  15.00-15.10, 16.00-16.10): `main.py --jalankan/--lanjut` menolak (pop up Windows + log, exit 1) dan
  `jalankan_harian.mulai()` melempar `HarianError` (muncul di UI) — kecuali job hanya berisi upload IRESIS.
  Mode uji tidak terpengaruh; paksa dengan `--abaikan-transfer-stok`. Ubah jam di `JENDELA`. Tes: `tests/test_transfer_stok.py`.
- `src/iresis.py` — upload Excel "Daftar Penjualan Faktur" (diunduh lewat
  `jubelio.ambil_url_faktur()` + `unduh_excel()`) ke menu Upload Resi IRESIS (server lokal
  `192.168.3.37`, login form + multipart `receiptFile`, sniff 2026-10-07), lewat
  `main.py --upload-iresis [--jalankan]` — langkah paling akhir tiap TIPE `bat\proses-harian.bat`. Mengunggah 2 file: faktur (`reference=invoice`, 2 hari) lalu pesanan (`reference=order`, 4 hari; sniff 2026-10-07 14:12).
  Sesudah upload, `ambil_total_picklist()` mengambil laporan "Total Picklist" IRESIS (sniff 2026-10-09) lalu `rekap_master_excel.isi_scan()` mengisi kolom P (SCAN) `PICKLIST.xlsx` folder sesi hari-hari terakhir, dicocokkan lewat nomor picklist di kolom L. Kegagalan tidak menghentikan TIPE (cetak_bermasalah + rekap waktu). Butuh `IRESIS_USERNAME`/
  `IRESIS_PASSWORD` di `.env`.
- `src/main.py` — satu-satunya entry point CLI (`argparse`), merutekan ke alur yang sesuai
  berdasarkan flag (`--label`, `--urgent`, `--reguler`, `--shopee-pagi`, `--jnt-siang`,
  `--lanjut`). `ROOT = Path(__file__).resolve().parent.parent` dihitung di sini supaya folder
  data (`data/`, `label-pengiriman/`, dll) selalu dibuat di root project, bukan
  di dalam `src/` — modul lain tidak punya `ROOT` sendiri dan mengandalkan ini.
  `bersihkan_laporan_lama()` (dipanggil tiap `main.py` jalan, setelah log siap) menghapus unduhan di
  `data/laporan-siap-proses|faktur|sku-spesial` yang lebih tua dari `MASA_SIMPAN_LAPORAN_HARI` (3 hari);
  folder sesi label & riwayat tidak disentuh. Tes: `tests/test_main.py`.

**Lima alur CLI berbeda dan independen** (dijabarkan lengkap di README.md): `--label`
(SKU spesial → otomatis lanjut `--reguler` kecuali dibatasi `--sku`), `--urgent` (Lazada /
GTL-SiCepat, selalu manual terpisah, TIDAK pernah bagian dari `--label --jalankan`),
`--reguler` (sisa TikTok Shop & Shopee non-spesial, bisa berdiri sendiri atau otomatis
setelah `--label`), `--shopee-pagi` dan `--jnt-siang` (manual 1x/hari, filter waktu pesan
WIB). Opsi `--kurir jnt`/`--kurir spx` pada `--label`/`--reguler` memisahkan picklist per
kurir saat PEMBUATAN saja — penentuan SKU "spesial" itu sendiri selalu menggabung J&T+SPX
(kecuali mode event di bawah).

**Mode event** (hari 10.10/11.11/12.12 dst; `bat\proses-event.bat`/`bat\proses-event-uji.bat`, 5 pilihan
menu: EVENT - TIPE 1-4 + MALAM): J&T, SPX Hemat, SPX Standard dipisah seharian. Flag `--event` (bersama `--label`/
`--reguler` + `--kurir jnt|spx-hemat|spx-hemat-pagi`) membuat penentuan SKU spesial dihitung PER
KURIR (`kurir_hitung` di `sku_spesial.py`); SPX Standard tidak punya jalur spesial — hanya
`--spx-standard [--pagi]`, dipecah per lantai. `--kurir spx-hemat`/`spx-hemat-pagi`/`jnt-ndd` tanpa
`--event` ditolak (`main.pesan_salah_mode_event`). J&T NEXT-DAY DELIVERY (NDD) dipisah dari J&T lain: di mode event
`--kurir jnt` diterjemahkan `main.terapkan_kurir_event()` menjadi kunci internal `jnt-event` (filter `j&t`, NDD dibuang
di sisi klien; nama file/subfolder tetap `JNT_*`), sedangkan NDD = `--kurir jnt-ndd` (`JNTNDD_*`); tanpa `--event` `jnt`
tetap memuat NDD. `KATALOG_EVENT` (alur.py) punya 3 langkah "J&T NDD" setelah J&T Kombinasi. Kunci kurir event TIDAK boleh ditambahkan ke
`KURIR_LABEL_FILE` (yang menurunkan jenis cetak harian di `print_spesial.py`) — pakai
`KURIR_LABEL_FILE_EVENT`/`KURIR_KODE_FILE_SEMUA`. Detail & jadwal:
[docs/jadwal-proses.md](docs/jadwal-proses.md) bagian "bat\proses-event.bat — mode event".

`bat\proses-harian.bat`/`proses-event.bat`/`proses-malam.bat` (sungguhan) dan kembaran `-uji`-nya (mode uji)
hanya meluncurkan `src\menu_konsol.py`; isi tiap TIPE ada di `src/alur.py` (`PRESET`) — urutan lengkap tiap TIPE
ada di [docs/jadwal-proses.md](docs/jadwal-proses.md). Jalankan `tests/test_alur.py` setelah mengubah langkah/flag
di `alur.py` atau flag di `main.py` (argparse tiap langkah divalidasi di sana).

## Konvensi penting lain

- Semua nama folder/file **baru** (bukan yang dibuat otomatis oleh program saat runtime,
  lihat bagian 5 [docs/standar-struktur-proyek.md](docs/standar-struktur-proyek.md)) harus
  kebab-case untuk folder/docs/bat, snake_case untuk `.py` — detail lengkap ada di dokumen
  itu, termasuk daftar nama yang SENGAJA tidak diubah karena jadi bagian logika program
  (pola nama file picklist/label hasil generate, folder sesi `label-pengiriman/YYYY-MM-DD/N`).
- Gaya kode Python mengikuti PEP 8 — ringkasannya ada di [docs/pep-8.md](docs/pep-8.md).
- **`.bat`: di dalam `for /f ... in ('...')`, path python.exe TIDAK boleh dikutip** — tulis
  `('.venv\Scripts\python.exe -c "..."')`, BUKAN `('".venv\Scripts\python.exe" -c "..."')`.
  for /f menjalankan perintahnya lewat `cmd /c`, yang membuang kutip pertama & terakhir kalau
  perintah diawali `"`, sehingga muncul error `'.venv\Scripts\python.exe" -c "import' is not
  recognized...`. Pola berkutip itu hanya aman untuk baris perintah biasa (di luar for /f).
  Bug ini sudah 3x muncul lagi karena for /f baru menyalin pola baris biasa;
  `tests/test_bat.py` sekarang menolaknya.
- **Lokasi `.bat`**: di root HANYA `proses-pesanan.bat` (tombol buka app, dulu `buka-app.bat`,
  yang diawali `cd /d "%~dp0"`); SEMUA `.bat` lain (`proses-harian`, `proses-malam`, `cetak-label`,
  `jalankan`, `instalasi`, varian `-uji`, event, pintasan cetak) ada di `bat/` dan harus diawali
  `cd /d "%~dp0.."` (bukan `%~dp0`) supaya `.venv\` dan `src\` tetap ketemu. `.bat` baru taruh di
  `bat/`; JANGAN menambah `.bat` lain di root (dikunci `tests/test_bat.py`). `git mv` bisa membuang CRLF — cek ulang (aturan di bawah).
- **`.bat` WAJIB berakhiran baris CRLF, bukan LF.** Di file LF, cmd.exe salah menghitung
  posisi saat mencari label (`call :catat_waktu`, `goto menu`) sehingga eksekusi melompat ke
  baris yang salah — kejadian 2026-10-01: memilih TIPE 1 ikut menjalankan langkah TIPE 2/3/4
  SUNGGUHAN, lalu menu "0. Keluar" malah melanjutkan "8/8 SPX KOMBINASI" (kembali ke `call`
  yang belum selesai). Alat edit (termasuk Claude) sering menulis file baru sebagai LF, dan git
  tidak mengubah working copy saat commit, jadi `.gitattributes` saja tidak cukup — cek
  ulang CRLF setelah mengedit `.bat`; `tests/test_bat.py` menolak `.bat` LF dan memastikan bat menu
  hanya peluncur tipis (tanpa label/goto/daftar langkah — risiko lompat label hilang sejak menu pindah ke Python).
  Jangan juga mengedit `.bat` yang sedang berjalan (cmd membaca ulang file per baris
  berdasarkan posisi byte).
- `.env` (tidak dikomit) berisi `JUBELIO_EMAIL`/`JUBELIO_PASSWORD` — lihat
  [docs/instalasi.md](docs/instalasi.md) untuk setup dari nol di PC lain.
