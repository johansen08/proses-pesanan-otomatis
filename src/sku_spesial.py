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


def resi_kandidat(df: pd.DataFrame) -> set[str]:
    """No pesanan yang lolos R1-R3; hanya ini yang perlu dicek nilainya ke API."""
    df = _tandai(df)
    lolos = (df["jml_baris_resi"] == 1) & (df["qty"] == 1) & (df["grup_kurir"] != "Lain")
    return set(df.loc[lolos, "No pesanan"])


def _rak_dominan(rak: pd.Series) -> str:
    """Rak yang paling sering dipakai SKU ini (biasanya cuma 1 rak per SKU)."""
    terisi = rak.dropna()
    terisi = terisi[terisi != ""]
    if terisi.empty:
        return "-"
    return terisi.mode().iat[0]


def hitung_sku_spesial(df: pd.DataFrame, nilai_pesanan: dict[str, float] | None = None):
    """nilai_pesanan: {No pesanan: grand_total}. None = aturan nilai 0 tidak dipakai."""
    df = _tandai(df)

    f1 = df[df["jml_baris_resi"] == 1]          # resi hanya 1 baris = 1 SKU
    f2 = f1[f1["qty"] == 1]                     # qty tepat 1
    f3 = f2[f2["grup_kurir"] != "Lain"]         # kurir J&T / SPX

    if nilai_pesanan is None:
        f4, resi_nilai_0, resi_tanpa_nilai = f3, 0, 0
    else:
        nilai = f3["No pesanan"].map(nilai_pesanan)
        # nilai 0 = pesanan kreator; nilai tidak ditemukan juga dikeluarkan
        f4 = f3[nilai.notna() & (nilai != 0)]
        resi_nilai_0 = int((nilai == 0).sum())
        resi_tanpa_nilai = int(nilai.isna().sum())

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
