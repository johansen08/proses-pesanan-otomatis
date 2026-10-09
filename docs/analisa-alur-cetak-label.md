# Analisa Alur Jubelio: Filter SKU → Picklist → Picking → Siap Dikirim → Label PDF

> **Cakupan dokumen ini**: rekaman untuk alur **SKU spesial** (1 picklist = 1 SKU, langkah 1
> memfilter per SKU). Langkah 2b–6 di bawah (buat picklist tanpa validasi SKU sampai label PDF)
> **dipakai juga** oleh 2 alur lain yang ditambahkan belakangan dan TIDAK direkam ulang di sini
> karena mekanismenya identik, cuma sumber/filter pesanan langkah 1 yang beda:
> - **Picklist urgent** (`proses_urgent()`): langkah 1 memfilter per `channel_ids` (skenario
>   Lazada) atau per `couriers` tanpa `channel_ids` (skenario GTL-SiCepat, lintas channel -
>   urgent-nya ditentukan kurir, bukan channel), bukan per SKU. Lihat README bagian
>   "Picklist urgent".
> - **Picklist sisa reguler** (`proses_reguler()`): langkah 1 memfilter `channel_ids` (TikTok
>   Shop/Shopee) + `couriers` (J&T/SPX) + `order_type` (buang "kilat"), lalu disaring lagi di
>   sisi kita (keluarkan resi SKU spesial, pisah 1 qty vs kombinasi). Lihat README bagian
>   "Picklist sisa reguler".
> - **Picklist Shopee Pagi** (`proses_shopee_pagi()`, ditambahkan belakangan): langkah 1
>   memfilter `channel_ids` (Shopee saja, tanpa filter kurir), lalu disaring lagi di sisi kita
>   berdasarkan jam pesan WIB (maksimal jam 12 siang hari itu — `JAM_CUTOFF_SHOPEE_PAGI` di
>   `ambil_pesanan_shopee_pagi()`). Dijalankan manual 1x sehari, bukan bagian alur otomatis
>   `--label --jalankan`. Lihat README bagian "Picklist Shopee Pagi".
>
> Di kedua alur itu, "SKU" pada tabel Pencatatan di bawah diisi **nama channel** (mis. `LAZADA`,
> `1QTY-REGULER`), bukan SKU asli - dipakai `lanjutkan_picklist()` cuma sebagai label nama
> file/kolom riwayat. Detail kode: `proses_label.py` (`ambil_pesanan_channel()`,
> `ambil_pesanan_reguler()`, `_proses_channel_batch()`).

Sumber:
- `sniff_jubel_20260926_090249`: 2 putaran (BM-AKS28-2, BM-AKS28-4). Body POST belum terekam.
- `sniff_jubel_20260926_092943`: 2 putaran lengkap **dengan body POST**.
  - T01-BSBI-5 → PICK-000154839, 6 pesanan
  - T01-BSCT-3 → PICK-000154840, 9 pesanan

Semua request ke `https://open.jubelio.com/core-api/` memakai header
`authorization: <token login>` (tanpa "Bearer"). Request ke server report (`report.jubelio.com` / `report-prod.jubelio.com`) memakai
cookie `JB_OMNI_ACCESS_TOKEN=<token login>`. Keduanya sudah dipakai di `jubelio.py`.

Semua langkah di bawah ✅ **terlihat langsung di rekaman** (URL, body, dan respons).

---

## Ringkasan alur per SKU spesial

| # | Menu di web | Request | Catatan |
|---|---|---|---|
| 1 | Penjualan › Pesanan › Siap Proses (filter) | `GET wms/sales/v2/orders/ready-to-process/` | |
| 2 | (tombol buat picklist) | `POST sales/picklists/items-to-pick/` → `POST wms/sales/picklists/` | bisa gagal 500 |
| 3 | Proses Pesanan › Picking › **Diproses** › Selesaikan | `GET sales/picklists/{id}` → `POST wms/sales/picklists/` (is_completed) | **tunggu** status FINISH_PICK |
| 4 | Proses Pesanan › Picking › **Selesai** (cari PICK-…, centang semua) | `GET wms/sales/v2/orders/finish-pick/?q=PICK-…` | |
| 5 | Siap Dikirim | `POST shipment/shipper-pickup-time/` → `POST wms/sales/shipments/orders/` (diulang) | tunggu semua resi terisi |
| 6 | Cetak label | `GET reports/shipping-label/` → Telerik REST API → PDF | |

---

## 1. Filter pesanan

`GET wms/sales/v2/orders/ready-to-process/`

| Parameter | Nilai | Arti |
|---|---|---|
| `q` | `T01-BSBI-5` | SKU |
| `sku_filter` | `true` | `q` dicari sebagai SKU |
| `couriers[0]`, `couriers[1]` | `j&t`, `spx` | kurir |
| `is_total_qty` | `0` | ikut aktif bersama filter "1 SKU 1 qty" |
| `page`, `page_size` | `1`, `25`/`200` | |
| `sort_by`, `sort_direction` | `grand_total`/`transaction_date`, `DESC`/`ASC` | |

Respons `{data:[...], totalCount}`. Per pesanan: `salesorder_id`, `salesorder_no`, `shipper`,
`grand_total`, `total_qty`, `location_id`, `stock_status`.

- Filter Jubelio **tidak** membuang pesanan kreator. Program harus membuang `grand_total == 0` sendiri.
- Program tetap memeriksa `total_qty == 1` sendiri.
- **Daftar ini bisa berisi pesanan yang sebenarnya sudah diproses di tempat lain** (lihat langkah 2).

## 2. Buat picklist

**a.** `POST sales/picklists/items-to-pick/`
```json
{"ids":[9068023,9068128,9068161,9068180,9068214,9067835]}
```
Respons: array item, masing-masing berisi `salesorder_detail_id, item_id, location_id, qty_ordered,
salesorder_id, bundle_item_id, package_detail_id, package_id, end_qty (stok), ...`

**b.** `POST wms/sales/picklists/`
```json
{"is_completed":false,"is_warehouse":true,
 "items":[{"salesorder_detail_id":14506334,"item_id":9436,"location_id":-1,"qty_ordered":1,
           "salesorder_id":9067835,"bundle_item_id":0,"package_detail_id":0,"package_id":0}, ...],
 "merge_location":false,"picker_id":null,"picklist_id":0,"picklist_no":"[auto]",
 "salesorderIds":[9068023,9068128,9068161,9068180,9068214,9067835]}
```
Respons: `{"status":"ok","data":{"picks":[{"picklist_id":154839,"picklist_no":"PICK-000154839","status":"ok"}],"invalidSO":[]}}`

⚠️ **Kasus gagal (terekam):** percobaan pertama dengan 11 pesanan ditolak **HTTP 500**:
> Pesanan sudah dipakai di transaksi lain. Pesanan: TT-586258229788574763-48087,
> Status Channel: AWAITING_COLLECTION, Status Sekarang: FINISH_PICK, Status Dituju: PICK

Setelah filter dimuat ulang, hanya tersisa 6 pesanan, dan picklist berhasil dibuat.
Program harus menangani ini: saat error ini muncul, filter ulang lalu coba lagi dengan
pesanan yang tersisa. Seluruh picklist ditolak, bukan hanya pesanan yang bermasalah.

Web juga langsung membuka cetak picklist: `GET reports/wms/pick-list/?ids[0]=154839` (report "Picklist Gudang").

## 3. Selesaikan picking (Picking › Diproses › Selesaikan)

**a.** `GET sales/picklists/154839` → `{picklist_id, picklist_no, is_completed:false, items:[...]}`.
Per item: `picklist_detail_id, item_id, location_id, qty_ordered, qty_picked:"0", salesorder_detail_id,
salesorder_id, bundle_item_id, package_id, package_detail_id, wms_status:"PICK", bin_id:null, invoice_no`.

**b.** `GET wms/default-bin/-1` (-1 = location_id) → `{"bin_id":14,"bin_final_code":"LX-BX-KX-RX-1",...}`

**c.** `POST wms/sales/picklists/`
```json
{"is_completed":true,"is_warehouse":true,
 "items":[{"bin_id":14,"bundle_item_id":0,"item_id":9436,"location_id":-1,
           "picklist_detail_id":13590336,"qty_ordered":1,"qty_picked":1,
           "salesorder_detail_id":14506334,"salesorder_id":9067835,"invoice_no":null,
           "update":true,"package_id":0,"package_detail_id":0}, ...],
 "picklist_id":154839,"picklist_no":"PICK-000154839","note":null}
```
Nilai `qty_picked` = `qty_ordered`, dan `bin_id` diambil dari default-bin lokasi.
Respons sama dengan langkah 2b.

**d. Tunggu sampai selesai.** Di UI, tulisan merah berubah menjadi hitam; popup jangan ditutup
sebelum itu. Di API, penanda selesainya adalah `GET sales/picklists/154839` yang mengembalikan:
- `is_completed: true` dan `completed_date` terisi
- setiap item `wms_status: "FINISH_PICK"`, `qty_picked: "1.0000"`, `bin_id: 14`

Program akan mengulang GET ini sampai kondisi tersebut terpenuhi (dengan batas waktu)
sebelum lanjut ke langkah 4.

## 4. Picking › Selesai (cari PICK-…, centang semua)

`GET wms/sales/v2/orders/finish-pick/?q=PICK-000154839&page=1&page_size=25&is_printed=0&sort_by=transaction_date&sort_direction=DESC`

Menampilkan pesanan picklist itu yang labelnya belum dicetak (`is_printed=0`).
Di rekaman, pencarian sebelum picking diselesaikan mengembalikan `totalCount: 0`, lalu setelah
selesai mengembalikan 6. "Centang semua" berarti memakai semua `salesorder_id` dari hasil ini.

## 5. Siap Dikirim

**a.** `POST shipment/shipper-pickup-time/` dengan body `{"ids":[...]}`, **satu salesorder_id per jenis kurir**.
Respons: pilihan slot pickup Shopee/SPX, mis. `[{"shipper":"SPX Hemat","timeSlots":[{"id":"1790413200","text":"26-Sep-2026 "}]}]`.
Di kedua rekaman, tidak ada request lain yang mengirim slot pickup, jadi langkah ini hanya menampilkan pilihan.

**b.** `POST wms/sales/shipments/orders/` dengan body `{"ids":[semua salesorder_id]}`
Respons per pesanan: `salesorder_id, shipment_no, tracking_no, shipper, internal_status, ...`.
**Diulang tiap ±3,5 detik dengan body yang sama sampai semua `tracking_no` terisi**
(rekaman: 4x untuk 6 pesanan dan 4x untuk 9 pesanan; resi J&T `JY…`, SPX `SPXID…`).

## 6. Label PDF (tanpa browser)

**a.** `GET reports/shipping-label/?ids[0]=…&ids[1]=…&tz=Asia/Jakarta`
→ `{"status":"ok","url":"https://report-prod.jubelio.com/?&token=…","title":"Label Pengiriman"}`

Untuk pesanan **Lazada** (`source == 4`), web menambahkan `&isFromLz=true` →
`"title":"Label Pengiriman Lazada"` (template report lain; parameter `list` berisi
`logo_delivery`, `shipper`, dst. per pesanan). Tanpa `isFromLz` Jubelio memberi template
umum sehingga PDF Lazada beda dari unduhan manual (sniff 2026-10-07, insiden label Lazada).
Program menambahkannya otomatis di `lanjutkan_picklist()` bila semua pesanan yang dicetak
berasal dari Lazada.

Template Lazada berukuran **A5 (148x210 mm)**, bukan 100x150 mm seperti template umum. PDF
disimpan apa adanya (A5), sama dengan unduhan manual. Label Lazada dicetak **manual** oleh tim
dengan skala custom **68%** (100/148 = 67,6%) di kertas 100x150 mm; tidak ada cetak bulk Lazada
(`print_spesial.py` hanya untuk SPESIAL/GTL-SICEPAT/SATUAN/KOMBINASI).

**b.** `GET <url>` → HTML berisi
`jQuery('#reportViewer').telerik_ReportViewer({... "reportSource":{"report":"Label Pengiriman-…","parameters":{...}} ...})`

**c.** Telerik REST API di `https://<host report>/api/reports/` (host sama dengan URL halaman label di langkah a/b):

| | Request | Respons |
|---|---|---|
| 1 | `POST clients` `{"timeStamp":<ms>}` | `{"clientId"}` |
| 2 | `POST clients/{c}/parameters` `{"report":…,"parameterValues":<reportSource.parameters>}` | daftar parameter `[{id, value, ...}]` |
| 3 | `POST clients/{c}/instances` `{"report":…,"parameterValues":{id: value dari langkah 2}}` | 201 `{"instanceId"}` |
| 4 | `POST clients/{c}/instances/{i}/documents` `{"format":"PDF","deviceInfo":{"ImmediatePrint":true,"BasePath":"/api/reports"},"useCache":true}` | 202 `{"documentId"}` |
| 5 | `GET .../documents/{d}/info` diulang tiap ±0,5 detik | 202 = masih diproses, 200 = selesai |
| 6 | `GET .../documents/{d}?response-content-disposition=inline` (rekaman asli) | `application/pdf` |

Terbukti di rekaman: isi langkah 2 **sama persis** dengan `reportSource` di HTML, dan
`parameterValues` langkah 3 **sama persis** dengan `{id: value}` dari respons langkah 2.
Web membuat dokumen HTML5 lebih dulu lalu PDF (dengan `baseDocumentID`). Program (`unduh_label()`
di `proses_label.py`) langsung meminta PDF terlebih dahulu — sudah terbukti jalan ke server
Jubelio — dan baru fallback ke jalur HTML5→PDF kalau permintaan PDF langsung gagal dengan
error biasa (mis. HTTP 500).

**Waktu normal & penanganan macet (revisi 2026-10-06)**: dari 613 label 02–06/10/2026 (selisih
jam di nama file vs waktu file ditulis = seluruh `unduh_label()`), pembuatan label normalnya
median 3–5 detik, paling lama 25,5 detik — label 198 halaman pun cuma 7,2 detik, jadi ukuran
label bukan penyebab lambat. Dokumen yang belum jadi setelah `TUNGGU_PDF_S` (45 detik) dianggap
**macet** di node report-prod-nya: seluruh alur di atas diulang dari langkah a dengan client
baru (URL & token baru, bisa jatuh ke node lain) — sama seperti client yang hilang (HTTP 410
"Client ... not found. Expired.") — sampai `TUNGGU_LABEL_S` (240 detik) habis, baru picklist
dinyatakan TERHENTI. Dulu dokumen macet ditunggu 180 detik lalu dicoba HTML5 180 detik lagi di
client/node yang SAMA (6 menit sia-sia per picklist, menahan langkah urgent/reguler yang
berurutan — insiden 2026-10-06). Tiap cek status (langkah 5) dibatasi `TUNGGU_INFO_DOKUMEN_S`
(30 detik) per request.

**Urutan host (revisi 2026-10-07)**: API Jubelio selalu mengembalikan URL di `report-prod.jubelio.com`, tapi host itu sering bermasalah (410/504/dokumen macet), sedangkan `report.jubelio.com` melayani report yang sama dan lebih stabil. `unduh_label()` mengganti host URL dari API (`HOST_REPORT` di `proses_label.py`) dan menjalankan SELURUH alur (halaman → client → dokumen → unduh) di SATU host per percobaan: `report.jubelio.com` dulu; gagal apa pun → ulang dari awal di `report-prod.jubelio.com`; lalu bergantian untuk 410/dokumen macet. `unduh_excel()` di `jubelio.py` memakai urutan host yang sama.

Beda kecil dari rekaman asli: langkah 6 di kode saat ini memakai
`response-content-disposition=attachment` (bukan `inline` seperti di rekaman) — sama-sama
mengunduh `application/pdf`, cuma header disposisinya beda.

---

## Pencatatan

Setiap proses menyimpan 1 baris ke `data/riwayat_picklist.xlsx` (`catat_riwayat()`, konstanta
`KOLOM_RIWAYAT` di `proses_label.py`) dengan 8 kolom: **Waktu, SKU, No Picklist, Total
Pesanan** (jumlah `salesorderIds` dikurangi `invalidSO`), **Resi Keluar** (jumlah resi yang
sudah dapat nomor resi), **File Label** (nama file PDF), **Catatan** (kosong jika sukses;
`GAGAL: ...` atau `TERHENTI: ...` + perintah `--lanjut` jika berhenti di tengah), dan
**Durasi** (lama proses SKU/skenario itu). Kalau file sedang dibuka di Excel, ditulis ke
`data/riwayat_picklist.csv` sebagai gantinya.

| Waktu | SKU | No Picklist | Total Pesanan | Resi Keluar | File Label | Catatan | Durasi |
|---|---|---|---|---|---|---|---|
| 26-09-2026 09:06 | BM-AKS28-2 | PICK-000154834 | 19 | 19 | PICK-000154834_SPESIAL_BM-AKS28-2_...pdf | | 0:02:10 |
| 26-09-2026 09:10 | BM-AKS28-4 | PICK-000154835 | 8 | 8 | PICK-000154835_SPESIAL_BM-AKS28-4_...pdf | | 0:01:32 |
| 26-09-2026 09:37 | T01-BSBI-5 | PICK-000154839 | 6 | 6 | PICK-000154839_SPESIAL_T01-BSBI-5_...pdf | | 0:01:48 |
| 26-09-2026 09:40 | T01-BSCT-3 | PICK-000154840 | 9 | 9 | PICK-000154840_SPESIAL_T01-BSCT-3_...pdf | | 0:02:05 |

Catatan: penanda `SPESIAL` di nama file hanya berlaku untuk picklist SKU spesial (Alur 1).
Picklist urgent/reguler/Shopee Pagi/J&T Resi Siang (Alur 2-5) tetap pakai nama skenario
tanpa penanda ini, mis. `PICK-000155230_LAZADA_...pdf` (lihat README.md bagian terkait).

(Kolom Resi Keluar/File Label/Durasi pada contoh di atas diisi sesuai skema saat ini untuk
ilustrasi — nilai persisnya tidak ada di rekaman sniff asli, yang cuma merekam sampai
Waktu/SKU/No picklist/Total pesanan.)

## Risiko dan pengaman untuk otomatisasi

- Langkah 2–5 **mengubah status pesanan sungguhan** (picklist, picking selesai, resi diminta ke
  marketplace). Program perlu **mode uji** yang hanya menampilkan rencana tanpa mengirim apa pun.
- Setiap langkah punya penanda selesai yang jelas (langkah 3d, 5b, 6c-5). Program menunggu penanda
  itu dengan batas waktu, dan tidak lanjut jika belum terpenuhi.
- Jika proses berhenti di tengah, program melanjutkan dari picklist yang sudah ada (dicari lewat
  `finish-pick/?q=PICK-…` atau `sales/picklists/{id}`), bukan membuat picklist baru.
- Pesanan yang resinya tidak keluar sampai batas waktu, dan `invalidSO`, dicatat di log.
