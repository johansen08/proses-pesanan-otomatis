# Rencana Pengembangan (belum diimplementasikan)

Bagian ini didokumentasikan dulu supaya idenya tidak terlewat, **bukan**
berarti sudah ada di kode saat ini. Jadwal operasional yang **sudah**
berjalan ada di [jadwal-proses.md](jadwal-proses.md).

## A. Proses otomatis berbasis polling (ganti jadwal jam manual)

Alih-alih jadwal jam manual seperti di [jadwal-proses.md](jadwal-proses.md),
rencana ke depan program jalan otomatis dengan logika:

1. Cek jumlah pesanan "Siap Proses" setiap **5 menit**.
2. Begitu totalnya **≥ 200**, mulai proses (urutan sama seperti TIPE
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

## B. Mode khusus hari event (SPX Standard vs SPX Hemat) — **SUDAH diimplementasikan 2026-10-08**

> Diimplementasikan: `proses-event.bat` / `proses-event-uji.bat`, flag `--event` /
> `--spx-standard` / `--pagi` / `--kurir spx-hemat|spx-hemat-pagi` di `main.py`,
> `proses_label.proses_spx_standard()` dkk, `sku_spesial.hitung_sku_spesial(kurir_hitung=...)`,
> jenis cetak baru di `print_spesial.py`. Jadwal, urutan langkah, folder hasil, dan rencana uji
> coba: [jadwal-proses.md](jadwal-proses.md) bagian "proses-event.bat — mode event". Bagian ini
> dibiarkan sebagai catatan keputusan.

Pemisahan **J&T vs SPX** saat pembuatan picklist sudah berjalan tiap hari lewat `--kurir` (TIPE
2/TIPE 3). Untuk hari event, SPX dipisah lagi menjadi **SPX Standard** dan **SPX Hemat**
(pembeda: field `shipper` Jubelio; filter `couriers[]` menerima `spx hemat` / `spx standard`,
dikonfirmasi sniff & uji langsung 2026-10-08):

| Kurir | SKU spesial? | 1 SKU 1 qty reguler | Kombinasi reguler |
|---|---|---|---|
| **J&T** | Ya | Ya | Ya |
| **SPX Standard** | Tidak — volumenya kecil, hanya dipecah per lantai 1/2/3/LAINNYA | – | – |
| **SPX Hemat** | Ya (sama seperti J&T) | Ya | Ya |

Keputusan (2026-10-08): penentuan SKU spesial dihitung **per kurir** di mode event (J&T dan SPX
Hemat tidak digabung, SPX Standard tidak ikut); Shopee Pagi mode event memisah SPX Standard
(per lantai) dan SPX Hemat (spesial/satuan/kombinasi) dengan **folder terpisah**; J&T Resi Siang
tetap opsional; menu event hanya dua pilihan.

Aturan "SPX tipe pengiriman kilat selalu dikeluarkan" (lihat
[jadwal-proses.md](jadwal-proses.md) bagian "Aturan permanen") tetap
berlaku untuk ketiga baris di tabel ini.

> **Catatan**: "J&T Resi Siang" (channel TikTok Shop, kurir J&T, ≤ 15.00)
> yang tadinya direncanakan di sini **sudah diimplementasikan** — lihat
> bagian "J&T Resi Siang & SPX Resi Pagi" di
> [jadwal-proses.md](jadwal-proses.md) dan [README.md](../README.md) bagian 5.

## C. Otomatisasi upload faktur Jubelio ke IRESIS (**SUDAH diimplementasikan 2026-10-07**)

> Diimplementasikan: `src/iresis.py`, `jubelio.ambil_url_faktur()`, `main.py --upload-iresis`,
> langkah terakhir tiap TIPE `proses-harian*.bat`, tes `tests/test_iresis.py`. Dokumen ini
> dibiarkan sebagai catatan hasil sniff; yang BELUM: rekaman kasus gagal (lihat risiko).

Setelah proses pesanan selesai, tim selalu melakukan langkah **manual**: unduh Excel
"Daftar Penjualan Faktur" terbaru dari Jubelio, lalu upload ke menu *Upload Resi* di
IRESIS supaya database IRESIS (status resi/picklist/ship) ikut ter-update. Alurnya sudah
terekam di `sniff/sniff_output/sniff_jubel_20261007_105328*` (2026-10-07) dan bisa
diotomatisasi dengan HTTP langsung, tanpa browser — pola yang sama dengan `src/jubelio.py`.

### Hasil sniff (2026-10-07)

**1. Unduh laporan dari Jubelio** (Penjualan > Laporan > "Daftar Penjualan Faktur")

| Langkah | Request |
|---|---|
| Minta URL laporan | `GET https://open.jubelio.com/core-api/reports/sales-list/date-range/?date_from=<..>&date_to=<..>&reference=invoice&hpp=true&tz=Asia/Jakarta` dengan header `authorization: <token login Jubelio>` → `{"status":"ok","url":"https://report-prod.jubelio.com/?&token=..."}` |
| Unduh Excel | URL di atas dengan path `/xlsx/` (fungsi `jubelio.url_excel()` + `unduh_excel()` yang sudah ada, bisa dipakai ulang apa adanya) |
| Hasil | `Daftar Penjualan.xlsx` (±1,1 MB, 1 sheet `Data1`, 23 kolom: NO_PESANAN, NO_RESI, PICKLIST, TGL_*/WAKTU_*, MARKETPLACE, TOKO, SKU, QTY, NO RAK, KURIR, STATUS_PESANAN, ...) |

Rentang tanggal yang dipakai tim saat itu: 2 hari (kemarin 00:00 s/d hari ini 23:59 WIB).
Berbeda dengan `URL_LAPORAN` "ready-to-pick-list" di `jubelio.py` (laporan lain, host `api`).

**2. Upload ke IRESIS** (server lokal `https://192.168.3.37/new-iresis/`, Apache/PHP,
sertifikat kemungkinan self-signed)

| Langkah | Request |
|---|---|
| Buka halaman login (dapat cookie `siresi_session`) | `GET /new-iresis/login` |
| Login | `POST /new-iresis/auth` form-urlencoded: `nama_komputer=&username=<user>&password=<..>&nama_pk=SRV-1&status_performa=NORMAL` → 303 ke `/new-iresis/` |
| Upload | `POST /new-iresis/receipt/upload-receipt-action`, multipart, field file bernama **`receiptFile`** (+ `token` kosong), header `X-Requested-With: XMLHttpRequest` → `{"code":201,"message":"Total Data Terinput: 0 \| Dilewati: 3 \| Duplikat: 0 \| Diupdate: 608 \| Data Tidak Berubah: 14661 \| Waktu: 1.5 dtk","data":{"token":"...","baris":15404}}` |
| Cek progres | `GET /new-iresis/receipt/upload-receipt-progress?token=<token>` → `data.status == "selesai"`, `persen == 100` |

Catatan: file yang diupload memang berisi ±15 ribu baris (laporan 2 hari) dan IRESIS
mengabaikan yang tidak berubah, jadi upload ulang aman (idempoten: "Data Tidak Berubah").

### Rencana implementasi

1. **`src/iresis.py` (baru)** — `login()`, `upload_faktur(path)`, `tunggu_selesai(token)`;
   `verify=False` + matikan warning `urllib3` khusus host ini (atau `IRESIS_CA_BUNDLE`
   di `.env`). Sukses = `code in (200, 201)` dan progres `selesai`; parse ringkasan
   (Terinput/Dilewati/Duplikat/Diupdate/Tidak Berubah) dan log.
2. **`src/jubelio.py`** — tambah `ambil_url_faktur(token, date_from, date_to)` untuk endpoint
   `sales-list/date-range`, lalu pakai ulang `unduh_excel()` (perlu parameter folder/nama file
   supaya tidak bentrok dengan `laporan-siap-proses/`; simpan di `laporan-faktur/`).
3. **`src/main.py`** — flag baru `--upload-iresis` (default mode uji: hanya unduh + tampilkan
   jumlah baris & rencana upload; upload sungguhan dengan `--jalankan`, konsisten dengan alur lain).
   Opsi `--hari N` (default 2) untuk rentang tanggal.
4. **`.env`** — `IRESIS_URL`, `IRESIS_USERNAME`, `IRESIS_PASSWORD`, opsional `IRESIS_NAMA_PK`
   (jangan dikomit; tambahkan contoh di `docs/instalasi.md`).
5. **Penempatan di alur** — langkah terakhir tiap TIPE `proses-harian.bat` (setelah
   `--tulis-excel --jalankan`), karena data faktur baru lengkap setelah resi tercetak. Kegagalan
   upload **tidak boleh** menggagalkan TIPE: cukup `cetak_bermasalah()` + simpan ke
   `peringatan_gagal.py` agar muncul lagi di rekap waktu. Update `test_bat.py` (urutan langkah)
   dan ingat aturan CRLF `.bat`.
6. **Tes offline** — `tests/test_iresis.py` dengan `requests` ditiru (pola `test_jubelio.py`),
   respons diambil dari rekaman sniff: login 303, upload 201, progres selesai, kasus
   login gagal / respons non-JSON / progres tidak selesai sampai batas tunggu.

### Risiko & pertanyaan terbuka

- **Sniff belum mencakup kegagalan**: format error IRESIS (file salah, sesi kedaluwarsa,
  password salah) belum terekam — rekam sekali dengan file rusak sebelum finalisasi.
- Akun IRESIS: pakai akun khusus bot (bukan akun personal `0001-ika`) agar log aktivitas jelas.
- Server `192.168.3.37` hanya terjangkau dari jaringan kantor — Task Scheduler harus jalan di PC
  yang satu LAN; cek perilaku bila server mati (retry 3x lalu peringatan).
- Apakah rentang 2 hari selalu cukup, atau perlu mengikuti sesi terakhir? (Usul: mulai dari 2
  hari karena itu kebiasaan tim; IRESIS toh melewati data yang tidak berubah.)
- Apakah `nama_pk`/`status_performa` hanya metadata komputer? (Diasumsikan ya; tetap kirim
  nilai yang sama seperti rekaman.)
