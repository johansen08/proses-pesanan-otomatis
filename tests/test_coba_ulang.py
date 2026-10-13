"""Uji coba_ulang.py (percobaan ulang otomatis picklist gagal di akhir tiap TIPE) - TANPA
menyentuh Jubelio: `main.py --lanjut` ditiru, log ditulis ke folder sementara.

Jalankan:  .venv\\Scripts\\python tests\\test_coba_ulang.py
"""
import shlex
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import coba_ulang  # noqa: E402
import menu_konsol as mk  # noqa: E402
import peringatan_gagal  # noqa: E402

SESI = Path("label-pengiriman/2026-10-13/4")


def _siapkan():
    folder = Path(tempfile.mkdtemp())
    coba_ulang.FOLDER_LOG = folder
    peringatan_gagal.atur_folder(folder)
    return folder


def uji_hanya_gagal_sejak_awal_yang_dicoba_sekali():
    _siapkan()
    peringatan_gagal.catat_terhenti("PICK-1", "SKU-A", SESI, "timeout unduh PDF", tag="SPESIAL")
    peringatan_gagal.catat_dibuat("PICK-2", "SKU-B", SESI)          # yatim: tidak dicoba
    peringatan_gagal.catat_terhenti("PICK-3", "SKU-C", SESI, "x", subfolder="SATUAN")
    peringatan_gagal.tandai_selesai("PICK-3")                       # sudah beres
    dipanggil = []

    def jalan(argumen):
        dipanggil.append(argumen)
        return 0

    assert coba_ulang.jalankan(0, True, jalan, lambda *_: None) == (0, 0) and not dipanggil   # uji
    assert coba_ulang.jalankan(9e12, False, jalan, lambda *_: None) == (0, 0)                 # terlalu baru
    assert coba_ulang.jalankan(0, False, jalan, lambda *_: None) == (1, 1)
    assert len(dipanggil) == 1
    a = dipanggil[0]
    assert a[2:5] == ["--lanjut", "PICK-1", "--nama"] and "--tag" in a and "--jalankan" in a, a
    assert a[a.index("--sesi") + 1] == "2026-10-13/4", a
    print("  hanya picklist gagal sejak awal TIPE, bukan yatim/selesai, bukan mode uji")


def uji_gagal_lagi_tidak_diulang_dan_dihitung():
    _siapkan()
    peringatan_gagal.catat_terhenti("PICK-1", "A", SESI, "x")
    peringatan_gagal.catat_terhenti("PICK-2", "B", SESI, "x")
    kode = iter([1, 0])
    teks = []
    dicoba, pulih = coba_ulang.jalankan(0, False, lambda a: next(kode), lambda t="": teks.append(t))
    assert (dicoba, pulih) == (2, 1) and any("PICK-1 masih gagal" in t for t in teks), teks
    print("  gagal lagi hanya dicoba sekali & dilaporkan")


def uji_peringatan_yang_sudah_pulih_hilang_dari_rekap():
    _siapkan()
    peringatan_gagal.catat("PICK-1: TERHENTI: timeout")
    peringatan_gagal.catat("PICK-2: TERHENTI: timeout")
    peringatan_gagal.catat("SKU-X: GAGAL sebelum picklist dibuat: err")
    assert len(peringatan_gagal.baca_belum_pulih(0)) == 3
    peringatan_gagal.tandai_selesai("PICK-1")
    sisa = peringatan_gagal.baca_belum_pulih(0)
    assert len(sisa) == 2 and not any("PICK-1" in s for s in sisa), sisa
    print("  baca_belum_pulih membuang peringatan picklist yang sudah selesai")


def uji_menu_konsol_menjalankan_coba_ulang_sebelum_rekap():
    _siapkan()
    peringatan_gagal.catat_terhenti("PICK-9", "SKU-Z", SESI, "timeout")
    panggilan = []

    def jalankan(argumen, env):
        panggilan.append(list(argumen))
        return 0

    waktu = mk.jalankan_tipe("TIPE 3", False, "2026-10-13/4", jalankan=jalankan,
                             sekarang=iter(range(1000, 9999)).__next__, cetak=lambda *_: None)
    nama_skrip = [Path(a[1]).name for a in panggilan]
    assert nama_skrip[-1] == "rekap_waktu.py" and "--lanjut" in panggilan[-2], panggilan[-2:]
    assert waktu[-1].startswith("COBA ULANG GAGAL:"), waktu[-1]
    assert "COBA ULANG GAGAL" in shlex.join(panggilan[-1])
    panggilan.clear()
    mk.jalankan_tipe("TIPE 3", True, "2026-10-13/4", jalankan=jalankan,       # uji: tanpa coba ulang
                     sekarang=iter(range(1000, 9999)).__next__, cetak=lambda *_: None)
    assert not any("--lanjut" in a for a in panggilan)
    print("  menu konsol: coba ulang jalan setelah semua langkah, sebelum rekap; mode uji tidak")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
