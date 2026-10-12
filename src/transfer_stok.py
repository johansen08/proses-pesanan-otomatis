"""Jendela waktu Transfer Stok: pesanan TIDAK boleh diproses (picklist/picking/resi/label)
karena stok sedang dipindahkan antar gudang/rak. Dipakai `main.py` (--jalankan/--lanjut) dan
`jalankan_harian.py` (UI). Mode uji (read-only) tidak terpengaruh."""
from __future__ import annotations

from datetime import datetime, time as jam

# (mulai, selesai) WIB, batas dalam: mulai <= sekarang < selesai
JENDELA = [
    (jam(7, 50), jam(8, 0)),
    (jam(9, 0), jam(9, 10)),
    (jam(11, 0), jam(11, 10)),
    (jam(13, 0), jam(13, 10)),
    (jam(15, 0), jam(15, 10)),
    (jam(16, 0), jam(16, 10)),
]


def jendela_aktif(sekarang: datetime | None = None) -> tuple[jam, jam] | None:
    """Jendela Transfer Stok yang sedang berlangsung, atau None."""
    t = (sekarang or datetime.now()).time().replace(second=0, microsecond=0)
    for mulai, selesai in JENDELA:
        if mulai <= t < selesai:
            return mulai, selesai
    return None


def pesan(sekarang: datetime | None = None) -> str | None:
    """Teks peringatan kalau sedang jendela Transfer Stok, selain itu None."""
    j = jendela_aktif(sekarang)
    if not j:
        return None
    return (f"WAKTU TRANSFER STOK ({j[0]:%H.%M}-{j[1]:%H.%M}) - JANGAN PROSES PESANAN.\n"
            f"Tunggu sampai jam {j[1]:%H.%M}, lalu jalankan lagi.")


def popup(teks: str) -> None:
    """Pop up Windows (selalu di atas). Gagal/bukan Windows: diam saja (pesan tetap dicetak di log)."""
    try:
        import ctypes
        # MB_OK | MB_ICONWARNING | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST
        ctypes.windll.user32.MessageBoxW(0, teks, "Transfer Stok", 0x0 | 0x30 | 0x1000 | 0x10000 | 0x40000)
    except Exception:
        pass
