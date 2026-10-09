"""Upload Excel 'Daftar Penjualan Faktur' Jubelio ke IRESIS (menu Upload Resi), tanpa browser.

Dulu langkah MANUAL tim setelah proses pesanan selesai. Alur (berdasarkan rekaman sniff
07-10-2026 10:53, server lokal Apache/PHP - hanya terjangkau dari LAN kantor):
  1. GET  <IRESIS_URL>/login                          -> cookie siresi_session
  2. POST <IRESIS_URL>/auth  (form-urlencoded)        -> 303 ke <IRESIS_URL>/ kalau berhasil
        nama_komputer=&username=..&password=..&nama_pk=SRV-1&status_performa=NORMAL
  3. POST <IRESIS_URL>/receipt/upload-receipt-action  (multipart, field file `receiptFile`,
        header X-Requested-With: XMLHttpRequest)
        -> {"code":201,"message":"Total Data Terinput: 0 | Dilewati: 3 | Duplikat: 0 |
            Diupdate: 608 | Data Tidak Berubah: 14661 | Waktu: 1.5 dtk","data":{"token":..}}
  4. GET  <IRESIS_URL>/receipt/upload-receipt-progress?token=..
        -> {"code":200,"data":{"status":"selesai","persen":100,...}}
Upload ulang file yang sama aman: IRESIS melewati baris yang tidak berubah.

Laporan Total Picklist (sniff 09-10-2026 08:12, menu Laporan > tab "Laporan Total Picklist"):
  POST <IRESIS_URL>/report/get-receipt-report-data-tab1  (DataTables server-side, form-urlencoded:
        draw, start, length, order[0][column]=2, start_date=YYYY-MM-DD HH:MM:SS, end_date=..)
        -> {"recordsTotal":92,"data":[["1.","2026-10-09","158725","30"],...],"grandTotal":"3352"}
     tiap baris = [no, tanggal, nomor picklist (angka), total resi]. Dipakai mengisi kolom SCAN
     di PICKLIST.xlsx (rekap_master_excel.isi_scan).

Konfigurasi lewat .env: IRESIS_URL (bawaan https://192.168.3.37/new-iresis), IRESIS_USERNAME,
IRESIS_PASSWORD, opsional IRESIS_NAMA_PK (bawaan SRV-1), IRESIS_CA_BUNDLE (path sertifikat
server; kalau kosong verifikasi SSL dimatikan karena sertifikat server lokal self-signed).
"""
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path

import requests
import urllib3

log = logging.getLogger("sku-spesial")

URL_BAWAAN = "https://192.168.3.37/new-iresis"
NAMA_PK_BAWAAN = "SRV-1"
NAMA_FIELD_FILE = "receiptFile"
MAKS_COBA_KONEKSI = 3
JEDA_COBA_KONEKSI_S = 10
MAKS_TUNGGU_PROGRES_S = 300
JEDA_PROGRES_S = 2
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36")


class IresisError(RuntimeError):
    pass


def _url_dasar() -> str:
    return os.environ.get("IRESIS_URL", URL_BAWAAN).rstrip("/")


def _verify():
    """Path CA bundle kalau diisi, selain itu False (sertifikat self-signed server lokal)."""
    ca = os.environ.get("IRESIS_CA_BUNDLE")
    if ca:
        return ca
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return False


def _kirim(fn, *a, tidur=time.sleep, **kw) -> requests.Response:
    """Ulangi kalau koneksi ke server IRESIS putus/timeout (server bisa sedang restart)."""
    for coba in range(1, MAKS_COBA_KONEKSI + 1):
        try:
            return fn(*a, verify=_verify(), **kw)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if coba == MAKS_COBA_KONEKSI:
                raise IresisError(f"Server IRESIS tidak terjangkau ({_url_dasar()}): {e}") from e
            log.warning("IRESIS: koneksi gagal (%s), coba lagi %d/%d", e, coba, MAKS_COBA_KONEKSI)
            tidur(JEDA_COBA_KONEKSI_S)


def login(username: str, password: str, nama_pk: str | None = None, timeout: int = 30,
          sesi: requests.Session | None = None) -> requests.Session:
    """Login ke IRESIS; mengembalikan Session yang sudah memegang cookie siresi_session."""
    sesi = sesi or requests.Session()
    sesi.headers["User-Agent"] = USER_AGENT
    dasar = _url_dasar()
    _kirim(sesi.get, f"{dasar}/login", timeout=timeout)
    r = _kirim(sesi.post, f"{dasar}/auth", timeout=timeout, allow_redirects=False,
               headers={"Referer": f"{dasar}/login"},
               data={"nama_komputer": "", "username": username, "password": password,
                     "nama_pk": nama_pk or os.environ.get("IRESIS_NAMA_PK", NAMA_PK_BAWAAN),
                     "status_performa": "NORMAL"})
    # berhasil = redirect ke halaman utama; gagal = halaman login ditampilkan lagi / redirect
    # kembali ke /login
    lokasi = r.headers.get("Location", "")
    if r.status_code not in (301, 302, 303, 307) or lokasi.rstrip("/").endswith("login"):
        raise IresisError(f"Login IRESIS gagal (HTTP {r.status_code}) - cek IRESIS_USERNAME/"
                          "IRESIS_PASSWORD di .env")
    return sesi


def _json(r: requests.Response, apa: str) -> dict:
    if r.status_code != 200:
        raise IresisError(f"{apa} gagal (HTTP {r.status_code}): {r.text[:300]}")
    try:
        return r.json()
    except ValueError as e:
        # biasanya halaman login (sesi habis) atau error PHP, bukan JSON
        raise IresisError(f"{apa}: respons bukan JSON: {r.text[:200]!r}") from e


def upload_faktur(sesi: requests.Session, file: Path, timeout: int = 300) -> dict:
    """Upload `file` (.xlsx) ke menu Upload Resi. Mengembalikan data JSON respons
    ({'code', 'message', 'data': {'token', 'baris', ...}})."""
    dasar = _url_dasar()
    with open(file, "rb") as f:
        r = _kirim(sesi.post, f"{dasar}/receipt/upload-receipt-action", timeout=timeout,
                   headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{dasar}/"},
                   data={"token": ""},
                   files={NAMA_FIELD_FILE: (file.name, f,
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    data = _json(r, "Upload faktur ke IRESIS")
    if data.get("code") not in (200, 201):
        raise IresisError(f"Upload ditolak IRESIS (code {data.get('code')}): "
                          f"{data.get('message')}")
    return data


def tunggu_selesai(sesi: requests.Session, token: str, timeout: int = 30,
                   maks_tunggu: float = MAKS_TUNGGU_PROGRES_S, tidur=time.sleep) -> str:
    """Poll progres sampai status 'selesai'. Mengembalikan ringkasan hasil (teks)."""
    dasar = _url_dasar()
    mulai = time.monotonic()
    while True:
        r = _kirim(sesi.get, f"{dasar}/receipt/upload-receipt-progress", timeout=timeout,
                   params={"token": token, "_": int(time.time() * 1000)},
                   headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{dasar}/"})
        data = _json(r, "Cek progres upload IRESIS")
        d = data.get("data") or {}
        status = d.get("status")
        if status == "selesai":
            return str(d.get("hasil") or d.get("pesan") or data.get("message") or "")
        if status in ("gagal", "error"):
            raise IresisError(f"Proses upload di IRESIS gagal: {d.get('pesan') or d}")
        if time.monotonic() - mulai > maks_tunggu:
            raise IresisError(f"Proses upload IRESIS belum selesai setelah {maks_tunggu:.0f} "
                              f"detik (status terakhir: {status}, {d.get('persen')}%)")
        tidur(JEDA_PROGRES_S)


def unggah(file: Path, username: str, password: str) -> str:
    """Alur lengkap: login -> upload -> tunggu selesai. Mengembalikan ringkasan hasil."""
    sesi = login(username, password)
    hasil = upload_faktur(sesi, file)
    token = (hasil.get("data") or {}).get("token")
    if not token:
        return str(hasil.get("message", ""))   # tanpa token tidak ada progres untuk dipantau
    return tunggu_selesai(sesi, token) or str(hasil.get("message", ""))


def ambil_total_picklist(sesi: requests.Session, dari: date, sampai: datetime,
                         timeout: int = 60, per_halaman: int = 500) -> dict[int, int]:
    """Laporan Total Picklist IRESIS -> {nomor picklist (angka): total resi}, untuk picklist yang
    tanggalnya di rentang `dari` 00:00 s.d. `sampai`."""
    dasar = _url_dasar()
    hasil: dict[int, int] = {}
    mulai = 0
    while True:
        form = {"draw": mulai // per_halaman + 1, "order[0][column]": 2, "order[0][dir]": "asc",
                "start": mulai, "length": per_halaman, "search[value]": "",
                "search[regex]": "false",
                "start_date": f"{dari:%Y-%m-%d} 00:00:00",
                "end_date": f"{sampai:%Y-%m-%d %H:%M:%S}"}
        r = _kirim(sesi.post, f"{dasar}/report/get-receipt-report-data-tab1", timeout=timeout,
                   headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{dasar}/"},
                   data=form)
        data = _json(r, "Ambil laporan total picklist IRESIS")
        baris = data.get("data")
        if not isinstance(baris, list):
            raise IresisError(f"Laporan total picklist: format tak dikenal: {str(data)[:200]}")
        for b in baris:
            try:
                hasil[int(b[2])] = int(b[3])
            except (IndexError, ValueError, TypeError) as e:
                raise IresisError(f"Laporan total picklist: baris tak dikenal {b!r}") from e
        mulai += per_halaman
        if not baris or mulai >= int(data.get("recordsFiltered") or 0):
            return hasil
