# Referensi API Jubelio & IRESIS (hasil rekaman sniff)

Disarikan dari seluruh rekaman `sniff/sniff_output/` (26 rekaman, 2026-09-26 s/d 2026-10-09) sebelum
rekaman lama dihapus. Hanya endpoint **unik** (id/token/uuid dinormalkan jadi `{id}`/`{token}`/`{hex}`)
yang dicatat, lengkap dengan parameter request dan bentuk response. Nilai sensitif (password, token,
cookie, isi alamat/nama pembeli) sengaja TIDAK disertakan. Kalau Jubelio mengubah alurnya, rekam ulang
lewat `sniff/run_sniff_jubel.bat`.

Host yang relevan:

| Host | Fungsi |
|---|---|
| `open.jubelio.com` | API utama (`/core-api/...`), JSON |
| `id-platform-api-wms-scan.jubelio.com` | API WMS scan (daftar ready-to-pick) |
| `report-prod.jubelio.com`, `report.jubelio.com` | Server laporan Telerik (render PDF/XLSX) |
| `v2.jubelio.com` | Front-end web (HTML saja, tidak dipakai program) |
| `192.168.3.37` | IRESIS lokal (`/new-iresis/...`) |

Host lain yang muncul di rekaman hanyalah pelacak/iklan/chat (Google Analytics/Ads, DoubleClick, Hotjar,
Freshchat/Freshworks, OpenAI pixel, Cloudflare, `account-service`/`analytic-collector`/`api-billing`/
`vault`/`val.jubelio.io`) — tidak relevan untuk otomatisasi.

## 1. Autentikasi (`open.jubelio.com`)

Semua panggilan `core-api` memakai cookie token `JB_OMNI_ACCESS_TOKEN` (header `authorization` dari login).

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/core-api/login` | JSON `{email, password, fid}` | `{token, userName, fullName, subscription, roles[], acls[], currentLocation, currentCompany, companies[], picking_type, ignore_packing, is_wms_migrated, ...}`. Gagal: HTTP 500 `{statusCode:500, error, message, code:"Invalid email or password"}` |
| POST | `/core-api/verify` | (tanpa body) | profil sesi, sama bentuk dengan login tanpa `token` (+ `uuid`, `fid`) — dipanggil browser berulang untuk cek sesi |

## 2. Pesanan & picklist (`open.jubelio.com`)

| Method | Path | Parameter | Response |
|---|---|---|---|
| GET | `/core-api/wms/sales/v2/orders/ready-to-process/` | query: `page`, `page_size` (25/50/100/200), `sort_by` (`transaction_date`/`due_date`/`grand_total`), `sort_direction` (`ASC`/`DESC`), `q` (cari SKU/nomor), `couriers[n]` (`gtl`,`j&t`,`sicepat`,`spx`,`spx hemat`,`spx standard`), `channel_ids[n]` (mis. 4, 64, 131076), `order_type[n]` (`umum`,`prioritas`,`po`,`dropshipper`,`kirim_hari_ini`,`cod`,`multi_location`,`multi_package`), `location_ids[n]` (`-1`=semua), `is_total_qty` (0/1), `sku_filter` (true/false), `combination[n]` + `combination_type=racks` (filter rak, mis. `1B-A2-3`) | `{data[], totalCount, statusCode, error}`. **HTTP 429** `{statusCode:429, error:"Too Many Requests"}` bila terlalu sering (sudah ditangani retry+backoff) |
| GET | `/core-api/sales/v2/orders/zones-racks-combination` | `page`, `page_size`, `sort_by=combination`, `sort_direction`, `q`, `combination_query`, `combination_type=racks`, `status=PAID`, `location_ids[0]=-1` | `{data[], totalCount}` (daftar kombinasi zona-rak) |
| GET | `/core-api/sales/orders/stat/` | `current_date` (ISO UTC) | `{failed, ready_to_pick}` (string angka) |
| GET | `/core-api/wms/sales/orders/stat` | — | `{failed_pick, empty_stock, request_cancel}` |
| GET | `/core-api/wms/sales/orders/instant-shipping-stat` | — | `{total_failed_shipping}` |
| POST | `/core-api/sales/picklists/items-to-pick/` | JSON `{ids:[salesorder_id,...]}` | array `{salesorder_detail_id, item_id, item_full_name, location_id, location_name, qty_ordered, salesorder_id, salesorder_no, bundle_item_id, package_id, package_detail_id, ...}` |
| POST | `/core-api/wms/sales/picklists/` | JSON `{picklist_id:0, picklist_no:"[auto]", is_completed:false, is_warehouse:true, merge_location:false, picker_id:null, note:null, salesorderIds:[...], items:[{salesorder_detail_id, item_id, location_id, qty_ordered, salesorder_id, bundle_item_id, package_detail_id, package_id}]}` | `{status, data:{picks[], invalidSO[]}}`. Gagal: HTTP 500 `{statusCode, error, message, code:"error: Pesanan sudah dipakai di transaksi lain. Pesanan: <no>, Status Channel: ..., Status Sekarang: FINISH_PICK, Status Dituju: PICK"}` |
| GET | `/core-api/sales/picklists/{id}` | — | `{picklist_id, picklist_no, created_date, completed_date, is_completed, picker_id, note, items[]}` |
| GET | `/core-api/wms/sales/v2/picklists/confirm-pick/` | `page`, `page_size`, `sort_by=picklist_id`, `sort_direction`, `q` (mis. `PICK-000155182`) | `{data[], totalCount}` (picklist menunggu konfirmasi picking) |
| GET | `/core-api/wms/sales/v2/orders/finish-pick/` | `page`, `page_size` (25/200), `sort_by`, `sort_direction`, `q` (nomor picklist), `is_printed=0` | `{data[], totalCount}` (pesanan siap resi setelah picking selesai) |
| GET | `id-platform-api-wms-scan.jubelio.com/wms/sales/v2/orders/ready-to-pick/` | `page`, `page_size`, `sort_by`, `sort_direction`, `q`, `is_printed=0` | `{data[], totalCount}` |
| GET | `/core-api/wms/sales/v2/orders/empty-stock/` | `page`, `q`, `sort_by`, `page_size`, `sort_direction` | `{data[], totalCount}` |
| POST | `/core-api/wms/sales/empty-stock` | JSON `{salesorder_ids:[...]}` | `{status:<num>}` (tandai stok kosong) |
| GET | `/core-api/wms/sales/orders/recheck-stock/` | — | `{status}` |
| POST | `/core-api/wms/sales/shipments/orders/` | JSON `{ids:[salesorder_id,...]}` | array `{salesorder_id, salesorder_no, shipment_no, tracking_no (resi), shipper, courier_id, channel_status, internal_status, store_id, is_cod, label_printed_count, package_count, ...}` — dipakai `minta_resi()` untuk polling nomor resi |
| POST | `/core-api/shipment/shipper-pickup-time/` | JSON `{ids:[...]}` | array `{shipper, key, timeSlots[]}` |
| GET | `/core-api/lazada/get-orders-ids` | `ids=[id,id,...]` (array JSON di query) | array `{salesorder_id, source, store_id, channel_order_detail_id}` |
| GET | `/core-api/wms/default-bin/-1` | — | `{bin_id, location_id, bin_final_code, acknowledge_stock}` |

## 3. Laporan & unduhan (`open.jubelio.com` -> `report-prod.jubelio.com`)

Pola: `core-api/reports/...` mengembalikan `{status, url, title}`; `url` membuka halaman viewer di
`report-prod.jubelio.com/?token=<JWT>`. Dari sana PDF/XLSX dirender lewat API Telerik di bawah.

| Method | Path | Parameter | Response |
|---|---|---|---|
| GET | `/core-api/reports/wms/pick-list/` | `ids[0]=<picklist_id>` (bisa banyak), `tz=Asia/Jakarta` | `{status, url, title}` -> report "Picklist Gudang" |
| GET | `/core-api/reports/shipping-label/` | `ids[0..n]=<salesorder_id>` (dikelompokkan), `tz=Asia/Jakarta`, opsional `isFromLz=true` (label Lazada, template "Label Pengiriman Lazada" A5) | `{status, url, title}` -> report "Label Pengiriman" / "Label Pengiriman Lazada" |
| GET | `/core-api/reports/sales-list/date-range/` | `date_from`, `date_to` (format `Sun Oct 04 2026 00:00:00 GMT+0700 (Western Indonesia Time)`), `reference` (`invoice`/`order`), `hpp=true`, `tz=Asia/Jakarta` | `{status, url, title}` -> report "Daftar Penjualan" (Excel Faktur/Pesanan untuk IRESIS) |
| GET | `/core-api/reports/sales-list/ready-to-pick-list/` | `tz` | `{status, url, title}` -> "laporan siap proses" |
| GET | `/core-api/reports/import-status` | — | `{status, exists}` |

Server laporan (`report-prod.jubelio.com`, identik di `report.jubelio.com`; `{hex}` = id 11 karakter hex):

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/?token=<JWT>` | token dari `url` di atas | HTML viewer |
| POST | `/api/reports/clients` | form `timeStamp=<ms>` | `{clientId}` |
| GET | `/api/reports/clients/sessionTimeout` | — | `{clientSessionTimeout}` |
| GET | `/api/reports/version` | — | string versi |
| POST | `/api/reports/clients/{clientId}/parameters` | JSON `{report:"<NamaReport>-<tenant>-<companyId>", parameterValues:{reportName, companyId, tenantId, logo_url, address, city, state, postcode, country, company_name, email, ids[], report_path, channelCategory, list}}` | array definisi parameter `{name,type,text,multivalue,value,...}` |
| POST | `/api/reports/clients/{clientId}/instances` | JSON `{report, parameterValues:{company_name, pick_id (picklist), tz, report_path, ids[], logo_url, address, city, state, country, postcode, list (JSON string array {salesorder_id, city_code, district_code, shipping_service...})}}` | HTTP 201 `{instanceId}` |
| POST | `/api/reports/clients/{clientId}/instances/{instanceId}/documents` | JSON `{format:"PDF"\|"HTML5", deviceInfo:{enableSearch, ContentOnly, UseSVG, BasePath, ImmediatePrint}, useCache, baseDocumentID}` | HTTP 202 `{documentId}` |
| GET | `.../documents/{documentId}/info` | — | `{documentReady, pageCount, documentMapAvailable, renderingExtensions[], ...}`; HTTP 202 selama belum siap -> polling |
| GET | `.../documents/{documentId}` | `response-content-disposition=attachment\|inline` | **PDF** (`application/pdf`) |
| GET | `.../documents/{documentId}/pages/{n}` | — | `{pageReady, pageNumber, pageContent, pageStyles, ...}` (render HTML per halaman; tidak dipakai program) |
| GET | `/xlsx/?token=<JWT>` | token dari `url` laporan | **XLSX** (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) — jalur unduh Excel "Daftar Penjualan"/"laporan siap proses" |

Nama report yang terekam: `Picklist Gudang`, `Label Pengiriman`, `Label Pengiriman Lazada`, `Daftar Penjualan`
(format nama `<Nama>-<tenantId>-<companyId>`). `report_path` berbeda untuk Lazada
(`C:\inetpub\wwwroot\Reports\<tenant>`) vs lainnya (`\\172.16.7.7\report-server-repo\template\<tenant>`).

## 4. Data master & pengaturan (read-only, dipanggil browser saat memuat halaman)

Semua `GET open.jubelio.com/core-api/...`, response JSON. Program tidak bergantung pada ini, dicatat
supaya tahu fungsinya kalau muncul lagi di rekaman:

| Path | Parameter utama | Response (ringkas) |
|---|---|---|
| `/inventory/v2/`, `/inventory/v2/items/masters/`, `/variations/v2/` | `page`, `page_size`, `q` (SKU), `sort_by`, `sort_direction`, `bundle_filter` | `{data[], totalCount}` (+ `channels`, `locations`) |
| `/v2/inventory/items/{id}`, `/inventory/variation/{id}`, `/inventory/get-group-status/{id}` | — | detail item / varian / status grup |
| `/inventory/activity/` | `itemId`, `page`, `page_size`, `q`, `sort_by`, `sort_direction` | `{activities[], locations[], row_count, total_stock}` |
| `/inventory/category`, `/inventory/categories/item-category-tree/` | `page`, `pageSize`, `sortBy`, `sortDirection`, `q` / `id` | kategori |
| `/locations/`, `/locations/v2/list`, `/locations/v2/pos`, `/locations/integration-status/`, `/sales/pos-wms/v2/locations/`, `/store-locations/`, `/store-locations/setting` | paging; `storeIds[n]`, `is_tokopedia_bind_tts`, `check_existing_store`, `session_filter` | lokasi/gudang/toko; setting toko = `default_shipper`, `use_lazada_label`, `use_tiktok_label`, `shipmentsetting[]`, dst. |
| `/marketplace/all-channel`, `/marketplace/integration-status`, `/marketplace/integration-status-exclude-pos`, `/marketplace/channel-integration-status-exclude-pos`, `/marketplace/internal/store`, `/marketplace/excluded-warehouse`, `/marketplace/unmapped-warehouse` | `is_tokopedia_bind_tts` | daftar channel `{channel_id, channel_name}` & toko `{store_id, store_name, is_active, ...}` — sumber `channel_id` untuk filter `channel_ids[n]` |
| `/sales/v2/status-list/` | — | `{data[], totalCount}` daftar status pesanan |
| `/purchase/v2/orders/progress/` | paging | `{data[], totalCount}` |
| `/systemsetting/order-setting` | — | `{automatic_request_awb, automatic_create_picklist, picking_type, ignore_packing, ignore_shipping, picking_acknowledge_stock, ...}` |
| `/systemsetting/{batch-serial-setting, complete-order-setting, custom-category-mapping, invoice-setting, is-use-lazada-document/, location-layout-setting, warehouse-setting}` | — | pengaturan (bool/angka) |
| `/systemsetting/key-pair/` | `type` (`forceClosePos`,`internalShipment`) | `[{id,text}]` |
| `/systemsetting/test-modules` | `module_code` | `{status,data[]}` |
| `/systemsetting/users/`, `/systemsetting/v2/users/` | paging, `q` | `{data[], totalCount}` |
| `/v2/companies/{id}` | `page`, `pageSize` | `[{company_id, company_name}]` |
| `/error-map/` | — | `[{error_message, friendly_message, parsing_type, type}]` |
| `/notification/v2/all` (GET), `/notification/v2/read` (POST) | `page`, `page_size` | notifikasi / `{status}` |
| `/questionnaire`, `/analytic/integration-status` | — | status onboarding / integrasi |

## 5. IRESIS lokal (`https://192.168.3.37/new-iresis/`, sertifikat self-signed)

Sesi berbasis cookie; semua halaman HTML kecuali yang ditandai JSON.

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/new-iresis/`, `/login`, `/welcome` | — | HTML (307/redirect ke login bila belum login) |
| POST | `/new-iresis/auth` | form `username`, `password`, `nama_komputer`, `nama_pk`, `status_performa` (mis. `NORMAL`) | HTTP 303 redirect ke `welcome` + cookie sesi |
| GET | `/new-iresis/welcome/get_dashboard_data` | — | HTML fragmen dashboard |
| GET | `/new-iresis/receipt/upload_receipt` | — | JSON `{view:<html form>, message}` — form berisi input `token` (hidden) & file `receiptFile` (.xls/.xlsx) |
| POST | `/new-iresis/receipt/upload-receipt-action` | multipart: file `receiptFile` + field `token` (kosong); body multipart tidak terekam di sniff, rujuk `src/iresis.py` | JSON `{code:201, message:"Total Data Terinput: n \| Dilewati: n \| Duplikat: n \| Diupdate: n \| Data Tidak Berubah: n \| Waktu: x dtk", data:{token, durasi, baris}}` |
| GET | `/new-iresis/receipt/upload-receipt-progress` | query `token` (dari respons upload), `_` (cache buster, ms) | JSON `{code:200, message, data:{status, tahap, pesan, persen, hasil, mulai, diperbarui}}` — polling progres proses di server |
| GET | `/new-iresis/report/receipt_report` | — | JSON `{view:<html>, message}` — dua tab: "Laporan Total Resi" (tab0) & "Laporan Total Picklist" (tab1) |
| POST | `/new-iresis/report/{token}` | form DataTables: `draw`, `start`, `length`, `order[0][column]`, `order[0][dir]`, `search[regex]`, `columns[n][data\|name\|searchable\|orderable\|search][...]`, `start_date`, `end_date` | HTML/JSON baris tabel (dipakai `ambil_total_picklist()`) |
| POST | `/new-iresis/report/export-to-excel-receipt-report-tab0` | form `reportrange` | file Excel laporan total resi |

## 6. Alur ringkas yang dipakai program

1. `POST /core-api/login` -> cookie token.
2. `GET .../orders/ready-to-process/` (filter kurir/channel/order_type) -> pilih pesanan.
3. `POST /sales/picklists/items-to-pick/` -> `POST /wms/sales/picklists/` (buat picklist).
4. `GET .../picklists/confirm-pick/` + konfirmasi -> `GET .../orders/finish-pick/` (pesanan Picking > Selesai).
5. `POST /wms/sales/shipments/orders/` (polling `tracking_no`/resi).
6. `GET /reports/shipping-label/` -> `report-prod` (`parameters` -> `instances` -> `documents` -> `info` polling -> unduh PDF).
7. `GET /reports/sales-list/date-range/` -> `report-prod/xlsx/?token=` -> upload ke IRESIS (`upload-receipt-action` + polling `upload-receipt-progress`) -> `report/{token}` untuk Total Picklist.
