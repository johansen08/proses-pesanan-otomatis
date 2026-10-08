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
        hasil = ps.daftar_label(folder, "spesial")
        assert [f.name for f in hasil] == [
            "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf",
            "PICK-000155622_SPESIAL_TRC4_2026-10-01_080320.pdf",
            "PICK-000155700_SPESIAL_TRC9_2026-10-01_090000.pdf",
        ], [f.name for f in hasil]
        print("  daftar_label_spesial: hanya file _SPESIAL_ di subfolder SPESIAL, urut nomor PICK naik")


def uji_daftar_label_spesial_gabung_folder_jnt_spx_dan_gabungan():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder_gabungan = folder / "SPESIAL"
        subfolder_gabungan.mkdir()
        _buat(subfolder_gabungan, "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf")
        subfolder_jnt = folder / "JNT_SPESIAL"
        subfolder_jnt.mkdir()
        _buat(subfolder_jnt, "PICK-000155622_JNT_SPESIAL_TRC4_2026-10-01_080320.pdf")
        subfolder_spx = folder / "SPX_SPESIAL"
        subfolder_spx.mkdir()
        _buat(subfolder_spx, "PICK-000155700_SPX_SPESIAL_TRC9_2026-10-01_090000.pdf")
        hasil = ps.daftar_label(folder, "spesial")
        assert [f.name for f in hasil] == [
            "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf",
            "PICK-000155622_JNT_SPESIAL_TRC4_2026-10-01_080320.pdf",
            "PICK-000155700_SPX_SPESIAL_TRC9_2026-10-01_090000.pdf",
        ], [f.name for f in hasil]
        print("  daftar_label_spesial: subfolder SPESIAL (gabungan), JNT_SPESIAL, SPX_SPESIAL "
              "(dari --kurir) semuanya ikut dicari & digabung, urut nomor PICK naik")


def uji_daftar_label_spesial_folder_kosong():
    with tempfile.TemporaryDirectory() as tmp:
        assert ps.daftar_label(Path(tmp), "spesial") == []
        print("  daftar_label_spesial: list kosong kalau tidak ada label spesial")


def uji_daftar_label_gtl_sicepat_hanya_file_gtl_sicepat():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "URGENT"
        subfolder.mkdir()
        _buat(subfolder,
             "PICK-000155622_GTL-SICEPAT-LANTAI2_2026-10-01_080320.pdf",
             "PICK-000155621_LAZADA_2026-10-01_080302.pdf",
             "catatan.txt")
        _buat(folder, "PICK-000155999_1QTY-REGULER-2A_2026-10-01_091500.pdf")
        _buat(subfolder, "PICK-000155620_GTL-SICEPAT-LANTAI1_2026-10-01_080250.pdf")
        hasil = ps.daftar_label(folder, "gtl-sicepat")
        assert [f.name for f in hasil] == [
            "PICK-000155620_GTL-SICEPAT-LANTAI1_2026-10-01_080250.pdf",
            "PICK-000155622_GTL-SICEPAT-LANTAI2_2026-10-01_080320.pdf",
        ], [f.name for f in hasil]
        semua = ps.daftar_label(folder, "gtl-sicepat", saring_nama=False)
        assert len(semua) == 3, [f.name for f in semua]
        print("  daftar_label(gtl-sicepat): hanya PDF GTL-SICEPAT di subfolder URGENT (Lazada "
             "tidak ikut), urut nomor PICK naik, file di folder sesi (bukan subfolder) diabaikan")


def uji_daftar_label_gtl_sicepat_tidak_ada_varian_kurir():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "JNT_URGENT").mkdir()
        _buat(folder / "JNT_URGENT", "PICK-000155621_GTL-SICEPAT-LANTAI1_2026-10-01_080302.pdf")
        assert ps.daftar_label(folder, "gtl-sicepat") == []
        print("  daftar_label(gtl-sicepat): subfolder JNT_URGENT TIDAK dicari (tidak "
             "punya varian kurir)")


def uji_daftar_label_satuan_gabung_variasi_kurir():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "SATUAN").mkdir()
        _buat(folder / "SATUAN", "PICK-000155621_1QTY-REGULER-2A_2026-10-01_080302.pdf")
        (folder / "JNT_SATUAN").mkdir()
        _buat(folder / "JNT_SATUAN",
             "PICK-000155622_JNT-1QTY-REGULER-3A_2026-10-01_080320.pdf")
        (folder / "SPX_SATUAN").mkdir()
        _buat(folder / "SPX_SATUAN",
             "PICK-000155700_SPX-1QTY-REGULER-LAINNYA_2026-10-01_090000.pdf")
        hasil = ps.daftar_label(folder, "satuan")
        assert [f.name for f in hasil] == [
            "PICK-000155621_1QTY-REGULER-2A_2026-10-01_080302.pdf",
            "PICK-000155622_JNT-1QTY-REGULER-3A_2026-10-01_080320.pdf",
            "PICK-000155700_SPX-1QTY-REGULER-LAINNYA_2026-10-01_090000.pdf",
        ], [f.name for f in hasil]
        print("  daftar_label(satuan): subfolder SATUAN + JNT_SATUAN + SPX_SATUAN "
             "digabung, urut nomor PICK naik")


def uji_daftar_label_kombinasi_gabung_variasi_kurir():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "KOMBINASI").mkdir()
        _buat(folder / "KOMBINASI",
             "PICK-000155621_KOMBINASI-REGULER-LANTAI1_2026-10-01_080302.pdf")
        (folder / "SPX_KOMBINASI").mkdir()
        _buat(folder / "SPX_KOMBINASI",
             "PICK-000155622_SPX-KOMBINASI-REGULER-LANTAI2_2026-10-01_080320.pdf")
        hasil = ps.daftar_label(folder, "kombinasi")
        assert [f.name for f in hasil] == [
            "PICK-000155621_KOMBINASI-REGULER-LANTAI1_2026-10-01_080302.pdf",
            "PICK-000155622_SPX-KOMBINASI-REGULER-LANTAI2_2026-10-01_080320.pdf",
        ], [f.name for f in hasil]
        print("  daftar_label(kombinasi): subfolder KOMBINASI + SPX_KOMBINASI digabung, "
             "urut nomor PICK naik")


def uji_daftar_label_per_kurir_hanya_subfolder_kurir_itu():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for sub, nama in (("JNT_SPESIAL", "PICK-000155622_JNT_SPESIAL_TRC4_2026-10-01_080320.pdf"),
                          ("SPX_SPESIAL", "PICK-000155700_SPX_SPESIAL_TRC9_2026-10-01_090000.pdf"),
                          ("JNT_SATUAN", "PICK-000155800_JNT-1QTY-REGULER-2A_2026-10-01_091500.pdf"),
                          ("SPX_SATUAN", "PICK-000155801_SPX-1QTY-REGULER-2A_2026-10-01_091600.pdf"),
                          ("JNT_KOMBINASI", "PICK-000155900_JNT-KOMBINASI-REGULER-LANTAI1_2026-10-01_092000.pdf"),
                          ("SPX_KOMBINASI", "PICK-000155901_SPX-KOMBINASI-REGULER-LANTAI1_2026-10-01_092100.pdf"),
                          ("SPX_PAGI", "PICK-000156000_SHOPEE-PAGI-LANTAI1_2026-10-01_130000.pdf"),
                          ("JNT_SIANG", "PICK-000156100_JNT-SIANG-LANTAI2_2026-10-01_150000.pdf")):
            (folder / sub).mkdir()
            _buat(folder / sub, nama)
        harapan = {
            "spesial-jnt": ["PICK-000155622_JNT_SPESIAL_TRC4_2026-10-01_080320.pdf"],
            "spesial-spx": ["PICK-000155700_SPX_SPESIAL_TRC9_2026-10-01_090000.pdf"],
            "satuan-jnt": ["PICK-000155800_JNT-1QTY-REGULER-2A_2026-10-01_091500.pdf"],
            "satuan-spx": ["PICK-000155801_SPX-1QTY-REGULER-2A_2026-10-01_091600.pdf"],
            "kombinasi-jnt": ["PICK-000155900_JNT-KOMBINASI-REGULER-LANTAI1_2026-10-01_092000.pdf"],
            "kombinasi-spx": ["PICK-000155901_SPX-KOMBINASI-REGULER-LANTAI1_2026-10-01_092100.pdf"],
            "spx-pagi": ["PICK-000156000_SHOPEE-PAGI-LANTAI1_2026-10-01_130000.pdf"],
            "jnt-siang": ["PICK-000156100_JNT-SIANG-LANTAI2_2026-10-01_150000.pdf"],
        }
        for jenis, nama in harapan.items():
            hasil = [f.name for f in ps.daftar_label(folder, jenis)]
            assert hasil == nama, (jenis, hasil)
        # jenis gabungan tetap menggabung kedua kurir
        assert len(ps.daftar_label(folder, "spesial")) == 2
        assert len(ps.daftar_label(folder, "satuan")) == 2
        assert len(ps.daftar_label(folder, "kombinasi")) == 2
        print("  daftar_label per kurir/spx-pagi/jnt-siang: hanya subfolder masing-masing; "
              "jenis gabungan tetap menggabung J&T+SPX")


def uji_nomor_terlompat_abaikan_nomor_yang_ada_di_jenis_kurir_lain():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for sub, nama in (("JNT_SPESIAL", "PICK-000000100_JNT_SPESIAL_A_2026-10-01_080000.pdf"),
                          ("SPX_SPESIAL", "PICK-000000101_SPX_SPESIAL_B_2026-10-01_080100.pdf"),
                          ("JNT_SPESIAL", "PICK-000000102_JNT_SPESIAL_C_2026-10-01_080200.pdf"),
                          ("SATUAN", "PICK-000000103_1QTY_2026-10-01_080300.pdf")):
            (folder / sub).mkdir(exist_ok=True)
            _buat(folder / sub, nama)
        jnt = ps.daftar_label(folder, "spesial-jnt", saring_nama=False)
        assert ps.cari_nomor_terlompat(jnt, "spesial-jnt") == [101]
        assert ps.cari_nomor_terlompat(jnt, "spesial-jnt", ps.nomor_pick_sesi(folder)) == []
        assert ps.cari_nomor_terlompat(jnt, "spesial-jnt", {100, 102}) == [101]
        print("  cari_nomor_terlompat: nomor yang ada di kurir/jenis lain di sesi sama tidak dihitung hilang")


def uji_sudah_dicetak_dilewati_dan_urutan_dipertahankan():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        a, b, c = (folder / n for n in ("PICK-1_a.pdf", "PICK-2_b.pdf", "PICK-3_c.pdf"))
        _buat(folder, a.name, b.name, c.name)
        catatan = folder / "logs" / "sudah.txt"
        assert ps.baca_sudah_dicetak(catatan) == set()
        ps.catat_sudah_dicetak(b, catatan)
        sudah = ps.baca_sudah_dicetak(catatan)
        belum, lewat = ps.saring_belum_dicetak([a, b, c], sudah)
        assert belum == [a, c] and lewat == [b], (belum, lewat)
        print("  sudah_dicetak: file tercatat dilewati, sisanya tetap urut")


def uji_cari_nomor_terlompat_berurut_sempurna():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "SPESIAL"
        subfolder.mkdir()
        _buat(subfolder,
             "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf",
             "PICK-000155622_SPESIAL_TRC4_2026-10-01_080320.pdf",
             "PICK-000155623_SPESIAL_TRC9_2026-10-01_090000.pdf")
        file_pdf = ps.daftar_label(folder, "spesial")
        assert ps.cari_nomor_terlompat(file_pdf, "spesial") == []
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
        file_pdf = ps.daftar_label(folder, "spesial")
        assert ps.cari_nomor_terlompat(file_pdf, "spesial") == [155623, 155624]
        print("  cari_nomor_terlompat: deteksi nomor PICK yang hilang di tengah")


def uji_cari_nomor_terlompat_kurang_dari_2_file():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "SPESIAL"
        subfolder.mkdir()
        _buat(subfolder, "PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf")
        file_pdf = ps.daftar_label(folder, "spesial")
        assert ps.cari_nomor_terlompat(file_pdf, "spesial") == []
        assert ps.cari_nomor_terlompat([], "spesial") == []
        print("  cari_nomor_terlompat: list kosong kalau <2 file (tidak ada rentang untuk dicek)")


def uji_cari_nomor_terlompat_jenis_gtl_sicepat_hitung_dari_semua_urgent():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        subfolder = folder / "URGENT"
        subfolder.mkdir()
        _buat(subfolder,
             "PICK-000155621_GTL-SICEPAT-LANTAI1_2026-10-01_080302.pdf",
             "PICK-000155622_LAZADA_2026-10-01_080400.pdf",
             "PICK-000155625_GTL-SICEPAT-LANTAI1_2026-10-01_090000.pdf")
        semua = ps.daftar_label(folder, "gtl-sicepat", saring_nama=False)
        # picklist Lazada (622) bukan nomor hilang; hanya 623 & 624 yang benar-benar terlompat
        assert ps.cari_nomor_terlompat(semua, "gtl-sicepat") == [155623, 155624]
        print("  cari_nomor_terlompat: gap dihitung dari SEMUA PDF subfolder URGENT, jadi picklist "
             "Lazada di antara nomor GTL-SiCepat tidak dianggap hilang")


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


def uji_cetak_timeout_jadi_cetak_error_dan_batch_lanjut():
    import subprocess
    from unittest import mock
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        a, b = folder / "a.pdf", folder / "b.pdf"
        a.write_bytes(b"%PDF-1.4")
        b.write_bytes(b"%PDF-1.4")
        panggilan = []

        def palsu(cmd, **kw):
            panggilan.append(cmd)
            if cmd[0] == "taskkill":
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if str(a) in cmd:
                raise subprocess.TimeoutExpired(cmd, 1)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        dicatat = []
        with mock.patch.object(ps.subprocess, "run", palsu),                 mock.patch.object(ps, "catat_sudah_dicetak", dicatat.append),                 mock.patch.object(ps, "JEDA_ANTAR_CETAK_S", 0):
            berhasil, gagal = ps.cetak_semua(Path("SumatraPDF.exe"), "P", [a, b], False)
        assert gagal == [a] and berhasil == [b], (berhasil, gagal)
        assert any(c[0] == "taskkill" for c in panggilan), "sisa SumatraPDF harus dimatikan"
        print("  cetak: timeout SumatraPDF -> file masuk gagal, taskkill, batch lanjut")


def uji_timeout_sumatra_dari_env():
    import os
    from unittest import mock
    for nilai, harapan in (("300", 300), ("abc", 120), ("-5", 120), ("0", 120)):
        with mock.patch.dict(os.environ, {"SUMATRA_TIMEOUT_S": nilai}):
            assert ps._timeout_sumatra() == harapan, (nilai, ps._timeout_sumatra())
    with mock.patch.dict(os.environ, clear=False):
        os.environ.pop("SUMATRA_TIMEOUT_S", None)
        assert ps._timeout_sumatra() == 120
    print("  _timeout_sumatra: env SUMATRA_TIMEOUT_S dipakai, tidak valid -> 120")


# -------------------------------------------------- mode event (SPX Hemat / SPX Standard)
def uji_daftar_label_event_folder_terpisah_dan_tidak_masuk_jenis_gabungan():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        isi = {
            "JNT_SPESIAL": "PICK-000200001_JNT_SPESIAL_A_2026-10-10_080000.pdf",
            "SPXHEMAT_SPESIAL": "PICK-000200002_SPXHEMAT_SPESIAL_B_2026-10-10_080100.pdf",
            "SPXHEMATPAGI_SPESIAL": "PICK-000200003_SPXHEMATPAGI_SPESIAL_C_2026-10-10_080200.pdf",
            "SPXHEMAT_SATUAN": "PICK-000200004_SPXHEMAT-1QTY-REGULER-2A_2026-10-10_080300.pdf",
            "SPXHEMATPAGI_SATUAN": "PICK-000200005_SPXHEMATPAGI-1QTY-REGULER-2A_2026-10-10_080400.pdf",
            "SPXHEMAT_KOMBINASI": "PICK-000200006_SPXHEMAT-KOMBINASI-REGULER-LANTAI1_2026-10-10_080500.pdf",
            "SPXHEMATPAGI_KOMBINASI": "PICK-000200007_SPXHEMATPAGI-KOMBINASI-REGULER-LANTAI1_2026-10-10_080600.pdf",
            "SPX_STANDARD": "PICK-000200008_SPX-STANDARD-LANTAI1_2026-10-10_080700.pdf",
            "SPX_PAGI": "PICK-000200009_SHOPEE-PAGI-SPX-STANDARD-LANTAI1_2026-10-10_080800.pdf",
        }
        for sub, nama in isi.items():
            (folder / sub).mkdir()
            _buat(folder / sub, nama)
        harapan = {
            "spesial-spx-hemat": "SPXHEMAT_SPESIAL", "spesial-spx-hemat-pagi": "SPXHEMATPAGI_SPESIAL",
            "satuan-spx-hemat": "SPXHEMAT_SATUAN", "satuan-spx-hemat-pagi": "SPXHEMATPAGI_SATUAN",
            "kombinasi-spx-hemat": "SPXHEMAT_KOMBINASI",
            "kombinasi-spx-hemat-pagi": "SPXHEMATPAGI_KOMBINASI",
            "spx-standard": "SPX_STANDARD", "spx-pagi": "SPX_PAGI",
            "spesial-jnt": "JNT_SPESIAL",     # J&T mode event = folder & jenis yang sama dgn harian
        }
        for jenis, sub in harapan.items():
            assert [f.name for f in ps.daftar_label(folder, jenis)] == [isi[sub]], jenis
        # jenis gabungan harian TIDAK berubah: hanya folder harian, event tidak ikut
        assert [f.name for f in ps.daftar_label(folder, "spesial")] == [isi["JNT_SPESIAL"]]
        assert ps.daftar_label(folder, "satuan") == []
        assert ps.daftar_label(folder, "kombinasi") == []
        print("  jenis event: tiap folder (SPXHEMAT_*, SPXHEMATPAGI_*, SPX_STANDARD) punya jenis "
              "sendiri; jenis gabungan harian tidak ikut mencetak label event")


def uji_pola_spesial_mengenali_awalan_kurir_event():
    cocok = {
        "PICK-000000001_SPESIAL_X_2026-10-10_080000.pdf": 1,
        "PICK-000000002_JNT_SPESIAL_X_2026-10-10_080000.pdf": 2,
        "PICK-000000003_SPX_SPESIAL_X_2026-10-10_080000.pdf": 3,
        "PICK-000000004_SPXHEMAT_SPESIAL_X_2026-10-10_080000.pdf": 4,
        "PICK-000000005_SPXHEMATPAGI_SPESIAL_X_2026-10-10_080000.pdf": 5,
    }
    for nama, nomor in cocok.items():
        m = ps.POLA_SPESIAL.match(nama)
        assert m and int(m.group(1)) == nomor, nama
    assert not ps.POLA_SPESIAL.match("PICK-000000007_SPXHEMAT-1QTY-REGULER-2A_2026-10-10.pdf")
    print("  POLA_SPESIAL: mengenali awalan SPXHEMAT_/SPXHEMATPAGI_ selain JNT_/SPX_")


def uji_nomor_terlompat_event_tidak_menghitung_jenis_event_lain():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for sub, nama in (("SPXHEMAT_SPESIAL", "PICK-000000100_SPXHEMAT_SPESIAL_A_2026-10-10_080000.pdf"),
                          ("SPXHEMATPAGI_SPESIAL", "PICK-000000101_SPXHEMATPAGI_SPESIAL_B_2026-10-10_080100.pdf"),
                          ("SPXHEMAT_SPESIAL", "PICK-000000102_SPXHEMAT_SPESIAL_C_2026-10-10_080200.pdf"),
                          ("SPX_STANDARD", "PICK-000000103_SPX-STANDARD-LANTAI1_2026-10-10_080300.pdf")):
            (folder / sub).mkdir(exist_ok=True)
            _buat(folder / sub, nama)
        hemat = ps.daftar_label(folder, "spesial-spx-hemat", saring_nama=False)
        assert ps.cari_nomor_terlompat(hemat, "spesial-spx-hemat") == [101]
        assert ps.cari_nomor_terlompat(hemat, "spesial-spx-hemat", ps.nomor_pick_sesi(folder)) == [], \
            "101 ada di folder Shopee Pagi (jenis lain) -> bukan nomor hilang"
        print("  cari_nomor_terlompat: nomor di folder event lain (Pagi/Standard) tidak dihitung hilang")


def uji_folder_dan_nama_file_buatan_proses_label_terbaca_print_spesial():
    import proses_label as pl

    for kurir in ("spx-hemat", "spx-hemat-pagi"):
        assert ps.JENIS_LABEL[f"spesial-{kurir}"] == [pl._tag_spesial(kurir)], kurir
        assert ps.JENIS_LABEL[f"satuan-{kurir}"] == [pl._gabung_kurir(pl.SUBFOLDER_SATUAN, kurir)]
        assert ps.JENIS_LABEL[f"kombinasi-{kurir}"] == \
            [pl._gabung_kurir(pl.SUBFOLDER_KOMBINASI, kurir)]
        # nama file PDF spesial yang dibuat lanjutkan_picklist(): f"{picklist_no}_{tag}_{sku}_..."
        nama = f"PICK-000200123_{pl._tag_spesial(kurir)}_TRC1_2026-10-10_080000.pdf"
        assert ps.POLA_SPESIAL.match(nama), nama
    assert ps.JENIS_LABEL["spx-standard"] == [pl.SUBFOLDER_SPX_STANDARD]
    assert ps.JENIS_LABEL["spx-pagi"] == [pl.SUBFOLDER_SPX_PAGI]
    print("  folder/tag buatan proses_label (SPXHEMAT*, SPXHEMATPAGI*, SPX_STANDARD, SPX_PAGI) "
          "sama persis dengan yang dicari print_spesial")


def uji_setiap_jenis_cetak_punya_bat_dan_bat_hanya_memakai_jenis_valid():
    import re

    bats = {}
    for f in ROOT.glob("cetak-label-*.bat"):
        for jenis in re.findall(r"--jenis\s+(\S+)", f.read_text(encoding="utf-8")):
            bats.setdefault(jenis, []).append(f.name)
    tanpa_bat = sorted(set(ps.JENIS_LABEL) - set(bats))
    assert not tanpa_bat, f"jenis tanpa .bat cetak: {tanpa_bat}"
    tak_dikenal = sorted(set(bats) - set(ps.JENIS_LABEL))
    assert not tak_dikenal, f".bat memanggil --jenis yang tidak ada: {tak_dikenal}"
    assert all(len(v) == 1 for v in bats.values()), f"1 jenis dipakai >1 .bat: {bats}"
    print(f"  {len(ps.JENIS_LABEL)} jenis cetak <-> {len(bats)} .bat cetak-label-*.bat: sama persis, "
          "tidak ada yang yatim")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
