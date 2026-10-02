"""Uji print_spesial.py (bagian logika murni - pencarian folder sesi & penyaringan
label SPESIAL di subfolder SPESIAL folder sesi). Bagian yang menjalankan
SumatraPDF/subprocess sungguhan TIDAK diuji di sini (perlu SumatraPDF + printer
sungguhan).

Jalankan:  .venv\\Scripts\\python tests\\test_print_spesial.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import print_spesial as ps  # noqa: E402


def _buat(folder: Path, *nama: str) -> None:
    for n in nama:
        (folder / n).write_bytes(b"%PDF-1.4")


def uji_folder_sesi_terbaru_pilih_tanggal_lalu_nomor_terbesar():
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp)
        for tanggal, nomor in (("2026-09-30", "1"), ("2026-09-30", "9"), ("2026-09-30", "10"),
                               ("2026-10-01", "1"), ("2026-10-01", "2")):
            (label / tanggal / nomor).mkdir(parents=True)
        (label / "bukan-folder-sesi").mkdir()
        (label / "bukan-folder.txt").write_text("x")
        terbaru = ps.folder_sesi_terbaru(label)
        assert terbaru.name == "2" and terbaru.parent.name == "2026-10-01", terbaru
        print("  folder_sesi_terbaru: pilih tanggal terbaru lalu nomor urut terbesar")


def uji_folder_sesi_terbaru_bandingkan_nomor_sebagai_angka_bukan_teks():
    with tempfile.TemporaryDirectory() as tmp:
        label = Path(tmp)
        for nomor in ("2", "10"):
            (label / "2026-10-01" / nomor).mkdir(parents=True)
        terbaru = ps.folder_sesi_terbaru(label)
        assert terbaru.name == "10", terbaru.name   # bukan "2" (perbandingan teks)
        print("  folder_sesi_terbaru: 10 > 2 (dibandingkan sebagai angka)")


def uji_folder_sesi_terbaru_tidak_ada_folder_sesi():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            ps.folder_sesi_terbaru(Path(tmp))
        except ps.CetakError:
            pass
        else:
            raise AssertionError("seharusnya CetakError kalau tidak ada folder sesi")
        print("  folder_sesi_terbaru: CetakError kalau folder label kosong/tidak ada sesi")


def uji_daftar_label_spesial_hanya_bertanda_spesial_urut_nomor_pick():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "SPESIAL"
        subfolder.mkdir()
        _buat(subfolder,
             "PICK-000155622_SPESIAL_TRC4_2026-10-01_080320.pdf",
             "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf",
             "PICK-000155700_SPESIAL_TRC9_2026-10-01_090000.pdf",
             "catatan.txt")
        _buat(folder,
             "PICK-000155999_1QTY-REGULER_2026-10-01_091500.pdf",   # bukan spesial, di folder sesi
             "PICK-000156000_KOMBINASI-REGULER_2026-10-01_091600.pdf")   # bukan spesial
        hasil = ps.daftar_label_spesial(folder)
        assert [f.name for f in hasil] == [
            "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf",
            "PICK-000155622_SPESIAL_TRC4_2026-10-01_080320.pdf",
            "PICK-000155700_SPESIAL_TRC9_2026-10-01_090000.pdf",
        ], [f.name for f in hasil]
        print("  daftar_label_spesial: hanya file _SPESIAL_ di subfolder SPESIAL, urut nomor PICK naik")


def uji_daftar_label_spesial_folder_kosong():
    with tempfile.TemporaryDirectory() as tmp:
        assert ps.daftar_label_spesial(Path(tmp)) == []
        print("  daftar_label_spesial: list kosong kalau tidak ada label spesial")


def uji_cari_nomor_terlompat_berurut_sempurna():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "SPESIAL"
        subfolder.mkdir()
        _buat(subfolder,
             "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf",
             "PICK-000155622_SPESIAL_TRC4_2026-10-01_080320.pdf",
             "PICK-000155623_SPESIAL_TRC9_2026-10-01_090000.pdf")
        file_pdf = ps.daftar_label_spesial(folder)
        assert ps.cari_nomor_terlompat(file_pdf) == []
        print("  cari_nomor_terlompat: list kosong kalau nomor PICK berurut sempurna")


def uji_cari_nomor_terlompat_ada_yang_hilang():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "SPESIAL"
        subfolder.mkdir()
        _buat(subfolder,
             "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf",
             "PICK-000155622_SPESIAL_TRC4_2026-10-01_080320.pdf",
             "PICK-000155625_SPESIAL_TRC9_2026-10-01_090000.pdf")
        file_pdf = ps.daftar_label_spesial(folder)
        assert ps.cari_nomor_terlompat(file_pdf) == [155623, 155624]
        print("  cari_nomor_terlompat: deteksi nomor PICK yang hilang di tengah")


def uji_cari_nomor_terlompat_kurang_dari_2_file():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "SPESIAL"
        subfolder.mkdir()
        _buat(subfolder, "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf")
        file_pdf = ps.daftar_label_spesial(folder)
        assert ps.cari_nomor_terlompat(file_pdf) == []
        assert ps.cari_nomor_terlompat([]) == []
        print("  cari_nomor_terlompat: list kosong kalau <2 file (tidak ada rentang untuk dicek)")


def uji_simpan_dan_baca_daftar_gagal_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        gagal = [folder / "a.pdf", folder / "b.pdf"]
        for f in gagal:
            f.write_bytes(b"%PDF-1.4")
        ps.FOLDER_LOG = folder / "logs"
        file_daftar = ps.simpan_daftar_gagal(gagal)
        assert file_daftar.is_file()
        dibaca = ps.baca_daftar_ulang(file_daftar)
        assert [p.name for p in dibaca] == ["a.pdf", "b.pdf"], dibaca
        print("  simpan_daftar_gagal + baca_daftar_ulang: roundtrip cocok, urutan dipertahankan")


def uji_baca_daftar_ulang_lewati_file_yang_sudah_tidak_ada():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        ada = folder / "ada.pdf"
        ada.write_bytes(b"%PDF-1.4")
        file_daftar = folder / "daftar.txt"
        file_daftar.write_text(f"{ada}\n{folder / 'sudah-dihapus.pdf'}\n", encoding="utf-8")
        hasil = ps.baca_daftar_ulang(file_daftar)
        assert [p.name for p in hasil] == ["ada.pdf"], hasil
        print("  baca_daftar_ulang: file yang sudah tidak ada dilewati, bukan error")


def uji_baca_daftar_ulang_file_tidak_ada():
    try:
        ps.baca_daftar_ulang(Path("tidak-ada-file-ini.txt"))
    except ps.CetakError:
        pass
    else:
        raise AssertionError("seharusnya CetakError kalau file daftar tidak ditemukan")
    print("  baca_daftar_ulang: CetakError kalau file daftar sendiri tidak ditemukan")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
