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

**Revisi 2026-09-30 (sudah diimplementasikan)**: J&T ternyata punya aturan
bisnis yang sama sifatnya dengan SPX ≤ 12.00 (SPX Resi Pagi) tapi untuk
channel **TikTok Shop**, dengan batas jam **15.00**, disebut **"J&T Resi
Siang"** di dokumen ini — lihat bagian ["J&T Resi Siang" (jam
15.00)](#jt-resi-siang-jam-1500) untuk alasan bisnisnya. Konsekuensinya,
jadwal jam 15.00 ke atas **berubah**: J&T Resi Siang jadi langkah wajib
sekali di jam 15.00, dan setelah itu J&T + SPX **kembali digabung** (seperti
SESI PAGI) sampai jam 16.00 — bukan tetap dipisah seperti SESI SORE
sebelumnya. Detail lengkap: lihat sesi "JAM 15.00" di bagian
[proses-harian.bat](#proses-harianbat--4-sesi) dan tabel [Jadwal
harian](#jadwal-harian-pagisore-sudah-berjalan-pakai-program) di bawah.

## Istilah tim → proses-harian.bat / perintah program

| Istilah tim | Perintah (`jalankan.bat ...`) |
|---|---|
| Urgent Lazada | `--urgent --channel lazada --jalankan` |
| Urgent GTL & SiCepat | `--urgent --channel gtl-sicepat --jalankan` |
| SPX & J&T spesial (digabung) | `--label --tanpa-reguler --jalankan` |
| SPX & J&T 1 SKU 1 qty reguler (digabung) | `--reguler --bagian 1qty --jalankan` |
| SPX & J&T kombinasi reguler (digabung) | `--reguler --bagian kombinasi --jalankan` |
| SPX ≤ 12.00 (SPX Resi Pagi, dulu disebut Shopee Pagi) | `--shopee-pagi --jalankan` |
| J&T ≤ 15.00, channel TikTok Shop (**J&T Resi Siang**) | `--jnt-siang --jalankan` |
| J&T spesial (dipisah) | `--label --kurir jnt --tanpa-reguler --jalankan` |
| J&T 1 SKU 1 qty reguler (dipisah) | `--reguler --bagian 1qty --kurir jnt --jalankan` |
| J&T kombinasi reguler (dipisah) | `--reguler --bagian kombinasi --kurir jnt --jalankan` |
| SPX spesial (dipisah) | `--label --kurir spx --tanpa-reguler --jalankan` |
| SPX 1 SKU 1 qty reguler (dipisah) | `--reguler --bagian 1qty --kurir spx --jalankan` |
| SPX kombinasi reguler (dipisah) | `--reguler --bagian kombinasi --kurir spx --jalankan` |

## proses-harian.bat — 4 sesi

```
1. SESI PAGI
2. JAM 13.00
3. SESI SORE
4. JAM 15.00        <- BARU
0. Keluar
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

Dipakai untuk siklus 07.00-11.xx **dan** dipakai lagi **setelah proses JAM
15.00 selesai** (siklus 15.xx, 16.00, 16.xx) — bukan berdasarkan jam pas,
tapi berdasarkan **urutan**: begitu JAM 15.00 selesai (bisa jam berapa
saja, tidak harus tepat), sesi berikutnya kembali ke SESI PAGI. Lihat sesi
"JAM 15.00" di bawah untuk alasannya.

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

Dipakai **setelah JAM 13.00 selesai** (kapan pun itu, tidak harus tepat
jam 14.00) **dan sebelum JAM 15.00 dimulai** — yaitu untuk siklus 13.xx
pasca transfer. **Dipakai lagi** untuk jadwal malam 18.00-23.00 (lihat
bagian [Jadwal malam](#jadwal-malam-1800-2300) di bawah) — bukan hanya
untuk siklus 13.xx. **Tidak dipakai** untuk siklus 15.00 ke atas (digantikan
sesi "JAM 15.00" lalu kembali ke SESI PAGI - lihat di bawah).

### 4. JAM 15.00 (BARU - J&T Resi Siang lalu kembali digabung)

1. URGENT LAZADA
2. URGENT GTL & SICEPAT
3. **J&T RESI SIANG** (channel TikTok Shop, kurir J&T, jam pesan ≤ 15.00 hari
   ini, digabung 1 picklist)
4. SPX - J&T SPESIAL *(digabung, seperti SESI PAGI - bukan dipisah)*
5. SPX - J&T 1 QTY REGULER *(digabung)*
6. SPX - J&T KOMBINASI *(digabung)*

Dijalankan **1x sehari, dipicu sekitar jam 15.00** (idealnya sesegera
mungkin setelah jam 15.00 supaya resi TikTok Shop yang wajib keluar tidak
tertunda lama, tapi **tidak harus persis** jam 15.00:00 - filter jam pesan
≤ 15.00 di kode yang menjamin cutoff-nya, bukan jam kliknya), menggantikan
SESI SORE untuk siklus itu. Langkah 3 (J&T Resi Siang) sama sifatnya dengan
SPX Resi Pagi di sesi JAM 13.00: dijalankan **cukup 1x sehari** (jangan
diulang di siklus 15.xx/16.00/16.xx). Bedanya dengan JAM 13.00: mulai
langkah 4, kurir **tidak** dipisah lagi - langsung memakai pola gabungan
SESI PAGI, karena setelah J&T Resi Siang selesai tidak ada lagi alasan
bisnis untuk memisah J&T/SPX hari itu (lihat ["J&T Resi
Siang"](#jt-resi-siang-jam-1500) di bawah).

Siklus setelah JAM 15.00 **selesai** (kapan pun itu — siklus 15.xx pasca
transfer, 16.00, 16.xx) memakai **SESI PAGI** lagi (gabung, tanpa J&T Resi
Siang - sudah selesai sekali di JAM 15.00).

SPX Resi Pagi **hanya** ada di sesi JAM 13.00 (channel Shopee, jam pesan
WIB maksimal 12.00 siang hari itu) dan J&T Resi Siang **hanya** ada di sesi
JAM 15.00 (channel TikTok Shop, jam pesan WIB maksimal 15.00 hari itu) —
keduanya dijalankan cukup **1x sehari**, jangan diulang di sesi lain.

### J&T Resi Siang (jam 15.00)

J&T punya aturan operasional: pesanan channel **TikTok Shop** yang **wajib
keluar** hari itu (dikirim lewat kurir J&T) harus **digabung jadi 1
picklist paling lambat jam 15.00** - supaya tidak tercampur dengan
pesanan TikTok yang masuk setelah jam 15.00. Ini sejajar dengan aturan SPX
yang sudah ada (Shopee wajib keluar ≤ 12.00, diimplementasikan sebagai
"SPX Resi Pagi"/`--shopee-pagi`), bedanya beda kurir (J&T, bukan SPX) dan
beda jam batas (15.00, bukan 12.00). Diimplementasikan sebagai **J&T Resi
Siang**/`--jnt-siang` di `proses_label.py`
(`ambil_pesanan_jnt_siang()`/`rencana_jnt_siang()`/`proses_jnt_siang()`,
konstanta `CHANNEL_ID_TIKTOK_SHOP` + filter kurir `["j&t"]` +
`JAM_CUTOFF_JNT_SIANG = 15`, label riwayat/PDF `JNT-SIANG`) — pola kodenya
identik dengan SPX Resi Pagi, tinggal beda channel/kurir/jam cutoff. Detail
pemakaian CLI: lihat [README.md](../README.md) bagian 5.

Urutan dalam tiap sesi tidak saling bergantung secara teknis (kecuali
spesial harus tahu SKU spesial hari itu, sudah ditangani lewat baca ulang
Excel di setiap langkah), tapi urgent dijalankan **lebih dulu** supaya
pesanan yang sudah "diambil" urgent tidak ikut terhitung sebagai kandidat
SKU spesial (kebijakan operasional tim, `proses-harian.bat` sudah mengikuti urutan
ini).

Detail masing-masing alur & opsi `--kurir`: lihat [README.md](../README.md).

### Penjaga jam (`dalam_jam_menu()`) — berbasis urutan, bukan jam pas

`proses-harian.bat` menanyakan konfirmasi ekstra (Y/N) kalau sesi dipilih
di luar jendela jam yang wajar untuknya (`cek_jam` di `proses-harian.bat`,
`dalam_jam_menu()` di `src/main.py`). Jendela ini **sengaja dibuat lebar**,
karena urutan sesi yang sebenarnya bergantung pada **kapan proses
sebelumnya benar-benar selesai** (bisa lebih cepat atau lebih lambat dari
jam bulat), bukan jam pas per menit:

| Menu | Jendela | Alasan |
|---|---|---|
| 1. SESI PAGI | 07.00-13.00 **dan** 15.00-17.59 | Jendela kedua dipakai lagi setelah JAM 15.00 selesai — dimulai dari jam 15.00 juga (bukan mepet ke belakang), supaya JAM 15.00 yang selesai cepat tidak salah kena peringatan |
| 2. JAM 13.00 | 13.01-14.00 | Dipicu sekitar jam 13.00 |
| 3. SESI SORE | 13.01-14.59 **dan** 18.00-23.00 | Jendela pertama dimulai dari 13.01 (sama dengan awal JAM 13.00) supaya SESI SORE yang dijalankan segera setelah JAM 13.00 selesai (bisa saja masih jam 13.xx, belum tentu sudah lewat jam 14.00) tidak salah kena peringatan; jendela kedua untuk jadwal malam |
| 4. JAM 15.00 | 15.00-15.59 | Dipicu sekitar jam 15.00 |

Jendela menu 2/3 (13.01-14.00 vs 13.01-14.59) dan menu 1/4 (15.00-17.59 vs
15.00-15.59) **sengaja tumpang tindih** — di rentang itu, dua menu
sekaligus dianggap wajar dipilih (tergantung mana yang sudah/belum
dijalankan tim hari itu). Guard ini **tidak menyimpan status** menu mana
yang sudah dijalankan; ini cuma sanity check jam untuk menangkap salah
pilih menu (mis. pilih SESI SORE jam 08.00 pagi), **bukan** validasi urutan
kerja yang sebenarnya — itu tetap tanggung jawab tim yang menjalankan.

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
| 15.00 | Urgent Lazada, Urgent GTL/SiCepat, **J&T ≤ 15.00 channel TikTok Shop (J&T Resi Siang)**, lalu SPX-J&T spesial, 1 qty reguler, kombinasi (**digabung lagi, seperti SESI PAGI**) | 4 (JAM 15.00) |
| 15.xx (setelah transfer) | Urgent Lazada, Urgent GTL/SiCepat, SPX-J&T spesial, 1 qty reguler, kombinasi (**digabung**, tanpa J&T Resi Siang lagi - sudah selesai jam 15.00) | 1 (SESI PAGI) |
| 16.00 | (ulang) | 1 (SESI PAGI) |
| 16.xx (setelah transfer) | (ulang) | 1 (SESI PAGI) |

**Catatan jam 13.00**: hanya siklus ini yang menyertakan SPX Resi Pagi
(langkah 3 di sesi JAM 13.00 — channel Shopee, jam pesan WIB maksimal
12.00 siang hari itu). Setelah jam 13.00, siklus berikutnya (13.xx dst)
pakai sesi **SESI SORE**, bukan JAM 13.00 lagi.

**Catatan jam 15.00**: hanya siklus ini yang menyertakan J&T Resi
Siang (channel TikTok Shop, jam pesan WIB maksimal 15.00 siang hari itu).
Berbeda dari pola jam 13.00: setelah jam 15.00, siklus berikutnya (15.xx
dst) **kembali** pakai sesi **SESI PAGI** (gabung), bukan SESI SORE lagi -
karena alasan bisnis pemisahan J&T/SPX (dipakai JAM 13.00 & SESI SORE)
sudah tidak berlaku lagi setelah J&T Resi Siang selesai.

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

> **Catatan**: "J&T Resi Siang" (channel TikTok Shop, kurir J&T, ≤ 15.00)
> yang tadinya direncanakan di sini **sudah diimplementasikan** — lihat
> bagian ["J&T Resi Siang" (jam 15.00)](#jt-resi-siang-jam-1500) di atas dan
> [README.md](../README.md) bagian 5.
