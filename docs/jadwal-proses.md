# Jadwal Proses Pesanan Harian (Tim Resi)

Dokumentasi jadwal operasional tim resi: jam berapa proses apa dijalankan,
dipetakan ke menu/perintah program yang sebenarnya. Ini dokumentasi
**kebijakan/SOP tim**, bukan kode — perubahan jadwal cukup edit file ini,
tidak perlu ubah program.

**Revisi 2026-10-08**: tambah **mode event** (`proses-event.bat`, hari 10.10 / 11.11 / 12.12 dst)
— J&T, SPX Hemat, dan SPX Standard dipisah sepanjang hari. `proses-harian.bat` **tidak berubah**
sama sekali; lihat bagian "proses-event.bat — mode event" di bawah.

**Revisi 2026-10-06**: tambah langkah **Recheck Stok** (`--recheck-stok`) sebagai langkah
PALING PERTAMA di tiap TIPE 1-4 (sebelum Sampel TikTok) — cek ulang stok SEMUA pesanan
berstatus stok kosong (`EMPTY_STOCK`, biasanya bekas picklist sebelumnya yang gagal karena
stok tidak ada) sekaligus, supaya pesanan yang stoknya sudah tersedia lagi ikut terhitung di
langkah-langkah berikutnya TIPE yang sama. Lihat bagian "Recheck stok" di bawah.

**Revisi 2026-10-01**: `proses-harian.bat` memakai **4 TIPE** (menggantikan
penamaan "SESI PAGI/JAM 13.00/SESI SORE/JAM 15.00" sebelumnya yang kurang
jelas) — **TIPE 1**, **TIPE 2**, **TIPE 3**, **TIPE 4**, dijalankan **1 kali
klik + 1 konfirmasi Y/N** per tipe. TIPE 1 & TIPE 4 menggabung J&T+SPX;
TIPE 2 & TIPE 3 memisahnya (`--kurir jnt`/`--kurir spx`). TIPE 2 (tepat jam
13.00) menghabiskan wajib keluar Shopee (SPX Resi Pagi, ≤ 12.00); TIPE 4
(tepat jam 15.00) menghabiskan wajib keluar TikTok Shop (J&T Resi Siang,
≤ 15.00). **TIPE 1 juga dipakai di sore hari, 16.00–17.00** — dulu
jendelanya terus sampai 07.00 keesokan harinya, kini dibatasi sampai 17.00;
setelah itu malam/dini hari memakai `proses-malam.bat` (Urgent + SPX-J&T). Penentuan SKU mana yang "spesial" (dari Excel) **tidak
berubah** di semua tipe, tetap menggabung J&T+SPX; `--kurir` cuma
membatasi resi kurir mana yang benar-benar dipicklist saat itu.

## Istilah tim → proses-harian.bat / perintah program

| Istilah tim | Perintah (`jalankan.bat ...`) |
|---|---|
| Recheck stok | `--recheck-stok --jalankan` |
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
1. TIPE 1 - GABUNG J&T+SPX              (07.00-12.00 / 16.00-17.00)
2. TIPE 2 - DIPISAH + SPX RESI PAGI     (TEPAT JAM 13.00)
3. TIPE 3 - DIPISAH                     (13.00-15.00)
4. TIPE 4 - GABUNG LAGI + J&T RESI SIANG (TEPAT JAM 15.00)
0. Keluar
```

Tiap pilihan menjalankan urutan langkah di bawah **berurut, 1 kali klik +
1 konfirmasi Y/N**. Recheck stok **selalu** dijalankan PALING PERTAMA di
tiap tipe (lihat pembahasan lebih lanjut di bawah), lalu picklist sampel
(TikTok Shop nilai 0/kosong) **selalu** dicek setelahnya (dilewati kalau
tidak ada pesanannya), lalu picklist urgent (Lazada, GTL/SiCepat) **selalu**
ikut setelahnya — tidak ada lagi cara memicunya sendirian lewat menu (masih
bisa manual lewat `jalankan.bat --recheck-stok ...`/`jalankan.bat --sampel
...`/`jalankan.bat --urgent ...` kalau perlu).

### TIPE 1 — gabung J&T+SPX (07.00-12.00, dan 16.00-17.00)

1. RECHECK STOK
2. SAMPEL TIKTOK (NILAI 0)
3. URGENT LAZADA
4. URGENT GTL & SICEPAT
5. SPX - J&T SPESIAL
6. SPX - J&T 1 QTY REGULER
7. SPX - J&T KOMBINASI
8. TULIS PICKLIST.XLSX *(lihat "Rekap PICKLIST.xlsx" di bawah)*
9. UPLOAD FAKTUR & PESANAN KE IRESIS *(lihat "Upload faktur ke IRESIS" di bawah)*

Dipakai untuk siklus pagi **07.00-11.xx**, DAN dipakai lagi untuk siklus
sore **16.00-17.00** — begitu TIPE 4 selesai (jam 15.00-an), TIPE 1
menggantikannya sampai jam 17.00. Setelah 17.00 sampai TIPE 1 lagi besok
pagi jam 07.00 (malam/dini hari), pakai `proses-malam.bat` (lihat di
bawah), bukan TIPE 1.

### TIPE 2 — dipisah + SPX Resi Pagi (TEPAT jam 13.00)

1. RECHECK STOK
2. SAMPEL TIKTOK (NILAI 0)
3. URGENT LAZADA
4. URGENT GTL & SICEPAT
5. SPX ≤ 12.00 (SPX RESI PAGI)
6. J&T SPESIAL
7. J&T 1 QTY REGULER
8. J&T KOMBINASI
9. SPX - SPESIAL
10. SPX - 1 QTY REGULER
11. SPX - KOMBINASI
12. TULIS PICKLIST.XLSX
13. UPLOAD FAKTUR & PESANAN KE IRESIS *(lihat "Upload faktur ke IRESIS" di bawah)*

Dipicu **tepat jam 13.00**, menghabiskan wajib keluar Shopee (langkah 5,
channel Shopee, jam pesan WIB maksimal 12.00 siang hari itu, cukup
**1x sehari** — jangan diulang di TIPE 3). Jam **12.00-13.00 sengaja
dikosongkan** dari jendela tipe mana pun (jam istirahat tim) — bukan celah
jadwal.

### TIPE 3 — dipisah, tanpa SPX Resi Pagi (13.00-15.00)

1. RECHECK STOK
2. SAMPEL TIKTOK (NILAI 0)
3. URGENT LAZADA
4. URGENT GTL & SICEPAT
5. J&T SPESIAL
6. J&T 1 QTY REGULER
7. J&T KOMBINASI
8. SPX - SPESIAL
9. SPX - 1 QTY REGULER
10. SPX - KOMBINASI
11. TULIS PICKLIST.XLSX
12. UPLOAD FAKTUR & PESANAN KE IRESIS *(lihat "Upload faktur ke IRESIS" di bawah)*

Dipakai **setelah TIPE 2 selesai** (kapan pun itu, tidak harus tepat jam
13.00) **dan sebelum TIPE 4 dimulai** — jam 13.00 sampai 15.00. **Tidak
dipakai lagi** di luar rentang ini (malam hari pakai `proses-malam.bat`, lihat
di bawah).

### TIPE 4 — gabung lagi + J&T Resi Siang (TEPAT jam 15.00)

1. RECHECK STOK
2. SAMPEL TIKTOK (NILAI 0)
3. URGENT LAZADA
4. URGENT GTL & SICEPAT
5. J&T ≤ 15.00 (J&T RESI SIANG)
6. SPX - J&T SPESIAL *(digabung, seperti TIPE 1 - bukan dipisah)*
7. SPX - J&T 1 QTY REGULER *(digabung)*
8. SPX - J&T KOMBINASI *(digabung)*
9. TULIS PICKLIST.XLSX
10. UPLOAD FAKTUR & PESANAN KE IRESIS *(lihat "Upload faktur ke IRESIS" di bawah)*

Dipicu **tepat jam 15.00**, menghabiskan wajib keluar TikTok Shop (langkah
4, channel TikTok Shop, kurir J&T, jam pesan WIB maksimal 15.00 hari itu,
cukup **1x sehari** — jangan diulang di TIPE 1 berikutnya). Mulai langkah 5,
kurir **tidak** dipisah lagi — langsung memakai pola gabungan TIPE 1, karena
setelah J&T Resi Siang selesai tidak ada lagi alasan bisnis untuk memisah
J&T/SPX hari itu. Setelah TIPE 4 selesai, lanjut ke **TIPE 1** (lihat di
atas) sampai jam 17.00.

### proses-malam.bat (tanpa menu)

Satu klik + 1 konfirmasi Y/N, tanpa cek jam & tanpa Recheck Stok/Sampel/IRESIS: 1. Urgent Lazada,
2. Urgent GTL & SiCepat (tanpa `--lewati-malam`, jadi tidak ditahan), 3. SPX - J&T SPESIAL,
4. 1 QTY REGULER, 5. KOMBINASI (J&T+SPX digabung), 6. Tulis PICKLIST.xlsx, lalu rekap waktu.

### Upload faktur ke IRESIS (langkah paling terakhir tiap TIPE)

**Sejak 2026-10-07**: langkah **UPLOAD FAKTUR & PESANAN KE IRESIS** (`--upload-iresis --jalankan`) jadi
langkah paling akhir tiap TIPE 1-4. Dulu langkah manual tim: unduh Excel "Daftar Penjualan
Faktur" dari Jubelio lalu upload ke menu *Upload Resi* IRESIS supaya database IRESIS
(picklist/resi/status) ter-update. Sekarang program mengunduh laporan 2 hari terakhir
(`--hari N` untuk mengubah) ke `laporan-faktur/` lalu mengunggahnya lewat `src/iresis.py`.

- **Sejak 2026-10-07 (sniff 14:12)**: langkah yang sama juga mengunggah laporan **PESANAN**
  (`reference=order`, endpoint & form IRESIS sama) sebagai upload ke-2, rentang 4 hari
  (3 hari ke belakang + hari ini; ubah dengan `--hari-pesanan N`), disimpan sebagai
  `laporan-faktur/daftar_penjualan_pesanan_*.xlsx`. Gagalnya faktur tidak membatalkan upload
  pesanan (dan sebaliknya); exit code 1 kalau salah satu gagal.
- Butuh `IRESIS_USERNAME` & `IRESIS_PASSWORD` di `.env` (opsional `IRESIS_URL`,
  `IRESIS_NAMA_PK`, `IRESIS_CA_BUNDLE`); PC harus satu LAN dengan server IRESIS.
- **Revisi 2026-10-08**: jam **20.00-04.59** semua yang terkait IRESIS (unduh faktur/pesanan +
  upload) **dilewati otomatis** (`jam_tanpa_iresis()` di `src/main.py`; langkah di `.bat` tetap
  tampil tapi langsung selesai). Paksa manual: `jalankan.bat --upload-iresis --jalankan --paksa`.
- Upload ulang aman (IRESIS melewati baris yang tidak berubah).
- Gagal (server mati/login salah/respons aneh): TIPE tetap selesai, peringatan "UPLOAD IRESIS
  GAGAL" dicetak mencolok & muncul lagi di rekap waktu; upload ulang manual dengan
  `jalankan.bat --upload-iresis --jalankan`.

### Rekap PICKLIST.xlsx (langkah terakhir tiap TIPE)

**Revisi 2026-10-06**: langkah **TULIS PICKLIST.XLSX** (`--tulis-excel --jalankan`) jadi
langkah PALING TERAKHIR di tiap TIPE 1-4. Selama langkah-langkah sebelumnya, tiap picklist
cuma masuk antrean (`logs/antrian_picklist_excel.jsonl`); baru di langkah ini `PICKLIST.xlsx`
dibuka & disimpan **sekali** (±2 menit, file ~51 ribu baris). Dulu dibuka & disimpan di TIAP
langkah, sehingga TIPE 2/3 kehilangan ±15-20 menit cuma untuk Excel (insiden 2026-10-06).

- Picklist dari `--lanjut` manual juga masuk antrean → ikut tertulis di akhir TIPE
  berikutnya, atau langsung lewat `jalankan.bat --tulis-excel --jalankan`.
- Kalau `PICKLIST.xlsx` sedang dibuka di Excel/rusak: antrean TIDAK dibuang, muncul di blok
  PERHATIAN rekap akhir TIPE, dicoba lagi otomatis di TIPE berikutnya. **Tutup Excel sebelum
  TIPE selesai** supaya rekap langsung tertulis.

Implementasi kode: `catat()`/`terapkan()` di `src/rekap_master_excel.py`,
`tulis_picklist_excel()` di `src/main.py`.

### Jam tunda Urgent Lazada & GTL/SiCepat

**Revisi 2026-10-02**: pesanan urgent yang jam pesannya (WIB) masih jauh dari waktu proses
tidak buru-buru dipicklist — ditahan dulu, baru dilanjutkan otomatis sekali TIPE 1 jam 16.00
dijalankan lagi:

| | Urgent Lazada | Urgent GTL/SiCepat |
|---|---|---|
| Jam tunda (WIB) | di atas 14.00 | di atas 15.00 |
| Dilanjutkan otomatis setelah | jam 16.00 | jam 16.00 |

Berlaku di setiap TIPE (07.00-15.00): pesanan yang jam pesannya di atas jam tunda hari itu
TIDAK ikut picklist saat itu — bukan dibuang, cuma ditahan sampai jendela TIPE 1 jam 16.00
(lihat jadwal harian di bawah) dijalankan, lalu otomatis ikut tanpa batas jam lagi (karena
sudah lewat jam 16.00, batas tunda diabaikan sepenuhnya). Implementasi kode:
`JAM_CUTOFF_URGENT_LAZADA`/`JAM_CUTOFF_URGENT_GTL_SICEPAT`/`JAM_LANJUT_URGENT` &
`_saring_jam_urgent()` di `src/proses_label.py`.

**Revisi 2026-10-08**: TIPE 1 yang dijalankan di jendela malam (16.00-06.59) **melewati**
langkah 3 & 4 (Urgent Lazada, Urgent GTL & SiCepat) lewat `--urgent ... --lewati-malam`
(`jam_malam()` di `src/main.py`) — sebelumnya pesanan yang ditahan ikut terambil begitu jam 16.00.
TIPE 1 pagi (07.00-12.00) tetap menjalankan urgent. Pesanan urgent yang tertahan tidak hilang:
diproses lagi di TIPE 1 pagi / TIPE 2-4 besok, atau manual lewat `jalankan.bat --urgent`.

### Recheck stok

Dijalankan **PALING PERTAMA di tiap TIPE 1-4** (langkah 1, sebelum picklist sampel) — cek
ulang stok untuk SEMUA pesanan yang berstatus stok kosong (`EMPTY_STOCK`, biasanya bekas
picklist sebelumnya yang gagal karena stok tidak ada). Pesanan yang stoknya sudah tersedia
lagi otomatis kembali ke proses normal, sehingga ikut terhitung di langkah-langkah
berikutnya (sampel/urgent/spesial/reguler) TIPE yang sama. Kalau tidak ada pesanan stok
kosong saat itu, langkah ini otomatis dilewati tanpa memanggil Jubelio lagi.

| | Recheck stok |
|---|---|
| Lingkup | SEMUA pesanan `EMPTY_STOCK` sekaligus (bukan per-pesanan/per-SKU) |
| Dipicu di | TIPE 1-4, langkah 1 (paling pertama, tiap kali TIPE dijalankan) |
| CLI | `--recheck-stok` |

Implementasi kode: `ambil_stok_kosong()`/`recheck_stok()` di `src/jubelio.py`,
`recheck_stok_pesanan()` di `src/main.py`.

### Picklist sampel (TikTok Shop nilai 0/kosong)

Dicek **langkah 2 di tiap TIPE 1-4** (setelah Recheck Stok, sebelum Urgent Lazada) — pesanan
channel TikTok Shop yang nilainya 0/kosong (sampel/kreator) digabung jadi **1 picklist**
("SAMPEL-TIKTOK"), bukan dibuang. Kalau tidak ada pesanan sampel saat itu, langkah ini
otomatis dilewati tanpa membuat picklist apa pun, lalu lanjut ke langkah berikutnya.

| | Picklist sampel |
|---|---|
| Channel | TikTok Shop ("Shop \| Tokopedia") |
| Syarat | nilai pesanan (`grand_total`) 0 atau kosong |
| Dipicu di | TIPE 1-4, langkah 2 (setelah Recheck Stok, tiap kali TIPE dijalankan) |
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
| Kurir | SPX saja (kurir Shopee lain diproses alur reguler) | J&T saja |
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
| 1 | 07.00-11.59 **dan** 16.00-16.59 | Pagi "07.00-12.00" + sore "16.00-17.00" (dicek sebagai jam-dalam-sehari, berulang tiap hari). |
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

## proses-event.bat — mode event (10.10, 11.11, 12.12, dst)

Dipakai **seharian penuh** di hari event (tanggal kembar / promo besar) **menggantikan**
`proses-harian.bat`. Beda utamanya: J&T, SPX Hemat, dan SPX Standard **dipisah sepanjang hari**
(bukan bergantian digabung/dipisah per TIPE). Alur harian tidak disentuh — kalau ada masalah di
hari event, tim langsung kembali ke `proses-harian.bat`. `proses-event-uji.bat` = versi mode uji
(tanpa `--jalankan`, tanpa konfirmasi, tanpa pertanyaan), langkahnya dijaga identik dengan versi
sungguhan oleh `tests/test_bat.py`.

### Pemisahan kurir

| Kurir | Spesial | 1 qty reguler (satuan) | Kombinasi | Per lantai saja |
|---|---|---|---|---|
| **J&T** | ya | ya | ya | – |
| **SPX Hemat** | ya | ya | ya | – |
| **SPX Standard** | – | – | – | ya (lantai 1 / 2 / 3 / LAINNYA) |

SPX Standard volumenya kecil, jadi seluruh pesanannya digabung lalu dipecah per lantai rak gudang
saja (tidak ada pemisahan spesial/satuan/kombinasi). Pembeda kurir diambil dari kolom `shipper`
Jubelio (`SPX Hemat`, `SPX Standard`) — filter `couriers[]` Jubelio menerima nilai selengkap
`spx hemat` / `spx standard` (sniff & uji langsung 2026-10-08; jangan pakai `hemat` saja, ikut
menangkap `J&T Express Hemat`).

### Dua pilihan menu

```
1. EVENT - SESI BIASA          (J&T / SPX HEMAT / SPX STANDARD dipisah)
2. EVENT - TEPAT JAM 13.00     (SHOPEE PAGI <= 12.00, lalu sesi biasa)
0. Keluar
```

**Pilihan 1 — sesi biasa (kapan saja):**

1. RECHECK STOK
2. SAMPEL TIKTOK (NILAI 0)
3. URGENT LAZADA *(`--lewati-malam`: dilewati 16.00-06.59, sama seperti TIPE 1)*
4. URGENT GTL & SICEPAT *(idem)*
5. J&T <= 15.00 (J&T RESI SIANG) — **opsional**, ditanya di awal (Y/N, bawaan N)
6. J&T SPESIAL
7. J&T 1 QTY REGULER
8. J&T KOMBINASI
9. SPX HEMAT SPESIAL
10. SPX HEMAT 1 QTY REGULER
11. SPX HEMAT KOMBINASI
12. SPX STANDARD (PER LANTAI)
13. TULIS PICKLIST.XLSX
14. UPLOAD FAKTUR & PESANAN KE IRESIS

**Pilihan 2 — tepat jam 13.00 (Shopee Pagi, cukup 1x sehari):**

1-4. sama seperti di atas, tetapi urgent **tanpa** `--lewati-malam` (seperti TIPE 2)
5. SPX STANDARD PAGI <= 12.00 (PER LANTAI)
6. SPX HEMAT PAGI SPESIAL
7. SPX HEMAT PAGI 1 QTY REGULER
8. SPX HEMAT PAGI KOMBINASI
9-11. J&T spesial / 1 qty / kombinasi
12-14. SPX Hemat spesial / 1 qty / kombinasi
15. SPX STANDARD (PER LANTAI)
16. TULIS PICKLIST.XLSX
17. UPLOAD FAKTUR & PESANAN KE IRESIS

Shopee Pagi mendahului langkah seharian supaya pesanan Shopee dengan jam pesan WIB maksimal
12.00 pasti masuk picklist pagi yang **foldernya terpisah** (tabel di bawah). Pesanan setelah
jam 12.00 diproses langkah seharian di pilihan yang sama. Kalau SKU spesial punya kurang dari 3
resi yang masuk jendela ≤ 12.00, SKU itu dilewati di langkah pagi dan baru diproses langkah
seharian (perilaku sama dengan SKU lain yang kurang dari 3 resi).

**J&T Resi Siang (≤ 15.00) tetap opsional.** Di pilihan 1 ditanya sekali di awal, tepat setelah
konfirmasi Y/N (supaya proses setelahnya tidak berhenti menunggu input); jawab `Y` hanya di sesi
sekitar jam 15.00, cukup 1x sehari. Di pilihan 2 tidak ditanya. Di versi uji selalu ditampilkan
(hanya baca).

### Istilah tim → perintah program

| Istilah tim | Perintah (`jalankan.bat ...`) |
|---|---|
| J&T spesial (event) | `--label --event --kurir jnt --tanpa-reguler --jalankan` |
| J&T 1 qty reguler (event) | `--reguler --event --kurir jnt --bagian 1qty --jalankan` |
| J&T kombinasi (event) | `--reguler --event --kurir jnt --bagian kombinasi --jalankan` |
| SPX Hemat spesial | `--label --event --kurir spx-hemat --tanpa-reguler --jalankan` |
| SPX Hemat 1 qty reguler | `--reguler --event --kurir spx-hemat --bagian 1qty --jalankan` |
| SPX Hemat kombinasi | `--reguler --event --kurir spx-hemat --bagian kombinasi --jalankan` |
| SPX Standard per lantai | `--spx-standard --jalankan` |
| SPX Hemat Pagi spesial / 1 qty / kombinasi | sama dengan SPX Hemat, `--kurir spx-hemat-pagi` |
| SPX Standard Pagi per lantai | `--spx-standard --pagi --jalankan` |
| J&T Resi Siang | `--jnt-siang --jalankan` (sama dengan harian) |

`--kurir spx-hemat` dan `--kurir spx-hemat-pagi` **ditolak tanpa `--event`** (exit 2, sebelum login
dan sebelum membuat folder sesi) — supaya salah ketik tidak diam-diam menghasilkan picklist dengan
hitungan spesial yang tidak dimaksud. `--event` hanya sah bersama `--label`/`--reguler` dan
`--kurir jnt|spx-hemat|spx-hemat-pagi`.

### Folder hasil dan cetak bulk

Tiap kelompok punya subfolder (di dalam folder sesi `label-pengiriman/<tanggal>/<sesi>/`) dan
jenis cetak sendiri. Jenis cetak harian gabungan (`spesial`, `satuan`, `kombinasi`) **tidak**
ikut mencetak folder event.

**Cara mencetak di hari event: jalankan `cetak-label.bat` → `2. EVENT`.** Di sana ada paket
**SEMUA EVENT** (berurutan J&T → SPX Hemat Pagi → SPX Hemat → SPX Standard, printer & konfirmasi
cukup sekali) dan paket per kelompok (J&T / SPX Hemat Pagi / SPX Hemat / SPX Standard). Langsung
tanpa menu: `cetak-label.bat --paket event-semua`. Kolom terakhir tabel berikut = jenis di menu.

| Hasil | Subfolder | `print_spesial.py --jenis` | `.bat` cetak |
|---|---|---|---|
| J&T (event) | `JNT_SPESIAL`, `JNT_SATUAN`, `JNT_KOMBINASI` (sama dengan harian) | `spesial-jnt`, `satuan-jnt`, `kombinasi-jnt` | menu EVENT → paket J&T |
| SPX Hemat | `SPXHEMAT_SPESIAL`, `SPXHEMAT_SATUAN`, `SPXHEMAT_KOMBINASI` | `spesial-spx-hemat`, dst | menu EVENT → paket SPX Hemat |
| SPX Hemat Pagi | `SPXHEMATPAGI_SPESIAL`, `SPXHEMATPAGI_SATUAN`, `SPXHEMATPAGI_KOMBINASI` | `spesial-spx-hemat-pagi`, dst | menu EVENT → paket SPX Hemat Pagi |
| SPX Standard | `SPX_STANDARD` (`SPX-STANDARD-LANTAI*`) | `spx-standard` | menu EVENT → paket SPX Standard |
| SPX Standard Pagi | `SPX_PAGI` (`SHOPEE-PAGI-SPX-STANDARD-LANTAI*`) | `spx-pagi` | menu EVENT → paket SPX Standard |
| J&T Resi Siang | `JNT_SIANG` | `jnt-siang` | menu HARIAN → J&T RESI SIANG |

### Aturan SKU spesial di mode event

Dengan `--event`, penentuan SKU spesial dihitung **per kurir** (`hitung_sku_spesial(...,
kurir_hitung=...)` di `sku_spesial.py`): minimal 3 resi sejenis **dari kurir itu saja** — resi J&T
dan SPX Hemat **tidak digabung**, dan SPX Standard tidak ikut hitungan sama sekali. Tanpa
`--event` perilaku harian tetap: J&T + semua SPX digabung (lihat "Aturan permanen").

### Penjaga jam

Pilihan 2 diberi peringatan Y/N kalau dipilih di luar 12.00-15.59 (`dalam_jam_menu("E2")` —
Shopee Pagi baru masuk akal setelah jam 12.00). Pilihan 1 tidak punya jendela jam.

### Uji coba sebelum hari event pertama (10.10)

1. Di hari biasa, buka web Jubelio (Siap Proses) dan cek: jumlah filter kurir `spx hemat` +
   `spx standard` **sama dengan** `spx`. Kalau tidak sama, ada varian lain yang belum tertangani.
2. Jalankan `proses-event-uji.bat` pilihan 1 dan 2 (mode uji, hanya baca). Cek log: SPX Standard
   muncul hanya per lantai; SPX Hemat muncul sebagai spesial/satuan/kombinasi; tidak ada pesanan
   SPX kilat; jumlah per kelompok masuk akal terhadap angka di web Jubelio.
3. Di hari event jalankan lagi `proses-event-uji.bat` dulu, baru `proses-event.bat`. Setelah
   langkah pertama selesai, cek folder `label-pengiriman/<tanggal>/<sesi>/` dan hasil cetaknya
   (`cetak-label-*-spx-hemat.bat` dst) sebelum meneruskan sesi berikutnya.
4. Cadangan: `proses-harian.bat` tidak berubah dan tetap bisa dipakai kapan saja.

## Jadwal harian (sudah berjalan pakai program)

Dijalankan tim setiap hari, siklus 2 jam di jam kerja (jam bulat, lalu
diulang lagi setelah proses transfer bank/pembayaran selesai) dan 1x per
jam di luar jam kerja:

| Jam | Yang dijalankan | TIPE proses-harian.bat |
|---|---|---|
| 07.00 | Recheck stok, Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, SPX & J&T spesial, 1 qty reguler, kombinasi reguler (**digabung**) | 1 |
| 07.xx (setelah transfer) | (ulang) | 1 |
| 09.00 | (ulang) | 1 |
| 09.xx (setelah transfer) | (ulang) | 1 |
| 11.00 | (ulang) | 1 |
| 11.xx (setelah transfer) | (ulang) | 1 |
| 12.00-13.00 | *(jam istirahat, tidak ada proses)* | - |
| 13.00 | Recheck stok, Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, **SPX ≤ 12.00 (SPX Resi Pagi)**, J&T spesial, J&T 1 qty reguler, J&T kombinasi, SPX spesial, SPX 1 qty reguler, SPX kombinasi (**dipisah**) | 2 |
| 13.xx (setelah TIPE 2 selesai) | Recheck stok, Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, J&T spesial, J&T 1 qty reguler, J&T kombinasi, SPX spesial, SPX 1 qty reguler, SPX kombinasi (**dipisah**, tanpa SPX Resi Pagi lagi) | 3 |
| 15.00 | Recheck stok, Sampel TikTok (nilai 0/kosong), Urgent Lazada, Urgent GTL/SiCepat, **J&T ≤ 15.00 (J&T Resi Siang)**, lalu SPX-J&T spesial, 1 qty reguler, kombinasi (**digabung lagi**) | 4 |
| 16.00 | Recheck stok, Sampel TikTok (nilai 0/kosong), ~~Urgent Lazada, Urgent GTL/SiCepat~~ (**dilewati** 16.00-06.59, lihat catatan di bawah), SPX-J&T spesial, 1 qty reguler, kombinasi (**digabung**, tanpa J&T Resi Siang lagi - sudah selesai jam 15.00) | 1 |
| 16.xx (setelah transfer, sebelum 17.00) | (ulang) | 1 |
| 17.00-06.xx (malam & dini hari) | Urgent Lazada, Urgent GTL/SiCepat, SPX-J&T (**digabung**), 1x per jam bila ada pesanan masuk | `proses-malam.bat` |

**Catatan jam 13.00**: hanya siklus ini yang menyertakan SPX Resi Pagi
(langkah 5 di TIPE 2 — channel Shopee, jam pesan WIB maksimal 12.00 siang
hari itu). Setelah jam 13.00, siklus berikutnya (13.xx dst, sebelum jam
15.00) pakai TIPE 3, bukan TIPE 2 lagi.

**Catatan jam 15.00**: hanya siklus ini yang menyertakan J&T Resi Siang
(channel TikTok Shop, jam pesan WIB maksimal 15.00 siang hari itu). Setelah
jam 15.00, siklus berikutnya (16.00-17.00) **kembali**
pakai TIPE 1 (gabung) — bukan TIPE 3 (dipisah) lagi, karena alasan bisnis
pemisahan J&T/SPX (TIPE 2 & TIPE 3) sudah tidak berlaku setelah J&T Resi
Siang selesai.

**Jadwal malam & dini hari (17.00-07.00)** memakai `proses-malam.bat`
(lihat bagian "proses-malam.bat" di atas), bukan lagi siklus TIPE 1. Kalau belum pernah dicoba pakai program di luar jam kerja normal
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
  `sku_spesial.py`) di **alur harian** (`proses-harian.bat`) **selalu**
  menggabung resi J&T+SPX (minimal 3 resi sejenis), terlepas dari TIPE mana
  yang dipakai. `--kurir` di TIPE 2/TIPE 3 hanya membatasi resi kurir mana
  yang benar-benar dipicklist saat proses SKU spesial itu berjalan — bukan
  mengubah daftar SKU spesial itu sendiri. **Satu-satunya pengecualian**
  adalah mode event (`proses-event.bat`, flag `--event`): di sana hitungan
  dilakukan per kurir (J&T dan SPX Hemat terpisah, SPX Standard tidak ikut).
  Pengecualian ini tidak pernah aktif tanpa `--event`.

---

Rencana pengembangan yang belum diimplementasikan (proses otomatis berbasis
polling, pemisahan SPX Standard vs SPX Hemat) didokumentasikan terpisah di
[rencana-pengembangan.md](rencana-pengembangan.md) supaya tidak tercampur
dengan jadwal operasional aktual di atas.
