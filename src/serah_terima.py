"""Kunci serah-terima antar perangkat + pengecekan file konflik sinkron (OneDrive/Google Drive/
Syncthing) untuk skenario 2 perangkat bergantian memakai folder project yang disinkronkan
(PC kantor 07.00-17.00, laptop malam 20.00-24.00).

KUNCI: `logs/serah_terima.json` (folder logs ikut tersinkron). Tiap proses python yang mengubah
data (main.py --jalankan/--lanjut, print_spesial.py) memanggil `ambil()` di awal dan `lepas()` di
akhir. Kalau kunci dipegang PERANGKAT LAIN dan masih segar (pembaruan < TTL_DETIK), proses
ditolak - mencegah dua perangkat menulis nomor sesi/picklist/riwayat cetak yang sama. Proses
lain di perangkat yang SAMA boleh ikut (UI mencetak ke beberapa printer paralel): kunci menyimpan
daftar PID, bebas kalau daftarnya kosong. Kunci yang tidak diperbarui > TTL_DETIK dianggap basi
(proses mati mendadak) dan boleh diambil alih. Setelah dilepas, tercatat perangkat & waktu
terakhir selesai; perangkat lain yang mulai < JEDA_SINKRON_DETIK sesudahnya diberi PERINGATAN
(sinkron mungkin belum selesai mengirim data terbaru), bukan ditolak.

KONFLIK: `cari_konflik()` mencari file salinan konflik buatan klien sinkron di logs/, data/, dan
folder sesi label-pengiriman hari-hari terakhir. Hanya peringatan.

Kunci ini hanya sebaik sinkronnya: kalau sinkron belum mengirim kunci "dipegang" dari perangkat
lain, perangkat ini tidak melihatnya. Tetap tunggu indikator sinkron selesai sebelum berganti.
"""
from __future__ import annotations

import json
import os
import re
import socket
import time
from datetime import datetime, timedelta
from pathlib import Path

TTL_DETIK = 3 * 3600          # kunci tanpa pembaruan selama ini dianggap basi
JEDA_SINKRON_DETIK = 10 * 60  # perangkat lain baru selesai < ini lalu = peringatan sinkron

_file_kunci: Path | None = None
_memegang = False

# Pola nama salinan konflik: Syncthing ".sync-conflict-", Dropbox "conflicted copy",
# Google Drive/OneDrive "nama (1).ext", OneDrive "nama-NAMAPC.ext" (ditambah dinamis).
_POLA_BAKU = (re.compile(r"\.sync-conflict-", re.I), re.compile(r"conflicted copy", re.I),
              re.compile(r" \(\d+\)\.[A-Za-z0-9]+$"))


def atur_folder(folder_log: Path) -> None:
    global _file_kunci
    _file_kunci = folder_log / "serah_terima.json"


def nama_perangkat() -> str:
    """`PERANGKAT` di .env kalau ada, selain itu nama komputer Windows."""
    return (os.environ.get("PERANGKAT") or socket.gethostname() or "TIDAK-DIKENAL").strip().upper()


def _baca() -> dict:
    if not _file_kunci or not _file_kunci.exists():
        return {}
    try:
        d = json.loads(_file_kunci.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (ValueError, OSError):
        return {}   # file rusak/setengah tersinkron: perlakukan sebagai bebas


def _tulis(d: dict) -> None:
    _file_kunci.parent.mkdir(parents=True, exist_ok=True)
    sementara = _file_kunci.with_name(f"{_file_kunci.name}.{os.getpid()}.tmp")
    sementara.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(sementara, _file_kunci)


def _aktif(d: dict, sekarang: float) -> bool:
    return bool(d.get("pid")) and sekarang - d.get("pembaruan", 0) < TTL_DETIK


def _fmt(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%d-%m-%Y %H:%M")


def ambil(aksi: str, abaikan: bool = False) -> tuple[str | None, list[str]]:
    """Ambil kunci. Return (galat, peringatan): galat tidak None = proses HARUS berhenti.
    `abaikan` memaksa mengambil alih meski dipegang perangkat lain (dicatat sebagai peringatan)."""
    global _memegang
    if not _file_kunci:
        return None, []
    sekarang, saya = time.time(), nama_perangkat()
    d = _baca()
    peringatan: list[str] = []
    if _aktif(d, sekarang) and d.get("perangkat") != saya:
        pesan = (f"KUNCI SERAH-TERIMA dipegang perangkat {d.get('perangkat')} sejak "
                 f"{_fmt(d.get('mulai_epoch', 0))} ({d.get('aksi', '?')}), terakhir aktif "
                 f"{_fmt(d.get('pembaruan', 0))}. Tunggu selesai & sinkron, atau paksa dengan "
                 f"--abaikan-kunci (hanya kalau yakin perangkat itu sudah berhenti).")
        if not abaikan:
            return pesan, []
        peringatan.append("DIPAKSA: " + pesan)
    elif (not d.get("pid") and d.get("perangkat_terakhir") not in (None, saya)
          and sekarang - d.get("selesai", 0) < JEDA_SINKRON_DETIK):
        peringatan.append(
            f"Perangkat {d['perangkat_terakhir']} baru selesai {_fmt(d['selesai'])} (< "
            f"{JEDA_SINKRON_DETIK // 60} menit lalu). Pastikan SINKRON dari perangkat itu sudah "
            f"selesai diunduh ke sini sebelum lanjut.")
    pid_lain = [p for p in d.get("pid", []) if d.get("perangkat") == saya] if _aktif(d, sekarang) else []
    baru = {"perangkat": saya, "pid": sorted(set(pid_lain + [os.getpid()])), "aksi": aksi,
            "mulai_epoch": d.get("mulai_epoch", sekarang) if pid_lain else sekarang,
            "pembaruan": sekarang, "perangkat_terakhir": d.get("perangkat_terakhir"),
            "selesai": d.get("selesai", 0)}
    _tulis(baru)
    _memegang = True
    return None, peringatan


def lepas() -> None:
    """Lepas kunci milik proses ini (tidak berbuat apa-apa kalau tidak memegang)."""
    global _memegang
    if not _file_kunci or not _memegang:
        return
    _memegang = False
    d = _baca()
    pid = [p for p in d.get("pid", []) if p != os.getpid()]
    if d.get("perangkat") != nama_perangkat():
        return   # kunci sudah diambil alih perangkat lain (--abaikan-kunci): jangan ditimpa
    d["pid"] = pid
    if not pid:
        d.update(perangkat_terakhir=nama_perangkat(), selesai=time.time())
    d["pembaruan"] = time.time()
    _tulis(d)


def status() -> str:
    d, sekarang = _baca(), time.time()
    if not d:
        return "Kunci serah-terima: belum pernah dipakai."
    if _aktif(d, sekarang):
        return (f"Kunci: DIPEGANG {d['perangkat']} sejak {_fmt(d.get('mulai_epoch', 0))} "
                f"({d.get('aksi', '?')}), aktif terakhir {_fmt(d['pembaruan'])}.")
    basi = " (kunci basi, proses mungkin mati mendadak)" if d.get("pid") else ""
    return (f"Kunci: BEBAS{basi}. Terakhir dipakai {d.get('perangkat_terakhir') or d.get('perangkat')}"
            f" selesai {_fmt(d['selesai']) if d.get('selesai') else '-'}.")


def cari_konflik(root: Path, hari: int = 3, perangkat_lain: tuple[str, ...] = ()) -> list[Path]:
    """File salinan konflik di logs/, data/ dan folder sesi label-pengiriman `hari` hari terakhir.
    `perangkat_lain`: nama komputer lain (OneDrive menambah '-NAMAPC' di nama file konflik)."""
    pola = list(_POLA_BAKU)
    for nama in {nama_perangkat(), *(n.upper() for n in perangkat_lain if n)}:
        pola.append(re.compile(rf"-{re.escape(nama)}\.[A-Za-z0-9]+$", re.I))
    folder = [root / "logs", root / "data"]
    tgl = root / "label-pengiriman"
    hari_ini = datetime.now().date()
    folder += [tgl / str(hari_ini - timedelta(days=h)) for h in range(max(hari, 1))]
    ketemu = []
    for f in folder:
        if not f.is_dir():
            continue
        for p in f.rglob("*"):
            # .venv & template milik tim tidak diperiksa; hanya file biasa
            if p.is_file() and "template" not in p.parts and any(r.search(p.name) for r in pola):
                ketemu.append(p)
    return sorted(ketemu)


def laporan_konflik(root: Path, hari: int = 3) -> list[str]:
    """Baris peringatan siap cetak (kosong = tidak ada konflik)."""
    d = _baca()
    lain = tuple(n for n in (d.get("perangkat"), d.get("perangkat_terakhir")) if n)
    ketemu = cari_konflik(root, hari, lain)
    if not ketemu:
        return []
    return ([f"PERHATIAN: {len(ketemu)} file salinan KONFLIK sinkron ditemukan - dua perangkat "
             "mengubah file yang sama. Bandingkan, pertahankan yang benar, hapus salinannya:"]
            + [f"  {p.relative_to(root)}" for p in ketemu[:30]]
            + ([f"  ... dan {len(ketemu) - 30} lainnya"] if len(ketemu) > 30 else []))
