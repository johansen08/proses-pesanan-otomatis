"""Download Excel 'Laporan Siap Proses' dan nilai pesanan dari Jubelio (tanpa browser).

Alur (berdasarkan rekaman sniff 26-09-2026 08:18):
  1. POST open.jubelio.com/core-api/login                      -> token login
  2. GET  open.jubelio.com/core-api/reports/sales-list/
          ready-to-pick-list/?tz=Asia/Jakarta                   -> https://report-prod.jubelio.com/?&token=...
  3. GET  report-prod.jubelio.com/xlsx/?&token=...              -> file .xlsx
          (path "/" diganti "/xlsx/"; cookie JB_OMNI_ACCESS_TOKEN = token login)
  4. GET  open.jubelio.com/core-api/wms/sales/v2/orders/ready-to-process/
                                                                -> grand_total per pesanan
                                                                   (Excel tidak punya kolom nilai)

Laporan "Daftar Penjualan Faktur" (sniff 07-10-2026 10:53, lihat ambil_url_faktur() &
iresis.py): sama dengan langkah 2-3 di atas, tapi endpoint
GET open.jubelio.com/core-api/reports/sales-list/date-range/?date_from=..&date_to=..&
reference=invoice&hpp=true&tz=Asia/Jakarta

Recheck stok (berdasarkan rekaman sniff 05-10-2026 15:17, lihat ambil_stok_kosong()/
recheck_stok() & main.py --recheck-stok):
  1. GET open.jubelio.com/core-api/wms/sales/v2/orders/empty-stock/   -> daftar pesanan
                                                                          stok kosong
  2. GET open.jubelio.com/core-api/wms/sales/orders/recheck-stock/    -> picu cek ulang
                                                                          (berlaku utk SEMUA
                                                                          pesanan di atas)
"""
import logging
import os
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

log = logging.getLogger("sku-spesial")

API = "https://open.jubelio.com/core-api"
HOST_REPORT = ("report.jubelio.com", "report-prod.jubelio.com")   # urutan coba: utama, cadangan
URL_LOGIN = f"{API}/login"
URL_LAPORAN = f"{API}/reports/sales-list/ready-to-pick-list/"
URL_FAKTUR = f"{API}/reports/sales-list/date-range/"
URL_PESANAN = f"{API}/wms/sales/v2/orders/ready-to-process/"
URL_STOK_KOSONG = f"{API}/wms/sales/v2/orders/empty-stock/"
URL_RECHECK_STOK = f"{API}/wms/sales/orders/recheck-stock/"
UKURAN_HALAMAN_PESANAN = 200  # maksimum yang didukung API Jubelio - kurangi jumlah request
MAKS_HALAMAN = 50          # pengaman: 50 x 200 = 10.000 pesanan
# Jumlah No pesanan yang dicari satu-satu (lewat q=...) bersamaan di ambil_nilai_pesanan() -
# sama pola dengan proses_label.MAKS_WORKER_PARALEL.
MAKS_WORKER_PARALEL = 5

# Jubelio membalas HTTP 429 (Too Many Requests) kalau request terlalu rapat - kejadian
# 03-10-2026: setelah ~26 picklist SKU spesial berturut-turut, 2 SKU terakhir gagal 429, lalu
# TIPE 5/6 (reguler) langsung gagal total di ambil_nilai_pesanan() karena saat itu belum ada
# retry sama sekali untuk 429 (beda dengan putus koneksi yang sudah ditangani _kirim() di
# proses_label.py - lihat MAKS_COBA_KONEKSI). Coba ulang dengan jeda (menghormati header
# Retry-After kalau Jubelio mengirimnya) sebelum menyerah.
MAKS_COBA_429 = 5
JEDA_COBA_429_S = 15

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
HEADER_DASAR = {
    "accept": "application/json",
    "Origin": "https://v2.jubelio.com",
    "Referer": "https://v2.jubelio.com/",
    "User-Agent": USER_AGENT,
}
# Header & fid yang dikirim web Jubelio saat login (diambil dari sniff).
HEADER_LOGIN_TAMBAHAN = {
    "x-login-check": "true",
    "q2xpzw50lvbsyxrmb3jt": os.environ.get(
        "JUBELIO_CLIENT_KEY", "R2GiTbWOkwOJFkSQjVDSqn8T0yqIXJAsEHXEZR2ox8I"),
}
FID_DEFAULT = "cb069442f28fc54deb889b66d930d7e6"


class JubelioError(RuntimeError):
    pass


_sesi_bersama: requests.Session | None = None


def _sesi() -> requests.Session:
    """Session requests dibagi semua fungsi di modul ini supaya koneksi TCP/TLS ke
    open.jubelio.com/report-prod.jubelio.com dipakai ulang antar panggilan berurutan dalam
    1 proses (mis. login() -> ambil_url_laporan() -> unduh_excel(), atau ambil_stok_kosong()
    -> recheck_stok() -> ambil_stok_kosong() lagi) - bukan buka koneksi baru tiap panggilan
    requests.get/post module-level."""
    global _sesi_bersama
    if _sesi_bersama is None:
        _sesi_bersama = requests.Session()
    return _sesi_bersama


def _jeda_retry_after(r: requests.Response, bawaan: float) -> float:
    """Header Retry-After Jubelio berupa detik (bukan HTTP-date) - pakai itu kalau valid,
    kalau tidak pakai jeda bawaan. Ditambah jitter (+0-20%) supaya beberapa worker paralel
    (lihat MAKS_WORKER_PARALEL di proses_label.py) yang kena 429 bersamaan tidak retry
    serempak di detik yang sama persis (thundering herd)."""
    try:
        jeda = max(float(r.headers.get("Retry-After", "")), 0)
    except ValueError:
        jeda = bawaan
    return jeda + random.uniform(0, jeda * 0.2)


def _kirim_dengan_retry429(fn, *a, tidur=time.sleep, **kw) -> requests.Response:
    """Panggil `fn` (requests.get/post), ulangi kalau Jubelio membalas HTTP 429 - lihat
    MAKS_COBA_429."""
    r = None
    for coba in range(1, MAKS_COBA_429 + 1):
        r = fn(*a, **kw)
        if r.status_code != 429 or coba == MAKS_COBA_429:
            return r
        tidur(_jeda_retry_after(r, JEDA_COBA_429_S * coba))
    return r


def _header(token: str | None = None) -> dict:
    h = dict(HEADER_DASAR, **{"x-jube-reqid": str(uuid.uuid4())})
    if token:
        h["authorization"] = token
    return h


def login(email: str, password: str, timeout: int = 60) -> str:
    body = {"email": email, "password": password,
            "fid": os.environ.get("JUBELIO_FID", FID_DEFAULT)}
    r = _kirim_dengan_retry429(_sesi().post, URL_LOGIN, json=body, timeout=timeout,
                               headers={**_header(), **HEADER_LOGIN_TAMBAHAN})
    if r.status_code != 200:
        raise JubelioError(f"Login gagal (HTTP {r.status_code}): {_pesan(r)}")
    token = r.json().get("token")
    if not token:
        raise JubelioError("Login berhasil tetapi token tidak ada di respons")
    return token


def ambil_url_laporan(token: str, timeout: int = 60) -> str:
    r = _kirim_dengan_retry429(_sesi().get, URL_LAPORAN, params={"tz": "Asia/Jakarta"},
                               headers=_header(token), timeout=timeout)
    if r.status_code != 200:
        raise JubelioError(f"Gagal minta laporan (HTTP {r.status_code}): {_pesan(r)}")
    data = r.json()
    if data.get("status") != "ok" or not data.get("url"):
        raise JubelioError(f"Respons laporan tidak valid: status={data.get('status')}")
    return data["url"]


def ambil_url_faktur(token: str, dari: date, sampai: date, timeout: int = 60) -> str:
    """URL laporan 'Daftar Penjualan Faktur' (kolom picklist/resi/status ship) untuk rentang
    tanggal `dari`..`sampai` (WIB, inklusif) - diunggah ke IRESIS oleh iresis.py. Format
    tanggal meniru web Jubelio (string Date JavaScript)."""
    def _js(d: date, jam: str) -> str:
        return f"{d:%a %b %d %Y} {jam} GMT+0700 (Western Indonesia Time)"

    r = _kirim_dengan_retry429(
        _sesi().get, URL_FAKTUR, headers=_header(token), timeout=timeout,
        params={"date_from": _js(dari, "00:00:00"), "date_to": _js(sampai, "23:59:59"),
                "reference": "invoice", "hpp": "true", "tz": "Asia/Jakarta"})
    if r.status_code != 200:
        raise JubelioError(f"Gagal minta laporan faktur (HTTP {r.status_code}): {_pesan(r)}")
    data = r.json()
    if data.get("status") != "ok" or not data.get("url"):
        raise JubelioError(f"Respons laporan faktur tidak valid: status={data.get('status')}")
    return data["url"]


def _halaman_pesanan(sesi: requests.Session, token: str, page: int, q: str = "",
                     page_size: int = UKURAN_HALAMAN_PESANAN, timeout: int = 60) -> dict:
    r = _kirim_dengan_retry429(sesi.get, URL_PESANAN, headers=_header(token), timeout=timeout,
                               params={"page": page, "q": q, "sort_by": "transaction_date",
                                       "page_size": page_size, "sort_direction": "DESC"})
    if r.status_code != 200:
        raise JubelioError(f"Gagal ambil daftar pesanan (HTTP {r.status_code}): {_pesan(r)}")
    return r.json()


def _angka(v) -> float:
    """None/"" (field grand_total kosong di API) dianggap 0 - sama dengan pesanan
    kreator bernilai 0, bukan error. Lihat proses_label._angka (aturan yang sama)."""
    return float(v) if v not in (None, "") else 0.0


def ambil_nilai_pesanan(token: str, dicari: set[str]) -> dict[str, float]:
    """Ambil grand_total per No pesanan dari daftar 'Siap Proses'.

    Semua halaman diambil dulu; No pesanan di `dicari` yang belum ketemu
    dicari satu per satu lewat parameter q. No pesanan yang sama sekali tidak
    ketemu di API (bukan field grand_total-nya yang kosong, tapi pesanannya
    sendiri tidak ada di hasil) tidak masuk dict ini - lihat sku_spesial.hitung_sku_spesial
    yang mengeluarkannya lewat nilai.notna().
    """
    nilai: dict[str, float] = {}
    sesi = _sesi()
    page, total = 1, None
    while page <= MAKS_HALAMAN:
        j = _halaman_pesanan(sesi, token, page)
        data = j.get("data") or []
        total = j.get("totalCount", total)
        for o in data:
            nilai[o["salesorder_no"]] = _angka(o.get("grand_total"))
        if not data or (total is not None and page * UKURAN_HALAMAN_PESANAN >= int(total)):
            break
        page += 1

    belum = sorted(dicari - nilai.keys())
    if belum:
        def _cari_satu(no: str) -> tuple[str, float | None]:
            for o in _halaman_pesanan(sesi, token, 1, q=no).get("data") or []:
                if o.get("salesorder_no") == no:
                    return no, _angka(o.get("grand_total"))
            return no, None

        with ThreadPoolExecutor(max_workers=min(MAKS_WORKER_PARALEL, len(belum))) as ex:
            for no, v in ex.map(_cari_satu, belum):
                if v is not None:
                    nilai[no] = v
    return nilai


def ambil_stok_kosong(token: str, timeout: int = 60) -> list[dict]:
    """Ambil daftar pesanan yang berstatus EMPTY_STOCK (stok kosong saat pembuatan picklist
    sebelumnya - tombol "Stok Kosong" di web, lihat rekaman sniff 05-10-2026 15:17). Bentuk
    tiap pesanan sama dengan _halaman_pesanan()/ambil_nilai_pesanan() (salesorder_no, dst)."""
    hasil: list[dict] = []
    sesi = _sesi()
    page, total = 1, None
    while page <= MAKS_HALAMAN:
        r = _kirim_dengan_retry429(
            sesi.get, URL_STOK_KOSONG, headers=_header(token), timeout=timeout,
            params={"page": page, "q": "", "sort_by": "transaction_date",
                    "page_size": UKURAN_HALAMAN_PESANAN, "sort_direction": "DESC"})
        if r.status_code != 200:
            raise JubelioError(f"Gagal ambil daftar stok kosong (HTTP {r.status_code}): {_pesan(r)}")
        j = r.json()
        data = j.get("data") or []
        hasil.extend(data)
        total = j.get("totalCount", total)
        if not data or (total is not None and page * UKURAN_HALAMAN_PESANAN >= int(total)):
            break
        page += 1
    return hasil


def recheck_stok(token: str, timeout: int = 60) -> None:
    """Picu Jubelio mengecek ulang stok SEMUA pesanan yang berstatus EMPTY_STOCK sekaligus
    (tombol "Recheck Stok" di web) - GET tanpa body/parameter, bukan per-pesanan (lihat
    rekaman sniff 05-10-2026 15:17: dipanggil sekali, langsung mengosongkan daftar
    stok kosong yang sebelumnya berisi 15 pesanan)."""
    r = _kirim_dengan_retry429(_sesi().get, URL_RECHECK_STOK, headers=_header(token),
                               timeout=timeout)
    if r.status_code != 200:
        raise JubelioError(f"Gagal recheck stok (HTTP {r.status_code}): {_pesan(r)}")
    if r.json().get("status") != "ok":
        raise JubelioError(f"Respons recheck stok tidak valid: {_pesan(r)}")


def _pesan(r: requests.Response) -> str:
    try:
        j = r.json()
        if not isinstance(j, dict):
            return str(j)[:300]
        # pada error 500 Jubelio, alasan sebenarnya ada di "code"
        bagian = [str(j[k]) for k in ("message", "code", "error") if j.get(k)]
        return " | ".join(bagian or [str(j)])[:500]
    except ValueError:
        return r.text[:300]


def url_excel(url_laporan: str) -> str:
    """https://report-prod.jubelio.com/?&token=X -> https://report-prod.jubelio.com/xlsx/?&token=X"""
    u = urlsplit(url_laporan)
    return urlunsplit((u.scheme, u.netloc, "/xlsx/", u.query, ""))


def unduh_excel(token: str, url_laporan: str, folder: Path, timeout: int = 180,
                awalan: str = "laporan_siap_proses") -> Path:
    # report.jubelio.com lebih stabil -> dicoba dulu; report-prod.jubelio.com (host bawaan URL
    # dari API) sebagai cadangan kalau gagal/bukan Excel
    url = urlsplit(url_excel(url_laporan))
    galat = None
    for host in HOST_REPORT:
        try:
            r = _kirim_dengan_retry429(
                _sesi().get, urlunsplit(url._replace(netloc=host)), timeout=timeout,
                cookies={"JB_OMNI_ACCESS_TOKEN": token},
                headers={"User-Agent": USER_AGENT, "Referer": "https://v2.jubelio.com/"})
        except requests.exceptions.RequestException as e:
            galat = JubelioError(f"Gagal download Excel dari {host}: {e}")
            continue
        if r.status_code != 200:
            galat = JubelioError(f"Gagal download Excel (HTTP {r.status_code}): {r.text[:300]}")
        elif not r.content.startswith(b"PK"):    # file .xlsx selalu diawali 'PK' (zip)
            galat = JubelioError("Respons download bukan file Excel "
                                 f"(content-type: {r.headers.get('content-type')})")
        else:
            galat = None
            break
        log.warning("%s (%s)%s", galat, host,
                    ", coba host cadangan" if host != HOST_REPORT[-1] else "")
    if galat:
        raise galat

    folder.mkdir(parents=True, exist_ok=True)
    tujuan = folder / f"{awalan}_{datetime.now():%Y-%m-%d_%H%M%S}.xlsx"
    tujuan.write_bytes(r.content)
    return tujuan
