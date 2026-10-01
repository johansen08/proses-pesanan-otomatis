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
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

API = "https://open.jubelio.com/core-api"
URL_LOGIN = f"{API}/login"
URL_LAPORAN = f"{API}/reports/sales-list/ready-to-pick-list/"
URL_PESANAN = f"{API}/wms/sales/v2/orders/ready-to-process/"
MAKS_HALAMAN = 400          # pengaman: 400 x 25 = 10.000 pesanan

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


def _header(token: str | None = None) -> dict:
    h = dict(HEADER_DASAR, **{"x-jube-reqid": str(uuid.uuid4())})
    if token:
        h["authorization"] = token
    return h


def login(email: str, password: str, timeout: int = 60) -> str:
    body = {"email": email, "password": password,
            "fid": os.environ.get("JUBELIO_FID", FID_DEFAULT)}
    r = requests.post(URL_LOGIN, json=body, timeout=timeout,
                      headers={**_header(), **HEADER_LOGIN_TAMBAHAN})
    if r.status_code != 200:
        raise JubelioError(f"Login gagal (HTTP {r.status_code}): {_pesan(r)}")
    token = r.json().get("token")
    if not token:
        raise JubelioError("Login berhasil tetapi token tidak ada di respons")
    return token


def ambil_url_laporan(token: str, timeout: int = 60) -> str:
    r = requests.get(URL_LAPORAN, params={"tz": "Asia/Jakarta"},
                     headers=_header(token), timeout=timeout)
    if r.status_code != 200:
        raise JubelioError(f"Gagal minta laporan (HTTP {r.status_code}): {_pesan(r)}")
    data = r.json()
    if data.get("status") != "ok" or not data.get("url"):
        raise JubelioError(f"Respons laporan tidak valid: status={data.get('status')}")
    return data["url"]


def _halaman_pesanan(sesi: requests.Session, token: str, page: int, q: str = "",
                     page_size: int = 25, timeout: int = 60) -> dict:
    r = sesi.get(URL_PESANAN, headers=_header(token), timeout=timeout, params={
        "page": page, "q": q, "sort_by": "transaction_date",
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
    with requests.Session() as sesi:
        page, total = 1, None
        while page <= MAKS_HALAMAN:
            j = _halaman_pesanan(sesi, token, page)
            data = j.get("data") or []
            total = j.get("totalCount", total)
            for o in data:
                nilai[o["salesorder_no"]] = _angka(o.get("grand_total"))
            if not data or (total is not None and page * 25 >= int(total)):
                break
            page += 1

        for no in sorted(dicari - nilai.keys()):
            for o in _halaman_pesanan(sesi, token, 1, q=no).get("data") or []:
                if o.get("salesorder_no") == no:
                    nilai[no] = _angka(o.get("grand_total"))
    return nilai


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


def unduh_excel(token: str, url_laporan: str, folder: Path, timeout: int = 180) -> Path:
    r = requests.get(url_excel(url_laporan), timeout=timeout,
                     cookies={"JB_OMNI_ACCESS_TOKEN": token},
                     headers={"User-Agent": USER_AGENT, "Referer": "https://v2.jubelio.com/"})
    if r.status_code != 200:
        raise JubelioError(f"Gagal download Excel (HTTP {r.status_code}): {r.text[:300]}")
    if not r.content.startswith(b"PK"):        # file .xlsx selalu diawali 'PK' (zip)
        raise JubelioError("Respons download bukan file Excel "
                           f"(content-type: {r.headers.get('content-type')})")

    folder.mkdir(parents=True, exist_ok=True)
    tujuan = folder / f"laporan_siap_proses_{datetime.now():%Y-%m-%d_%H%M%S}.xlsx"
    tujuan.write_bytes(r.content)
    return tujuan
