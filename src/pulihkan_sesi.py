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


def daftar_picklist(file_jurnal: Path | None, folder_sesi: Path, sesi: str) -> dict[str, dict]:
    """Gabungan jurnal + nama PDF (jurnal menang), urut nomor picklist."""
    gabung = dari_pdf(folder_sesi)
    gabung.update(dari_jurnal(file_jurnal, sesi))
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
