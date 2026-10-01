"""Proses pesanan Jubelio sampai label pengiriman PDF - 5 alur, langkah 3-6 dipakai bersama
(lihat analisa-alur-cetak-label.md untuk detail request/respons langkah-langkah ini):
  1. Filter pesanan Siap Proses (disaring pakai aturan masing-masing, lihat di bawah)
  2. Buat picklist                          -> PICK-000xxxxxx
  3. Selesaikan picking, tunggu semua item berstatus FINISH_PICK
  4. Ambil pesanan picklist di Picking > Selesai
  5. Siap dikirim, tunggu semua nomor resi keluar
  6. Unduh label PDF (Telerik report-prod, tanpa browser)
Setiap picklist dicatat di riwayat_picklist.xlsx.

Alur 1 - SKU spesial (fungsi rencana()/proses()/lanjutkan()): per SKU, filter kurir J&T/SPX
(default, digabung) atau 1 kurir saja lewat parameter `kurir` ("jnt"/"spx" - lihat
KURIR_PILIHAN, dipakai TIPE 2 & TIPE 3 supaya J&T dan SPX jadi picklist terpisah
saat pembuatan, lihat JADWAL-PROSES.md), disaring lagi dengan aturan SKU spesial (resi
tunggal, qty 1, nilai != 0, SKU >= 3 resi sejenis - lihat panduan-sku-spesial.md; penentuan
SKU spesial itu sendiri TETAP menggabung J&T+SPX, `kurir` hanya membatasi resi mana yang
benar-benar dipicklist). 1 picklist = 1 SKU, validasi SKU-nya sama semua lewat _cek_item().
Nama file label PDF alur ini (dan hanya alur ini) disisipi penanda `SPESIAL`:
`PICK-000xxxxxx_SPESIAL_<SKU>_<tanggal>_<jam>.pdf` (lihat TAG_SPESIAL, dipakai lewat
parameter `tag` di lanjutkan_picklist()). Alur 2-5 TIDAK memakai penanda ini.

Alur 2 - picklist urgent (fungsi rencana_urgent()/proses_urgent()): lintas SKU, 2 skenario -
channel Lazada, dan kurir GTL/SiCepat (lintas channel, TIDAK dibatasi channel Tokopedia -
lihat SKENARIO_URGENT), sebanyak mungkin per picklist (maks MAKS_PESANAN_PICKLIST, dipecah
kalau lebih). Tidak ada validasi SKU sejenis (multi-SKU per pesanan boleh). **Alur berdiri
sendiri** - dipanggil HANYA lewat main.py --urgent, TIDAK otomatis dipanggil oleh alur 1
(--label --jalankan). Kalau perlu urgent diproses lebih dulu, itu harus dijalankan manual
terpisah sebelum --label --jalankan (lihat README bagian "Picklist urgent").

Alur 3 - picklist sisa reguler (fungsi rencana_reguler()/proses_reguler()), dijalankan
SETELAH alur 1: lintas SKU, channel TikTok Shop ("Shop | Tokopedia") & Shopee, kurir J&T/SPX
(default, digabung) atau 1 kurir saja lewat parameter `kurir` (sama seperti alur 1), yang
BUKAN bagian SKU spesial (dikecualikan lewat resi_spesial_semua) - dipecah 2 picklist: 1 SKU
1 qty, dan kombinasi (qty > 1). Sama seperti alur 2: lintas SKU, maks MAKS_PESANAN_PICKLIST
per picklist.

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
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import jubelio
import peringatan_picklist
import peringatan_resi
from sku_spesial import KURIR_DIIZINKAN, MIN_RESI

REPORT_API = "https://report-prod.jubelio.com/api/reports"
KURIR_FILTER = ["j&t", "spx"]           # nilai filter kurir di web Jubelio
# Pemisahan J&T/SPX saat proses (dipakai TIPE 2 & TIPE 3 - lihat proses-harian.bat/
# JADWAL-PROSES.md): nilai --kurir CLI ("jnt"/"spx") -> nilai filter kurir Jubelio.
# kurir=None (default, dipakai TIPE 1/TIPE 4) = J&T dan SPX digabung seperti semula.
KURIR_PILIHAN = {"jnt": "j&t", "spx": "spx"}
# Penanda di nama file label PDF, HANYA untuk picklist SKU spesial (Alur 1 - proses()/
# lanjutkan_picklist() dipanggil dari proses()). Alur 2-5 (urgent/reguler/Shopee Pagi/
# J&T Resi Siang) tidak memakai tag ini, begitu juga lanjutkan() (resume generik lewat
# --lanjut, tidak tahu picklist itu dari alur mana).
TAG_SPESIAL = "SPESIAL"


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
SKENARIO_URGENT = [
    ("Lazada", [CHANNEL_ID_LAZADA], None),
    ("GTL-SiCepat", None, KURIR_FILTER_URGENT_GTL_SICEPAT),
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

# Picklist "Shopee Pagi" (lintas SKU): dijalankan MANUAL, 1x sehari jam 13:00 - bukan bagian
# alur otomatis --label --jalankan. Semua pesanan channel Shopee yang jam pesannya (WIB)
# maksimal jam 12:00 HARI INI, digabung jadi 1 picklist (dipecah kalau > MAKS_PESANAN_PICKLIST).
JAM_CUTOFF_SHOPEE_PAGI = 12
LABEL_SHOPEE_PAGI = "SHOPEE-PAGI"
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
TUNGGU_PICKING_S = 90                   # batas tunggu status FINISH_PICK
TUNGGU_FINISH_PICK_S = 90               # batas tunggu pesanan muncul di Picking > Selesai
TUNGGU_RESI_S = 180                     # batas tunggu semua nomor resi keluar
JEDA_RESI_S = 3.5                       # jeda polling resi (sama dengan web)
TUNGGU_PDF_S = 180
TUNGGU_CLIENT_REPORT_S = 300            # batas total coba ulang report-prod "410 Expired"
JEDA_COBA_CLIENT_REPORT_S = 5
# Koneksi putus di tengah request (mis. RemoteDisconnected) - ulangi request YANG SAMA
# beberapa kali sebelum menyerah, supaya 1 kedipan koneksi tidak menggagalkan seluruh
# picklist (operator harus --lanjut manual). Dipasang di Klien._kirim(), dipakai semua
# request keluar (get/post/report_get/report_post) - jadi retry-nya tepat di titik
# request yang gagal, bukan mengulang dari awal langkah 3-6.
MAKS_COBA_KONEKSI = 3
JEDA_COBA_KONEKSI_S = 5

KOLOM_RIWAYAT = ["Waktu", "SKU", "No Picklist", "Total Pesanan", "Resi Keluar",
                 "File Label", "Catatan", "Durasi"]

log = logging.getLogger("sku-spesial")


class ProsesError(RuntimeError):
    pass


class Lewati(Exception):
    """SKU tidak diproses (bukan error sistem), mis. pesanan tersisa < MIN_RESI."""


# ============================================================== koneksi
class Klien:
    def __init__(self, token: str, sesi=None, tidur=time.sleep):
        self.token = token
        self.sesi = sesi or requests.Session()
        self.tidur = tidur
        self.cookie = {"JB_OMNI_ACCESS_TOKEN": token}
        # Load balancer report-prod memilih node dari token di Referer; client Telerik
        # hanya ada di memori node itu, jadi Referer harus URL halaman label (seperti web).
        self.halaman_report = "https://report-prod.jubelio.com/"

    @staticmethod
    def _json(r, apa: str):
        if r.status_code >= 400:
            raise ProsesError(f"{apa} gagal (HTTP {r.status_code}): {jubelio._pesan(r)}")
        return r.json()

    def _kirim(self, fn, *a, **kw):
        """Panggil `fn` (sesi.get/sesi.post), ulangi kalau koneksi putus di tengah jalan
        (mis. ConnectionError/RemoteDisconnected, Timeout) - lihat MAKS_COBA_KONEKSI."""
        for coba in range(1, MAKS_COBA_KONEKSI + 1):
            try:
                return fn(*a, **kw)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if coba == MAKS_COBA_KONEKSI:
                    raise
                log.warning("  Koneksi putus (percobaan %d/%d): %s -> ulangi %d detik lagi",
                           coba, MAKS_COBA_KONEKSI, e, JEDA_COBA_KONEKSI_S)
                self.tidur(JEDA_COBA_KONEKSI_S)

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
    def report_get(self, url: str, params=None, referer: str | None = None):
        return self._kirim(self.sesi.get, url, params=params, cookies=self.cookie, timeout=180,
                           headers={"User-Agent": jubelio.USER_AGENT,
                                    "Referer": referer or self.halaman_report})

    def report_post(self, path: str, body):
        r = self._kirim(self.sesi.post, f"{REPORT_API}/{path}", json=body, cookies=self.cookie,
                        timeout=120,
                        headers={"User-Agent": jubelio.USER_AGENT,
                                 "Referer": self.halaman_report,
                                 "Origin": "https://report-prod.jubelio.com",
                                 "X-Requested-With": "XMLHttpRequest"})
        return self._json(r, f"report {path.rsplit('/', 1)[-1]}")


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
def cari_pesanan(k: Klien, sku: str, kurir: str | None = None) -> list[dict]:
    """`kurir`: None (default) = J&T + SPX digabung, atau "jnt"/"spx" untuk 1 kurir saja
    (lihat KURIR_PILIHAN - dipakai TIPE 2 & TIPE 3)."""
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
            return hasil
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


# ============================================== 1b. picklist urgent per channel
def ambil_pesanan_channel(k: Klien, channel_ids: list[int] | None = None,
                          couriers: list[str] | None = None) -> list[dict]:
    """Semua pesanan Siap Proses, lintas SKU, diurutkan tanggal transaksi TERLAMA dulu (ASC)
    supaya resi yang lebih lama selalu masuk picklist pertama kalau bagi_batch() memecahnya
    jadi beberapa picklist. `channel_ids` opsional: None/kosong = semua channel (dipakai
    skenario yang urgent-nya ditentukan kurir, bukan channel - mis. GTL/SiCepat, yang urgent
    baik dari Tokopedia asli maupun "Shop | Tokopedia"/TikTok). Opsional filter kurir. Kurir
    SPX dan channel Shopee selalu ikut menyertakan pesanan tipe "pengiriman kilat" kalau tidak
    difilter -> tipe itu tidak diproses lewat alur picklist ini (lihat TIPE_PESANAN_FILTER),
    jadi filter tipe pesanan otomatis ditambahkan kalau channel-nya Shopee dan/atau
    kurirnya SPX."""
    pakai_filter_tipe = ((channel_ids and CHANNEL_ID_SHOPEE in channel_ids)
                         or any(c.lower() == "spx" for c in couriers or []))
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
    if not channel_ids:
        return hasil
    # jaga-jaga: saring lagi di sisi kita terhadap channel_id sungguhan, jangan andalkan
    # filter API saja (lihat catatan "Shop | Tokopedia" di atas)
    izin = set(channel_ids)
    return [o for o in hasil if o.get("source") in izin]


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


def rencana_urgent(k: Klien, skenario: list[tuple] | None = None) -> None:
    """Mode uji picklist urgent: hanya membaca data, tidak mengubah apa pun di Jubelio."""
    for nama, channel_ids, couriers in skenario or SKENARIO_URGENT:
        pesanan = ambil_pesanan_channel(k, channel_ids, couriers)
        batch = bagi_batch([o["salesorder_id"] for o in pesanan])
        log.info("[UJI] Urgent %-10s pesanan siap proses %3d -> %d picklist (maks %d/picklist)",
                 nama, len(pesanan), len(batch), MAKS_PESANAN_PICKLIST)


def _proses_channel_batch(k: Klien, nama: str, label: str, pesanan: list[dict],
                          file_riwayat: Path, folder_label: Path,
                          label_file: str | None = None) -> list[dict]:
    """Pecah `pesanan` jadi beberapa batch (maks MAKS_PESANAN_PICKLIST), buat 1 picklist per
    batch sampai label PDF (buat picklist -> selesaikan picking -> minta resi -> unduh label).
    `label` dipakai lanjutkan_picklist() cuma sebagai penanda (bukan SKU asli), jadi nama file
    label & kolom SKU di riwayat otomatis jadi mis. PICK-000xxxxxx_LAZADA_<tanggal>_<jam>.pdf.
    `label_file`: varian `label` yang aman dipakai di nama file (mis. tanpa "&"); default sama
    dengan `label`. Dipakai proses_urgent() & proses_reguler(); kegagalan 1 batch tidak
    menghentikan yang lain."""
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
        log.info("  [%d/%d] Picklist %s dibuat, %d pesanan", n, len(batch), pno, len(ids_pakai))
        try:
            baris = lanjutkan_picklist(k, pid, pno, len(ids_pakai), label, folder_label,
                                       nama_file=label_file)
        except Exception as e:     # noqa: BLE001 - batch lain tetap lanjut
            log.exception("  TERHENTI di %s: %s", pno, e)
            baris = {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": label,
                     "No Picklist": pno, "Total Pesanan": len(ids_pakai),
                     "Catatan": f"TERHENTI: {e}. Lanjutkan: .\\run.bat --lanjut {pno} --jalankan"}
        baris["Durasi"] = durasi(time.monotonic() - mulai)
        catat_riwayat(file_riwayat, baris)
        hasil.append(baris)
    return hasil


def proses_urgent(k: Klien, file_riwayat: Path, folder_label: Path,
                  skenario: list[tuple] | None = None) -> list[dict]:
    """Picklist urgent (channel Lazada; kurir GTL/SiCepat lintas channel - lihat
    SKENARIO_URGENT), sebanyak mungkin per picklist (maks MAKS_PESANAN_PICKLIST, dipecah kalau
    lebih). Alur berdiri sendiri, dipanggil HANYA lewat main.py --urgent (tidak otomatis
    dipanggil dari alur --label --jalankan/SKU spesial). Kegagalan 1 skenario tidak
    menghentikan yang lain."""
    hasil = []
    for nama, channel_ids, couriers in skenario or SKENARIO_URGENT:
        label = nama.upper()
        try:
            pesanan = ambil_pesanan_channel(k, channel_ids, couriers)
            hasil += _proses_channel_batch(k, f"Urgent {nama}", label, pesanan,
                                           file_riwayat, folder_label)
        except Exception as e:      # noqa: BLE001 - channel lain & SKU spesial tetap lanjut
            log.exception("  GAGAL urgent %s: %s", nama, e)
            hasil.append({"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": label,
                          "Catatan": f"GAGAL: {e}"})
    return hasil


# ==================================================== 1c. picklist sisa reguler
def ambil_pesanan_reguler(k: Klien, kurir: str | None = None) -> list[dict]:
    """Semua pesanan Siap Proses channel TikTok Shop ("Shop | Tokopedia") & Shopee, kurir
    J&T/SPX (atau 1 kurir saja, lihat cari_pesanan()), lintas SKU (belum dipisah spesial/
    1 qty/kombinasi, lihat pisah_reguler())."""
    return ambil_pesanan_channel(k, CHANNEL_IDS_REGULER, _filter_kurir(kurir, KURIR_FILTER_REGULER))


def pisah_reguler(pesanan: list[dict],
                  resi_spesial_semua: set[str]) -> tuple[list[dict], list[dict]]:
    """Keluarkan resi yang sudah termasuk SKU spesial hari ini, lalu pisah sisanya jadi
    (1 SKU 1 qty, kombinasi/multi-baris/qty>1) berdasarkan total_qty pesanan."""
    sisa = [o for o in pesanan if o["salesorder_no"] not in resi_spesial_semua]
    satu_qty = [o for o in sisa if _angka(o.get("total_qty")) == 1]
    kombinasi = [o for o in sisa if _angka(o.get("total_qty")) != 1]
    return satu_qty, kombinasi


_BAGIAN_REGULER = {
    "1qty": ("1 Qty Reguler", LABEL_REGULER_1QTY, 0),
    "kombinasi": ("Kombinasi Reguler", LABEL_REGULER_KOMBINASI, 1),
}
KURIR_LABEL = {"jnt": "J&T", "spx": "SPX"}   # awalan nama/label saat kurir dipisah (tampilan)
# nama file tidak boleh mengandung "&" (dibuang _nama_file()), jadi nama picklist/PDF
# tetap pakai varian tanpa simbol; kolom SKU di riwayat & log tetap pakai KURIR_LABEL.
KURIR_LABEL_FILE = {"jnt": "JNT", "spx": "SPX"}


def _nama_kurir(nama: str, kurir: str | None) -> str:
    return f"{KURIR_LABEL[kurir]} {nama}" if kurir else nama


def _label_kurir(label: str, kurir: str | None) -> str:
    return f"{KURIR_LABEL[kurir]}-{label}" if kurir else label


def _label_kurir_file(label: str, kurir: str | None) -> str:
    return f"{KURIR_LABEL_FILE[kurir]}-{label}" if kurir else label


def rencana_reguler(k: Klien, resi_spesial_semua: set[str], bagian: str | None = None,
                    kurir: str | None = None) -> None:
    """Mode uji picklist sisa reguler: hanya membaca data, tidak mengubah apa pun di Jubelio.
    `kurir`: lihat cari_pesanan()."""
    kelompok = pisah_reguler(ambil_pesanan_reguler(k, kurir), resi_spesial_semua)
    for kunci, (nama, _, idx) in _BAGIAN_REGULER.items():
        if bagian and bagian != kunci:
            continue
        pesanan = kelompok[idx]
        batch = bagi_batch([o["salesorder_id"] for o in pesanan])
        log.info("[UJI] Reguler %-20s pesanan siap proses %3d -> %d picklist (maks %d/picklist)",
                 _nama_kurir(nama, kurir), len(pesanan), len(batch), MAKS_PESANAN_PICKLIST)


def proses_reguler(k: Klien, resi_spesial_semua: set[str], file_riwayat: Path,
                   folder_label: Path, bagian: str | None = None,
                   kurir: str | None = None) -> list[dict]:
    """Picklist "sisa reguler" (bukan SKU spesial) channel TikTok Shop & Shopee, kurir J&T/SPX
    (atau 1 kurir saja - lihat cari_pesanan(), dipakai TIPE 2 & TIPE 3): (1) 1 SKU
    1 qty yang tidak spesial, (2) kombinasi/multi-baris/qty>1. Dipanggil SETELAH proses SKU
    spesial selesai (perlu resi_spesial_semua supaya tidak dobel proses). Sebanyak mungkin per
    picklist (maks MAKS_PESANAN_PICKLIST, dipecah kalau lebih)."""
    kelompok = pisah_reguler(ambil_pesanan_reguler(k, kurir), resi_spesial_semua)
    hasil = []
    for kunci, (nama, label, idx) in _BAGIAN_REGULER.items():
        if bagian and bagian != kunci:
            continue
        try:
            hasil += _proses_channel_batch(k, f"Reguler {_nama_kurir(nama, kurir)}",
                                           _label_kurir(label, kurir), kelompok[idx],
                                           file_riwayat, folder_label,
                                           label_file=_label_kurir_file(label, kurir))
        except Exception as e:      # noqa: BLE001 - bagian lain tetap lanjut
            log.exception("  GAGAL reguler %s: %s", nama, e)
            hasil.append({"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"),
                          "SKU": _label_kurir(label, kurir), "Catatan": f"GAGAL: {e}"})
    return hasil


# ==================================================== 1d. picklist Shopee Pagi
def ambil_pesanan_shopee_pagi(k: Klien, jam: int = JAM_CUTOFF_SHOPEE_PAGI,
                              sekarang: datetime | None = None) -> list[dict]:
    """Semua pesanan Siap Proses channel Shopee dengan jam pesan (WIB) maksimal `jam`
    HARI INI. Dipakai untuk picklist yang dijalankan manual 1x sehari jam 13:00 (mis. resi
    yang masuk sebelum jam 12 siang harus sudah masuk picklist ini). `sekarang`: dipakai
    tes, default waktu sungguhan (WIB) saat dipanggil."""
    pesanan = ambil_pesanan_channel(k, [CHANNEL_ID_SHOPEE])
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
    """Mode uji picklist Shopee Pagi: hanya membaca data, tidak mengubah apa pun di Jubelio."""
    pesanan = ambil_pesanan_shopee_pagi(k)
    batch = bagi_batch([o["salesorder_id"] for o in pesanan])
    log.info("[UJI] Shopee Pagi (s.d. jam %02d:00 WIB) pesanan siap proses %3d -> "
             "%d picklist (maks %d/picklist)", JAM_CUTOFF_SHOPEE_PAGI, len(pesanan),
             len(batch), MAKS_PESANAN_PICKLIST)


def proses_shopee_pagi(k: Klien, file_riwayat: Path, folder_label: Path) -> list[dict]:
    """Picklist Shopee Pagi: semua pesanan Shopee yang jam pesannya (WIB) maksimal jam 12
    siang hari ini, digabung jadi 1 picklist (dipecah kalau > MAKS_PESANAN_PICKLIST). Dipanggil
    MANUAL 1x sehari (mis. jam 13:00), bukan bagian alur otomatis --label --jalankan."""
    pesanan = ambil_pesanan_shopee_pagi(k)
    return _proses_channel_batch(k, "Shopee Pagi", LABEL_SHOPEE_PAGI, pesanan,
                                 file_riwayat, folder_label)


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
    Jubelio."""
    pesanan = ambil_pesanan_jnt_siang(k)
    batch = bagi_batch([o["salesorder_id"] for o in pesanan])
    log.info("[UJI] J&T Resi Siang (s.d. jam %02d:00 WIB) pesanan siap proses %3d -> "
             "%d picklist (maks %d/picklist)", JAM_CUTOFF_JNT_SIANG, len(pesanan),
             len(batch), MAKS_PESANAN_PICKLIST)


def proses_jnt_siang(k: Klien, file_riwayat: Path, folder_label: Path) -> list[dict]:
    """Picklist J&T Resi Siang: semua pesanan channel TikTok Shop, kurir J&T, yang jam
    pesannya (WIB) maksimal jam 15 siang hari ini, digabung jadi 1 picklist (dipecah kalau
    > MAKS_PESANAN_PICKLIST). Dipanggil MANUAL 1x sehari (mis. jam 15:00), bukan bagian alur
    otomatis --label --jalankan."""
    pesanan = ambil_pesanan_jnt_siang(k)
    return _proses_channel_batch(k, "J&T Resi Siang", LABEL_JNT_SIANG, pesanan,
                                 file_riwayat, folder_label)


# ============================================================== 2. picklist
def buat_picklist(k: Klien, sku: str, resi_spesial: set[str],
                  kurir: str | None = None) -> tuple[int, str, list[int], list[dict]]:
    """`kurir`: lihat cari_pesanan()."""
    for coba in range(1, MAKS_COBA_PICKLIST + 1):
        pakai, _ = saring(cari_pesanan(k, sku, kurir), resi_spesial, kurir)
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
    while True:
        p = k.get(f"sales/picklists/{picklist_id}")
        if _picking_selesai(p):
            return
        if time.monotonic() > batas:
            status = sorted({str(i.get("wms_status")) for i in p.get("items") or []})
            raise ProsesError(f"Picking belum selesai setelah {TUNGGU_PICKING_S} detik (status {status})")
        k.tidur(1)


# ============================================================== 4. Picking > Selesai
def pesanan_selesai_pick(k: Klien, picklist_no: str, jumlah: int) -> list[dict]:
    batas = time.monotonic() + TUNGGU_FINISH_PICK_S
    while True:
        hasil, page = [], 1
        while True:
            j = k.get("wms/sales/v2/orders/finish-pick/", {
                "q": picklist_no, "page": page, "page_size": 25, "is_printed": 0,
                "sort_by": "transaction_date", "sort_direction": "DESC"})
            data = j.get("data") or []
            hasil += [o for o in data if o.get("picklist_no") in (None, picklist_no)]
            if not data or page * 25 >= int(j.get("totalCount") or 0):
                break
            page += 1
        if len(hasil) >= jumlah or time.monotonic() > batas:
            return hasil
        k.tidur(2)


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
    """Status di respons resi bisa tertinggal; pastikan lewat detail pesanan."""
    for r in rows:
        try:
            o = k.get(f"sales/orders/{r['salesorder_id']}")
        except ProsesError as e:
            log.warning("  Status pesanan %s gagal dicek: %s", r.get("salesorder_no"), e)
            continue
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


def _tunggu_dokumen(k: Klien, dasar: str, doc_id: str) -> None:
    batas = time.monotonic() + TUNGGU_PDF_S
    while True:
        r = k.report_get(f"{REPORT_API}/{dasar}/documents/{doc_id}/info")
        if r.status_code == 200:
            return
        if r.status_code != 202:
            raise ProsesError(f"Pembuatan dokumen gagal (HTTP {r.status_code}): {r.text[:200]}")
        if time.monotonic() > batas:
            raise ProsesError(f"Dokumen belum selesai dibuat setelah {TUNGGU_PDF_S} detik")
        k.tidur(0.5)


def _expired(e: ProsesError) -> bool:
    return "410" in str(e) and "Expired" in str(e)


def _buat_instance_report(k: Klien, rs: dict) -> str:
    """clients -> parameters -> instances. Jika node report-prod tetap tidak menemukan
    client (HTTP 410 "Client ... not found. Expired."), ulangi dari awal dengan clientId baru."""
    batas = time.monotonic() + TUNGGU_CLIENT_REPORT_S
    coba = 0
    while True:
        coba += 1
        try:
            c = k.report_post("clients", {"timeStamp": int(time.time() * 1000)})["clientId"]
            params = k.report_post(f"clients/{c}/parameters",
                                   {"report": rs["report"], "parameterValues": rs["parameters"]})
            nilai = {p["id"]: p["value"] for p in params}
            inst = k.report_post(f"clients/{c}/instances",
                                 {"report": rs["report"], "parameterValues": nilai})
            return f"clients/{c}/instances/{inst['instanceId']}"
        except ProsesError as e:
            if not _expired(e) or time.monotonic() + JEDA_COBA_CLIENT_REPORT_S > batas:
                raise
            log.info("  Client report kedaluwarsa (percobaan %d), ulangi %d detik lagi: %s",
                     coba, JEDA_COBA_CLIENT_REPORT_S, e)
            k.tidur(JEDA_COBA_CLIENT_REPORT_S)


def unduh_label(k: Klien, ids: list[int], tujuan: Path) -> Path:
    j = k.get("reports/shipping-label/", {**_ids_param(ids), "tz": "Asia/Jakarta"})
    halaman = k.report_get(j["url"], referer="https://v2.jubelio.com/")
    if halaman.status_code != 200:
        raise ProsesError(f"Halaman label gagal dibuka (HTTP {halaman.status_code})")
    rs = _report_source(halaman.text)
    k.halaman_report = j["url"]

    dasar = _buat_instance_report(k, rs)

    pdf = {"format": "PDF", "deviceInfo": {"ImmediatePrint": True, "BasePath": "/api/reports"},
           "useCache": True}
    try:
        doc = k.report_post(f"{dasar}/documents", pdf)["documentId"]
        _tunggu_dokumen(k, dasar, doc)
    except ProsesError as e:
        # cara web: buat tampilan HTML5 dulu, lalu PDF berdasarkan dokumen itu
        log.info("  PDF langsung gagal (%s), mencoba lewat HTML5", e)
        html5 = k.report_post(f"{dasar}/documents", {
            "format": "HTML5", "useCache": True, "deviceInfo": {
                "enableSearch": True, "ContentOnly": True, "UseSVG": True, "BasePath": "/api/reports"}})
        _tunggu_dokumen(k, dasar, html5["documentId"])
        doc = k.report_post(f"{dasar}/documents",
                            {**pdf, "baseDocumentID": html5["documentId"]})["documentId"]
        _tunggu_dokumen(k, dasar, doc)

    r = k.report_get(f"{REPORT_API}/{dasar}/documents/{doc}",
                     params={"response-content-disposition": "attachment"})
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        raise ProsesError(f"Unduh PDF label gagal (HTTP {r.status_code}, "
                          f"{r.headers.get('content-type')})")
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_bytes(r.content)
    return tujuan


# ============================================================== riwayat
def catat_riwayat(file: Path, baris: dict) -> None:
    from openpyxl import Workbook, load_workbook

    try:
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
        ws.append([baris.get(kol, "") for kol in KOLOM_RIWAYAT])
        wb.save(file)
    except PermissionError:
        cadangan = file.with_suffix(".csv")
        log.warning("  %s sedang dibuka di Excel; riwayat ditulis ke %s", file.name, cadangan.name)
        baru = not cadangan.exists()
        with open(cadangan, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=KOLOM_RIWAYAT)
            if baru:
                w.writeheader()
            w.writerow({kol: baris.get(kol, "") for kol in KOLOM_RIWAYAT})


# ============================================================== alur
def _nama_file(teks: str) -> str:
    return re.sub(r"[^\w.-]+", "_", teks)


def lanjutkan_picklist(k: Klien, picklist_id: int, picklist_no: str, jumlah: int,
                       sku: str, folder_label: Path, nama_file: str | None = None,
                       tag: str | None = None) -> dict:
    """Langkah 3-6. Aman dipanggil ulang untuk picklist yang prosesnya terhenti.
    `nama_file`: varian `sku` yang dipakai untuk nama file PDF (mis. tanpa "&"); default
    sama dengan `sku`. `tag`: penanda opsional disisipkan setelah No Picklist di nama file
    (mis. TAG_SPESIAL untuk Alur 1 - SKU spesial); default tanpa penanda."""
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
    ada_resi = [r["salesorder_id"] for r in rows if _ada_resi(r)]
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
        tujuan = folder_label / (f"{awalan}{_nama_file(nama_file or sku)}_"
                                 f"{datetime.now():%Y-%m-%d_%H%M%S}.pdf")
        file_label = str(unduh_label(k, ada_resi, tujuan))
        log.info("  Label: %s", file_label)
    return {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": sku,
            "No Picklist": picklist_no, "Total Pesanan": jumlah, "Resi Keluar": len(ada_resi),
            "File Label": file_label, "Catatan": catatan}


def rencana(k: Klien, resi_per_sku: dict[str, list[str]],
            rak_per_sku: dict[str, str] | None = None, kurir: str | None = None) -> list[dict]:
    """Mode uji: hanya membaca data, tidak mengubah apa pun di Jubelio. `kurir`: lihat
    cari_pesanan()."""
    rak_per_sku = rak_per_sku or {}
    hasil = []
    for sku, resi in resi_per_sku.items():
        pakai, buang = saring(cari_pesanan(k, sku, kurir), set(resi), kurir)
        kurir: dict[str, int] = {}
        for o in pakai:
            kurir[o["shipper"]] = kurir.get(o["shipper"], 0) + 1
        status = "akan diproses" if len(pakai) >= MIN_RESI else f"dilewati (< {MIN_RESI} pesanan)"
        log.info("[UJI] Rak %-8s %-14s resi spesial %3d | siap diproses %3d | %s | %s",
                 rak_per_sku.get(sku, "-"), sku, len(resi), len(pakai), status,
                 ", ".join(f"{n} {kur}" for kur, n in sorted(kurir.items())))
        for no, alasan in buang:
            if alasan != "tidak termasuk resi spesial di Excel":
                log.info("        - %s dibuang: %s", no, alasan)
        hilang = set(resi) - {o["salesorder_no"] for o in pakai} - {no for no, _ in buang}
        if hilang:
            log.info("        - %d resi spesial sudah tidak ada di Siap Proses", len(hilang))
        hasil.append({"sku": sku, "pesanan": len(pakai), "status": status})
    return hasil


def proses(k: Klien, resi_per_sku: dict[str, list[str]], folder_label: Path,
           file_riwayat: Path, rak_per_sku: dict[str, str] | None = None,
           kurir: str | None = None) -> list[dict]:
    """Proses SKU sesuai urutan resi_per_sku (urut rak). Tiap hasil berisi Rak, Durasi & detik.
    `kurir`: lihat cari_pesanan()."""
    rak_per_sku = rak_per_sku or {}
    hasil = []
    for n, (sku, resi) in enumerate(resi_per_sku.items(), 1):
        mulai = time.monotonic()
        rak = rak_per_sku.get(sku, "-")
        log.info("=== [%d/%d] Rak %s | SKU %s (%d resi spesial)",
                 n, len(resi_per_sku), rak, sku, len(resi))
        try:
            log.info("  [1-2] Filter pesanan & buat picklist")
            pid, pno, ids, _ = buat_picklist(k, sku, set(resi), kurir)
        except Lewati as e:
            log.info("  Dilewati: %s", e)
            baris = {"SKU": sku, "Catatan": f"Dilewati: {e}"}
        except Exception as e:     # noqa: BLE001 - satu SKU gagal, SKU lain tetap jalan
            log.exception("  GAGAL %s: %s", sku, e)
            baris = {"SKU": sku, "Catatan": f"GAGAL sebelum picklist dibuat: {e}"}
        else:
            log.info("  Picklist %s dibuat, %d pesanan", pno, len(ids))
            baris = {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": sku,
                     "No Picklist": pno, "Total Pesanan": len(ids)}
            try:
                baris = lanjutkan_picklist(k, pid, pno, len(ids), sku, folder_label, tag=TAG_SPESIAL)
            except Exception as e:     # noqa: BLE001
                log.exception("  TERHENTI di %s: %s", pno, e)
                baris["Catatan"] = f"TERHENTI: {e}. Lanjutkan: .\\run.bat --lanjut {pno} --jalankan"

        detik = time.monotonic() - mulai
        baris.update({"Rak": rak, "detik": detik, "Durasi": durasi(detik)})
        if "No Picklist" in baris:
            catat_riwayat(file_riwayat, baris)
        log.info("  Selesai SKU %s dalam %s", sku, baris["Durasi"])
        hasil.append(baris)
    return hasil


def lanjutkan(k: Klien, picklist_no: str, folder_label: Path, file_riwayat: Path) -> dict:
    """Lanjutkan picklist yang prosesnya terhenti (mis. PICK-000154839)."""
    m = re.fullmatch(r"PICK-0*(\d+)", picklist_no.strip().upper())
    if not m:
        raise ProsesError(f"Format nomor picklist tidak dikenal: {picklist_no}")
    p = k.get(f"sales/picklists/{int(m.group(1))}")
    skus = sorted({str(i.get("item_code")) for i in p["items"]})
    sku = "+".join(skus)
    jumlah = len({i["salesorder_id"] for i in p["items"]})
    log.info("=== Lanjutkan %s (SKU %s, %d pesanan)", p["picklist_no"], sku, jumlah)
    mulai = time.monotonic()
    try:
        baris = lanjutkan_picklist(k, p["picklist_id"], p["picklist_no"], jumlah, sku, folder_label)
    except Exception as e:
        catat_riwayat(file_riwayat, {"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "SKU": sku,
                                     "No Picklist": p["picklist_no"], "Total Pesanan": jumlah,
                                     "Catatan": f"TERHENTI lagi: {e}",
                                     "Durasi": durasi(time.monotonic() - mulai)})
        raise
    baris["Durasi"] = durasi(time.monotonic() - mulai)
    catat_riwayat(file_riwayat, baris)
    return baris
