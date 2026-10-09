"""Uji jalankan_harian.py (menu Harian UI desktop) - TANPA menyentuh Jubelio: proses
`main.py`/`rekap_waktu.py` ditiru dengan proses python kecil, sesi label ditiru.

Jalankan:  .venv\\Scripts\\python tests\\test_jalankan_harian.py
"""
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import jalankan_harian as jh  # noqa: E402


def _tunggu(selesai=lambda j: j["status"] != "jalan", batas=15.0):
    mulai = time.time()
    while time.time() - mulai < batas:
        j = jh.keadaan()
        if selesai(j):
            return j
        time.sleep(0.05)
    raise AssertionError(f"job tidak selesai: {jh.keadaan()}")


class Palsu:
    """Ganti jh._luncurkan: catat argumen, jalankan proses python kecil sesuai flag."""

    def __init__(self, gagal=(), blok=()):
        self.panggilan, self.gagal, self.blok = [], set(gagal), set(blok)

    def __call__(self, argumen, env):
        self.panggilan.append((list(argumen), dict(env)))
        flag = " ".join(argumen[2:])
        if any(b in flag for b in self.blok):
            kode = "import time; print('mulai', flush=True); time.sleep(60)"
        elif any(g in flag for g in self.gagal):
            kode = "import sys; print('ERROR palsu'); sys.exit(1)"
        else:
            kode = "print('ok palsu')"
        return subprocess.Popen([sys.executable, "-c", kode], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8")

    def flag_main(self):
        """Flag tiap panggilan main.py (tanpa python & path skrip), urut."""
        return [a[2:] for a, _ in self.panggilan if Path(a[1]).name == "main.py"]


def _reset():
    jh._job = None
    jh._proses = None


def uji_validasi_pilihan():
    _reset()
    for langkah, judul in ((["Recheck stok"], "TIPE 9"), (["Tidak ada"], "TIPE 1"), ([], "TIPE 1"),
                           ("Recheck stok", "TIPE 1"), ([1], "TIPE 1")):
        try:
            jh.mulai(langkah, judul)
        except jh.HarianError:
            pass
        else:
            raise AssertionError(f"harus ditolak: {langkah!r} {judul!r}")
    assert jh._job is None
    print("  mulai(): judul/langkah tak dikenal, kosong, bukan daftar -> ditolak, tidak ada job")


def uji_malam_menolak_langkah_iresis():
    _reset()
    palsu = Palsu()
    with mock.patch.object(jh, "_luncurkan", palsu), mock.patch.object(jh, "_sesi_label", return_value="x/1"):
        try:
            jh.mulai(["Urgent Lazada", "Upload faktur & pesanan ke IRESIS"], "MALAM")
        except jh.HarianError as e:
            assert "IRESIS" in str(e)
        else:
            raise AssertionError("MALAM harus menolak langkah IRESIS")
    assert jh._job is None and not palsu.panggilan
    print("  MALAM: langkah IRESIS ditolak sebelum proses apa pun jalan")


def uji_urutan_katalog_flag_jalankan_dan_lewati_malam():
    _reset()
    palsu = Palsu()
    with mock.patch.object(jh, "_luncurkan", palsu), mock.patch.object(jh, "_sesi_label", return_value="2026-10-08/7"):
        # dikirim acak: urutan harus mengikuti KATALOG
        jh.mulai(["Upload faktur & pesanan ke IRESIS", "SPX-J&T Spesial", "Urgent Lazada", "Recheck stok"], "TIPE 1")
        j = _tunggu()
    assert j["status"] == "selesai", j
    assert [x["nama"] for x in j["langkah"]] == ["Recheck stok", "Urgent Lazada", "SPX-J&T Spesial", "Upload faktur & pesanan ke IRESIS"]
    assert palsu.flag_main() == [
        ["--recheck-stok", "--jalankan"],
        ["--urgent", "--channel", "lazada", "--jalankan", "--lewati-malam"],   # TIPE 1 -> lewati malam
        ["--label", "--tanpa-reguler", "--jalankan"],
        ["--upload-iresis", "--jalankan"]], palsu.flag_main()
    assert all(env["LABEL_SESI_DIR"] == "2026-10-08/7" for _, env in palsu.panggilan)
    rekap = palsu.panggilan[-1][0]
    assert Path(rekap[1]).name == "rekap_waktu.py" and rekap[2] == "TIPE 1", rekap
    assert len(rekap) == 3 + 4 and rekap[3].startswith("RECHECK STOK:"), rekap
    assert any(l.startswith("=== 2/4 URGENT LAZADA") for l in j["lines"]), j["lines"]

    # MALAM & TIPE 2: urgent TANPA --lewati-malam
    for judul in ("MALAM", "TIPE 2"):
        _reset()
        palsu = Palsu()
        with mock.patch.object(jh, "_luncurkan", palsu), mock.patch.object(jh, "_sesi_label", return_value="x/1"):
            jh.mulai(["Urgent GTL & SiCepat"], judul)
            _tunggu()
        assert palsu.flag_main() == [["--urgent", "--channel", "gtl-sicepat", "--jalankan"]], (judul, palsu.flag_main())
    print("  urutan = KATALOG, tiap langkah 1 proses main.py --jalankan, --lewati-malam hanya TIPE 1, "
          "LABEL_SESI_DIR & rekap waktu benar")


def uji_langkah_gagal_tidak_menghentikan_berikutnya():
    _reset()
    palsu = Palsu(gagal=["--sampel"])
    with mock.patch.object(jh, "_luncurkan", palsu), mock.patch.object(jh, "_sesi_label", return_value="x/1"):
        jh.mulai(["Recheck stok", "Sampel TikTok (nilai 0)", "Upload faktur & pesanan ke IRESIS"], "KUSTOM")
        j = _tunggu()
    status = [(x["nama"], x["status"]) for x in j["langkah"]]
    assert status == [("Recheck stok", "selesai"), ("Sampel TikTok (nilai 0)", "gagal"),
                      ("Upload faktur & pesanan ke IRESIS", "selesai")], status
    assert j["status"] == "gagal" and len(palsu.flag_main()) == 3
    assert any("ERROR palsu" in l for l in j["lines"])
    print("  langkah gagal: berikutnya tetap jalan (seperti .bat), status job 'gagal', log tersimpan")


def uji_satu_job_sekaligus_dan_hentikan():
    _reset()
    palsu = Palsu(blok=["--recheck-stok"])
    with mock.patch.object(jh, "_luncurkan", palsu), mock.patch.object(jh, "_sesi_label", return_value="x/1"):
        jh.mulai(["Recheck stok", "Sampel TikTok (nilai 0)"], "TIPE 3")
        _tunggu(lambda j: any("mulai" in l for l in j["lines"]))
        try:
            jh.mulai(["Recheck stok"], "TIPE 3")
        except jh.HarianError as e:
            assert "berjalan" in str(e)
        else:
            raise AssertionError("job kedua harus ditolak")
        assert jh.info is not None and jh.hentikan() is True
        j = _tunggu()
    assert j["status"] == "dihentikan", j["status"]
    assert [x["status"] for x in j["langkah"]] == ["gagal", "antri"], j["langkah"]   # sisa tidak dijalankan
    assert len(palsu.flag_main()) == 1 and not any(Path(a[1]).name == "rekap_waktu.py" for a, _ in palsu.panggilan)
    assert jh.hentikan() is False      # tidak ada job berjalan lagi
    print("  satu job sekaligus, hentikan: langkah berjalan dimatikan, sisa dibatalkan, tanpa rekap")


def uji_keadaan_lines_bertahap():
    _reset()
    assert jh.keadaan()["status"] == "kosong"
    palsu = Palsu()
    with mock.patch.object(jh, "_luncurkan", palsu), mock.patch.object(jh, "_sesi_label", return_value="x/1"):
        jh.mulai(["Recheck stok"], "TIPE 1")
        j = _tunggu()
    total = j["total"]
    assert total == len(j["lines"]) and total >= 3
    sisa = jh.keadaan(total - 2)
    assert sisa["lines"] == j["lines"][-2:] and sisa["total"] == total
    assert jh.keadaan(total)["lines"] == []
    print("  keadaan(dari): baris log diambil bertahap berdasarkan indeks")


def uji_katalog_diterima_argparse_dan_sama_dengan_bat():
    """Setiap langkah KATALOG diuji lewat argparse main.py SUNGGUHAN (berhenti sebelum login) dan
    harus punya padanan persis (himpunan flag) di proses-harian.bat atau proses-malam.bat, supaya
    UI tidak menyimpang dari .bat kalau salah satunya diubah."""
    import re
    import shlex
    import main as m

    class Berhenti(Exception):
        pass

    pola = re.compile(r'^"\.venv\\Scripts\\python\.exe" src\\main\.py (.*)$')
    himpunan_bat = set()
    for nama in ("proses-harian.bat", "proses-malam.bat"):
        for baris in (ROOT / "bat" / nama).read_text(encoding="utf-8").splitlines():
            cocok = pola.match(baris)
            if cocok:
                token = [t for t in shlex.split(cocok.group(1), posix=False) if t not in ("--jalankan", "--lewati-malam")]
                himpunan_bat.add(frozenset(token))
    for nama, flag in jh.KATALOG:
        assert frozenset(flag) in himpunan_bat, f"{nama}: {flag} tidak ada di .bat"
        argumen = [*flag, "--jalankan"] + (["--lewati-malam"] if flag[:1] == ["--urgent"] else [])
        with mock.patch.object(sys, "argv", ["main.py", *argumen]),                 mock.patch.object(m, "muat_env", side_effect=Berhenti):
            try:
                m._main()
            except Berhenti:
                pass
            except SystemExit as e:
                raise AssertionError(f"{nama}: argparse menolak {argumen} (exit {e.code})")
    print(f"  {len(jh.KATALOG)} langkah KATALOG: diterima argparse main.py & ada padanannya di .bat")


def uji_info_tidak_menggandakan_picklist_terhenti():
    """Peringatan 'gagal' di UI tidak memuat picklist TERHENTI (sudah punya bagian Gagal unduh
    PDF yang bisa di-download ulang); kegagalan lain tetap tampil."""
    import tempfile
    import peringatan_gagal as pg

    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(jh, "FOLDER_LOG", Path(tmp)):
        pg.atur_folder(Path(tmp))
        pg.catat("PICK-000000001: TERHENTI: timeout unduh. Lanjutkan: .\\jalankan.bat --lanjut x")
        pg.catat("UPLOAD IRESIS: GAGAL (faktur): koneksi putus")
        try:
            gagal = jh.info()["peringatan"]["gagal"]
        finally:
            pg._file_peringatan = None
    assert len(gagal) == 1 and "IRESIS" in gagal[0], gagal
    print("  info(): picklist TERHENTI disaring dari 'gagal', kegagalan lain tetap")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
