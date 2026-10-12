"""Fungsi bersama modul peringatan_* (gagal, picklist, resi, sisa): jurnal JSONL lintas-proses
dan blok cetak peringatan. Modul ini tanpa status - tiap modul peringatan_* tetap memegang
`_file_peringatan`/`_sesi`-nya sendiri dan meneruskannya ke sini.

Satu baris jurnal peringatan = {"epoch", "waktu", "pesan"}; dibaca ulang oleh proses python lain
(rekap_waktu.py) lewat baca_sejak().
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

# Penulisan jurnal bisa datang dari beberapa thread worker sekaligus (lihat MAKS_WORKER_PARALEL
# di proses_label.proses()), jadi append ke file dikunci supaya tidak ada baris tertimpa.
_lock = threading.Lock()


def tambah_baris(file: Path | None, baris: dict) -> None:
    """Tambahkan `baris` (dict) ke jurnal JSONL `file`; diam saja kalau `file` None."""
    if not file:
        return
    with _lock, open(file, "a", encoding="utf-8") as f:
        f.write(json.dumps(baris, ensure_ascii=False) + "\n")


def baca_baris(file: Path | None) -> list[dict]:
    """Semua baris jurnal JSONL yang valid (baris rusak dilewati); kosong kalau file belum ada."""
    if not file or not file.exists():
        return []
    hasil = []
    for baris in file.read_text(encoding="utf-8").splitlines():
        try:
            hasil.append(json.loads(baris))
        except ValueError:
            continue
    return hasil


def catat_pesan(file: Path | None, pesan: str) -> None:
    """Simpan 1 peringatan teks ke jurnal `file` (format baku: epoch, waktu, pesan)."""
    sekarang = datetime.now()
    tambah_baris(file, {"epoch": sekarang.timestamp(),
                        "waktu": sekarang.strftime("%d-%m-%Y %H:%M"), "pesan": pesan})


def baca_sejak(file: Path | None, epoch: float) -> list[str]:
    """Peringatan yang tercatat sejak `epoch` (dari file, lintas proses python)."""
    return [f"[{d.get('waktu', '')}] {d.get('pesan', '')}"
            for d in baca_baris(file) if d.get("epoch", 0) >= epoch]


def cetak(peringatan: list[str], judul: str) -> None:
    """Cetak blok peringatan yang mencolok."""
    if not peringatan:
        return
    print()
    print("!" * 60)
    print(f"  {judul}")
    print("!" * 60)
    for p in peringatan:
        print(f"  - {p}")
    print("!" * 60)
