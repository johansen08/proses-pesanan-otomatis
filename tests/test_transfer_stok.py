"""Tes jendela Transfer Stok (tanpa API). Jalankan: .venv\\Scripts\\python tests\\test_transfer_stok.py"""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import transfer_stok as ts  # noqa: E402
import jalankan_harian as jh  # noqa: E402


def t(jam_menit: str) -> datetime:
    h, m = map(int, jam_menit.split(":"))
    return datetime(2026, 10, 12, h, m, 30)


def test_batas_jendela():
    aktif = ["07:50", "07:59", "09:00", "09:09", "11:00", "11:09", "13:00", "13:09",
             "15:00", "15:09", "16:00", "16:09"]
    luar = ["07:49", "08:00", "08:30", "09:10", "10:59", "11:10", "13:10", "15:10", "16:10", "20:00", "00:00"]
    for x in aktif:
        assert ts.jendela_aktif(t(x)), x
        assert "TRANSFER STOK" in ts.pesan(t(x))
    for x in luar:
        assert ts.jendela_aktif(t(x)) is None, x
        assert ts.pesan(t(x)) is None, x
    assert "09.10" in ts.pesan(t("09:05"))


def test_ui_menolak_saat_transfer_stok():
    asli = ts.pesan
    ts.pesan = lambda sekarang=None: asli(t("09:05"))
    try:
        for langkah, judul in (([n for n, _ in jh.KATALOG[:1]], "TIPE 1"),):
            try:
                jh.mulai(langkah, judul)
                raise AssertionError("harus ditolak")
            except jh.HarianError as e:
                assert "TRANSFER STOK" in str(e)
    finally:
        ts.pesan = asli


if __name__ == "__main__":
    test_batas_jendela()
    test_ui_menolak_saat_transfer_stok()
    print("OK")
