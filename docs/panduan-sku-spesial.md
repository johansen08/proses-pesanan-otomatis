# Panduan SKU Spesial: Aturan Bisnis & Spesifikasi

Spesifikasi lengkap aturan bisnis "SKU spesial" yang dipakai `src/sku_spesial.py`
(hitung dari Excel) dan `src/proses_label.py` (proses sampai label pengiriman).
Implementasi referensi awal (kerangka download, kode contoh `sku_spesial.py` versi
pertama, checklist generik) ada di dokumen terpisah:
[referensi-implementasi-sku-spesial-awal.md](referensi-implementasi-sku-spesial-awal.md).

---

## 1. Istilah

| Istilah | Arti |
|---|---|
| **Resi** | Satu nilai unik di kolom `No pesanan`. |
| **Baris** | Satu baris di Excel = satu SKU dalam satu resi. |
| **Resi multi-baris** | `No pesanan` yang muncul lebih dari 1 baris → resi berisi lebih dari 1 SKU. |
| **Resi tunggal** | Resi yang memenuhi semua syarat R1–R3 (lihat bagian 3). |
| **SKU spesial** | SKU yang punya minimal 3 resi tunggal. |

---

## 2. Spesifikasi Input

- Format: `.xlsx`, sheet pertama (di contoh bernama `Data1`).
- **Baris header dicari otomatis** (bukan selalu baris 1): program membaca 30 baris pertama
  dan memakai baris pertama yang mengandung header `No pesanan` **dan** `SKU` (implementasi
  saat ini di `sku_spesial.py`, fungsi `_cari_baris_header()` — ditambahkan karena file export
  Jubelio kadang punya baris judul sebelum header).
- Excel ini **bersifat duplikat `No pesanan`**: satu resi dengan N SKU ditulis dalam N baris.

### Kolom yang dipakai

| Kolom | Tipe | Contoh | Keterangan |
|---|---|---|---|
| `No pesanan` | teks | `SP-2609261MWPGK1P`, `TT-586257037476792248-48087` | Kunci resi |
| `SKU` | teks | `C227-BRS3-2` | |
| `qty` | angka | `1` | |
| `Kurir` | teks | `SPX Hemat` | Lihat daftar di bawah |

Kolom lain (`Tanggal`, `Nama Barang`, `Nama Toko`, `Rak`, dst.) tidak dipakai dalam perhitungan.
Kolom boleh berpindah posisi, tetapi **nama header harus sama persis** (spasi di awal/akhir diabaikan).

### Nilai `Kurir` yang pernah muncul

| Nilai asli | Grup |
|---|---|
| `J&T Express Standard`, `J&T Express Hemat`, `J&T Express NEXT-DAY DELIVERY` | **J&T** ✅ |
| `SPX Hemat`, `SPX Standard` | **SPX** ✅ |
| `GoTo Logistics GTL ...`, `SiCepat ...` | Lain ❌ |

Aturan pengelompokan: **teks kurir diawali `J&T` atau `SPX`** (tidak peka huruf besar/kecil).
Varian layanan baru (mis. `SPX Instant`) otomatis ikut grupnya.

---

## 3. Aturan Bisnis

Sebuah resi dihitung sebagai **resi tunggal** jika memenuhi **semua** syarat:

| Kode | Syarat | Cara cek |
|---|---|---|
| **R1** | Resi hanya berisi 1 SKU | `No pesanan` muncul **tepat 1 baris** di seluruh file |
| **R2** | Qty = 1 | `qty == 1` pada baris tersebut |
| **R3** | Kurir J&T atau SPX | `Kurir` diawali `J&T` atau `SPX` |
| **R3b** | Bukan pesanan kreator | Nilai pesanan (`grand_total` dari API Jubelio) **≠ 0**. Excel tidak punya kolom nilai, jadi nilai diambil dari `GET core-api/wms/sales/v2/orders/ready-to-process/` (dicocokkan `salesorder_no` = `No pesanan`). Resi yang nilainya tidak ditemukan di API **juga dikeluarkan** dan jumlahnya dicatat sebagai peringatan di log. |

**Kosong vs 0 pada nilai pesanan** - ini dua kondisi *berbeda* yang keduanya sudah ditangani
(jangan dianggap sama dengan "resi tidak ditemukan"):

- **Field `grand_total` kosong (`None`/`""`) pada pesanan yang ADA di hasil API** - dianggap
  **sama dengan nilai 0** (bukan error, bukan "tidak ditemukan"). Konversinya ada di fungsi
  `_angka()` yang didefinisikan terpisah di dua modul dengan aturan sama:
  `src/jubelio.py` (`ambil_nilai_pesanan`, dipakai alur `--label` via `hitung_sku_spesial`) dan
  `src/proses_label.py` (`saring()`, dipakai saat picklist/label sungguhan dieksekusi). Kalau
  salah satu diubah, yang satunya harus ikut diubah supaya hasil cek "nilai 0 (kreator)" di
  kedua alur tetap konsisten.
- **Pesanan itu sendiri tidak ketemu di API** (beda dari field-nya kosong) - di
  `sku_spesial.hitung_sku_spesial()` menghasilkan `NaN` setelah `map()`, disaring lewat
  `nilai.notna()`, dicatat terpisah sebagai `resi_tanpa_nilai` (bukan `resi_nilai_0`).

Lalu:

| Kode | Syarat |
|---|---|
| **R4** | SKU dinyatakan **spesial** jika jumlah resi tunggalnya **≥ 3** (J&T + SPX **digabung**). |

### Keputusan penting (jangan diubah tanpa persetujuan)

1. **R1 memakai jumlah baris, bukan jumlah SKU unik.** Setiap `No pesanan` yang muncul > 1 baris
   langsung gugur, apa pun isinya. Contoh: `SP-2609250XDF1N9W` berisi `C227-BRS3-1` (qty 1) dan
   `C227-BRS3-2` (qty 1) → **tidak dihitung** untuk kedua SKU.
2. **R2 dicek setelah R1.** Resi 1 baris dengan qty 2 atau lebih → gugur.
3. **R4 digabung**, bukan per kurir. (Jika per kurir: SKU spesial bila J&T ≥ 3 **atau** SPX ≥ 3 —
   pada data contoh hasilnya menjadi 18 SKU karena `BM-LCB009` = 2 J&T + 2 SPX.)
4. Filter kurir dilakukan **per resi setelah** R1, jadi resi multi-baris dengan kurir apa pun tetap gugur.

---

## 4. Algoritma

```
INPUT : tabel baris (No pesanan, SKU, qty, Kurir)

1. Bersihkan data
   - trim spasi pada No pesanan, SKU, Kurir
   - ubah qty ke angka (nilai tak valid → kosong)
   - buang baris yang No pesanan-nya kosong

2. Untuk setiap baris: jml_baris_resi = jumlah baris dengan No pesanan yang sama
3. Untuk setiap baris: grup_kurir = "J&T" | "SPX" | "Lain" (berdasarkan awalan teks)

4. f1 = baris dengan jml_baris_resi == 1          # R1
5. f2 = f1 dengan qty == 1                         # R2
6. f3 = f2 dengan grup_kurir != "Lain"             # R3
6b. ambil grand_total dari API untuk No pesanan di f3
    f3 = f3 tanpa resi dengan grand_total == 0 atau tidak ditemukan   # R3b

7. per_sku = hitung jumlah baris f3 per SKU        # 1 baris f3 = 1 resi
8. tabel   = per_sku dengan jumlah >= 3            # R4
             urutkan: **No Rak naik, lalu SKU naik (A–Z)** — bukan Jumlah Resi turun.
             ("No Rak" = rak yang paling sering dipakai SKU itu di kolom `Rak`, diambil
             dengan `_rak_dominan()`; urutan ini dipakai supaya proses per SKU di
             `proses_label.py` mengikuti urutan fisik rak gudang, bukan urutan jumlah resi.)

9. Total SKU Spesial  = banyaknya baris tabel
   Total Resi Spesial = jumlah kolom Jumlah Resi

10. Validasi: semua resi spesial harus jml_baris_resi == 1 dan No pesanan unik
             → jika gagal, hentikan program (jangan buat PDF)

OUTPUT: tabel (SKU, Jumlah Resi) + 2 total + ringkasan penyaringan
```

---

## 5. Spesifikasi Output (PDF)

PDF **hanya** berisi (sesuai implementasi saat ini di `sku_spesial.py::buat_pdf`):

1. **Tanggal** dan **Jam** laporan dibuat
2. **Tabel**

   | No Rak | SKU | Jumlah Resi |
   |---|---|---|
   | … | … | … |
   | **Total SKU Spesial** | | **n** |
   | **Total Resi Spesial** | | **n** |

   Baris data diberi warna latar per lantai gudang (digit pertama `No Rak`: `1`→biru,
   `2`→hijau, `3`→oranye, lainnya tanpa warna) — murni bantuan visual, tidak mengubah
   aturan bisnis R1–R4.

Tanpa judul, nama file sumber, keterangan syarat, atau ringkasan penyaringan
(ringkasan penyaringan dicatat di file log saja).

Nama file: `laporan-sku-spesial/SKU_Spesial_YYYY-MM-DD_HHMM.pdf`.

### Detail resi per sesi (Excel, dibuat saat `--label --jalankan`)

Implementasi: `proses_label.py::catat_detail_spesial()`, dipanggil dari `lanjutkan_picklist()`
HANYA untuk picklist ber-tag `TAG_SPESIAL` (Alur 1). Berbeda dari PDF ringkasan di atas (yang
berbasis SKU), file ini berbasis **resi** - 1 baris per pesanan yang resinya BENAR-BENAR keluar
& labelnya berhasil diunduh (bukan yang batal/belum dapat resi - sudah ditangani
`peringatan_resi.py`). Tujuannya supaya tim resi tidak perlu buka PDF label satu-satu untuk
tahu SKU & nomor picklist asal tiap resi.

1 file per sesi, langsung di folder sesi (`label-pengiriman/<tanggal>/<sesi>/`, BUKAN di
subfolder `SPESIAL`):

| Kolom | Isi |
|---|---|
| `No Picklist` | `picklist_no` picklist SKU spesial yang bersangkutan |
| `SKU` | SKU picklist itu |
| `No Pesanan` | `salesorder_no` (nomor pesanan asli, sama dengan kolom `No pesanan` di Excel sumber) |
| `No Resi` | `tracking_no` |

Baris ditulis sekaligus per picklist (tidak diselang picklist lain), dan picklist diproses
berurutan per SKU (urutan rak) - jadi isinya otomatis terkelompok per `No Picklist`+`SKU` tanpa
perlu sorting tambahan.

**Nama file berbeda tergantung jumlah resi yang benar-benar keluar** (dibandingkan ke `MIN_RESI`,
bukan nilai baru):

- **`detail-resi-spesial.xlsx`** - jumlah baris (resi keluar) di picklist itu masih **>= MIN_RESI**:
  SKU tetap sah spesial.
- **`detail-resi-bukan-spesial.xlsx`** - jumlah baris **< MIN_RESI** (mis. dari 4 pesanan yang
  awalnya diperkirakan spesial, 2 batal + 1 request-cancel saat proses, tinggal 1 yang benar-benar
  tercetak): SKU itu gugur jadi tidak spesial lagi, tapi baris yang sudah tercetak labelnya tetap
  dicatat di sini (bukan dibuang), supaya kelihatan saat memilah resi fisik hasil cetak.

Mode uji (tanpa `--jalankan`) tidak pernah menulis file ini - tidak ada resi/label sungguhan
yang bisa dicatat. Picklist yang diselesaikan lewat `--lanjut` (resume generik via
`lanjutkan()`, bukan `proses()`) juga tidak mengisi file ini, karena `lanjutkan()` tidak tahu
picklist itu dari alur mana (tidak memakai `tag` - batasan yang sama berlaku untuk penanda
nama file & subfolder `SPESIAL`, lihat bagian 1 README).

> **Sumber angka di tabel** (implementasi di `main.py`, bukan `sku_spesial.py`): dasarnya
> **kandidat** hasil algoritma bagian 4 (langkah 1-8 dokumen ini) untuk `main.py` biasa dan
> mode uji `--label`. Tapi untuk `--label --jalankan` (proses picklist sungguhan), PDF baru
> dibuat SETELAH proses selesai, dari jumlah pesanan yang **benar-benar berhasil dipicklist**
> per SKU — bisa lebih kecil dari kandidat kalau ada yang dilewati (< 3 resi tersisa), gagal,
> atau kena stok kosong/invalidSO. Lihat README bagian "Proses SKU spesial sampai label
> pengiriman" untuk detail.

---

## 6. Data Acuan untuk Pengujian

Gunakan file `laporan siap proses.xlsx` (data 26-09-2026) sebagai **golden test**.
Program dianggap benar jika hasilnya persis seperti ini.

### Ringkasan penyaringan

| Tahap | Jumlah |
|---|---:|
| Total baris | 747 |
| Total resi (No pesanan unik) | 445 |
| Resi multi-baris (gugur R1) | 128 resi / 430 baris |
| Lolos R1 (1 baris) | 317 |
| Lolos R2 (qty = 1) | 275 |
| Lolos R3 (J&T/SPX) | 262 |
| **Resi spesial** | **207** |
| **SKU spesial** | **19** |

### Tabel hasil

| No | SKU | Jumlah Resi |
|---:|---|---:|
| 1 | C227-BRS3-2 | 52 |
| 2 | GL-FNF-6 | 30 |
| 3 | GL-FNF-3 | 26 |
| 4 | T01-PTAA-5 | 12 |
| 5 | T01-PTAE-2 | 12 |
| 6 | C227-BRS3-1 | 10 |
| 7 | C226-GTJ-1 | 9 |
| 8 | T01-BKAG-2 | 9 |
| 9 | MX-5011-2 | 7 |
| 10 | MX-5054-1 | 6 |
| 11 | BM-AKS28-5 | 5 |
| 12 | C222-AK32-10 | 5 |
| 13 | BM-LCB009 | 4 |
| 14 | MX-5043-2 | 4 |
| 15 | T01-PTAD-3 | 4 |
| 16 | C223-ANT78-1 | 3 |
| 17 | MX-5040-5 | 3 |
| 18 | T01-PTAA-20 | 3 |
| 19 | T01-PTAD-2 | 3 |
| | **Total SKU Spesial** | **19** |
| | **Total Resi Spesial** | **207** |

### Kasus uji kecil (unit test)

| No pesanan | SKU | qty | Kurir | Hasil yang diharapkan |
|---|---|---:|---|---|
| A | X | 1 | SPX Hemat | ✅ dihitung untuk X |
| B | X | 1 | J&T Express Hemat | ✅ dihitung untuk X |
| C | X | 1 | spx standard | ✅ dihitung (huruf kecil tetap cocok) |
| D | X | 1 | SPX Hemat | ❌ D muncul 2 baris |
| D | Y | 1 | SPX Hemat | ❌ D muncul 2 baris |
| E | X | 2 | SPX Hemat | ❌ qty 2 |
| F | X | 1 | *(kosong)* | ❌ kurir kosong |
| G | X | 1 | GoTo Logistics GTL Hemat | ❌ kurir lain |
| " H" | Z | 1 | SPX Hemat | ✅ untuk Z (spasi di-trim) |
| I | Z | 1 | SPX Hemat | ✅ untuk Z |

Hasil: **X = 3 resi → spesial**, Z = 2 resi → tidak spesial. Total SKU spesial 1, total resi spesial 3.

---

## 7. Parameter yang Bisa Diubah

| Parameter | Default | Lokasi |
|---|---|---|
| Minimal resi per SKU | `3` | `MIN_RESI` |
| Kurir yang dihitung | `("J&T", "SPX")` | `KURIR_DIIZINKAN` |
| Mode hitung kurir | gabungan | ubah logika R4 jika ingin per kurir |
| Kolom wajib | `No pesanan, SKU, qty, Kurir` | `KOLOM_WAJIB` |
| Urutan tabel/PDF | No Rak naik, lalu SKU naik | `hitung_sku_spesial()` (`sort_values`) |
| Warna latar per lantai (kosmetik) | lantai 1/2/3 → biru/hijau/oranye | `WARNA_LANTAI` |
| Batas baris pencarian header | 30 baris pertama | `_cari_baris_header()` |
