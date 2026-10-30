"""Snapshot data Siap Proses per TIPE/job: Excel "Laporan Siap Proses" + nilai (grand_total) semua
pesanan Siap Proses, dipakai ulang oleh SEMUA langkah `main.py` dalam satu TIPE (konsol `menu_konsol.py`
maupun UI `jalankan_harian.py` mengisi env SNAPSHOT_SIAP_PROSES = path berkas snapshot, satu per TIPE).

Kenapa: tiap langkah label/reguler dulu mengunduh Excel (~8-10 detik) dan membaca ulang seluruh daftar
pesanan untuk nilainya; mode event punya 9-12 langkah seperti itu per TIPE, padahal datanya sama.
Snapshot basi aman: pesanan yang sudah masuk picklist langkah sebelumnya otomatis tersaring (cari_pesanan
hanya mengembalikan yang masih Siap Proses); pesanan BARU setelah snapshot tidak ikut hitungan spesial tapi
tetap ditangani langkah reguler (yang membaca pesanan hidup).

Tanpa env (jalan manual dari CLI) perilaku TIDAK berubah: selalu unduh baru. Snapshot lebih tua dari
UMUR_MAKS_S dianggap tidak ada.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "data" / "laporan-siap-proses"      # sama dengan main.FOLDER_EXCEL (dibersihkan otomatis 3 hari)
ENV = "SNAPSHOT_SIAP_PROSES"
UMUR_MAKS_S = 30 * 60


def jalur_baru(waktu: float | None = None, folder: Path | None = None) -> str:
    """Path berkas snapshot BARU untuk satu TIPE/job (unik per waktu + proses). Berkas baru ada setelah
    langkah pertama yang butuh Excel menyimpannya."""
    return str((folder or FOLDER) / f"snapshot_{int(waktu or time.time())}_{os.getpid()}.json")


class Snapshot:
    def __init__(self, path: Path):
        self.path = Path(path)

    def baca(self, sekarang: float | None = None) -> dict | None:
        """Isi snapshot ({"waktu", "excel", "nilai" | None, "tak_ketemu"}) atau None kalau tidak ada,
        rusak, lebih tua dari UMUR_MAKS_S, atau Excelnya sudah tidak ada."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if (sekarang or time.time()) - float(data["waktu"]) > UMUR_MAKS_S:
                return None
            if not Path(data["excel"]).is_file():
                return None
            return data
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def simpan(self, excel: str, nilai: dict | None, tak_ketemu: list[str] | None = None,
               sekarang: float | None = None) -> None:
        """Tulis atomik. `waktu` tetap waktu snapshot ASAL kalau Excel-nya sama (umur dihitung sejak unduh)."""
        lama = self.baca(sekarang)
        waktu = lama["waktu"] if lama and lama["excel"] == excel else (sekarang or time.time())
        isi = {"waktu": waktu, "excel": excel, "nilai": nilai, "tak_ketemu": list(tak_ketemu or [])}
        sementara = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            sementara.write_text(json.dumps(isi), encoding="utf-8")
            os.replace(sementara, self.path)
        except OSError:
            pass    # snapshot hanya optimasi: gagal menulis = langkah berikutnya mengunduh sendiri


def dari_env() -> Snapshot | None:
    path = os.environ.get(ENV)
    return Snapshot(Path(path)) if path else None
