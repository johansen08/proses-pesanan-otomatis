"""Penamaan folder sesi label: `N` (sesi biasa) atau `N-PEMULIHAN` (hasil pulihkan_sesi.py).

Satu-satunya tempat yang tahu pola ini supaya cetak bulk, UI, dan penomoran sesi baru
memperlakukan folder pemulihan sebagai sesi sungguhan (labelnya harus bisa dicetak)."""
from __future__ import annotations

import re

SUFIKS_PEMULIHAN = "PEMULIHAN"
NAMA_PENANDA_PULIHAN = "pulihan.json"   # di folder N-PEMULIHAN: {"asal": "YYYY-MM-DD/N"}
POLA_SESI = re.compile(rf"^(\d+)(?:-({SUFIKS_PEMULIHAN}))?$")


def nomor_sesi(nama: str) -> int | None:
    """"10" -> 10, "11-PEMULIHAN" -> 11, selain itu None (bukan folder sesi)."""
    m = POLA_SESI.match(nama)
    return int(m.group(1)) if m else None


def urutan_sesi(nama: str) -> tuple[int, int] | None:
    """Kunci urut: nomor, lalu sesi biasa sebelum pemulihannya. None kalau bukan folder sesi."""
    m = POLA_SESI.match(nama)
    return (int(m.group(1)), 1 if m.group(2) else 0) if m else None


def nama_pemulihan(nomor: int) -> str:
    return f"{nomor}-{SUFIKS_PEMULIHAN}"


# Kode ringkas sesi untuk fitur Pilah (disambung "-" jadi nama folder hasil, mis. SPESIAL-SATUAN-1-2-11P):
# "11" = sesi biasa, "11P" = 11-PEMULIHAN.
POLA_KODE = re.compile(r"^(\d+)(P?)$")


def kode_sesi(nama: str) -> str | None:
    m = POLA_SESI.match(nama)
    return f"{int(m.group(1))}{'P' if m.group(2) else ''}" if m else None


def folder_dari_kode(kode: str) -> str:
    m = POLA_KODE.match(kode)
    if not m:
        raise ValueError(f"Kode sesi tidak dikenal: {kode!r}")
    return nama_pemulihan(int(m.group(1))) if m.group(2) else str(int(m.group(1)))


def urutan_kode(kode: str) -> tuple[int, int]:
    m = POLA_KODE.match(kode)
    return (int(m.group(1)), 1 if m.group(2) else 0) if m else (0, 0)
