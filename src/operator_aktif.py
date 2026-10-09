"""Daftar operator & operator yang sedang menjalankan program (`data/operator.json`).

Nama operator aktif ditulis ke kolom F `PICKLIST.xlsx` oleh rekap_master_excel.py. File dibaca
ULANG tiap kali dipanggil (tanpa cache), jadi pergantian operator dari UI / `main.py --operator`
langsung berlaku di proses berikutnya tanpa restart. Kalau file belum ada, dipakai DAFTAR_AWAL
dengan operator aktif pertama di daftar; penulisan atomik (file sementara lalu os.replace).

Format: {"aktif": "PUTRI", "daftar": ["PUTRI", "ALFIANA", ...]}
"""
from __future__ import annotations

import json
import os
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "data" / "operator.json"
DAFTAR_AWAL = ["PUTRI", "ALFIANA", "SAHRUL", "DENADA", "SELVI"]


class OperatorError(ValueError):
    pass


def normalkan(nama) -> str:
    """Huruf besar, spasi berlebih dirapikan. Melempar OperatorError kalau kosong / bukan teks."""
    if not isinstance(nama, str) or not " ".join(nama.split()):
        raise OperatorError("Nama operator tidak boleh kosong")
    nama = " ".join(nama.split()).upper()
    if len(nama) > 30:
        raise OperatorError("Nama operator terlalu panjang (maks 30 karakter)")
    return nama


def _baca() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        daftar = [normalkan(n) for n in d["daftar"]]
        daftar = list(dict.fromkeys(daftar))
        if daftar:
            aktif = normalkan(d.get("aktif"))
            if aktif not in daftar:
                aktif = daftar[0]
            return {"aktif": aktif, "daftar": daftar}
    except (OSError, ValueError, KeyError, TypeError):
        pass       # file belum ada / rusak -> pakai bawaan
    return {"aktif": DAFTAR_AWAL[0], "daftar": list(DAFTAR_AWAL)}


def _tulis(d: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    sementara = FILE.with_name(f"{FILE.name}.{os.getpid()}.tmp")
    sementara.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(sementara, FILE)


def ambil_aktif() -> str:
    return _baca()["aktif"]


def ambil_daftar() -> list[str]:
    return _baca()["daftar"]


def info() -> dict:
    return _baca()


def tambah(nama) -> dict:
    """Tambah operator ke daftar (tidak mengganti operator aktif). Duplikat ditolak."""
    nama = normalkan(nama)
    d = _baca()
    if nama in d["daftar"]:
        raise OperatorError(f"Operator {nama} sudah ada di daftar")
    d["daftar"].append(nama)
    _tulis(d)
    return d


def set_aktif(nama) -> dict:
    """Ganti operator aktif; hanya nama yang sudah ada di daftar."""
    nama = normalkan(nama)
    d = _baca()
    if nama not in d["daftar"]:
        raise OperatorError(f"Operator {nama} belum ada di daftar (tambahkan dulu)")
    d["aktif"] = nama
    _tulis(d)
    return d
