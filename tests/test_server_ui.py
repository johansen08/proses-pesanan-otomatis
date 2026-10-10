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
        _buat(label / hari_ini.isoformat() / "2" / "SPX_PAGI", "PICK-000000010_SHOPEE-PAGI-LANTAI1_x.pdf")  # bukan jenis utama: tetap tampil per nama subfolder
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
                assert [s["no"] for s in sesi_hari_ini] == [1, 2], "sesi 2 (SPX_PAGI) ikut tampil"
                assert [(j["nama"], len(j["files"])) for j in sesi_hari_ini[1]["jenis"]] == [("SPX_PAGI", 1)]
                jenis = {j["nama"]: j["files"] for j in sesi_hari_ini[0]["jenis"]}
                assert set(jenis) == {"Spesial", "Satuan"}, jenis
                assert jenis["Spesial"][0] == {"f": a, "rel": rel_a, "kb": 2, "done": True}, jenis
                assert jenis["Satuan"][0]["done"] is False

                # --- /api/printer
                su._cache_printer = None
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


def uji_server_ui_endpoint_harian():
    import jalankan_harian as jh

    jh._job = None
    panggilan = []

    def luncur_palsu(argumen, env):
        panggilan.append(argumen)
        return subprocess.Popen([sys.executable, "-c", "print('ok palsu')"], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8")

    with mock.patch.object(jh, "_luncurkan", luncur_palsu), mock.patch.object(jh, "_sesi_label", return_value="x/1"),             mock.patch.object(jh, "info", return_value={"jam_ok": {"TIPE 1": True}, "peringatan": {}, "berjalan": False}):
        server = ThreadingHTTPServer(("127.0.0.1", 0), su.Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            assert _panggil(port, "/api/harian/info")[1]["jam_ok"] == {"TIPE 1": True}
            # tidak valid -> 400, tidak ada proses dijalankan
            assert _panggil(port, "/api/harian/jalankan", {"langkah": ["ngawur"], "judul": "TIPE 1"})[0] == 400
            assert _panggil(port, "/api/harian/jalankan", {"langkah": [], "judul": "TIPE 1"})[0] == 400
            assert _panggil(port, "/api/harian/jalankan", {"langkah": ["Recheck stok"], "judul": "X"})[0] == 400
            assert _panggil(port, "/api/harian/jalankan", data="x", tipe="text/plain")[0] == 404
            assert _panggil(port, "/api/harian/info", host="evil.example.com")[0] == 403
            assert panggilan == []
            # valid
            kode, h = _panggil(port, "/api/harian/jalankan", {"langkah": ["Recheck stok"], "judul": "TIPE 1"})
            assert kode == 200 and h["job"], h
            for _ in range(100):
                kode, j = _panggil(port, "/api/harian/job?dari=0")
                if j["status"] != "jalan":
                    break
                time.sleep(0.1)
            assert j["status"] == "selesai" and j["langkah"][0]["status"] == "selesai", j
            kode, j2 = _panggil(port, f"/api/harian/job?dari={j['total']}")
            assert j2["lines"] == [] and j2["total"] == j["total"]
            assert _panggil(port, "/api/harian/hentikan", {}) == (200, {"dihentikan": False})
        finally:
            server.shutdown()
            jh._job = None
    print("  server_ui harian: info, validasi 400/404/403, jalankan -> job selesai, lines bertahap, hentikan tanpa job")


def uji_server_ui_port_terpakai_tidak_menjalankan_server_kedua():
    """Tombol buka app diklik dua kali: port sudah dipakai -> main() cukup membuka tampilan
    (mock webbrowser) dan keluar 0, bukan error/ server kedua."""
    server = su.Server(("127.0.0.1", 0), su.Handler)
    port = server.server_address[1]
    dibuka = []
    try:
        with mock.patch.object(su.webbrowser, "open", dibuka.append),                 mock.patch.object(sys, "argv", ["server_ui.py", "--port", str(port), "--buka", "--menu", "cetak"]):
            assert su.main() == 0
    finally:
        server.server_close()
    assert dibuka == [f"http://127.0.0.1:{port}/#cetak"], dibuka
    print("  server_ui: port terpakai -> hanya membuka tampilan (#menu), tanpa server kedua")


def uji_server_ui_dua_printer_berbeda_bersamaan():
    """Printer BERBEDA boleh mencetak bersamaan; printer yang sama antre (409); file yang sama
    tidak boleh dicetak dua printer sekaligus (409)."""
    hari_ini = date.today().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        log_dir = Path(tmp) / "logs"
        log_dir.mkdir()
        nama = ["PICK-000000001_SPESIAL_A_x.pdf", "PICK-000000002_SPESIAL_B_x.pdf", "PICK-000000003_SPESIAL_C_x.pdf"]
        _buat(label / hari_ini / "1" / "SPESIAL", *nama)
        rel = [f"{hari_ini}/1/SPESIAL/{n}" for n in nama]
        popen_asli = subprocess.Popen
        diluncurkan = []

        def popen_palsu(perintah, **kw):    # tiap job menggantung ~1,5 detik supaya tumpang tindih
            diluncurkan.append(perintah)
            return popen_asli([sys.executable, "-c", "import time; print('[1/1] Mencetak x', flush=True); time.sleep(1.5)"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")

        su._jobs.clear()
        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(ps, "FOLDER_LOG", log_dir),                 mock.patch.object(su.subprocess, "Popen", popen_palsu):
            server = su.Server(("127.0.0.1", 0), su.Handler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                assert _panggil(port, "/api/cetak", {"files": [rel[0]], "printer": "PRINTER-A"})[0] == 200
                # printer berbeda, file berbeda -> boleh bersamaan
                assert _panggil(port, "/api/cetak", {"files": [rel[1]], "printer": "PRINTER-B"})[0] == 200
                # printer yang sama masih mencetak -> 409
                kode, e = _panggil(port, "/api/cetak", {"files": [rel[2]], "printer": "PRINTER-A"})
                assert kode == 409 and "PRINTER-A" in e["error"], (kode, e)
                # file yang sedang dicetak printer A tidak boleh dikirim ke printer C
                kode, e = _panggil(port, "/api/cetak", {"files": [rel[0], rel[2]], "printer": "PRINTER-C"})
                assert kode == 409 and "PRINTER-A" in e["error"], (kode, e)
                assert len(diluncurkan) == 2
                # status terpisah per printer
                kode, ja = _panggil(port, "/api/job?printer=PRINTER-A")
                kode, jb = _panggil(port, "/api/job?printer=PRINTER-B")
                assert ja["printer"] == "PRINTER-A" and jb["printer"] == "PRINTER-B" and ja["id"] != jb["id"]
                assert ja["status"] == "jalan" and jb["status"] == "jalan"
                assert {n: v["status"] for n, v in _panggil(port, "/api/jobs")[1]["jobs"].items()} ==                     {"PRINTER-A": "jalan", "PRINTER-B": "jalan"}
                assert _panggil(port, "/api/job?printer=TIDAK-ADA")[1]["status"] == "kosong"
                for _ in range(60):
                    sj = [_panggil(port, f"/api/job?printer={n}")[1]["status"] for n in ("PRINTER-A", "PRINTER-B")]
                    if sj == ["selesai", "selesai"]:
                        break
                    time.sleep(0.1)
                assert sj == ["selesai", "selesai"], sj
                # setelah A selesai, A boleh dipakai lagi
                assert _panggil(port, "/api/cetak", {"files": [rel[2]], "printer": "PRINTER-A"})[0] == 200
                # nama file daftar pilihan unik per job (tidak saling menimpa)
                assert len({c[c.index("--file-dari") + 1] for c in diluncurkan}) == len(diluncurkan)
            finally:
                time.sleep(1.8)          # biarkan job terakhir selesai sebelum folder sementara dihapus
                server.shutdown()
                su._jobs.clear()
    print("  server_ui: printer berbeda mencetak bersamaan, printer sama/file sama ditolak 409, status per printer")


def uji_server_ui_download_ulang_picklist_terhenti():
    """Picklist terhenti dikumpulkan terstruktur (peringatan_gagal), UI memilih sebagian/semua,
    server menjalankan `main.py --lanjut` berurutan dengan argumen asalnya."""
    import jalankan_harian as jh
    import peringatan_gagal as pg

    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp) / "logs"
        log_dir.mkdir()
        sesi = Path(tmp) / "label-pengiriman" / "2026-10-09" / "2"
        panggilan = []

        def luncur_palsu(argumen, env):
            panggilan.append(argumen)
            return subprocess.Popen([sys.executable, "-c", "print('lanjut palsu')"], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding="utf-8")

        jh._job = None
        su._lanjut = None
        with mock.patch.object(jh, "FOLDER_LOG", log_dir), mock.patch.object(jh, "_luncurkan", luncur_palsu):
            pg.atur_folder(log_dir)
            pg.catat_terhenti("PICK-000000001", "SPX-A", sesi, "timeout unduh", tag="SPX_SPESIAL")
            pg.catat_terhenti("PICK-000000002", "GTL", sesi, "410 Expired", subfolder="URGENT")
            pg.catat_terhenti("PICK-000000003", "X", sesi, "gagal")
            pg.tandai_selesai("PICK-000000003")
            assert [d["picklist"] for d in pg.daftar_terhenti()] == ["PICK-000000002", "PICK-000000001"]
            server = su.Server(("127.0.0.1", 0), su.Handler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                kode, d = _panggil(port, "/api/terhenti")
                assert kode == 200 and len(d["daftar"]) == 2 and d["job"] is None, d
                # pilihan tidak ada di daftar / kosong / bukan daftar -> 400, tidak ada proses
                assert _panggil(port, "/api/terhenti/jalankan", {"picklist": ["PICK-000000003"]})[0] == 400
                assert _panggil(port, "/api/terhenti/jalankan", {"picklist": []})[0] == 400
                assert _panggil(port, "/api/terhenti/jalankan", {"picklist": "PICK-000000001"})[0] == 400
                assert _panggil(port, "/api/terhenti/jalankan", {"picklist": ["PICK-000000001"]}, host="evil.example.com")[0] == 403
                assert panggilan == []
                kode, _ = _panggil(port, "/api/terhenti/jalankan", {"picklist": ["PICK-000000001", "PICK-000000002"]})
                assert kode == 200
                for _ in range(100):
                    j = _panggil(port, "/api/terhenti")[1]["job"]
                    if j["status"] != "jalan":
                        break
                    time.sleep(0.1)
                assert j["status"] == "selesai" and j["maju"] == 2 and j["gagal"] == 0, j
                assert len(panggilan) == 2
                a, b = panggilan
                assert a[a.index("--lanjut") + 1] == "PICK-000000001" and "--tag" in a and "SPX_SPESIAL" in a
                assert b[b.index("--lanjut") + 1] == "PICK-000000002" and b[b.index("--subfolder") + 1] == "URGENT"
                assert a[a.index("--sesi") + 1] == "2026-10-09/2" and a[-1] == "--jalankan"
            finally:
                server.shutdown()
                su._lanjut = None
                pg._file_peringatan = None
    print("  server_ui: picklist terhenti dikumpulkan, validasi pilihan, download ulang berurutan dengan argumen asal")


def uji_server_ui_daftar_printer_di_cache():
    """Get-Printer lambat (proses PowerShell): dipanggil sekali per TTL, bukan tiap tab/permintaan;
    kegagalan tidak di-cache; setelah TTL dibaca ulang."""
    su._cache_printer = None
    try:
        with mock.patch.object(ps, "daftar_printer", return_value=["P1", "P2"]) as m:
            server = ThreadingHTTPServer(("127.0.0.1", 0), su.Handler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                for _ in range(3):
                    assert _panggil(port, "/api/printer") == (200, {"printer": ["P1", "P2"]})
                assert m.call_count == 1, m.call_count

                # hasil cache yang dikembalikan salinan: perubahan pemanggil tidak merusak cache
                su.daftar_printer_cache().append("X")
                assert su.daftar_printer_cache() == ["P1", "P2"]

                # setelah TTL lewat -> dibaca ulang
                waktu, daftar = su._cache_printer
                su._cache_printer = (waktu - su.TTL_PRINTER_S - 1, daftar)
                m.return_value = ["P3"]
                assert _panggil(port, "/api/printer") == (200, {"printer": ["P3"]})
                assert m.call_count == 2

                # kegagalan tidak di-cache: panggilan berikutnya mencoba lagi
                su._cache_printer = None
                m.side_effect = ps.CetakError("Tidak ada printer")
                assert _panggil(port, "/api/printer")[0] == 500
                m.side_effect = None
                m.return_value = ["P4"]
                assert _panggil(port, "/api/printer") == (200, {"printer": ["P4"]})

                # panggilan bersamaan (tab dibuka serentak) hanya memicu satu Get-Printer
                su._cache_printer = None
                m.reset_mock()

                def lambat():
                    time.sleep(0.3)
                    return ["P5"]
                m.side_effect = lambat
                hasil = []
                ts = [threading.Thread(target=lambda: hasil.append(su.daftar_printer_cache())) for _ in range(4)]
                [t.start() for t in ts]
                [t.join() for t in ts]
                assert m.call_count == 1 and hasil == [["P5"]] * 4, (m.call_count, hasil)
            finally:
                server.shutdown()
    finally:
        su._cache_printer = None
    print("  server_ui: daftar printer di-cache (TTL), salinan aman, gagal tidak di-cache, serentak = 1 panggilan")


def uji_server_ui_halaman_cetak_digambar_sebelum_printer():
    """Regresi freeze: gambarCetak() harus dipanggil SEBELUM menunggu /api/printer di initCetak."""
    html = (ROOT / "data" / "prototype-desktop" / "index.html").read_text(encoding="utf-8")
    badan = html[html.index("async function initCetak()"):html.index("/* ---------- init")]
    assert badan.index("gambarCetak()") < badan.index("/api/printer"), "daftar sesi harus digambar dulu"
    print("  index.html: initCetak menggambar sesi sebelum menunggu printer")


def uji_server_ui_lanjut_cetak_terputus():
    """/api/sebagian mendaftar file terputus; /api/sebagian/lanjut menjalankan print_spesial.py
    --lanjut-sebagian --mulai-dari <path>=<halaman>; file tak tercatat / halaman di luar rentang ditolak."""
    hari_ini = date.today().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        log_dir = Path(tmp) / "logs"
        log_dir.mkdir()
        nama = ["PICK-000000001_SPESIAL_A_x.pdf", "PICK-000000002_SPESIAL_B_x.pdf"]
        _buat(label / hari_ini / "1" / "SPESIAL", *nama)
        rel = [f"{hari_ini}/1/SPESIAL/{n}" for n in nama]
        catatan = log_dir / "cetak_sebagian.json"
        diluncurkan = []
        popen_asli = subprocess.Popen

        def popen_palsu(perintah, **kw):
            diluncurkan.append(perintah)
            return popen_asli([sys.executable, "-c", "print('lanjut palsu')"], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding="utf-8")

        su._jobs.clear()
        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(ps, "FOLDER_LOG", log_dir), \
                mock.patch.object(ps, "FILE_SEBAGIAN", catatan), mock.patch.object(su.subprocess, "Popen", popen_palsu):
            ps.catat_sebagian(label / rel[0], "PRINTER-A", "5", 4, 10)
            server = su.Server(("127.0.0.1", 0), su.Handler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                kode, isi = _panggil(port, "/api/sebagian")
                assert kode == 200 and [(d["rel"], d["tercetak"], d["total"]) for d in isi["daftar"]] == [(rel[0], 4, 10)], isi
                assert _panggil(port, "/api/sebagian/lanjut", {"item": [{"rel": rel[1], "mulai": 1}], "printer": "P"})[0] == 400
                assert _panggil(port, "/api/sebagian/lanjut", {"item": [{"rel": rel[0], "mulai": 11}], "printer": "P"})[0] == 400
                assert _panggil(port, "/api/sebagian/lanjut", {"item": [{"rel": rel[0], "mulai": 5}], "printer": "PRINTER-A"})[0] == 200
                perintah = diluncurkan[0]
                assert "--lanjut-sebagian" in perintah and "--tanpa-konfirmasi" in perintah, perintah
                assert perintah[perintah.index("--mulai-dari") + 1].endswith("SPESIAL_A_x.pdf=5"), perintah
            finally:
                server.shutdown()
                server.server_close()
        print("  server_ui: /api/sebagian daftar file terputus, lanjut dari halaman pilihan, validasi ditolak")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
