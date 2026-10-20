"""Penamaan folder sesi label: `N` (sesi biasa) atau `N-PEMULIHAN` (hasil pulihkan_sesi.py).

Satu-satunya tempat yang tahu pola ini supaya cetak bulk, UI, dan penomoran sesi baru
memperlakukan folder pemulihan sebagai sesi sungguhan (labelnya harus bisa dicetak)."""
from __future__ import annotations

import re

SUFIKS_PEMULIHAN = "PEMULIHAN"
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
