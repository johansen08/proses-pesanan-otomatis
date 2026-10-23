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
        j = "PICK-000000004_SPESIAL_J_x.pdf"
        _buat(label / hari_ini.isoformat() / "1" / "JNT_SPESIAL", j)   # harus tampil "Spesial J&T", BUKAN "Spesial"
        _buat(label / kemarin / "3" / "KOMBINASI", "PICK-000000003_KOMBINASI-REGULER-LANTAI1_x.pdf")
        _buat(label / lama / "1" / "SPESIAL", "PICK-000000009_SPESIAL_Z_x.pdf")     # di luar 3 hari
        _buat(label / hari_ini.isoformat() / "2" / "SPX_PAGI", "PICK-000000010_SHOPEE-PAGI-LANTAI1_x.pdf")  # tampil sebagai "Shopee Pagi"
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
                assert [(j["nama"], len(j["files"])) for j in sesi_hari_ini[1]["jenis"]] == [("Shopee Pagi", 1)]
                jenis = {j["nama"]: j["files"] for j in sesi_hari_ini[0]["jenis"]}
                assert set(jenis) == {"Spesial", "Satuan", "Spesial J&T"}, jenis
                assert [x["f"] for x in jenis["Spesial J&T"]] == [j] and [x["f"] for x in jenis["Spesial"]] == [a], jenis
                assert jenis["Spesial"][0] == {"f": a, "rel": rel_a, "kb": 2, "done": True}, jenis
                assert jenis["Satuan"][0]["done"] is False

                # --- /api/printer
                su._cache_printer = None
                assert _panggil(port, "/api/printer") == (200, {"printer": ["PRINTER-X"], "virtual": []})

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


def uji_server_ui_urgent_lazada_kelompok_sendiri():
    hari_ini = date.today()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        urgent = label / hari_ini.isoformat() / "1" / "URGENT"
        _buat(urgent, "PICK-000000002_LAZADA_x.pdf", "PICK-000000001_GTL-SICEPAT-LANTAI1_x.pdf",
              "PICK-000000003_JNE-LEX_x.pdf")
        with mock.patch.object(ps, "FOLDER_LABEL", label), \
                mock.patch.object(ps, "FILE_SUDAH_DICETAK", Path(tmp) / "sudah_dicetak.txt"):
            d = su.data_sesi(hari_ini)
        jenis = {j["nama"]: [f["f"] for f in j["files"]] for j in d["hari"][0]["sesi"][0]["jenis"]}
        assert jenis == {"GTL-SiCepat": ["PICK-000000001_GTL-SICEPAT-LANTAI1_x.pdf"],
                         "Urgent Lazada · skala 68%": ["PICK-000000002_LAZADA_x.pdf"],
                         "URGENT": ["PICK-000000003_JNE-LEX_x.pdf"]}, jenis
    print("  server_ui: label Lazada tampil di kelompok 'Urgent Lazada - skala 68%', JNE-LEX tetap di URGENT")


def uji_server_ui_sesi_pemulihan_tampil_di_menu_cetak():
    hari_ini = date.today()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        _buat(label / hari_ini.isoformat() / "10" / "SPESIAL", "PICK-000000001_SPESIAL_A_2026-10-19_172147.pdf")
        _buat(label / hari_ini.isoformat() / "11-PEMULIHAN" / "SPESIAL", "PICK-000000001_SPESIAL_A_2026-10-19_180000.pdf")
        with mock.patch.object(ps, "FOLDER_LABEL", label), \
                mock.patch.object(ps, "FILE_SUDAH_DICETAK", Path(tmp) / "sudah_dicetak.txt"):
            sesi = su.data_sesi(hari_ini)["hari"][0]["sesi"]
            assert [s["id"] for s in sesi] == [f"{hari_ini.isoformat()}/10", f"{hari_ini.isoformat()}/11-PEMULIHAN"], sesi
            assert sesi[1]["no"] == 11 and sesi[1]["judul"] == "11-PEMULIHAN" and "judul" not in sesi[0]
            assert ps.folder_sesi_terbaru(label).name == "11-PEMULIHAN"
    print("  server_ui: folder N-PEMULIHAN tampil sebagai sesi tersendiri di menu Cetak & dianggap sesi terbaru")


def uji_server_ui_pilah_sesi_pemulihan():
    import json as _json
    import pilah_satuan as pl
    hari_ini = date.today()
    tgl = hari_ini.isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        _buat(label / tgl / "11" / "SATUAN", f"PICK-000000002_1QTY-REGULER-2A_{tgl}_072000.pdf")
        _buat(label / tgl / "11-PEMULIHAN" / "SATUAN", f"PICK-000000002_1QTY-REGULER-2A_{tgl}_180000.pdf")
        (label / tgl / "11-PEMULIHAN" / "pulihan.json").write_text(_json.dumps({"asal": f"{tgl}/11"}), encoding="utf-8")
        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(pl, "MASA_TENANG_S", 0):
            sesi = su.data_pilah(hari_ini)["hari"][0]["sesi"]
            assert [(x["no"], x["kode"], x.get("judul"), x["layak"]) for x in sesi] ==                 [(11, "11", None, True), (11, "11P", "11-PEMULIHAN", True)], sesi
            # sesi N dan N-PEMULIHAN-nya tidak boleh dipilih bersamaan (resi sama)
            try:
                su.mulai_pilah({"tanggal": tgl, "sesi": ["11", "11P"], "min_resi": 3}, "analisis")
                assert False
            except ValueError as e:
                assert "pilih salah satu" in str(e), e
    print("  server_ui pilah: sesi N-PEMULIHAN tampil (kode 11P), jam dari sesi asal, tidak bersamaan dengan sesi asalnya")


def uji_server_ui_pilah_lanjutan():
    import pilah_satuan as pl
    hari_ini = date.today()
    tgl = hari_ini.isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        _buat(label / tgl / "1" / "SATUAN", f"PICK-000000002_1QTY-REGULER-2A_{tgl}_072000.pdf")
        _buat(label / tgl / "2" / "SATUAN", f"PICK-000000003_1QTY-REGULER-2A_{tgl}_080000.pdf")
        _buat(label / tgl / "SISA-SATUAN-1", "SISA-SATUAN_1QTY-REGULER-2A_1resi.pdf")   # sisa belum dilanjutkan
        _buat(label / tgl / "SISA-SATUAN-9" / "sudah-dipilah-lagi", "SISA-SATUAN_x_1resi.pdf")   # sudah dipindah -> bukan
        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(pl, "MASA_TENANG_S", 0):
            assert su.data_pilah(hari_ini)["hari"][0]["lanjutan"] == ["1"]
            for data, kata in (({"lanjutan_dari": "1; rm"}, "lanjutan_dari harus label"),
                               ({"lanjutan_dari": "7"}, "tidak ditemukan"),
                               ({"lanjutan_dari": "1", "sesi": ["1"]}, "sudah termasuk")):
                try:
                    su.mulai_pilah({"tanggal": tgl, "sesi": ["2"], "min_resi": 3, **data}, "analisis")
                    assert False, data
                except ValueError as e:
                    assert kata in str(e), e
    print("  server_ui pilah: daftar hasil yang bisa dilanjutkan; lanjutan_dari divalidasi (format, hasil ada, sesi tumpang tindih)")


def uji_server_ui_pulih_status_dan_job():
    import json as _json
    import peringatan_gagal
    import peringatan_resi
    hari_ini = date.today()
    tgl = hari_ini.isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        log_dir = Path(tmp) / "logs"
        log_dir.mkdir()
        sesi = label / tgl / "10"
        _buat(sesi / "SPESIAL", f"PICK-000000001_SPESIAL_A_{tgl}_172147.pdf", f"PICK-000000002_SPESIAL_B_{tgl}_172150.pdf")
        _buat(sesi / "SATUAN", f"PICK-000000004_1QTY-REGULER-2A_{tgl}_172200.pdf")
        (log_dir / "picklist_terhenti.jsonl").write_text("\n".join(_json.dumps(d) for d in [
            {"op": "dibuat", "picklist": "PICK-000000003", "nama": "C", "tag": "SPESIAL", "subfolder": None, "sesi": f"{tgl}/10"},
            {"op": "tambah", "picklist": "PICK-000000003", "nama": "C", "tag": "SPESIAL", "subfolder": None, "sesi": f"{tgl}/10",
             "alasan": "timeout", "epoch": 9e12}]) + "\n", encoding="utf-8")
        peringatan_resi.atur_folder(log_dir)
        peringatan_resi.catat_tanpa_resi("PICK-000000002", "B", ["SP-1", "SP-2"])
        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(su.jh, "FOLDER_LOG", log_dir):
            d = su.data_pulih(hari_ini)
            h = d["hari"][0]
            assert h["tanggal"] == tgl and h["berikut"] == "11-PEMULIHAN", h
            st = {p["no"]: p["st"] for p in h["sesi"][0]["pl"]}
            assert st == {"PICK-000000001": "ok", "PICK-000000002": "kurang", "PICK-000000003": "terhenti",
                          "PICK-000000004": "ok"}, st
            for salah in ({"tanggal": "x", "sesi": "10"}, {"tanggal": tgl, "sesi": "10P"}, {"tanggal": tgl, "sesi": "99"}):
                try:
                    su.mulai_pulih(salah, "cek")
                    assert False, salah
                except ValueError:
                    pass
            # keluaran main.py dibaca jadi kemajuan, hasil per picklist, folder tujuan
            awal = "2026-10-20 08:41 INFO   "      # awalan util_umum.atur_log: sebelumnya lupa -> progress tidak pernah update
            keluaran = [awal + "=== Pulihkan PICK-000000001 (A)", awal + "  [5] PICK-000000001: minta resi untuk 3 pesanan",
                        awal + "  OK PICK-000000001: resi 3/3",
                        awal + "=== Pulihkan PICK-000000002 (B)",
                        awal + "  OK PICK-000000002: resi 1/3 - belum dapat resi: SP-1, SP-2",
                        "2026-10-20 08:42 ERROR   GAGAL PICK-000000004: boom",
                        awal + "Hasil pemulihan ke folder: C:\\x\\" + tgl + "\\11-PEMULIHAN"]
            diluncurkan = []

            def luncur(argumen, env):
                diluncurkan.append(argumen)
                return subprocess.Popen([sys.executable, "-c", "print(" + repr("\n".join(keluaran)) + ")"],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
            with mock.patch.object(su.jh, "_luncurkan", luncur), \
                    mock.patch.object(su.jh, "keadaan", return_value={"status": "kosong"}):
                su.mulai_pulih({"tanggal": tgl, "sesi": "10"}, "jalankan")
                assert "--jalankan" in diluncurkan[0] and f"{tgl}/10" in diluncurkan[0]
                for _ in range(100):
                    j = su.info_pulih()
                    if j["status"] != "jalan":
                        break
                    time.sleep(0.05)
                assert j["status"] == "selesai" and j["maju"] == 3 and j["folder"] == "11-PEMULIHAN", j
                assert j["aktif"] == {}, "picklist yang selesai/gagal keluar dari daftar berjalan"
                assert j["tahap"]["PICK-000000001"] == "minta resi", j["tahap"]
                assert j["hasil"]["PICK-000000002"] == {"resi": 1, "total": 3, "sisa": 2}
                assert j["hasil"]["PICK-000000004"] == {"gagal": "boom"}
                su.mulai_pulih({"tanggal": tgl, "sesi": "10"}, "cek")
                assert "--jalankan" not in diluncurkan[1]
    peringatan_resi._file_peringatan = None
    peringatan_gagal._file_peringatan = None
    print("  server_ui pulih: status picklist dari data lokal, validasi, job membaca hasil per picklist & folder tujuan")


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


def uji_server_ui_cetak_banyak_printer_membagi_berurutan_seimbang():
    """`printers` di /api/cetak: file dibagi blok berurutan, satu job per printer; semua printer
    harus bebas sebelum satu pun jalan; printer virtual ditandai di /api/printer."""
    hari_ini = date.today().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        log_dir = Path(tmp) / "logs"
        log_dir.mkdir()
        nama = [f"PICK-00000000{i}_SPESIAL_A{i}_x.pdf" for i in range(1, 7)]
        _buat(label / hari_ini / "1" / "SPESIAL", *nama)
        rel = [f"{hari_ini}/1/SPESIAL/{n}" for n in nama]
        popen_asli = subprocess.Popen
        diluncurkan = []

        def popen_palsu(perintah, **kw):
            diluncurkan.append(perintah)
            return popen_asli([sys.executable, "-c", "import time; print('[1/1] Mencetak x', flush=True); time.sleep(1)"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")

        su._jobs.clear()
        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(ps, "FOLDER_LOG", log_dir), \
                mock.patch.object(su.subprocess, "Popen", popen_palsu), \
                mock.patch.object(su, "_jumlah_halaman", lambda f: 10), \
                mock.patch.object(su, "daftar_printer_cache", lambda: ["P1", "P2", "P3", "OneNote (Desktop)", "Microsoft Print to PDF"]):
            server = su.Server(("127.0.0.1", 0), su.Handler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                kode, p = _panggil(port, "/api/printer")
                assert p["virtual"] == ["OneNote (Desktop)", "Microsoft Print to PDF"], p
                assert _panggil(port, "/api/cetak", {"files": rel, "printers": []})[0] == 400
                assert _panggil(port, "/api/cetak", {"files": rel, "printers": ["P1", "P1"]})[0] == 400
                assert _panggil(port, "/api/cetak", {"files": rel, "printers": "P1"})[0] == 400
                # P2 sibuk -> tidak ada printer yang dimulai
                assert _panggil(port, "/api/cetak", {"files": [rel[0]], "printer": "P2"})[0] == 200
                kode, e = _panggil(port, "/api/cetak", {"files": rel[1:], "printers": ["P1", "P2", "P3"]})
                assert kode == 409 and "P2" in e["error"] and len(diluncurkan) == 1, (kode, e)
                time.sleep(1.2)
                kode, r = _panggil(port, "/api/cetak", {"files": rel, "printers": ["P1", "P2", "P3"]})
                assert kode == 200 and [(n, v["file"]) for n, v in r["jobs"].items()] == [("P1", 2), ("P2", 2), ("P3", 2)], r
                # tiap printer menerima blok berurutan; gabungan = semua file tanpa tumpang tindih
                bagian = []
                for c in diluncurkan[1:]:
                    isi = Path(c[c.index("--file-dari") + 1]).read_text(encoding="utf-8").split()
                    bagian.append(isi)
                assert bagian == [rel[0:2], rel[2:4], rel[4:6]], bagian
                # file lebih sedikit dari printer -> printer berlebih tidak dipakai
                time.sleep(1.2)
                kode, r = _panggil(port, "/api/cetak", {"files": rel[:2], "printers": ["P1", "P2", "P3"]})
                assert kode == 200 and list(r["jobs"]) == ["P1", "P2"], r
            finally:
                time.sleep(1.3)
                server.shutdown()
                su._jobs.clear()
    print("  server_ui: cetak banyak printer membagi file berurutan & seimbang, cek printer bebas dulu, printer virtual ditandai")


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
                    assert _panggil(port, "/api/printer") == (200, {"printer": ["P1", "P2"], "virtual": []})
                assert m.call_count == 1, m.call_count

                # hasil cache yang dikembalikan salinan: perubahan pemanggil tidak merusak cache
                su.daftar_printer_cache().append("X")
                assert su.daftar_printer_cache() == ["P1", "P2"]

                # setelah TTL lewat -> dibaca ulang
                waktu, daftar = su._cache_printer
                su._cache_printer = (waktu - su.TTL_PRINTER_S - 1, daftar)
                m.return_value = ["P3"]
                assert _panggil(port, "/api/printer") == (200, {"printer": ["P3"], "virtual": []})
                assert m.call_count == 2

                # kegagalan tidak di-cache: panggilan berikutnya mencoba lagi
                su._cache_printer = None
                m.side_effect = ps.CetakError("Tidak ada printer")
                assert _panggil(port, "/api/printer")[0] == 500
                m.side_effect = None
                m.return_value = ["P4"]
                assert _panggil(port, "/api/printer") == (200, {"printer": ["P4"], "virtual": []})

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


def uji_server_ui_pilah_satuan():
    """Menu Pilah: daftar sesi satuan, validasi, job analisis/buat (proses ditiru), folder hasil
    ikut tampil di data_sesi (menu Cetak)."""
    import jalankan_harian as jh
    import pilah_satuan as pl
    from reportlab.pdfgen import canvas

    hari_ini = date.today().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp) / "label-pengiriman"
        for sesi, n, jam, folder in (("1", 3, "081500", "SATUAN"), ("2", 2, "104000", "SATUAN"),
                                      ("4", 1, "140500", "SATUAN"),            # diproses 14.05: di luar 07.00-12.00
                                      ("5", 1, "090000", "JNT_SATUAN")):       # satuan per kurir, bukan gabungan
            d = label / hari_ini / sesi / folder
            d.mkdir(parents=True)
            c = canvas.Canvas(str(d / f"PICK-00000000{sesi}_1QTY-REGULER-2A_{hari_ini}_{jam}.pdf"))
            for _ in range(n):
                c.showPage()
            c.save()
        _buat(label / hari_ini / "3" / "SPESIAL", "PICK-000000009_SPESIAL_A_x.pdf")   # tanpa satuan: tidak masuk daftar
        hasil_json = {"sesi": "1-2", "pdf": 2, "halaman": 5, "tak_cocok": 0, "spesial": [], "sisa": {"2A": 5},
                      "folder": [], "file": 0}
        diluncurkan = []

        def luncur_palsu(argumen, env):
            diluncurkan.append(argumen)
            kode = ('print("a.pdf: 3 halaman dipetakan"); print("b.pdf: 2 halaman dipetakan"); '
                    f'print({pl.PENANDA_JSON + json.dumps(hasil_json)!r})')
            return subprocess.Popen([sys.executable, "-c", kode], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding="utf-8")

        su._pilah = None
        import kurasi_satuan
        with mock.patch.object(ps, "FOLDER_LABEL", label), mock.patch.object(jh, "_luncurkan", luncur_palsu), \
                mock.patch.object(ps, "FILE_SUDAH_DICETAK", Path(tmp) / "x.txt"), \
                mock.patch.object(kurasi_satuan, "FILE_KURASI", Path(tmp) / "kurasi0.json"), \
                mock.patch.object(pl, "MASA_TENANG_S", 0), \
                mock.patch.object(jh, "FOLDER_LOG", Path(tmp) / "logs"):
            server = su.Server(("127.0.0.1", 0), su.Handler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                kode, d = _panggil(port, "/api/pilah/sesi")
                sesi = d["hari"][0]["sesi"]
                assert kode == 200 and [(s["no"], s["picklist"], s["label"], s["layak"], s["jam"]) for s in sesi] == [
                    (1, 1, 3, True, "08.15"), (2, 1, 2, True, "10.40"), (4, 1, 1, False, "14.05"),
                    (5, 1, 1, True, "09.00")], d
                assert "di luar 07.00-12.00" in sesi[2]["alasan"] and sesi[3]["alasan"] is None, sesi
                # validasi: tidak ada proses dijalankan
                for bad in ({"tanggal": "x", "sesi": ["1"]}, {"tanggal": hari_ini, "sesi": []},
                            {"tanggal": hari_ini, "sesi": ["3"]}, {"tanggal": hari_ini, "sesi": ["1"], "min_resi": 0},
                            {"tanggal": hari_ini, "sesi": ["1"], "min_resi": "3"},
                            {"tanggal": "2020-01-01", "sesi": ["1"]},
                            {"tanggal": hari_ini, "sesi": ["1", "4"]}):     # sesi gabungan di luar jam 07.00-12.00
                    kode, isi = _panggil(port, "/api/pilah/analisis", bad)
                    assert kode == 400, bad
                kode, isi = _panggil(port, "/api/pilah/buat", {"tanggal": hari_ini, "sesi": ["1", "4"]})
                assert kode == 400 and "Sesi 4" in isi["error"] and "Sesi 1" not in isi["error"], isi
                assert _panggil(port, "/api/pilah/analisis", data="x", tipe="text/plain")[0] == 404
                assert diluncurkan == []
                # analisis -> job selesai dengan hasil
                assert _panggil(port, "/api/pilah/analisis", {"tanggal": hari_ini, "sesi": ["2", "1"], "min_resi": 3})[0] == 200
                for _ in range(100):
                    kode, j = _panggil(port, "/api/pilah/job")
                    if j["status"] != "jalan":
                        break
                    time.sleep(0.1)
                assert j["status"] == "selesai" and j["hasil"] == hasil_json and j["maju"] == 2 and j["total"] == 2, j
                assert PENANDA_TIDAK_BOCOR(j["lines"])
                p = diluncurkan[0]
                assert "--analisis-saja" in p and p[p.index("--sesi") + 1] == "1-2" and "--json" in p, p
                # buat -> tanpa --analisis-saja
                assert _panggil(port, "/api/pilah/buat", {"tanggal": hari_ini, "sesi": ["1", "2"]})[0] == 200
                for _ in range(100):
                    j = _panggil(port, "/api/pilah/job")[1]
                    if j["status"] != "jalan":
                        break
                    time.sleep(0.1)
                assert "--analisis-saja" not in diluncurkan[1] and j["mode"] == "buat", diluncurkan[1]
                # mode hanya-Excel diteruskan ke proses; tipe salah ditolak
                assert _panggil(port, "/api/pilah/buat", {"tanggal": hari_ini, "sesi": ["1"], "tanpa_pdf": "ya"})[0] == 400
                n_sebelum = len(diluncurkan)
                assert _panggil(port, "/api/pilah/buat", {"tanggal": hari_ini, "sesi": ["1"], "tanpa_pdf": True})[0] == 200
                for _ in range(100):
                    j = _panggil(port, "/api/pilah/job")[1]
                    if j["status"] != "jalan":
                        break
                    time.sleep(0.1)
                assert "--tanpa-pdf" in diluncurkan[n_sebelum] and j["tanpa_pdf"] is True, diluncurkan[n_sebelum]
                assert "--tanpa-pdf" not in diluncurkan[1]
                # proses harian / download ulang berjalan -> label sesi belum lengkap -> 409 (tidak ada proses baru)
                n_sebelum = len(diluncurkan)
                with mock.patch.object(jh, "keadaan", return_value={"status": "jalan"}):
                    kode, isi = _panggil(port, "/api/pilah/analisis", {"tanggal": hari_ini, "sesi": ["1"]})
                    assert kode == 409 and "proses harian" in isi["error"], isi
                assert len(diluncurkan) == n_sebelum
                # PDF sudah dikurasi ke folder hasil LAIN -> 'buat' ditolak 400 (analisis tetap boleh)
                asal1 = sorted((label / hari_ini).glob("1/SATUAN/*.pdf"))
                with mock.patch.object(kurasi_satuan, "FILE_KURASI", Path(tmp) / "kurasi.json"):
                    kurasi_satuan.catat(asal1, "1-2")
                    (label / hari_ini / "SPESIAL-SATUAN-1-2").mkdir(exist_ok=True)   # folder hasil lama masih ada
                    kode, isi = _panggil(port, "/api/pilah/buat", {"tanggal": hari_ini, "sesi": ["1"]})
                    assert kode == 400 and "SPESIAL-SATUAN-1-2" in isi["error"], isi
                    assert _panggil(port, "/api/pilah/buat", {"tanggal": hari_ini, "sesi": ["1"], "tanpa_pdf": True})[0] == 200
                    for _ in range(100):
                        if _panggil(port, "/api/pilah/job")[1]["status"] != "jalan":
                            break
                        time.sleep(0.1)
                    assert _panggil(port, "/api/pilah/analisis", {"tanggal": hari_ini, "sesi": ["1"]})[0] == 200
                    for _ in range(100):
                        if _panggil(port, "/api/pilah/job")[1]["status"] != "jalan":
                            break
                        time.sleep(0.1)
                    (label / hari_ini / "SPESIAL-SATUAN-1-2").rmdir()
                # sesi yang PDF-nya baru diubah (proses harian masih menulis) tampil tidak layak
                with mock.patch.object(pl, "MASA_TENANG_S", 120):
                    sesi_aktif = _panggil(port, "/api/pilah/sesi")[1]["hari"][0]["sesi"]
                    assert not sesi_aktif[0]["layak"] and "masih menulis label" in sesi_aktif[0]["alasan"], sesi_aktif
                    assert _panggil(port, "/api/pilah/buat", {"tanggal": hari_ini, "sesi": ["1"]})[0] == 400
                # folder hasil tampil di menu Cetak sebagai pseudo-sesi
                _buat(label / hari_ini / "SPESIAL-SATUAN-1-2", "SPESIAL-SATUAN_X_3resi.pdf")
                _buat(label / hari_ini / "SISA-SATUAN-1-2", "SISA-SATUAN_1QTY-REGULER-2A_2resi.pdf")
                hari = su.data_sesi()["hari"][0]["sesi"]
                # satuan asal yang dikurasi diberi penanda di data_sesi (UI menampilkan & tidak mencetaknya)
                import kurasi_satuan
                asal = sorted((label / hari_ini).glob("*/SATUAN/*.pdf"))
                with mock.patch.object(kurasi_satuan, "FILE_KURASI", Path(tmp) / "kurasi.json"):
                    kurasi_satuan.catat(asal[:1], "1-2")
                    hari2 = su.data_sesi()["hari"][0]["sesi"]
                    kur = [f for s in hari2 for j in s["jenis"] for f in j["files"] if f.get("kurasi")]
                    assert [(f["f"], f["kurasi"]) for f in kur] == [(asal[0].name, "1-2")], kur
                    assert all("kurasi" not in f for s in hari for j in s["jenis"] for f in j["files"])   # tanpa penanda: tak ada kunci
                judul = {s.get("judul"): s for s in hari if s.get("judul")}
                assert set(judul) == {"SPESIAL-SATUAN-1-2", "SISA-SATUAN-1-2"}, [s["id"] for s in hari]
                assert judul["SISA-SATUAN-1-2"]["jenis"][0]["files"][0]["rel"].endswith("SISA-SATUAN_1QTY-REGULER-2A_2resi.pdf")
            finally:
                server.shutdown()
                server.server_close()
                su._pilah = None
    print("  server_ui pilah: daftar sesi satuan, validasi 400/404, analisis & buat jadi job, folder hasil masuk menu Cetak")


def PENANDA_TIDAK_BOCOR(lines):
    """Baris ringkasan JSON tidak ikut ke log yang tampil di UI."""
    return not any(l.startswith("##HASIL##") for l in lines)


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
