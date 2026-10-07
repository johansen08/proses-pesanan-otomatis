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


def uji_daftar_label_lazada_hanya_file_lazada():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "URGENT").mkdir()
        _buat(folder / "URGENT",
             "PICK-000155622_LAZADA_2026-10-01_080320.pdf",
             "PICK-000155621_GTL-SICEPAT-LANTAI1_2026-10-01_080302.pdf")
        assert [f.name for f in ps.daftar_label(folder, "lazada")] == [
            "PICK-000155622_LAZADA_2026-10-01_080320.pdf"]
        print("  daftar_label(lazada): hanya PDF Lazada di subfolder URGENT (GTL-SiCepat tidak ikut)")


def _pdf_a5(halaman=2, ukuran=(419.528, 595.276)):
    import io
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=ukuran)
    for n in range(halaman):
        c.rect(10, 10, ukuran[0] - 20, ukuran[1] - 20)
        c.drawString(20, ukuran[1] - 30, f"HALAMAN {n}")
        c.showPage()
    c.save()
    return buf.getvalue()


def uji_render_label_lazada_skala_68_dan_file_lama_tidak_terkecil_lagi():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        a5 = tmp / "PICK-000155622_LAZADA_a5.pdf"
        a5.write_bytes(_pdf_a5(3))
        kecil = tmp / "PICK-000155623_LAZADA_kecil.pdf"
        kecil.write_bytes(_pdf_a5(1, (283.465, 425.197)))          # file lama sudah 100x150 mm
        (tmp / "out").mkdir()
        png = ps.render_label_lazada(a5, 203, tmp / "out")
        assert len(png) == 3
        w, h = Image.open(png[0]).size
        # A5 x 68% pada 203 dpi: 419.528/72*203*0.68 = 804 px, 595.276/72*203*0.68 = 1141 px
        assert (w, h) == (804, 1141) or (abs(w - 804) <= 1 and abs(h - 1141) <= 1), (w, h)
        assert Image.open(png[0]).mode == "L"
        wk, hk = Image.open(ps.render_label_lazada(kecil, 203, tmp / "out")[0]).size
        assert abs(wk - 799) <= 1 and abs(hk - 1199) <= 1, (wk, hk)   # 100x150 mm @203 dpi, 100%
    print("  render lazada: A5 -> 804x1141 px (68% @203 dpi), 3 halaman; file lama 100x150 tidak terkecil lagi")


def uji_cetak_lazada_lewat_gambar_bukan_sumatra_dan_gtl_tetap_sumatra():
    import subprocess

    panggilan = []

    def palsu(perintah, **kw):
        panggilan.append(list(perintah))
        return subprocess.CompletedProcess(perintah, 0, "", "")

    asli_run, asli_dpi = ps.subprocess.run, ps.dpi_printer
    ps.subprocess.run, ps.dpi_printer = palsu, lambda printer: 203
    try:
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "PICK-000155622_LAZADA_2026-10-01_080320.pdf"
            f.write_bytes(_pdf_a5(2))
            dibaca = f.read_bytes()
            assert ps.cetak(None, "PRN", f, pantau=False, jenis="lazada")
            assert ps.cetak(Path("S.exe"), "PRN", f, pantau=False, jenis="gtl-sicepat")
            assert f.read_bytes() == dibaca, "file asli di folder sesi tidak boleh diubah"
    finally:
        ps.subprocess.run, ps.dpi_printer = asli_run, asli_dpi
    lazada, gtl = panggilan
    assert lazada[0] == "powershell" and "-File" in lazada and "Sumatra" not in " ".join(lazada), lazada
    assert lazada[lazada.index("-Dpi") + 1] == "203" and lazada[lazada.index("-Printer") + 1] == "PRN"
    assert len(lazada[lazada.index("-Gambar") + 1].split(",")) == 2, "1 PNG per halaman PDF"
    assert gtl[0] == "S.exe" and "-print-to" in gtl and "-print-settings" not in gtl, gtl
    print("  cetak(lazada): render ke PNG + cetak_gambar.ps1 (tanpa SumatraPDF); gtl-sicepat tetap SumatraPDF")


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


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
