"""Pemulihan satu sesi (`main.py --pulihkan-sesi YYYY-MM-DD/N [--jalankan]`).

Hasilnya ditulis ke folder BARU `label-pengiriman/<tanggal>/N-PEMULIHAN` (N = nomor sesi
berikutnya hari itu; sesi asal TIDAK diubah) sehingga label pemulihan tampil & bisa dicetak
sebagai sesi tersendiri (lihat nama_sesi.py).

Untuk sesi yang SUDAH punya picklist berhasil dibuat tapi tahap sesudahnya bermasalah (PDF
kurang/rusak/ketinggalan pesanan yang resinya telat - insiden 2026-10-19 -, Excel tidak
lengkap, proses mati di tengah): program TIDAK membuat picklist baru, hanya mengulang tahap
sesudah picklist dibuat untuk SEMUA picklist sesi itu (proses_label.pulihkan_picklist():
selesaikan picking, minta resi, unduh ulang PDF, isi ulang detail-resi-*.xlsx, PICKLIST.xlsx
dan riwayat).

Daftar picklist sesi dibaca dari jurnal logs/picklist_terhenti.jsonl (tiap picklist yang dibuat
tercatat dengan nama/tag/subfolder/sesi); picklist yang tidak ada di jurnal tapi PDF-nya ada di
folder sesi ditambahkan dari nama file PDF-nya.
"""
from __future__ import annotations

import re
from pathlib import Path

import jurnal_peringatan
import nama_sesi

POLA_PDF = re.compile(r"^(PICK-\d+)_(.+)_\d{4}-\d{2}-\d{2}_\d{6}\.pdf$")
POLA_TAG = re.compile(r"^((?:[A-Z0-9]+_)?SPESIAL)_(.+)$")


def dari_jurnal(file_jurnal: Path | None, sesi: str) -> dict[str, dict]:
    """{no picklist: {nama, tag, subfolder}} dari baris op "dibuat"/"tambah" bertanda `sesi`."""
    hasil: dict[str, dict] = {}
    for d in jurnal_peringatan.baca_baris(file_jurnal):
        if d.get("op") in ("dibuat", "tambah") and d.get("sesi") == sesi and d.get("picklist"):
            hasil[d["picklist"]] = {"nama": d.get("nama"), "tag": d.get("tag"),
                                    "subfolder": d.get("subfolder")}
    return hasil


def dari_pdf(folder_sesi: Path) -> dict[str, dict]:
    """{no picklist: {nama, tag, subfolder}} dari nama file PDF di folder sesi."""
    hasil: dict[str, dict] = {}
    for f in sorted(folder_sesi.rglob("*.pdf")):
        m = POLA_PDF.match(f.name)
        if not m:
            continue
        sisa = m.group(2)
        t = POLA_TAG.match(sisa)
        tag, nama = (t.group(1), t.group(2)) if t else (None, sisa)
        rel = f.parent.relative_to(folder_sesi)
        subfolder = None if tag or str(rel) == "." else rel.parts[0]
        hasil.setdefault(m.group(1), {"nama": nama, "tag": tag, "subfolder": subfolder})
    return hasil


def kelas_jenis(nama: str) -> str:
    """Jenis picklist dari nama/label di kolom T PICKLIST.xlsx (= nama file PDF)."""
    n = (nama or "").upper()
    if n.startswith("1QTY-REGULER"):
        return "satuan"
    if n.startswith("KOMBINASI-REGULER"):
        return "kombinasi"
    if n.startswith("GTL-SICEPAT-SPESIAL-"):
        return "gtl-spesial"
    if n.startswith("SHOPEE-PAGI-SPESIAL-"):
        return "spx-pagi-spesial"
    if n.startswith("JNT-SIANG-SPESIAL-"):
        return "jnt-siang-spesial"
    if n.startswith("JNTSIANG-1QTY"):
        return "jnt-siang-satuan"
    if n.startswith(("GTL-SICEPAT", "LAZADA", "JNE-LEX", "URGENT")):
        return "urgent"
    if n.startswith("SHOPEE-PAGI"):
        return "spx-pagi"
    if n.startswith("JNT-SIANG"):
        return "jnt-siang"
    if n.startswith("SAMPEL"):
        return "sampel"
    return "spesial"


# (tag, subfolder) bawaan per jenis kalau tidak ada contoh lain di sesi yang sama
BAWAAN_JENIS = {"satuan": (None, "SATUAN"), "kombinasi": (None, "KOMBINASI"), "urgent": (None, "URGENT"),
                "gtl-spesial": (None, "GTL_SICEPAT_SPESIAL"),
                "spx-pagi-spesial": (None, "SPX-PAGI-SPESIAL"),
                "jnt-siang-spesial": (None, "JNT-SIANG-SPESIAL"), "jnt-siang-satuan": (None, "JNTSIANG_SATUAN"),
                "spx-pagi": (None, "SPX_PAGI"), "jnt-siang": (None, "JNT_SIANG"), "sampel": (None, None),
                "spesial": ("SPESIAL", None)}


def dari_excel(folder_sesi: Path, tahu: dict[str, dict]) -> dict[str, dict]:
    """{no picklist: {nama, tag, subfolder}} dari PICKLIST.xlsx sesi (kolom L nomor, T jenis/label).
    Menangkap picklist yang TIDAK punya PDF (belum ada resi sama sekali, mis. spesial yang resinya 0) dan
    tidak tercatat di jurnal (jurnal ada di PC lain / sesi lama). Baris "PICKLIST CANCEL" (nomor terlompat)
    dilewati. Tag/subfolder ditebak dari jenisnya, memakai contoh `tahu` (picklist sejenis yang sudah diketahui
    di sesi ini, mis. tag kurir JNT_SPESIAL) lebih dulu, baru nilai BAWAAN_JENIS."""
    contoh: dict[str, tuple] = {}
    for v in tahu.values():
        contoh.setdefault(kelas_jenis(v.get("nama")), (v.get("tag"), v.get("subfolder")))
    hasil = {}
    for angka, x in _baca_excel_sesi(folder_sesi).items():
        jenis = x.get("jenis")
        if not jenis or jenis.strip().upper() == "PICKLIST CANCEL":
            continue
        tag, subfolder = contoh.get(kelas_jenis(jenis)) or BAWAAN_JENIS[kelas_jenis(jenis)]
        hasil[f"PICK-{angka:09d}"] = {"nama": jenis.strip(), "tag": tag, "subfolder": subfolder}
    return hasil


def daftar_picklist(file_jurnal: Path | None, folder_sesi: Path, sesi: str) -> dict[str, dict]:
    """SEMUA picklist sesi, urut nomor: PICKLIST.xlsx sesi (paling lengkap, termasuk picklist tanpa PDF) +
    nama PDF + jurnal; yang lebih rinci menang (jurnal > PDF > Excel)."""
    gabung = dari_pdf(folder_sesi)
    gabung.update(dari_jurnal(file_jurnal, sesi))
    for no, v in dari_excel(folder_sesi, gabung).items():
        gabung.setdefault(no, v)
    return dict(sorted(gabung.items()))


def folder_pemulihan(folder_label: Path, tanggal: str) -> Path:
    """Buat & kembalikan `<folder_label>/<tanggal>/N-PEMULIHAN`, N = nomor sesi terbesar hari itu + 1
    (sesi biasa maupun pemulihan dihitung, jadi sesi biasa berikutnya tidak bentrok nomor)."""
    folder_tanggal = folder_label / tanggal
    folder_tanggal.mkdir(parents=True, exist_ok=True)
    terbesar = max((n for d in folder_tanggal.iterdir()
                    if d.is_dir() and (n := nama_sesi.nomor_sesi(d.name)) is not None), default=0)
    folder = folder_tanggal / nama_sesi.nama_pemulihan(terbesar + 1)
    folder.mkdir()
    return folder


POLA_WAKTU = re.compile(r"_(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\d{2}\.pdf$", re.IGNORECASE)


def _baca_excel_sesi(folder_sesi: Path) -> dict[int, dict]:
    """{nomor picklist: {total, resi, catatan}} dari PICKLIST.xlsx sesi (kolom L, M, N, U); kosong kalau
    file tidak ada/tak terbaca."""
    file = folder_sesi / "PICKLIST.xlsx"
    if not file.exists():
        return {}
    try:
        from openpyxl import load_workbook
        wb = load_workbook(file, read_only=True, data_only=False)
        hasil = {}
        for baris in wb.worksheets[0].iter_rows(min_row=6, min_col=12, max_col=21, values_only=True):
            nomor, total, resi, jenis, catatan = baris[0], baris[1], baris[2], baris[8], baris[9]
            if isinstance(nomor, int):
                hasil[nomor] = {"total": total if isinstance(total, (int, float)) else None,
                                "resi": resi if isinstance(resi, (int, float)) else None,
                                "jenis": str(jenis) if jenis else "",
                                "catatan": str(catatan) if catatan else ""}
        wb.close()
        return hasil
    except Exception:       # noqa: BLE001 - tampilan status tidak boleh gagal karena Excel rusak/terbuka
        return {}


def status_sesi(folder_sesi: Path, sesi: str, file_jurnal: Path | None, terhenti: dict[str, str],
                tanpa_resi: set[str]) -> dict:
    """Satu sesi untuk tab Pulih: {no, jam, pl: [{no, sub, nama, total, resi, st, catatan}]}. Status dari data
    LOKAL (tanpa Jubelio): terhenti (jurnal terhenti), pdf-hilang (tak ada PDF-nya), kurang (resi < total
    di PICKLIST.xlsx / ada peringatan tanpa resi), selain itu ok."""
    daftar = daftar_picklist(file_jurnal, folder_sesi, sesi)
    excel = _baca_excel_sesi(folder_sesi)
    pdf = {m.group(1) for f in folder_sesi.rglob("*.pdf") if (m := re.match(r"^(PICK-\d+)_", f.name))}
    waktu = [m.groups() for f in folder_sesi.rglob("*.pdf") if (m := POLA_WAKTU.search(f.name))]
    jam = min((f"{h}.{mnt}" for _, h, mnt in waktu), default="--.--")
    pl = []
    for no, v in daftar.items():
        angka = int(no.replace("PICK-", ""))
        x = excel.get(angka, {})
        total, resi = x.get("total"), x.get("resi")
        st, catatan = "ok", x.get("catatan", "")[:160]
        if no in terhenti:
            st, catatan = "terhenti", terhenti[no]
        elif no not in pdf and resi == 0:
            st, catatan = "kurang", "Belum ada resi sama sekali (belum ada PDF)"
        elif no not in pdf:
            st, catatan = "pdf-hilang", "File PDF tidak ada di folder sesi"
        elif no in tanpa_resi or (total is not None and resi is not None and resi < total):
            st = "kurang"
        pl.append({"no": no, "sub": v.get("tag") or v.get("subfolder") or "(sesi)", "nama": v.get("nama") or "",
                   "total": total, "resi": resi, "st": st, "catatan": catatan})
    return {"no": folder_sesi.name, "jam": jam, "pl": pl}


def asal_pemulihan(folder_pemulihan: Path) -> str | None:
    """"YYYY-MM-DD/N" sesi asal folder N-PEMULIHAN dari penanda pulihan.json (None kalau tak ada/rusak)."""
    import json
    try:
        return json.loads((folder_pemulihan / nama_sesi.NAMA_PENANDA_PULIHAN).read_text(encoding="utf-8"))["asal"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
