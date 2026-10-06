"""Uji fungsi murni/filesystem di main.py (bukan alur CLI penuh - itu sudah dicakup
lewat test_proses_label.py & test_sku_spesial.py untuk bagian yang dipanggilnya).

Jalankan:  .venv\\Scripts\\python tests\\test_main.py
"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main as m  # noqa: E402


# -------------------------------------------------- dalam_jam_menu()
def _jam(h, mnt=0):
    return datetime(2026, 9, 29, h, mnt)


def uji_dalam_jam_menu_tipe1_melingkupi_tengah_malam():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(23, 30)
        assert m.dalam_jam_menu("1") is True
        dt.now.return_value = _jam(6, 59)
        assert m.dalam_jam_menu("1") is True
        dt.now.return_value = _jam(13, 0)
        assert m.dalam_jam_menu("1") is False
    print("  TIPE 1: valid 16.00-24.00 dan 00.00-12.00 (melingkupi tengah malam), tidak di jam 13.00")


def uji_dalam_jam_menu_tipe2_dan_tipe3_tumpang_tindih_sengaja():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(13, 30)
        assert m.dalam_jam_menu("2") is True and m.dalam_jam_menu("3") is True
        dt.now.return_value = _jam(14, 30)
        assert m.dalam_jam_menu("2") is False and m.dalam_jam_menu("3") is True
    print("  TIPE 2 & 3: tumpang tindih sengaja di jam 13.00-13.59, lalu hanya TIPE 3 sampai 14.59")


def uji_dalam_jam_menu_jam_istirahat_12_sampai_13_tidak_ada_menu_valid():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(12, 30)
        assert not any(m.dalam_jam_menu(x) for x in "1234")
    print("  jam istirahat 12.00-13.00: sengaja tidak ada TIPE menu yang valid")


def uji_dalam_jam_menu_tipe4():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(15, 30)
        assert m.dalam_jam_menu("4") is True
        dt.now.return_value = _jam(16, 0)
        assert m.dalam_jam_menu("4") is False
    print("  TIPE 4: valid persis 15.00-15.59")


# -------------------------------------------------- muat_env()
def uji_muat_env_parsing_dasar():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / ".env"
        f.write_text(
            "# komentar diabaikan\n"
            "\n"
            'JUBELIO_EMAIL="a@b.com"\n'
            "JUBELIO_PASSWORD='rahasia'\n"
            "TANPA_KUTIP=nilai biasa\n",
            encoding="utf-8",
        )
        import os
        for k in ("JUBELIO_EMAIL", "JUBELIO_PASSWORD", "TANPA_KUTIP"):
            os.environ.pop(k, None)
        m.muat_env(f)
        assert os.environ["JUBELIO_EMAIL"] == "a@b.com"
        assert os.environ["JUBELIO_PASSWORD"] == "rahasia"
        assert os.environ["TANPA_KUTIP"] == "nilai biasa"
        for k in ("JUBELIO_EMAIL", "JUBELIO_PASSWORD", "TANPA_KUTIP"):
            os.environ.pop(k, None)
    print("  muat_env: baca KUNCI=nilai, lewati komentar/baris kosong, buang kutip di nilai")


def uji_muat_env_tidak_timpa_env_yang_sudah_ada():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / ".env"
        f.write_text("JUBELIO_EMAIL=dari_file\n", encoding="utf-8")
        os.environ["JUBELIO_EMAIL"] = "dari_environment_asli"
        try:
            m.muat_env(f)
            assert os.environ["JUBELIO_EMAIL"] == "dari_environment_asli"
        finally:
            os.environ.pop("JUBELIO_EMAIL", None)
    print("  muat_env: environment variable yang sudah ada tidak ditimpa nilai dari .env")


def uji_muat_env_file_tidak_ada_tidak_error():
    m.muat_env(Path("file-env-tidak-pernah-ada.env"))
    print("  muat_env: file .env tidak ada -> tidak error, dilewati saja")


# -------------------------------------------------- sesi_label_baru() / folder_label_sesi()
def uji_sesi_label_baru_nomor_urut_bertambah():
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(m, "FOLDER_LABEL", Path(tmp)), \
             mock.patch.object(m, "datetime") as dt:
            dt.now.return_value = datetime(2026, 9, 30)
            n1 = m.sesi_label_baru()
            n2 = m.sesi_label_baru()
            assert n1 == "2026-09-30/1" and n2 == "2026-09-30/2", (n1, n2)
            assert (Path(tmp) / n1).is_dir() and (Path(tmp) / n2).is_dir()
    print("  sesi_label_baru: nomor urut bertambah per panggilan untuk tanggal yang sama")


def uji_sesi_label_baru_abaikan_folder_bukan_pola_sesi():
    with tempfile.TemporaryDirectory() as tmp:
        folder_tanggal = Path(tmp) / "2026-09-30"
        folder_tanggal.mkdir()
        (folder_tanggal / "5").mkdir()
        (folder_tanggal / "folder-lain").mkdir()
        (folder_tanggal / "bukan_angka").mkdir()
        with mock.patch.object(m, "FOLDER_LABEL", Path(tmp)), \
             mock.patch.object(m, "datetime") as dt:
            dt.now.return_value = datetime(2026, 9, 30)
            nama = m.sesi_label_baru()
        assert nama == "2026-09-30/6", nama
    print("  sesi_label_baru: folder yang tidak cocok pola sesi diabaikan, lanjut dari nomor "
          "tertinggi yang valid")


def uji_folder_label_sesi_pakai_env_jika_ada():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(m, "FOLDER_LABEL", Path(tmp)):
            os.environ["LABEL_SESI_DIR"] = "2026-09-30/7"
            try:
                folder = m.folder_label_sesi()
            finally:
                os.environ.pop("LABEL_SESI_DIR", None)
            assert folder == Path(tmp) / "2026-09-30" / "7" and folder.is_dir()
    print("  folder_label_sesi: pakai LABEL_SESI_DIR dari environment kalau ada, bukan bikin sesi baru")


def uji_sesi_valid_untuk_opsi_lanjut():
    import argparse
    assert m._sesi_valid("2026-10-06/12") == "2026-10-06/12"
    assert m._sesi_valid("2026-10-06\\12\\") == "2026-10-06/12"     # disalin dari Explorer
    for salah in ("12", "2026-10-06", "../2026-10-06/12", "2026-10-06/12/SPESIAL", "x/1"):
        try:
            m._sesi_valid(salah)
        except argparse.ArgumentTypeError:
            continue
        raise AssertionError(f"--sesi {salah!r} seharusnya ditolak")
    print("  --sesi: hanya menerima pola folder sesi YYYY-MM-DD/N")


def uji_peringatan_picklist_terlompat():
    import peringatan_picklist as pp
    with tempfile.TemporaryDirectory() as tmp:
        pp.atur_folder(Path(tmp))
        pp._sesi.clear()
        assert pp.periksa_nomor("PICK-000155661") is None      # pertama kali: belum ada pembanding
        assert pp.ambil_nomor_hilang() == []
        assert pp.periksa_nomor("PICK-000155662") is None      # berurutan: aman
        assert pp.ambil_nomor_hilang() == []
        pesan = pp.periksa_nomor("PICK-000155665")
        assert pesan and "PICK-000155663" in pesan and "PICK-000155664" in pesan, pesan
        assert pp.ambil_nomor_hilang() == [155663, 155664]
        assert pp.periksa_nomor("PICK-000155666") is None
        assert pp.ambil_nomor_hilang() == []       # ditimpa kosong lagi setelah berurutan
        assert len(pp._sesi) == 1
        assert len(pp.baca_sejak(0)) == 1 and pp.baca_sejak(9e12) == []
    pp._file_terakhir = pp._file_peringatan = None
    print("  peringatan_picklist: nomor terlompat terdeteksi & tersimpan, berurutan tidak dianggap")


def uji_peringatan_resi_tanpa_resi():
    import peringatan_resi as pr
    with tempfile.TemporaryDirectory() as tmp:
        pr.atur_folder(Path(tmp))
        pr._sesi.clear()
        pr.catat_tanpa_resi("PICK-000154839", "T01-BSBI-5", [])
        assert pr._sesi == [], "tidak ada pesanan tanpa resi: tidak perlu dicatat"
        pr.catat_tanpa_resi("PICK-000154839", "T01-BSBI-5", ["SO9068180", "SO9068214"])
        assert len(pr._sesi) == 1
        pesan = pr._sesi[0]
        assert "PICK-000154839" in pesan and "SO9068180" in pesan and "SO9068214" in pesan, pesan
        assert len(pr.baca_sejak(0)) == 1 and pr.baca_sejak(9e12) == []
    pr._file_peringatan = None
    print("  peringatan_resi: pesanan tanpa resi (bukan batal) dicatat untuk diinformasikan ke CS")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
