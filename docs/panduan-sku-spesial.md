# Panduan Otomatisasi: Excel "Laporan Siap Proses" → Laporan SKU Spesial (PDF)

Dokumen ini adalah spesifikasi + panduan implementasi untuk program yang berjalan otomatis:

```
[1] Download Excel  →  [2] Validasi  →  [3] Hitung SKU spesial  →  [4] Buat PDF  →  [5] Arsip / kirim
```

Tahap 2–4 sudah punya implementasi referensi Python yang teruji (lihat bagian 8).
Tahap 1 dan 5 bergantung pada sistem sumber dan tujuan Anda, jadi disediakan kerangka + checklist.

---

## 1. Istilah

| Istilah | Arti |
|---|---|
| **Resi** | Satu nilai unik di kolom `No pesanan`. |
| **Baris** | Satu baris di Excel = satu SKU dalam satu resi. |
| **Resi multi-baris** | `No pesanan` yang muncul lebih dari 1 baris → resi berisi lebih dari 1 SKU. |
| **Resi tunggal** | Resi yang memenuhi semua syarat R1–R3 (lihat bagian 3). |
| **SKU spesial** | SKU yang punya minimal 3 resi tunggal. |

---

## 2. Spesifikasi Input

- Format: `.xlsx`, sheet pertama (di contoh bernama `Data1`).
- **Baris header dicari otomatis** (bukan selalu baris 1): program membaca 30 baris pertama
  dan memakai baris pertama yang mengandung header `No pesanan` **dan** `SKU` (implementasi
  saat ini di `sku_spesial.py`, fungsi `_cari_baris_header()` — ditambahkan karena file export
  Jubelio kadang punya baris judul sebelum header).
- Excel ini **bersifat duplikat `No pesanan`**: satu resi dengan N SKU ditulis dalam N baris.

### Kolom yang dipakai

| Kolom | Tipe | Contoh | Keterangan |
|---|---|---|---|
| `No pesanan` | teks | `SP-2609261MWPGK1P`, `TT-586257037476792248-48087` | Kunci resi |
| `SKU` | teks | `C227-BRS3-2` | |
| `qty` | angka | `1` | |
| `Kurir` | teks | `SPX Hemat` | Lihat daftar di bawah |

Kolom lain (`Tanggal`, `Nama Barang`, `Nama Toko`, `Rak`, dst.) tidak dipakai dalam perhitungan.
Kolom boleh berpindah posisi, tetapi **nama header harus sama persis** (spasi di awal/akhir diabaikan).

### Nilai `Kurir` yang pernah muncul

| Nilai asli | Grup |
|---|---|
| `J&T Express Standard`, `J&T Express Hemat`, `J&T Express NEXT-DAY DELIVERY` | **J&T** ✅ |
| `SPX Hemat`, `SPX Standard` | **SPX** ✅ |
| `GoTo Logistics GTL ...`, `SiCepat ...` | Lain ❌ |

Aturan pengelompokan: **teks kurir diawali `J&T` atau `SPX`** (tidak peka huruf besar/kecil).
Varian layanan baru (mis. `SPX Instant`) otomatis ikut grupnya.

---

## 3. Aturan Bisnis

Sebuah resi dihitung sebagai **resi tunggal** jika memenuhi **semua** syarat:

| Kode | Syarat | Cara cek |
|---|---|---|
| **R1** | Resi hanya berisi 1 SKU | `No pesanan` muncul **tepat 1 baris** di seluruh file |
| **R2** | Qty = 1 | `qty == 1` pada baris tersebut |
| **R3** | Kurir J&T atau SPX | `Kurir` diawali `J&T` atau `SPX` |
| **R3b** | Bukan pesanan kreator | Nilai pesanan (`grand_total` dari API Jubelio) **≠ 0**. Excel tidak punya kolom nilai, jadi nilai diambil dari `GET core-api/wms/sales/v2/orders/ready-to-process/` (dicocokkan `salesorder_no` = `No pesanan`). Resi yang nilainya tidak ditemukan di API **juga dikeluarkan** dan jumlahnya dicatat sebagai peringatan di log. |

Lalu:

| Kode | Syarat |
|---|---|
| **R4** | SKU dinyatakan **spesial** jika jumlah resi tunggalnya **≥ 3** (J&T + SPX **digabung**). |

### Keputusan penting (jangan diubah tanpa persetujuan)

1. **R1 memakai jumlah baris, bukan jumlah SKU unik.** Setiap `No pesanan` yang muncul > 1 baris
   langsung gugur, apa pun isinya. Contoh: `SP-2609250XDF1N9W` berisi `C227-BRS3-1` (qty 1) dan
   `C227-BRS3-2` (qty 1) → **tidak dihitung** untuk kedua SKU.
2. **R2 dicek setelah R1.** Resi 1 baris dengan qty 2 atau lebih → gugur.
3. **R4 digabung**, bukan per kurir. (Jika per kurir: SKU spesial bila J&T ≥ 3 **atau** SPX ≥ 3 —
   pada data contoh hasilnya menjadi 18 SKU karena `BM-LCB009` = 2 J&T + 2 SPX.)
4. Filter kurir dilakukan **per resi setelah** R1, jadi resi multi-baris dengan kurir apa pun tetap gugur.

---

## 4. Algoritma

```
INPUT : tabel baris (No pesanan, SKU, qty, Kurir)

1. Bersihkan data
   - trim spasi pada No pesanan, SKU, Kurir
   - ubah qty ke angka (nilai tak valid → kosong)
   - buang baris yang No pesanan-nya kosong

2. Untuk setiap baris: jml_baris_resi = jumlah baris dengan No pesanan yang sama
3. Untuk setiap baris: grup_kurir = "J&T" | "SPX" | "Lain" (berdasarkan awalan teks)

4. f1 = baris dengan jml_baris_resi == 1          # R1
5. f2 = f1 dengan qty == 1                         # R2
6. f3 = f2 dengan grup_kurir != "Lain"             # R3
6b. ambil grand_total dari API untuk No pesanan di f3
    f3 = f3 tanpa resi dengan grand_total == 0 atau tidak ditemukan   # R3b

7. per_sku = hitung jumlah baris f3 per SKU        # 1 baris f3 = 1 resi
8. tabel   = per_sku dengan jumlah >= 3            # R4
             urutkan: **No Rak naik, lalu SKU naik (A–Z)** — bukan Jumlah Resi turun.
             ("No Rak" = rak yang paling sering dipakai SKU itu di kolom `Rak`, diambil
             dengan `_rak_dominan()`; urutan ini dipakai supaya proses per SKU di
             `proses_label.py` mengikuti urutan fisik rak gudang, bukan urutan jumlah resi.)

9. Total SKU Spesial  = banyaknya baris tabel
   Total Resi Spesial = jumlah kolom Jumlah Resi

10. Validasi: semua resi spesial harus jml_baris_resi == 1 dan No pesanan unik
             → jika gagal, hentikan program (jangan buat PDF)

OUTPUT: tabel (SKU, Jumlah Resi) + 2 total + ringkasan penyaringan
```

---

## 5. Spesifikasi Output (PDF)

PDF **hanya** berisi (sesuai implementasi saat ini di `sku_spesial.py::buat_pdf`):

1. **Tanggal** dan **Jam** laporan dibuat
2. **Tabel**

   | No Rak | SKU | Jumlah Resi |
   |---|---|---|
   | … | … | … |
   | **Total SKU Spesial** | | **n** |
   | **Total Resi Spesial** | | **n** |

   Baris data diberi warna latar per lantai gudang (digit pertama `No Rak`: `1`→biru,
   `2`→hijau, `3`→oranye, lainnya tanpa warna) — murni bantuan visual, tidak mengubah
   aturan bisnis R1–R4.

Tanpa judul, nama file sumber, keterangan syarat, atau ringkasan penyaringan
(ringkasan penyaringan dicatat di file log saja).

Nama file: `laporan-sku-spesial/SKU_Spesial_YYYY-MM-DD_HHMM.pdf`.

> **Sumber angka di tabel** (implementasi di `main.py`, bukan bagian 8 di bawah): dasarnya
> **kandidat** hasil algoritma bagian 4 (langkah 1-8 dokumen ini) untuk `main.py` biasa dan
> mode uji `--label`. Tapi untuk `--label --jalankan` (proses picklist sungguhan), PDF baru
> dibuat SETELAH proses selesai, dari jumlah pesanan yang **benar-benar berhasil dipicklist**
> per SKU — bisa lebih kecil dari kandidat kalau ada yang dilewati (< 3 resi tersisa), gagal,
> atau kena stok kosong/invalidSO. Lihat README bagian "Proses SKU spesial sampai label
> pengiriman" untuk detail.

---

## 6. Data Acuan untuk Pengujian

Gunakan file `laporan siap proses.xlsx` (data 26-09-2026) sebagai **golden test**.
Program dianggap benar jika hasilnya persis seperti ini.

### Ringkasan penyaringan

| Tahap | Jumlah |
|---|---:|
| Total baris | 747 |
| Total resi (No pesanan unik) | 445 |
| Resi multi-baris (gugur R1) | 128 resi / 430 baris |
| Lolos R1 (1 baris) | 317 |
| Lolos R2 (qty = 1) | 275 |
| Lolos R3 (J&T/SPX) | 262 |
| **Resi spesial** | **207** |
| **SKU spesial** | **19** |

### Tabel hasil

| No | SKU | Jumlah Resi |
|---:|---|---:|
| 1 | C227-BRS3-2 | 52 |
| 2 | GL-FNF-6 | 30 |
| 3 | GL-FNF-3 | 26 |
| 4 | T01-PTAA-5 | 12 |
| 5 | T01-PTAE-2 | 12 |
| 6 | C227-BRS3-1 | 10 |
| 7 | C226-GTJ-1 | 9 |
| 8 | T01-BKAG-2 | 9 |
| 9 | MX-5011-2 | 7 |
| 10 | MX-5054-1 | 6 |
| 11 | BM-AKS28-5 | 5 |
| 12 | C222-AK32-10 | 5 |
| 13 | BM-LCB009 | 4 |
| 14 | MX-5043-2 | 4 |
| 15 | T01-PTAD-3 | 4 |
| 16 | C223-ANT78-1 | 3 |
| 17 | MX-5040-5 | 3 |
| 18 | T01-PTAA-20 | 3 |
| 19 | T01-PTAD-2 | 3 |
| | **Total SKU Spesial** | **19** |
| | **Total Resi Spesial** | **207** |

### Kasus uji kecil (unit test)

| No pesanan | SKU | qty | Kurir | Hasil yang diharapkan |
|---|---|---:|---|---|
| A | X | 1 | SPX Hemat | ✅ dihitung untuk X |
| B | X | 1 | J&T Express Hemat | ✅ dihitung untuk X |
| C | X | 1 | spx standard | ✅ dihitung (huruf kecil tetap cocok) |
| D | X | 1 | SPX Hemat | ❌ D muncul 2 baris |
| D | Y | 1 | SPX Hemat | ❌ D muncul 2 baris |
| E | X | 2 | SPX Hemat | ❌ qty 2 |
| F | X | 1 | *(kosong)* | ❌ kurir kosong |
| G | X | 1 | GoTo Logistics GTL Hemat | ❌ kurir lain |
| " H" | Z | 1 | SPX Hemat | ✅ untuk Z (spasi di-trim) |
| I | Z | 1 | SPX Hemat | ✅ untuk Z |

Hasil: **X = 3 resi → spesial**, Z = 2 resi → tidak spesial. Total SKU spesial 1, total resi spesial 3.

---

## 7. Tahap 1 — Download Excel (kerangka)

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

## 8. Tahap 2–4 — Implementasi Referensi (Python)

Sudah diuji terhadap data acuan bagian 6 (hasil 19 SKU / 207 resi) dan kasus uji kecil.

> **Kode di bawah adalah versi AWAL** (lihat juga catatan di [README.md](../README.md)).
> Kode yang sungguhan dipakai adalah `sku_spesial.py` di folder ini, yang sudah berkembang
> dari versi ini dengan tambahan (tidak semuanya tercermin di kode contoh bawah):
> - Baris header dicari otomatis, bukan selalu baris 1 (lihat bagian 2).
> - Kolom `Rak` ikut dibaca; tabel & PDF punya kolom **"No Rak"** dan diurutkan per rak,
>   bukan per Jumlah Resi (lihat bagian 4 & 5).
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

### Kode `sku_spesial.py`

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

## 9. Tahap 5 — Menggabungkan Semua & Penjadwalan

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

### Struktur folder yang disarankan

```
sku-spesial/
├─ .env                  # APP_USER, APP_PASS (jangan di-commit)
├─ downloader.py         # tahap 1
├─ sku_spesial.py        # tahap 2–4
├─ main.py               # alur lengkap
├─ tests/test_sku.py     # kasus uji bagian 6
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

## 10. Penanganan Error & Checklist Validasi

| Kondisi | Tindakan |
|---|---|
| Download gagal / file 0 byte | Ulangi maks. 3 kali, lalu hentikan & catat di log |
| Kolom wajib hilang / nama header berubah | Hentikan, tampilkan nama kolom yang hilang |
| `qty` bukan angka | Baris tersebut otomatis tidak lolos R2; catat jumlahnya di log |
| Muncul nilai kurir baru | Catat di log daftar kurir unik yang masuk grup "Lain" untuk dicek |
| Validasi langkah 10 gagal | Hentikan, jangan buat PDF |
| File Excel sama diproses dua kali | Simpan hash file di log; lewati jika sudah pernah |

Checklist sebelum dipakai rutin:

- [ ] Golden test (bagian 6) menghasilkan 19 SKU / 207 resi
- [ ] Unit test kasus kecil lolos
- [ ] PDF menampilkan "J&T" dengan benar
- [ ] Kredensial tersimpan di `.env`, bukan di kode
- [ ] Log tersimpan tiap eksekusi (waktu, nama file, ringkasan penyaringan)

---

## 11. Parameter yang Bisa Diubah

| Parameter | Default | Lokasi |
|---|---|---|
| Minimal resi per SKU | `3` | `MIN_RESI` |
| Kurir yang dihitung | `("J&T", "SPX")` | `KURIR_DIIZINKAN` |
| Mode hitung kurir | gabungan | ubah logika R4 jika ingin per kurir |
| Kolom wajib | `No pesanan, SKU, qty, Kurir` | `KOLOM_WAJIB` |
| Urutan tabel/PDF | No Rak naik, lalu SKU naik | `hitung_sku_spesial()` (`sort_values`) |
| Warna latar per lantai (kosmetik) | lantai 1/2/3 → biru/hijau/oranye | `WARNA_LANTAI` |
| Batas baris pencarian header | 30 baris pertama | `_cari_baris_header()` |
