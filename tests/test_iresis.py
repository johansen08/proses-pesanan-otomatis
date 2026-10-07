"""Uji iresis.py + jubelio.ambil_url_faktur dengan requests ditiru (tanpa jaringan).
Respons meniru rekaman sniff 07-10-2026 10:53.

Jalankan:  .venv\Scripts\python tests\test_iresis.py
"""
import sys
import tempfile
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import iresis  # noqa: E402
import jubelio  # noqa: E402

RINGKAS = ("Total Data Terinput: 0 | Dilewati: 3 | Duplikat: 0 | Diupdate: 608 | "
           "Data Tidak Berubah: 14661 | Waktu: 1.5 dtk")


class Resp:
    def __init__(self, status=200, data=None, headers=None, text=""):
        self.status_code, self._data, self.headers, self.text = status, data, headers or {}, text

    def json(self):
        if self._data is None:
            raise ValueError("bukan JSON")
        return self._data


class Sesi:
    """Sesi tiruan: mencatat request, membalas dari antrean per (metode, akhiran url)."""

    def __init__(self, balasan):
        self.balasan, self.log, self.headers = balasan, [], {}

    def _ambil(self, metode, url, kw):
        self.log.append((metode, url, kw))
        for (m, akhir), antre in self.balasan.items():
            if m == metode and url.endswith(akhir):
                x = antre.pop(0) if len(antre) > 1 else antre[0]
                if isinstance(x, Exception):
                    raise x
                return x
        raise AssertionError(f"request tak terduga: {metode} {url}")

    def get(self, url, **kw):
        return self._ambil("GET", url, kw)

    def post(self, url, **kw):
        return self._ambil("POST", url, kw)


def _balasan_normal():
    return {
        ("GET", "/login"): [Resp(200, text="<html>")],
        ("POST", "/auth"): [Resp(303, headers={"Location": "https://192.168.3.37/new-iresis/"})],
        ("POST", "/upload-receipt-action"): [Resp(200, {"code": 201, "message": RINGKAS,
                                              "data": {"token": "tok123", "baris": 15404}})],
        ("GET", "/upload-receipt-progress"): [
            Resp(200, {"code": 200, "data": {"status": "berjalan", "persen": 40}}),
            Resp(200, {"code": 200, "data": {"status": "selesai", "persen": 100,
                                              "hasil": RINGKAS}})],
    }


def _xlsx():
    f = Path(tempfile.mkdtemp()) / "faktur.xlsx"
    f.write_bytes(b"PK\x03\x04isi")
    return f


def uji_alur_normal():
    sesi = Sesi(_balasan_normal())
    s = iresis.login("bot", "rahasia", sesi=sesi)
    form = [k for m, u, k in sesi.log if u.endswith("/auth")][0]["data"]
    assert form == {"nama_komputer": "", "username": "bot", "password": "rahasia",
                    "nama_pk": "SRV-1", "status_performa": "NORMAL"}, form
    hasil = iresis.upload_faktur(s, _xlsx())
    up = [k for m, u, k in sesi.log if u.endswith("/upload-receipt-action")][0]
    assert list(up["files"]) == ["receiptFile"], up["files"]
    assert up["headers"]["X-Requested-With"] == "XMLHttpRequest"
    ringkas = iresis.tunggu_selesai(s, hasil["data"]["token"], tidur=lambda s_: None)
    assert ringkas == RINGKAS, ringkas
    prog = [k for m, u, k in sesi.log if u.endswith("-progress")]
    assert len(prog) == 2 and prog[0]["params"]["token"] == "tok123"


def uji_login_gagal():
    for balasan in (Resp(200, text="<html>login lagi"),
                    Resp(303, headers={"Location": "https://x/new-iresis/login"})):
        b = _balasan_normal()
        b[("POST", "/auth")] = [balasan]
        try:
            iresis.login("bot", "salah", sesi=Sesi(b))
        except iresis.IresisError as e:
            assert "Login IRESIS gagal" in str(e)
        else:
            raise AssertionError("login gagal harus IresisError")


def uji_upload_ditolak_dan_bukan_json():
    s = Sesi({("POST", "/upload-receipt-action"): [Resp(200, {"code": 400, "message": "File salah"})]})
    try:
        iresis.upload_faktur(s, _xlsx())
    except iresis.IresisError as e:
        assert "File salah" in str(e)
    else:
        raise AssertionError
    s = Sesi({("POST", "/upload-receipt-action"): [Resp(200, None, text="<html>login")]})
    try:
        iresis.upload_faktur(s, _xlsx())
    except iresis.IresisError as e:
        assert "bukan JSON" in str(e)
    else:
        raise AssertionError


def uji_progres_tak_selesai():
    s = Sesi({("GET", "/upload-receipt-progress"): [
        Resp(200, {"code": 200, "data": {"status": "berjalan", "persen": 10}})]})
    try:
        iresis.tunggu_selesai(s, "t", maks_tunggu=-1, tidur=lambda s_: None)
    except iresis.IresisError as e:
        assert "belum selesai" in str(e)
    else:
        raise AssertionError


def uji_server_mati_diulang():
    gagal = requests.exceptions.ConnectionError("mati")
    sesi = Sesi({("GET", "/login"): [gagal, Resp(200)], ("POST", "/auth"): [
        Resp(303, headers={"Location": "/new-iresis/"})]})
    asli = iresis.time.sleep
    iresis.time.sleep = lambda s_: None
    try:
        iresis.login("bot", "x", sesi=sesi)       # gagal sekali lalu berhasil
        sesi = Sesi({("GET", "/login"): [gagal]})
        try:
            iresis.login("bot", "x", sesi=sesi)
        except iresis.IresisError as e:
            assert "tidak terjangkau" in str(e)
        else:
            raise AssertionError
        assert len(sesi.log) == iresis.MAKS_COBA_KONEKSI
    finally:
        iresis.time.sleep = asli


def uji_url_faktur():
    s = Sesi({("GET", "/date-range/"): [Resp(200, {"status": "ok", "url": "https://r/?&token=T"})]})
    jubelio._sesi_bersama = s
    try:
        url = jubelio.ambil_url_faktur("TOK", date(2026, 10, 6), date(2026, 10, 7))
    finally:
        jubelio._sesi_bersama = None
    assert url == "https://r/?&token=T"
    k = s.log[0][2]
    assert k["params"]["date_from"] == "Tue Oct 06 2026 00:00:00 GMT+0700 (Western Indonesia Time)"
    assert k["params"]["date_to"] == "Wed Oct 07 2026 23:59:59 GMT+0700 (Western Indonesia Time)"
    assert k["params"]["reference"] == "invoice" and k["headers"]["authorization"] == "TOK"


def uji_url_pesanan():
    s = Sesi({("GET", "/date-range/"): [Resp(200, {"status": "ok", "url": "https://r/?&token=T"})]})
    jubelio._sesi_bersama = s
    try:
        jubelio.ambil_url_pesanan("TOK", date(2026, 10, 4), date(2026, 10, 7))
    finally:
        jubelio._sesi_bersama = None
    k = s.log[0][2]
    assert k["params"]["reference"] == "order"
    assert k["params"]["date_from"] == "Sun Oct 04 2026 00:00:00 GMT+0700 (Western Indonesia Time)"


if __name__ == "__main__":
    for nama, fn in sorted(globals().items()):
        if nama.startswith("uji_"):
            fn()
            print("OK", nama)
