"""Uji sku_spesial.py (logika murni berbasis pandas, tanpa API/Excel sungguhan dari Jubelio).

Jalankan:  .venv\\Scripts\\python tests\\test_sku_spesial.py
"""
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import sku_spesial as ss  # noqa: E402


def _df(baris):
    """baris: list of (No pesanan, SKU, qty, Kurir[, Rak])."""
    kolom = ["No pesanan", "SKU", "qty", "Kurir", "Rak"]
    data = [list(b) + [None] * (5 - len(b)) for b in baris]
    return pd.DataFrame(data, columns=kolom)


# -------------------------------------------------- kasus uji kecil dari docs/panduan-sku-spesial.md §6
def uji_kasus_kecil_dari_dokumentasi():
    df = _df([
        ("A", "X", 1, "SPX Hemat"),
        ("B", "X", 1, "J&T Express Hemat"),
        ("C", "X", 1, "spx standard"),
        ("D", "X", 1, "SPX Hemat"),
        ("D", "Y", 1, "SPX Hemat"),
        ("E", "X", 2, "SPX Hemat"),
        ("F", "X", 1, ""),
        ("G", "X", 1, "GoTo Logistics GTL Hemat"),
        (" H", "Z", 1, "SPX Hemat"),
        ("I", "Z", 1, "SPX Hemat"),
    ])
    tabel, ringkasan = ss.hitung_sku_spesial(df)
    assert list(tabel["SKU"]) == ["X"], tabel
    assert int(tabel.loc[tabel["SKU"] == "X", "Jumlah Resi"].iat[0]) == 3, tabel
    assert ringkasan["total_sku_spesial"] == 1
    assert ringkasan["total_resi_spesial"] == 3
    print("  kasus kecil dokumentasi: X = 3 resi -> spesial, Z = 2 resi -> tidak spesial")


def uji_resi_multibaris_gugur_r1():
    # D muncul 2 baris -> gugur untuk SEMUA SKU di baris itu, apa pun isinya
    df = _df([
        ("D", "X", 1, "SPX Hemat"),
        ("D", "Y", 1, "SPX Hemat"),
        ("A", "X", 1, "SPX Hemat"),
        ("B", "X", 1, "SPX Hemat"),
    ])
    kandidat = ss.resi_kandidat(df)
    assert kandidat == {"A", "B"}, kandidat
    print("  resi 2 baris (D): gugur untuk kedua SKU, tidak dihitung sama sekali")


def uji_r2_dicek_setelah_r1():
    # resi 1 baris dengan qty >= 2 -> gugur meski kurir & SKU valid
    df = _df([("A", "X", 2, "SPX Hemat")])
    kandidat = ss.resi_kandidat(df)
    assert kandidat == set(), kandidat
    print("  resi 1 baris qty 2: gugur di R2")


def uji_r4_digabung_bukan_per_kurir():
    # BM-LCB009: 2 J&T + 2 SPX = 4 digabung -> spesial (>=3), bukan per-kurir yang masing2 < 3
    baris = [(f"R{i}", "BM-LCB009", 1, "J&T Express Hemat") for i in range(2)] + \
            [(f"R{i}", "BM-LCB009", 1, "SPX Hemat") for i in range(2, 4)]
    df = _df(baris)
    tabel, ringkasan = ss.hitung_sku_spesial(df)
    assert list(tabel["SKU"]) == ["BM-LCB009"]
    assert int(tabel["Jumlah Resi"].iat[0]) == 4
    print("  R4 digabung: 2 J&T + 2 SPX = 4 resi -> spesial (bukan dihitung terpisah per kurir)")


def uji_r3b_nilai_pesanan_nol_atau_tidak_ditemukan_dikeluarkan():
    df = _df([(f"R{i}", "X", 1, "SPX Hemat") for i in range(4)])
    nilai_pesanan = {"R0": 10000.0, "R1": 0.0, "R2": 10000.0}   # R3 sengaja tidak ada di dict
    tabel, ringkasan = ss.hitung_sku_spesial(df, nilai_pesanan)
    assert ringkasan["resi_nilai_0"] == 1 and ringkasan["resi_tanpa_nilai"] == 1
    assert ringkasan["resi_lolos_nilai"] == 2
    assert tabel.empty, "cuma 2 resi valid (< MIN_RESI 3) -> X tidak spesial"
    print("  R3b: nilai 0 (kreator) dan nilai tidak ditemukan sama-sama dikeluarkan dari hitungan")


def uji_grup_kurir_tidak_peka_huruf_besar_kecil_dan_awalan():
    kurir = pd.Series(["J&T Express Hemat", "spx hemat", "SPX Instant", "GoTo Logistics GTL", None, ""])
    hasil = ss.grup_kurir(kurir)
    assert list(hasil) == ["J&T", "SPX", "SPX", "Lain", "Lain", "Lain"], list(hasil)
    print("  grup_kurir: varian layanan baru (SPX Instant) & huruf kecil tetap kecocok awalan")


def uji_urutan_tabel_no_rak_naik_lalu_sku_naik():
    baris = []
    for sku, rak in [("B-SKU", "2A"), ("A-SKU", "1A"), ("C-SKU", "1A")]:
        baris += [(f"{sku}-{i}", sku, 1, "SPX Hemat", rak) for i in range(3)]
    df = _df(baris)
    tabel, _ = ss.hitung_sku_spesial(df)
    assert list(tabel["SKU"]) == ["A-SKU", "C-SKU", "B-SKU"], tabel
    assert list(tabel["No Rak"]) == ["1A", "1A", "2A"], tabel
    print("  urutan tabel: No Rak naik dulu, lalu SKU A-Z (bukan Jumlah Resi turun)")


def uji_rak_dominan_pakai_rak_paling_sering_dipakai():
    baris = [(f"R{i}", "X", 1, "SPX Hemat", "1A") for i in range(3)] + \
            [("R3", "X", 1, "SPX Hemat", "1B")]
    df = _df(baris)
    tabel, _ = ss.hitung_sku_spesial(df)
    assert tabel.loc[tabel["SKU"] == "X", "No Rak"].iat[0] == "1A", tabel
    print("  rak dominan: rak yang paling sering muncul untuk SKU itu yang dipakai")


def uji_rak_dominan_kosong_jadi_strip():
    df = _df([(f"R{i}", "X", 1, "SPX Hemat", None) for i in range(3)])
    tabel, _ = ss.hitung_sku_spesial(df)
    assert tabel.loc[tabel["SKU"] == "X", "No Rak"].iat[0] == "-", tabel
    print("  rak kosong untuk semua resi SKU itu: No Rak jadi '-'")


def uji_grup_rak_per_pesanan_kompak_satu_grup():
    df = _df([
        ("A", "PTAA-47", 1, "SPX Hemat", "1B-A4-2"),
        ("A", "TL003", 1, "SPX Hemat", "1B-A5-2"),
        ("B", "MX-5054-7", 3, "J&T Express Hemat", "2B-A1-2"),
    ])
    hasil = ss.grup_rak_per_pesanan(df, ["2A", "3A", "1B", "2B", "3B"])
    assert hasil == {"A": "1B", "B": "2B"}, hasil
    print("  grup_rak_per_pesanan: komponen bundle beda rak tapi 1 grup -> grup itu terdeteksi")


def uji_grup_rak_per_pesanan_konflik_atau_tidak_dikenal_diabaikan():
    df = _df([
        ("C", "X", 1, "SPX Hemat", "1B-A1-1"),
        ("C", "Y", 1, "SPX Hemat", "2A-B1-1"),     # beda grup -> konflik, diabaikan
        ("D", "Z", 1, "SPX Hemat", "4C-X-1"),      # prefix di luar grup_rak -> diabaikan
        ("E", "W", 1, "SPX Hemat", None),          # tidak ada rak -> diabaikan
    ])
    hasil = ss.grup_rak_per_pesanan(df, ["2A", "3A", "1B", "2B", "3B"])
    assert hasil == {}, hasil
    print("  grup_rak_per_pesanan: beda grup dalam 1 pesanan, prefix tak dikenal, atau rak "
          "kosong -> tidak dimasukkan (biar fallback lain yg menentukan)")


def uji_grup_rak_per_pesanan_abaikan_komponen_tl_pada_konflik():
    # PTAA-71: TL001 (1B) + PTAA-22 (2B) - beda grup, tapi TL diabaikan -> pakai grup PTAA-22
    df = _df([
        ("F", "TL001", 1, "SPX Hemat", "1B-A5-2"),
        ("F", "PTAA-22", 1, "SPX Hemat", "2B-B6-3"),
    ])
    hasil = ss.grup_rak_per_pesanan(df, ["2A", "3A", "1B", "2B", "3B"])
    assert hasil == {"F": "2B"}, hasil
    print("  grup_rak_per_pesanan: komponen TL diabaikan saat beda grup dgn komponen lain "
          "(PTAA-22) -> pakai grup komponen non-TL")


def uji_grup_rak_per_pesanan_hanya_komponen_tl_tetap_dipakai():
    df = _df([("G", "TL005", 1, "SPX Hemat", "3A-C1-1")])
    hasil = ss.grup_rak_per_pesanan(df, ["2A", "3A", "1B", "2B", "3B"])
    assert hasil == {"G": "3A"}, hasil
    print("  grup_rak_per_pesanan: kalau cuma ada komponen TL sendirian (tidak ada komponen "
          "lain), tetap dipakai raknya")


def uji_grup_rak_per_pesanan_fallback_sku_dasar_bundle_bd():
    df = _df([
        ("H", "BD-MX-5054-2", 1, "SPX Hemat", None),            # bundle sendiri blm py rak
        ("I", "MX-5054-2", 2, "J&T Express Hemat", "2B-A1-2"),  # SKU dasar di pesanan lain
    ])
    hasil = ss.grup_rak_per_pesanan(df, ["2A", "3A", "1B", "2B", "3B"])
    assert hasil == {"H": "2B", "I": "2B"}, hasil
    print("  grup_rak_per_pesanan: bundle \"BD-\" tanpa rak sendiri -> fallback ke rak dominan "
          "SKU dasarnya (dari pesanan lain)")


def uji_sku_bundle_per_pesanan_hanya_rak_kosong_dan_tidak_ambigu():
    df = _df([
        ("A", "T01-PTAA-66", 1, "SPX Hemat", None),       # bundle, Rak kosong -> kandidat
        ("B", "X", 1, "SPX Hemat", "1B-A1-1"),            # Rak terisi -> bukan kandidat
        ("C", "SKU1", 1, "SPX Hemat", None),
        ("C", "SKU2", 1, "SPX Hemat", None),               # 2 SKU beda, Rak sama2 kosong -> ambigu
    ])
    hasil = ss.sku_bundle_per_pesanan(df)
    assert hasil == {"A": "T01-PTAA-66"}, hasil
    print("  sku_bundle_per_pesanan: hanya pesanan Rak kosong & 1 SKU yang diambil "
          "(bukan terisi, bukan ambigu >1 SKU)")


def uji_lantai_per_pesanan_longgar_beda_zona_sama_lantai():
    df = _df([
        ("A", "X", 1, "SPX Hemat", "2A-B1-1"),
        ("A", "Y", 1, "SPX Hemat", "2B-C2-2"),   # beda grup rak (2A vs 2B) tapi SAMA lantai
    ])
    hasil = ss.lantai_per_pesanan(df, ["1", "2", "3"])
    assert hasil == {"A": "2"}, hasil
    print("  lantai_per_pesanan: beda grup rak (2A vs 2B) tapi 1 lantai -> tetap terdeteksi "
          "(lebih longgar dari grup_rak_per_pesanan)")


def uji_lantai_per_pesanan_beda_lantai_diabaikan():
    df = _df([
        ("B", "X", 1, "SPX Hemat", "1B-A1-1"),
        ("B", "Y", 1, "SPX Hemat", "2A-B1-1"),   # beda lantai -> ambigu
    ])
    hasil = ss.lantai_per_pesanan(df, ["1", "2", "3"])
    assert hasil == {}, hasil
    print("  lantai_per_pesanan: beda lantai dalam 1 pesanan -> tidak dimasukkan (ambigu)")


def uji_lantai_per_pesanan_abaikan_tl_dan_fallback_sku_dasar():
    df = _df([
        ("C", "TL001", 1, "SPX Hemat", "1B-A5-2"),
        ("C", "PTAA-22", 1, "SPX Hemat", "2B-B6-3"),
        ("D", "BD-MX-5054-2", 1, "SPX Hemat", None),
        ("E", "MX-5054-2", 2, "J&T Express Hemat", "2B-A1-2"),
    ])
    hasil = ss.lantai_per_pesanan(df, ["1", "2", "3"])
    assert hasil == {"C": "2", "D": "2", "E": "2"}, hasil
    print("  lantai_per_pesanan: aturan abaikan-TL dan fallback bundle \"BD-\" tetap berlaku "
          "di granularitas lantai")


def uji_sku_dikecualikan_tidak_pernah_spesial():
    # C225-UB & semua variannya (C225-UB11-1, dst): kondisi khusus - tidak pernah dihitung
    # spesial walau resinya banyak
    df = (
        [(f"R{i}", "C225-UB", 1, "SPX Hemat") for i in range(5)]
        + [(f"T{i}", "C225-UB11-1", 1, "SPX Hemat") for i in range(5)]
        + [(f"U{i}", "C225-UB11-2", 1, "SPX Hemat") for i in range(5)]
        + [(f"V{i}", "C225-UB10-1", 1, "SPX Hemat") for i in range(5)]
        + [(f"S{i}", "X", 1, "SPX Hemat") for i in range(3)]
    )
    tabel, ringkasan = ss.hitung_sku_spesial(_df(df))
    assert list(tabel["SKU"]) == ["X"], tabel
    for sku in ("C225-UB", "C225-UB11-1", "C225-UB11-2", "C225-UB10-1"):
        assert sku not in ringkasan["resi_per_sku"], sku
    print("  AWALAN_SKU_DIKECUALIKAN_SPESIAL: C225-UB dan semua variannya "
          "(C225-UB11-1/C225-UB11-2/C225-UB10-1) tidak pernah masuk tabel spesial walau 5 resi "
          "masing-masing (SKU lain tetap dihitung normal)")


def uji_min_resi_tepat_batas():
    df2 = _df([(f"R{i}", "X", 1, "SPX Hemat") for i in range(2)])
    df3 = _df([(f"R{i}", "X", 1, "SPX Hemat") for i in range(3)])
    tabel2, _ = ss.hitung_sku_spesial(df2)
    tabel3, _ = ss.hitung_sku_spesial(df3)
    assert tabel2.empty, "2 resi belum spesial"
    assert list(tabel3["SKU"]) == ["X"], "tepat 3 resi sudah spesial"
    print("  batas MIN_RESI: 2 resi belum spesial, tepat 3 resi sudah spesial")


# -------------------------------------------------- baca_excel: header & kolom
def _tulis_excel(path: Path, baris_sebelum_header: list[list], header: list[str], data: list[list]):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    for b in baris_sebelum_header:
        ws.append(b)
    ws.append(header)
    for d in data:
        ws.append(d)
    wb.save(path)


def uji_cari_baris_header_bukan_baris_pertama():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "laporan.xlsx"
        _tulis_excel(f, [["Laporan Siap Proses"], ["Dicetak: 2026-09-26"]],
                     ["No pesanan", "SKU", "qty", "Kurir"],
                     [["A", "X", 1, "SPX Hemat"]])
        df = ss.baca_excel(f)
        assert list(df["No pesanan"]) == ["A"], df
        print("  baca_excel: header ditemukan walau bukan baris pertama (ada judul di atasnya)")


def uji_cari_baris_header_tidak_ditemukan():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "laporan.xlsx"
        _tulis_excel(f, [], ["Kolom Lain", "Lainnya"], [["x", "y"]])
        try:
            ss.baca_excel(f)
        except ValueError as e:
            assert "No pesanan" in str(e) or "SKU" in str(e)
        else:
            raise AssertionError("seharusnya ValueError kalau header tidak ditemukan")
        print("  baca_excel: ValueError kalau header 'No pesanan'/'SKU' tidak ada di 30 baris pertama")


def uji_kolom_wajib_hilang():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "laporan.xlsx"
        _tulis_excel(f, [], ["No pesanan", "SKU", "qty"],   # Kurir hilang
                     [["A", "X", 1]])
        try:
            ss.baca_excel(f)
        except ValueError as e:
            assert "Kurir" in str(e), e
        else:
            raise AssertionError("seharusnya ValueError kalau kolom wajib hilang")
        print("  baca_excel: ValueError menyebut nama kolom wajib yang hilang (mis. Kurir)")


def uji_baca_excel_buang_baris_no_pesanan_kosong_dan_trim_spasi():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "laporan.xlsx"
        _tulis_excel(f, [], ["No pesanan", "SKU", "qty", "Kurir"],
                     [[" A ", " X ", 1, " SPX Hemat "], [None, "Y", 1, "SPX Hemat"]])
        df = ss.baca_excel(f)
        assert list(df["No pesanan"]) == ["A"], df
        assert df["SKU"].iat[0] == "X" and df["Kurir"].iat[0] == "SPX Hemat"
        print("  baca_excel: baris No pesanan kosong dibuang, spasi di awal/akhir di-trim")


def uji_validasi_resi_multibaris_tidak_lolos_ke_tabel_spesial():
    # Pengaman internal: pastikan tidak pernah raise untuk kasus normal (regresi guard)
    df = _df([(f"R{i}", "X", 1, "SPX Hemat") for i in range(5)])
    tabel, ringkasan = ss.hitung_sku_spesial(df)
    resi_spesial = ringkasan["resi_per_sku"]["X"]
    assert len(resi_spesial) == len(set(resi_spesial)) == 5
    print("  validasi internal: resi spesial tetap unik & 1-baris (guard RuntimeError tidak terpicu)")



# -------------------------------------------------- mode event: hitung spesial PER KURIR
def _resi(awalan, kurir, jumlah, sku="X"):
    return [(f"{awalan}{i}", sku, 1, kurir) for i in range(jumlah)]


def uji_event_default_tetap_menggabung_semua_kurir():
    # 2 J&T + 2 SPX Hemat + 2 SPX Standard untuk SKU yang sama: digabung (alur harian) = 6 resi
    df = _df(_resi("J", "J&T Express Standard", 2) + _resi("H", "SPX Hemat", 2)
             + _resi("S", "SPX Standard", 2))
    tabel, ringkasan = ss.hitung_sku_spesial(df)
    assert int(tabel["Jumlah Resi"].iat[0]) == 6, tabel
    assert ringkasan["kurir_hitung"] is None
    assert ss.resi_kandidat(df) == ss.resi_kandidat(df, None) == set(df["No pesanan"])
    print("  tanpa kurir_hitung: J&T + SPX Hemat + SPX Standard tetap digabung (alur harian)")


def uji_event_jnt_dan_spx_hemat_dihitung_terpisah_masing_masing_min_resi():
    df = _df(_resi("J", "J&T Express Standard", 2) + _resi("H", "SPX Hemat", 2))
    # digabung 4 resi -> spesial; dipisah, masing-masing cuma 2 (< MIN_RESI 3) -> tidak spesial
    assert len(ss.hitung_sku_spesial(df)[0]) == 1
    for kurir in ("jnt", "spx-hemat"):
        tabel, _ = ss.hitung_sku_spesial(df, kurir_hitung=kurir)
        assert tabel.empty, (kurir, tabel)
    print("  event: 2 J&T + 2 SPX Hemat -> tidak ada yang spesial (ambang dihitung per kurir, "
          "bukan digabung 4)")


def uji_event_resi_spesial_hanya_dari_kurir_yang_dihitung():
    df = _df(_resi("J", "J&T Express Standard", 3) + _resi("H", "SPX Hemat", 3)
             + _resi("S", "SPX Standard", 5))
    tabel_j, r_j = ss.hitung_sku_spesial(df, kurir_hitung="jnt")
    tabel_h, r_h = ss.hitung_sku_spesial(df, kurir_hitung="spx-hemat")
    assert r_j["resi_per_sku"] == {"X": ["J0", "J1", "J2"]}, r_j["resi_per_sku"]
    assert r_h["resi_per_sku"] == {"X": ["H0", "H1", "H2"]}, r_h["resi_per_sku"]
    assert int(tabel_j["Jumlah Resi"].iat[0]) == int(tabel_h["Jumlah Resi"].iat[0]) == 3
    # SPX Standard 5 resi TIDAK pernah ikut menaikkan hitungan Hemat (dan tidak ikut spesial)
    assert not any(no.startswith("S") for r in (r_j, r_h)
                   for daftar in r["resi_per_sku"].values() for no in daftar)
    assert ss.resi_kandidat(df, "jnt") == {"J0", "J1", "J2"}
    assert ss.resi_kandidat(df, "spx-hemat") == {"H0", "H1", "H2"}
    print("  event: daftar resi spesial J&T dan SPX Hemat terpisah; SPX Standard (5 resi) "
          "tidak ikut spesial maupun menaikkan hitungan Hemat")


def uji_event_spx_hemat_tidak_menangkap_jnt_hemat_atau_spx_standard():
    df = _df(_resi("A", "SPX Hemat", 1) + _resi("B", "J&T Express Hemat", 3)
             + _resi("C", "spx standard", 3) + _resi("D", "spx hemat", 1) + _resi("E", " SPX Hemat ", 1))
    # kolom Kurir di-strip baca_excel(); _df() di sini tidak -> strip manual seperti baca_excel
    df["Kurir"] = df["Kurir"].astype("string").str.strip()
    _, r = ss.hitung_sku_spesial(df, kurir_hitung="spx-hemat")
    assert r["resi_per_sku"] == {"X": ["A0", "D0", "E0"]}, r["resi_per_sku"]
    print("  event: 'spx-hemat' cocok 'SPX Hemat'/'spx hemat' (huruf kecil), bukan J&T Hemat "
          "atau SPX Standard")


def uji_event_kurir_hitung_tidak_dikenal_ditolak():
    df = _df(_resi("A", "SPX Hemat", 3))
    for fungsi in (lambda: ss.hitung_sku_spesial(df, kurir_hitung="hemat"),
                   lambda: ss.resi_kandidat(df, "gtl")):
        try:
            fungsi()
        except ValueError as e:
            assert "tidak dikenal" in str(e)
        else:
            raise AssertionError("kurir_hitung salah harus ValueError, bukan diam-diam kosong")
    print("  kurir_hitung salah ketik -> ValueError (tidak diam-diam menghasilkan nol SKU spesial)")


def uji_event_kunci_kurir_hitung_sama_dengan_kurir_pilihan_proses_label():
    import proses_label as pl
    assert set(ss.KURIR_AWALAN_HITUNG) == set(pl.KURIR_PILIHAN), \
        "kunci --kurir harus sama di sku_spesial dan proses_label"
    print("  kunci KURIR_AWALAN_HITUNG sama dengan proses_label.KURIR_PILIHAN")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
