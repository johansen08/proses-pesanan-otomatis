"""Uji pilah_satuan.py tanpa API/Jubelio sungguhan (klien tiruan, PDF label tiruan).

Jalankan:  .venv\\Scripts\\python tests\\test_pilah_satuan.py
"""
import json
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import kurasi_satuan  # noqa: E402
import proses_label  # noqa: E402
import pilah_satuan as ps  # noqa: E402
import print_spesial  # noqa: E402

# Tes TIDAK boleh menulis catatan sungguhan di logs/: arahkan ke folder sementara.
_LOG_TES = Path(tempfile.mkdtemp())
kurasi_satuan.FILE_KURASI = _LOG_TES / "satuan_dikurasi.json"
print_spesial.FILE_SUDAH_DICETAK = _LOG_TES / "sudah_dicetak.txt"
ps.MASA_TENANG_S = 0   # file tes baru dibuat; cek "sesi masih menulis" diuji khusus di bawah


def _pdf_label(tujuan: Path, halaman: list[tuple[str, str]]) -> None:
    c = canvas.Canvas(str(tujuan))
    for pesanan, resi in halaman:
        c.drawString(50, 700, "No Pesanan")
        c.drawString(50, 680, f": {pesanan}")
        c.drawString(50, 660, f"No Resi: {resi}")
        c.showPage()
    c.save()


class KlienPalsu:
    """item per picklist: {nomor: [(sku, pesanan, resi, status), ...]}"""

    def __init__(self, data):
        self.data = data

    def get(self, path):
        nomor = int(path.rsplit("/", 1)[1])
        return {"items": [{"item_code": s, "salesorder_no": o, "tracking_no": r,
                           "shipper": "SPX Hemat", "wms_status": w}
                          for s, o, r, w in self.data[nomor]]}


def _siapkan(tmp: Path):
    # sesi 1: picklist 10 (X x2, Y x1, Z batal); sesi 2: picklist 20 (X x1, Y x1) -> X=3, Y=2
    (tmp / "1" / "SATUAN").mkdir(parents=True)
    (tmp / "2" / "SATUAN").mkdir(parents=True)
    _pdf_label(tmp / "1" / "SATUAN" / "PICK-000000010_1QTY-REGULER-2A_2026-10-13_081500.pdf",
               [("O1", "R1"), ("O2", "R2"), ("O3", "R3"), ("O4", "R4")])
    _pdf_label(tmp / "2" / "SATUAN" / "PICK-000000020_1QTY-REGULER-2A_2026-10-13_104000.pdf",
               [("O5", "R5"), ("O6", "R6")])
    return KlienPalsu({
        10: [("X", "O1", "R1", "FINISH_PICK"), ("X", "O2", "R2", "FINISH_PICK"),
             ("Y", "O3", "R3", "FINISH_PICK"), ("Z", "O4", "R4", "CANCELED")],
        20: [("X", "O5", "R5", "FINISH_PICK"), ("Y", "O6", "R6", "FINISH_PICK")]})


def uji_hanya_satuan_gabungan_jnt_spx():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _siapkan(tmp)
        (tmp / "1" / "JNT_SATUAN").mkdir()
        (tmp / "1" / "SPXHEMAT_SATUAN").mkdir()
        _pdf_label(tmp / "1" / "JNT_SATUAN" / "PICK-000000030_1QTY-REGULER-2A_2026-10-13_082000.pdf", [("O7", "R7")])
        _pdf_label(tmp / "1" / "SPXHEMAT_SATUAN" / "PICK-000000031_1QTY-REGULER-2A_2026-10-13_082100.pdf", [("O8", "R8")])
        assert [f.name[:14] for f in ps.cari_pdf_satuan(tmp)] == ["PICK-000000010", "PICK-000000020"]
        # sesi yang HANYA punya satuan per kurir: ditolak dengan alasan jelas
        (tmp / "3" / "JNT_SATUAN").mkdir(parents=True)
        _pdf_label(tmp / "3" / "JNT_SATUAN" / "PICK-000000040_1QTY-REGULER-2A_2026-10-13_090000.pdf", [("O9", "R9")])
        ok, alasan = ps.periksa_sesi(tmp / "3")
        assert not ok and "dipisah per kurir" in alasan, alasan
        try:
            ps.pdf_terpilih(tmp, ["1", "3"])
            assert False, "sesi 3 harus ditolak"
        except ps.SesiTidakValid as e:
            assert "Sesi 3" in str(e) and "Sesi 1" not in str(e), e
        # tanpa --sesi: hanya sesi yang boleh (1, 2); sesi 3 diabaikan tanpa error
        assert ps.pdf_terpilih(tmp)[1] == ["1", "2"]
    print("  hanya subfolder SATUAN (gabungan); JNT_/SPXHEMAT_SATUAN tidak ikut; sesi per-kurir ditolak")


def uji_hanya_sesi_diproses_0700_1200_dan_2000_0700():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)

        def sesi(no, jam):
            f = tmp / no / "SATUAN"
            f.mkdir(parents=True)
            _pdf_label(f / f"PICK-0000000{no}0_1QTY-REGULER-2A_2026-10-13_{jam}.pdf", [("O" + no, "R" + no)])
            (tmp / no / "SPESIAL").mkdir()   # waktu mulai sesi = cap TERAWAL dari semua PDF sesi
            _pdf_label(tmp / no / "SPESIAL" / f"PICK-0000000{no}9_SPESIAL_A_2026-10-13_{jam}.pdf", [("Z", "Z")])
        kasus = {"1": ("070000", True), "2": ("115900", True), "3": ("120000", True),      # pagi 07.00-12.00
                 "4": ("120100", False), "5": ("153000", False), "6": ("195900", False),   # siang-sore: ditolak
                 "7": ("200000", True), "8": ("233000", True), "9": ("003000", True),      # malam 20.00-07.00
                 "10": ("065900", True), "11": ("070100", True)}   # 06.59 (malam) dan 07.01 (pagi) sama-sama boleh
        for no, (jam, _) in kasus.items():
            sesi(no, jam)
        hasil = {no: ps.periksa_sesi(tmp / no)[0] for no in kasus}
        assert hasil == {no: ok for no, (_, ok) in kasus.items()}, hasil
        assert "di luar 07.00-12.00 atau 20.00-07.00" in ps.periksa_sesi(tmp / "5")[1]
        assert ps.dalam_jendela(0) and ps.dalam_jendela(7 * 60) and ps.dalam_jendela(12 * 60) and ps.dalam_jendela(20 * 60)             and ps.dalam_jendela(24 * 60 - 1) and not ps.dalam_jendela(12 * 60 + 1) and not ps.dalam_jendela(20 * 60 - 1)
        # tanpa cap waktu di nama file -> tidak bisa dibuktikan -> ditolak
        (tmp / "12" / "SATUAN").mkdir(parents=True)
        _pdf_label(tmp / "12" / "SATUAN" / "PICK-000000120_1QTY-REGULER-2A_x.pdf", [("O8", "R8")])
        ok, alasan = ps.periksa_sesi(tmp / "12")
        assert not ok and "tidak diketahui" in alasan
        # sesi eksplisit di luar jendela -> SesiTidakValid; --abaikan-jendela (uji) melewatinya
        try:
            ps.pdf_terpilih(tmp, ["1", "6"])
            assert False
        except ps.SesiTidakValid as e:
            assert "Sesi 6" in str(e) and "Sesi 1" not in str(e)
        assert ps.pdf_terpilih(tmp, ["1", "6"], abaikan_jendela=True)[1] == ["1", "6"]
        assert ps.pdf_terpilih(tmp)[1] == sorted((n for n, (_, ok) in kasus.items() if ok), key=int)   # 4,5,6 & 12 tersaring
    print("  sesi boleh 07.00-12.00 & 20.00-07.00 (lewat tengah malam), 12.01-19.59 & tanpa cap waktu ditolak; --abaikan-jendela untuk uji")


def uji_resi_kurir_lain_tidak_dihitung_spesial():
    baris = [{"sku": "X", "resi": f"R{i}", "pesanan": f"O{i}", "kurir": "J&T Express Standard" if i < 2 else "SPX Hemat"}
             for i in range(2)] + [{"sku": "X", "resi": "R9", "pesanan": "O9", "kurir": "SiCepat Reguler"}]
    layak, sisa = ps.kelompokkan(baris, 3)
    assert not layak and sisa == {"X": 2}, (layak, sisa)       # kurir lain tidak ikut menggenapkan jadi 3
    baris.append({"sku": "X", "resi": "R10", "pesanan": "O10", "kurir": "spx standard"})
    layak, _ = ps.kelompokkan(baris, 3)
    assert [b["resi"] for b in layak["X"]] == ["R0", "R1", "R10"]   # huruf kecil tetap cocok
    assert ps.kurir_diizinkan("J&T Express NEXT-DAY DELIVERY") and not ps.kurir_diizinkan("GoTo Logistics GTL") and not ps.kurir_diizinkan(None)
    print("  resi berkurir selain J&T/SPX tidak dihitung spesial (tetap sisa)")


def uji_cari_pdf_urut_nomor_pick():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _siapkan(tmp)
        (tmp / "1" / "SPESIAL").mkdir()
        _pdf_label(tmp / "1" / "SPESIAL" / "PICK-000000001_SPESIAL_X_x.pdf", [("O9", "R9")])
        nama = [f.name[:14] for f in ps.cari_pdf_satuan(tmp)]
        assert nama == ["PICK-000000010", "PICK-000000020"], nama  # SPESIAL tidak ikut
    print("  hanya subfolder *SATUAN, urut nomor PICK")


def uji_pilah_gabung_lintas_sesi():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        h = ps.pilah(k, tmp)
        assert h["pdf"] == 2 and h["halaman"] == 5 and h["tak_cocok"] == 1, h  # O4 batal
        assert set(h["layak"]) == {"X"} and len(h["layak"]["X"]) == 3, h["layak"]
        assert h["sisa_sku"] == 1  # Y baru 2 resi
        pdf_x = tmp / "SPESIAL-SATUAN-1-2" / "SPESIAL-SATUAN_2A_X_3resi.pdf"
        assert pdf_x.exists() and len(PdfReader(str(pdf_x)).pages) == 3
        teks = "".join(p.extract_text() for p in PdfReader(str(pdf_x)).pages)
        assert all(r in teks for r in ("R1", "R2", "R5")) and "R3" not in teks
        assert (tmp / "SPESIAL-SATUAN-1-2" / "detail-resi-spesial-satuan-1-2.xlsx").exists()
        assert not (tmp / "SPESIAL-SATUAN-1-2" / "SPESIAL-SATUAN_2A_Y_2resi.pdf").exists()
    print("  X gabungan 2 sesi (3 resi) dikelompokkan, Y (2) tidak, item batal dibuang")


def uji_sisa_satuan_per_kelompok_rak():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        h = ps.pilah(k, tmp)
        # sisa = Y (O3 di picklist 10, O6 di picklist 20); Z batal dibuang; X pindah ke spesial
        assert {kel: [b["resi"] for b in bs] for kel, bs in h["sisa"].items()} ==             {"1QTY-REGULER-2A": ["R3", "R6"]}, h["sisa"]
        pdf = tmp / "SISA-SATUAN-1-2" / "SISA-SATUAN_1QTY-REGULER-2A_2resi.pdf"
        assert pdf.exists()
        teks = "".join(p.extract_text() for p in PdfReader(str(pdf)).pages)
        assert "R3" in teks and "R6" in teks and "R1" not in teks
    print("  SISA-SATUAN-<sesi>: halaman non-spesial per kelompok rak, tanpa yang batal")


def uji_pilih_sesi():
    assert ps.parse_sesi("1-2-3") == ["1", "2", "3"] and ps.parse_sesi("3, 1") == ["1", "3"]
    assert ps.parse_sesi("") is None and ps.parse_sesi(None) is None
    try:
        ps.parse_sesi("a-1")
        assert False
    except ValueError:
        pass
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        assert [f.name[:14] for f in ps.cari_pdf_satuan(tmp, ["2"])] == ["PICK-000000020"]
        h = ps.pilah(k, tmp, min_resi=1, buat_pdf=False, sesi=["2"])
        assert h["sesi"] == "2" and h["folder"].name == "SPESIAL-SATUAN-2" and h["halaman"] == 2
        from openpyxl import load_workbook
        ws = load_workbook(h["folder"] / "detail-resi-spesial-satuan-2.xlsx")["Detail"]
        baris = list(ws.iter_rows(values_only=True))
        assert baris[0] == ("No Picklist", "SKU", "No Pesanan", "No Resi")
        assert baris[1] == ("PICK-000000020", "X", "O5", "R5"), baris[1]
        # format SAMA dengan detail-resi-spesial.xlsx (proses_label): 1 sheet "Detail", 4 kolom, tanpa tambahan
        wb = load_workbook(h["folder"] / "detail-resi-spesial-satuan-2.xlsx")
        assert wb.sheetnames == ["Detail"] and ws.max_column == 4, (wb.sheetnames, ws.max_column)
        assert list(baris[0]) == proses_label.KOLOM_DETAIL_SPESIAL
        assert [ws.column_dimensions[c].width for c in "ABCD"] == [18, 16, 22, 18]
        assert all(len(b) == 4 for b in baris)
    print("  --sesi memilih sesi; folder SPESIAL-SATUAN-<sesi>; Excel detail format detail-resi-spesial")


def uji_satuan_asal_diberi_penanda_dikurasi():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        asal = ps.cari_pdf_satuan(tmp)
        ps.pilah(k, tmp, tulis=False)
        ps.pilah(k, tmp, buat_pdf=False)
        assert kurasi_satuan.baca() == {}, "analisis-saja / --tanpa-pdf tidak menandai"
        h = ps.pilah(k, tmp)
        assert h["dikurasi"] == 2
        assert kurasi_satuan.baca() == {str(f.resolve()): "1-2" for f in asal}
        # penanda hanya berlaku selama folder hasilnya ada
        import shutil
        shutil.rmtree(tmp / "SPESIAL-SATUAN-1-2", ignore_errors=True)
        assert kurasi_satuan.baca(), "folder SISA-SATUAN masih ada -> penanda masih berlaku"
        shutil.rmtree(tmp / "SISA-SATUAN-1-2")
        assert kurasi_satuan.baca() == {}
    print("  PDF satuan asal ditandai dikurasi hanya saat folder hasil dibuat; hilang kalau folder hasil dihapus")


def uji_status_tercetak_hasil_pilah_dijaga_saat_dibuat_ulang():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        ps.pilah(k, tmp)
        spesial = tmp / "SPESIAL-SATUAN-1-2" / "SPESIAL-SATUAN_2A_X_3resi.pdf"
        sisa = tmp / "SISA-SATUAN-1-2" / "SISA-SATUAN_1QTY-REGULER-2A_2resi.pdf"
        for f in (spesial, sisa):
            print_spesial.catat_sudah_dicetak(f)
        ps.pilah(k, tmp)   # sama persis -> status tercetak tetap
        assert print_spesial.baca_sudah_dicetak() >= {str(spesial.resolve()), str(sisa.resolve())}
        ps.pilah(k, tmp, min_resi=2)   # X & Y spesial: SISA hilang, SPESIAL X isinya sama
        sudah = print_spesial.baca_sudah_dicetak()
        assert str(sisa.resolve()) not in sudah, "file hilang/berubah: status tercetak harus dilupakan"
        assert str(spesial.resolve()) in sudah, "isi identik: status tercetak tetap"
    print("  dibuat ulang: status tercetak tetap bila isi identik, dilupakan bila file berubah/hilang")


def uji_analisis_saja_cache_dan_ringkasan_json():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        cache = tmp / "cache" / "analisis.json"
        h = ps.pilah(k, tmp, tulis=False, cache=cache)
        assert not (tmp / "SPESIAL-SATUAN-1-2").exists() and not (tmp / "SISA-SATUAN-1-2").exists()  # tidak menulis
        assert cache.exists()
        # tahap "buat": cache dipakai, Jubelio (klien) tidak disentuh sama sekali
        h2 = ps.pilah(None, tmp, cache=cache)
        assert set(h2["layak"]) == {"X"} and h2["tak_cocok"] == 1 and (tmp / "SPESIAL-SATUAN-1-2").is_dir()
        # ambang berubah: tetap dari cache, hasil beda, file lama dibersihkan
        h3 = ps.pilah(None, tmp, min_resi=2, cache=cache)
        assert set(h3["layak"]) == {"X", "Y"}
        h4 = ps.pilah(None, tmp, min_resi=3, cache=cache)
        assert not (tmp / "SPESIAL-SATUAN-1-2" / "SPESIAL-SATUAN_2A_Y_2resi.pdf").exists()   # sisa dari ambang 2
        assert sorted(p.name for p in (tmp / "SPESIAL-SATUAN-1-2").iterdir()) == [
            "SPESIAL-SATUAN_2A_X_3resi.pdf", "detail-resi-spesial-satuan-1-2.xlsx"]
        # PDF berubah -> cache tidak berlaku (None -> baca_cache gagal -> butuh klien)
        pdf = ps.cari_pdf_satuan(tmp)[0]
        pdf.write_bytes(pdf.read_bytes() + b"\n%x")
        assert ps.baca_cache(cache, tmp, ps.cari_pdf_satuan(tmp)) is None
        j = ps.ringkasan_json(h4)
        assert j["spesial"] == [{"sku": "X", "n": 3, "rak": "2A", "sesi": {"1": 2, "2": 1}}], j
        assert j["sisa"] == {"2A": 2} and j["tak_cocok"] == 1 and j["folder"] == [
            "SPESIAL-SATUAN-1-2", "SISA-SATUAN-1-2"]
        json_utuh = ps.PENANDA_JSON + __import__("json").dumps(j)
        assert json_utuh.startswith("##HASIL## ")
    print("  analisis-saja tidak menulis; cache menghindari Jubelio; pilah ulang membersihkan file lama; ringkasan JSON")


def uji_ambang_dan_tanpa_pdf():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        h = ps.pilah(k, tmp, min_resi=2, buat_pdf=False)
        assert set(h["layak"]) == {"X", "Y"}
        assert [f.suffix for f in h["file"]] == [".xlsx"]  # tanpa PDF
    print("  --min-resi 2 memasukkan Y; --tanpa-pdf hanya Excel")


def _baris(rak, resi="R"):
    return {"sku": "?", "resi": resi, "pesanan": resi, "kurir": "SPX Hemat",
            "pdf": Path(f"x/1/SATUAN/PICK-000000001_1QTY-REGULER-{rak}_2026-10-13_081500.pdf")}


def uji_spesial_satuan_urut_rak_lalu_sku():
    layak = {"B": [_baris("2A")] * 3, "A": [_baris("3A")] * 3, "C": [_baris("1B")] * 3, "D": [_baris("2A")] * 3,
             "E": [_baris("2A"), _baris("2A"), _baris("3B")]}     # rak dominan E = 2A
    assert [s for s, _ in ps.urutan_spesial(layak)] == ["C", "B", "D", "E", "A"], ps.urutan_spesial(layak)
    assert ps.rak_dominan(layak["E"]) == "2A"
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        h = ps.pilah(k, tmp)
        assert [f.name for f in h["file"] if f.suffix == ".pdf" and "SPESIAL" in f.name] == ["SPESIAL-SATUAN_2A_X_3resi.pdf"]
        j = ps.ringkasan_json(h)
        assert [(x["rak"], x["sku"]) for x in j["spesial"]] == [("2A", "X")]
    print("  SPESIAL-SATUAN urut rak (1B,2A,2B,3A,3B,LAINNYA) lalu SKU; rak dominan ada di nama file & ringkasan")


def uji_pilah_ulang_di_atas_pdf_yang_sudah_dikurasi_ditolak():
    import shutil
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        ps.pilah(k, tmp, min_resi=1)                      # sesi 1-2 dikurasi -> SPESIAL/SISA-SATUAN-1-2
        asal = ps.cari_pdf_satuan(tmp)
        assert kurasi_satuan.bentrok(asal, "1-2") == {}  # sesi yang persis sama: boleh dibuat ulang
        assert list(kurasi_satuan.bentrok(asal, "1")) == ["1-2"]
        h = ps.pilah(k, tmp, sesi=["1"], tulis=False)     # analisis tetap jalan, hanya diberi peringatan
        assert {k: len(v) for k, v in h["bentrok"].items()} == {"1-2": 1} and ps.ringkasan_json(h)["bentrok"] == {"1-2": 1}
        try:
            ps.pilah(k, tmp, sesi=["1"])
            assert False, "harus ditolak: resi akan ada di dua folder hasil"
        except ps.KurasiBentrok as e:
            assert "SPESIAL-SATUAN-1-2" in str(e) and "hapus folder" in str(e), e
        assert not (tmp / "SPESIAL-SATUAN-1").exists() and not (tmp / "SISA-SATUAN-1").exists()   # tidak ada yang ditulis
        ps.pilah(k, tmp, min_resi=1)                      # sesi sama: tidak bentrok
        ps.pilah(k, tmp, sesi=["1"], buat_pdf=False)      # mode hanya-Excel tidak menandai -> tidak bentrok
        shutil.rmtree(tmp / "SPESIAL-SATUAN-1-2", ignore_errors=True)
        shutil.rmtree(tmp / "SISA-SATUAN-1-2", ignore_errors=True)  # folder lama dihapus -> penanda tak berlaku -> boleh
        assert kurasi_satuan.bentrok(asal, "1") == {}
        ps.pilah(k, tmp, sesi=["1"])
    print("  PDF yang sudah dikurasi ke folder hasil lain: analisis memperingatkan, buat ditolak; sesi sama/folder lama dihapus boleh")


def uji_sesi_yang_masih_menulis_label_ditolak():
    import os
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _siapkan(tmp)
        lama, ps.MASA_TENANG_S = ps.MASA_TENANG_S, 120
        try:
            ok, alasan = ps.periksa_sesi(tmp / "1")
            assert not ok and "masih menulis label" in alasan, alasan       # file baru dibuat sekarang
            try:
                ps.pdf_terpilih(tmp, ["1"])
                assert False
            except ps.SesiTidakValid as e:
                assert "Sesi 1" in str(e)
            ok_abai, _ = ps.periksa_sesi(tmp / "1", abaikan_jendela=True)
            assert not ok_abai, "--abaikan-jendela hanya melewati syarat JAM, bukan sesi yang masih menulis"
            for f in (tmp / "1").rglob("*.pdf"):
                os.utime(f, (f.stat().st_atime, f.stat().st_mtime - 300))   # 5 menit lalu
            assert ps.periksa_sesi(tmp / "1")[0] is True
        finally:
            ps.MASA_TENANG_S = lama
    print("  sesi yang PDF-nya baru diubah (<2 menit) ditolak; --abaikan-jendela tidak melewatinya")


def uji_cache_analisis_kedaluwarsa():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        cache = tmp / "cache.json"
        ps.pilah(k, tmp, tulis=False, cache=cache)
        pdfs = ps.cari_pdf_satuan(tmp)
        assert ps.baca_cache(cache, tmp, pdfs) is not None
        data = json.loads(cache.read_text(encoding="utf-8"))
        data["dibuat"] -= ps.UMUR_CACHE_MAKS_S + 5      # lewat 15 menit
        cache.write_text(json.dumps(data), encoding="utf-8")
        assert ps.baca_cache(cache, tmp, pdfs) is None, "cache kedaluwarsa tidak boleh dipakai"
        del data["dibuat"]                              # cache lama tanpa cap waktu juga ditolak
        cache.write_text(json.dumps(data), encoding="utf-8")
        assert ps.baca_cache(cache, tmp, pdfs) is None
        h = ps.pilah(k, tmp, tulis=False, cache=cache)  # dibaca ulang dari Jubelio & cache diperbarui
        assert ps.baca_cache(cache, tmp, pdfs) is not None and h["tak_cocok"] == 1
    print("  cache analisis kedaluwarsa setelah 15 menit / tanpa cap waktu -> dibaca ulang dari Jubelio")


def uji_nomor_pick_terlompat_di_antara_picklist_satuan():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for sesi in ("1", "2"):
            (tmp / sesi / "SATUAN").mkdir(parents=True)
        for sesi, nomor in (("1", 10), ("1", 12), ("2", 20), ("2", 21)):
            _pdf_label(tmp / sesi / "SATUAN" / f"PICK-0000000{nomor}_1QTY-REGULER-2A_2026-10-13_081500.pdf", [("O", "R")])
        assert ps.nomor_terlompat_satuan(ps.cari_pdf_satuan(tmp)) == [11]            # 11 hilang di sesi 1
        (tmp / "1" / "KOMBINASI").mkdir()
        _pdf_label(tmp / "1" / "KOMBINASI" / "PICK-000000011_KOMBINASI-REGULER-LANTAI1_2026-10-13_081500.pdf", [("O", "R")])
        assert ps.nomor_terlompat_satuan(ps.cari_pdf_satuan(tmp)) == []              # nomor 11 ada di jenis lain
        h = ps.ringkasan_json({"sesi": "1-2", "pdf": 4, "halaman": 0, "tak_cocok": 0, "kurir_lain": 0, "layak": {},
                               "sisa": {}, "file": [], "terlompat": [11], "bentrok": {}})
        assert h["terlompat"] == ["PICK-000000011"]
    print("  nomor PICK terlompat di antara picklist satuan satu sesi diperingatkan (nomor jenis lain tidak dihitung)")


def uji_mode_hanya_excel_tanpa_pdf_dan_tanpa_penanda():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        k = _siapkan(tmp)
        h = ps.pilah(k, tmp, buat_pdf=False)
        assert [f.name for f in h["file"]] == ["detail-resi-spesial-satuan-1-2.xlsx"]
        assert not (tmp / "SISA-SATUAN-1-2").exists() and not any((tmp / "SPESIAL-SATUAN-1-2").glob("*.pdf"))
        assert kurasi_satuan.baca() == {} and "dikurasi" not in h
        assert ps.ringkasan_json(h)["tanpa_pdf"] is True
        # sesudah mode PDF lalu hanya-Excel pada sesi sama: PDF lama hilang, penanda dicabut (tak ada pengganti)
        ps.pilah(k, tmp)
        assert kurasi_satuan.baca()
        ps.pilah(k, tmp, buat_pdf=False)
        assert kurasi_satuan.baca() == {} and not any((tmp / "SPESIAL-SATUAN-1-2").glob("*.pdf"))
        assert ps.ringkasan_json(ps.pilah(k, tmp))["tanpa_pdf"] is False
    print("  mode hanya-Excel: tanpa PDF/SISA, tanpa penanda dikurasi (dan mencabut penanda dari mode PDF sebelumnya)")


def uji_resi_dobel_dihitung_sekali():
    baris = [{"sku": "X", "resi": "R1", "pesanan": "O1", "kurir": "SPX Hemat"}] * 3
    layak, sisa = ps.kelompokkan(baris, 3)
    assert not layak and sisa == {"X": 1}
    print("  halaman dobel (resi sama) tidak menggelembungkan hitungan")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
