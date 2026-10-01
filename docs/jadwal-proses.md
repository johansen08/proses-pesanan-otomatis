# Jadwal Proses Pesanan Harian (Tim Resi)

Dokumentasi jadwal operasional tim resi: jam berapa proses apa dijalankan,
dipetakan ke menu/perintah program yang sebenarnya. Ini dokumentasi
**kebijakan/SOP tim**, bukan kode — perubahan jadwal cukup edit file ini,
tidak perlu ubah program.

**Revisi 2026-10-01**: `proses-harian.bat` memakai **4 TIPE** (menggantikan
penamaan "SESI PAGI/JAM 13.00/SESI SORE/JAM 15.00" sebelumnya yang kurang
jelas) — **TIPE 1**, **TIPE 2**, **TIPE 3**, **TIPE 4**, dijalankan **1 kali
klik + 1 konfirmasi Y/N** per tipe. TIPE 1 & TIPE 4 menggabung J&T+SPX;
TIPE 2 & TIPE 3 memisahnya (`--kurir jnt`/`--kurir spx`). TIPE 2 (tepat jam
13.00) menghabiskan wajib keluar Shopee (SPX Resi Pagi, ≤ 12.00); TIPE 4
(tepat jam 15.00) menghabiskan wajib keluar TikTok Shop (J&T Resi Siang,
≤ 15.00). **TIPE 1 sekarang melingkupi sore/malam/dini hari juga**
(16.00–07.00 keesokan harinya) — jadwal malam yang dulu dokumentasinya
terpisah sekarang menyatu di sini, dan dulu dipisah J&T/SPX (TIPE 3), kini
digabung (TIPE 1). Penentuan SKU mana yang "spesial" (dari Excel) **tidak
berubah** di semua tipe, tetap menggabung J&T+SPX; `--kurir` cuma
membatasi resi kurir mana yang benar-benar dipicklist saat itu.

## Istilah tim → proses-harian.bat / perintah program

| Istilah tim | Perintah (`jalankan.bat ...`) |
|---|---|
| Sampel TikTok (nilai 0/kosong) | `--sampel --jalankan` |
| Urgent Lazada | `--urgent --channel lazada --jalankan` |
| Urgent GTL & SiCepat | `--urgent --channel gtl-sicepat --jalankan` |
| SPX & J&T spesial (digabung) | `--label --tanpa-reguler --jalankan` |
| SPX & J&T 1 SKU 1 qty reguler (digabung) | `--reguler --bagian 1qty --jalankan` |
| SPX & J&T kombinasi reguler (digabung) | `--reguler --bagian kombinasi --jalankan` |
| SPX ≤ 12.00 (SPX Resi Pagi, habiskan wajib keluar Shopee) | `--shopee-pagi --jalankan` |
| J&T ≤ 15.00, channel TikTok Shop (J&T Resi Siang, habiskan wajib keluar TikTok) | `--jnt-siang --jalankan` |
| J&T spesial (dipisah) | `--label --kurir jnt --tanpa-reguler --jalankan` |
| J&T 1 SKU 1 qty reguler (dipisah) | `--reguler --bagian 1qty --kurir jnt --jalankan` |
| J&T kombinasi reguler (dipisah) | `--reguler --bagian kombinasi --kurir jnt --jalankan` |
| SPX spesial (dipisah) | `--label --kurir spx --tanpa-reguler --jalankan` |
| SPX 1 SKU 1 qty reguler (dipisah) | `--reguler --bagian 1qty --kurir spx --jalankan` |
| SPX kombinasi reguler (dipisah) | `--reguler --bagian kombinasi --kurir spx --jalankan` |

## proses-harian.bat — 4 TIPE

```
1. TIPE 1 - GABUNG J&T+SPX              (07.00-12.00 / 16.00-07.00)
2. TIPE 2 - DIPISAH + SPX RESI PAGI     (TEPAT JAM 13.00)
3. TIPE 3 - DIPISAH                     (13.00-15.00)
4. TIPE 4 - GABUNG LAGI + J&T RESI SIANG (TEPAT JAM 15.00)
0. Keluar
```

Tiap pilihan menjalankan urutan langkah di bawah **berurut, 1 kali klik +
1 konfirmasi Y/N**. Picklist sampel (TikTok Shop nilai 0/kosong) **selalu**
dicek PALING PERTAMA di tiap tipe (dilewati kalau tidak ada pesanannya),
lalu picklist urgent (Lazada, GTL/SiCepat) **selalu** ikut setelahnya —
tidak ada lagi cara memicunya sendirian lewat menu (masih bisa manual lewat
`jalankan.bat --sampel ...`/`jalankan.bat --urgent ...` kalau perlu).

### TIPE 1 — gabung J&T+SPX (07.00-12.00, dan 16.00-07.00 keesokan harinya)

1. SAMPEL TIKTOK (NILAI 0)
2. URGENT LAZADA
3. URGENT GTL & SICEPAT
4. SPX - J&T SPESIAL
5. SPX - J&T 1 QTY REGULER
6. SPX - J&T KOMBINASI

Dipakai untuk siklus pagi **07.00-11.xx**, DAN dipakai lagi untuk siklus
sore/malam/dini hari **16.00 sampai 07.00 keesokan harinya** — begitu TIPE 4
selesai (jam 15.00-an), TIPE 1 menggantikannya terus sampai TIPE 1 lagi
besok pagi jam 07.00. Ini sekaligus **menggantikan jadwal malam** yang dulu
didokumentasikan terpisah pakai TIPE 3 (dipisah) — sekarang malam hari
**digabung** (TIPE 1), bukan dipisah lagi.

### TIPE 2 — dipisah + SPX Resi Pagi (TEPAT jam 13.00)

1. SAMPEL TIKTOK (NILAI 0)
2. URGENT LAZADA
3. URGENT GTL & SICEPAT
4. SPX ≤ 12.00 (SPX RESI PAGI)
5. J&T SPESIAL
6. J&T 1 QTY REGULER
7. J&T KOMBINASI
8. SPX - SPESIAL
9. SPX - 1 QTY REGULER
10. SPX - KOMBINASI

Dipicu **tepat jam 13.00**, menghabiskan wajib keluar Shopee (langkah 3,
channel Shopee, jam pesan WIB maksimal 12.00 siang hari itu, cukup
**1x sehari** — jangan diulang di TIPE 3). Jam **12.00-13.00 sengaja
dikosongkan** dari jendela tipe mana pun (jam istirahat tim) — bukan celah
jadwal.

### TIPE 3 — dipisah, tanpa SPX Resi Pagi (13.00-15.00)

1. SAMPEL TIKTOK (NILAI 0)
2. URGENT LAZADA
3. URGENT GTL & SICEPAT
4. J&T SPESIAL
5. J&T 1 QTY REGULER
6. J&T KOMBINASI
7. SPX - SPESIAL
8. SPX - 1 QTY REGULER
9. SPX - KOMBINASI

Dipakai **setelah TIPE 2 selesai** (kapan pun itu, tidak harus tepat jam
13.00) **dan sebelum TIPE 4 dimulai** — jam 13.00 sampai 15.00. **Tidak
dipakai lagi** di luar rentang ini (malam hari sekarang pakai TIPE 1, lihat
di atas).

### TIPE 4 — gabung lagi + J&T Resi Siang (TEPAT jam 15.00)

1. SAMPEL TIKTOK (NILAI 0)
2. URGENT LAZADA
3. URGENT GTL & SICEPAT
4. J&T ≤ 15.00 (J&T RESI SIANG)
5. SPX - J&T SPESIAL *(digabung, seperti TIPE 1 - bukan dipisah)*
6. SPX - J&T 1 QTY REGULER *(digabung)*
7. SPX - J&T KOMBINASI *(digabung)*

Dipicu **tepat jam 15.00**, menghabiskan wajib keluar TikTok Shop (langkah
3, channel TikTok Shop, kurir J&T, jam pesan WIB maksimal 15.00 hari itu,
cukup **1x sehari** — jangan diulang di TIPE 1 berikutnya). Mulai langkah 4,
kurir **tidak** dipisah lagi — langsung memakai pola gabungan TIPE 1, karena
setelah J&T Resi Siang selesai tidak ada lagi alasan bisnis untuk memisah
J&T/SPX hari itu. Setelah TIPE 4 selesai, lanjut ke **TIPE 1** (lihat di
atas) sampai jam 07.00 besok.

### Picklist sampel (TikTok Shop nilai 0/kosong)

Dicek **PALING PERTAMA di tiap TIPE 1-4** (langkah 1, sebelum Urgent Lazada) — pesanan
channel TikTok Shop yang nilainya 0/kosong (sampel/kreator) digabung jadi **1 picklist**
("SAMPEL-TIKTOK"), bukan dibuang. Kalau tidak ada pesanan sampel saat itu, langkah ini
otomatis dilewati tanpa membuat picklist apa pun, lalu lanjut ke langkah berikutnya.

| | Picklist sampel |
|---|---|
| Channel | TikTok Shop ("Shop \| Tokopedia") |
| Syarat | nilai pesanan (`grand_total`) 0 atau kosong |
| Dipicu di | TIPE 1-4, langkah 1 (paling pertama, tiap kali TIPE dijalankan) |
| CLI | `--sampel` |
| Label riwayat/PDF | `SAMPEL-TIKTOK` |

Format nama file PDF & kolom SKU di riwayat: lihat
[README.md bagian 0](../README.md#0-picklist-sampel---sampel). Implementasi kode:
`ambil_pesanan_sampel()`/`rencana_sampel()`/`proses_sampel()` di `src/proses_label.py`.

### J&T Resi Siang & SPX Resi Pagi

Baik Shopee maupun TikTok Shop punya aturan "wajib keluar" di jam
tertentu, cuma beda kurir dan beda jam cutoff:

| | SPX Resi Pagi | J&T Resi Siang |
|---|---|---|
| Channel | Shopee | TikTok Shop |
| Kurir | (tidak difilter) | J&T saja |
| Jam cutoff (WIB) | ≤ 12.00 | ≤ 15.00 |
| Dipicu di | TIPE 2, tepat jam 13.00 | TIPE 4, tepat jam 15.00 |
| CLI | `--shopee-pagi` | `--jnt-siang` |
| Label riwayat/PDF | `SHOPEE-PAGI` | `JNT-SIANG` |

Keduanya dijalankan cukup **1x sehari**. Implementasi kode:
`ambil_pesanan_shopee_pagi()`/`ambil_pesanan_jnt_siang()` dkk di
`proses_label.py` (pola identik, beda channel/kurir/jam cutoff). Detail
pemakaian CLI: lihat [README.md](../README.md) bagian 4 & 5.

Urutan dalam tiap TIPE tidak saling bergantung secara teknis (kecuali
spesial harus tahu SKU spesial hari itu, sudah ditangani lewat baca ulang
Excel di setiap langkah), tapi urgent dijalankan **lebih dulu** supaya
pesanan yang sudah "diambil" urgent tidak ikut terhitung sebagai kandidat
SKU spesial (kebijakan operasional tim, `proses-harian.bat` sudah mengikuti
urutan ini).

Detail masing-masing alur & opsi `--kurir`: lihat [README.md](../README.md).

### Penjaga jam (`dalam_jam_menu()`) — sanity check, bukan validasi urutan

`proses-harian.bat` menanyakan konfirmasi ekstra (Y/N) kalau TIPE dipilih
di luar jendela jam yang wajar untuknya (`cek_jam` di `proses-harian.bat`,
`dalam_jam_menu()` di `src/main.py`):

| TIPE | Jendela | Catatan |
|---|---|---|
| 1 | 00.00-12.00 **dan** 16.00-23.59 | Gabungan "07.00-12.00" + ekor malam "16.00-07.00" (dicek sebagai jam-dalam-sehari, berulang tiap hari) |
| 2 | 13.00-13.59 | Jam istirahat 12.00-13.00 sengaja TIDAK masuk jendela tipe mana pun |
| 3 | 13.00-14.59 | Mulai dari 13.00 juga (bukan 13.01) supaya TIPE 3 yang dijalankan segera setelah TIPE 2 selesai (bisa saja masih "jam 13.00-an") tidak salah kena peringatan |
| 4 | 15.00-15.59 | |

Jendela TIPE 2/3 (13.00-13.59 vs 13.00-14.59) dan TIPE 1/4 (saat 15.xx,
TIPE 1 belum masuk jendela sampai jam 16.00 — lihat catatan di bawah)
**sengaja tumpang tindih di sebagian rentang** — di situ, lebih dari satu
TIPE dianggap wajar dipilih tim, tergantung mana yang sudah/belum
dijalankan hari itu. Guard ini **tidak menyimpan status** TIPE mana yang
sudah dijalankan; ini cuma sanity check jam untuk menangkap salah pilih
menu (mis. pilih TIPE 3 jam 08.00 pagi), **bukan** validasi urutan kerja
yang sebenarnya — itu tetap tanggung jawab tim yang menjalankan.

Catatan jam 15.00-16.00: TIPE 4 (15.00-15.59) dan TIPE 1 (mulai 16.00)
**tidak** tumpang tindih seperti TIPE 2/3 — begitu TIPE 4 selesai (idealnya
masih dalam jam 15.00-an), tim lanjut ke TIPE 1 meski jendelanya baru mulai
jam 16.00; guard akan menanyakan konfirmasi kalau TIPE 1 dipilih sebelum
jam 16.00, tim cukup jawab Y karena itu memang urutan yang benar (TIPE 4
baru saja selesai).

## Jadwal harian (sudah berjalan pakai program)

Dijalankan tim setiap hari, siklus 2 jam di jam kerja (jam bulat, lalu
diulang lagi setelah proses transfer bank/pembayaran selesai) dan 1x per
jam di luar jam kerja:

| Jam | Yang dijalankan | TIPE proses-harian.bat |
|---|---|---|
| 07.00 | Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, SPX & J&T spesial, 1 qty reguler, kombinasi reguler (**digabung**) | 1 |
| 07.xx (setelah transfer) | (ulang) | 1 |
| 09.00 | (ulang) | 1 |
| 09.xx (setelah transfer) | (ulang) | 1 |
| 11.00 | (ulang) | 1 |
| 11.xx (setelah transfer) | (ulang) | 1 |
| 12.00-13.00 | *(jam istirahat, tidak ada proses)* | - |
| 13.00 | Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, **SPX ≤ 12.00 (SPX Resi Pagi)**, J&T spesial, J&T 1 qty reguler, J&T kombinasi, SPX spesial, SPX 1 qty reguler, SPX kombinasi (**dipisah**) | 2 |
| 13.xx (setelah TIPE 2 selesai) | Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, J&T spesial, J&T 1 qty reguler, J&T kombinasi, SPX spesial, SPX 1 qty reguler, SPX kombinasi (**dipisah**, tanpa SPX Resi Pagi lagi) | 3 |
| 15.00 | Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, **J&T ≤ 15.00 (J&T Resi Siang)**, lalu SPX-J&T spesial, 1 qty reguler, kombinasi (**digabung lagi**) | 4 |
| 16.00 | Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, SPX-J&T spesial, 1 qty reguler, kombinasi (**digabung**, tanpa J&T Resi Siang lagi - sudah selesai jam 15.00) | 1 |
| 16.xx (setelah transfer) | (ulang) | 1 |
| 18.00, 19.00, 20.00, 21.00, 22.00, 23.00 | (ulang, 1x per jam - tidak ada proses transfer di jam-jam ini) | 1 |
| 00.00-06.xx (dini hari) | (ulang kalau ada pesanan masuk) | 1 |

**Catatan jam 13.00**: hanya siklus ini yang menyertakan SPX Resi Pagi
(langkah 3 di TIPE 2 — channel Shopee, jam pesan WIB maksimal 12.00 siang
hari itu). Setelah jam 13.00, siklus berikutnya (13.xx dst, sebelum jam
15.00) pakai TIPE 3, bukan TIPE 2 lagi.

**Catatan jam 15.00**: hanya siklus ini yang menyertakan J&T Resi Siang
(channel TikTok Shop, jam pesan WIB maksimal 15.00 siang hari itu). Setelah
jam 15.00, siklus berikutnya (16.00 dst, sampai 07.00 besok) **kembali**
pakai TIPE 1 (gabung) — bukan TIPE 3 (dipisah) lagi, karena alasan bisnis
pemisahan J&T/SPX (TIPE 2 & TIPE 3) sudah tidak berlaku setelah J&T Resi
Siang selesai.

**Jadwal malam & dini hari (16.00-07.00) sudah menyatu di tabel di atas**
(dulu didokumentasikan terpisah sebagai "Jadwal malam", dipisah J&T/SPX)
— sekarang bagian dari siklus TIPE 1 yang sama dengan pagi hari, digabung
J&T/SPX. Kalau belum pernah dicoba pakai program di luar jam kerja normal
(mis. tengah malam), jalankan dulu manual dan cek hasilnya di Jubelio
(jumlah picklist, resi, label PDF) sebelum mempercayakannya tanpa
pengawasan.

## Aturan permanen (jangan sampai dilanggar perubahan apa pun ke depan)

- **Pesanan SPX tipe pengiriman kilat tidak pernah diikutkan** ke picklist
  apa pun di alur ini (spesial, 1 qty reguler, kombinasi reguler, SPX Resi
  Pagi) — baik saat J&T/SPX digabung (TIPE 1, TIPE 4) maupun dipisah (TIPE
  2, TIPE 3). Ini sudah diimplementasikan di kode (`TIPE_PESANAN_FILTER`,
  otomatis aktif setiap kali filter kurir SPX atau channel Shopee dipakai —
  lihat bagian 3 [README.md](../README.md)). Setiap pengembangan baru wajib
  mempertahankan aturan ini.
- **Penentuan SKU "spesial"** (dari Excel, `hitung_sku_spesial` di
  `sku_spesial.py`) **selalu** menggabung resi J&T+SPX (minimal 3 resi
  sejenis), terlepas dari TIPE mana yang dipakai. `--kurir` di TIPE 2/TIPE 3
  hanya membatasi resi kurir mana yang benar-benar dipicklist saat proses
  SKU spesial itu berjalan — bukan mengubah daftar SKU spesial itu sendiri.

---

Rencana pengembangan yang belum diimplementasikan (proses otomatis berbasis
polling, pemisahan SPX Standard vs SPX Hemat) didokumentasikan terpisah di
[rencana-pengembangan.md](rencana-pengembangan.md) supaya tidak tercampur
dengan jadwal operasional aktual di atas.
