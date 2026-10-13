"""Percobaan ulang OTOMATIS di akhir tiap TIPE: setelah semua langkah selesai (sebelum rekap
waktu), picklist yang TERHENTI/GAGAL selama TIPE itu (mis. gagal unduh label PDF, lihat
peringatan_gagal.catat_terhenti()) dilanjutkan SEKALI LAGI lewat `main.py --lanjut ... --jalankan`
- sama dengan tombol "Download ulang" di UI, tapi tanpa menunggu operator.

Dipakai menu_konsol.py dan jalankan_harian.py (satu perilaku). Hanya picklist op "tambah"
(benar-benar gagal) sejak awal TIPE yang dicoba; picklist yatim ("dibuat" tanpa catatan) tidak,
karena bisa saja masih diproses perangkat/proses lain. Mode uji tidak mencoba apa pun.
Satu kali saja per picklist: yang masih gagal tetap tercatat dan muncul di rekap akhir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import peringatan_gagal

SRC = Path(__file__).resolve().parent
FOLDER_LOG = SRC.parent / "logs"
NAMA_LANGKAH = "COBA ULANG GAGAL"


def perintah_lanjut(d: dict) -> list[str]:
    """Argumen lengkap `main.py --lanjut ... --jalankan` untuk satu item daftar_terhenti()."""
    p = [sys.executable, str(SRC / "main.py"), "--lanjut", d["picklist"], "--nama", d["nama"]]
    if d.get("tag"):
        p += ["--tag", d["tag"]]
    if d.get("subfolder"):
        p += ["--subfolder", d["subfolder"]]
    return p + ["--sesi", d["sesi"], "--jalankan"]


def terhenti_sejak(awal: float) -> list[dict]:
    """Picklist gagal (bukan yatim) yang tercatat sejak `awal`, urut paling lama dulu."""
    peringatan_gagal.atur_folder(FOLDER_LOG)
    return sorted((d for d in peringatan_gagal.daftar_terhenti()
                   if d.get("op") == "tambah" and d.get("epoch", 0) >= awal),
                  key=lambda d: d.get("epoch", 0))


def jalankan(awal: float, uji: bool, jalankan_proses, cetak=print) -> tuple[int, int]:
    """Coba ulang sekali picklist gagal sejak `awal`. `jalankan_proses(argumen) -> kode`.
    Mengembalikan (dicoba, pulih)."""
    if uji:
        return 0, 0
    antrean = terhenti_sejak(awal)
    if not antrean:
        return 0, 0
    cetak("")
    cetak(f"=== {NAMA_LANGKAH}: {len(antrean)} picklist gagal/terhenti dicoba sekali lagi ===")
    pulih = 0
    for i, d in enumerate(antrean, 1):
        cetak(f"--- {i}/{len(antrean)} {d['picklist']} ({d.get('nama')}) ---")
        try:
            kode = jalankan_proses(perintah_lanjut(d))
        except OSError as e:
            cetak(f"GAGAL menjalankan: {e}")
            kode = -1
        if kode == 0:
            pulih += 1
        else:
            cetak(f"{d['picklist']} masih gagal (lihat peringatan di rekap akhir)")
    cetak(f"{NAMA_LANGKAH}: {pulih}/{len(antrean)} berhasil dilanjutkan.")
    return len(antrean), pulih
