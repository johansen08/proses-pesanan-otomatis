"""Catat picklist/proses yang TERHENTI atau GAGAL (mis. timeout unduh label PDF - lihat
main.cetak_bermasalah()) ke file lintas-proses, supaya tetap terlihat di rekap paling akhir
tiap TIPE proses-harian.bat lewat rekap_waktu.py - bukan hanya tercetak sekali di tengah log
lalu tenggelam begitu langkah berikutnya berjalan (insiden 2026-10-06: picklist urgent
bermasalah luput kebaca karena cuma scroll ke rekap paling bawah).

main.cetak_bermasalah() sendiri sudah mencetak blok peringatan ini LANGSUNG saat terjadi -
modul ini cuma menyimpan salinannya ke file (pola sama dengan peringatan_picklist.py/
peringatan_resi.py) supaya proses python lain (rekap_waktu.py, dipanggil .bat setelah semua
langkah satu TIPE selesai) bisa membacanya kembali lewat baca_sejak().

Folder log diatur main.py lewat atur_folder(); tanpa itu (mis. di test) peringatan tidak
disimpan di mana pun (hanya diteruskan ke pemanggil lewat cetak_bermasalah()).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_file_peringatan: Path | None = None


def atur_folder(folder_log: Path) -> None:
    global _file_peringatan
    _file_peringatan = folder_log / "picklist_bermasalah.jsonl"


def catat(pesan: str) -> None:
    if not _file_peringatan:
        return
    baris = {"epoch": datetime.now().timestamp(),
             "waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "pesan": pesan}
    with open(_file_peringatan, "a", encoding="utf-8") as f:
        f.write(json.dumps(baris, ensure_ascii=False) + "\n")


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


def cetak(peringatan: list[str],
          judul: str = "PERHATIAN: PICKLIST TERHENTI/GAGAL (LANGKAH SEBELUMNYA)") -> None:
    """Cetak blok peringatan yang mencolok (dipanggil rekap_waktu.py di akhir tiap TIPE)."""
    if not peringatan:
        return
    print()
    print("!" * 60)
    print(f"  {judul}")
    print("!" * 60)
    for p in peringatan:
        print(f"  - {p}")
    print("!" * 60)
