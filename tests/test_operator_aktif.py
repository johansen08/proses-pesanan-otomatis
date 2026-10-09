"""Uji operator_aktif.py (daftar operator & operator aktif di data/operator.json) dan
penerapannya di server_ui (/api/operator) - tanpa menyentuh data/operator.json sungguhan.

Jalankan:  .venv\\Scripts\\python tests\\test_operator_aktif.py
"""
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import operator_aktif as oa  # noqa: E402
import server_ui as su  # noqa: E402


def uji_bawaan_tambah_ganti_dan_validasi():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(oa, "FILE", Path(tmp) / "operator.json"):
        assert oa.ambil_aktif() == "PUTRI"
        assert oa.ambil_daftar() == ["PUTRI", "ALFIANA", "SAHRUL", "DENADA", "SELVI"]
        d = oa.tambah("  budi   santoso ")
        assert d["daftar"][-1] == "BUDI SANTOSO" and d["aktif"] == "PUTRI"
        for salah in ("", "   ", None, 5, "putri", "x" * 31):
            try:
                oa.tambah(salah)
            except oa.OperatorError:
                pass
            else:
                raise AssertionError(f"harus ditolak: {salah!r}")
        assert oa.set_aktif("selvi")["aktif"] == "SELVI" and oa.ambil_aktif() == "SELVI"
        try:
            oa.set_aktif("TIDAK ADA")
        except oa.OperatorError:
            pass
        else:
            raise AssertionError("operator di luar daftar harus ditolak")
        assert oa.ambil_aktif() == "SELVI"
        # file rusak / aktif tidak ada di daftar -> tetap aman
        oa.FILE.write_text("{rusak", encoding="utf-8")
        assert oa.ambil_aktif() == "PUTRI"
        oa.FILE.write_text(json.dumps({"aktif": "X", "daftar": ["a", "A", "b"]}), encoding="utf-8")
        assert oa.info() == {"aktif": "A", "daftar": ["A", "B"]}
        assert not list(Path(tmp).glob("*.tmp"))
    print("  operator_aktif: bawaan, tambah, ganti, validasi, file rusak")


def _panggil(port, path, data=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="POST" if data is not None else "GET",
                                 data=None if data is None else json.dumps(data).encode())
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def uji_api_operator_dan_kunci_saat_proses_berjalan():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(oa, "FILE", Path(tmp) / "operator.json"):
        server = ThreadingHTTPServer(("127.0.0.1", 0), su.Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            kode, d = _panggil(port, "/api/operator")
            assert kode == 200 and d["aktif"] == "PUTRI" and len(d["daftar"]) == 5 and d["terkunci"] is False
            assert _panggil(port, "/api/operator", {"aksi": "tambah", "nama": "budi"})[1]["daftar"][-1] == "BUDI"
            assert _panggil(port, "/api/operator", {"aksi": "tambah", "nama": "budi"})[0] == 400
            assert _panggil(port, "/api/operator", {"aksi": "aktif", "nama": "Sahrul"})[1]["aktif"] == "SAHRUL"
            assert _panggil(port, "/api/operator", {"aksi": "aktif", "nama": "zzz"})[0] == 400
            assert _panggil(port, "/api/operator", {"aksi": "hapus", "nama": "BUDI"})[0] == 400
            # proses harian berjalan -> ganti ditolak (tambah tetap boleh)
            with mock.patch.object(su.jh, "keadaan", return_value={"status": "jalan"}):
                assert _panggil(port, "/api/operator")[1]["terkunci"] is True
                assert _panggil(port, "/api/operator", {"aksi": "aktif", "nama": "SELVI"})[0] == 409
                assert _panggil(port, "/api/operator", {"aksi": "tambah", "nama": "rina"})[0] == 200
            assert oa.ambil_aktif() == "SAHRUL"
        finally:
            server.shutdown()
    print("  server_ui: /api/operator tambah/ganti/validasi/kunci saat proses berjalan")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
