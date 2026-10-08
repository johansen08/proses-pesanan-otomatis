"""Uji server_ui.py (server lokal UI desktop menu Cetak) - tanpa printer & tanpa mencetak:
folder label sementara, dan subprocess print_spesial.py ditiru.

Jalankan:  .venv\\Scripts\\python tests\\test_server_ui.py
"""
import json
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import print_spesial as ps  # noqa: E402
import server_ui as su  # noqa: E402


def _buat(folder: Path, *nama: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for n in nama:
        (folder / n).write_bytes(b"%PDF-1.4" + b"x" * 2048)


def _panggil(port, path, data=None, tipe="application/json", host=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="POST" if data is not None else "GET",
                                 data=None if data is None else (json.dumps(data) if tipe == "application/json" else data).encode())
    if data is not None:
        req.add_header("Content-Type", tipe)
    if host:
        req.add_header("Host", host)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def uji_server_ui_sesi_cetak_dan_penjagaan():
    hari_ini = date.today()
    kemarin = (hari_ini - timedelta(days=1)).isoformat()
    lama = (hari_ini - timedelta(days=5)).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        log_dir = Path(tmp) / "logs"
        a = "PICK-000000001_SPESIAL_A_x.pdf"
        b = "PICK-000000002_1QTY-REGULER-2A_x.pdf"
        _buat(label / hari_ini.isoformat() / "1" / "SPESIAL", a)
        _buat(label / hari_ini.isoformat() / "1" / "SATUAN", b)
        _buat(label / kemarin / "3" / "KOMBINASI", "PICK-000000003_KOMBINASI-REGULER-LANTAI1_x.pdf")
        _buat(label / lama / "1" / "SPESIAL", "PICK-000000009_SPESIAL_Z_x.pdf")     # di luar 3 hari
        _buat(label / hari_ini.isoformat() / "2" / "SPX_PAGI", "PICK-000000010_SHOPEE-PAGI-LANTAI1_x.pdf")  # jenis tak ditampilkan
        log_dir.mkdir()
        rel_a = f"{hari_ini.isoformat()}/1/SPESIAL/{a}"
        (log_dir / "sudah_dicetak.txt").write_text(str((label / rel_a).resolve()) + "\n", encoding="utf-8")

        diluncurkan = []
        popen_asli = subprocess.Popen   # su.subprocess = modul yang sama: simpan sebelum ditiru

        def popen_palsu(perintah, **kw):
            diluncurkan.append(perintah)
            return popen_asli([sys.executable, "-c", 'print("[1/1] Mencetak x"); print("Selesai")'],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(ps, "FOLDER_LOG", log_dir), \
                mock.patch.object(ps, "FILE_SUDAH_DICETAK", log_dir / "sudah_dicetak.txt"), \
                mock.patch.object(su.subprocess, "Popen", popen_palsu), \
                mock.patch.object(ps, "daftar_printer", return_value=["PRINTER-X"]):
            server = ThreadingHTTPServer(("127.0.0.1", 0), su.Handler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                # --- /api/sesi: hanya 3 hari & jenis yang ditampilkan, status sudah dicetak ikut
                kode, d = _panggil(port, "/api/sesi")
                assert kode == 200, d
                tanggal = [h["tanggal"] for h in d["hari"]]
                assert tanggal == [kemarin, hari_ini.isoformat()], tanggal
                sesi_hari_ini = d["hari"][1]["sesi"]
                assert [s["no"] for s in sesi_hari_ini] == [1], "sesi 2 hanya berisi SPX_PAGI -> tidak tampil"
                jenis = {j["nama"]: j["files"] for j in sesi_hari_ini[0]["jenis"]}
                assert set(jenis) == {"Spesial", "Satuan"}, jenis
                assert jenis["Spesial"][0] == {"f": a, "rel": rel_a, "kb": 2, "done": True}, jenis
                assert jenis["Satuan"][0]["done"] is False

                # --- /api/printer
                assert _panggil(port, "/api/printer") == (200, {"printer": ["PRINTER-X"]})

                # --- penjagaan: host asing, bukan JSON, path di luar folder, printer kosong
                assert _panggil(port, "/api/sesi", host="evil.example.com")[0] == 403
                assert _panggil(port, "/api/cetak", data="files=1", tipe="text/plain")[0] == 404
                assert _panggil(port, "/api/cetak", {"files": ["../../x.pdf"], "printer": "P"})[0] == 400
                assert _panggil(port, "/api/cetak", {"files": [rel_a], "printer": ""})[0] == 400
                assert _panggil(port, "/api/cetak", {"files": "bukan-daftar", "printer": "P"})[0] == 400
                assert diluncurkan == [], "permintaan tidak valid tidak boleh menjalankan cetak"

                # --- cetak: dua file, urutan dipertahankan, argumen CLI benar
                rel_b = f"{hari_ini.isoformat()}/1/SATUAN/{b}"
                kode, h = _panggil(port, "/api/cetak", {"files": [rel_b, rel_a], "printer": "PRINTER-X"})
                assert kode == 200 and h["job"], h
                perintah = diluncurkan[0]
                assert "--file-dari" in perintah and "--tanpa-konfirmasi" in perintah, perintah
                assert perintah[perintah.index("--printer") + 1] == "PRINTER-X"
                assert "--cetak-ulang-semua" not in perintah
                daftar = Path(perintah[perintah.index("--file-dari") + 1]).read_text(encoding="utf-8").split()
                assert daftar == [rel_b, rel_a], daftar
                for _ in range(50):
                    kode, j = _panggil(port, "/api/job")
                    if j["status"] != "jalan":
                        break
                    time.sleep(0.1)
                assert j["status"] == "selesai" and any("Mencetak" in x for x in j["lines"]), j

                # --- opsi ulang diteruskan sebagai --cetak-ulang-semua
                _panggil(port, "/api/cetak", {"files": [rel_a], "printer": "PRINTER-X", "ulang": True})
                assert "--cetak-ulang-semua" in diluncurkan[1]
            finally:
                server.shutdown()
    print("  server_ui: sesi 3 hari + status tercetak, penjagaan host/JSON/path, argumen print_spesial benar")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
