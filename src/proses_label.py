"""Proses pesanan Jubelio sampai label pengiriman PDF - 5 alur, langkah 3-6 dipakai bersama
(lihat analisa-alur-cetak-label.md untuk detail request/respons langkah-langkah ini):
  1. Filter pesanan Siap Proses (disaring pakai aturan masing-masing, lihat di bawah)
  2. Buat picklist                          -> PICK-000xxxxxx
  3. Selesaikan picking, tunggu semua item berstatus FINISH_PICK
  4. Ambil pesanan picklist di Picking > Selesai
  5. Siap dikirim, tunggu semua nomor resi keluar
  6. Unduh label PDF (Telerik report-prod, tanpa browser)
Setiap picklist dicatat di riwayat_picklist.xlsx. Picklist SKU spesial (Alur 1) juga dicatat
per-resi di detail-resi-spesial.xlsx/detail-resi-bukan-spesial.xlsx - lihat catat_detail_spesial().

Alur 0 - picklist sampel (fungsi rencana_sampel()/proses_sampel()): lintas SKU, pesanan channel
TikTok Shop ("Shop | Tokopedia") yang nilainya 0/kosong (lihat CHANNEL_ID_TIKTOK_SHOP &
catatan TT-586350230929114342-67824, 01-10-2026) - SEBELUMNYA dibuang diam-diam oleh
ambil_pesanan_channel() (dipakai Alur 2-5) tanpa pernah masuk picklist apa pun. Mulai
proses-harian.bat TIPE 1-4, picklist ini SELALU dicek PALING PERTAMA (sebelum picklist
urgent) lewat main.py --sampel: 1 picklist kalau ada pesanannya, dilewati kalau tidak ada,
lalu lanjut seperti biasa ke urgent/spesial/reguler. ambil_pesanan_channel() (Alur 2-5) TETAP
mengeluarkan pesanan sampel ini dari hasilnya supaya tidak dobel diproses.

Alur 1 - SKU spesial (fungsi rencana()/proses()/lanjutkan()): per SKU, filter kurir J&T/SPX
(default, digabung) atau 1 kurir saja lewat parameter `kurir` ("jnt"/"spx" - lihat
KURIR_PILIHAN, dipakai TIPE 2 & TIPE 3 supaya J&T dan SPX jadi picklist terpisah
saat pembuatan, lihat JADWAL-PROSES.md), disaring lagi dengan aturan SKU spesial (resi
tunggal, qty 1, nilai != 0, SKU >= 3 resi sejenis - lihat panduan-sku-spesial.md; penentuan
SKU spesial itu sendiri TETAP menggabung J&T+SPX, `kurir` hanya membatasi resi mana yang
benar-benar dipicklist). 1 picklist = 1 SKU, validasi SKU-nya sama semua lewat _cek_item().
Nama file label PDF alur ini (dan hanya alur ini) disisipi penanda `SPESIAL`:
`PICK-000xxxxxx_SPESIAL_<SKU>_<tanggal>_<jam>.pdf`, DAN disimpan di subfolder `SPESIAL`
di dalam folder sesi (mis. `label-pengiriman/2026-10-02/1/SPESIAL/`, bukan langsung di
`label-pengiriman/2026-10-02/1/`) - lihat TAG_SPESIAL, dipakai lewat parameter `tag` di
lanjutkan_picklist() baik untuk penanda nama file maupun nama subfolder. Alur ini juga satu-
satunya yang mengisi detail-resi-spesial.xlsx/detail-resi-bukan-spesial.xlsx (langsung di
folder sesi, BUKAN di subfolder SPESIAL) - lihat catat_detail_spesial(). Alur 2 & 3 juga
disimpan di subfolder masing-masing (`URGENT`, `SATUAN`, `KOMBINASI` - lihat parameter
`subfolder`, berbeda dari `tag`: TIDAK ikut disisipkan ke nama file, lihat catatan di Alur
2/3 di bawah); Alur 0, 4 & 5 (sampel, Shopee Pagi, J&T Resi Siang) TIDAK memakai penanda
maupun subfolder apa pun, tetap langsung di folder sesi.

Alur 2 - picklist urgent (fungsi rencana_urgent()/proses_urgent()): lintas SKU, 2 skenario -
channel Lazada, dan kurir GTL/SiCepat (lintas channel, TIDAK dibatasi channel Tokopedia -
lihat SKENARIO_URGENT), sebanyak mungkin per picklist (maks MAKS_PESANAN_PICKLIST, dipecah
kalau lebih). Tidak ada validasi SKU sejenis (multi-SKU per pesanan boleh). Pesanan yang jam
pesannya (WIB) di atas jam cutoff skenario (Lazada > jam 14.00, GTL/SiCepat > jam 15.00)
ditahan dulu, baru diproses otomatis setelah jam 16.00 (lihat JAM_CUTOFF_URGENT_LAZADA/
JAM_CUTOFF_URGENT_GTL_SICEPAT, JAM_LANJUT_URGENT & _saring_jam_urgent()). **Alur berdiri
sendiri** - dipanggil HANYA lewat main.py --urgent, TIDAK otomatis dipanggil oleh alur 1
(--label --jalankan). Kalau perlu urgent diproses lebih dulu, itu harus dijalankan manual
terpisah sebelum --label --jalankan (lihat README bagian "Picklist urgent"). Label KEDUA
skenario (Lazada maupun GTL/SiCepat) disimpan di subfolder `URGENT` di dalam folder sesi
(mis. `label-pengiriman/2026-10-02/1/URGENT/`) - lihat SUBFOLDER_URGENT, parameter
`subfolder` di lanjutkan_picklist().

Alur 3 - picklist sisa reguler (fungsi rencana_reguler()/proses_reguler()), dijalankan
SETELAH alur 1: lintas SKU, channel TikTok Shop ("Shop | Tokopedia") & Shopee, kurir J&T/SPX
(default, digabung) atau 1 kurir saja lewat parameter `kurir` (sama seperti alur 1), yang
BUKAN bagian SKU spesial (dikecualikan lewat resi_spesial_semua) - dipecah 2 picklist: 1 SKU
1 qty, dan kombinasi (qty > 1). Sama seperti alur 2: lintas SKU, maks MAKS_PESANAN_PICKLIST
per picklist. Label bagian "1 qty" disimpan di subfolder `SATUAN`, bagian "kombinasi" di
subfolder `KOMBINASI` (lihat SUBFOLDER_SATUAN/SUBFOLDER_KOMBINASI) - dengan --kurir disisipi
awalan JNT_/SPX_ sama seperti TAG_SPESIAL (mis. `JNT_SATUAN`/`SPX_KOMBINASI`).

Alur 4 - picklist Shopee Pagi (fungsi rencana_shopee_pagi()/proses_shopee_pagi()), dijalankan
MANUAL 1x sehari (mis. jam 13:00), BUKAN bagian alur otomatis main.py --label --jalankan:
lintas SKU, channel Shopee saja, pesanan yang jam pesannya (WIB) maksimal jam 12 siang hari
ini (JAM_CUTOFF_SHOPEE_PAGI) - digabung jadi 1 picklist, maks MAKS_PESANAN_PICKLIST.

Alur 5 - picklist J&T Resi Siang (fungsi rencana_jnt_siang()/proses_jnt_siang()), dijalankan
MANUAL 1x sehari (mis. jam 15:00), BUKAN bagian alur otomatis main.py --label --jalankan:
sama pola dengan alur 4, tapi channel TikTok Shop saja, kurir J&T saja, pesanan yang jam
pesannya (WIB) maksimal jam 15 siang hari ini (JAM_CUTOFF_JNT_SIANG) - digabung jadi 1
picklist, maks MAKS_PESANAN_PICKLIST. Aturan bisnis J&T: pesanan TikTok Shop wajib keluar
lewat J&T digabung 1 picklist paling lambat jam 15:00 (lihat docs/jadwal-proses.md).

Alur 2, 3, 4 & 5 berbagi _proses_channel_batch() (buat picklist -> langkah 3-6), beda cuma
sumber datanya (ambil_pesanan_channel(), ambil_pesanan_reguler()+pisah_reguler(),
ambil_pesanan_shopee_pagi(), atau ambil_pesanan_jnt_siang()) dan label yang dipakai untuk
nama file/kolom SKU di riwayat (nama skenario, bukan SKU asli).

Mode uji (rencana*(), default lewat main.py tanpa --jalankan) hanya membaca data (langkah 1)
dan menampilkan rencana. Langkah 2-6 hanya dijalankan lewat proses*()/lanjutkan() (main.py
--jalankan).
"""
from __future__ import annotations

import csv
import json
import logging
import re
import threading
import time
from urllib.parse import urlsplit, urlunsplit
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import jubelio
import peringatan_picklist
import peringatan_resi
import rekap_master_excel
from sku_spesial import AWALAN_KOMPONEN_DIABAIKAN, KURIR_DIIZINKAN, MIN_RESI

# Host server report (Telerik) Jubelio, urut dari yang dicoba PERTAMA. report.jubelio.com lebih
# stabil; report-prod.jubelio.com (host bawaan URL dari API Jubelio) sering bermasalah (410/504/
# dokumen macet), jadi dipakai sebagai cadangan. unduh_label() menjalankan SELURUH alur
# (halaman -> client -> dokumen -> unduh) di SATU host per percobaan, lalu berganti host di
# percobaan berikutnya.
HOST_REPORT = ("report.jubelio.com", "report-prod.jubelio.com")
HOST_REPORT_UTAMA = HOST_REPORT[0]
KURIR_FILTER = ["j&t", "spx"]           # nilai filter kurir di web Jubelio
# Pemisahan J&T/SPX saat proses (dipakai TIPE 2 & TIPE 3 - lihat proses-harian.bat/
# JADWAL-PROSES.md): nilai --kurir CLI ("jnt"/"spx") -> nilai filter kurir Jubelio.
# kurir=None (default, dipakai TIPE 1/TIPE 4) = J&T dan SPX digabung seperti semula.
#
# "spx-hemat"/"spx-standard" (mode EVENT, proses-event.bat - lihat docs/jadwal-proses.md): varian
# SPX dipisah sendiri-sendiri. Nilai filter `couriers[]` Jubelio TIDAK membedakan huruf besar/
# kecil dan memakai pencocokan sebagian teks, jadi harus selengkap "spx hemat" (bukan "hemat"
# saja - ikut menangkap "J&T Express Hemat"); sniff 2026-10-08 & uji langsung API.
#
# "spx-hemat-pagi" = SPX Hemat untuk Shopee Pagi mode event (pesanan jam pesan <= 12:00 saja -
# lihat KURIR_BERBATAS): filter kurirnya SAMA dengan "spx-hemat", tapi diberi kunci sendiri
# supaya tag/subfolder/label/nama file-nya TERPISAH dari SPX Hemat sisa hari (SPXHEMATPAGI_*).
KURIR_PILIHAN = {"jnt": "j&t", "spx": "spx", "spx-hemat": "spx hemat",
                 "spx-hemat-pagi": "spx hemat", "spx-standard": "spx standard"}
# Penanda di nama file label PDF DAN nama subfolder tempat labelnya disimpan
# (folder_label / tag), HANYA untuk picklist SKU spesial (Alur 1 - proses()/
# lanjutkan_picklist() dipanggil dari proses()); lanjutkan() (--lanjut) hanya memakainya kalau
# diberi --tag, yang sudah tercantum di Catatan TERHENTI (lihat perintah_lanjut()). Kalau
# --kurir jnt/spx dipakai di alur 1, tag disisipi awalan KURIR_LABEL_FILE (mis.
# "JNT_SPESIAL"/"SPX_SPESIAL") supaya nama file & subfolder J&T dan SPX tidak bercampur -
# lihat proses().
TAG_SPESIAL = "SPESIAL"

# Subfolder tempat label disimpan di dalam folder sesi (folder_label), untuk Alur 2
# (urgent) & Alur 3 (reguler) - BEDA dengan TAG_SPESIAL di atas: hanya memengaruhi lokasi
# file, nama file PDF tidak ikut disisipi penanda ini (lihat parameter `subfolder` di
# lanjutkan_picklist(), beda dari `tag`). Tujuannya supaya tim gudang bisa menyortir fisik
# print-out Lazada/GTL-SiCepat (urgent), 1 qty reguler (satuan), dan kombinasi/multi-qty
# reguler (kombinasi) tanpa harus baca nama file satu-satu.
SUBFOLDER_URGENT = "URGENT"            # Alur 2: Lazada & GTL-SiCepat (kedua skenario)
SUBFOLDER_SATUAN = "SATUAN"            # Alur 3 bagian "1qty" (1 SKU qty 1, bukan spesial)
SUBFOLDER_KOMBINASI = "KOMBINASI"      # Alur 3 bagian "kombinasi" (qty > 1 / multi-baris)
SUBFOLDER_SPX_PAGI = "SPX_PAGI"        # Shopee Pagi (SPX <= 12.00), nama file tetap SHOPEE-PAGI-*
SUBFOLDER_JNT_SIANG = "JNT_SIANG"      # J&T Resi Siang (TikTok Shop <= 15.00), nama file JNT-SIANG-*


def _filter_kurir(kurir: str | None, gabungan: list[str]) -> list[str]:
    return [KURIR_PILIHAN[kurir]] if kurir else gabungan
# SKU bundle (paket) yang boleh diproses sebagai SKU spesial: hanya yang namanya
# mengandung "PTAA" (mis. T01-PTAA-5). Bundle lain (PTAE, PTAD, BKAG, dst) TIDAK
# boleh jadi picklist spesial - baru diketahui bundle atau bukan lewat bundle_item_id
# saat items-to-pick (lihat _cek_item()), bukan dari nama SKU-nya sendiri.
SKU_BUNDLE_DIIZINKAN = "ptaa"
# Tipe pesanan yang diproses (sniff 29-09-2026). "kilat" (pengiriman kilat)
# sengaja dikeluarkan karena tipe itu tidak diproses lewat alur ini.
TIPE_PESANAN_FILTER = ["umum", "prioritas", "po", "dropshipper", "kirim_hari_ini",
                       "cod", "multi_location", "multi_package"]
PESAN_SUDAH_DIPAKAI = "sudah dipakai di transaksi lain"

# Picklist urgent per channel/kurir (lintas SKU) - alur berdiri sendiri, lihat catatan "Alur 2"
# di docstring atas (TIDAK otomatis dipanggil sebelum picklist SKU spesial).
CHANNEL_ID_LAZADA = 4
# Kurir GTL & SiCepat = urgent apa pun channel-nya (TIDAK dibatasi channel Tokopedia): sniff
# 29-09-2026 channel_id dari core-api/marketplace/all-channel, 128 = TOKOPEDIA asli, 131076 =
# "Shop | Tokopedia" (logo TikTok, BUKAN Tokopedia asli, lihat CHANNEL_ID_TIKTOK_SHOP) - kedua
# channel itu sama-sama urgent kalau kurirnya GTL/SiCepat, jadi filter channel sengaja
# DILEPAS di sini, cukup filter kurir.
KURIR_FILTER_URGENT_GTL_SICEPAT = ["gtl", "sicepat"]
MAKS_PESANAN_PICKLIST = 200             # gabung sebanyak mungkin, pecah kalau lebih dari ini
# Jam tunda per skenario urgent (WIB, HARI INI): pesanan yang jam pesannya di atas jam ini
# belum "mendesak" - sengaja DITAHAN dulu (tidak masuk picklist) sampai JAM_LANJUT_URGENT,
# bukan dibuang. Kebijakan tim: Lazada ditahan di atas jam 14.00, GTL/SiCepat ditahan di atas
# jam 15.00 - keduanya baru dilanjutkan otomatis setelah jam 16.00 (lihat JAM_LANJUT_URGENT &
# _saring_jam_urgent()). Pesanan tanpa transaction_date TIDAK ditahan (lebih aman langsung
# diproses daripada tidak pernah tercek lagi).
JAM_CUTOFF_URGENT_LAZADA = 14
JAM_CUTOFF_URGENT_GTL_SICEPAT = 15
# Setelah jam ini (WIB), jam tunda di atas diabaikan sepenuhnya - proses_urgent()/
# rencana_urgent() berikutnya memproses SEMUA pesanan termasuk yang tadinya ditahan (selaras
# dengan jadwal tim: proses-harian.bat TIPE 1 jam 16.00, lihat docs/jadwal-proses.md).
JAM_LANJUT_URGENT = 16
# GTL-SiCepat (lintas channel, volumenya besar) dipecah per LANTAI rak gudang (sama pola
# dengan bagian "kombinasi" picklist sisa reguler, lihat _kelompok_kombinasi_per_lantai() -
# live API ready-to-process dibatasi channel_ids/couriers skenario ini, bukan
# CHANNEL_IDS_REGULER/KURIR_FILTER_REGULER). Lazada (volume kecil) TETAP 1 picklist gabungan
# seperti semula - elemen ke-5 tuple ini (`per_lantai`) yang membedakan.
SKENARIO_URGENT = [
    ("Lazada", [CHANNEL_ID_LAZADA], None, JAM_CUTOFF_URGENT_LAZADA, False),
    ("GTL-SiCepat", None, KURIR_FILTER_URGENT_GTL_SICEPAT, JAM_CUTOFF_URGENT_GTL_SICEPAT, True),
]

# Picklist "sisa reguler" (lintas SKU, dibuat SETELAH picklist SKU spesial selesai): pesanan
# channel TikTok Shop & Shopee, kurir J&T/SPX, yang BUKAN bagian dari SKU spesial hari itu.
# channel_id 131076 = "Shop | Tokopedia" di Jubelio, itu nama lain TikTok Shop (Tokopedia asli
# = channel_id 128, TIDAK dipakai di sini) -> BUKAN Tokopedia asli.
CHANNEL_ID_TIKTOK_SHOP = 131076
CHANNEL_ID_SHOPEE = 64
CHANNEL_IDS_REGULER = [CHANNEL_ID_TIKTOK_SHOP, CHANNEL_ID_SHOPEE]
KURIR_FILTER_REGULER = ["j&t", "spx"]
LABEL_REGULER_1QTY = "1QTY-REGULER"     # 1 SKU, qty 1, tidak spesial
LABEL_REGULER_KOMBINASI = "KOMBINASI-REGULER"   # sisanya (multi-baris/qty>1), tidak spesial

# Pecah lagi bagian "1qty reguler" per grup rak gudang (lihat docs/superpowers/specs/
# 2026-10-02-pecah-1qty-per-rak-design.md) - grup 1A sengaja tidak ada (tidak dipakai di
# gudang ini, dikonfirmasi lewat sniff 02-10-2026). Urutan di sini = urutan pembuatan
# picklist (bukan alfabetis) - diminta tim operasional supaya picker jalan runtut.
GRUP_RAK = ["2A", "3A", "1B", "2B", "3B"]
LABEL_RAK_LAINNYA = "LAINNYA"            # pesanan 1qty yang rak-nya di luar GRUP_RAK
MAKS_KOMBINASI_PER_PANGGILAN = 40        # batasi panjang query combination[] per request

# Grup rak untuk bagian "kombinasi" reguler: lebih longgar dari GRUP_RAK (per LANTAI, bukan
# per grup rak) karena pesanan kombinasi (qty>1/multi-SKU) lazim tersebar di >1 rak sekaligus -
# urutan sama dengan WARNA_LANTAI di sku_spesial.py.
LANTAI_RAK = ["1", "2", "3"]

# Picklist "Shopee Pagi" (lintas SKU): dijalankan MANUAL, 1x sehari jam 13:00 - bukan bagian
# alur otomatis --label --jalankan. Semua pesanan channel Shopee yang jam pesannya (WIB)
# maksimal jam 12:00 HARI INI, digabung jadi 1 picklist (dipecah kalau > MAKS_PESANAN_PICKLIST).
JAM_CUTOFF_SHOPEE_PAGI = 12
LABEL_SHOPEE_PAGI = "SHOPEE-PAGI"
# Hanya kurir SPX yang ikut (sesuai namanya "SPX Resi Pagi"): pesanan Shopee kurir lain tidak
# ikut picklist ini - mereka diproses alur reguler biasa (KURIR_FILTER_REGULER).
KURIR_FILTER_SHOPEE_PAGI = ["spx"]
WIB = ZoneInfo("Asia/Jakarta")

# Picklist "J&T Resi Siang" (lintas SKU): dijalankan MANUAL, 1x sehari jam 15:00 - bukan
# bagian alur otomatis --label --jalankan. Aturan bisnis J&T: pesanan channel TikTok Shop
# yang wajib keluar hari itu lewat kurir J&T harus digabung jadi 1 picklist paling lambat
# jam 15:00 (supaya tidak tercampur pesanan yang masuk setelah jam 15:00) - sejajar dengan
# Shopee Pagi (SPX ≤ 12:00) tapi beda channel (TikTok Shop, bukan Shopee), beda kurir
# (difilter J&T saja - SPX di channel TikTok Shop TIDAK ikut aturan ini) dan beda jam
# cutoff. Lihat docs/jadwal-proses.md bagian "J&T Resi Siang".
JAM_CUTOFF_JNT_SIANG = 15
LABEL_JNT_SIANG = "JNT-SIANG"

MAKS_COBA_PICKLIST = 3
# Langkah 3-6 (tunggu picking selesai, minta resi, unduh PDF - lihat lanjutkan_picklist())
# paling banyak menghabiskan waktu TUNGGU (bukan HTTP), jadi proses() menjalankannya BERSAMAAN
# antar SKU lewat ThreadPoolExecutor - picklist (langkah 1-2) TETAP dibuat berurutan dulu
# (lihat proses()) karena deteksi picklist terlompat (peringatan_picklist.ambil_nomor_hilang())
# butuh urutan pasti nomor picklist yang baru dibuat.
MAKS_WORKER_PARALEL = 5
TUNGGU_PICKING_S = 90                   # batas tunggu status FINISH_PICK
TUNGGU_FINISH_PICK_S = 90               # batas tunggu pesanan muncul di Picking > Selesai
TUNGGU_RESI_S = 180                     # batas tunggu semua nomor resi keluar
JEDA_RESI_S = 3.5                       # jeda polling resi (sama dengan web)
# Dokumen label NORMALNYA jadi dalam hitungan detik: 613 label 02-06/10/2026 (selisih jam di
# nama file vs waktu file ditulis = seluruh unduh_label()) median 3-5 detik, PALING LAMA 25,5
# detik - termasuk label 198 halaman (7,2 detik), jadi ukuran label bukan penyebab lambat.
# Dokumen yang belum jadi setelah TUNGGU_PDF_S praktis MACET di node report-prod-nya (insiden
# 2026-10-06: dulu ditunggu 180 detik lalu HTML5 180 detik lagi di client/node yang SAMA =
# 6 menit sia-sia per picklist, menahan seluruh langkah urgent/reguler yang berurutan) ->
# unduh_label() mengulang dari awal dengan client baru, sama seperti 410 Expired.
TUNGGU_PDF_S = 60
TUNGGU_INFO_DOKUMEN_S = 30              # batas 1 request cek status dokumen (biasanya instan)
TUNGGU_UNDUH_PDF_S = 30                 # batas tunggu request unduh dokumen PDF itu sendiri
TUNGGU_LABEL_S = 240                    # batas total coba ulang label (410 Expired/dokumen macet)
JEDA_COBA_LABEL_S = 5
# Koneksi putus di tengah request (mis. RemoteDisconnected) - ulangi request YANG SAMA
# beberapa kali sebelum menyerah, supaya 1 kedipan koneksi tidak menggagalkan seluruh
# picklist (operator harus --lanjut manual). Dipasang di Klien._kirim(), dipakai semua
# request keluar (get/post/report_get/report_post) - jadi retry-nya tepat di titik
# request yang gagal, bukan mengulang dari awal langkah 3-6.
MAKS_COBA_KONEKSI = 3
JEDA_COBA_KONEKSI_S = 5
# HTTP 502/503/504 dari report-prod (mis. "Halaman label gagal dibuka (HTTP 504)" saat server
# report Jubelio kelebihan beban, insiden 2026-10-06) - diulang dengan jatah MAKS_COBA_KONEKSI
# yang sama. HANYA untuk report_get()/report_post(): request report-prod cuma membuat objek
# render sementara (client/instance/dokumen) jadi aman diulang, BEDA dengan POST ke API utama
# (mis. buat picklist) yang bisa saja sudah diproses walau gateway membalas 504 -> picklist ganda.
KODE_GATEWAY_SEMENTARA = (502, 503, 504)
# HTTP 429 (Too Many Requests) dari Jubelio - lihat jubelio.MAKS_COBA_429/_kirim_dengan_retry429
# untuk latar belakang (kejadian 03-10-2026: 26+ picklist SKU spesial berturut-turut bikin
# Jubelio membatasi laju). Dipasang di sini juga karena Klien dipakai untuk picklist/resi/label,
# bukan cuma ambil_nilai_pesanan.
MAKS_COBA_429 = jubelio.MAKS_COBA_429
JEDA_COBA_429_S = jubelio.JEDA_COBA_429_S

KOLOM_RIWAYAT = ["Waktu", "SKU", "No Picklist", "Total Pesanan", "Resi Keluar",
                 "File Label", "Catatan", "Durasi"]

# Detail resi SKU spesial (1 file per sesi, di folder_label - lihat catat_detail_spesial()):
# dipakai HANYA utk picklist ber-tag TAG_SPESIAL (Alur 1), 1 baris per pesanan yang resinya
# BENAR-BENAR keluar & labelnya berhasil diunduh (bukan yang batal/belum dapat resi - itu
# sudah ditangani peringatan_resi.py). Kalau dari 1 picklist SKU spesial jumlah baris itu
# masih >= MIN_RESI, SKU-nya tetap sah spesial -> NAMA_DETAIL_SPESIAL. Kalau < MIN_RESI
# (mis. sebagian resi di picklist itu ternyata batal/request-cancel saat proses, jadi yang
# benar-benar tercetak cuma 1-2) -> SKU itu gugur jadi tidak spesial lagi, tapi baris yang
# sudah tercetak labelnya tetap dicatat, ke file BEDA (NAMA_DETAIL_BUKAN_SPESIAL) supaya bisa
# dipisah saat memilah resi fisik.
NAMA_DETAIL_SPESIAL = "detail-resi-spesial.xlsx"
NAMA_DETAIL_BUKAN_SPESIAL = "detail-resi-bukan-spesial.xlsx"
KOLOM_DETAIL_SPESIAL = ["No Picklist", "SKU", "No Pesanan", "No Resi"]


def nama_detail_per_kurir(nama_dasar: str, tag: str | None) -> str:
    """Nama file detail resi untuk `tag` picklist: kalau --kurir jnt/spx dipakai (tag diawali
    JNT_/SPX_, lihat _tag_spesial()) disisipi akhiran kurir sebelum ekstensi, mis.
    detail-resi-spesial.xlsx -> detail-resi-spesial-jnt.xlsx, supaya resi J&T dan SPX
    (TIPE 2 & 3, kurir dipisah) tidak bercampur di 1 file. Tanpa kurir (TIPE 1 & 4, digabung)
    nama dasar apa adanya."""
    for kode in KURIR_KODE_FILE_SEMUA.values():
        if tag and tag.startswith(f"{kode}_"):
            dasar, ekstensi = nama_dasar.rsplit(".", 1)
            return f"{dasar}-{kode.lower()}.{ekstensi}"
    return nama_dasar

log = logging.getLogger("sku-spesial")


class ProsesError(RuntimeError):
    pass


class Lewati(Exception):
    """SKU tidak diproses (bukan error sistem), mis. pesanan tersisa < MIN_RESI."""


class DokumenMacet(ProsesError):
    """Dokumen label report-prod belum jadi setelah TUNGGU_PDF_S - lihat unduh_label()."""


# ============================================================== koneksi
class Klien:
    def __init__(self, token: str, sesi=None, tidur=time.sleep):
        self.token = token
        self.sesi = sesi or requests.Session()
        self.tidur = tidur
        self.cookie = {"JB_OMNI_ACCESS_TOKEN": token}
        # Load balancer report-prod memilih node dari token di Referer; client Telerik
        # hanya ada di memori node itu, jadi Referer harus URL halaman label (seperti web).
        # HANYA dipakai sebagai default awal (1 Klien dipakai bersama banyak worker paralel -
        # lihat proses()): unduh_label() TIDAK BOLEH menimpa atribut ini lagi (race condition
        # antar-thread - 1 SKU bisa memakai Referer SKU lain yang sedang jalan bersamaan,
        # menyasar node report-prod yang salah -> _tunggu_dokumen() timeout 180 detik, insiden
        # 2026-10-06), tapi harus meneruskan `referer` secara eksplisit ke tiap report_get()/
        # report_post() di sepanjang alurnya sendiri (lihat _buat_instance_report(),
        # _tunggu_dokumen(), unduh_label()).
        self.halaman_report = f"https://{HOST_REPORT_UTAMA}/"

    @staticmethod
    def _json(r, apa: str):
        if r.status_code >= 400:
            raise ProsesError(f"{apa} gagal (HTTP {r.status_code}): {jubelio._pesan(r)}")
        return r.json()

    def _kirim(self, fn, *a, ulang_gateway: bool = False, **kw):
        """Panggil `fn` (sesi.get/sesi.post), ulangi kalau koneksi putus di tengah jalan
        (mis. ConnectionError/RemoteDisconnected, Timeout) - lihat MAKS_COBA_KONEKSI - atau
        kalau Jubelio membalas HTTP 429 (Too Many Requests) - lihat MAKS_COBA_429.
        `ulang_gateway`: ulangi juga HTTP 502/503/504 - lihat KODE_GATEWAY_SEMENTARA."""
        for coba in range(1, MAKS_COBA_KONEKSI + 1):
            try:
                r = fn(*a, **kw)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if coba == MAKS_COBA_KONEKSI:
                    raise
                log.warning("  Koneksi putus (percobaan %d/%d): %s -> ulangi %d detik lagi",
                           coba, MAKS_COBA_KONEKSI, e, JEDA_COBA_KONEKSI_S)
                self.tidur(JEDA_COBA_KONEKSI_S)
                continue
            if r.status_code == 429:
                return self._kirim_ulang_429(fn, a, kw, r)
            if ulang_gateway and r.status_code in KODE_GATEWAY_SEMENTARA and coba < MAKS_COBA_KONEKSI:
                log.warning("  Server report membalas HTTP %d (percobaan %d/%d) -> ulangi %d detik "
                            "lagi", r.status_code, coba, MAKS_COBA_KONEKSI, JEDA_COBA_KONEKSI_S)
                self.tidur(JEDA_COBA_KONEKSI_S)
                continue
            return r

    def _kirim_ulang_429(self, fn, a, kw, r):
        for coba in range(2, MAKS_COBA_429 + 1):
            jeda = jubelio._jeda_retry_after(r, JEDA_COBA_429_S * (coba - 1))
            log.warning("  HTTP 429 Too Many Requests (percobaan %d/%d) -> tunggu %s lagi",
                       coba - 1, MAKS_COBA_429, durasi(jeda))
            self.tidur(jeda)
            r = fn(*a, **kw)
            if r.status_code != 429:
                return r
        return r

    def get(self, path: str, params=None):
        r = self._kirim(self.sesi.get, f"{jubelio.API}/{path}", params=params,
                        headers=jubelio._header(self.token), timeout=60)
        return self._json(r, f"GET {path}")

    def post_mentah(self, path: str, body):
        return self._kirim(self.sesi.post, f"{jubelio.API}/{path}", json=body,
                           headers=jubelio._header(self.token), timeout=120)

    def post(self, path: str, body):
        return self._json(self.post_mentah(path, body), f"POST {path}")

    # report-prod (Telerik) memakai cookie, bukan header authorization
    def report_get(self, url: str, params=None, referer: str | None = None, timeout=180):
        return self._kirim(self.sesi.get, url, params=params, cookies=self.cookie, timeout=timeout,
                           ulang_gateway=True,
                           headers={"User-Agent": jubelio.USER_AGENT,
                                    "Referer": referer or self.halaman_report})

    def report_post(self, path: str, body, referer: str | None = None):
        referer = referer or self.halaman_report
        r = self._kirim(self.sesi.post, f"{_api_report(referer)}/{path}", json=body,
                        cookies=self.cookie, timeout=120, ulang_gateway=True,
                        headers={"User-Agent": jubelio.USER_AGENT,
                                 "Referer": referer,
                                 "Origin": f"https://{urlsplit(referer).netloc}",
                                 "X-Requested-With": "XMLHttpRequest"})
        return self._json(r, f"report {path.rsplit('/', 1)[-1]}")


def _ganti_host(url: str, host: str) -> str:
    u = urlsplit(url)
    return urlunsplit((u.scheme, host, u.path, u.query, u.fragment))


def _api_report(referer: str) -> str:
    """Basis API report di host yang SAMA dengan `referer` (URL halaman label)."""
    host = urlsplit(referer).netloc
    return f"https://{host if host in HOST_REPORT else HOST_REPORT_UTAMA}/api/reports"


def _angka(v) -> float:
    return float(v) if v not in (None, "") else 0.0


def _bulat(v):
    f = _angka(v)
    return int(f) if f.is_integer() else f


def _ids_param(ids) -> dict:
    return {f"ids[{i}]": v for i, v in enumerate(ids)}


def durasi(detik: float) -> str:
    menit, dtk = divmod(round(detik), 60)
    return f"{menit} menit {dtk} detik" if menit else f"{dtk} detik"


# ============================================================== 1. filter
def batas_jam_hari_ini(jam: int, sekarang: datetime | None = None) -> datetime:
    """Jam `jam`:00:00 WIB HARI INI (dari `sekarang`, default waktu sungguhan) - batas jam pesan
    untuk picklist ber-cutoff (Shopee Pagi 12:00, J&T Siang 15:00, dan varian mode event)."""
    return (sekarang or datetime.now(WIB)).replace(hour=jam, minute=0, second=0, microsecond=0)


# Kurir yang otomatis dibatasi jam pesan (nilai = jam cutoff WIB hari ini): dipakai main.py supaya
# `--kurir spx-hemat-pagi` selalu berarti "hanya pesanan s.d. jam 12:00" tanpa flag terpisah.
KURIR_BERBATAS = {"spx-hemat-pagi": JAM_CUTOFF_SHOPEE_PAGI}


def batas_untuk_kurir(kurir: str | None, sekarang: datetime | None = None) -> datetime | None:
    """Batas jam pesan untuk `kurir` (lihat KURIR_BERBATAS), None kalau kurir itu tidak dibatasi."""
    jam = KURIR_BERBATAS.get(kurir) if kurir else None
    return batas_jam_hari_ini(jam, sekarang) if jam is not None else None


def saring_sampai_batas(pesanan: list[dict], batas: datetime | None) -> list[dict]:
    """Pesanan yang jam pesannya (WIB) maksimal `batas` (pas di batas ikut). `batas` None =
    tidak menyaring sama sekali. Pesanan tanpa transaction_date dibuang - sama dengan aturan
    ambil_pesanan_shopee_pagi()/ambil_pesanan_jnt_siang()."""
    if batas is None:
        return pesanan
    hasil = []
    for o in pesanan:
        ts = o.get("transaction_date")
        if not ts:
            continue
        waktu = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(WIB)
        if waktu <= batas:
            hasil.append(o)
    return hasil


def cari_pesanan(k: Klien, sku: str, kurir: str | None = None,
                 batas: datetime | None = None) -> list[dict]:
    """`kurir`: None (default) = J&T + SPX digabung, atau "jnt"/"spx" untuk 1 kurir saja
    (lihat KURIR_PILIHAN - dipakai TIPE 2 & TIPE 3; "spx-hemat"/"spx-standard" mode event).
    `batas`: kalau diisi, hanya pesanan dengan jam pesan <= batas (lihat saring_sampai_batas();
    dipakai Shopee Pagi mode event)."""
    filter_kurir = _filter_kurir(kurir, KURIR_FILTER)
    hasil, page = [], 1
    while True:
        params = {"q": sku, "page": page, "page_size": 200, "is_total_qty": 0,
                  "sku_filter": "true", "sort_by": "transaction_date", "sort_direction": "DESC"}
        params.update({f"couriers[{i}]": c for i, c in enumerate(filter_kurir)})
        params.update({f"order_type[{i}]": t for i, t in enumerate(TIPE_PESANAN_FILTER)})
        j = k.get("wms/sales/v2/orders/ready-to-process/", params)
        data = j.get("data") or []
        hasil += data
        if not data or len(hasil) >= int(j.get("totalCount") or 0):
            return saring_sampai_batas(hasil, batas)
        page += 1


def saring(pesanan: list[dict], resi_spesial: set[str],
          kurir: str | None = None) -> tuple[list[dict], list[tuple[str, str]]]:
    """Pesanan yang boleh diproses + (No pesanan, alasan) yang dibuang. `kurir`: lihat
    cari_pesanan()."""
    awalan = ((KURIR_PILIHAN[kurir].upper(),) if kurir
             else tuple(x.upper() for x in KURIR_DIIZINKAN))
    pakai, buang = [], []
    for o in pesanan:
        no = o["salesorder_no"]
        if no not in resi_spesial:
            buang.append((no, "tidak termasuk resi spesial di Excel"))
        elif _angka(o.get("grand_total")) == 0:
            buang.append((no, "nilai pesanan 0 (kreator)"))
        elif _angka(o.get("total_qty")) != 1:
            buang.append((no, f"total qty {o.get('total_qty')}"))
        elif not str(o.get("shipper", "")).upper().startswith(awalan):
            buang.append((no, f"kurir {o.get('shipper')}"))
        else:
            pakai.append(o)
    return pakai, buang


# ============================================== 1a. picklist sampel (TikTok Shop nilai 0)
def _ambil_pesanan_channel_mentah(k: Klien, channel_ids: list[int] | None = None,
                                  couriers: list[str] | None = None) -> list[dict]:
    """Pengambilan mentah dipakai ambil_pesanan_channel() & ambil_pesanan_sampel() - BELUM
    dikeluarkan pesanan sampelnya (lihat masing-masing fungsi itu). Semua pesanan Siap Proses,
    lintas SKU, diurutkan tanggal transaksi TERLAMA dulu (ASC) supaya resi yang lebih lama
    selalu masuk picklist pertama kalau bagi_batch() memecahnya jadi beberapa picklist.
    `channel_ids` opsional: None/kosong = semua channel (dipakai skenario yang urgent-nya
    ditentukan kurir, bukan channel - mis. GTL/SiCepat, yang urgent baik dari Tokopedia asli
    maupun "Shop | Tokopedia"/TikTok). Opsional filter kurir. Kurir SPX dan channel Shopee
    selalu ikut menyertakan pesanan tipe "pengiriman kilat" kalau tidak difilter -> tipe itu
    tidak diproses lewat alur picklist ini (lihat TIPE_PESANAN_FILTER), jadi filter tipe
    pesanan otomatis ditambahkan kalau channel-nya Shopee dan/atau kurirnya SPX."""
    pakai_filter_tipe = ((channel_ids and CHANNEL_ID_SHOPEE in channel_ids)
                         or any(c.lower().startswith("spx") for c in couriers or []))
    hasil, page = [], 1
    while True:
        # ASC (terlama dulu): kalau totalnya > MAKS_PESANAN_PICKLIST dan dipecah beberapa
        # picklist (bagi_batch()), resi yang lebih lama (mis. pesanan sebelum jam 12 saat
        # program baru jalan jam 13) harus selalu masuk picklist PERTAMA, bukan tertahan di
        # batch belakangan cuma karena kebetulan pesanannya lebih lama dari yang lain.
        params = {"q": "", "page": page, "page_size": 200, "sku_filter": "false",
                  "sort_by": "transaction_date", "sort_direction": "ASC"}
        if channel_ids:
            params.update({f"channel_ids[{i}]": c for i, c in enumerate(channel_ids)})
        if couriers:
            params.update({f"couriers[{i}]": c for i, c in enumerate(couriers)})
        if pakai_filter_tipe:
            params.update({f"order_type[{i}]": t for i, t in enumerate(TIPE_PESANAN_FILTER)})
        j = k.get("wms/sales/v2/orders/ready-to-process/", params)
        data = j.get("data") or []
        hasil += data
        if not data or len(hasil) >= int(j.get("totalCount") or 0):
            break
        page += 1
    if channel_ids:
        # jaga-jaga: saring lagi di sisi kita terhadap channel_id sungguhan, jangan andalkan
        # filter API saja (lihat catatan "Shop | Tokopedia" di atas)
        izin = set(channel_ids)
        hasil = [o for o in hasil if o.get("source") in izin]
    return hasil


def _is_sampel(o: dict) -> bool:
    """channel TikTok Shop ("Shop | Tokopedia", source 131076) kosong/0 nilainya = pesanan
    sampel/kreator (lihat catatan TT-586350230929114342-67824, 01-10-2026) - khusus channel
    ini saja, BUKAN Shopee/Lazada/GTL-SiCepat yang nilai kecilnya tetap pesanan sungguhan
    (sniff 01-10-2026: Shopee terendah Rp 1.058, tidak pernah 0/kosong)."""
    return o.get("source") == CHANNEL_ID_TIKTOK_SHOP and _angka(o.get("grand_total")) == 0


LABEL_SAMPEL = "SAMPEL-TIKTOK"


def ambil_pesanan_sampel(k: Klien) -> list[dict]:
    """Semua pesanan Siap Proses channel TikTok Shop nilai 0/kosong (lihat _is_sampel()) -
    dipakai picklist sampel (Alur 0), SELALU dicek paling pertama di tiap TIPE
    proses-harian.bat, sebelum urgent."""
    return [o for o in _ambil_pesanan_channel_mentah(k, [CHANNEL_ID_TIKTOK_SHOP]) if _is_sampel(o)]


def rencana_sampel(k: Klien) -> None:
    """Mode uji picklist sampel: hanya membaca data, tidak mengubah apa pun di Jubelio."""
    pesanan = ambil_pesanan_sampel(k)
    batch = bagi_batch([o["salesorder_id"] for o in pesanan])
    log.info("[UJI] Sampel TikTok Shop (nilai 0/kosong) pesanan siap proses %3d -> "
             "%d picklist (maks %d/picklist)", len(pesanan), len(batch), MAKS_PESANAN_PICKLIST)


def proses_sampel(k: Klien, file_riwayat: Path, folder_label: Path) -> list[dict]:
    """Picklist sampel: semua pesanan TikTok Shop nilai 0/kosong, digabung jadi 1 picklist
    (dipecah kalau > MAKS_PESANAN_PICKLIST). Dijalankan PALING PERTAMA di tiap TIPE
    proses-harian.bat (sebelum urgent) lewat main.py --sampel; dilewati otomatis kalau tidak
    ada pesanan sampel saat itu (_proses_channel_batch mengembalikan [] tanpa bikin picklist)."""
    pesanan = ambil_pesanan_sampel(k)
    return _proses_channel_batch(k, "Sampel TikTok Shop", LABEL_SAMPEL, pesanan,
                                 file_riwayat, folder_label)


# ============================================== 1b. picklist urgent per channel
def ambil_pesanan_channel(k: Klien, channel_ids: list[int] | None = None,
                          couriers: list[str] | None = None) -> list[dict]:
    """Seperti _ambil_pesanan_channel_mentah(), tapi pesanan sampel (lihat _is_sampel(), Alur 0)
    dikeluarkan dari hasilnya supaya tidak dobel diproses - picklist sampel punya alurnya
    sendiri (ambil_pesanan_sampel()/proses_sampel()), dijalankan terpisah sebelum ini."""
    hasil = _ambil_pesanan_channel_mentah(k, channel_ids, couriers)
    sampel = [o["salesorder_no"] for o in hasil if _is_sampel(o)]
    if sampel:
        log.warning("  %d pesanan TikTok Shop nilai 0 (sampel/kreator) dikeluarkan dari sini "
                    "(punya picklist sendiri lewat --sampel): %s", len(sampel), ", ".join(sampel))
    return [o for o in hasil if not _is_sampel(o)]


def bagi_batch(ids: list[int], maks: int = MAKS_PESANAN_PICKLIST) -> list[list[int]]:
    """Pecah jadi beberapa batch maks `maks` pesanan, memaksimalkan tiap batch (isi penuh
    dulu baru lanjut ke batch berikutnya), bukan dibagi rata."""
    return [ids[i:i + maks] for i in range(0, len(ids), maks)] if ids else []


def buat_picklist_channel(k: Klien, ids: list[int]) -> tuple[int, str, list[int]]:
    """Buat 1 picklist dari daftar salesorder_id apa adanya (lintas SKU/lokasi), dipakai untuk
    picklist urgent per channel. Beda dengan buat_picklist(): tidak ada saring per-SKU/resi
    spesial (idnya sudah difilter lewat ambil_pesanan_channel)."""
    for coba in range(1, MAKS_COBA_PICKLIST + 1):
        items = k.post("sales/picklists/items-to-pick/", {"ids": ids})
        items, pesan_kosong = _pisahkan_stok_kosong(k, items)
        for p in pesan_kosong:
            log.warning("  Stok kosong (ditandai di Jubelio, dikeluarkan dari picklist): %s", p)
        ids_pakai = sorted({x["salesorder_id"] for x in items})
        if not ids_pakai:
            raise Lewati("semua pesanan kena stok kosong, tidak ada yang bisa diproses")

        body = {
            "is_completed": False, "is_warehouse": True,
            "items": [{"salesorder_detail_id": x["salesorder_detail_id"], "item_id": x["item_id"],
                       "location_id": x["location_id"], "qty_ordered": _bulat(x["qty_ordered"]),
                       "salesorder_id": x["salesorder_id"], "bundle_item_id": x["bundle_item_id"],
                       "package_detail_id": x.get("package_detail_id") or 0,
                       "package_id": x.get("package_id") or 0} for x in items],
            "merge_location": False, "picker_id": None, "picklist_id": 0,
            "picklist_no": "[auto]", "salesorderIds": ids_pakai,
        }
        r = k.post_mentah("wms/sales/picklists/", body)
        if r.status_code >= 400 and PESAN_SUDAH_DIPAKAI in r.text:
            log.warning("  Picklist ditolak (percobaan %d): %s -> ulangi",
                        coba, jubelio._pesan(r)[:250])
            k.tidur(2)
            continue
        data = Klien._json(r, "Buat picklist")["data"]
        picks = data.get("picks") or []
        if len(picks) != 1:
            raise ProsesError(f"Terbentuk {len(picks)} picklist, diharapkan 1: {data}")
        peringatan_picklist.periksa_nomor(picks[0]["picklist_no"])
        invalid = set(data.get("invalidSO") or [])
        if invalid:
            log.warning("  %d pesanan ditolak Jubelio (invalidSO): %s", len(invalid), sorted(invalid))
        return picks[0]["picklist_id"], picks[0]["picklist_no"], sorted(set(ids_pakai) - invalid)
    raise ProsesError(f"Picklist tetap ditolak setelah {MAKS_COBA_PICKLIST} percobaan")


def _saring_jam_urgent(pesanan: list[dict], jam_cutoff: int,
                       sekarang: datetime | None = None) -> tuple[list[dict], int]:
    """Terapkan jam tunda urgent (lihat JAM_CUTOFF_URGENT_LAZADA/JAM_CUTOFF_URGENT_GTL_SICEPAT
    & JAM_LANJUT_URGENT di atas): sebelum jam JAM_LANJUT_URGENT, pesanan yang jam pesannya
    (WIB) di atas `jam_cutoff` HARI INI ditahan (belum diproses), sisanya diproses seperti
    biasa. Setelah jam JAM_LANJUT_URGENT, semua pesanan diproses tanpa batas jam ini.
    `sekarang`: dipakai tes, default waktu sungguhan (WIB) saat dipanggil. Return (pesanan
    yang boleh diproses sekarang, jumlah yang ditahan)."""
    now = sekarang or datetime.now(WIB)
    if now.hour >= JAM_LANJUT_URGENT:
        return pesanan, 0
    batas = now.replace(hour=jam_cutoff, minute=0, second=0, microsecond=0)
    pakai, ditahan = [], 0
    for o in pesanan:
        ts = o.get("transaction_date")
        if ts and datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(WIB) > batas:
            ditahan += 1
            continue
        pakai.append(o)
    return pakai, ditahan


def rencana_urgent(k: Klien, skenario: list[tuple] | None = None,
                   sekarang: datetime | None = None) -> None:
    """Mode uji picklist urgent: hanya membaca data, tidak mengubah apa pun di Jubelio.
    Skenario `per_lantai` (GTL-SiCepat) ditampilkan dipecah per LANTAI_RAK + LABEL_RAK_LAINNYA
    (lihat _kelompok_kombinasi_per_lantai())."""
    for nama, channel_ids, couriers, jam_cutoff, per_lantai in skenario or SKENARIO_URGENT:
        mentah = ambil_pesanan_channel(k, channel_ids, couriers)
        pesanan, ditahan = _saring_jam_urgent(mentah, jam_cutoff, sekarang)
        tunda = (f" (+{ditahan} ditahan, jam pesan di atas {jam_cutoff:02d}.00 WIB, lanjut "
                f"otomatis setelah jam {JAM_LANJUT_URGENT:02d}.00)" if ditahan else "")
        if not per_lantai:
            batch = bagi_batch([o["salesorder_id"] for o in pesanan])
            log.info("[UJI] Urgent %-10s pesanan siap proses %3d -> %d picklist (maks %d/picklist)%s",
                     nama, len(pesanan), len(batch), MAKS_PESANAN_PICKLIST, tunda)
            continue
        log.info("[UJI] Urgent %-10s pesanan siap proses %3d, dipecah per lantai%s",
                 nama, len(pesanan), tunda)
        per_lt = _kelompok_kombinasi_per_lantai(k, pesanan, channel_ids=channel_ids,
                                                couriers=couriers)
        for lt, sub in per_lt.items():
            batch = bagi_batch([o["salesorder_id"] for o in sub])
            log.info("  %-8s pesanan %3d -> %d picklist (maks %d/picklist)",
                     _label_lantai(lt), len(sub), len(batch), MAKS_PESANAN_PICKLIST)


def _proses_channel_batch(k: Klien, nama: str, label: str, pesanan: list[dict],
                          file_riwayat: Path, folder_label: Path,
                          label_file: str | None = None,
                          subfolder: str | None = None) -> list[dict]:
    """Pecah `pesanan` jadi beberapa batch (maks MAKS_PESANAN_PICKLIST), buat 1 picklist per
    batch sampai label PDF (buat picklist -> selesaikan picking -> minta resi -> unduh label).
    `label` dipakai lanjutkan_picklist() cuma sebagai penanda (bukan SKU asli), jadi nama file
    label & kolom SKU di riwayat otomatis jadi mis. PICK-000xxxxxx_LAZADA_<tanggal>_<jam>.pdf.
    `label_file`: varian `label` yang aman dipakai di nama file (mis. tanpa "&"); default sama
    dengan `label`. `subfolder`: lihat parameter `subfolder` di lanjutkan_picklist() (mis.
    SUBFOLDER_URGENT/SUBFOLDER_SATUAN/SUBFOLDER_KOMBINASI) - TIDAK memengaruhi nama file,
    hanya lokasi penyimpanan PDF-nya. Dipakai proses_urgent() & proses_reguler(); kegagalan
    1 batch tidak menghentikan yang lain."""
    hasil = []
    log.info("=== %s", nama)
    batch = bagi_batch([o["salesorder_id"] for o in pesanan])
    if not batch:
        log.info("  Tidak ada pesanan Siap Proses")
        return hasil
    log.info("  %d pesanan -> %d picklist", len(pesanan), len(batch))
    for n, ids in enumerate(batch, 1):
        mulai = time.monotonic()
        try:
            pid, pno, ids_pakai = buat_picklist_channel(k, ids)
        except Lewati as e:
            log.info("  [%d/%d] Dilewati: %s", n, len(batch), e)
            continue
        nomor_terlompat = peringatan_picklist.ambil_nomor_hilang()
        log.info("  [%d/%d] Picklist %s dibuat, %d pesanan", n, len(batch), pno, len(ids_pakai))
        try:
            baris = lanjutkan_picklist(k, pid, pno, len(ids_pakai), label, folder_label,
                                       nama_file=label_file, subfolder=subfolder)
        except Exception as e:     # noqa: BLE001 - batch lain tetap lanjut
            log.exception("  TERHENTI di %s: %s", pno, e)
            lanjut = perintah_lanjut(pno, folder_label, label_file or label, subfolder=subfolder)
            baris = {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": label,
                     "No Picklist": pno, "Total Pesanan": len(ids_pakai),
                     "Catatan": f"TERHENTI: {e}. Lanjutkan: {lanjut}"}
        baris["Durasi"] = durasi(time.monotonic() - mulai)
        catat_riwayat(file_riwayat, baris)
        rekap_master_excel.catat(baris, nomor_terlompat)
        hasil.append(baris)
    return hasil


def proses_urgent(k: Klien, file_riwayat: Path, folder_label: Path,
                  skenario: list[tuple] | None = None,
                  sekarang: datetime | None = None) -> list[dict]:
    """Picklist urgent (channel Lazada; kurir GTL/SiCepat lintas channel - lihat
    SKENARIO_URGENT), sebanyak mungkin per picklist (maks MAKS_PESANAN_PICKLIST, dipecah kalau
    lebih). Alur berdiri sendiri, dipanggil HANYA lewat main.py --urgent (tidak otomatis
    dipanggil dari alur --label --jalankan/SKU spesial). Pesanan yang jam pesannya di atas
    jam cutoff skenario ditahan dulu (lihat _saring_jam_urgent()/JAM_LANJUT_URGENT), baru
    diproses saat proses_urgent() dipanggil lagi setelah jam JAM_LANJUT_URGENT. Skenario
    `per_lantai` (GTL-SiCepat) dipecah jadi picklist per LANTAI_RAK + LABEL_RAK_LAINNYA (lihat
    _kelompok_kombinasi_per_lantai()/_proses_subkelompok()) - label/nama file jadi
    "GTL-SICEPAT-LANTAI1" dst, bukan "GTL-SICEPAT" polos. Kedua skenario (Lazada DAN
    GTL-SiCepat) disimpan di subfolder SUBFOLDER_URGENT ("URGENT") di dalam folder sesi -
    lihat lanjutkan_picklist(). `sekarang`: dipakai tes, default waktu sungguhan (WIB) saat
    dipanggil. Kegagalan 1 skenario/sub-kelompok tidak menghentikan yang lain."""
    hasil = []
    for nama, channel_ids, couriers, jam_cutoff, per_lantai in skenario or SKENARIO_URGENT:
        label = nama.upper()
        try:
            mentah = ambil_pesanan_channel(k, channel_ids, couriers)
            pesanan, ditahan = _saring_jam_urgent(mentah, jam_cutoff, sekarang)
            if ditahan:
                log.info("  %d pesanan %s ditahan (jam pesan di atas %02d.00 WIB), lanjut "
                         "otomatis setelah jam %02d.00", ditahan, nama, jam_cutoff,
                         JAM_LANJUT_URGENT)
            if per_lantai:
                per_lt = _kelompok_kombinasi_per_lantai(k, pesanan, channel_ids=channel_ids,
                                                        couriers=couriers)
                subkelompok = {_label_lantai(lt): p for lt, p in per_lt.items()}
                hasil += _proses_subkelompok(k, nama, label, subkelompok, file_riwayat,
                                             folder_label, kurir=None, prefix="Urgent",
                                             subfolder=SUBFOLDER_URGENT)
            else:
                hasil += _proses_channel_batch(k, f"Urgent {nama}", label, pesanan,
                                               file_riwayat, folder_label,
                                               subfolder=SUBFOLDER_URGENT)
        except Exception as e:      # noqa: BLE001 - channel lain & SKU spesial tetap lanjut
            log.exception("  GAGAL urgent %s: %s", nama, e)
            hasil.append({"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": label,
                          "Catatan": f"GAGAL: {e}"})
    return hasil


# ==================================================== 1c. picklist sisa reguler
def ambil_pesanan_reguler(k: Klien, kurir: str | None = None,
                          batas: datetime | None = None) -> list[dict]:
    """Semua pesanan Siap Proses channel TikTok Shop ("Shop | Tokopedia") & Shopee, kurir
    J&T/SPX (atau 1 kurir saja, lihat cari_pesanan()), lintas SKU (belum dipisah spesial/
    1 qty/kombinasi, lihat pisah_reguler()). `batas`: lihat cari_pesanan()."""
    return saring_sampai_batas(
        ambil_pesanan_channel(k, CHANNEL_IDS_REGULER, _filter_kurir(kurir, KURIR_FILTER_REGULER)),
        batas)


def _ambil_kombinasi_rak_mentah(k: Klien) -> list[str]:
    """Semua kombinasi rak NON-KOSONG (tunggal MAUPUN gabungan multi-rak dipisah " - ") dari
    pesanan berstatus PAID, lewat sales/v2/orders/zones-racks-combination (paging sampai
    habis). Dipakai bersama ambil_kombinasi_rak() (1qty - buang gabungan) dan
    ambil_kombinasi_rak_semua() (kombinasi - simpan gabungan)."""
    hasil, mentah, page = [], 0, 1
    while True:
        params = {"page": page, "q": "", "sort_by": "combination", "sort_direction": "asc",
                  "page_size": 200, "combination_query": "", "location_ids[0]": -1,
                  "combination_type": "racks", "status": "PAID"}
        j = k.get("sales/v2/orders/zones-racks-combination", params)
        data = j.get("data") or []
        mentah += len(data)
        hasil += [row["combination"] for row in data if row.get("combination")]
        if not data or mentah >= int(j.get("totalCount") or 0):
            return hasil
        page += 1


def ambil_kombinasi_rak(k: Klien) -> list[str]:
    """Semua kombinasi rak TUNGGAL (bukan gabungan multi-rak dipisah " - ") dari pesanan
    berstatus PAID. Dipakai untuk memetakan salesorder_id -> grup rak lewat
    kelompokkan_kombinasi_per_grup() + ambil_id_per_grup_rak() (bagian 1qty - 1 pesanan 1 item
    selalu di 1 rak)."""
    return [c for c in _ambil_kombinasi_rak_mentah(k) if " - " not in c]


def ambil_kombinasi_rak_semua(k: Klien) -> list[str]:
    """Semua kombinasi rak TUNGGAL MAUPUN GABUNGAN dari pesanan berstatus PAID. Dipakai bagian
    kombinasi reguler (qty>1/multi-SKU, lazim tersebar di >1 rak sekaligus) lewat
    kelompokkan_kombinasi_per_lantai() + ambil_id_per_grup_rak() - beda dengan
    ambil_kombinasi_rak() yang membuang kombinasi gabungan."""
    return _ambil_kombinasi_rak_mentah(k)


def lantai_dari_kombinasi(kombinasi: str) -> str | None:
    """Lantai (digit pertama tiap segmen rak) kalau SEMUA segmen kombinasi (dipisah " - " utk
    gabungan multi-rak, lihat ambil_kombinasi_rak_semua()) sepakat 1 lantai yang ada di
    LANTAI_RAK; None kalau campur lantai atau ada segmen yang lantainya tidak valid."""
    lantai = set()
    for segmen in kombinasi.split(" - "):
        segmen = segmen.strip()
        digit = segmen[0] if segmen and segmen[0].isdigit() else None
        if digit not in LANTAI_RAK:
            return None
        lantai.add(digit)
    return next(iter(lantai)) if len(lantai) == 1 else None


def kelompokkan_kombinasi_per_lantai(kombinasi: list[str]) -> dict[str, list[str]]:
    """Kelompokkan string kombinasi rak (tunggal maupun gabungan, lihat
    ambil_kombinasi_rak_semua()) ke LANTAI_RAK lewat lantai_dari_kombinasi(). Kombinasi yang
    lantainya tidak bisa dipastikan (campur/tak dikenal) diabaikan di sini - pesanan dengan
    kombinasi itu otomatis masuk LABEL_RAK_LAINNYA lewat pisah_kombinasi_per_lantai()."""
    hasil = {lt: [] for lt in LANTAI_RAK}
    for c in kombinasi:
        lt = lantai_dari_kombinasi(c)
        if lt:
            hasil[lt].append(c)
    return hasil


def kelompokkan_kombinasi_per_grup(kombinasi: list[str]) -> dict[str, list[str]]:
    """Kelompokkan string kombinasi rak tunggal (lihat ambil_kombinasi_rak()) berdasarkan
    prefix sebelum '-' pertama, hanya untuk prefix yang ada di GRUP_RAK. Prefix di luar
    GRUP_RAK diabaikan di sini - pesanan dengan rak itu otomatis masuk LABEL_RAK_LAINNYA
    lewat pisah_satu_qty_per_rak(), bukan di sini."""
    hasil = {grup: [] for grup in GRUP_RAK}
    for c in kombinasi:
        prefix = c.split("-", 1)[0]
        if prefix in hasil:
            hasil[prefix].append(c)
    return hasil


def _potong(seq: list, n: int) -> list[list]:
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def ambil_id_per_grup_rak(k: Klien, kombinasi_per_grup: dict[str, list[str]],
                          channel_ids: list[int] | None = None,
                          couriers: list[str] | None = None) -> dict[str, set[int]]:
    """Untuk tiap grup di kombinasi_per_grup (lihat kelompokkan_kombinasi_per_grup()), cari
    salesorder_id yang kombinasi raknya cocok lewat ready-to-process?combination[]=... (bisa
    diulang), dibatasi channel_ids/couriers yang sama seperti ambil_pesanan_reguler(). Daftar
    kombinasi dipecah per MAKS_KOMBINASI_PER_PANGGILAN nilai supaya query string tidak
    kepanjangan. Dipakai _kelompok_1qty_per_rak(). Antar grup saling independen, jadi
    dijalankan BERSAMAAN lewat ThreadPoolExecutor."""
    pakai_filter_tipe = ((channel_ids and CHANNEL_ID_SHOPEE in channel_ids)
                         or any(c.lower().startswith("spx") for c in couriers or []))

    def _ambil_grup(item: tuple[str, list[str]]) -> tuple[str, set[int]]:
        grup, daftar = item
        ids = set()
        for potongan in _potong(daftar, MAKS_KOMBINASI_PER_PANGGILAN):
            page, ambil = 1, 0
            while True:
                params = {"q": "", "page": page, "page_size": 200, "sku_filter": "false",
                          "sort_by": "transaction_date", "sort_direction": "ASC",
                          "combination_type": "racks"}
                params.update({f"combination[{i}]": c for i, c in enumerate(potongan)})
                if channel_ids:
                    params.update({f"channel_ids[{i}]": c for i, c in enumerate(channel_ids)})
                if couriers:
                    params.update({f"couriers[{i}]": c for i, c in enumerate(couriers)})
                if pakai_filter_tipe:
                    params.update({f"order_type[{i}]": t
                                   for i, t in enumerate(TIPE_PESANAN_FILTER)})
                j = k.get("wms/sales/v2/orders/ready-to-process/", params)
                data = j.get("data") or []
                ambil += len(data)
                ids.update(o["salesorder_id"] for o in data)
                if not data or ambil >= int(j.get("totalCount") or 0):
                    break
                page += 1
        return grup, ids

    if not kombinasi_per_grup:
        return {}
    with ThreadPoolExecutor(max_workers=min(MAKS_WORKER_PARALEL, len(kombinasi_per_grup))) as ex:
        return dict(ex.map(_ambil_grup, kombinasi_per_grup.items()))


# ===================================================== fallback SKU bundling (live, master data)
def _item_variasi(k: Klien, kode: str) -> dict | None:
    """Cari 1 item exact match `item_code` (case-insensitive, lewat pencarian substring
    variations/v2/) - field "rack_no" di endpoint ini adalah rak MASTER STATIS per item,
    sudah lama ditempel di kartu item, beda dengan location_id di items-to-pick/
    ready-to-process yang selalu -1/virtual untuk item bundle. Inilah yang dicetak Jubelio di
    laporan "Picklist Gudang" sebagai "<item_code>-<rack_no>" (ditemukan lewat sniff
    03-10-2026 - lihat memori project_1qty_per_rak_grup). None kalau tidak ketemu (SKU sudah
    dihapus dsb). Dipakai _grup_bundle_live()."""
    j = k.get("variations/v2/", {"page": 1, "q": kode, "page_size": 25, "sort_direction": "NONE"})
    for row in j.get("data") or []:
        if str(row.get("item_code", "")).upper() == kode.upper():
            return row
    return None


def _komposisi_bundle(k: Klien, item_id: int) -> list[dict]:
    """Komponen ASLI SKU bundle (mis. SKU jualan "T01-PTAA-66" -> komponen "T01-PTAA-50" +
    "TL003") lewat v2/inventory/items/{item_id} -> bundles_variants[].compositions[]
    (ditemukan sniff 03-10-2026). Kosong kalau item bukan bundle/tidak ada datanya."""
    j = k.get(f"v2/inventory/items/{item_id}")
    hasil = []
    for bv in j.get("bundles_variants") or []:
        hasil += bv.get("compositions") or []
    return hasil


def _grup_bundle_live(k: Klien, sku: str, klasifikasi) -> str | None:
    """Resolusi 1 SKU bundle -> key (grup rak/lantai, lewat `klasifikasi(rack_no) -> key|None`)
    lewat master data Jubelio: cari item SKU itu, ambil komponennya (_komposisi_bundle()),
    abaikan komponen berawalan AWALAN_KOMPONEN_DIABAIKAN (TL - sama aturan dengan
    sku_spesial._klasifikasi_per_pesanan()) kalau ada komponen lain, lalu klasifikasikan
    `rack_no` tiap komponen yang tersisa. None kalau SKU itu bukan bundle, item/komponennya
    tidak ketemu, komponen tersebar >1 key beda (ambigu), atau panggilan API gagal - ini
    fallback TAMBAHAN, tidak boleh menghentikan proses reguler kalau API bermasalah."""
    try:
        item = _item_variasi(k, sku)
        if not item or not item.get("is_bundle"):
            return None
        komponen = _komposisi_bundle(k, item["item_id"])
        tanpa_tl = [c for c in komponen if not str(c.get("item_code", "")).upper()
                   .startswith(AWALAN_KOMPONEN_DIABAIKAN)]
        kunci = set()
        for c in (tanpa_tl or komponen):
            comp = _item_variasi(k, str(c.get("item_code", "")))
            kk = klasifikasi(comp.get("rack_no")) if comp else None
            if kk:
                kunci.add(kk)
        return next(iter(kunci)) if len(kunci) == 1 else None
    except Exception as e:      # noqa: BLE001 - fallback tambahan, jangan gagalkan proses reguler
        log.warning("  Gagal resolusi rak bundle live utk SKU %s: %s", sku, e)
        return None


def _prefix_rak(rak, grup_rak: list[str]) -> str | None:
    if rak in (None, "", "-"):
        return None
    prefix = str(rak).split("-", 1)[0]
    return prefix if prefix in grup_rak else None


def _lantai_rak(rak, lantai_list: list[str]) -> str | None:
    if rak in (None, "", "-"):
        return None
    digit = str(rak)[0]
    return digit if digit in lantai_list else None


def _rak_bundle_live_per_pesanan(k: Klien, sku_per_pesanan: dict[str, str], klasifikasi) -> dict[str, str]:
    """Bungkus _grup_bundle_live() per pesanan, DIKACHE per SKU (bukan per pesanan) supaya 1
    picklist dengan banyak pesanan SKU bundle yang sama cukup query live sekali."""
    cache: dict[str, str | None] = {}
    hasil = {}
    for no, sku in sku_per_pesanan.items():
        if sku not in cache:
            cache[sku] = _grup_bundle_live(k, sku, klasifikasi)
        if cache[sku]:
            hasil[no] = cache[sku]
    return hasil


def grup_rak_bundle_live(k: Klien, sku_per_pesanan: dict[str, str],
                         grup_rak: list[str]) -> dict[str, str]:
    """"No pesanan" -> grup rak untuk SKU bundling, diresolusi lewat master data Jubelio
    (variations/v2/, v2/inventory/items/ - lihat _grup_bundle_live()), BUKAN lewat kolom Rak
    Excel yang memang tidak pernah terisi untuk SKU bundle (lihat sku_spesial.
    sku_bundle_per_pesanan()). Fallback ini LEBIH DIUTAMAKAN daripada sku_spesial.
    grup_rak_per_pesanan()/Excel - dipanggil main.py sebelum proses_reguler()/rencana_reguler(),
    hasilnya di-merge ke grup_dari_excel (live menang kalau ada, Excel tetap fallback
    terakhir utk kasus lain yang bukan bundling). `sku_per_pesanan`: dari sku_spesial.
    sku_bundle_per_pesanan(df)."""
    return _rak_bundle_live_per_pesanan(k, sku_per_pesanan,
                                        lambda rak: _prefix_rak(rak, grup_rak))


def lantai_bundle_live(k: Klien, sku_per_pesanan: dict[str, str],
                       lantai_list: list[str]) -> dict[str, str]:
    """Sama seperti grup_rak_bundle_live() tapi granularitas LANTAI (digit pertama rack_no,
    "2A"/"2B" dianggap sama) - dipakai fallback bagian kombinasi reguler."""
    return _rak_bundle_live_per_pesanan(k, sku_per_pesanan,
                                        lambda rak: _lantai_rak(rak, lantai_list))


def pisah_satu_qty_per_rak(satu_qty: list[dict], id_per_grup: dict[str, set[int]],
                           grup_dari_excel: dict[str, str] | None = None) -> dict[str, list[dict]]:
    """Partisi satu_qty (hasil pisah_reguler()[0]) ke grup rak (GRUP_RAK, urutan itu) +
    LABEL_RAK_LAINNYA. Grup ditentukan dulu lewat id_per_grup (salesorder_id, dari live API -
    lihat ambil_id_per_grup_rak()); kalau tidak cocok di situ, coba `grup_dari_excel`
    (salesorder_no -> grup, dari sku_spesial.grup_rak_per_pesanan() - fallback KHUSUS SKU
    bundling: API live Jubelio selalu melaporkan location_id -1/virtual untuk item bundle,
    jadi tidak pernah ketemu lewat id_per_grup, padahal kolom Rak di Excel tetap berisi rak
    fisik asli komponennya, ditemukan 03-10-2026). Sisanya masuk LABEL_RAK_LAINNYA. Murni
    logika data, tidak memanggil API."""
    grup_dari_excel = grup_dari_excel or {}
    hasil = {grup: [] for grup in GRUP_RAK}
    hasil[LABEL_RAK_LAINNYA] = []
    for o in satu_qty:
        grup_cocok = next((grup for grup in GRUP_RAK
                           if o["salesorder_id"] in id_per_grup.get(grup, ())), None)
        if grup_cocok is None:
            grup_cocok = grup_dari_excel.get(o["salesorder_no"])
        hasil[grup_cocok or LABEL_RAK_LAINNYA].append(o)
    return hasil


def pisah_kombinasi_per_lantai(kombinasi: list[dict], id_per_lantai: dict[str, set[int]],
                               lantai_dari_excel: dict[str, str] | None = None) -> dict[str, list[dict]]:
    """Partisi kombinasi (hasil pisah_reguler()[1]) ke lantai (LANTAI_RAK, urutan itu) +
    LABEL_RAK_LAINNYA. Lantai ditentukan dulu lewat id_per_lantai (salesorder_id, dari live
    API - lihat ambil_id_per_grup_rak()); kalau tidak cocok, coba `lantai_dari_excel`
    (salesorder_no -> lantai, dari sku_spesial.lantai_per_pesanan() - fallback SKU bundling,
    sama alasannya dengan pisah_satu_qty_per_rak()). Sisanya masuk LABEL_RAK_LAINNYA (termasuk
    pesanan yang item-itemnya tersebar di >1 lantai). Murni logika data, tidak memanggil API."""
    lantai_dari_excel = lantai_dari_excel or {}
    hasil = {lt: [] for lt in LANTAI_RAK}
    hasil[LABEL_RAK_LAINNYA] = []
    for o in kombinasi:
        lt_cocok = next((lt for lt in LANTAI_RAK
                         if o["salesorder_id"] in id_per_lantai.get(lt, ())), None)
        if lt_cocok is None:
            lt_cocok = lantai_dari_excel.get(o["salesorder_no"])
        hasil[lt_cocok or LABEL_RAK_LAINNYA].append(o)
    return hasil


def pisah_reguler(pesanan: list[dict],
                  resi_spesial_semua: set[str]) -> tuple[list[dict], list[dict]]:
    """Keluarkan resi yang sudah termasuk SKU spesial hari ini, lalu pisah sisanya jadi
    (1 SKU 1 qty, kombinasi/multi-baris/qty>1) berdasarkan total_qty pesanan."""
    sisa = [o for o in pesanan if o["salesorder_no"] not in resi_spesial_semua]
    satu_qty = [o for o in sisa if _angka(o.get("total_qty")) == 1]
    kombinasi = [o for o in sisa if _angka(o.get("total_qty")) != 1]
    return satu_qty, kombinasi


def _kelompok_1qty_per_rak(k: Klien, satu_qty: list[dict],
                           grup_dari_excel: dict[str, str] | None = None) -> dict[str, list[dict]]:
    """Bungkus ambil_kombinasi_rak()+kelompokkan_kombinasi_per_grup()+ambil_id_per_grup_rak()+
    pisah_satu_qty_per_rak(): hasilnya peta grup -> daftar pesanan 1qty (urutan GRUP_RAK +
    LABEL_RAK_LAINNYA). Selalu query rak dengan CHANNEL_IDS_REGULER + KURIR_FILTER_REGULER
    penuh (bukan parameter `kurir` dari proses_reguler()) karena cuma dipakai cek keanggotaan
    salesorder_id - `satu_qty` yang masuk ke sini sudah difilter kurir sebelumnya. `grup_dari_excel`
    (opsional, dari sku_spesial.grup_rak_per_pesanan()): fallback khusus SKU bundling - lihat
    pisah_satu_qty_per_rak(). Kalau pengambilan data rak live API gagal (API down dsb), SEMUA
    pesanan 1qty jatuh ke grup_dari_excel/LABEL_RAK_LAINNYA supaya tidak ada yang hilang, tidak
    menghentikan proses reguler lainnya."""
    try:
        kombinasi = ambil_kombinasi_rak(k)
        id_per_grup = ambil_id_per_grup_rak(k, kelompokkan_kombinasi_per_grup(kombinasi),
                                            CHANNEL_IDS_REGULER, KURIR_FILTER_REGULER)
    except Exception as e:      # noqa: BLE001 - jangan gagalkan seluruh 1qty gara2 gagal rak
        log.warning("  Gagal ambil data rak (%s) - semua 1qty masuk kelompok \"%s\"/Excel",
                   e, LABEL_RAK_LAINNYA)
        id_per_grup = {}
    return pisah_satu_qty_per_rak(satu_qty, id_per_grup, grup_dari_excel)


def _kelompok_kombinasi_per_lantai(k: Klien, kombinasi: list[dict],
                                   lantai_dari_excel: dict[str, str] | None = None,
                                   channel_ids: list[int] | None = CHANNEL_IDS_REGULER,
                                   couriers: list[str] | None = KURIR_FILTER_REGULER) -> dict[str, list[dict]]:
    """Sama polanya dengan _kelompok_1qty_per_rak() tapi granularitas LANTAI (bukan grup rak)
    dan kombinasi rak TIDAK dibuang gabungannya (lihat ambil_kombinasi_rak_semua()) - pesanan
    kombinasi (qty>1/multi-SKU) lazim tersebar di >1 rak sekaligus. `ambil_id_per_grup_rak()`
    dipakai ulang apa adanya (generik atas dict apa pun, tidak ada logika grup-rak spesifik di
    dalamnya), dibatasi `channel_ids`/`couriers` - default skenario reguler
    (CHANNEL_IDS_REGULER/KURIR_FILTER_REGULER), tapi dioverride skenario urgent GTL-SiCepat
    (channel_ids=None, couriers=KURIR_FILTER_URGENT_GTL_SICEPAT) lewat proses_urgent()/
    rencana_urgent() supaya query ready-to-process-nya cocok dengan lingkup `kombinasi` yang
    masuk. Kalau pengambilan data rak live API gagal, SEMUA pesanan kombinasi jatuh ke
    lantai_dari_excel/LABEL_RAK_LAINNYA, tidak menghentikan proses lainnya."""
    try:
        kombinasi_rak = ambil_kombinasi_rak_semua(k)
        id_per_lantai = ambil_id_per_grup_rak(k, kelompokkan_kombinasi_per_lantai(kombinasi_rak),
                                              channel_ids, couriers)
    except Exception as e:      # noqa: BLE001 - jangan gagalkan kombinasi gara2 gagal rak
        log.warning("  Gagal ambil data rak (%s) - semua kombinasi masuk kelompok \"%s\"/Excel",
                   e, LABEL_RAK_LAINNYA)
        id_per_lantai = {}
    return pisah_kombinasi_per_lantai(kombinasi, id_per_lantai, lantai_dari_excel)


_BAGIAN_REGULER = {
    "1qty": ("1 Qty Reguler", LABEL_REGULER_1QTY, 0, SUBFOLDER_SATUAN),
    "kombinasi": ("Kombinasi Reguler", LABEL_REGULER_KOMBINASI, 1, SUBFOLDER_KOMBINASI),
}
KURIR_LABEL = {"jnt": "J&T", "spx": "SPX", "spx-hemat": "SPX-HEMAT",
               "spx-hemat-pagi": "SPX-HEMAT-PAGI", "spx-standard": "SPX-STANDARD"}   # awalan nama/label saat kurir dipisah (tampilan)
# nama file tidak boleh mengandung "&" (dibuang _nama_file()), jadi nama picklist/PDF
# tetap pakai varian tanpa simbol; kolom SKU di riwayat & log tetap pakai KURIR_LABEL.
KURIR_LABEL_FILE = {"jnt": "JNT", "spx": "SPX"}
# Varian SPX mode event dipisah dari KURIR_LABEL_FILE di atas SENGAJA: print_spesial.py
# menurunkan daftar jenis cetak/subfolder-nya dari KURIR_LABEL_FILE, jadi menambahkan di sana
# otomatis mengubah perilaku cetak harian. Dipakai lewat KURIR_KODE_FILE_SEMUA di bawah.
KURIR_LABEL_FILE_EVENT = {"spx-hemat": "SPXHEMAT", "spx-hemat-pagi": "SPXHEMATPAGI",
                          "spx-standard": "SPXSTD"}
KURIR_KODE_FILE_SEMUA = {**KURIR_LABEL_FILE, **KURIR_LABEL_FILE_EVENT}


def _nama_kurir(nama: str, kurir: str | None) -> str:
    return f"{KURIR_LABEL[kurir]} {nama}" if kurir else nama


def _label_kurir(label: str, kurir: str | None) -> str:
    return f"{KURIR_LABEL[kurir]}-{label}" if kurir else label


def _label_kurir_file(label: str, kurir: str | None) -> str:
    return f"{KURIR_KODE_FILE_SEMUA[kurir]}-{label}" if kurir else label


def _gabung_kurir(dasar: str, kurir: str | None) -> str:
    """Sisipkan awalan kurir (JNT_/SPX_) ke `dasar` (tag nama file atau subfolder) kalau
    --kurir dipakai, supaya J&T dan SPX tidak bercampur - dipakai _tag_spesial() (Alur 1)
    dan subfolder SATUAN/KOMBINASI (Alur 3, lihat proses_reguler())."""
    return f"{KURIR_KODE_FILE_SEMUA[kurir]}_{dasar}" if kurir else dasar


def _tag_spesial(kurir: str | None) -> str:
    """Tag dipakai lanjutkan_picklist() di proses() (Alur 1). Tanpa --kurir tetap
    TAG_SPESIAL polos; dengan --kurir disisipi awalan KURIR_LABEL_FILE supaya nama file
    & subfolder J&T dan SPX tidak bercampur (mis. "JNT_SPESIAL"/"SPX_SPESIAL")."""
    return _gabung_kurir(TAG_SPESIAL, kurir)


def _label_lantai(lantai: str) -> str:
    """"1"/"2"/"3" -> "LANTAI1"/"LANTAI2"/"LANTAI3"; LABEL_RAK_LAINNYA dikembalikan apa
    adanya."""
    return f"LANTAI{lantai}" if lantai in LANTAI_RAK else lantai


def _proses_subkelompok(k: Klien, nama: str, label: str, subkelompok: dict[str, list[dict]],
                        file_riwayat: Path, folder_label: Path, kurir: str | None,
                        prefix: str = "Reguler", subfolder: str | None = None) -> list[dict]:
    """Proses tiap sub-kelompok (grup rak utk 1qty, lantai utk kombinasi/urgent GTL-SiCepat -
    key subkelompok dipakai apa adanya di nama/label, pemanggil yang format tampilannya, lihat
    _label_lantai()) lewat _proses_channel_batch() - kegagalan 1 sub-kelompok tidak
    menghentikan yang lain. `prefix`: "Reguler" (default, dipakai proses_reguler()) atau
    "Urgent" (proses_urgent(), skenario per_lantai - lihat SKENARIO_URGENT); string kosong
    (proses_shopee_pagi()/proses_jnt_siang()) melewatkan prefix sama sekali (nama skenarionya
    sendiri sudah jelas tanpa awalan). `subfolder`: diteruskan apa adanya ke
    _proses_channel_batch() (lihat lanjutkan_picklist()) - sama untuk semua sub-kelompok di
    sini (grup rak/lantai TIDAK ikut memecah subfolder, hanya nama file/label)."""
    hasil = []
    for sub, pesanan in subkelompok.items():
        nama_x, label_x = f"{nama} {sub}", f"{label}-{sub}"
        tampil = _nama_kurir(nama_x, kurir)
        try:
            hasil += _proses_channel_batch(k, f"{prefix} {tampil}" if prefix else tampil,
                                           _label_kurir(label_x, kurir), pesanan,
                                           file_riwayat, folder_label,
                                           label_file=_label_kurir_file(label_x, kurir),
                                           subfolder=subfolder)
        except Exception as e:      # noqa: BLE001 - sub-kelompok lain tetap lanjut
            log.exception("  GAGAL %s %s: %s", prefix.lower(), nama_x, e)
            hasil.append({"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"),
                          "SKU": _label_kurir(label_x, kurir), "Catatan": f"GAGAL: {e}"})
    return hasil


def rencana_reguler(k: Klien, resi_spesial_semua: set[str], bagian: str | None = None,
                    kurir: str | None = None,
                    grup_dari_excel: dict[str, str] | None = None,
                    lantai_dari_excel: dict[str, str] | None = None,
                    batas: datetime | None = None) -> None:
    """Mode uji picklist sisa reguler: hanya membaca data, tidak mengubah apa pun di Jubelio.
    `kurir`: lihat cari_pesanan(). Bagian "1qty" dipecah per grup rak (lihat
    _kelompok_1qty_per_rak()/GRUP_RAK, `grup_dari_excel`: fallback SKU bundling). Bagian
    "kombinasi" dipecah per lantai (lihat _kelompok_kombinasi_per_lantai()/LANTAI_RAK,
    `lantai_dari_excel`: fallback SKU bundling). `batas`: lihat cari_pesanan()."""
    kelompok = pisah_reguler(ambil_pesanan_reguler(k, kurir, batas), resi_spesial_semua)
    for kunci, (nama, _, idx, _subfolder) in _BAGIAN_REGULER.items():
        if bagian and bagian != kunci:
            continue
        if kunci == "1qty":
            subkelompok = _kelompok_1qty_per_rak(k, kelompok[idx], grup_dari_excel)
        else:   # "kombinasi"
            per_lantai = _kelompok_kombinasi_per_lantai(k, kelompok[idx], lantai_dari_excel)
            subkelompok = {_label_lantai(lt): p for lt, p in per_lantai.items()}
        for sub, pesanan in subkelompok.items():
            batch = bagi_batch([o["salesorder_id"] for o in pesanan])
            log.info("[UJI] Reguler %-20s pesanan siap proses %3d -> %d picklist "
                     "(maks %d/picklist)", _nama_kurir(f"{nama} {sub}", kurir),
                     len(pesanan), len(batch), MAKS_PESANAN_PICKLIST)


def proses_reguler(k: Klien, resi_spesial_semua: set[str], file_riwayat: Path,
                   folder_label: Path, bagian: str | None = None,
                   kurir: str | None = None,
                   grup_dari_excel: dict[str, str] | None = None,
                   lantai_dari_excel: dict[str, str] | None = None,
                   batas: datetime | None = None) -> list[dict]:
    """Picklist "sisa reguler" (bukan SKU spesial) channel TikTok Shop & Shopee, kurir J&T/SPX
    (atau 1 kurir saja - lihat cari_pesanan(), dipakai TIPE 2 & TIPE 3): (1) 1 SKU 1 qty yang
    tidak spesial - dipecah per grup rak (lihat _kelompok_1qty_per_rak(), GRUP_RAK), (2)
    kombinasi/multi-baris/qty>1 - dipecah per lantai (lihat _kelompok_kombinasi_per_lantai(),
    LANTAI_RAK). Kegagalan 1 sub-kelompok tidak menghentikan sub-kelompok lain (lihat
    _proses_subkelompok()). Dipanggil SETELAH proses SKU spesial selesai (perlu
    resi_spesial_semua supaya tidak dobel proses). Sebanyak mungkin per picklist (maks
    MAKS_PESANAN_PICKLIST, dipecah kalau lebih). `grup_dari_excel`/`lantai_dari_excel`: lihat
    pisah_satu_qty_per_rak()/pisah_kombinasi_per_lantai() (fallback khusus SKU bundling).
    Bagian "1qty" disimpan di subfolder SUBFOLDER_SATUAN ("SATUAN"), bagian "kombinasi" di
    SUBFOLDER_KOMBINASI ("KOMBINASI") - kalau --kurir dipakai, subfolder disisipi awalan
    JNT_/SPX_ (lihat _gabung_kurir()). `batas`: lihat cari_pesanan()."""
    kelompok = pisah_reguler(ambil_pesanan_reguler(k, kurir, batas), resi_spesial_semua)
    hasil = []
    for kunci, (nama, label, idx, subfolder) in _BAGIAN_REGULER.items():
        if bagian and bagian != kunci:
            continue
        if kunci == "1qty":
            subkelompok = _kelompok_1qty_per_rak(k, kelompok[idx], grup_dari_excel)
        else:   # "kombinasi"
            per_lantai = _kelompok_kombinasi_per_lantai(k, kelompok[idx], lantai_dari_excel)
            subkelompok = {_label_lantai(lt): p for lt, p in per_lantai.items()}
        hasil += _proses_subkelompok(k, nama, label, subkelompok, file_riwayat, folder_label,
                                     kurir, subfolder=_gabung_kurir(subfolder, kurir))
    return hasil


# ==================================================== 1d. picklist Shopee Pagi
def ambil_pesanan_shopee_pagi(k: Klien, jam: int = JAM_CUTOFF_SHOPEE_PAGI,
                              sekarang: datetime | None = None) -> list[dict]:
    """Semua pesanan Siap Proses channel Shopee dengan jam pesan (WIB) maksimal `jam`
    HARI INI. Dipakai untuk picklist yang dijalankan manual 1x sehari jam 13:00 (mis. resi
    yang masuk sebelum jam 12 siang harus sudah masuk picklist ini). `sekarang`: dipakai
    tes, default waktu sungguhan (WIB) saat dipanggil."""
    pesanan = ambil_pesanan_channel(k, [CHANNEL_ID_SHOPEE], KURIR_FILTER_SHOPEE_PAGI)
    batas = (sekarang or datetime.now(WIB)).replace(hour=jam, minute=0, second=0, microsecond=0)
    hasil = []
    for o in pesanan:
        ts = o.get("transaction_date")
        if not ts:
            continue
        waktu = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(WIB)
        if waktu <= batas:
            hasil.append(o)
    return hasil


def rencana_shopee_pagi(k: Klien) -> None:
    """Mode uji picklist Shopee Pagi: hanya membaca data, tidak mengubah apa pun di Jubelio.
    Dipecah per LANTAI_RAK + LABEL_RAK_LAINNYA (lihat _kelompok_kombinasi_per_lantai()), sama
    pola dengan bagian kombinasi picklist sisa reguler/urgent GTL-SiCepat."""
    pesanan = ambil_pesanan_shopee_pagi(k)
    log.info("[UJI] Shopee Pagi (s.d. jam %02d:00 WIB) pesanan siap proses %3d, dipecah "
             "per lantai", JAM_CUTOFF_SHOPEE_PAGI, len(pesanan))
    per_lt = _kelompok_kombinasi_per_lantai(k, pesanan, channel_ids=[CHANNEL_ID_SHOPEE],
                                            couriers=KURIR_FILTER_SHOPEE_PAGI)
    for lt, sub in per_lt.items():
        batch = bagi_batch([o["salesorder_id"] for o in sub])
        log.info("  %-8s pesanan %3d -> %d picklist (maks %d/picklist)",
                 _label_lantai(lt), len(sub), len(batch), MAKS_PESANAN_PICKLIST)


def proses_shopee_pagi(k: Klien, file_riwayat: Path, folder_label: Path) -> list[dict]:
    """Picklist Shopee Pagi: semua pesanan Shopee yang jam pesannya (WIB) maksimal jam 12
    siang hari ini, dipecah per LANTAI rak gudang (1/2/3/LAINNYA - lihat
    _kelompok_kombinasi_per_lantai()/_proses_subkelompok()), masing-masing dipecah lagi kalau
    > MAKS_PESANAN_PICKLIST. Label/nama file jadi "SHOPEE-PAGI-LANTAI1" dst, bukan
    "SHOPEE-PAGI" polos. Dipanggil MANUAL 1x sehari (mis. jam 13:00), bukan bagian alur
    otomatis --label --jalankan. Kegagalan 1 sub-kelompok tidak menghentikan yang lain."""
    pesanan = ambil_pesanan_shopee_pagi(k)
    per_lt = _kelompok_kombinasi_per_lantai(k, pesanan, channel_ids=[CHANNEL_ID_SHOPEE],
                                            couriers=KURIR_FILTER_SHOPEE_PAGI)
    subkelompok = {_label_lantai(lt): p for lt, p in per_lt.items()}
    return _proses_subkelompok(k, "Shopee Pagi", LABEL_SHOPEE_PAGI, subkelompok,
                               file_riwayat, folder_label, kurir=None, prefix="",
                               subfolder=SUBFOLDER_SPX_PAGI)


# ==================================================== 1e. picklist J&T Resi Siang
def ambil_pesanan_jnt_siang(k: Klien, jam: int = JAM_CUTOFF_JNT_SIANG,
                            sekarang: datetime | None = None) -> list[dict]:
    """Semua pesanan Siap Proses channel TikTok Shop, kurir J&T saja, dengan jam pesan
    (WIB) maksimal `jam` HARI INI. Dipakai untuk picklist yang dijalankan manual 1x sehari
    jam 15:00 (resi TikTok Shop wajib keluar lewat J&T yang masuk sebelum jam 15:00 harus
    sudah masuk picklist ini). `sekarang`: dipakai tes, default waktu sungguhan (WIB) saat
    dipanggil."""
    pesanan = ambil_pesanan_channel(k, [CHANNEL_ID_TIKTOK_SHOP], couriers=["j&t"])
    batas = (sekarang or datetime.now(WIB)).replace(hour=jam, minute=0, second=0, microsecond=0)
    hasil = []
    for o in pesanan:
        ts = o.get("transaction_date")
        if not ts:
            continue
        waktu = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(WIB)
        if waktu <= batas:
            hasil.append(o)
    return hasil


def rencana_jnt_siang(k: Klien) -> None:
    """Mode uji picklist J&T Resi Siang: hanya membaca data, tidak mengubah apa pun di
    Jubelio. Dipecah per LANTAI_RAK + LABEL_RAK_LAINNYA (lihat
    _kelompok_kombinasi_per_lantai()), sama pola dengan bagian kombinasi picklist sisa
    reguler/urgent GTL-SiCepat/Shopee Pagi."""
    pesanan = ambil_pesanan_jnt_siang(k)
    log.info("[UJI] J&T Resi Siang (s.d. jam %02d:00 WIB) pesanan siap proses %3d, dipecah "
             "per lantai", JAM_CUTOFF_JNT_SIANG, len(pesanan))
    per_lt = _kelompok_kombinasi_per_lantai(k, pesanan, channel_ids=[CHANNEL_ID_TIKTOK_SHOP],
                                            couriers=["j&t"])
    for lt, sub in per_lt.items():
        batch = bagi_batch([o["salesorder_id"] for o in sub])
        log.info("  %-8s pesanan %3d -> %d picklist (maks %d/picklist)",
                 _label_lantai(lt), len(sub), len(batch), MAKS_PESANAN_PICKLIST)


def proses_jnt_siang(k: Klien, file_riwayat: Path, folder_label: Path) -> list[dict]:
    """Picklist J&T Resi Siang: semua pesanan channel TikTok Shop, kurir J&T, yang jam
    pesannya (WIB) maksimal jam 15 siang hari ini, dipecah per LANTAI rak gudang (1/2/3/
    LAINNYA - lihat _kelompok_kombinasi_per_lantai()/_proses_subkelompok()), masing-masing
    dipecah lagi kalau > MAKS_PESANAN_PICKLIST. Label/nama file jadi "JNT-SIANG-LANTAI1" dst,
    bukan "JNT-SIANG" polos. Dipanggil MANUAL 1x sehari (mis. jam 15:00), bukan bagian alur
    otomatis --label --jalankan. Kegagalan 1 sub-kelompok tidak menghentikan yang lain."""
    pesanan = ambil_pesanan_jnt_siang(k)
    per_lt = _kelompok_kombinasi_per_lantai(k, pesanan, channel_ids=[CHANNEL_ID_TIKTOK_SHOP],
                                            couriers=["j&t"])
    subkelompok = {_label_lantai(lt): p for lt, p in per_lt.items()}
    return _proses_subkelompok(k, "J&T Resi Siang", LABEL_JNT_SIANG, subkelompok,
                               file_riwayat, folder_label, kurir=None, prefix="",
                               subfolder=SUBFOLDER_JNT_SIANG)


# ==================================================== 1f. picklist SPX Standard (mode event)
# Mode event (proses-event.bat, hari 10.10/11.11/12.12 dst): SPX Standard volumenya kecil, jadi
# TIDAK dipecah spesial/satuan/kombinasi - semua pesanannya digabung lalu dipecah per LANTAI rak
# gudang saja (1/2/3/LAINNYA, pola sama dengan Shopee Pagi/J&T Siang). SPX Hemat sebaliknya
# diproses lewat alur biasa dengan kurir="spx-hemat" (spesial, satuan, kombinasi).
LABEL_SPX_STANDARD = "SPX-STANDARD"
LABEL_SHOPEE_PAGI_SPX_STANDARD = "SHOPEE-PAGI-SPX-STANDARD"
SUBFOLDER_SPX_STANDARD = "SPX_STANDARD"
KURIR_FILTER_SPX_STANDARD = [KURIR_PILIHAN["spx-standard"]]


def _lingkup_spx_standard(pagi: bool, sekarang: datetime | None) -> tuple[list[int], datetime | None]:
    """(channel_ids, batas jam pesan) picklist SPX Standard. `pagi`: versi Shopee Pagi (channel
    Shopee saja, jam pesan <= JAM_CUTOFF_SHOPEE_PAGI hari ini); selain itu seluruh hari event
    (CHANNEL_IDS_REGULER, tanpa batas jam)."""
    if pagi:
        return [CHANNEL_ID_SHOPEE], batas_jam_hari_ini(JAM_CUTOFF_SHOPEE_PAGI, sekarang)
    return CHANNEL_IDS_REGULER, None


def ambil_pesanan_spx_standard(k: Klien, pagi: bool = False,
                               sekarang: datetime | None = None) -> list[dict]:
    """Semua pesanan Siap Proses kurir SPX Standard (lihat _lingkup_spx_standard())."""
    channel_ids, batas = _lingkup_spx_standard(pagi, sekarang)
    return saring_sampai_batas(
        ambil_pesanan_channel(k, channel_ids, KURIR_FILTER_SPX_STANDARD), batas)


def _kelompok_spx_standard(k: Klien, pesanan: list[dict], pagi: bool,
                           lantai_dari_excel: dict[str, str] | None = None) -> dict[str, list[dict]]:
    """Peta lantai -> pesanan (key sudah berformat LANTAI1/2/3/LAINNYA, lihat _label_lantai())."""
    channel_ids, _ = _lingkup_spx_standard(pagi, None)
    per_lt = _kelompok_kombinasi_per_lantai(k, pesanan, lantai_dari_excel,
                                            channel_ids=channel_ids,
                                            couriers=KURIR_FILTER_SPX_STANDARD)
    return {_label_lantai(lt): p for lt, p in per_lt.items()}


def rencana_spx_standard(k: Klien, pagi: bool = False, sekarang: datetime | None = None,
                         lantai_dari_excel: dict[str, str] | None = None) -> None:
    """Mode uji picklist SPX Standard: hanya membaca data, tidak mengubah apa pun di Jubelio."""
    pesanan = ambil_pesanan_spx_standard(k, pagi, sekarang)
    log.info("[UJI] %s pesanan siap proses %3d, dipecah per lantai",
             "Shopee Pagi SPX Standard" if pagi else "SPX Standard", len(pesanan))
    for lt, sub in _kelompok_spx_standard(k, pesanan, pagi, lantai_dari_excel).items():
        batch = bagi_batch([o["salesorder_id"] for o in sub])
        log.info("  %-8s pesanan %3d -> %d picklist (maks %d/picklist)",
                 lt, len(sub), len(batch), MAKS_PESANAN_PICKLIST)


def proses_spx_standard(k: Klien, file_riwayat: Path, folder_label: Path, pagi: bool = False,
                        sekarang: datetime | None = None,
                        lantai_dari_excel: dict[str, str] | None = None) -> list[dict]:
    """Picklist SPX Standard: semua pesanan kurir SPX Standard digabung (TANPA dipisah spesial/
    satuan/kombinasi), dipecah per LANTAI rak gudang (1/2/3/LAINNYA - lihat
    _kelompok_spx_standard()/_proses_subkelompok()), masing-masing dipecah lagi kalau >
    MAKS_PESANAN_PICKLIST. Label/nama file "SPX-STANDARD-LANTAI1" dst, disimpan di subfolder
    SUBFOLDER_SPX_STANDARD. `pagi`: versi Shopee Pagi di hari event - hanya pesanan Shopee jam
    pesan <= 12:00, label "SHOPEE-PAGI-SPX-STANDARD-LANTAI1" dst, disimpan di SUBFOLDER_SPX_PAGI
    (ikut tercetak bersama jenis cetak spx-pagi). Dipanggil lewat mode event saja, tidak pernah
    dari alur harian. Kegagalan 1 sub-kelompok tidak menghentikan yang lain."""
    pesanan = ambil_pesanan_spx_standard(k, pagi, sekarang)
    subkelompok = _kelompok_spx_standard(k, pesanan, pagi, lantai_dari_excel)
    if pagi:
        nama, label = "Shopee Pagi SPX Standard", LABEL_SHOPEE_PAGI_SPX_STANDARD
        subfolder = SUBFOLDER_SPX_PAGI
    else:
        nama, label = "SPX Standard", LABEL_SPX_STANDARD
        subfolder = SUBFOLDER_SPX_STANDARD
    return _proses_subkelompok(k, nama, label, subkelompok, file_riwayat, folder_label,
                               kurir=None, prefix="", subfolder=subfolder)


# ============================================================== 2. picklist
def buat_picklist(k: Klien, sku: str, resi_spesial: set[str], kurir: str | None = None,
                  batas: datetime | None = None) -> tuple[int, str, list[int], list[dict]]:
    """`kurir`, `batas`: lihat cari_pesanan()."""
    for coba in range(1, MAKS_COBA_PICKLIST + 1):
        pakai, _ = saring(cari_pesanan(k, sku, kurir, batas), resi_spesial, kurir)
        if len(pakai) < MIN_RESI:
            raise Lewati(f"pesanan tersisa {len(pakai)} (< {MIN_RESI})")
        ids = [o["salesorder_id"] for o in pakai]

        items = k.post("sales/picklists/items-to-pick/", {"ids": ids})
        _cek_item(sku, ids, items)
        items, pesan_kosong = _pisahkan_stok_kosong(k, items)
        for p in pesan_kosong:
            log.warning("  Stok kosong (ditandai di Jubelio, dikeluarkan dari picklist): %s", p)
        ids = sorted({x["salesorder_id"] for x in items})
        if not ids:
            raise Lewati("semua pesanan kena stok kosong, tidak ada yang bisa diproses")

        body = {
            "is_completed": False, "is_warehouse": True,
            "items": [{"salesorder_detail_id": x["salesorder_detail_id"], "item_id": x["item_id"],
                       "location_id": x["location_id"], "qty_ordered": _bulat(x["qty_ordered"]),
                       "salesorder_id": x["salesorder_id"], "bundle_item_id": x["bundle_item_id"],
                       "package_detail_id": x.get("package_detail_id") or 0,
                       "package_id": x.get("package_id") or 0} for x in items],
            "merge_location": False, "picker_id": None, "picklist_id": 0,
            "picklist_no": "[auto]", "salesorderIds": ids,
        }
        r = k.post_mentah("wms/sales/picklists/", body)
        if r.status_code >= 400 and PESAN_SUDAH_DIPAKAI in r.text:
            log.warning("  Picklist ditolak (percobaan %d): %s -> filter ulang",
                        coba, jubelio._pesan(r)[:250])
            k.tidur(2)
            continue
        data = Klien._json(r, "Buat picklist")["data"]
        picks = data.get("picks") or []
        if len(picks) != 1:
            raise ProsesError(f"Terbentuk {len(picks)} picklist, diharapkan 1: {data}")
        peringatan_picklist.periksa_nomor(picks[0]["picklist_no"])
        invalid = set(data.get("invalidSO") or [])
        if invalid:
            log.warning("  %d pesanan ditolak Jubelio (invalidSO): %s", len(invalid), sorted(invalid))
        ids_terpakai = set(ids)
        sisa = [o for o in pakai if o["salesorder_id"] in ids_terpakai and o["salesorder_id"] not in invalid]
        return picks[0]["picklist_id"], picks[0]["picklist_no"], [o["salesorder_id"] for o in sisa], sisa
    raise ProsesError(f"Picklist tetap ditolak setelah {MAKS_COBA_PICKLIST} percobaan")


def _cek_item(sku: str, ids: list[int], items: list[dict]) -> None:
    """Validasi item hasil items-to-pick. SKU biasa = 1 item per pesanan.
    SKU bundle (paket) meledak jadi >1 komponen per pesanan (bundle_item_id sama,
    1 salesorder_detail_id); nama komponen tidak berhubungan dengan nama SKU jualan,
    jadi dicek lewat bundle_item_id, bukan nama. SKU bundle hanya boleh diproses sebagai
    spesial kalau namanya mengandung "PTAA" (lihat SKU_BUNDLE_DIIZINKAN) - bundle lain
    (PTAE, PTAD, BKAG, dst) dilewati (Lewati) supaya SKU itu sama sekali tidak jadi
    picklist spesial."""
    per_so: dict[int, list[dict]] = {}
    for x in items:
        per_so.setdefault(x["salesorder_id"], []).append(x)
    if sorted(per_so) != sorted(ids):
        raise Lewati("item dari Jubelio tidak cocok dengan pesanan")

    for so_id, xs in per_so.items():
        if len({x["salesorder_detail_id"] for x in xs}) != 1:
            raise Lewati(f"pesanan {so_id} berisi lebih dari 1 baris pesanan untuk {sku}")
        bundle_ids = {x.get("bundle_item_id") or 0 for x in xs}
        if len(bundle_ids) != 1:
            raise Lewati(f"pesanan {so_id}: item campur bundle dan non-bundle")
        if next(iter(bundle_ids)) == 0:
            if len(xs) != 1 or not str(xs[0].get("item_full_name", "")).startswith(f"{sku} - "):
                raise Lewati(f"ada item lain: {xs[0].get('item_full_name')}")
        elif SKU_BUNDLE_DIIZINKAN not in sku.lower():
            raise Lewati(f"SKU {sku} bundle tapi bukan {SKU_BUNDLE_DIIZINKAN.upper()}, "
                        "tidak diproses sebagai spesial")
        for x in xs:
            if _angka(x["qty_ordered"]) != 1:
                raise Lewati(f"qty item {x['qty_ordered']} pada {x.get('salesorder_no')}")

    lokasi = {x["location_id"] for x in items}
    if len(lokasi) != 1:
        raise Lewati(f"pesanan berasal dari {len(lokasi)} lokasi berbeda")


def _pisahkan_stok_kosong(k: Klien, items: list[dict]) -> tuple[list[dict], list[str]]:
    """Seperti web Jubelio (terverifikasi dari rekaman sniff sungguhan, bukan tebakan dari kode JS):
    kalau total kebutuhan suatu komponen (item_id+location_id) melebihi stoknya, SEMUA pesanan
    yang butuh komponen itu ditandai 'stok kosong' lewat API wms/sales/empty-stock dan dikeluarkan
    dari daftar yang dipakai untuk membuat picklist (bukan cuma kelebihannya). Picklist tetap
    dibuat untuk pesanan yang komponennya masih cukup stok.
    Return: (item yang tetap diproses, daftar pesan ringkasan kekurangan per komponen)."""
    per_komponen: dict[tuple, list[dict]] = {}
    for x in items:
        per_komponen.setdefault((x["location_id"], x["item_id"]), []).append(x)

    kurang: dict[tuple, dict] = {}          # (location_id, item_id) -> {nama, pesanan[]}
    pesanan_kosong: set[str] = set()        # salesorder_no yang dikeluarkan
    for kunci, baris in per_komponen.items():
        stok = _angka(baris[0].get("end_qty"))
        total = sum(_angka(x["qty_ordered"]) for x in baris)
        if total > stok:
            info = kurang.setdefault(kunci, {"nama": baris[0].get("item_full_name"), "pesanan": []})
            for x in baris:
                if x["salesorder_no"] not in info["pesanan"]:
                    info["pesanan"].append(x["salesorder_no"])
                pesanan_kosong.add(x["salesorder_no"])

    if not pesanan_kosong:
        return items, []

    ids_kosong = sorted({x["salesorder_id"] for x in items if x["salesorder_no"] in pesanan_kosong})
    k.post("wms/sales/empty-stock", {"salesorder_ids": ids_kosong})

    pesan = [f"{v['nama']} tidak cukup stok untuk: {', '.join(v['pesanan'])}" for v in kurang.values()]
    sisa = [x for x in items if x["salesorder_no"] not in pesanan_kosong]
    return sisa, pesan


def _mulai_backoff(awal: float, maks: float, faktor: float = 1.5):
    """Generator jeda polling adaptif (dipakai selesaikan_picking()/pesanan_selesai_pick()/
    _tunggu_dokumen() - BUKAN minta_resi(), yang jedanya sengaja tetap meniru web, lihat
    JEDA_RESI_S): makin lama status yang ditunggu belum siap, makin jarang dicek - responsif
    di awal (kebanyakan kasus selesai cepat), tidak membebani Jubelio dengan request status
    beruntun kalau ternyata lambat."""
    jeda = awal
    while True:
        yield jeda
        jeda = min(jeda * faktor, maks)


# ============================================================== 3. selesaikan picking
def _picking_selesai(p: dict) -> bool:
    return bool(p.get("is_completed")) and all(
        i.get("wms_status") == "FINISH_PICK" for i in p.get("items") or [])


def selesaikan_picking(k: Klien, picklist_id: int) -> None:
    p = k.get(f"sales/picklists/{picklist_id}")
    if _picking_selesai(p):
        log.info("  Picking sudah selesai sebelumnya")
        return
    bin_lokasi = {loc: k.get(f"wms/default-bin/{loc}")["bin_id"]
                  for loc in {i["location_id"] for i in p["items"]}}

    body = {
        "is_completed": True, "is_warehouse": True,
        "items": [{"bin_id": bin_lokasi[i["location_id"]], "bundle_item_id": i["bundle_item_id"],
                   "item_id": i["item_id"], "location_id": i["location_id"],
                   "picklist_detail_id": i["picklist_detail_id"],
                   "qty_ordered": _bulat(i["qty_ordered"]), "qty_picked": _bulat(i["qty_ordered"]),
                   "salesorder_detail_id": i["salesorder_detail_id"],
                   "salesorder_id": i["salesorder_id"], "invoice_no": i.get("invoice_no"),
                   "update": True, "package_id": i.get("package_id") or 0,
                   "package_detail_id": i.get("package_detail_id") or 0} for i in p["items"]],
        "picklist_id": p["picklist_id"], "picklist_no": p["picklist_no"], "note": p.get("note"),
    }
    k.post("wms/sales/picklists/", body)

    # penanda selesai (di UI: tulisan merah -> hitam)
    batas = time.monotonic() + TUNGGU_PICKING_S
    backoff = _mulai_backoff(0.5, 3)
    while True:
        p = k.get(f"sales/picklists/{picklist_id}")
        if _picking_selesai(p):
            return
        if time.monotonic() > batas:
            status = sorted({str(i.get("wms_status")) for i in p.get("items") or []})
            raise ProsesError(f"Picking belum selesai setelah {TUNGGU_PICKING_S} detik (status {status})")
        k.tidur(next(backoff))


# ============================================================== 4. Picking > Selesai
def pesanan_selesai_pick(k: Klien, picklist_no: str, jumlah: int) -> list[dict]:
    batas = time.monotonic() + TUNGGU_FINISH_PICK_S
    backoff = _mulai_backoff(1, 5)
    while True:
        hasil, ambil, page = [], 0, 1
        while True:
            j = k.get("wms/sales/v2/orders/finish-pick/", {
                "q": picklist_no, "page": page, "page_size": 200, "is_printed": 0,
                "sort_by": "transaction_date", "sort_direction": "DESC"})
            data = j.get("data") or []
            ambil += len(data)
            hasil += [o for o in data if o.get("picklist_no") in (None, picklist_no)]
            if not data or ambil >= int(j.get("totalCount") or 0):
                break
            page += 1
        if len(hasil) >= jumlah or time.monotonic() > batas:
            return hasil
        k.tidur(next(backoff))


# ============================================================== 5. siap dikirim
def info_slot_pickup(k: Klien, pesanan: list[dict]) -> None:
    """Seperti web: kirim 1 salesorder_id per kurir. Hanya menampilkan slot, tidak memilih."""
    per_kurir = {}
    for o in pesanan:
        per_kurir.setdefault(o.get("shipper"), o["salesorder_id"])
    try:
        k.post("shipment/shipper-pickup-time/", {"ids": list(per_kurir.values())})
    except ProsesError as e:
        log.warning("  Info slot pickup gagal diambil (diabaikan): %s", e)


def _ada_resi(r: dict) -> bool:
    return bool(str(r.get("tracking_no") or "").strip())


def _batal(r: dict) -> bool:
    """CANCELED / CANCELLED / IN_CANCEL: resinya tidak akan pernah keluar."""
    return any("CANCEL" in str(r.get(x) or "").upper()
               for x in ("internal_status", "wms_status", "channel_status", "marketplace_status"))


def _cek_batal_detail(k: Klien, rows: list[dict]) -> None:
    """Status di respons resi bisa tertinggal; pastikan lewat detail pesanan. Tiap pesanan
    independen (GET sales/orders/<id>), jadi dicek BERSAMAAN lewat ThreadPoolExecutor - bisa
    sampai MAKS_PESANAN_PICKLIST (200) pesanan sekaligus kalau resi timeout di picklist besar."""
    if not rows:
        return

    def _ambil(r: dict) -> tuple[dict, dict | None]:
        try:
            return r, k.get(f"sales/orders/{r['salesorder_id']}")
        except ProsesError as e:
            log.warning("  Status pesanan %s gagal dicek: %s", r.get("salesorder_no"), e)
            return r, None

    with ThreadPoolExecutor(max_workers=min(MAKS_WORKER_PARALEL, len(rows))) as ex:
        for r, o in ex.map(_ambil, rows):
            if o is not None:
                r.update({x: o.get(x) for x in ("internal_status", "wms_status", "channel_status")})


def minta_resi(k: Klien, ids: list[int]) -> list[dict]:
    """Ulangi seperti web sampai semua nomor resi terisi (atau batas waktu habis).
    Pesanan yang dibatalkan tidak ditunggu."""
    batas = time.monotonic() + TUNGGU_RESI_S
    while True:
        rows = k.post("wms/sales/shipments/orders/", {"ids": ids})
        tunggu = [r for r in rows if not _ada_resi(r) and not _batal(r)]
        if not tunggu:
            return rows
        if time.monotonic() > batas:
            _cek_batal_detail(k, tunggu)
            kosong = [r["salesorder_no"] for r in tunggu if not _batal(r)]
            if kosong:
                log.warning("  %d pesanan belum dapat resi setelah %d detik: %s",
                            len(kosong), TUNGGU_RESI_S, kosong)
            return rows
        k.tidur(JEDA_RESI_S)


# ============================================================== 6. label PDF
def _report_source(html: str) -> dict:
    kunci = "telerik_ReportViewer("
    i = html.find(kunci)
    if i < 0:
        raise ProsesError("Halaman label tidak berisi konfigurasi report")
    cfg, _ = json.JSONDecoder().raw_decode(html, i + len(kunci))
    return cfg["reportSource"]


def _tunggu_dokumen(k: Klien, dasar: str, doc_id: str, referer: str) -> None:
    batas = time.monotonic() + TUNGGU_PDF_S
    backoff = _mulai_backoff(0.3, 2)
    while True:
        r = k.report_get(f"{_api_report(referer)}/{dasar}/documents/{doc_id}/info", referer=referer,
                         timeout=TUNGGU_INFO_DOKUMEN_S)
        if r.status_code == 200:
            return
        if r.status_code != 202:
            raise ProsesError(f"Pembuatan dokumen gagal (HTTP {r.status_code}): {r.text[:200]}")
        if time.monotonic() > batas:
            raise DokumenMacet(f"Dokumen belum selesai dibuat setelah {TUNGGU_PDF_S} detik")
        k.tidur(next(backoff))


def _expired(e: ProsesError) -> bool:
    return "410" in str(e) and "Expired" in str(e)


def _ulang_label(e: ProsesError) -> bool:
    """Gagal yang diulang unduh_label() dari awal dengan client baru (lihat di sana)."""
    return _expired(e) or isinstance(e, DokumenMacet)


def _buat_instance_report(k: Klien, rs: dict, referer: str) -> str:
    """clients -> parameters -> instances."""
    c = k.report_post("clients", {"timeStamp": int(time.time() * 1000)},
                      referer=referer)["clientId"]
    params = k.report_post(f"clients/{c}/parameters",
                           {"report": rs["report"], "parameterValues": rs["parameters"]},
                           referer=referer)
    nilai = {p["id"]: p["value"] for p in params}
    inst = k.report_post(f"clients/{c}/instances",
                         {"report": rs["report"], "parameterValues": nilai},
                         referer=referer)
    return f"clients/{c}/instances/{inst['instanceId']}"


def unduh_label(k: Klien, ids: list[int], tujuan: Path, lazada: bool = False) -> Path:
    """Client Telerik report-prod hanya hidup di memori 1 node; kalau node itu kehilangan
    client kita (HTTP 410 "Client ... not found. Expired.") di langkah MANA PUN - instances,
    documents, info, sampai unduh PDF-nya (insiden 2026-10-06: 20 picklist TERHENTI di
    langkah documents, 1 di unduh PDF, yang dulu tidak ikut diulang) - ATAU dokumennya macet
    tidak kunjung jadi (DokumenMacet, lihat TUNGGU_PDF_S), ulangi SELURUH alur dari halaman
    label dengan client baru (url label & token baru, bisa jatuh ke node lain), sampai
    TUNGGU_LABEL_S habis. `lazada`: lihat _unduh_label_sekali()."""
    mulai = time.monotonic()
    batas = mulai + TUNGGU_LABEL_S
    coba = 0
    while True:
        coba += 1
        host = HOST_REPORT[(coba - 1) % len(HOST_REPORT)]
        try:
            isi = _unduh_label_sekali(k, ids, host, lazada)
            break
        except (ProsesError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            # gagal APA PUN di host pertama -> langsung coba host cadangan; selanjutnya hanya
            # kalau client kedaluwarsa/dokumen macet
            if coba > 1 and not (isinstance(e, ProsesError) and _ulang_label(e)):
                raise
            if time.monotonic() + JEDA_COBA_LABEL_S > batas:
                raise type(e)(f"{e} (menyerah setelah {coba} percobaan dengan client baru, "
                              f"{durasi(time.monotonic() - mulai)})") from e
            log.info("  Label gagal di %s (percobaan %d: %s), ulangi dari awal dengan client "
                     "baru di %s %d detik lagi", host, coba, e,
                     HOST_REPORT[coba % len(HOST_REPORT)], JEDA_COBA_LABEL_S)
            k.tidur(JEDA_COBA_LABEL_S)
    if coba > 1:
        log.info("  Label berhasil di percobaan %d via %s (%s)", coba, host,
                 durasi(time.monotonic() - mulai))
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_bytes(isi)
    return tujuan


# Template "Label Pengiriman Lazada" berukuran A5 (148x210 mm), sedangkan kertas label thermal
# 100x150 mm. PDF disimpan A5 asli (sama dengan unduhan manual); label Lazada dicetak MANUAL
# oleh tim dengan skala custom 68% (100/148 = 67,6%) - TIDAK ada cetak bulk Lazada.


def _unduh_label_sekali(k: Klien, ids: list[int], host: str = HOST_REPORT_UTAMA,
                        lazada: bool = False) -> bytes:
    """`lazada`: tambahkan isFromLz=true seperti web untuk pesanan Lazada. Tanpa ini Jubelio
    memberi template umum "Label Pengiriman" (PDF beda dari unduhan manual); dengan ini
    template "Label Pengiriman Lazada" (sniff 2026-10-07)."""
    params = {**_ids_param(ids), "tz": "Asia/Jakarta"}
    if lazada:
        params["isFromLz"] = "true"
    j = k.get("reports/shipping-label/", params)
    # API Jubelio memberi URL di report-prod; dialihkan ke `host` untuk seluruh alur ini
    url_halaman = _ganti_host(j["url"], host)
    halaman = k.report_get(url_halaman, referer="https://v2.jubelio.com/")
    if halaman.status_code != 200:
        raise ProsesError(f"Halaman label gagal dibuka (HTTP {halaman.status_code})")
    rs = _report_source(halaman.text)
    # referer LOKAL (bukan k.halaman_report - k dibagi banyak worker paralel sekaligus, lihat
    # proses(); menimpa atribut bersama itu race condition, lihat catatan di Klien.__init__).
    referer = url_halaman

    dasar = _buat_instance_report(k, rs, referer)

    pdf = {"format": "PDF", "deviceInfo": {"ImmediatePrint": True, "BasePath": "/api/reports"},
           "useCache": True}
    try:
        doc = k.report_post(f"{dasar}/documents", pdf, referer=referer)["documentId"]
        _tunggu_dokumen(k, dasar, doc, referer)
    except ProsesError as e:
        if _ulang_label(e):
            # client hilang (HTML5 di client yang sama pasti 410 juga) / dokumen macet di node
            # ini (HTML5 di node yang sama ikut macet - insiden 2026-10-06) -> unduh_label()
            # mengulang dari awal dengan client baru
            raise
        # cara web: buat tampilan HTML5 dulu, lalu PDF berdasarkan dokumen itu
        log.info("  PDF langsung gagal (%s), mencoba lewat HTML5", e)
        html5 = k.report_post(f"{dasar}/documents", {
            "format": "HTML5", "useCache": True, "deviceInfo": {
                "enableSearch": True, "ContentOnly": True, "UseSVG": True, "BasePath": "/api/reports"}},
            referer=referer)
        _tunggu_dokumen(k, dasar, html5["documentId"], referer)
        doc = k.report_post(f"{dasar}/documents",
                            {**pdf, "baseDocumentID": html5["documentId"]},
                            referer=referer)["documentId"]
        _tunggu_dokumen(k, dasar, doc, referer)

    url_dok = f"{_api_report(referer)}/{dasar}/documents/{doc}"
    r = k.report_get(url_dok, params={"response-content-disposition": "attachment"},
                     referer=referer, timeout=TUNGGU_UNDUH_PDF_S)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        url_alt = _ganti_host(url_dok, next(h for h in HOST_REPORT if h != host))
        log.info("  Unduh PDF label dari %s gagal (HTTP %s), coba %s",
                 url_dok, r.status_code, url_alt)
        r = k.report_get(url_alt, params={"response-content-disposition": "attachment"},
                         referer=referer, timeout=TUNGGU_UNDUH_PDF_S)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        jenis = r.headers.get("content-type") or ""
        # isi JSON ikut dicantumkan supaya _expired() bisa mengenali 410 "Client ... Expired."
        rinci = f": {jubelio._pesan(r)}" if "json" in jenis else ""
        raise ProsesError(f"Unduh PDF label gagal (HTTP {r.status_code}, {jenis}){rinci}")
    return r.content


# ============================================================== riwayat
# Workbook riwayat_picklist.xlsx & detail-resi-*.xlsx dibuka SEKALI per file (cache di sini,
# key = path resolve()) dan disimpan SEKALI di akhir proses lewat tutup_riwayat() (dipanggil
# main.py lewat finally), menghindari load_workbook()+wb.save() ULANG seluruh file tiap
# picklist/batch (O(n^2) kalau dibuka-simpan tiap baris). File ini kecil, jadi cukup 1x per
# proses - beda dengan PICKLIST.xlsx (puluhan MB) yang diantrekan & ditulis 1x per TIPE (lihat
# rekap_master_excel.py).
# catat_detail_spesial() bisa dipanggil dari beberapa thread worker sekaligus (lihat
# MAKS_WORKER_PARALEL di proses()), jadi semua akses _wb_cache/worksheet dikunci _lock_wb.
_wb_cache: dict[Path, "Workbook"] = {}
_lock_wb = threading.Lock()


def _wb_riwayat(file: Path) -> tuple["Workbook", "Worksheet"]:
    from openpyxl import Workbook, load_workbook

    key = file.resolve()
    if key in _wb_cache:
        wb = _wb_cache[key]
        return wb, wb.active
    if file.exists():
        wb = load_workbook(file)
        ws = wb.active
        if ws.cell(1, len(KOLOM_RIWAYAT)).value is None:    # file lama belum punya kolom Durasi
            ws.cell(1, len(KOLOM_RIWAYAT), KOLOM_RIWAYAT[-1])
            ws.column_dimensions["H"].width = 18
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Riwayat"
        ws.append(KOLOM_RIWAYAT)
        for kol, lebar in zip("ABCDEFGH", (18, 16, 18, 14, 12, 60, 60, 18)):
            ws.column_dimensions[kol].width = lebar
    _wb_cache[key] = wb
    return wb, ws


def catat_riwayat(file: Path, baris: dict) -> None:
    try:
        with _lock_wb:
            wb, ws = _wb_riwayat(file)
            ws.append([baris.get(kol, "") for kol in KOLOM_RIWAYAT])
    except PermissionError:
        cadangan = file.with_suffix(".csv")
        log.warning("  %s sedang dibuka di Excel; riwayat ditulis ke %s", file.name, cadangan.name)
        baru = not cadangan.exists()
        with open(cadangan, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=KOLOM_RIWAYAT)
            if baru:
                w.writeheader()
            w.writerow({kol: baris.get(kol, "") for kol in KOLOM_RIWAYAT})


def _wb_detail_spesial(file: Path) -> tuple["Workbook", "Worksheet"]:
    from openpyxl import Workbook, load_workbook

    key = file.resolve()
    if key in _wb_cache:
        wb = _wb_cache[key]
        return wb, wb.active
    if file.exists():
        wb = load_workbook(file)
        ws = wb.active
    else:
        file.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "Detail"
        ws.append(KOLOM_DETAIL_SPESIAL)
        for kol, lebar in zip("ABCD", (18, 16, 22, 18)):
            ws.column_dimensions[kol].width = lebar
    _wb_cache[key] = wb
    return wb, ws


def catat_detail_spesial(folder_label: Path, nama_file: str, baris_list: list[dict]) -> None:
    """Tulis/tambah `baris_list` (kolom KOLOM_DETAIL_SPESIAL) ke `folder_label/nama_file` -
    1 file per sesi, dipanggil dari lanjutkan_picklist() - lihat NAMA_DETAIL_SPESIAL/
    NAMA_DETAIL_BUKAN_SPESIAL untuk kapan masing-masing nama file dipakai."""
    file = folder_label / nama_file
    try:
        with _lock_wb:
            wb, ws = _wb_detail_spesial(file)
            for baris in baris_list:
                ws.append([baris.get(kol, "") for kol in KOLOM_DETAIL_SPESIAL])
    except PermissionError:
        cadangan = file.with_suffix(".csv")
        log.warning("  %s sedang dibuka di Excel; detail ditulis ke %s", file.name, cadangan.name)
        baru = not cadangan.exists()
        with open(cadangan, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=KOLOM_DETAIL_SPESIAL)
            if baru:
                w.writeheader()
            for baris in baris_list:
                w.writerow({kol: baris.get(kol, "") for kol in KOLOM_DETAIL_SPESIAL})


def tutup_riwayat() -> None:
    """Simpan semua workbook riwayat/detail-spesial yang dibuka selama proses ke disk SEKALI -
    WAJIB dipanggil di akhir proses (main.py, lewat finally). Kalau sedang dibuka di Excel
    (PermissionError), dicoba ulang singkat lalu disimpan ke file cadangan supaya baris yang
    sudah ditulis di memori proses ini tidak hilang."""
    import peringatan_gagal

    for key, wb in list(_wb_cache.items()):
        try:
            for coba in range(3):
                try:
                    wb.save(key)
                    break
                except PermissionError:
                    if coba < 2:
                        time.sleep(2)
            else:
                cadangan = key.with_name(f"{key.stem}_tertunda_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
                wb.save(cadangan)
                peringatan_gagal.catat(
                    f"{key.name} sedang dibuka (tutup dulu di Excel) - baris baru disimpan "
                    f"sementara ke {cadangan.name}, gabungkan manual ke {key.name}")
        except Exception as e:     # noqa: BLE001 - jangan sampai proses picklist utama gagal
            peringatan_gagal.catat(f"Gagal simpan {key.name} maupun cadangannya: {e}")
    _wb_cache.clear()


# ============================================================== alur
def _nama_file(teks: str) -> str:
    return re.sub(r"[^\w.-]+", "_", teks)


def perintah_lanjut(picklist_no: str, folder_label: Path, nama: str,
                    tag: str | None = None, subfolder: str | None = None) -> str:
    """Perintah --lanjut lengkap untuk picklist yang TERHENTI, dicantumkan di Catatan
    riwayat/peringatan supaya tinggal disalin. Membawa nama label, tag/subfolder, dan folder
    sesi asal - tanpa itu lanjutkan() tidak tahu picklist ini dari alur mana, sehingga PDF-nya
    tidak masuk subfolder yang dibaca print_spesial.py --jenis dan tidak satu sesi dengan
    label lain dari proses yang sama."""
    def _kutip(s: str) -> str:
        return f'"{s}"' if " " in s else s

    bagian = [r".\jalankan.bat", "--lanjut", picklist_no, "--nama", _kutip(nama)]
    if tag:
        bagian += ["--tag", tag]
    if subfolder:
        bagian += ["--subfolder", subfolder]
    bagian += ["--sesi", f"{folder_label.parent.name}/{folder_label.name}", "--jalankan"]
    return " ".join(bagian)


def lanjutkan_picklist(k: Klien, picklist_id: int, picklist_no: str, jumlah: int,
                       sku: str, folder_label: Path, nama_file: str | None = None,
                       tag: str | None = None, subfolder: str | None = None) -> dict:
    """Langkah 3-6. Aman dipanggil ulang untuk picklist yang prosesnya terhenti.
    `nama_file`: varian `sku` yang dipakai untuk nama file PDF (mis. tanpa "&"); default
    sama dengan `sku`. `tag`: penanda opsional disisipkan setelah No Picklist di nama file
    (mis. TAG_SPESIAL untuk Alur 1 - SKU spesial); default tanpa penanda. Kalau `tag` diisi,
    file PDF-nya juga disimpan di subfolder `folder_label/<tag>` (bukan langsung di
    `folder_label`), supaya folder sesi tidak penuh puluhan file SPESIAL bercampur label
    lain - lihat TAG_SPESIAL. `subfolder`: subfolder tujuan yang TIDAK ikut disisipkan ke
    nama file (beda dari `tag`) - dipakai Alur 2/3 (lihat SUBFOLDER_URGENT/SUBFOLDER_SATUAN/
    SUBFOLDER_KOMBINASI di proses_urgent()/proses_reguler()) supaya nama file tetap seperti
    semula, cuma lokasi penyimpanannya yang pindah. Default (keduanya None) tanpa subfolder;
    kalau keduanya diisi (tidak terjadi di kode saat ini), `subfolder` menang.
    Kalau `tag` menandakan SKU spesial (lihat TAG_SPESIAL/_tag_spesial()), tiap pesanan yang
    resinya benar-benar keluar dicatat juga ke catat_detail_spesial() - NAMA_DETAIL_SPESIAL
    kalau jumlahnya masih >= MIN_RESI, NAMA_DETAIL_BUKAN_SPESIAL kalau kurang (sebagian resi
    di picklist ini batal/tidak keluar saat proses, jadi SKU-nya gugur jadi tidak spesial)."""
    log.info("  [3] Selesaikan picking %s", picklist_no)
    selesaikan_picking(k, picklist_id)

    log.info("  [4] Cari pesanan %s di Picking > Selesai", picklist_no)
    pesanan = pesanan_selesai_pick(k, picklist_no, jumlah)
    if not pesanan:
        raise ProsesError(f"Tidak ada pesanan {picklist_no} di Picking > Selesai "
                          "(mungkin label sudah dicetak)")
    if len(pesanan) != jumlah:
        log.warning("  Pesanan di Picking > Selesai %d, picklist berisi %d", len(pesanan), jumlah)
    ids = [o["salesorder_id"] for o in pesanan]

    log.info("  [5] Siap dikirim: minta resi untuk %d pesanan", len(ids))
    info_slot_pickup(k, pesanan)
    rows = minta_resi(k, ids)
    baris_ada_resi = [r for r in rows if _ada_resi(r)]
    ada_resi = [r["salesorder_id"] for r in baris_ada_resi]
    batal = [str(r.get("salesorder_no")) for r in rows if not _ada_resi(r) and _batal(r)]
    tanpa_resi = [str(r.get("salesorder_no")) for r in rows if not _ada_resi(r) and not _batal(r)]
    if batal:
        log.info("  %d pesanan dibatalkan, tidak dicetak (tetap dihitung selesai): %s",
                 len(batal), ", ".join(batal))
    peringatan_resi.catat_tanpa_resi(picklist_no, sku, tanpa_resi)
    catatan = "; ".join(teks for teks in (
        f"batal, tidak dicetak: {', '.join(batal)}" if batal else "",
        f"belum dapat resi: {', '.join(tanpa_resi)}" if tanpa_resi else "") if teks)

    file_label = ""
    if ada_resi:
        log.info("  [6] Unduh label PDF (%d pesanan)", len(ada_resi))
        awalan = f"{picklist_no}_{tag}_" if tag else f"{picklist_no}_"
        sub = subfolder if subfolder is not None else tag
        folder_tujuan = (folder_label / sub) if sub else folder_label
        tujuan = folder_tujuan / (f"{awalan}{_nama_file(nama_file or sku)}_"
                                  f"{datetime.now():%Y-%m-%d_%H%M%S}.pdf")
        sumber = {o.get("source") for o in pesanan if o["salesorder_id"] in set(ada_resi)}
        file_label = str(unduh_label(k, ada_resi, tujuan, lazada=sumber == {CHANNEL_ID_LAZADA}))
        log.info("  Label: %s", file_label)

    if tag and tag.endswith(TAG_SPESIAL) and baris_ada_resi:
        nama_detail = nama_detail_per_kurir(
            NAMA_DETAIL_SPESIAL if len(baris_ada_resi) >= MIN_RESI
            else NAMA_DETAIL_BUKAN_SPESIAL, tag)
        catat_detail_spesial(folder_label, nama_detail, [
            {"No Picklist": picklist_no, "SKU": sku, "No Pesanan": r.get("salesorder_no"),
             "No Resi": r.get("tracking_no")} for r in baris_ada_resi])

    return {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": sku,
            "No Picklist": picklist_no, "Total Pesanan": jumlah, "Resi Keluar": len(ada_resi),
            "File Label": file_label, "Catatan": catatan, "Tanpa Resi": tanpa_resi}


def rencana(k: Klien, resi_per_sku: dict[str, list[str]],
            rak_per_sku: dict[str, str] | None = None, kurir: str | None = None,
            batas: datetime | None = None) -> list[dict]:
    """Mode uji: hanya membaca data, tidak mengubah apa pun di Jubelio. `kurir`, `batas`:
    lihat cari_pesanan()."""
    rak_per_sku = rak_per_sku or {}
    hasil = []
    for sku, resi in resi_per_sku.items():
        pakai, buang = saring(cari_pesanan(k, sku, kurir, batas), set(resi), kurir)
        hitung_kurir: dict[str, int] = {}
        for o in pakai:
            hitung_kurir[o["shipper"]] = hitung_kurir.get(o["shipper"], 0) + 1
        status = "akan diproses" if len(pakai) >= MIN_RESI else f"dilewati (< {MIN_RESI} pesanan)"
        log.info("[UJI] Rak %-8s %-14s resi spesial %3d | siap diproses %3d | %s | %s",
                 rak_per_sku.get(sku, "-"), sku, len(resi), len(pakai), status,
                 ", ".join(f"{n} {kur}" for kur, n in sorted(hitung_kurir.items())))
        for no, alasan in buang:
            if alasan != "tidak termasuk resi spesial di Excel":
                log.info("        - %s dibuang: %s", no, alasan)
        hilang = set(resi) - {o["salesorder_no"] for o in pakai} - {no for no, _ in buang}
        if hilang:
            log.info("        - %d resi spesial sudah tidak ada di Siap Proses%s", len(hilang),
                     " (atau lewat jam batas)" if batas else "")
        hasil.append({"sku": sku, "pesanan": len(pakai), "status": status})
    return hasil


def proses(k: Klien, resi_per_sku: dict[str, list[str]], folder_label: Path,
           file_riwayat: Path, rak_per_sku: dict[str, str] | None = None,
           kurir: str | None = None, batas: datetime | None = None) -> list[dict]:
    """Proses SKU sesuai urutan resi_per_sku (urut rak). Tiap hasil berisi Rak, Durasi & detik.
    `kurir`, `batas`: lihat cari_pesanan(). Picklist (langkah 1-2) dibuat berurutan untuk tiap SKU
    (perlu urutan pasti demi peringatan_picklist.ambil_nomor_hilang()), tapi langkah 3-6
    (tunggu picking, minta resi, unduh PDF - lihat lanjutkan_picklist()) untuk SKU yang
    picklist-nya berhasil dibuat dijalankan BERSAMAAN lewat ThreadPoolExecutor
    (lihat MAKS_WORKER_PARALEL) karena di situlah waktu TUNGGU paling banyak terpakai."""
    rak_per_sku = rak_per_sku or {}
    hasil: list[dict] = []
    tugas = []     # (indeks di hasil, mulai, pid, pno, jumlah, sku, nomor_terlompat)

    for n, (sku, resi) in enumerate(resi_per_sku.items(), 1):
        mulai = time.monotonic()
        rak = rak_per_sku.get(sku, "-")
        log.info("=== [%d/%d] Rak %s | SKU %s (%d resi spesial)",
                 n, len(resi_per_sku), rak, sku, len(resi))
        hasil.append({"Rak": rak, "mulai": mulai})    # placeholder, diisi penuh di bawah
        idx = len(hasil) - 1
        try:
            log.info("  [1-2] Filter pesanan & buat picklist")
            pid, pno, ids, _ = buat_picklist(k, sku, set(resi), kurir, batas)
        except Lewati as e:
            log.info("  Dilewati: %s", e)
            detik = time.monotonic() - mulai
            hasil[idx] = {"SKU": sku, "Catatan": f"Dilewati: {e}", "Rak": rak,
                         "detik": detik, "Durasi": durasi(detik)}
        except Exception as e:     # noqa: BLE001 - satu SKU gagal, SKU lain tetap jalan
            log.exception("  GAGAL %s: %s", sku, e)
            detik = time.monotonic() - mulai
            hasil[idx] = {"SKU": sku, "Catatan": f"GAGAL sebelum picklist dibuat: {e}", "Rak": rak,
                         "detik": detik, "Durasi": durasi(detik)}
        else:
            nomor_terlompat = peringatan_picklist.ambil_nomor_hilang()
            log.info("  Picklist %s dibuat, %d pesanan - lanjut diproses paralel", pno, len(ids))
            tugas.append((idx, mulai, pid, pno, len(ids), sku, nomor_terlompat))

    def _lanjutkan(t: tuple) -> tuple:
        idx, mulai, pid, pno, jumlah, sku, nomor_terlompat = t
        baris = {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": sku,
                 "No Picklist": pno, "Total Pesanan": jumlah}
        tag = _tag_spesial(kurir)
        try:
            baris = lanjutkan_picklist(k, pid, pno, jumlah, sku, folder_label, tag=tag)
        except Exception as e:     # noqa: BLE001 - satu SKU gagal, SKU lain tetap jalan
            log.exception("  TERHENTI di %s: %s", pno, e)
            baris["Catatan"] = (f"TERHENTI: {e}. Lanjutkan: "
                                f"{perintah_lanjut(pno, folder_label, sku, tag=tag)}")
        return idx, mulai, nomor_terlompat, baris

    if tugas:
        with ThreadPoolExecutor(max_workers=min(MAKS_WORKER_PARALEL, len(tugas))) as ex:
            for idx, mulai, nomor_terlompat, baris in ex.map(_lanjutkan, tugas):
                rak = hasil[idx]["Rak"]
                detik = time.monotonic() - mulai
                baris.update({"Rak": rak, "detik": detik, "Durasi": durasi(detik)})
                catat_riwayat(file_riwayat, baris)
                rekap_master_excel.catat(baris, nomor_terlompat)
                log.info("  Selesai SKU %s dalam %s", baris["SKU"], baris["Durasi"])
                hasil[idx] = baris

    for h in hasil:
        h.pop("mulai", None)
    return hasil


def lanjutkan(k: Klien, picklist_no: str, folder_label: Path, file_riwayat: Path,
              nama: str | None = None, tag: str | None = None,
              subfolder: str | None = None) -> dict:
    """Lanjutkan picklist yang prosesnya terhenti (mis. PICK-000154839). `nama`/`tag`/
    `subfolder`: sama dengan saat picklist itu dibuat (lihat perintah_lanjut() - sudah
    tercantum di Catatan TERHENTI-nya), supaya nama file & subfolder PDF-nya sama dengan alur
    asalnya. Tanpa `nama`, nama file memakai SKU-nya kalau cuma 1 SKU, selain itu "LANJUTAN"
    - BUKAN gabungan semua SKU, yang untuk picklist lintas SKU bisa ratusan karakter
    (PICK-000157269: 70 SKU) dan melewati batas 255 karakter nama file Windows."""
    m = re.fullmatch(r"PICK-0*(\d+)", picklist_no.strip().upper())
    if not m:
        raise ProsesError(f"Format nomor picklist tidak dikenal: {picklist_no}")
    p = k.get(f"sales/picklists/{int(m.group(1))}")
    skus = sorted({str(i.get("item_code")) for i in p["items"]})
    sku = nama or "+".join(skus)
    nama_file = nama or (skus[0] if len(skus) == 1 else "LANJUTAN")
    jumlah = len({i["salesorder_id"] for i in p["items"]})
    log.info("=== Lanjutkan %s (SKU %s, %d pesanan)", p["picklist_no"], sku, jumlah)
    mulai = time.monotonic()
    try:
        baris = lanjutkan_picklist(k, p["picklist_id"], p["picklist_no"], jumlah, sku, folder_label,
                                   nama_file=nama_file, tag=tag, subfolder=subfolder)
    except Exception as e:
        baris_gagal = {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": sku,
                       "No Picklist": p["picklist_no"], "Total Pesanan": jumlah,
                       "Catatan": f"TERHENTI lagi: {e}",
                       "Durasi": durasi(time.monotonic() - mulai)}
        catat_riwayat(file_riwayat, baris_gagal)
        rekap_master_excel.catat(baris_gagal)
        raise
    baris["Durasi"] = durasi(time.monotonic() - mulai)
    catat_riwayat(file_riwayat, baris)
    rekap_master_excel.catat(baris)
    return baris
