"""Uji rekap_master_excel.py (PICKLIST.xlsx) TANPA pernah menyentuh file master asli - dipakai
workbook kecil tiruan yang mereplikasi struktur sheet "HARI INI" (formula di kolom B/E, baris
hari ini di-pre-fill OPR/TANGGAL ke depan, 1 contoh baris kuning "PICKLIST CANCEL") sesuai
verifikasi struktur file master (06-10-2026).

Jalankan:  .venv\\Scripts\\python tests\\test_rekap_master_excel.py
"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import rekap_master_excel as rme  # noqa: E402

TARGET = "2026-10-06"
TARGET_DT = datetime(2026, 10, 6)


def _reset():
    rme._wb = rme._ws = None
    rme._baris_cari_mulai = rme.BARIS_DATA_AWAL


def _buat_master(folder: Path) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = rme.SHEET
    ws.append(["" for _ in range(27)])                                    # baris 1 (dilewati)
    ws.append(["" for _ in range(27)])                                    # baris 2
    ws.append(["" for _ in range(27)])                                    # baris 3
    ws.append(["", "CODE", "", "", "NO", "OPR", "TGL PROSES", "JAM"])     # baris 4: header
    ws.append(["" for _ in range(27)])                                    # baris 5
    # baris 6-7: data historis lama (tanggal lain, L sudah terisi) - formula B/E spt asli
    for r in (6, 7):
        ws.cell(r, 2, f'=IF(L{r}="","",I{r}&"-"&J{r})')
        ws.cell(r, 5, f'=IF(L{r}="","",IF(G{r}=G{r - 1},E{r - 1}+1,1))')
        ws.cell(r, 6, "SELVI")
        ws.cell(r, 7, datetime(2026, 10, 5))
        ws.cell(r, 12, 157000 + r)
    # baris 8: PRE-FILL hari ini (TARGET) - OPR/TANGGAL sudah diisi ke depan, L masih kosong
    ws.cell(8, 2, '=IF(L8="","",I8&"-"&J8)')
    ws.cell(8, 5, '=IF(L8="","",IF(G8=G7,E7+1,1))')
    ws.cell(8, 6, "PUTRI")
    ws.cell(8, 7, TARGET_DT)
    # baris 9: benar-benar kosong (belum ada pre-fill apa pun) - utk kasus fallback
    file_master = folder / rme.NAMA_MASTER
    wb.save(file_master)
    return file_master


def uji_salinan_dibuat_dari_master_kalau_belum_ada():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        assert not (folder / rme.NAMA_SALINAN).exists()
        rme.catat({"Waktu": f"06-10-2026 09:15", "SKU": "AKS28", "No Picklist": "PICK-000157361",
                  "Total Pesanan": 10, "Resi Keluar": 10})
        rme.terapkan()
        assert (folder / rme.NAMA_SALINAN).exists()
    print("  PICKLIST.xlsx dibuat dari master kalau belum ada")


def uji_catat_isi_baris_pre_fill_tanpa_ganggu_formula():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat({"Waktu": "06-10-2026 09:15", "SKU": "AKS28", "No Picklist": "PICK-000157361",
                  "Total Pesanan": 10, "Resi Keluar": 9, "Tanpa Resi": ["SO123"]})
        rme.terapkan()

        from openpyxl import load_workbook
        wb = load_workbook(folder / rme.NAMA_SALINAN)
        ws = wb[rme.SHEET]
        assert ws.cell(8, rme.KOLOM_L_PICKLIST).value == 157361
        assert ws.cell(8, rme.KOLOM_F_OPR).value == "PUTRI"
        assert ws.cell(8, rme.KOLOM_H_JAM).value == 9.15
        assert ws.cell(8, rme.KOLOM_M_LOLOS).value == 10
        assert ws.cell(8, rme.KOLOM_N_PRINT).value == 9
        assert ws.cell(8, rme.KOLOM_T_JENIS).value == "AKS28"
        assert ws.cell(8, rme.KOLOM_U_CATATAN).value == "SO123"
        assert ws.cell(8, 2).value == '=IF(L8="","",I8&"-"&J8)'          # formula B utuh
        assert ws.cell(8, 5).value == '=IF(L8="","",IF(G8=G7,E7+1,1))'  # formula E utuh
        assert ws.cell(8, rme.KOLOM_L_PICKLIST).fill.patternType is None    # tidak kuning
    print("  catat(): isi baris pre-fill hari ini (F/G sudah ada), formula B/E tidak disentuh")


def uji_catat_fallback_baris_kosong_kalau_belum_ada_pre_fill():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        # tanggal 07-10-2026 belum di-pre-fill di master tiruan -> harus jatuh ke baris 9 (kosong)
        rme.catat({"Waktu": "07-10-2026 08:00", "SKU": "PTAA", "No Picklist": "PICK-000157400",
                  "Total Pesanan": 5, "Resi Keluar": 5})
        rme.terapkan()

        from openpyxl import load_workbook
        wb = load_workbook(folder / rme.NAMA_SALINAN)
        ws = wb[rme.SHEET]
        assert ws.cell(9, rme.KOLOM_F_OPR).value == "PUTRI"
        assert ws.cell(9, rme.KOLOM_G_TGL).value == datetime(2026, 10, 7)
        assert ws.cell(9, rme.KOLOM_L_PICKLIST).value == 157400
    print("  catat(): fallback ke baris kosong & isi F/G sendiri kalau belum ada pre-fill")


def uji_nomor_terlompat_jadi_baris_kuning_sebelum_baris_utama():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat({"Waktu": "06-10-2026 10:00", "SKU": "BSCT", "No Picklist": "PICK-000157363",
                  "Total Pesanan": 3, "Resi Keluar": 3}, nomor_terlompat=[157362])
        rme.terapkan()

        from openpyxl import load_workbook
        wb = load_workbook(folder / rme.NAMA_SALINAN)
        ws = wb[rme.SHEET]
        # baris 8 (pre-fill) dipakai utk nomor yang terlompat, baris 9 (fallback kosong) utk picklist asli
        assert ws.cell(8, rme.KOLOM_L_PICKLIST).value == 157362
        assert ws.cell(8, rme.KOLOM_T_JENIS).value == "PICKLIST CANCEL"
        for c in range(rme.KOLOM_FILL_AWAL, rme.KOLOM_FILL_AKHIR + 1):
            assert ws.cell(8, c).fill.fgColor.rgb == rme.WARNA_KUNING
        assert ws.cell(9, rme.KOLOM_L_PICKLIST).value == 157363
        assert ws.cell(9, rme.KOLOM_T_JENIS).value == "BSCT"
        assert ws.cell(9, rme.KOLOM_L_PICKLIST).fill.patternType is None
    print("  nomor_terlompat: baris kuning PICKLIST CANCEL ditulis sebelum baris picklist asli")


def uji_catatan_gagal_bikin_baris_kuning():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat({"Waktu": "06-10-2026 11:00", "SKU": "MX-5054", "No Picklist": "PICK-000157365",
                  "Total Pesanan": 2, "Catatan": "TERHENTI: timeout unduh label"})
        rme.terapkan()

        from openpyxl import load_workbook
        wb = load_workbook(folder / rme.NAMA_SALINAN)
        ws = wb[rme.SHEET]
        assert ws.cell(8, rme.KOLOM_L_PICKLIST).value == 157365
        for c in range(rme.KOLOM_FILL_AWAL, rme.KOLOM_FILL_AKHIR + 1):
            assert ws.cell(8, c).fill.fgColor.rgb == rme.WARNA_KUNING
    print("  Catatan GAGAL/TERHENTI: baris picklist itu sendiri ikut ditandai kuning")


def uji_tanpa_no_picklist_dilewati():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat({"SKU": "AKS28", "Catatan": "Dilewati: tidak ada stok"})
        assert rme._wb is None, "belum pernah buka workbook kalau tidak ada No Picklist"
        assert rme.jumlah_antrian() == 0
        rme.terapkan()
        assert not (folder / rme.NAMA_SALINAN).exists()
    print("  catat(): baris tanpa No Picklist (gagal sebelum picklist dibuat) dilewati")


# -------------------------------------------------- antrean (insiden 2026-10-06)
def _baris(no: int, waktu: str = "06-10-2026 13:45", **lain) -> dict:
    return {"Waktu": waktu, "SKU": f"SKU{no}", "No Picklist": f"PICK-000{no}",
            "Total Pesanan": 3, "Resi Keluar": 3, **lain}


def _isi_kolom_l(folder: Path) -> list:
    from openpyxl import load_workbook

    ws = load_workbook(folder / rme.NAMA_SALINAN)[rme.SHEET]
    return [ws.cell(r, rme.KOLOM_L_PICKLIST).value for r in range(6, 13)]    # [2] = baris 8


class _KunciSepertiExcel:
    """Buka file dengan share mode baca-saja (Windows CreateFileW) - persis cara Excel
    mengunci file yang sedang dibuka: proses lain masih bisa MEMBACA, tapi tidak bisa
    membukanya untuk ditulis maupun menimpanya lewat os.replace."""

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.HANDLE]
        generic_read, file_share_read, open_existing = 0x80000000, 0x1, 3
        self.k32 = k32
        self.h = k32.CreateFileW(str(self.path), generic_read, file_share_read, None,
                                 open_existing, 0, None)
        assert self.h not in (None, wintypes.HANDLE(-1).value), ctypes.get_last_error()
        return self

    def __exit__(self, *exc):
        self.k32.CloseHandle(self.h)


def _bisa_kunci_windows() -> bool:
    if sys.platform != "win32":
        print("  (dilewati: bukan Windows)")
        return False
    return True


def uji_catat_cuma_antre_tanpa_buka_workbook():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat(_baris(157401))
        rme.catat({"SKU": "X", "No Picklist": "PICK-000157402"})          # tanpa Waktu
        assert rme._wb is None, "catat() tidak boleh membuka PICKLIST.xlsx (~48 detik)"
        assert not (folder / rme.NAMA_SALINAN).exists()
        assert rme.jumlah_antrian() == 2
        entri = rme._baca_entri(folder / "logs" / rme.NAMA_ANTRIAN)
        assert entri[0]["baris"]["No Picklist"] == "PICK-000157401"
        assert entri[1]["baris"]["Waktu"], "Waktu kosong diisi saat catat(), bukan saat ditulis"
    print("  catat(): cuma menambah antrean (logs/), tidak membuka/membuat PICKLIST.xlsx")


def uji_terapkan_tulis_semua_antrean_berurutan_lalu_kosongkan():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat(_baris(157401))
        rme.catat(_baris(157403), nomor_terlompat=[157402])
        rme.catat(_baris(157404, Catatan="TERHENTI: HTTP 410"))
        assert rme.terapkan() == 3
        assert _isi_kolom_l(folder)[2:6] == [157401, 157402, 157403, 157404]
        assert rme.jumlah_antrian() == 0
        assert not list((folder / "logs").glob("antrian_*")), "antrean harus kosong"
        assert not (folder / rme.NAMA_SEMENTARA).exists()

        def _jangan_dibuka():
            raise AssertionError("antrean kosong tidak boleh membuka PICKLIST.xlsx")
        asli, rme._buka = rme._buka, _jangan_dibuka
        try:
            assert rme.terapkan() == 0
        finally:
            rme._buka = asli
    print("  terapkan(): semua antrean ditulis berurutan dalam 1x buka/simpan, antrean dikosongkan;"
          " antrean kosong tidak membuka workbook")


def uji_terapkan_berikutnya_lanjut_di_baris_setelahnya():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat(_baris(157401))
        rme.terapkan()
        rme.catat(_baris(157405))         # TIPE berikutnya
        rme.terapkan()
        assert _isi_kolom_l(folder)[2:4] == [157401, 157405]
    print("  terapkan() berulang (tiap TIPE): baris baru lanjut setelah baris sebelumnya")


def uji_salinan_sedang_dibuka_excel_antrean_tetap_disimpan():
    if not _bisa_kunci_windows():
        return
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat(_baris(157401))
        rme.terapkan()                                         # PICKLIST.xlsx sudah ada
        rme.catat(_baris(157402))

        def _jangan_dibuka():
            raise AssertionError("file terkunci Excel: jangan buang ~48 detik load_workbook()")
        asli, rme._buka = rme._buka, _jangan_dibuka
        try:
            with _KunciSepertiExcel(folder / rme.NAMA_SALINAN):
                assert rme.terapkan() == 0
        finally:
            rme._buka = asli
        assert rme.jumlah_antrian() == 1, "antrean tidak boleh dibuang"
        assert rme.terapkan() == 1                            # Excel sudah ditutup
        assert _isi_kolom_l(folder)[2:4] == [157401, 157402]
    print("  PICKLIST.xlsx dibuka di Excel: dilewati TANPA load, antrean tetap, ditulis di "
          "terapkan() berikutnya")


def uji_simpan_gagal_file_lama_utuh_dan_antrean_tidak_hilang():
    """Excel membuka PICKLIST.xlsx SETELAH dicek (di tengah ~2 menit load/save): os.replace
    gagal -> PICKLIST.xlsx lama tetap utuh (bukan setengah tertulis), file sementara dibuang,
    antrean lama + antrean baru tetap urut di terapkan() berikutnya."""
    if not _bisa_kunci_windows():
        return
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _buat_master(folder)
        rme.atur_root(folder)
        _reset()
        rme.catat(_baris(157401))
        rme.terapkan()
        rme.catat(_baris(157402))
        jeda_asli, cek_asli = rme.JEDA_COBA_GANTI_FILE_S, rme._sedang_dibuka
        rme.JEDA_COBA_GANTI_FILE_S, rme._sedang_dibuka = 0, lambda f: False
        try:
            with _KunciSepertiExcel(folder / rme.NAMA_SALINAN):
                assert rme.terapkan() == 0
        finally:
            rme.JEDA_COBA_GANTI_FILE_S, rme._sedang_dibuka = jeda_asli, cek_asli
        assert _isi_kolom_l(folder)[2:4] == [157401, None], "file lama harus utuh"
        assert not (folder / rme.NAMA_SEMENTARA).exists()
        rme.catat(_baris(157403))                    # antrean baru saat yang lama tertunda
        assert rme.jumlah_antrian() == 2
        assert rme.terapkan() == 2
        assert _isi_kolom_l(folder)[2:5] == [157401, 157402, 157403]
    print("  simpan gagal: PICKLIST.xlsx lama utuh, file sementara dibuang, antrean tertunda + "
          "baru ditulis urut berikutnya")


def uji_master_tidak_ada_catat_tidak_menambah_antrean():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        rme.atur_root(folder)
        _reset()
        rme.catat(_baris(157401))
        assert rme.jumlah_antrian() == 0
        assert rme.terapkan() == 0
        assert not (folder / rme.NAMA_SALINAN).exists()
    print("  file master tidak ada (fitur opsional): catat() tidak menumpuk antrean")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
