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

## B. Mode khusus hari event (SPX Standard vs SPX Hemat)

Pemisahan **J&T vs SPX** saat pembuatan picklist (dulu direncanakan di sini
untuk "hari event") **sudah diimplementasikan** lewat `--kurir` dan dipakai
tiap hari di TIPE 2/TIPE 3 (lihat [jadwal-proses.md](jadwal-proses.md)) —
bukan cuma hari event lagi. Yang **belum** diimplementasikan: pemisahan
lebih lanjut antara **SPX Standard vs SPX Hemat** (keduanya sama-sama "SPX"
di Jubelio hari ini, perlu dicek dulu field/atribut apa yang membedakan
varian ini sebelum implementasi):

| Kurir | SKU spesial? | 1 SKU 1 qty reguler | Kombinasi reguler |
|---|---|---|---|
| **J&T** | Ya | Ya | Ya |
| **SPX Standard** | Perlu dikaji ulang — mungkin tidak perlu dipisah spesial kalau volumenya kecil | Ya | Ya |
| **SPX Hemat** | Ya (sama seperti J&T) | Ya | Ya |

Aturan "SPX tipe pengiriman kilat selalu dikeluarkan" (lihat
[jadwal-proses.md](jadwal-proses.md) bagian "Aturan permanen") tetap
berlaku untuk ketiga baris di tabel ini.

> **Catatan**: "J&T Resi Siang" (channel TikTok Shop, kurir J&T, ≤ 15.00)
> yang tadinya direncanakan di sini **sudah diimplementasikan** — lihat
> bagian "J&T Resi Siang & SPX Resi Pagi" di
> [jadwal-proses.md](jadwal-proses.md) dan [README.md](../README.md) bagian 5.
