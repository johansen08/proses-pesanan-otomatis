"""Buat laporan daftar SKU spesial (PDF) dari Excel 'laporan siap proses'.

Pemakaian:
    python src/sku_spesial.py "laporan siap proses.xlsx" --out laporan_sku_spesial.pdf
"""
import argparse
import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

# File Excel dari Jubelio tidak punya default style -> openpyxl selalu warning saat dibaca.
# Tidak berpengaruh ke hasil (openpyxl otomatis pakai style default-nya sendiri).
warnings.filterwarnings("ignore", message="Workbook contains no default style, apply openpyxl's default",
                        category=UserWarning, module="openpyxl.*")
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ---------------------------------------------------------------- konfigurasi
KOLOM_WAJIB = ["No pesanan", "SKU", "qty", "Kurir"]
KURIR_DIIZINKAN = ("J&T", "SPX")   # dicocokkan dengan awalan teks kolom Kurir
MIN_RESI = 3                       # minimal resi per SKU (J&T + SPX digabung)

# Mode EVENT (proses-event.bat, lihat docs/jadwal-proses.md): penentuan SKU spesial dihitung
# PER KURIR, bukan digabung - J&T dan SPX Hemat masing-masing punya ambang MIN_RESI sendiri dan
# daftar resi spesial sendiri; SPX Standard tidak punya jalur spesial sama sekali (volumenya
# kecil, hanya dipecah per lantai - lihat proses_label.proses_spx_standard()). Kunci = nilai
# --kurir CLI (sama dengan proses_label.KURIR_PILIHAN), nilai = awalan teks kolom Kurir Excel
# (huruf besar). Hanya dipakai kalau `kurir_hitung` diisi; default None = J&T+SPX digabung
# seperti semula (alur harian TIDAK berubah).
KURIR_AWALAN_HITUNG = {"jnt": "J&T", "spx": "SPX", "spx-hemat": "SPX HEMAT",
                       "spx-hemat-pagi": "SPX HEMAT", "spx-standard": "SPX STANDARD"}

# Awalan SKU yang SENGAJA tidak pernah dihitung spesial walau jumlah resinya >= MIN_RESI -
# dicocokkan dengan awalan teks SKU (bukan exact match), jadi semua varian seperti
# "C225-UB11-1"/"C225-UB11-2"/"C225-UB10-1" ikut dikecualikan. Resinya tetap mengalir ke jalur
# "satuan" (1qty reguler) lewat pisah_reguler() di proses_label.py, karena tidak termasuk
# resi_spesial_semua (kondisi khusus tim, 06-10-2026).
AWALAN_SKU_DIKECUALIKAN_SPESIAL = ("C225-UB",)


# ---------------------------------------------------------------- 1. baca data
def _cari_baris_header(path: Path) -> int:
    """Cari baris header (bisa bukan baris pertama jika export berisi judul)."""
    awal = pd.read_excel(path, sheet_name=0, header=None, nrows=30)
    for i, baris in awal.iterrows():
        isi = {str(v).strip() for v in baris if pd.notna(v)}
        if {"No pesanan", "SKU"} <= isi:
            return i
    raise ValueError("Header 'No pesanan' / 'SKU' tidak ditemukan di 30 baris pertama")


def baca_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, header=_cari_baris_header(path))
    df.columns = [str(c).strip() for c in df.columns]

    hilang = [c for c in KOLOM_WAJIB if c not in df.columns]
    if hilang:
        raise ValueError(f"Kolom wajib tidak ditemukan: {hilang}")

    for c in ["No pesanan", "SKU", "Kurir"]:
        df[c] = df[c].astype("string").str.strip()
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")

    if "Rak" not in df.columns:
        df["Rak"] = pd.NA
    df["Rak"] = df["Rak"].astype("string").str.strip()

    df = df.dropna(subset=["No pesanan"])
    df = df[df["No pesanan"] != ""]
    return df


# ---------------------------------------------------------------- 2. hitung
def grup_kurir(kurir: pd.Series) -> pd.Series:
    hasil = pd.Series("Lain", index=kurir.index)
    for awalan in KURIR_DIIZINKAN:
        hasil[kurir.fillna("").str.upper().str.startswith(awalan.upper())] = awalan
    return hasil


def _tandai(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["jml_baris_resi"] = df.groupby("No pesanan")["No pesanan"].transform("size")
    df["grup_kurir"] = grup_kurir(df["Kurir"])
    return df


def _lolos_kurir(df: pd.DataFrame, kurir_hitung: str | None = None) -> pd.Series:
    """Baris yang kurirnya ikut dihitung. `kurir_hitung` None = J&T atau SPX (digabung, seperti
    semula); selain itu salah satu kunci KURIR_AWALAN_HITUNG = hanya kurir/varian itu."""
    if kurir_hitung is None:
        return df["grup_kurir"] != "Lain"
    if kurir_hitung not in KURIR_AWALAN_HITUNG:
        raise ValueError(f"kurir_hitung tidak dikenal: {kurir_hitung!r} "
                         f"(pilihan: {sorted(KURIR_AWALAN_HITUNG)})")
    return df["Kurir"].fillna("").str.upper().str.startswith(KURIR_AWALAN_HITUNG[kurir_hitung])


def resi_kandidat(df: pd.DataFrame, kurir_hitung: str | None = None) -> set[str]:
    """No pesanan yang lolos R1-R3; hanya ini yang perlu dicek nilainya ke API.
    `kurir_hitung`: lihat _lolos_kurir() - harus sama dengan yang dipakai hitung_sku_spesial()."""
    df = _tandai(df)
    lolos = (df["jml_baris_resi"] == 1) & (df["qty"] == 1) & _lolos_kurir(df, kurir_hitung)
    return set(df.loc[lolos, "No pesanan"])


def _rak_dominan(rak: pd.Series) -> str:
    """Rak yang paling sering dipakai SKU ini (biasanya cuma 1 rak per SKU)."""
    terisi = rak.dropna()
    terisi = terisi[terisi != ""]
    if terisi.empty:
        return "-"
    return terisi.mode().iat[0]


# Prefix SKU komponen "tali/strap" pada bundle PTAA (mis. TL001, TL003) - item ini SUDAH ada
# di meja packer (dipasok terpisah), jadi rak/lantainya TIDAK dipertimbangkan saat menentukan
# grup rak bundle PTAA (picker kadang tidak perlu ambil lagi) - dikonfirmasi tim 03-10-2026
# (contoh: PTAA-71 = TL001 rak 1B + PTAA-22 rak 2B -> grup yang dipakai 2B, abaikan TL001).
AWALAN_KOMPONEN_DIABAIKAN = ("TL",)
# Prefix bundle yang SKU dasarnya didapat dengan membuang prefix ini (mis. "BD-MX-5054-2" ->
# "MX-5054-2") - dipakai saat baris pesanan si bundle sendiri tidak py Rak sama sekali (belum
# dialokasikan Jubelio), fallback ke rak yang paling sering dipakai SKU dasar itu di SKU lain
# (lihat _rak_dominan_per_sku()) - dikonfirmasi tim 03-10-2026.
AWALAN_BUNDLE_SKU_DASAR = ("BD-",)


def _rak_dominan_per_sku(df: pd.DataFrame) -> dict[str, str]:
    """SKU -> rak yang paling sering dipakai SKU itu, diagregasi dari SEMUA baris Excel (lintas
    pesanan) - dipakai grup_rak_per_pesanan() sebagai fallback kedua utk bundle yang baris
    pesanannya sendiri tidak py Rak (mis. "BD-MX-5054-2" tidak py Rak, tapi SKU dasarnya
    "MX-5054-2" muncul dgn Rak asli di pesanan lain)."""
    return df.groupby("SKU")["Rak"].agg(_rak_dominan).to_dict()


def _grup_dari_rak(rak, grup_rak: list[str]) -> str | None:
    if pd.isna(rak) or rak in ("", "-"):
        return None
    prefix = str(rak).split("-", 1)[0]
    return prefix if prefix in grup_rak else None


def _klasifikasi_per_pesanan(df: pd.DataFrame, klasifikasi,
                             rak_dominan_sku: dict[str, str] | None = None) -> dict[str, str]:
    """Inti bersama grup_rak_per_pesanan() & lantai_per_pesanan(): untuk tiap pesanan, abaikan
    komponen berawalan AWALAN_KOMPONEN_DIABAIKAN (TL) kalau ada komponen lain, lalu
    klasifikasikan Rak tiap baris yang tersisa lewat `klasifikasi(rak) -> key | None`. Kalau
    baris yang dipakai kompak 1 key -> pakai key itu; kalau tidak ada key sama sekali (mis. SKU
    bundle sendiri belum dialokasikan Jubelio) -> coba klasifikasikan rak dominan SKU dasarnya
    (strip AWALAN_BUNDLE_SKU_DASAR) lewat `klasifikasi` yang sama; kalau masih ambigu (>1 key
    beda) atau tidak ketemu -> pesanan itu TIDAK dimasukkan ke hasil (biar pemanggil pakai
    fallback lain / LAINNYA). `rak_dominan_sku`: hasil rak_dominan_per_sku(df) kalau pemanggil
    sudah menghitungnya sendiri (mis. main.py memanggil grup_rak_per_pesanan() DAN
    lantai_per_pesanan() untuk df yang sama) - dihitung ulang kalau tidak diberikan."""
    if rak_dominan_sku is None:
        rak_dominan_sku = _rak_dominan_per_sku(df)
    hasil = {}
    for no, grup_df in df.groupby("No pesanan"):
        tanpa_diabaikan = grup_df[~grup_df["SKU"].astype(str).str.upper()
                                  .str.startswith(AWALAN_KOMPONEN_DIABAIKAN)]
        baris = tanpa_diabaikan if not tanpa_diabaikan.empty else grup_df

        kunci = {kk for kk in (klasifikasi(r) for r in baris["Rak"]) if kk}
        if len(kunci) == 1:
            hasil[str(no)] = next(iter(kunci))
            continue
        if kunci:
            continue   # >1 key beda tanpa cara membedakan lagi -> ambigu, jangan ditebak

        kunci_dasar = set()
        for sku in baris["SKU"].astype(str):
            dasar = sku[len(aw):] if (aw := next((a for a in AWALAN_BUNDLE_SKU_DASAR
                                                  if sku.upper().startswith(a)), None)) else sku
            kk = klasifikasi(rak_dominan_sku.get(dasar))
            if kk:
                kunci_dasar.add(kk)
        if len(kunci_dasar) == 1:
            hasil[str(no)] = next(iter(kunci_dasar))
    return hasil


def rak_dominan_per_sku(df: pd.DataFrame) -> dict[str, str]:
    """Versi publik _rak_dominan_per_sku() - panggil SEKALI lalu teruskan ke
    grup_rak_per_pesanan()/lantai_per_pesanan() lewat parameter `rak_dominan_sku` kalau
    keduanya dipanggil untuk df yang sama (mis. main.py) - supaya agregasi groupby("SKU")
    penuh tidak dihitung ulang."""
    return _rak_dominan_per_sku(df)


def grup_rak_per_pesanan(df: pd.DataFrame, grup_rak: list[str],
                         rak_dominan_sku: dict[str, str] | None = None) -> dict[str, str]:
    """"No pesanan" -> grup rak (prefix sebelum '-' pertama di kolom Rak Excel). Dipakai
    proses_label.py sebagai fallback penentu grup rak khusus SKU bundling: API live Jubelio
    selalu melaporkan location_id -1 (lokasi virtual, bukan rak fisik) untuk item bundle,
    padahal kolom Rak di Excel ini tetap berisi rak fisik asli tiap komponennya (ditemukan
    03-10-2026 - lihat catatan di proses_label.py). Lihat _klasifikasi_per_pesanan() untuk
    aturan abaikan-TL/fallback-rak-dominan-SKU-dasarnya & parameter `rak_dominan_sku`."""
    return _klasifikasi_per_pesanan(df, lambda rak: _grup_dari_rak(rak, grup_rak), rak_dominan_sku)


def lantai_per_pesanan(df: pd.DataFrame, lantai_list: list[str],
                       rak_dominan_sku: dict[str, str] | None = None) -> dict[str, str]:
    """"No pesanan" -> lantai (digit pertama Rak Excel). Sama alasan & aturan dengan
    grup_rak_per_pesanan() (lihat _klasifikasi_per_pesanan()) - cuma granularitas lebih
    longgar: "2A" dan "2B" dianggap SAMA (lantai "2"). Dipakai fallback bagian kombinasi
    reguler (proses_label.py) yang lazim tersebar di >1 rak dalam 1 lantai yang sama."""
    def klasifikasi(rak):
        lt = _lantai(rak)
        return lt if lt in lantai_list else None
    return _klasifikasi_per_pesanan(df, klasifikasi, rak_dominan_sku)


def sku_bundle_per_pesanan(df: pd.DataFrame) -> dict[str, str]:
    """"No pesanan" -> SKU, utk pesanan yang kolom Rak-nya KOSONG di Excel (ciri khas SKU
    bundle - lihat grup_rak_per_pesanan(): Excel cuma punya 1 baris SKU bundle itu sendiri,
    tidak pernah meledak jadi baris komponen seperti di picklist fisik, jadi kolom Rak-nya
    tidak pernah terisi lewat jalur manapun - fallback _rak_dominan_per_sku()/AWALAN_BUNDLE_
    SKU_DASAR di _klasifikasi_per_pesanan() pun ikut gagal kalau SKU bundle itu TIDAK berawalan
    salah satu AWALAN_BUNDLE_SKU_DASAR, mis. "T01-PTAA-66"/"T01-PTAA-77", ditemukan 03-10-2026).

    Dipakai proses_label.grup_rak_bundle_live()/lantai_bundle_live() sebagai daftar kandidat
    SKU yang perlu dicoba diresolusi lewat API live Jubelio (variations/v2/,
    v2/inventory/items/) - fallback yang LEBIH DIUTAMAKAN daripada Excel utk SKU bundling,
    karena menemukan rak fisik komponen langsung dari master data, bukan menebak dari baris
    Excel yang memang tidak ada. Pesanan dengan >1 SKU beda di baris Rak kosongnya dilewati
    (ambigu, bukan kasus 1-SKU-bundle biasa)."""
    kosong = df[df["Rak"].isna() | df["Rak"].astype(str).isin(("", "-"))]
    hasil = {}
    for no, grup_df in kosong.groupby("No pesanan"):
        skus = set(grup_df["SKU"].astype(str))
        if len(skus) == 1:
            hasil[str(no)] = next(iter(skus))
    return hasil


def hitung_sku_spesial(df: pd.DataFrame, nilai_pesanan: dict[str, float] | None = None,
                       kurir_hitung: str | None = None):
    """nilai_pesanan: {No pesanan: grand_total}. None = aturan nilai 0 tidak dipakai.
    `kurir_hitung`: None (default) = J&T + SPX digabung; atau kunci KURIR_AWALAN_HITUNG untuk
    menghitung SATU kurir/varian saja (mode event) - resi kurir lain tidak ikut dihitung
    sehingga tidak menambah jumlah resi SKU maupun masuk daftar resi spesial."""
    df = _tandai(df)

    f1 = df[df["jml_baris_resi"] == 1]          # resi hanya 1 baris = 1 SKU
    f2 = f1[f1["qty"] == 1]                     # qty tepat 1
    f3 = f2[_lolos_kurir(f2, kurir_hitung)]     # kurir J&T / SPX (atau 1 kurir, mode event)

    if nilai_pesanan is None:
        f4, resi_nilai_0, resi_tanpa_nilai = f3, 0, 0
    else:
        nilai = f3["No pesanan"].map(nilai_pesanan)
        # nilai 0 = pesanan kreator; nilai tidak ditemukan juga dikeluarkan
        f4 = f3[nilai.notna() & (nilai != 0)]
        resi_nilai_0 = int((nilai == 0).sum())
        resi_tanpa_nilai = int(nilai.isna().sum())

    # lihat AWALAN_SKU_DIKECUALIKAN_SPESIAL
    f4 = f4[~f4["SKU"].astype(str).str.upper().str.startswith(
        tuple(a.upper() for a in AWALAN_SKU_DIKECUALIKAN_SPESIAL))]

    per_sku = f4.groupby("SKU").size().rename("Jumlah Resi").reset_index()
    rak_per_sku = f4.groupby("SKU")["Rak"].agg(_rak_dominan).rename("No Rak").reset_index()
    per_sku = per_sku.merge(rak_per_sku, on="SKU", how="left")
    tabel = (
        per_sku[per_sku["Jumlah Resi"] >= MIN_RESI]
        .sort_values(["No Rak", "SKU"], ascending=[True, True])
        .reset_index(drop=True)[["No Rak", "SKU", "Jumlah Resi"]]
    )

    resi_spesial = f4[f4["SKU"].isin(tabel["SKU"])]
    # Pengaman: tidak boleh ada resi multi-baris yang lolos
    if not (resi_spesial["jml_baris_resi"] == 1).all() or not resi_spesial["No pesanan"].is_unique:
        raise RuntimeError("Validasi gagal: ada resi multi-baris di daftar spesial")

    ringkasan = {
        "total_baris": len(df),
        "total_resi": df["No pesanan"].nunique(),
        "resi_1_baris": len(f1),
        "resi_1_baris_qty1": len(f2),
        "resi_lolos_kurir": len(f3),
        "kurir_hitung": kurir_hitung,
        "resi_nilai_0": resi_nilai_0,
        "resi_tanpa_nilai": resi_tanpa_nilai,
        "resi_lolos_nilai": len(f4),
        "total_sku_spesial": len(tabel),
        "total_resi_spesial": int(tabel["Jumlah Resi"].sum()),
        # {SKU: [No pesanan, ...]} - resi yang akan diproses sampai label
        "resi_per_sku": {sku: sorted(g["No pesanan"])
                         for sku, g in resi_spesial.groupby("SKU")},
    }
    return tabel, ringkasan


# ---------------------------------------------------------------- 3. PDF
WARNA_LANTAI = {
    "1": colors.HexColor("#dbe9f6"),   # biru soft
    "2": colors.HexColor("#dcefdc"),   # hijau soft
    "3": colors.HexColor("#fdecd2"),   # oranye soft
}


def _lantai(rak: str) -> str:
    rak = str(rak).strip()
    return rak[0] if rak and rak[0].isdigit() else ""


def buat_pdf(tabel: pd.DataFrame, ringkasan: dict, out: Path, waktu: datetime) -> None:
    """PDF hanya berisi tanggal & jam, lalu tabel SKU spesial beserta totalnya."""
    gaya = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title="SKU Spesial")
    isi = [
        Paragraph(f"Tanggal: {waktu:%d-%m-%Y}<br/>Jam: {waktu:%H:%M}", gaya["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    data = [["No Rak", "SKU", "Jumlah Resi"]]
    data += [[rak, sku, int(jml)] for rak, sku, jml
             in zip(tabel["No Rak"], tabel["SKU"], tabel["Jumlah Resi"])]
    data += [["Total SKU Spesial", "", ringkasan["total_sku_spesial"]],
             ["Total Resi Spesial", "", ringkasan["total_resi_spesial"]]]

    t = Table(data, colWidths=[4 * cm, 7 * cm, 3 * cm], repeatRows=1, hAlign="LEFT")
    gaya_tabel = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9d9d9")),
        ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
        ("SPAN", (0, -2), (1, -2)),
        ("SPAN", (0, -1), (1, -1)),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]
    for i, rak in enumerate(tabel["No Rak"], start=1):     # baris 1..n = baris data (0 = header)
        warna = WARNA_LANTAI.get(_lantai(rak))
        if warna:
            gaya_tabel.append(("BACKGROUND", (0, i), (-1, i), warna))
    t.setStyle(TableStyle(gaya_tabel))
    isi.append(t)
    doc.build(isi)


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("excel", type=Path)
    ap.add_argument("--out", type=Path, default=Path("laporan_sku_spesial.pdf"))
    args = ap.parse_args()

    df = baca_excel(args.excel)
    tabel, ringkasan = hitung_sku_spesial(df)
    buat_pdf(tabel, ringkasan, args.out, datetime.now())

    print(tabel.to_string(index=False))
    print(f"Total SKU Spesial : {ringkasan['total_sku_spesial']}")
    print(f"Total Resi Spesial: {ringkasan['total_resi_spesial']}")
    print(f"PDF disimpan di   : {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
