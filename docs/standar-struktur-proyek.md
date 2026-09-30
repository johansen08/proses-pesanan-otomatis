# Standar Struktur & Penamaan Project

Aturan ini dipakai supaya nama folder/file di project ini konsisten dan langsung
menjelaskan isinya tanpa perlu buka dulu. Berlaku untuk penamaan **baru** ke depan;
lihat bagian "Kenapa ada yang belum sesuai" untuk pengecualian yang sudah ada.

## 1. Folder

- **Huruf kecil semua**, kata dipisah tanda hubung `-` (kebab-case): `laporan-siap-proses`,
  bukan `Laporan_Siap_Proses` atau `LaporanSiapProses`.
- **Tidak pernah pakai spasi** di nama folder — spasi bermasalah di path Windows,
  command line, dan git.
- **Nama harus menjelaskan ISI**, bukan format filenya. Contoh yang diperbaiki:
  - `excel/` → **`laporan-siap-proses/`** (isinya laporan Siap Proses dari Jubelio,
    kebetulan formatnya `.xlsx` — nama folder tidak perlu menyebut format file)
  - `laporan/` → **`laporan-sku-spesial/`** (isinya PDF ringkasan SKU spesial, dipisah
    jelas dari `laporan-siap-proses/` supaya tidak tertukar)
- Folder 1 kata (`docs`, `logs`, `tests`, `sniff`) tidak butuh tanda hubung — aturan
  kebab-case otomatis terpenuhi kalau cuma 1 kata.

## 2. File kode Python (`.py`)

- **snake_case** (huruf kecil + garis bawah `_`): `sku_spesial.py`, `proses_label.py`.
  Ini mengikuti konvensi resmi bahasa Python (PEP 8), bukan pilihan bebas seperti folder
  — jangan diubah ke kebab-case meski aturan folder di atas pakai `-`.

## 3. File dokumentasi (`.md`)

- Dikumpulkan dalam folder **`docs/`**, kecuali `README.md` yang tetap di root (huruf
  besar semua) — itu konvensi universal supaya editor/GitHub/file explorer menampilkannya
  otomatis sebagai halaman utama project.
- Nama file dalam `docs/`: huruf kecil, kebab-case, mis. `docs/jadwal-proses.md`,
  `docs/panduan-sku-spesial.md`. Tidak perlu awalan/angka urut — nama sudah cukup
  jelas menjelaskan isinya.

## 4. Skrip batch (`.bat`)

- Huruf kecil, 1-2 kata jelas: `menu.bat`, `run.bat`, `setup.bat`, `uji.bat`. Sudah
  konsisten, dipertahankan apa adanya.

## 5. File yang dibuat OTOMATIS oleh program saat runtime

Nama file laporan/label yang di-generate `main.py`/`jubelio.py`/`proses_label.py` (mis.
`laporan_siap_proses_2026-09-30_065510.xlsx`, `SKU_Spesial_2026-09-30_0654.pdf`,
`PICK-000155300_1QTY-REGULER_...pdf`, folder sesi `2026-09-30_5/`) **TIDAK** mengikuti
aturan kebab-case di atas dan **sengaja tidak diubah** oleh standarisasi ini, karena:

- Formatnya (garis bawah `_` sebagai pemisah tanggal/jam/kode) adalah bagian dari
  **logika program**, bukan sekadar rapikan folder — mengubahnya berarti mengubah kode
  di `main.py`/`jubelio.py`/`proses_label.py`.
- Beberapa nama folder di antaranya di-parse ulang oleh kode (mis. `sesi_label_baru()`
  di `main.py` mencari pola `YYYY-MM-DD_N` di `label/`) — ganti pemisah bisa merusak
  fungsi itu.

Kalau suatu saat pola ini mau distandarkan juga, lakukan sebagai perubahan kode
tersendiri (bukan bagian dari rapi-rapi struktur folder), dan uji dulu lewat
`tests/test_proses_label.py`.

## 6. Struktur saat ini

```
proses-pesanan-otomatis/
├─ README.md                      # halaman utama, tetap di root
├─ docs/                          # dokumentasi lain, semua kebab-case
│  ├─ standar-struktur-proyek.md  # dokumen ini
│  ├─ instalasi.md
│  ├─ jadwal-proses.md
│  ├─ panduan-sku-spesial.md
│  └─ analisa-alur-cetak-label.md
├─ main.py / jubelio.py / sku_spesial.py / proses_label.py   # kode, snake_case
├─ menu.bat / run.bat / setup.bat / uji.bat                  # skrip, huruf kecil
├─ tests/                         # kasus uji
├─ sniff/                         # perekam alur Jubelio (tools dev)
├─ laporan-siap-proses/           # Excel hasil download Jubelio (dibuat otomatis)
├─ laporan-sku-spesial/           # PDF ringkasan SKU spesial (dibuat otomatis)
├─ label/                         # PDF label pengiriman per picklist (dibuat otomatis)
├─ logs/                          # log tiap eksekusi (dibuat otomatis)
└─ riwayat_picklist.xlsx          # riwayat semua picklist
```

## 7. Kenapa ada yang belum sesuai

- **`label/`** seharusnya jadi `label-pengiriman/` (biar konsisten dengan
  `laporan-siap-proses/`/`laporan-sku-spesial/`), tapi rename ini **ditunda** karena
  saat standarisasi ini dibuat folder tersebut sedang dipakai proses `python.exe`/
  `menu.bat` yang masih berjalan (tidak aman dipindah sambil ada proses yang mungkin
  sedang menulis PDF ke dalamnya). Untuk menyelesaikan setelah proses yang berjalan
  selesai:

  ```powershell
  cd C:\proses-pesanan-otomatis
  Rename-Item label label-pengiriman
  ```

  Lalu di `main.py`, ganti baris `FOLDER_LABEL = ROOT / "label"` menjadi
  `FOLDER_LABEL = ROOT / "label-pengiriman"` (baris ini sudah ditandai `# TODO`) dan
  hapus catatan bagian ini setelah selesai.
