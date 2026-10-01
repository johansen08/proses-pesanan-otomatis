# Referensi Implementasi Awal: SKU Spesial

> **Dokumen ini bersifat historis/generik** — kerangka awal sebelum `src/sku_spesial.py` dan
> `src/proses_label.py` yang sebenarnya ditulis, disimpan sebagai rujukan desain (checklist
> "Tahap 1" download Excel, kode contoh pertama, pola penjadwalan generik). **Bukan** dokumentasi
> perilaku program saat ini — untuk itu lihat
> [panduan-sku-spesial.md](panduan-sku-spesial.md) (aturan bisnis & spesifikasi) dan kode
> `src/sku_spesial.py` langsung. Kode di bagian 2 di bawah sudah berkembang jauh dari versi
> contoh ini (lihat catatan di bagian 2).

---

## 1. Tahap 1 — Download Excel (kerangka)

Isi checklist ini sesuai sistem sumber Anda:

- [ ] URL halaman login dan halaman export
- [ ] Cara login (username/password, OTP, SSO?)
- [ ] Filter yang harus dipilih sebelum export (tanggal, status "siap proses", toko)
- [ ] Nama tombol export & format file yang dihasilkan
- [ ] Jam berapa data dianggap final untuk diproses

Rekomendasi:

- Pakai **API resmi** jika sistem menyediakannya (paling stabil).
- Jika hanya lewat web, pakai **Playwright** (Python) untuk otomatisasi browser.
- Simpan kredensial di **environment variable / file `.env`**, jangan ditulis di kode.
- Jangan otomatiskan CAPTCHA; jika sistem memakai CAPTCHA/OTP, gunakan sesi login yang disimpan
  (`storage_state`) yang diperbarui manual secara berkala.

Kerangka Playwright (ganti semua `<...>`):

```python
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def download_excel(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()

        page.goto("<URL_LOGIN>")
        page.fill("<selector_username>", os.environ["APP_USER"])
        page.fill("<selector_password>", os.environ["APP_PASS"])
        page.click("<selector_tombol_login>")

        page.goto("<URL_HALAMAN_LAPORAN_SIAP_PROSES>")
        # ... pilih filter jika perlu ...
        with page.expect_download() as info:
            page.click("<selector_tombol_export>")
        tujuan = folder / info.value.suggested_filename
        info.value.save_as(tujuan)

        browser.close()
    return tujuan
```

Setelah download, cek: file ada, ukuran > 0, bisa dibuka `pandas.read_excel`.

---

## 2. Tahap 2–4 — Implementasi Referensi (Python)

Diuji terhadap data acuan di [panduan-sku-spesial.md](panduan-sku-spesial.md) bagian 6
(hasil 19 SKU / 207 resi) dan kasus uji kecilnya.

> **Kode di bawah adalah versi AWAL.** Kode yang sungguhan dipakai adalah `src/sku_spesial.py`,
> yang sudah berkembang dari versi ini dengan tambahan (tidak semuanya tercermin di kode
> contoh bawah):
> - Baris header dicari otomatis, bukan selalu baris 1 (lihat panduan bagian 2).
> - Kolom `Rak` ikut dibaca; tabel & PDF punya kolom **"No Rak"** dan diurutkan per rak,
>   bukan per Jumlah Resi (lihat panduan bagian 4 & 5).
> - R3b (buang pesanan kreator via nilai API) sudah terintegrasi lewat parameter
>   `nilai_pesanan` di `hitung_sku_spesial()`, bukan tahap terpisah sesudahnya.
> - `hitung_sku_spesial()` juga mengembalikan `resi_per_sku` (daftar No pesanan per SKU)
>   yang dipakai `proses_label.py` untuk memproses picklist per SKU.

### Instalasi

Disarankan memakai virtual environment terpisah:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install pandas openpyxl reportlab
```

> Catatan: `reportlab` terbaru butuh `pillow` ≥ 12. Jika Python global Anda juga dipakai `streamlit`
> (butuh `pillow` < 12), wajib pakai venv terpisah agar tidak bentrok.

### Menjalankan

```bash
python sku_spesial.py "laporan siap proses.xlsx" --out laporan_sku_spesial.pdf
```

### Kode `sku_spesial.py` (versi awal)

```python
"""Buat laporan daftar SKU spesial (PDF) dari Excel 'laporan siap proses'.

Pemakaian:
    python sku_spesial.py "laporan siap proses.xlsx" --out laporan_sku_spesial.pdf
"""
import argparse
import html
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
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
def baca_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]

    hilang = [c for c in KOLOM_WAJIB if c not in df.columns]
    if hilang:
        raise ValueError(f"Kolom wajib tidak ditemukan: {hilang}")

    for c in ["No pesanan", "SKU", "Kurir"]:
        df[c] = df[c].astype("string").str.strip()
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")

    df = df.dropna(subset=["No pesanan"])
    df = df[df["No pesanan"] != ""]
    return df


# ---------------------------------------------------------------- 2. hitung
def grup_kurir(kurir: pd.Series) -> pd.Series:
    hasil = pd.Series("Lain", index=kurir.index)
    for awalan in KURIR_DIIZINKAN:
        hasil[kurir.fillna("").str.upper().str.startswith(awalan.upper())] = awalan
    return hasil


def hitung_sku_spesial(df: pd.DataFrame):
    df = df.copy()
    df["jml_baris_resi"] = df.groupby("No pesanan")["No pesanan"].transform("size")
    df["grup_kurir"] = grup_kurir(df["Kurir"])

    f1 = df[df["jml_baris_resi"] == 1]          # resi hanya 1 baris = 1 SKU
    f2 = f1[f1["qty"] == 1]                     # qty tepat 1
    f3 = f2[f2["grup_kurir"] != "Lain"]         # kurir J&T / SPX

    per_sku = f3.groupby("SKU").size().rename("Jumlah Resi").reset_index()
    tabel = (
        per_sku[per_sku["Jumlah Resi"] >= MIN_RESI]
        .sort_values(["Jumlah Resi", "SKU"], ascending=[False, True])
        .reset_index(drop=True)
    )

    resi_spesial = f3[f3["SKU"].isin(tabel["SKU"])]
    # Pengaman: tidak boleh ada resi multi-baris yang lolos
    if not (resi_spesial["jml_baris_resi"] == 1).all() or not resi_spesial["No pesanan"].is_unique:
        raise RuntimeError("Validasi gagal: ada resi multi-baris di daftar spesial")

    ringkasan = {
        "total_baris": len(df),
        "total_resi": df["No pesanan"].nunique(),
        "resi_1_baris": len(f1),
        "resi_1_baris_qty1": len(f2),
        "resi_lolos_kurir": len(f3),
        "total_sku_spesial": len(tabel),
        "total_resi_spesial": int(tabel["Jumlah Resi"].sum()),
    }
    return tabel, ringkasan


# ---------------------------------------------------------------- 3. PDF
def buat_pdf(tabel: pd.DataFrame, ringkasan: dict, sumber: Path, out: Path) -> None:
    gaya = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title="Laporan SKU Spesial")
    isi = [
        Paragraph("Laporan Daftar SKU Spesial", gaya["Title"]),
        Paragraph(f"Sumber: {html.escape(sumber.name)}<br/>"
                  f"Dibuat: {datetime.now():%d-%m-%Y %H:%M}", gaya["Normal"]),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Syarat: resi berisi 1 SKU dengan qty 1, kurir "
                  f"{html.escape(' / '.join(KURIR_DIIZINKAN))}, minimal {MIN_RESI} resi per SKU.",
                  gaya["Italic"]),
        Spacer(1, 0.5 * cm),
    ]

    data = [["No", "SKU", "Jumlah Resi"]]
    data += [[i + 1, sku, int(jml)]
             for i, (sku, jml) in enumerate(zip(tabel["SKU"], tabel["Jumlah Resi"]))]
    data += [["", "Total SKU Spesial", ringkasan["total_sku_spesial"]],
             ["", "Total Resi Spesial", ringkasan["total_resi_spesial"]]]

    t = Table(data, colWidths=[1.5 * cm, 9 * cm, 4 * cm], repeatRows=1)
    n = len(data)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, n - 2), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, n - 2), (-1, -1), colors.HexColor("#dde7f0")),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, n - 3), [colors.white, colors.HexColor("#f5f5f5")]),
    ]))
    isi.append(t)

    isi += [Spacer(1, 0.6 * cm), Paragraph("Ringkasan penyaringan", gaya["Heading3"])]
    alur = [
        ["Total baris data", ringkasan["total_baris"]],
        ["Total resi (No pesanan unik)", ringkasan["total_resi"]],
        ["Resi 1 baris (1 SKU)", ringkasan["resi_1_baris"]],
        ["Resi 1 baris, qty 1", ringkasan["resi_1_baris_qty1"]],
        ["Resi 1 baris, qty 1, kurir J&T/SPX", ringkasan["resi_lolos_kurir"]],
        [f"Resi spesial (SKU >= {MIN_RESI} resi)", ringkasan["total_resi_spesial"]],
    ]
    t2 = Table(alur, colWidths=[10.5 * cm, 4 * cm])
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    isi.append(t2)
    doc.build(isi)


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("excel", type=Path)
    ap.add_argument("--out", type=Path, default=Path("laporan_sku_spesial.pdf"))
    args = ap.parse_args()

    df = baca_excel(args.excel)
    tabel, ringkasan = hitung_sku_spesial(df)
    buat_pdf(tabel, ringkasan, args.excel, args.out)

    print(tabel.to_string(index=False))
    print(f"Total SKU Spesial : {ringkasan['total_sku_spesial']}")
    print(f"Total Resi Spesial: {ringkasan['total_resi_spesial']}")
    print(f"PDF disimpan di   : {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Catatan implementasi

- Karakter `&` pada teks yang masuk ke `Paragraph` reportlab **wajib di-escape** (`html.escape`),
  kalau tidak "J&T" akan tampil sebagai "J&T;".
- Jangan pakai `assert` untuk validasi produksi (bisa mati dengan `python -O`); pakai `raise`.
- Jika SKU spesial = 0, PDF tetap dibuat dengan tabel kosong dan total 0 (bukan error).

---

## 3. Tahap 5 — Menggabungkan Semua & Penjadwalan

### Program utama (contoh alur)

```python
from pathlib import Path
from datetime import datetime
from sku_spesial import baca_excel, hitung_sku_spesial, buat_pdf
# from downloader import download_excel   # tahap 1

def jalankan():
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    excel = download_excel(Path("data/masuk"))           # [1]
    df = baca_excel(excel)                                # [2]
    tabel, ringkasan = hitung_sku_spesial(df)             # [3]
    out = Path("data/laporan") / f"laporan_sku_spesial_{stamp}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    buat_pdf(tabel, ringkasan, excel, out)                # [4]
    # [5] kirim/arsip: salin ke folder bersama, email, dsb.
    return out
```

### Struktur folder yang disarankan (contoh generik, bukan struktur project ini)

```
sku-spesial/
├─ .env                  # APP_USER, APP_PASS (jangan di-commit)
├─ downloader.py         # tahap 1
├─ sku_spesial.py        # tahap 2–4
├─ main.py               # alur lengkap
├─ tests/test_sku.py     # kasus uji
├─ data/masuk/           # Excel hasil download (arsip mentah)
├─ data/laporan/         # PDF hasil
└─ logs/                 # log tiap eksekusi
```

### Penjadwalan di Windows

Pakai **Task Scheduler** → *Create Basic Task* → pilih jadwal (mis. setiap hari 08:00) →
*Start a program*:

- Program: `C:\path\ke\sku-spesial\.venv\Scripts\python.exe`
- Arguments: `main.py`
- Start in: `C:\path\ke\sku-spesial`

---

## 4. Penanganan Error & Checklist Validasi

| Kondisi | Tindakan |
|---|---|
| Download gagal / file 0 byte | Ulangi maks. 3 kali, lalu hentikan & catat di log |
| Kolom wajib hilang / nama header berubah | Hentikan, tampilkan nama kolom yang hilang |
| `qty` bukan angka | Baris tersebut otomatis tidak lolos R2; catat jumlahnya di log |
| Muncul nilai kurir baru | Catat di log daftar kurir unik yang masuk grup "Lain" untuk dicek |
| Validasi langkah 10 (panduan-sku-spesial.md bagian 4) gagal | Hentikan, jangan buat PDF |
| File Excel sama diproses dua kali | Simpan hash file di log; lewati jika sudah pernah |

Checklist sebelum dipakai rutin:

- [ ] Golden test ([panduan-sku-spesial.md](panduan-sku-spesial.md) bagian 6) menghasilkan 19 SKU / 207 resi
- [ ] Unit test kasus kecil lolos
- [ ] PDF menampilkan "J&T" dengan benar
- [ ] Kredensial tersimpan di `.env`, bukan di kode
- [ ] Log tersimpan tiap eksekusi (waktu, nama file, ringkasan penyaringan)
