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
jalankan.bat
jalankan.bat --label --sku <SKU> --jalankan

# Uji tanpa akses internet (server Jubelio / requests ditiru di dalam test)
.venv\Scripts\python tests\test_proses_label.py
.venv\Scripts\python tests\test_print_spesial.py
.venv\Scripts\python tests\test_sku_spesial.py
.venv\Scripts\python tests\test_jubelio.py
.venv\Scripts\python tests\test_main.py
.venv\Scripts\python tests\test_rekap_master_excel.py
.venv\Scripts\python tests\test_bat.py      # WAJIB setelah mengubah file .bat apa pun
```

Tidak ada test runner (pytest dsb) terpasang sebagai framework — tiap file test adalah skrip
mandiri yang dijalankan langsung dengan `python`, memakai server Jubelio tiruan
(`JubelioPalsu`/mock di `test_proses_label.py`, berbasis rekaman HAR di `sniff/sniff_output/`)
atau `requests.get`/`post`/`Session` yang ditiru langsung (`test_jubelio.py`), bukan
`unittest`/`pytest` assertions berjalan via CLI test discovery. Jalankan satu file sekaligus
seperti di atas untuk "menjalankan satu test". `test_sku_spesial.py` dan `test_main.py` murni
logika data/filesystem (tanpa API sama sekali) — cocok dijalankan paling sering karena paling
cepat dan jadi yang pertama dicek kalau mengubah aturan bisnis SKU spesial atau penomoran
sesi label.

**Mode uji vs sungguhan**: hampir semua alur CLI defaultnya adalah mode uji (read-only, hanya
menampilkan rencana) kecuali diberi flag `--jalankan`, yang baru benar-benar mengubah data di
Jubelio. `proses-harian-uji.bat` adalah kembaran `proses-harian.bat` yang selalu memakai mode
uji — pakai ini untuk mencoba perubahan sebelum menjalankan `proses-harian.bat` sungguhan.

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
  Shopee Pagi, J&T Resi Siang), plus pencatatan riwayat ke `riwayat_picklist.xlsx`. Label
  Lazada diminta dengan `isFromLz=true` (template "Label Pengiriman Lazada", A5) lalu
  disimpan apa adanya; `cetak-label-lazada.bat` memperkecilnya ke skala 68% di kertas 100x150 mm tepat sebelum cetak: `print_spesial.py --jenis lazada` merender PDF ke gambar 68% (pypdfium2) dan mencetaknya lewat `src/cetak_gambar.ps1` (driver Windows, BUKAN SumatraPDF — skala dari SumatraPDF terbukti tidak diterapkan) —
  tanpa `isFromLz` PDF-nya beda dari unduhan manual (sniff 2026-10-07).
- `src/print_spesial.py` — program terpisah untuk mencetak ulang (bulk, lewat SumatraPDF,
  parameter `--jenis`) label SPESIAL/GTL-SICEPAT/SATUAN/KOMBINASI yang sudah ada; tidak
  membuat picklist/label baru.
- `src/peringatan_picklist.py` — deteksi nomor picklist yang terlompat (picklist batal/gagal
  dibuat karena Jubelio error). Nomor terakhir disimpan di `logs/picklist_terakhir.txt`,
  peringatan di `logs/picklist_terlompat.jsonl`; dicetak paling akhir oleh `main.py` dan juga
  di bawah rekap waktu `src/rekap_waktu.py` (akhir tiap TIPE `proses-harian.bat`).
- `src/peringatan_resi.py` — pola yang sama dengan `peringatan_picklist.py`, tapi untuk
  pesanan yang sudah Picking > Selesai namun tidak kunjung dapat nomor resi sampai batas
  tunggu `minta_resi()` di `proses_label.py` habis (dan bukan berstatus batal) — biasanya
  tanda ada request cancel dari customer/channel yang masih diproses Jubelio, sehingga tim
  resi perlu tahu nomor pesanannya untuk diinformasikan ke tim admin/CS. Peringatan di
  `logs/pesanan_tanpa_resi.jsonl`; dicetak di tempat yang sama (akhir `main.py` & rekap
  waktu tiap TIPE).
- `src/peringatan_gagal.py` — persistensi lintas-proses (pola sama, `logs/picklist_bermasalah.
  jsonl`) untuk picklist/proses yang TERHENTI/GAGAL (lihat `main.cetak_bermasalah()`, dipicu
  mis. timeout unduh label PDF di `proses_label.py`). `main.cetak_bermasalah()` sendiri sudah
  mencetak peringatan ini LANGSUNG saat terjadi; modul ini cuma menyimpannya ke file supaya
  `src/rekap_waktu.py` bisa mencetaknya ULANG di rekap akhir tiap TIPE — kalau langkah yang
  bermasalah bukan langkah terakhir TIPE itu, peringatannya tenggelam di tengah log dan luput
  dibaca kalau cuma scroll ke rekap paling bawah (insiden 2026-10-06).
- `src/rekap_master_excel.py` — catat tiap picklist ke `PICKLIST.xlsx` (sheet `HARI INI`,
  kolom F/G/H/L/M/N/T/U), SALINAN kerja dari file master "PICK LIST - EXCEL 2022 - 2024 -
  MASTER - TERBARU NEW.xlsx" yang tetap dijalankan MANUAL oleh tim — program TIDAK PERNAH
  menulis ke file master langsung, tim verifikasi `PICKLIST.xlsx` dulu baru copy manual kalau
  sudah sesuai (dibuat otomatis dari master kalau belum ada/sudah dihapus tim). Picklist
  terlompat (dari `peringatan_picklist.ambil_nomor_hilang()`) jadi baris kuning "PICKLIST
  CANCEL" tersendiri, meniru pola manual yang sudah ada di file master. Karena file itu besar
  (~51 ribu baris: buka ~48 detik + simpan ~67 detik), `catat()` cuma menambah antrean
  `logs/antrian_picklist_excel.jsonl`; workbook baru dibuka & disimpan SEKALI per TIPE oleh
  `terapkan()` lewat `main.py --tulis-excel --jalankan` (langkah terakhir tiap TIPE
  `proses-harian.bat`), disimpan atomik (file sementara lalu `os.replace`). Dulu dibuka &
  disimpan di TIAP proses — ±15-20 menit per TIPE habis untuk Excel, dan file pernah rusak
  (insiden 2026-10-06). Kalau gagal (file dibuka di Excel/rusak), antrean tidak dibuang.
- `src/iresis.py` — upload Excel "Daftar Penjualan Faktur" (diunduh lewat
  `jubelio.ambil_url_faktur()` + `unduh_excel()`) ke menu Upload Resi IRESIS (server lokal
  `192.168.3.37`, login form + multipart `receiptFile`, sniff 2026-10-07), lewat
  `main.py --upload-iresis [--jalankan]` — langkah paling akhir tiap TIPE `proses-harian.bat`.
  Kegagalan tidak menghentikan TIPE (cetak_bermasalah + rekap waktu). Butuh `IRESIS_USERNAME`/
  `IRESIS_PASSWORD` di `.env`.
- `src/main.py` — satu-satunya entry point CLI (`argparse`), merutekan ke alur yang sesuai
  berdasarkan flag (`--label`, `--urgent`, `--reguler`, `--shopee-pagi`, `--jnt-siang`,
  `--lanjut`). `ROOT = Path(__file__).resolve().parent.parent` dihitung di sini supaya folder
  data (`laporan-siap-proses/`, `label-pengiriman/`, dll) selalu dibuat di root project, bukan
  di dalam `src/` — modul lain tidak punya `ROOT` sendiri dan mengandalkan ini.

**Lima alur CLI berbeda dan independen** (dijabarkan lengkap di README.md): `--label`
(SKU spesial → otomatis lanjut `--reguler` kecuali dibatasi `--sku`), `--urgent` (Lazada /
GTL-SiCepat, selalu manual terpisah, TIDAK pernah bagian dari `--label --jalankan`),
`--reguler` (sisa TikTok Shop & Shopee non-spesial, bisa berdiri sendiri atau otomatis
setelah `--label`), `--shopee-pagi` dan `--jnt-siang` (manual 1x/hari, filter waktu pesan
WIB). Opsi `--kurir jnt`/`--kurir spx` pada `--label`/`--reguler` memisahkan picklist per
kurir saat PEMBUATAN saja — penentuan SKU "spesial" itu sendiri selalu menggabung J&T+SPX.

`proses-harian.bat` (sungguhan) dan `proses-harian-uji.bat` (mode uji, struktur sama) adalah
menu interaktif 4 TIPE yang masing-masing menjalankan rangkaian flag `jalankan.bat` di atas
secara berurutan dalam satu konfirmasi Y/N — urutan lengkap tiap TIPE ada di
[docs/jadwal-proses.md](docs/jadwal-proses.md).

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
- **`.bat` WAJIB berakhiran baris CRLF, bukan LF.** Di file LF, cmd.exe salah menghitung
  posisi saat mencari label (`call :catat_waktu`, `goto menu`) sehingga eksekusi melompat ke
  baris yang salah — kejadian 2026-10-01: memilih TIPE 1 ikut menjalankan langkah TIPE 2/3/4
  SUNGGUHAN, lalu menu "0. Keluar" malah melanjutkan "8/8 SPX KOMBINASI" (kembali ke `call`
  yang belum selesai). Alat edit (termasuk Claude) sering menulis file baru sebagai LF, dan git
  tidak mengubah working copy saat commit, jadi `.gitattributes` saja tidak cukup — cek
  ulang CRLF setelah mengedit `.bat`; `tests/test_bat.py` menolak `.bat` LF dan
  menyimulasikan tiap TIPE di cmd.exe (python palsu) untuk memastikan urutan langkahnya.
  Jangan juga mengedit `.bat` yang sedang berjalan (cmd membaca ulang file per baris
  berdasarkan posisi byte).
- `.env` (tidak dikomit) berisi `JUBELIO_EMAIL`/`JUBELIO_PASSWORD` — lihat
  [docs/instalasi.md](docs/instalasi.md) untuk setup dari nol di PC lain.
