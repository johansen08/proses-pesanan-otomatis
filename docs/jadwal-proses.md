# Jadwal Proses Pesanan Harian (Tim Resi)

Dokumentasi jadwal operasional tim resi: jam berapa proses apa dijalankan,
dipetakan ke menu/perintah program yang sebenarnya. Ini dokumentasi
**kebijakan/SOP tim**, bukan kode — perubahan jadwal cukup edit file ini,
tidak perlu ubah program.

**Diperbarui 2026-09-30**: `proses-harian.bat` dirombak jadi **3 sesi** (menggantikan
menu 7-pilihan sebelumnya): **SESI PAGI**, **JAM 13.00**, **SESI SORE** —
tiap sesi menjalankan seluruh langkahnya berurut dengan **1 kali klik +
1 konfirmasi Y/N**. Mulai **JAM 13.00** dan **SESI SORE**, kurir **J&T dan
SPX dipisah** saat pembuatan picklist (pakai `--kurir jnt` / `--kurir spx`)
— **SESI PAGI** tetap menggabung J&T+SPX seperti sebelumnya. Penentuan SKU
mana yang "spesial" (dari Excel) **tidak berubah**, tetap menggabung
J&T+SPX; `--kurir` cuma membatasi resi kurir mana yang benar-benar
dipicklist saat itu.

## Istilah tim → proses-harian.bat / perintah program

| Istilah tim | Perintah (`jalankan.bat ...`) |
|---|---|
| Urgent Lazada | `--urgent --channel lazada --jalankan` |
| Urgent GTL & SiCepat | `--urgent --channel gtl-sicepat --jalankan` |
| SPX & J&T spesial (digabung) | `--label --tanpa-reguler --jalankan` |
| SPX & J&T 1 SKU 1 qty reguler (digabung) | `--reguler --bagian 1qty --jalankan` |
| SPX & J&T kombinasi reguler (digabung) | `--reguler --bagian kombinasi --jalankan` |
| SPX ≤ 12.00 (SPX Resi Pagi, dulu disebut Shopee Pagi) | `--shopee-pagi --jalankan` |
| J&T spesial (dipisah) | `--label --kurir jnt --tanpa-reguler --jalankan` |
| J&T 1 SKU 1 qty reguler (dipisah) | `--reguler --bagian 1qty --kurir jnt --jalankan` |
| J&T kombinasi reguler (dipisah) | `--reguler --bagian kombinasi --kurir jnt --jalankan` |
| SPX spesial (dipisah) | `--label --kurir spx --tanpa-reguler --jalankan` |
| SPX 1 SKU 1 qty reguler (dipisah) | `--reguler --bagian 1qty --kurir spx --jalankan` |
| SPX kombinasi reguler (dipisah) | `--reguler --bagian kombinasi --kurir spx --jalankan` |

## proses-harian.bat — 3 sesi

```
1. SESI PAGI
2. JAM 13.00
3. SESI SORE
4. Keluar
```

Tiap pilihan menjalankan urutan langkah di bawah **berurut, 1 kali klik +
1 konfirmasi Y/N**. Picklist urgent (Lazada, GTL/SiCepat) **selalu** ikut
di awal tiap sesi — tidak ada lagi cara memicunya sendirian lewat menu
(masih bisa manual lewat `jalankan.bat --urgent ...` kalau perlu).

### 1. SESI PAGI (J&T + SPX digabung, seperti semula)

1. URGENT LAZADA
2. URGENT GTL & SICEPAT
3. SPX - J&T SPESIAL
4. SPX - J&T 1 QTY REGULER
5. SPX - J&T KOMBINASI

### 2. JAM 13.00 (J&T dan SPX dipisah + SPX Resi Pagi)

1. URGENT LAZADA
2. URGENT GTL & SICEPAT
3. SPX PAGI (RESI SHOPEE ≤ 12.00)
4. J&T SPESIAL
5. J&T 1 QTY REGULER
6. J&T KOMBINASI
7. SPX - SPESIAL
8. SPX - 1 QTY REGULER
9. SPX - KOMBINASI

### 3. SESI SORE (J&T dan SPX dipisah, tanpa SPX Resi Pagi)

1. URGENT LAZADA
2. URGENT GTL & SICEPAT
3. J&T SPESIAL
4. J&T 1 QTY REGULER
5. J&T KOMBINASI
6. SPX - SPESIAL
7. SPX - 1 QTY REGULER
8. SPX - KOMBINASI

SPX Resi Pagi **hanya** ada di sesi JAM 13.00 (channel Shopee, jam pesan
WIB maksimal 12.00 siang hari itu) — dijalankan cukup **1x sehari**, jangan
diulang di SESI SORE.

Urutan dalam tiap sesi tidak saling bergantung secara teknis (kecuali
spesial harus tahu SKU spesial hari itu, sudah ditangani lewat baca ulang
Excel di setiap langkah), tapi urgent dijalankan **lebih dulu** supaya
pesanan yang sudah "diambil" urgent tidak ikut terhitung sebagai kandidat
SKU spesial (kebijakan operasional tim, `proses-harian.bat` sudah mengikuti urutan
ini).

Detail masing-masing alur & opsi `--kurir`: lihat [README.md](../README.md).

## Jadwal harian (pagi–sore, sudah berjalan pakai program)

Dijalankan tim setiap hari, siklus 2 jam (jam bulat, lalu diulang lagi
setelah proses transfer bank/pembayaran selesai):

| Jam | Yang dijalankan | Sesi proses-harian.bat |
|---|---|---|
| 07.00 | Urgent Lazada, Urgent GTL/SiCepat, SPX & J&T spesial (digabung), 1 SKU 1 qty reguler, kombinasi reguler | 1 (SESI PAGI) |
| 07.xx (setelah transfer) | (ulang) | 1 |
| 09.00 | (ulang) | 1 |
| 09.xx (setelah transfer) | (ulang) | 1 |
| 11.00 | (ulang) | 1 |
| 11.xx (setelah transfer) | (ulang) | 1 |
| 13.00 | Urgent Lazada, Urgent GTL/SiCepat, **SPX ≤ 12.00 (SPX Resi Pagi)**, J&T spesial, J&T 1 qty reguler, J&T kombinasi, SPX spesial, SPX 1 qty reguler, SPX kombinasi (**J&T/SPX dipisah**) | 2 (JAM 13.00) |
| 13.xx (setelah transfer) | Urgent Lazada, Urgent GTL/SiCepat, J&T spesial, J&T 1 qty reguler, J&T kombinasi, SPX spesial, SPX 1 qty reguler, SPX kombinasi (**J&T/SPX dipisah**, tanpa SPX Resi Pagi lagi) | 3 (SESI SORE) |
| 15.00 | (ulang) | 3 |
| 15.xx (setelah transfer) | (ulang) | 3 |
| 16.00 | (ulang) | 3 |
| 16.xx (setelah transfer) | (ulang) | 3 |

**Catatan jam 13.00**: hanya siklus ini yang menyertakan SPX Resi Pagi
(langkah 3 di sesi JAM 13.00 — channel Shopee, jam pesan WIB maksimal
12.00 siang hari itu). Setelah jam 13.00, siklus berikutnya (13.xx dst)
pakai sesi **SESI SORE**, bukan JAM 13.00 lagi.

## Jadwal malam (18.00–23.00)

Tidak ada proses transfer bank di jam-jam ini, jadi tiap jam cuma 1 kali
jalan (tidak ada pengulangan "setelah transfer").

| Jam | Yang dijalankan | Sesi proses-harian.bat |
|---|---|---|
| 18.00 | Urgent Lazada, Urgent GTL/SiCepat, J&T & SPX dipisah (spesial, 1 qty, kombinasi) | 3 (SESI SORE) |
| 19.00 | (ulang) | 3 |
| 20.00 | (ulang) | 3 |
| 21.00 | (ulang) | 3 |
| 22.00 | (ulang) | 3 |
| 23.00 | (ulang) | 3 |

> ⚠️ **Belum pernah dicoba pakai program.** Jadwal malam ini baru rencana —
> sebelum dijadikan rutin, jalankan dulu manual di jam-jam ini dan cek
> hasilnya di Jubelio (jumlah picklist, resi, label PDF) sebelum
> mempercayakannya tanpa pengawasan.

## Aturan permanen (jangan sampai dilanggar perubahan apa pun ke depan)

- **Pesanan SPX tipe pengiriman kilat tidak pernah diikutkan** ke picklist
  apa pun di alur ini (spesial, 1 qty reguler, kombinasi reguler, SPX Resi
  Pagi) — baik saat J&T/SPX digabung (SESI PAGI) maupun dipisah (JAM 13.00,
  SESI SORE). Ini sudah diimplementasikan di kode (`TIPE_PESANAN_FILTER`,
  otomatis aktif setiap kali filter kurir SPX atau channel Shopee dipakai —
  lihat bagian 3 [README.md](../README.md)). Setiap pengembangan baru wajib
  mempertahankan aturan ini.
- **Penentuan SKU "spesial"** (dari Excel, `hitung_sku_spesial` di
  `sku_spesial.py`) **selalu** menggabung resi J&T+SPX (minimal 3 resi
  sejenis), terlepas dari sesi mana yang dipakai. `--kurir` di sesi JAM
  13.00/SESI SORE hanya membatasi resi kurir mana yang benar-benar
  dipicklist saat proses SKU spesial itu berjalan — bukan mengubah daftar
  SKU spesial itu sendiri.

---

# Rencana Pengembangan (belum diimplementasikan)

Bagian ini didokumentasikan dulu supaya idenya tidak terlewat, **bukan**
berarti sudah ada di kode saat ini.

## A. Proses otomatis berbasis polling (ganti jadwal jam manual)

Alih-alih jadwal jam manual seperti di atas, rencana ke depan program jalan
otomatis dengan logika:

1. Cek jumlah pesanan "Siap Proses" setiap **5 menit**.
2. Begitu totalnya **≥ 200**, mulai proses (urutan sama seperti sesi
   `proses-harian.bat` yang berlaku saat itu: urgent → spesial → reguler).
3. **Tunggu sampai proses itu benar-benar selesai** sebelum melakukan
   pengecekan berikutnya — proses bisa saja butuh waktu **lebih dari 5
   menit**, jadi pengecekan selanjutnya **tidak boleh mulai** kalau proses
   sebelumnya masih berjalan.
4. Tujuan aturan #3: mencegah 2 proses berjalan **tumpang-tindih**
   (race condition) yang bisa membuat picklist ganda/tidak konsisten di
   Jubelio.

Implikasi desain (untuk saat implementasi nanti): perlu mekanisme lock/flag
("sedang proses") yang dicek sebelum tiap siklus polling mulai, dan jadwal
jam manual di atas kemungkinan digantikan sepenuhnya oleh mode polling ini
(atau berjalan berdampingan sebagai fallback — perlu diputuskan saat
implementasi).

## B. Mode khusus hari event (SPX Standard vs SPX Hemat)

Pemisahan **J&T vs SPX** saat pembuatan picklist (dulu direncanakan di sini
untuk "hari event") **sudah diimplementasikan** lewat `--kurir` dan dipakai
tiap hari di sesi JAM 13.00/SESI SORE (lihat bagian atas) — bukan cuma hari
event lagi. Yang **belum** diimplementasikan: pemisahan lebih lanjut antara
**SPX Standard vs SPX Hemat** (keduanya sama-sama "SPX" di Jubelio hari
ini, perlu dicek dulu field/atribut apa yang membedakan varian ini sebelum
implementasi):

| Kurir | SKU spesial? | 1 SKU 1 qty reguler | Kombinasi reguler |
|---|---|---|---|
| **J&T** | Ya | Ya | Ya |
| **SPX Standard** | Perlu dikaji ulang — mungkin tidak perlu dipisah spesial kalau volumenya kecil | Ya | Ya |
| **SPX Hemat** | Ya (sama seperti J&T) | Ya | Ya |

Aturan "SPX tipe pengiriman kilat selalu dikeluarkan" (lihat bagian
"Aturan permanen" di atas) tetap berlaku untuk ketiga baris di tabel ini.
