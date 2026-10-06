"""Deteksi pesanan yang sudah Picking > Selesai tapi belum dapat nomor resi setelah batas
tunggu (lihat minta_resi() di proses_label.py), padahal belum berstatus batal.

Ini biasanya tandanya ada request cancel dari customer/channel yang masih diproses Jubelio:
kalau request itu disetujui, status pesanan nanti jadi cancelled (resi memang tidak akan
pernah keluar); kalau ditolak, resi baru keluar belakangan dan pesanan jadi ready to ship.
Dicatat di sini (bukan cuma log.warning biasa) supaya tim resi langsung tahu nomor pesanan
mana saja yang begini dan bisa menginformasikannya ke tim admin/CS, tanpa perlu menelusuri
log atau riwayat_picklist.xlsx dulu.

Folder log diatur main.py lewat atur_folder(); tanpa itu (mis. di test) peringatan hanya
disimpan di memori proses ini.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

log = logging.getLogger("sku-spesial")

_file_peringatan: Path | None = None
_sesi: list[str] = []      # peringatan yang muncul di proses python ini
# catat() bisa dipanggil dari beberapa thread worker sekaligus (lihat MAKS_WORKER_PARALEL di
# proses_label.proses()), jadi _sesi & penulisan file dikunci supaya tidak ada baris tertimpa.
_lock = threading.Lock()


def atur_folder(folder_log: Path) -> None:
    global _file_peringatan
    _file_peringatan = folder_log / "pesanan_tanpa_resi.jsonl"


def catat(pesan: str) -> None:
    log.warning("  %s", pesan)
    with _lock:
        _sesi.append(pesan)
        if _file_peringatan:
            baris = {"epoch": datetime.now().timestamp(),
                     "waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "pesan": pesan}
            with open(_file_peringatan, "a", encoding="utf-8") as f:
                f.write(json.dumps(baris, ensure_ascii=False) + "\n")


def catat_tanpa_resi(picklist_no: str, sku: str, nomor_pesanan: list[str]) -> None:
    """Panggil tiap kali minta_resi() selesai tapi masih ada pesanan (bukan batal) tanpa resi."""
    if not nomor_pesanan:
        return
    catat(f"{len(nomor_pesanan)} pesanan picklist {picklist_no} (SKU {sku}) belum dapat resi: "
          f"{', '.join(nomor_pesanan)}. Kemungkinan ada request cancel yang masih diproses - "
          f"informasikan no pesanan ini ke tim admin/CS (kalau cancel disetujui nanti jadi "
          f"cancelled, kalau ditolak nanti jadi ready to ship dan resi keluar).")


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
          judul: str = "PERHATIAN: PESANAN BELUM DAPAT RESI (CEK KEMUNGKINAN REQUEST CANCEL)") -> None:
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
