# Desain: Pecah picklist 1qty reguler berdasarkan grup rak

Status: disetujui user (2026-10-02), siap masuk tahap rencana implementasi.

## Latar belakang

Picklist "1 SKU 1 qty reguler" (`--reguler --bagian 1qty`, lihat
[docs/jadwal-proses.md](../../jadwal-proses.md)) saat ini digabung jadi 1 picklist (dipecah
cuma kalau melebihi `MAKS_PESANAN_PICKLIST`), tanpa memperhatikan lokasi rak barangnya di
gudang. Permintaan pengembangan: pecah lagi berdasarkan grup rak paling depan, supaya picker
tidak bolak-balik antar zona gudang. Grup yang diproses: **2A, 3A, 1B, 2B, 3B** (grup 1A tidak
ada di gudang ini, dikonfirmasi lewat data sniff `sniff_jubel_20261002_134304`).

## Temuan riset (sniff)

Tidak ada field rak di daftar pesanan (`wms/sales/v2/orders/ready-to-process/`) — field
lengkapnya (lihat sniff terbaru) cuma berisi info pesanan/channel, tanpa info lokasi rak.
Rak cuma bisa diketahui lewat 2 endpoint:

1. `GET core-api/sales/v2/orders/zones-racks-combination?...&combination_type=racks&status=PAID`
   — daftar string kombinasi rak unik lintas SEMUA pesanan berstatus PAID, format
   `GROUP-ZONE-SLOT` (mis. `2A-B1-1`). Pesanan multi-item di rak berbeda muncul sebagai
   gabungan dipisah `" - "` (mis. `"1B-A3-4 - 2A-E1-4 - ..."`) — diabaikan untuk kebutuhan ini
   karena pesanan 1 qty (1 SKU, 1 item) selalu di 1 rak saja.
2. `GET core-api/wms/sales/v2/orders/ready-to-process/?...&combination[]=<nilai>&combination_type=racks`
   — endpoint YANG SAMA dengan yang sudah dipakai `_ambil_pesanan_channel_mentah()`/
   `cari_pesanan()`, ditambah parameter `combination[]` (bisa diulang) untuk filter pesanan
   yang kombinasi raknya PERSIS cocok salah satu nilai yang dikirim. Parameter ini bisa
   digabung dengan `channel_ids[]`/`couriers[]` yang sudah ada.

Belum ada rekaman sniff pembuatan picklist sungguhan dengan filter rak aktif (sniff yang ada
baru eksplorasi listing) — risiko diterima user (lihat keputusan di sesi brainstorming),
karena `buat_picklist_channel()` generik (terima `salesorder_id` apa saja) sehingga perilakunya
seharusnya sama persis dengan alur urgent/reguler yang sudah ada.

## Keputusan desain (hasil brainstorming dengan user)

- **Default diganti**, bukan opsi baru: tiap kali `--reguler --bagian 1qty` dijalankan,
  otomatis dipecah per grup rak. Bagian `"kombinasi"` TIDAK berubah.
- Split per rak tetap jalan bersama `--kurir jnt`/`--kurir spx` (pola existing: `--kurir`
  cuma membatasi resi kurir mana yang diproses, bukan konsep terpisah) — label jadi gabungan
  kurir + grup, mis. `JNT-1QTY-REGULER-2A`.
- Pesanan 1qty yang rak-nya di luar 5 grup target (kombinasi kosong/prefix lain) digabung jadi
  1 picklist **"lainnya"** (label `1QTY-REGULER-LAINNYA`), supaya tidak ada pesanan yang
  hilang/tertinggal.
- Urutan pembuatan picklist: **2A → 3A → 1B → 2B → 3B → lainnya** (urutan yang diminta user,
  bukan urutan alfabetis).
- Pendekatan teknis "ambil daftar kombinasi dulu, lalu query ulang per grup" disetujui
  meski menambah beberapa request API per hari (bukan per pesanan) — tidak ada cara lain yang
  terlihat di data sniff saat ini.

## Alur data

1. Hitung `satu_qty` seperti sekarang lewat `pisah_reguler()` (sudah terfilter: bukan SKU
   spesial, kurir sesuai, total_qty==1).
2. `ambil_kombinasi_rak(k)` — paging `zones-racks-combination` (`status=PAID`,
   `combination_type=racks`) sampai habis, kembalikan semua string kombinasi TUNGGAL (buang
   yang mengandung `" - "` dan yang kosong).
3. `kelompokkan_kombinasi_per_grup(kombinasi)` — kelompokkan string per prefix (bagian sebelum
   `-` pertama), hanya untuk prefix yang ada di `GRUP_RAK = ["2A", "3A", "1B", "2B", "3B"]`;
   prefix lain diabaikan di langkah ini (otomatis jadi bagian "lainnya" lewat langkah 5).
4. `ambil_id_per_grup_rak(k, kombinasi_per_grup, channel_ids, couriers)` — untuk tiap grup,
   query `ready-to-process` dengan `combination[]=<semua kombinasi grup itu>` (dipecah batch
   maks ±40 nilai per request kalau grup itu py banyak rak, supaya URL tidak kepanjangan) +
   `channel_ids`/`couriers` yang sama seperti `ambil_pesanan_reguler()`. Hasil: `{grup: set
   salesorder_id}`.
5. `pisah_satu_qty_per_rak(satu_qty, id_per_grup)` — partisi murni (tanpa API): untuk tiap
   pesanan di `satu_qty`, cek masuk grup mana (lewat `salesorder_id`); yang tidak match grup
   manapun → `"lainnya"`. Return `dict` dengan key `GRUP_RAK + ["lainnya"]`, urutan sesuai
   `GRUP_RAK`.
6. Tiap kelompok (termasuk "lainnya" kalau tidak kosong) diproses lewat `_proses_channel_batch()`
   yang sudah ada (tetap kena `bagi_batch()`/`MAKS_PESANAN_PICKLIST` kalau grup itu > batas).

## Komponen (fungsi baru/diubah) — `src/proses_label.py`

- `GRUP_RAK = ["2A", "3A", "1B", "2B", "3B"]` — konstanta baru, urutan proses.
- `ambil_kombinasi_rak(k) -> list[str]` — baru.
- `kelompokkan_kombinasi_per_grup(kombinasi: list[str]) -> dict[str, list[str]]` — baru, murni
  logika (tidak panggil API).
- `ambil_id_per_grup_rak(k, kombinasi_per_grup, channel_ids, couriers) -> dict[str, set[int]]`
  — baru.
- `pisah_satu_qty_per_rak(satu_qty: list[dict], id_per_grup: dict[str, set[int]]) ->
  dict[str, list[dict]]` — baru, murni logika (tidak panggil API) → gampang ditest.
- `rencana_reguler()` & `proses_reguler()` — diubah: untuk `bagian == "1qty"` (atau `bagian is
  None`, dipanggil lewat pipeline grup rak di atas, lalu loop per grup (urutan `GRUP_RAK +
  ["lainnya"]`) memanggil `_proses_channel_batch()`/cetak rencana per grup, bukan 1 batch
  gabungan. Bagian `"kombinasi"` tidak berubah.
- Label: `"1QTY-REGULER-2A"`, …, `"1QTY-REGULER-LAINNYA"`; dengan `--kurir` tetap diawali
  seperti sekarang lewat `_label_kurir()`/`_label_kurir_file()` yang sudah ada (mis.
  `JNT-1QTY-REGULER-2A`).

## Penanganan error & edge-case

- `zones-racks-combination` gagal/timeout atau tidak ada grup yang ketemu → fallback: semua
  `satu_qty` masuk `"lainnya"` (log warning), supaya pesanan tidak hilang — tidak menghentikan
  seluruh proses reguler.
- Grup yang hasilnya kosong (tidak ada pesanan) → dilewati tanpa bikin picklist kosong, sama
  seperti pola `_proses_channel_batch()` sekarang (`if not batch: return []`).
- Kegagalan 1 grup (mis. picklist ditolak Jubelio) tidak menghentikan grup lain — pola
  `try/except` per grup sama seperti `proses_reguler()` sekarang (kegagalan 1 bagian tidak
  menghentikan bagian lain).

## Testing

- Test murni logika (tanpa API) di `tests/test_proses_label.py` gaya yang sudah ada:
  `kelompokkan_kombinasi_per_grup()` dan `pisah_satu_qty_per_rak()` dengan data sintetis
  (termasuk kasus 1A tidak ada, kasus kombinasi gabungan diabaikan, kasus grup kosong, kasus
  sisa masuk "lainnya").
- Test end-to-end lewat `JubelioPalsu` (mock) yang sudah ada: tambah endpoint palsu
  `zones-racks-combination` + `ready-to-process` dengan `combination[]`, pastikan
  `proses_reguler(bagian="1qty")` menghasilkan picklist terpisah per grup sesuai urutan
  `GRUP_RAK` + lainnya.

## Di luar cakupan

- Bagian `"kombinasi"` reguler (multi-baris/qty>1) tidak berubah.
- Picklist urgent, Shopee Pagi, J&T Resi Siang, dan SKU spesial tidak terpengaruh.
- Tidak ada opsi CLI baru — perilaku `--reguler --bagian 1qty` berubah langsung (bukan
  opt-in).
