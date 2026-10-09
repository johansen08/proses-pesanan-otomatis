"""Deteksi nomor picklist yang terlompat (picklist batal/gagal dibuat di Jubelio).

Nomor picklist Jubelio berurutan. Kalau pembuatan picklist ditolak/error di sisi Jubelio
(mis. "Internal Server Error"), nomornya bisa sudah terpakai tapi picklist-nya tidak ada,
sehingga picklist berikutnya melompat (mis. PICK-000155661 lalu PICK-000155663; 155662 tidak
ada di Jubelio). Modul ini mengingat nomor picklist terakhir yang dibuat program (lintas
proses python, disimpan di file) dan mencatat peringatan kalau ada nomor yang terlompat,
supaya di akhir proses tim resi tahu dan bisa menginformasikannya.

Catatan: nomor terlompat juga bisa karena ada orang lain membuat picklist langsung di
Jubelio di sela-sela program berjalan - pesannya sengaja menyebut kemungkinan ini.

Folder log diatur main.py lewat atur_folder(); tanpa itu (mis. di test) peringatan hanya
disimpan di memori proses ini.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

MAKS_NOMOR_DITAMPILKAN = 20

log = logging.getLogger("sku-spesial")

_file_terakhir: Path | None = None
_file_peringatan: Path | None = None
_sesi: list[str] = []      # peringatan yang muncul di proses python ini
_hilang_terakhir: list[int] = []   # nomor terlompat dari periksa_nomor() PALING TERAKHIR
_sudah_ada_picklist = False        # sudah ada picklist yang dibuat di proses python ini?


def atur_folder(folder_log: Path) -> None:
    global _file_terakhir, _file_peringatan, _sudah_ada_picklist
    _sudah_ada_picklist = False
    _file_terakhir = folder_log / "picklist_terakhir.txt"
    _file_peringatan = folder_log / "picklist_terlompat.jsonl"


def _angka(picklist_no: str) -> int | None:
    m = re.fullmatch(r"PICK-0*(\d+)", str(picklist_no).strip().upper())
    return int(m.group(1)) if m else None


def _baca_terakhir() -> int | None:
    try:
        return int(_file_terakhir.read_text().strip()) if _file_terakhir else None
    except (OSError, ValueError):
        return None


def catat(pesan: str) -> None:
    log.warning("  %s", pesan)
    _sesi.append(pesan)
    if _file_peringatan:
        baris = {"epoch": datetime.now().timestamp(),
                 "waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "pesan": pesan}
        with open(_file_peringatan, "a", encoding="utf-8") as f:
            f.write(json.dumps(baris, ensure_ascii=False) + "\n")


def periksa_nomor(picklist_no: str) -> str | None:
    """Panggil tiap kali picklist baru berhasil dibuat. Mengembalikan pesan peringatan
    kalau ada nomor yang terlompat sejak picklist terakhir yang dicatat, selain itu None.
    Nomor yang terlompat (kalau ada) juga disimpan utk ambil_nomor_hilang()."""
    global _hilang_terakhir, _sudah_ada_picklist
    n = _angka(picklist_no)
    if n is None:
        return None
    terakhir = _baca_terakhir()
    pesan = None
    _hilang_terakhir = []
    if terakhir is not None and n > terakhir + 1:
        hilang_nomor = list(range(terakhir + 1, n))
        # Gap sebelum picklist PERTAMA proses ini hanya diperingatkan, tidak masuk
        # ambil_nomor_hilang() (=> tidak ditulis "PICKLIST CANCEL" di PICKLIST.xlsx): terjadi
        # sebelum program jalan, bisa jadi dibuat orang lain di PC lain.
        if _sudah_ada_picklist:
            _hilang_terakhir = hilang_nomor
        hilang = [f"PICK-{i:09d}" for i in hilang_nomor]
        daftar = ", ".join(hilang[:MAKS_NOMOR_DITAMPILKAN])
        if len(hilang) > MAKS_NOMOR_DITAMPILKAN:
            daftar += f", ... (+{len(hilang) - MAKS_NOMOR_DITAMPILKAN} lagi)"
        pesan = (f"Nomor picklist terlompat: setelah PICK-{terakhir:09d} langsung "
                 f"PICK-{n:09d}. Tidak ada di program: {daftar}. Kemungkinan picklist batal/"
                 f"gagal dibuat karena Jubelio error (atau dibuat orang lain di Jubelio) - "
                 f"cek nomor tsb di Jubelio dan informasikan ke tim resi.")
        catat(pesan)
    _sudah_ada_picklist = True
    if _file_terakhir and (terakhir is None or n > terakhir):
        try:
            _file_terakhir.write_text(str(n))
        except OSError:
            pass
    return pesan


def ambil_nomor_hilang() -> list[int]:
    """Nomor picklist yang terlompat dari periksa_nomor() PALING TERAKHIR (kosong kalau tidak
    ada gap, atau gap itu terjadi SEBELUM picklist pertama proses ini) - dipakai
    rekap_master_excel.catat() utk menandai baris kuning "PICKLIST CANCEL" di PICKLIST.xlsx
    sesi, meniru pola manual yang sudah ada di file master (row 29, 05-10-2026).
    Panggil SEGERA setelah periksa_nomor() dipanggil utk picklist yang baru dibuat - sebelum
    periksa_nomor() dipanggil lagi untuk picklist berikutnya (nilainya ditimpa tiap panggilan)."""
    return _hilang_terakhir


def baca_sejak(epoch: float) -> list[str]:
    """Peringatan yang tercatat sejak `epoch` (dari file, lintas proses python)."""
    if not _file_peringatan or not _file_peringatan.exists():
        return []
    hasil = []
    for baris in _file_peringatan.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(baris)
        except ValueError:
            continue
        if d.get("epoch", 0) >= epoch:
            hasil.append(f"[{d.get('waktu', '')}] {d.get('pesan', '')}")
    return hasil


def cetak(peringatan: list[str], judul: str = "PERHATIAN: PICKLIST TERLOMPAT / BATAL") -> None:
    """Cetak blok peringatan yang mencolok (dipanggil paling akhir)."""
    if not peringatan:
        return
    print()
    print("!" * 60)
    print(f"  {judul}")
    print("!" * 60)
    for p in peringatan:
        print(f"  - {p}")
    print("!" * 60)


def cetak_sesi() -> None:
    cetak(_sesi)
